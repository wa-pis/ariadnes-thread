"""Independent, native-free fixed-position force reference for ADR0156.

Inputs use SI, TDB seconds from J2000, SSB origin and J2000 orientation. Only
an identity-pinned pure Type2 polynomial helper is reused; force arithmetic is
independent of the binary64 calculator. Importing this module evaluates no field.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


ORACLE_PATH = Path(__file__).with_name("0153-real-ephemeris-oracle.py")
ORACLE_SHA256 = "23915fee1feacca37f4a4c0f794feec177aac777407b9c87cc0f8176b0b4a6c8"
PROFILES = (80, 100)
GEOMETRIES = ("d0", "d1", "d2", "d3")
ARM_NAMES = ("compensated", "uncorrected", "wrong_sign")
CONTRIBUTIONS = ("native_source", "residual_rephasing", "relative_assembly", "field_evaluation")
CHAINS = {"Sun": ((10, 0),), "Earth": ((399, 0),), "Moon": ((301, 399), (399, 0))}
MODELS = {"A": ("Sun", "Moon"), "B": ("Sun", "Moon", "Earth")}
PRECISION_RELATIVE = Decimal("1e-60")
ABSOLUTE_ENVELOPE_M_S2 = Decimal("1e-15")
RELATIVE_ENVELOPE = Decimal("1e-11")
type ExactVector = tuple[Fraction, Fraction, Fraction]
type DecimalVector = tuple[Decimal, Decimal, Decimal]


def load_oracle() -> ModuleType:
    """Load only the unchanged, hash-pinned stdlib polynomial helper."""
    raw = ORACLE_PATH.read_bytes()
    if sha256(raw).hexdigest() != ORACLE_SHA256:
        raise ValueError("polynomial helper SHA256 mismatch")
    spec = importlib.util.spec_from_file_location("ariadna_0157_polynomial_oracle", ORACLE_PATH)
    if spec is None or spec.loader is None:
        raise ValueError("polynomial helper loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(ORACLE_PATH), "exec"), module.__dict__)
    return module


ORACLE = load_oracle()


def _number(value: Any, field: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{field}: expected finite number excluding bool")
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f"{field}: expected finite number") from error
    if not math.isfinite(result):
        raise ValueError(f"{field}: expected finite number")
    return result


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise ValueError(f"{field}: expected object with string keys")
    return value


def _exact_vector(value: Any, field: str) -> ExactVector:
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ValueError(f"{field}: expected three finite components")
    items = tuple(Fraction.from_float(_number(item, f"{field}[{i}]"))
                  for i, item in enumerate(value))
    return items[0], items[1], items[2]


def _sum_exact(*vectors: ExactVector) -> ExactVector:
    values = tuple(sum((vector[i] for vector in vectors), Fraction()) for i in range(3))
    return values[0], values[1], values[2]


def _negative(vector: ExactVector) -> ExactVector:
    return -vector[0], -vector[1], -vector[2]


def _encoded(vector: ExactVector) -> list[dict[str, str]]:
    return [{"numerator": str(value.numerator), "denominator": str(value.denominator)}
            for value in vector]


def _json_equal(left: Any, right: Any) -> bool:
    try:
        return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(
            right, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("saved assessment: expected finite JSON") from error


def reconstruct_source(row: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct exact selected polynomials and reconcile every saved assessment.

    The caller additionally binds retained file hashes, frozen epochs, directory
    metadata and full provenance. This helper verifies body chains, frame, type,
    record/segment coverage and the exact saved polynomial assessment itself.
    """
    row = _mapping(row, "source row")
    body = row.get("body")
    if type(body) is not str or body not in CHAINS:
        raise ValueError("source body: expected Sun, Moon or Earth")
    hi = _number(row.get("hi_tdb_s"), "hi_tdb_s")
    lo = _number(row.get("lo_s"), "lo_s")
    if row.get("hi_hex") != hi.hex() or row.get("lo_hex") != lo.hex():
        raise ValueError("source epoch numeric/hex mismatch")
    hi_exact, time_exact = Fraction.from_float(hi), Fraction.from_float(hi) + Fraction.from_float(lo)
    state = row.get("state_si")
    if not isinstance(state, (list, tuple)) or len(state) != 6:
        raise ValueError("state_si: expected six finite components")
    native = [_number(value, f"state_si[{i}]") for i, value in enumerate(state)]
    segments = row.get("segments")
    if type(segments) is not list or len(segments) != len(CHAINS[body]):
        raise ValueError("source segments: invalid centre chain")
    records: list[Any] = []
    for i, (segment, expected) in enumerate(zip(segments, CHAINS[body], strict=True)):
        segment = _mapping(segment, f"segments[{i}]")
        metadata = tuple(segment.get(key) for key in ("body", "centre", "frame", "type"))
        if any(type(value) is not int for value in metadata) or metadata != (*expected, 1, 2):
            raise ValueError("source chain/body/centre/frame/type mismatch")
        first = Fraction.from_float(_number(segment.get("first_tdb_s"), "segment first_tdb_s"))
        last = Fraction.from_float(_number(segment.get("last_tdb_s"), "segment last_tdb_s"))
        if not first <= min(hi_exact, time_exact) <= max(hi_exact, time_exact) <= last:
            raise ValueError("source segment coverage")
        words = segment.get("words")
        if type(words) is not list:
            raise ValueError("record.words: expected list")
        records.append(ORACLE.parse_record([
            _number(value, f"record.words[{j}]") for j, value in enumerate(words)]))
    position_hi, _, _ = ORACLE.evaluate_chain(records, hi_exact)
    position_time, _, _ = ORACLE.evaluate_chain(records, time_exact)
    assessment = ORACLE.assess(native, records, hi, lo)
    if not _json_equal(row.get("assessment"), assessment):
        raise ValueError("saved assessment reconstruction mismatch")
    return {"body": body, "position_hi_m": position_hi, "position_time_m": position_time,
            "native_m": _exact_vector(native[:3], "native_m"),
            "correction_m": _exact_vector(assessment["correction_m"], "correction_m"),
            "assessment": assessment}


