"""Independent saved-operand checks for ADR0162; SI/SSB/J2000/TDB/NONE.

Only pinned pure references are reused. Solver q/w are actual binary64 inputs,
not prescribed motion or a bound on integration error. Import evaluates no field.
"""
from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from hashlib import sha256
import importlib.util
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

HISTORICAL_PATH = Path(__file__).with_name("0160-moving-reference.py")
HISTORICAL_SHA256 = "3562d4aa1bc2a41d546520ffbd1a1bc67169fe8b77718ec1a808ecc43132bde6"
BODIES = ("Sun", "Moon", "Earth")
INCLUDED = BODIES[:2]
CONTRIBUTIONS = ("native_source", "rephasing_and_drift", "relative_assembly", "field_evaluation")


def _load_historical() -> ModuleType:
    raw = HISTORICAL_PATH.read_bytes()
    if sha256(raw).hexdigest() != HISTORICAL_SHA256:
        raise ValueError("immutable reference SHA256 mismatch")
    spec = importlib.util.spec_from_file_location("ariadna_0163_motion_primitives", HISTORICAL_PATH)
    if spec is None or spec.loader is None:
        raise ValueError("immutable reference loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(HISTORICAL_PATH), "exec"), module.__dict__)
    return module


MOTION = _load_historical()
BASE = MOTION.BASE
ORACLE = BASE.ORACLE


def idle() -> None:
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def assess_motion(initial: dict[str, Any], motion: dict[str, Any]) -> dict[str, Any]:
    """Bound assembly of actual q/w operands, without an ideal-correction claim."""
    o = MOTION._motion_operands(initial, motion)
    gates: dict[str, Any] = {name: [] for name in ("drift_product", "position_sum", "velocity_sum")}
    for j in range(3):
        gates["drift_product"].append(MOTION._round_gate(motion["drift_m"][j], o["exact_drift"][j], "m"))
        gates["position_sum"].append(MOTION._sum_gate(
            motion["position_m"][j], o["exact_position"][j],
            MOTION._ulp(motion["drift_m"][j])/2 + MOTION._ulp(motion["position_m"][j]),
            o["r0"][j]+o["drift"][j]+o["q"][j], "m"))
        gates["velocity_sum"].append(MOTION._sum_gate(
            motion["velocity_m_s"][j], o["exact_velocity"][j],
            MOTION._ulp(motion["velocity_m_s"][j]), o["exact_velocity"][j], "m/s"))
    return {"component_gates": gates, "passed": all(g["passed"] for values in gates.values() for g in values),
            "q_w_scope": "actual binary64 solver operands; truncation accuracy unverified"}


def compare_states(left: object, right: object, position_limit_m: float,
                   velocity_limit_m_s: float) -> dict[str, Any]:
    """Compare Cartesian six-states using exact squared norms and SI limits."""
    vectors = []
    for name, value in (("left", left), ("right", right)):
        _require(isinstance(value, (list, tuple)) and len(value) == 6, name+": expected six-state")
        vectors.append(tuple(Fraction.from_float(BASE._number(x, name)) for x in value))
    pl = Fraction.from_float(BASE._number(position_limit_m, "position_limit_m"))
    vl = Fraction.from_float(BASE._number(velocity_limit_m_s, "velocity_limit_m_s"))
    _require(pl > 0 and vl > 0, "positive comparison limits required")
    delta = tuple(x-y for x, y in zip(*vectors, strict=True))
    ps = sum((x*x for x in delta[:3]), Fraction())
    vs = sum((x*x for x in delta[3:]), Fraction())
    with localcontext() as context:
        context.prec = 100
        return {"position_error_m": str(BASE._decimal(ps).sqrt()),
                "velocity_error_m_s": str(BASE._decimal(vs).sqrt()),
                "position_limit_m": float(pl), "velocity_limit_m_s": float(vl),
                "position_passed": ps <= pl*pl, "velocity_passed": vs <= vl*vl,
                "passed": ps <= pl*pl and vs <= vl*vl}


def _source(row: dict[str, Any], initial: dict[str, Any], motion: dict[str, Any],
            geometry: dict[str, Any], body: str, radius: float,
            *, progress: dict[str, Any] | None = None) -> dict[str, Any]:
    """Rebuild source and all four exact geometries before any reference field."""
    target = {} if progress is None else progress
    row = BASE._mapping(row, "source row")
    _require(row.get("body") == body, "source body/order mismatch")
    o = MOTION._motion_operands(initial, motion)
    s = Fraction.from_float(BASE._number(row.get("elapsed_s"), "source elapsed_s"))
    hi, lo = (BASE._number(row.get(k), k) for k in ("hi_tdb_s", "lo_s"))
    t = Fraction.from_float(BASE._number(initial.get("epoch_tdb_s"), "initial epoch"))+s
    _require(s == o["s"] and Fraction(hi)+Fraction(lo) == t and hi == float(t), "source/motion split epoch mismatch")
    raw, si = row.get("state_km_km_s"), row.get("state_si")
    _require(isinstance(raw, (list, tuple)) and len(raw) == 6 and isinstance(si, (list, tuple)) and len(si) == 6,
             "source state: expected six raw and SI components")
    raw = [BASE._number(x, "raw state") for x in raw]
    si = [BASE._number(x, "SI state") for x in si]
    _require(si == [x*1000 for x in raw], "source SI conversion mismatch")
    segments = row.get("segments")
    _require(type(segments) is list and len(segments) == len(BASE.CHAINS[body]), "source centre chain mismatch")
    records = []
    for seg, expected in zip(segments, BASE.CHAINS[body], strict=True):
        seg = BASE._mapping(seg, "source segment")
        metadata = tuple(seg.get(k) for k in ("body", "centre", "frame", "type"))
        _require(all(type(x) is int for x in metadata) and metadata == (*expected, 1, 2),
                 "source body/centre/frame/type mismatch")
        first = Fraction(BASE._number(seg.get("first_tdb_s"), "segment first"))
        last = Fraction(BASE._number(seg.get("last_tdb_s"), "segment last"))
        _require(first <= min(Fraction(hi), t) <= max(Fraction(hi), t) <= last, "source segment coverage")
        records.append(ORACLE.parse_record(seg.get("words")))
    source_assessment = ORACLE.assess(si, records, hi, lo)
    target["source_assessment"] = source_assessment
    _require(source_assessment["passed"], "source parity/increment/Taylor gate")
    p_hi, _, _ = ORACLE.evaluate_chain(records, Fraction(hi))
    p_time, _, _ = ORACLE.evaluate_chain(records, t)
    b = BASE._exact_vector(si[:3], "native position")
    c = BASE._exact_vector(geometry.get("rephasing_m"), "source rephasing")
    d = BASE._exact_vector(geometry.get("separation_m"), "source separation")
    e_b = tuple(b[j]-p_hi[j] for j in range(3))
    ds = {"d0": tuple(p_time[j]-o["exact_position"][j] for j in range(3)),
          "d1": tuple(p_time[j]+e_b[j]-o["exact_position"][j] for j in range(3)),
          "d2": tuple(b[j]+c[j]-o["r0"][j]-o["drift"][j]-o["q"][j] for j in range(3)),
          "d3": d}
    relative = [MOTION._sum_gate(geometry["separation_m"][j], ds["d2"][j],
                                MOTION._ulp(geometry["separation_m"][j]), ds["d2"][j], "m") for j in range(3)]
    rephase = [MOTION._round_gate(geometry["rephasing_m"][j], Fraction(si[j+3])*Fraction(lo), "m") for j in range(3)]
    increment = tuple(c[j]-(p_time[j]-p_hi[j]) for j in range(3))
    drift_error = tuple(o["drift"][j]-o["exact_drift"][j] for j in range(3))
    identity = all(ds["d2"][j]-ds["d1"][j] == increment[j]-drift_error[j] for j in range(3))
    rr = Fraction(BASE._number(radius, "radius_m"))
    _require(rr > 0, "positive radius required")
    domains = {name: sum((x*x for x in vec), Fraction()) > rr*rr for name, vec in ds.items()}
    target.update(component_gates={"relative_sum": relative, "rephasing_product": rephase},
                  geometry_error_identity=identity, domain_guards=domains,
                  exact_geometries_m={k: BASE._encoded(v) for k, v in ds.items()})
    _require(all(domains.values()), "source exterior-domain guard: "+body)
    _require(identity and all(x["passed"] for x in relative+rephase), "required relative assembly/RN-product gate")
    return {"body": body, "source_assessment": source_assessment, "geometries": ds,
            "component_gates": {"relative_sum": relative, "rephasing_product": rephase},
            "geometry_error_identity": identity, "domain_guards": domains,
            "exact_geometries_m": {k: BASE._encoded(v) for k, v in ds.items()}}


def _assess_fields(fields: dict[str, Any], scales: dict[str, Any], candidate: object) -> dict[str, Any]:
    candidate = BASE._exact_vector(candidate, "candidate acceleration")
    references, contributions, gates, telescope = {}, {}, {}, {}
    for p in BASE.PROFILES:
        key = str(p)
        with localcontext() as context:
            context.prec = p
            context.rounding = ROUND_HALF_EVEN
            f = fields[key]
            a = tuple(BASE._decimal(x) for x in candidate)
            errors = (BASE._subtract(f["d1"], f["d0"]), BASE._subtract(f["d2"], f["d1"]),
                      BASE._subtract(f["d3"], f["d2"]), BASE._subtract(a, f["d3"]))
            residual = BASE._subtract(BASE._sum_decimal(errors), BASE._subtract(a, f["d0"]))
            error_norm = BASE._norm(residual)
            limit = BASE.PRECISION_RELATIVE*sum(scales[key].values(), Decimal())
            telescope[key] = {"residual_m_s2": BASE._wire_vector(residual), "error_norm_m_s2": str(error_norm),
                              "limit_m_s2": str(limit), "passed": error_norm <= limit}
            references[key] = {k: BASE._wire_vector(f[k]) for k in BASE.GEOMETRIES}
            contributions[key] = {k: BASE._wire_vector(v) for k, v in zip(CONTRIBUTIONS, errors, strict=True)}
            gates[key] = {"returned_geometry": BASE._gate(a, f["d3"], scales[key]["d3"]),
                          "overall": BASE._gate(a, f["d0"], scales[key]["d0"])}
    with localcontext() as context:
        context.prec = 100
        differences = {}
        for k in BASE.GEOMETRIES:
            low, high = fields["80"][k], fields["100"][k]
            difference = BASE._norm(BASE._subtract(low, high))
            limit = BASE.PRECISION_RELATIVE*scales["100"][k]
            zero = (BASE._norm(low) == 0) == (BASE._norm(high) == 0)
            differences[k] = {"difference_norm_m_s2": str(difference), "limit_m_s2": str(limit),
                              "zero_preserved": zero, "passed": zero and difference <= limit}
    stable = all(gates["80"][k]["passed"] == gates["100"][k]["passed"] for k in ("returned_geometry", "overall"))
    precision = stable and all(v["passed"] for v in differences.values())
    return {"reference": references, "reference_norms_m_s2": {p: {k: str(v) for k, v in row.items()} for p, row in scales.items()},
            "contributions_m_s2": contributions, "gates": gates, "telescope": telescope,
            "precision": {"reference_fields": differences, "gate_classifications_stable": stable, "passed": precision},
            "passed": precision and all(v["passed"] for v in telescope.values())
            and all(v["passed"] for row in gates.values() for v in row.values())}


def assess_observation(initial: dict[str, Any], motion: dict[str, Any],
                       body_rows: dict[str, Any], geometry: dict[str, Any],
                       gm_m3_s2: dict[str, float], radii_m: dict[str, float],
                       consume: Callable[[str, str], None], check: Callable[[], None] = idle,
                       *, progress: dict[str, Any] | None = None) -> dict[str, Any]:
    """Qualify one predetermined sample; no additional runtime source/force arms."""
    check()
    result = {} if progress is None else BASE._mapping(progress, "observation progress")
    _require(not result, "observation progress must start empty")
    _require(tuple(body_rows) == BODIES and tuple(geometry) == BODIES, "observation body/order mismatch")
    result.update(motion=assess_motion(initial, motion), bodies={}, sources={})
    _require(result["motion"]["passed"], "required motion assembly gate")
    prepared = {}
    for body in BODIES:
        check()
        consume("body_checks", "attempt")
        result["bodies"][body] = {"body": body}
        prepared[body] = _source(body_rows[body], initial, motion, geometry[body], body, radii_m[body],
                                 progress=result["bodies"][body])
        result["bodies"][body].update({k: v for k, v in prepared[body].items() if k != "geometries"})
        consume("body_checks", "complete")
        check()
    # Every body's reference geometry, including Earth, is guarded before fields.
    field_sets, scale_sets = {}, {}
    for body in INCLUDED:
        consume("source_rows", "attempt")
        check()
        gm = Fraction(BASE._number(gm_m3_s2[body], "gm_m3_s2"))
        _require(gm > 0, "positive GM required")
        fields, scales = {}, {}
        result["sources"][body] = {"body": body, "raw_reference": {}}
        for p in BASE.PROFILES:
            key = str(p)
            fields[key], scales[key] = {}, {}
            result["sources"][body]["raw_reference"][key] = {}
            with localcontext() as context:
                context.prec = p
                context.rounding = ROUND_HALF_EVEN
                for name in BASE.GEOMETRIES:
                    check()
                    consume("reference_fields", "attempt")
                    fields[key][name] = BASE._field(prepared[body]["geometries"][name], gm)
                    result["sources"][body]["raw_reference"][key][name] = BASE._wire_vector(fields[key][name])
                    consume("reference_fields", "complete")
                    check()
                    scales[key][name] = BASE._norm(fields[key][name])
        assessed = _assess_fields(fields, scales, geometry[body].get("acceleration_m_s2"))
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
    actual = [math.fsum(BASE._number(geometry[b]["acceleration_m_s2"][j], "source acceleration") for b in INCLUDED) for j in range(3)]
    result["A"] = _assess_fields(totals, total_scales, actual)
    _require(result["A"]["passed"], "required force/precision/telescope gate: A")
    consume("model_totals", "complete")
    check()
    result["passed"] = True
    return result
