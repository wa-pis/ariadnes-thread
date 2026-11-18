"""Compare the exact three saved R5.59f nodes with their R5.59i point replays."""

from fractions import Fraction
import math
from types import ModuleType
from typing import Any

type Row = dict[str, Any]

SIGNS = ("positive", "negative")
_STATE_GATES = {"relative_position_m": 0.001, "relative_velocity_m_s": 1e-6,
                "ssb_position_m": 0.001, "ssb_velocity_m_s": 1e-6}
_ROOT_GATES = {"asymptote_m_s": 1e-6, "impulse_m_s": 1e-6, "velocity_m_s": 1e-6,
               "tnw_m_s": 1e-6, "radius_m": 0.001}
_MASS_GATES = {"duration_s": 1e-6, "mass_kg": 1e-8}


def _need(ok: object, reason: str) -> None:
    if not ok:
        raise ValueError(f"phase anchor: {reason}")


def _gates(values: Row, expected: dict[str, float], reader: ModuleType) -> None:
    _need(isinstance(values, dict) and set(values) == set(expected)
          and all(0 <= reader._number(values[name]) <= limit for name, limit in expected.items()),
          "discrepancy gates")


def _precise(raw: object, reader: ModuleType) -> tuple[Fraction, ...]:
    _need(isinstance(raw, list) and len(raw) == 6, "independent state shape")
    return tuple(Fraction(reader._decimal(x)) for x in raw)


def _states(previous: Row, current: Row, reader: ModuleType) -> None:
    for label in ("relative_si", "ssb_si"):
        old, new = (reader._vector(row[label], 6) for row in (previous, current))
        _need(math.dist(old[:3], new[:3]) <= 0.001 and math.dist(old[3:], new[3:]) <= 1e-6,
              f"{label} mismatch")
    exact_old, exact_new = (_precise(row["independent_relative_si"], reader) for row in (previous, current))
    diff = tuple(a-b for a, b in zip(exact_old, exact_new, strict=True))
    for values, limit in ((diff[:3], Fraction("0.001")), (diff[3:], Fraction("0.000001"))):
        _need(sum(d*d for d in values) <= limit*limit, "independent state mismatch")
    for row in (previous, current):
        _gates(row["discrepancies"], _STATE_GATES, reader)


def _tnw(row: Row, reader: ModuleType) -> tuple[float, float, float]:
    a, e = reader._vector(row["angles_rad"], 2)
    _need(-math.pi <= a < math.pi and -math.pi/2 <= e <= math.pi/2, "TNW angle domain")
    speed = math.hypot(*reader._vector(row["impulse_m_s"], 3))
    _need(speed > 0 and math.isfinite(speed), "impulse speed domain")
    in_plane = speed*math.cos(e)
    return in_plane*math.cos(a), in_plane*math.sin(a), speed*math.sin(e)


def _root(previous: Row, current: Row, reader: ModuleType) -> None:
    reason = previous["reason"]
    _need(reason == current["reason"] and reason in (None, "guard", "degenerate"), "signed root disposition")
    if reason == "degenerate":
        _need(set(previous) == set(current) == {"reason"}, "degenerate root evidence")
        return
    _need(previous["radial"] == current["radial"] and previous["radial"] in ("inward", "outward", "turning"),
          "radial classification")
    radii = [reader._number(row["minimum_radius_m"]) for row in (previous, current)]
    _need(min(radii) > 0 and abs(radii[0]-radii[1]) <= 0.001, "incoming-leg radius mismatch")
    for name in ("impulse_m_s", "hyperbolic_velocity_m_s", "reconstructed_excess_m_s"):
        vectors = (reader._vector(row[name], 3) for row in (previous, current))
        _need(math.dist(*vectors) <= 1e-6, f"{name} mismatch")
    speed = [Fraction(reader._decimal(row["independent_speed_m_s"])) for row in (previous, current)]
    _need(min(speed) > 0 and abs(speed[0]-speed[1]) <= Fraction("0.000001"), "independent impulse mismatch")
    _need(math.dist(_tnw(previous, reader), _tnw(current, reader)) <= 1e-6, "TNW kick mismatch")
    for row in (previous, current):
        _gates(row["discrepancies"], _ROOT_GATES, reader)


def _pairs(previous: Row, current: Row, degree: int, reader: ModuleType) -> None:
    expected = [["positive", sign] for sign in SIGNS if previous["branches"][sign]["reason"] is None]
    for row in (previous, current):
        _need(isinstance(row["pairs"], list) and [pair["roots"] for pair in row["pairs"]] == expected,
              "signed pair inventory")
    for old, new in zip(previous["pairs"], current["pairs"], strict=True):
        _need(type(old["index"]) is int and old["index"] == degree, "saved pair phase")
        for pair in (old, new):
            _need(pair["reason"] == "commanded-dry-floor"
                  and all(pair.get(key) is None for key in ("command_words", "ledgers", "ideal_end_masses_kg")),
                  "original commanded dry-floor refusal")
            _gates(pair["independent_mass_discrepancies"], _MASS_GATES, reader)
        low = [reader._number(pair["total_delta_v_m_s"]) for pair in (old, new)]
        high = [Fraction(reader._decimal(pair["oracle_total_delta_v_m_s"])) for pair in (old, new)]
        _need(min(low) > 0 and abs(low[0]-low[1]) <= 1e-6
              and min(high) > 0 and abs(high[0]-high[1]) <= Fraction("0.000001"), "paired cost mismatch")


def verify_anchor(previous: Row, current: Row, degree: int, reader: ModuleType) -> None:
    """Enforce identity or the original SI gates; neither select nor retarget a node."""
    try:
        _need(type(degree) is int and degree in (150, 151, 152), "unexpected anchor phase")
        angle = (math.tau*degree/360).hex()
        _need(type(previous["index"]) is int and previous["index"] == degree
              and current["phase_deg"] == str(degree)
              and current["angle_word"] == previous["angle_word"] == angle, "phase identity")
        _need(current["eligible"] == [] and current["unresolved"] is False, "eligible or unresolved replay")
        _states(previous, current, reader)
        _need(set(previous["branches"]) == set(current["branches"]) == set(SIGNS), "signed root inventory")
        for sign in SIGNS:
            _root(previous["branches"][sign], current["branches"][sign], reader)
        _pairs(previous, current, degree, reader)
    except (KeyError, TypeError, ArithmeticError, AttributeError) as exc:
        raise ValueError("phase anchor: malformed evidence") from exc
