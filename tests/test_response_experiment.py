from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from space_nav import targeting_experiment as experiment
from space_nav.errors import TrajectoryRefinementError
from space_nav.models import FiniteBurnRecord
from space_nav.research import ResearchProgress, ResearchRun
from space_nav.scenario import load_scenario
from test_targeting_experiment import REFERENCE, SCENARIO, _state, pipeline as d7_pipeline
from test_damping_experiment import DAMPING
from test_research_propagation import _rig


def test_response_budget_enforces_pairs_caps_and_deadline() -> None:
    clock = [0.]
    budget = experiment._ResponseBudget("fixture", 300, lambda: clock[0])
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_arc(first_in_evaluation=True)
    for _ in range(5):
        budget.begin_control()
        for profile in range(2):
            for arc in range(3):
                budget.begin_arc(first_in_evaluation=arc == 0)
                with pytest.raises(TrajectoryRefinementError):
                    budget.begin_arc(first_in_evaluation=False)
                budget.complete_arc()
            if profile == 0:
                with pytest.raises(TrajectoryRefinementError):
                    budget.begin_control()
    assert (budget.control_attempts, budget.propagation_evaluations, budget.completed_arcs) == (5, 10, 30)
    for action in (budget.begin_control, lambda: budget.begin_arc(first_in_evaluation=True)):
        with pytest.raises(TrajectoryRefinementError):
            action()
    clock[0] = 300
    with pytest.raises(TrajectoryRefinementError):
        budget.check()


@pytest.fixture
def pipeline(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    original_targeting = experiment._TargetingBudget
    rig = d7_pipeline.__wrapped__(monkeypatch)
    monkeypatch.setattr(experiment, "_TargetingBudget", original_targeting)
    original_budget = experiment._ResponseBudget
    def budget(*args: Any) -> Any:
        value = original_budget(*args, monotonic=lambda: rig.clock[0])
        rig.budgets.append(value)
        return value
    monkeypatch.setattr(experiment, "_ResponseBudget", budget)

    def compose(budget: Any, scenario: Any, env: Any, start: Any, end: Any,
                controls: tuple[float, ...], *, tighter: bool, register_control: bool) -> ResearchRun:
        index = len(rig.calls)
        assert not register_control and tighter == bool(index % 2)
        assert budget.control_attempts == index//2+1
        assert end == _state(rig.stored["nominal"]["target_state"])
        rig.calls.append((controls, tighter, env))
        raw = rig.stored["tighter" if tighter else "nominal"]
        if rig.failure == f"run-{index}":
            budget.begin_arc(first_in_evaluation=True)
            return ResearchRun(profile="tighter" if tighter else "nominal", outcome="aborted",
                               reason="manufactured native failure", progress=ResearchProgress(1, 0),
                               checked_state_count=1, check_coverage="manufactured",
                               integrator_settings_json=json.dumps(raw["integrator_settings"]))
        for arc in range(3):
            budget.begin_arc(first_in_evaluation=arc == 0)
            budget.complete_arc()
        states = [_state(v) for v in raw["boundaries"]]
        epochs = (start.epoch_tdb_s, start.epoch_tdb_s+controls[2], end.epoch_tdb_s-controls[5], end.epoch_tdb_s)
        states = [replace(s, epoch_tdb_s=t) for s, t in zip(states, epochs)]
        if rig.failure == ("tighter-baseline" if tighter else "baseline") and index < 2:
            states[1] = replace(states[1], position_m=(states[1].position_m[0]+20, *states[1].position_m[1:]))
        mass0 = scenario.spacecraft.initial_mass_kg
        rate = scenario.spacecraft.max_thrust_n/(9.80665*scenario.spacecraft.isp_s)
        mass1 = mass0 - (epochs[1]-epochs[0])*rate
        mass2 = mass1 - (epochs[3]-epochs[2])*rate
        masses = (mass0, mass1, mass1, mass2)
        burns = tuple(replace(FiniteBurnRecord(**{**b, "direction_tnw": tuple(b["direction_tnw"])}),
                              start_epoch_tdb_s=epochs[i], end_epoch_tdb_s=epochs[i+1],
                              initial_mass_kg=masses[i], final_mass_kg=masses[i+1],
                              propellant_mass_kg=masses[i]-masses[i+1],
                              ideal_equivalent_delta_v_m_s=9.80665*scenario.spacecraft.isp_s
                              * math.log(masses[i]/masses[i+1])) for b, i in zip(raw["burns"], (0, 2)))
        if rig.failure == "deadline" and index == 0:
            rig.clock[0] = 300
        return ResearchRun(profile="tighter" if tighter else "nominal", outcome="completed", reason=None,
                           progress=ResearchProgress(3, 3), checked_state_count=10,
                           check_coverage="manufactured", integrator_settings_json=json.dumps(raw["integrator_settings"]),
                           boundaries=tuple(states), boundary_masses_kg=masses, burns=burns, target_state=end)
    monkeypatch.setattr(experiment, "_compose_research_run", compose)
    monkeypatch.setattr(experiment.correction, "_correction", lambda *a: pytest.fail("D9 must not solve"))
    return rig


def test_independent_commands_profiles_targets_and_accounting(pipeline: SimpleNamespace) -> None:
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, response_reference=DAMPING)["science"]
    assert s["outcome"] == "completed", s["reason"]
    assert (s["control_attempts"], s["propagation_evaluations"], s["attempted_arcs"], s["completed_arcs"]) == (5, 10, 30, 30)
    assert len({id(env.bodies) for env in pipeline.envs}) == 10
    assert len(pipeline.budgets) == 1 and pipeline.budgets[0].stopped
    for i, alpha in enumerate(experiment.response._ALPHAS):
        nominal, tighter = s["runs"][2*i:2*i+2]
        assert nominal["alpha"] == tighter["alpha"] == alpha
        assert nominal["controls"] == tighter["controls"]
        assert nominal["controls"] == [v+alpha*d for v, d in zip(pipeline.seed, s["retained_control_step"])]
        assert nominal["run"]["profile"] == "nominal" and tighter["run"]["profile"] == "tighter"
    assert not all(d["within_thresholds"] for d in s["baseline_profile_comparison"])
    assert s["selected_alpha"] is s["correction"] is s["improvement"] is None
    assert not s["continuous_safety_verified"] and s["response_unavailable_reason"] is None
    assert len(s["response_diagnostics"]["checks"]) == 12
    assert not s["response_diagnostics"]["consistent"]  # Constant fixture contradicts nonzero g.
    json.dumps(s, allow_nan=False)


