"""Independent ADR0179 sample gates on saved SI/SSB/J2000/TDB/NONE operands."""
from __future__ import annotations

from collections.abc import Callable
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

HISTORICAL_PATH = Path(__file__).with_name("0163-corrected-reference.py")
HISTORICAL_SHA256 = "2500e52496289cc75c93dba8825cd222d70f56cc97f48171b8e01328fe2bde65"


def _load_historical() -> ModuleType:
    raw = HISTORICAL_PATH.read_bytes()
    if sha256(raw).hexdigest() != HISTORICAL_SHA256:
        raise ValueError("immutable reference SHA256 mismatch")
    spec = importlib.util.spec_from_file_location("ariadna_0180_reference_primitives", HISTORICAL_PATH)
    if spec is None:
        raise ValueError("immutable reference loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(HISTORICAL_PATH), "exec"), module.__dict__)
    return module


HISTORICAL = _load_historical()
BASE = HISTORICAL.BASE
ORACLE = HISTORICAL.ORACLE
MOTION = HISTORICAL.MOTION
BODIES = HISTORICAL.BODIES
INCLUDED = HISTORICAL.INCLUDED
MOON_EARTH = "Moon/Earth"
assess_motion = HISTORICAL.assess_motion
compare_states = HISTORICAL.compare_states
_require = HISTORICAL._require
idle = HISTORICAL.idle

type Vector = tuple[Fraction, Fraction, Fraction]
type Evaluation = tuple[Vector, Vector, Vector]
type Chain = tuple[tuple[int, int], ...]
type Event = Callable[[str, str], None]
type Check = Callable[[], None]

POSITION_LIMIT_M = Fraction(1, 1000)
VELOCITY_LIMIT_M_S = Fraction(1, 1_000_000)
INCREMENT_LIMIT_M = Fraction(1, 10**12)


def _number(value: Any, label: str) -> float:
    return BASE._number(value, label)


def _words(value: object, size: int, label: str, *, binary64: bool = False) -> tuple[float, ...]:
    _require(isinstance(value, (list, tuple)) and len(value) == size, label + ": wrong size")
    if binary64:
        _require(all(type(x) is float for x in value), label + ": expected binary64 words")
    return tuple(_number(x, label) for x in value)


def _bits(vector: tuple[float, ...]) -> list[str]:
    return [x.hex() for x in vector]


def _vector(values: tuple[Fraction, ...]) -> Vector:
    return values[0], values[1], values[2]


def _rational_words(value: object) -> Vector:
    _require(type(value) in (list, tuple) and len(value) == 3 and all(type(x) is str for x in value),
             "Moon pre-round separation requires three exact fraction strings")
    result = tuple(map(Fraction, value))
    _require(all(str(x) == y for x, y in zip(result, value, strict=True)),
             "Moon pre-round separation has noncanonical fraction")
    return _vector(result)


def _square(vector: Vector) -> Fraction:
    return sum((x*x for x in vector), Fraction())


def _segment_key(segment: dict[str, Any], expected: tuple[int, int]) -> str:
    metadata = tuple(segment.get(k) for k in ("body", "centre", "frame", "type"))
    _require(all(type(x) is int for x in metadata) and metadata == (*expected, 1, 2),
             "source body/centre/frame/type mismatch")
    # JSON keeps -0.0 and distinguishes booleans from numbers.
    return json.dumps(segment, sort_keys=True, allow_nan=False)


def _record_templates(rows: dict[str, Any], hi: Fraction, exact: Fraction) -> dict[tuple[int, int], Any]:
    records, identities = {}, {}
    for body in (*BODIES, MOON_EARTH):
        chain = BASE.CHAINS[body] if body != MOON_EARTH else ((301, 399),)
        segments = rows[body].get("segments")
        _require(type(segments) is list and len(segments) == len(chain), "source centre chain mismatch")
        for segment, key in zip(segments, chain, strict=True):
            segment = BASE._mapping(segment, "source segment")
            pin = _segment_key(segment, key)
            if key in identities:
                _require(identities[key] == pin, "shared centre chain record mismatch")
                continue
            first, last = (Fraction(_number(segment.get(k), "segment " + k))
                           for k in ("first_tdb_s", "last_tdb_s"))
            _require(first <= min(hi, exact) <= max(hi, exact) <= last, "source segment coverage")
            record = ORACLE.parse_record(segment.get("words"))
            _require(record.midpoint_tdb_s-record.radius_s <= min(hi, exact)
                     <= max(hi, exact) <= record.midpoint_tdb_s+record.radius_s, "source record coverage")
            identities[key], records[key] = pin, record
    _require(set(records) == {(10, 0), (399, 0), (301, 399)}, "expected three independent records")
    return records


def _evaluate(records: dict[tuple[int, int], Any], hi: Fraction, exact: Fraction,
              consume: Event, check: Check) -> dict[Fraction, dict[tuple[int, int], Evaluation]]:
    cache: dict[Fraction, dict[tuple[int, int], Evaluation]] = {}
    for epoch in dict.fromkeys((hi, exact)):
        states: dict[tuple[int, int], Evaluation] = {}
        cache[epoch] = states
        for key, record in records.items():
            check()
            consume("record_evaluations", "attempt")
            states[key] = ORACLE.evaluate_chain((record,), epoch)
            consume("record_evaluations", "complete")
            check()
    return cache


def _chain(cache: dict[tuple[int, int], Evaluation], chain: Chain) -> Evaluation:
    first = cache[chain[0]]
    if len(chain) == 1:
        return first
    second = cache[chain[1]]
    return (BASE._sum_exact(first[0], second[0]), BASE._sum_exact(first[1], second[1]),
            BASE._sum_exact(first[2], second[2]))


def _signed_product(a: float, b: float) -> float:
    exact = Fraction(a) * Fraction(b)
    if exact:
        return float(exact)
    negative = math.copysign(1.0, a) != math.copysign(1.0, b)
    return -0.0 if negative else 0.0


def _state_errors(state: tuple[Fraction, ...], evaluated: Evaluation) -> tuple[Vector, Vector]:
    pos, vel, _ = evaluated
    return (_vector(tuple(state[j]-pos[j] for j in range(3))),
            _vector(tuple(state[j+3]-vel[j] for j in range(3))))


def _moon_earth_parity(row: dict[str, Any], evaluated: Evaluation, hi: float) -> dict[str, Any]:
    raw = _words(row.get("state_km_km_s"), 6, MOON_EARTH, binary64=True)
    error_p, error_v = _state_errors(tuple(Fraction(x)*1000 for x in raw), evaluated)
    p_sq, v_sq = _square(error_p), _square(error_v)
    checks = {"position_parity": p_sq <= POSITION_LIMIT_M**2, "velocity_parity": v_sq <= VELOCITY_LIMIT_M_S**2}
    return {"hi_tdb_s": hi, "state_km_km_s": list(raw), "source_assessment": {
        "position_error_norm_m": ORACLE._norm(error_p), "velocity_error_norm_m_s": ORACLE._norm(error_v),
        "signed_position_error_m": BASE._encoded(error_p), "signed_velocity_error_m_s": BASE._encoded(error_v),
        "position_error_squared_m2": str(p_sq), "velocity_error_squared_m2_s2": str(v_sq),
        "checks": checks, "passed": all(checks.values()),
    }, "passed": all(checks.values())}


def _ssb_assessment(si: tuple[float, ...], hi: float, lo: float,
                    evaluated: Evaluation, at_time: Evaluation) -> dict[str, Any]:
    """Apply the ADR0153 checks to evaluated operands without re-reading a record."""
    position, velocity, acceleration_bound = evaluated
    native = tuple(map(Fraction, si))
    error_p, error_v = _state_errors(native, evaluated)
    time = Fraction(lo)
    displacement = _vector(tuple(at_time[0][j]-position[j] for j in range(3)))
    product = _vector(tuple(v*time for v in native[3:]))
    corrected = [_signed_product(v, lo) for v in si[3:]]
    c = tuple(map(Fraction, corrected))
    rounding = _vector(tuple(c[j]-product[j] for j in range(3)))
    incremental = _vector(tuple(c[j]-displacement[j] for j in range(3)))
    total = _vector(tuple(error_p[j]+incremental[j] for j in range(3)))
    wrong = _vector(tuple(-c[j]-displacement[j] for j in range(3)))
    taylor = _vector(tuple(velocity[j]*time-displacement[j] for j in range(3)))
    velocity_term = _vector(tuple(error_v[j]*time for j in range(3)))
    _require(all(incremental[j] == taylor[j]+velocity_term[j]+rounding[j] for j in range(3)),
             "source increment signed telescope")
    bounds = _vector(tuple(abs(error_v[j])*abs(time)+acceleration_bound[j]*time*time/2+abs(rounding[j])
                           for j in range(3)))
    checks = {
        "position_parity": _square(error_p) <= POSITION_LIMIT_M**2,
        "velocity_parity": _square(error_v) <= VELOCITY_LIMIT_M_S**2,
        "increment": _square(incremental) <= INCREMENT_LIMIT_M**2,
        "taylor": all(abs(incremental[j]) <= bounds[j] for j in range(3)),
    }
    vectors = {
        "position_hi_m": position, "velocity_hi_m_s": velocity, "displacement_m": displacement,
        "source_position_floor_m": error_p, "velocity_error_m_s": error_v, "correction_exact_product_m": product,
        "correction_rounding_error_m": rounding, "increment_error_m": incremental,
        "corrected_position_error_m": total, "corrected_position_m": _vector(tuple(native[j]+c[j] for j in range(3))),
        "wrong_sign_increment_error_m": wrong, "acceleration_bound_m_s2": acceleration_bound, "taylor_bound_m": bounds,
        "signed_taylor_m": taylor, "signed_velocity_source_m": velocity_term,
    }
    return {
        "hi_tdb_s": hi, "lo_tdb_s": lo, "hi_hex": hi.hex(), "lo_hex": lo.hex(),
        "exact_epoch_tdb_s": ORACLE._encoded(Fraction(hi)+time), "correction_m": corrected,
        "exact": {key: BASE._encoded(values) for key, values in vectors.items()},
        "position_error_norm_m": ORACLE._norm(error_p), "velocity_error_norm_m_s": ORACLE._norm(error_v),
        "increment_error_norm_m": ORACLE._norm(incremental), "corrected_position_error_norm_m": ORACLE._norm(total),
        "wrong_sign_increment_error_norm_m": ORACLE._norm(wrong),
        "wrong_sign_passed": _square(wrong) <= INCREMENT_LIMIT_M**2,
        "wrong_sign_increment_passed": _square(wrong) <= INCREMENT_LIMIT_M**2,
        "checks": checks, "passed": all(checks.values()),
    }


def _geometry(body: str, geometry: dict[str, Any], assessment: dict[str, Any],
              source: Vector, evaluated: Evaluation, at_time: Evaluation, operands: dict[str, Any],
              radius: float, progress: dict[str, Any]) -> dict[str, Vector]:
    p_hi, p_time = evaluated[0], at_time[0]
    rephasing = _words(geometry.get("rephasing_m"), 3, body + " rephasing")
    _require(_bits(rephasing) == _bits(tuple(assessment["correction_m"])), body + " signed rephasing product")
    separation = _words(geometry.get("separation_m"), 3, body + " separation")
    c = tuple(map(Fraction, rephasing))
    x, r0, drift, exact_drift, q = (operands[k] for k in ("exact_position", "r0", "drift", "exact_drift", "q"))
    ds = {
        "d0": _vector(tuple(p_time[j]-x[j] for j in range(3))),
        "d1": _vector(tuple(p_time[j]+source[j]-p_hi[j]-x[j] for j in range(3))),
        "d2": _vector(tuple(source[j]+c[j]-r0[j]-drift[j]-q[j] for j in range(3))),
        "d3": _vector(tuple(map(Fraction, separation))),
    }
    if body == "Moon":
        _require(_rational_words(geometry.get("pre_round_separation_m")) == ds["d2"],
                 "Moon split pre-round separation mismatch")
        relative = [MOTION._round_gate(separation[j], ds["d2"][j], "m") for j in range(3)]
        for j, gate in enumerate(relative):
            # Historical _round_gate compares zeros by value. Here bits are part of the new assembly contract.
            gate["passed"] = gate["passed"] and separation[j].hex() == float(ds["d2"][j]).hex()
    else:
        relative = [MOTION._sum_gate(separation[j], ds["d2"][j], MOTION._ulp(separation[j]), ds["d2"][j], "m")
                    for j in range(3)]
    product = tuple(Fraction(item["numerator"]+"/"+item["denominator"])
                    for item in assessment["exact"]["correction_exact_product_m"])
    rephase = [MOTION._round_gate(rephasing[j], product[j], "m") for j in range(3)]
    increment = tuple(c[j]-(p_time[j]-p_hi[j]) for j in range(3))
    identity = all(ds["d2"][j]-ds["d1"][j] == increment[j]-(drift[j]-exact_drift[j]) for j in range(3))
    rr = Fraction(_number(radius, "radius_m"))
    _require(rr > 0, "positive radius required")
    domains = {name: _square(values) > rr*rr for name, values in ds.items()}
    rho = math.hypot(*separation)
    progress.update(component_gates={"relative_sum": relative, "rephasing_product": rephase},
                    geometry_error_identity=identity, domain_guards=domains,
                    binary64_exterior=math.isfinite(rho) and rho > radius,
                    exact_geometries_m={k: BASE._encoded(v) for k, v in ds.items()})
    _require(all(domains.values()) and progress["binary64_exterior"], "source exterior-domain guard: "+body)
    _require(identity and all(x["passed"] for x in relative+rephase), "required relative assembly/RN-product gate")
    return ds


def _raw_states(rows: dict[str, Any], initial: dict[str, Any], operands: dict[str, Any]) -> tuple[
    float, float, Fraction, dict[str, tuple[float, ...]], dict[str, tuple[float, ...]],
]:
    exact = Fraction(_number(initial.get("epoch_tdb_s"), "initial epoch")) + operands["s"]
    hi = float(exact)
    lo = float(exact-Fraction(hi))
    raw, si = {}, {}
    for body in (*BODIES, MOON_EARTH):
        row = BASE._mapping(rows[body], "source row")
        is_geo = body == MOON_EARTH
        _require(row.get("body") == ("Moon" if is_geo else body), "source body/order mismatch")
        if is_geo:
            _require((row.get("observer"), row.get("frame"), row.get("aberration")) == ("Earth", "J2000", "NONE"),
                     "Moon/Earth source observer/frame/correction mismatch")
            _require(_number(row.get("epoch_tdb_s"), "Moon/Earth query epoch").hex() == hi.hex(),
                     "Moon/Earth query epoch mismatch")
        else:
            if "epoch_tdb_s" in row:
                _require(_number(row["epoch_tdb_s"], body + " query epoch").hex() == hi.hex(),
                         body + " query epoch mismatch")
            for key, value in (("origin", "SSB"), ("orientation", "J2000"), ("aberration_correction", "NONE")):
                if key in row:
                    _require(row[key] == value, body + " source " + key)
        for key, expected in (("elapsed_s", float(operands["s"])), ("hi_tdb_s", hi), ("lo_s", lo)):
            if not is_geo or key in row:
                _require(_number(row.get(key), key).hex() == expected.hex(), "source/motion split epoch mismatch")
        raw[body] = _words(row.get("state_km_km_s"), 6, body + " raw state", binary64=is_geo)
        if not is_geo:
            si[body] = _words(row.get("state_si"), 6, body + " SI state")
            _require(_bits(si[body]) == _bits(tuple(x*1000 for x in raw[body])), "source SI conversion mismatch")
    return hi, lo, exact, raw, si


def assess_observation(initial: dict[str, Any], motion: dict[str, Any],
                       body_rows: dict[str, Any], geometry: dict[str, Any],
                       gm_m3_s2: dict[str, float], radii_m: dict[str, float],
                       consume: Event, check: Check = idle, *,
                       progress: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check one predetermined sample using three shared retained Type 2 records."""
    check()
    result = {} if progress is None else BASE._mapping(progress, "observation progress")
    _require(not result, "observation progress must start empty")
    _require(tuple(body_rows) == (*BODIES, MOON_EARTH) and tuple(geometry) == BODIES,
             "observation body/order mismatch")
    result.update(motion=assess_motion(initial, motion), bodies={}, sources={})
    _require(result["motion"]["passed"], "required motion assembly gate")
    operands = MOTION._motion_operands(initial, motion)
    hi, lo, exact, raw, si = _raw_states(body_rows, initial, operands)
    elapsed = _number(motion["elapsed_s"], "motion elapsed")
    v0 = _words(initial["velocity_m_s"], 3, "initial velocity")
    drift = _words(motion["drift_m"], 3, "saved drift")
    _require(_bits(drift) == _bits(tuple(_signed_product(v, elapsed) for v in v0)), "signed drift product")
    records = _record_templates(body_rows, Fraction(hi), exact)
    evaluated = _evaluate(records, Fraction(hi), exact, consume, check)
    centre_km = _vector(tuple(Fraction(e)+Fraction(g) for e, g in zip(
        raw["Earth"][:3], raw[MOON_EARTH][:3], strict=True)))
    split_si = _vector(tuple(1000*x for x in centre_km))

    prepared = {}
    for body in BODIES:
        check()
        consume("body_checks", "attempt")
        evidence = {"body": body}
        result["bodies"][body] = evidence
        chain = BASE.CHAINS[body]
        at_hi, at_time = (_chain(evaluated[epoch], chain) for epoch in (Fraction(hi), exact))
        assessment = _ssb_assessment(si[body], hi, lo, at_hi, at_time)
        evidence["source_assessment"] = assessment
        _require(assessment["passed"], "source parity/increment/Taylor gate: "+body)
        source = split_si if body == "Moon" else _vector(tuple(map(Fraction, si[body][:3])))
        prepared[body] = _geometry(body, geometry[body], assessment, source, at_hi, at_time, operands,
                                   radii_m[body], evidence)
        consume("body_checks", "complete")
        check()

    consume("moon_earth_checks", "attempt")
    geocentric = _moon_earth_parity(body_rows[MOON_EARTH], evaluated[Fraction(hi)][(301, 399)], hi)
    result["moon_earth"] = geocentric
    rounded = tuple(float(x) for x in centre_km)
    matches = [a == b for a, b in zip(_bits(rounded), _bits(raw["Moon"][:3]), strict=True)]
    geocentric["rounded_closure"] = {
        "split_km_hex": _bits(rounded), "direct_moon_ssb_km_hex": _bits(raw["Moon"][:3]),
        "position_matches": matches, "position_passed": all(matches),
    }
    _require(geocentric["passed"], "Moon/Earth state parity gate")
    consume("moon_earth_checks", "complete")
    check()

    # No field is evaluated until all three exterior guards and four source checks have passed.
    field_sets, scale_sets = {}, {}
    for body in INCLUDED:
        consume("source_rows", "attempt")
        check()
        gm = Fraction(_number(gm_m3_s2[body], "gm_m3_s2"))
        _require(gm > 0, "positive GM required")
        fields, scales = {}, {}
        result["sources"][body] = {"body": body, "raw_reference": {}}
        for p in BASE.PROFILES:
            key = str(p)
            fields[key], scales[key] = {}, {}
            raw_reference = result["sources"][body]["raw_reference"][key] = {}
            with localcontext() as context:
                context.prec = p
                context.rounding = ROUND_HALF_EVEN
                for name in BASE.GEOMETRIES:
                    check()
                    consume("reference_fields", "attempt")
                    fields[key][name] = BASE._field(prepared[body][name], gm)
                    raw_reference[name] = BASE._wire_vector(fields[key][name])
                    consume("reference_fields", "complete")
                    check()
                    scales[key][name] = BASE._norm(fields[key][name])
        assessed = HISTORICAL._assess_fields(fields, scales, geometry[body].get("acceleration_m_s2"))
        result["sources"][body].update(assessed)
        _require(assessed["passed"], "required force/precision/telescope gate: "+body)
        field_sets[body], scale_sets[body] = fields, scales
        consume("source_rows", "complete")
        check()
    consume("model_totals", "attempt")
    check()
    totals, total_scales = {}, {}
    for p in BASE.PROFILES:
        key = str(p)
        with localcontext() as context:
            context.prec = p
            context.rounding = ROUND_HALF_EVEN
            totals[key] = {k: BASE._sum_decimal([field_sets[b][key][k] for b in INCLUDED]) for k in BASE.GEOMETRIES}
            total_scales[key] = {k: sum((scale_sets[b][key][k] for b in INCLUDED), Decimal()) for k in BASE.GEOMETRIES}
    actual = [math.fsum(_number(geometry[b]["acceleration_m_s2"][j], "source acceleration")
                       for b in INCLUDED) for j in range(3)]
    result["A"] = HISTORICAL._assess_fields(totals, total_scales, actual)
    _require(result["A"]["passed"], "required force/precision/telescope gate: A")
    consume("model_totals", "complete")
    check()
    result["passed"] = True
    return result
