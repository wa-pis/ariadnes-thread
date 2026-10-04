from __future__ import annotations

import numpy as np
import pytest

from space_nav import research_correction as correction


@pytest.mark.parametrize("amplitude", [0.1, 1.0, 10.0])
def test_coupled_matrix_independent_solution_and_prediction(amplitude: float) -> None:
    matrix = np.array([[3, 1, 0, 0, 0, 1], [0, 4, 1, 0, 0, 0],
                       [0, 0, 5, 1, 0, 0], [0, 0, 0, 6, 1, 0],
                       [0, 0, 0, 0, 7, 1], [1, 0, 0, 0, 0, 8]], dtype=float)
    residual = amplitude * np.array([1, -2, 3, -4, 5, -6], dtype=float)
    expected = np.linalg.solve(matrix, -residual)
    divisor = max(1.0, float(np.max(np.abs(expected))))
    result = correction._central_correction(tuple(map(tuple, matrix)),
        tuple(residual * correction._RESIDUAL_SCALES))
    assert result["rank"] == 6 and result["reason"] is None
    assert result["uncapped"] == pytest.approx(expected, abs=1e-12)
    assert result["divisor"] == pytest.approx(divisor, abs=1e-12)
    assert result["capped"] == pytest.approx(expected / divisor, abs=1e-12)
    assert result["control_step"] == pytest.approx(
        expected / divisor * correction._TRUST_SCALES, abs=1e-9)
    assert result["predicted_change"] == pytest.approx(matrix @ (expected/divisor), abs=1e-12)
    assert result["predicted_residual"] == pytest.approx(residual*(1-1/divisor), abs=1e-12)
    assert result["predicted_score"] < np.linalg.norm(residual)


def test_rank_loss_and_zero_step_stop() -> None:
    identity = tuple(map(tuple, np.eye(6)))
    assert correction._central_correction(identity, (0,)*6)["reason"] == "zero-control-step"
    result = correction._central_correction(tuple(map(tuple, np.zeros((6, 6)))), (1,)*6)
    assert result["reason"] == "rank-deficient" and result["control_step"] is None
    assert result["predicted_score"] is None


def test_no_predicted_decrease_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    identity = tuple(map(tuple, np.eye(6)))
    step = correction._MatrixStep(6, (1,)*6, (1,)*6, 1, (1,)*6,
                                  correction._TRUST_SCALES, None)
    monkeypatch.setattr(correction, "_solve_matrix", lambda *args: step)
    result = correction._central_correction(identity, correction._RESIDUAL_SCALES)
    assert result["reason"] == "no-predicted-decrease"
    assert result["predicted_score"] == pytest.approx(2*np.sqrt(6))


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf")])
def test_nonfinite_or_boolean_matrix_rejected(bad: float) -> None:
    matrix = [list(row) for row in np.eye(6)]
    matrix[0][0] = bad
    with pytest.raises(ValueError):
        correction._central_correction(tuple(map(tuple, matrix)), (1,)*6)
