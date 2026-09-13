"""Conditional error-transport lemma; not a full-force or native-stage certificate."""

from fractions import Fraction
import math

import pytest


def _shifted_reference_defect_m_s2_m_s3(
    offset_s: float, position_sensitivity_s_inv2: Fraction, velocity_sensitivity_s_inv: Fraction,
    defect_m_s2: Fraction, defect_rate_m_s3: Fraction,
    position_shift_m: Fraction, velocity_shift_m_s: Fraction,
) -> tuple[Fraction, Fraction]:
    """Bound shifted-reference defect by D2+J2*tau in SI.

    q2(tau)=q1(offset+tau)+delta_p+delta_v*tau. Old defect and state
    sensitivities must hold on both references/chords over the entire interval.
    Shift arguments bound vector norms, not signed error or incoming uncertainty.
    """
    assert type(offset_s) is float and math.isfinite(offset_s) and offset_s >= 0
    assert all(isinstance(value, Fraction) and value >= 0 for value in (
        position_sensitivity_s_inv2, velocity_sensitivity_s_inv, defect_m_s2,
        defect_rate_m_s3, position_shift_m, velocity_shift_m_s,
    ))
    return (defect_m_s2 + defect_rate_m_s3*Fraction(offset_s)
            + position_sensitivity_s_inv2*position_shift_m + velocity_sensitivity_s_inv*velocity_shift_m_s,
            defect_rate_m_s3 + position_sensitivity_s_inv2*velocity_shift_m_s)


@pytest.mark.parametrize("offset_s", [0.0, 0.125])
@pytest.mark.parametrize("lx,lv", [(0, 0), (1, 0), (0, 1), (1, 1)])
@pytest.mark.parametrize("force_sign,p_sign,v_sign", [(1, 1, 1), (1, -1, 1), (-1, 1, -1), (-1, -1, -1)])
def test_shifted_defect_encloses_manufactured_force(
    offset_s: float, lx: int, lv: int, force_sign: int, p_sign: int, v_sign: int,
) -> None:
    d, j, p, v = map(Fraction, ("0.001", "0.002", "0.0001", "0.00001"))
    shifted_d, shifted_j = _shifted_reference_defect_m_s2_m_s3(offset_s, Fraction(lx), Fraction(lv), d, j, p, v)
    # Independent force f(t,x,v)=t+s*(D+J*t)+Lx*(x-t^3/6)+Lv*(v-t^2/2).
    # q1=t^3/6; q2=q1(offset+tau)+signed shifts. Its residual is affine
    # in tau, so bounding both exact coefficients proves the whole interval.
    constant = force_sign*(d+j*Fraction(offset_s)) + lx*p_sign*p + lv*v_sign*v
    slope = force_sign*j + lx*v_sign*v
    assert abs(constant) <= shifted_d and abs(slope) <= shifted_j
    for tau in (Fraction(0), Fraction(1, 128), Fraction(1, 64)):
        t = Fraction(offset_s) + tau
        q2 = t**3/6 + p_sign*p + v_sign*v*tau
        q2_velocity = t**2/2 + v_sign*v
        force = t + force_sign*(d+j*t) + lx*(q2-t**3/6) + lv*(q2_velocity-t**2/2)
        assert force - t == constant + slope*tau
        assert abs(force - t) <= shifted_d + shifted_j*tau
        if force_sign == p_sign == v_sign:
            assert abs(force - t) == shifted_d + shifted_j*tau
    if force_sign == p_sign == v_sign == 1 and offset_s > 0:
        assert constant > d + lx*p + lv*v  # Omitting time rebasing underbounds.
        if lx or lv:
            assert constant > d + j*Fraction(offset_s)  # Omitting reference shifts underbounds.


def test_shifted_defect_preserves_zero_shift_and_zero_field() -> None:
    assert _shifted_reference_defect_m_s2_m_s3(0.0, Fraction(2), Fraction(3), Fraction(4), Fraction(5),
                                             Fraction(0), Fraction(0)) == (4, 5)
    assert _shifted_reference_defect_m_s2_m_s3(0.125, *(Fraction(0),)*6) == (0, 0)


