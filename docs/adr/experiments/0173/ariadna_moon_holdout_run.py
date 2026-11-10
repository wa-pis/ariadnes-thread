"""Run one ADR0172 capture and a separate stdlib-only analysis after approval."""
from __future__ import annotations

# ruff: noqa: E402 -- Include child startup/imports in the external deadline.
from time import monotonic
PROCESS_START = monotonic()

from collections.abc import Callable
from contextlib import ExitStack
from hashlib import sha256
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
if __name__ == "__main__":
    sys.path[:0] = [str(HERE.parent / number) for number in ("0173", "0170", "0167")]

from ariadna_moon_holdout_analysis import ANALYSIS_CAPS, analyze
from ariadna_moon_holdout_capture import CAPTURE_CAPS, capture, validate_capture
from ariadna_moon_holdout_inputs import INPUT_SHA256, load_inputs
from ariadna_split_capture import native_adapter
from ariadna_split_common import (
    BUDGETS, FAILURES, Recorder, digest, encode, journal_rows, number, parse_json, require, same, wire,
)
from ariadna_split_run import finish, record_failure, store

LIVE_DIR = Path("/private/tmp/ariadna-r527")
PINNED_PYTHON = Path("/opt/homebrew/Caskroom/miniforge/base/envs/space-nav/bin/python")
INPUTS = "docs/adr/experiments/0172-inputs.json"
MANIFEST = "docs/adr/experiments/0173-verification.json"
PARTS = ("inputs", "capture", "analysis", "run")
TESTED = {
    *(f"docs/adr/experiments/0173/ariadna_moon_holdout_{part}.py" for part in PARTS),
    *(f"tests/test_moon_holdout_{part}.py" for part in PARTS),
}
REUSED = {
    *(f"docs/adr/experiments/0167/ariadna_split_{part}.py"
      for part in ("analysis", "capture", "common", "inputs", "run")),
    "docs/adr/experiments/0170/ariadna_frozen_moon_inputs.py",
    "tests/test_split_ephemeris_capture.py",
}
CAPS = {"capture": CAPTURE_CAPS, "analysis": ANALYSIS_CAPS}
FLAGS = {"capture": ("-I", "-B"), "analysis": ("-I", "-S", "-B")}
WATCHDOGS = {"capture": 20.0, "analysis": 15.0}
FORBIDDEN = {"spiceypy", "tudatpy", "numpy", "scipy", "space_nav"}


def require_offline() -> None:
    require(not any(name.split(".", 1)[0] in FORBIDDEN for name in sys.modules),
            "holdout analysis requires a fresh standard-library-only process")


def prep_pin(root: Path, manifest_sha: str, check: Callable[[], Any]) -> dict[str, Any]:
    """Bind prepared and reused sources before using the frozen input inventory."""
    check()
    raw = (root / MANIFEST).read_bytes()
    require(sha256(raw).hexdigest() == manifest_sha, "R5.26 preparation manifest SHA-256")
    proof = parse_json(raw)
    require(proof["preparation_complete"] is True, "R5.26 preparation not verified")
    require(proof["inputs_sha256"] == INPUT_SHA256 == digest(root / INPUTS), "ADR0172 input SHA-256")
    tested, reused = proof["tested_source_sha256"], proof["reused_source_sha256"]
    require(set(tested) == TESTED and set(reused) == REUSED, "R5.26 prepared source inventory")
    for path, expected in (tested | reused).items():
        check()
        require(digest(root / path) == expected, "prepared or reused source SHA-256: " + path)
    check()
    return {"preparation_sha256": manifest_sha, "inputs_sha256": INPUT_SHA256,
            "tested_source_sha256": tested, "reused_source_sha256": reused}


def verify_bound_inputs(root: Path, identity: dict[str, Any], check: Callable[[], Any]) -> None:
    require(identity["inputs_sha256"] == INPUT_SHA256 and identity["retained_evidence_sha256"],
            "holdout archive identity")
    for path, expected in identity["retained_evidence_sha256"].items():
        check()
        require(digest(root / path) == expected, "final archive SHA-256: " + path)
    check()


