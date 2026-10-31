"""Independent, stdlib-only research-profile decoder; not a general OEM importer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
import re
from typing import Iterator

READER_ID = "r1-oem-audit-v1"
PROFILE_ID = "ariadna-oem-kvn-v1"
_TIME = re.compile(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.(\d{6})", re.ASCII)
_NUMBER = re.compile(r"-?\d\.\d{15}E[+-](?:\d{2}|[1-9]\d{2})", re.ASCII)
_ID = re.compile(r"[a-f0-9]{64}")
_MAX_SI = Decimal("1.7976931348623157e308")


def require(condition: bool, field: str) -> None:
    if not condition:
        raise ValueError(field)


@dataclass(frozen=True, slots=True)
class Point:
    epoch_tdb_s: Decimal
    state_si: tuple[Decimal, ...]

    def __post_init__(self) -> None:
        require(type(self.epoch_tdb_s) is Decimal and self.epoch_tdb_s.is_finite(), "epoch_tdb_s")
        require(type(self.state_si) is tuple and len(self.state_si) == 6, "six-state shape")
        require(all(type(x) is Decimal and x.is_finite() and abs(x) <= _MAX_SI
                    for x in self.state_si), "finite SI state")


@dataclass(frozen=True, slots=True)
class Decoded:
    result_id: str
    qualification: str
    creation_utc: str
    points: tuple[Point, ...]


def calendar_seconds(text: str, *, utc: bool = False) -> Decimal:
    """Decode a calendar label; UTC is checked only for the creation header."""
    require(type(text) is str, "calendar text")
    if utc:
        require(text.endswith("Z"), "UTC creation_date Z")
        text = text[:-1]
    match = _TIME.fullmatch(text)
    require(match is not None, "calendar format")
    assert match is not None
    year, month, day, hour, minute, second, micros = map(int, match.groups())
    require(1900 <= year <= 2100, "calendar year")
    require(hour < 24 and minute < 60 and second < 60, "calendar clock")
    days = (date(year, month, day) - date(2000, 1, 1)).days
    with localcontext() as context:
        context.prec = 80
        return Decimal(days*86400 + hour*3600 + minute*60 + second - 43200) + Decimal(micros)/1000000


def _next(lines: Iterator[str]) -> str:
    try:
        return next(lines)
    except StopIteration as exc:
        raise ValueError("truncated header/metadata") from exc


def _value(lines: Iterator[str], key: str) -> str:
    line = _next(lines)
    require(line.startswith(key + " = "), f"{key}: missing, reordered or duplicate")
    value = line[len(key) + 3:]
    require(bool(value) and value == value.strip() and "=" not in value, f"{key}: value")
    return value


def read_bytes(payload: bytes) -> Decoded:
    """Strict candidate profile, including explicit unregistered-originator caveat."""
    require(type(payload) is bytes and 0 < len(payload) <= 2_000_000, "file byte limit")
    require(payload.endswith(b"\n"), "final LF")
    require(all(byte == 10 or 32 <= byte <= 126 for byte in payload), "ASCII/LF only")
    text_lines = payload.decode("ascii").splitlines()
    require(all(0 < len(line) <= 1024 for line in text_lines), "empty/long line")
    lines = iter(text_lines)
    require(_next(lines) == "CCSDS_OEM_VERS = 3.0", "OEM version")
    require(_next(lines) == "COMMENT PROFILE ariadna-oem-kvn-v1", "profile comment")
    require(_next(lines) == "COMMENT RESEARCH_ONLY NOT_FOR_OPERATIONAL_NAVIGATION", "research comment")
    require(_next(lines) == "COMMENT ORIGINATOR_UNREGISTERED NO_FULL_CCSDS_CONFORMANCE", "originator caveat")
    line = _next(lines)
    require(line.startswith("COMMENT QUALIFICATION "), "qualification comment prefix")
    qualification = line.removeprefix("COMMENT QUALIFICATION ")
    require(qualification in ("ideal-model-feasible", "unqualified"), "qualification comment")
    line = _next(lines)
    require(line.startswith("COMMENT RESULT_ID "), "result ID comment prefix")
    result_id = line.removeprefix("COMMENT RESULT_ID ")
    require(_ID.fullmatch(result_id) is not None, "result ID comment")
    creation = _value(lines, "CREATION_DATE")
    calendar_seconds(creation, utc=True)
    require(_value(lines, "ORIGINATOR") == "ARIADNA", "originator")
    require(_value(lines, "MESSAGE_ID") == result_id, "MESSAGE_ID binding")
    require(_next(lines) == "META_START", "META_START")
    for key, expected in (("OBJECT_NAME", "UNKNOWN"), ("OBJECT_ID", "UNKNOWN"),
                          ("CENTER_NAME", "SOLAR SYSTEM BARYCENTER"),
                          ("REF_FRAME", "ICRF"), ("TIME_SYSTEM", "TDB")):
        require(_value(lines, key) == expected, key)
    start = _value(lines, "START_TIME")
    stop = _value(lines, "STOP_TIME")
    calendar_seconds(start)
    calendar_seconds(stop)
    require(_next(lines) == "META_STOP", "META_STOP")
    points: list[Point] = []
    first, last = "", ""
    with localcontext() as context:
        context.prec = 80
        for line in lines:
            fields = line.split(" ")
            require(len(fields) == 7 and all(fields), "epoch plus six fields")
            require(len(points) < 1001, "point count limit")
            epoch = calendar_seconds(fields[0])
            require(not points or epoch > points[-1].epoch_tdb_s, "strictly increasing epochs")
            values: list[Decimal] = []
            for token in fields[1:]:
                require(_NUMBER.fullmatch(token) is not None, "16-digit scientific component")
                require(token.lstrip("-")[0] != "0" or Decimal(token) == 0, "normalized mantissa")
                require(Decimal(token) != 0 or token.endswith("E+00"), "normalized zero")
                values.append(Decimal(token) * 1000)
            points.append(Point(epoch, tuple(values)))
            first = first or fields[0]
            last = fields[0]
    require(2 <= len(points), "at least two nodes")
    require((start, stop) == (first, last), "metadata endpoint bounds")
    return Decoded(result_id, qualification, creation, tuple(points))


def compare(decoded: Decoded, expected: tuple[Point, ...]) -> dict[str, Decimal]:
    """Compare all reconstructed SI/TDB nodes; never qualify trajectory physics."""
    require(type(expected) is tuple and len(decoded.points) == len(expected) >= 2, "expected count")
    require(all(isinstance(point, Point) for point in expected), "expected Point")
    require(all(b.epoch_tdb_s > a.epoch_tdb_s for a, b in zip(expected, expected[1:])), "expected order")
    maximum_time = maximum_position = maximum_velocity = Decimal(0)
    with localcontext() as context:
        context.prec = 80
        for actual, reference in zip(decoded.points, expected):
            time_error = abs(actual.epoch_tdb_s - reference.epoch_tdb_s)
            difference = [a-b for a, b in zip(actual.state_si, reference.state_si)]
            position = sum(x*x for x in difference[:3]).sqrt()
            velocity = sum(x*x for x in difference[3:]).sqrt()
            require(time_error <= Decimal("0.000001"), "epoch error >1microsecond")
            require(position <= Decimal("0.001"), "position error >1mm")
            require(velocity <= Decimal("1e-9"), "velocity error >1e-9m/s")
            maximum_time = max(maximum_time, time_error)
            maximum_position = max(maximum_position, position)
            maximum_velocity = max(maximum_velocity, velocity)
    return {"epoch_error_s": maximum_time, "position_error_m": maximum_position,
            "velocity_error_m_s": maximum_velocity}


def verify(
    payload: bytes, expected: tuple[Point, ...], *, result_id: str, qualification: str,
) -> dict[str, Decimal]:
    """Bind decoded bytes to an independently supplied result identity/status/table."""
    require(type(result_id) is str and _ID.fullmatch(result_id) is not None, "expected result ID")
    require(qualification in ("ideal-model-feasible", "unqualified"), "expected qualification")
    decoded = read_bytes(payload)
    require(decoded.result_id == result_id, "paired result ID mismatch")
    require(decoded.qualification == qualification, "paired qualification mismatch")
    return compare(decoded, expected)
