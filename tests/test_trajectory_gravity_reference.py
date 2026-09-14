"""Gravity-only comparison polynomials; the truth still includes all forces."""

from fractions import Fraction as F
import math

import pytest

from test_trajectory_error_transport import (
    _coast_error_envelope, _fresh_reference_defect_m_s2_m_s3,
)


def _gravity_reference_defect_m_s2_m_s3(
    duration_s: float, gravity_anchor_error_m_s2: F, jerk_error_m_s3: F,
    monopole_curvature_m_s4: F, nonmonopole_translation_rate_m_s3: F,
    rotation_rate_m_s3: F, srp_norm_m_s2: F, relativity_norm_m_s2: F,
) -> tuple[F, F]:
    """Conditional D/J for a gravity-only anchor, NOT an old full-force a0.

    Caller must bind gravity anchor, reference/chord domain and all uniform
    channels. Full truth retains SRP/relativity. No numerical qualification.
    """
    # Reuse input validation and the identical gravitational rate assembly.
    d, j = _fresh_reference_defect_m_s2_m_s3(
        duration_s, gravity_anchor_error_m_s2, jerk_error_m_s3,
        monopole_curvature_m_s4, nonmonopole_translation_rate_m_s3,
        rotation_rate_m_s3, srp_norm_m_s2, relativity_norm_m_s2,
    )
    # Here the residual contains l(t), not the old anchor's l(t)-l(0).
    return d-srp_norm_m_s2-relativity_norm_m_s2, j


@pytest.mark.parametrize("channels", [(0, 0, 0, 0, 0, 0, 0), (1, 2, 3, 4, 5, 0, 0),
                                     (0, 0, 0, 0, 0, 2, 3), (1, 2, 3, 4, 5, 2, 3)])
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("reverses", [False, True])
@pytest.mark.parametrize("incoming", [False, True])
def test_gravity_reference_encloses_exact_truth(channels, sign, reverses, incoming) -> None:
    e, ej, k, translation, rotation, srp, relativity = map(F, channels)
    h = F(1, 8)
    d, j = _gravity_reference_defect_m_s2_m_s3(float(h), *map(F, channels))
    rate, light = ej+translation+rotation, srp+relativity
    assert (d, j) == (e+light, rate+k*h/2)
    p0, v0 = (F(1, 10000), F(1, 10**7)) if incoming else (F(0), F(0))
    origin, speed, a0, j0 = map(F, (10**12, 7, 11, 13))
    for t in (F(0), h/4, h/2, 3*h/4, h):
        gravity = a0+j0*t+sign*(e+rate*t+k*t*t/2)
        nongravity = sign*light*(1-2*reverses*t/h)
        assert abs(nongravity) <= light
        z = sign*(gravity+nongravity-(a0+j0*t))
        bound = d+j*t
        # Identities with nonnegative terms prove BOTH signs on all 0<=t<=h,
        # including where a reversing force changes the sign of the residual.
        assert bound-z == 2*reverses*light*t/h+k*t*(h-t)/2 >= 0
        assert bound+z == 2*e+2*rate*t+k*t*(h+t)/2+2*light*(1-reverses*t/h) >= 0
        if t == h and not reverses:
            assert abs(z) == bound
            if light:
                assert abs(z) > (d-light)+j*t
            if k:
                assert abs(z) > d+(j-k*h/2)*t
        q_p = origin+speed*t+a0*t*t/2+j0*t**3/6
        q_v = speed+a0*t+j0*t*t/2
        truth_p = origin+sign*p0+(speed+sign*v0)*t+(a0+sign*(e+light))*t*t/2+(j0+sign*(rate-2*reverses*light/h))*t**3/6+sign*k*t**4/24
        truth_v = speed+sign*v0+(a0+sign*(e+light))*t+(j0+sign*(rate-2*reverses*light/h))*t*t/2+sign*k*t**3/6
        p, v = _coast_error_envelope(float(t), p0, v0, F(0), F(0), d, acceleration_defect_rate_m_s3=j)
        assert abs(truth_p-q_p) <= p and abs(truth_v-q_v) <= v
        if t == 0:
            assert (p, v) == (p0, v0)


@pytest.mark.parametrize("sign", [-1, 1])
def test_single_charge_cannot_relabel_full_force_anchor(sign: int) -> None:
    h, light = F(1, 8), F(3)
    args = (float(h), *(F(0),)*5, light, F(0))
    single, _ = _gravity_reference_defect_m_s2_m_s3(*args)
    double, _ = _fresh_reference_defect_m_s2_m_s3(*args)
    # g=0; l(0)=sign*L, l(h)=-sign*L. Old q'' includes l(0).
    wrong_anchor_residual = abs(-sign*light-sign*light)
    assert single < wrong_anchor_residual == double
    assert abs(-sign*light) == single  # New gravity-only q''=0 instead.


@pytest.mark.parametrize("field", range(1, 8))
@pytest.mark.parametrize("invalid", [F(-1), True, 0.0])
def test_gravity_reference_rejects_invalid_channel(field, invalid) -> None:
    args = [0.125]+[F(0)]*7
    args[field] = invalid
    with pytest.raises(AssertionError):
        _gravity_reference_defect_m_s2_m_s3(*args)


@pytest.mark.parametrize("horizon", [0.0, -1.0, True, math.nan, math.inf])
def test_gravity_reference_rejects_invalid_horizon(horizon) -> None:
    with pytest.raises(AssertionError):
        _gravity_reference_defect_m_s2_m_s3(horizon, *(F(0),)*7)
