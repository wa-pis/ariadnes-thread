"""Verify the R5.59f binding and readback on fabricated archives only."""

from hashlib import sha256
import json
from pathlib import Path
from runpy import run_path
from shutil import copytree
from time import monotonic_ns
from typing import Any

import pytest

ART = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
type Row = dict[str, Any]
type Pins = dict[str, str]
type Source = tuple[Path, Pins]


@pytest.fixture(scope="module")
def runner() -> Row:
    return run_path(str(ART / "0214-phase-binding.py"))


@pytest.fixture(scope="module")
def fixtures() -> Row:
    return run_path(str(ART / "0213-phase-fixtures.py"))


@pytest.fixture(scope="module")
def source(tmp_path_factory: pytest.TempPathFactory, fixtures: Row) -> Source:
    root = tmp_path_factory.mktemp("r559f-artificial") / "source"
    return root, fixtures["build"](root)


def pin(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def pins(root: Path) -> Pins:
    return {name: pin(root / name) for name in FILES}


def read(root: Path, name: str) -> Row:
    return json.loads((root / name).read_bytes())


def save(root: Path, name: str, row: Row) -> None:
    raw = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
    (root / name).write_text(raw + "\n")


def bind_report(root: Path, report: Row) -> Pins:
    """Rebind writable receipts so a mutation exercises semantic checks."""
    save(root, "report.json", report)
    receipt = read(root, "receipt.json")
    receipt["report_sha256"] = pin(root / "report.json")
    save(root, "receipt.json", receipt)
    completion = read(root, "completion.json")
    completion["receipt_sha256"] = pin(root / "receipt.json")
    save(root, "completion.json", completion)
    return pins(root)


@pytest.fixture(scope="module")
def proposal(
    tmp_path_factory: pytest.TempPathFactory, runner: Row, source: Source,
) -> tuple[Path, Row]:
    output = tmp_path_factory.mktemp("r559f-artificial-output") / "first"
    assert runner["launch"](output, artificial=source) == 0
    report = runner["verify_result"](output, artificial=source, expected_completion_sha256=pin(output / FILES[3]))
    return output, report


def verify_grid(report: Row, archive: Source) -> None:
    root, expected = archive
    assert report["schema"] == "ariadna-r559f-phase-evidence-v1"
    assert report["stage"] == "R5.59f"
    assert report["mode"] == "artificial" and report["synthetic"] is True
    assert report["source_pins"] == expected == pins(root)
    assert sorted(report["archive_open_attempts"]) == sorted(FILES)
    assert report["source_bytes"] == sum((root / name).stat().st_size for name in FILES) <= 128 * 1024
    assert report["live_authorized"] is report["physical_launch_authorized"] is False
    for key in ("r559f_attempts", "r560_attempts", "spice_queries", "kernel_accesses", "force_evaluations", "integrations"):
        assert type(report[key]) is int and report[key] == 0
    assert report["work"]["phase_positions"] == 360 and report["work"]["mars_roots"] == 720
    assert [row["index"] for row in report["rows"]] == list(range(360))
    assert all(set(row["branches"]) == {"positive", "negative"} for row in report["rows"])
    upstream = read(root, "report.json")
    assert report["reference"]["normalized"] == upstream["normalized"]
    assert report["reference"]["lunar"] == upstream["branch_decisions"]["Moon"]["positive"]
    zero = report["rows"][0]
    assert zero["angle_word"] == float(0).hex()
    assert "commanded-dry-floor" in {pair["reason"] for pair in zero["pairs"]}


def test_same_binding_checks_all_phases_and_the_known_winner(
    source: Source, proposal: tuple[Path, Row], fixtures: Row,
) -> None:
    output, report = proposal
    verify_grid(report, source)
    assert report["status"] == "artificial-phase-proposal"
    winner = report["selected"]
    assert winner["index"] == fixtures["EXPECTED_INDEX"] == 95
    assert report["command_words"] == winner["command_words"]
    completion = read(output, "completion.json")
    assert completion["exit_code"] == 0
    assert 0 < completion["elapsed_through_readback_ns"] < 30_000_000_000


def test_same_binding_keeps_a_verified_empty_grid(
    runner: Row, fixtures: Row, tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    archive = root, fixtures["build"](root, impossible=True)
    output = tmp_path / "empty"
    assert runner["launch"](output, artificial=archive) == 2
    report = runner["verify_result"](output, artificial=archive)
    verify_grid(report, archive)
    assert report["status"] == "no-eligible-pair-on-grid"
    assert report["selected"] is report["command_words"] is None


def test_retained_loader_authenticates_fabricated_retained_shape(
    runner: Row, source: Source, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "fabricated-retained-shape"
    copytree(source[0], root)
    header = {"mode": "retained", "candidate_id": "d0001-t0035"}
    save(root, "attempt.json", read(root, "attempt.json") | header)
    attempt = pin(root / "attempt.json")
    report = read(root, "report.json") | header | {"attempt_sha256": attempt, "r559c_attempts": 1}
    normalized = report["normalized"]
    normalized.update(scope="retained", candidate_id=header["candidate_id"])
    io = runner["_io"]()
    report["normalized_sha256"] = sha256(io._wire(normalized)).hexdigest()
    save(root, "receipt.json", read(root, "receipt.json") | header | {"attempt_sha256": attempt})
    expected = bind_report(root, report)
    reference = dict(normalized=normalized, lunar=report["branch_decisions"]["Moon"]["positive"],
                     zero_branches=report["branch_decisions"]["Mars"], zero_pairs=report["pairs"])
    namespace = runner["_reference"].__globals__
    monkeypatch.setitem(namespace, "EPOCH_WORDS", tuple(report["epoch_words"]))
    monkeypatch.setitem(namespace, "REFERENCE_SHA256", sha256(io._wire(reference)).hexdigest())
    _, methods = runner["_methods"](io, expected, "retained")
    previous, reader, screen = (runner["_load"](name, methods[name]) for name in ("previous", "reader", "screen"))

    def load() -> tuple[Row, int]:
        return runner["_reference"](root, expected, "retained", io, previous, reader, screen, lambda: None)

    assert load() == (reference, sum((root / name).stat().st_size for name in FILES))
    save(root, "report.json", report | {"changed_after_pin": True})
    with pytest.raises(ValueError, match=r"report\.json: source encoding or pin"):
        load()


@pytest.mark.parametrize("fault", ["byte-pin", "rebound-profile", "rebound-lineage"])
def test_source_rejection_before_any_scientific_rows(
    runner: Row, source: Source, tmp_path: Path, fault: str,
) -> None:
    root = tmp_path / "modified"
    copytree(source[0], root)
    report = read(root, "report.json")
    expected = dict(source[1])
    if fault == "byte-pin":
        save(root, "report.json", report | {"changed_but_valid_json": True})
    elif fault == "rebound-profile":
        expected = bind_report(root, report | {"mode": "retained"})
    else:
        expected = bind_report(root, report | {"attempt_sha256": "f" * 64})
    archive = root, expected
    output = tmp_path / "result"
    assert runner["launch"](output, artificial=archive) == 3
    if (output / "report.json").is_file():
        invalid = read(output, "report.json")
        assert invalid["status"] == "invalid-evidence"
        assert invalid["rows"] == [] and invalid["command_words"] is None
    if (output / "completion.json").is_file():
        assert runner["verify_result"](output, artificial=archive)["status"] == "invalid-evidence"


def test_independent_audit_does_not_reopen_the_archive(
    runner: Row, source: Source, proposal: tuple[Path, Row],
) -> None:
    output, report = proposal
    root, expected = source
    hidden = root.with_name("temporarily-hidden")
    root.rename(hidden)
    try:
        completion = pin(output / "completion.json")
        assert runner["verify_result"](output, artificial=(root, expected), expected_completion_sha256=completion) == report
        with pytest.raises(ValueError):
            runner["verify_result"](output, artificial=(root, expected), expected_completion_sha256="0" * 64)
    finally:
        hidden.rename(root)


@pytest.mark.parametrize("fault", ["phase", "selection", "pins", "attempt-counter"])
def test_audit_rejects_rebound_output(
    runner: Row, source: Source, proposal: tuple[Path, Row], tmp_path: Path, fault: str,
) -> None:
    output = tmp_path / "mutated"
    copytree(proposal[0], output)
    report = read(output, "report.json")
    if fault == "phase":
        report["rows"][317]["index"] = 316
    elif fault == "selection":
        report["selected"]["ledgers"]["mass_kg_exact"]["effective"][-1] = "2000"
    elif fault == "pins":
        report["source_pins"]["report.json"] = "7" * 64
    else:
        report["r559f_attempts"] = 1
    forged = bind_report(output, report)
    with pytest.raises(ValueError):
        runner["verify_result"](output, artificial=source, expected_completion_sha256=forged["completion.json"])


def test_retained_and_existing_output_gates_do_not_start_a_worker(
    runner: Row, source: Source, proposal: tuple[Path, Row], tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_spawn(*args: Any, **kwargs: Any) -> None:
        pytest.fail("an ineligible request dispatched a worker")

    monkeypatch.setattr(runner["launch"].__globals__["subprocess"], "run", no_spawn)
    output = proposal[0]
    first = pins(output)
    assert runner["launch"](output, artificial=source) == 3
    assert pins(output) == first
    with pytest.raises(ValueError):
        runner["verify_result"](output)
    for destination, archive in ((tmp_path / "not-canonical", None), (runner["RETAINED_OUTPUT"], source)):
        try:
            assert runner["launch"](destination, artificial=archive) == 3
        except ValueError:
            pass


def test_parent_watchdog_keeps_only_the_first_partial_evidence(
    runner: Row, source: Source, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = runner["launch"].__globals__
    real_spawn = namespace["subprocess"].run
    late = False

    def spawn_late(*args: Any, **kwargs: Any) -> Any:
        nonlocal late
        result = real_spawn(*args, **kwargs)
        assert result.returncode == 0
        late = True
        return result

    def clock() -> int:
        return monotonic_ns() + (31_000_000_000 if late else 0)

    monkeypatch.setattr(namespace["subprocess"], "run", spawn_late)
    monkeypatch.setitem(namespace, "monotonic_ns", clock)
    output = tmp_path / "late"
    assert runner["launch"](output, artificial=source) == 3
    partial = {item.name: pin(item) for item in output.iterdir()}
    assert set(partial) == set(FILES[:3])
    with pytest.raises((OSError, ValueError)):
        runner["verify_result"](output, artificial=source)
    assert runner["launch"](output, artificial=source) == 3
    assert {item.name: pin(item) for item in output.iterdir()} == partial
