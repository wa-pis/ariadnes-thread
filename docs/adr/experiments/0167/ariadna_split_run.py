"""Private ADR0166 parent and isolated children; importing never requests states."""
from __future__ import annotations

# ruff: noqa: E402 -- Take the child timestamp before other imports.
from time import monotonic
PROCESS_START = monotonic()

from collections.abc import Callable
from contextlib import ExitStack
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, TextIO

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
if __name__ == "__main__":
    sys.path.insert(0, str(HERE))

from ariadna_split_common import (
    ANALYSIS_CAPS, BUDGETS, CAPTURE_CAPS, FAILURES, Recorder, digest, encode,
    journal_rows, number, parse_json, require, same, wire,
)

LIVE_DIR = Path("/private/tmp/ariadna-r521")
PINNED_PYTHON = Path("/opt/homebrew/Caskroom/miniforge/base/envs/space-nav/bin/python")
MANIFEST = "docs/adr/experiments/0167-verification.json"
INPUTS = "docs/adr/experiments/0166-inputs.json"
HELPERS = tuple(f"docs/adr/experiments/0167/ariadna_split_{part}.py" for part in
                ("analysis", "capture", "common", "inputs", "run"))
TESTS = tuple(f"tests/test_split_ephemeris_{part}.py" for part in
              ("analysis", "capture", "inputs", "run"))
FLAGS = {"capture": ("-I", "-B"), "analysis": ("-I", "-S", "-B")}
WATCHDOGS = {"capture": 20.0, "analysis": 15.0}
CAPS = {"capture": CAPTURE_CAPS, "analysis": ANALYSIS_CAPS}


def prep_pin(root: Path, manifest_sha: str, check: Callable[[], Any]) -> dict[str, Any]:
    check()
    manifest = root / MANIFEST
    require(digest(manifest) == manifest_sha, "preparation manifest SHA-256")
    verified = parse_json(manifest.read_bytes())
    require(verified["preparation_complete"] is True, "preparation not verified")
    tested = verified["tested_source_sha256"]
    require(set(tested) == set(HELPERS + TESTS), "tested source inventory")
    for name, expected in tested.items():
        check()
        require(digest(root / name) == expected, "tested source digest: " + name)
    input_sha = digest(root / INPUTS)
    require(input_sha == verified["inputs_sha256"], "frozen input SHA-256")
    check()
    return {"preparation_sha256": manifest_sha, "input_sha256": input_sha,
            "helper_sha256": {name: tested[name] for name in HELPERS},
            "tested_source_sha256": tested}


def paths(directory: Path, phase: str) -> dict[str, Path]:
    require(phase in CAPS, "unknown phase")
    return {part: directory / f"{phase}.{ext}" for part, ext in {
        "report": "json", "journal": "ledger.jsonl", "receipt": "receipt.json",
        "attempt": "attempt.json", "parent": "parent-receipt.json",
    }.items()}


def store(stream: TextIO, data: dict[str, Any]) -> None:
    stream.write(encode(data).decode())
    stream.flush()
    os.fsync(stream.fileno())


def record_failure(report: dict[str, Any], stage: str, exc: BaseException) -> None:
    report["status"] = "failed"
    report.setdefault("error", {"stage": stage, "type": type(exc).__name__, "message": str(exc)})


def in_budget(value: Any, phase: str, message: str) -> float:
    elapsed_s = number(value, message)
    require(0 <= elapsed_s <= BUDGETS[phase], message)
    return elapsed_s


def read_phase(directory: Path, phase: str, execution: str) -> tuple[dict[str, Any], dict[str, Any]]:
    files = paths(directory, phase)
    receipt = parse_json(files["receipt"].read_bytes())
    require(receipt["finalization"] == "passed", phase + " finalization")
    for part in ("report", "journal"):
        require(receipt[part + "_sha256"] == digest(files[part]), phase + " " + part + " hash")
    report = parse_json(files["report"].read_bytes())
    same([report["contract"], report["phase"], report["execution"], report["budget_s"]],
         ["ADR0166", phase, execution, BUDGETS[phase]], phase + " contract")
    same(receipt["status"], report["status"], phase + " status")
    start = number(report["external_start_s"], phase + " start")
    same(receipt["external_start_s"], start, phase + " receipt start")
    boot = in_budget(report["child_start_elapsed_s"], phase, phase + " child start")
    flushed = in_budget(receipt["elapsed_before_receipt_s"], phase, phase + " receipt time")
    reported = in_budget(report["elapsed_before_report_s"], phase, phase + " report time")
    require(boot <= reported <= flushed, phase + " receipt timeline")
    cursor = boot
    for entry in report["ledger"]:
        for key in ("attempted_s", "returned_s", "completed_s"):
            if key in entry:
                timestamp = number(entry[key], phase + " " + key)
                require(cursor <= timestamp <= reported, phase + " ledger timeline")
                cursor = timestamp
    saved = files["journal"].read_bytes()
    reconstructed = b"".join(encode(row) for i, entry in enumerate(report["ledger"])
                             for row in journal_rows(i, entry))
    require(saved == reconstructed, phase + " durable ledger mismatch")
    return report, receipt