def paths(directory: Path, phase: str) -> dict[str, Path]:
    require(phase in CAPS, "unknown holdout phase")
    return {part: directory / f"{phase}.{suffix}" for part, suffix in {
        "report": "json", "journal": "ledger.jsonl", "receipt": "receipt.json",
        "attempt": "attempt.json", "parent": "parent-receipt.json",
    }.items()}


def marker(phase: str, manifest_sha: str) -> dict[str, str]:
    return {"contract": "ADR0172", "phase": phase, "preparation_sha256": manifest_sha}


def within_budget(value: Any, phase: str, field: str) -> float:
    stamp = number(value, field)
    require(0 <= stamp <= BUDGETS[phase], field)
    return stamp


def read_saved(directory: Path, phase: str, execution: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Check the flushed child report and ordered raw journal without running a phase."""
    files = paths(directory, phase)
    receipt = parse_json(files["receipt"].read_bytes())
    require(receipt["finalization"] == "passed", phase + " child finalization")
    for part in ("report", "journal"):
        same(receipt[part + "_sha256"], digest(files[part]), phase + " " + part + " hash")
    report = parse_json(files["report"].read_bytes())
    same([report["contract"], report["phase"], report["execution"], report["budget_s"]],
         ["ADR0172", phase, execution, BUDGETS[phase]], "holdout contract")
    require(report["status"] in ("passed", "failed"), phase + " status")
    same(receipt["status"], report["status"], phase + " receipt status")
    same(receipt["external_start_s"], report["external_start_s"], phase + " receipt start")
    first = within_budget(report["child_start_elapsed_s"], phase, "child start")
    last = within_budget(report["elapsed_before_report_s"], phase, "report deadline")
    flushed = within_budget(receipt["elapsed_before_receipt_s"], phase, "receipt deadline")
    require(first <= last <= flushed, phase + " receipt timeline")
    counts = {op: dict.fromkeys(("attempted", "returned", "completed"), 0) for op in CAPS[phase]}
    cursor = first
    durable = []
    for index, entry in enumerate(report["ledger"]):
        op = entry["operation"]
        require(op in counts, phase + " ledger operation")
        keys = {"operation", "api", "args", "attempted_s"}
        if "raw" in entry:
            keys.update(("raw", "returned_s"))
            if "completed_s" in entry:
                keys.add("completed_s")
        require(set(entry) == keys, phase + " ledger entry fields")
        for field, count in (("attempted_s", "attempted"), ("returned_s", "returned"), ("completed_s", "completed")):
            if field in entry:
                stamp = number(entry[field], phase + " event stamp")
                require(cursor <= stamp <= last, phase + " ledger timeline")
                cursor = stamp
                counts[op][count] += 1
        durable.extend(journal_rows(index, entry))
    require(all(c["attempted"] <= CAPS[phase][op] for op, c in counts.items()), phase + " ledger cap")
    same(report["counts"], counts, phase + " recomputed counts")
    require(files["journal"].read_bytes() == b"".join(map(encode, durable)), phase + " durable journal")
    require(report["explicit_native_attempts"] ==
            (sum(c["attempted"] for c in counts.values()) if phase == "capture" and execution == "live" else 0)
            and report["new_record_acquisitions"] == report["propagations"] == 0
            and report["r517_requalified"] is False, phase + " scope")
    if report["status"] == "passed":
        same(counts, {op: dict.fromkeys(("attempted", "returned", "completed"), cap)
                      for op, cap in CAPS[phase].items()}, phase + " completed counts")
        require("error" not in report and not report["unavailable"], phase + " incomplete pass")
        same(report["final_identity_pin"], report["identity_pin"], phase + " final pin")
        if execution == "live":
            require(report["final_archive_identity_complete"] is True, phase + " final archive identity")
    else:
        require("error" in report, phase + " earliest failure missing")
    return report, receipt


def read_capture(directory: Path, execution: str, pin: dict[str, Any],
                 bundle: dict[str, Any]) -> tuple[list[list[float]], dict[str, str]]:
    """Require a qualified capture and independently replay its saved call order."""
    files = paths(directory, "capture")
    report, child = read_saved(directory, "capture", execution)
    parent = parse_json(files["parent"].read_bytes())
    manifest_sha = pin["preparation_sha256"]
    same(parse_json(files["attempt"].read_bytes()), marker("capture", manifest_sha), "capture attempt marker")
    same([parent[key] for key in ("contract", "phase", "preparation_sha256", "returncode", "finalization",
                                 "external_start_s", "attempt_sha256", "child_receipt_sha256")],
         ["ADR0172", "capture", manifest_sha, 0, "passed", child["external_start_s"],
          digest(files["attempt"]), digest(files["receipt"])], "capture parent receipt binding")
    require(within_budget(parent["external_elapsed_s"], "capture", "capture parent time") >=
            child["elapsed_before_receipt_s"], "capture parent timeline")
    require(report["status"] == "passed", "capture not qualified for analysis")
    same(report["identity_pin"], pin, "capture preparation identity")
    if execution == "live":
        same(report["input_identity"], bundle["identity"], "capture frozen input identity")
    return validate_capture(bundle, report, pin), {
        "capture_parent_sha256": digest(files["parent"]), "capture_receipt_sha256": digest(files["receipt"]),
    }


def run_phase(
    directory: Path, phase: str, start_s: float, *, execution: str,
    input_loader: Callable[[Callable[[], Any]], dict[str, Any]],
    pin_loader: Callable[[Callable[[], Any]], dict[str, Any]],
    adapter_factory: Callable[[], Any] | None = None,
    clock: Callable[[], float] = monotonic, boot_s: float = PROCESS_START,
) -> bool:
    """Run one child phase; injectable inputs and clock are for synthetic tests."""
    files = paths(directory, phase)
    require(execution in ("live", "synthetic"), "holdout execution mode")
    require((phase == "capture") == (adapter_factory is not None), "capture adapter scope")
    require(all(not files[key].exists() for key in ("report", "journal", "receipt")), "existing holdout evidence")
    report: dict[str, Any] = {
        "contract": "ADR0172", "phase": phase, "execution": execution, "status": "pending",
        "external_start_s": start_s, "child_start_elapsed_s": wire(boot_s - start_s),
        "unavailable": list(range(16)), "new_record_acquisitions": 0, "propagations": 0,
        "r517_requalified": False,
    }
    with ExitStack() as stack:
        streams = {part: stack.enter_context(files[part].open("x", encoding="utf-8"))
                   for part in ("report", "journal", "receipt")}
        recorder = Recorder(report, CAPS[phase], start_s, BUDGETS[phase], clock=clock, journal=streams["journal"])
        stage = "preparation"
        try:
            if execution == "live":
                require_offline()
            recorder.check(boot_s - start_s)
            recorder.check()
            pin = pin_loader(recorder.check)
            report["identity_pin"] = pin
            stage = "archived inputs"
            bundle = input_loader(recorder.check)
            if "identity" in bundle:
                report["input_identity"] = bundle["identity"]
            recorder.check()
            if phase == "capture":
                stage = "capture"
                require(adapter_factory is not None, "missing capture adapter")
                capture(bundle, report, recorder, adapter=adapter_factory(), identity_pin=pin)
                require(report["capture_phase"] == "complete", "incomplete capture")
                report["status"] = "passed"
            else:
                stage = "capture evidence"
                states, capture_pin = read_capture(directory, execution, pin, bundle)
                report.update(capture_pin)
                stage = "analysis"
                analyze(bundle, states, report, recorder)
                require(report["status"] in ("passed", "failed"), "missing analysis verdict")
            stage = "final preparation identity"
            report["final_identity_pin"] = pin_loader(recorder.check)
            same(report["final_identity_pin"], pin, "holdout preparation identity changed")
            if execution == "live":
                stage = "final archive identity"
                verify_bound_inputs(ROOT, report["input_identity"], recorder.check)
                report["final_archive_identity_complete"] = True
                if phase == "analysis":
                    require_offline()
            recorder.check()
        except FAILURES as exc:
            record_failure(report, stage, exc)
            report["execution_incomplete"] = True
        report["explicit_native_attempts"] = (
            sum(c["attempted"] for c in recorder.counts.values()) if phase == "capture" and execution == "live" else 0)
        return finish(report, recorder, files, streams)


def supervise(directory: Path, phase: str, manifest_sha: str) -> bool:
    """Launch and finalize one bounded child, with an exclusive attempt marker."""
    require(re.fullmatch(r"[0-9a-f]{64}", manifest_sha) is not None, "preparation manifest SHA-256 required")
    files = paths(directory, phase)
    require_offline()
    directory.mkdir(mode=0o700, exist_ok=True)
    require(not directory.is_symlink() and all(not file.exists() for file in files.values()),
            "existing holdout evidence")
    with files["attempt"].open("x", encoding="utf-8") as stream:
        store(stream, marker(phase, manifest_sha))
    start = monotonic()
    parent: dict[str, Any] = {**marker(phase, manifest_sha), "external_start_s": start,
                              "finalization": "failed", "returncode": None}
    try:
        child = subprocess.run(
            [str(PINNED_PYTHON), *FLAGS[phase], str(HERE / Path(__file__).name),
             "_child", phase, manifest_sha, repr(start)],
            cwd=ROOT, capture_output=True, text=True, timeout=WATCHDOGS[phase], check=False,
        )
        parent.update(returncode=child.returncode, stderr=child.stderr)
        report, receipt = read_saved(directory, phase, "live")
        same(report["external_start_s"], start, phase + " parent start")
        require(child.returncode == (0 if report["status"] == "passed" else 2), phase + " parent/child verdict")
        if report["status"] == "passed":
            same(report["identity_pin"]["preparation_sha256"], manifest_sha, phase + " parent preparation")
        require(within_budget(monotonic() - start, phase, "external deadline") >=
                receipt["elapsed_before_receipt_s"], phase + " parent timeline")
        parent.update(finalization="passed", attempt_sha256=digest(files["attempt"]),
                      child_receipt_sha256=digest(files["receipt"]))
    except (*FAILURES, subprocess.TimeoutExpired) as exc:
        parent["error"] = {"type": type(exc).__name__, "message": str(exc)}
    parent["external_elapsed_s"] = monotonic() - start
    with files["parent"].open("x", encoding="utf-8") as stream:
        store(stream, parent)
        elapsed_s = monotonic() - start
        if elapsed_s > BUDGETS[phase]:
            parent.update(finalization="failed", external_elapsed_s=elapsed_s)
            parent.setdefault("error", {"message": "deadline after parent receipt flush"})
            stream.seek(0)
            stream.truncate()
            store(stream, parent)
    return parent["returncode"] == 0 and parent["finalization"] == "passed"


def main(args: list[str]) -> int:
    if len(args) == 1:
        require(not LIVE_DIR.exists() and not LIVE_DIR.is_symlink(), "existing R5.27 attempt directory")
        return 0 if supervise(LIVE_DIR, "capture", args[0]) and supervise(LIVE_DIR, "analysis", args[0]) else 2
    require(len(args) == 4 and args[0] == "_child", "expected R5.26 preparation manifest SHA-256")
    _, phase, manifest_sha, started = args
    require(phase in CAPS and sys.flags.isolated and sys.flags.dont_write_bytecode
            and bool(sys.flags.no_site) == (phase == "analysis"), "holdout child interpreter flags")
    same(parse_json(paths(LIVE_DIR, phase)["attempt"].read_bytes()), marker(phase, manifest_sha),
         "holdout parent attempt")
    return 0 if run_phase(
        LIVE_DIR, phase, float(started), execution="live", input_loader=lambda check: load_inputs(ROOT, check),
        pin_loader=lambda check: prep_pin(ROOT, manifest_sha, check),
        adapter_factory=native_adapter if phase == "capture" else None,
    ) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except FAILURES as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
