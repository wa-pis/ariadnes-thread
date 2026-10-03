from __future__ import annotations

import json
import math
from typing import Any

import pytest

from space_nav import research_columns as columns
from space_nav.errors import TrajectoryRefinementError


def test_independent_quadratic_columns_order_units_and_identity() -> None:
    # Distinct linear columns and exact quadratic bias in trust coordinates.
    steps = (0.25, -0.125, 150.0, -0.0625, 0.125, -300.0)
    trusts = (0.25, 0.25, 600.0, 0.25, 0.25, 600.0)
    probes = (1e-5, 1e-5, 1.0, 1e-5, 1e-5, 1.0)
    base = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
    pairs = []
    for i, (h, trust) in enumerate(zip(probes, trusts)):
        q = h / trust
        derivative = tuple(float((i + 1) * (j + 1)) for j in range(6))
        quadratic = tuple(float(j + 2) for j in range(6))
        plus = tuple(
            b + d * q + k * q * q for b, d, k in zip(base, derivative, quadratic)
        )
        minus = tuple(
            b - d * q + k * q * q for b, d, k in zip(base, derivative, quadratic)
        )
        pair = columns._column_pair(base, plus, minus, i, derivative, steps)
        assert pair["central"] == pytest.approx(derivative, abs=1e-10, rel=0)
        assert pair["even"] == pytest.approx(
            tuple(k * q for k in quadratic), abs=1e-10, rel=0
        )
        assert pair["forward"] == pytest.approx(
            tuple(d + k * q for d, k in zip(derivative, quadratic)), abs=1e-10, rel=0
        )
        assert pair["central_contribution"] == pytest.approx(
            tuple(d * steps[i] / trust for d in derivative), abs=1e-10, rel=0
        )
        assert pair["identity_defect"] == pytest.approx((0.0,) * 6, abs=1e-10, rel=0)
        pairs.append(pair)
    expected = tuple(
        sum((i + 1) * (j + 1) * s / t for i, (s, t) in enumerate(zip(steps, trusts)))
        for j in range(6)
    )
    result = columns._column_diagnostics(pairs, expected, (expected, expected))
    assert result["central_direction"] == pytest.approx(expected, abs=1e-10, rel=0)
    assert result["consistent"] and len(result["checks"]) == 2
    assert result["direction_identity_defect"] == pytest.approx(
        (0.0,) * 6, abs=1e-10, rel=0
    )
    json.dumps(result, allow_nan=False)


def _linear_pairs(slope: float) -> list[dict[str, Any]]:
    return [
        dict(
            index=i,
            central_contribution=(slope if i == 0 else 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            forward_contribution=(slope if i == 0 else 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            even_contribution=(0.0,) * 6,
        )
        for i in range(6)
    ]


@pytest.mark.parametrize("slope,passes", [(11.0, True), (11.000001, False)])
def test_threshold_equality_failure_and_fixed_denominator(
    slope: float, passes: bool
) -> None:
    result = columns._column_diagnostics(
        _linear_pairs(slope), (10.0, 0, 0, 0, 0, 0), ((10.0, 0, 0, 0, 0, 0),) * 2
    )
    assert result["consistent"] is passes
    assert all(
        c["within_threshold"] is passes and c["threshold"] == 0.1
        for c in result["checks"]
    )


def test_zero_central_and_cancelled_contributions_are_not_divided_by() -> None:
    pairs = _linear_pairs(0.0)
    pairs[0]["central_contribution"] = (1e8, 0, 0, 0, 0, 0)
    pairs[1]["central_contribution"] = (-1e8, 0, 0, 0, 0, 0)
    result = columns._column_diagnostics(
        pairs, (10.0, 0, 0, 0, 0, 0), ((10.0, 0, 0, 0, 0, 0),) * 2
    )
    assert result["central_direction"] == (0.0,) * 6
    assert result["central_cancellation"]["sum_contribution_norms"] == 2e8
    assert result["central_cancellation"]["unavailable_reason"] == "zero-denominator"
    assert not result["consistent"]
    tiny = columns._column_diagnostics(
        _linear_pairs(1e100), (1e-300, 0, 0, 0, 0, 0), ((0.0,) * 6,) * 2
    )
    assert all(
        c["norm_ratio"] is None and c["unavailable_reason"] == "nonfinite-ratio"
        for c in tiny["checks"]
    )
    json.dumps(tiny, allow_nan=False)


@pytest.mark.parametrize("bad", [True, math.nan, math.inf])
def test_nonfinite_boolean_inputs_rejected(bad: float) -> None:
    with pytest.raises((ValueError, TrajectoryRefinementError)):
        columns._column_pair(
            (bad, 0, 0, 0, 0, 0), (0.0,) * 6, (0.0,) * 6, 0, (0.0,) * 6, (0.0,) * 6
        )
    with pytest.raises((ValueError, TrajectoryRefinementError)):
        columns._column_diagnostics(
            _linear_pairs(bad), (10.0, 0, 0, 0, 0, 0), ((0.0,) * 6,) * 2
        )


@pytest.mark.parametrize("index", [True, 1.0, -1, 6])
def test_invalid_column_index(index: int) -> None:
    with pytest.raises(ValueError):
        columns._column_pair(
            (0.0,) * 6, (0.0,) * 6, (0.0,) * 6, index, (0.0,) * 6, (0.0,) * 6
        )


def test_compensated_direction_preserves_cancellation() -> None:
    pairs = _linear_pairs(0.0)
    for i, value in enumerate((1e16, 1.0, -1e16)):
        pairs[i]["central_contribution"] = (value, 0.0, 0.0, 0.0, 0.0, 0.0)
    result = columns._column_diagnostics(
        pairs, (1.0, 0, 0, 0, 0, 0), ((1.0, 0, 0, 0, 0, 0),) * 2
    )
    assert result["central_direction"] == (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert result["consistent"] and result["central_cancellation"]["value"] == 2e16


def test_shapes_zero_retained_and_overflow() -> None:
    with pytest.raises(ValueError):
        columns._column_diagnostics([], (1.0,) * 6, ((0.0,) * 6,) * 2)
    with pytest.raises(ValueError, match="zero-retained"):
        columns._column_diagnostics(_linear_pairs(1.0), (0.0,) * 6, ((0.0,) * 6,) * 2)
    with pytest.raises((ValueError, TrajectoryRefinementError)):
        columns._column_pair(
            (0.0,) * 6, (1e308,) * 6, (-1e308,) * 6, 0, (0.0,) * 6, (0.0,) * 6
        )
