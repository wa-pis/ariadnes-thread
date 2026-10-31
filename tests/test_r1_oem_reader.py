"""Independent-reader preparation only: no writer or native trajectory calls."""

from __future__ import annotations

import builtins
from decimal import Decimal, localcontext
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs/adr/experiments/0124-oem-reader.py"
FIXTURES = ROOT / "tests/fixtures/r1_oem"
spec = importlib.util.spec_from_file_location("r1_oem_reader", SCRIPT)
assert spec is not None and spec.loader is not None
reader = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reader
spec.loader.exec_module(reader)
PAYLOAD = (FIXTURES / "asymmetric.oem").read_bytes()
TABLE = json.loads((FIXTURES / "expected-si.json").read_text())["states"]


@pytest.fixture(autouse=True)
def no_scientific_or_writer_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    original = builtins.__import__

    def guarded(name: str, *args: Any, **kwargs: Any) -> Any:
        assert not name.startswith(("space_nav", "tudatpy", "spiceypy", "numpy", "scipy")), name
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)


def expected_points() -> tuple[Any, ...]:
    return tuple(reader.Point(Decimal(row[0]), tuple(map(Decimal, row[1:]))) for row in TABLE)


def test_hand_authored_si_values_and_metadata() -> None:
    decoded = reader.read_bytes(PAYLOAD)
    assert decoded.points == expected_points()
    assert decoded.qualification == "unqualified"
    assert decoded.result_id == "0123456789abcdef" * 4
    assert decoded.creation_utc == "2026-10-31T00:00:00.000000Z"
    assert reader.compare(decoded, expected_points()) == {
        "epoch_error_s": Decimal(0), "position_error_m": Decimal(0), "velocity_error_m_s": Decimal(0)}


@pytest.mark.parametrize(("text", "seconds"), [
    ("2000-01-01T12:00:00.000000", "0"),
    ("2000-01-01T11:59:59.999999", "-0.000001"),
    ("2000-01-01T00:00:00.000000", "-43200"),
    ("2000-01-02T12:00:00.000000", "86400"),
    ("2000-02-29T12:00:00.000000", "5097600"),
    ("2000-03-01T12:00:00.000000", "5184000"),
    ("1900-01-01T00:00:00.000000", "-3155716800"),
])
def test_independent_calendar_anchors(text: str, seconds: str) -> None:
    with localcontext() as context:
        context.prec = 6
        actual = reader.calendar_seconds(text)
    assert actual == Decimal(seconds)


@pytest.mark.parametrize("text", ["1900-02-29T00:00:00.000000", "2100-02-29T00:00:00.000000",
    "1899-12-31T23:59:59.999999", "2101-01-01T00:00:00.000000", "2000-13-01T00:00:00.000000",
    "2000-01-01T24:00:00.000000", "2000-01-01T12:60:00.000000", "2000-01-01T12:00:60.000000",
    "2000-01-01T12:00:00.000000Z", "2000-01-01T12:00:00.000000+00:00", "2000-001T12:00:00",
    "2000-01-01T12:00:00.00000", "２０００-01-01T12:00:00.000000", "NaN", ""])
def test_reject_calendar(text: str) -> None:
    with pytest.raises(ValueError):
        reader.calendar_seconds(text)


