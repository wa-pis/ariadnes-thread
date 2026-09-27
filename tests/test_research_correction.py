from __future__ import annotations

from dataclasses import asdict, replace
import json
import math

import numpy as np
import pytest

from space_nav import research_correction as correction
from space_nav.scenario import load_scenario


def _linear_probes(base: tuple[float, ...], matrix: np.ndarray) -> tuple[tuple[float, ...], ...]:
    # Independently manufacture SI residuals from a known scaled linear map.
    return tuple(tuple(base[i] + matrix[i, j] * (1e-5, 1e-5, 1, 1e-5, 1e-5, 1)[j]
                       / (0.25, 0.25, 600, 0.25, 0.25, 600)[j]
                       * (1000, 1000, 1000, 0.01, 0.01, 0.01)[i]
                       for i in range(6)) for j in range(6))


@pytest.mark.parametrize("amplitude", [0.1, 10.0])
def test_independent_coupled_linear_oracle(amplitude: float) -> None:
    # Permuted, coupled triangular map: known solution, not another least-squares oracle.
    matrix = np.array([[2, 1, 0, 0, 0, 0], [0, 3, 1, 0, 0, 0], [0, 0, 4, 1, 0, 0],
                       [0, 0, 0, 5, 1, 0], [0, 0, 0, 0, 6, 1], [0, 0, 0, 0, 0, 7]], dtype=float)
    matrix = matrix[:, [2, 5, 0, 4, 1, 3]]
    exact = np.array([1, -0.5, 0.25, -0.125, 0.0625, -0.03125]) * amplitude
    base = tuple((-matrix @ exact) * np.array([1000]*3 + [0.01]*3))
    result = correction._correction(base, _linear_probes(base, matrix))
    assert result.rank == 6 and result.reason is None
    assert np.array(result.jacobian) == pytest.approx(matrix, abs=2e-9, rel=0)
    expected = exact / max(1.0, amplitude) * np.array([0.25, 0.25, 600]*2)
    assert result.control_step == pytest.approx(expected, abs=2e-6, rel=0)  # rad / s
    assert all(abs(v) <= s for v, s in zip(result.control_step, [0.25, 0.25, 600]*2))
    json.dumps(asdict(result), allow_nan=False)


def test_rank_deficiency_retains_diagnostics_without_step() -> None:
    result = correction._correction((1.0,)*6, ((1.0,)*6,)*6)
    assert result.rank == 0 and result.control_step is None
    assert result.reason == "rank-deficient" and result.singular_values == (0.0,)*6


def test_rank_cutoff_is_relative_and_pinned() -> None:
    matrix = np.diag([1, 1, 1, 1, 1, 1e-13])
    result = correction._correction((0.0,)*6, _linear_probes((0.0,)*6, matrix))
    assert result.rank == 5 and result.control_step is None
    assert result.singular_values[-1] == pytest.approx(1e-13, rel=1e-12)


def test_finite_inputs_can_overflow_differences() -> None:
    base = (1e308, 0, 0, 0, 0, 0)
    probe = (-1e308, 0, 0, 0, 0, 0)
    with pytest.raises(ValueError, match="probe residual change"):
        correction._correction(base, (probe,)*6)


@pytest.mark.parametrize("bad", [True, "1", float("nan"), float("inf"), 1e308])
def test_invalid_or_overflowing_residual_rejected(bad: object) -> None:
    with pytest.raises(ValueError):
        correction._correction((0.0,)*6, ((0, 0, 0, 0, 0, bad),)*6)


def test_missing_probe_and_bad_shape_rejected() -> None:
    with pytest.raises(ValueError):
        correction._correction((0.0,)*6, ((0.0,)*6,)*5)
    with pytest.raises(ValueError):
        correction._residual((0.0,)*5)


def test_nonfinite_native_solve_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(np.linalg, "lstsq", lambda *a, **kw: (np.full(6, np.nan), (), 6, np.ones(6)))
    with pytest.raises(ValueError, match="least-squares solution"):
        correction._correction((1.0,)*6, ((1.0,)*6,)*6)


def test_native_solve_failure_translated(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise np.linalg.LinAlgError("manufactured failure")
    monkeypatch.setattr(np.linalg, "lstsq", fail)
    with pytest.raises(ValueError, match="solve failed"):
        correction._correction((1.0,)*6, ((1.0,)*6,)*6)


def test_trial_reuses_angle_and_physical_bounds() -> None:
    craft = load_scenario("examples/m3_feasible_mission.toml").spacecraft
    seed = (math.pi-0.1, 0.0, 100.0, 0.0, 0.0, 100.0)
    trial = correction._trial_controls("fixture", craft, 0, 1000, seed, (0.2, 0, 1, 0, 0, 2))
    assert trial == pytest.approx((-math.pi+0.1, 0, 101, 0, 0, 102))
    assert correction._trial_controls("fixture", craft, 0, 1000, seed, (0, 0, -100, 0, 0, 0)) == "rejected-control-bounds"
    assert correction._trial_controls("fixture", craft, 0, 200, seed, (0,)*6) == "rejected-control-bounds"
    high = (0, math.pi/2, 100, 0, 0, 100)
    assert correction._trial_controls("fixture", craft, 0, 1000, high, (0, 0.01, 0, 0, 0, 0)) == "rejected-control-bounds"
    craft = replace(craft, max_thrust_n=craft.isp_s*9.80665, dry_mass_kg=craft.initial_mass_kg-201)
    assert correction._trial_controls("fixture", craft, 0, 1000, seed, (0, 0, 2, 0, 0, 0)) == "rejected-dry-mass"
    with pytest.raises(ValueError, match="trust scales"):
        correction._trial_controls("fixture", craft, 0, 1000, seed, (0.26, 0, 0, 0, 0, 0))


def test_score_closure_and_improvement_are_distinct() -> None:
    edge = (1000.0, 0, 0, 0.01, 0, 0)
    assert correction._residual(edge).closes
    assert not correction._residual((1000.0001, 0, 0, 0, 0, 0)).closes
    assert not correction._residual((0, 0, 0, 0.010001, 0, 0)).closes
    assert correction._residual((600, 800, 0, 0, 0, 0)).score == 1
    assert correction._improvement((1000.1, 0, 0, 0, 0, 0), edge)[0]  # closes despite larger score
    assert correction._improvement((0,)*6, (0,)*6) == (True, None, "zero-baseline-score")
    # A smaller weighted score can accompany a larger position miss.
    assert correction._improvement((1000, 0, 0, 1, 0, 0), (2000, 0, 0, 0.1, 0, 0))[0]
    assert not correction._improvement((2000, 0, 0, 0, 0, 0), (1999.9, 0, 0, 0, 0, 0))[0]
    assert correction._improvement((2000, 0, 0, 0, 0, 0), (1999.8, 0, 0, 0, 0, 0))[0]
    assert correction._improvement((1e-300, 0, 0, 0, 0, 0), (1e300, 0, 0, 0, 0, 0)) == (False, None, "nonfinite-score-ratio")
