"""Invocation-local reuse must preserve the exact harmonic oracle."""
from fractions import Fraction

import numpy as np
import pytest

from space_nav import trajectory
import test_trajectory_spk as spk
from test_trajectory_spk import (
    _HarmonicErrorCache, _generic_harmonic_term_errors_m_s2, _reused_harmonic_term_errors_m_s2,
)

_Inputs = tuple[float, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]


def _inputs() -> _Inputs:
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    cosine[0, 0], cosine[2, 1], sine[2, 1] = 1.0, 0.125, -0.25
    return (125.0, 1.0, cosine, sine, np.zeros(3), np.asarray([3.0, -4.0, 1.0]),
            np.eye(3), np.zeros((6, 3)))


def test_reuse_matches_uncached_and_isolates_results() -> None:
    budget = trajectory._RefinementBudget("reuse-parity", 300.0)
    cache: _HarmonicErrorCache = {}
    inputs = _inputs()
    expected = _generic_harmonic_term_errors_m_s2(budget, *inputs)
    first = _reused_harmonic_term_errors_m_s2(cache, budget, *inputs)
    assert first == expected
    first.clear()
    assert _reused_harmonic_term_errors_m_s2(cache, budget, *inputs) == expected
    assert len(cache) == 1 and all(isinstance(value, tuple) for value in cache.values())
    independent_cache: _HarmonicErrorCache = {}
    assert _reused_harmonic_term_errors_m_s2(independent_cache, budget, *inputs) == expected
    assert len(independent_cache) == 1


@pytest.mark.parametrize("index", range(8))
def test_every_scientific_input_change_misses(index: int) -> None:
    budget = trajectory._RefinementBudget("reuse-miss", 300.0)
    cache: _HarmonicErrorCache = {}
    inputs = _inputs()
    before = _reused_harmonic_term_errors_m_s2(cache, budget, *inputs)
    if index < 2:
        inputs = (inputs[0] + (index == 0), inputs[1] + (index == 1), *inputs[2:])
    else:
        array = inputs[index]
        if index == 3:
            array[2, 1] += 0.125  # Valid sine term; first column must stay zero.
        else:
            array.flat[0] += 0.125
    actual = _reused_harmonic_term_errors_m_s2(cache, budget, *inputs)
    assert actual == _generic_harmonic_term_errors_m_s2(budget, *inputs)
    assert len(cache) == 2
    assert _reused_harmonic_term_errors_m_s2(cache, budget, *_inputs()) == before


@pytest.mark.parametrize("invalid", ["boolean", "nan", "shape", "dtype", "triangular", "sine"])
def test_invalid_input_cannot_hit_or_populate_cache(invalid: str) -> None:
    budget = trajectory._RefinementBudget("reuse-invalid", 300.0)
    cache: _HarmonicErrorCache = {}
    inputs = _inputs()
    _reused_harmonic_term_errors_m_s2(cache, budget, *inputs)
    if invalid == "boolean":
        inputs = (True, *inputs[1:])  # type: ignore[assignment] -- invalid scalar boundary.
    elif invalid == "nan":
        inputs[7][0, 0] = np.nan
    elif invalid == "shape":
        inputs = (*inputs[:7], inputs[7].reshape(3, 6))
    elif invalid == "dtype":
        inputs = (*inputs[:7], inputs[7].astype(np.float32))
    elif invalid == "triangular":
        inputs[2][0, 1] = 1.0
    else:
        inputs[3][0, 0] = 1.0
    with pytest.raises(AssertionError):
        _reused_harmonic_term_errors_m_s2(cache, budget, *inputs)
    assert len(cache) == 1


def test_reuse_hit_still_checks_deadline() -> None:
    now_s = [0.0]
    budget = trajectory._RefinementBudget("reuse-deadline", 300.0, lambda: now_s[0])
    cache: _HarmonicErrorCache = {}
    _reused_harmonic_term_errors_m_s2(cache, budget, *_inputs())
    now_s[0] = 301.0
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _reused_harmonic_term_errors_m_s2(cache, budget, *_inputs())
    assert len(cache) == 1


def test_reuse_monopole_has_independent_exact_oracle() -> None:
    budget = trajectory._RefinementBudget("reuse-monopole", 300.0)
    cache: _HarmonicErrorCache = {}
    for _ in range(2):
        result = _reused_harmonic_term_errors_m_s2(
            cache, budget, 125.0, 1.0, np.ones((1, 1)), np.zeros((1, 1)),
            np.zeros(3), np.asarray([3.0, -4.0, 0.0]), np.eye(3), np.asarray([[-3.0, 4.0, 0.125]]),
        )
        assert result == {(0, 0): Fraction(1, 8)}
    assert len(cache) == 1


def test_hit_does_not_reevaluate(monkeypatch: pytest.MonkeyPatch) -> None:
    budget = trajectory._RefinementBudget("reuse-hit", 300.0)
    cache: _HarmonicErrorCache = {}
    expected = _reused_harmonic_term_errors_m_s2(cache, budget, *_inputs())

    def unexpected(*args: object, **kwargs: object) -> dict[tuple[int, int], Fraction]:
        raise AssertionError("unexpected uncached evaluation")

    monkeypatch.setattr(spk, "_generic_harmonic_term_errors_m_s2", unexpected)
    assert _reused_harmonic_term_errors_m_s2(cache, budget, *_inputs()) == expected
    with pytest.raises(AssertionError, match="unexpected uncached"):
        _reused_harmonic_term_errors_m_s2({}, budget, *_inputs())


def test_expired_computation_is_not_retained(monkeypatch: pytest.MonkeyPatch) -> None:
    now_s = [0.0]
    budget = trajectory._RefinementBudget("reuse-expired-miss", 300.0, lambda: now_s[0])
    cache: _HarmonicErrorCache = {}

    def expire(*args: object, **kwargs: object) -> dict[tuple[int, int], Fraction]:
        now_s[0] = 301.0
        return {(0, 0): Fraction(0)}

    monkeypatch.setattr(spk, "_generic_harmonic_term_errors_m_s2", expire)
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _reused_harmonic_term_errors_m_s2(cache, budget, *_inputs())
    assert not cache
