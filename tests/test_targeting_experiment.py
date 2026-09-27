from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from space_nav import targeting_experiment as experiment
from space_nav import research_propagation as propagation
from space_nav.errors import TrajectoryRefinementError
from space_nav.models import FiniteBurnRecord, TrajectoryBoundaryState
from space_nav.research import ResearchProgress, ResearchRun, _ResearchBudget
from space_nav.scenario import load_scenario
from test_research_propagation import _rig


REFERENCE = Path("docs/decisions/experiments/0079-research-reference.json")
SCENARIO = Path("examples/m3_feasible_mission.toml")


def test_budget_enforces_order_caps_and_old_limits() -> None:
    budget = experiment._TargetingBudget("fixture", 300, lambda: 0)
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_arc(first_in_evaluation=True)
    for run in range(9):
        if run < 8:
            budget.begin_control()
        for arc in range(3):
            budget.begin_arc(first_in_evaluation=arc == 0)
            with pytest.raises(TrajectoryRefinementError):
                budget.begin_arc(first_in_evaluation=False)
            budget.complete_arc()
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations, budget.completed_arcs) == (8, 9, 27, 27)
    for action in (budget.begin_control, lambda: budget.begin_arc(first_in_evaluation=True)):
        with pytest.raises(TrajectoryRefinementError):
            action()
    old = _ResearchBudget("fixture", 300, lambda: 0)
    old.begin_control()
    with pytest.raises(TrajectoryRefinementError):
        old.begin_control()


