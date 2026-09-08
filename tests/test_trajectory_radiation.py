from __future__ import annotations

from dataclasses import replace
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
_EPOCH_TDB_S = 12345.0
_SOURCE_POSITION_M = (0.0, 0.0, 0.0)
_OCCULTING_POSITION_M = (1.0e9, 0.0, 0.0)
_SOURCE_RADIUS_M = 1.0e8
_OCCULTING_RADIUS_M = 1.0e8


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


def _synthetic_srp_system(
    spacecraft: SpacecraftSpec,
) -> tuple[Any, Any, trajectory._SolarRadiationPressureSetup]:
    import numpy as np
    from tudatpy.dynamics import environment_setup, propagation_setup

    setup = trajectory._build_solar_radiation_pressure_setup(
        "d0001-t0035",
        spacecraft,
    )
    positions_m = {
        "Sun": _SOURCE_POSITION_M,
        "Mercury": (-5.0e9, 5.0e9, 0.0),
        "Venus": (-5.0e9, -5.0e9, 0.0),
        "Earth": (0.0, 1.0e10, 0.0),
        "Moon": _OCCULTING_POSITION_M,
        "Mars": (0.0, -1.0e10, 0.0),
        "Jupiter": (5.0e9, 5.0e9, 0.0),
        "Saturn": (5.0e9, -5.0e9, 0.0),
    }
    radii_m = {body: 1.0e6 for body in trajectory.PHYSICAL_BODY_NAMES}
    radii_m["Sun"] = _SOURCE_RADIUS_M
    radii_m["Moon"] = _OCCULTING_RADIUS_M

    body_settings = environment_setup.BodyListSettings("SSB", "J2000")
    for body in trajectory.PHYSICAL_BODY_NAMES:
        body_settings.add_empty_settings(body)
        settings = body_settings.get(body)
        settings.ephemeris_settings = environment_setup.ephemeris.constant(
            np.asarray((*positions_m[body], 0.0, 0.0, 0.0)),
            "SSB",
            "J2000",
        )
        settings.shape_settings = environment_setup.shape.spherical(radii_m[body])
    body_settings.get("Sun").radiation_source_settings = setup.source_settings

    bodies = environment_setup.create_system_of_bodies(body_settings)
    trajectory._install_spacecraft_radiation_target(
        "d0001-t0035",
        environment_setup,
        bodies,
        setup,
    )
    acceleration_models = propagation_setup.create_acceleration_models(
        bodies,
        {
            trajectory.SPACECRAFT_BODY_NAME: (
                setup.acceleration_settings_by_source
            )
        },
        [trajectory.SPACECRAFT_BODY_NAME],
        ["SSB"],
    )
    return bodies, acceleration_models, setup