@pytest.mark.parametrize("field", range(6))
@pytest.mark.parametrize("invalid", [Fraction(-1), True, math.nan])
def test_shifted_defect_rejects_invalid_bound(field: int, invalid: object) -> None:
    values: list[object] = [Fraction(1)] * 6
    values[field] = invalid
    with pytest.raises(AssertionError):
        _shifted_reference_defect_m_s2_m_s3(0.125, *values)  # type: ignore[arg-type] -- boundary rejection.


@pytest.mark.parametrize("offset_s", [-1.0, True, math.nan, math.inf])
def test_shifted_defect_rejects_invalid_offset(offset_s: float) -> None:
    with pytest.raises(AssertionError):
        _shifted_reference_defect_m_s2_m_s3(offset_s, *(Fraction(1),)*6)


def _recentered_coast_reaches_m_m_s(
    duration_s: float, position_offset_m: Fraction, velocity_offset_m_s: Fraction,
    nominal_speed_m_s: Fraction, position_error_m: Fraction, velocity_error_m_s: Fraction,
    acceleration_m_s2: Fraction,
) -> tuple[Fraction, Fraction]:
    """Bound reach about old SI centres from a new nominal state and error ball.

    Offsets/speed must bound Euclidean norms. Acceleration must hold on the
    original domain for the entire shifted interval; closure is a separate gate.
    """
    assert type(duration_s) is float and math.isfinite(duration_s) and duration_s >= 0
    assert all(isinstance(value, Fraction) and value >= 0 for value in (
        position_offset_m, velocity_offset_m_s, nominal_speed_m_s,
        position_error_m, velocity_error_m_s, acceleration_m_s2,
    ))
    h = Fraction(duration_s)
    return (position_offset_m + position_error_m + (nominal_speed_m_s + velocity_error_m_s)*h + acceleration_m_s2*h**2/2,
            velocity_offset_m_s + velocity_error_m_s + acceleration_m_s2*h)


@pytest.mark.parametrize("duration_s", [0.0, 1 / 64])
@pytest.mark.parametrize("acceleration", [0, 2])
@pytest.mark.parametrize("direction", [-1, 1])
@pytest.mark.parametrize("origin_m", [0, 10**12])
def test_recentered_reach_attains_exact_acceleration(
    duration_s: float, acceleration: int, direction: int, origin_m: int,
) -> None:
    h, p, v = Fraction(duration_s), Fraction(1, 10000), Fraction(1, 10**7)
    # Old centre x0=origin, v0=2*s; new nominal x=origin+3*s, v=4*s.
    position_m = origin_m + direction*(3+p+(4+v)*h+acceleration*h*h/2)
    velocity_m_s = direction*(4+v+acceleration*h)
    bounds = _recentered_coast_reaches_m_m_s(
        duration_s, Fraction(3), Fraction(2), Fraction(4), p, v, Fraction(acceleration),
    )
    assert bounds == (abs(position_m-origin_m), abs(velocity_m_s-2*direction))


@pytest.mark.parametrize("field", range(6))
@pytest.mark.parametrize("invalid", [Fraction(-1), True, math.nan])
def test_recentered_reach_rejects_invalid_bound(field: int, invalid: object) -> None:
    values: list[object] = [Fraction(1)] * 6
    values[field] = invalid
    with pytest.raises(AssertionError):
        _recentered_coast_reaches_m_m_s(0.125, *values)  # type: ignore[arg-type] -- boundary rejection.


@pytest.mark.parametrize("duration_s", [-1.0, True, math.nan, math.inf])
def test_recentered_reach_rejects_invalid_duration(duration_s: float) -> None:
    with pytest.raises(AssertionError):
        _recentered_coast_reaches_m_m_s(duration_s, *(Fraction(1),)*6)


