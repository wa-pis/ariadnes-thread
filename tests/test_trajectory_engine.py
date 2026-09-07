from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError
from space_nav.scenario import load_scenario


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("case", ["spacecraft", "burn", "azimuth", "elevation"])
def test_invalid_engine_input_fails_before_native_setup(
    case: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    spacecraft = load_scenario(ROOT / "examples/reference_mission.toml").spacecraft
    native_import = MagicMock(side_effect=AssertionError("native setup reached"))
    monkeypatch.setattr(trajectory, "_import_tudat_environment_setup", native_import)
    with pytest.raises(TrajectoryRefinementError) as caught:
        trajectory._install_tnw_engine(
            "engine-control", MagicMock(),
            None if case == "spacecraft" else spacecraft,  # type: ignore[arg-type]
            "coast" if case == "burn" else "departure",  # type: ignore[arg-type]
            True if case == "azimuth" else 0.0,
            float("nan") if case == "elevation" else 0.0,
        )
    assert caught.value.__cause__ is not None
    native_import.assert_not_called()


@pytest.mark.parametrize("failure", ["import", "frame", "rotation", "engine"])
def test_native_engine_failures_are_contextual_and_chained(
    failure: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    spacecraft = load_scenario(ROOT / "examples/reference_mission.toml").spacecraft
    bodies = MagicMock()
    bodies.global_frame_origin.return_value = "Earth" if failure == "frame" else "SSB"
    bodies.global_frame_orientation.return_value = "J2000"
    environment = MagicMock()
    propagation = MagicMock()
    original = RuntimeError("injected native failure")
    importer = MagicMock(return_value=environment)
    if failure == "import":
        importer.side_effect = original
    elif failure == "rotation":
        environment.add_rotation_model.side_effect = original
    elif failure == "engine":
        environment.add_engine_model.side_effect = original
    monkeypatch.setattr(trajectory, "_import_tudat_environment_setup", importer)
    monkeypatch.setattr(
        trajectory, "_import_tudat_propagation_setup", MagicMock(return_value=propagation),
    )
    with pytest.raises(TrajectoryRefinementError, match="engine-control") as caught:
        trajectory._install_tnw_engine(
            "engine-control", bodies, spacecraft, "departure", 0.0, 0.0,
        )
    if failure == "frame":
        assert isinstance(caught.value.__cause__, ValueError)
    else:
        assert caught.value.__cause__ is original
    if failure in {"import", "frame", "rotation"}:
        environment.add_engine_model.assert_not_called()
