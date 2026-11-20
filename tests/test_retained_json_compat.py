"""Qualify the historical JSON encoding repair on fabricated archives only."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from runpy import run_path
from types import ModuleType
from typing import Any

import pytest

ART = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
HELPER = Path(__file__).with_name("test_retained_bound_trace.py")
ROLES = (
    "grid_attempt", "grid_report", "grid_receipt", "grid_audit",
    "study_attempt", "study_report", "study_receipt", "study_completion", "study_audit",
)
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
type Row = dict[str, Any]
type Methods = dict[str, ModuleType]


def _wire(row: Any, *, form: str = "compact") -> bytes:
    options: Row = dict(sort_keys=True, allow_nan=False)
    if form == "compact":
        options["separators"] = (",", ":")
    elif form == "indent":
        options["indent"] = 2
    else:
        assert form == "spaced"
    return (json.dumps(row, **options) + "\n").encode()


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _historical_profile(root: Path, methods: Methods, *, case: str = "witness") -> Row:
    """Apply the historical encoding profile to the existing artificial fixture."""
    profile = run_path(str(HELPER))["build_profile"](root, methods, case=case)
    records = {role: json.loads(path.read_bytes()) for role, path in profile["inputs"].items()}

    def put(role: str) -> None:
        form = "indent" if role == "grid_audit" else "spaced" if role == "study_audit" else "compact"
        path = profile["inputs"][role]
        path.write_bytes(_wire(records[role], form=form))
        profile["pins"][role] = _digest(path)

    put("grid_audit")
    grid_pins = {name: profile["pins"]["grid_" + name.removesuffix(".json")]
                 for name in FILES[:3]} | {"audit.json": profile["pins"]["grid_audit"]}
    source_bytes = sum(profile["inputs"][role].stat().st_size for role in ROLES[:4])
    for role in ("study_attempt", "study_report", "study_receipt", "study_audit"):
        records[role]["source_pins"] = grid_pins
        records[role]["source_bytes"] = source_bytes
    put("study_attempt")
    for role in ("study_report", "study_receipt", "study_audit"):
        records[role]["attempt_sha256"] = profile["pins"]["study_attempt"]
    put("study_report")
    records["study_receipt"]["report_sha256"] = profile["pins"]["study_report"]
    put("study_receipt")
    records["study_completion"]["receipt_sha256"] = profile["pins"]["study_receipt"]
    put("study_completion")
    put("study_audit")
    return profile


@pytest.fixture(scope="module")
def runner() -> Row:
    return run_path(str(ART / "0227-retained-trace.py"))


@pytest.fixture(scope="module")
def methods(runner: Row) -> Methods:
    return runner["_methods"]()


@pytest.mark.parametrize("case", ["witness", "refusal"])
def test_historical_encoding_profile_admits_only_fabricated_full_matrix(
    runner: Row, methods: Methods, tmp_path: Path, case: str,
) -> None:
    profile = _historical_profile(tmp_path / "source", methods, case=case)
    before = dict(profile["pins"])
    assert profile["scope"] == "artificial"
    assert 2_280_855 <= sum(path.stat().st_size for path in profile["inputs"].values()) <= 4 * 1024**2
    for role, path in profile["inputs"].items():
        form = "indent" if role == "grid_audit" else "spaced" if role == "study_audit" else "compact"
        row = json.loads(path.read_bytes())
        assert path.read_bytes() == _wire(row, form=form)
        assert runner["_record"](path.read_bytes(), role) == row

    original = run_path(str(ART / "0225-retained-trace.py"))
    assert original["METHODS"] == runner["METHODS"]
    with pytest.raises(ValueError, match="study_audit canonical record"):
        original["_inputs"](profile, original["Budget"]())
    data, inventory = runner["_inputs"](profile, runner["Budget"]())
    assert [row["point"]["phase_deg"] for row in data["selected"]] == ["9601/64", "9665/64", "9727/64"]
    assert inventory["source_pins"] == before
    output = tmp_path / ("r559m-artificial-json-" + case)
    report = runner["run"](output, profile)
    assert len(report["rows"]) == 24
    assert report["work"]["bounds"] == 48
    assert report["work"]["points"] == 0 and report["work"]["oracle_mass"] == 12
    assert all(_wire(row["trace"]["result"]) == _wire(row["control"]) for row in report["rows"])
    assert all(row["containment"]["containment_checks"] == 16 for row in report["rows"])
    audit_path = tmp_path / ("r559m-artificial-json-" + case + "-audit.json")
    saved = runner["audit"](output, profile, _digest(output / "completion.json"), audit_path=audit_path)
    assert saved == report
    audit = json.loads(audit_path.read_bytes())
    assert audit["work"] == dict(bounds=0, points=0, events=0, oracle_mass=6)
    assert all(profile["pins"][role] == _digest(path) == before[role]
               for role, path in profile["inputs"].items())
    assert {path.name for path in output.iterdir()} == set(FILES)
    assert all((output / name).read_bytes() == _wire(json.loads((output / name).read_bytes())) for name in FILES)


@pytest.mark.parametrize("form", ["compact", "indent"])
def test_existing_sorted_encodings_remain_admitted_for_every_role(runner: Row, form: str) -> None:
    row = dict(a=[1, dict(b="finite")], z=False)
    raw = _wire(row, form=form)
    assert all(runner["_record"](raw, role) == row for role in ROLES)


def test_default_spaced_encoding_is_limited_to_study_audit(runner: Row) -> None:
    row = dict(a=[1, 2], b=dict(c="historical spacing"))
    raw = _wire(row, form="spaced")
    assert runner["_record"](raw, "study_audit") == row
    for role in ROLES[:-1]:
        with pytest.raises(ValueError):
            runner["_record"](raw, role)


@pytest.mark.parametrize("raw", [
    b'{"a":1,"a":2}\n',
    b'{"a":[{"b":1,"b":2}]}\n',
    b'{"a":NaN}\n',
    b'{"a":Infinity}\n',
    b'{"a":-Infinity}\n',
    b'{"a":[{"b":1e999}]}\n',
    b'{"a":}\n',
    b' {"a":1}\n',
    b'{"a":1}',
    b'{"b":2,"a":1}\n',
    b'{"a":"\xff"}\n',
], ids=["duplicate", "nested-duplicate", "nan", "infinity", "negative-infinity", "overflow",
        "malformed", "leading-space", "missing-newline", "unsorted", "invalid-utf8"])
def test_ambiguous_nonfinite_malformed_or_unapproved_bytes_are_rejected(runner: Row, raw: bytes) -> None:
    for role in ROLES:
        with pytest.raises(ValueError):
            runner["_record"](raw, role)


def test_top_level_arrays_and_scalars_are_not_records(runner: Row) -> None:
    for raw in (b'[1,2]\n', b'null\n', b'true\n', b'"text"\n', b'1\n'):
        for role in ROLES:
            with pytest.raises(ValueError):
                runner["_record"](raw, role)


def test_raw_pin_is_checked_before_parsing_a_semantically_equal_reencoding(
    runner: Row, methods: Methods, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _historical_profile(tmp_path / "source", methods)
    path = profile["inputs"]["study_audit"]
    original = path.read_bytes()
    record = json.loads(original)
    path.write_bytes(_wire(record))
    assert json.loads(path.read_bytes()) == json.loads(original)
    assert _digest(path) != profile["pins"]["study_audit"]
    original_record = runner["_record"]

    def parse(raw: bytes, role: str) -> Row:
        assert role != "study_audit", "the changed raw pin must fail before JSON decoding"
        return original_record(raw, role)

    monkeypatch.setitem(runner["_inputs"].__globals__, "_record", parse)
    with pytest.raises(ValueError, match="study_audit source pin"):
        runner["_inputs"](deepcopy(profile), runner["Budget"]())
