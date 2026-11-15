"""Verify ADR0207 selectors on fabricated archive bytes, without running a seed."""

from hashlib import sha256
import json
import math
import os
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

ART = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
type Row = dict[str, Any]
type Files = dict[str, bytes]


@pytest.fixture(scope="module")
def adapter() -> Row:
    return run_path(str(ART / "0209-archive-adapter.py"))


@pytest.fixture(scope="module")
def fixture() -> Row:
    return run_path(str(ART / "0209-archive-fixtures.py"))


def noop() -> None:
    pass


def shape(adapter: Row, fixture: Row) -> object:
    return adapter["ArchiveProfile"]("artificial-moon-mars", fixture["profile_words"]())


def prepare(adapter: Row, fixture: Row, directory: Path, files: Files) -> Row:
    return adapter["prepare"](fixture["write"](directory, files), fixture["pins"](files),
                              shape(adapter, fixture), check_deadline=noop)


def modify(files: Files, name: str, keys: tuple[str | int, ...], value: object) -> Files:
    doc = json.loads(files[name])
    node = doc
    for key in keys[:-1]:
        node = node[key]
    node[keys[-1]] = value
    return files | {name: (json.dumps(doc, sort_keys=True, separators=(",", ":"))+"\n").encode()}


def test_exact_archive_selectors_and_scope(adapter: Row, fixture: Row, tmp_path: Path) -> None:
    files = fixture["build"]()
    result = prepare(adapter, fixture, tmp_path, files)
    assert result["status"] == "archive-inputs-validated" and result["scope"] == "artificial"
    assert result["candidate_id"] == "artificial-moon-mars"
    assert result["epoch_words"] == fixture["profile_words"]()
    assert result["source_pins"] == fixture["pins"](files) and result["source_bytes"] == sum(map(len, files.values()))
    assert result["command_words"] is None and result["live_authorized"] is False
    assert result["orientation"] == "J2000" and result["origin"] == "SSB" and result["units"] == "SI"
    assert [row["guard_m"] for row in result["endpoints"]] == [1737400., 3396190.]
    assert [row["shape_radius_m"] for row in result["endpoints"]] == [1737400., 3389500.]
    source = run_path(str(ART / "0208-seed-fixtures.py"))["build"]()["sections"]
    for i, row in enumerate(result["endpoints"]):
        for field in ("relative_si", "orbit_relative_si", "body_ssb_si", "endpoint_ssb_si"):
            assert list(row[field]) == source["audit"]["endpoints"][i][field]
        assert list(row["v_infinity_m_s"]) == source["r1"]["excess_m_s"][i]
    assert result["rejected_command_words"] == [
        [x.hex() for x in fixture[name]] for name in ("BASE_CONTROLS", "CORRECTION_CONTROLS", "HALF_CONTROLS",
                                                      "QUARTER_CONTROLS")
    ]


def test_artificial_sources_cannot_claim_retained_pins(adapter: Row, fixture: Row, tmp_path: Path) -> None:
    files = fixture["build"]()
    # The policy rejects before opening even the first source.
    paths = {name: tmp_path/name for name in files}
    with pytest.raises(adapter["ArchiveInputError"], match="fixed retained trust pins"):
        adapter["prepare"](paths, fixture["pins"](files), adapter["RETAINED_PROFILE"], check_deadline=noop)
    mixed = fixture["pins"](files)
    mixed[adapter["R1"]] = adapter["RETAINED_PINS"][adapter["R1"]]
    with pytest.raises(adapter["ArchiveInputError"], match="mixed retained"):
        adapter["prepare"](paths, mixed, shape(adapter, fixture), check_deadline=noop)


@pytest.mark.parametrize(("key", "tail", "value", "reason"), [
    ("R1", ("runs", 1, "selected", "flight_time_s"), 1., "R1 archived repeatability"),
    ("R1", ("runs", 1, "endpoints", "arrival", "body_state", "epoch_utc"), "2040Z", "R1 archived repeatability"),
    ("R4", ("science", "scenario", "spacecraft", "initial_mass_kg"), 999., "source candidate or scenario"),
    ("R4", ("science", "candidate", "candidate_id"), "other", "source candidate or scenario"),
    ("AUDIT", ("rows", 0, "stored_endpoint", "position_m", 0), 0., "audit operand"),
    ("AUDIT", ("rows", 1, "stored_body", "orientation"), "ecliptic", "audit operand"),
    ("AUDIT", ("rows", 0, "orbit", "true_anomaly_rad"), 0., "audit operand"),
    ("AUDIT", ("rows", 1, "retained_relative_exact", 0), "0.001", "relative reconstruction"),
    ("AUDIT", ("rows", 0, "binary64_relative", 0), 0., "relative reconstruction"),
    ("AUDIT", ("rows", 0, "decimal80_relative", 0), "0.001", "relative reconstruction"),
    ("AUDIT", ("rows", 0, "decimal100_relative", 0), "0.001", "relative reconstruction"),
    ("AUDIT", ("rows", 0, "retained_relative_exact", 0), "1e99999", "unbounded decimal"),
    ("AUDIT", ("rows", 0, "gm_m3_s2"), 1., "audit operand"),
    ("AUDIT", ("rows", 1, "shape_radius_m"), 3396190., "audit operand"),
    ("AUDIT", ("native_imports_or_calls",), False, "R4 audit status"),
    ("AUDIT", ("finalization_gate",), "stalled", "R4 audit status"),
    ("FRACTIONS", ("science", "runs", 1, "role"), "not-a-fraction", "correction roles"),
    ("FRACTIONS", ("science", "runs", 1, "controls", 2), True, "finite numeric field"),
    ("SEED", ("science", "force_model_id"), "model-B", "baseline outcome"),
    ("SEED", ("science", "seed_commands", "arrival_azimuth_rad"), math.pi, "noncanonical rejected command"),
])
def test_semantic_fault_even_with_all_fixture_hashes_rebound(
    adapter: Row, fixture: Row, tmp_path: Path, key: str, tail: tuple[str | int, ...], value: object, reason: str,
) -> None:
    files = fixture["relink"](modify(fixture["build"](), adapter[key], tail, value))
    with pytest.raises(adapter["ArchiveInputError"], match=reason):
        prepare(adapter, fixture, tmp_path, files)


