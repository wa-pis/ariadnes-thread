from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from space_nav import coast_diagnostic as coast
from space_nav import trajectory as physical
from space_nav.errors import TrajectoryRefinementError
from space_nav.scenario import load_scenario
from test_research_propagation import _rig
from test_research_report import _report


REFERENCE = Path("docs/adr/experiments/0079-research-reference.json")
SCENARIO = Path("examples/m3_feasible_mission.toml")


def test_budget_two_arcs_and_no_retry() -> None:
    budget = coast._CoastBudget("d0001-t0035", 300, lambda: 0.0)
    for _ in range(2):
        budget.begin_arc(first_in_evaluation=True)
        with pytest.raises(TrajectoryRefinementError):
            budget.begin_arc(first_in_evaluation=True)
        budget.complete_arc()
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_arc(first_in_evaluation=True)
    assert budget.native_arc_propagations == budget.completed_arcs == 2
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_control()
    with pytest.raises(TrajectoryRefinementError):
        coast._CoastBudget("d0001-t0035", 301)


@pytest.mark.parametrize("fault", ["", "event", "dry", "early", "native", "failed",
                                   "history-impact", "reset", "deadline"])
def test_coast_native_boundary_errors(monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    rig = _rig(monkeypatch, fault)
    budget = coast._CoastBudget(rig.report.candidate_id, 300, lambda: rig.clock[0])
    result = coast._propagate_coast(
        budget, rig.environment, rig.report.scenario, rig.initial, 2000.0, 200.0,
        tighter=False,
    )
    if not fault:
        assert result.endpoint == (1.0,) * 6 + (2000.0,)
        assert budget.completed_arcs == 1
        assert result.checked_state_count >= 4
    else:
        assert result.endpoint is None and result.reason
        assert budget.completed_arcs == 0
        assert budget.stopped
        if fault in ("event", "dry"):
            assert "rejected-" in result.reason
            assert "final epoch mismatch" not in result.reason
        second = coast._propagate_coast(
            budget, rig.environment, rig.report.scenario, rig.initial, 2000.0, 200.0,
            tighter=True,
        )
        assert second.endpoint is None
    assert len(rig.calls) == budget.native_arc_propagations == 1


@pytest.mark.parametrize("fault", ["coast-mass", "coast-intermediate-mass"])
def test_coast_rejects_mass_change(monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    rig = _rig(monkeypatch, fault)
    budget = coast._CoastBudget(rig.report.candidate_id, 300, lambda: 0.0)
    for tighter in (False, True):
        result = coast._propagate_coast(
            budget, rig.environment, rig.report.scenario, rig.initial, 2000.0, 200.0,
            tighter=tighter,
        )
    assert result.endpoint is None and "mass changed" in result.reason
    assert budget.native_arc_propagations == 2 and budget.completed_arcs == 1


def test_reference_identity_rejected_without_launch(tmp_path: Path) -> None:
    scenario = load_scenario(SCENARIO)
    assert coast._load_reference(REFERENCE, scenario)["candidate_id"] == "d0001-t0035"
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    report = coast._run_diagnostic(scenario, bad)
    assert report["science"]["attempted_arcs"] == 0
    assert "digest" in report["science"]["reason"]
    changed = replace(scenario, spacecraft=replace(scenario.spacecraft, dry_mass_kg=501))
    report = coast._run_diagnostic(changed, REFERENCE)
    assert report["science"]["attempted_arcs"] == 0
    assert "scenario differs" in report["science"]["reason"]


def test_signed_differences_not_subtracted_norms() -> None:
    zero = (0.0,) * 7
    a = (3.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    b = (-3.0, -4.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert coast._difference(a, zero)["position_norm_m"] == 5
    assert coast._difference(b, zero)["position_norm_m"] == 5
    delta = coast._difference(a, b)
    assert delta["position_norm_m"] == 10
    assert delta["position_m"] == (6.0, 8.0, 0.0)
    assert delta["within_thresholds"]
    assert not coast._difference((10.00001,) + zero[1:], zero)["within_thresholds"]
    for value in (float("inf"), float("nan"), True):
        with pytest.raises(ValueError):
            coast._difference((value,) + zero[1:], zero)


def test_entrypoint_retains_failure_and_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    args = [str(SCENARIO), str(tmp_path / "missing.json"), str(output)]
    assert coast.main(args) == 1
    data = json.loads(output.read_text())
    assert data["science"]["attempted_arcs"] == 0
    assert data["science"]["comparisons"] is None
    with pytest.raises(FileExistsError):
        coast.main(args)


@pytest.mark.parametrize("fault", ["dry", "model", "interval"])
def test_preflight_rejection_launches_nothing(monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    rig = _rig(monkeypatch)
    budget = coast._CoastBudget(rig.report.candidate_id, 300, lambda: 0.0)
    mass = rig.report.scenario.spacecraft.dry_mass_kg if fault == "dry" else 2000.0
    if fault == "model":
        rig.environment.model_id = "wrong"
    end = 99.0 if fault == "interval" else 200.0
    result = coast._propagate_coast(budget, rig.environment, rig.report.scenario,
                                   rig.initial, mass, end, tighter=False)
    assert result.endpoint is None and result.reason
    assert budget.stopped and budget.native_arc_propagations == 0
    assert not rig.calls


def test_budget_expiry_before_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    scenario = load_scenario(SCENARIO)
    original = coast._CoastBudget
    times = iter((0.0, 301.0))
    monkeypatch.setattr(coast, "_CoastBudget", lambda *a: original(*a, monotonic=lambda: next(times)))
    result = coast._run_diagnostic(scenario, REFERENCE)
    assert result["science"]["attempted_arcs"] == 0
    assert "deadline" in result["science"]["reason"]


@pytest.mark.parametrize("failure", ["", "candidate", "runtime", "environment", "reuse", "nominal", "tighter"])
def test_diagnostic_wiring(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    scenario = load_scenario(SCENARIO)
    stored = coast._load_reference(REFERENCE, scenario)
    budgets: list[object] = []
    starts: list[tuple] = []
    envs: list[object] = []

    def verify(scenario: object, candidate: object, **kwargs: object) -> object:
        if failure == "candidate":
            raise TrajectoryRefinementError("candidate mismatch")
        return candidate

    def build(*args: object, **kwargs: object) -> object:
        budgets.append(kwargs["budget"])
        env = envs[0] if envs and failure == "reuse" else SimpleNamespace(bodies=object())
        envs.append(env)
        return env

    def propagate(budget: Any, env: object, scenario: object, initial: object,
                  mass: float, end: float, *, tighter: bool) -> coast._CoastRun:
        assert budget is budgets[0]
        budget.begin_arc(first_in_evaluation=True)
        starts.append((initial, mass, end))
        profile = "tighter" if tighter else "nominal"
        if failure == profile:
            budget.stopped = True
            return coast._CoastRun(profile, None, 1, "manufactured failure")
        boundary = stored["nominal"]["boundaries"][2]
        endpoint = (*boundary["position_m"], *boundary["velocity_m_s"], mass)
        budget.complete_arc()
        return coast._CoastRun(profile, endpoint, 4, None)

    monkeypatch.setattr(physical, "_verify_candidate_handoff", verify)
    monkeypatch.setattr(physical, "_build_physical_environment", build)
    monkeypatch.setattr(coast, "_runtime_manifest", lambda seed: {} if failure == "runtime"
                        else stored["provenance"]["runtime"])
    monkeypatch.setattr(coast, "_environment_manifest", lambda env: {} if failure == "environment"
                        else stored["provenance"]["environment"])
    monkeypatch.setattr(coast, "_propagate_coast", propagate)
    result = coast._run_diagnostic(scenario, REFERENCE)["science"]
    if not failure:
        assert result["outcome"] == "completed"
        assert starts[0] == starts[1]
        assert budgets[0] is budgets[1]
        assert result["comparisons"]["restart_drift"]["position_norm_m"] == 0
        assert result["attempted_arcs"] == result["completed_arcs"] == 2
    else:
        assert result["outcome"] == "aborted" and result["comparisons"] is None
        expected = 2 if failure == "tighter" else 1 if failure in ("nominal", "reuse") else 0
        assert result["attempted_arcs"] == expected
    assert result["continuous_safety_verified"] is False
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("study", [False, True])
def test_native_coast_matches_uniform_motion(monkeypatch: pytest.MonkeyPatch, study: bool) -> None:
    """Toy native oracle: negligible gravity, not reference-mission evidence."""
    from tudatpy.dynamics import environment_setup, propagation_setup
    import numpy as np

    report = _report()
    settings = environment_setup.BodyListSettings("SSB", "J2000")
    settings.add_empty_settings("Spacecraft")
    settings.get("Spacecraft").constant_mass = 2000.0
    for name in physical.PHYSICAL_BODY_NAMES:
        settings.add_empty_settings(name)
        settings.get(name).ephemeris_settings = environment_setup.ephemeris.constant(
            np.asarray([1e12, 0.0, 0.0, 0.0, 0.0, 0.0]), "SSB", "J2000",
        )
        settings.get(name).gravity_field_settings = environment_setup.gravity_field.central(1.0)

    def forces(cid: object, env: Any, *, burn_id: object) -> Any:
        assert burn_id is None
        return propagation_setup.create_acceleration_models(
            env.bodies, {"Spacecraft": {name: [propagation_setup.acceleration.point_mass_gravity()]
                                       for name in physical.PHYSICAL_BODY_NAMES}},
            ["Spacecraft"], ["SSB"],
        )

    monkeypatch.setattr(physical, "_build_arc_force_models", forces)
    initial = replace(report.nominal.boundaries[0], position_m=(0.0, 1e7, 0.0),
                      velocity_m_s=(1000.0, 0.0, 0.0))
    budget = (coast._StepStudyBudget if study else coast._CoastBudget)(report.candidate_id, 300)
    for tighter in ((True, True, True) if study else (False, True)):
        env = SimpleNamespace(
            model_id=physical.PHYSICAL_MODEL_IDENTIFIER, origin="SSB", orientation="J2000",
            initial_epoch_tdb_s=100.0, final_epoch_tdb_s=200.0,
            bodies=environment_setup.create_system_of_bodies(settings),
            collision_resource=physical._build_collision_resource(report.candidate_id),
        )
        result = coast._propagate_coast(budget, env, report.scenario, initial, 2000.0, 200.0,
                                       tighter=tighter)
        assert result.reason is None
        assert result.endpoint[:3] == pytest.approx((100000.0, 1e7, 0.0), abs=1e-6, rel=0)
        assert result.endpoint[3:6] == pytest.approx((1000.0, 0.0, 0.0), abs=1e-9, rel=0)
        assert result.endpoint[6] == 2000.0
        if study:
            assert result.saved_mesh is not None
            assert result.saved_mesh.interval_count >= 1
    assert budget.completed_arcs == (3 if study else 2)
