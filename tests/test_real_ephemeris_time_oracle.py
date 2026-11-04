"""Native-free exact tests of the ADR0153 polynomial/time boundary oracle."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from fractions import Fraction
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any

import pytest


ORACLE_PATH = Path(__file__).resolve().parents[1] / "docs/adr/experiments/0153-real-ephemeris-oracle.py"


def _load_oracle() -> Any:
    name = "ariadna_0153_exact_oracle_test"
    spec = importlib.util.spec_from_file_location(name, ORACLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


oracle = _load_oracle()


def _record(
    x: tuple[int | float, ...], y: tuple[int | float, ...], z: tuple[int | float, ...],
    *, midpoint: int | float = 1000, radius: int | float = 2,
) -> Any:
    return oracle.parse_record([midpoint, radius, *x, *y, *z])


def _decoded(value: dict[str, str]) -> Fraction:
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def _decoded_vector(row: dict[str, Any], key: str) -> tuple[Fraction, ...]:
    return tuple(_decoded(value) for value in row["exact"][key])


@pytest.mark.parametrize("u", [Fraction(-1), Fraction(-3, 4), Fraction(), Fraction(1, 3), Fraction(1)])
def test_exact_degree_four_matches_independent_ordinary_polynomial(u: Fraction) -> None:
    record = _record((1, 2, 3, 4, 5), (-0.5, -1, -1.5, -2, -2.5), (7, 0, 0, 0, 0))
    position, velocity, bounds = oracle.evaluate_chain([record], Fraction(1000) + 2 * u)
    # Expanded independently: 1+2T1+3T2+4T3+5T4.
    ordinary = 3 - 10 * u - 34 * u**2 + 16 * u**3 + 40 * u**4
    derivative = -10 - 68 * u + 48 * u**2 + 160 * u**3
    acceleration = -68 + 96 * u + 480 * u**2
    assert position == (1000 * ordinary, -500 * ordinary, Fraction(7000))
    assert velocity == (500 * derivative, -250 * derivative, Fraction())
    assert bounds == (Fraction(127000), Fraction(63500), Fraction())
    assert abs(250 * acceleration) <= bounds[0]
    assert record.degree == 4


def test_acceleration_bound_is_attained_at_record_endpoint() -> None:
    record = _record((0, 0, 0, 1), (0, 0, 0, 0), (0, 0, 0, 0))
    _, _, bounds = oracle.evaluate_chain([record], Fraction(1002))
    # T3''(1)=24; SI conversion and radius^-2 give 1000*24/4.
    assert bounds == (Fraction(6000), Fraction(), Fraction())


def test_chain_sums_states_and_bounds_with_each_records_own_normalization() -> None:
    relative = _record((1, 2), (3, 4), (5, 6), midpoint=10, radius=2)
    earth = _record((7, -3), (8, -4), (9, -5), midpoint=8, radius=4)
    position, velocity, bounds = oracle.evaluate_chain([relative, earth], Fraction(10))
    assert position == (Fraction(6500), Fraction(9000), Fraction(11500))
    assert velocity == (Fraction(250), Fraction(1000), Fraction(1750))
    assert bounds == (Fraction(), Fraction(), Fraction())


def test_fraction_conversion_preserves_binary64_instead_of_display_decimal() -> None:
    record = _record((0.1,), (0.0,), (0.0,), midpoint=978995455.2304223, radius=1)
    assert record.midpoint_tdb_s == Fraction.from_float(978995455.2304223)
    assert record.midpoint_tdb_s != Fraction("978995455.2304223")
    assert record.coefficients_km[0][0] == Fraction.from_float(0.1)
    with pytest.raises(FrozenInstanceError):
        record.radius_s = Fraction(3)


@pytest.mark.parametrize("words", [[], [0, 1], [0, 1, 2, 3], [0, 1, 2, 3, 4, 5]])
def test_invalid_record_layout_rejected(words: list[int]) -> None:
    with pytest.raises(ValueError, match="record.words"):
        oracle.parse_record(words)


@pytest.mark.parametrize("bad", [True, "1", None, math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("index", [0, 1, 2, 4])
def test_record_rejects_invalid_or_nonfinite_words(bad: Any, index: int) -> None:
    words: list[Any] = [1000, 2, 1, 2, 3]
    words[index] = bad
    with pytest.raises(ValueError, match=rf"record.words\[{index}\]"):
        oracle.parse_record(words)


@pytest.mark.parametrize("radius", [0, -1])
def test_nonpositive_radius_rejected(radius: int) -> None:
    with pytest.raises(ValueError, match="radius_s"):
        oracle.parse_record([0, radius, 1, 2, 3])


@pytest.mark.parametrize("epoch", [Fraction(997), Fraction(1003)])
def test_record_coverage_rejected(epoch: Fraction) -> None:
    with pytest.raises(ValueError, match="coverage"):
        oracle.evaluate_chain([_record((1,), (2,), (3,))], epoch)


def test_chain_requires_exact_epoch_and_one_or_two_valid_records() -> None:
    record = _record((1,), (2,), (3,))
    for records in ([], [record, record, record], [None]):
        with pytest.raises(ValueError, match="records"):
            oracle.evaluate_chain(records, Fraction(1000))
    with pytest.raises(ValueError, match="epoch_tdb_s"):
        oracle.evaluate_chain([record], 1000.0)


def test_linear_realistic_speed_sample_retains_source_floor_and_rejects_wrong_sign() -> None:
    record = _record((1, 60), (2, 0), (3, 0))  # 30000m/s in X.
    floor = 2.0**-20
    lo = 2.0**-26
    row = oracle.assess([1000.0 + floor, 2000.0, 3000.0, 30000.0, 0.0, 0.0], [record], 1000.0, lo)
    assert row["passed"] and all(row["checks"].values())
    assert not row["wrong_sign_increment_passed"]
    assert _decoded_vector(row, "increment_error_m") == (Fraction(),) * 3
    assert _decoded_vector(row, "source_position_floor_m") == (Fraction.from_float(floor), Fraction(), Fraction())
    assert _decoded_vector(row, "corrected_position_error_m") == _decoded_vector(row, "source_position_floor_m")
    assert row["correction_m"][0] == 30000.0 * lo
    assert _decoded_vector(row, "corrected_position_m")[0] == Fraction.from_float(1000.0 + floor) + Fraction.from_float(30000.0 * lo)
    assert row["hi_hex"] == (1000.0).hex()
    json.dumps(row, allow_nan=False)


def test_nonlinear_taylor_term_is_measured_exactly() -> None:
    record = _record((0, 0, 1), (0, 0, 0), (0, 0, 0))
    lo = 2.0**-30
    row = oracle.assess([-1000.0, 0.0, 0.0, 0.0, 0.0, 0.0], [record], 1000.0, lo)
    expected = Fraction.from_float(lo) ** 2 * 500
    assert _decoded_vector(row, "increment_error_m")[0] == -expected
    assert _decoded_vector(row, "taylor_bound_m")[0] == expected
    assert row["checks"]["taylor"]
    assert row["passed"]


def test_velocity_floor_and_binary64_product_rounding_are_in_taylor_bound() -> None:
    record = _record((1, 0.1), (0, 0), (0, 0), radius=1)
    _, reference_velocity, _ = oracle.evaluate_chain([record], Fraction(1000))
    velocity = float(reference_velocity[0])
    row = oracle.assess([1000.0, 0.0, 0.0, velocity, 0.0, 0.0], [record], 1000.0, 0.1)
    product = Fraction.from_float(velocity) * Fraction.from_float(0.1)
    rounding_error = Fraction.from_float(velocity * 0.1) - product
    assert _decoded_vector(row, "correction_rounding_error_m")[0] == rounding_error
    assert _decoded_vector(row, "velocity_error_m_s")[0] == Fraction.from_float(velocity) - reference_velocity[0]
    assert row["checks"]["taylor"]


@pytest.mark.parametrize("lo", [0.0, 2.0**-26, -(2.0**-26)])
def test_lo_sign_and_zero_are_preserved(lo: float) -> None:
    record = _record((1, 2), (2, 0), (3, 0))
    row = oracle.assess([1000.0, 2000.0, 3000.0, 1000.0, 0.0, 0.0], [record], 1000.0, lo)
    assert row["passed"]
    assert row["correction_m"][0] == 1000 * lo
    assert _decoded(row["exact_epoch_tdb_s"]) == Fraction(1000) + Fraction.from_float(lo)
    assert row["wrong_sign_increment_passed"] == (lo == 0)


@pytest.mark.parametrize("state", [[1, 2], [True, 2, 3, 4, 5, 6], [1, 2, 3, math.inf, 5, 6]])
def test_assessment_rejects_invalid_state(state: list[Any]) -> None:
    with pytest.raises(ValueError, match="state_si"):
        oracle.assess(state, [_record((1,), (2,), (3,))], 1000.0, 0.0)


@pytest.mark.parametrize("time_field", ["hi", "lo"])
@pytest.mark.parametrize("bad", [True, math.nan, math.inf])
def test_assessment_rejects_invalid_time(time_field: str, bad: Any) -> None:
    operands = {"hi": 1000.0, "lo": 0.0, time_field: bad}
    with pytest.raises(ValueError, match=time_field):
        oracle.assess([1000.0, 2000.0, 3000.0, 0, 0, 0], [_record((1,), (2,), (3,))], **operands)


def test_assessment_rejects_exact_time_outside_record_even_if_hi_inside() -> None:
    with pytest.raises(ValueError, match="coverage"):
        oracle.assess([1000, 2000, 3000, 0, 0, 0], [_record((1,), (2,), (3,))], 1002.0, 2.0**-30)


@pytest.mark.parametrize(
    ("state", "failed_check"),
    [([1000.002, 2000, 3000, 1000, 0, 0], "position_parity"),
     ([1000, 2000, 3000, 1000.000002, 0, 0], "velocity_parity")],
)
def test_parity_gates_are_not_hidden_by_increment_success(state: list[float], failed_check: str) -> None:
    row = oracle.assess(state, [_record((1, 2), (2, 0), (3, 0))], 1000.0, 0.0)
    assert not row["passed"]
    assert not row["checks"][failed_check]
    assert row["checks"]["increment"]


def test_module_has_only_stdlib_imports_and_no_native_queries() -> None:
    tree = ast.parse(ORACLE_PATH.read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    assert modules <= {"__future__", "collections", "dataclasses", "fractions", "math", "typing"}


def test_nonlinear_chain_acceleration_bounds_add_in_si() -> None:
    first = _record((0, 0, 1, 0), (0, 0, 0, 0), (0, 0, 0, 0), radius=2)
    second = _record((0, 0, 0, 1), (0, 0, 0, 0), (0, 0, 0, 0), midpoint=1001, radius=4)
    _, _, bounds = oracle.evaluate_chain([first, second], Fraction(1000))
    assert bounds == (Fraction(1000 + 1500), Fraction(), Fraction())
