"""Private ADR0196 producer of bounded, lossless model B study records."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction
from hashlib import sha256
import math
from pathlib import Path
import sys
from types import FunctionType, ModuleType
from typing import Any, Protocol

HERE = Path(__file__).resolve().parent
DURATION_S = 16_000.0
OFFSETS = tuple(float(i) for i in range(0, 16_001, 50))
BODIES = ("Sun", "Moon", "Earth")
PROFILES = ("normal", "tighter")
NATIVE_LIMITS = (.01, 1e-5)
ADAPTIVE_LIMITS = (.001, 1e-6)
CAPS = {
    "rhs": 160_000, "trials": 13_000, "states": 641_284, "solves": 2,
    "binary64_fields": 481_926, "dynamic_totals": 160_642, "body_checks": 3_852,
    "moon_earth_checks": 1_284, "source_rows": 3_852, "reference_fields": 30_816,
    "model_totals": 1_284, "record_evaluations": 7_704, "native_arcs": 2,
    "native_guard_reads": 144_012, "native_reference_fields": 3_852,
    "native_telemetry": 642, "initializations": 1, "identities": 2, "metadata": 30,
    "gm_acquisitions": 0,
}
PINS = {
    "0180-split-study.py": "e0937a7c4528febf84f5016a6d3d92148bbab1554b8f6d8c8b41ef3258bc754b",
    "0186-long-b-integrator.py": "e0bb9a459b0aa81f281225e00b5db0766f81d3a8e2dff61547756b7c68a77dc6",
    "0186-long-b-reference.py": "4fb366b232c1515e4d6f96d2bc14b77249ed09bed909bbe3d79ac9a29b59e7c5",
    "0183-earth-native.py": "6730fe7aa4d9b3407a6c16e3a4232277860db261f65130a12166de1721fa7060",
    "0183-earth-native-replay.py": "3ddff9eb6b4ee320aae9cd8dddc89f5f9dbe82bbcea3758dad1d17f3e396eba6",
}
type Row = dict[str, Any]
type Vector = tuple[float, ...]
type Check = Callable[[], None]
type Provider = Callable[[str, float, str, str, str], object]


class Writer(Protocol):
    def append(self, kind: str, row: Row) -> None: ...


def require(ok: object, label: str) -> None:
    if not ok:
        raise ValueError(label)


def load(name: str) -> ModuleType:
    path = HERE / name
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == PINS[name], "frozen source hash: " + name)
    module = ModuleType("r550_" + path.stem.replace("-", "_"))
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


INTEGRATOR = load("0186-long-b-integrator.py")
NATIVE = load("0183-earth-native.py")
REPLAY = load("0183-earth-native-replay.py")
REFERENCE = load("0186-long-b-reference.py")
LEGACY = load("0180-split-study.py")


def _bind(function: FunctionType, scope: Row) -> FunctionType:
    result = FunctionType(function.__code__, scope, function.__name__, function.__defaults__, function.__closure__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result


# Isolate the horizon change; the pinned modules retain their original controls.
_motion = INTEGRATOR.assemble_motion
build_row = _bind(INTEGRATOR.build_row, INTEGRATOR.build_row.__globals__ | {
    "assemble_motion": _bind(_motion, _motion.__globals__ | {"DURATION_S": DURATION_S})})
query_bodies = INTEGRATOR.query_bodies


def _reference_motion(initial: Row, motion: Row) -> Row:
    """Extend the input domain of the pinned independent assembly arithmetic."""
    ref = REFERENCE
    s = ref.MOTION._exact(motion.get("elapsed_s"), "motion.elapsed_s")
    require(0 <= s <= DURATION_S, "reference elapsed outside [0,16000]s")
    r0 = ref.MOTION._vector(initial.get("position_m"), "initial.position_m")
    v0 = ref.MOTION._vector(initial.get("velocity_m_s"), "initial.velocity_m_s")
    q, w = (ref.MOTION._vector(motion.get(key), "motion." + key) for key in ("q_m", "w_m_s"))
    drift, position, velocity = (ref.MOTION._vector(motion.get(key), "motion." + key)
                                  for key in ("drift_m", "position_m", "velocity_m_s"))
    exact_drift = tuple(v*s for v in v0)
    return {"r0": r0, "v0": v0, "s": s, "q": q, "w": w, "drift": drift,
            "position": position, "velocity": velocity, "exact_drift": exact_drift,
            "exact_position": tuple(r+d+c for r, d, c in zip(r0, exact_drift, q, strict=True)),
            "exact_velocity": tuple(v+c for v, c in zip(v0, w, strict=True))}


_ref_scope = REFERENCE.assess_observation.__globals__ | {"_motion_operands": _reference_motion}
assess_motion = _ref_scope["assess_motion"] = _bind(REFERENCE.assess_motion, _ref_scope)
assess_observation = _bind(REFERENCE.assess_observation, _ref_scope)


@dataclass(slots=True)
class Budget:
    clock: Callable[[], float]
    start_s: float
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    on_trial: Check | None = None

    def check(self) -> None:
        elapsed_s = self.clock() - self.start_s
        require(math.isfinite(elapsed_s) and 0 <= elapsed_s < 480, "study deadline/clock")

    def event(self, operation: str, phase: str) -> None:
        if phase == "attempt":
            self.check()
        row = self.counts.get(operation)
        if row is None:
            require(operation in CAPS, "study budget operation")
            row = self.counts[operation] = {"attempted": 0, "returned": 0, "completed": 0}
        if phase == "attempt":
            require(row["attempted"] < CAPS[operation], operation + " attempt cap")
            row["attempted"] += 1
        else:
            require(phase in ("return", "complete"), "study budget phase")
            key = "returned" if phase == "return" else "completed"
            require(row[key] < row["attempted"], operation + " unmatched " + phase)
            row[key] += 1
            if operation == "trials" and phase == "complete" and self.on_trial is not None:
                self.on_trial()
        self.check()


def new_budget(clock: Callable[[], float], start_s: float) -> Budget:
    """Use the parent watchdog's start for all bounded work."""
    return Budget(clock, start_s)


