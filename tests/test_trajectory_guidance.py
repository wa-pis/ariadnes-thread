from __future__ import annotations

from dataclasses import FrozenInstanceError
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Literal

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("burn_id", ["departure", "arrival"])
@pytest.mark.parametrize("excess", [(-2.0, 3.0, 4.0), (0.0, -1.0, 0.0),
                                    (0.0, 0.0, 1.0), (0.0, 0.0, -1.0)])
@pytest.mark.parametrize("state", [(1.0, 0.0, 0.0, 0.0, 1.0, 0.0),
                                   (2.0, 3.0, 4.0, -1.0, 2.0, 3.0)])
def test_burn_angle_seed_reconstructs_signed_excess_direction(
    burn_id: Literal["departure", "arrival"], excess: tuple[float, ...],
    state: tuple[float, ...],
) -> None:
    import numpy as np

    angles = trajectory._seed_burn_angles_rad("seed-control", burn_id, excess, state)
    azimuth_rad, elevation_rad = angles
    assert -math.pi <= azimuth_rad < math.pi
    assert -math.pi / 2 <= elevation_rad <= math.pi / 2
    actual = _oracle_direction(state, np.zeros(6), *angles)
    expected = np.asarray(excess) / np.linalg.norm(excess)
    if burn_id == "arrival":
        expected = -expected
    assert np.linalg.norm(actual - expected) <= 1e-12
    assert angles == trajectory._seed_burn_angles_rad("seed-control", burn_id, excess, state)


@pytest.mark.parametrize("excess", [(0.0, 0.0, 0.0), (1e-12, 0.0, 0.0),
                                    (math.nan, 0.0, 0.0), (True, 0.0, 0.0)])
def test_burn_angle_seed_rejects_undefined_excess(excess: tuple[object, ...]) -> None:
    with pytest.raises(TrajectoryRefinementError, match="seed-control.*excess") as caught:
        trajectory._seed_burn_angles_rad(
            "seed-control", "departure", excess, (1.0, 0.0, 0.0, 0.0, 1.0, 0.0),
        )
    assert isinstance(caught.value.__cause__, ValueError)


def test_burn_angle_seed_rejects_bad_burn_and_degenerate_frame() -> None:
    for burn_id, state in (("coast", (1.0,) * 6), ("arrival", (0.0,) * 6)):
        with pytest.raises(TrajectoryRefinementError, match="seed-control") as caught:
            trajectory._seed_burn_angles_rad(
                "seed-control", burn_id, (1.0, 2.0, 3.0), state,  # type: ignore[arg-type]
            )
        assert isinstance(caught.value.__cause__, ValueError)


class _FakeBody:
    def __init__(self, state: object) -> None:
        self._state = state
        self.state_reads = 0

    @property
    def state(self) -> object:
        self.state_reads += 1
        return self._state

    def set_state(self, state: object) -> None:
        self._state = state


class _FakeBodies:
    def __init__(self, states: dict[str, object]) -> None:
        self._bodies = {
            name: _FakeBody(state) for name, state in states.items()
        }

    def get(self, body: str) -> _FakeBody:
        return self._bodies[body]

    def get_body(self, body: str) -> _FakeBody:
        return self.get(body)

    def body(self, name: str) -> _FakeBody:
        return self._bodies[name]


def _states() -> dict[str, tuple[float, ...]]:
    spacecraft = (1.0e9, -2.0e9, 3.0e9, 11.0, -7.0, 5.0)
    moon_relative = (2.0e6, 3.0e6, 4.0e6, 5.0, -1.0, 2.0)
    mars_relative = (-4.0e6, 2.0e6, 1.0e6, -3.0, 6.0, 2.0)
    return {
        "Spacecraft": spacecraft,
        "Moon": tuple(
            spacecraft[index] - moon_relative[index] for index in range(6)
        ),
        "Mars": tuple(
            spacecraft[index] - mars_relative[index] for index in range(6)
        ),
    }