def _initial_velocity_interval_m_s(
    duration_s: float, position_sensitivity_s_inv2: Fraction, velocity_sensitivity_s_inv: Fraction,
    position_accuracy_margin_m: Fraction, velocity_accuracy_margin_m_s: Fraction,
    position_closure_margin_m: Fraction, velocity_closure_margin_m_s: Fraction,
) -> tuple[Fraction, bool] | None:
    """Return conditional [0, upper] / [0, upper) in m/s, or an empty interval.

    Margins are evaluated at zero initial velocity radius and fixed position
    radius. Accuracy gates are inclusive; first-exit closure gates are strict.
    This inverts the existing affine envelope, not the physical dynamics.
    """
    assert type(duration_s) is float and math.isfinite(duration_s) and duration_s > 0
    assert all(isinstance(value, Fraction) for value in (
        position_accuracy_margin_m, velocity_accuracy_margin_m_s,
        position_closure_margin_m, velocity_closure_margin_m_s,
    ))
    position_gain_s, velocity_gain = _coast_error_envelope(
        duration_s, Fraction(0), Fraction(1), position_sensitivity_s_inv2,
        velocity_sensitivity_s_inv, Fraction(0),
    )
    limits = ((position_accuracy_margin_m / position_gain_s, True),
              (velocity_accuracy_margin_m_s / velocity_gain, True),
              (position_closure_margin_m / Fraction(duration_s), False),
              (velocity_closure_margin_m_s, False))
    upper = min(value for value, _ in limits)
    included = all(closed for value, closed in limits if value == upper)
    return None if upper < 0 or (upper == 0 and not included) else (upper, included)


@pytest.mark.parametrize("margins,expected", [
    ((1, 2, 3, 4), (Fraction(1), True)),
    ((2, 1, 3, 4), (Fraction(1), True)),
    ((2, 3, 1, 4), (Fraction(1), False)),
    ((2, 3, 4, 1), (Fraction(1), False)),
    ((1, 1, 2, 2), (Fraction(1), True)),
    ((1, 2, 1, 2), (Fraction(1), False)),
    ((0, 1, 2, 2), (Fraction(0), True)),
    ((1, 1, 0, 2), None),
    ((-1, 1, 2, 2), None),
    ((1, 1, 2, -1), None),
])
def test_initial_velocity_interval_uniform_motion(
    margins: tuple[int, ...], expected: tuple[Fraction, bool] | None,
) -> None:
    # Independent x(t)=x0+v*t: at h=1 s, both endpoint gains are one.
    assert _initial_velocity_interval_m_s(1.0, Fraction(0), Fraction(0), *map(Fraction, margins)) == expected


@pytest.mark.parametrize("active", range(4))
def test_initial_velocity_interval_matches_original_envelope(active: int) -> None:
    h = 0.125
    p, lx, lv, d, j = map(Fraction, ("0.0001", "0.1", "0.2", "0.001", "0.002"))
    base = _coast_error_envelope(h, p, Fraction(0), lx, lv, d, acceleration_defect_rate_m_s3=j)
    margins = [Fraction(1)] * 4
    margins[active] = Fraction(1, 1000)
    interval = _initial_velocity_interval_m_s(h, lx, lv, *margins)
    assert interval is not None
    upper, included = interval
    for v, expected in ((upper / 2, True), (upper, included), (upper * 2, False)):
        actual = _coast_error_envelope(h, p, v, lx, lv, d, acceleration_defect_rate_m_s3=j)
        assert (actual[0] <= base[0] + margins[0] and actual[1] <= base[1] + margins[1]
                and v * Fraction(h) < margins[2] and v < margins[3]) == expected
    assert included == (active < 2)


@pytest.mark.parametrize("duration_s", [0.0, -1.0, True, math.nan, math.inf])
def test_initial_velocity_interval_rejects_duration(duration_s: float) -> None:
    with pytest.raises(AssertionError):
        _initial_velocity_interval_m_s(duration_s, Fraction(0), Fraction(0), *(Fraction(1),) * 4)


@pytest.mark.parametrize("field", range(6))
@pytest.mark.parametrize("invalid", [True, 1.0, math.nan])
def test_initial_velocity_interval_rejects_nonfractions(field: int, invalid: object) -> None:
    values: list[object] = [Fraction(0), Fraction(0), *(Fraction(1),) * 4]
    values[field] = invalid
    with pytest.raises(AssertionError):
        _initial_velocity_interval_m_s(1.0, *values)  # type: ignore[arg-type] -- invalid boundary inputs.


@pytest.mark.parametrize("lx,lv", [(-1, 0), (0, -1), (2, 0), (0, 1)])
def test_initial_velocity_interval_rejects_sensitivity(lx: int, lv: int) -> None:
    with pytest.raises(AssertionError):
        _initial_velocity_interval_m_s(1.0, Fraction(lx), Fraction(lv), *(Fraction(1),) * 4)


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


