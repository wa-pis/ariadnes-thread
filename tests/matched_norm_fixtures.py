"""Full fabricated trace pack with independent, local Decimal96 norm snapshots."""

from copy import deepcopy
from decimal import (
    ROUND_CEILING, ROUND_FLOOR, Context, Decimal, DivisionByZero,
    InvalidOperation, Overflow,
)
from hashlib import sha256
from pathlib import Path
from typing import Any

from lineage_fixtures import (
    ART, ROOT as ROOT, ROLES, fabricated_archive as lineage_archive,
    rechain as lineage_rechain, reseal, wire,
)

SCOPE = "artificial-matched-norm"
CANDIDATE = "artificial-matched-norm-case"
REFERENCE = sha256(b"independently fabricated matched-norm qualification reference").hexdigest()
type Row = dict[str, Any]
type Vector = list[dict[str, str]]


def contract() -> Row:
    """Load design metadata only; retained numerical records are never read."""
    import json

    return json.loads((ART / "0234-matched-norm-contract.json").read_bytes())


def selected_norm_events(row: Row) -> list[tuple[str, Row, Row]]:
    """Find only the three contract roles by direct structural child ordinals."""
    events = row["trace"]["events"]
    calls = [event for event in events if event["event"] == "call"]
    bounds = next(event for event in calls if event["stage"] == "bounds")
    reverse = next(event for event in calls if event["stage"] == "_reverse" and event["parent"] == bounds["call"])
    selected = []
    for role, parent, ordinal in (
        ("impulse-squared", bounds["call"], 0),
        ("radius-squared", reverse["call"], 1),
        ("angular-momentum-squared", reverse["call"], 4),
    ):
        call = [event for event in calls if event["stage"] == "_norm2" and event["parent"] == parent][ordinal]
        returned = next(event for event in events if event["call"] == call["call"] and event["event"] == "return")
        selected.append((role, call, returned))
    return selected


def _interval(lo: str, hi: str | None = None) -> dict[str, str]:
    return dict(lo=lo, hi=lo if hi is None else hi)


def fabricated_vector(index: int) -> Vector:
    """Cover signs, degeneracy, exponents and precision using invented operands."""
    tail = "1234567890" * 9 + "12345"
    lo, hi = "1." + tail, "2." + tail
    negative_lo, negative_hi = "-" + hi, "-" + lo
    cases = (
        [_interval("-2", "3"), _interval("-4", "-1"), _interval("0", "5")],
        [_interval("-0", "0.00"), _interval("0E-96", "-0E+12"), _interval("-0.000", "0")],
        [_interval("3"), _interval("-4"), _interval("-0", "0.0")],
        [_interval(lo, hi), _interval(negative_lo, negative_hi), _interval("0", lo)],
        [_interval(lo + "E+120", hi + "E+120"), _interval("-3E+119", "4E+119"), _interval("0E+120")],
        [_interval(lo + "E-90", hi + "E-90"), _interval("-3E-91", "4E-91"), _interval("0E-90")],
        [_interval("-1", "0"), _interval("0", "2"), _interval("-3", "0.00")],
        [_interval("-5", "-2"), _interval("-7", "-6"), _interval("1", "2")],
        [_interval("1." + "0" * 95 + "1"), _interval("0"), _interval("0")],
        [_interval("-1." + "0" * 95 + "1"), _interval("-0"), _interval("0.00")],
        [_interval("1E+200", "2E+200"), _interval("-2E-200", "3E-200"), _interval("4E-50", "5E-50")],
        [_interval(lo), _interval(negative_hi), _interval(hi)],
    )
    vector = deepcopy(cases[index % len(cases)])
    for interval in vector:
        for endpoint, raw in interval.items():
            mantissa, marker, exponent = raw.partition("E")
            digits = sum(character.isdigit() for character in mantissa)
            if digits < 96:
                if "." not in mantissa:
                    mantissa += "."
                mantissa += "0" * (96 - digits)
            interval[endpoint] = mantissa + (marker + exponent if marker else "")
    return vector