def _live_propagate(adapter: ModuleType, prepared: Any, initial: Vector, epoch_tdb_s: float,
                    step_s: float, context: Any, guard: Callable[[float, Vector], None]) -> Row:
    """ADR0140's RK4 controls on the private fixed 16,000 s horizon."""
    from tudatpy.dynamics import propagation_setup, simulator

    context.check()
    guard(epoch_tdb_s, initial)
    try:
        adapter.validate_inventory(prepared)
        engine_step = propagation_setup.integrator.runge_kutta_fixed_step(
            step_s, propagation_setup.integrator.CoefficientSets.rk_4,
            assess_termination_on_minor_steps=False)
        termination = propagation_setup.propagator.time_termination(
            epoch_tdb_s + DURATION_S, terminate_exactly_on_final_condition=True)
        dependent = [propagation_setup.dependent_variable.total_acceleration("Spacecraft")]
        dependent += [propagation_setup.dependent_variable.single_acceleration(
            propagation_setup.acceleration.point_mass_gravity_type, "Spacecraft", body) for body in BODIES]
        settings = propagation_setup.propagator.translational(
            ["SSB"], prepared.accelerations, ["Spacecraft"], initial, epoch_tdb_s, engine_step,
            termination, propagator=propagation_setup.propagator.cowell, output_variables=dependent)
    except Exception as exc:  # Untyped native settings/readback boundary.
        raise adapter.NativeError(f"native propagation setup failed: {exc}") from exc
    context.arcs_attempted += 1
    try:
        engine = simulator.create_dynamics_simulator(prepared.bodies, settings)
        raw = {"state_history": engine.state_history, "dependent_variable_history": engine.dependent_variable_history,
               "integration_completed": engine.integration_completed_successfully}
    except Exception as exc:  # Untyped native integration/output boundary.
        raise adapter.NativeError(f"native integration failed: {exc}") from exc
    context.arcs_returned += 1
    context.last_returned = raw
    result = adapter.validate_history(raw, initial, epoch_tdb_s, DURATION_S, step_s,
                                      OFFSETS, prepared.included, context.check, guard)
    context.arcs_completed += 1
    return result


