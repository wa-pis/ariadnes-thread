from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from space_nav import coast_diagnostic as coast
from space_nav import trajectory as physical
from space_nav.errors import TrajectoryRefinementError
from space_nav.scenario import load_scenario
from test_coast_diagnostic import REFERENCE, SCENARIO
from test_research_propagation import _rig


BASELINE = Path("docs/decisions/experiments/0082-identical-start-coast.json")


def test_profiles_change_only_cap_and_reach_native_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    from tudatpy.dynamics.propagation_setup import integrator

    pinned = physical._arc_integrator_profile("fixture", "coast", tighter=True)
    validation = MagicMock(wraps=integrator.step_size_validation)
    factory = MagicMock(wraps=integrator.runge_kutta_variable_step)
    control = MagicMock(wraps=integrator.step_size_control_elementwise_matrix_tolerance)
    monkeypatch.setattr(integrator, "step_size_validation", validation)
    monkeypatch.setattr(integrator, "runge_kutta_variable_step", factory)
    monkeypatch.setattr(integrator, "step_size_control_elementwise_matrix_tolerance", control)
    for index, cap in enumerate((21600.0, 10800.0, 5400.0)):
        profile = coast._step_profile("fixture", index)
        assert profile == {**pinned, "maximum_step_s": cap}
        physical._build_integrator_from_profile("fixture", "coast", profile)
        assert validation.call_args.args[:2] == (1e-5, cap)
        assert factory.call_args.args[:2] == (75.0, integrator.CoefficientSets.rkdp_87)
        assert control.call_args.args == (((1e-13,),) * 7,
                                         ((1e-5,),) * 3 + ((1e-8,),) * 3 + ((1e-11,),))
    assert physical._arc_integrator_profile("fixture", "coast", tighter=True) == pinned
    for invalid in (-1, 3, True, 1.0):
        with pytest.raises(ValueError):
            coast._step_profile("fixture", invalid)


def test_budget_three_arcs_without_changing_d5() -> None:
    for cls, limit in ((coast._StepStudyBudget, 3), (coast._CoastBudget, 2)):
        budget = cls("fixture", 300, lambda: 0.0)
        for _ in range(limit):
            budget.begin_arc(first_in_evaluation=True)
            with pytest.raises(TrajectoryRefinementError):
                budget.begin_arc(first_in_evaluation=True)
            budget.complete_arc()
        with pytest.raises(TrajectoryRefinementError):
            budget.begin_arc(first_in_evaluation=True)
        assert budget.native_arc_propagations == limit


def test_saved_mesh_is_ordered_finite_and_explicit() -> None:
    mesh = coast._saved_mesh((100.0, 102.0, 106.0, 112.0))
    assert (mesh.interval_count, mesh.minimum_interval_s,
            mesh.median_interval_s, mesh.maximum_interval_s) == (3, 2, 4, 6)
    assert mesh == coast._saved_mesh((100, 102, 106, 112))
    assert mesh.epoch_sequence_sha256 != coast._saved_mesh((101, 103, 107, 113)).epoch_sequence_sha256
    for invalid in ((), (1,), (1, 1), (2, 1), (1, float("nan")), (False, 1)):
        with pytest.raises(ValueError):
            coast._saved_mesh(invalid)


