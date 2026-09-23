from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from space_nav import research_propagation as propagation
from space_nav import trajectory as physical
from space_nav.errors import TrajectoryRefinementError
from space_nav.research import ResearchProgress, ResearchReport
from test_research_propagation import _rig


def _identity_fields(rig: SimpleNamespace) -> None:
    # Manufactured identity, not verified physical resources.
    for name in (
        "harmonic_fields",
        "gravity_acceleration_inventory",
        "solar_radiation_pressure",
        "relativity",
    ):
        setattr(rig.environment, name, ("manufactured",))


def _compare(rig: SimpleNamespace) -> ResearchReport:
    candidate = SimpleNamespace(
        candidate_id=rig.report.candidate_id,
        departure_epoch_tdb_s=rig.initial.epoch_tdb_s,
        arrival_epoch_tdb_s=rig.target.epoch_tdb_s,
    )
    return propagation._compare_research_profiles(
        rig.budget,
        rig.report.scenario,
        candidate,
        rig.environment,
        rig.initial,
        rig.target,
        rig.report.seed_controls,
        rig.report.provenance_json,
    )


@pytest.mark.parametrize(
    "failure", ["", "nominal", "native", "resources", "deadline", "reuse", "changed"]
)
def test_comparison_uses_fresh_environment_and_one_budget(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    rig = _rig(monkeypatch, "native" if failure == "nominal" else "")
    _identity_fields(rig)
    builds = []
    repeated = []

    def build(candidate: object, spacecraft: object, *, budget: object) -> object:
        assert budget is rig.budget
        assert spacecraft is rig.report.scenario.spacecraft
        builds.append(candidate)
        if failure == "resources":
            raise TrajectoryRefinementError("missing resource")
        if failure == "reuse":
            return rig.environment
        fresh = _rig(monkeypatch, "native" if failure == "native" else "")
        _identity_fields(fresh)
        repeated.append(fresh)
        if failure == "deadline":
            rig.clock[0] = 300.0
        if failure == "changed":
            fresh.environment.relativity = ("changed",)
        return fresh.environment

    monkeypatch.setattr(physical, "_build_physical_environment", build)
    result = _compare(rig)
    assert result.seed_controls is rig.report.seed_controls
    assert result.continuous_safety_verified is False
    if failure == "nominal":
        assert not builds
        assert result.nominal.outcome == "aborted"
        assert result.tighter.outcome == "unavailable"
        assert result.progress == ResearchProgress(1, 0)
    elif failure:
        assert len(builds) == 1
        assert result.nominal.outcome == "completed"
        assert result.nominal.terminal_errors is not None
        assert result.tighter.terminal_errors is None
        assert result.numerical_agreement is None
        assert result.comparison_reason
        expected = (
            ResearchProgress(4, 3) if failure == "native" else ResearchProgress(3, 3)
        )
        assert result.progress == expected
    else:
        assert len(builds) == 1 and len(repeated) == 1
        assert result.outcome == "completed"
        assert result.numerical_agreement is True
        assert len(result.integration_differences) == 4
        assert result.progress == ResearchProgress(6, 6)
        assert rig.budget.control_attempts == 1
        assert rig.budget.propagation_evaluations == 2
        assert repeated[0].calls == rig.calls
        assert result.nominal.burns == result.tighter.burns
    if failure == "deadline":
        assert not repeated[0].calls
        assert "deadline" in result.comparison_reason
        assert rig.budget.deadline_monotonic_s == 300.0


@pytest.mark.parametrize("index", [1, 2, 3])
@pytest.mark.parametrize("error,agreement", [(10.0, True), (10.00001, False)])
def test_completed_replay_disagreement_is_reported(
    monkeypatch: pytest.MonkeyPatch, index: int, error: float, agreement: bool
) -> None:
    rig = _rig(monkeypatch)
    _identity_fields(rig)
    actual = propagation._propagate_research_run

    def build(*args: object, **kwargs: object) -> object:
        fresh = _rig(monkeypatch)
        _identity_fields(fresh)
        return fresh.environment

    def run(*args: object, **kwargs: object) -> object:
        result = actual(*args, **kwargs)
        if kwargs.get("tighter") and result.outcome == "completed":
            states = list(result.boundaries)
            state = states[index]
            states[index] = replace(
                state, position_m=(state.position_m[0] + error, *state.position_m[1:])
            )
            result = replace(result, boundaries=tuple(states))
        return result

    monkeypatch.setattr(physical, "_build_physical_environment", build)
    monkeypatch.setattr(propagation, "_propagate_research_run", run)
    result = _compare(rig)
    assert result.outcome == "completed"
    assert result.numerical_agreement is agreement
    assert result.integration_differences[index].position_difference_m == pytest.approx(
        error
    )
    assert result.comparison_reason == (
        None if agreement else "integration-threshold-exceeded"
    )
    assert result.continuous_safety_verified is False


def test_wrong_candidate_is_rejected_before_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rig = _rig(monkeypatch)
    with pytest.raises(ValueError, match="candidate identity"):
        propagation._compare_research_profiles(
            rig.budget,
            rig.report.scenario,
            SimpleNamespace(
                candidate_id="wrong",
                departure_epoch_tdb_s=100.0,
                arrival_epoch_tdb_s=200.0,
            ),
            rig.environment,
            rig.initial,
            rig.target,
            rig.report.seed_controls,
            rig.report.provenance_json,
        )
    assert not rig.calls
