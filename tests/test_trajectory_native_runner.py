from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


@pytest.mark.parametrize("case", ["success", "expired", "import-time", "native-time",
                                  "import-failure", "native-failure"])
def test_native_arc_budget_boundaries(case: str, monkeypatch: pytest.MonkeyPatch) -> None:
    now_s = [0.0]
    budget = trajectory._RefinementBudget("runner-control", 1.0, lambda: now_s[0])
    native = MagicMock()
    result = object()
    failure = RuntimeError("injected native failure")

    def import_simulator() -> object:
        if case == "import-time":
            now_s[0] = 1.0
        if case == "import-failure":
            raise failure
        return native

    def run(bodies: object, settings: object) -> object:
        assert budget.propagation_evaluations == budget.native_arc_propagations == 1
        if case == "native-time":
            now_s[0] = 1.0
        if case == "native-failure":
            raise failure
        return result

    importer = MagicMock(side_effect=import_simulator)
    native.create_dynamics_simulator.side_effect = run
    monkeypatch.setattr(trajectory, "_import_tudat_simulator", importer)
    bodies, settings = object(), object()
    if case == "expired":
        now_s[0] = 1.0
    if case == "success":
        assert trajectory._run_native_arc(
            budget, bodies, settings, first_in_evaluation=True,
        ) is result
        native.create_dynamics_simulator.assert_called_once_with(bodies, settings)
    else:
        with pytest.raises(TrajectoryRefinementError, match="runner-control") as caught:
            trajectory._run_native_arc(
                budget, bodies, settings, first_in_evaluation=True,
            )
        if case.endswith("failure"):
            assert caught.value.__cause__ is failure
        else:
            assert "no partial result" in str(caught.value)
    calls = 1 if case in {"success", "native-time", "native-failure"} else 0
    assert budget.propagation_evaluations == budget.native_arc_propagations == calls
    assert native.create_dynamics_simulator.call_count == calls
    assert budget.control_attempts == 0
    if case == "expired":
        importer.assert_not_called()