@pytest.mark.parametrize("duration_s", [0.0, 1 / 64, 1 / 8])
@pytest.mark.parametrize("sensitivity", [Fraction(0), Fraction(1, 10)])
@pytest.mark.parametrize("zero_part", [False, True])
def test_zero_initial_error_transport_is_additive(
    duration_s: float, sensitivity: Fraction, zero_part: bool,
) -> None:
    # SI: independent forcing channels D_i + J_i*t; identical feedback
    # constants and zero initial error are essential for this attribution.
    parts = [(Fraction(1, 1000), Fraction(2, 1000)),
             (Fraction(0), Fraction(0)) if zero_part else (Fraction(3, 1000), Fraction(4, 1000))]
    bounds = [_coast_error_envelope(duration_s, Fraction(0), Fraction(0), sensitivity, sensitivity, d,
                                   acceleration_defect_rate_m_s3=j) for d, j in parts]
    d, j = (sum((part[index] for part in parts), Fraction(0)) for index in (0, 1))
    combined = _coast_error_envelope(duration_s, Fraction(0), Fraction(0), sensitivity, sensitivity, d,
                                     acceleration_defect_rate_m_s3=j)
    assert tuple(sum((bound[index] for bound in bounds), Fraction(0)) for index in (0, 1)) == combined
    if sensitivity == 0:
        h = Fraction(duration_s)
        # Independent exact integration of D+J*t, without feedback.
        assert combined == (d*h**2/2 + j*h**3/6, d*h + j*h**2/2)


@pytest.mark.parametrize("duration_s", [0.0, 1 / 8])
@pytest.mark.parametrize("p", [Fraction(0), Fraction(1, 1000)])
@pytest.mark.parametrize("v", [Fraction(0), Fraction(1, 10**7)])
@pytest.mark.parametrize("sensitivity", [Fraction(0), Fraction(1, 10)])
def test_error_transport_adds_initial_ball_to_linear_defect(
    duration_s: float, p: Fraction, v: Fraction, sensitivity: Fraction,
) -> None:
    d, j = Fraction(1, 1000), Fraction(2, 1000)  # m/s^2 and m/s^3.
    total = _coast_error_envelope(duration_s, p, v, sensitivity, sensitivity, d, acceleration_defect_rate_m_s3=j)
    initial = _coast_error_envelope(duration_s, p, v, sensitivity, sensitivity, Fraction(0))
    forcing = _coast_error_envelope(duration_s, Fraction(0), Fraction(0), sensitivity, sensitivity, d,
                                    acceleration_defect_rate_m_s3=j)
    assert total == tuple(a+b for a, b in zip(initial, forcing, strict=True))
    if sensitivity == 0:
        h = Fraction(duration_s)
        # Independent integration of x''=D+J*t with x(0)=p m, v(0)=v m/s.
        assert total == (p+v*h+d*h*h/2+j*h**3/6, v+d*h+j*h*h/2)


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


@pytest.mark.parametrize("first_s,second_s,rate", [
    (1 / 64, 1 / 32, Fraction(0)), (1 / 32, 1 / 64, Fraction(1, 100000)),
    (1 / 64, 1 / 8, Fraction(1, 100000)), (1 / 8, 1 / 64, Fraction(1, 100000)),
])
@pytest.mark.parametrize("direction", [-1, 1])
def test_two_segment_transport_rebases_linear_force(
    first_s: float, second_s: float, rate: Fraction, direction: int,
) -> None:
    p, v, d = Fraction(1, 10000), Fraction(1, 10**7), Fraction(1, 100000)
    first_p, first_v = _coast_error_envelope(
        first_s, p, v, Fraction(0), Fraction(0), d, acceleration_defect_rate_m_s3=rate,
    )
    second_d = d + rate * Fraction(first_s)  # Global force D+J*t, not D+J*(t-t1).
    result = _coast_error_envelope(
        second_s, first_p, first_v, Fraction(0), Fraction(0), second_d, acceleration_defect_rate_m_s3=rate,
    )
    total_s = Fraction(first_s) + Fraction(second_s)
    # Independent global integration of x''=s*(D+J*t), x0=s*p, v0=s*v.
    exact_p = direction * (p + v*total_s + d*total_s**2/2 + rate*total_s**3/6)
    exact_v = direction * (v + d*total_s + rate*total_s**2/2)
    assert result == (abs(exact_p), abs(exact_v))
    reset = _coast_error_envelope(
        second_s, p, v, Fraction(0), Fraction(0), second_d, acceleration_defect_rate_m_s3=rate,
    )
    assert reset[0] < abs(exact_p) and reset[1] < abs(exact_v)
    stale_clock = _coast_error_envelope(
        second_s, first_p, first_v, Fraction(0), Fraction(0), d, acceleration_defect_rate_m_s3=rate,
    )
    assert (stale_clock == result) == (rate == 0)
    if rate > 0:
        assert stale_clock[0] < abs(exact_p) and stale_clock[1] < abs(exact_v)


