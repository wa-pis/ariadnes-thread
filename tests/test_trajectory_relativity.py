from __future__ import annotations

from decimal import Inexact, ROUND_FLOOR, localcontext
from fractions import Fraction
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from space_nav import ephemeris, trajectory
from space_nav.errors import TrajectoryRefinementError
from space_nav.models import ImpulsiveTransferCandidate, SpacecraftSpec


ROOT = Path(__file__).resolve().parents[1]
_EPOCH_TDB_S = 12_345.0
_SUN_GRAVITATIONAL_PARAMETER_M3_S2 = 1.32712440018e20
_SPEED_OF_LIGHT_M_S = 299_792_458.0
_POSITION_M = (1.2e11, -0.7e11, 0.2e11)
_VELOCITY_M_S = (22.0e3, 27.0e3, -4.0e3)


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


def test_relativity_import_remains_tudatpy_and_kernel_lazy() -> None:
    code = """
import sys
from space_nav import ephemeris, trajectory

assert trajectory._RelativityResource
assert trajectory._build_relativistic_acceleration_settings
assert trajectory._set_general_relativity_ppn_parameters
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


def test_real_environment_installs_exact_sun_schwarzschild_correction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    import numpy as np
    from tudatpy.dynamics import (
        environment_setup,
        parameters_setup,
        propagation_setup,
    )

    relativity_calls: list[tuple[tuple[object, ...], dict[str, object], Any]] = []
    eih_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    gamma_calls: list[Any] = []
    beta_calls: list[Any] = []
    parameter_set_calls: list[
        tuple[tuple[Any, ...], Any, tuple[object, ...], dict[str, object], Any]
    ] = []
    acceleration = propagation_setup.acceleration
    original_relativity = acceleration.relativistic_correction
    original_eih = acceleration.einstein_infeld_hofmann
    original_gamma = parameters_setup.ppn_parameter_gamma
    original_beta = parameters_setup.ppn_parameter_beta
    original_parameter_set = parameters_setup.create_parameter_set

    empty_settings = environment_setup.BodyListSettings("SSB", "J2000")
    empty_bodies = environment_setup.create_system_of_bodies(empty_settings)
    poisoned_parameters = original_parameter_set(
        [original_gamma(), original_beta()],
        empty_bodies,
    )
    poisoned_parameters.parameter_vector = np.asarray([0.75, 1.25])
    assert np.array_equal(
        poisoned_parameters.parameter_vector,
        np.asarray([0.75, 1.25]),
    )

    def record_relativity(*args: object, **kwargs: object) -> Any:
        setting = original_relativity(*args, **kwargs)
        relativity_calls.append((args, kwargs, setting))
        return setting

    def record_eih(*args: object, **kwargs: object) -> Any:
        eih_calls.append((args, kwargs))
        return original_eih(*args, **kwargs)

    def record_gamma() -> Any:
        setting = original_gamma()
        gamma_calls.append(setting)
        return setting

    def record_beta() -> Any:
        setting = original_beta()
        beta_calls.append(setting)
        return setting

    def record_parameter_set(
        settings: Any,
        bodies: Any,
        *args: object,
        **kwargs: object,
    ) -> Any:
        parameters = original_parameter_set(settings, bodies, *args, **kwargs)
        parameter_set_calls.append(
            (tuple(settings), bodies, args, kwargs, parameters)
        )
        return parameters

    monkeypatch.setattr(acceleration, "relativistic_correction", record_relativity)
    monkeypatch.setattr(acceleration, "einstein_infeld_hofmann", record_eih)
    monkeypatch.setattr(parameters_setup, "ppn_parameter_gamma", record_gamma)
    monkeypatch.setattr(parameters_setup, "ppn_parameter_beta", record_beta)
    monkeypatch.setattr(
        parameters_setup,
        "create_parameter_set",
        record_parameter_set,
    )

    try:
        environment = trajectory._build_physical_environment(
            _real_candidate(monkeypatch),
            _spacecraft(),
            gravity_models_path=_gravity_models_path(),
        )

        assert len(relativity_calls) == 1
        args, kwargs, setting = relativity_calls[0]
        assert args == ()
        assert kwargs == {
            "use_schwarzschild": True,
            "use_lense_thirring": False,
            "use_de_sitter": False,
            "de_sitter_central_body": "",
        }
        assert eih_calls == []
        assert len(gamma_calls) == len(beta_calls) == 1
        assert len(parameter_set_calls) == 1
        ppn_settings, ppn_bodies, ppn_args, ppn_kwargs, ppn_parameters = (
            parameter_set_calls[0]
        )
        assert len(ppn_settings) == 2
        assert ppn_settings[0] is gamma_calls[0]
        assert ppn_settings[1] is beta_calls[0]
        assert ppn_bodies is environment.bodies
        assert ppn_args == ()
        assert ppn_kwargs == {}
        assert np.array_equal(
            ppn_parameters.parameter_vector,
            np.asarray([1.0, 1.0]),
        )
        assert environment.relativity == trajectory._RelativityResource(
            source_body="Sun",
            target_body="Spacecraft",
            acceleration_type="schwarzschild-relativistic-correction",
            ppn_beta=1.0,
            ppn_gamma=1.0,
            schwarzschild_enabled=True,
            lense_thirring_enabled=False,
            de_sitter_enabled=False,
            einstein_infeld_hoffmann_enabled=False,
        )
        assert tuple(environment.relativistic_acceleration_settings) == ("Sun",)
        assert environment.relativistic_acceleration_settings["Sun"] == (setting,)
    finally:
        poisoned_parameters.parameter_vector = np.asarray([1.0, 1.0])


def test_relativity_factory_failure_is_chained_with_candidate_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.dynamics import propagation_setup

    failure = RuntimeError("relativity settings factory failed")

    def fail_factory(*_args: object, **_kwargs: object) -> object:
        raise failure

    monkeypatch.setattr(
        propagation_setup.acceleration,
        "relativistic_correction",
        fail_factory,
    )

    with pytest.raises(
        TrajectoryRefinementError,
        match=(
            r"d0001-t0035.*force-model-construction.*"
            r"Sun Schwarzschild relativistic correction"
        ),
    ) as caught:
        trajectory._build_relativistic_acceleration_settings("d0001-t0035")

    assert caught.value.__cause__ is failure


def test_ppn_parameter_failure_is_chained_with_candidate_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.dynamics import environment_setup, parameters_setup

    body_settings = environment_setup.BodyListSettings("SSB", "J2000")
    bodies = environment_setup.create_system_of_bodies(body_settings)
    failure = RuntimeError("PPN parameter factory failed")

    def fail_parameter_set(*_args: object, **_kwargs: object) -> object:
        raise failure

    monkeypatch.setattr(
        parameters_setup,
        "create_parameter_set",
        fail_parameter_set,
    )

    with pytest.raises(
        TrajectoryRefinementError,
        match=r"d0001-t0035.*force-model-construction.*PPN",
    ) as caught:
        trajectory._set_general_relativity_ppn_parameters(
            "d0001-t0035",
            bodies,
        )

    assert caught.value.__cause__ is failure


@pytest.mark.parametrize("velocity", [
    _VELOCITY_M_S, (12000.0, -7000.0, 2000.0), (7000.0, 12000.0, 0.0), (0.0, 0.0, 0.0),
])
def test_real_schwarzschild_acceleration_matches_independent_formula(
    velocity: tuple[float, float, float],
) -> None:
    pytest.importorskip("tudatpy")
    import numpy as np
    from tudatpy import dynamics
    from tudatpy.dynamics import (
        environment_setup,
        parameters_setup,
        propagation_setup,
    )

    body_settings = environment_setup.BodyListSettings("SSB", "J2000")
    body_settings.add_empty_settings("Sun")
    sun_settings = body_settings.get("Sun")
    sun_settings.ephemeris_settings = environment_setup.ephemeris.constant(
        np.zeros(6),
        "SSB",
        "J2000",
    )
    sun_settings.gravity_field_settings = environment_setup.gravity_field.central(
        _SUN_GRAVITATIONAL_PARAMETER_M3_S2
    )
    bodies = environment_setup.create_system_of_bodies(body_settings)
    bodies.create_empty_body("Spacecraft")
    ppn_parameters = parameters_setup.create_parameter_set(
        [
            parameters_setup.ppn_parameter_gamma(),
            parameters_setup.ppn_parameter_beta(),
        ],
        bodies,
    )
    ppn_parameters.parameter_vector = np.asarray([0.8, 1.2])

    try:
        trajectory._set_general_relativity_ppn_parameters(
            "d0001-t0035",
            bodies,
        )
        assert np.array_equal(
            ppn_parameters.parameter_vector,
            np.asarray([1.0, 1.0]),
        )
        settings, resource = (
            trajectory._build_relativistic_acceleration_settings(
                "d0001-t0035"
            )
        )
        assert resource.ppn_beta == resource.ppn_gamma == 1.0
        acceleration_models = propagation_setup.create_acceleration_models(
            bodies,
            {"Spacecraft": settings},
            ["Spacecraft"],
            ["SSB"],
        )

        initial_state = np.asarray((*_POSITION_M, *velocity), dtype=float)
        output_variables = [
            propagation_setup.dependent_variable.single_acceleration(
                (
                    propagation_setup.acceleration
                    .relativistic_correction_acceleration_type
                ),
                "Spacecraft",
                "Sun",
            )
        ]
        integrator_settings = (
            propagation_setup.integrator.runge_kutta_fixed_step(
                0.01,
                propagation_setup.integrator.CoefficientSets.rk_4,
            )
        )
        termination_settings = propagation_setup.propagator.time_termination(
            _EPOCH_TDB_S + 0.01,
            terminate_exactly_on_final_condition=True,
        )
        propagator_settings = propagation_setup.propagator.translational(
            ["SSB"],
            acceleration_models,
            ["Spacecraft"],
            initial_state,
            _EPOCH_TDB_S,
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
        assert initial_epoch_tdb_s == _EPOCH_TDB_S
        actual_m_s2 = np.asarray(history[initial_epoch_tdb_s], dtype=float)
    finally:
        ppn_parameters.parameter_vector = np.asarray([1.0, 1.0])

    position_m = np.asarray(_POSITION_M, dtype=float)
    velocity_m_s = np.asarray(velocity, dtype=float)
    distance_m = float(np.linalg.norm(position_m))
    speed_squared_m2_s2 = float(np.dot(velocity_m_s, velocity_m_s))
    radial_velocity_m2_s = float(np.dot(position_m, velocity_m_s))
    expected_m_s2 = (
        _SUN_GRAVITATIONAL_PARAMETER_M3_S2
        / (_SPEED_OF_LIGHT_M_S**2 * distance_m**3)
        * (
            (
                4.0 * _SUN_GRAVITATIONAL_PARAMETER_M3_S2 / distance_m
                - speed_squared_m2_s2
            )
            * position_m
            + 4.0 * radial_velocity_m2_s * velocity_m_s
        )
    )
    expected_norm_m_s2 = float(np.linalg.norm(expected_m_s2))
    tolerance_m_s2 = max(1.0e-15, 1.0e-12 * expected_norm_m_s2)

    assert actual_m_s2.shape == (3,)
    assert np.all(np.isfinite(actual_m_s2))
    assert np.all(np.isfinite(expected_m_s2))
    assert float(np.linalg.norm(actual_m_s2)) > 0.0
    assert expected_norm_m_s2 > 0.0
    assert float(np.linalg.norm(actual_m_s2 - expected_m_s2)) <= tolerance_m_s2
    bound_m_s2 = trajectory._schwarzschild_acceleration_upper_bound(
        "relativity-bound", _SUN_GRAVITATIONAL_PARAMETER_M3_S2, distance_m * 0.999,
        math.sqrt(speed_squared_m2_s2) * 1.001,
    )
    assert float(np.linalg.norm(actual_m_s2)) <= bound_m_s2


@pytest.mark.parametrize("speed_m_s", [0.0, 5.0, 50000.0])
def test_schwarzschild_bound_rounds_outward_against_exact_rational_oracle(speed_m_s: float) -> None:
    gm_m3_s2, distance_m = 7.0, 3.0
    exact = Fraction(gm_m3_s2) / (299792458**2 * Fraction(distance_m)**2) * (
        4 * Fraction(gm_m3_s2) / Fraction(distance_m) + 3 * Fraction(speed_m_s)**2
    )
    bound_m_s2 = trajectory._schwarzschild_acceleration_upper_bound(
        "bound", gm_m3_s2, distance_m, speed_m_s,
    )
    assert Fraction(bound_m_s2) >= exact
    assert math.isclose(bound_m_s2, float(exact), rel_tol=1e-15)
    assert trajectory._schwarzschild_acceleration_upper_bound(
        "bound", gm_m3_s2, 2 * distance_m, speed_m_s,
    ) < bound_m_s2 / 4
    assert trajectory._schwarzschild_acceleration_upper_bound(
        "bound", gm_m3_s2, distance_m, speed_m_s + 1,
    ) > bound_m_s2
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_FLOOR
        context.traps[Inexact] = True
        assert trajectory._schwarzschild_acceleration_upper_bound(
            "bound", gm_m3_s2, distance_m, speed_m_s,
        ) == bound_m_s2


def test_radial_velocity_attains_schwarzschild_orientation_maximum() -> None:
    # Independent exact vector formula for r=(3,0,0), GM=7 and |v|<=5.
    bound_m_s2 = trajectory._schwarzschild_acceleration_upper_bound("bound", 7.0, 3.0, 5.0)
    norms_squared: list[Fraction] = []
    for velocity in ((5, 0, 0), (-5, 0, 0), (0, 5, 0), (3, 4, 0), (0, 0, 0)):
        speed_squared = sum(value**2 for value in velocity)
        radial_product = 3 * velocity[0]
        acceleration = tuple(
            Fraction(7, 299792458**2 * 27) * (
                (Fraction(28, 3) - speed_squared) * position + 4 * radial_product * value
            ) for position, value in zip((3, 0, 0), velocity, strict=True)
        )
        norm_squared = sum((value**2 for value in acceleration), Fraction(0))
        assert norm_squared <= Fraction(bound_m_s2)**2
        norms_squared.append(norm_squared)
    assert norms_squared[0] == norms_squared[1] == max(norms_squared)
    assert all(value < norms_squared[0] for value in norms_squared[2:])


@pytest.mark.parametrize("field", ["gm", "distance", "speed"])
@pytest.mark.parametrize("value", [True, -1.0, math.nan, math.inf, "bad"])
def test_schwarzschild_bound_rejects_invalid_inputs(field: str, value: object) -> None:
    values = {"gm": 7.0, "distance": 3.0, "speed": 5.0}
    values[field] = value  # type: ignore[assignment]  # Invalid input probe.
    with pytest.raises(TrajectoryRefinementError, match="schwarzschild-bound") as caught:
        trajectory._schwarzschild_acceleration_upper_bound(
            "bound", values["gm"], values["distance"], values["speed"],
        )
    assert caught.value.__cause__ is not None


@pytest.mark.parametrize(("gm_m3_s2", "distance_m"), [(0.0, 3.0), (7.0, 0.0)])
def test_schwarzschild_bound_rejects_zero_gm_or_distance(gm_m3_s2: float, distance_m: float) -> None:
    with pytest.raises(TrajectoryRefinementError, match="positive"):
        trajectory._schwarzschild_acceleration_upper_bound("bound", gm_m3_s2, distance_m, 0.0)


def test_schwarzschild_bound_handles_float_underflow_and_rejects_overflow() -> None:
    assert trajectory._schwarzschild_acceleration_upper_bound(
        "bound", 1e-300, 1e300, 0.0,
    ) == math.nextafter(0.0, math.inf)
    with pytest.raises(TrajectoryRefinementError, match="upper bound_m_s2"):
        trajectory._schwarzschild_acceleration_upper_bound("bound", 1e300, 1e-300, 0.0)
