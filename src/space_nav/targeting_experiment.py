"""Private bounded D7/D8 orchestration; no production targeting or safety claim."""

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


_DAMPING_SHA256 = "c370c31f4a3dcd1f3ef324d0f2331bb46d707af0eae6d256ee935471a6c9233d"
_CONTROL_NAMES = ("departure_azimuth_rad", "departure_elevation_rad", "departure_duration_s",
                  "arrival_azimuth_rad", "arrival_elevation_rad", "arrival_duration_s")


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


@dataclass(slots=True)
class _DampingBudget(_TargetingBudget):
    tighter_started: bool = field(default=False, init=False)

    def begin_control(self) -> None:
        if self.tighter_started or self.control_attempts >= 3:
            self._fail("D8-budget", "three controls only; no controls after selection")
        _TargetingBudget.begin_control(self)

    def begin_tighter(self) -> None:
        self.check()
        if (self.stopped or self.tighter_started or self.control_attempts not in (2, 3)
                or self.propagation_evaluations != self.control_attempts
                or self.completed_arcs != self.native_arc_propagations
                or self.completed_arcs != 3 * self.control_attempts):
            self._fail("D8-budget", "one frozen run after completed trial only")
        self.tighter_started = True

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check()
        first = self.native_arc_propagations % 3 == 0
        expected_controls = self.propagation_evaluations + int(first) - int(self.tighter_started)
        if (self.stopped or self.native_arc_propagations >= 12
                or self.completed_arcs != self.native_arc_propagations
                or not isinstance(first_in_evaluation, bool) or first_in_evaluation != first
                or self.control_attempts != expected_controls):
            self._fail("D8-budget", "four ordered three-arc evaluations only; no retries")
        physical._RefinementBudget.begin_arc(self, first_in_evaluation=first_in_evaluation)


def _load_damping_reference(path: Path, stored: dict[str, Any]) -> dict[str, Any]:
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != _DAMPING_SHA256:
        raise ValueError("damping reference digest differs from Decision 0086")
    payload = json.loads(raw)
    _validate_damping_reference(payload, stored)
    return payload


def _validate_damping_reference(payload: dict[str, Any], stored: dict[str, Any]) -> None:
    """Validate imported scientific identity even after its artifact digest passes."""
    json.dumps(payload, allow_nan=False)
    data = payload["science"]
    for key, expected in (("reference_sha256", _REFERENCE_SHA256), ("outcome", "not-improving"),
                          ("scenario", stored["scenario"]), ("candidate", stored["provenance"]["candidate"]),
                          ("runtime", stored["provenance"]["runtime"]),
                          ("environment", stored["provenance"]["environment"]),
                          ("seed_controls", [stored["seed_commands"][n] for n in _CONTROL_NAMES])):
        if data[key] != expected:
            raise ValueError(f"damping reference {key} mismatch")
    if data["correction"]["rank"] != 6 or data["correction"]["reason"] is not None:
        raise ValueError("damping requires a rank-six completed correction")
    step = physical._finite_cartesian_values(data["correction"]["control_step"], "retained direction")
    if any(abs(v) > bound for v, bound in zip(step, correction._TRUST_SCALES)):
        raise ValueError("retained direction exceeds trust scales")
    baseline = data["runs"][0]
    run = baseline["run"]
    if (baseline["role"] != "baseline" or baseline["controls"] != data["seed_controls"]
            or run["outcome"] != "completed" or run["profile"] != "nominal"
            or run["integrator_settings"] != stored["nominal"]["integrator_settings"]
            or run["target_state"] != stored["nominal"]["target_state"]
            or run["boundaries"][0] != stored["nominal"]["boundaries"][0]
            or not all(d["within_thresholds"] for d in _compare_boundaries(run, stored["nominal"]))):
        raise ValueError("damping reference baseline identity mismatch")


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


