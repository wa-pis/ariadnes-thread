from __future__ import annotations

from dataclasses import replace
import math
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys

import pytest

import space_nav
from space_nav.ephemeris import CartesianState
from space_nav.errors import TrajectoryRefinementError, TransferSearchError
from space_nav.models import (
    FiniteBurnRecord,
    ImpulsiveTransferCandidate,
    PhysicalTrajectoryResult,
    TrajectoryBoundaryDifference,
    TrajectoryBoundaryState,
    TransferSearchResult,
)
from space_nav.scenario import load_scenario
from space_nav import trajectory


ROOT = Path(__file__).resolve().parents[1]
SCENARIO = load_scenario(ROOT / "examples" / "reference_mission.toml")


def _candidate(**changes: object) -> ImpulsiveTransferCandidate:
    values: dict[str, object] = {
        "candidate_id": "d0001-t0035",
        "departure_epoch_utc": "2031-01-01T00:00:00Z",
        "arrival_epoch_utc": "2031-01-02T00:00:00Z",
        "departure_epoch_tdb_s": 100.0,
        "arrival_epoch_tdb_s": 200.0,
        "flight_time_s": 100.0,
        "departure_v_infinity_m_s": (1.0, 2.0, 3.0),
        "arrival_v_infinity_m_s": (4.0, 5.0, 6.0),
        "departure_delta_v_m_s": 10.0,
        "arrival_delta_v_m_s": 20.0,
        "total_delta_v_m_s": 30.0,
        "propellant_mass_kg": 100.0,
        "final_mass_kg": 1400.0,
        "mass_feasible": True,
    }
    values.update(changes)
    return ImpulsiveTransferCandidate(**values)  # type: ignore[arg-type]


def _search_result(candidate: ImpulsiveTransferCandidate) -> TransferSearchResult:
    return TransferSearchResult(
        ephemeris_origin="SSB",
        transfer_central_body="Sun",
        orientation="J2000",
        time_scale="TDB seconds since J2000",
        evaluated_candidates=1,
        solved_candidates=1,
        failed_candidates=0,
        mass_feasible_candidates=int(candidate.mass_feasible),
        pareto_front=(candidate,),
    )


def test_m3_contracts_are_public_package_exports() -> None:
    assert space_nav.TrajectoryBoundaryState is TrajectoryBoundaryState
    assert space_nav.FiniteBurnRecord is FiniteBurnRecord
    assert space_nav.TrajectoryBoundaryDifference is TrajectoryBoundaryDifference
    assert space_nav.PhysicalTrajectoryResult is PhysicalTrajectoryResult
    assert space_nav.TrajectoryRefinementError is TrajectoryRefinementError
    assert {
        "TrajectoryBoundaryState",
        "FiniteBurnRecord",
        "TrajectoryBoundaryDifference",
        "PhysicalTrajectoryResult",
        "TrajectoryRefinementError",
    } <= set(space_nav.__all__)