@pytest.mark.parametrize("fault", ["", "event", "dry", "native", "deadline", "reset", "history-impact"])
def test_shared_composer_with_d7_budget(monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    rig = _rig(monkeypatch, fault)
    budget = experiment._TargetingBudget(rig.report.candidate_id, 300, lambda: rig.clock[0])
    for index in range(2 if not fault else 1):
        budget.begin_control()
        run = propagation._compose_research_run(
            budget, rig.report.scenario, rig.environment, rig.initial, rig.target,
            rig.report.seed_controls, tighter=False, register_control=False,
        )
        assert run.progress.attempted_arcs <= 3
        assert run.outcome == ("aborted" if fault else "completed")
        if fault:
            assert not run.boundaries and run.terminal_errors is None
            with pytest.raises(TrajectoryRefinementError):
                budget.begin_control()
        else:
            assert budget.completed_arcs == (index + 1) * 3


def _state(raw: dict[str, Any]) -> TrajectoryBoundaryState:
    return TrajectoryBoundaryState(**{**raw, "position_m": tuple(raw["position_m"]),
                                     "velocity_m_s": tuple(raw["velocity_m_s"])})


@pytest.fixture
def pipeline(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    scenario = load_scenario(SCENARIO)
    stored = experiment._load_reference(REFERENCE, scenario)
    raw = stored["nominal"]
    initial, target = _state(raw["boundaries"][0]), _state(raw["target_state"])
    seed = tuple(stored["seed_commands"][n] for n in (
        "departure_azimuth_rad", "departure_elevation_rad", "departure_duration_s",
        "arrival_azimuth_rad", "arrival_elevation_rad", "arrival_duration_s"))
    nominal = ResearchRun(
        profile="nominal", outcome="completed", reason=None, progress=ResearchProgress(3, 3),
        checked_state_count=10, check_coverage="manufactured test",
        integrator_settings_json=json.dumps(raw["integrator_settings"]),
        boundaries=tuple(_state(v) for v in raw["boundaries"]),
        boundary_masses_kg=tuple(raw["boundary_masses_kg"]),
        burns=tuple(FiniteBurnRecord(**{**v, "direction_tnw": tuple(v["direction_tnw"])}) for v in raw["burns"]),
        target_state=target,
    )
    rig = SimpleNamespace(scenario=scenario, stored=stored, seed=seed, calls=[], budgets=[], envs=[],
                          failure="", clock=[0.0])
    original_budget = experiment._TargetingBudget

    def budget(*args: Any) -> Any:
        value = original_budget(*args, monotonic=lambda: rig.clock[0])
        rig.budgets.append(value)
        return value

    def build(*args: Any, **kwargs: Any) -> Any:
        assert kwargs["budget"] is rig.budgets[0]
        env = SimpleNamespace(bodies=object(), harmonic_fields=tuple(
            SimpleNamespace(**v) for v in stored["provenance"]["environment"]["harmonic_fields"]))
        if rig.failure == "reuse" and rig.envs:
            env = rig.envs[0]
        rig.envs.append(env)
        return env

    def compose(budget: Any, scenario: Any, env: Any, start: Any, end: Any,
                controls: tuple[float, ...], *, tighter: bool, register_control: bool) -> ResearchRun:
        assert start == initial and end == target and not register_control
        index = len(rig.calls)
        rig.calls.append((controls, tighter, env))
        assert budget.control_attempts == min(index + 1, 8)
        if rig.failure == f"run-{index}":
            budget.begin_arc(first_in_evaluation=True)
            return ResearchRun(profile="tighter" if tighter else "nominal", outcome="aborted",
                reason="manufactured failure", progress=ResearchProgress(1, 0),
                checked_state_count=1, check_coverage="manufactured",
                integrator_settings_json=nominal.integrator_settings_json)
        for arc in range(3):
            budget.begin_arc(first_in_evaluation=arc == 0)
            budget.complete_arc()
        states = list(nominal.boundaries)
        epochs = (initial.epoch_tdb_s, initial.epoch_tdb_s + controls[2],
                  target.epoch_tdb_s-controls[5], target.epoch_tdb_s)
        states = [replace(s, epoch_tdb_s=t) for s, t in zip(states, epochs)]
        if index == 0 and rig.failure == "baseline":
            states[1] = replace(states[1], position_m=(states[1].position_m[0]+20, *states[1].position_m[1:]))
        if index >= 7:
            factor = 2 if rig.failure == "not-improving" else 0.5
            states[-1] = replace(states[-1],
                position_m=tuple(b + factor*(a-b) for a, b in zip(states[-1].position_m, target.position_m)),
                velocity_m_s=tuple(b + factor*(a-b) for a, b in zip(states[-1].velocity_m_s, target.velocity_m_s)))
            if tighter and rig.failure == "disagreement":
                states[-1] = replace(states[-1], position_m=(states[-1].position_m[0]+20, *states[-1].position_m[1:]))
        mass0 = scenario.spacecraft.initial_mass_kg
        exhaust = 9.80665 * scenario.spacecraft.isp_s
        rate = scenario.spacecraft.max_thrust_n / exhaust
        mass1 = mass0 - (epochs[1]-epochs[0]) * rate
        mass2 = mass1 - (epochs[3]-epochs[2]) * rate
        masses = (mass0, mass1, mass1, mass2)
        burns = tuple(replace(b, start_epoch_tdb_s=epochs[i], end_epoch_tdb_s=epochs[i+1],
                              initial_mass_kg=masses[i], final_mass_kg=masses[i+1],
                              propellant_mass_kg=masses[i]-masses[i+1],
                              ideal_equivalent_delta_v_m_s=exhaust*math.log(masses[i]/masses[i+1]))
                      for b, i in zip(nominal.burns, (0, 2)))
        if rig.failure == "deadline" and index == 0:
            rig.clock[0] = 300
        return replace(nominal, profile="tighter" if tighter else "nominal", boundaries=tuple(states),
                       burns=burns, boundary_masses_kg=masses)

    monkeypatch.setattr(experiment, "_TargetingBudget", budget)
    monkeypatch.setattr(experiment.physical, "_verify_candidate_handoff", lambda scenario, candidate, **kw: candidate)
    monkeypatch.setattr(experiment, "_runtime_manifest", lambda seed: stored["provenance"]["runtime"])
    monkeypatch.setattr(experiment.physical, "_build_physical_environment", build)
    monkeypatch.setattr(experiment, "_environment_manifest", lambda env: stored["provenance"]["environment"])
    monkeypatch.setattr(experiment.physical, "_build_boundary_states", lambda *a: (initial, target))
    monkeypatch.setattr(experiment.physical, "_build_initial_burn_controls", lambda *a: seed)
    monkeypatch.setattr(experiment, "_compose_research_run", compose)
    monkeypatch.setattr(experiment.correction, "_correction", lambda *a: experiment.correction._Correction(
        (), (), 0 if rig.failure == "rank" else 6, (),
        None if rig.failure == "rank" else (0.0001, 0, 0, 0, 0, 0),
        "rank-deficient" if rig.failure == "rank" else None))
    return rig


@pytest.mark.parametrize("failure,count,outcome", [
    ("", 9, "improving"), ("not-improving", 8, "not-improving"),
    ("baseline", 1, "aborted"), ("reuse", 1, "aborted"), ("rank", 7, "aborted"),
    ("deadline", 1, "aborted"), ("disagreement", 9, "improving"),
    *[(f"run-{i}", i+1, "aborted") for i in range(9)],
])
def test_pipeline_stops_and_preserves_evidence(pipeline: SimpleNamespace, failure: str,
                                              count: int, outcome: str) -> None:
    pipeline.failure = failure
    result = experiment._run_targeting(pipeline.scenario, REFERENCE)
    s = result["science"]
    assert s["outcome"] == outcome, s["reason"]
    assert len(pipeline.calls) == count
    assert len(pipeline.budgets) == 1 and pipeline.budgets[0].stopped
    assert s["attempted_arcs"] <= 27 and s["control_attempts"] <= 8
    assert not s["continuous_safety_verified"]
    if not failure or failure == "disagreement":
        assert s["numerical_agreement"] == (not failure)
        assert s["improvement"]["improving"]
        assert pipeline.calls[-1][0] == pipeline.calls[-2][0]
        assert s["control_attempts"] == 8 and s["propagation_evaluations"] == 9
        for i in range(6):
            probe = pipeline.calls[i+1][0]
            expected = tuple(v + (experiment.correction._PROBE_STEPS[i] if j == i else 0)
                             for j, v in enumerate(pipeline.seed))
            assert probe == pytest.approx(expected)
    if failure == "run-8":
        assert s["improvement"]["improving"] and s["numerical_agreement"] is None
        assert s["runs"][-1]["run"]["boundaries"] == []
    json.dumps(result, allow_nan=False)


def test_reference_rejection_and_output_preservation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    result = experiment._run_targeting(load_scenario(SCENARIO), bad)
    assert result["science"]["attempted_arcs"] == 0
    assert "reference digest" in result["science"]["reason"]
    calls = []
    monkeypatch.setattr(experiment, "_run_targeting", lambda *a: calls.append(a) or result)
    output = tmp_path / "output.json"
    argv = [str(SCENARIO), str(bad), str(output)]
    assert experiment.main(argv) == 1
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        experiment.main(argv)
    assert len(calls) == 1 and output.read_bytes() == before


@pytest.mark.parametrize("fault", ["runtime", "resource", "seed", "target", "settings"])
def test_preparation_mismatch_never_launches(pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch,
                                            fault: str) -> None:
    if fault == "runtime":
        monkeypatch.setattr(experiment, "_runtime_manifest", lambda *a: {})
    elif fault == "resource":
        monkeypatch.setattr(experiment, "_environment_manifest", lambda *a: {})
    elif fault == "seed":
        monkeypatch.setattr(experiment.physical, "_build_initial_burn_controls", lambda *a: "rejected-dry-mass")
    elif fault == "target":
        original = experiment.physical._build_boundary_states
        def changed(*args: Any) -> Any:
            initial, target = original(*args)
            return initial, replace(target, position_m=(0, 0, 0))
        monkeypatch.setattr(experiment.physical, "_build_boundary_states", changed)
    else:
        monkeypatch.setattr(experiment.physical, "_arc_integrator_profile", lambda *a, **kw: {})
    science = experiment._run_targeting(pipeline.scenario, REFERENCE)["science"]
    assert science["outcome"] == "aborted" and science["attempted_arcs"] == 0
    assert not pipeline.calls
    if fault == "seed":
        assert science["control_attempts"] == 1
        assert science["rejection_counts"] == {"rejected-dry-mass": 1}


@pytest.mark.parametrize("attempt", [2, 8])
def test_analytic_probe_or_trial_rejection_counts_without_native_launch(
    pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, attempt: int,
) -> None:
    original = experiment.physical._prepare_burn_controls
    calls = []
    def reject(*args: Any) -> Any:
        calls.append(args)
        return "rejected-control-bounds" if len(calls) == attempt else original(*args)
    monkeypatch.setattr(experiment.physical, "_prepare_burn_controls", reject)
    science = experiment._run_targeting(pipeline.scenario, REFERENCE)["science"]
    assert science["outcome"] == "aborted"
    assert science["control_attempts"] == attempt
    assert science["propagation_evaluations"] == attempt-1
    assert len(pipeline.calls) == attempt-1
    assert science["runs"][-1]["run"] is None
    assert science["rejection_counts"] == {"rejected-control-bounds": 1}


def test_already_closed_baseline_stops_before_probes(pipeline: SimpleNamespace,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    original = experiment.correction._residual
    monkeypatch.setattr(experiment.correction, "_residual", lambda v: replace(original(v), closes=True))
    science = experiment._run_targeting(pipeline.scenario, REFERENCE)["science"]
    assert science["outcome"] == "baseline-closed"
    assert len(pipeline.calls) == 1 and science["numerical_agreement"] is None


def test_expired_clock_before_preparation_launches_nothing(pipeline: SimpleNamespace,
                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    original = experiment._load_reference
    def expired(*args: Any) -> Any:
        result = original(*args)
        pipeline.clock[0] = 300
        return result
    monkeypatch.setattr(experiment, "_load_reference", expired)
    science = experiment._run_targeting(pipeline.scenario, REFERENCE)["science"]
    assert science["outcome"] == "aborted" and not pipeline.envs
    assert science["control_attempts"] == science["attempted_arcs"] == 0