@dataclass(slots=True)
class Arc:
    budget: Budget
    writer: Writer
    name: str
    arcs_returned: int = 0
    arcs_completed: int = 0
    _attempted: int = 0
    _raw: Row | None = None

    def check(self) -> None:
        self.budget.check()

    @property
    def arcs_attempted(self) -> int:
        return self._attempted

    @arcs_attempted.setter
    def arcs_attempted(self, value: int) -> None:
        require(value == 1 and self._attempted == 0, "one arc per profile")
        self.budget.event("native_arcs", "attempt")
        self._attempted = value

    @property
    def last_returned(self) -> Row | None:
        return self._raw

    @last_returned.setter
    def last_returned(self, raw: Row) -> None:
        require(self._raw is None and self._attempted == self.arcs_returned == 1, "unmatched native return")
        self._raw = raw
        self.writer.append("native_return", {"name": self.name,
                                             "integration_completed": NATIVE.wire(raw["integration_completed"])})
        self.budget.event("native_arcs", "return")
        states, forces = raw["state_history"], raw["dependent_variable_history"]
        require(isinstance(states, dict) and isinstance(forces, dict), "native histories must be mappings")
        for j, (epoch, value) in enumerate(states.items()):
            row = {"name": self.name, "index": j, "epoch_tdb_s": NATIVE.wire(epoch), "state": NATIVE.wire(value)}
            if epoch in forces:
                row["acceleration_m_s2"] = NATIVE.wire(forces[epoch])
            self.writer.append("native_raw", row)
            self.check()
        for epoch, force in forces.items():
            if epoch not in states:
                self.writer.append("native_unpaired_force", {"name": self.name, "epoch_tdb_s": NATIVE.wire(epoch),
                                                               "acceleration_m_s2": NATIVE.wire(force)})


def _native_profile(bundle: Row, name: str, budget: Budget, writer: Writer,
                    adapter: Any, injected: bool) -> list[list[float]]:
    initial = bundle["initial"]
    state = adapter.vector(initial["position_m"] + initial["velocity_m_s"], 6)
    t0 = adapter.number(initial["epoch_tdb_s"])
    step = 1. if name == "normal" else .5
    n = int(DURATION_S / step) + 1
    gm, radii = bundle["gm_m3_s2"], bundle["radii_m"]
    require(gm == adapter.GM and radii == adapter.GUARDS and all((t0 + s) - t0 == s for s in (step, *OFFSETS)),
            "native frozen controls and exact epoch grid")
    prepared = adapter.build_model("B", budget.check)
    inventory = NATIVE.inventory(adapter, prepared, gm)
    writer.append("native_start", {"name": name, "step_s": step, "inventory": inventory,
                                   "coast_mass_kg": bundle["mass_kg"]})
    context = Arc(budget, writer, name)
    guard_groups = 0
    coepoch_guards: dict[int, list[Vector]] = {}
    coepoch_mesh_indices = {int(offset / step) for offset in OFFSETS}

    def guard(epoch: float, state_on_mesh: Vector) -> None:
        nonlocal guard_groups
        group = guard_groups
        require(group <= n and epoch == t0 + max(0, group - 1) * step, "native guard order/grid")
        retained = coepoch_guards.setdefault(group, []) if group - 1 in coepoch_mesh_indices else None
        for body in BODIES:
            budget.event("native_guard_reads", "attempt")
            row = {"name": name, "group": group, "body": body, "epoch_tdb_s": epoch}
            try:
                try:
                    raw = prepared.bodies.get(body).ephemeris.cartesian_state(epoch)
                    flat = raw.reshape(-1) if hasattr(raw, "reshape") else raw
                except Exception as exc:  # Untyped native ephemeris boundary.
                    raise ValueError(f"native guard failed: {body} at {epoch}: {exc}") from exc
                row["state_si"] = NATIVE.wire(flat)
                budget.event("native_guard_reads", "return")
                body_pos = adapter.vector(row["state_si"], 6)[:3]
                distance = math.dist(state_on_mesh[:3], body_pos)
                require(math.isfinite(distance) and radii[body] > 0, "native guard distance/radius")
                row.update(distance_m=distance, passed=distance > radii[body])
                require(row["passed"], f"native {body} exclusion sphere at {epoch}")
                if retained is not None:
                    retained.append(body_pos)
                budget.event("native_guard_reads", "complete")
            finally:
                writer.append("native_guard", row)
        guard_groups += 1

    if injected:
        result = adapter.propagate(prepared, state, t0, DURATION_S, step, OFFSETS, context, guard)
    else:
        result = _live_propagate(adapter, prepared, state, t0, step, context, guard)
    require(context.arcs_returned == context.arcs_completed == 1 and guard_groups == n + 1,
            "native arc and exact guard coverage")
    budget.event("native_arcs", "complete")
    samples = result["samples"]
    saved: list[list[float]] = []
    for j, (sample, offset) in enumerate(zip(samples, OFFSETS, strict=True)):
        budget.check()
        row = NATIVE.wire(sample)
        writer.append("native_sample", {"name": name, "index": j, **row})
        require(row["epoch_tdb_s"] == t0 + offset, "native sample time")
        if j == 0:
            require(REPLAY.same_words(row["state"], state, 6), "native exact archived restart")
        REPLAY.telemetry(REPLAY.vector(row["state"], 6), REPLAY.vector(row["acceleration_m_s2"], 12),
                         coepoch_guards[int(offset / step) + 1], gm, budget.event)
        saved.append(row["state"])
    writer.append("native_end", {"name": name, "arc": {"attempted": 1, "returned": 1, "completed": 1},
                                 "result": NATIVE.wire({k: v for k, v in result.items() if k != "samples"})})
    return saved


