"""Private ADR0185 model B DOP853 integration on the fixed 600 s coast."""

from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction
from hashlib import sha256
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

type Row = dict[str, Any]
type Provider = Callable[[str, float, str, str, str], object]

DURATION_S = 600.
OFFSETS = tuple(float(s) for s in range(0, 601, 50))


def _load_b() -> ModuleType:
    path = Path(__file__).with_name("0183-earth-integrator.py")
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != "f54b7b2f96034448f835e8d2f0d630278ac8c61a6d1e55b28c26e7e0c0162068":
        raise ValueError("frozen B integrator identity")
    module = ModuleType("ariadna_0186_b_primitives")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


_b = _load_b()
_split = _b._split
BODIES, REQUESTS = _b.BODIES, _b.REQUESTS
require, number, vector, settings = _b.require, _b.number, _b.vector, _b.settings
split_epoch, query_bodies = _b.split_epoch, _b.query_bodies
LIMITS: dict[str, int] = {
    **_b.LIMITS,
    "states": 40052,
    "binary64_fields": 30078,
    "dynamic_totals": 10026,
    "body_checks": 156,
    "moon_earth_checks": 52,
    "source_rows": 156,
    "reference_fields": 1248,
    "model_totals": 52,
    "record_evaluations": 312,
    "native_guard_reads": 5412,
    "native_reference_fields": 156,
    "native_telemetry": 26,
}


class Budget(_b.Budget):
    """Use one clock and one ordered ledger for all model B work."""

    __slots__ = ()

    def event(self, operation: str, phase: str) -> None:
        require(operation in LIMITS and phase in ("attempt", "return", "complete"), "budget event")
        if phase == "attempt":
            self.check()
        count = self.counts.setdefault(operation, {"attempted": 0, "returned": 0, "completed": 0})
        if phase == "attempt":
            require(count["attempted"] < LIMITS[operation], operation + " attempt cap")
            count["attempted"] += 1
        else:
            key = "returned" if phase == "return" else "completed"
            require(count[key] < count["attempted"], operation + " unmatched " + phase)
            count[key] += 1
        self.ledger.append({"operation": operation, "phase": phase})
        self.check()


def assemble_motion(initial: Row, s: float, correction: object) -> Row:
    """Assemble actual DOP853 corrections without impeding the longer grid."""
    s = number(s, "elapsed_s")
    require(0 <= s <= DURATION_S, "elapsed_s outside [0,600]")
    y = vector(correction, 6, "correction")
    r0 = vector(initial["position_m"], 3, "r0")
    v0 = vector(initial["velocity_m_s"], 3, "v0")
    drift = [v*s for v in v0]
    x = [math.fsum((r0[j], drift[j], y[j])) for j in range(3)]
    v = [math.fsum((v0[j], y[j+3])) for j in range(3)]
    return {"elapsed_s": s, "q_m": y[:3], "w_m_s": y[3:], "drift_m": drift,
            "position_m": vector(x, 3, "position"), "velocity_m_s": vector(v, 3, "velocity")}


def build_row(initial: Row, s: float, correction: object, bodies: dict[str, Row],
              gm_m3_s2: dict[str, float], radii_m: dict[str, float], budget: Budget,
              row: Row, *, moon_earth: Row) -> Row:
    """Apply the original Sun/Moon/Earth point fields in SSB axes."""
    motion = assemble_motion(initial, s, correction)
    hi, lo = split_epoch(initial["epoch_tdb_s"], motion["elapsed_s"])
    geometry: dict[str, Row] = {}
    row.update(elapsed_s=motion["elapsed_s"], hi_tdb_s=hi, lo_s=lo,
               correction=vector(correction, 6, "correction"), motion=motion,
               bodies=bodies, moon_earth=moon_earth, geometry=geometry)
    require(tuple(bodies) == BODIES, "three ordered body returns required")
    moon_km = _split.state_words(moon_earth, "Moon", "Earth", hi)[:3]
    earth_km = _split.state_words(bodies["Earth"], "Earth", "SSB", hi)[:3]
    r0, drift, q = initial["position_m"], motion["drift_m"], motion["q_m"]
    for body in BODIES:
        raw = bodies[body]
        words = _split.state_words(raw, body, "SSB", hi)
        state = vector(raw["state_si"], 6, "body state_si")
        require([v.hex() for v in state] == [(v * 1000).hex() for v in words], "raw/SI mismatch")
        c = vector([v * lo for v in state[3:]], 3, "signed rephasing")
        if body == "Moon":
            exact, separation = _split.split_separation(earth_km, moon_km, r0, drift, q, c)
        else:
            separation = [math.fsum((state[j], -r0[j], -drift[j], -q[j], c[j])) for j in range(3)]
        rho = math.hypot(*separation)
        radius = number(radii_m[body], "guard radius")
        part = geometry[body] = {"rephasing_m": c, "separation_m": separation, "distance_m": rho}
        if body == "Moon":
            part["pre_round_separation_m"] = [str(v) for v in exact]
            require(sum(v * v for v in exact) > Fraction(radius)**2, "exact exterior guard: Moon")
        require(math.isfinite(rho) and radius > 0 and rho > radius, "exterior guard: " + body)
    for body, part in geometry.items():
        budget.event("binary64_fields", "attempt")
        part["acceleration_m_s2"] = _b._field(gm_m3_s2[body], part["separation_m"], part["distance_m"])
        budget.event("binary64_fields", "complete")
    budget.event("dynamic_totals", "attempt")
    a = [math.fsum(geometry[b]["acceleration_m_s2"][j] for b in BODIES) for j in range(3)]
    row["derivative"] = vector(motion["w_m_s"] + a, 6, "derivative")
    budget.event("dynamic_totals", "complete")
    return row