@pytest.mark.parametrize("durations_s", [(1 / 64, 1 / 32), (1 / 32, 1 / 64), (1 / 128, 1 / 64), (1 / 64, 1 / 128)])
@pytest.mark.parametrize("model", ["position", "velocity", "coupled"])
def test_two_segment_nonlinear_transport_closes_domains(
    durations_s: tuple[float, float], model: str,
) -> None:
    # x=1/(1-t), v=1/(1-t)^2, relative to the zero reference.
    # All three ODEs from the single-arc oracle have |f|<=54 m/s^2
    # on 0<=x<=3 m, 0<=v<=3 m/s; these constants cover entire chords.
    lx = Fraction(0 if model == "velocity" else 54 if model == "position" else 27)
    lv = Fraction(0 if model == "position" else 6 if model == "velocity" else 3)
    p, v, elapsed_s = Fraction(1), Fraction(1), Fraction(0)
    expected_unresolved = (model == "position" and sum(durations_s) > 1 / 32
                           or model == "coupled" and durations_s == (1 / 64, 1 / 32))
    for duration_s in durations_s:
        h = Fraction(duration_s)
        closed = p + v*h + 54*h**2/2 < 3 and v + 54*h < 3  # m and m/s, strict first-exit closure.
        if not closed:
            # Retain measured failures: a broad enclosure cannot certify the
            # next segment even though the exact positive trajectory stays inside.
            assert expected_unresolved and elapsed_s > 0
            assert 1 / (1 - elapsed_s - h) < 3
            assert 1 / (1 - elapsed_s - h)**2 < 3
            return  # No second envelope or safe classification without closure.
        p, v = _coast_error_envelope(duration_s, p, v, lx, lv, Fraction(0))
        elapsed_s += h
        assert 1 / (1 - elapsed_s) <= p < 3  # m.
        assert 1 / (1 - elapsed_s)**2 <= v < 3  # m/s.
    assert not expected_unresolved


@pytest.mark.parametrize("active", range(4))
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_two_segment_handoff_rejects_failed_gate(active: int, offset: int) -> None:
    h = 0.125
    p, v = _coast_error_envelope(h, Fraction(0), Fraction(0), Fraction(0), Fraction(0), Fraction(1, 1000))
    base_p, base_v = _coast_error_envelope(h, p, Fraction(0), Fraction(0), Fraction(0), Fraction(1, 1000))
    second_p, second_v = _coast_error_envelope(h, p, v, Fraction(0), Fraction(0), Fraction(1, 1000))
    # SI endpoint gates, then margins left after the v=0 first-exit reach.
    gains = (Fraction(h), Fraction(1), Fraction(h), Fraction(1))
    margins = [Fraction(1)] * 4
    margins[active] = gains[active] * v * Fraction(2 + offset, 2)
    interval = _initial_velocity_interval_m_s(h, Fraction(0), Fraction(0), *margins)
    assert interval is not None
    upper, included = interval
    admitted = v < upper or (v == upper and included)
    assert admitted == (second_p <= base_p + margins[0] and second_v <= base_v + margins[1]
                        and v*Fraction(h) < margins[2] and v < margins[3])
    assert admitted == (offset > 0 or (offset == 0 and active < 2))
    # A reset to zero would falsely admit every failed handoff in this fixture.
    assert 0 < upper