@dataclass(slots=True)
class Tally:
    """The pinned observer needs only length, append, and its active trial."""

    count: int = 0
    last: Row | None = None

    def __len__(self) -> int:
        return self.count

    def append(self, row: Row) -> None:
        self.last = row
        self.count += 1


def build_rhs(bundle: Row, provider: Provider, budget: Budget, row: Row, s: float, correction: object) -> None:
    """Acquire and preserve one compensated RHS row; callers own archive write order."""
    budget.event("rhs", "attempt")
    row["requests"] = []
    elapsed = INTEGRATOR.number(float(s), "RHS elapsed")
    require(0 <= elapsed <= DURATION_S, "RHS time outside frozen interval")
    row["correction"] = INTEGRATOR.vector(correction, 6, "correction")
    query_bodies(elapsed, bundle["initial"], provider, budget, row, row["requests"])
    build_row(bundle["initial"], elapsed, row["correction"], row["bodies"], bundle["gm_m3_s2"],
              bundle["radii_m"], budget, row, moon_earth=row["moon_earth"])
    row["completed"] = True
    budget.event("rhs", "complete")


def _observation(bundle: Row, writer: Writer, budget: Budget, name: str, kind: str,
                 row: Row, trial: int | None, window: int | None) -> None:
    hi, lo = row["hi_tdb_s"], row["lo_s"]
    current = {"profile": name, "kind": kind, "index": row["index"], "trial_index": trial,
               "window": window, "progress": {}, "hi_tdb_s": hi,
               "exact_tdb_s": str(Fraction(hi) + Fraction(lo))}
    try:
        current["assessment"] = assess_observation(
            bundle["initial"], row["motion"], LEGACY.body_rows(bundle, row), row["geometry"],
            bundle["gm_m3_s2"], bundle["radii_m"], budget.event, budget.check, progress=current["progress"])
        require(current["assessment"] == current["progress"], "complete observation progress identity")
        del current["progress"]  # Lossless deduplication of the immutable completed result.
        require(current["assessment"]["passed"], "required source/force/assembly gate")
    finally:
        writer.append("observation", current)