def test_m3_imports_do_not_import_tudatpy_or_load_kernels() -> None:
    code = """
import sys
import space_nav
from space_nav import (
    FiniteBurnRecord,
    PhysicalTrajectoryResult,
    TrajectoryBoundaryDifference,
    TrajectoryBoundaryState,
    TrajectoryRefinementError,
)
from space_nav import ephemeris, trajectory

assert not any(
    name == "tudatpy" or name.startswith("tudatpy.") for name in sys.modules
)
assert not ephemeris._kernels_loaded
assert "moon_to_mars" not in sys.modules
"""
    environment = os.environ | {"PYTHONPATH": str(ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_matching_candidate_is_reproduced_once_and_canonicalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reproduced = _candidate()
    supplied = replace(
        reproduced,
        departure_epoch_utc="2031-01-01T00:00:00.000001Z",
        arrival_epoch_utc="2031-01-02T00:00:00.000001Z",
        departure_epoch_tdb_s=reproduced.departure_epoch_tdb_s + 0.4e-6,
        arrival_epoch_tdb_s=reproduced.arrival_epoch_tdb_s + 0.8e-6,
        flight_time_s=reproduced.flight_time_s + 0.4e-6,
        departure_v_infinity_m_s=(1.0 + 0.5e-6, 2.0, 3.0),
        arrival_v_infinity_m_s=(4.0, 5.0 + 0.5e-6, 6.0),
        departure_delta_v_m_s=reproduced.departure_delta_v_m_s + 0.25e-6,
        arrival_delta_v_m_s=reproduced.arrival_delta_v_m_s + 0.25e-6,
        total_delta_v_m_s=reproduced.total_delta_v_m_s + 0.5e-6,
        propellant_mass_kg=reproduced.propellant_mass_kg * (1.0 + 0.5e-12),
        final_mass_kg=reproduced.final_mass_kg * (1.0 + 0.5e-12),
    )
    calls = 0

    def search(scenario: object) -> TransferSearchResult:
        nonlocal calls
        calls += 1
        assert scenario is SCENARIO
        return _search_result(reproduced)

    monkeypatch.setattr(trajectory, "search_impulsive_transfers", search)

    assert trajectory._verify_candidate_handoff(SCENARIO, supplied) is reproduced
    assert calls == 1


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        (
            {"departure_epoch_utc": "2031-01-01T00:00:00.000002Z"},
            "departure_epoch_utc",
        ),
        (
            {"arrival_epoch_utc": "2031-01-02T00:00:00.000002Z"},
            "arrival_epoch_utc",
        ),
        (
            {
                "departure_epoch_tdb_s": 100.0 + 2e-6,
                "arrival_epoch_tdb_s": 200.0 + 2e-6,
            },
            "departure_epoch_tdb_s",
        ),
        (
            {
                "arrival_epoch_tdb_s": 200.0 + 2e-6,
                "flight_time_s": 100.0 + 2e-6,
            },
            "arrival_epoch_tdb_s",
        ),
        (
            {
                "departure_epoch_tdb_s": 100.0 - 0.4e-6,
                "arrival_epoch_tdb_s": 200.0 + 0.4e-6,
                "flight_time_s": 100.0 + 1.2e-6,
            },
            "flight_time_s",
        ),
        (
            {"departure_v_infinity_m_s": (1.0 + 2e-6, 2.0, 3.0)},
            "departure_v_infinity_m_s",
        ),
        (
            {
                "departure_delta_v_m_s": 10.0 + 2e-6,
                "total_delta_v_m_s": 30.0 + 2e-6,
            },
            "departure_delta_v_m_s",
        ),
        (
            {
                "arrival_delta_v_m_s": 20.0 + 2e-6,
                "total_delta_v_m_s": 30.0 + 2e-6,
            },
            "arrival_delta_v_m_s",
        ),
        (
            {
                "departure_delta_v_m_s": 10.0 + 0.6e-6,
                "arrival_delta_v_m_s": 20.0 + 0.6e-6,
                "total_delta_v_m_s": 30.0 + 1.2e-6,
            },
            "total_delta_v_m_s",
        ),
        ({"propellant_mass_kg": 100.0 * (1.0 + 3e-12)}, "propellant_mass_kg"),
        (
            {"arrival_v_infinity_m_s": (4.0, 5.0 + 2e-6, 6.0)},
            "arrival_v_infinity_m_s",
        ),
        ({"final_mass_kg": 1400.0 * (1.0 + 3e-12)}, "final_mass_kg"),
        ({"mass_feasible": False}, "mass_feasible"),
    ],
)
def test_altered_candidate_is_rejected_before_refinement(
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, object],
    field: str,
) -> None:
    reproduced = _candidate()
    supplied = replace(reproduced, **changes)
    monkeypatch.setattr(
        trajectory,
        "search_impulsive_transfers",
        lambda _scenario: _search_result(reproduced),
    )

    with pytest.raises(
        TrajectoryRefinementError,
        match=rf"d0001-t0035.*candidate-verification.*{field}",
    ) as caught:
        trajectory._verify_candidate_handoff(SCENARIO, supplied)

    assert isinstance(caught.value.__cause__, ValueError)
    assert field in str(caught.value.__cause__)


