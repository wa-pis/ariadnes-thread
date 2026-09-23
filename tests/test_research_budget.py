from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from space_nav.errors import TrajectoryRefinementError
from space_nav.research import ResearchProgress, _ResearchBudget


def test_two_runs_six_arcs_and_no_seventh_launch() -> None:
    budget = _ResearchBudget("d0001-t0035", 300, lambda: 0.0)
    budget.begin_control()
    for index in range(6):
        budget.begin_arc(first_in_evaluation=index in (0, 3))
        assert budget.snapshot() == ResearchProgress(index + 1, index)
        budget.complete_arc()
    assert budget.propagation_evaluations == 2
    assert budget.snapshot() == ResearchProgress(6, 6)
    with pytest.raises(TrajectoryRefinementError, match="limit 6"):
        budget.begin_arc(first_in_evaluation=True)
    assert budget.native_arc_propagations == 6
    assert budget.snapshot().continuous_safety_verified is False


@pytest.mark.parametrize("stage", ["before-control", "before-launch", "after-native", "after-nominal"])
def test_shared_deadline_never_resets(stage: str) -> None:
    clock = [10.0]
    budget = _ResearchBudget("d0001-t0035", 300, lambda: clock[0])
    if stage != "before-control":
        budget.begin_control()
    if stage == "after-native":
        budget.begin_arc(first_in_evaluation=True)
    if stage == "after-nominal":
        for index in range(3):
            budget.begin_arc(first_in_evaluation=index == 0)
            budget.complete_arc()
    before = budget.snapshot()
    clock[0] = 310.0
    with pytest.raises(TrajectoryRefinementError, match="shared deadline"):
        if stage == "before-control":
            budget.begin_control()
        elif stage == "after-native":
            budget.complete_arc()
        else:
            budget.begin_arc(first_in_evaluation=True)
    assert budget.snapshot() == before
    assert budget.deadline_monotonic_s == 310.0


def test_failed_or_unaccepted_arc_cannot_be_retried() -> None:
    budget = _ResearchBudget("d0001-t0035", 300, lambda: 0.0)
    with pytest.raises(TrajectoryRefinementError, match="registered first"):
        budget.begin_arc(first_in_evaluation=True)
    budget.begin_control()
    budget.begin_arc(first_in_evaluation=True)
    for first in (True, False):
        with pytest.raises(TrajectoryRefinementError, match="no retries"):
            budget.begin_arc(first_in_evaluation=first)
    with pytest.raises(TrajectoryRefinementError, match="one fixed control"):
        budget.begin_control()
    assert budget.snapshot() == ResearchProgress(1, 0)


def test_order_and_duplicate_completion_rejected() -> None:
    budget = _ResearchBudget("d0001-t0035", 300, lambda: 0.0)
    budget.begin_control()
    with pytest.raises(TrajectoryRefinementError, match="ordered"):
        budget.begin_arc(first_in_evaluation=False)
    with pytest.raises(TrajectoryRefinementError, match="pending"):
        budget.complete_arc()
    budget.begin_arc(first_in_evaluation=True)
    budget.complete_arc()
    with pytest.raises(TrajectoryRefinementError, match="pending"):
        budget.complete_arc()
    with pytest.raises(TrajectoryRefinementError, match="ordered"):
        budget.begin_arc(first_in_evaluation=True)
    assert budget.snapshot() == ResearchProgress(1, 1)


@pytest.mark.parametrize("attempted,completed", [(True, 0), (1, False), (1.0, 0), (-1, 0), (1, 2), (7, 6)])
def test_invalid_progress(attempted: object, completed: object) -> None:
    with pytest.raises(ValueError):
        ResearchProgress(attempted, completed)  # type: ignore[arg-type] -- invalid boundary inputs


def test_progress_cannot_claim_safety_or_be_mutated() -> None:
    progress = ResearchProgress(3, 3)
    with pytest.raises(FrozenInstanceError):
        progress.completed_arcs = 4  # type: ignore[misc] -- immutability check
    with pytest.raises(TypeError):
        ResearchProgress(3, 3, continuous_safety_verified=True)  # type: ignore[call-arg] -- fixed safety status


def test_research_cannot_expand_arc_partition() -> None:
    with pytest.raises(TrajectoryRefinementError, match="exactly three"):
        _ResearchBudget("d0001-t0035", 300, lambda: 0.0, max_arcs_per_evaluation=4)
