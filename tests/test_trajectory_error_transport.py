"""Conditional error-transport lemma; not a full-force or native-stage certificate."""

from fractions import Fraction
import math

import pytest


def _coast_error_envelope(
    duration_s: float, position_error_m: Fraction, velocity_error_m_s: Fraction,
    position_sensitivity_s_inv2: Fraction, velocity_sensitivity_s_inv: Fraction,
    acceleration_defect_m_s2: Fraction,
) -> tuple[Fraction, Fraction]:
    """Bound SI position/velocity errors given a closed domain and uniform sensitivities.

    Reference position must differentiate to reference velocity. Its acceleration
    defect and force sensitivities must hold throughout both paths and chords.
    Returned bounds alone do not establish those premises or domain closure.
    """
    assert type(duration_s) is float and math.isfinite(duration_s) and duration_s >= 0
    assert all(isinstance(value, Fraction) and value >= 0 for value in (
        position_error_m, velocity_error_m_s, position_sensitivity_s_inv2,
        velocity_sensitivity_s_inv, acceleration_defect_m_s2,
    ))
    duration = Fraction(duration_s)
    feedback = position_sensitivity_s_inv2 * duration**2 / 2 + velocity_sensitivity_s_inv * duration
    assert feedback < 1, "unresolved error-envelope feedback; no enclosure returned"
    acceleration_error = (
        position_sensitivity_s_inv2 * (position_error_m + duration * velocity_error_m_s)
        + velocity_sensitivity_s_inv * velocity_error_m_s + acceleration_defect_m_s2
    ) / (1 - feedback)
    return (
        position_error_m + duration * velocity_error_m_s + duration**2 * acceleration_error / 2,
        velocity_error_m_s + duration * acceleration_error,
    )


@pytest.mark.parametrize("duration_s", [0.0, 1 / 64, 0.3])
@pytest.mark.parametrize("initial_position,initial_velocity,defect", [
    (Fraction(0), Fraction(0), Fraction(0)),
    (Fraction(1, 1000), Fraction(1, 1000000), Fraction(0)),
    (Fraction(0), Fraction(0), Fraction(1, 1000)),
    (Fraction(1), Fraction(2), Fraction(3)),
])
def test_error_transport_attains_constant_acceleration(
    duration_s: float, initial_position: Fraction, initial_velocity: Fraction, defect: Fraction,
) -> None:
    position, velocity = _coast_error_envelope(
        duration_s, initial_position, initial_velocity, Fraction(0), Fraction(0), defect,
    )
    time = Fraction(duration_s)
    # Exact scalar solution relative to a zero reference; SI throughout.
    assert position == initial_position + initial_velocity * time + defect * time**2 / 2
    assert velocity == initial_velocity + defect * time


@pytest.mark.parametrize("duration_s", [1 / 64, 1 / 8, 1 / 4])
@pytest.mark.parametrize("model", ["position", "velocity", "coupled"])
def test_error_transport_checks_exact_nonlinear_motion(duration_s: float, model: str) -> None:
    time = Fraction(duration_s)
    # x=1/(1-t), v=1/(1-t)^2 solves all three ODEs on [0,h]:
    # x''=2*x^3, x''=2*v^(3/2), x''=x^3+v^(3/2).
    # The reference is identically zero; derivatives on the positive chords
    # give the following uniform Lipschitz constants, independently of the lemma.
    position_sensitivity = Fraction(0) if model == "velocity" else (6 if model == "position" else 3) / (1 - time)**2
    velocity_sensitivity = Fraction(0) if model == "position" else (3 if model == "velocity" else Fraction(3, 2)) / (1 - time)
    if model == "velocity" and time == Fraction(1, 4):
        # k=1 makes this lemma unresolved despite a finite exact trajectory.
        assert 1 / (1 - time) == Fraction(4, 3) and 1 / (1 - time)**2 == Fraction(16, 9)
        with pytest.raises(AssertionError, match="unresolved error-envelope"):
            _coast_error_envelope(
                duration_s, Fraction(1), Fraction(1), position_sensitivity, velocity_sensitivity, Fraction(0),
            )
        return
    position, velocity = _coast_error_envelope(
        duration_s, Fraction(1), Fraction(1), position_sensitivity, velocity_sensitivity, Fraction(0),
    )
    assert Fraction(1) < 1 / (1 - time) <= position  # m
    assert Fraction(1) < 1 / (1 - time)**2 <= velocity  # m/s


def test_error_transport_carries_errors_across_four_segments() -> None:
    position, velocity = Fraction(1, 1000), Fraction(1, 1000000)
    defect = Fraction(1, 1000)
    for segment in range(1, 5):
        position, velocity = _coast_error_envelope(0.25, position, velocity, Fraction(0), Fraction(0), defect)
        time = Fraction(segment, 4)
        assert position == Fraction(1, 1000) + time / 1000000 + defect * time**2 / 2
        assert velocity == Fraction(1, 1000000) + defect * time
    reset_position, reset_velocity = _coast_error_envelope(
        0.25, Fraction(1, 1000), Fraction(1, 1000000), Fraction(0), Fraction(0), defect,
    )
    assert position > reset_position and velocity > reset_velocity


@pytest.mark.parametrize("position_sensitivity,velocity_sensitivity", [(2, 0), (0, 1), (1, 1)])
def test_error_transport_rejects_unresolved_feedback(position_sensitivity: int, velocity_sensitivity: int) -> None:
    with pytest.raises(AssertionError, match="unresolved error-envelope"):
        _coast_error_envelope(
            1.0, Fraction(1), Fraction(1), Fraction(position_sensitivity), Fraction(velocity_sensitivity), Fraction(0),
        )


def test_error_transport_preserves_near_singular_exact_feedback() -> None:
    margin = Fraction(1, 2**60)
    position, velocity = _coast_error_envelope(1.0, Fraction(0), Fraction(1), Fraction(0), 1 - margin, Fraction(0))
    assert velocity == 1 / margin
    assert position == 1 + (1 - margin) / (2 * margin)
    # No floating-point denominator, clipping or relaxed closure threshold.


@pytest.mark.parametrize("field", range(5))
@pytest.mark.parametrize("invalid", [Fraction(-1), 0.0, True, math.nan, math.inf])
def test_error_transport_rejects_invalid_bounds(field: int, invalid: object) -> None:
    bounds = [Fraction(0)] * 5
    bounds[field] = invalid  # type: ignore[assignment] -- intentionally invalid boundary value.
    with pytest.raises(AssertionError):
        _coast_error_envelope(0.25, *bounds)


@pytest.mark.parametrize("duration_s", [-1.0, True, math.nan, math.inf])
def test_error_transport_rejects_invalid_duration(duration_s: float) -> None:
    with pytest.raises(AssertionError):
        _coast_error_envelope(duration_s, Fraction(0), Fraction(0), Fraction(0), Fraction(0), Fraction(0))
