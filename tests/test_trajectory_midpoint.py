"""Euclidean midpoint errors for stored acceleration enclosures, not full forces."""

from fractions import Fraction
from hashlib import sha256
from itertools import product
import json
import math
from pathlib import Path

import pytest

from test_trajectory_spk import _dyadic_sqrt_bounds


def _midpoint_acceleration_l2_bound_m_s2(
    prefix_intervals_m_s2: tuple[tuple[Fraction, Fraction], ...], tail_l2_m_s2: Fraction,
) -> tuple[tuple[float, ...], Fraction]:
    """Round a midpoint and bound its L2 error for a box plus a separate L2 tail.

    Inputs share SI and one Cartesian frame. Tail must not already be in the
    supplied box. The bound includes midpoint rounding, not source/PCK errors.
    """
    assert len(prefix_intervals_m_s2) == 3
    assert all(len(pair) == 2 and all(isinstance(value, Fraction) for value in pair)
               and pair[0] <= pair[1] for pair in prefix_intervals_m_s2)
    assert isinstance(tail_l2_m_s2, Fraction) and tail_l2_m_s2 >= 0
    midpoint_m_s2 = tuple(float((lo+hi)/2) for lo, hi in prefix_intervals_m_s2)
    assert all(math.isfinite(value) for value in midpoint_m_s2)
    component_errors = tuple(max(abs(Fraction(mid)-lo), abs(Fraction(mid)-hi))
                             for mid, (lo, hi) in zip(midpoint_m_s2, prefix_intervals_m_s2, strict=True))
    squared = sum((error**2 for error in component_errors), Fraction(0))
    prefix_l2 = _dyadic_sqrt_bounds(squared)[1] if squared else Fraction(0)
    return midpoint_m_s2, prefix_l2+tail_l2_m_s2


@pytest.mark.parametrize("centre", [(Fraction(0),)*3, (Fraction(1, 3), Fraction(-2, 7), Fraction(1, 10)),
                                   (Fraction(2**60+1), Fraction(-2**60-1), Fraction(2)**-1100)])
@pytest.mark.parametrize("widths", [(0, 0, 0), (3, 4, 0), (1, 1, 1)])
@pytest.mark.parametrize("tail", [Fraction(0), Fraction(2), Fraction(1, 10)])
def test_midpoint_l2_encloses_independent_vectors(
    centre: tuple[Fraction, ...], widths: tuple[int, ...], tail: Fraction,
) -> None:
    box = tuple((c-w, c+w) for c, w in zip(centre, widths, strict=True))
    midpoint, bound = _midpoint_acceleration_l2_bound_m_s2(box, tail)
    directions = ((Fraction(0),)*3, (Fraction(1), Fraction(0), Fraction(0)),
                  (Fraction(3, 5), Fraction(4, 5), Fraction(0)),
                  (Fraction(-3, 5), Fraction(-4, 5), Fraction(0)))
    for corner, direction in product(product(*box), directions):
        assert sum(value**2 for value in direction) <= 1
        truth = tuple(value+tail*axis for value, axis in zip(corner, direction, strict=True))
        assert sum((value-Fraction(mid))**2 for value, mid in zip(truth, midpoint, strict=True)) <= bound**2
    if centre == (Fraction(0),)*3 and widths == (3, 4, 0):
        assert bound == 5+tail  # Aligned (3,4,0) corner plus tail attains this.
    if centre == (Fraction(0),)*3 and widths == (0, 0, 0):
        assert bound == tail  # A norm-bounded tail is counted once, not per axis.
    if centre == (Fraction(0),)*3 and widths == (1, 1, 1) and tail == 0:
        assert bound**2 >= 3 and bound > 1  # One component's radius is insufficient.
    if centre == (Fraction(1, 3), Fraction(-2, 7), Fraction(1, 10)) and widths == (0, 0, 0):
        assert bound > tail  # Nonrepresentable midpoint rounding is not lost.


@pytest.mark.parametrize("case", ["shape", "order", "float", "boolean-tail", "negative-tail", "nonfinite", "overflow"])
def test_midpoint_l2_rejects_invalid_input(case: str) -> None:
    box = ((Fraction(0), Fraction(0)),)*3
    tail = Fraction(0)
    if case == "shape":
        box = box[:2]
    elif case == "order":
        box = ((Fraction(1), Fraction(0)),)*3
    elif case in {"float", "nonfinite"}:
        box = ((float("inf") if case == "nonfinite" else 0.0, Fraction(0)),)*3
    elif case == "boolean-tail":
        tail = True
    elif case == "negative-tail":
        tail = Fraction(-1)
    elif case == "overflow":
        box = ((Fraction(10**400), Fraction(10**400)),)*3
    with pytest.raises(OverflowError if case == "overflow" else AssertionError):
        _midpoint_acceleration_l2_bound_m_s2(box, tail)


def test_stored_degree100_box_midpoint() -> None:
    record = json.loads((Path(__file__).parent / "data/m3_mars_degree100_evaluation.json").read_text())
    assert record["prefix_degree"] == 100
    snapshot_bytes = (Path(__file__).parent / "data/m3_fresh_harmonic_replay.json").read_bytes()
    assert record["snapshot_sha256"] == sha256(snapshot_bytes).hexdigest()
    snapshot = json.loads(snapshot_bytes)
    assert (snapshot["origin"], snapshot["orientation"]) == ("SSB", "J2000")
    box = tuple(tuple(map(Fraction, pair)) for pair in record["component_intervals_m_s2"])
    # Recorded intervals ALREADY contain the tail. Do not add it again or
    # subtract a rounded tail to guess unavailable exact prefix intervals.
    midpoint, bound = _midpoint_acceleration_l2_bound_m_s2(box, Fraction(0))
    for corner in product(*box):
        assert sum((value-Fraction(mid))**2 for value, mid in zip(corner, midpoint, strict=True)) <= bound**2
    reported = math.nextafter(float(bound), math.inf)
    assert math.isfinite(reported) and Fraction(reported) >= bound > 0
    print(json.dumps({"stored_degree100_box_midpoint": {
        "midpoint_m_s2": midpoint, "l2_error_upper_m_s2": reported,
        "origin": "SSB", "orientation": "J2000", "epoch_tdb_s": snapshot["epoch_tdb_s"],
        "qualification": "Conservative whole-box L2 bound including existing tail and rounding; no source/PCK, other-force or trajectory qualification",
    }}, sort_keys=True, allow_nan=False))
