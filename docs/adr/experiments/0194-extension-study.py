"""Private ADR0193 50 s model B study; live bindings stay lazy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction
from hashlib import sha256
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
DURATION_S = 50.
OFFSETS = tuple(float(i) for i in range(0, 51, 5))
BODIES = ("Sun", "Moon", "Earth")
ORDER = ("normal", "tighter")
NATIVE_LIMITS = (.01, 1e-5)
ADAPTIVE_LIMITS = (.001, 1e-6)
LIMITS = {
    "rhs": 10000, "trials": 1000, "states": 40044, "solves": 2,
    "binary64_fields": 30066, "dynamic_totals": 10022, "body_checks": 108,
    "moon_earth_checks": 36, "source_rows": 108, "reference_fields": 864,
    "model_totals": 36, "record_evaluations": 216,
    "native_arcs": 2, "native_guard_reads": 462, "native_reference_fields": 132,
    "native_telemetry": 22, "initializations": 1, "identities": 2, "metadata": 30,
}
PINS = {
    "0180-split-study.py": "e0937a7c4528febf84f5016a6d3d92148bbab1554b8f6d8c8b41ef3258bc754b",
    "0186-long-b-integrator.py": "e0bb9a459b0aa81f281225e00b5db0766f81d3a8e2dff61547756b7c68a77dc6",
    "0186-long-b-reference.py": "4fb366b232c1515e4d6f96d2bc14b77249ed09bed909bbe3d79ac9a29b59e7c5",
    "0183-earth-native.py": "6730fe7aa4d9b3407a6c16e3a4232277860db261f65130a12166de1721fa7060",
    "0183-earth-native-replay.py": "3ddff9eb6b4ee320aae9cd8dddc89f5f9dbe82bbcea3758dad1d17f3e396eba6",
}
type Row = dict[str, Any]
type Provider = Callable[[str, float, str, str, str], object]
type Check = Callable[[], None]
type Vector = tuple[float, ...]


def require(ok: bool, label: str) -> None:
    if not ok:
        raise ValueError(label)


def load(name: str, check: Check) -> ModuleType:
    """Load a pinned predecessor without changing its frozen controls."""
    check()
    source = HERE / name
    raw = source.read_bytes()
    require(sha256(raw).hexdigest() == PINS[name], "source hash: " + name)
    module = ModuleType("r547_" + source.stem.replace("-", "_"))
    module.__file__ = str(source)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(source), "exec"), module.__dict__)
    check()
    return module


@dataclass(slots=True)
class Budget:
    clock: Callable[[], float]
    start_s: float
    duration_s: float = 60.
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    ledger: list[dict[str, str]] = field(default_factory=list)

    def check(self) -> None:
        elapsed_s = self.clock() - self.start_s
        require(math.isfinite(elapsed_s) and 0 <= elapsed_s < self.duration_s, "study deadline/clock")

    def event(self, operation: str, phase: str) -> None:
        require(operation in LIMITS and phase in ("attempt", "return", "complete"), "study budget operation")
        if phase == "attempt":
            self.check()
        row = self.counts.setdefault(operation, {"attempted": 0, "returned": 0, "completed": 0})
        if phase == "attempt":
            require(row["attempted"] < LIMITS[operation], operation + " attempt cap")
            row["attempted"] += 1
        else:
            key = "returned" if phase == "return" else "completed"
            require(row[key] < row["attempted"], operation + " unmatched " + phase)
            row[key] += 1
        self.ledger.append({"operation": operation, "phase": phase})
        self.check()


def new_budget(clock: Callable[[], float], started_s: float) -> Budget:
    """Create the observed study budget with a parent-owned monotonic start."""
    return Budget(clock, started_s)


def _native_profile(bundle: Row, report: Row, name: str, budget: Budget,
                    native: ModuleType, replay: ModuleType, adapter: ModuleType) -> list[Row]:
    initial = bundle["initial"]
    position_velocity = adapter.vector(initial["position_m"] + initial["velocity_m_s"], 6)
    start = adapter.number(initial["epoch_tdb_s"])
    step = 1. if name == "normal" else .5
    count = int(DURATION_S / step) + 1
    gm, radii = bundle["gm_m3_s2"], bundle["radii_m"]
    require(gm == adapter.GM and radii == adapter.GUARDS and all(
        (start + s) - start == s for s in (step, *OFFSETS)), "native frozen inputs and epoch grid")
    guards: list[Row] = []
    row = {"name": name, "step_s": step, "guards": guards, "coast_mass_kg": bundle["mass_kg"],
           "arc": {"attempted": 0, "returned": 0, "completed": 0}}
    report["native_profiles"].append(row)
    prepared = adapter.build_model("B", budget.check)
    row["inventory"] = native.inventory(adapter, prepared, gm)
    context = native.Arc(budget, row)

    def guard(epoch: float, state: Vector) -> None:
        group, remainder = divmod(len(guards), len(BODIES))
        require(not remainder and epoch == start + max(0, group - 1) * step
                and group <= count, "native guard order/grid")
        for body in BODIES:
            budget.event("native_guard_reads", "attempt")
            saved: Row = {"body": body, "epoch_tdb_s": epoch, "group": group}
            guards.append(saved)
            try:
                raw = prepared.bodies.get(body).ephemeris.cartesian_state(epoch)
                flat = raw.reshape(-1) if hasattr(raw, "reshape") else raw
            except Exception as exc:  # Untyped native ephemeris boundary.
                raise ValueError(f"native guard failed: {body} at {epoch}: {exc}") from exc
            saved["state_si"] = native.wire(flat)
            budget.event("native_guard_reads", "return")
            radius = math.dist(state[:3], adapter.vector(saved["state_si"], 6)[:3])
            require(math.isfinite(radius) and radii[body] > 0, "native guard radius/distance")
            saved.update(distance_m=radius, passed=radius > radii[body])
            require(saved["passed"], f"native {body} exclusion sphere at {epoch}")
            budget.event("native_guard_reads", "complete")

    result = adapter.propagate(prepared, position_velocity, start, DURATION_S, step, OFFSETS, context, guard)
    require(context.arcs_completed == context.arcs_returned == 1 and len(guards) == 3 * (1 + count),
            "native arc/guard coverage")
    row["result"] = native.wire(result)
    row["arc"]["completed"] = 1
    budget.event("native_arcs", "complete")
    samples = row["result"]["samples"]
    require(len(samples) == len(OFFSETS), "native sample count")
    for sample, offset in zip(samples, OFFSETS, strict=True):
        budget.check()
        require(sample["epoch_tdb_s"] == start + offset, "native sample epoch")
        first = 3 * (int(offset / step) + 1)  # Exclude the duplicate preflight group.
        replay.telemetry(replay.vector(sample["state"], 6), replay.vector(sample["acceleration_m_s2"], 12),
                         [replay.vector(g["state_si"], 6)[:3] for g in guards[first:first + 3]],
                         gm, budget.event)
    require(replay.same_words(samples[0]["state"], position_velocity, 6), "native exact archived restart")
    return samples


def _adaptive_profile(bundle: Row, report: Row, name: str, budget: Budget, provider: Provider,
                      integrator: ModuleType) -> Row:
    from scipy.integrate import DOP853, solve_ivp

    initial = bundle["initial"]
    settings = integrator.settings(name)
    budget.event("solves", "attempt")
    profile: Row = {"name": name, "settings": settings, "rhs_start": len(report["rhs"]),
                    "outputs": [], "coast_mass_kg": bundle["mass_kg"]}
    report["profiles"].append(profile)

    def build(s: float, correction: list[float], node: Row, row: Row) -> None:
        integrator.build_row(initial, s, correction, node["bodies"], bundle["gm_m3_s2"],
                             bundle["radii_m"], budget, row, moon_earth=node["moon_earth"])

    def rhs(s: float, correction: Any) -> list[float]:
        budget.event("rhs", "attempt")
        index = len(report["rhs"])
        row: Row = {"profile": name, "index": index - profile["rhs_start"], "global_index": index}
        report["rhs"].append(row)
        elapsed = integrator.number(float(s), "RHS elapsed")
        require(0 <= elapsed <= DURATION_S, "RHS time outside extension")
        row["correction"] = integrator.vector(correction.tolist(), 6, "correction")
        integrator.query_bodies(elapsed, initial, provider, budget, row, report["state_requests"])
        build(elapsed, row["correction"], row, row)
        row["completed"] = True
        budget.event("rhs", "complete")
        return row["derivative"]

    method = integrator._split.observed_class(DOP853, report, profile, budget)
    result = solve_ivp(rhs, (0., DURATION_S), [0.] * 6, method=method, t_eval=OFFSETS, **settings)
    raw = {"success": bool(result.success), "status": int(result.status), "message": str(result.message),
           "t": result.t.tolist(), "y": result.y.tolist(), "nfev": int(result.nfev)}
    profile["raw_returned"] = raw
    budget.event("solves", "return")
    require(raw["success"] and raw["status"] == 0 and raw["t"] == list(OFFSETS)
            and len(raw["y"]) == 6 and all(len(values) == len(OFFSETS) for values in raw["y"]),
            "incomplete adaptive profile")
    require(raw["nfev"] == len(report["rhs"]) - profile["rhs_start"], "RHS/nfev mismatch")
    for index, (offset, node) in enumerate(zip(OFFSETS, report["node_table"], strict=True)):
        row = {"profile": name, "index": index}
        profile["outputs"].append(row)
        build(offset, [values[index] for values in raw["y"]], node, row)
    budget.event("solves", "complete")
    return profile


def _observe(profile: Row, report: Row, bundle: Row, reference: ModuleType,
             legacy: ModuleType, budget: Budget) -> None:
    rhs = report["rhs"][profile["rhs_start"]:][:7]
    require(len(rhs) == 7 and all(r["index"] == i and r["completed"] is True
                                  for i, r in enumerate(rhs))
            and any(r["lo_s"] != 0 for r in rhs), "first seven completed RHS and low epoch")
    for kind, rows in (("output", profile["outputs"]), ("rhs", rhs)):
        for row in rows:
            budget.check()
            owners = [trial["index"] for trial in report["trials"]
                      if kind == "rhs" and trial["rhs_start"] <= row["global_index"] < trial["rhs_end"]]
            require(len(owners) <= 1, "overlapping trial membership")
            hi, lo = row["hi_tdb_s"], row["lo_s"]
            observation: Row = {"profile": profile["name"], "kind": kind, "index": row["index"],
                                "trial_index": owners[0] if owners else None, "progress": {},
                                "hi_tdb_s": hi, "exact_tdb_s": str(Fraction(hi) + Fraction(lo))}
            report["observations"].append(observation)
            observation["assessment"] = reference.assess_observation(
                bundle["initial"], row["motion"], legacy.body_rows(bundle, row), row["geometry"],
                bundle["gm_m3_s2"], bundle["radii_m"], budget.event, budget.check,
                progress=observation["progress"])
            require(observation["assessment"]["passed"], "required source/force/assembly gate")


def _compare(report: Row, reference: ModuleType, family: str, index: int, epoch: float,
             a: list[float], b: list[float], limits: tuple[float, float]) -> None:
    assessment = reference.compare_states(a, b, *limits)
    diff = [right - left for left, right in zip(a, b, strict=True)]
    pn, vn = math.hypot(*diff[:3]), math.hypot(*diff[3:])
    require(all(map(math.isfinite, (*diff, pn, vn))), "nonfinite signed profile residual")
    difference = {"vector": diff, "position_norm_m": pn, "velocity_norm_m_s": vn}
    report["comparisons"].append({"name": family, "index": index, "epoch_tdb_s": epoch,
                                  "assessment": assessment, "difference": difference})
    summary = report["comparison_summary"].setdefault(
        family, {"max_position_norm_m": 0., "max_velocity_norm_m_s": 0., "endpoint": None})
    summary["max_position_norm_m"] = max(summary["max_position_norm_m"], pn)
    summary["max_velocity_norm_m_s"] = max(summary["max_velocity_norm_m_s"], vn)
    if index == len(OFFSETS) - 1:
        summary["endpoint"] = difference
    require(assessment["passed"], "trajectory comparison: " + family)


def _idle(_stage: str) -> None:
    pass


def run(bundle: Row, report: Row, budget: Budget, provider: Provider,
        native_adapter: ModuleType | None = None, *, set_stage: Callable[[str], None] = _idle) -> None:
    """Retain the two independent profiles per engine and all fixed sample operands."""
    for key in ("native_profiles", "profiles", "rhs", "trials", "observations",
                "node_table", "comparisons", "state_requests"):
        require(report.setdefault(key, []) == [], "preexisting report work: " + key)
    require(report.setdefault("comparison_summary", {}) == {}, "preexisting comparison summary")
    report["counts"], report["ledger"] = budget.counts, budget.ledger
    require(tuple(bundle["offsets_s"]) == OFFSETS, "frozen extension coepochs")
    initial = bundle["initial"]
    start = initial["epoch_tdb_s"]
    initial_state = initial["position_m"] + initial["velocity_m_s"]
    native = load("0183-earth-native.py", budget.check)
    replay = load("0183-earth-native-replay.py", budget.check)
    integrator = load("0186-long-b-integrator.py", budget.check)
    reference = load("0186-long-b-reference.py", budget.check)
    legacy = load("0180-split-study.py", budget.check)
    adapter = native.load_adapter() if native_adapter is None else native_adapter

    # Check the archived common Moon state before any propagation. These are the
    # same canonical coepoch requests used later to reconstruct force samples.
    set_stage("node-table")
    for offset in OFFSETS:
        row: Row = {}
        report["node_table"].append(row)
        integrator.query_bodies(offset, initial, provider, budget, row, report["state_requests"])
        if offset == 0:
            require(replay.same_words(row["bodies"]["Moon"]["state_si"], bundle["restart_moon_state_si"], 6),
                    "archived restart Moon state words")
    states: dict[str, list[list[float]]] = {}
    for name in ORDER:
        set_stage("native-" + name)
        samples = _native_profile(bundle, report, name, budget, native, replay, adapter)
        states["native_" + name] = [sample["state"] for sample in samples]
    set_stage("native-step-comparison")
    for j, (a, b) in enumerate(zip(states["native_normal"], states["native_tighter"], strict=True)):
        budget.check()
        _compare(report, reference, "native_step", j, start + OFFSETS[j], a, b, NATIVE_LIMITS)

    for name in ORDER:
        set_stage("solve-" + name)
        profile = _adaptive_profile(bundle, report, name, budget, provider, integrator)
        rows = []
        for output in profile["outputs"]:
            motion = output["motion"]
            output["motion_assessment"] = reference.assess_motion(initial, motion)
            require(output["motion_assessment"]["passed"], "output assembly bound")
            rows.append(motion["position_m"] + motion["velocity_m_s"])
        require(profile["outputs"][0]["hi_tdb_s"] == start
                and replay.same_words(rows[0], initial_state, 6), "adaptive exact archived restart")
        states["dop853_" + name] = rows
        set_stage("samples-" + name)
        _observe(profile, report, bundle, reference, legacy, budget)
    set_stage("profile-comparisons")
    pairs = zip(states["native_tighter"], states["dop853_normal"], states["dop853_tighter"], strict=True)
    for j, (native_state, normal, tight) in enumerate(pairs):
        budget.check()
        _compare(report, reference, "native_tighter", j, start + OFFSETS[j], native_state, tight, NATIVE_LIMITS)
        _compare(report, reference, "oracle_step", j, start + OFFSETS[j], normal, tight, ADAPTIVE_LIMITS)
    require(len(report["comparisons"]) == 33 and len(report["observations"]) == 36
            and budget.counts["native_telemetry"]["completed"] == 22
            and budget.counts["native_guard_reads"]["completed"] == 462, "extension scope counts")
    budget.check()
