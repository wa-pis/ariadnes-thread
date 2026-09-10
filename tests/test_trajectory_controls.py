from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError
from space_nav.scenario import load_scenario


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("offset_s", [-1.0, 0.0, 1.0])
def test_burn_window_requires_strictly_positive_coast(offset_s: float) -> None:
    spacecraft = load_scenario(ROOT / "examples/reference_mission.toml").spacecraft
    controls = (0.0, 0.0, 10.0, 0.0, 0.0, 20.0)
    result = trajectory._prepare_burn_controls(
        "control-fixture", spacecraft, 100.0, 130.0 + offset_s, controls,
    )
    assert result == (controls if offset_s > 0 else "rejected-control-bounds")


@pytest.mark.parametrize("total_burn_s", [999.0, 1000.0, 1001.0])
def test_analytic_dry_mass_boundary_uses_constant_mass_flow(total_burn_s: float) -> None:
    spacecraft = load_scenario(ROOT / "examples/reference_mission.toml").spacecraft
    # Choose exactly 1 kg/s, independently of production mass-flow arithmetic.
    spacecraft = replace(spacecraft, max_thrust_n=9.80665 * spacecraft.isp_s)
    controls = (0.0, 0.0, 500.0, 0.0, 0.0, total_burn_s - 500.0)
    result = trajectory._prepare_burn_controls(
        "control-fixture", spacecraft, 0.0, 2000.0, controls,
    )
    assert result == (controls if total_burn_s <= 1000 else "rejected-dry-mass")


@pytest.mark.parametrize("last_duration_s", [math.nextafter(500.0, 0.0), 500.0, math.nextafter(500.0, math.inf)])
def test_analytic_mass_gate_preserves_sub_ulp_duration_shortfalls(last_duration_s: float) -> None:
    spacecraft = load_scenario(ROOT / "examples/reference_mission.toml").spacecraft
    spacecraft = replace(spacecraft, max_thrust_n=9.80665 * spacecraft.isp_s)
    assert spacecraft.max_thrust_n / (9.80665 * spacecraft.isp_s) == 1.0  # kg/s
    assert spacecraft.initial_mass_kg - spacecraft.dry_mass_kg == 1000.0  # kg
    assert 500.0 + last_duration_s == 1000.0  # Rounded sum loses the side of the boundary.
    controls = (0.0, 0.0, 500.0, 0.0, 0.0, last_duration_s)
    result = trajectory._prepare_burn_controls("sub-ulp-mass", spacecraft, 0.0, 2000.0, controls)
    assert result == (controls if last_duration_s <= 500.0 else "rejected-dry-mass")


def test_control_angles_are_canonical_and_repeatable() -> None:
    spacecraft = load_scenario(ROOT / "examples/reference_mission.toml").spacecraft
    original = (5 * math.pi, math.pi / 2, 1.0, -5 * math.pi, -math.pi / 2, 2.0)
    expected = (-math.pi, math.pi / 2, 1.0, -math.pi, -math.pi / 2, 2.0)
    for controls in (original, expected):
        assert trajectory._prepare_burn_controls(
            "control-fixture", spacecraft, 0.0, 100.0, controls,
        ) == expected


@pytest.mark.parametrize("index", [2, 5])
def test_positive_duration_must_advance_representable_epoch(index: int) -> None:
    spacecraft = load_scenario(ROOT / "examples/reference_mission.toml").spacecraft
    controls = [0.0, 0.0, 1.0, 0.0, 0.0, 1.0]
    controls[index] = 1e-12
    assert trajectory._prepare_burn_controls(
        "control-fixture", spacecraft, 1e9, 1e9 + 100.0, tuple(controls),
    ) == "rejected-control-bounds"


@pytest.mark.parametrize("index,value", [(1, 2.0), (4, -2.0), (2, 0.0), (5, -1.0)])
def test_control_domain_rejects_bad_elevation_or_duration(index: int, value: float) -> None:
    spacecraft = load_scenario(ROOT / "examples/reference_mission.toml").spacecraft
    controls = [0.0, 0.0, 1.0, 0.0, 0.0, 1.0]
    controls[index] = value
    assert trajectory._prepare_burn_controls(
        "control-fixture", spacecraft, 0.0, 100.0, tuple(controls),
    ) == "rejected-control-bounds"


@pytest.mark.parametrize("invalid", [True, "1", math.nan, math.inf])
def test_nonfinite_or_malformed_controls_are_fatal(invalid: object) -> None:
    spacecraft = load_scenario(ROOT / "examples/reference_mission.toml").spacecraft
    with pytest.raises(TrajectoryRefinementError, match="control-fixture") as caught:
        trajectory._prepare_burn_controls(
            "control-fixture", spacecraft, 0.0, 100.0,
            (0.0, 0.0, 0.0, 0.0, invalid, 1.0),
        )
    assert isinstance(caught.value.__cause__, ValueError)


@pytest.mark.parametrize("case", ["length", "epoch", "order"])
def test_control_structure_and_epochs_are_validated(case: str) -> None:
    spacecraft = load_scenario(ROOT / "examples/reference_mission.toml").spacecraft
    with pytest.raises(TrajectoryRefinementError, match="control-fixture"):
        trajectory._prepare_burn_controls(
            "control-fixture", spacecraft, math.nan if case == "epoch" else 0.0,
            0.0 if case == "order" else 100.0,
            (1.0,) * (5 if case == "length" else 6),
        )