def _run_targeting(
    scenario: Scenario, reference: Path, *, damping_reference: Path | None = None,
) -> dict[str, Any]:
    """One update at most; preserve diagnostics after failure, never retry."""
    damping = damping_reference is not None
    budget = (_DampingBudget if damping else _TargetingBudget)("d0001-t0035", 300.0)
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
    if damping:
        science.update(maximum_controls=3, maximum_evaluations=4, maximum_native_arcs=12,
                       expected_damping_reference_sha256=_DAMPING_SHA256,
                       damping_baseline_comparison=None, selected_alpha=None,
                       fractions=[{"alpha": a, "status": "not-started", "reason": None} for a in (0.5, 0.25)])
    stage = "reference-verification"
    previous: list[physical._PhysicalEnvironment] = []
    with SCIENCE_LOCK:
        try:
            budget.check()
            stored = _load_reference(reference, scenario)
            science["reference_sha256"] = _REFERENCE_SHA256
            budget.check()
            if damping:
                stage = "damping-reference-verification"
                retained = _load_damping_reference(damping_reference, stored)
                science.update(damping_reference_sha256=_DAMPING_SHA256,
                               imported_source_sha256=retained["source_sha256"],
                               retained_control_step=retained["science"]["correction"]["control_step"])
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
            if isinstance(seed, str):
                science["rejection_counts"][seed] = 1
                raise ValueError(seed)
            if seed != tuple(stored["seed_commands"][n] for n in _CONTROL_NAMES):
                raise ValueError("prescribed seed mismatch")
            for state, expected in ((initial, stored["nominal"]["boundaries"][0]),
                                    (target, stored["nominal"]["target_state"])):
                if json.loads(json.dumps(asdict(state))) != expected:
                    raise ValueError("rebuilt boundary/target mismatch")
            science["seed_controls"] = seed

            def evaluate(role: str, controls: tuple[float, ...], *, tighter: bool = False,
                         alpha: float | None = None) -> ResearchRun:
                nonlocal stage
                stage = role
                budget.check()
                if not tighter and role != "baseline":
                    budget.begin_control()
                if damping and tighter:
                    budget.begin_tighter()
                entry: dict[str, Any] = {"role": role, "controls": controls, "run": None, "reason": None}
                if damping:
                    entry["alpha"] = alpha
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
            if damping:
                science["damping_baseline_comparison"] = _compare_boundaries(
                    _run_data(baseline), retained["science"]["runs"][0]["run"],
                )
                if not all(d["within_thresholds"] for d in science["damping_baseline_comparison"]):
                    raise ValueError("D7 baseline drift; damping not started")
            base_residual = _terminal_residual(baseline)
            if correction._residual(base_residual).closes:
                science["outcome"] = "baseline-closed"
            elif damping:
                science["outcome"] = "not-improving"
                for fraction in science["fractions"]:
                    alpha = fraction["alpha"]
                    fraction.update(status="attempted",
                                    score_threshold=correction._residual(base_residual).score * (1-1e-4*alpha))
                    controls = tuple(v + alpha*d for v, d in zip(seed, science["retained_control_step"]))
                    trial = evaluate(f"fraction-{alpha:g}", controls, alpha=alpha)
                    improving, ratio, reason = correction._improvement(
                        base_residual, _terminal_residual(trial), alpha=alpha,
                    )
                    fraction.update(status="completed", improving=improving, score_ratio=ratio,
                                    ratio_unavailable_reason=reason)
                    if not improving:
                        continue
                    science["selected_alpha"] = alpha
                    science["improvement"] = dict(fraction)
                    frozen = tuple(science["runs"][-1]["controls"])
                    tighter = evaluate("tighter", frozen, tighter=True, alpha=alpha)
                    differences = _compare_boundaries(_run_data(trial), _run_data(tighter))
                    science["tighter_comparison"] = differences
                    science["numerical_agreement"] = all(d["within_thresholds"] for d in differences)
                    science["outcome"] = "improving"
                    break
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
            if damping:
                for fraction in science["fractions"]:
                    if fraction["status"] == "not-started":
                        fraction.update(status="skipped", reason="earlier-selection" if science["selected_alpha"]
                                        is not None else science["outcome"])
                    elif fraction["status"] == "attempted":
                        fraction.update(status="failed", reason=science["reason"])
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
    parser.add_argument("--damping-reference", type=Path, help="Opt into D8 with retained Decision 0086 JSON")
    args = parser.parse_args(argv)
    scenario = load_scenario(args.scenario)
    with args.output.open("x", encoding="utf-8") as stream:
        result = (_run_targeting(scenario, args.reference, damping_reference=args.damping_reference)
                  if args.damping_reference is not None else _run_targeting(scenario, args.reference))
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return 1 if result["science"]["outcome"] == "aborted" else 0


if __name__ == "__main__":
    raise SystemExit(main())
