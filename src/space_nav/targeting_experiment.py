"""Private bounded D7 orchestration; no production targeting or safety claim."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from . import research_correction as correction
from . import trajectory as physical
from .cli import _runtime_manifest
from .coast_diagnostic import _difference, _environment_manifest, _load_reference, _REFERENCE_SHA256
from .errors import EphemerisError, TrajectoryRefinementError
from .explorer import SCIENCE_LOCK
from .models import ImpulsiveTransferCandidate, Scenario
from .research import ResearchRun, _ResearchBudget
from .research_propagation import _ARCS, _COVERAGE, _compose_research_run
from .scenario import load_scenario


@dataclass(slots=True)
class _TargetingBudget(_ResearchBudget):
    stopped: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _ResearchBudget.__post_init__(self)
        if self.runtime_seconds != 300:
            self._fail("D7-budget", "D7 requires 300 seconds")

    def begin_control(self) -> None:
        self.check()
        if (self.stopped or self.control_attempts >= 8
                or self.control_attempts != self.propagation_evaluations
                or self.completed_arcs != 3 * self.propagation_evaluations
                or self.completed_arcs != self.native_arc_propagations):
            self._fail("D7-budget", "eight ordered controls only; no retries")
        physical._RefinementBudget.begin_control(self)

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check()
        first = self.native_arc_propagations % 3 == 0
        expected_controls = min(self.propagation_evaluations + int(first), 8)
        if (self.stopped or self.native_arc_propagations >= 27
                or self.completed_arcs != self.native_arc_propagations
                or not isinstance(first_in_evaluation, bool) or first_in_evaluation != first
                or self.control_attempts != expected_controls):
            self._fail("D7-budget", "nine three-arc evaluations only; no retries")
        physical._RefinementBudget.begin_arc(self, first_in_evaluation=first_in_evaluation)


def _run_data(run: ResearchRun) -> dict[str, Any]:
    data = asdict(run)
    settings = data.pop("integrator_settings_json")
    data["integrator_settings"] = None if settings is None else json.loads(settings)
    return json.loads(json.dumps(data, allow_nan=False))


def _compare_boundaries(left: dict[str, Any], right: dict[str, Any]) -> list[dict[str, Any]]:
    if len(left["boundaries"]) != 4 or len(right["boundaries"]) != 4:
        raise ValueError("comparison requires four completed boundaries")
    differences = []
    for i, (a, b) in enumerate(zip(left["boundaries"], right["boundaries"])):
        for key in ("label", "epoch_tdb_s", "epoch_utc", "origin", "orientation"):
            if a[key] != b[key]:
                raise ValueError(f"boundary {i} {key} mismatch")
        differences.append(_difference(
            (*a["position_m"], *a["velocity_m_s"], left["boundary_masses_kg"][i]),
            (*b["position_m"], *b["velocity_m_s"], right["boundary_masses_kg"][i]),
        ))
    return differences


def _terminal_residual(run: ResearchRun) -> tuple[float, ...]:
    if run.outcome != "completed" or run.target_state is None:
        raise ValueError("completed run required for residual")
    end, target = run.boundaries[-1], run.target_state
    return correction._residual(tuple(a-b for a, b in zip(
        (*end.position_m, *end.velocity_m_s), (*target.position_m, *target.velocity_m_s),
    ))).values


def _run_targeting(scenario: Scenario, reference: Path) -> dict[str, Any]:
    """One update at most; preserve diagnostics after failure, never retry."""
    budget = _TargetingBudget("d0001-t0035", 300.0)
    science: dict[str, Any] = {
        "research_only": True, "continuous_safety_verified": False,
        "origin": "SSB", "orientation": "J2000", "units": "SI",
        "time_scale": "TDB seconds since J2000", "scenario": scenario.to_dict(),
        "runtime_limit_s": 300, "maximum_controls": 8, "maximum_evaluations": 9,
        "maximum_native_arcs": 27, "automatic_retries": 0, "check_coverage": _COVERAGE,
        "outcome": "aborted", "reason": None, "runs": [], "baseline_comparison": None,
        "correction": None, "improvement": None, "tighter_comparison": None,
        "numerical_agreement": None, "expected_reference_sha256": _REFERENCE_SHA256,
        "rejection_counts": {},
        "control_units": ["rad", "rad", "s", "rad", "rad", "s"],
        "interpretation": "One empirical correction; improvement, closure and numerical "
        "agreement are separate. No accuracy, continuous safety or strict M3 qualification.",
    }
    stage = "reference-verification"
    previous: list[physical._PhysicalEnvironment] = []
    with SCIENCE_LOCK:
        try:
            budget.check()
            stored = _load_reference(reference, scenario)
            science["reference_sha256"] = _REFERENCE_SHA256
            budget.check()
            stage = "candidate-verification"
            values = dict(stored["provenance"]["candidate"])
            for key in ("departure_v_infinity_m_s", "arrival_v_infinity_m_s"):
                values[key] = tuple(values[key])
            candidate = physical._verify_candidate_handoff(
                scenario, ImpulsiveTransferCandidate(**values),
                deadline_monotonic_s=budget.deadline_monotonic_s, monotonic=budget.monotonic,
            )
            science["candidate"] = asdict(candidate)
            budget.check()
            runtime = _runtime_manifest(scenario.limits.random_seed)
            if runtime != stored["provenance"]["runtime"]:
                raise ValueError("runtime/kernel identity mismatch")
            science["runtime"] = runtime

            def fresh_environment() -> physical._PhysicalEnvironment:
                budget.check()
                env = physical._build_physical_environment(candidate, scenario.spacecraft, budget=budget)
                budget.check()
                manifest = _environment_manifest(env)
                if manifest != stored["provenance"]["environment"]:
                    raise ValueError("environment/resource identity mismatch")
                if any(env is old or env.bodies is old.bodies for old in previous):
                    raise ValueError("fresh native environment required for every run")
                previous.append(env)
                science["environment"] = manifest
                return env

            stage = "boundary-and-seed-preparation"
            environment = fresh_environment()
            gm = {v.body: v.gravitational_parameter_m3_s2 for v in environment.harmonic_fields}
            initial, target = physical._build_boundary_states(scenario, candidate, gm["Moon"], gm["Mars"])
            budget.begin_control()  # Count the seed before its analytic validation.
            seed = physical._build_initial_burn_controls(scenario, candidate, gm["Moon"], gm["Mars"])
            names = ("departure_azimuth_rad", "departure_elevation_rad", "departure_duration_s",
                     "arrival_azimuth_rad", "arrival_elevation_rad", "arrival_duration_s")
            if isinstance(seed, str):
                science["rejection_counts"][seed] = 1
                raise ValueError(seed)
            if seed != tuple(stored["seed_commands"][n] for n in names):
                raise ValueError("prescribed seed mismatch")
            for state, expected in ((initial, stored["nominal"]["boundaries"][0]),
                                    (target, stored["nominal"]["target_state"])):
                if json.loads(json.dumps(asdict(state))) != expected:
                    raise ValueError("rebuilt boundary/target mismatch")
            science["seed_controls"] = seed

            def evaluate(role: str, controls: tuple[float, ...], *, tighter: bool = False) -> ResearchRun:
                nonlocal stage
                stage = role
                budget.check()
                if not tighter and role != "baseline":
                    budget.begin_control()
                entry: dict[str, Any] = {"role": role, "controls": controls, "run": None, "reason": None}
                science["runs"].append(entry)
                prepared = physical._prepare_burn_controls(
                    candidate.candidate_id, scenario.spacecraft, initial.epoch_tdb_s,
                    target.epoch_tdb_s, controls,
                )
                if isinstance(prepared, str):
                    entry["reason"] = prepared
                    science["rejection_counts"][prepared] = 1
                    raise ValueError(prepared)
                entry["controls"] = prepared
                env = environment if role == "baseline" else fresh_environment()
                expected_settings = stored["tighter" if tighter else "nominal"]["integrator_settings"]
                settings = {arc: physical._arc_integrator_profile(candidate.candidate_id, arc, tighter=tighter)
                            for arc in _ARCS}
                if json.loads(json.dumps(settings)) != expected_settings:
                    raise ValueError("integrator settings mismatch")
                run = _compose_research_run(budget, scenario, env, initial, target, prepared,
                                            tighter=tighter, register_control=False)
                entry["run"] = _run_data(run)
                if run.outcome != "completed":
                    entry["reason"] = run.reason
                    science["rejection_counts"][str(run.reason)] = 1
                    raise ValueError(run.reason)
                entry["residual"] = asdict(correction._residual(_terminal_residual(run)))
                budget.check()
                return run

            baseline = evaluate("baseline", seed)
            science["baseline_comparison"] = _compare_boundaries(_run_data(baseline), stored["nominal"])
            if not all(d["within_thresholds"] for d in science["baseline_comparison"]):
                raise ValueError("baseline drift; probes not started")
            base_residual = _terminal_residual(baseline)
            if correction._residual(base_residual).closes:
                science["outcome"] = "baseline-closed"
            else:
                probes = []
                for i, h in enumerate(correction._PROBE_STEPS):
                    controls = tuple(v + (h if j == i else 0) for j, v in enumerate(seed))
                    probes.append(_terminal_residual(evaluate(f"probe-{i}", controls)))
                stage = "correction-solve"
                update = correction._correction(base_residual, tuple(probes))
                science["correction"] = asdict(update)
                if update.control_step is None:
                    raise ValueError(update.reason)
                trial_controls = tuple(a+b for a, b in zip(seed, update.control_step))
                trial = evaluate("trial", trial_controls)
                improving, ratio, reason = correction._improvement(base_residual, _terminal_residual(trial))
                science["improvement"] = {"improving": improving, "score_ratio": ratio,
                                          "ratio_unavailable_reason": reason}
                science["outcome"] = "not-improving"
                if improving:
                    frozen = tuple(science["runs"][-1]["controls"])
                    tighter = evaluate("tighter", frozen, tighter=True)
                    differences = _compare_boundaries(_run_data(trial), _run_data(tighter))
                    science["tighter_comparison"] = differences
                    science["numerical_agreement"] = all(d["within_thresholds"] for d in differences)
                    science["outcome"] = "improving"
            budget.check()
        except (ValueError, OSError, EphemerisError, TrajectoryRefinementError) as exc:
            science["outcome"] = "aborted"
            science["reason"] = f"{stage}: {exc}"
        finally:
            budget.stopped = True
    science.update(control_attempts=budget.control_attempts,
                   propagation_evaluations=budget.propagation_evaluations,
                   attempted_arcs=budget.native_arc_propagations, completed_arcs=budget.completed_arcs)
    source = Path(__file__).parent
    return json.loads(json.dumps({"science": science,
        "source_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(source.glob("*.py"))},
        "wall_clock": {"elapsed_s": budget._last_monotonic_s - (budget.deadline_monotonic_s - 300)},
    }, allow_nan=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    scenario = load_scenario(args.scenario)
    with args.output.open("x", encoding="utf-8") as stream:
        result = _run_targeting(scenario, args.reference)
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return 1 if result["science"]["outcome"] == "aborted" else 0


if __name__ == "__main__":
    raise SystemExit(main())
