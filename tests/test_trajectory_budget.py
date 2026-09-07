from __future__ import annotations

import math

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


def test_budget_counts_rejected_controls_partial_arcs_and_diagnostics() -> None:
    now_s = [100.0]
    budget = trajectory._RefinementBudget("budget-control", 300.0, lambda: now_s[0])
    assert budget.deadline_monotonic_s == 400.0
    budget.begin_control()  # Analytic rejection starts no propagation.
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations) == (1, 0, 0)
    budget.begin_control()
    budget.begin_arc(first_in_evaluation=True)  # Impact in the first arc.
    # Frozen diagnostic starts an evaluation, but not another control attempt.
    budget.begin_arc(first_in_evaluation=True)
    budget.begin_arc(first_in_evaluation=False)
    budget.begin_arc(first_in_evaluation=False)
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations) == (2, 2, 4)
    now_s[0] = 400.0
    with pytest.raises(TrajectoryRefinementError, match="shared deadline") as caught:
        budget.begin_control()
    for detail in ("300 s", "control_attempts=2", "propagation_evaluations=2",
                   "native_arc_propagations=4", "no partial result"):
        assert detail in str(caught.value)
    assert budget.deadline_monotonic_s == 400.0
    assert budget.control_attempts == 2


@pytest.mark.parametrize("limit", ["control", "evaluation", "arc"])
def test_budget_enforces_exact_caps_without_incrementing_failed_attempt(limit: str) -> None:
    budget = trajectory._RefinementBudget("budget-control", 300.0, lambda: 0.0)
    if limit == "control":
        for _ in range(73):
            budget.begin_control()
        with pytest.raises(TrajectoryRefinementError, match="limit 73"):
            budget.begin_control()
        assert budget.control_attempts == 73
    else:
        for _ in range(76):
            budget.begin_arc(first_in_evaluation=True)
            if limit == "arc":
                budget.begin_arc(first_in_evaluation=False)
                budget.begin_arc(first_in_evaluation=False)
        with pytest.raises(TrajectoryRefinementError, match=f"limit {228 if limit == 'arc' else 76}"):
            budget.begin_arc(first_in_evaluation=True)
        assert budget.propagation_evaluations == 76
        assert budget.native_arc_propagations == (228 if limit == "arc" else 76)


@pytest.mark.parametrize("runtime", [0.0, -1.0, math.inf, math.nan, True])
def test_budget_rejects_invalid_runtime(runtime: float) -> None:
    with pytest.raises(TrajectoryRefinementError, match="budget-construction"):
        trajectory._RefinementBudget("budget-control", runtime, lambda: 0.0)


@pytest.mark.parametrize("invalid_clock", [-1.0, math.nan, math.inf])
def test_budget_rejects_backward_or_nonfinite_clock(invalid_clock: float) -> None:
    clock = iter([0.0, invalid_clock])
    budget = trajectory._RefinementBudget("budget-control", 300.0, lambda: next(clock))
    with pytest.raises(TrajectoryRefinementError, match="deadline"):
        budget.check()


def test_budget_rejects_orphan_and_fourth_arcs() -> None:
    budget = trajectory._RefinementBudget("budget-control", 300.0, lambda: 0.0)
    with pytest.raises(TrajectoryRefinementError, match="continuation"):
        budget.begin_arc(first_in_evaluation=False)
    budget.begin_arc(first_in_evaluation=True)
    budget.begin_arc(first_in_evaluation=False)
    budget.begin_arc(first_in_evaluation=False)
    with pytest.raises(TrajectoryRefinementError, match="continuation"):
        budget.begin_arc(first_in_evaluation=False)
    assert budget.native_arc_propagations == 3
