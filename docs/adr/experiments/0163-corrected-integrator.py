"""Private ADR0162 numeric candidate; scientific imports remain lazy."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from time import monotonic
from typing import Any, Callable

BODIES = ("Sun", "Moon", "Earth")
OFFSETS = (0., 50., 100., 150., 200., 250., 300.)
LIMITS = {"rhs": 10000, "states": 30021, "trials": 1000, "binary64_fields": 20028,
          "dynamic_totals": 10014, "body_checks": 84, "source_rows": 56,
          "reference_fields": 448, "model_totals": 28, "native_guards": 42,
          "solves": 2, "initializations": 1, "identities": 2, "metadata": 30}
Check = Callable[[], None]


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


def build_row(initial: dict[str, Any], s: float, correction: Any,
              bodies: dict[str, Any], gm_m3_s2: dict[str, float], radii_m: dict[str, float],
              budget: Budget, row: dict[str, Any]) -> dict[str, Any]:
    """Guard all three relative geometries before either included force."""
    motion = assemble_motion(initial, s, correction)
    hi, lo = split_epoch(initial["epoch_tdb_s"], motion["elapsed_s"])
    row.update(elapsed_s=motion["elapsed_s"], hi_tdb_s=hi, lo_s=lo,
               correction=vector(correction, 6, "correction"), motion=motion, bodies=bodies, geometry={})
    require(tuple(bodies) == BODIES, "three ordered body returns required")
    for body in BODIES:
        raw = bodies[body]
        require(raw["body"] == body and raw["epoch_tdb_s"] == hi, "body/epoch mismatch")
        state = vector(raw["state_si"], 6, "body state_si")
        require(state == [v*1000 for v in vector(raw["state_km_km_s"], 6, "raw state")], "raw/SI mismatch")
        c = [v*lo for v in state[3:]]
        d = [math.fsum((state[j], -initial["position_m"][j], -motion["drift_m"][j],
                       -motion["q_m"][j], c[j])) for j in range(3)]
        rho = math.hypot(*d)
        radius = number(radii_m[body], "guard radius")
        row["geometry"][body] = {"rephasing_m": c, "separation_m": d, "distance_m": rho}
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


def query_bodies(s: float, initial: dict[str, Any], provider: Callable[[str, float], Any],
                 budget: Budget, row: dict[str, Any]) -> dict[str, Any]:
    hi, lo = split_epoch(initial["epoch_tdb_s"], s)
    row.update(elapsed_s=s, hi_tdb_s=hi, lo_s=lo, bodies={})
    for body in BODIES:
        budget.event("states", "attempt")
        raw = provider(body, hi)
        # Keep even invalid/late returned values before checking the deadline.
        item = {"body": body, "epoch_tdb_s": hi, "state_km_km_s": raw}
        row["bodies"][body] = item
        budget.event("states", "return")
        values = vector(raw, 6, "raw " + body)
        item["state_si"] = vector([v*1000 for v in values], 6, "SI " + body)
        budget.event("states", "complete")
    return row["bodies"]


def observed_class(base: Any, report: dict[str, Any], profile: dict[str, Any], budget: Budget) -> Any:
    """Observe pinned estimator without replacing its controller or stage arithmetic."""
    class Observed(base):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            original_fun = self.fun
            self._inside_step = False
            self._stage_cursor = 0
            self._active_trial: dict[str, Any] | None = None
            def traced_fun(t: float, y: Any) -> Any:
                if self._inside_step:
                    if self._stage_cursor % self.n_stages == 0:
                        budget.event("trials", "attempt")
                        trial = {"profile": profile["name"], "index": len(report["trials"]),
                            "t_before_s": float(self.t), "t_new_s": None, "h_s": None,
                            "rhs_start": len(report["rhs"]), "rhs_end": None,
                            "accepted": None, "decision": "unavailable"}
                        report["trials"].append(trial)
                        self._active_trial = trial
                    self._stage_cursor += 1
                try:
                    return original_fun(t, y)
                finally:
                    if self._inside_step and self._active_trial is not None:
                        self._active_trial["rhs_end"] = len(report["rhs"])
            self.fun = traced_fun

        def _step_impl(self) -> Any:
            self._inside_step = True
            self._stage_cursor = 0
            try:
                return super()._step_impl()
            finally:
                self._inside_step = False

        def _estimate_error_norm(self, k: Any, h: float, scale: Any) -> float:
            trial = self._active_trial
            require(trial is not None and self._stage_cursor % self.n_stages == 0,
                    "pinned DOP853 twelve-stage observer reconciliation")
            trial.update(t_new_s=float(self.t+h), h_s=float(h), rhs_end=len(report["rhs"]))
            error = float(super()._estimate_error_norm(k, h, scale))
            trial.update(error_norm=number(error, "error norm"), scale=vector(scale.tolist(), 6, "scale"),
                         accepted=error < 1., decision="accepted" if error < 1. else "rejected",
                         nfev=int(self.nfev))
            require(error >= 0 and all(v > 0 for v in trial["scale"]), "invalid error/scales")
            budget.event("trials", "complete")
            return error

        def step(self) -> Any:
            try:
                return super().step()
            finally:
                profile["solver_state"] = {"t_s": float(self.t), "y": self.y.tolist(),
                                           "status": self.status, "nfev": int(self.nfev)}
    return Observed


def solve_profile(bundle: dict[str, Any], name: str, report: dict[str, Any],
                  provider: Callable[[str, float], Any], budget: Budget,
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
        bodies = query_bodies(s, bundle["initial"], provider, budget, row)
        build_row(bundle["initial"], s, row["correction"], bodies,
                  bundle["gm_m3_s2"], bundle["radii_m"], budget, row)
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
                  bundle["gm_m3_s2"], bundle["radii_m"], budget, row)
    budget.event("solves", "complete")
    return profile