def test_missing_malformed_and_search_failure_are_contextual_and_chained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reproduced = _candidate()
    monkeypatch.setattr(
        trajectory,
        "search_impulsive_transfers",
        lambda _scenario: _search_result(reproduced),
    )
    with pytest.raises(
        TrajectoryRefinementError,
        match="d9999-t9999.*candidate-verification.*Pareto",
    ) as missing:
        trajectory._verify_candidate_handoff(
            SCENARIO,
            replace(reproduced, candidate_id="d9999-t9999"),
        )
    assert isinstance(missing.value.__cause__, LookupError)

    def must_not_search(_scenario: object) -> TransferSearchResult:
        raise AssertionError("malformed candidate started M2 search")

    monkeypatch.setattr(trajectory, "search_impulsive_transfers", must_not_search)
    with pytest.raises(
        TrajectoryRefinementError,
        match="malformed.*candidate-verification",
    ) as malformed:
        trajectory._verify_candidate_handoff(
            SCENARIO,
            SimpleNamespace(candidate_id="malformed"),  # type: ignore[arg-type]
        )
    assert isinstance(malformed.value.__cause__, TypeError)

    failure = TransferSearchError("M2 search failed")

    def fail(_scenario: object) -> TransferSearchResult:
        raise failure

    monkeypatch.setattr(trajectory, "search_impulsive_transfers", fail)
    with pytest.raises(
        TrajectoryRefinementError,
        match="d0001-t0035.*candidate-verification.*M2 search failed",
    ) as search_failure:
        trajectory._verify_candidate_handoff(SCENARIO, reproduced)
    assert search_failure.value.__cause__ is failure


def _zero_body_state(body: str, epoch_tdb_s: float) -> CartesianState:
    epochs = {
        100.0: "2031-01-01T00:00:00Z",
        200.0: "2031-01-02T00:00:00Z",
    }
    return CartesianState(
        body=body,
        epoch_utc=epochs[epoch_tdb_s],
        epoch_tdb_s=epoch_tdb_s,
        origin="SSB",
        orientation="J2000",
        position_m=(0.0, 0.0, 0.0),
        velocity_m_s=(0.0, 0.0, 0.0),
    )


def test_boundary_states_match_direct_tudatpy_and_spice_conversion() -> None:
    from tudatpy.astro import element_conversion
    from tudatpy.interface import spice

    spice.load_standard_kernels()
    departure_tdb_s = float(
        spice.convert_date_string_to_ephemeris_time(
            _candidate().departure_epoch_utc
        )
    )
    arrival_tdb_s = float(
        spice.convert_date_string_to_ephemeris_time(_candidate().arrival_epoch_utc)
    )
    candidate = replace(
        _candidate(),
        departure_epoch_tdb_s=departure_tdb_s,
        arrival_epoch_tdb_s=arrival_tdb_s,
        flight_time_s=arrival_tdb_s - departure_tdb_s,
    )
    departure, target = trajectory._build_boundary_states(
        SCENARIO,
        candidate,
        trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
    )

    definitions = (
        (
            departure,
            SCENARIO.departure_orbit,
            "Moon",
            candidate.departure_epoch_tdb_s,
            trajectory.MOON_ORBIT_SHAPE_RADIUS_M,
            trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        ),
        (
            target,
            SCENARIO.target_orbit,
            "Mars",
            candidate.arrival_epoch_tdb_s,
            trajectory.MARS_ORBIT_SHAPE_RADIUS_M,
            trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        ),
    )
    expected_labels = ("departure-ignition", "arrival-cutoff")
    expected_utc = (
        candidate.departure_epoch_utc,
        candidate.arrival_epoch_utc,
    )

    for index, (boundary, orbit, body, epoch_tdb_s, radius_m, gm) in enumerate(
        definitions
    ):
        semi_major_axis_m = (
            2.0 * radius_m
            + orbit.periapsis_altitude_m
            + orbit.apoapsis_altitude_m
        ) / 2.0
        relative = element_conversion.keplerian_to_cartesian_elementwise(
            semi_major_axis_m,
            orbit.eccentricity,
            orbit.inclination_rad,
            orbit.argument_of_periapsis_rad,
            orbit.raan_rad,
            orbit.true_anomaly_rad,
            gm,
        )
        body_state = spice.get_body_cartesian_state_at_epoch(
            target_body_name=body,
            observer_body_name="SSB",
            reference_frame_name="J2000",
            aberration_corrections="NONE",
            ephemeris_time=epoch_tdb_s,
        )
        expected = tuple(
            float(body_state[component] + relative[component])
            for component in range(6)
        )

        assert boundary.label == expected_labels[index]
        assert boundary.epoch_utc == expected_utc[index]
        assert boundary.epoch_tdb_s == epoch_tdb_s
        assert boundary.origin == "SSB"
        assert boundary.orientation == "J2000"
        assert math.dist(boundary.position_m, expected[:3]) <= 0.001
        assert math.dist(boundary.velocity_m_s, expected[3:]) <= 0.000001


