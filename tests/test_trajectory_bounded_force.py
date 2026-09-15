"""Low-degree finite manufactured fields; no physical full-field anchor."""

from fractions import Fraction
import json
import math
from time import perf_counter

import numpy as np
import pytest

from space_nav import trajectory
from test_trajectory_rounded_arithmetic import _DyadicInterval
from test_trajectory_spk import _dyadic_sqrt_bounds, _generic_harmonic_term_intervals_m_s2


@pytest.mark.parametrize("bits", [24, 80, 120])
@pytest.mark.parametrize("q,normalization_squared", [(Fraction(25, 16), Fraction(1)),
                                                    (Fraction(1, 3), Fraction(5)),
                                                    (Fraction(200), Fraction(34, math.factorial(16)))])
def test_rounded_normalization_encloses_exact_squared_ratio(bits: int, q: Fraction, normalization_squared: Fraction) -> None:
    root_lo, root_hi = _dyadic_sqrt_bounds(q)
    norm_lo, norm_hi = _dyadic_sqrt_bounds(normalization_squared)
    factor = _DyadicInterval(norm_lo/root_hi, norm_hi/root_lo, bits)
    assert 0 < factor.lower <= factor.upper
    assert factor.lower**2 <= normalization_squared/q <= factor.upper**2


@pytest.mark.parametrize("bits", [24, 80, 120])
@pytest.mark.parametrize("scale", [1.0, 2.0])
def test_bounded_monopole_matches_independent_vector(bits: int, scale: float) -> None:
    terms = dict(_generic_harmonic_term_intervals_m_s2(
        trajectory._RefinementBudget("bounded-monopole", 300.0), 125.0, scale,
        np.ones((1, 1)), np.zeros((1, 1)), np.zeros(3), scale*np.asarray([3.0, -4.0, 0.0]),
        np.eye(3), bits=bits,
    ))
    for exact, (lo, hi) in zip((Fraction(-3), Fraction(4), Fraction(0)), terms[0, 0], strict=True):
        assert lo <= exact/Fraction(scale)**2 <= hi


def test_low_degree_bounded_force_encloses_exact_terms_and_sum() -> None:
    budget = trajectory._RefinementBudget("bounded-force-degree8", 300.0)
    gm, radius = 42828375815756.1, 3396000.0
    body = np.full(3, 1e12)
    offset = np.asarray([3000000.0, -4000000.0, 1000000.0])
    matrices = {"identity": np.eye(3), "proper-signed-permutation": np.asarray([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]]),
                "stored-shear-scale": np.asarray([[1., .125, 0.], [0., .875, 0.], [0., 0., 1.125]])}
    reports = []
    for degree in (0, 2, 8):
        cosine, sine = np.zeros((degree+1, degree+1)), np.zeros((degree+1, degree+1))
        for n in range(degree+1):
            for m in range(n+1):
                cosine[n, m] = (-1.)**(n+m)*2.**(-n-m-8)
                sine[n, m] = (-1.)**m*2.**(-n-m-9) if m else 0.
        cosine[0, 0] = 1.0
        for name, matrix in matrices.items():
            started = perf_counter()
            exact = list(_generic_harmonic_term_intervals_m_s2(
                budget, gm, radius, cosine, sine, body, body+offset, matrix,
            ))
            exact_elapsed_s = perf_counter()-started
            for bits in (24, 53, 80, 120):
                started = perf_counter()
                bounded = list(_generic_harmonic_term_intervals_m_s2(
                    budget, gm, radius, cosine, sine, body, body+offset, matrix, bits=bits,
                ))
                bounded_elapsed_s = perf_counter()-started
                exact_sum, bounded_sum = [[Fraction(0)]*2 for _ in range(3)], [[Fraction(0)]*2 for _ in range(3)]
                maximum_width = Fraction(0)
                for (key, components), (exact_key, exact_components) in zip(bounded, exact, strict=True):
                    assert key == exact_key
                    for axis, ((lo, hi), (elo, ehi)) in enumerate(zip(components, exact_components, strict=True)):
                        assert lo <= elo <= ehi <= hi, (degree, name, bits, key, axis)
                        maximum_width = max(maximum_width, hi-lo)
                        for side in range(2):
                            exact_sum[axis][side] += exact_components[axis][side]
                            bounded_sum[axis][side] += components[axis][side]
                assert len(bounded) == (degree+1)*(degree+2)//2
                midpoint = [float((lo+hi)/2) for lo, hi in bounded_sum]
                midpoint_error = Fraction(0)
                widths = []
                for axis, ((lo, hi), (elo, ehi)) in enumerate(zip(bounded_sum, exact_sum, strict=True)):
                    assert lo <= elo <= ehi <= hi
                    midpoint_error += max(abs(Fraction(midpoint[axis])-lo), abs(Fraction(midpoint[axis])-hi))
                    widths.append(math.nextafter(float(hi-lo), math.inf) if hi != lo else 0.0)
                reports.append({"degree": degree, "matrix": name, "bits": bits, "terms": len(bounded),
                                "maximum_term_width_upper_m_s2": math.nextafter(float(maximum_width), math.inf),
                                "summed_component_width_upper_m_s2": widths, "midpoint_m_s2": midpoint,
                                "midpoint_l1_error_upper_m_s2": math.nextafter(float(midpoint_error), math.inf),
                                "exact_elapsed_s": exact_elapsed_s, "bounded_elapsed_s": bounded_elapsed_s})
                budget.check()
    assert budget.native_arc_propagations == 0
    print(json.dumps({"low_degree_bounded_force": {"scope": "manufactured finite fields at exact stored geometry; source/PCK/native input errors excluded",
                                                 "gm_m3_s2": gm, "reference_radius_m": radius,
                                                 "body_position_m": body.tolist(), "spacecraft_position_m": (body+offset).tolist(),
                                                 "matrices": {key: value.tolist() for key, value in matrices.items()},
                                                 "coefficients": "C00=1; Cnm=(-1)^(n+m)*2^(-n-m-8) otherwise; Sn0=0, Snm=(-1)^m*2^(-n-m-9) for m>0",
                                                 "native_arcs": 0, "cases": reports}}, sort_keys=True))


@pytest.mark.parametrize("invalid", ["boolean", "zero", "negative", "float", "singularity", "nonfinite", "expired"])
def test_bounded_force_rejects_invalid_inputs(invalid: str) -> None:
    bits = {"boolean": True, "zero": 0, "negative": -1, "float": 53.0}.get(invalid, 80)
    position = np.zeros(3) if invalid == "singularity" else np.asarray([math.nan, 1., 1.]) if invalid == "nonfinite" else np.ones(3)
    clock = iter([0., 301.]) if invalid == "expired" else None
    budget = trajectory._RefinementBudget("bounded-force-invalid", 300., lambda: next(clock)) if clock else trajectory._RefinementBudget("bounded-force-invalid", 300.)
    with pytest.raises(trajectory.TrajectoryRefinementError if clock else AssertionError):
        list(_generic_harmonic_term_intervals_m_s2(
            budget, 125., 1., np.ones((1, 1)), np.zeros((1, 1)), np.zeros(3), position, np.eye(3),
            bits=bits,  # type: ignore[arg-type] -- rejection controls.
        ))