@pytest.mark.parametrize(("old", "new"), [
    (b"CCSDS_OEM_VERS = 3.0", b"CCSDS_OEM_VERS = 2.0"),
    (b"COMMENT PROFILE ariadna-oem-kvn-v1", b"COMMENT PROFILE future"),
    (b"COMMENT RESEARCH_ONLY NOT_FOR_OPERATIONAL_NAVIGATION", b"COMMENT operational"),
    (b"COMMENT ORIGINATOR_UNREGISTERED NO_FULL_CCSDS_CONFORMANCE", b"COMMENT certified"),
    (b"COMMENT QUALIFICATION unqualified", b"unqualified"),
    (b"COMMENT QUALIFICATION unqualified", b"COMMENT QUALIFICATION mission-qualified"),
    (b"COMMENT RESULT_ID ", b""),
    (b"ORIGINATOR = ARIADNA", b"ORIGINATOR = JPL"),
    (b"MESSAGE_ID = 0123", b"MESSAGE_ID = 9999"),
    (b"OBJECT_ID = UNKNOWN", b"OBJECT_ID = 2031-001A"),
    (b"CENTER_NAME = SOLAR SYSTEM BARYCENTER", b"CENTER_NAME = SUN"),
    (b"REF_FRAME = ICRF", b"REF_FRAME = EME2000"),
    (b"TIME_SYSTEM = TDB", b"TIME_SYSTEM = UTC"),
    (b"META_START", b"META_START\nCOVARIANCE_START"),
    (b"META_STOP", b"INTERPOLATION = LAGRANGE\nMETA_STOP"),
    (b"OBJECT_NAME = UNKNOWN", b"OBJECT_NAME = UNKNOWN\nOBJECT_NAME = UNKNOWN"),
    (b"OBJECT_NAME = UNKNOWN", b"OBJECT_NAME = UNKNOWN\nCOMMENT injected"),
    (b"OBJECT_NAME = UNKNOWN", b"OBJECT_NAME ="),
    (b"2000-01-02T12:00:00.000000\nMETA_STOP", b"2000-01-03T12:00:00.000000\nMETA_STOP"),
    (b"1.234567890123456E+05", b"NaN"),
    (b"1.234567890123456E+05", b"Infinity"),
    (b"1.234567890123456E+05", b"1.2345678901234567E+05"),
    (b"1.234567890123456E+05", b"0.123456789012345E+06"),
    (b"1.234567890123456E+05", b"1.234567890123456e+05"),
    (b"1.234567890123456E+05", b"1.234567890123456E+309"),
    (b"1.234567890123456E+05", b"1.234567890123456E+05 [km]"),
    (b"1.234567890123456E+05", b"1.234567890123456E+05 0"),
    (b"2000-01-01T11:59:59.999999 1.", b"2000-01-01T12:00:00.000000 1."),
    (b"CREATION_DATE = 2026-10-31T00:00:00.000000Z", b"CREATION_DATE = 2026-10-31T00:00:00.000000"),
    (b"\n", b"\r\n"), (b"\n", b"\n\n"), (b" = ", b"\t= "),
])
def test_reject_corrupt_or_unsupported_profile(old: bytes, new: bytes) -> None:
    assert old in PAYLOAD
    with pytest.raises(ValueError):
        reader.read_bytes(PAYLOAD.replace(old, new))


@pytest.mark.parametrize("payload", [b"", PAYLOAD[:-1], PAYLOAD[:500], PAYLOAD+b"META_START\n",
    PAYLOAD+b"\xff\n", b"X"*2_000_001, PAYLOAD.replace(b"ARIADNA", b"A"*1025)])
def test_file_limits_and_truncation(payload: bytes) -> None:
    with pytest.raises(ValueError):
        reader.read_bytes(payload)


@pytest.mark.parametrize(("old", "new"), [
    (b"1.234567890123456E+05", b"1.234567890123456E+08"),
    (b"1.234567890123456E+05 -2.345678901234567E+05", b"-2.345678901234567E+05 1.234567890123456E+05"),
])
def test_false_units_or_axes_parse_but_fail_physical_comparison(old: bytes, new: bytes) -> None:
    decoded = reader.read_bytes(PAYLOAD.replace(old, new))
    with pytest.raises(ValueError, match="position error"):
        reader.compare(decoded, expected_points())


def test_false_time_label_requires_expected_physical_epochs() -> None:
    # Numerals can be valid TDB syntax while actually copied from UTC. Syntax cannot know.
    decoded = reader.read_bytes(PAYLOAD)
    expected = tuple(reader.Point(p.epoch_tdb_s+Decimal(60), p.state_si) for p in expected_points())
    with pytest.raises(ValueError, match="epoch error"):
        reader.compare(decoded, expected)


@pytest.mark.parametrize(("field", "value", "passes"), [
    (0, "0.000001", True), (0, "0.000001000001", False),
    (1, "0.001", True), (1, "0.001000000001", False),
    (4, "1e-9", True), (4, "1.000000001e-9", False),
])
def test_inclusive_time_position_velocity_gates(field: int, value: str, passes: bool) -> None:
    expected = list(expected_points())
    point = expected[1]
    if field == 0:
        expected[1] = reader.Point(Decimal(value), point.state_si)
    else:
        state = list(point.state_si)
        state[field-1] += Decimal(value)
        expected[1] = reader.Point(point.epoch_tdb_s, tuple(state))
    if passes:
        reader.compare(reader.read_bytes(PAYLOAD), tuple(expected))
    else:
        with pytest.raises(ValueError, match="error"):
            reader.compare(reader.read_bytes(PAYLOAD), tuple(expected))


def test_euclidean_not_componentwise_and_expected_count() -> None:
    expected = list(expected_points())
    state = list(expected[1].state_si)
    state[0] += Decimal("0.0008")
    state[1] += Decimal("0.0008")
    expected[1] = reader.Point(Decimal(0), tuple(state))
    with pytest.raises(ValueError, match="position error"):
        reader.compare(reader.read_bytes(PAYLOAD), tuple(expected))
    with pytest.raises(ValueError, match="count"):
        reader.compare(reader.read_bytes(PAYLOAD), expected_points()[:2])


