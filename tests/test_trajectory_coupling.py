from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


@pytest.mark.parametrize("case", ["state", "mass", "epoch", "thrust"])
def test_invalid_arc_input_fails_before_native_setup(
    case: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    importer = MagicMock(side_effect=AssertionError("native setup reached"))
    monkeypatch.setattr(trajectory, "_import_tudat_propagation_setup", importer)
    with pytest.raises(TrajectoryRefinementError, match="coupling-control") as caught:
        trajectory._build_coupled_arc_settings(
            "coupling-control", MagicMock(), MagicMock(),
            (0.0,) * (5 if case == "state" else 6),
            True if case == "mass" else 1500.0,
            float("nan") if case == "epoch" else 100.0,
            MagicMock(), MagicMock(),
            thrust_enabled=1 if case == "thrust" else True,  # type: ignore[arg-type]
        )
    assert caught.value.__cause__ is not None
    importer.assert_not_called()


@pytest.mark.parametrize(
    "case", ["import", "frame", "rate", "models", "translation", "mass", "coupled"],
)
def test_native_coupling_failure_keeps_original_cause(
    case: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bodies = MagicMock()
    bodies.global_frame_origin.return_value = "Earth" if case == "frame" else "SSB"
    bodies.global_frame_orientation.return_value = "J2000"
    setup = MagicMock()
    importer = MagicMock(return_value=setup)
    failure = RuntimeError("native coupling failure")
    failing_calls = {
        "import": importer,
        "rate": setup.mass_rate.from_thrust,
        "models": setup.create_mass_rate_models,
        "translation": setup.propagator.translational,
        "mass": setup.propagator.mass,
        "coupled": setup.propagator.multitype,
    }
    if case != "frame":
        failing_calls[case].side_effect = failure
    monkeypatch.setattr(trajectory, "_import_tudat_propagation_setup", importer)
    with pytest.raises(TrajectoryRefinementError, match="coupling-control") as caught:
        trajectory._build_coupled_arc_settings(
            "coupling-control", bodies, MagicMock(), (0.0,) * 6,
            1500.0, 100.0, MagicMock(), MagicMock(), thrust_enabled=True,
        )
    if case == "frame":
        assert isinstance(caught.value.__cause__, ValueError)
    else:
        assert caught.value.__cause__ is failure
    if case != "coupled":
        setup.propagator.multitype.assert_not_called()
