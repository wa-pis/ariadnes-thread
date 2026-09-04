from __future__ import annotations

import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

from space_nav import ephemeris, trajectory
from space_nav.errors import TrajectoryRefinementError
from space_nav.models import ImpulsiveTransferCandidate


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


def test_real_gravity_matches_independent_fixed_state_component_sum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    import numpy as np
    from tudatpy import dynamics
    from tudatpy.dynamics import propagation_setup

    candidate = _real_candidate(monkeypatch)
    environment = trajectory._build_physical_environment(
        candidate,
        gravity_models_path=_gravity_models_path(),
    )
    assert environment.gravity_acceleration_inventory == _expected_inventory()
    assert tuple(environment.gravity_acceleration_settings) == _SOURCE_ORDER
    bodies = environment.bodies
    bodies.create_empty_body("Spacecraft")
    bodies.create_empty_body("GravityOracle")

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
        + np.asarray([1_837_400.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        "cruise": (moon_state + mars_state) / 2.0,
        "near-Mars": mars_state
        + np.asarray([3_689_500.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
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

    for label, state in fixed_states.items():
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
        direct_components_m_s2 = initial_values[3:].reshape(len(_SOURCE_ORDER), 3)
        direct_total_m_s2 = direct_components_m_s2.sum(axis=0)
        component_norm_sum_m_s2 = sum(
            float(np.linalg.norm(component))
            for component in direct_components_m_s2
        )
        tolerance_m_s2 = max(1e-15, 1e-12 * component_norm_sum_m_s2)

        assert all(math.isfinite(value) for value in production_total_m_s2), label
        assert np.all(np.isfinite(direct_components_m_s2)), label
        assert float(np.linalg.norm(direct_components_m_s2[4])) > 0.0, label
        assert float(np.linalg.norm(direct_components_m_s2[5])) > 0.0, label
        assert (
            float(np.linalg.norm(production_total_m_s2 - direct_total_m_s2))
            <= tolerance_m_s2
        ), label
