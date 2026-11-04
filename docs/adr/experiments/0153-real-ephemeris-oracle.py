"""Exact arithmetic for the ADR0153 Type2 ephemeris boundary experiment.

Records contain km, epochs are TDB seconds from J2000, and returned states use SI.
This module neither loads kernels nor imports a scientific package.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
import math
from typing import Any


type Vector3 = tuple[Fraction, Fraction, Fraction]
type Coefficients = tuple[tuple[Fraction, ...], tuple[Fraction, ...], tuple[Fraction, ...]]


def _exact(value: int | float, field: str) -> Fraction:
    """Preserve a supplied binary64 value exactly; reject invalid operands."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field}: expected a finite number, excluding bool")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field}: expected a finite number")
        return Fraction.from_float(value)
    return Fraction(value)


@dataclass(frozen=True, slots=True)
class Type2Record:
    """One Type2 record; coefficient order is X, Y, Z then increasing degree."""

    midpoint_tdb_s: Fraction
    radius_s: Fraction
    coefficients_km: Coefficients

    def __post_init__(self) -> None:
        if not isinstance(self.midpoint_tdb_s, Fraction):
            raise ValueError("midpoint_tdb_s: expected Fraction")
        if not isinstance(self.radius_s, Fraction) or self.radius_s <= 0:
            raise ValueError("radius_s: expected positive Fraction")
        if not isinstance(self.coefficients_km, tuple) or len(self.coefficients_km) != 3:
            raise ValueError("coefficients_km: expected three immutable coefficient blocks")
        if not isinstance(self.coefficients_km[0], tuple):
            raise ValueError("coefficients_km: expected immutable coefficient blocks")
        size = len(self.coefficients_km[0])
        if size == 0 or any(
            not isinstance(block, tuple)
            or len(block) != size
            or any(not isinstance(value, Fraction) for value in block)
            for block in self.coefficients_km
        ):
            raise ValueError("coefficients_km: expected equal nonempty Fraction blocks")

    @property
    def degree(self) -> int:
        """Return the position polynomial degree."""
        return len(self.coefficients_km[0]) - 1


def parse_record(words: Sequence[int | float]) -> Type2Record:
    """Read MID, RADIUS, X/Y/Z coefficients from one already-selected record."""
    if len(words) < 5 or (len(words) - 2) % 3:
        raise ValueError("record.words: expected MID/RADIUS and three equal nonempty blocks")
    values = tuple(_exact(value, f"record.words[{index}]") for index, value in enumerate(words))
    size = (len(values) - 2) // 3
    return Type2Record(
        values[0], values[1],
        (values[2:2 + size], values[2 + size:2 + 2 * size], values[2 + 2 * size:]),
    )


def _evaluate_record(record: Type2Record, epoch_tdb_s: Fraction) -> tuple[Vector3, Vector3, Vector3]:
    if not isinstance(epoch_tdb_s, Fraction):
        raise ValueError("epoch_tdb_s: expected exact Fraction")
    offset = epoch_tdb_s - record.midpoint_tdb_s
    if abs(offset) > record.radius_s:
        raise ValueError("epoch_tdb_s: outside selected record coverage")
    u = offset / record.radius_s
    basis = [Fraction(1)]
    derivative = [Fraction(0)]
    if record.degree:
        basis.append(u)
        derivative.append(Fraction(1))
    for _ in range(2, record.degree + 1):
        derivative.append(2 * basis[-1] + 2 * u * derivative[-1] - derivative[-2])
        basis.append(2 * u * basis[-1] - basis[-2])
    position: list[Fraction] = []
    velocity: list[Fraction] = []
    acceleration_bound: list[Fraction] = []
    for coefficients in record.coefficients_km:
        position.append(1000 * sum((c * t for c, t in zip(coefficients, basis, strict=True)), Fraction()))
        velocity.append(
            1000 * sum((c * d for c, d in zip(coefficients, derivative, strict=True)), Fraction())
            / record.radius_s
        )
        acceleration_bound.append(
            1000 * sum((abs(c) * k * k * (k * k - 1) for k, c in enumerate(coefficients)), Fraction())
            / (3 * record.radius_s * record.radius_s)
        )
    return (
        (position[0], position[1], position[2]),
        (velocity[0], velocity[1], velocity[2]),
        (acceleration_bound[0], acceleration_bound[1], acceleration_bound[2]),
    )


def evaluate_chain(
    records: Sequence[Type2Record], epoch_tdb_s: Fraction,
) -> tuple[Vector3, Vector3, Vector3]:
    """Sum one direct record or Moon->Earth plus Earth->SSB in exact SI.

    Selection, body IDs, J2000 frame and Type2 metadata are caller obligations.
    The acceleration bound applies throughout every selected record interval.
    """
    if len(records) not in (1, 2):
        raise ValueError("records: expected one direct or two centre-chain records")
    if any(not isinstance(record, Type2Record) for record in records):
        raise ValueError("records: expected Type2Record values")
    states = tuple(_evaluate_record(record, epoch_tdb_s) for record in records)
    components = [
        _vector([sum((state[kind][axis] for state in states), Fraction()) for axis in range(3)])
        for kind in range(3)
    ]
    return components[0], components[1], components[2]


