"""Qualify the R5.59c composition exclusively with fabricated archive files."""

from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
from runpy import run_path
from time import monotonic_ns
from typing import Any

import pytest

ART = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
INPUT_CAP = 512 * 1024
OUTPUT_CAP = 128 * 1024
EVIDENCE = ("attempt.json", "report.json", "receipt.json", "completion.json")
type Row = dict[str, Any]
type Files = dict[str, bytes]
type Artificial = tuple[Path, dict[str, str], tuple[str, str, str]]


@pytest.fixture(scope="module")
def runner() -> Row:
    return run_path(str(ART / "0210-retained-runner.py"))


@pytest.fixture(scope="module")
def archives() -> Row:
    return run_path(str(ART / "0209-archive-fixtures.py"))


def wire(row: Row) -> bytes:
    return (json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def inputs(archives: Row, path: Path, files: Files | None = None) -> Artificial:
    if files is None:
        files = archives["build"]()
    archives["write"](path, files)
    return path, archives["pins"](files), archives["profile_words"]()


def evidence(path: Path) -> Files:
    return {p.name: p.read_bytes() for p in path.iterdir()}


def no_physical_authority(report: Row) -> None:
    assert report["mode"] == "artificial"
    assert report["live_authorized"] is False
    assert report["physical_launch_authorized"] is False
    assert report["physical_status"] == "physical-join-not-established"
    assert report["physical_residuals"] == dict.fromkeys(("epoch_s", "position_m", "velocity_m_s", "mass_kg"))
    for name in ("spice_queries", "kernel_accesses", "force_evaluations", "integrations", "r559c_attempts", "r560_attempts"):
        assert type(report[name]) is int and report[name] == 0


def verify(runner: Row, out: Path, profile: Artificial) -> Row:
    return runner["verify_result"](out, artificial=profile,
                                   expected_completion_sha256=sha((out / EVIDENCE[-1]).read_bytes()))


def test_full_input_cap_known_conics_and_exclusive_evidence(runner: Row, archives: Row, tmp_path: Path) -> None:
    files = archives["build"]()
    files[archives["FRACTIONS"]] += b" " * (INPUT_CAP - sum(map(len, files.values())))
    profile = inputs(archives, tmp_path / "archives", files)
    out = tmp_path / "evidence"
    assert runner["launch"](out, artificial=profile) == 0
    first = evidence(out)
    assert set(first) == set(EVIDENCE) and 0 < sum(map(len, first.values())) <= OUTPUT_CAP
    report = verify(runner, out, profile)
    no_physical_authority(report)
    assert report["status"] == "artificial-command-proposal"
    normalized = report["normalized"]
    assert normalized["source_bytes"] == INPUT_CAP and normalized["source_pins"] == profile[1]
    assert tuple(normalized["epoch_words"]) == profile[2]
    assert len(report["archive_open_attempts"]) == 6 and set(report["archive_open_attempts"]) == files.keys()
    assert normalized["command_words"] is None and normalized["scope"] == "artificial"
    known_moon, known_mars = run_path(str(ART / "0208-seed-fixtures.py"))["known_geometry"]()
    assert report["selected_roots"] == [known_moon.root, known_mars.root] == ["negative", "positive"]
    assert report["branch_decisions"]["Mars"]["negative"]["reason"] == "guard"
    for state in (known_moon, known_mars):
        group = report["branch_decisions"][state.body]
        assert set(group) == {"positive", "negative"}
        assert math.dist(group[state.root]["hyperbolic_velocity_m_s"], state.hyperbolic_m_s) < 1e-6
        assert math.dist(group[state.root]["reconstructed_excess_m_s"], state.excess_m_s) < 1e-6
    assert {tuple(pair["roots"]) for pair in report["pairs"]} == {("positive", "positive"), ("negative", "positive")}
    winner, = [pair for pair in report["pairs"] if pair["roots"] == report["selected_roots"]]
    assert report["command_words"] == winner["command_words"]
    _, _, td, _, _, ta = map(float.fromhex, report["command_words"])
    flow = Fraction(1000 / (9.80665 * 450))
    assert Fraction(winner["ledgers"]["mass_kg_exact"]["commanded"][-1]) == 2000 - flow * (Fraction(td) + Fraction(ta))
    t0, t1, tx, t2, tf = map(float.fromhex, winner["ledgers"]["epoch_words"])
    assert t0 < t1 == t0 + td < tx < t2 == tf - ta < tf
    assert Fraction(winner["ledgers"]["mass_kg_exact"]["effective"][-1]) == (
        2000 - flow * (Fraction(t1) - Fraction(t0) + Fraction(tf) - Fraction(t2))
    )
    assert runner["launch"](out, artificial=profile) == 3
    assert evidence(out) == first
    assert evidence(profile[0]) == files


def test_repeatable_science_on_separate_artificial_outputs(runner: Row, archives: Row, tmp_path: Path) -> None:
    profile = inputs(archives, tmp_path / "archives")
    one, two = tmp_path / "one", tmp_path / "two"
    assert runner["launch"](one, artificial=profile) == runner["launch"](two, artificial=profile) == 0
    a, b = verify(runner, one, profile), verify(runner, two, profile)
    assert a["run_id"] != b["run_id"]
    fields = ("status", "normalized", "normalized_sha256", "branch_decisions", "pairs", "selected_roots", "command_words")
    assert [a[key] for key in fields] == [b[key] for key in fields]


def test_degenerate_lunar_direction_preserves_scientific_refusal(runner: Row, archives: Row, tmp_path: Path) -> None:
    files = archives["build"]()
    r1, audit = (json.loads(files[archives[key]]) for key in ("R1", "AUDIT"))
    position = list(map(float, audit["rows"][0]["retained_relative_exact"][:3]))
    for run in r1["runs"]:
        run["selected"]["departure_v_infinity_m_s"] = position
    files[archives["R1"]] = wire(r1)
    for key in ("R4", "FRACTIONS"):
        doc = json.loads(files[archives[key]])
        doc["science"]["candidate"] = r1["runs"][0]["selected"]
        files[archives[key]] = wire(doc)
    profile = inputs(archives, tmp_path / "archives", archives["relink"](files))
    out = tmp_path / "refusal"
    assert runner["launch"](out, artificial=profile) == 2
    report = verify(runner, out, profile)
    no_physical_authority(report)
    assert report["status"] == "command-seed-unavailable" and report["command_words"] is None
    assert {row["reason"] for row in report["branch_decisions"]["Moon"].values()} == {"degenerate"}
    assert set(report["branch_decisions"]["Mars"]) == {"positive", "negative"}
    assert report["pairs"] == []
    assert json.loads((out / "completion.json").read_bytes())["exit_code"] == 2


@pytest.mark.parametrize("fault", ["wrong-digest", "symlink", "one-byte-over-cap"])
def test_archive_failure_never_freezes_a_command(runner: Row, archives: Row, tmp_path: Path, fault: str) -> None:
    files = archives["build"]()
    name = archives["FRACTIONS"]
    if fault == "one-byte-over-cap":
        files[name] += b" " * (INPUT_CAP + 1 - sum(map(len, files.values())))
    profile = inputs(archives, tmp_path / "archives", files)
    source = profile[0] / name
    if fault == "wrong-digest":
        source.write_bytes(source.read_bytes() + b" ")
    if fault == "symlink":
        target = source.rename(tmp_path / "same-bytes-replacement.json")
        source.symlink_to(target)
    out = tmp_path / "invalid"
    assert runner["launch"](out, artificial=profile) == 3
    report = verify(runner, out, profile)
    no_physical_authority(report)
    assert report["status"] == "invalid-evidence" and report["command_words"] is None
    assert report["branch_decisions"] == {} and report["pairs"] == []
    assert name in report["archive_open_attempts"]


def rebound_report(output: Path, report: Row) -> None:
    """Rehash the writable chain so the verifier has to inspect scientific content."""
    edited = wire(report)
    (output / "report.json").write_bytes(edited)
    receipt = json.loads((output / "receipt.json").read_bytes())
    receipt["report_sha256"] = sha(edited)
    rec = wire(receipt)
    (output / "receipt.json").write_bytes(rec)
    completion = json.loads((output / "completion.json").read_bytes())
    completion["receipt_sha256"] = sha(rec)
    (output / "completion.json").write_bytes(wire(completion))


@pytest.mark.parametrize("fault", ["branch", "pair", "ledger", "normalized", "physical"])
def test_readback_rejects_rebound_invalid_science(runner: Row, archives: Row, tmp_path: Path, fault: str) -> None:
    profile = inputs(archives, tmp_path / "archives")
    out = tmp_path / "rebound"
    assert runner["launch"](out, artificial=profile) == 0
    report = json.loads((out / "report.json").read_bytes())
    if fault == "branch":
        del report["branch_decisions"]["Moon"]["positive"]
    elif fault == "pair":
        report["pairs"].pop()
    elif fault == "ledger":
        selected, = [pair for pair in report["pairs"] if pair["roots"] == report["selected_roots"]]
        selected["ledgers"]["mass_kg_exact"]["effective"][-1] = "500"
    elif fault == "normalized":
        report["normalized"]["scope"] = "retained"
        report["normalized_sha256"] = sha(wire(report["normalized"]))
    else:
        report["physical_launch_authorized"] = True
    rebound_report(out, report)
    with pytest.raises(ValueError):
        verify(runner, out, profile)


def test_readback_refuses_wrong_completion_pin_and_noncanonical_bytes(
    runner: Row, archives: Row, tmp_path: Path,
) -> None:
    profile = inputs(archives, tmp_path / "archives")
    out = tmp_path / "readback"
    assert runner["launch"](out, artificial=profile) == 0
    with pytest.raises(ValueError):
        runner["verify_result"](out, artificial=profile, expected_completion_sha256="a" * 64)
    path = out / "report.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        verify(runner, out, profile)


def test_late_parent_invalidates_completion_but_keeps_partial_evidence(
    runner: Row, archives: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = inputs(archives, tmp_path / "archives")
    state = runner["launch"].__globals__
    parent_late = False
    run = state["subprocess"].run

    def simulate_late_parent(*args: Any, **kwargs: Any) -> object:
        nonlocal parent_late
        result = run(*args, **kwargs)
        assert result.returncode == 0
        parent_late = True
        return result

    def clock() -> int:
        return monotonic_ns() + (30 * 10**9 if parent_late else 0)

    monkeypatch.setattr(state["subprocess"], "run", simulate_late_parent)
    monkeypatch.setitem(state, "monotonic_ns", clock)
    out = tmp_path / "late"
    assert runner["launch"](out, artificial=profile) == 3
    assert set(evidence(out)) == set(EVIDENCE[:3])
    with pytest.raises((ValueError, OSError)):
        runner["verify_result"](out, artificial=profile)


def test_independent_readback_needs_no_source_file_reopen(
    runner: Row, archives: Row, tmp_path: Path,
) -> None:
    profile = inputs(archives, tmp_path / "archives")
    out = tmp_path / "readback"
    assert runner["launch"](out, artificial=profile) == 0
    profile[0].rename(tmp_path / "moved-away")
    assert verify(runner, out, profile)["status"] == "artificial-command-proposal"
    # Looking at the same evidence with the retained identity never runs a worker.
    with pytest.raises(ValueError, match="source or method identity"):
        runner["verify_result"](out)


def test_reject_wrong_destination_before_worker_spawn(
    runner: Row, archives: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = inputs(archives, tmp_path / "archives")
    state = runner["launch"].__globals__

    def unexpected_spawn(*_: Any, **__: Any) -> None:
        pytest.fail("invalid mode/destination reached worker launch")

    monkeypatch.setattr(state["subprocess"], "run", unexpected_spawn)
    with pytest.raises(ValueError, match="retained evidence destination"):
        runner["launch"](runner["RETAINED_OUTPUT"], artificial=profile)
    with pytest.raises(ValueError, match="retained evidence destination"):
        runner["launch"](tmp_path / "not-the-retained-destination")
    assert not (tmp_path / "not-the-retained-destination").exists()
