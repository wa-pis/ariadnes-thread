"""ADR0166 offline arithmetic on already verified, same-epoch state returns."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from math import hypot, inf, isfinite, nextafter
import struct
from typing import Any

from ariadna_split_common import Recorder, number, require

_PRECISIONS = (80, 100)
_RELATIVE_PRECISION = Decimal("1e-60")
_GEOMETRIES = ("d0", "d1", "d2", "d3")
_STATE_LABELS = ("E", "G", "B")
_POS_PARITY_M = Fraction(1, 1_000)
_VEL_PARITY_M_S = Fraction(1, 1_000_000)


def _bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _ulp_offset(actual: float, expected: float) -> int:
    def rank(value: float) -> int:
        bits = _bits(value)
        sign = 1 << 63
        return (sign - 1) - (bits ^ sign) if bits & sign else sign + bits
    return rank(actual) - rank(expected)


def _binary_vector(values: object, size: int, field: str) -> tuple[float, ...]:
    require(type(values) in (list, tuple) and len(values) == size, field + " dimensions")
    return tuple(number(x, field) for x in values)


def _exact_vector(values: object, size: int, field: str) -> tuple[Fraction, ...]:
    require(type(values) in (list, tuple) and len(values) == size
            and all(type(x) is Fraction for x in values), field + " exact vector")
    return tuple(values)


def _round_exact(exact: Fraction) -> float:
    """Check the one binary64 round against its neighbours, including ties."""
    rounded = float(exact)
    require(isfinite(rounded), "nonfinite nearest-even result")
    if not exact:
        require(_bits(rounded) == 0, "exact zero must round to +0")
    if not rounded and exact:
        require((_bits(rounded) >> 63) == (exact < 0), "underflow zero sign")
    error = abs(Fraction(rounded) - exact)
    for neighbour in (nextafter(rounded, -inf), nextafter(rounded, inf)):
        if isfinite(neighbour):
            distance = abs(Fraction(neighbour) - exact)
            require(error < distance or (error == distance and _bits(rounded) % 2 == 0),
                    "not nearest-even binary64")
    return rounded


def _subtract[T: (Fraction, Decimal)](left: Sequence[T], right: Sequence[T]) -> tuple[T, ...]:
    return tuple(a - b for a, b in zip(left, right, strict=True))


def _squares(vector: Sequence[Fraction]) -> Fraction:
    return sum((x * x for x in vector), Fraction())


def _decimal(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


def _norm(vector: Sequence[Decimal]) -> Decimal:
    return sum((x * x for x in vector), Decimal()).sqrt()


def _decimal_field(separation_m: Sequence[Fraction], gm_m3_s2: Fraction, precision: int) -> tuple[Decimal, ...]:
    with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN)):
        separation = tuple(_decimal(x) for x in separation_m)
        square = sum((x * x for x in separation), Decimal())
        denominator = square * square.sqrt()
        gm = _decimal(gm_m3_s2)
        return tuple(gm * x / denominator for x in separation)


def _binary64_field(separation_m: Sequence[float], gm_m3_s2: float, rho_m: float) -> tuple[float, ...]:
    return tuple(gm_m3_s2 * (x / rho_m) / (rho_m * rho_m) for x in separation_m)


def _decimal_vector(values: object, field: str) -> tuple[Decimal, ...]:
    require(type(values) in (list, tuple) and len(values) == 3
            and all(type(x) is Decimal and x.is_finite() for x in values), field + " finite Decimal vector")
    return tuple(values)


def _gate(candidate_m_s2: Sequence[Decimal], reference_m_s2: Sequence[Decimal],
          reference_norm_m_s2: Decimal) -> dict[str, Decimal | bool]:
    error = _norm(_subtract(candidate_m_s2, reference_m_s2))
    limit = max(Decimal("1e-15"), Decimal("1e-11") * reference_norm_m_s2)
    return {"error_norm_m_s2": error, "envelope_m_s2": limit, "passed": error <= limit}


def _note_failure(report: dict[str, Any], stage: str, detail: str) -> None:
    report["status"] = "failed"
    report.setdefault("error", {"stage": stage, "type": "NumericalCheck", "message": detail})


def _state_checks(sample: dict[str, Any], raw: dict[str, tuple[float, ...]],
                  exact_si: dict[str, tuple[Fraction, ...]], result: dict[str, Any]) -> bool:
    result["states"] = checked = {}
    for label in _STATE_LABELS:
        components = raw[label]
        reference = exact_si[label]
        errors = _subtract(tuple(1000 * Fraction(x) for x in components), reference)
        position_sq, velocity_sq = _squares(errors[:3]), _squares(errors[3:])
        expected_raw = tuple(_round_exact(x / 1000) for x in reference)
        row: dict[str, Any] = {
            "signed_position_error_m": errors[:3],
            "signed_velocity_error_m_s": errors[3:],
            "position_error_squared_m2": position_sq,
            "velocity_error_squared_m2_s2": velocity_sq,
            "position_parity_passed": position_sq <= _POS_PARITY_M**2,
            "velocity_parity_passed": velocity_sq <= _VEL_PARITY_M_S**2,
            "nearest_reference_raw_ulp_offsets": [_ulp_offset(x, y) for x, y in zip(components, expected_raw, strict=True)],
        }
        if label != "G":
            historical_body = "Earth" if label == "E" else "Moon"
            saved_hex = sample["raw_hex"][historical_body]
            require(type(saved_hex) is list and len(saved_hex) == 6, "archived raw state dimensions")
            same_bits = [x.hex() == hx for x, hx in zip(components, saved_hex, strict=True)]
            row["historical_bit_matches"] = same_bits
            row["historical_reproduction_passed"] = all(same_bits)
        checked[label] = row
    return all(row["position_parity_passed"] and row["velocity_parity_passed"]
               and row.get("historical_reproduction_passed", True) for row in checked.values())


def _closure(raw: dict[str, tuple[float, ...]], exact_si: dict[str, tuple[Fraction, ...]],
             reference: dict[str, Any], row: dict[str, Any]) -> tuple[Fraction, ...]:
    raw_exact = {label: tuple(Fraction(x) for x in raw[label]) for label in _STATE_LABELS}
    summed = tuple(e + g for e, g in zip(raw_exact["E"], raw_exact["G"], strict=True))
    rounded = tuple(_round_exact(x) for x in summed)
    matches = [x.hex() == y.hex() for x, y in zip(rounded, raw["B"], strict=True)]
    residual = _subtract(raw_exact["B"], summed)
    terms_m = {
        "earth_leg": _subtract(tuple(1000 * x for x in raw_exact["E"][:3]), exact_si["E"][:3]),
        "moon_leg": _subtract(tuple(1000 * x for x in raw_exact["G"][:3]), exact_si["G"][:3]),
        "barycentric_raw_rounding": tuple(1000 * x for x in residual[:3]),
        "historical_si_rounding": _subtract(
            tuple(Fraction(x) for x in _binary_vector(reference["saved_moon_m"], 3, "saved Moon SI position")),
            tuple(1000 * x for x in raw_exact["B"][:3])),
    }
    saved_m = _exact_vector(reference["saved_moon_source_residual_m"], 3, "saved direct source residual")
    telescope = tuple(map(sum, zip(*terms_m.values(), strict=True)))
    row["closure"] = {
        "position_matches": matches[:3], "position_passed": all(matches[:3]),
        "velocity_diagnostic_matches": matches[3:],
        "b_minus_legs_position_km": residual[:3], "b_minus_legs_velocity_km_s": residual[3:],
        "direct_position_raw_ulp_offsets": [_ulp_offset(b, r) for b, r in zip(raw["B"][:3], rounded[:3], strict=True)],
        "signed_source_terms_m": terms_m, "total_source_residual_m": telescope,
        "saved_direct_source_residual_m": saved_m, "source_telescope_passed": telescope == saved_m,
    }
    require(telescope == saved_m, "exact signed source telescope differs from archived residual")
    return tuple(1000 * x for x in summed[:3])


def _geometry(bundle: dict[str, Any], sample: dict[str, Any], reference: dict[str, Any],
              split_moon_m: Sequence[Fraction], result: dict[str, Any]) -> tuple[dict[str, tuple[Fraction, ...]], tuple[float, ...], float]:
    initial = bundle["frozen_initial"]
    r0_m = tuple(Fraction(x) for x in _binary_vector(initial["position_m"], 3, "initial position"))
    v0_m_s = _binary_vector(initial["velocity_m_s"], 3, "initial velocity")
    elapsed_s = number(sample["elapsed_s"], "sample elapsed_s")
    exact_drift_m = tuple(Fraction(v) * Fraction(elapsed_s) for v in v0_m_s)
    frozen_drift_m = _binary_vector(sample["frozen_drift_m"], 3, "saved drift")
    require(tuple(d.hex() for d in frozen_drift_m) == tuple((v * elapsed_s).hex() for v in v0_m_s),
            "frozen drift differs from RN(v0*s)")
    q_m = tuple(Fraction(x) for x in _binary_vector(sample["frozen_q_m"], 3, "saved q"))
    x_m = tuple(r + d + q for r, d, q in zip(r0_m, exact_drift_m, q_m, strict=True))
    xhat_m = tuple(r + Fraction(d) + q for r, d, q in zip(r0_m, frozen_drift_m, q_m, strict=True))
    moon_si = _exact_vector(reference["moon_state_si"], 6, "exact Moon state")
    d0_m = _subtract(moon_si[:3], x_m)
    require(d0_m == _exact_vector(reference["d0_m"], 3, "archived Moon d0"), "archived Moon d0 geometry mismatch")
    d1_m, d2_m = _subtract(split_moon_m, x_m), _subtract(split_moon_m, xhat_m)
    rounded_m = tuple(_round_exact(x) for x in d2_m)
    d3_m = tuple(Fraction(x) for x in rounded_m)
    geometries = dict(zip(_GEOMETRIES, (d0_m, d1_m, d2_m, d3_m), strict=True))
    radius_m = number(bundle["moon_radius_m"], "Moon radius")
    require(radius_m > 0, "Moon radius must be positive")
    radius_sq_m2 = Fraction(radius_m) ** 2
    domains = {name: _squares(d) > radius_sq_m2 for name, d in geometries.items()}
    rho_m = hypot(*rounded_m)
    result.update(
        exact_spacecraft_m=x_m, exact_spacecraft_with_rounded_drift_m=xhat_m,
        exact_separations_m=geometries, rounded_separation_m=rounded_m,
        exact_separation_deltas_m={"source": _subtract(d1_m, d0_m),
                                  "drift": _subtract(d2_m, d1_m),
                                  "assembly": _subtract(d3_m, d2_m)},
        rho_m=rho_m if isfinite(rho_m) else None,
        exact_exterior=domains, binary64_exterior=isfinite(rho_m) and rho_m > radius_m,
    )
    require(all(domains.values()) and result["binary64_exterior"], "strictly exterior lunar geometry required")
    return geometries, rounded_m, rho_m


def _static_force(bundle: dict[str, Any], sample: dict[str, Any], reference: dict[str, Any],
                  split_moon_m: Sequence[Fraction], result: dict[str, Any], recorder: Recorder) -> bool:
    geometries, rounded_m, rho_m = _geometry(bundle, sample, reference, split_moon_m, result)
    gm_m3_s2 = number(bundle["moon_gm_m3_s2"], "Moon GM")
    require(gm_m3_s2 > 0, "Moon GM must be positive")
    fields, norms = {}, {}
    for p in _PRECISIONS:
        a0 = _decimal_vector(reference["a0"][p], "archived Moon d0 field")
        a0_norm = reference["a0_norm"][p]
        require(type(a0_norm) is Decimal and a0_norm.is_finite() and a0_norm > 0, "archived Moon d0 norm")
        with localcontext(Context(prec=p, rounding=ROUND_HALF_EVEN)):
            require(abs(_norm(a0) - a0_norm) <= _RELATIVE_PRECISION * a0_norm,
                    "archived Moon d0 norm does not match its saved field")
        fields[p], norms[p] = {"d0": a0}, {"d0": a0_norm}
    ordinal = sample["observation_ordinal"]
    binary64 = recorder.call(
        "binary64_field", "moon_point_mass", [ordinal, "d3", rounded_m, gm_m3_s2, rho_m],
        lambda: _binary64_field(rounded_m, gm_m3_s2, rho_m),
        lambda x: _binary_vector(x, 3, "binary64 Moon field"),
    )
    result.update(binary64_m_s2=binary64, reference_m_s2={str(p): f for p, f in fields.items()},
                  reference_norms_m_s2={str(p): n for p, n in norms.items()},
                  gates={}, signed_field_contributions_m_s2={}, telescope={})
    for p in _PRECISIONS:
        with localcontext(Context(prec=p, rounding=ROUND_HALF_EVEN)):
            for name in _GEOMETRIES[1:]:
                d = geometries[name]
                field = recorder.call(
                    "decimal_field", "moon_point_mass", [ordinal, name, p, d, gm_m3_s2],
                    lambda: _decimal_field(d, Fraction(gm_m3_s2), p),
                    lambda x: _decimal_vector(x, "Decimal Moon field"),
                )
                fields[p][name] = field
                norms[p][name] = _norm(field)
            f = fields[p]
            candidate = tuple(_decimal(Fraction(x)) for x in binary64)
            result["gates"][str(p)] = {
                "returned_geometry": _gate(candidate, f["d3"], norms[p]["d3"]),
                "overall": _gate(candidate, f["d0"], norms[p]["d0"]),
            }
            increments = tuple(_subtract(a, f[name]) for a, name in zip(
                (f["d1"], f["d2"], f["d3"], candidate), _GEOMETRIES, strict=True))
            result["signed_field_contributions_m_s2"][str(p)] = dict(zip(
                ("source", "drift", "assembly", "evaluation"), increments, strict=True))
            residual = _subtract(tuple(sum(column, Decimal()) for column in zip(*increments, strict=True)),
                                 _subtract(candidate, f["d0"]))
            error_norm = _norm(residual)
            limit = _RELATIVE_PRECISION * sum(norms[p].values(), Decimal())
            result["telescope"][str(p)] = {"residual_m_s2": residual, "error_norm_m_s2": error_norm,
                                      "limit_m_s2": limit, "passed": error_norm <= limit}
    precision = {}
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        for name in _GEOMETRIES:
            low, high = fields[80][name], fields[100][name]
            difference = _norm(_subtract(low, high))
            limit = _RELATIVE_PRECISION * norms[100][name]
            zero_agreement = all((x == 0) == (y == 0) for x, y in zip(low, high, strict=True))
            precision[name] = {"difference_norm_m_s2": difference, "limit_m_s2": limit,
                               "zero_agreement": zero_agreement, "passed": zero_agreement and difference <= limit}
    gates = result["gates"]
    stable = all(gates["80"][name]["passed"] == gates["100"][name]["passed"] for name in gates["100"])
    result["precision"] = {"references": precision, "classifications_stable": stable,
                           "passed": stable and all(item["passed"] for item in precision.values())}
    result["passed"] = (result["precision"]["passed"]
                        and all(item["passed"] for item in result["telescope"].values())
                        and all(gate["passed"] for by_precision in gates.values() for gate in by_precision.values()))
    return result["passed"]


def analyze(bundle: dict[str, Any], states: list[dict[str, list[float]]],
            report: dict[str, Any], recorder: Recorder) -> None:
    """Verify archived reproduction, source closure and static force independently."""
    report.update(status="pending", numerical_passed=False, rows=[], state_prerequisites_passed=None,
                  position_closure_passed=None, static_force_passed=None,
                  unavailable=["state_prerequisites", "position_closure", "static_force"])
    samples = bundle["samples_in_probe_order"]
    references = bundle["references"]
    require(len(samples) == len(references) == len(states) == 3, "exactly three frozen observations")
    prepared = []
    for sample, values, reference in zip(samples, states, references, strict=True):
        recorder.check()
        ordinal = sample["observation_ordinal"]
        row: dict[str, Any] = {"observation_ordinal": ordinal, "static_force": None}
        report["rows"].append(row)
        hi = number(sample["hi_tdb_s"], "sample hi")
        elapsed_s = number(sample["elapsed_s"], "sample elapsed_s")
        t0 = number(bundle["frozen_initial"]["epoch_tdb_s"], "initial epoch")
        require(hi.hex() == sample["hi_hex"] and sample["lo_hex"] == "0x0.0p+0"
                and Fraction(hi) == Fraction(t0) + Fraction(elapsed_s), "exact frozen coepoch required")
        row.update(hi_tdb_s=hi, elapsed_s=elapsed_s)
        require(set(values) == set(_STATE_LABELS), "expected E/G/B states")
        raw = {label: _binary_vector(values[label], 6, label + " raw state") for label in _STATE_LABELS}
        earth_si = _exact_vector(reference["earth_state_si"], 6, "exact Earth state")
        moon_si = _exact_vector(reference["moon_state_si"], 6, "exact Moon state")
        exact_si = {"E": earth_si, "G": _subtract(moon_si, earth_si), "B": moon_si}
        row["state_prerequisites_passed"] = _state_checks(sample, raw, exact_si, row)
        if not row["state_prerequisites_passed"]:
            _note_failure(report, "state_prerequisites", f"observation {ordinal}: archive reproduction or state parity")
        prepared.append((sample, reference, row, raw, exact_si))
    report["unavailable"].remove("state_prerequisites")
    report["state_prerequisites_passed"] = all(row["state_prerequisites_passed"] for row in report["rows"])
    split_rows = []
    for sample, reference, row, raw, exact_si in prepared:
        recorder.check()
        split_moon_m = _closure(raw, exact_si, reference, row)
        if not row["closure"]["position_passed"]:
            _note_failure(report, "position_closure", f"observation {row['observation_ordinal']}: raw position closure")
        split_rows.append((sample, reference, row, split_moon_m))
    report["position_closure_matches"] = sum(sum(row["closure"]["position_matches"]) for row in report["rows"])
    report["position_closure_passed"] = report["position_closure_matches"] == 9
    report["unavailable"].remove("position_closure")
    if not report["state_prerequisites_passed"]:
        return
    for sample, reference, row, split_moon_m in split_rows:
        recorder.check()
        baseline = sample["retained_moon_overall_gate_passed"]
        require(type(baseline) is bool, "archived direct classification must be boolean")
        row["static_force"] = {"archived_direct_overall_passed": baseline, "passed": None}
        if not _static_force(bundle, sample, reference, split_moon_m, row["static_force"], recorder):
            _note_failure(report, "static_force", f"observation {row['observation_ordinal']}: static Moon force gates")
    recorder.check()
    report["static_force_passed"] = all(row["static_force"]["passed"] for row in report["rows"])
    report["unavailable"].remove("static_force")
    report["numerical_passed"] = report["position_closure_passed"] and report["static_force_passed"]
    report["status"] = "passed" if report["numerical_passed"] else "failed"