def _adaptive_profile(bundle: Row, writer: Writer, budget: Budget, name: str, provider: Provider,
                      nodes: list[Row], trace: dict[str, Tally], solve: Callable[..., Any],
                      base_solver: type[Any]) -> list[list[float]]:
    settings = INTEGRATOR.settings(name)
    count, trials = trace["rhs"], trace["trials"]
    start_index = len(count)
    profile: Row = {"name": name, "settings": settings, "rhs_start": start_index,
                    "coast_mass_kg": bundle["mass_kg"]}
    budget.event("solves", "attempt")
    writer.append("profile_start", profile)
    first: list[tuple[Row, int | None]] = []
    selected: dict[int, tuple[Row, int | None]] = {}
    written_trial = len(trials) - 1

    def close_trial() -> None:
        nonlocal written_trial
        trial = trials.last
        require(trial is not None and trial["index"] == written_trial + 1, "adaptive trial order")
        writer.append("trial", trial)
        written_trial += 1

    def rhs(s: float, y: Any) -> list[float]:
        j = len(count) - start_index
        active = trials.last
        owner = active["index"] if active is not None and active["accepted"] is None else None
        usage = "initial" if j == 0 else "trial" if owner is not None else "dense"
        row: Row = {"profile": name, "index": j, "global_index": len(count), "usage": usage}
        count.append(row)
        try:
            build_rhs(bundle, provider, budget, row, s, y.tolist())
            if j < 7:
                first.append((row, owner))
            if s > 300:
                window = math.ceil((s - 300) / 50) - 1
                require(0 <= window < 314 and j >= 7, "RHS observation overlap/window")
                selected.setdefault(window, (row, owner))
        finally:
            writer.append("rhs", row if row.get("completed") else LEGACY.finite_wire(row))
        return row["derivative"]

    budget.on_trial = close_trial
    try:
        method = INTEGRATOR._split.observed_class(base_solver, trace, profile, budget)
        result = solve(rhs, (0., DURATION_S), [0.] * 6, method=method, t_eval=OFFSETS, **settings)
    finally:
        budget.on_trial = None
        if len(trials) - 1 > written_trial:
            close_trial()
    raw = {"name": name, "success": bool(result.success), "status": int(result.status),
           "message": str(result.message), "t": result.t.tolist(), "y": result.y.tolist(),
           "nfev": int(result.nfev), "solver_state": profile.get("solver_state")}
    writer.append("profile_return", LEGACY.finite_wire(raw))
    budget.event("solves", "return")
    require(raw["success"] and raw["status"] == 0 and raw["t"] == list(OFFSETS)
            and len(raw["y"]) == 6 and all(len(series) == len(OFFSETS) for series in raw["y"])
            and raw["nfev"] == len(count) - start_index, "adaptive completion/grid/nfev")
    require(len(first) == 7 and any(item[0]["lo_s"] != 0 for item in first)
            and set(selected) == set(range(314)), "required first-seven and later RHS window coverage")
    outputs: list[Row] = []
    states: list[list[float]] = []
    initial = bundle["initial"]
    for j, (s, node) in enumerate(zip(OFFSETS, nodes, strict=True)):
        row = {"profile": name, "index": j}
        try:
            build_row(initial, s, [series[j] for series in raw["y"]], node["bodies"],
                      bundle["gm_m3_s2"], bundle["radii_m"], budget, row, moon_earth=node["moon_earth"])
            motion = row["motion"]
            row["motion_assessment"] = assess_motion(initial, motion)
            state = motion["position_m"] + motion["velocity_m_s"]
            require(row["motion_assessment"]["passed"], "output assembly bound")
            if j == 0:
                require(REPLAY.same_words(state, initial["position_m"] + initial["velocity_m_s"], 6),
                        "adaptive exact archived restart")
            states.append(state)
            outputs.append(row)
        finally:
            writer.append("output", {k: v for k, v in row.items() if k not in ("bodies", "moon_earth")})
    budget.event("solves", "complete")
    for row in outputs:
        _observation(bundle, writer, budget, name, "output", row, None, None)
    for row, trial in first:
        _observation(bundle, writer, budget, name, "rhs", row, trial, None)
    for window in range(314):
        row, trial = selected[window]
        _observation(bundle, writer, budget, name, "rhs", row, trial, window)
    writer.append("profile_end", {"name": name})
    return states