def direct_decimal_norm(vector: Vector, *, independent: bool) -> dict[str, str]:
    """Independent fixture oracle: explicit Decimal primitives, no private core imports."""
    floor = Context(prec=96, rounding=ROUND_FLOOR, Emin=-999999, Emax=999999,
                    capitals=1, clamp=0, traps=[InvalidOperation, DivisionByZero, Overflow])
    ceiling = Context(prec=96, rounding=ROUND_CEILING, Emin=-999999, Emax=999999,
                      capitals=1, clamp=0, traps=[InvalidOperation, DivisionByZero, Overflow])
    pieces = []
    for value in vector:
        lo, hi = Decimal(value["lo"]), Decimal(value["hi"])
        if independent:
            corners = [(left, right) for left in (lo, hi) for right in (lo, hi)]
            lower = min(floor.multiply(left, right) for left, right in corners)
            upper = max(ceiling.multiply(left, right) for left, right in corners)
        else:
            a = Decimal(0) if lo <= 0 <= hi else min(floor.abs(lo), floor.abs(hi))
            b = max(ceiling.abs(lo), ceiling.abs(hi))
            lower, upper = floor.multiply(a, a), ceiling.multiply(b, b)
        pieces.append((lower, upper))
    lower = floor.add(floor.add(pieces[0][0], pieces[1][0]), pieces[2][0])
    upper = ceiling.add(ceiling.add(pieces[0][1], pieces[1][1]), pieces[2][1])
    return dict(lo=str(max(Decimal(0), lower) if independent else lower), hi=str(upper))


def rechain(archive: Row) -> None:
    """Refresh artificial trace seals, descriptor snapshots and seven-record hashes."""
    rows = archive["report"]["rows"]
    for row in rows:
        reseal(row["trace"])
    archive["report"]["saved_endpoint_descriptors"] = [
        dict(pointer=f"/report/rows/{index}/trace/events/{event['index']}/fields/{field}",
             stage=event["stage"], field=field, endpoint_kind="saved-canonical-interval",
             lo=value["lo"], hi=value["hi"])
        for index, row in enumerate(rows) for event in row["trace"]["events"]
        for field, value in event["fields"].items()
    ]
    lineage_rechain(archive)
    archive["manifest"]["scope"] = SCOPE


def fabricated_archive() -> Row:
    """Reuse full artificial structure; replace only selected local norm snapshots."""
    archive = lineage_archive()
    for role in ROLES:
        record = archive[role]
        for key, value in (("scope", SCOPE), ("candidate_id", CANDIDATE), ("reference_sha256", REFERENCE)):
            if key in record:
                record[key] = value
    archive["_context"]["scope"] = SCOPE
    for row_index, row in enumerate(archive["report"]["rows"]):
        for role_index, (_, call, returned) in enumerate(selected_norm_events(row)):
            vector = fabricated_vector(row_index * 3 + role_index)
            for component, interval in enumerate(vector):
                call["fields"][f"v[{component}]"] = deepcopy(interval)
                returned["fields"][f"v[{component}]"] = deepcopy(interval)
            returned["fields"]["return"] = direct_decimal_norm(vector, independent=row["independent"])
    archive["report"]["fixture_semantics"] = (
        "All source observations are fabricated qualification data. Only the selected72 local norm snapshots "
        "are mathematically constructed with an independent test Decimal96 helper; other saved-looking values "
        "and historical counters remain fabricated metadata. No retained numerical record, scientific producer, "
        "orbital/geometry/root/mass/integration/SPICE helper or private evaluator was used. Distinct pointer "
        "origins remain distinct even when fabricated values repeat."
    )
    rechain(archive)
    return archive


def write_artificial_pack(folder: Path) -> Row:
    """Write seven exclusive artificial records; historical source is only hashed as bytes."""
    archive = fabricated_archive()
    folder.mkdir()
    inputs, pins = {}, {}
    for role in ROLES:
        path = folder / (role + ".json")
        raw = wire(archive[role])
        path.write_bytes(raw)
        inputs[role] = str(path.absolute())
        pins[role] = dict(sha256=sha256(raw).hexdigest(), bytes=len(raw))
    return dict(scope=SCOPE, inputs=inputs, pins=pins, expected_events=1248,
                reference_sha256=REFERENCE, candidate_id=CANDIDATE,
                completion_sha256=pins["completion"]["sha256"])