def test_reference_boundary_radii_are_body_relative_and_distinct() -> None:
    candidate = _candidate()
    departure, target = trajectory._build_boundary_states(
        SCENARIO,
        candidate,
        trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        state_query=_zero_body_state,
    )

    departure_radius_m = math.dist(departure.position_m, (0.0, 0.0, 0.0))
    target_radius_m = math.dist(target.position_m, (0.0, 0.0, 0.0))
    assert departure_radius_m == pytest.approx(1_837_400.0, abs=0.001)
    assert target_radius_m == pytest.approx(3_689_500.0, abs=0.001)
    assert departure_radius_m != pytest.approx(1_838_000.0, abs=0.001)
    assert target_radius_m != pytest.approx(3_696_000.0, abs=0.001)
    assert departure.position_m != (0.0, 0.0, 0.0)
    assert target.position_m != (0.0, 0.0, 0.0)


def test_boundary_builder_uses_exact_elements_gms_and_componentwise_addition() -> None:
    candidate = _candidate()
    converter_calls: list[tuple[float, ...]] = []
    query_calls: list[tuple[str, float]] = []

    def convert(*values: float) -> tuple[float, ...]:
        converter_calls.append(values)
        return (10.0, 20.0, 30.0, 1.0, 2.0, 3.0)

    def query(body: str, epoch_tdb_s: float) -> CartesianState:
        query_calls.append((body, epoch_tdb_s))
        offset = 100.0 if body == "Moon" else 1_000.0
        return CartesianState(
            body=body,
            epoch_utc=(
                candidate.departure_epoch_utc
                if body == "Moon"
                else candidate.arrival_epoch_utc
            ),
            epoch_tdb_s=epoch_tdb_s,
            origin="SSB",
            orientation="J2000",
            position_m=(offset, 2.0 * offset, 3.0 * offset),
            velocity_m_s=(4.0 * offset, 5.0 * offset, 6.0 * offset),
        )

    departure, target = trajectory._build_boundary_states(
        SCENARIO,
        candidate,
        trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        state_query=query,
        element_converter=convert,
    )

    assert query_calls == [("Moon", 100.0), ("Mars", 200.0)]
    assert departure.position_m == (110.0, 220.0, 330.0)
    assert departure.velocity_m_s == (401.0, 502.0, 603.0)
    assert target.position_m == (1_010.0, 2_020.0, 3_030.0)
    assert target.velocity_m_s == (4_001.0, 5_002.0, 6_003.0)
    assert converter_calls == [
        (
            1_837_400.0,
            0.0,
            math.pi / 2.0,
            0.0,
            0.0,
            0.0,
            trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        ),
        (
            8_539_500.0,
            SCENARIO.target_orbit.eccentricity,
            math.radians(25.0),
            0.0,
            0.0,
            0.0,
            trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        ),
    ]