def _evaluate_srp(
    bodies: Any,
    acceleration_models: Any,
    state: Any,
) -> tuple[Any, float, float, float]:
    import numpy as np
    from tudatpy import dynamics
    from tudatpy.dynamics import propagation_setup

    acceleration = propagation_setup.acceleration
    output_variables = [
        propagation_setup.dependent_variable.single_acceleration(
            acceleration.radiation_pressure_type,
            trajectory.SPACECRAFT_BODY_NAME,
            "Sun",
        ),
        propagation_setup.dependent_variable.received_irradiance_shadow_function(
            trajectory.SPACECRAFT_BODY_NAME,
            "Sun",
        ),
        propagation_setup.dependent_variable.received_irradiance(
            trajectory.SPACECRAFT_BODY_NAME,
            "Sun",
        ),
        propagation_setup.dependent_variable.body_mass(
            trajectory.SPACECRAFT_BODY_NAME
        ),
    ]
    integrator_settings = propagation_setup.integrator.runge_kutta_fixed_step(
        0.01,
        propagation_setup.integrator.CoefficientSets.rk_4,
    )
    termination_settings = propagation_setup.propagator.time_termination(
        _EPOCH_TDB_S + 0.01,
        terminate_exactly_on_final_condition=True,
    )
    propagator_settings = propagation_setup.propagator.translational(
        ["SSB"],
        acceleration_models,
        [trajectory.SPACECRAFT_BODY_NAME],
        state,
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
    values = np.asarray(history[initial_epoch_tdb_s], dtype=float)
    assert values.shape == (6,)
    return values[:3], float(values[3]), float(values[4]), float(values[5])


def _assert_doubled(scaled: Any, baseline: Any) -> None:
    import numpy as np

    expected = 2.0 * baseline
    expected_norm = float(np.linalg.norm(expected))
    assert expected_norm > 0.0
    assert (
        float(np.linalg.norm(scaled - expected)) / expected_norm
        <= 1.0e-12
    )


def test_radiation_import_remains_tudatpy_and_kernel_lazy() -> None:
    code = """
import sys
from space_nav import ephemeris, trajectory

assert trajectory.SUN_LUMINOSITY_W == 3.828e26
assert trajectory.SPACECRAFT_BODY_NAME == "Spacecraft"
assert trajectory.SOLAR_RADIATION_OCCULTING_BODY_NAMES == ("Moon", "Earth", "Mars")
assert trajectory._build_solar_radiation_pressure_setup
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


def test_real_environment_installs_exact_explicit_solar_radiation_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.dynamics import environment_setup, propagation_setup

    calls: dict[str, list[Any]] = {
        "luminosity": [],
        "source": [],
        "target": [],
        "acceleration": [],
        "mass": [],
        "add_mass": [],
        "add_target": [],
    }
    radiation = environment_setup.radiation_pressure
    original_luminosity = radiation.constant_luminosity
    original_source = radiation.isotropic_radiation_source
    original_target = radiation.cannonball_radiation_target
    original_acceleration = propagation_setup.acceleration.radiation_pressure
    original_mass = environment_setup.rigid_body.constant_rigid_body_properties
    original_add_mass = environment_setup.add_mass_properties_model
    original_add_target = environment_setup.add_radiation_pressure_target_model

    def record_luminosity(luminosity_w: float) -> Any:
        result = original_luminosity(luminosity_w)
        calls["luminosity"].append((luminosity_w, result))
        return result

    def record_source(luminosity_settings: Any) -> Any:
        result = original_source(luminosity_settings)
        calls["source"].append((luminosity_settings, result))
        return result

    def record_target(
        area_m2: float,
        coefficient: float,
        occultors: dict[str, list[str]],
    ) -> Any:
        result = original_target(area_m2, coefficient, occultors)
        calls["target"].append(
            (area_m2, coefficient, dict(occultors), result)
        )
        return result

    def record_acceleration(*args: object, **kwargs: object) -> Any:
        result = original_acceleration(*args, **kwargs)
        calls["acceleration"].append((args, kwargs, result))
        return result

    def record_mass(mass_kg: float) -> Any:
        result = original_mass(mass_kg)
        calls["mass"].append((mass_kg, result))
        return result

    def record_add_mass(bodies: Any, body: str, settings: Any) -> None:
        calls["add_mass"].append((bodies, body, settings))
        original_add_mass(bodies, body, settings)

    def record_add_target(bodies: Any, body: str, settings: Any) -> None:
        calls["add_target"].append((bodies, body, settings))
        original_add_target(bodies, body, settings)

    monkeypatch.setattr(radiation, "constant_luminosity", record_luminosity)
    monkeypatch.setattr(radiation, "isotropic_radiation_source", record_source)
    monkeypatch.setattr(radiation, "cannonball_radiation_target", record_target)
    monkeypatch.setattr(
        propagation_setup.acceleration,
        "radiation_pressure",
        record_acceleration,
    )
    monkeypatch.setattr(
        environment_setup.rigid_body,
        "constant_rigid_body_properties",
        record_mass,
    )
    monkeypatch.setattr(
        environment_setup,
        "add_mass_properties_model",
        record_add_mass,
    )
    monkeypatch.setattr(
        environment_setup,
        "add_radiation_pressure_target_model",
        record_add_target,
    )

    spacecraft = _spacecraft()
    environment = trajectory._build_physical_environment(
        _real_candidate(monkeypatch),
        spacecraft,
        gravity_models_path=_gravity_models_path(),
    )

    assert len(calls["luminosity"]) == 1
    assert calls["luminosity"][0][0] == 3.828e26
    assert calls["source"] == [
        (calls["luminosity"][0][1], calls["source"][0][1])
    ]
    assert len(calls["target"]) == 1
    assert calls["target"][0][:3] == (
        spacecraft.srp_area_m2,
        spacecraft.reflectivity_coefficient,
        {"Sun": ["Moon", "Earth", "Mars"]},
    )
    assert len(calls["acceleration"]) == 1
    assert calls["acceleration"][0][:2] == ((), {})
    assert len(calls["mass"]) == 1
    assert calls["mass"][0][0] == spacecraft.initial_mass_kg
    assert len(calls["add_mass"]) == 1
    assert calls["add_mass"][0][1:] == (
        trajectory.SPACECRAFT_BODY_NAME,
        calls["mass"][0][1],
    )
    assert len(calls["add_target"]) == 1
    assert calls["add_target"][0][1:] == (
        trajectory.SPACECRAFT_BODY_NAME,
        calls["target"][0][3],
    )

    expected_resource = trajectory._SolarRadiationPressureResource(
        source_body="Sun",
        target_body="Spacecraft",
        luminosity_w=3.828e26,
        reference_area_m2=spacecraft.srp_area_m2,
        reflectivity_coefficient=spacecraft.reflectivity_coefficient,
        initial_mass_kg=spacecraft.initial_mass_kg,
        occulting_bodies=("Moon", "Earth", "Mars"),
        acceleration_type="cannonball-radiation-pressure",
        uses_current_body_mass=True,
    )
    assert environment.solar_radiation_pressure == expected_resource
    settings = environment.solar_radiation_pressure_acceleration_settings
    assert tuple(settings) == ("Sun",)
    assert len(settings["Sun"]) == 1
    assert settings["Sun"][0] is calls["acceleration"][0][2]
    assert set(environment.bodies.list_of_bodies()) == (
        set(trajectory.PHYSICAL_BODY_NAMES) | {"Spacecraft"}
    )
    spacecraft_body = environment.bodies.get("Spacecraft")
    assert spacecraft_body.mass == spacecraft.initial_mass_kg
    assert len(spacecraft_body.radiation_pressure_target_models) == 1
    assert spacecraft_body.radiation_pressure_target_models[
        0
    ].radiation_pressure_coefficient == spacecraft.reflectivity_coefficient
    assert environment.bodies.get("Sun").radiation_pressure_source_model is not None


def test_radiation_factory_failure_is_chained_with_candidate_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.dynamics import environment_setup

    failure = RuntimeError("luminosity factory failed")

    def fail_luminosity(_luminosity_w: float) -> object:
        raise failure

    monkeypatch.setattr(
        environment_setup.radiation_pressure,
        "constant_luminosity",
        fail_luminosity,
    )
    with pytest.raises(
        TrajectoryRefinementError,
        match=(
            r"d0001-t0035.*force-model-construction.*"
            r"explicit Sun cannonball radiation-pressure setup failed"
        ),
    ) as caught:
        trajectory._build_solar_radiation_pressure_setup(
            "d0001-t0035",
            _spacecraft(),
        )

    assert caught.value.__cause__ is failure


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (None, object()),
        ("initial_mass_kg", True),
        ("srp_area_m2", float("nan")),
        ("reflectivity_coefficient", 0.0),
    ],
)
def test_invalid_radiation_inputs_fail_before_tudat_factories(
    monkeypatch: pytest.MonkeyPatch,
    field: str | None,
    value: object,
) -> None:
    import_calls = 0

    def record_import() -> object:
        nonlocal import_calls
        import_calls += 1
        return object()

    monkeypatch.setattr(
        trajectory,
        "_import_tudat_environment_setup",
        record_import,
    )
    monkeypatch.setattr(
        trajectory,
        "_import_tudat_propagation_setup",
        record_import,
    )
    spacecraft: object = (
        value if field is None else replace(_spacecraft(), **{field: value})
    )

    with pytest.raises(
        TrajectoryRefinementError,
        match=r"d0001-t0035.*force-model-construction",
    ) as caught:
        trajectory._build_solar_radiation_pressure_setup(
            "d0001-t0035",
            spacecraft,  # type: ignore[arg-type]
        )

    expected_context = "spacecraft must be a SpacecraftSpec" if field is None else field
    assert expected_context in str(caught.value)
    assert caught.value.__cause__ is not None
    assert import_calls == 0


def test_radiation_target_install_failure_is_chained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.dynamics import environment_setup

    failure = RuntimeError("target factory failed")

    def fail_target_install(_bodies: Any, _body: str, _settings: Any) -> None:
        raise failure

    monkeypatch.setattr(
        environment_setup,
        "add_radiation_pressure_target_model",
        fail_target_install,
    )
    with pytest.raises(
        TrajectoryRefinementError,
        match=r"d0001-t0035.*force-model-construction.*Spacecraft",
    ) as caught:
        _synthetic_srp_system(_spacecraft())

    assert caught.value.__cause__ is failure


def test_clear_solar_radiation_scales_with_area_coefficient_and_current_mass(
) -> None:
    pytest.importorskip("tudatpy")
    import numpy as np
    from tudatpy import constants

    spacecraft = _spacecraft()
    base_bodies, base_models, _ = _synthetic_srp_system(spacecraft)
    area_bodies, area_models, _ = _synthetic_srp_system(
        replace(spacecraft, srp_area_m2=2.0 * spacecraft.srp_area_m2)
    )
    coefficient_bodies, coefficient_models, _ = _synthetic_srp_system(
        replace(
            spacecraft,
            reflectivity_coefficient=(
                2.0 * spacecraft.reflectivity_coefficient
            ),
        )
    )
    clear_state = np.asarray([2.0e9, 4.0e8, 0.0, 0.0, 0.0, 0.0])

    base_acceleration, base_shadow, base_irradiance, base_mass = _evaluate_srp(
        base_bodies,
        base_models,
        clear_state,
    )
    area_acceleration, area_shadow, _, area_mass = _evaluate_srp(
        area_bodies,
        area_models,
        clear_state,
    )
    coefficient_acceleration, coefficient_shadow, _, coefficient_mass = (
        _evaluate_srp(
            coefficient_bodies,
            coefficient_models,
            clear_state,
        )
    )
    base_bodies.get(trajectory.SPACECRAFT_BODY_NAME).mass = (
        spacecraft.initial_mass_kg / 2.0
    )
    mass_acceleration, mass_shadow, _, current_mass = _evaluate_srp(
        base_bodies,
        base_models,
        clear_state,
    )

    assert base_mass == area_mass == coefficient_mass == spacecraft.initial_mass_kg
    assert current_mass == spacecraft.initial_mass_kg / 2.0
    for shadow in (base_shadow, area_shadow, coefficient_shadow, mass_shadow):
        assert abs(shadow - 1.0) <= 1.0e-12
    _assert_doubled(area_acceleration, base_acceleration)
    _assert_doubled(coefficient_acceleration, base_acceleration)
    _assert_doubled(mass_acceleration, base_acceleration)

    distance_m = float(np.linalg.norm(clear_state[:3]))
    expected_irradiance_w_m2 = trajectory.SUN_LUMINOSITY_W / (
        4.0 * math.pi * distance_m**2
    )
    assert (
        abs(base_irradiance - expected_irradiance_w_m2)
        / expected_irradiance_w_m2
        <= 1.0e-12
    )
    expected_acceleration_m_s2 = (
        expected_irradiance_w_m2
        * spacecraft.srp_area_m2
        * spacecraft.reflectivity_coefficient
        / (constants.SPEED_OF_LIGHT * spacecraft.initial_mass_kg)
    )
    assert (
        abs(float(np.linalg.norm(base_acceleration)) - expected_acceleration_m_s2)
        / expected_acceleration_m_s2
        <= 1.0e-12
    )
    assert constants.SPEED_OF_LIGHT == trajectory._SPEED_OF_LIGHT_M_S == 299792458.0
    _, srp_bound_m_s2 = trajectory._thrust_and_srp_upper_bounds(
        "srp-bound", spacecraft, distance_m * 0.999, thrust_enabled=False,
    )
    assert current_mass == spacecraft.dry_mass_kg
    assert np.linalg.norm(mass_acceleration) <= srp_bound_m_s2


def test_clear_umbra_and_penumbra_match_direct_tudat_shadow_function() -> None:
    pytest.importorskip("tudatpy")
    import numpy as np
    from tudatpy.astro import fundamentals

    bodies, acceleration_models, _ = _synthetic_srp_system(_spacecraft())
    offsets_m = {
        "umbra": 0.0,
        "penumbra": 1.5e8,
        "clear": 4.0e8,
    }
    measured: dict[str, float] = {}
    for label, offset_m in offsets_m.items():
        state = np.asarray([2.0e9, offset_m, 0.0, 0.0, 0.0, 0.0])
        acceleration_m_s2, shadow, _, _ = _evaluate_srp(bodies, acceleration_models, state)
        thrust_bound_m_s2, srp_bound_m_s2 = trajectory._thrust_and_srp_upper_bounds(
            "srp-bound", _spacecraft(), float(np.linalg.norm(state[:3])) * 0.999,
            thrust_enabled=False,
        )
        assert thrust_bound_m_s2 == 0.0
        assert np.linalg.norm(acceleration_m_s2) <= srp_bound_m_s2
        direct_by_body = {}
        for occulting_body in trajectory.SOLAR_RADIATION_OCCULTING_BODY_NAMES:
            occulting = bodies.get(occulting_body)
            direct_by_body[occulting_body] = float(
                fundamentals.compute_shadow_function(
                    np.asarray(_SOURCE_POSITION_M),
                    _SOURCE_RADIUS_M,
                    occulting.ephemeris.cartesian_state(_EPOCH_TDB_S)[:3],
                    occulting.shape_model.average_radius,
                    state[:3],
                )
            )

        assert abs(direct_by_body["Earth"] - 1.0) <= 1.0e-12, label
        assert abs(direct_by_body["Mars"] - 1.0) <= 1.0e-12, label
        assert 0.0 <= shadow <= 1.0, label
        assert abs(shadow - direct_by_body["Moon"]) <= 1.0e-12, label
        measured[label] = shadow

    assert abs(measured["umbra"]) <= 1.0e-12
    assert 0.0 < measured["penumbra"] < 1.0
    assert abs(measured["clear"] - 1.0) <= 1.0e-12


def test_thrust_srp_bounds_round_outward_against_exact_rational_oracles() -> None:
    spacecraft = replace(_spacecraft(), dry_mass_kg=3.0)
    distance_m = 149597870700.0
    thrust_m_s2, srp_m_s2 = trajectory._thrust_and_srp_upper_bounds(
        "bound", spacecraft, distance_m, thrust_enabled=True,
    )
    exact_thrust = Fraction(spacecraft.max_thrust_n) / Fraction(spacecraft.dry_mass_kg)
    exact_srp_enclosure = (
        Fraction(trajectory.SUN_LUMINOSITY_W) * Fraction(spacecraft.srp_area_m2)
        * Fraction(spacecraft.reflectivity_coefficient)
        / (12 * 299792458 * Fraction(spacecraft.dry_mass_kg) * Fraction(distance_m)**2)
    )
    for bound, exact in ((thrust_m_s2, exact_thrust), (srp_m_s2, exact_srp_enclosure)):
        assert Fraction(bound) >= exact
        assert math.isclose(bound, float(exact), rel_tol=1e-15)
    physical_srp_m_s2 = float(exact_srp_enclosure) * 3 / math.pi
    assert 1.047 < srp_m_s2 / physical_srp_m_s2 < 1.048
    assert trajectory._thrust_and_srp_upper_bounds(
        "bound", spacecraft, distance_m, thrust_enabled=False,
    ) == (0.0, srp_m_s2)
    distant = trajectory._thrust_and_srp_upper_bounds(
        "bound", spacecraft, 2 * distance_m, thrust_enabled=True,
    )
    assert distant == (thrust_m_s2, srp_m_s2 / 4)
    lighter = trajectory._thrust_and_srp_upper_bounds(
        "bound", replace(spacecraft, dry_mass_kg=1.5), distance_m, thrust_enabled=True,
    )
    assert lighter == (2 * thrust_m_s2, 2 * srp_m_s2)
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_FLOOR
        context.traps[Inexact] = True
        assert trajectory._thrust_and_srp_upper_bounds(
            "bound", spacecraft, distance_m, thrust_enabled=True,
        ) == (thrust_m_s2, srp_m_s2)


@pytest.mark.parametrize("field", [
    "dry_mass_kg", "max_thrust_n", "srp_area_m2", "reflectivity_coefficient", "distance",
])
@pytest.mark.parametrize("value", [True, 0.0, -1.0, math.nan, math.inf])
def test_thrust_srp_bounds_reject_invalid_contributing_inputs(field: str, value: float) -> None:
    spacecraft = _spacecraft() if field == "distance" else replace(_spacecraft(), **{field: value})
    with pytest.raises(TrajectoryRefinementError, match="thrust-srp-bound") as caught:
        trajectory._thrust_and_srp_upper_bounds(
            "bound", spacecraft, value if field == "distance" else 1e11, thrust_enabled=False,
        )
    assert caught.value.__cause__ is not None


@pytest.mark.parametrize("flag", [0, 1, "burn", None])
def test_thrust_srp_bounds_require_explicit_boolean_phase(flag: object) -> None:
    with pytest.raises(TrajectoryRefinementError, match="thrust_enabled"):
        trajectory._thrust_and_srp_upper_bounds(
            "bound", _spacecraft(), 1e11,
            thrust_enabled=flag,  # type: ignore[arg-type]  # Invalid input probe.
        )


def test_thrust_srp_bounds_reject_wrong_record_and_overflow() -> None:
    with pytest.raises(TrajectoryRefinementError, match="SpacecraftSpec"):
        trajectory._thrust_and_srp_upper_bounds(
            "bound", None, 1e11,  # type: ignore[arg-type]  # Invalid input probe.
            thrust_enabled=False,
        )
    with pytest.raises(TrajectoryRefinementError, match="upper bound_m_s2"):
        trajectory._thrust_and_srp_upper_bounds(
            "bound", replace(_spacecraft(), max_thrust_n=1e308, dry_mass_kg=1e-308),
            1.0, thrust_enabled=True,
        )


def test_thrust_srp_bounds_round_subnormal_srp_outward() -> None:
    _, bound_m_s2 = trajectory._thrust_and_srp_upper_bounds(
        "bound", replace(_spacecraft(), initial_mass_kg=1.1e300, dry_mass_kg=1e300),
        1e200, thrust_enabled=False,
    )
    assert bound_m_s2 == math.nextafter(0.0, math.inf)