def _decimal(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


def _field(geometry_m: ExactVector, gm_m3_s2: Fraction) -> DecimalVector:
    """Evaluate one rational geometry within the caller's Decimal context."""
    vector = tuple(_decimal(value) for value in geometry_m)
    square = sum((value * value for value in vector), Decimal())
    denominator = square * square.sqrt()
    gm = _decimal(gm_m3_s2)
    result = tuple(gm * value / denominator for value in vector)
    if any(not value.is_finite() for value in result):
        raise ValueError("reference field: nonfinite result")
    return result[0], result[1], result[2]


def _norm(vector: DecimalVector) -> Decimal:
    return sum((value * value for value in vector), Decimal()).sqrt()


def _subtract(left: DecimalVector, right: DecimalVector) -> DecimalVector:
    return left[0] - right[0], left[1] - right[1], left[2] - right[2]


def _sum_decimal(vectors: Sequence[DecimalVector]) -> DecimalVector:
    values = tuple(sum((vector[i] for vector in vectors), Decimal()) for i in range(3))
    return values[0], values[1], values[2]


def _wire_vector(vector: DecimalVector) -> list[str]:
    return [str(value) for value in vector]


def _read_vector(value: Any, field: str) -> DecimalVector:
    if type(value) is not list or len(value) != 3 or any(type(item) is not str for item in value):
        raise ValueError(f"{field}: expected three Decimal strings")
    vector = tuple(Decimal(item) for item in value)
    if any(not item.is_finite() for item in vector):
        raise ValueError(f"{field}: nonfinite Decimal")
    return vector[0], vector[1], vector[2]


def _gate(candidate: DecimalVector, reference: DecimalVector, scale: Decimal) -> dict[str, Any]:
    error = _norm(_subtract(candidate, reference))
    envelope = max(ABSOLUTE_ENVELOPE_M_S2, RELATIVE_ENVELOPE * scale)
    return {"error_norm_m_s2": str(error), "envelope_m_s2": str(envelope),
            "passed": error <= envelope}


def _assessment(
    fields: dict[str, dict[str, DecimalVector]],
    scales: dict[str, dict[str, Decimal]],
    candidates: dict[str, ExactVector],
) -> dict[str, Any]:
    references: dict[str, Any] = {}
    reference_norms: dict[str, Any] = {}
    contributions: dict[str, Any] = {}
    gates: dict[str, Any] = {}
    telescope: dict[str, Any] = {}
    for precision in PROFILES:
        key = str(precision)
        with localcontext() as context:
            context.prec = precision
            context.rounding = ROUND_HALF_EVEN
            f = fields[key]
            candidate = {name: tuple(_decimal(value) for value in vector)
                         for name, vector in candidates.items()}
            compensated = candidate["compensated"]
            errors = (_subtract(f["d1"], f["d0"]), _subtract(f["d2"], f["d1"]),
                      _subtract(f["d3"], f["d2"]), _subtract(compensated, f["d3"]))
            residual = _subtract(_sum_decimal(errors), _subtract(compensated, f["d0"]))
            scale = sum(scales[key].values(), Decimal())
            telescope_error = _norm(residual)
            telescope_limit = PRECISION_RELATIVE * scale
            telescope[key] = {"residual_m_s2": _wire_vector(residual),
                              "error_norm_m_s2": str(telescope_error),
                              "limit_m_s2": str(telescope_limit),
                              "passed": telescope_error <= telescope_limit}
            references[key] = {name: _wire_vector(f[name]) for name in GEOMETRIES}
            reference_norms[key] = {name: str(scales[key][name]) for name in GEOMETRIES}
            contributions[key] = {name: _wire_vector(vector)
                                  for name, vector in zip(CONTRIBUTIONS, errors, strict=True)}
            gates[key] = {
                "returned_geometry": _gate(compensated, f["d3"], scales[key]["d3"]),
                "overall": _gate(compensated, f["d0"], scales[key]["d0"]),
                "controls": {name: _gate(candidate[name], f["d0"], scales[key]["d0"])
                             for name in ARM_NAMES[1:]},
            }
    with localcontext() as context:
        context.prec = 100
        context.rounding = ROUND_HALF_EVEN
        differences: dict[str, Any] = {}
        for name in GEOMETRIES:
            low, high = fields["80"][name], fields["100"][name]
            difference = _norm(_subtract(low, high))
            limit = PRECISION_RELATIVE * scales["100"][name]
            zero_preserved = (_norm(low) == 0) == (_norm(high) == 0)
            differences[name] = {"difference_norm_m_s2": str(difference),
                                 "limit_m_s2": str(limit),
                                 "zero_preserved": zero_preserved,
                                 "passed": zero_preserved and difference <= limit}
    stable = all(gates["80"][name]["passed"] == gates["100"][name]["passed"]
                 for name in ("returned_geometry", "overall")) and all(
        gates["80"]["controls"][name]["passed"] == gates["100"]["controls"][name]["passed"]
        for name in ARM_NAMES[1:])
    precision_passed = stable and all(value["passed"] for value in differences.values())
    return {
        "reference": references, "reference_norms_m_s2": reference_norms,
        "contributions_m_s2": contributions, "gates": gates, "telescope": telescope,
        "precision": {"reference_fields": differences, "gate_classifications_stable": stable,
                      "passed": precision_passed},
        "passed": precision_passed and all(value["passed"] for value in telescope.values())
        and all(gates[str(p)][name]["passed"] for p in PROFILES
                for name in ("returned_geometry", "overall")),
    }


def _candidate_vectors(arms: dict[str, Any]) -> dict[str, ExactVector]:
    arms = _mapping(arms, "arms")
    if set(arms) != set(ARM_NAMES):
        raise ValueError("arms: expected compensated/uncorrected/wrong_sign")
    return {name: _exact_vector(_mapping(arms[name], name).get("acceleration_m_s2"),
                                f"{name}.acceleration_m_s2") for name in ARM_NAMES}


def assess_source(
    row: dict[str, Any], position_m: Sequence[float], gm_m3_s2: float, radius_m: float,
    arms: dict[str, Any], consume_reference: Callable[[str], None], *,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assess four exact geometries at 80/100 digits; controls use d0 only.

    Required false gates remain ordinary finite evidence for the caller's
    fail-stop. Domain/input failures raise before any reference field is consumed.
    Callbacks account for each attempted and successfully completed field.
    Optional progress preserves each returned vector before its completion event.
    """
    if progress is not None:
        progress = _mapping(progress, "source progress")
        progress["reference"] = {str(precision): {} for precision in PROFILES}
    source = reconstruct_source(row)
    position = _exact_vector(position_m, "position_m")
    gm = Fraction.from_float(_number(gm_m3_s2, "gm_m3_s2"))
    radius = Fraction.from_float(_number(radius_m, "radius_m"))
    if gm <= 0 or radius <= 0:
        raise ValueError("gm_m3_s2 and radius_m: expected positive values")
    candidates = _candidate_vectors(arms)
    separations = {name: _exact_vector(arms[name].get("separation_m"), f"{name}.separation_m")
                   for name in ARM_NAMES}
    corrections = {name: _exact_vector(arms[name].get("rephasing_m"), f"{name}.rephasing_m")
                   for name in ARM_NAMES}
    expected = source["correction_m"]
    if corrections != {"compensated": expected, "uncorrected": (Fraction(),) * 3,
                       "wrong_sign": _negative(expected)}:
        raise ValueError("candidate correction operands/sign mismatch")
    source_discrepancy = _sum_exact(source["native_m"], _negative(source["position_hi_m"]))
    geometries = {
        "d0": _sum_exact(source["position_time_m"], _negative(position)),
        "d1": _sum_exact(source["position_time_m"], source_discrepancy, _negative(position)),
        "d2": _sum_exact(source["native_m"], expected, _negative(position)),
        "d3": separations["compensated"],
    }
    guards = {name: sum((value * value for value in vector), Fraction()) > radius * radius
              for name, vector in {**geometries, **separations}.items()}
    if not all(guards.values()):
        raise ValueError("source exterior-domain guard: " + source["body"])
    fields: dict[str, dict[str, DecimalVector]] = {}
    scales: dict[str, dict[str, Decimal]] = {}
    for precision in PROFILES:
        key = str(precision)
        with localcontext() as context:
            context.prec = precision
            context.rounding = ROUND_HALF_EVEN
            fields[key], scales[key] = {}, {}
            for name in GEOMETRIES:
                consume_reference("attempt")
                fields[key][name] = _field(geometries[name], gm)
                if progress is not None:
                    progress["reference"][key][name] = _wire_vector(fields[key][name])
                consume_reference("complete")
                scales[key][name] = _norm(fields[key][name])
    result = _assessment(fields, scales, candidates)
    return {"body": source["body"], "exact_geometries_m": {
        name: _encoded(vector) for name, vector in geometries.items()},
        "exact_position_hi_m": _encoded(source["position_hi_m"]),
        "exact_position_time_m": _encoded(source["position_time_m"]),
        "exact_native_source_discrepancy_m": _encoded(source_discrepancy),
        "domain_guards": guards, "saved_assessment_reconciled": True, **result}


def _idle(_phase: str) -> None:
    """Allow direct pure assessment without an external execution ledger."""


def assess_totals(
    source_results: list[dict[str, Any]], arms: dict[str, Any], *,
    consume_model: Callable[[str], None] = _idle,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Sum retained source vectors before norms; cancellation keeps source scales.

    Exactly Sun/Moon/Earth are required. No additional force evaluation occurs.
    ``arms`` maps A/B to the three candidate-arm acceleration records. Optional
    progress preserves each model result before its completion event.
    """
    if type(source_results) is not list or len(source_results) != 3:
        raise ValueError("totals source set: expected Sun/Moon/Earth")
    sources: dict[str, dict[str, Any]] = {}
    for result in source_results:
        result = _mapping(result, "source result")
        body = result.get("body")
        if type(body) is not str or body not in CHAINS or body in sources:
            raise ValueError("totals source set: expected unique Sun/Moon/Earth")
        sources[body] = result
    arms = _mapping(arms, "total arms")
    if set(arms) != set(MODELS):
        raise ValueError("total arms: expected models A/B")
    totals = {} if progress is None else _mapping(progress, "model progress")
    if totals:
        raise ValueError("model progress: expected initially empty object")
    for model, bodies in MODELS.items():
        consume_model("attempt")
        candidates = _candidate_vectors(arms[model])
        fields: dict[str, dict[str, DecimalVector]] = {}
        scales: dict[str, dict[str, Decimal]] = {}
        for precision in PROFILES:
            key = str(precision)
            with localcontext() as context:
                context.prec = precision
                context.rounding = ROUND_HALF_EVEN
                fields[key], scales[key] = {}, {}
                for name in GEOMETRIES:
                    vectors = [_read_vector(sources[body]["reference"][key][name], "reference field")
                               for body in bodies]
                    fields[key][name] = _sum_decimal(vectors)
                    scales[key][name] = sum((_norm(vector) for vector in vectors), Decimal())
        totals[model] = {"model": model, "source_order": list(bodies),
                         **_assessment(fields, scales, candidates)}
        consume_model("complete")
        if not totals[model]["passed"]:
            break
    return totals