def _compare(writer: Writer, summary: Row, family: str, index: int, epoch_tdb_s: float,
             a: list[float], b: list[float], limits: tuple[float, float]) -> None:
    assessment = REFERENCE.compare_states(a, b, *limits)
    diff = [right - left for left, right in zip(a, b, strict=True)]
    pn, vn = math.hypot(*diff[:3]), math.hypot(*diff[3:])
    require(all(map(math.isfinite, (*diff, pn, vn))), "nonfinite signed residual")
    difference = {"vector": diff, "position_norm_m": pn, "velocity_norm_m_s": vn}
    writer.append("comparison", {"name": family, "index": index, "epoch_tdb_s": epoch_tdb_s,
                                 "assessment": assessment, "difference": difference})
    one = summary.setdefault(family, {"max_position_norm_m": 0., "max_velocity_norm_m_s": 0., "endpoint": None})
    one["max_position_norm_m"] = max(one["max_position_norm_m"], pn)
    one["max_velocity_norm_m_s"] = max(one["max_velocity_norm_m_s"], vn)
    if index == len(OFFSETS) - 1:
        one["endpoint"] = difference
    require(assessment["passed"], "trajectory comparison: " + family)


def run(bundle: Row, writer: Writer, budget: Budget, provider: Provider, native_adapter: Any = None,
        *, solve: Callable[..., Any] | None = None, base_solver: type[Any] | None = None) -> Row:
    """Run two native arcs and two adaptive solves, streaming bounded evidence."""
    require(tuple(bundle["offsets_s"]) == OFFSETS, "frozen far coepochs")
    require((solve is None) == (base_solver is None), "solver injection requires both adapters")
    require(type(bundle["mass_kg"]) in (float, int) and 0 < bundle["mass_kg"] < math.inf, "coast mass")
    if solve is None or base_solver is None:
        from scipy.integrate import DOP853, solve_ivp

        solve, base_solver = solve_ivp, DOP853
    initial = bundle["initial"]
    start = initial["epoch_tdb_s"]
    adapter = NATIVE.load_adapter() if native_adapter is None else native_adapter
    nodes = []
    for j, offset in enumerate(OFFSETS):
        row: Row = {"index": j, "requests": []}
        try:
            query_bodies(offset, initial, provider, budget, row, row["requests"])
            if j == 0:
                require(REPLAY.same_words(row["bodies"]["Moon"]["state_si"], bundle["restart_moon_state_si"], 6),
                        "archived restart Moon state words")
        finally:
            writer.append("node", LEGACY.finite_wire(row))
        nodes.append(row)

    rk4 = [_native_profile(bundle, name, budget, writer, adapter, native_adapter is not None) for name in PROFILES]
    trace = {"rhs": Tally(), "trials": Tally()}
    dop = [_adaptive_profile(bundle, writer, budget, name, provider, nodes, trace, solve, base_solver)
           for name in PROFILES]
    summary: Row = {"comparison_summary": {}, "counts": {k: dict(v) for k, v in budget.counts.items()}}
    comparisons = summary["comparison_summary"]
    for j, (normal, tight) in enumerate(zip(*rk4, strict=True)):
        budget.check()
        _compare(writer, comparisons, "native_step", j, start + OFFSETS[j], normal, tight, NATIVE_LIMITS)
    for j, (native, normal, tight) in enumerate(zip(rk4[1], *dop, strict=True)):
        budget.check()
        _compare(writer, comparisons, "native_tighter", j, start + OFFSETS[j], native, tight, NATIVE_LIMITS)
        _compare(writer, comparisons, "oracle_step", j, start + OFFSETS[j], normal, tight, ADAPTIVE_LIMITS)
    for operation in ("native_arcs", "solves", "native_guard_reads", "native_telemetry", "native_reference_fields",
                      "body_checks", "moon_earth_checks", "source_rows", "reference_fields", "model_totals"):
        require(budget.counts[operation]["completed"] == CAPS[operation], "incomplete required " + operation)
    writer.append("study_summary", summary)
    budget.check()
    return summary
