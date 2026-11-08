"""Independent Fraction/Decimal assembly checks for ADR0159; no candidate imports.

SI, SSB/J2000, TDB seconds since J2000 and geometric NONE source states. Only
immutable pure source/reference helpers are reused. Import evaluates no field.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from hashlib import sha256
import importlib.util
import math
from pathlib import Path
import struct
import sys
from types import ModuleType
from typing import Any

REFERENCE_PATH = Path(__file__).with_name("0157-fixed-gravity-reference.py")
REFERENCE_SHA256 = "1337ba2b1fea94381e175603a501ec36b992a2194faf46dea6a3e429a7aef9b8"
ARMS = ("compensated", "flattened_craft", "omitted_q")
ALIASES = dict(zip(ARMS, ("compensated", "uncorrected", "wrong_sign"), strict=True))
MODELS = {"A": ("Sun", "Moon"), "B": ("Sun", "Moon", "Earth")}
FIXTURE_ACCELERATION = (Fraction(-1), Fraction(1, 2), Fraction(-1, 4))
LABEL = "controlled-kinematic-arithmetic-probe"
type ExactVector = tuple[Fraction, Fraction, Fraction]


def _load_reference() -> ModuleType:
    raw = REFERENCE_PATH.read_bytes()
    if sha256(raw).hexdigest() != REFERENCE_SHA256:
        raise ValueError("immutable reference SHA256 mismatch")
    spec = importlib.util.spec_from_file_location(
        "ariadna_0160_base_reference", REFERENCE_PATH
    )
    if spec is None or spec.loader is None:
        raise ValueError("immutable reference loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(REFERENCE_PATH), "exec"), module.__dict__)
    return module


BASE = _load_reference()
ORACLE = BASE.ORACLE


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: Any, field: str) -> float:
    return BASE._number(value, field)


def _exact(value: Any, field: str) -> Fraction:
    return Fraction.from_float(_number(value, field))


def _vector(value: Any, field: str) -> ExactVector:
    return BASE._exact_vector(value, field)


def _encoded(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _encoded_vector(value: ExactVector) -> list[dict[str, str]]:
    return [_encoded(component) for component in value]


def _norm(value: ExactVector) -> str:
    with localcontext() as context:
        context.prec = 100
        context.rounding = ROUND_HALF_EVEN
        return str(sum((BASE._decimal(x) ** 2 for x in value), Decimal()).sqrt())


def _ulp(value: float) -> Fraction:
    return Fraction.from_float(math.ulp(value))


def _round_gate(value: Any, target: Fraction, units: str) -> dict[str, Any]:
    actual = _number(value, "rounded operand")
    expected = float(target)
    _require(math.isfinite(expected), "rounding target outside binary64 range")
    error = Fraction.from_float(actual) - target
    bound = _ulp(actual) / 2
    midpoint = False
    if Fraction.from_float(expected) != target:
        neighbor = math.nextafter(
            expected, math.inf if target > Fraction.from_float(expected) else -math.inf
        )
        if math.isfinite(neighbor):
            midpoint = 2 * target == Fraction.from_float(
                expected
            ) + Fraction.from_float(neighbor)
    even = int.from_bytes(struct.pack(">d", actual)) % 2 == 0
    nearest = actual == expected
    zero = target != 0 or actual == 0
    return {
        "signed_error": _encoded(error),
        "bound": _encoded(bound),
        "units": units,
        "expected_rn_hex": expected.hex(),
        "midpoint": midpoint,
        "nearest_ties_even": nearest and (not midpoint or even),
        "zero_preserved": zero,
        "passed": abs(error) <= bound and nearest and (not midpoint or even) and zero,
    }


def _sum_gate(
    value: Any, target: Fraction, bound: Fraction, operand_sum: Fraction, units: str
) -> dict[str, Any]:
    error = _exact(value, "returned sum") - target
    zero = operand_sum != 0 or _number(value, "returned sum") == 0
    return {
        "signed_error": _encoded(error),
        "bound": _encoded(bound),
        "units": units,
        "zero_required": operand_sum == 0,
        "zero_preserved": zero,
        "passed": abs(error) <= bound and zero,
    }


def prescribed_corrections(elapsed_s: Any) -> dict[str, Any]:
    """Independently construct only the prescribed rounded q/w input metadata."""
    elapsed = _number(elapsed_s, "elapsed_s")
    _require(0 <= elapsed <= 300, "elapsed_s outside [0,300]s")
    s = Fraction.from_float(elapsed)
    ideal_q = tuple(a * s * s / 2 for a in FIXTURE_ACCELERATION)
    ideal_w = tuple(a * s for a in FIXTURE_ACCELERATION)
    q, w = [float(x) for x in ideal_q], [float(x) for x in ideal_w]
    return {
        "q_ideal_m": [_encoded(x) for x in ideal_q],
        "w_ideal_m_s": [_encoded(x) for x in ideal_w],
        "q_m": q,
        "q_hex": [x.hex() for x in q],
        "q_ratios": [_encoded(Fraction.from_float(x)) for x in q],
        "w_m_s": w,
        "w_hex": [x.hex() for x in w],
        "w_ratios": [_encoded(Fraction.from_float(x)) for x in w],
    }


def _motion_operands(initial: dict[str, Any], motion: dict[str, Any]) -> dict[str, Any]:
    initial = BASE._mapping(initial, "initial")
    motion = BASE._mapping(motion, "motion")
    r0 = _vector(initial.get("position_m"), "initial.position_m")
    v0 = _vector(initial.get("velocity_m_s"), "initial.velocity_m_s")
    s = _exact(motion.get("elapsed_s"), "motion.elapsed_s")
    _require(0 <= s <= 300, "elapsed_s outside [0,300]s")
    q = _vector(motion.get("q_m"), "motion.q_m")
    w = _vector(motion.get("w_m_s"), "motion.w_m_s")
    drift = _vector(motion.get("drift_m"), "motion.drift_m")
    position = _vector(motion.get("position_m"), "motion.position_m")
    velocity = _vector(motion.get("velocity_m_s"), "motion.velocity_m_s")
    exact_drift = tuple(v * s for v in v0)
    exact_position = tuple(
        r + d + c for r, d, c in zip(r0, exact_drift, q, strict=True)
    )
    exact_velocity = tuple(v + c for v, c in zip(v0, w, strict=True))
    return {
        "r0": r0,
        "v0": v0,
        "s": s,
        "q": q,
        "w": w,
        "drift": drift,
        "position": position,
        "velocity": velocity,
        "exact_drift": exact_drift,
        "exact_position": exact_position,
        "exact_velocity": exact_velocity,
    }


def assess_motion(initial: dict[str, Any], motion: dict[str, Any]) -> dict[str, Any]:
    """Check returned six-state assembly with exact input and sum-zero semantics."""
    operands = _motion_operands(initial, motion)
    s = operands["s"]
    q_ideal = tuple(a * s * s / 2 for a in FIXTURE_ACCELERATION)
    w_ideal = tuple(a * s for a in FIXTURE_ACCELERATION)
    metadata = prescribed_corrections(motion["elapsed_s"])
    wire = {
        name: BASE._json_equal(motion.get(name), value)
        for name, value in metadata.items()
    }
    # Numerical zero may have either sign; hex metadata must match actual operands.
    for values_name, hex_name in (("q_m", "q_hex"), ("w_m_s", "w_hex")):
        wire[values_name] = motion[values_name] == metadata[values_name]
        wire[hex_name] = motion.get(hex_name) == [
            float(x).hex() for x in motion[values_name]
        ]
    wire["label"] = motion.get("label") == LABEL
    wire["elapsed_hex"] = motion.get("elapsed_hex") == float(s).hex()
    checks: dict[str, Any] = {
        name: []
        for name in (
            "q_rounding",
            "w_rounding",
            "drift_product",
            "position_sum",
            "velocity_sum",
        )
    }
    for j in range(3):
        checks["q_rounding"].append(_round_gate(motion["q_m"][j], q_ideal[j], "m"))
        checks["w_rounding"].append(_round_gate(motion["w_m_s"][j], w_ideal[j], "m/s"))
        checks["drift_product"].append(
            _round_gate(motion["drift_m"][j], operands["exact_drift"][j], "m")
        )
        checks["position_sum"].append(
            _sum_gate(
                motion["position_m"][j],
                operands["exact_position"][j],
                _ulp(motion["drift_m"][j]) / 2 + _ulp(motion["position_m"][j]),
                operands["r0"][j] + operands["drift"][j] + operands["q"][j],
                "m",
            )
        )
        checks["velocity_sum"].append(
            _sum_gate(
                motion["velocity_m_s"][j],
                operands["exact_velocity"][j],
                _ulp(motion["velocity_m_s"][j]),
                operands["exact_velocity"][j],
                "m/s",
            )
        )
    drift_error = tuple(
        a - b for a, b in zip(operands["drift"], operands["exact_drift"], strict=True)
    )
    position_error = tuple(
        a - b
        for a, b in zip(operands["position"], operands["exact_position"], strict=True)
    )
    velocity_error = tuple(
        a - b
        for a, b in zip(operands["velocity"], operands["exact_velocity"], strict=True)
    )
    return {
        "exact_position_m": _encoded_vector(operands["exact_position"]),
        "exact_velocity_m_s": _encoded_vector(operands["exact_velocity"]),
        "exact_drift_m": _encoded_vector(operands["exact_drift"]),
        "component_gates": checks,
        "wire_metadata": wire,
        "error_norms": {
            "drift_m": _norm(drift_error),
            "position_m": _norm(position_error),
            "velocity_m_s": _norm(velocity_error),
        },
        "passed": all(wire.values())
        and all(c["passed"] for v in checks.values() for c in v),
    }


def _candidates(arms: dict[str, Any]) -> dict[str, ExactVector]:
    arms = BASE._mapping(arms, "arms")
    _require(
        set(arms) == set(ARMS), "expected compensated/flattened_craft/omitted_q arms"
    )
    return {
        ALIASES[name]: _vector(
            BASE._mapping(arms[name], name).get("acceleration_m_s2"), name
        )
        for name in ARMS
    }


def _rename(result: dict[str, Any]) -> dict[str, Any]:
    for values in result["contributions_m_s2"].values():
        values["rephasing_and_drift"] = values.pop("residual_rephasing")
    for values in result["gates"].values():
        old = values["controls"]
        values["controls"] = {name: old[ALIASES[name]] for name in ARMS[1:]}
    return result


def preflight_source(
    row: dict[str, Any],
    initial: dict[str, Any],
    motion: dict[str, Any],
    gm_m3_s2: float,
    radius_m: float,
    arms: dict[str, Any],
    *,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check every exact/control geometry before any binary64 or Decimal field.

    Arms need separation/rephasing operands only. Returned Fraction objects are
    private computation operands; progress retains only finite wire evidence.
    """
    target = {} if progress is None else BASE._mapping(progress, "source progress")
    target["reference"] = {str(p): {} for p in BASE.PROFILES}
    source = BASE.reconstruct_source(row)
    o = _motion_operands(initial, motion)
    _require(
        _exact(row.get("elapsed_s"), "source elapsed_s") == o["s"],
        "source/motion elapsed mismatch",
    )
    _require(
        _exact(initial.get("epoch_tdb_s"), "initial epoch") + o["s"]
        == _exact(row["hi_tdb_s"], "hi") + _exact(row["lo_s"], "lo"),
        "source/motion epoch mismatch",
    )
    gm, radius = _exact(gm_m3_s2, "gm_m3_s2"), _exact(radius_m, "radius_m")
    _require(gm > 0 and radius > 0, "positive GM and radius required")
    arms = BASE._mapping(arms, "arms")
    _require(
        set(arms) == set(ARMS), "expected compensated/flattened_craft/omitted_q arms"
    )
    separations = {
        name: _vector(arms[name].get("separation_m"), name + ".separation_m")
        for name in ARMS
    }
    correction = source["correction_m"]
    corrections = {
        name: _vector(arms[name].get("rephasing_m"), name + ".rephasing_m")
        for name in ARMS
    }
    discrepancy = tuple(
        source["native_m"][j] - source["position_hi_m"][j] for j in range(3)
    )
    geometries = {
        "d0": tuple(
            source["position_time_m"][j] - o["exact_position"][j] for j in range(3)
        ),
        "d1": tuple(
            source["position_time_m"][j] + discrepancy[j] - o["exact_position"][j]
            for j in range(3)
        ),
        "d2": tuple(
            source["native_m"][j]
            + correction[j]
            - o["r0"][j]
            - o["drift"][j]
            - o["q"][j]
            for j in range(3)
        ),
        "d3": separations["compensated"],
    }
    increment = tuple(
        correction[j] - (source["position_time_m"][j] - source["position_hi_m"][j])
        for j in range(3)
    )
    drift_error = tuple(o["drift"][j] - o["exact_drift"][j] for j in range(3))
    identity = all(
        geometries["d2"][j] - geometries["d1"][j] == increment[j] - drift_error[j]
        for j in range(3)
    )
    relative = [
        _sum_gate(
            arms["compensated"]["separation_m"][j],
            geometries["d2"][j],
            _ulp(arms["compensated"]["separation_m"][j]),
            geometries["d2"][j],
            "m",
        )
        for j in range(3)
    ]
    rephase = [
        _round_gate(
            arms["compensated"]["rephasing_m"][j],
            _exact(row["state_si"][j + 3], "body velocity") * _exact(row["lo_s"], "lo"),
            "m",
        )
        for j in range(3)
    ]
    guards = {
        name: sum((v * v for v in vector), Fraction()) > radius * radius
        for name, vector in {**geometries, **separations}.items()
    }
    assembly = {
        "exact_geometries_m": {
            name: _encoded_vector(v) for name, v in geometries.items()
        },
        "exact_position_hi_m": _encoded_vector(source["position_hi_m"]),
        "exact_position_time_m": _encoded_vector(source["position_time_m"]),
        "exact_native_source_discrepancy_m": _encoded_vector(discrepancy),
        "exact_source_increment_error_m": _encoded_vector(increment),
        "exact_drift_product_error_m": _encoded_vector(drift_error),
        "geometry_error_identity": identity,
        "relative_sum_components": relative,
        "rephasing_product_components": rephase,
        "correction_operands_match": all(v == correction for v in corrections.values()),
        "domain_guards": guards,
        "saved_assessment_reconciled": True,
    }
    target["assembly"] = assembly
    _require(all(guards.values()), "source exterior-domain guard: " + source["body"])
    _require(
        assembly["correction_operands_match"]
        and identity
        and all(x["passed"] for x in relative + rephase),
        "required relative assembly/RN-product gate",
    )
    return {
        "body": source["body"],
        "geometries_m": geometries,
        "gm_m3_s2": gm,
        "assembly": assembly,
    }


