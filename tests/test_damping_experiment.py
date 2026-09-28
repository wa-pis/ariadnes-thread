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
from space_nav.scenario import load_scenario
from test_targeting_experiment import REFERENCE, SCENARIO, pipeline as d7_pipeline
from test_research_propagation import _rig


DAMPING = Path("docs/adr/experiments/0086-targeting-study.json")


@pytest.mark.parametrize("trials", [1, 2])
def test_local_budget_supports_early_selection_and_stops_after_tighter(trials: int) -> None:
    budget = experiment._DampingBudget("fixture", 300, lambda: 0)
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_tighter()
    for _ in range(trials + 1):
        budget.begin_control()
        for arc in range(3):
            budget.begin_arc(first_in_evaluation=arc == 0)
            with pytest.raises(TrajectoryRefinementError):
                budget.begin_arc(first_in_evaluation=False)
            budget.complete_arc()
    budget.begin_tighter()
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_control()
    for arc in range(3):
        budget.begin_arc(first_in_evaluation=arc == 0)
        budget.complete_arc()
    assert budget.control_attempts == trials + 1
    assert budget.propagation_evaluations == trials + 2
    assert budget.native_arc_propagations == (trials + 2)*3 <= 12
    for action in (budget.begin_control, budget.begin_tighter,
                   lambda: budget.begin_arc(first_in_evaluation=True)):
        with pytest.raises(TrajectoryRefinementError):
            action()


@pytest.mark.parametrize("alpha", [0.5, 0.25])
def test_fraction_decrease_threshold_and_closure(alpha: float) -> None:
    base = (2000.0, 0, 0, 0, 0, 0)
    threshold = 2000 * (1 - 1e-4*alpha)
    assert experiment.correction._improvement(base, (threshold, 0, 0, 0, 0, 0), alpha=alpha)[0]
    assert not experiment.correction._improvement(base, (threshold+1e-8, 0, 0, 0, 0, 0), alpha=alpha)[0]
    assert not experiment.correction._improvement(base, (threshold, 0, 0, 0, 0, 0))[0]
    assert experiment.correction._improvement((1000.1, 0, 0, 0, 0, 0),
                                             (1000, 0, 0, 0.01, 0, 0), alpha=alpha)[0]
    assert experiment.correction._improvement((0,)*6, (0,)*6, alpha=alpha)[1:] == (None, "zero-baseline-score")
    for bad in (True, 0, -1, 0.1, math.nan, math.inf):
        with pytest.raises(ValueError):
            experiment.correction._improvement(base, base, alpha=bad)


@pytest.mark.parametrize("fault", ["scenario", "candidate", "runtime", "environment", "seed_controls",
                                   "rank", "direction", "target", "settings", "epoch"])
def test_imported_identity_and_direction_rejected(fault: str) -> None:
    stored = experiment._load_reference(REFERENCE, load_scenario(SCENARIO))
    payload = experiment._load_damping_reference(DAMPING, stored)
    data = deepcopy(payload)
    s = data["science"]
    if fault in ("scenario", "candidate", "runtime", "environment", "seed_controls"):
        s[fault] = None
    elif fault == "rank":
        s["correction"]["rank"] = 5
    elif fault == "direction":
        s["correction"]["control_step"][0] = 0.26
    elif fault == "target":
        s["runs"][0]["run"]["target_state"]["position_m"][0] += 1
    elif fault == "settings":
        s["runs"][0]["run"]["integrator_settings"] = {}
    else:
        s["runs"][0]["run"]["boundaries"][1]["epoch_tdb_s"] += 1
    with pytest.raises(ValueError):
        experiment._validate_damping_reference(data, stored)


@pytest.fixture
def pipeline(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    original_targeting = experiment._TargetingBudget
    rig = d7_pipeline.__wrapped__(monkeypatch)
    monkeypatch.setattr(experiment, "_TargetingBudget", original_targeting)
    original_budget = experiment._DampingBudget
    def budget(*args: Any) -> Any:
        result = original_budget(*args, monotonic=lambda: rig.clock[0])
        rig.budgets.append(result)
        return result
    monkeypatch.setattr(experiment, "_DampingBudget", budget)
    original_compose = experiment._compose_research_run
    rig.selection = 0.5
    def compose(*args: Any, **kwargs: Any) -> Any:
        index = len(rig.calls)
        run = original_compose(*args, **kwargs)
        if run.outcome != "completed" or index == 0:
            return run
        improving = rig.selection is not None and (rig.selection == 0.5 or index >= 2)
        factor = 0.5 if improving else 2.0
        end, target = run.boundaries[-1], run.target_state
        end = replace(end,
            position_m=tuple(b+factor*(a-b) for a, b in zip(end.position_m, target.position_m)),
            velocity_m_s=tuple(b+factor*(a-b) for a, b in zip(end.velocity_m_s, target.velocity_m_s)))
        if kwargs["tighter"] and rig.failure == "disagreement":
            end = replace(end, position_m=(end.position_m[0]+20, *end.position_m[1:]))
        return replace(run, boundaries=(*run.boundaries[:-1], end))
    monkeypatch.setattr(experiment, "_compose_research_run", compose)
    def no_solve(*args: Any) -> Any:
        pytest.fail("D8 must not solve a new correction")
    monkeypatch.setattr(experiment.correction, "_correction", no_solve)
    return rig


@pytest.mark.parametrize("selection,count", [(0.5, 3), (0.25, 4), (None, 3)])
def test_order_independent_commands_selection_and_frozen_validation(pipeline: SimpleNamespace,
                                                                   selection: float | None, count: int) -> None:
    pipeline.selection = selection
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, damping_reference=DAMPING)["science"]
    assert s["outcome"] == ("improving" if selection else "not-improving"), s["reason"]
    assert len(pipeline.calls) == count and s["selected_alpha"] == selection
    assert s["numerical_agreement"] is (True if selection else None)
    assert len(pipeline.budgets) == 1 and pipeline.budgets[0].stopped
    assert len({id(env.bodies) for env in pipeline.envs}) == count
    for i, alpha in enumerate((0.5,) if selection == 0.5 else (0.5, 0.25), 1):
        assert s["runs"][i]["controls"] == [a+alpha*d for a, d in zip(pipeline.seed, s["retained_control_step"])]
        assert s["runs"][i]["alpha"] == alpha
        assert s["fractions"][i-1]["score_threshold"] == s["runs"][0]["residual"]["score"]*(1-1e-4*alpha)
    if selection:
        assert s["runs"][-1]["controls"] == s["runs"][-2]["controls"]
    if selection == 0.5:
        assert s["fractions"][1] == {"alpha": 0.25, "status": "skipped", "reason": "earlier-selection"}
    json.dumps(s, allow_nan=False)


