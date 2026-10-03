from __future__ import annotations

import json
import math

import pytest

from space_nav import research_response as response
from space_nav.errors import TrajectoryRefinementError


def _curve(slope: float, quadratic: float = 0.0) -> tuple[tuple[float, ...], ...]:
    return tuple((a*slope+a*a*quadratic, 0., 0., 0., 0., 0.) for a in response._ALPHAS)


def test_direction_column_order_and_trust_units() -> None:
    # Distinct columns plus a coupled row: independent exact oracle.
    matrix = tuple(tuple(float(i+1) if i == j else 0. for j in range(6)) for i in range(6))
    direction = response._direction(matrix, (.25, -.125, 150., -.0625, .125, -300.))
    assert direction == (1., -1., .75, -1., 2.5, -3.)
    assert response._direction(((1., 2., 3., 4., 5., 6.),)*6, (.25,)*2+(600.,)+(.25,)*2+(600.,)) == (21.,)*6


def test_linear_and_quadratic_independent_oracles() -> None:
    result = response._response_diagnostics((10., 0, 0, 0, 0, 0), _curve(10, 1000), _curve(10, 1000))
    assert len(result["checks"]) == 12 and result["consistent"]
    for profile in result["profiles"].values():
        assert profile["slopes"] == [(10., 0, 0, 0, 0, 0)]*2
        for i, alpha in enumerate((2**-14, 2**-15)):
            assert profile["curvatures"][i][0] == pytest.approx(alpha*1000, rel=0, abs=1e-10)
        for sample in profile["samples"]:
            a = sample["alpha"]
            assert sample["predicted"][0] == a*10
            assert sample["model_error"][0] == pytest.approx(a*a*1000, rel=0, abs=1e-14)
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("slope,passes", [(11., True), (11.000001, False)])
def test_threshold_equality_and_model_failure(slope: float, passes: bool) -> None:
    result = response._response_diagnostics((10., 0, 0, 0, 0, 0), _curve(slope), _curve(slope))
    assert result["consistent"] is passes
    assert all(c["threshold"] == .1 for c in result["checks"])
    assert all(c["within_threshold"] is passes for c in result["checks"] if c["kind"] == "model")


def test_scale_curvature_and_profile_checks_detect_different_effects() -> None:
    # Cubic terms change centered slopes by a^2; asymmetric quadratic terms add curvature.
    nominal = tuple((a*10 + a**3*1e9 + a*a*1e5, 0., 0., 0., 0., 0.) for a in response._ALPHAS)
    result = response._response_diagnostics((10., 0, 0, 0, 0, 0), nominal, _curve(10))
    failed = {c["kind"] for c in result["checks"] if not c["within_threshold"]}
    assert failed == {"model", "curvature", "scale", "profile"}


@pytest.mark.parametrize("bad", [True, math.nan, math.inf])
def test_nonfinite_and_boolean_components_rejected(bad: float) -> None:
    with pytest.raises((ValueError, TrajectoryRefinementError)):
        response._response_diagnostics((bad, 0, 0, 0, 0, 0), _curve(10), _curve(10))
    with pytest.raises((ValueError, TrajectoryRefinementError)):
        response._direction(((bad, 0, 0, 0, 0, 0),)*6, (1.,)*6)


def test_shape_zero_overflow_and_finite_unavailable_ratio() -> None:
    with pytest.raises(ValueError, match="six Jacobian"):
        response._direction((), (1.,)*6)
    with pytest.raises(ValueError, match="zero-predicted"):
        response._direction(((0.,)*6,)*6, (1.,)*6)
    with pytest.raises(ValueError, match="five ordered"):
        response._response_diagnostics((10., 0, 0, 0, 0, 0), (), _curve(10))
    with pytest.raises((ValueError, TrajectoryRefinementError)):
        response._direction(((1e308,)*6,)*6, (.25, .25, 600., .25, .25, 600.))
    result = response._response_diagnostics((1e-300, 0, 0, 0, 0, 0), _curve(1e100), _curve(1e100))
    unavailable = [c for c in result["checks"] if c["unavailable_reason"]]
    assert unavailable and all(c["norm_ratio"] is None for c in unavailable)
    assert not result["consistent"]
    json.dumps(result, allow_nan=False)
