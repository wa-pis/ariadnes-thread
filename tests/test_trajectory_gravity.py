from __future__ import annotations

import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Literal
from unittest.mock import MagicMock

import pytest

from space_nav import ephemeris, trajectory
from space_nav.errors import TrajectoryRefinementError
from space_nav.models import ImpulsiveTransferCandidate, SpacecraftSpec


ROOT = Path(__file__).resolve().parents[1]

_SOURCE_ORDER = (
    "Sun",
    "Mercury",
    "Venus",
    "Earth",
    "Moon",
    "Mars",
    "Jupiter",
    "Saturn",
)


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
        "final_mass_kg": 1_400.0,
        "mass_feasible": True,
    }
    values.update(changes)
    return ImpulsiveTransferCandidate(**values)  # type: ignore[arg-type]


def _spacecraft() -> SpacecraftSpec:
    return SpacecraftSpec(
        initial_mass_kg=2_000.0,
        dry_mass_kg=1_000.0,
        max_thrust_n=1_000.0,
        isp_s=450.0,
        srp_area_m2=20.0,
        reflectivity_coefficient=1.3,
        maneuver_magnitude_sigma_fraction=0.001,
        maneuver_pointing_sigma_rad=math.radians(0.05),
    )


def _real_candidate(monkeypatch: pytest.MonkeyPatch) -> ImpulsiveTransferCandidate:
    monkeypatch.setattr(ephemeris, "_spice", None)
    monkeypatch.setattr(ephemeris, "_kernels_loaded", False)
    departure_epoch_utc = "2031-01-01T00:00:00Z"
    arrival_epoch_utc = "2031-01-02T00:00:00Z"
    departure_epoch_tdb_s = ephemeris.utc_to_tdb(departure_epoch_utc)
    arrival_epoch_tdb_s = ephemeris.utc_to_tdb(arrival_epoch_utc)
    return _candidate(
        departure_epoch_utc=departure_epoch_utc,
        arrival_epoch_utc=arrival_epoch_utc,
        departure_epoch_tdb_s=departure_epoch_tdb_s,
        arrival_epoch_tdb_s=arrival_epoch_tdb_s,
        flight_time_s=arrival_epoch_tdb_s - departure_epoch_tdb_s,
    )


def _gravity_models_path() -> Path:
    pytest.importorskip("tudatpy")
    from tudatpy import data

    return Path(data.get_gravity_models_path())


def _harmonic_resources() -> tuple[trajectory._HarmonicFieldResource, ...]:
    return (
        trajectory._HarmonicFieldResource(
            body="Moon",
            model="gggrx1200",
            file_name="gggrx_1200l_sha.tab",
            degree=200,
            order=200,
            expected_sha256=trajectory.MOON_HARMONIC_COEFFICIENT_SHA256,
            actual_sha256=trajectory.MOON_HARMONIC_COEFFICIENT_SHA256,
            associated_frame="IAU_Moon",
            rotation_base_frame="J2000",
            rotation_target_frame="IAU_Moon",
            gravitational_parameter_m3_s2=(
                trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2
            ),
            normalization_radius_m=(
                trajectory.MOON_HARMONIC_NORMALIZATION_RADIUS_M
            ),
            orbit_shape_radius_m=trajectory.MOON_ORBIT_SHAPE_RADIUS_M,
        ),
        trajectory._HarmonicFieldResource(
            body="Mars",
            model="jgmro120d",
            file_name="jgmro120d.txt",
            degree=120,
            order=120,
            expected_sha256=trajectory.MARS_HARMONIC_COEFFICIENT_SHA256,
            actual_sha256=trajectory.MARS_HARMONIC_COEFFICIENT_SHA256,
            associated_frame="IAU_Mars",
            rotation_base_frame="J2000",
            rotation_target_frame="IAU_Mars",
            gravitational_parameter_m3_s2=(
                trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2
            ),
            normalization_radius_m=(
                trajectory.MARS_HARMONIC_NORMALIZATION_RADIUS_M
            ),
            orbit_shape_radius_m=trajectory.MARS_ORBIT_SHAPE_RADIUS_M,
        ),
    )


