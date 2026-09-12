"""Conditional error-transport lemma; not a full-force or native-stage certificate."""

from fractions import Fraction
import math

import pytest


def _cubic_reference_endpoint(
    initial_state_m_m_s: tuple[Fraction, ...], acceleration_m_s2: tuple[Fraction, ...],
    jerk_m_s3: tuple[Fraction, ...], duration_s: float,
) -> tuple[Fraction, ...]:
    """Return exact reference position (m), velocity (m/s); elapsed time in seconds."""
    assert type(duration_s) is float and math.isfinite(duration_s) and duration_s >= 0
    assert all(len(vector) == size and all(isinstance(value, Fraction) for value in vector)
               for vector, size in ((initial_state_m_m_s, 6), (acceleration_m_s2, 3), (jerk_m_s3, 3)))
    time = Fraction(duration_s)
    position_m = tuple(p + v*time + a*time**2/2 + j*time**3/6 for p, v, a, j in
                       zip(initial_state_m_m_s[:3], initial_state_m_m_s[3:], acceleration_m_s2, jerk_m_s3, strict=True))
    velocity_m_s = tuple(v + a*time + j*time**2/2 for v, a, j in
                         zip(initial_state_m_m_s[3:], acceleration_m_s2, jerk_m_s3, strict=True))
    return position_m + velocity_m_s


@pytest.mark.parametrize("duration_s", [0.0, 1 / 64, 1 / 32])
@pytest.mark.parametrize("selected_jerk,omitted_jerk", [(-1, -2), (-1, 2), (1, -2), (1, 2)])
def test_partial_cubic_reference_retains_omitted_force(
    duration_s: float, selected_jerk: int, omitted_jerk: int,
) -> None:
    initial = tuple(map(Fraction, (10**12, -10**12, 0, 2, 0, 0)))
    acceleration = (Fraction(1, 4), Fraction(0), Fraction(0))
    reference = _cubic_reference_endpoint(initial, acceleration, (Fraction(selected_jerk), Fraction(0), Fraction(0)), duration_s)
    time = Fraction(duration_s)
    # Independent integration of f(t)=a0+(selected+omitted)*t along x.
    total_jerk = selected_jerk + omitted_jerk
    exact_position = initial[0] + time*(initial[3] + time*(acceleration[0]/2 + total_jerk*time/6))
    exact_velocity = initial[3] + time*(acceleration[0] + total_jerk*time/2)
    bound_m, bound_m_s = _coast_error_envelope(
        duration_s, Fraction(0), Fraction(0), Fraction(0), Fraction(0), Fraction(0),
        acceleration_defect_rate_m_s3=Fraction(abs(omitted_jerk)),
    )
    assert abs(exact_position - reference[0]) == bound_m
    assert abs(exact_velocity - reference[3]) == bound_m_s
    assert reference[1:3] == initial[1:3] and reference[4:] == initial[4:]


@pytest.mark.parametrize("duration_s", [-1.0, True, math.nan, math.inf])
def test_cubic_reference_rejects_invalid_duration(duration_s: float) -> None:
    with pytest.raises(AssertionError):
        _cubic_reference_endpoint((Fraction(0),)*6, (Fraction(0),)*3, (Fraction(0),)*3, duration_s)


@pytest.mark.parametrize("field", range(3))
@pytest.mark.parametrize("invalid", ["length", "boolean", "float"])
def test_cubic_reference_rejects_invalid_vectors(field: int, invalid: str) -> None:
    vectors: list[tuple[object, ...]] = [(Fraction(0),)*6, (Fraction(0),)*3, (Fraction(0),)*3]
    vector = vectors[field]
    vectors[field] = vector[:-1] if invalid == "length" else (True if invalid == "boolean" else 0.0,) + vector[1:]
    with pytest.raises(AssertionError):
        _cubic_reference_endpoint(*vectors, 0.25)  # type: ignore[arg-type] -- boundary rejection.