@pytest.mark.parametrize("failure,count", [("baseline", 1), ("tighter-baseline", 2), ("reuse", 1),
                                         ("deadline", 1), *[(f"run-{i}", i+1) for i in range(10)]])
def test_failure_stops_without_retry_or_partial_endpoint(pipeline: SimpleNamespace, failure: str, count: int) -> None:
    pipeline.failure = failure
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, response_reference=DAMPING)["science"]
    assert s["outcome"] == "aborted" and len(pipeline.calls) == count
    assert s["response_diagnostics"] is None and s["response_unavailable_reason"] == s["reason"]
    assert s["selected_alpha"] is None and s["automatic_retries"] == 0
    if failure.startswith("run-"):
        assert not s["runs"][-1]["run"]["boundaries"]
    assert s["attempted_arcs"] <= 30 and s["control_attempts"] <= 5


@pytest.mark.parametrize("fault", ["event", "dry", "native", "deadline", "reset", "history-impact"])
def test_d9_reuses_native_composer_failure_guards(monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    rig = _rig(monkeypatch, fault)
    budget = experiment._ResponseBudget(rig.report.candidate_id, 300, lambda: rig.clock[0])
    budget.begin_control()
    run = experiment._compose_research_run(budget, rig.report.scenario, rig.environment,
        rig.initial, rig.target, rig.report.seed_controls, tighter=False, register_control=False)
    assert run.outcome == "aborted" and not run.boundaries
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_arc(first_in_evaluation=True)


@pytest.mark.parametrize("attempt", [2, 4, 6, 8])
def test_analytic_rejection_counts_before_launch(pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch,
                                               attempt: int) -> None:
    original = experiment.physical._prepare_burn_controls
    calls = []
    def reject(*args: Any) -> Any:
        calls.append(args)
        return "rejected-control-bounds" if len(calls) == attempt+1 else original(*args)
    monkeypatch.setattr(experiment.physical, "_prepare_burn_controls", reject)
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, response_reference=DAMPING)["science"]
    assert s["outcome"] == "aborted" and len(pipeline.calls) == attempt
    assert s["control_attempts"] == attempt//2+1 and s["runs"][-1]["run"] is None
    assert s["rejection_counts"] == {"rejected-control-bounds": 1}


