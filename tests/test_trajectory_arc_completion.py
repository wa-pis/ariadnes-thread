from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


STATE = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 1500.0)


def test_completed_state_is_immutable_and_selects_latest_epoch() -> None:
    simulator = SimpleNamespace(
        integration_completed_successfully=True,
        state_history={10.0: list(STATE), 0.0: [0.0] * 7},
    )
    state, mass = trajectory._read_completed_arc_state("fixture", "coast", simulator, 10.0)
    simulator.state_history[10.0][0] = 99.0
    assert state == STATE[:6] and mass == STATE[6]
    assert isinstance(state, tuple)


@pytest.mark.parametrize("flag", [False, None, 1, "True"])
def test_unsuccessful_integration_never_reads_partial_history(flag: object) -> None:
    simulator = MagicMock()
    simulator.integration_completed_successfully = flag
    history = PropertyMock(side_effect=AssertionError("partial history read"))
    type(simulator).state_history = history
    with pytest.raises(TrajectoryRefinementError, match="coast.*10.0") as caught:
        trajectory._read_completed_arc_state("fixture", "coast", simulator, 10.0)
    assert isinstance(caught.value.__cause__, RuntimeError)
    history.assert_not_called()


@pytest.mark.parametrize("history", [
    {}, {9.0: STATE}, {11.0: STATE}, {float("nan"): STATE},
    {True: STATE}, {10.0: STATE[:6]}, {10.0: STATE + (0.0,)},
    {10.0: (float("nan"),) + STATE[1:]},
    {10.0: STATE[:6] + (float("inf"),)},
    {10.0: STATE[:6] + (0.0,)}, {10.0: STATE[:6] + (-1.0,)},
    {10.0: (True,) + STATE[1:]},
])
def test_invalid_history_cannot_produce_completed_state(history: dict[object, object]) -> None:
    simulator = SimpleNamespace(integration_completed_successfully=True, state_history=history)
    with pytest.raises(TrajectoryRefinementError, match="fixture.*coast.*10.0") as caught:
        trajectory._read_completed_arc_state("fixture", "coast", simulator, 10.0)
    assert isinstance(caught.value.__cause__, ValueError)


def test_native_history_failure_preserves_original_cause() -> None:
    simulator = MagicMock()
    simulator.integration_completed_successfully = True
    original = RuntimeError("native output unavailable")
    type(simulator).state_history = PropertyMock(side_effect=original)
    with pytest.raises(TrajectoryRefinementError) as caught:
        trajectory._read_completed_arc_state("fixture", "coast", simulator, 10.0)
    assert caught.value.__cause__ is original


@pytest.mark.parametrize("expected", [True, float("nan"), float("inf"), "10"])
def test_invalid_expected_epoch_fails_before_reading_native(expected: object) -> None:
    simulator = MagicMock()
    completed = PropertyMock(side_effect=AssertionError("native read"))
    type(simulator).integration_completed_successfully = completed
    with pytest.raises(TrajectoryRefinementError):
        trajectory._read_completed_arc_state("fixture", "coast", simulator, expected)
    completed.assert_not_called()