def _coast_error_envelope(
    duration_s: float, position_error_m: Fraction, velocity_error_m_s: Fraction,
    position_sensitivity_s_inv2: Fraction, velocity_sensitivity_s_inv: Fraction,
    acceleration_defect_m_s2: Fraction,
    *, acceleration_defect_rate_m_s3: Fraction = Fraction(0),
) -> tuple[Fraction, Fraction]:
    """Bound SI position/velocity errors given a closed domain and uniform sensitivities.

    Reference position must differentiate to reference velocity. Its acceleration
    defect must be <= D+J*t, where D/J are the supplied acceleration defect/rate.
    Force sensitivities must hold throughout both paths and chords.
    Returned bounds alone do not establish those premises or domain closure.
    """
    assert type(duration_s) is float and math.isfinite(duration_s) and duration_s >= 0
    assert all(isinstance(value, Fraction) and value >= 0 for value in (
        position_error_m, velocity_error_m_s, position_sensitivity_s_inv2,
        velocity_sensitivity_s_inv, acceleration_defect_m_s2, acceleration_defect_rate_m_s3,
    ))
    duration = Fraction(duration_s)
    feedback = position_sensitivity_s_inv2 * duration**2 / 2 + velocity_sensitivity_s_inv * duration
    assert feedback < 1, "unresolved error-envelope feedback; no enclosure returned"
    defect_position_m = acceleration_defect_rate_m_s3 * duration**3 / 6
    defect_velocity_m_s = acceleration_defect_rate_m_s3 * duration**2 / 2
    # Bound the time-independent part Lx*P+Lv*V+D, integrating J*t exactly.
    acceleration_error = (
        position_sensitivity_s_inv2 * (position_error_m + duration * velocity_error_m_s + defect_position_m)
        + velocity_sensitivity_s_inv * (velocity_error_m_s + defect_velocity_m_s) + acceleration_defect_m_s2
    ) / (1 - feedback)
    return (
        position_error_m + duration * velocity_error_m_s + duration**2 * acceleration_error / 2 + defect_position_m,
        velocity_error_m_s + duration * acceleration_error + defect_velocity_m_s,
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


@pytest.mark.parametrize("duration_s", [0.0, 1 / 64, 0.3])
@pytest.mark.parametrize("initial_position,initial_velocity,defect", [
    (Fraction(0), Fraction(0), Fraction(0)),
    (Fraction(1, 1000), Fraction(1, 1000000), Fraction(1, 1000)),
])
@pytest.mark.parametrize("rate", [Fraction(0), Fraction(3, 2)])
def test_error_transport_attains_constant_jerk(
    duration_s: float, initial_position: Fraction, initial_velocity: Fraction,
    defect: Fraction, rate: Fraction,
) -> None:
    position, velocity = _coast_error_envelope(
        duration_s, initial_position, initial_velocity, Fraction(0), Fraction(0), defect,
        acceleration_defect_rate_m_s3=rate,
    )
    time = Fraction(duration_s)
    # Independent exact trajectory x''=D+J*t relative to a zero reference.
    assert position == initial_position + initial_velocity * time + defect * time**2 / 2 + rate * time**3 / 6
    assert velocity == initial_velocity + defect * time + rate * time**2 / 2
    uniform = _coast_error_envelope(
        duration_s, initial_position, initial_velocity, Fraction(0), Fraction(0), defect + rate * time,
    )
    assert position <= uniform[0] and velocity <= uniform[1]
    assert ((position, velocity) == uniform) == (rate == 0 or time == 0)


@pytest.mark.parametrize("duration_s", [1 / 64, 1 / 8, 1 / 4])
@pytest.mark.parametrize("lx,lv", [(1, 0), (0, 1), (1, 1)])
def test_linear_defect_transport_encloses_manufactured_solution(duration_s: float, lx: int, lv: int) -> None:
    time = Fraction(duration_s)
    # x=t^3/6 solves x''=Lx*x+Lv*x'+t-Lx*t^3/6-Lv*t^2/2.
    # At the zero reference the force lies in [0,t] on the entire interval.
    assert 0 <= lx * time**2 / 6 + lv * time / 2 < 1
    position, velocity = _coast_error_envelope(
        duration_s, Fraction(0), Fraction(0), Fraction(lx), Fraction(lv), Fraction(0),
        acceleration_defect_rate_m_s3=Fraction(1),
    )
    assert time**3 / 6 < position  # m; strict positive feedback above the exact oracle.
    assert time**2 / 2 < velocity  # m/s
    uniform = _coast_error_envelope(
        duration_s, Fraction(0), Fraction(0), Fraction(lx), Fraction(lv), time,
    )
    assert position < uniform[0] and velocity < uniform[1]


@pytest.mark.parametrize("duration_s", [1 / 64, 1 / 32, 1 / 8, 1 / 4])
@pytest.mark.parametrize("offset_m", [0, 10**12])
@pytest.mark.parametrize("direction", [-1, 1])
def test_cubic_reference_encloses_exact_time_forced_motion(
    duration_s: float, offset_m: int, direction: int,
) -> None:
    # One-metre/one-second fixture: x=b+s/(1-t), x''=2*s/(1-t)^3.
    # The force depends only on time, so Lx=Lv=0 globally for t<1 s.
    time = Fraction(duration_s)
    exact_position_m = offset_m + direction / (1 - time)
    exact_velocity_m_s = direction / (1 - time)**2
    bounds: list[tuple[Fraction, Fraction]] = []
    actual_errors: list[tuple[Fraction, Fraction]] = []
    for degree in (2, 3):
        reference_position_m = offset_m + direction * sum((time**n for n in range(degree + 1)), Fraction(0))
        reference_velocity_m_s = direction * sum((n * time**(n - 1) for n in range(1, degree + 1)), Fraction(0))
        # f'=6*s/(1-t)^4; f''=24*s/(1-t)^5. Taylor's integral
        # remainder gives D2<=6*t/(1-h)^4, D3<=12*t^2/(1-h)^5.
        rate_m_s3 = 6 / (1 - time)**4 if degree == 2 else 12 * time / (1 - time)**5
        position_m, velocity_m_s = _coast_error_envelope(
            duration_s, Fraction(0), Fraction(0), Fraction(0), Fraction(0), Fraction(0),
            acceleration_defect_rate_m_s3=rate_m_s3,
        )
        errors = (abs(exact_position_m - reference_position_m), abs(exact_velocity_m_s - reference_velocity_m_s))
        assert 0 < errors[0] <= position_m and 0 < errors[1] <= velocity_m_s
        bounds.append((position_m, velocity_m_s))
        actual_errors.append(errors)
    assert all(cubic < quadratic for quadratic, cubic in zip(*actual_errors, strict=True))
    assert all(cubic / quadratic == 2 * time / (1 - time) < 1
               for quadratic, cubic in zip(*bounds, strict=True))


@pytest.mark.parametrize("invalid", [Fraction(-1), 0.0, True, math.nan, math.inf])
def test_error_transport_rejects_invalid_defect_rate(invalid: object) -> None:
    with pytest.raises(AssertionError):
        _coast_error_envelope(
            0.25, Fraction(0), Fraction(0), Fraction(0), Fraction(0), Fraction(0),
            acceleration_defect_rate_m_s3=invalid,  # type: ignore[arg-type] -- boundary rejection.
        )


def test_linear_defect_transport_rejects_unresolved_feedback() -> None:
    with pytest.raises(AssertionError, match="unresolved error-envelope"):
        _coast_error_envelope(
            1.0, Fraction(0), Fraction(0), Fraction(0), Fraction(1), Fraction(0),
            acceleration_defect_rate_m_s3=Fraction(1),
        )


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
