"""Independent ADR0182 force gates on the fixed B observation set."""

from __future__ import annotations

from collections.abc import Callable
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import importlib.util
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

REFERENCE_SHA256 = "8116ae56bcb1f6b9f0ae51c0fd28251bbf45eabb02420c03e0e832390a4bef91"
type Event = Callable[[str, str], None]
type Check = Callable[[], None]


def _load_reference() -> ModuleType:
    path = Path(__file__).with_name("0180-split-reference.py")
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != REFERENCE_SHA256:
        raise ValueError("immutable split reference SHA256 mismatch")
    spec = importlib.util.spec_from_file_location("ariadna_r536_split_reference", path)
    if spec is None:
        raise ValueError("immutable split reference loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


SPLIT = _load_reference()
BASE, HISTORICAL, MOTION = SPLIT.BASE, SPLIT.HISTORICAL, SPLIT.MOTION
BODIES, MOON_EARTH = SPLIT.BODIES, SPLIT.MOON_EARTH
assess_motion, compare_states, idle = SPLIT.assess_motion, SPLIT.compare_states, SPLIT.idle


def assess_observation(initial: dict[str, Any], motion: dict[str, Any],
                       body_rows: dict[str, Any], geometry: dict[str, Any],
                       gm_m3_s2: dict[str, float], radii_m: dict[str, float],
                       consume: Event, check: Check = idle, *,
                       progress: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check one predetermined sample using three shared retained Type 2 records."""
    check()
    result = {} if progress is None else BASE._mapping(progress, "observation progress")
    SPLIT._require(not result, "observation progress must start empty")
    SPLIT._require(tuple(body_rows) == (*BODIES, MOON_EARTH) and tuple(geometry) == BODIES,
             "observation body/order mismatch")
    result.update(motion=assess_motion(initial, motion), bodies={}, sources={})
    SPLIT._require(result["motion"]["passed"], "required motion assembly gate")
    operands = MOTION._motion_operands(initial, motion)
    hi, lo, exact, raw, si = SPLIT._raw_states(body_rows, initial, operands)
    elapsed = SPLIT._number(motion["elapsed_s"], "motion elapsed")
    v0 = SPLIT._words(initial["velocity_m_s"], 3, "initial velocity")
    drift = SPLIT._words(motion["drift_m"], 3, "saved drift")
    SPLIT._require(SPLIT._bits(drift) == SPLIT._bits(tuple(SPLIT._signed_product(v, elapsed) for v in v0)), "signed drift product")
    records = SPLIT._record_templates(body_rows, Fraction(hi), exact)
    evaluated = SPLIT._evaluate(records, Fraction(hi), exact, consume, check)
    centre_km = SPLIT._vector(tuple(Fraction(e)+Fraction(g) for e, g in zip(
        raw["Earth"][:3], raw[MOON_EARTH][:3], strict=True)))
    split_si = SPLIT._vector(tuple(1000*x for x in centre_km))

    prepared = {}
    for body in BODIES:
        check()
        consume("body_checks", "attempt")
        evidence = {"body": body}
        result["bodies"][body] = evidence
        chain = BASE.CHAINS[body]
        at_hi, at_time = (SPLIT._chain(evaluated[epoch], chain) for epoch in (Fraction(hi), exact))
        assessment = SPLIT._ssb_assessment(si[body], hi, lo, at_hi, at_time)
        evidence["source_assessment"] = assessment
        SPLIT._require(assessment["passed"], "source parity/increment/Taylor gate: "+body)
        source = split_si if body == "Moon" else SPLIT._vector(tuple(map(Fraction, si[body][:3])))
        prepared[body] = SPLIT._geometry(body, geometry[body], assessment, source, at_hi, at_time, operands,
                                   radii_m[body], evidence)
        consume("body_checks", "complete")
        check()

    consume("moon_earth_checks", "attempt")
    geocentric = SPLIT._moon_earth_parity(body_rows[MOON_EARTH], evaluated[Fraction(hi)][(301, 399)], hi)
    result["moon_earth"] = geocentric
    rounded = tuple(float(x) for x in centre_km)
    matches = [a == b for a, b in zip(SPLIT._bits(rounded), SPLIT._bits(raw["Moon"][:3]), strict=True)]
    geocentric["rounded_closure"] = {
        "split_km_hex": SPLIT._bits(rounded), "direct_moon_ssb_km_hex": SPLIT._bits(raw["Moon"][:3]),
        "position_matches": matches, "position_passed": all(matches),
    }
    SPLIT._require(geocentric["passed"], "Moon/Earth state parity gate")
    consume("moon_earth_checks", "complete")
    check()

    # No field is evaluated until all three exterior guards and four source checks have passed.
    field_sets, scale_sets = {}, {}
    for body in BODIES:
        consume("source_rows", "attempt")
        check()
        gm = Fraction(SPLIT._number(gm_m3_s2[body], "gm_m3_s2"))
        SPLIT._require(gm > 0, "positive GM required")
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
        SPLIT._require(assessed["passed"], "required force/precision/telescope gate: "+body)
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
            totals[key] = {k: BASE._sum_decimal([field_sets[b][key][k] for b in BODIES]) for k in BASE.GEOMETRIES}
            total_scales[key] = {k: sum((scale_sets[b][key][k] for b in BODIES), Decimal()) for k in BASE.GEOMETRIES}
    actual = [math.fsum(SPLIT._number(geometry[b]["acceleration_m_s2"][j], "source acceleration")
                       for b in BODIES) for j in range(3)]
    result["B"] = HISTORICAL._assess_fields(totals, total_scales, actual)
    SPLIT._require(result["B"]["passed"], "required force/precision/telescope gate: B")
    consume("model_totals", "complete")
    check()
    result["passed"] = True
    return result
