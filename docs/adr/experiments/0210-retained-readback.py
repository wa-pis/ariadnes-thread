"""Independently audit saved R5.59c science evidence without solving a conic."""

from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from itertools import product
import math
from types import ModuleType
from typing import Any

type Row = dict[str, Any]
type Vector = tuple[float, ...]

BODIES = ("Moon", "Mars")
SIGNS = ("positive", "negative")
PROPOSALS = {"retained": "analytic-command-proposal", "artificial": "artificial-command-proposal"}
EPS_V = 1e-6
EPS_R = 0.001
EPS_DURATION = 1e-6
EPS_MASS = 1e-8
RANK_GAP = Decimal("4e-6")


def _need(ok: object, reason: str) -> None:
    if not ok:
        raise ValueError(f"R5.59c readback: {reason}")


def _number(value: Any) -> float:
    _need(type(value) in (int, float) and math.isfinite(value), "nonfinite or nonnumeric field")
    return float(value)


def _vector(values: Any, count: int) -> Vector:
    _need(isinstance(values, list) and len(values) == count, f"expected {count} components")
    return tuple(map(_number, values))


def _word(value: Any) -> float:
    _need(type(value) is str and len(value) <= 32, "binary64 word")
    result = float.fromhex(value)
    _need(math.isfinite(result) and result.hex() == value, "noncanonical binary64 word")
    return result


def _decimal(value: Any) -> Decimal:
    _need(type(value) is str and 0 < len(value) <= 256, "decimal precision field")
    result = Decimal(value)
    _need(result.is_finite() and abs(result.adjusted()) <= 400, "unbounded decimal field")
    return result


def _root(row: Row, endpoint: Row) -> str | None:
    reason = row["reason"]
    if reason == "degenerate":
        _need(set(row) == {"reason"}, "degenerate root evidence")
        return reason
    if reason == "independent-classification":
        _need(row["primary"] != row["oracle"] or row["primary"] not in (None, "guard", "degenerate"),
              "root classification agrees")
        return reason
    _need(reason in (None, "guard", "independent-invariant"), "unrecognized root decision")
    radius = _number(row["minimum_radius_m"])
    bounds = row["discrepancies"]
    _need(set(bounds) == {"asymptote_m_s", "impulse_m_s", "velocity_m_s", "tnw_m_s", "radius_m"},
          "root discrepancy inventory")
    _need(row["radial"] in ("outward", "inward", "turning") and radius > 0, "root leg classification")
    impulse = _vector(row["impulse_m_s"], 3)
    v_hyp = _vector(row["hyperbolic_velocity_m_s"], 3)
    v_inf = _vector(row["reconstructed_excess_m_s"], 3)
    a, e = _vector(row["angles_rad"], 2)
    _need(-math.pi <= a < math.pi and abs(e) <= math.pi/2, "root TNW angle domain")
    oracle_speed = _decimal(row["independent_speed_m_s"])
    _need(oracle_speed > 0 and math.hypot(*impulse) > 0, "nonpositive impulse norm")
    errors = {key: _number(value) for key, value in bounds.items()}
    _need(min(errors.values()) >= 0, "negative root discrepancy")
    if reason != "independent-invariant":
        _need(all(error <= (EPS_R if key == "radius_m" else EPS_V) for key, error in errors.items()),
              "root exceeds independent gates")
        _need((reason == "guard") == (radius <= _number(endpoint["guard_m"]) + EPS_R),
              "root guard decision")
        local_v = tuple(float(_decimal(word)) for word in endpoint["relative_si"][3:])
        # Compare the recorded impulse at each endpoint with the physical-time velocity change.
        sign = 1 if endpoint["body"] == "Moon" else -1
        _need(math.dist(impulse, tuple(sign * (a-b) for a, b in zip(v_hyp, local_v, strict=True))) <= EPS_V
              and math.dist(v_inf, _vector(endpoint["v_infinity_m_s"], 3)) <= EPS_V
              and abs(math.hypot(*impulse) - float(oracle_speed)) <= EPS_V, "signed root operands")
    return reason


