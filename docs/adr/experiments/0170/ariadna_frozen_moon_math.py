"""R5.23 offline split-source arithmetic on prevalidated frozen operands."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from math import copysign, hypot, isfinite
from typing import Any

from ariadna_split_analysis import (
    _binary64_field,
    _binary_vector,
    _bits,
    _decimal,
    _decimal_field,
    _decimal_vector,
    _gate,
    _norm,
    _round_exact,
    _squares,
    _subtract,
)
from ariadna_split_common import FAILURES, Recorder, number, require

_GEOMETRIES = ("d0", "d1", "d2", "d3")
_PRECISIONS = (80, 100)
_RELATIVE = Decimal("1e-60")
_POS_PARITY_M = Fraction(1, 1000)
_VEL_PARITY_M_S = Fraction(1, 1_000_000)
_INCREMENT_M = Fraction(1, 10**12)
_ORDER = tuple((profile, kind, index) for profile in ("normal", "tighter")
               for kind in ("output", "rhs") for index in range(7))
_CONTROLS = {("normal", "rhs", 6), ("normal", "output", 0), ("normal", "output", 5)}
_MODES = ("measured", "proxy")


def _add(left: Sequence[Fraction], right: Sequence[Fraction]) -> tuple[Fraction, ...]:
    return tuple(x + y for x, y in zip(left, right, strict=True))


def _exact_record(words: Sequence[float], epoch: Fraction) -> tuple[Fraction, ...]:
    """Evaluate a degree-12 Type 2 record, including the chain rule for velocity."""
    midpoint, radius, *coefficients = map(Fraction, _binary_vector(words, 41, "Type 2 record"))
    require(radius > 0 and midpoint - radius <= epoch < midpoint + radius,
            "reference epoch outside half-open Type 2 record")
    x = (epoch - midpoint) / radius
    values, derivatives = [Fraction(1), x], [Fraction(0), Fraction(1)]
    for _ in range(2, 13):
        values.append(2 * x * values[-1] - values[-2])
        derivatives.append(2 * values[-2] + 2 * x * derivatives[-1] - derivatives[-2])
    blocks = [coefficients[i:i + 13] for i in range(0, 39, 13)]
    positions = tuple(1000 * sum(c * t for c, t in zip(block, values, strict=True)) for block in blocks)
    velocities = tuple(1000 * sum(c * t for c, t in zip(block, derivatives, strict=True)) / radius
                       for block in blocks)
    return positions + velocities


def _reference(epoch: Fraction, records: dict[str, list[float]],
               cache: dict[Fraction, dict[str, tuple[Fraction, ...]]],
               recorder: Recorder) -> dict[str, tuple[Fraction, ...]]:
    if epoch not in cache:
        recorder.call("reference_epoch", "admit_exact_epoch", [epoch], lambda: epoch)
        values = {}
        for label in ("E", "G"):
            words = records[label]
            values[label] = recorder.call("record", "exact_type2_state_si", [label, epoch, words],
                                          lambda: _exact_record(words, epoch))
        values["B"] = _add(values["E"], values["G"])
        cache[epoch] = values
    return cache[epoch]


def _rounded_product(left: float, right: float) -> float:
    exact = Fraction(left) * Fraction(right)
    if exact:
        return _round_exact(exact)
    negative = (_bits(left) ^ _bits(right)) >> 63
    return copysign(0.0, -1.0 if negative else 1.0)


def _saved_product(saved: object, operands: Sequence[float], factor: float, name: str) -> tuple[Fraction, ...]:
    values = _binary_vector(saved, 3, name)
    require(all(_bits(value) == _bits(_rounded_product(operand, factor))
                for value, operand in zip(values, operands, strict=True)),
            name + ": signed binary64 product mismatch")
    return tuple(map(Fraction, values))


def _parity(raw: Sequence[float], reference: Sequence[Fraction]) -> dict[str, Any]:
    errors = _subtract(tuple(1000 * Fraction(x) for x in raw), reference)
    position, velocity = _squares(errors[:3]), _squares(errors[3:])
    return {
        "signed_position_error_m": errors[:3], "signed_velocity_error_m_s": errors[3:],
        "position_error_squared_m2": position, "velocity_error_squared_m2_s2": velocity,
        "position_passed": position <= _POS_PARITY_M**2, "velocity_passed": velocity <= _VEL_PARITY_M_S**2,
    }


def _source(row: dict[str, Any], reference: dict[str, tuple[Fraction, ...]],
            result: dict[str, Any]) -> tuple[tuple[Fraction, ...], bool]:
    mode = row["source_mode"]
    labels = ("E", "G", "B") if mode == "measured" else ("E", "B")
    require(set(row["states"]) == set(labels), "archived state labels do not match source mode")
    raw = {name: _binary_vector(row["states"][name], 6, name + " raw state") for name in labels}
    parity = {label: _parity(raw[label], reference[label]) for label in labels}
    g_position = (raw["G"][:3] if mode == "measured"
                  else tuple(_round_exact(x / 1000) for x in reference["G"][:3]))
    summed_km = _add(tuple(map(Fraction, raw["E"][:3])), tuple(map(Fraction, g_position)))
    rounded_km = tuple(_round_exact(x) for x in summed_km)
    matches = [_bits(x) == _bits(b) for x, b in zip(rounded_km, raw["B"][:3], strict=True)]
    result.update(raw_states_km_km_s=raw, state_parity=parity,
                  geocentric_position_km=g_position,
                  closure={"position_matches": matches, "position_passed": all(matches),
                           "b_minus_legs_position_km": _subtract(
                               tuple(map(Fraction, raw["B"][:3])), summed_km)})
    split_m = tuple(1000 * x for x in summed_km)
    result["signed_source_position_errors_m"] = {
        "earth_leg": _subtract(tuple(1000 * Fraction(x) for x in raw["E"][:3]), reference["E"][:3]),
        "moon_leg": _subtract(tuple(1000 * Fraction(x) for x in g_position), reference["G"][:3]),
        "split_sum": _subtract(split_m, reference["B"][:3]),
    }
    require(_add(result["signed_source_position_errors_m"]["earth_leg"],
                 result["signed_source_position_errors_m"]["moon_leg"])
            == result["signed_source_position_errors_m"]["split_sum"], "exact source telescope mismatch")
    return split_m, all(state["position_passed"] and state["velocity_passed"] for state in parity.values())


def _motion(row: dict[str, Any], initial: dict[str, Any], elapsed: float, lo: float,
            hi_moon: Sequence[Fraction], moon: Sequence[Fraction], result: dict[str, Any]
            ) -> tuple[tuple[Fraction, ...], tuple[Fraction, ...], tuple[Fraction, ...], bool]:
    motion = row["motion"]
    require(_bits(number(motion["elapsed_s"], "motion elapsed")) == _bits(elapsed), "motion elapsed mismatch")
    r0 = tuple(map(Fraction, _binary_vector(initial["position_m"], 3, "initial position")))
    v0 = _binary_vector(initial["velocity_m_s"], 3, "initial velocity")
    v_b = _binary_vector(row["states_si"]["B"], 6, "saved Moon SI state")[3:]
    q = tuple(map(Fraction, _binary_vector(motion["q_m"], 3, "saved q")))
    w = _binary_vector(motion["w_m_s"], 3, "saved w")
    drift = tuple(Fraction(v) * Fraction(elapsed) for v in v0)
    increment = _subtract(moon[:3], hi_moon[:3])
    c = _saved_product(row["moon_geometry"]["rephasing_m"], v_b, lo, "saved rephasing")
    dhat = _saved_product(motion["drift_m"], v0, elapsed, "saved drift")
    result["motion"] = {"q_m": motion["q_m"], "w_m_s": w, "drift_m": motion["drift_m"],
                        "saved_moon_velocity_m_s": v_b, "rephasing_m": row["moon_geometry"]["rephasing_m"]}
    vf = tuple(Fraction(v) * Fraction(lo) for v in v_b)
    hi_drift = tuple(v * Fraction(lo) for v in hi_moon[3:])
    taylor = _subtract(hi_drift, increment)
    velocity = _subtract(vf, hi_drift)
    rounding = _subtract(c, vf)
    error = _subtract(c, increment)
    require(_add(_add(taylor, velocity), rounding) == error, "exact rephasing telescope mismatch")
    squared = _squares(error)
    passed = squared <= _INCREMENT_M**2
    result["time_increment"] = {
        "reference_increment_m": increment, "taylor_m": taylor, "velocity_source_m": velocity,
        "product_rounding_m": rounding, "signed_error_m": error,
        "error_squared_m2": squared, "limit_m": _INCREMENT_M, "passed": passed,
    }
    x, xhat = _add(_add(r0, drift), q), _add(_add(r0, dhat), q)
    return x, xhat, c, passed


def _geometry(split_m: Sequence[Fraction], hi_moon: Sequence[Fraction], moon: Sequence[Fraction],
              x: Sequence[Fraction], xhat: Sequence[Fraction], c: Sequence[Fraction],
              radius: float, result: dict[str, Any]
              ) -> tuple[dict[str, tuple[Fraction, ...]], tuple[float, ...], float]:
    source = _subtract(split_m, hi_moon[:3])
    d0 = _subtract(moon[:3], x)
    d1 = _add(d0, source)
    d2 = _subtract(_add(split_m, c), xhat)
    rounded = tuple(map(_round_exact, d2))
    d3 = tuple(map(Fraction, rounded))
    drift = _subtract(xhat, x)
    drift_rephasing = _subtract(result["time_increment"]["signed_error_m"], drift)
    assembly = _subtract(d3, d2)
    require(drift_rephasing == _subtract(d2, d1)
            and _add(_add(source, drift_rephasing), assembly) == _subtract(d3, d0),
            "exact separation telescope mismatch")
    geometries = dict(zip(_GEOMETRIES, (d0, d1, d2, d3), strict=True))
    exact_exterior = {key: _squares(values) > Fraction(radius)**2 for key, values in geometries.items()}
    rho = hypot(*rounded)
    binary64_exterior = isfinite(rho) and rho > radius
    result["static_force"] = {"exact_spacecraft_m": x, "exact_spacecraft_with_rounded_drift_m": xhat,
                              "exact_separations_m": geometries, "rounded_separation_m": rounded,
                              "exact_separation_deltas_m": {"source": source, "drift_rephasing": drift_rephasing,
                                                            "drift_rounding": drift, "assembly": assembly},
                              "rho_m": rho, "exact_exterior": exact_exterior,
                              "binary64_exterior": binary64_exterior}
    require(all(exact_exterior.values()) and binary64_exterior, "strictly exterior lunar geometry required")
    return geometries, rounded, rho


def _relative_check(candidate: Sequence[Decimal], reference: Sequence[Decimal]) -> dict[str, Any]:
    difference = _norm(_subtract(candidate, reference))
    limit = _RELATIVE * _norm(reference)
    zero_agreement = all((x == 0) == (y == 0) for x, y in zip(candidate, reference, strict=True))
    return {"difference_norm_m_s2": difference, "limit_m_s2": limit, "zero_agreement": zero_agreement,
            "passed": zero_agreement and difference <= limit}


def _force(ordinal: int, geometries: dict[str, tuple[Fraction, ...]], rounded: tuple[float, ...],
           rho: float, gm: float, result: dict[str, Any], recorder: Recorder) -> bool:
    binary64 = recorder.call(
        "binary64_field", "moon_point_mass", [ordinal, "d3", rounded, gm, rho],
        lambda: _binary64_field(rounded, gm, rho), lambda x: _binary_vector(x, 3, "binary64 Moon field"),
    )
    fields, norms, gates, telescope, contributions = {}, {}, {}, {}, {}
    result.update(binary64_m_s2=binary64, reference_m_s2=fields, reference_norms_m_s2=norms,
                  gates=gates, telescope=telescope, signed_field_contributions_m_s2=contributions)
    for precision in _PRECISIONS:
        key = str(precision)
        f, n = fields[key], norms[key] = {}, {}
        with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN)):
            for name, d in geometries.items():
                field = recorder.call(
                    "decimal_field", "moon_point_mass", [ordinal, name, precision, d, gm],
                    lambda: _decimal_field(d, Fraction(gm), precision),
                    lambda x: _decimal_vector(x, "Decimal Moon field"),
                )
                f[name] = field
                n[name] = _norm(field)
            candidate = tuple(_decimal(Fraction(value)) for value in binary64)
            gates[key] = {"returned_geometry": _gate(candidate, f["d3"], n["d3"]),
                          "overall": _gate(candidate, f["d0"], n["d0"])}
            increments = tuple(_subtract(a, f[name]) for a, name in zip(
                (f["d1"], f["d2"], f["d3"], candidate), _GEOMETRIES, strict=True))
            contributions[key] = dict(zip(("source", "drift_rephasing", "assembly", "evaluation"),
                                          increments, strict=True))
            residual = _subtract(tuple(sum(column, Decimal()) for column in zip(*increments, strict=True)),
                                 _subtract(candidate, f["d0"]))
            error, limit = _norm(residual), _RELATIVE * sum(n.values(), Decimal())
            telescope[key] = {"residual_m_s2": residual, "error_norm_m_s2": error,
                              "limit_m_s2": limit, "passed": error <= limit}
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        convergence = {name: _relative_check(fields["80"][name], fields["100"][name]) for name in _GEOMETRIES}
    stable = all(gates["80"][name]["passed"] == gate["passed"] for name, gate in gates["100"].items())
    precision_passed = stable and all(item["passed"] for item in convergence.values())
    result["precision"] = {"references": convergence, "classifications_stable": stable,
                           "passed": precision_passed}
    result["passed"] = (precision_passed and all(item["passed"] for item in telescope.values())
                        and all(gate["passed"] for by_precision in gates.values() for gate in by_precision.values()))
    return result["passed"]


def _control(saved: dict[str, Any], actual: dict[str, Any], evidence: dict[str, Any]) -> bool:
    saved = saved["static_force"]
    comparisons = {
        "exact_separations": all(actual["exact_separations_m"][name]
                                 == tuple(map(Fraction, saved["exact_separations_m"][name]))
                                 for name in _GEOMETRIES),
        "rounded_separation_bits": tuple(map(_bits, actual["rounded_separation_m"]))
        == tuple(map(_bits, _binary_vector(saved["rounded_separation_m"], 3, "control separation"))),
        "binary64_acceleration_bits": tuple(map(_bits, actual["binary64_m_s2"]))
        == tuple(map(_bits, _binary_vector(saved["binary64_m_s2"], 3, "control acceleration"))),
        "rho_bits": _bits(actual["rho_m"]) == _bits(number(saved["rho_m"], "control rho")),
        "force_verdict": actual["passed"] is saved["passed"],
        "gate_verdicts": all(gate["passed"] is saved["gates"][p][name]["passed"]
                             for p, gates in actual["gates"].items() for name, gate in gates.items()),
    }
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        references = {p: {name: _relative_check(field, _decimal_vector(
            tuple(map(Decimal, saved["reference_m_s2"][p][name])), "control field"))
            for name, field in fields.items()} for p, fields in actual["reference_m_s2"].items()}
    passed = all(comparisons.values()) and all(item["passed"] for fields in references.values()
                                               for item in fields.values())
    evidence["control"] = {"checks": comparisons, "reference_checks": references, "passed": passed}
    return passed


def _failure(report: dict[str, Any], evidence: dict[str, Any] | None, stage: str,
             message: str, kind: str = "NumericalCheck") -> None:
    ordinal = None if evidence is None else evidence["observation_ordinal"]
    error = {"stage": stage, "type": kind, "message": message, "observation_ordinal": ordinal}
    report["status"] = "failed"
    report.setdefault("error", error)
    if evidence is not None:
        evidence["status"] = "failed"
        evidence.setdefault("error", error)


def analyze(bundle: dict[str, Any], report: dict[str, Any], recorder: Recorder) -> None:
    """Keep every valid scheduled row and stop on a violated prerequisite or budget."""
    report.update(status="pending", numerical_passed=False, rows=[], unavailable=[],
                  source_counts={mode: dict.fromkeys(("attempted", "passed", "failed"), 0) for mode in _MODES})
    cache: dict[Fraction, dict[str, tuple[Fraction, ...]]] = {}
    unavailable = report["unavailable"]
    evidence, counts = None, None
    hi_epochs, exact_epochs = set(), set()
    stage = "input"
    try:
        initial = bundle["initial"]
        t0 = number(initial["epoch_tdb_s"], "initial epoch")
        gm = number(bundle["gm_m3_s2"], "Moon GM")
        radius = number(bundle["radius_m"], "Moon radius")
        require(gm > 0 and radius > 0, "positive Moon GM and radius required")
        require(len(bundle["rows"]) == len(_ORDER), "expected exactly 28 observations")
        for ordinal, (row, identity) in enumerate(zip(bundle["rows"], _ORDER, strict=True)):
            stage = "observation"
            evidence, counts = None, None
            evidence = {"observation_ordinal": ordinal, "profile": row["profile"], "kind": row["kind"],
                        "index": row["index"], "source_mode": row["source_mode"], "status": "pending"}
            report["rows"].append(evidence)
            recorder.call("observation", "admit_frozen_observation", [ordinal, identity, row["source_mode"]],
                          lambda: ordinal)
            mode = row["source_mode"]
            require((row["profile"], row["kind"], row["index"]) == identity and mode in _MODES,
                    "unexpected observation identity or source mode")
            require((row["control"] is not None) == (identity in _CONTROLS)
                    and (row["control"] is None or mode == "measured"), "unexpected measured control mapping")
            counts = report["source_counts"][mode]
            counts["attempted"] += 1
            stage = "epoch"
            elapsed = number(row["elapsed_s"], "elapsed time")
            hi = number(row["hi_tdb_s"], "rounded epoch")
            lo = number(row["lo_s"], "low epoch part")
            exact = Fraction(t0) + Fraction(elapsed)
            require(0 <= elapsed <= 300 and exact == Fraction(hi) + Fraction(lo)
                    and _bits(hi) == _bits(_round_exact(exact)), "frozen epoch identity mismatch")
            evidence.update(elapsed_s=elapsed, hi_tdb_s=hi, lo_s=lo, exact_tdb_s=exact,
                            archived_direct={"assessed_by_r5_17": row["profile"] == "normal",
                                             "available": row["archived_direct"] is not None,
                                             "overall": row["archived_direct"]})
            hi_epochs.add(Fraction(hi))
            exact_epochs.add(exact)
            stage = "reference"
            high = _reference(Fraction(hi), bundle["records"], cache, recorder)
            target = _reference(exact, bundle["records"], cache, recorder)
            evidence["reference_states_si"] = {"hi": high, "exact": target}
            stage = "source"
            split, parity = _source(row, high, evidence)
            stage = "motion"
            x, xhat, c, increment = _motion(row, initial, elapsed, lo, high["B"], target["B"], evidence)
            if not parity or not increment:
                if not parity:
                    _failure(report, evidence, "state_parity", "saved state outside parity limits")
                if not increment:
                    _failure(report, evidence, "time_increment", "rephasing outside increment envelope")
                recorder.check()
                counts["failed"] += 1
                counts = None
                unavailable.append({"observation_ordinal": ordinal, "stage": "static_force"})
                continue
            stage = "geometry"
            geometries, rounded, rho = _geometry(split, high["B"], target["B"], x, xhat, c, radius, evidence)
            stage = "force"
            force = _force(ordinal, geometries, rounded, rho, gm, evidence["static_force"], recorder)
            direct = row["archived_direct"]
            if direct is not None:
                evidence["archived_direct"]["split_overall"] = evidence["static_force"]["gates"]["100"]["overall"]
                evidence["archived_direct"]["same_verdict"] = (
                    direct["passed"] is evidence["archived_direct"]["split_overall"]["passed"])
            if not force:
                _failure(report, evidence, "force", "Moon field precision, telescope or gate failed")
            stage = "control"
            if row["control"] is not None and not _control(row["control"], evidence["static_force"], evidence):
                _failure(report, evidence, stage, "archived measured control differs")
            recorder.check()
            if evidence["status"] == "pending":
                evidence["status"] = "passed"
            counts[evidence["status"]] += 1
            counts = None
        stage = "coverage"
        evidence = None
        report["epoch_counts"] = {"rounded": len(hi_epochs), "exact": len(exact_epochs), "union": len(cache)}
        require(report["epoch_counts"] == {"rounded": 19, "exact": 19, "union": 29}
                and [report["source_counts"][mode]["attempted"] for mode in _MODES] == [7, 21],
                "frozen epoch or source cardinality mismatch")
        if report["status"] == "pending":
            report.update(status="passed", numerical_passed=True)
    except FAILURES as error:
        if counts is not None:
            counts["failed"] += 1
        _failure(report, evidence, stage, str(error), type(error).__name__)
        report["epoch_counts"] = {"rounded": len(hi_epochs), "exact": len(exact_epochs), "union": len(cache)}
        if evidence is not None:
            unavailable.append({"observation_ordinal": evidence["observation_ordinal"], "blocked_at": stage})
        unavailable.extend({"observation_ordinal": index, "stage": "observation"}
                           for index in range(len(report["rows"]), len(_ORDER)))
        raise