@pytest.mark.parametrize("failure,count", [("baseline", 1), ("reuse", 1), ("deadline", 1),
                                          ("run-0", 1), ("run-1", 2), ("run-2", 3),
                                          ("disagreement", 3)])
def test_failure_or_disagreement_never_falls_back(pipeline: SimpleNamespace, failure: str, count: int) -> None:
    pipeline.failure = failure
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, damping_reference=DAMPING)["science"]
    assert len(pipeline.calls) == count
    assert s["outcome"] == ("improving" if failure == "disagreement" else "aborted")
    assert s["fractions"][1]["status"] == "skipped"
    if failure in ("run-2", "disagreement"):
        assert s["selected_alpha"] == 0.5 and s["improvement"]["improving"]
        assert s["numerical_agreement"] is (False if failure == "disagreement" else None)
    assert s["attempted_arcs"] <= 12


@pytest.mark.parametrize("fault", ["event", "dry", "native", "deadline", "reset"])
def test_d8_reuses_composer_guards(monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    rig = _rig(monkeypatch, fault)
    budget = experiment._DampingBudget(rig.report.candidate_id, 300, lambda: rig.clock[0])
    budget.begin_control()
    run = experiment._compose_research_run(budget, rig.report.scenario, rig.environment,
        rig.initial, rig.target, rig.report.seed_controls, tighter=False, register_control=False)
    assert run.outcome == "aborted" and not run.boundaries
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_control()


def test_bad_artifact_and_exclusive_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    result = experiment._run_targeting(load_scenario(SCENARIO), REFERENCE, damping_reference=bad)
    assert result["science"]["attempted_arcs"] == 0
    assert "damping reference digest" in result["science"]["reason"]
    calls = []
    monkeypatch.setattr(experiment, "_run_targeting", lambda *a, **kw: calls.append(kw) or result)
    output = tmp_path / "evidence.json"
    argv = [str(SCENARIO), str(REFERENCE), str(output), "--damping-reference", str(bad)]
    assert experiment.main(argv) == 1
    with pytest.raises(FileExistsError):
        experiment.main(argv)
    assert calls == [{"damping_reference": bad}]


@pytest.mark.parametrize("attempt", [2, 3])
def test_analytic_rejection_counts_and_stops(pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch,
                                            attempt: int) -> None:
    pipeline.selection = None
    original = experiment.physical._prepare_burn_controls
    calls = []
    def reject(*args: Any) -> Any:
        calls.append(args)
        return "rejected-control-bounds" if len(calls) == attempt else original(*args)
    monkeypatch.setattr(experiment.physical, "_prepare_burn_controls", reject)
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, damping_reference=DAMPING)["science"]
    assert s["outcome"] == "aborted" and s["control_attempts"] == attempt
    assert len(pipeline.calls) == s["propagation_evaluations"] == attempt-1
    assert s["runs"][-1]["run"] is None and s["fractions"][attempt-2]["status"] == "failed"
    assert s["rejection_counts"] == {"rejected-control-bounds": 1}


def test_quarter_tighter_failure_does_not_erase_selection(pipeline: SimpleNamespace) -> None:
    pipeline.selection, pipeline.failure = 0.25, "run-3"
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, damping_reference=DAMPING)["science"]
    assert s["outcome"] == "aborted" and s["selected_alpha"] == 0.25
    assert s["improvement"]["improving"] and s["numerical_agreement"] is None
    assert len(pipeline.calls) == 4 and s["attempted_arcs"] == 10
    assert s["runs"][-1]["run"]["boundaries"] == []


def test_closed_baseline_skips_both_fractions(pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    original = experiment.correction._residual
    monkeypatch.setattr(experiment.correction, "_residual", lambda v: replace(original(v), closes=True))
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, damping_reference=DAMPING)["science"]
    assert s["outcome"] == "baseline-closed" and len(pipeline.calls) == 1
    assert all(f["status"] == "skipped" and f["reason"] == "baseline-closed" for f in s["fractions"])


def test_single_deadline_covers_import_verification(pipeline: SimpleNamespace,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    original = experiment._load_damping_reference
    def expired(*args: Any) -> Any:
        result = original(*args)
        pipeline.clock[0] = 300
        return result
    monkeypatch.setattr(experiment, "_load_damping_reference", expired)
    s = experiment._run_targeting(pipeline.scenario, REFERENCE, damping_reference=DAMPING)["science"]
    assert s["outcome"] == "aborted" and s["attempted_arcs"] == 0
    assert not pipeline.envs and s["control_attempts"] == 0
