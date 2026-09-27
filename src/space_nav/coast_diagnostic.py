"""Private D5/D6 coast diagnostics; no mission qualification."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import median
from typing import Any

from . import trajectory as physical
from .cli import _runtime_manifest
from .errors import EphemerisError, TrajectoryRefinementError
from .explorer import SCIENCE_LOCK
from .models import ImpulsiveTransferCandidate, Scenario, TrajectoryBoundaryState
from .research_propagation import _COVERAGE


_REFERENCE_SHA256 = "17f03d9557be6e439af5f1c388e1eb092f55236b3c2afc3de65006d5f639c235"
_STEP_BASELINE_SHA256 = "1a62dd55c642e71530a7092522ff5c6c3408444e4f9e7bea149894f25d1928a2"
_MAXIMUM_STEPS_S = (21600.0, 10800.0, 5400.0)


@dataclass(slots=True)
class _CoastBudget(physical._RefinementBudget):
    completed_arcs: int = field(default=0, init=False)
    stopped: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        physical._RefinementBudget.__post_init__(self)
        if self.runtime_seconds != 300.0:
            self._fail("coast-budget", "D5 requires the fixed 300-second budget")

    def begin_control(self) -> None:
        self._fail("coast-budget", "coast diagnosis has no control search")

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check()
        if (self.stopped or self.native_arc_propagations >= 2
                or self.completed_arcs != self.native_arc_propagations
                or first_in_evaluation is not True):
            self._fail("coast-budget", "two single arcs only; no retries or continuation")
        physical._RefinementBudget.begin_arc(self, first_in_evaluation=True)

    def complete_arc(self) -> None:
        self.check()
        if self.stopped or self.native_arc_propagations != self.completed_arcs + 1:
            self._fail("coast-budget", "no single pending arc to accept")
        self.completed_arcs += 1


class _StepStudyBudget(_CoastBudget):
    """D6 only: three single coast arcs, retaining D5's independent two-arc cap."""

    __slots__ = ()

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check()
        if (self.stopped or self.native_arc_propagations >= 3
                or self.completed_arcs != self.native_arc_propagations
                or first_in_evaluation is not True):
            self._fail("step-study-budget", "three single arcs only; no retries or continuation")
        physical._RefinementBudget.begin_arc(self, first_in_evaluation=True)


def _step_profile(candidate_id: object, index: int) -> dict[str, Any]:
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 3:
        raise ValueError("step profile index must be 0, 1 or 2")
    return {**physical._arc_integrator_profile(candidate_id, "coast", tighter=True),
            "maximum_step_s": _MAXIMUM_STEPS_S[index]}


@dataclass(frozen=True, slots=True)
class _SavedMesh:
    epoch_sequence_sha256: str
    interval_count: int
    minimum_interval_s: float
    median_interval_s: float
    maximum_interval_s: float


