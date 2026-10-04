from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from space_nav import targeting_experiment as experiment
from space_nav.errors import TrajectoryRefinementError
from space_nav.scenario import load_scenario
from test_damping_experiment import pipeline as damping_pipeline
from test_targeting_experiment import REFERENCE, SCENARIO
from test_research_propagation import _rig


CENTRAL = Path("docs/adr/experiments/0095-central-column-study.json")


@pytest.fixture
def pipeline(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    original = experiment._DampingBudget
    rig = damping_pipeline.__wrapped__(monkeypatch)
    monkeypatch.setattr(experiment, "_DampingBudget", original)
    budget_type = experiment._CentralBudget
    def budget(*args: Any) -> Any:
        result = budget_type(*args, monotonic=lambda: rig.clock[0])
        rig.budgets.append(result)
        return result
    monkeypatch.setattr(experiment, "_CentralBudget", budget)
    return rig


@pytest.mark.parametrize("selection,count", [(0.5, 3), (None, 2)])
def test_single_trial_and_conditional_frozen_tighter(pipeline: SimpleNamespace,
                                                    selection: float | None, count: int) -> None:
    pipeline.selection = selection
    science = experiment._run_targeting(pipeline.scenario, REFERENCE,
                                       central_reference=CENTRAL)["science"]
    assert science["outcome"] == ("improving" if selection else "not-improving"), science["reason"]
    assert len(pipeline.calls) == count
    assert science["attempted_arcs"] == count*3
    assert science["runs"][1]["controls"] == [a+b for a, b in zip(
        pipeline.seed, science["correction"]["control_step"])]
    if selection:
        assert science["runs"][2]["controls"] == science["runs"][1]["controls"]
    assert len({id(env.bodies) for env in pipeline.envs}) == count
    json.dumps(science, allow_nan=False)


@pytest.mark.parametrize("failure,count", [("baseline", 1), ("reuse", 1), ("deadline", 1),
    ("run-0", 1), ("run-1", 2), ("run-2", 3), ("disagreement", 3)])
def test_failures_stop_without_retry(pipeline: SimpleNamespace, failure: str, count: int) -> None:
    pipeline.failure = failure
    science = experiment._run_targeting(pipeline.scenario, REFERENCE,
                                       central_reference=CENTRAL)["science"]
    assert len(pipeline.calls) == count
    assert science["outcome"] == ("improving" if failure == "disagreement" else "aborted")
    if failure in ("run-2", "disagreement"):
        assert science["improvement"]["improving"]
        assert science["numerical_agreement"] is (False if failure == "disagreement" else None)
    assert science["attempted_arcs"] <= 9


@pytest.mark.parametrize("field", ["scenario", "candidate", "runtime", "environment", "seed_controls"])
def test_imported_identity_rejected(field: str) -> None:
    stored = experiment._load_reference(REFERENCE, load_scenario(SCENARIO))
    payload = deepcopy(experiment._load_central_reference(CENTRAL, stored))
    payload["science"][field] = None
    with pytest.raises(ValueError):
        experiment._validate_central_reference(payload, stored)


def test_budget_limits_and_tighter_order() -> None:
    budget = experiment._CentralBudget("fixture", 300, lambda: 0)
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_tighter()
    for _ in range(2):
        budget.begin_control()
        for arc in range(3):
            budget.begin_arc(first_in_evaluation=arc == 0)
            budget.complete_arc()
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_control()
    budget.begin_tighter()
    for arc in range(3):
        budget.begin_arc(first_in_evaluation=arc == 0)
        budget.complete_arc()
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_arc(first_in_evaluation=True)
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations) == (2, 3, 9)


