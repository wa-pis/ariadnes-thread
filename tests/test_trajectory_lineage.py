"""Exact lineage of the four retained nominal controls, not mission safety."""

from fractions import Fraction
import json
import math
from pathlib import Path

import pytest


def _encode_error_pair(values: tuple[Fraction, Fraction]) -> list[list[str]]:
    """Hex avoids Python's decimal-digit ceiling without relaxing it globally."""
    return [[hex(value.numerator), hex(value.denominator)] for value in values]


def _decode_error_pair(values: list[list[str]]) -> tuple[Fraction, ...]:
    return tuple(Fraction(int(numerator, 16), int(denominator, 16)) for numerator, denominator in values)


def _check_nominal_lineage(report: dict, endpoint: dict) -> None:
    rows = report["arcs"]
    assert len(rows) == report["accepted_nominal_arcs"] == 4
    assert report["charged_inventory_arcs"] == 13
    assert report["origin"] == endpoint["origin"] == "SSB"
    assert report["orientation"] == endpoint["orientation"] == "J2000"
    assert report["time_scale"] == endpoint["time_scale"] == "TDB seconds since J2000"
    assert report["model_id"] == endpoint["model_id"]
    previous = None
    previous_ordinal = 0
    for row, duration in zip(rows, (Fraction(1, 64), Fraction(1, 64), Fraction(1, 32), Fraction(1, 16)), strict=True):
        assert Fraction(row["end_epoch_tdb_s"])-Fraction(row["start_epoch_tdb_s"]) == duration
        initial, final = row["initial_state_m_m_s_kg"], row["terminal_state_m_m_s_kg"]
        assert len(initial) == len(final) == 7
        assert all(type(value) is float and math.isfinite(value) for value in initial+final)
        assert initial[6] == final[6] == endpoint["initial_state_m_m_s_kg"][6]
        incoming, outgoing = [_decode_error_pair(row[key]) for key in ("incoming_error_exact_m_m_s", "outgoing_error_exact_m_m_s")]
        assert len(incoming) == len(outgoing) == 2
        assert all(0 <= a <= b <= gate for a, b, gate in zip(incoming, outgoing, (Fraction("0.001"), Fraction("0.000001")), strict=True))
        ordinal = row["native_arc_ordinal"]
        assert type(ordinal) is int and previous_ordinal < ordinal <= report["charged_inventory_arcs"]
        previous_ordinal = ordinal
        if previous is None:
            assert incoming == (0, 0)
        else:
            assert previous["end_epoch_tdb_s"] == row["start_epoch_tdb_s"]
            assert previous["terminal_state_m_m_s_kg"] == initial
            assert _decode_error_pair(previous["outgoing_error_exact_m_m_s"]) == incoming
        previous = row
    assert Fraction(rows[-1]["end_epoch_tdb_s"])-Fraction(rows[0]["start_epoch_tdb_s"]) == Fraction(1, 8)
    for key in ("start_epoch_tdb_s", "end_epoch_tdb_s", "initial_state_m_m_s_kg", "terminal_state_m_m_s_kg"):
        assert rows[-1][key] == endpoint[key]
    last_incoming = _decode_error_pair(rows[-1]["incoming_error_exact_m_m_s"])
    assert [math.nextafter(float(value), math.inf) if value else 0.0 for value in last_incoming] == endpoint["incoming_error_m_m_s"]
    # Last row uses the old shifted reference; the fresh reference is separate.
    assert all(a <= Fraction(b) for a, b in zip(_decode_error_pair(rows[-1]["outgoing_error_exact_m_m_s"]), endpoint["outgoing_error_m_m_s"], strict=True))


def _reports() -> tuple[dict, dict]:
    directory = Path(__file__).with_name("data")
    return tuple(json.loads((directory / f"m3_{name}.json").read_text())[name]
                 for name in ("nominal_four_arc_lineage", "fresh_endpoint_binding"))


def test_nominal_lineage_replays_all_three_handoffs() -> None:
    _check_nominal_lineage(*_reports())


@pytest.mark.parametrize("join", [0, 1, 2])
@pytest.mark.parametrize("component", [0, 3, 6])
def test_nominal_lineage_rejects_changed_predecessor_state(join: int, component: int) -> None:
    report, endpoint = _reports()
    report["arcs"][join]["terminal_state_m_m_s_kg"][component] += 1.0
    with pytest.raises(AssertionError):
        _check_nominal_lineage(report, endpoint)


@pytest.mark.parametrize("join", [0, 1, 2])
@pytest.mark.parametrize("field", ["end_epoch_tdb_s", "outgoing_error_exact_m_m_s"])
def test_nominal_lineage_rejects_changed_predecessor_epoch_or_error(join: int, field: str) -> None:
    report, endpoint = _reports()
    row = report["arcs"][join]
    if field == "end_epoch_tdb_s":
        row[field] += 1.0
    else:
        values = _decode_error_pair(row[field])
        row[field] = _encode_error_pair((values[0]+Fraction(1, 10**9), values[1]))
    with pytest.raises(AssertionError):
        _check_nominal_lineage(report, endpoint)


def test_nominal_lineage_does_not_replace_charged_count_with_accepted_count() -> None:
    report, endpoint = _reports()
    report["charged_inventory_arcs"] = 4
    with pytest.raises(AssertionError):
        _check_nominal_lineage(report, endpoint)


def test_exact_error_hex_round_trip_exceeds_decimal_digit_limit() -> None:
    values = (Fraction(10**5000+1, 10**5010+3), Fraction(0))
    assert _decode_error_pair(_encode_error_pair(values)) == values