@pytest.mark.parametrize("first,second,trend,ratio,reason", [
    (10.0, 1.0, "decreasing", 0.1, None),
    (1.0, 10.0, "increasing", 10.0, None),
    (1.0, 1.0, "unchanged", 1.0, None),
    (0.0, 0.0, "unchanged", None, "zero_previous_difference"),
    (0.0, 1.0, "increasing", None, "zero_previous_difference"),
    (1e-300, 1e300, "increasing", None, "nonfinite_ratio"),
])
def test_ratio_never_invents_accuracy(first: float, second: float, trend: str,
                                    ratio: float | None, reason: str | None) -> None:
    result = coast._difference_trend(first, second)
    assert result == {"trend": trend, "ratio": ratio, "ratio_unavailable_reason": reason}
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("fault", ["event", "dry", "native", "deadline", "reset"])
def test_study_uses_same_guards(monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    rig = _rig(monkeypatch, fault)
    monkeypatch.setattr(physical, "_build_integrator_from_profile", lambda *args: None)
    budget = coast._StepStudyBudget(rig.report.candidate_id, 300, lambda: rig.clock[0])
    result = coast._propagate_coast(budget, rig.environment, rig.report.scenario,
                                   rig.initial, 2000.0, 200.0, tighter=True)
    assert result.endpoint is None and result.saved_mesh is None
    assert result.reason and budget.stopped and budget.native_arc_propagations == 1
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_arc(first_in_evaluation=True)


@pytest.mark.parametrize("failure", ["", "baseline", "first", "second", "third", "reuse", "deadline"])
def test_study_pipeline_stops_and_preserves_baseline(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    scenario = load_scenario(SCENARIO)
    stored = coast._load_reference(REFERENCE, scenario)
    baseline = coast._load_step_baseline(BASELINE, stored)
    endpoint = tuple(baseline["profiles"][1]["endpoint"])
    environments: list[Any] = []
    calls: list[tuple] = []
    budgets: list[Any] = []
    clock = [0.0]
    original = coast._StepStudyBudget

    class ClockBudget(original):
        def __post_init__(self) -> None:
            self.monotonic = lambda: clock[0]
            super().__post_init__()

    def build(*args: object, **kwargs: Any) -> Any:
        budgets.append(kwargs["budget"])
        env = environments[0] if failure == "reuse" and len(environments) == 2 else SimpleNamespace(bodies=object())
        environments.append(env)
        return env

    def propagate(budget: Any, env: object, scenario: object, initial: object,
                  mass: float, end: float, *, tighter: bool) -> coast._CoastRun:
        index = len(calls)
        assert tighter is True and budget is budgets[0]
        calls.append((initial, mass, end))
        budget.begin_arc(first_in_evaluation=True)
        if failure == ("first", "second", "third")[index]:
            budget.stopped = True
            return coast._CoastRun(str(index), None, 1, "manufactured native failure")
        shifted = (endpoint[0] + (20 if failure == "baseline" else (0, 100, 110)[index]), *endpoint[1:])
        result = coast._CoastRun(str(index), shifted, 3, None, coast._saved_mesh((0, 10-index, 20)))
        budget.complete_arc()
        if failure == "deadline":
            clock[0] = 300.0
        return result

    monkeypatch.setattr(coast, "_StepStudyBudget", ClockBudget)
    monkeypatch.setattr(physical, "_verify_candidate_handoff", lambda scenario, candidate, **kw: candidate)
    monkeypatch.setattr(physical, "_build_physical_environment", build)
    monkeypatch.setattr(coast, "_runtime_manifest", lambda seed: stored["provenance"]["runtime"])
    monkeypatch.setattr(coast, "_environment_manifest", lambda env: stored["provenance"]["environment"])
    monkeypatch.setattr(coast, "_propagate_coast", propagate)
    science = coast._run_diagnostic(scenario, REFERENCE, step_baseline=BASELINE)["science"]
    assert all(c == calls[0] for c in calls)
    if not failure:
        assert science["outcome"] == "completed" and science["attempted_arcs"] == 3
        assert science["baseline_comparison"]["position_norm_m"] == 0
        assert science["comparisons"]["position"]["ratio"] == 0.1
        assert len(science["comparisons"]["pairs"]) == 3
        assert not science["comparisons"]["pairs"]["0-1"]["saved_meshes_identical"]
    else:
        expected = {"baseline": 1, "first": 1, "second": 2, "third": 3, "reuse": 2, "deadline": 1}[failure]
        assert science["outcome"] == "aborted" and science["attempted_arcs"] == expected
        assert science["comparisons"] is None and science["reason"]
        if failure == "baseline":
            assert not science["baseline_comparison"]["within_thresholds"]


def test_bad_step_baseline_does_not_launch(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    result = coast._run_diagnostic(load_scenario(SCENARIO), REFERENCE, step_baseline=bad)
    assert result["science"]["attempted_arcs"] == 0
    assert "baseline digest" in result["science"]["reason"]


def test_unchanged_mesh_and_endpoint_are_explicit() -> None:
    run = coast._CoastRun("fixture", (0.0,) * 7, 3, None, coast._saved_mesh((0, 1, 2)))
    result = coast._study_comparisons([run, run, run])
    assert all(v["saved_meshes_identical"] and v["endpoints_identical"] for v in result["pairs"].values())
    assert result["position"]["ratio"] is None
    assert result["position"]["trend"] == "unchanged"
