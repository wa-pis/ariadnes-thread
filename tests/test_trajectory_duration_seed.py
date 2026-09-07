from __future__ import annotations

from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError
from space_nav.scenario import load_scenario


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("delta_v_m_s", [(2000.0, 1500.0), (0.0, 1500.0), (2000.0, 0.0)])
def test_duration_seed_matches_high_precision_sequential_oracle(
    delta_v_m_s: tuple[float, float],
) -> None:
    spacecraft = load_scenario(ROOT / "examples/m3_feasible_mission.toml").spacecraft
    actual = trajectory._seed_burn_durations_s("seed-control", spacecraft, *delta_v_m_s)
    with localcontext() as context:
        context.prec = 50
        exhaust = Decimal("9.80665") * Decimal(str(spacecraft.isp_s))
        mass_rate = Decimal(str(spacecraft.max_thrust_n)) / exhaust
        mass = Decimal(str(spacecraft.initial_mass_kg))
        expected = []
        for delta_v in delta_v_m_s:
            after = mass * (-Decimal(str(delta_v)) / exhaust).exp()
            expected.append(float((mass - after) / mass_rate))
            mass = after
    assert actual == pytest.approx(expected, abs=1e-6, rel=0.0)
    assert actual == trajectory._seed_burn_durations_s(
        "seed-control", spacecraft, *delta_v_m_s,
    )
    if delta_v_m_s[0] > 0.0 and delta_v_m_s[1] > 0.0:
        fresh_mass_arrival = trajectory._seed_burn_durations_s(
            "seed-control", spacecraft, 0.0, delta_v_m_s[1],
        )[1]
        assert actual[1] < fresh_mass_arrival


@pytest.mark.parametrize("invalid", [True, "100", -1.0, float("nan"), float("inf")])
@pytest.mark.parametrize("burn", [0, 1])
def test_invalid_duration_seed_input_is_chained(
    invalid: object, burn: int,
) -> None:
    spacecraft = load_scenario(ROOT / "examples/m3_feasible_mission.toml").spacecraft
    values: list[object] = [2000.0, 1500.0]
    values[burn] = invalid
    with pytest.raises(TrajectoryRefinementError, match="seed-control.*burn-seed") as caught:
        trajectory._seed_burn_durations_s("seed-control", spacecraft, *values)
    assert isinstance(caught.value.__cause__, ValueError)