def test_zero_direction_stops_before_propagation(pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    original = experiment._load_damping_reference
    def zero(*args: Any) -> Any:
        value = deepcopy(original(*args))
        value["science"]["correction"]["jacobian"] = [[0.]*6]*6
        return value
    monkeypatch.setattr(experiment, "_load_damping_reference", zero)
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, response_reference=DAMPING)["science"]
    assert "zero-predicted" in s["reason"] and not pipeline.calls
    assert s["attempted_arcs"] == 0 and s["control_attempts"] == 0


def test_closed_seed_does_not_skip_response_study(pipeline: SimpleNamespace,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    original = experiment.correction._residual
    monkeypatch.setattr(experiment.correction, "_residual", lambda v: replace(original(v), closes=True))
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, response_reference=DAMPING)["science"]
    assert s["outcome"] == "completed" and len(pipeline.calls) == 10
    assert s["selected_alpha"] is None


@pytest.mark.parametrize("fault", ["runtime", "resource", "seed", "target", "settings"])
def test_preparation_mismatch_prevents_native_launch(pipeline: SimpleNamespace,
                                                   monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    if fault == "runtime":
        monkeypatch.setattr(experiment, "_runtime_manifest", lambda seed: {})
    elif fault == "resource":
        monkeypatch.setattr(experiment, "_environment_manifest", lambda env: {})
    elif fault == "seed":
        monkeypatch.setattr(experiment.physical, "_build_initial_burn_controls", lambda *a: (1.,)*6)
    elif fault == "target":
        original = experiment.physical._build_boundary_states
        def changed(*args: Any) -> Any:
            initial, target = original(*args)
            return initial, replace(target, position_m=(target.position_m[0]+1, *target.position_m[1:]))
        monkeypatch.setattr(experiment.physical, "_build_boundary_states", changed)
    else:
        monkeypatch.setattr(experiment.physical, "_arc_integrator_profile", lambda *a, **kw: {})
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, response_reference=DAMPING)["science"]
    assert s["outcome"] == "aborted" and s["attempted_arcs"] == 0
    assert not pipeline.calls


def test_nonfinite_response_arithmetic_stops_with_retained_runs(pipeline: SimpleNamespace,
                                                               monkeypatch: pytest.MonkeyPatch) -> None:
    def failed(*args: Any) -> Any:
        raise ValueError("nonfinite manufactured arithmetic")
    monkeypatch.setattr(experiment.response, "_response_diagnostics", failed)
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, response_reference=DAMPING)["science"]
    assert s["outcome"] == "aborted" and s["completed_arcs"] == 30
    assert s["response_diagnostics"] is None and "response-arithmetic" in s["reason"]
    assert len(s["runs"]) == 10 and all(e["run"]["outcome"] == "completed" for e in s["runs"])


def test_import_deadline_covers_verification(pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    original = experiment._load_damping_reference
    def expired(*args: Any) -> Any:
        result = original(*args)
        pipeline.clock[0] = 300
        return result
    monkeypatch.setattr(experiment, "_load_damping_reference", expired)
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, response_reference=DAMPING)["science"]
    assert s["outcome"] == "aborted" and s["attempted_arcs"] == 0 and not pipeline.envs


def test_cli_modes_binding_and_exclusive_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = tmp_path/"bad.json"
    bad.write_text("{}")
    result = experiment._run_targeting(load_scenario(SCENARIO), REFERENCE, response_reference=bad)
    assert result["science"]["attempted_arcs"] == 0
    calls = []
    monkeypatch.setattr(experiment, "_run_targeting", lambda *a, **kw: calls.append(kw) or result)
    output = tmp_path/"evidence.json"
    argv = [str(SCENARIO), str(REFERENCE), str(output), "--response-reference", str(bad)]
    assert experiment.main(argv) == 1
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        experiment.main(argv)
    assert calls == [{"response_reference": bad}] and output.read_bytes() == before
    with pytest.raises(SystemExit) as exc:
        experiment.main([*argv, "--damping-reference", str(DAMPING)])
    assert exc.value.code == 2