def _ledgers(epochs: Vector, durations: Vector, rate: float, initial: float, dry: float
             ) -> tuple[str | None, Row | None]:
    t0, tx, tf = epochs
    td, ta = durations
    t1, t2 = t0 + td, tf - ta
    if not (0 < min(td, ta) and t0 < t1 < tx < t2 < tf):
        return "exact-event-order", None
    elapsed = {"commanded": (Fraction(td), Fraction(ta)),
               "effective": (Fraction(t1)-Fraction(t0), Fraction(tf)-Fraction(t2))}
    exact_rate = Fraction(rate)
    flows = {}
    for basis, spans in elapsed.items():
        coast = Fraction(initial) - exact_rate*spans[0]
        final = coast - exact_rate*spans[1]
        if final < dry:
            return f"{basis}-dry-floor", None
        flows[basis] = list(map(str, (coast, coast, final)))
    return None, dict(epoch_words=[t.hex() for t in (t0, t1, tx, t2, tf)], mass_kg_exact=flows)


def _pair(pair: Row, d: Row, a: Row, epochs: Vector, craft: Row, rejected: set[Vector]) -> bool:
    initial, dry, thrust, isp = (_number(craft[key]) for key in
                                 ("initial_mass_kg", "dry_mass_kg", "max_thrust_n", "isp_s"))
    exhaust = 9.80665 * isp
    rate = thrust / exhaust
    speeds = tuple(math.hypot(*_vector(row["impulse_m_s"], 3)) for row in (d, a))
    refs = tuple(_decimal(row["independent_speed_m_s"]) for row in (d, a))
    _need(_number(pair["total_delta_v_m_s"]) == sum(speeds), "binary64 ranking cost")
    with localcontext(prec=96):
        _need(_decimal(pair["oracle_total_delta_v_m_s"]) == sum(refs), "independent ranking cost")
        masses_hi = (Decimal(initial)*(-refs[0]/Decimal(exhaust)).exp(),
                     Decimal(initial)*(-sum(refs)/Decimal(exhaust)).exp())
        durations_hi = ((Decimal(initial)-masses_hi[0])/Decimal(rate),
                        (masses_hi[0]-masses_hi[1])/Decimal(rate))
    before = initial
    durations, masses = [], []
    for speed in speeds:
        consumed = -before*math.expm1(-speed/exhaust)
        before -= consumed
        durations.append(consumed/rate)
        masses.append(before)
    duration_error = max(abs(x-float(y)) for x, y in zip(durations, durations_hi, strict=True))
    mass_error = max(abs(x-float(y)) for x, y in zip(masses, masses_hi, strict=True))
    errors = pair["independent_mass_discrepancies"]
    _need(set(errors) == {"duration_s", "mass_kg"} and _number(errors["duration_s"]) == duration_error
          and _number(errors["mass_kg"]) == mass_error, "independent sequence discrepancies")
    ledger = None
    controls = (*_vector(d["angles_rad"], 2), durations[0], *_vector(a["angles_rad"], 2), durations[1])
    if duration_error > EPS_DURATION or mass_error > EPS_MASS:
        reason = "independent-mass"
    else:
        reason, ledger = _ledgers(epochs, tuple(durations), rate, initial, dry)
        if reason is None and controls in rejected:
            reason = "historically-rejected"
    _need(pair["reason"] == reason and pair.get("ledgers") == ledger, "pair decision or exact ledger")
    if reason is None:
        _need(pair["command_words"] == [value.hex() for value in controls]
              and _vector(pair["ideal_end_masses_kg"], 2) == tuple(masses), "pair controls or ideal masses")
        return True
    _need(pair.get("command_words") is None and pair.get("ideal_end_masses_kg") is None,
          "rejected pair declares commands or masses")
    return False


