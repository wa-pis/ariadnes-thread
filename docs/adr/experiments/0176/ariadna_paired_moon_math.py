"""ADR0175 exact paired assembly and recorded point-mass comparisons."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from math import hypot, isfinite
from typing import Any, Protocol

from ariadna_frozen_moon_math import _relative_check, _saved_product
from ariadna_split_analysis import (
    _binary64_field, _binary_vector, _decimal, _decimal_field, _decimal_vector,
    _gate, _norm, _round_exact, _squares, _subtract,
)
from ariadna_split_common import FAILURES, number, require

ORDINALS = (1, 2, 4, 6, 11, 15, 16, 18, 20, 25, 27)
CAPS = {"observation": len(ORDINALS), "binary64_field": 22, "decimal_field": 110}
ARMS = ("proxy", "measured")
PRECISIONS = (80, 100)
RELATIVE = Decimal("1e-60")
INCREMENT_LIMIT_M = Fraction(1, 10**12)

type ExactVector = tuple[Fraction, ...]
type FloatVector = tuple[float, ...]
type DecimalVector = tuple[Decimal, ...]


class PairRecorder(Protocol):
    """Record attempts and finite returns; readback can supply the saved returns."""

    def check(self) -> float: ...

    def call(self, operation: str, api: str, args: list[Any], invoke: Callable[[], Any],
             validate: Callable[[Any], None] | None = None) -> Any: ...


def _raw(values: object, size: int, label: str) -> FloatVector:
    require(type(values) in (list, tuple) and all(type(x) is float for x in values),
            label + ": expected binary64 words")
    return _binary_vector(values, size, label)


def _exact(values: object, size: int, label: str) -> ExactVector:
    require(type(values) in (list, tuple) and len(values) == size
            and all(type(value) is str for value in values), label + ": exact fraction strings")
    result = tuple(map(Fraction, values))
    require(all(str(x) == value for x, value in zip(result, values, strict=True)), label + ": noncanonical fraction")
    return result


def _hex(values: Sequence[float]) -> list[str]:
    return [value.hex() for value in values]


def _geometry(bundle: dict[str, Any], pair: dict[str, Any], result: dict[str, Any],
              radius_m: float) -> dict[str, ExactVector]:
    row, initial = pair["archive"], bundle["initial"]
    require(row["source_mode"] == "proxy" and row["status"] == "passed", "archived proxy row did not pass")
    t0 = number(initial["epoch_tdb_s"], "initial epoch TDB s")
    s = number(row["elapsed_s"], "elapsed s")
    hi = number(row["hi_tdb_s"], "rounded epoch TDB s")
    lo = number(row["lo_s"], "low epoch s")
    epoch = Fraction(t0) + Fraction(s)
    require(0 <= s <= 300 and epoch == Fraction(hi) + Fraction(lo) == Fraction(row["exact_tdb_s"])
            and _round_exact(epoch).hex() == hi.hex(), "frozen exact coepoch")
    motion = row["motion"]
    r0 = tuple(map(Fraction, _raw(initial["position_m"], 3, "initial position m")))
    v0 = _raw(initial["velocity_m_s"], 3, "initial velocity m/s")
    q = tuple(map(Fraction, _raw(motion["q_m"], 3, "saved q m")))
    w_m_s = _raw(motion["w_m_s"], 3, "saved w m/s")
    drift_m = _raw(motion["drift_m"], 3, "saved drift m")
    rephasing_m = _raw(motion["rephasing_m"], 3, "saved rephasing m")
    direct_velocity = _raw(motion["saved_moon_velocity_m_s"], 3, "saved direct Moon velocity m/s")
    dhat = _saved_product(drift_m, v0, s, "saved drift")
    c = _saved_product(rephasing_m, direct_velocity, lo, "saved rephasing")
    x = tuple(a + Fraction(v) * Fraction(s) + q_i for a, v, q_i in zip(r0, v0, q, strict=True))
    xhat = tuple(a + d + q_i for a, d, q_i in zip(r0, dhat, q, strict=True))
    archived = row["static_force"]
    require(x == _exact(archived["exact_spacecraft_m"], 3, "archived X")
            and xhat == _exact(archived["exact_spacecraft_with_rounded_drift_m"], 3, "archived Xhat"),
            "saved spacecraft motion mismatch")

    ref = row["reference_states_si"]
    p_hi = _exact(ref["hi"]["B"], 6, "saved exact P(hi) state")[:3]
    p_exact = _exact(ref["exact"]["B"], 6, "saved exact P(T) state")[:3]
    increment = _subtract(p_exact, p_hi)
    increment_error = _subtract(c, increment)
    increment_sq = _squares(increment_error)
    require(increment_sq <= INCREMENT_LIMIT_M**2, "rephasing increment norm gate")
    require(increment == _exact(row["time_increment"]["reference_increment_m"], 3, "archived increment")
            and increment_error == _exact(row["time_increment"]["signed_error_m"], 3, "archived increment error")
            and increment_sq == Fraction(row["time_increment"]["error_squared_m2"])
            and row["time_increment"]["passed"] is True, "archived rephasing check mismatch")

    earth = _raw(row["raw_states_km_km_s"]["E"], 6, "saved Earth/SSB state")
    moon = _raw(row["raw_states_km_km_s"]["B"], 6, "saved Moon/SSB state")
    captured = _raw(pair["captured_state_km_km_s"], 6, "captured Moon/Earth state")
    proxy = _raw(row["geocentric_position_km"], 3, "saved geocentric proxy km")
    require(_hex(captured[:3]) != _hex(proxy), "pair has no geocentric position bit miss")
    source_step = tuple(1000 * (Fraction(m) - Fraction(p)) for m, p in zip(captured[:3], proxy, strict=True))
    d0 = _subtract(p_exact, x)
    exact = {"d0": d0}
    rounded = {}
    for arm, g in zip(ARMS, (proxy, captured[:3]), strict=True):
        d2 = tuple(1000 * (Fraction(e) + Fraction(g_i)) + c_i - x_i
                   for e, g_i, c_i, x_i in zip(earth[:3], g, c, xhat, strict=True))
        rounded[arm] = tuple(map(_round_exact, d2))
        exact[arm + "_d2"] = d2
        exact[arm + "_d3"] = tuple(map(Fraction, rounded[arm]))

    require(_subtract(exact["measured_d2"], exact["proxy_d2"]) == source_step, "exact source separation difference")
    require(d0 == _exact(archived["exact_separations_m"]["d0"], 3, "archived d0")
            and exact["proxy_d2"] == _exact(archived["exact_separations_m"]["d2"], 3, "archived d2")
            and exact["proxy_d3"] == _exact(archived["exact_separations_m"]["d3"], 3, "archived d3")
            and _hex(rounded["proxy"]) == _hex(_raw(archived["rounded_separation_m"], 3, "archived rounded d3")),
            "proxy separation replay mismatch")
    rho_m = {arm: hypot(*values) for arm, values in rounded.items()}
    require(all(_squares(values) > Fraction(radius_m)**2 for values in exact.values())
            and all(isfinite(rho) and rho > radius_m for rho in rho_m.values()),
            "strictly exterior lunar geometry required")

    result.update(
        profile=row["profile"], kind=row["kind"], index=row["index"],
        elapsed_s=s, hi_tdb_s=hi, lo_s=lo, exact_tdb_s=epoch,
        signed_source_step_m=source_step, proxy_position_km_hex=_hex(proxy),
        captured_moon_earth_state_km_km_s=captured, earth_ssb_state_km_km_s=earth,
        moon_ssb_state_km_km_s=moon, exact_spacecraft_m=x, exact_spacecraft_with_rounded_drift_m=xhat,
        motion={"q_m": q, "w_m_s": w_m_s, "drift_m": drift_m,
                "rephasing_m": rephasing_m, "saved_moon_velocity_m_s": direct_velocity},
        signed_increment_error_m=increment_error, increment_error_squared_m2=increment_sq,
        exact_separations_m=exact, rounded_separations_m=rounded,
        rounded_separation_hex={arm: _hex(values) for arm, values in rounded.items()}, rho_m=rho_m,
    )
    return exact


def _references(ordinal: int, exact: dict[str, ExactVector], gm: float,
                recorder: PairRecorder, result: dict[str, Any]) -> dict[str, dict[str, DecimalVector]]:
    fields: dict[str, dict[str, DecimalVector]] = {}
    result["reference_m_s2"] = fields
    for precision in PRECISIONS:
        refs: dict[str, DecimalVector] = {}
        fields[str(precision)] = refs
        for name, separation in exact.items():
            refs[name] = recorder.call(
                "decimal_field", "moon_point_mass", [ordinal, name, precision, separation, gm],
                lambda: _decimal_field(separation, Fraction(gm), precision),
                lambda raw: _decimal_vector(raw, "Decimal Moon field"),
            )
    return fields


def _attribution(references: dict[str, DecimalVector], candidates: dict[str, DecimalVector],
                 exact_delta: ExactVector) -> dict[str, Any]:
    fp2, fm2 = references["proxy_d2"], references["measured_d2"]
    fp3, fm3 = references["proxy_d3"], references["measured_d3"]
    p, m = candidates["proxy"], candidates["measured"]
    source = _subtract(fm2, fp2)
    rounding = _subtract(_subtract(fm3, fm2), _subtract(fp3, fp2))
    evaluation = _subtract(_subtract(m, fm3), _subtract(p, fp3))
    residual = _subtract(tuple(map(sum, zip(source, rounding, evaluation, strict=True))),
                         tuple(map(_decimal, exact_delta)))
    error = _norm(residual)
    limit = RELATIVE * sum(map(_norm, (fp2, fm2, fp3, fm3, p, m)))
    return {"signed_source_m_s2": source, "signed_rounding_m_s2": rounding,
            "signed_evaluation_m_s2": evaluation, "signed_residual_m_s2": residual,
            "residual_norm_m_s2": error, "limit_m_s2": limit, "passed": error <= limit}


def _compare(pair: dict[str, Any], result: dict[str, Any],
             fields: dict[str, dict[str, DecimalVector]], binary: dict[str, FloatVector]) -> None:
    archived = pair["archive"]["static_force"]
    exact_a = {arm: tuple(map(Fraction, a)) for arm, a in binary.items()}
    delta = _subtract(exact_a["measured"], exact_a["proxy"])
    same_d3 = result["rounded_separation_hex"]["measured"] == result["rounded_separation_hex"]["proxy"]
    same_a = _hex(binary["measured"]) == _hex(binary["proxy"])
    require(not same_d3 or same_a, "same separation must yield identical acceleration bits")
    gates, attributions = {}, {}
    result.update(gates=gates, attribution=attributions,
                  signed_delta_acceleration_m_s2=delta, same_rounded_separation_bits=same_d3,
                  same_acceleration_bits=same_a, same_acceleration_values=not any(delta),
                  source_step_masked_by_rounding=any(result["signed_source_step_m"]) and same_d3)
    for precision in PRECISIONS:
        key = str(precision)
        references = fields[key]
        with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN)):
            candidates = {arm: tuple(map(_decimal, vector)) for arm, vector in exact_a.items()}
            by_arm = {}
            for arm, candidate in candidates.items():
                by_gate = {}
                for name, ref in (("returned_geometry", references[arm + "_d3"]), ("overall", references["d0"])):
                    gate = _gate(candidate, ref, _norm(ref))
                    gate["signed_margin_m_s2"] = gate["envelope_m_s2"] - gate["error_norm_m_s2"]
                    by_gate[name] = gate
                by_arm[arm] = by_gate
            gates[key] = by_arm
            for name in by_arm["proxy"]:
                require(by_arm["proxy"][name]["passed"] is archived["gates"][key][name]["passed"] is True,
                        f"proxy {name} gate replay mismatch at {precision} digits")
            attributions[key] = _attribution(references, candidates, delta)

    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        convergence = {name: _relative_check(fields["80"][name], ref) for name, ref in fields["100"].items()}
        for key in fields:
            for archived_name, name in (("d0", "d0"), ("d3", "proxy_d3")):
                stored = archived["reference_m_s2"][key][archived_name]
                require(type(stored) is list and all(type(x) is str for x in stored),
                        "proxy archived Decimal field words")
                saved = _decimal_vector(tuple(map(Decimal, stored)), "proxy archived Decimal field")
                require(_relative_check(fields[key][name], saved)["passed"],
                        f"proxy reference {archived_name} replay mismatch at {key} digits")
        result["delta_acceleration_norm_m_s2"] = _norm(tuple(map(_decimal, delta)))

    names = tuple(gates["100"]["proxy"])
    stable = all(gates["80"][arm][name]["passed"] == gates["100"][arm][name]["passed"]
                 for arm in ARMS for name in names)
    attribution_passed = all(entry["passed"] for entry in attributions.values())
    precision_passed = stable and all(check["passed"] for check in convergence.values())
    result.update(precision={"references": convergence, "classifications_stable": stable, "passed": precision_passed},
                  attribution_passed=attribution_passed,
                  gate_flips={key: {name: arms["proxy"][name]["passed"] != arms["measured"][name]["passed"]
                                    for name in names} for key, arms in gates.items()})
    if not (precision_passed and attribution_passed):
        result["outcome"] = "unresolved"
    elif all(gates[key]["measured"][name]["passed"] for key in gates for name in names):
        result["outcome"] = "confirmed"
    else:
        result["outcome"] = "negative"


def _pair(bundle: dict[str, Any], pair: dict[str, Any], result: dict[str, Any],
          gm: float, radius_m: float, recorder: PairRecorder) -> None:
    exact = _geometry(bundle, pair, result, radius_m)
    ordinal = result["observation_ordinal"]
    binary: dict[str, FloatVector] = {}
    result["binary64_m_s2"] = binary
    for arm in ARMS:
        rounded, rho = result["rounded_separations_m"][arm], result["rho_m"][arm]
        binary[arm] = recorder.call(
            "binary64_field", "moon_point_mass", [ordinal, arm, rounded, gm, rho],
            lambda: _binary64_field(rounded, gm, rho),
            lambda raw: _raw(raw, 3, "binary64 Moon field"),
        )
        if arm == "proxy":
            saved = _raw(pair["archive"]["static_force"]["binary64_m_s2"], 3, "saved proxy acceleration")
            require(_hex(binary[arm]) == _hex(saved), "proxy acceleration bit replay mismatch")
    result["acceleration_hex"] = {arm: _hex(vector) for arm, vector in binary.items()}
    fields = _references(ordinal, exact, gm, recorder, result)
    _compare(pair, result, fields, binary)


def analyze(bundle: dict[str, Any], report: dict[str, Any], recorder: PairRecorder) -> None:
    """Run each fixed pair or read back its supplied fields in the same order."""
    rows: list[dict[str, Any]] = []
    report.update(status="pending", outcome="pending", rows=rows, unavailable=list(ORDINALS))
    ordinal: int | None = None
    evidence: dict[str, Any] | None = None
    stage = "inputs"
    try:
        gm = number(bundle["gm_m3_s2"], "Moon GM m^3/s^2")
        radius = number(bundle["radius_m"], "Moon radius m")
        require(gm > 0 and radius > 0, "positive Moon GM and radius required")
        inputs = bundle["rows"]
        require(type(inputs) is list and len(inputs) == len(ORDINALS), "expected all 11 fixed pairs")
        for ordinal, pair in zip(ORDINALS, inputs, strict=True):
            stage = "admission"
            evidence = None
            require(type(pair["archive"]["observation_ordinal"]) is int
                    and pair["archive"]["observation_ordinal"] == ordinal, "frozen pair order")
            recorder.call("observation", "admit_frozen_pair", [ordinal], lambda: ordinal)
            stage = "pair"
            evidence = {"observation_ordinal": ordinal, "outcome": "pending"}
            rows.append(evidence)
            _pair(bundle, pair, evidence, gm, radius, recorder)
            recorder.check()
            report["unavailable"].pop(0)
            if evidence["outcome"] != "confirmed":
                if evidence["outcome"] == "negative":
                    failed = [name for name, gate in evidence["gates"]["100"]["measured"].items()
                              if not gate["passed"]]
                    message = "measured force gate failed: " + ", ".join(failed)
                else:
                    message = "force precision or attribution unresolved"
                report.setdefault("error", {"stage": stage, "observation_ordinal": ordinal,
                                            "type": "NumericalCheck", "message": message})
        outcomes = {row["outcome"] for row in rows}
        outcome = next((state for state in ("unresolved", "negative") if state in outcomes), "confirmed")
        report.update(status="passed" if outcome == "confirmed" else "failed", outcome=outcome)
    except FAILURES as exc:
        if evidence is not None:
            evidence["outcome"] = "incomplete"
        stopped = {"stage": stage, "observation_ordinal": ordinal, "type": type(exc).__name__, "message": str(exc)}
        report.update(status="failed", outcome="incomplete", stopped=stopped)
        report.setdefault("error", stopped)
        raise