@pytest.mark.parametrize("bridge", ["aligned", "opposed", "orthogonal", "zero", "position_only", "velocity_only"])
@pytest.mark.parametrize("direction", [-1, 1])
@pytest.mark.parametrize("offset_m", [0, 10**12])
def test_reference_recentring_carries_bridge_exactly_once(bridge: str, direction: int, offset_m: int) -> None:
    # Exact 3D motion x''=u*(D+J*t). Both u and the nonzero bridge
    # direction have unit Euclidean norm; use squared norms, not rounded roots.
    u = (direction * Fraction(3, 5), direction * Fraction(4, 5), Fraction(0))
    bridge_axis = ((-u[1], u[0], Fraction(0)) if bridge == "orthogonal" else
                   u if bridge == "aligned" else tuple(-value for value in u))
    assert sum(value**2 for value in u) == sum(value**2 for value in bridge_axis) == 1
    first_s, second_s = 1 / 64, 1 / 32
    d, j = Fraction(1, 1000), Fraction(1, 10000)  # m/s^2, m/s^3.
    first_p, first_v = _coast_error_envelope(
        first_s, Fraction(0), Fraction(0), Fraction(0), Fraction(0), d, acceleration_defect_rate_m_s3=j,
    )
    delta_p = Fraction(0) if bridge in ("zero", "velocity_only") else first_p / 2
    delta_v = Fraction(0) if bridge in ("zero", "position_only") else first_v / 2
    old_reference_p = (Fraction(offset_m), Fraction(-offset_m), Fraction(offset_m))
    native_p = tuple(value + delta_p*axis for value, axis in zip(old_reference_p, bridge_axis, strict=True))
    native_v = tuple(delta_v*axis for axis in bridge_axis)
    total_s = Fraction(first_s) + Fraction(second_s)
    exact_p = tuple(value + axis*(d*total_s**2/2 + j*total_s**3/6)
                    for value, axis in zip(old_reference_p, u, strict=True))
    exact_v = tuple(axis*(d*total_s + j*total_s**2/2) for axis in u)
    new_reference_p = tuple(p + Fraction(second_s)*v for p, v in zip(native_p, native_v, strict=True))
    actual_p_squared = sum((truth - reference)**2 for truth, reference in zip(exact_p, new_reference_p, strict=True))
    actual_v_squared = sum((truth - reference)**2 for truth, reference in zip(exact_v, native_v, strict=True))
    # At the handoff: (truth-native)=(truth-old_reference)+(old_reference-native).
    for raw, delta, old_centre, centre in (
        (first_p, delta_p, old_reference_p, native_p), (first_v, delta_v, (Fraction(0),)*3, native_v),
    ):
        true_boundary = tuple(value + raw*axis for value, axis in zip(old_centre, u, strict=True))
        bridge_vector = tuple(a-b for a, b in zip(old_centre, centre, strict=True))
        assert sum(value**2 for value in bridge_vector) == delta**2
        new_error = tuple(a-b for a, b in zip(true_boundary, centre, strict=True))
        assert new_error == tuple(raw*axis + shift for axis, shift in zip(u, bridge_vector, strict=True))
        assert sum(value**2 for value in new_error) <= (raw + delta)**2
    # Convert a raw reference-relative bound once. A native-relative bound
    # already contains this bridge and is passed unchanged to q2(0)=native.
    native_relative = first_p + delta_p, first_v + delta_v
    second_d = d + j*Fraction(first_s)
    final_p, final_v = _coast_error_envelope(
        second_s, *native_relative, Fraction(0), Fraction(0), second_d, acceleration_defect_rate_m_s3=j,
    )
    assert actual_p_squared <= final_p**2 and actual_v_squared <= final_v**2
    if bridge in ("opposed", "zero", "position_only", "velocity_only"):
        assert (actual_p_squared, actual_v_squared) == (final_p**2, final_v**2)
    omitted = _coast_error_envelope(
        second_s, first_p, first_v, Fraction(0), Fraction(0), second_d, acceleration_defect_rate_m_s3=j,
    )
    if bridge in ("opposed", "position_only", "velocity_only"):
        assert actual_p_squared > omitted[0]**2
        assert (actual_v_squared > omitted[1]**2) == (delta_v > 0)
    duplicated = _coast_error_envelope(
        second_s, native_relative[0] + delta_p, native_relative[1] + delta_v,
        Fraction(0), Fraction(0), second_d, acceleration_defect_rate_m_s3=j,
    )
    # Double counting is conservative, but can falsely lose an inclusive gate.
    assert duplicated == (final_p + delta_p + Fraction(second_s)*delta_v, final_v + delta_v)
    assert (duplicated[0] > final_p) == (bridge != "zero")


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