def read_capture(directory: Path, execution: str, identity_pin: dict[str, Any]) -> dict[str, Any]:
    report, receipt = read_phase(directory, "capture", execution)
    require(report["status"] == "passed" and "error" not in report, "capture incomplete")
    same(report["identity_pin"], identity_pin, "capture preparation identity")
    same(report["final_identity_pin"], identity_pin, "capture final preparation identity")
    if execution == "live":
        files = paths(directory, "capture")
        parent = parse_json(files["parent"].read_bytes())
        attempt = parse_json(files["attempt"].read_bytes())
        same(attempt, {"phase": "capture", "preparation_sha256": identity_pin["preparation_sha256"]},
             "capture attempt identity")
        same([parent["phase"], parent["returncode"], parent["finalization"]],
             ["capture", 0, "passed"], "capture parent receipt")
        same(parent["preparation_sha256"], identity_pin["preparation_sha256"],
             "capture parent preparation identity")
        same(parent["external_start_s"], report["external_start_s"], "capture parent start")
        same(parent["attempt_sha256"], digest(files["attempt"]), "capture attempt hash")
        same(parent["child_receipt_sha256"], digest(files["receipt"]), "capture child receipt hash")
        elapsed = in_budget(parent["external_elapsed_s"], "capture", "capture external deadline")
        require(elapsed >= receipt["elapsed_before_receipt_s"], "capture parent timeline")
    return report


def finish(
    report: dict[str, Any], recorder: Recorder, files: dict[str, Path], streams: dict[str, TextIO],
) -> bool:
    finalization = "passed"
    try:
        report["elapsed_before_report_s"] = recorder.check()
        store(streams["report"], wire(report))
        os.fsync(streams["journal"].fileno())
        recorder.check()
    except FAILURES as exc:
        finalization = "failed"
        record_failure(report, "finalization", exc)
        report["elapsed_before_report_s"] = wire(recorder.elapsed())
        streams["report"].seek(0)
        streams["report"].truncate()
        store(streams["report"], wire(report))
    receipt = {"status": report["status"], "finalization": finalization,
               "external_start_s": recorder.start_s, "elapsed_before_receipt_s": wire(recorder.elapsed()),
               **{part + "_sha256": digest(files[part]) for part in ("report", "journal")}}
    store(streams["receipt"], receipt)
    if finalization == "passed":
        try:
            same(parse_json(files["receipt"].read_bytes()), receipt, "child receipt readback")
            recorder.check()
        except FAILURES as exc:
            receipt["finalization"] = "failed"
            receipt["finalization_error"] = str(exc)
            receipt["elapsed_after_flush_s"] = wire(recorder.elapsed())
            streams["receipt"].seek(0)
            streams["receipt"].truncate()
            store(streams["receipt"], receipt)
            return False
    return finalization == "passed" and report["status"] == "passed"


def run_phase(
    directory: Path, phase: str, start_s: float, *, execution: str,
    input_loader: Callable[[Callable[[], Any]], dict[str, Any]],
    pin_loader: Callable[[Callable[[], Any]], dict[str, Any]],
    adapter_factory: Callable[[], Any] | None = None,
    clock: Callable[[], float] = monotonic, boot_s: float = PROCESS_START,
) -> bool:
    """Execute one phase against new output paths; injection is for tests only."""
    from ariadna_split_capture import capture, validate_capture

    files = paths(directory, phase)
    require(execution in ("live", "synthetic"), "execution mode")
    require(all(not files[part].exists() for part in ("report", "journal", "receipt")), "existing phase evidence")
    report: dict[str, Any] = {
        "contract": "ADR0166", "phase": phase, "execution": execution, "status": "passed",
        "external_start_s": start_s, "child_start_elapsed_s": wire(boot_s - start_s),
        "production_or_mission_verified": False,
    }
    with ExitStack() as stack:
        streams = {part: stack.enter_context(files[part].open("x", encoding="utf-8"))
                   for part in ("report", "journal", "receipt")}
        recorder = Recorder(report, CAPS[phase], start_s, BUDGETS[phase], clock=clock, journal=streams["journal"])
        stage = "preparation"
        try:
            recorder.check(boot_s - start_s)
            recorder.check()
            pin = pin_loader(recorder.check)
            report["identity_pin"] = pin
            bundle = input_loader(recorder.check)
            if phase == "capture":
                stage = "capture"
                require(adapter_factory is not None, "capture adapter required")
                capture(bundle, report, recorder, adapter=adapter_factory(), identity_pin=pin)
                stage = "final preparation identity"
                report["final_identity_pin"] = pin_loader(recorder.check)
                same(report["final_identity_pin"], pin, "before/after tested helper/input identity")
            else:
                from ariadna_split_analysis import analyze

                stage = "capture verification"
                saved = read_capture(directory, execution, pin)
                states = validate_capture(bundle, saved, pin)
                report["capture_receipt_sha256"] = digest(paths(directory, "capture")["receipt"])
                recorder.check()
                stage = "analysis"
                analyze(bundle, states, report, recorder)
            recorder.check()
        except FAILURES as exc:
            record_failure(report, stage, exc)
            report.setdefault("unavailable", ["completed capture"] if phase == "capture"
                              else ["state parity", "position closure", "static force"])
        return finish(report, recorder, files, streams)


