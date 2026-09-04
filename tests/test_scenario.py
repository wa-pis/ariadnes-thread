from __future__ import annotations

import json
import math
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from space_nav.errors import ScenarioValidationError
from space_nav.scenario import load_scenario


REFERENCE = Path(__file__).parents[1] / "examples" / "reference_mission.toml"


def _scenario_file(tmp_path: Path, text: str | None = None) -> Path:
    path = tmp_path / "mission.toml"
    path.write_text(REFERENCE.read_text() if text is None else text, encoding="utf-8")
    return path


def _replace(tmp_path: Path, old: str, new: str) -> Path:
    return _scenario_file(tmp_path, REFERENCE.read_text().replace(old, new))


def test_reference_scenario_is_normalized_and_json_ready() -> None:
    scenario = load_scenario(REFERENCE)

    assert scenario.search.departure_start_utc == "2031-01-01T00:00:00Z"
    assert scenario.search.time_of_flight_min_s == 180 * 86_400
    assert scenario.departure_orbit.periapsis_altitude_m == 100_000
    assert scenario.departure_orbit.apoapsis_altitude_m == 100_000
    assert scenario.departure_orbit.inclination_rad == pytest.approx(math.pi / 2)
    assert scenario.target_orbit.periapsis_altitude_m == 300_000
    assert scenario.target_orbit.apoapsis_altitude_m == 10_000_000
    assert 0 < scenario.target_orbit.eccentricity < 1
    assert scenario.tracking.stations == ("DSS-14", "DSS-43", "DSS-63")
    assert scenario.tracking.cadence_s == 21_600
    assert scenario.spacecraft.maneuver_pointing_sigma_rad == pytest.approx(
        math.radians(0.05)
    )
    json.dumps(scenario.to_dict(), allow_nan=False)


def test_defaults_are_applied_independently(tmp_path: Path) -> None:
    text = REFERENCE.read_text()
    text = text[: text.index("[tracking]")]
    scenario = load_scenario(_scenario_file(tmp_path, text))

    assert scenario.tracking.stations == ("DSS-14", "DSS-43", "DSS-63")
    assert scenario.tracking.cadence_s == 6 * 3_600
    assert scenario.tracking.range_sigma_m == 10
    assert scenario.tracking.range_rate_sigma_m_s == 0.0001
    assert scenario.tracking.angular_sigma_rad == pytest.approx(math.radians(1 / 3600))
    assert scenario.tracking.min_elevation_rad == pytest.approx(math.radians(10))
    assert scenario.limits.runtime_seconds == 300
    assert scenario.limits.random_seed == 42
    assert scenario.limits.max_candidates == 2000


def test_values_are_immutable_deterministic_and_spice_free() -> None:
    first = load_scenario(REFERENCE)
    second = load_scenario(REFERENCE)

    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.limits.random_seed = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    ("old", "new", "field"),
    [
        ("max_thrust_n = 1000.0\n", "", "spacecraft.max_thrust_n"),
        ("max_thrust_n = 1000.0", "max_thrust_n = true", "spacecraft.max_thrust_n"),
        ("isp_s = 450.0", "isp_s = nan", "spacecraft.isp_s"),
        ("srp_area_m2 = 20.0", "srp_area_m2 = 0.0", "spacecraft.srp_area_m2"),
        ("initial_mass_kg = 2000.0", "initial_mass_kg = 1000.0", "spacecraft.initial_mass_kg"),
        ("departure_end_utc = \"2031-12-31T00:00:00Z\"", "departure_end_utc = \"2030-12-31T00:00:00Z\"", "search.departure_end_utc"),
        ("time_of_flight_max_days = 320.0", "time_of_flight_max_days = 180.0", "search.time_of_flight_max_days"),
        ("apoapsis_altitude_km = 10000.0", "apoapsis_altitude_km = 300.0", "target_orbit.apoapsis_altitude_km"),
        ("periapsis_altitude_km = 300.0", "periapsis_altitude_km = 301.0", "target_orbit.periapsis_altitude_km"),
        ("apoapsis_altitude_km = 10000.0", "apoapsis_altitude_km = 9999.0", "target_orbit.apoapsis_altitude_km"),
        ("inclination_deg = 90.0", "inclination_deg = 181.0", "departure_orbit.inclination_deg"),
        ("raan_deg = 0.0", "raan_deg = 360.0", "departure_orbit.raan_deg"),
        ("max_candidates = 2000", "max_candidates = 2001", "limits.max_candidates"),
    ],
)
def test_field_specific_validation(
    tmp_path: Path, old: str, new: str, field: str
) -> None:
    with pytest.raises(ScenarioValidationError) as caught:
        load_scenario(_replace(tmp_path, old, new))

    assert caught.value.field == field
    assert str(caught.value).count(field) == 1


def test_unknown_section_and_field_are_rejected(tmp_path: Path) -> None:
    for suffix, field in (
        ("\n[extra]\nvalue = 1\n", "extra"),
        ("\nlimits_typo = 1\n", "limits.limits_typo"),
    ):
        with pytest.raises(ScenarioValidationError) as caught:
            load_scenario(_scenario_file(tmp_path, REFERENCE.read_text() + suffix))
        assert caught.value.field == field


def test_missing_and_malformed_files_are_wrapped(tmp_path: Path) -> None:
    with pytest.raises(ScenarioValidationError) as missing:
        load_scenario(tmp_path / "missing.toml")
    assert missing.value.field is None

    with pytest.raises(ScenarioValidationError) as malformed:
        load_scenario(_scenario_file(tmp_path, "[search\n"))
    assert malformed.value.field is None

    invalid_utf8 = tmp_path / "invalid-utf8.toml"
    invalid_utf8.write_bytes(b"\xff\xfe")
    with pytest.raises(ScenarioValidationError, match="invalid TOML") as encoded:
        load_scenario(invalid_utf8)
    assert encoded.value.field is None


def test_one_tracking_override_preserves_other_defaults(tmp_path: Path) -> None:
    text = REFERENCE.read_text()
    text = text[: text.index("[tracking]")] + "[tracking]\ncadence_hours = 12.0\n"
    scenario = load_scenario(_scenario_file(tmp_path, text))

    assert scenario.tracking.cadence_s == 43_200
    assert scenario.tracking.range_sigma_m == 10
    assert scenario.limits.max_candidates == 2000
