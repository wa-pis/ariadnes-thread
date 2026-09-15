"""Low-degree interval recurrence controls, not normalized gravity evidence."""

from fractions import Fraction
import json
import math
from time import perf_counter

import pytest

from space_nav import trajectory
from test_trajectory_rounded_arithmetic import _DyadicInterval
from test_trajectory_spk import _regular_solid_harmonic_jets


@pytest.mark.parametrize("bounds", [(-3, -1), (-2, 3), (0, 0), (1, 4)])
@pytest.mark.parametrize("other_bounds", [(-4, -2), (-1, 2), (0, 0), (2, 5)])
def test_interval_operations_cover_exact_box_samples(bounds: tuple[int, int], other_bounds: tuple[int, int]) -> None:
    a = _DyadicInterval(*(Fraction(x, 3) for x in bounds), 24)
    b = _DyadicInterval(*(Fraction(x, 7) for x in other_bounds), 24)
    for x in (Fraction(bounds[0], 3), Fraction(sum(bounds), 6), Fraction(bounds[1], 3)):
        for y in (Fraction(other_bounds[0], 7), Fraction(sum(other_bounds), 14), Fraction(other_bounds[1], 7)):
            for result, exact in ((a+b, x+y), (a-b, x-y), (a*b, x*y), (a/7, x/7),
                                  (a**2, x*x), (-a, -x), (2-a, 2-x), (2*a, 2*x),
                                  (Fraction(1, 7)+a, Fraction(1, 7)+x)):
                assert result.lower <= exact <= result.upper


@pytest.mark.parametrize("invalid", ["reversed", "precision", "mixed", "float", "zero-divisor",
                                    "negative-divisor", "interval-divisor", "power"])
def test_interval_arithmetic_rejects_unsupported_operations(invalid: str) -> None:
    a = _DyadicInterval(Fraction(-1), Fraction(2), 24)
    with pytest.raises(AssertionError):
        if invalid == "reversed":
            _DyadicInterval(Fraction(2), Fraction(1), 24)
        elif invalid == "precision":
            _DyadicInterval(Fraction(0), Fraction(1), True)
        elif invalid == "mixed":
            a + _DyadicInterval(Fraction(0), Fraction(1), 53)
        elif invalid == "float":
            a + 0.5  # type: ignore[arg-type] -- rejection control.
        elif invalid == "zero-divisor":
            a / 0
        elif invalid == "negative-divisor":
            a / -1
        elif invalid == "interval-divisor":
            a / a  # type: ignore[arg-type] -- deliberately unsupported.
        else:
            a**3


def test_low_degree_interval_jets_enclose_exact_oracle() -> None:
    budget = trajectory._RefinementBudget("bounded-solid-degree8", 300.0)
    reports = []
    for point in ((Fraction(1, 3), Fraction(-2, 5), Fraction(7, 11)),
                  tuple(map(Fraction, (0.31, -0.47, 0.83))),
                  (Fraction(0), Fraction(0), Fraction(-1)), (Fraction(0),)*3):
        started_s = perf_counter()
        exact_rows = list(_regular_solid_harmonic_jets(budget, point, 8))
        exact_elapsed_s = perf_counter() - started_s
        for bits in (24, 53, 80, 120):
            started_s = perf_counter()
            enclosed = tuple(_DyadicInterval(x, x, bits) for x in point)
            bounded_rows = list(_regular_solid_harmonic_jets(budget, enclosed, 8))
            bounded_elapsed_s = perf_counter() - started_s
            width = scaled_width = Fraction(0)
            scalar_count = 0
            for exact_row, bounded_row in zip(exact_rows, bounded_rows, strict=True):
                assert exact_row[:2] == bounded_row[:2]
                for exact_jet, bounded_jet in zip(exact_row[2:], bounded_row[2:], strict=True):
                    for exact, bounded in zip(exact_jet, bounded_jet, strict=True):
                        if isinstance(bounded, Fraction):  # Exact degree-zero constants.
                            bounded = _DyadicInterval(bounded, bounded, bits)
                        assert bounded.lower <= exact <= bounded.upper, (bits, exact_row[:2])
                        for endpoint in (bounded.lower, bounded.upper):
                            numerator = abs(endpoint.numerator)
                            if numerator:
                                assert (numerator // (numerator & -numerator)).bit_length() <= bits
                        width = max(width, bounded.upper - bounded.lower)
                        scaled_width = max(scaled_width, (bounded.upper - bounded.lower)/max(1, abs(exact)))
                        scalar_count += 1
            assert len(bounded_rows) == 45 and scalar_count == 360
            budget.check()
            reports.append({"coordinates_exact": [[hex(x.numerator), hex(x.denominator)] for x in point],
                            "bits": bits, "maximum_degree": 8, "terms": 45, "scalar_components": scalar_count,
                            "maximum_width_upper": math.nextafter(float(width), math.inf) if width else 0.0,
                            "maximum_width_over_max_one_abs_exact_upper": math.nextafter(float(scaled_width), math.inf) if scaled_width else 0.0,
                            "exact_elapsed_s": exact_elapsed_s, "bounded_elapsed_s": bounded_elapsed_s})
    assert budget.native_arc_propagations == 0
    print(json.dumps({"low_degree_interval_jets": {"scope": "dimensionless unnormalized polynomial jets; not force",
                                                  "native_arcs": 0, "cases": reports}}, sort_keys=True))


@pytest.mark.parametrize("invalid", ["mixed-types", "mixed-precision"])
def test_interval_jets_reject_mixed_coordinates(invalid: str) -> None:
    a = _DyadicInterval(Fraction(0), Fraction(0), 24)
    last = Fraction(0) if invalid == "mixed-types" else _DyadicInterval(Fraction(0), Fraction(0), 53)
    with pytest.raises(AssertionError):
        list(_regular_solid_harmonic_jets(trajectory._RefinementBudget("mixed-jets", 300.0), (a, a, last), 8))


def test_interval_jets_preserve_deadline_check() -> None:
    clock = iter([0.0, 0.0, 0.0, 0.0, 301.0])
    a = _DyadicInterval(Fraction(1, 3), Fraction(1, 3), 24)
    stream = _regular_solid_harmonic_jets(
        trajectory._RefinementBudget("interval-jets-expired", 300.0, lambda: next(clock)), (a, a, a), 2,
    )
    assert next(stream)[:2] == (0, 0)
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        next(stream)