def _saved_mesh(epochs: tuple[float, ...]) -> _SavedMesh:
    values = tuple(physical._finite_float("saved epoch", v) for v in epochs)
    intervals = tuple(physical._positive_finite("saved interval", b - a)
                      for a, b in zip(values, values[1:]))
    if not intervals:
        raise ValueError("saved mesh requires at least two distinct epochs")
    digest = sha256(json.dumps(values, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return _SavedMesh(digest, len(intervals), min(intervals), median(intervals), max(intervals))


@dataclass(frozen=True, slots=True)
class _CoastRun:
    """Checked private output; endpoint is absent on any failure, SI/SSB/J2000."""

    profile: str
    endpoint: tuple[float, ...] | None
    checked_state_count: int
    reason: str | None
    saved_mesh: _SavedMesh | None = None


def _propagate_coast(
    budget: _CoastBudget,
    environment: physical._PhysicalEnvironment,
    scenario: Scenario,
    initial: TrajectoryBoundaryState,
    mass_kg: float,
    end_tdb_s: float,
    *,
    tighter: bool,
) -> _CoastRun:
    """One guarded coast; caller verifies provenance and holds SCIENCE_LOCK."""
    profile = "tighter" if tighter else "nominal"
    checked = 0
    detected: TrajectoryRefinementError | None = None
    state = (*initial.position_m, *initial.velocity_m_s)
    epoch = initial.epoch_tdb_s

    def check_state(at: float, sample: object, mass: object) -> None:
        nonlocal checked
        rejection = physical._classify_environment_trial_state(
            budget, environment, at, sample, mass, scenario.spacecraft.dry_mass_kg,
        )
        checked += 1
        if mass == scenario.spacecraft.dry_mass_kg:
            rejection = "rejected-dry-mass"
        if rejection is not None:
            raise TrajectoryRefinementError(f"coast at {at} TDB s: {rejection}")

    def stop(at: float) -> bool:
        nonlocal detected
        budget.check()
        if detected is not None:
            return True
        if at > end_tdb_s:
            return False
        try:
            body = environment.bodies.get(physical.SPACECRAFT_BODY_NAME)
            sample, mass = body.state, body.mass
        except Exception as exc:
            physical._raise_refinement_error(
                budget.candidate_id, "coast-guard", str(exc), exc,
            )
        try:
            check_state(at, sample, mass)
        except TrajectoryRefinementError as exc:
            detected = exc
            return True
        return False

    try:
        budget.check()
        study = isinstance(budget, _StepStudyBudget)
        if study:
            index = budget.native_arc_propagations
            if tighter is not True or budget.stopped or budget.completed_arcs != index:
                raise ValueError("step study requires ordered tighter profiles")
            settings = _step_profile(budget.candidate_id, index)
            profile = f"step-{_MAXIMUM_STEPS_S[index]:g}"
        elif (not isinstance(tighter, bool) or budget.stopped
              or budget.native_arc_propagations != int(tighter)
              or budget.completed_arcs != int(tighter)):
            raise ValueError("coast profiles must run once in nominal/tighter order")
        end_tdb_s = physical._finite_float("end_tdb_s", end_tdb_s)
        if (environment.model_id != physical.PHYSICAL_MODEL_IDENTIFIER
                or (initial.origin, initial.orientation) != ("SSB", "J2000")
                or not environment.initial_epoch_tdb_s <= epoch < end_tdb_s
                <= environment.final_epoch_tdb_s):
            raise ValueError("coast requires the pinned model and a covered forward interval")
        check_state(epoch, state, mass_kg)
        setup = physical._import_tudat_propagation_setup()
        try:
            termination = setup.propagator.hybrid_termination(
                [setup.propagator.custom_termination(stop),
                 setup.propagator.time_termination(
                     end_tdb_s, terminate_exactly_on_final_condition=True)],
                fulfill_single_condition=True,
            )
        except Exception as exc:
            physical._raise_refinement_error(
                budget.candidate_id, "coast-termination", str(exc), exc,
            )
        forces = physical._build_arc_force_models(
            budget.candidate_id, environment, burn_id=None,
        )
        coupled = physical._build_coupled_arc_settings(
            budget.candidate_id, environment.bodies, forces, state, mass_kg, epoch,
            (physical._build_integrator_from_profile(budget.candidate_id, "coast", settings)
             if study else physical._build_arc_integrator(budget.candidate_id, "coast", tighter=tighter)),
            termination, thrust_enabled=False,
        )
        simulator = physical._run_native_arc(
            budget, environment.bodies, coupled, first_in_evaluation=True,
        )
        budget.check()
        try:
            success = simulator.integration_completed_successfully
            samples = sorted(simulator.state_history.items())
        except Exception as exc:
            physical._raise_refinement_error(
                budget.candidate_id, "coast-history", str(exc), exc,
            )
        if success is not True:
            raise ValueError(f"native integration failed; detected event: {detected}")
        if detected is not None:
            raise detected
        first: tuple[float, ...] | None = None
        for at, raw in samples:
            budget.check()
            flatten = getattr(raw, "reshape", None)
            values = tuple(flatten(-1) if callable(flatten) else raw)
            if len(values) != 7:
                raise ValueError("coast history requires seven state/mass components")
            check_state(at, values[:6], values[6])
            if values[6] != mass_kg:
                raise ValueError("coast mass changed in saved history")
            if first is None:
                first = values
        if not samples or samples[0][0] != epoch or first != (*state, mass_kg):
            raise ValueError("native initial state/mass/epoch differs from supplied coast start")
        final, final_mass = physical._read_completed_arc_state(
            budget.candidate_id, "coast", simulator, end_tdb_s,
        )
        if final_mass != mass_kg:
            raise ValueError("coast mass changed")
        mesh = _saved_mesh(tuple(at for at, _ in samples)) if study else None
        result = _CoastRun(profile, (*final, final_mass), checked, None, mesh)
        budget.complete_arc()
        return result
    except (TrajectoryRefinementError, EphemerisError, ValueError, TypeError, RuntimeError) as exc:
        budget.stopped = True
        return _CoastRun(profile, None, checked, f"{profile} coast from {epoch} TDB s: {exc}")


def _difference(left: tuple[float, ...], right: tuple[float, ...]) -> dict[str, Any]:
    if len(left) != 7 or len(right) != 7:
        raise ValueError("differences require seven components")
    values = tuple(physical._finite_float(
        "difference", physical._finite_float("left component", a)
        - physical._finite_float("right component", b),
    ) for a, b in zip(left, right))
    position, velocity, mass = math.hypot(*values[:3]), math.hypot(*values[3:6]), values[6]
    for value in (position, velocity):
        physical._finite_float("difference norm", value)
    return {
        "position_m": values[:3], "velocity_m_s": values[3:6], "mass_kg": mass,
        "position_norm_m": position, "velocity_norm_m_s": velocity,
        "mass_absolute_kg": abs(mass),
        "within_thresholds": position <= 10 and velocity <= 1e-4 and abs(mass) <= 1e-6,
    }


def _environment_manifest(environment: physical._PhysicalEnvironment) -> dict[str, Any]:
    data = {
        name: getattr(environment, name)
        for name in ("model_id", "origin", "orientation", "initial_epoch_tdb_s", "final_epoch_tdb_s")
    }
    data.update(
        harmonic_fields=[asdict(v) for v in environment.harmonic_fields],
        gravity=[asdict(v) for v in environment.gravity_acceleration_inventory],
        solar_radiation_pressure=asdict(environment.solar_radiation_pressure),
        relativity=asdict(environment.relativity),
        collision_resource=asdict(environment.collision_resource),
    )
    return json.loads(json.dumps(data, allow_nan=False))


def _difference_trend(first: float, second: float) -> dict[str, Any]:
    a = physical._finite_float("first difference", first)
    b = physical._finite_float("second difference", second)
    if min(a, b) < 0:
        raise ValueError("difference norms must be nonnegative")
    ratio = b / a if a > 0 else None
    reason = "zero_previous_difference" if a == 0 else None
    if ratio is not None and not math.isfinite(ratio):
        ratio, reason = None, "nonfinite_ratio"
    return {"ratio": ratio, "ratio_unavailable_reason": reason,
            "trend": "decreasing" if b < a else "increasing" if b > a else "unchanged"}


def _study_comparisons(runs: list[_CoastRun]) -> dict[str, Any]:
    if len(runs) != 3 or any(r.endpoint is None or r.saved_mesh is None for r in runs):
        raise ValueError("step comparisons require three complete endpoints and meshes")
    pairs = {}
    for i, j in ((0, 1), (1, 2), (0, 2)):
        left, right = runs[i], runs[j]
        pairs[f"{i}-{j}"] = {
            **_difference(left.endpoint, right.endpoint),
            "endpoints_identical": left.endpoint == right.endpoint,
            "saved_meshes_identical": left.saved_mesh.epoch_sequence_sha256
            == right.saved_mesh.epoch_sequence_sha256,
        }
    return {
        "pairs": pairs,
        "position": _difference_trend(pairs["0-1"]["position_norm_m"], pairs["1-2"]["position_norm_m"]),
        "velocity": _difference_trend(pairs["0-1"]["velocity_norm_m_s"], pairs["1-2"]["velocity_norm_m_s"]),
    }


def _load_step_baseline(path: Path, stored: dict[str, Any]) -> dict[str, Any]:
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != _STEP_BASELINE_SHA256:
        raise ValueError("step baseline digest differs from Decision 0082")
    data = json.loads(raw)["science"]
    if (data["outcome"] != "completed" or data["scenario"] != stored["scenario"]
            or data["reference_sha256"] != _REFERENCE_SHA256
            or data["environment"] != stored["provenance"]["environment"]
            or data["initial"] != stored["nominal"]["boundaries"][1]
            or data["initial_mass_kg"] != stored["nominal"]["boundary_masses_kg"][1]
            or data["end_epoch_tdb_s"] != stored["nominal"]["boundaries"][2]["epoch_tdb_s"]):
        raise ValueError("step baseline input/model identity mismatch")
    return data


def _load_reference(path: Path, scenario: Scenario) -> dict[str, Any]:
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != _REFERENCE_SHA256:
        raise ValueError("reference digest differs from retained Decision 0079")
    data = json.loads(raw)["science"]
    if data["scenario"] != json.loads(json.dumps(scenario.to_dict())):
        raise ValueError("normalized scenario differs from reference")
    if scenario.limits.runtime_seconds != 300:
        raise ValueError("reference requires 300 seconds")
    for profile in ("nominal", "tighter"):
        run = data[profile]
        if run["outcome"] != "completed":
            raise ValueError("reference profiles must be completed")
        for item in run["boundaries"]:
            if (item["origin"], item["orientation"]) != ("SSB", "J2000"):
                raise ValueError("reference frame mismatch")
    return data


def _run_diagnostic(
    scenario: Scenario, reference: Path, *, step_baseline: Path | None = None,
) -> dict[str, Any]:
    """D5 two arcs, or opt-in D6 three arcs; one shared clock and no retries."""
    study = step_baseline is not None
    budget = (_StepStudyBudget if study else _CoastBudget)("d0001-t0035", 300.0)
    science: dict[str, Any] = {
        "research_only": True, "continuous_safety_verified": False,
        "origin": "SSB", "orientation": "J2000", "units": "SI",
        "time_scale": "TDB seconds since J2000", "scenario": scenario.to_dict(),
        "expected_reference_sha256": _REFERENCE_SHA256, "check_coverage": _COVERAGE,
        "runtime_limit_s": 300, "maximum_native_arcs": 3 if study else 2, "automatic_retries": 0,
        "profiles": [], "comparisons": None, "reason": None, "outcome": "aborted",
        "interpretation": "Signed differences, not additive norms or exact sensitivity. "
        "Restart drift must pass thresholds before interpreting the isolated comparison. "
        "Neither profile is ground truth; no target closure or safety qualification.",
    }
    if study:
        science.update(
            expected_step_baseline_sha256=_STEP_BASELINE_SHA256,
            baseline_comparison=None,
            interpretation="Maximum-step sensitivity only, not absolute error, convergence order, "
            "ground truth, target closure or safety. Unchanged meshes/endpoints are not proof of accuracy.",
            saved_mesh_description="Ordered saved epochs and intervals, including endpoint handling; "
            "not all rejected steps or internal RK stages.",
        )
    stage = "reference-verification"
    with SCIENCE_LOCK:
        try:
            budget.check()
            stored = _load_reference(reference, scenario)
            science["reference_sha256"] = _REFERENCE_SHA256
            baseline = _load_step_baseline(step_baseline, stored) if study else None
            if study:
                science["step_baseline_sha256"] = _STEP_BASELINE_SHA256
            budget.check()
            stage = "candidate-verification"
            values = dict(stored["provenance"]["candidate"])
            for name in ("departure_v_infinity_m_s", "arrival_v_infinity_m_s"):
                values[name] = tuple(values[name])
            candidate = physical._verify_candidate_handoff(
                scenario, ImpulsiveTransferCandidate(**values),
                deadline_monotonic_s=budget.deadline_monotonic_s, monotonic=budget.monotonic,
            )
            budget.check()
            science["candidate"] = asdict(candidate)
            runtime = _runtime_manifest(scenario.limits.random_seed)
            if runtime != stored["provenance"]["runtime"]:
                raise ValueError("runtime/kernel identity differs from reference")
            science["runtime"] = runtime
            raw_initial = dict(stored["nominal"]["boundaries"][1])
            for name in ("position_m", "velocity_m_s"):
                raw_initial[name] = tuple(raw_initial[name])
            initial = TrajectoryBoundaryState(**raw_initial)
            mass = stored["nominal"]["boundary_masses_kg"][1]
            end = stored["nominal"]["boundaries"][2]["epoch_tdb_s"]
            science.update(initial=asdict(initial), initial_mass_kg=mass, end_epoch_tdb_s=end)
            endpoints: list[tuple[float, ...]] = []
            previous: list[physical._PhysicalEnvironment] = []
            runs: list[_CoastRun] = []
            for index, tighter in enumerate((True, True, True) if study else (False, True)):
                stage = (f"step-{_MAXIMUM_STEPS_S[index]:g}" if study
                         else "tighter" if tighter else "nominal") + "-preparation"
                budget.check()
                environment = physical._build_physical_environment(
                    candidate, scenario.spacecraft, budget=budget,
                )
                budget.check()
                manifest = _environment_manifest(environment)
                if manifest != stored["provenance"]["environment"]:
                    raise ValueError("environment identity differs from reference")
                if any(environment is old or environment.bodies is old.bodies for old in previous):
                    raise ValueError("coast profiles require fresh native environments")
                science["environment"] = manifest
                pinned_settings = physical._arc_integrator_profile(
                    candidate.candidate_id, "coast", tighter=tighter,
                )
                stored_settings = stored["tighter" if tighter else "nominal"]["integrator_settings"]["coast"]
                if json.loads(json.dumps(pinned_settings, allow_nan=False)) != stored_settings:
                    raise ValueError("integrator profile differs from reference")
                settings = _step_profile(candidate.candidate_id, index) if study else pinned_settings
                stage = "coast-propagation"
                run = _propagate_coast(budget, environment, scenario, initial, mass, end, tighter=tighter)
                serialized = {**asdict(run), "integrator_settings": settings}
                if not study:
                    serialized.pop("saved_mesh")  # Preserve the D5 report shape.
                science["profiles"].append(serialized)
                if run.endpoint is None:
                    raise ValueError(run.reason)
                endpoints.append(run.endpoint)
                runs.append(run)
                previous.append(environment)
                if study and index == 0:
                    science["baseline_comparison"] = _difference(
                        run.endpoint, tuple(baseline["profiles"][1]["endpoint"]),
                    )
                    if not science["baseline_comparison"]["within_thresholds"]:
                        raise ValueError("step-study baseline mismatch; refinements not started")
            old = []
            for profile in ("nominal", "tighter"):
                item = stored[profile]["boundaries"][2]
                old.append((*item["position_m"], *item["velocity_m_s"],
                            stored[profile]["boundary_masses_kg"][2]))
            science["comparisons"] = _study_comparisons(runs) if study else {
                "restart_drift": _difference(endpoints[0], old[0]),
                "same_input_profiles": _difference(endpoints[0], endpoints[1]),
                "tighter_changed_input_and_restart": _difference(endpoints[1], old[1]),
            }
            budget.check()
            science["outcome"] = "completed"
        except (EphemerisError, TrajectoryRefinementError, ValueError, OSError) as exc:
            budget.stopped = True
            science["reason"] = f"{stage}: {exc}"
            science["comparisons"] = None
    science["attempted_arcs"] = budget.native_arc_propagations
    science["completed_arcs"] = budget.completed_arcs
    source = Path(__file__).parent
    return json.loads(json.dumps({
        "science": science,
        "source_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(source.glob("*.py"))},
        "wall_clock": {"elapsed_s": budget._last_monotonic_s - (budget.deadline_monotonic_s - 300)},
    }, allow_nan=False))


def main(argv: list[str] | None = None) -> int:
    """Standalone diagnostic entrypoint, never overwrite retained evidence."""
    from .scenario import load_scenario

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--step-baseline", type=Path, help="Opt in to D6 using retained Decision 0082 JSON")
    args = parser.parse_args(argv)
    scenario = load_scenario(args.scenario)
    with args.output.open("x", encoding="utf-8") as stream:
        result = _run_diagnostic(scenario, args.reference, step_baseline=args.step_baseline)
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    # Zero means the diagnostic completed, not that profile thresholds passed.
    return 0 if result["science"]["outcome"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