@pytest.mark.parametrize("reason", ["rank-deficient", "zero-control-step", "no-predicted-decrease"])
def test_solve_guard_retains_diagnostic_without_trial(pipeline: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch, reason: str) -> None:
    calls = []
    def solve(*args: Any) -> dict[str, Any]:
        calls.append(args)
        return {"reason": reason, "control_step": None}
    monkeypatch.setattr(experiment.correction, "_central_correction", solve)
    science = experiment._run_targeting(pipeline.scenario, REFERENCE,
                                       central_reference=CENTRAL)["science"]
    assert len(calls) == 1 and len(pipeline.calls) == 1
    assert science["outcome"] == "aborted" and science["correction"]["reason"] == reason
    assert science["tighter_status"] == "skipped"


def test_closed_baseline_skips_solve(pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    original_loader = experiment._load_central_reference
    original_residual = experiment.correction._residual
    def load(*args: Any) -> Any:
        result = original_loader(*args)
        monkeypatch.setattr(experiment.correction, "_residual",
                            lambda values: replace(original_residual(values), closes=True))
        return result
    monkeypatch.setattr(experiment, "_load_central_reference", load)
    monkeypatch.setattr(experiment.correction, "_central_correction",
                        lambda *args: pytest.fail("closed baseline must not solve"))
    science = experiment._run_targeting(pipeline.scenario, REFERENCE,
                                       central_reference=CENTRAL)["science"]
    assert science["outcome"] == "baseline-closed" and len(pipeline.calls) == 1


def test_analytic_trial_rejection_counts_before_launch(pipeline: SimpleNamespace,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    original = experiment.physical._prepare_burn_controls
    calls = []
    def prepare(*args: Any) -> Any:
        calls.append(args)
        return "rejected-control-bounds" if len(calls) == 2 else original(*args)
    monkeypatch.setattr(experiment.physical, "_prepare_burn_controls", prepare)
    science = experiment._run_targeting(pipeline.scenario, REFERENCE,
                                       central_reference=CENTRAL)["science"]
    assert science["outcome"] == "aborted" and len(pipeline.calls) == 1
    assert science["control_attempts"] == 2 and science["propagation_evaluations"] == 1
    assert science["runs"][-1]["run"] is None


@pytest.mark.parametrize("fault", ["event", "dry", "native", "deadline", "reset", "history-impact"])
def test_shared_native_failure_guards(monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    rig = _rig(monkeypatch, fault)
    budget = experiment._CentralBudget(rig.report.candidate_id, 300, lambda: rig.clock[0])
    budget.begin_control()
    run = experiment._compose_research_run(budget, rig.report.scenario, rig.environment,
        rig.initial, rig.target, rig.report.seed_controls, tighter=False, register_control=False)
    assert run.outcome == "aborted" and not run.boundaries
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_control()


@pytest.mark.parametrize("fault", ["matrix", "raw", "ratio", "settings", "commands"])
def test_retained_data_reconstruction_rejects_mismatch(fault: str) -> None:
    stored = experiment._load_reference(REFERENCE, load_scenario(SCENARIO))
    payload = deepcopy(experiment._load_central_reference(CENTRAL, stored))
    science = payload["science"]
    if fault == "matrix":
        science["column_pairs"][0]["central"][0] += 1
    elif fault == "raw":
        science["runs"][1]["run"]["boundaries"][-1]["position_m"][0] += 1
    elif fault == "ratio":
        science["column_diagnostics"]["checks"][0]["norm_ratio"] = -1
    elif fault == "settings":
        science["runs"][1]["run"]["integrator_settings"] = {}
    else:
        science["runs"][1]["controls"][0] += 1
    with pytest.raises(ValueError):
        experiment._validate_central_reference(payload, stored)


def test_bad_digest_and_cli_exclusivity(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    science = experiment._run_targeting(load_scenario(SCENARIO), REFERENCE,
                                       central_reference=bad)["science"]
    assert science["attempted_arcs"] == 0 and "central reference digest" in science["reason"]
    with pytest.raises(SystemExit) as error:
        experiment.main([str(SCENARIO), str(REFERENCE), str(tmp_path / "out.json"),
                         "--central-reference", str(CENTRAL), "--damping-reference", str(bad)])
    assert error.value.code == 2