@pytest.mark.parametrize(("key", "tail", "reason"), [
    ("AUDIT", ("input_sha256", "0119-m2-reference.json"), "R4 audit status or lineage"),
    ("R4", ("science", "expected_reference_sha256"), "correction history linkage"),
    ("FRACTIONS", ("science", "central_step_sha256"), "fractions central source"),
])
def test_independent_pins_do_not_replace_cross_file_provenance(
    adapter: Row, fixture: Row, tmp_path: Path, key: str, tail: tuple[str, ...], reason: str,
) -> None:
    files = modify(fixture["build"](), adapter[key], tail, "0"*64)
    if key == "R4":
        # Update direct references without repairing the wrong historical edge.
        wrong = files[adapter["R4"]]
        files = fixture["relink"](files | {adapter["R4"]: wrong})
        files[adapter["R4"]] = wrong
        contract = files[adapter["CONTRACT"]]
        expected_old = fixture["pins"](fixture["relink"](files))[adapter["R4"]]
        files[adapter["CONTRACT"]] = contract.replace(expected_old.encode(), sha256(wrong).hexdigest().encode())
    elif key == "AUDIT":
        contract = files[adapter["CONTRACT"]]
        original = fixture["pins"](fixture["build"]())[adapter["AUDIT"]]
        files[adapter["CONTRACT"]] = contract.replace(original.encode(), sha256(files[adapter["AUDIT"]]).hexdigest().encode())
    with pytest.raises(adapter["ArchiveInputError"], match=reason):
        prepare(adapter, fixture, tmp_path, files)


@pytest.mark.parametrize("case", ["word", "decimal", "duplicate", "hash", "model"])
def test_contract_rejects_wrong_immutable_table(adapter: Row, fixture: Row, tmp_path: Path, case: str) -> None:
    files = fixture["build"]()
    name = adapter["CONTRACT"]
    text = files[name].decode()
    word = fixture["profile_words"]()[1]
    epoch = float.fromhex(word)
    if case == "word":
        new = math.nextafter(epoch, math.inf)
        text = text.replace(f"{epoch} (`{word}`)", f"{new} (`{new.hex()}`)")
    elif case == "decimal":
        text = text.replace(f"{epoch} (`{word}`)", f"{epoch+1} (`{word}`)")
    elif case == "duplicate":
        text += next(line+"\n" for line in text.splitlines() if line.startswith("| t* ="))
    elif case == "hash":
        digest = fixture["pins"](files)[adapter["R1"]]
        text = text.replace(digest, "0"*64)
    else:
        text = text.replace(adapter["MODEL"], "model-B")
    files[name] = text.encode()
    with pytest.raises(adapter["ArchiveInputError"], match="exact event|lineage|force model"):
        prepare(adapter, fixture, tmp_path, files)


@pytest.mark.parametrize("fault", ["missing", "extra", "changed", "link", "fifo", "duplicate-key"])
def test_reads_only_six_authenticated_regular_files(adapter: Row, fixture: Row, tmp_path: Path, fault: str) -> None:
    files = fixture["build"]()
    if fault == "duplicate-key":
        files[adapter["FRACTIONS"]] = b'{"science":0,'+files[adapter["FRACTIONS"]][1:]
    pins = fixture["pins"](files)
    paths = fixture["write"](tmp_path, files)
    name = adapter["FRACTIONS"]
    if fault == "extra":
        paths["other.json"] = tmp_path/"other.json"
    elif fault == "changed":
        paths[name].write_bytes(files[name]+b" ")
    elif fault == "missing":
        paths[name].unlink()
    elif fault == "link":
        target = paths[name].rename(tmp_path/"else.json")
        paths[name].symlink_to(target)
    elif fault == "fifo":
        paths[name].unlink()
        os.mkfifo(paths[name])
    with pytest.raises(adapter["ArchiveInputError"]):
        adapter["prepare"](paths, pins, shape(adapter, fixture), check_deadline=noop)


@pytest.mark.parametrize("over", [0, 1])
def test_aggregate_byte_ceiling(adapter: Row, fixture: Row, tmp_path: Path, over: int) -> None:
    files = fixture["build"]()
    pad = adapter["INPUT_LIMIT"]-sum(map(len, files.values()))
    files[adapter["FRACTIONS"]] += b" "*(pad+over)
    if over:
        with pytest.raises(adapter["ArchiveInputError"], match="byte cap or file type"):
            prepare(adapter, fixture, tmp_path, files)
    else:
        assert prepare(adapter, fixture, tmp_path, files)["source_bytes"] == 512*1024


def test_parent_deadline_cannot_return_a_late_packet(adapter: Row, fixture: Row, tmp_path: Path) -> None:
    files = fixture["build"]()
    calls = 0

    def expired() -> None:
        nonlocal calls
        calls += 1
        if calls == 9:
            raise TimeoutError("parent deadline")

    with pytest.raises(adapter["ArchiveInputError"], match="parent deadline"):
        adapter["prepare"](fixture["write"](tmp_path, files), fixture["pins"](files), shape(adapter, fixture),
                           check_deadline=expired)
