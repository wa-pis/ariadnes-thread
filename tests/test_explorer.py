from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import tomllib

import pytest

from space_nav import ephemeris
from space_nav.errors import EphemerisError, ScenarioValidationError, TransferSearchError
from space_nav.explorer import propagate_two_body, sample_transfer
from space_nav.scenario import load_scenario, scenario_from_mapping
from space_nav.transfer import search_impulsive_transfers


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "examples/reference_mission.toml"


def test_mapping_parser_matches_file_and_rejects_invalid_mass() -> None:
    raw = tomllib.loads(REFERENCE.read_text())
    assert scenario_from_mapping(raw) == load_scenario(REFERENCE)
    raw["spacecraft"]["initial_mass_kg"] = 999.0
    with pytest.raises(ScenarioValidationError, match="initial_mass_kg"):
        scenario_from_mapping(raw)


@pytest.mark.parametrize("fraction", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_sampler_matches_independent_circular_orbit(fraction: float) -> None:
    radius_m, gm_m3_s2 = 7e6, 3.986004418e14
    speed_m_s = math.sqrt(gm_m3_s2 / radius_m)
    period_s = 2 * math.pi * math.sqrt(radius_m**3 / gm_m3_s2)
    actual = propagate_two_body(
        (radius_m, 0.0, 0.0, 0.0, speed_m_s, 0.0),
        fraction * period_s, gm_m3_s2,
    )
    angle = fraction * 2 * math.pi
    assert math.dist(actual[:3], (radius_m * math.cos(angle), radius_m * math.sin(angle), 0)) <= 0.01
    assert math.dist(actual[3:], (-speed_m_s * math.sin(angle), speed_m_s * math.cos(angle), 0)) <= 1e-6


def test_reference_arc_endpoints_repeatability_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = next(c for c in search_impulsive_transfers(load_scenario(REFERENCE)).pareto_front
                     if c.candidate_id == "d0001-t0035")
    states = sample_transfer(candidate)
    assert len(states) == 121
    assert states == sample_transfer(candidate)
    for state, body, excess in (
        (states[0], "Moon", candidate.departure_v_infinity_m_s),
        (states[-1], "Mars", candidate.arrival_v_infinity_m_s),
    ):
        reference = ephemeris._query_body_state_tdb(body, state.epoch_tdb_s)
        assert math.dist(state.position_m, reference.position_m) <= 100
        assert math.dist(state.velocity_m_s, tuple(reference.velocity_m_s[i] + excess[i] for i in range(3))) <= 0.001
        assert state.origin == "SSB" and state.orientation == "J2000"
    with pytest.raises(TransferSearchError, match="count"):
        sample_transfer(candidate, True)
    with pytest.raises(TransferSearchError, match="arrival"):
        sample_transfer(replace(candidate, departure_v_infinity_m_s=(0.0, 0.0, 0.0)))

    def unavailable(body: str, epoch: float) -> None:
        raise EphemerisError("kernel unavailable")

    monkeypatch.setattr(ephemeris, "_query_body_state_tdb", unavailable)
    with pytest.raises(TransferSearchError, match="resource error") as caught:
        sample_transfer(candidate)
    assert isinstance(caught.value.__cause__, EphemerisError)


@pytest.mark.parametrize("elapsed", [True, -1.0, math.nan, math.inf])
def test_sampling_rejects_bad_inputs(elapsed: float) -> None:
    with pytest.raises(TransferSearchError, match="finite SI"):
        propagate_two_body((7e6, 0.0, 0.0, 0.0, 7500.0, 0.0), elapsed, 3.986e14)