def test_circular_departure_preserves_argument_of_latitude_equivalence() -> None:
    from tudatpy.astro import element_conversion

    candidate = _candidate()
    baseline_orbit = replace(
        SCENARIO.departure_orbit,
        argument_of_periapsis_rad=0.4,
        true_anomaly_rad=0.6,
    )
    baseline_scenario = replace(SCENARIO, departure_orbit=baseline_orbit)
    delta_rad = 1.5
    shifted_orbit = replace(
        baseline_orbit,
        argument_of_periapsis_rad=(
            baseline_orbit.argument_of_periapsis_rad + delta_rad
        )
        % math.tau,
        true_anomaly_rad=(baseline_orbit.true_anomaly_rad - delta_rad) % math.tau,
    )
    shifted_scenario = replace(SCENARIO, departure_orbit=shifted_orbit)
    converter_calls: list[tuple[float, ...]] = []

    def convert(*values: float) -> object:
        converter_calls.append(values)
        return element_conversion.keplerian_to_cartesian_elementwise(*values)

    baseline, _ = trajectory._build_boundary_states(
        baseline_scenario,
        candidate,
        trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        state_query=_zero_body_state,
        element_converter=convert,
    )
    shifted, _ = trajectory._build_boundary_states(
        shifted_scenario,
        candidate,
        trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
        state_query=_zero_body_state,
        element_converter=convert,
    )

    assert math.dist(baseline.position_m, shifted.position_m) <= 0.001
    assert math.dist(baseline.velocity_m_s, shifted.velocity_m_s) <= 0.000001
    assert converter_calls[0][3] == 0.0
    assert converter_calls[0][5] == pytest.approx(1.0)
    assert converter_calls[2][3] == 0.0
    assert converter_calls[2][5] == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("moon_gm", "converted_state"),
    [
        (0.0, (0.0,) * 6),
        (math.nan, (0.0,) * 6),
        (True, (0.0,) * 6),
        (
            trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            (True, 0.0, 0.0, 0.0, 0.0, 0.0),
        ),
        (
            trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            (0.0,) * 6,
        ),
        (
            trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            (0.0,) * 5,
        ),
        (
            trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            (0.0, 0.0, 0.0, 0.0, 0.0, math.inf),
        ),
    ],
)
def test_invalid_boundary_inputs_fail_with_context_and_no_fallback(
    moon_gm: float,
    converted_state: tuple[float, ...],
) -> None:
    query_calls: list[tuple[str, float]] = []

    def query(body: str, epoch_tdb_s: float) -> CartesianState:
        query_calls.append((body, epoch_tdb_s))
        return _zero_body_state(body, epoch_tdb_s)

    def convert(*_values: float) -> tuple[float, ...]:
        return converted_state

    with pytest.raises(
        TrajectoryRefinementError,
        match="d0001-t0035.*boundary-state-construction.*Moon.*100.0",
    ) as caught:
        trajectory._build_boundary_states(
            SCENARIO,
            _candidate(),
            moon_gm,
            trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            state_query=query,
            element_converter=convert,
        )

    assert isinstance(caught.value.__cause__, ValueError)
    assert query_calls == []


def test_boundary_body_and_ephemeris_failures_are_contextual_and_chained() -> None:
    wrong_scenario = replace(
        SCENARIO,
        departure_orbit=replace(SCENARIO.departure_orbit, central_body="Mars"),
    )
    with pytest.raises(
        TrajectoryRefinementError,
        match="d0001-t0035.*boundary-state-construction.*central_body.*Mars",
    ) as wrong_body:
        trajectory._build_boundary_states(
            wrong_scenario,
            _candidate(),
            trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            state_query=_zero_body_state,
        )
    assert isinstance(wrong_body.value.__cause__, ValueError)

    def wrong_utc(body: str, epoch_tdb_s: float) -> CartesianState:
        state = _zero_body_state(body, epoch_tdb_s)
        return replace(state, epoch_utc="2030-01-01T00:00:00Z")

    with pytest.raises(
        TrajectoryRefinementError,
        match="d0001-t0035.*boundary-state-construction.*exact UTC/TDB",
    ) as mismatched_epoch:
        trajectory._build_boundary_states(
            SCENARIO,
            _candidate(),
            trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            state_query=wrong_utc,
        )
    assert isinstance(mismatched_epoch.value.__cause__, ValueError)

    failure = space_nav.EphemerisError("missing kernel coverage")

    def fail(_body: str, _epoch_tdb_s: float) -> CartesianState:
        raise failure

    with pytest.raises(
        TrajectoryRefinementError,
        match="d0001-t0035.*boundary-state-construction.*missing kernel coverage",
    ) as unavailable:
        trajectory._build_boundary_states(
            SCENARIO,
            _candidate(),
            trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            state_query=fail,
        )
    assert unavailable.value.__cause__ is failure