def fill_node_table(bundle: Row, report: Row, provider: Provider, budget: Budget) -> None:
    """Acquire all 13 shared nodes once, in frozen order."""
    require(not report["node_table"], "shared node table already started")
    require(type(bundle["offsets_s"]) is list and vector(bundle["offsets_s"], len(OFFSETS), "offsets") == list(OFFSETS),
            "shared node offsets")
    for s in OFFSETS:
        row: Row = {}
        report["node_table"].append(row)
        query_bodies(s, bundle["initial"], provider, budget, row, report["state_requests"])


def solve_profile(bundle: Row, name: str, report: Row, provider: Provider, budget: Budget,
                  *, observed: bool = True) -> Row:
    """Integrate correction variables and preserve B RHS and output operands."""
    from scipy.integrate import DOP853, solve_ivp

    require(len(report["node_table"]) == len(OFFSETS) and
            [row.get("elapsed_s") for row in report["node_table"]] == list(OFFSETS), "shared node table")
    profile_settings = settings(name)
    budget.event("solves", "attempt")
    profile = {"name": name, "settings": profile_settings, "rhs_start": len(report["rhs"]), "outputs": []}
    report["profiles"].append(profile)

    def build(s: float, y: list[float], node: Row, row: Row) -> None:
        build_row(bundle["initial"], s, y, node["bodies"],
                  bundle["gm_m3_s2"], bundle["radii_m"], budget, row, moon_earth=node["moon_earth"])

    def rhs(s: float, y: Any) -> list[float]:
        budget.event("rhs", "attempt")
        index = len(report["rhs"])
        row: Row = {"profile": name, "index": index - profile["rhs_start"], "global_index": index}
        report["rhs"].append(row)
        s = number(float(s), "elapsed_s")
        require(0 <= s <= DURATION_S, "RHS time outside interval")
        row["correction"] = vector(y.tolist(), 6, "correction")
        query_bodies(s, bundle["initial"], provider, budget, row, report["state_requests"])
        build(s, row["correction"], row, row)
        row["completed"] = True
        budget.event("rhs", "complete")
        return row["derivative"]

    method = _split.observed_class(DOP853, report, profile, budget) if observed else "DOP853"
    result = solve_ivp(rhs, (0., DURATION_S), [0.] * 6, method=method, t_eval=OFFSETS, **profile_settings)
    raw = profile["raw_returned"] = {"success": bool(result.success), "status": int(result.status),
        "message": str(result.message), "t": result.t.tolist(), "y": result.y.tolist(), "nfev": int(result.nfev)}
    budget.event("solves", "return")
    require(raw["success"] and raw["status"] == 0 and raw["t"] == list(OFFSETS), "incomplete solve")
    require(len(raw["y"]) == 6 and all(len(v) == len(OFFSETS) for v in raw["y"]), "returned array shape")
    require(raw["nfev"] == len(report["rhs"]) - profile["rhs_start"], "RHS/nfev mismatch")
    for index, node in enumerate(report["node_table"]):
        row = {"profile": name, "index": index}
        profile["outputs"].append(row)
        build(OFFSETS[index], [v[index] for v in raw["y"]], node, row)
    budget.event("solves", "complete")
    return profile
