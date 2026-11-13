"""Private ADR0179 numeric candidate; scientific imports remain lazy."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from hashlib import sha256
import importlib.util
import math
from pathlib import Path
import sys
from time import monotonic
from typing import Any, Callable

BODIES = ("Sun", "Moon", "Earth")
REQUESTS = (*((body, "SSB") for body in BODIES), ("Moon", "Earth"))
OFFSETS = (0., 50., 100., 150., 200., 250., 300.)
LIMITS = {"rhs": 10000, "states": 40028, "trials": 1000, "binary64_fields": 20028,
          "dynamic_totals": 10014, "body_checks": 84, "source_rows": 56,
          "moon_earth_checks": 28, "record_evaluations": 168,
          "reference_fields": 448, "model_totals": 28, "native_guards": 42,
          "solves": 2, "initializations": 1, "identities": 2, "metadata": 30}
Provider = Callable[[str, float, str, str, str], Any]



def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def number(value: Any, name: str) -> float:
    require(type(value) in (int, float) and math.isfinite(value), name + ": finite nonboolean number")
    return float(value)


def vector(value: Any, size: int, name: str) -> list[float]:
    require(type(value) in (list, tuple) and len(value) == size, name + ": vector size")
    return [number(x, name) for x in value]


def split_epoch(epoch_tdb_s: float, elapsed_s: float) -> tuple[float, float]:
    a, b = number(epoch_tdb_s, "epoch"), number(elapsed_s, "elapsed")
    hi = a + b
    require(math.isfinite(hi), "epoch overflow")
    virtual = hi - a
    lo = (a - (hi - virtual)) + (b - virtual)
    require(math.isfinite(lo), "epoch low overflow")
    return hi, lo


def settings(name: str) -> dict[str, Any]:
    require(name in ("normal", "tighter"), "profile name")
    tight = name == "tighter"
    return {"rtol": 1e-13 if tight else 1e-12,
            "atol": [1e-8 if tight else 1e-7]*3 + [1e-11 if tight else 1e-10]*3,
            "max_step": 2.5 if tight else 5., "first_step": .5 if tight else 1.}


@dataclass(slots=True)
class Budget:
    clock: Callable[[], float] = monotonic
    start_s: float = field(default_factory=monotonic)
    duration_s: float = 60.
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    ledger: list[dict[str, Any]] = field(default_factory=list)

    def check(self) -> None:
        elapsed = number(self.clock(), "clock") - number(self.start_s, "start_s")
        require(0 <= elapsed < self.duration_s, "process deadline/clock")

    def event(self, operation: str, phase: str) -> None:
        require(operation in LIMITS and phase in ("attempt", "return", "complete"), "budget event")
        if phase == "attempt":
            self.check()
        c = self.counts.setdefault(operation, {"attempted": 0, "returned": 0, "completed": 0})
        if phase == "attempt":
            require(c["attempted"] < LIMITS[operation], operation + " attempt cap")
            c["attempted"] += 1
        else:
            key = "returned" if phase == "return" else "completed"
            require(c[key] < c["attempted"], operation + " unmatched " + phase)
            c[key] += 1
        self.ledger.append({"operation": operation, "phase": phase})
        self.check()


def assemble_motion(initial: dict[str, Any], s: float, correction: Any) -> dict[str, Any]:
    s = number(s, "elapsed_s")
    require(0 <= s <= 300, "elapsed_s outside [0,300]")
    y = vector(correction, 6, "correction")
    r0 = vector(initial["position_m"], 3, "r0")
    v0 = vector(initial["velocity_m_s"], 3, "v0")
    drift = [v*s for v in v0]
    x = [math.fsum((r0[j], drift[j], y[j])) for j in range(3)]
    v = [math.fsum((v0[j], y[j+3])) for j in range(3)]
    return {"elapsed_s": s, "q_m": y[:3], "w_m_s": y[3:], "drift_m": drift,
            "position_m": vector(x, 3, "position"), "velocity_m_s": vector(v, 3, "velocity")}


def state_words(item: dict[str, Any], body: str, observer: str, hi: float) -> list[float]:
    require((item["body"], item["observer"], item["frame"], item["aberration"])
            == (body, observer, "J2000", "NONE")
            and number(item["epoch_tdb_s"], "state epoch").hex() == hi.hex(),
            "state target/observer/frame/aberration/epoch mismatch")
    return vector(item["state_km_km_s"], 6, "raw state")


def split_separation(earth_km: list[float], moon_km: list[float], r0_m: list[float],
                     drift_m: list[float], q_m: list[float], c_m: list[float]
                     ) -> tuple[list[Fraction], list[float]]:
    """Round only the final Moon-to-spacecraft displacement in SI."""
    exact = [1000*(Fraction(e)+Fraction(g))+Fraction(c)-Fraction(r)-Fraction(d)-Fraction(q)
             for e, g, r, d, q, c in zip(earth_km, moon_km, r0_m, drift_m, q_m, c_m, strict=True)]
    return exact, vector([float(x) for x in exact], 3, "split Moon separation")


def build_row(initial: dict[str, Any], s: float, correction: Any,
              bodies: dict[str, Any], gm_m3_s2: dict[str, float], radii_m: dict[str, float],
              budget: Budget, row: dict[str, Any], *, moon_earth: dict[str, Any]) -> dict[str, Any]:
    """Guard all three relative geometries before either included force."""
    motion = assemble_motion(initial, s, correction)
    hi, lo = split_epoch(initial["epoch_tdb_s"], motion["elapsed_s"])
    row.update(elapsed_s=motion["elapsed_s"], hi_tdb_s=hi, lo_s=lo,
               correction=vector(correction, 6, "correction"), motion=motion, bodies=bodies, moon_earth=moon_earth, geometry={})
    require(tuple(bodies) == BODIES, "three ordered body returns required")
    g_km = state_words(moon_earth, "Moon", "Earth", hi)[:3]
    e_km = state_words(bodies["Earth"], "Earth", "SSB", hi)[:3]
    for body in BODIES:
        raw = bodies[body]
        words = state_words(raw, body, "SSB", hi)
        state = vector(raw["state_si"], 6, "body state_si")
        require([v.hex() for v in state] == [(v*1000).hex() for v in words], "raw/SI mismatch")
        c = vector([v*lo for v in state[3:]], 3, "signed rephasing")
        r0, drift, q = initial["position_m"], motion["drift_m"], motion["q_m"]
        if body == "Moon":
            exact, d = split_separation(e_km, g_km, r0, drift, q, c)
        else:
            d = [math.fsum((state[j], -r0[j], -drift[j], -q[j], c[j])) for j in range(3)]
        rho = math.hypot(*d)
        radius = number(radii_m[body], "guard radius")
        geometry = {"rephasing_m": c, "separation_m": d, "distance_m": rho}
        row["geometry"][body] = geometry
        if body == "Moon":
            geometry["pre_round_separation_m"] = [str(v) for v in exact]
            require(sum(v*v for v in exact) > Fraction(radius)**2, "exact exterior guard: Moon")
        require(math.isfinite(rho) and radius > 0 and rho > radius, "exterior guard: " + body)
    for body in BODIES[:2]:
        g = row["geometry"][body]
        budget.event("binary64_fields", "attempt")
        mu = number(gm_m3_s2[body], "mu")
        require(mu > 0, "positive GM")
        d, rho = g["separation_m"], g["distance_m"]
        square = rho*rho
        require(math.isfinite(square) and square > 0, "squared distance range")
        g["acceleration_m_s2"] = vector([mu*(di/rho)/square for di in d], 3, "force")
        budget.event("binary64_fields", "complete")
    budget.event("dynamic_totals", "attempt")
    a = [math.fsum(row["geometry"][b]["acceleration_m_s2"][j] for b in BODIES[:2]) for j in range(3)]
    row["derivative"] = vector(motion["w_m_s"] + a, 6, "derivative")
    budget.event("dynamic_totals", "complete")
    return row


def query_bodies(s: float, initial: dict[str, Any], provider: Provider, budget: Budget,
                 row: dict[str, Any], requests: list[dict[str, Any]]) -> dict[str, Any]:
    hi, lo = split_epoch(initial["epoch_tdb_s"], s)
    row.update(elapsed_s=s, hi_tdb_s=hi, lo_s=lo, bodies={})
    for body, observer in REQUESTS:
        request = {"body": body, "observer": observer, "frame": "J2000", "aberration": "NONE",
                   "epoch_tdb_s": hi}
        budget.event("states", "attempt")
        requests.append(request)
        raw = provider(body, hi, "J2000", "NONE", observer)
        # Retain the raw response before validation or the post-call deadline.
        item = {**request, "state_km_km_s": raw}
        if observer == "SSB":
            row["bodies"][body] = item
        else:
            row["moon_earth"] = item
        budget.event("states", "return")
        values = vector(raw, 6, "raw " + body + "/" + observer)
        if observer == "SSB":
            item["state_si"] = vector([v*1000 for v in values], 6, "SI " + body)
        budget.event("states", "complete")
    return row["bodies"]


def load_observer() -> Callable[..., Any]:
    """Reuse the unmodified, tested DOP853 observer."""
    path = Path(__file__).with_name("0163-corrected-integrator.py")
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == "fbc8411ca6d8ad3ebde72563d8b4134f9d5e2d2235e5441f945e4aa10873efed",
            "historical observer identity")
    spec = importlib.util.spec_from_file_location("ariadna_0163_observer", path)
    if spec is None or spec.loader is None:
        raise ValueError("historical observer loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module.observed_class


observed_class = load_observer()


def solve_profile(bundle: dict[str, Any], name: str, report: dict[str, Any],
                  provider: Provider, budget: Budget,
                  *, observed: bool = True) -> dict[str, Any]:
    from scipy.integrate import DOP853, solve_ivp

    budget.event("solves", "attempt")
    profile = {"name": name, "settings": settings(name), "rhs_start": len(report["rhs"]), "outputs": []}
    report["profiles"].append(profile)
    def rhs(s: float, y: Any) -> list[float]:
        budget.event("rhs", "attempt")
        row: dict[str, Any] = {"profile": name, "index": len(report["rhs"])-profile["rhs_start"],
                                "global_index": len(report["rhs"])}
        report["rhs"].append(row)
        s = number(float(s), "elapsed_s")
        require(0 <= s <= 300, "RHS time outside interval")
        row["correction"] = vector(y.tolist(), 6, "correction")
        bodies = query_bodies(s, bundle["initial"], provider, budget, row, report["state_requests"])
        build_row(bundle["initial"], s, row["correction"], bodies,
                  bundle["gm_m3_s2"], bundle["radii_m"], budget, row, moon_earth=row["moon_earth"])
        row["completed"] = True
        budget.event("rhs", "complete")
        return row["derivative"]
    method = observed_class(DOP853, report, profile, budget) if observed else "DOP853"
    result = solve_ivp(rhs, (0., 300.), [0.]*6, method=method, t_eval=OFFSETS, **profile["settings"])
    # Serialize all returned arrays before post-call deadline/completion checks.
    profile["raw_returned"] = {"success": bool(result.success), "status": int(result.status),
        "message": str(result.message), "t": result.t.tolist(), "y": result.y.tolist(), "nfev": int(result.nfev)}
    budget.event("solves", "return")
    raw = profile["raw_returned"]
    require(raw["success"] and raw["status"] == 0 and raw["t"] == list(OFFSETS), "incomplete solve")
    require(len(raw["y"]) == 6 and all(len(v) == 7 for v in raw["y"]), "returned array shape")
    require(raw["nfev"] == len(report["rhs"])-profile["rhs_start"], "RHS/nfev mismatch")
    for index, node in enumerate(report["node_table"]):
        row = {"profile": name, "index": index}
        profile["outputs"].append(row)
        build_row(bundle["initial"], OFFSETS[index], [v[index] for v in raw["y"]], node["bodies"],
                  bundle["gm_m3_s2"], bundle["radii_m"], budget, row, moon_earth=node["moon_earth"])
    budget.event("solves", "complete")
    return profile