def _oracle_direction(
    spacecraft_state: object,
    central_body_state: object,
    azimuth_rad: float,
    elevation_rad: float,
) -> Any:
    import numpy as np

    spacecraft = np.asarray(spacecraft_state, dtype=float)
    central_body = np.asarray(central_body_state, dtype=float)
    relative_position_m = spacecraft[:3] - central_body[:3]
    relative_velocity_m_s = spacecraft[3:] - central_body[3:]
    t_hat = relative_velocity_m_s / np.linalg.norm(relative_velocity_m_s)
    w_raw = np.cross(relative_position_m, relative_velocity_m_s)
    w_hat = w_raw / np.linalg.norm(w_raw)
    n_hat = np.cross(w_hat, t_hat)
    return (
        math.cos(elevation_rad) * math.cos(azimuth_rad) * t_hat
        + math.cos(elevation_rad) * math.sin(azimuth_rad) * n_hat
        + math.sin(elevation_rad) * w_hat
    )


def test_guidance_import_remains_tudatpy_and_kernel_lazy() -> None:
    code = """
import sys
from space_nav import ephemeris, trajectory

assert trajectory._TNW_DEGENERACY_THRESHOLD == 1e-12
assert trajectory._VECTOR_TOLERANCE == 1e-12
assert trajectory._TnwBasis
assert trajectory._build_tnw_basis
assert trajectory._direction_tnw_from_angles
assert trajectory._map_tnw_direction_to_inertial
assert trajectory._build_tnw_direction_callback
assert not any(
    name == "tudatpy" or name.startswith("tudatpy.") for name in sys.modules
)
assert "numpy" not in sys.modules
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


def test_tnw_basis_matches_independent_oracle_and_is_right_handed() -> None:
    import numpy as np

    position_m = np.asarray([7.0, -3.0, 2.0])
    velocity_m_s = np.asarray([1.0, 4.0, -2.0])
    basis = trajectory._build_tnw_basis(position_m, velocity_m_s)

    expected_t = velocity_m_s / np.linalg.norm(velocity_m_s)
    expected_w_raw = np.cross(position_m, velocity_m_s)
    expected_w = expected_w_raw / np.linalg.norm(expected_w_raw)
    expected_n = np.cross(expected_w, expected_t)
    actual = np.asarray((basis.t_hat, basis.n_hat, basis.w_hat))
    expected = np.asarray((expected_t, expected_n, expected_w))

    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1.0e-15)
    np.testing.assert_allclose(
        actual @ actual.T,
        np.identity(3),
        rtol=0.0,
        atol=1.0e-15,
    )
    np.testing.assert_allclose(
        np.cross(actual[0], actual[1]),
        actual[2],
        rtol=0.0,
        atol=1.0e-15,
    )
    assert not hasattr(basis, "__dict__")
    with pytest.raises(FrozenInstanceError):
        basis.t_hat = (1.0, 0.0, 0.0)  # type: ignore[misc]


def test_tnw_basis_is_invariant_under_positive_position_velocity_scaling() -> None:
    import numpy as np

    position_m = np.asarray([7.0, -3.0, 2.0])
    velocity_m_s = np.asarray([1.0, 4.0, -2.0])
    baseline = trajectory._build_tnw_basis(position_m, velocity_m_s)
    scaled = trajectory._build_tnw_basis(
        7.5 * position_m,
        0.125 * velocity_m_s,
    )

    np.testing.assert_allclose(
        (scaled.t_hat, scaled.n_hat, scaled.w_hat),
        (baseline.t_hat, baseline.n_hat, baseline.w_hat),
        rtol=0.0,
        atol=1.0e-15,
    )


@pytest.mark.parametrize(
    ("azimuth_rad", "elevation_rad", "expected"),
    [
        (0.0, 0.0, (1.0, 0.0, 0.0)),
        (math.pi / 2.0, 0.0, (0.0, 1.0, 0.0)),
        (-math.pi / 2.0, 0.0, (0.0, -1.0, 0.0)),
        (0.0, math.pi / 2.0, (0.0, 0.0, 1.0)),
        (0.0, -math.pi / 2.0, (0.0, 0.0, -1.0)),
    ],
)
def test_tnw_angle_cardinals_have_exact_axis_order_and_sign(
    azimuth_rad: float,
    elevation_rad: float,
    expected: tuple[float, float, float],
) -> None:
    direction = trajectory._direction_tnw_from_angles(
        azimuth_rad,
        elevation_rad,
    )

    assert direction == pytest.approx(expected, rel=0.0, abs=1.0e-15)


def test_angle_formula_and_inertial_mapping_are_exact_and_unit_length() -> None:
    import numpy as np

    azimuth_rad = math.pi / 3.0
    elevation_rad = -math.pi / 6.0
    expected_tnw = (
        math.cos(elevation_rad) * math.cos(azimuth_rad),
        math.cos(elevation_rad) * math.sin(azimuth_rad),
        math.sin(elevation_rad),
    )
    direction_tnw = trajectory._direction_tnw_from_angles(
        azimuth_rad,
        elevation_rad,
    )
    basis = trajectory._build_tnw_basis(
        (2.0, 0.0, 0.0),
        (0.0, 3.0, 0.0),
    )
    direction_inertial = trajectory._map_tnw_direction_to_inertial(
        basis,
        direction_tnw,
    )
    expected_inertial = (
        -expected_tnw[1],
        expected_tnw[0],
        expected_tnw[2],
    )

    assert direction_tnw == pytest.approx(expected_tnw, rel=0.0, abs=1.0e-15)
    np.testing.assert_allclose(
        direction_inertial,
        expected_inertial,
        rtol=0.0,
        atol=1.0e-15,
    )
    assert abs(math.dist(direction_tnw, (0.0, 0.0, 0.0)) - 1.0) <= 1.0e-15
    assert abs(float(np.linalg.norm(direction_inertial)) - 1.0) <= 1.0e-15


@pytest.mark.parametrize(
    ("burn_id", "central_body"),
    [("departure", "Moon"), ("arrival", "Mars")],
)
def test_callback_subtracts_the_selected_central_body_state(
    burn_id: str,
    central_body: str,
) -> None:
    import numpy as np

    states = _states()
    bodies = _FakeBodies(states)
    azimuth_rad = 0.37
    elevation_rad = -0.21
    callback = trajectory._build_tnw_direction_callback(
        "d0001-t0035",
        bodies,
        burn_id,
        azimuth_rad,
        elevation_rad,
    )

    actual = callback(123.5)
    expected = _oracle_direction(
        states["Spacecraft"],
        states[central_body],
        azimuth_rad,
        elevation_rad,
    )
    wrong_body = "Mars" if central_body == "Moon" else "Moon"
    wrong = _oracle_direction(
        states["Spacecraft"],
        states[wrong_body],
        azimuth_rad,
        elevation_rad,
    )

    assert isinstance(actual, tuple)
    assert len(actual) == 3
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1.0e-12)
    assert float(np.linalg.norm(np.asarray(actual) - wrong)) > 1.0e-3
    assert bodies.body("Spacecraft").state_reads == 1
    assert bodies.body(central_body).state_reads == 1
    assert bodies.body(wrong_body).state_reads == 0


def test_callback_rebuilds_the_frame_from_each_current_state() -> None:
    import numpy as np

    states = _states()
    bodies = _FakeBodies(states)
    azimuth_rad = -0.41
    elevation_rad = 0.19
    callback = trajectory._build_tnw_direction_callback(
        "d0001-t0035",
        bodies,
        "departure",
        azimuth_rad,
        elevation_rad,
    )
    first = callback(100.0)

    updated_spacecraft = (
        1.2e9,
        -1.8e9,
        2.7e9,
        -9.0,
        13.0,
        4.0,
    )
    updated_relative = (3.0e6, -4.0e6, 2.0e6, 1.0, 3.0, -2.0)
    updated_moon = tuple(
        updated_spacecraft[index] - updated_relative[index]
        for index in range(6)
    )
    bodies.body("Spacecraft").set_state(updated_spacecraft)
    bodies.body("Moon").set_state(updated_moon)
    second = callback(101.0)
    expected_second = _oracle_direction(
        updated_spacecraft,
        updated_moon,
        azimuth_rad,
        elevation_rad,
    )

    np.testing.assert_allclose(second, expected_second, rtol=0.0, atol=1.0e-12)
    assert isinstance(first, tuple)
    assert isinstance(second, tuple)
    assert float(np.linalg.norm(np.asarray(first) - np.asarray(second))) > 1.0e-3
    assert bodies.body("Spacecraft").state_reads == 2
    assert bodies.body("Moon").state_reads == 2


@pytest.mark.parametrize(
    ("position_m", "velocity_m_s", "context"),
    [
        ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), "position"),
        ((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), "velocity"),
        ((math.nan, 0.0, 0.0), (0.0, 1.0, 0.0), "position"),
        ((1.0, 0.0, 0.0), (0.0, math.inf, 0.0), "velocity"),
        ((1.0, 0.0, 0.0), (2.0, 0.0, 0.0), "degenerate"),
        ((1.0, 0.0, 0.0), (1.0, 1.0e-12, 0.0), "degenerate"),
    ],
    ids=(
        "zero-position",
        "zero-velocity",
        "nonfinite-position",
        "nonfinite-velocity",
        "collinear",
        "threshold-collinear",
    ),
)
def test_tnw_basis_rejects_zero_nonfinite_and_collinear_states(
    position_m: object,
    velocity_m_s: object,
    context: str,
) -> None:
    with pytest.raises(ValueError, match=context):
        trajectory._build_tnw_basis(position_m, velocity_m_s)


def test_tnw_basis_accepts_geometry_just_above_degeneracy_threshold() -> None:
    import numpy as np

    basis = trajectory._build_tnw_basis(
        (1.0, 0.0, 0.0),
        (1.0, 1.0001e-12, 0.0),
    )

    assert np.all(np.isfinite((basis.t_hat, basis.n_hat, basis.w_hat)))


@pytest.mark.parametrize(
    ("azimuth_rad", "elevation_rad", "field"),
    [
        (True, 0.0, "azimuth_rad"),
        (math.nan, 0.0, "azimuth_rad"),
        (0.0, False, "elevation_rad"),
        (0.0, math.inf, "elevation_rad"),
    ],
)
def test_tnw_angles_reject_boolean_and_nonfinite_values(
    azimuth_rad: object,
    elevation_rad: object,
    field: str,
) -> None:
    with pytest.raises(ValueError, match=field):
        trajectory._direction_tnw_from_angles(
            azimuth_rad,
            elevation_rad,
        )


def test_callback_rejects_unknown_burn_before_reading_bodies() -> None:
    bodies = _FakeBodies(_states())

    with pytest.raises(
        TrajectoryRefinementError,
        match=r"d0001-t0035.*finite-burn-guidance.*burn_id",
    ) as caught:
        trajectory._build_tnw_direction_callback(
            "d0001-t0035",
            bodies,
            "coast",
            0.0,
            0.0,
        )

    assert isinstance(caught.value.__cause__, ValueError)
    assert all(body.state_reads == 0 for body in bodies._bodies.values())


def test_callback_wraps_invalid_angles_with_burn_and_body_context() -> None:
    bodies = _FakeBodies(_states())

    with pytest.raises(
        TrajectoryRefinementError,
        match=(
            r"d0001-t0035.*finite-burn-guidance.*departure.*Moon.*"
            r"azimuth_rad"
        ),
    ) as caught:
        trajectory._build_tnw_direction_callback(
            "d0001-t0035",
            bodies,
            "departure",
            math.nan,
            0.0,
        )

    assert isinstance(caught.value.__cause__, ValueError)
    assert all(body.state_reads == 0 for body in bodies._bodies.values())


def test_callback_missing_central_body_has_deterministic_context() -> None:
    states = _states()
    bodies = _FakeBodies({
        "Spacecraft": states["Spacecraft"],
        "Mars": states["Mars"],
    })
    callback = trajectory._build_tnw_direction_callback(
        "d0001-t0035",
        bodies,
        "departure",
        0.0,
        0.0,
    )

    messages = []
    causes = []
    for _ in range(2):
        with pytest.raises(TrajectoryRefinementError) as caught:
            callback(123.5)
        messages.append(str(caught.value))
        causes.append(caught.value.__cause__)

    assert messages[0] == messages[1]
    assert "d0001-t0035" in messages[0]
    assert "finite-burn-guidance" in messages[0]
    assert "departure" in messages[0]
    assert "Moon" in messages[0]
    assert "123.5" in messages[0]
    assert all(isinstance(cause, KeyError) for cause in causes)


def test_callback_invalid_runtime_state_is_wrapped_repeatably() -> None:
    states = _states()
    states["Spacecraft"] = (
        math.nan,
        *states["Spacecraft"][1:],
    )
    bodies = _FakeBodies(states)
    callback = trajectory._build_tnw_direction_callback(
        "d0001-t0035",
        bodies,
        "departure",
        0.0,
        0.0,
    )

    errors = []
    for _ in range(2):
        with pytest.raises(TrajectoryRefinementError) as caught:
            callback(321.0)
        errors.append(caught.value)

    assert str(errors[0]) == str(errors[1])
    assert "d0001-t0035" in str(errors[0])
    assert "finite-burn-guidance" in str(errors[0])
    assert "departure" in str(errors[0])
    assert "Moon" in str(errors[0])
    assert "321.0" in str(errors[0])
    assert all(isinstance(error.__cause__, ValueError) for error in errors)


@pytest.mark.parametrize("state", [
    (7.0e6, -3.0e6, 2.0e6, 100.0, 400.0, -200.0),
    (0.0, 2.0e6, 0.0, -1500.0, 0.0, 0.0),
])
def test_tnw_basis_matches_direct_tudat_rotation(
    state: tuple[float, ...],
) -> None:
    import numpy as np
    from tudatpy.astro import frame_conversion

    basis = trajectory._build_tnw_basis(state[:3], state[3:])
    # Our N = W cross T points inward: Tudat's default points outward.
    direct = frame_conversion.inertial_to_tnw_rotation_matrix(
        np.asarray(state), n_axis_points_away_from_central_body=False,
    )
    np.testing.assert_allclose(
        (basis.t_hat, basis.n_hat, basis.w_hat), direct,
        rtol=0.0, atol=1e-12,  # Dimensionless direction cosines.
    )


@pytest.mark.parametrize("axis", [
    (True, 0.0, 0.0), (math.nan, 0.0, 0.0), (2.0, 0.0, 0.0),
])
def test_basis_constructor_rejects_invalid_axes(axis: object) -> None:
    with pytest.raises(ValueError):
        trajectory._TnwBasis(axis, (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def test_basis_constructor_rejects_left_handed_axes() -> None:
    with pytest.raises(ValueError, match="T cross N"):
        trajectory._TnwBasis(
            (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, -1.0),
        )


@pytest.mark.parametrize("bad_position", [True, False])
def test_basis_rejects_overflowing_norm(bad_position: bool) -> None:
    huge = (1.7e308, 1.7e308, 0.0)
    with pytest.raises(ValueError, match="finite nonzero norm"):
        trajectory._build_tnw_basis(
            huge if bad_position else (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0) if bad_position else huge,
        )


def test_basis_copies_mutable_axis_input() -> None:
    axis = [1.0, 0.0, 0.0]
    basis = trajectory._TnwBasis(
        axis, (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
    )
    axis[0] = 2.0
    assert basis.t_hat == (1.0, 0.0, 0.0)


def test_mapping_rejects_nonunit_command() -> None:
    basis = trajectory._build_tnw_basis(
        (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
    )
    with pytest.raises(ValueError, match="unit vector"):
        trajectory._map_tnw_direction_to_inertial(basis, (2.0, 0.0, 0.0))