def _science(report: Row, io: ModuleType) -> None:
    mode, status = report["mode"], report["status"]
    normalized, digest = report.get("normalized"), report.get("normalized_sha256")
    branches, pairs = report.get("branch_decisions"), report.get("pairs")
    words, selection = report["command_words"], report.get("selected_roots")
    _need(mode in PROPOSALS, "unknown profile")
    if status == "invalid-evidence":
        _need(normalized is None and digest is None and words is None and selection is None and
              branches in (None, {}) and pairs in (None, []) and
              isinstance(report.get("error"), str) and 0 < len(report["error"]) <= 512, "invalid evidence shape")
        return
    _need(isinstance(normalized, dict) and digest == io._sha(io._wire(normalized)), "normalized digest")
    _need(normalized["scope"] == mode and normalized["source_pins"] == report["source_pins"]
          and normalized["candidate_id"] == report["candidate_id"]
          and normalized["epoch_words"] == report["epoch_words"]
          and normalized["schema"] == "ariadna-r559c-normalized-input-v1"
          and normalized["status"] == "archive-inputs-validated"
          and normalized["command_words"] is None and normalized["live_authorized"] is False
          and type(normalized["source_bytes"]) is int and 0 < normalized["source_bytes"] <= 512 * 1024,
          "normalized archive binding")
    epochs = _vector(normalized["epochs_tdb_s"], 3)
    _need(epochs[0] < epochs[1] < epochs[2] and normalized["epoch_words"] == [value.hex() for value in epochs],
          "normalized epoch words")
    _need(set(branches) == set(BODIES) and isinstance(pairs, list) and len(pairs) <= 4,
          "branch and pair inventory")
    roots: dict[str, list[str]] = {}
    unresolved = False
    for body, endpoint, epoch in zip(BODIES, normalized["endpoints"], epochs[::2], strict=True):
        _need(endpoint["body"] == body and endpoint["epoch_word"] == epoch.hex()
              and _number(endpoint["epoch_tdb_s"]) == epoch, "normalized endpoint epoch")
        group = branches[body]
        roots[body] = []
        if set(group) == {"rejected"}:
            _need(isinstance(group["rejected"], str) and group["rejected"], "unresolved body reason")
            unresolved = True
            continue
        _need(set(group) == set(SIGNS), "both signed roots required")
        for sign in SIGNS:
            reason = _root(group[sign], endpoint)
            unresolved |= reason not in (None, "guard", "degenerate")
            if reason is None:
                roots[body].append(sign)
    expected = set() if unresolved else set(product(*(roots[body] for body in BODIES)))
    got = [tuple(pair["roots"]) for pair in pairs]
    _need(len(got) == len(set(got)) and set(got) == expected, "Cartesian pair coverage")
    rejected = set()
    for command in normalized["rejected_command_words"]:
        _need(isinstance(command, list) and len(command) == 6, "historical exclusion words")
        rejected.add(tuple(map(_word, command)))
    good = [p for p in pairs if _pair(p, branches["Moon"][p["roots"][0]], branches["Mars"][p["roots"][1]],
                                      epochs, normalized["spacecraft"], rejected)]
    top = None
    if unresolved:
        reason = "unresolved-geometry"
    elif any(p["reason"] == "independent-mass" for p in pairs):
        reason = "unresolved-mass"
    elif not good:
        reason = "no-eligible-pair"
    else:
        by_local = sorted(good, key=lambda p: _number(p["total_delta_v_m_s"]))
        by_oracle = sorted(good, key=lambda p: _decimal(p["oracle_total_delta_v_m_s"]))
        top = by_local[0]
        reason = None
        if len(good) > 1 and (top is not by_oracle[0] or
            by_local[1]["total_delta_v_m_s"] - top["total_delta_v_m_s"] <= float(RANK_GAP) or
            Fraction(_decimal(by_oracle[1]["oracle_total_delta_v_m_s"])) -
            Fraction(_decimal(top["oracle_total_delta_v_m_s"])) <= Fraction(RANK_GAP)
        ):
            reason = "ambiguous-rank"
    if reason is None and top is not None:
        _need(status == PROPOSALS[mode] and report.get("reason") is None
              and words == top["command_words"] and selection == top["roots"], "unique proposal binding")
    else:
        _need(status == "command-seed-unavailable" and report["reason"] == reason and words is None
              and selection is None, "scientific refusal binding")


def validate_science(report: Row, io: ModuleType) -> None:
    """Verify the saved decision, exact ledgers and ranking without running the solver."""
    try:
        _science(report, io)
    except (KeyError, TypeError, OverflowError, InvalidOperation, IndexError) as exc:
        raise ValueError("R5.59c readback: malformed science evidence") from exc