@pytest.mark.parametrize("seconds", ["-0.0000005", "0.0000005", "0.000000499999"])
def test_expected_rounding_into_epoch_zero(seconds: str) -> None:
    expected = list(expected_points())
    expected[1] = reader.Point(Decimal(seconds), expected[1].state_si)
    reader.compare(reader.read_bytes(PAYLOAD), tuple(expected))


@pytest.mark.parametrize("state", [(Decimal(0),)*5, (True,)*6, (Decimal("NaN"),)*6,
                                  (Decimal("Infinity"),)*6, (Decimal("1e309"),)*6])
def test_expected_boundary_rejection(state: tuple[Any, ...]) -> None:
    with pytest.raises(ValueError):
        reader.Point(Decimal(0), state)


def test_reader_has_no_production_or_scientific_imports() -> None:
    import ast

    tree = ast.parse(SCRIPT.read_text())
    allowed = {"__future__", "dataclasses", "datetime", "decimal", "re", "typing"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name in allowed for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module in allowed


def test_binding_and_declared_qualification_are_not_promoted() -> None:
    kwargs = {"result_id": "0123456789abcdef"*4, "qualification": "unqualified"}
    assert reader.verify(PAYLOAD, expected_points(), **kwargs)["position_error_m"] == 0
    for key, value in (("result_id", "0"*64), ("qualification", "ideal-model-feasible"),
                       ("qualification", "mission-qualified"), ("result_id", "")):
        with pytest.raises(ValueError):
            reader.verify(PAYLOAD, expected_points(), **(kwargs | {key: value}))
    feasible = PAYLOAD.replace(b"QUALIFICATION unqualified", b"QUALIFICATION ideal-model-feasible")
    assert reader.read_bytes(feasible).qualification == "ideal-model-feasible"
    with pytest.raises(ValueError, match="qualification"):
        reader.verify(feasible, expected_points(), **kwargs)


def test_leap_day_and_carry_acceptance_table() -> None:
    payload = (FIXTURES / "leap-day.oem").read_bytes()
    # Expected times are hand arithmetic: day59 at midnight = 59*86400-43200.
    states = expected_points()[1:]
    expected = (reader.Point(Decimal("5140799.999999"), states[0].state_si),
                reader.Point(Decimal("5140800"), states[1].state_si))
    assert reader.compare(reader.read_bytes(payload), expected)["epoch_error_s"] == 0
    # A future half-even writer rounds this lower-side tie up across midnight.
    carry = (expected[0], reader.Point(Decimal("5140799.9999995"), states[1].state_si))
    assert reader.compare(reader.read_bytes(payload), carry)["epoch_error_s"] == Decimal("0.0000005")


@pytest.mark.parametrize("count", [1, 2, 1001, 1002])
def test_point_count_bounds(count: int) -> None:
    # Test-only fixed-state records exercise parser limits, not a trajectory exporter.
    tags = [f"2000-01-02T00:{i//60:02}:{i%60:02}.000000" for i in range(count)]
    header = PAYLOAD.split(b"META_STOP\n")[0].decode()
    header = header.replace("2000-01-01T11:59:59.999999", tags[0])
    header = header.replace("2000-01-02T12:00:00.000000", tags[-1])
    values = " ".join(["0.000000000000000E+00"]*6)
    payload = (header+"META_STOP\n"+"".join(tag+" "+values+"\n" for tag in tags)).encode()
    if 2 <= count <= 1001:
        assert len(reader.read_bytes(payload).points) == count
    else:
        with pytest.raises(ValueError, match="count|two nodes"):
            reader.read_bytes(payload)


def test_retained_reference_can_supply_expected_table_without_native_calls() -> None:
    from hashlib import sha256

    path = ROOT / "docs/adr/experiments/0119-m2-reference.json"
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == "3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0"
    states = json.loads(raw)["runs"][0]["states"]
    assert len(states) == 121
    expected = []
    for state in states:
        assert state["origin"] == "SSB" and state["orientation"] == "J2000"
        expected.append(reader.Point(Decimal.from_float(state["epoch_tdb_s"]), tuple(
            Decimal.from_float(x) for x in state["position_m"]+state["velocity_m_s"])))
    assert all(b.epoch_tdb_s > a.epoch_tdb_s for a, b in zip(expected, expected[1:]))
    # No OEM generated here: the frozen table is ready for later writer acceptance.
