from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


@pytest.mark.parametrize("case", ["success", "expired", "import-time", "native-time",
                                  "import-failure", "native-failure", "ppn-time", "ppn-failure"])
def test_native_arc_budget_boundaries(case: str, monkeypatch: pytest.MonkeyPatch) -> None:
    now_s = [0.0]
    budget = trajectory._RefinementBudget("runner-control", 1.0, lambda: now_s[0])
    native = MagicMock()
    result = object()
    failure = RuntimeError("injected native failure")

    def reset_ppn(candidate_id: str, supplied_bodies: object) -> None:
        assert candidate_id == budget.candidate_id and supplied_bodies is bodies
        assert budget.propagation_evaluations == budget.native_arc_propagations == 0
        if case == "ppn-time":
            now_s[0] = 1.0
        if case == "ppn-failure":
            raise TrajectoryRefinementError("runner-control PPN readback failure") from failure

    reset = MagicMock(side_effect=reset_ppn)
    monkeypatch.setattr(trajectory, "_set_general_relativity_ppn_parameters", reset)

    def import_simulator() -> object:
        if case == "import-time":
            now_s[0] = 1.0
        if case == "import-failure":
            raise failure
        return native

    def run(bodies: object, settings: object) -> object:
        reset.assert_called_once_with(budget.candidate_id, bodies)
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
    assert reset.call_count == (0 if case in {"expired", "import-time", "import-failure"} else 1)
    if case == "expired":
        importer.assert_not_called()


def test_native_runner_resets_ppn_for_every_continuation(monkeypatch: pytest.MonkeyPatch) -> None:
    budget = trajectory._RefinementBudget("runner-control", 300.0)
    bodies, settings, result = object(), object(), object()
    parameter_values = [0.75, 1.25]
    resets: list[tuple[int, int]] = []

    def reset(candidate_id: str, supplied_bodies: object) -> None:
        assert candidate_id == budget.candidate_id and supplied_bodies is bodies
        resets.append((budget.propagation_evaluations, budget.native_arc_propagations))
        parameter_values[:] = [1.0, 1.0]

    def run(supplied_bodies: object, supplied_settings: object) -> object:
        assert supplied_bodies is bodies and supplied_settings is settings
        assert parameter_values == [1.0, 1.0]
        return result

    native = MagicMock()
    native.create_dynamics_simulator.side_effect = run
    monkeypatch.setattr(trajectory, "_import_tudat_simulator", lambda: native)
    monkeypatch.setattr(trajectory, "_set_general_relativity_ppn_parameters", reset)
    for index in range(3):
        parameter_values[:] = [0.75, 1.25]
        assert trajectory._run_native_arc(budget, bodies, settings, first_in_evaluation=index == 0) is result
    assert resets == [(0, 0), (1, 1), (1, 2)]
    assert (budget.propagation_evaluations, budget.native_arc_propagations) == (1, 3)