def supervise(directory: Path, phase: str, manifest_sha: str) -> bool:
    """Launch one isolated child and measure from before spawn through evidence readback."""
    require(phase in CAPS and re.fullmatch(r"[0-9a-f]{64}", manifest_sha) is not None, "phase/manifest SHA-256")
    files = paths(directory, phase)
    if phase == "analysis":
        require(paths(directory, "capture")["parent"].is_file(), "no finalized capture attempt")
    directory.mkdir(mode=0o700, exist_ok=True)
    require(not directory.is_symlink() and all(not path.exists() for path in files.values()),
            "existing phase evidence")
    with files["attempt"].open("x", encoding="utf-8") as marker:
        store(marker, {"phase": phase, "preparation_sha256": manifest_sha})
    start = monotonic()
    child_code: int | None = None
    receipt: dict[str, Any] = {
        "phase": phase, "external_start_s": start, "preparation_sha256": manifest_sha,
        "finalization": "failed", "returncode": None,
    }
    try:
        completed = subprocess.run(
            [str(PINNED_PYTHON), *FLAGS[phase], str(HERE / Path(__file__).name),
             "_child", phase, manifest_sha, repr(start)],
            cwd=ROOT, capture_output=True, text=True, timeout=WATCHDOGS[phase], check=False,
        )
        child_code = completed.returncode
        receipt.update(returncode=child_code, stderr=completed.stderr)
        report, _ = read_phase(directory, phase, "live")
        same(report["external_start_s"], start, phase + " parent/child start")
        same([child_code, report["status"] == "passed"], [0, True] if child_code == 0
             else [2, False], phase + " child exit status")
        receipt["attempt_sha256"] = digest(files["attempt"])
        receipt["child_receipt_sha256"] = digest(files["receipt"])
        in_budget(monotonic() - start, phase, phase + " external deadline")
        receipt["finalization"] = "passed"
    except (*FAILURES, subprocess.TimeoutExpired) as exc:
        receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
    receipt["external_elapsed_s"] = monotonic() - start
    with files["parent"].open("x", encoding="utf-8") as stream:
        store(stream, receipt)
        elapsed = monotonic() - start
        if elapsed > BUDGETS[phase]:
            receipt.update(finalization="failed", external_elapsed_s=elapsed)
            receipt.setdefault("error", {"message": phase + " external deadline after receipt flush"})
            stream.seek(0)
            stream.truncate()
            store(stream, receipt)
    return child_code == 0 and receipt["finalization"] == "passed"


def main(args: list[str]) -> int:
    if len(args) == 2:
        phase, manifest_sha = args
        return 0 if supervise(LIVE_DIR, phase, manifest_sha) else 2
    require(len(args) == 4 and args[0] == "_child", "expected capture|analysis and preparation SHA-256")
    _, phase, manifest_sha, started = args
    attempt = parse_json(paths(LIVE_DIR, phase)["attempt"].read_bytes())
    same(attempt, {"phase": phase, "preparation_sha256": manifest_sha}, "parent attempt")

    from ariadna_split_inputs import load_inputs

    factory = None
    if phase == "capture":
        from ariadna_split_capture import native_adapter

        factory = native_adapter
    return 0 if run_phase(
        LIVE_DIR, phase, float(started), execution="live",
        input_loader=lambda check: load_inputs(ROOT, check),
        pin_loader=lambda check: prep_pin(ROOT, manifest_sha, check),
        adapter_factory=factory,
    ) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except FAILURES as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
