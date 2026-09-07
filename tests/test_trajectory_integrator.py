from __future__ import annotations

from typing import Literal
from unittest.mock import MagicMock

import numpy as np
import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


@pytest.mark.parametrize("arc", ["departure-burn", "coast", "arrival-burn"])
@pytest.mark.parametrize("tighter", [False, True])
def test_native_integrator_receives_exact_settings(
    arc: Literal["departure-burn", "coast", "arrival-burn"],
    tighter: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tudatpy.dynamics.propagation_setup import integrator

    control = MagicMock(wraps=integrator.step_size_control_elementwise_matrix_tolerance)
    validation = MagicMock(wraps=integrator.step_size_validation)
    factory = MagicMock(wraps=integrator.runge_kutta_variable_step)
    monkeypatch.setattr(
        integrator, "step_size_control_elementwise_matrix_tolerance", control
    )
    monkeypatch.setattr(integrator, "step_size_validation", validation)
    monkeypatch.setattr(integrator, "runge_kutta_variable_step", factory)
    result = trajectory._build_arc_integrator(
        "integrator-control", arc, tighter=tighter
    )
    assert result is not None
    relative = 1e-13 if tighter else 1e-11
    absolute = (
        [1e-5] * 3 + [1e-8] * 3 + [1e-11]
        if tighter
        else [1e-3] * 3 + [1e-6] * 3 + [1e-9]
    )
    np.testing.assert_array_equal(control.call_args.args[0], np.full((7, 1), relative))
    np.testing.assert_array_equal(
        control.call_args.args[1], np.asarray(absolute).reshape(7, 1)
    )
    expected_steps = {
        (False, False): (1.0, 1e-6, 30.0),
        (False, True): (300.0, 1e-3, 86400.0),
        (True, False): (0.25, 1e-8, 7.5),
        (True, True): (75.0, 1e-5, 21600.0),
    }[tighter, arc == "coast"]
    assert factory.call_args.args[0] == expected_steps[0]
    assert validation.call_args.args[:2] == expected_steps[1:]
    assert validation.call_args.args[2] == (
        integrator.MinimumIntegrationTimeStepHandling.throw_exception_below_minimum
    )
    assert validation.call_args.kwargs == {
        "accept_infinity_step": False,
        "accept_nan_step": False,
    }
    assert factory.call_args.args[1] == (
        integrator.CoefficientSets.rkdp_87
        if tighter
        else integrator.CoefficientSets.rkf_78
    )
    assert factory.call_args.kwargs == {"assess_termination_on_minor_steps": False}


@pytest.mark.parametrize("arc,tighter", [(None, False), ("burn", False), ("coast", 1)])
def test_invalid_integrator_options_do_not_import_native(
    arc: object,
    tighter: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    importer = MagicMock(side_effect=AssertionError("native boundary reached"))
    monkeypatch.setattr(trajectory, "_import_tudat_propagation_setup", importer)
    with pytest.raises(TrajectoryRefinementError) as caught:
        trajectory._build_arc_integrator(
            "integrator-control",
            arc,
            tighter=tighter,  # type: ignore[arg-type] -- invalid-input test
        )
    assert isinstance(caught.value.__cause__, ValueError)
    importer.assert_not_called()


@pytest.mark.parametrize("stage", ["import", "control", "validation", "factory"])
def test_integrator_setup_failure_preserves_cause(
    stage: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native = MagicMock()
    importer = MagicMock(return_value=native)
    original = RuntimeError("injected setup failure")
    failing = {
        "import": importer,
        "control": native.integrator.step_size_control_elementwise_matrix_tolerance,
        "validation": native.integrator.step_size_validation,
        "factory": native.integrator.runge_kutta_variable_step,
    }[stage]
    failing.side_effect = original
    monkeypatch.setattr(trajectory, "_import_tudat_propagation_setup", importer)
    with pytest.raises(TrajectoryRefinementError, match="integrator-control") as caught:
        trajectory._build_arc_integrator("integrator-control", "coast")
    assert caught.value.__cause__ is original
