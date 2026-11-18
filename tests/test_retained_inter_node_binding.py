"""Exercise the R5.59i archive-bound invocation on synthetic evidence only."""

from hashlib import sha256
import json
from pathlib import Path
from runpy import run_path
from shutil import copytree
from time import monotonic_ns
from typing import Any

import pytest

ARTIFACTS = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
ORIGINAL = ("attempt.json", "report.json", "receipt.json")
SOURCE_FILES = (*ORIGINAL, "audit.json")
RESULT_FILES = (*ORIGINAL, "completion.json")
LIMIT = 4 * 1024**2
type Row = dict[str, Any]
type Pins = dict[str, str]
type Source = tuple[Path, Pins]


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def pins(root: Path, names: tuple[str, ...] = SOURCE_FILES) -> Pins:
    return {name: digest(root / name) for name in names}


def read(root: Path, name: str) -> Row:
    return json.loads((root / name).read_bytes())


def _write_audit(path: Path, row: Row) -> None:
    path.write_text(json.dumps(row, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _wire(row: Row) -> bytes:
    return (json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _synthetic_archive(root: Path) -> Source:
    """Generate a valid 0214 refusal and a matching 0217-shaped readback."""
    outer = root.parent
    prior = run_path(str(ARTIFACTS / "0214-phase-binding.py"))
    seed = run_path(str(ARTIFACTS / "0213-phase-fixtures.py"))
    readback = run_path(str(ARTIFACTS / "0216-saved-phase-readback.py"))
    prior_input = outer / "r559f-artificial-source"
    prior_output = outer / "r559f-artificial-result"
    original_pins = seed["build"](prior_input, impossible=True)
    assert prior["launch"](prior_output, artificial=(prior_input, original_pins)) == 2

    root.mkdir()
    io = prior["_io"]()
    entries = []
    size = 0
    for name in ORIGINAL:
        raw = (prior_output / name).read_bytes()
        (root / name).write_bytes(raw)
        size += len(raw)
        entries.append((io._row(raw), io._sha(raw)))
    identity, methods = prior["_methods"](io, original_pins, "artificial")
    started = monotonic_ns()
    audit = readback["_audit_saved"](entries, prior, identity, methods, check=lambda: None)
    audit.update(
        schema="ariadna-r559f-saved-grid-audit-v1",
        saved_grid_verified=True,
        original_invocation_completed=False,
        original_new_completion_witness=False,
        source_pins=pins(root, ORIGINAL),
        evidence_bytes=size,
        archive_reopens=0,
        new_r559f_attempts=0,
        new_phase_scans=0,
        new_conic_solves=0,
        wall_ns=30_000_000_000,
        original_elapsed_before_receipt_ns=entries[2][0]["elapsed_before_receipt_ns"],
        elapsed_ns=monotonic_ns() - started,
        **prior["FLAGS"],
    )
    _write_audit(root / "audit.json", audit)
    return root, pins(root)


@pytest.fixture(scope="module")
def runner() -> Row:
    return run_path(str(ARTIFACTS / "0220-phase-invocation.py"))


@pytest.fixture(scope="module")
def archive(tmp_path_factory: pytest.TempPathFactory) -> Source:
    return _synthetic_archive(tmp_path_factory.mktemp("r559i-artificial") / "archive")


@pytest.fixture(scope="module")
def outcome(runner: Row, archive: Source) -> tuple[Path, Row]:
    root, _ = archive
    output = root.with_name("first-result")
    assert runner["launch"](artificial=archive, output=output) == 2
    report = runner["verify_result"](artificial=archive, output=output,
                                     completion_sha256=digest(output / "completion.json"))
    return output, report


def test_full_refusal_on_a_four_record_artificial_binding(archive: Source, outcome: tuple[Path, Row]) -> None:
    root, source_pins = archive
    output, report = outcome
    assert set(x.name for x in root.iterdir()) == set(SOURCE_FILES)
    assert pins(root) == source_pins
    assert set(x.name for x in output.iterdir()) == set(RESULT_FILES)
    assert report["status"] == "no-eligible-pair-on-local-interval"
    assert report["scope"] == "artificial"
    assert report["r559i_attempts"] == report["r560_attempts"] == 0
    assert report["live_authorized"] is report["physical_launch_authorized"] is False
    assert report["commands"] is None
    assert all(type(report[key]) is int and report[key] == 0 for key in
               ("spice_queries", "kernel_accesses", "force_evaluations", "integrations"))


def test_binder_accepts_retained_record_shape_only_under_matching_pins(
    archive: Source, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Format-only fixture. No retained paths, appraisal of synthetic costs, or worker launch.
    root, _ = archive
    bind = run_path(str(ARTIFACTS / "0220-phase-archive.py"))["bind"]
    prior = run_path(str(ARTIFACTS / "0214-phase-binding.py"))
    io = prior["_io"]()
    attempt, report, receipt, audit = (read(root, name) for name in SOURCE_FILES)
    for row in (attempt, report, receipt):
        row.update(mode="retained", synthetic=False, r559f_attempts=1)
    attempt_sha = sha256(_wire(attempt)).hexdigest()
    report.update(attempt_sha256=attempt_sha, source_bytes=13_363)
    reference = report["reference"]
    normalized = reference["normalized"]
    normalized.update(scope="retained", candidate_id="d0001-t0035")
    pair = report["rows"][151]["pairs"][0]
    old_least = audit["least_recorded_pair"]["total_delta_v_m_s"]
    pair.update(total_delta_v_m_s=old_least - 1., oracle_total_delta_v_m_s=str(old_least - 1.))
    receipt.update(attempt_sha256=attempt_sha, report_sha256=sha256(_wire(report)).hexdigest())
    records = {name: (row, sha256(_wire(row)).hexdigest())
               for name, row in zip(ORIGINAL, (attempt, report, receipt), strict=True)}
    new_pins = {name: digest for name, (_, digest) in records.items()}
    least = {key: pair[key] for key in ("index", "roots", "reason", "total_delta_v_m_s", "oracle_total_delta_v_m_s")}
    audit.update(candidate_id="d0001-t0035", source_bytes=13_363, adapter_uses=1,
                 source_pins=new_pins, evidence_bytes=sum(len(_wire(row)) for row in (attempt, report, receipt)),
                 least_recorded_pair=least, least_independent_pair=least,
                 zero_encoding=dict(phase_index=0, velocity_component_index=0, original="0E-569", audit_view="0"))
    records["audit.json"] = (audit, sha256(_wire(audit)).hexdigest())
    namespace = bind.__globals__
    monkeypatch.setitem(namespace, "SAVED_PINS", new_pins)
    monkeypatch.setitem(namespace, "UPSTREAM_PINS",
                        {name: attempt["source_pins"][name] for name in report["archive_open_attempts"]})
    monkeypatch.setitem(namespace, "EPOCH_WORDS", normalized["epoch_words"])
    monkeypatch.setitem(namespace, "REFERENCE_SHA256", sha256(_wire(reference)).hexdigest())

    source = bind(records, io, retained=True)
    assert source["scope"] == "retained"
    assert source["reference"] == reference
    assert [row["index"] for row in source["anchors"]] == [150, 151, 152]
    with pytest.raises(ValueError, match="pin overlap"):
        bind(records, io, retained=False)


@pytest.mark.parametrize("fault", ["byte-pin", "rebound-audit-provenance", "rebound-anchor", "source-cap"])
def test_source_faults_cannot_create_a_completion(
    runner: Row, archive: Source, tmp_path: Path, fault: str,
) -> None:
    root = tmp_path / "archive"
    copytree(archive[0], root)
    expected = archive[1]
    summary = read(root, "audit.json")
    if fault == "byte-pin":
        # This remains valid audit metadata but no longer matches the external file pin.
        summary["elapsed_ns"] += 1
    elif fault == "rebound-audit-provenance":
        summary["source_pins"]["report.json"] = "5" * 64
    elif fault == "rebound-anchor":
        report, receipt = (read(root, name) for name in ("report.json", "receipt.json"))
        report["rows"][151]["relative_si"][0] += 1000.
        (root / "report.json").write_bytes(_wire(report))
        receipt["report_sha256"] = digest(root / "report.json")
        (root / "receipt.json").write_bytes(_wire(receipt))
        summary.update(source_pins=pins(root, ORIGINAL),
                       evidence_bytes=sum((root / name).stat().st_size for name in ORIGINAL))
    else:
        # Correct hash and JSON isolate the byte cap from parsing and pin checks.
        summary["artificial_padding"] = "x" * LIMIT
    _write_audit(root / "audit.json", summary)
    if fault != "byte-pin":
        expected = pins(root)
    output = tmp_path / "result"
    assert runner["launch"](artificial=(root, expected), output=output) == 3
    assert not (output / "completion.json").exists()
    if fault == "rebound-anchor":
        assert {path.name for path in output.iterdir()} == {"attempt.json"}


def test_wrong_completion_pin_cannot_be_read_back(
    runner: Row, archive: Source, outcome: tuple[Path, Row],
) -> None:
    output, _ = outcome
    with pytest.raises(ValueError):
        runner["verify_result"](artificial=archive, output=output, completion_sha256="0" * 64)


def test_mode_paths_and_existing_output_are_rejected_before_dispatch(
    runner: Row, archive: Source, outcome: tuple[Path, Row], monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_spawn(*args: Any, **kwargs: Any) -> None:
        pytest.fail("a refused route spawned a worker")

    monkeypatch.setattr(runner["launch"].__globals__["subprocess"], "run", no_spawn)
    output, _ = outcome
    prior = pins(output, RESULT_FILES)
    assert runner["launch"](artificial=archive, output=output) == 3
    assert pins(output, RESULT_FILES) == prior
    with pytest.raises(ValueError):
        runner["launch"](artificial=archive, output=archive[0] / "nested-output")
    with pytest.raises(ValueError):
        runner["launch"](artificial=archive)
    with pytest.raises(ValueError):
        runner["launch"](output=output)
    assert pins(archive[0]) == archive[1]


def test_late_parent_keeps_only_partial_evidence(
    runner: Row, archive: Source, monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = runner["launch"].__globals__
    real_spawn = namespace["subprocess"].run
    late = False

    def run_late(*args: Any, **kwargs: Any) -> Any:
        nonlocal late
        completed = real_spawn(*args, **kwargs)
        assert completed.returncode == 2
        late = True
        return completed

    def clock() -> int:
        return monotonic_ns() + (31_000_000_000 if late else 0)

    monkeypatch.setattr(namespace["subprocess"], "run", run_late)
    monkeypatch.setitem(namespace, "monotonic_ns", clock)
    output = archive[0].with_name("late-result")
    assert runner["launch"](artificial=archive, output=output) == 3
    assert set(x.name for x in output.iterdir()) == set(ORIGINAL)
    prior = pins(output, ORIGINAL)
    assert runner["launch"](artificial=archive, output=output) == 3
    assert pins(output, ORIGINAL) == prior