def assess_source(
    row: dict[str, Any],
    initial: dict[str, Any],
    motion: dict[str, Any],
    gm_m3_s2: float,
    radius_m: float,
    arms: dict[str, Any],
    consume_reference: Callable[[str], None],
    *,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check moving geometry before eight independently evaluated reference fields."""
    target = {} if progress is None else BASE._mapping(progress, "source progress")
    prepared = preflight_source(
        row, initial, motion, gm_m3_s2, radius_m, arms, progress=target
    )
    geometries, gm = prepared["geometries_m"], prepared["gm_m3_s2"]
    candidates = _candidates(arms)
    fields: dict[str, Any] = {}
    scales: dict[str, Any] = {}
    for p in BASE.PROFILES:
        key = str(p)
        with localcontext() as context:
            context.prec = p
            context.rounding = ROUND_HALF_EVEN
            fields[key], scales[key] = {}, {}
            for name in BASE.GEOMETRIES:
                consume_reference("attempt")
                fields[key][name] = BASE._field(geometries[name], gm)
                target["reference"][key][name] = BASE._wire_vector(fields[key][name])
                consume_reference("complete")
                scales[key][name] = BASE._norm(fields[key][name])
    result = _rename(BASE._assessment(fields, scales, candidates))
    return {"body": prepared["body"], **prepared["assembly"], **result}


def _idle(_phase: str) -> None:
    pass


def assess_totals(
    source_results: list[dict[str, Any]],
    arms: dict[str, Any],
    *,
    consume_model: Callable[[str], None] = _idle,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate saved vectors with source-norm scales and preserve model prefixes."""
    _require(
        type(source_results) is list and len(source_results) == 3,
        "exactly three source results",
    )
    sources: dict[str, Any] = {}
    for item in source_results:
        item = BASE._mapping(item, "source result")
        body = item.get("body")
        _require(
            type(body) is str and body in BASE.CHAINS and body not in sources,
            "unique Sun/Moon/Earth sources",
        )
        sources[body] = item
    arms = BASE._mapping(arms, "model arms")
    _require(set(arms) == set(MODELS), "models A and B required")
    target = {} if progress is None else BASE._mapping(progress, "model progress")
    _require(not target, "model progress must initially be empty")
    for model, bodies in MODELS.items():
        consume_model("attempt")
        candidates = _candidates(arms[model])
        fields: dict[str, Any] = {}
        scales: dict[str, Any] = {}
        for p in BASE.PROFILES:
            key = str(p)
            with localcontext() as context:
                context.prec = p
                context.rounding = ROUND_HALF_EVEN
                fields[key], scales[key] = {}, {}
                for name in BASE.GEOMETRIES:
                    vectors = [
                        BASE._read_vector(
                            sources[b]["reference"][key][name], "reference"
                        )
                        for b in bodies
                    ]
                    fields[key][name] = BASE._sum_decimal(vectors)
                    scales[key][name] = sum((BASE._norm(v) for v in vectors), Decimal())
        target[model] = {
            "model": model,
            "source_order": list(bodies),
            **_rename(BASE._assessment(fields, scales, candidates)),
        }
        consume_model("complete")
        if not target[model]["passed"]:
            break
    return target
