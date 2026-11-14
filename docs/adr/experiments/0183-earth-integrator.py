"""Private ADR0182 model B DOP853 path with four direct state routes."""

from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable

Row = dict[str, Any]
Provider = Callable[[str, float, str, str, str], Any]


def _load_split() -> ModuleType:
    path = Path(__file__).with_name("0180-split-integrator.py")
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != "e728b272fa66c2e4ea801ec3996d0def71e2f6a423b6698019a46882201861d5":
        raise ValueError("frozen split integrator identity")
    module = ModuleType("ariadna_0183_frozen_split")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


_split = _load_split()
BODIES = _split.BODIES
REQUESTS = _split.REQUESTS
OFFSETS = _split.OFFSETS
LIMITS: dict[str, int] = {
    **{key: cap for key, cap in _split.LIMITS.items() if key != "native_guards"},
    "binary64_fields": 30042,
    "source_rows": 84,
    "reference_fields": 672,
    "native_arcs": 2,
    "native_guard_reads": 2712,
    "native_reference_fields": 84,
    "native_telemetry": 14,
}
require = _split.require
number = _split.number
vector = _split.vector
settings = _split.settings
split_epoch = _split.split_epoch
query_bodies = _split.query_bodies


class Budget(_split.Budget):
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


def _field(gm_m3_s2: float, separation_m: list[float], distance_m: float) -> list[float]:
    """Compute direct point gravity from the guarded body-minus-spacecraft vector."""
    mu = number(gm_m3_s2, "mu")
    require(mu > 0, "positive GM")
    square = distance_m * distance_m
    require(math.isfinite(square) and square > 0, "squared distance range")
    return vector([mu * (di / distance_m) / square for di in separation_m], 3, "force")


def build_row(initial: Row, s: float, correction: object, bodies: dict[str, Row],
              gm_m3_s2: dict[str, float], radii_m: dict[str, float], budget: Budget,
              row: Row, *, moon_earth: Row) -> Row:
    """Keep the A geometry and add Earth's direct field in SSB axes."""
    motion = _split.assemble_motion(initial, s, correction)
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
        part["acceleration_m_s2"] = _field(gm_m3_s2[body], part["separation_m"], part["distance_m"])
        budget.event("binary64_fields", "complete")
    budget.event("dynamic_totals", "attempt")
    a = [math.fsum(geometry[b]["acceleration_m_s2"][j] for b in BODIES) for j in range(3)]
    row["derivative"] = vector(motion["w_m_s"] + a, 6, "derivative")
    budget.event("dynamic_totals", "complete")
    return row


def fill_node_table(bundle: Row, report: Row, provider: Provider, budget: Budget) -> None:
    """Acquire the seven shared nodes once, in frozen order."""
    require(not report["node_table"], "shared node table already started")
    require(type(bundle["offsets_s"]) is list and vector(bundle["offsets_s"], 7, "offsets") == list(OFFSETS),
            "shared node offsets")
    for s in OFFSETS:
        row: Row = {}
        report["node_table"].append(row)
        query_bodies(s, bundle["initial"], provider, budget, row, report["state_requests"])


def solve_profile(bundle: Row, name: str, report: Row, provider: Provider, budget: Budget,
                  *, observed: bool = True) -> Row:
    """Integrate correction variables and preserve B RHS and output operands."""
    from scipy.integrate import DOP853, solve_ivp

    require(len(report["node_table"]) == 7 and
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
        require(0 <= s <= 300, "RHS time outside interval")
        row["correction"] = vector(y.tolist(), 6, "correction")
        query_bodies(s, bundle["initial"], provider, budget, row, report["state_requests"])
        build(s, row["correction"], row, row)
        row["completed"] = True
        budget.event("rhs", "complete")
        return row["derivative"]

    method = _split.observed_class(DOP853, report, profile, budget) if observed else "DOP853"
    result = solve_ivp(rhs, (0., 300.), [0.] * 6, method=method, t_eval=OFFSETS, **profile_settings)
    raw = profile["raw_returned"] = {"success": bool(result.success), "status": int(result.status),
        "message": str(result.message), "t": result.t.tolist(), "y": result.y.tolist(), "nfev": int(result.nfev)}
    budget.event("solves", "return")
    require(raw["success"] and raw["status"] == 0 and raw["t"] == list(OFFSETS), "incomplete solve")
    require(len(raw["y"]) == 6 and all(len(v) == 7 for v in raw["y"]), "returned array shape")
    require(raw["nfev"] == len(report["rhs"]) - profile["rhs_start"], "RHS/nfev mismatch")
    for index, node in enumerate(report["node_table"]):
        row = {"profile": name, "index": index}
        profile["outputs"].append(row)
        build(OFFSETS[index], [v[index] for v in raw["y"]], node, row)
    budget.event("solves", "complete")
    return profile