def _vector(values: Sequence[Fraction]) -> Vector3:
    """Make the three-component scientific contract explicit to type checkers."""
    if len(values) != 3:
        raise ValueError("vector: expected three components")
    return values[0], values[1], values[2]


def _encoded(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _encoded_vector(values: Vector3) -> list[dict[str, str]]:
    return [_encoded(value) for value in values]


def _square_norm(values: Vector3) -> Fraction:
    return sum((value * value for value in values), Fraction())


def _norm(values: Vector3) -> float:
    try:
        result = math.sqrt(float(_square_norm(values)))
    except OverflowError as error:
        raise ValueError("computed norm: outside finite diagnostic range") from error
    if not math.isfinite(result):
        raise ValueError("computed norm: outside finite diagnostic range")
    return result


def assess(
    state_si: Sequence[int | float], records: Sequence[Type2Record], hi: float, lo: float,
) -> dict[str, Any]:
    """Compare native SI state at hi with exact polynomials at hi and hi+lo.

    Exact rational checks, rather than rounded displayed norms, determine passes.
    Preserve the source floor and binary64 correction as separate operands.
    """
    if len(state_si) != 6:
        raise ValueError("state_si: expected six SI components")
    native = tuple(_exact(value, f"state_si[{index}]") for index, value in enumerate(state_si))
    hi_exact = _exact(hi, "hi")
    lo_exact = _exact(lo, "lo")
    position, velocity, acceleration_bound = evaluate_chain(records, hi_exact)
    exact_position, _, _ = evaluate_chain(records, hi_exact + lo_exact)
    displacement: Vector3 = _vector([exact_position[i] - position[i] for i in range(3)])
    source_floor: Vector3 = _vector([native[i] - position[i] for i in range(3)])
    velocity_error: Vector3 = _vector([native[i + 3] - velocity[i] for i in range(3)])
    product: Vector3 = _vector([native[i + 3] * lo_exact for i in range(3)])
    correction_float = [float(state_si[i + 3]) * float(lo) for i in range(3)]
    correction: Vector3 = _vector([_exact(value, f"correction_m[{i}]") for i, value in enumerate(correction_float)])
    product_error: Vector3 = _vector([correction[i] - product[i] for i in range(3)])
    incremental_error: Vector3 = _vector([correction[i] - displacement[i] for i in range(3)])
    total_error: Vector3 = _vector([source_floor[i] + incremental_error[i] for i in range(3)])
    corrected_position = _vector([native[i] + correction[i] for i in range(3)])
    wrong_sign_error: Vector3 = _vector([-correction[i] - displacement[i] for i in range(3)])
    taylor_bound = _vector([
        abs(velocity_error[i]) * abs(lo_exact)
        + acceleration_bound[i] * lo_exact * lo_exact / 2
        + abs(product_error[i]) for i in range(3)
    ])
    checks = {
        "position_parity": _square_norm(source_floor) <= Fraction(1, 1000) ** 2,
        "velocity_parity": _square_norm(velocity_error) <= Fraction(1, 1_000_000) ** 2,
        "increment": _square_norm(incremental_error) <= Fraction(1, 10**12) ** 2,
        "taylor": all(abs(incremental_error[i]) <= taylor_bound[i] for i in range(3)),
    }
    exact_vectors = {
        "position_hi_m": position,
        "velocity_hi_m_s": velocity,
        "displacement_m": displacement,
        "source_position_floor_m": source_floor,
        "velocity_error_m_s": velocity_error,
        "correction_exact_product_m": product,
        "correction_rounding_error_m": product_error,
        "increment_error_m": incremental_error,
        "corrected_position_error_m": total_error,
        "corrected_position_m": corrected_position,
        "wrong_sign_increment_error_m": wrong_sign_error,
        "acceleration_bound_m_s2": acceleration_bound,
        "taylor_bound_m": taylor_bound,
    }
    return {
        "hi_tdb_s": float(hi), "lo_tdb_s": float(lo),
        "hi_hex": float(hi).hex(), "lo_hex": float(lo).hex(),
        "exact_epoch_tdb_s": _encoded(hi_exact + lo_exact),
        "correction_m": correction_float,
        "exact": {name: _encoded_vector(values) for name, values in exact_vectors.items()},
        "position_error_norm_m": _norm(source_floor),
        "velocity_error_norm_m_s": _norm(velocity_error),
        "increment_error_norm_m": _norm(incremental_error),
        "corrected_position_error_norm_m": _norm(total_error),
        "wrong_sign_increment_error_norm_m": _norm(wrong_sign_error),
        "wrong_sign_passed": _square_norm(wrong_sign_error) <= Fraction(1, 10**12) ** 2,
        "wrong_sign_increment_passed": _square_norm(wrong_sign_error) <= Fraction(1, 10**12) ** 2,
        "checks": checks, "passed": all(checks.values()),
    }