def _expected_inventory() -> tuple[trajectory._GravityAccelerationResource, ...]:
    return (
        trajectory._GravityAccelerationResource(
            "Sun", "point-mass-gravity", None, None
        ),
        trajectory._GravityAccelerationResource(
            "Mercury", "point-mass-gravity", None, None
        ),
        trajectory._GravityAccelerationResource(
            "Venus", "point-mass-gravity", None, None
        ),
        trajectory._GravityAccelerationResource(
            "Earth", "point-mass-gravity", None, None
        ),
        trajectory._GravityAccelerationResource(
            "Moon", "spherical-harmonic-gravity", 200, 200
        ),
        trajectory._GravityAccelerationResource(
            "Mars", "spherical-harmonic-gravity", 120, 120
        ),
        trajectory._GravityAccelerationResource(
            "Jupiter", "point-mass-gravity", None, None
        ),
        trajectory._GravityAccelerationResource(
            "Saturn", "point-mass-gravity", None, None
        ),
    )


def test_gravity_assembly_import_remains_tudatpy_and_kernel_lazy() -> None:
    code = """
import sys
from space_nav import ephemeris, trajectory

assert trajectory._GravityAccelerationResource
assert trajectory._build_gravity_acceleration_settings
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


def test_gravity_settings_have_exact_sources_types_and_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.dynamics import propagation_setup

    calls: list[tuple[str, int | None, int | None, object]] = []

    def point_mass_gravity() -> object:
        setting = object()
        calls.append(("point-mass-gravity", None, None, setting))
        return setting

    def spherical_harmonic_gravity(degree: int, order: int) -> object:
        setting = object()
        calls.append(("spherical-harmonic-gravity", degree, order, setting))
        return setting

    monkeypatch.setattr(
        propagation_setup.acceleration,
        "point_mass_gravity",
        point_mass_gravity,
    )
    monkeypatch.setattr(
        propagation_setup.acceleration,
        "spherical_harmonic_gravity",
        spherical_harmonic_gravity,
    )

    settings_by_source, inventory = (
        trajectory._build_gravity_acceleration_settings(
            "d0001-t0035",
            _harmonic_resources(),
        )
    )

    assert inventory == _expected_inventory()
    assert tuple(settings_by_source) == _SOURCE_ORDER
    assert [(kind, degree, order) for kind, degree, order, _ in calls] == [
        (item.acceleration_type, item.degree, item.order) for item in inventory
    ]
    assert all(len(settings_by_source[source]) == 1 for source in _SOURCE_ORDER)
    assert [settings_by_source[source][0] for source in _SOURCE_ORDER] == [
        setting for _, _, _, setting in calls
    ]
    assert sum(
        item.acceleration_type == "point-mass-gravity" for item in inventory
    ) == 6
    assert not any(
        item.source_body in {"Moon", "Mars"}
        and item.acceleration_type == "point-mass-gravity"
        for item in inventory
    )


def test_gravity_inventory_validator_rejects_double_counting() -> None:
    settings_by_source = {source: (object(),) for source in _SOURCE_ORDER}
    settings_by_source["Moon"] += (object(),)

    with pytest.raises(ValueError, match="exactly one acceleration"):
        trajectory._validate_gravity_acceleration_inventory(
            settings_by_source,
            _expected_inventory(),
            _harmonic_resources(),
        )


@pytest.mark.parametrize(
    "case", ["success", "gravity", "srp", "relativity", "import", "ppn", "factory"],
)
@pytest.mark.parametrize("burn_id", [None, "departure", "arrival"])
def test_arc_force_assembly_inventory_order_and_failures(
    case: str, monkeypatch: pytest.MonkeyPatch,
    burn_id: Literal["departure", "arrival"] | None,
) -> None:
    environment = MagicMock(spec=trajectory._PhysicalEnvironment)
    gravity = {source: (object(),) for source in _SOURCE_ORDER}
    environment.gravity_acceleration_settings = gravity
    environment.gravity_acceleration_inventory = _expected_inventory()
    environment.harmonic_fields = _harmonic_resources()
    srp, relativity = object(), object()
    environment.solar_radiation_pressure_acceleration_settings = {"Sun": (srp,)}
    environment.relativistic_acceleration_settings = {"Sun": (relativity,)}
    native = MagicMock()
    importer = MagicMock(return_value=native)
    reset = MagicMock()
    failure = RuntimeError("injected native assembly failure")
    if case == "gravity":
        gravity["Moon"] += (object(),)
    elif case == "srp":
        environment.solar_radiation_pressure_acceleration_settings = {"Earth": (srp,)}
    elif case == "relativity":
        environment.relativistic_acceleration_settings = {"Sun": (relativity,) * 2}
    elif case == "import":
        importer.side_effect = failure
    elif case == "ppn":
        def fail_ppn(*args: object) -> None:
            raise TrajectoryRefinementError("PPN readback failure") from failure

        reset.side_effect = fail_ppn
    elif case == "factory":
        native.create_acceleration_models.side_effect = failure
    calls = MagicMock()
    calls.attach_mock(reset, "reset")
    calls.attach_mock(native.create_acceleration_models, "factory")
    monkeypatch.setattr(trajectory, "_import_tudat_propagation_setup", importer)
    monkeypatch.setattr(trajectory, "_set_general_relativity_ppn_parameters", reset)
    if case == "success":
        result = trajectory._build_arc_force_models(
            "assembly-control", environment, burn_id=burn_id,
        )
        assert result is native.create_acceleration_models.return_value
        assert [call[0] for call in calls.mock_calls] == ["reset", "factory"]
        reset.assert_called_once_with("assembly-control", environment.bodies)
        expected = dict(gravity)
        expected["Sun"] += (srp, relativity)
        if burn_id is None:
            native.acceleration.thrust_from_engine.assert_not_called()
        else:
            native.acceleration.thrust_from_engine.assert_called_once_with(
                f"{burn_id}-main",
            )
            expected["Spacecraft"] = (
                native.acceleration.thrust_from_engine.return_value,
            )
        native.create_acceleration_models.assert_called_once_with(
            environment.bodies, {"Spacecraft": expected}, ["Spacecraft"], ["SSB"],
        )
        assert all(len(value) == 1 for value in gravity.values())
    else:
        with pytest.raises(TrajectoryRefinementError) as caught:
            trajectory._build_arc_force_models(
                "assembly-control", environment, burn_id=burn_id,
            )
        if case in {"import", "ppn", "factory"}:
            assert caught.value.__cause__ is failure
        else:
            assert isinstance(caught.value.__cause__, ValueError)
        if case != "factory":
            native.create_acceleration_models.assert_not_called()
        if case != "ppn":
            assert "assembly-control" in str(caught.value)


@pytest.mark.parametrize("burn_id", ["coast", "", True, [], 1])
def test_arc_force_invalid_burn_fails_before_native_import(
    monkeypatch: pytest.MonkeyPatch, burn_id: object,
) -> None:
    importer = MagicMock()
    monkeypatch.setattr(trajectory, "_import_tudat_propagation_setup", importer)
    with pytest.raises(TrajectoryRefinementError, match="burn_id"):
        trajectory._build_arc_force_models(
            "invalid-burn", MagicMock(),
            burn_id=burn_id,  # type: ignore[arg-type]  # Invalid boundary probe.
        )
    importer.assert_not_called()


def test_gravity_factory_failure_is_chained_with_candidate_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.dynamics import propagation_setup

    failure = RuntimeError("gravity settings factory failed")

    def fail_factory() -> object:
        raise failure

    monkeypatch.setattr(
        propagation_setup.acceleration,
        "point_mass_gravity",
        fail_factory,
    )

    with pytest.raises(
        TrajectoryRefinementError,
        match=r"d0001-t0035.*force-model-construction.*point-mass-gravity.*Sun",
    ) as caught:
        trajectory._build_gravity_acceleration_settings(
            "d0001-t0035",
            _harmonic_resources(),
        )

    assert caught.value.__cause__ is not None
    assert caught.value.__cause__.__cause__ is failure


@pytest.mark.parametrize(
    ("combined", "burn_id"),
    [(False, None), (True, None), (True, "departure"), (True, "arrival")],
)
def test_real_gravity_matches_independent_fixed_state_component_sum(
    monkeypatch: pytest.MonkeyPatch,
    combined: bool,
    burn_id: Literal["departure", "arrival"] | None,
) -> None:
    pytest.importorskip("tudatpy")
    import numpy as np
    from tudatpy import dynamics
    from tudatpy.dynamics import (
        environment_setup, parameters_setup, propagation_setup,
    )

    candidate = _real_candidate(monkeypatch)
    environment = trajectory._build_physical_environment(
        candidate,
        _spacecraft(),
        gravity_models_path=_gravity_models_path(),
    )
    assert environment.gravity_acceleration_inventory == _expected_inventory()
    assert tuple(environment.gravity_acceleration_settings) == _SOURCE_ORDER
    bodies = environment.bodies
    if combined:
        trajectory._install_tnw_engine(
            candidate.candidate_id, bodies, _spacecraft(),
            burn_id or "departure", 0.4, 0.2,
        )
    bodies.create_empty_body("GravityOracle")
    if combined:
        bodies.get("GravityOracle").mass = _spacecraft().initial_mass_kg
        environment_setup.add_radiation_pressure_target_model(
            bodies, "GravityOracle",
            environment_setup.radiation_pressure.cannonball_radiation_target(
                20.0, 1.3, {"Sun": ["Moon", "Earth", "Mars"]},
            ),
        )
    ppn = parameters_setup.create_parameter_set(
        [parameters_setup.ppn_parameter_gamma(), parameters_setup.ppn_parameter_beta()],
        bodies,
    )

    production_models = propagation_setup.create_acceleration_models(
        bodies,
        {"Spacecraft": environment.gravity_acceleration_settings},
        ["Spacecraft"],
        ["SSB"],
    )
    direct_settings = {
        "Sun": [propagation_setup.acceleration.point_mass_gravity()],
        "Mercury": [propagation_setup.acceleration.point_mass_gravity()],
        "Venus": [propagation_setup.acceleration.point_mass_gravity()],
        "Earth": [propagation_setup.acceleration.point_mass_gravity()],
        "Moon": [
            propagation_setup.acceleration.spherical_harmonic_gravity(200, 200)
        ],
        "Mars": [
            propagation_setup.acceleration.spherical_harmonic_gravity(120, 120)
        ],
        "Jupiter": [propagation_setup.acceleration.point_mass_gravity()],
        "Saturn": [propagation_setup.acceleration.point_mass_gravity()],
    }
    if combined:
        direct_settings["Sun"] += [
            propagation_setup.acceleration.radiation_pressure(),
            propagation_setup.acceleration.relativistic_correction(
                use_schwarzschild=True,
                use_lense_thirring=False,
                use_de_sitter=False,
                de_sitter_central_body="",
            ),
        ]
    oracle_models = propagation_setup.create_acceleration_models(
        bodies,
        {"GravityOracle": direct_settings},
        ["GravityOracle"],
        ["SSB"],
    )
    acceleration_models = production_models | oracle_models

    epoch_tdb_s = candidate.departure_epoch_tdb_s
    moon_state = np.asarray(
        bodies.get("Moon").ephemeris.cartesian_state(epoch_tdb_s),
        dtype=float,
    )
    mars_state = np.asarray(
        bodies.get("Mars").ephemeris.cartesian_state(epoch_tdb_s),
        dtype=float,
    )
    fixed_states = {
        "near-Moon": moon_state
        + np.asarray([1_837_400.0, 0.0, 0.0, 0.0, 1500.0, 0.0]),
        "cruise": (moon_state + mars_state) / 2.0,
        "near-Mars": mars_state
        + np.asarray([3_689_500.0, 0.0, 0.0, 0.0, 1500.0, 0.0]),
    }

    acceleration = propagation_setup.acceleration
    component_variables = []
    for source in _SOURCE_ORDER:
        acceleration_type = (
            acceleration.spherical_harmonic_gravity_type
            if source in {"Moon", "Mars"}
            else acceleration.point_mass_gravity_type
        )
        component_variables.append(
            propagation_setup.dependent_variable.single_acceleration(
                acceleration_type,
                "GravityOracle",
                source,
            )
        )
    output_variables = [
        propagation_setup.dependent_variable.total_acceleration("Spacecraft"),
        *component_variables,
    ]
    if combined:
        output_variables += [
            propagation_setup.dependent_variable.single_acceleration(
                kind, "GravityOracle", "Sun",
            )
            for kind in (
                acceleration.radiation_pressure_type,
                acceleration.relativistic_correction_acceleration_type,
            )
        ]

    for label, state in fixed_states.items():
        if combined:
            try:
                ppn.parameter_vector = np.asarray([0.75, 1.25])
                production_models = trajectory._build_arc_force_models(
                    candidate.candidate_id, environment, burn_id=burn_id,
                )
                assert np.array_equal(ppn.parameter_vector, [1.0, 1.0]), label
                acceleration_models = production_models | oracle_models
            finally:
                ppn.parameter_vector = np.asarray([1.0, 1.0])
        integrator_settings = (
            propagation_setup.integrator.runge_kutta_fixed_step(
                0.01,
                propagation_setup.integrator.CoefficientSets.rk_4,
            )
        )
        termination_settings = propagation_setup.propagator.time_termination(
            epoch_tdb_s + 0.01,
            terminate_exactly_on_final_condition=True,
        )
        propagator_settings = propagation_setup.propagator.translational(
            ["SSB", "SSB"],
            acceleration_models,
            ["Spacecraft", "GravityOracle"],
            np.concatenate((state, state)),
            epoch_tdb_s,
            integrator_settings,
            termination_settings,
            output_variables=output_variables,
        )
        simulator = dynamics.simulator.create_dynamics_simulator(
            bodies,
            propagator_settings,
        )
        history = simulator.dependent_variable_history
        initial_epoch_tdb_s = min(history)
        assert initial_epoch_tdb_s == epoch_tdb_s, label
        initial_values = np.asarray(history[initial_epoch_tdb_s], dtype=float)
        production_total_m_s2 = initial_values[:3]
        direct_components_m_s2 = initial_values[3:].reshape(-1, 3)
        if not combined:
            for source, source_state in (("Moon", moon_state), ("Mars", mars_state)):
                field = bodies.get(source).gravity_field_model
                # A strictly smaller radius avoids treating a rounded norm as
                # a proven lower distance. This is a fixed-state control only.
                distance_floor_m = float(np.linalg.norm(state[:3] - source_state[:3])) * 0.999
                bound_m_s2 = trajectory._harmonic_acceleration_upper_bound(
                    candidate.candidate_id, field.gravitational_parameter,
                    field.reference_radius, distance_floor_m,
                    field.cosine_coefficients, field.sine_coefficients,
                )
                actual_m_s2 = float(np.linalg.norm(direct_components_m_s2[_SOURCE_ORDER.index(source)]))
                assert actual_m_s2 <= bound_m_s2, (label, source, actual_m_s2, bound_m_s2)
        direct_total_m_s2 = direct_components_m_s2.sum(axis=0)
        component_norm_sum_m_s2 = sum(
            float(np.linalg.norm(component))
            for component in direct_components_m_s2
        )
        if burn_id is not None:
            relative = state - (moon_state if burn_id == "departure" else mars_state)
            tangent = relative[3:] / np.linalg.norm(relative[3:])
            normal = np.cross(relative[:3], relative[3:])
            normal /= np.linalg.norm(normal)
            inward = np.cross(normal, tangent)
            direction = (
                math.cos(0.2) * math.cos(0.4) * tangent
                + math.cos(0.2) * math.sin(0.4) * inward
                + math.sin(0.2) * normal
            )
            thrust_acceleration_m_s2 = (
                _spacecraft().max_thrust_n / _spacecraft().initial_mass_kg
            )
            direct_total_m_s2 += thrust_acceleration_m_s2 * direction
            component_norm_sum_m_s2 += thrust_acceleration_m_s2
        tolerance_m_s2 = max(1e-15, 1e-12 * component_norm_sum_m_s2)

        assert all(math.isfinite(value) for value in production_total_m_s2), label
        assert np.all(np.isfinite(direct_components_m_s2)), label
        assert float(np.linalg.norm(direct_components_m_s2[4])) > 0.0, label
        assert float(np.linalg.norm(direct_components_m_s2[5])) > 0.0, label
        assert (
            float(np.linalg.norm(production_total_m_s2 - direct_total_m_s2))
            <= tolerance_m_s2
        ), label

    if combined and burn_id is None:
        # Only departure-main was installed: never silently select another engine.
        with pytest.raises(
            TrajectoryRefinementError, match="force-model-construction.*arrival",
        ) as caught:
            trajectory._build_arc_force_models(
                candidate.candidate_id, environment, burn_id="arrival",
            )
        assert caught.value.__cause__ is not None
