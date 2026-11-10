"""One-shot ADR0175 study and independent readback of the saved force returns."""
from __future__ import annotations

# ruff: noqa: E402 -- Time starts before importing the study and its dependencies.
from time import monotonic

PROCESS_START = monotonic()

from collections.abc import Callable, Iterator
from contextlib import ExitStack
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
if __name__ == "__main__":
    sys.path[:0] = [str(HERE.parent / n) for n in ("0176", "0173", "0170", "0167")]

from ariadna_paired_moon_inputs import INPUT_PATH, INPUT_SHA256, ORDINALS, load_inputs, verify_bound_inputs
from ariadna_paired_moon_math import CAPS, analyze
from ariadna_split_common import (
    FAILURES, Recorder, digest, encode, journal_rows, number, parse_json, require, same, wire,
)
from ariadna_split_run import finish, record_failure, store

BUDGET_S, WATCHDOG_S = 10.0, 15.0
LIVE_DIR = Path("/private/tmp/ariadna-r530")
PINNED_PYTHON = Path("/opt/homebrew/Caskroom/miniforge/base/envs/space-nav/bin/python")
MANIFEST = "docs/adr/experiments/0176-verification.json"
CONTRACT = "ADR0175"
TESTED = {
    *(f"docs/adr/experiments/0176/ariadna_paired_moon_{part}.py" for part in ("inputs", "math", "run")),
    *(f"tests/test_paired_moon_{part}.py" for part in ("inputs", "math", "run")),
}
REUSED = {
    *(f"docs/adr/experiments/0167/ariadna_split_{part}.py"
      for part in ("analysis", "capture", "common", "inputs", "run")),
    *(f"docs/adr/experiments/0170/ariadna_frozen_moon_{part}.py" for part in ("inputs", "math")),
    *(f"docs/adr/experiments/0173/ariadna_moon_holdout_{part}.py" for part in ("capture", "inputs")),
}
SCOPE = {"native_calls": 0, "new_record_acquisitions": 0, "record_evaluations": 0,
         "propagations": 0, "optimizer_calls": 0, "other_body_fields": 0, "r517_requalified": False}
COMPLETE = ("confirmed", "negative", "unresolved")
ORDER = ("observation", *("binary64_field",) * 2, *("decimal_field",) * 10)


def require_offline() -> None:
    blocked = {"tudatpy", "spiceypy", "numpy", "scipy", "space_nav"}
    require(not any(name.split(".", 1)[0] in blocked for name in sys.modules),
            "paired Moon check requires a fresh stdlib-only process")


def prep_pin(root: Path, manifest_sha: str, check: Callable[[], Any]) -> dict[str, Any]:
    check()
    path = root / MANIFEST
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == manifest_sha, "R5.29 preparation manifest SHA-256")
    proof = parse_json(raw)
    require(proof["preparation_complete"] is True, "R5.29 preparation not verified")
    require(proof["inputs_sha256"] == INPUT_SHA256 == digest(root / INPUT_PATH), "ADR0175 inventory SHA-256")
    tested, reused = proof["tested_source_sha256"], proof["reused_source_sha256"]
    require(set(tested) == TESTED and set(reused) == REUSED, "R5.29 prepared source inventory")
    for name, expected in (tested | reused).items():
        check()
        require(digest(root / name) == expected, "prepared or reused SHA-256: " + name)
    check()
    return {"preparation_sha256": manifest_sha, "inputs_sha256": INPUT_SHA256,
            "tested_source_sha256": tested, "reused_source_sha256": reused}


def paths(directory: Path) -> dict[str, Path]:
    return {key: directory / f"pair.{suffix}" for key, suffix in {
        "attempt": "attempt.json", "report": "json", "journal": "ledger.jsonl",
        "receipt": "receipt.json", "parent": "parent-receipt.json",
    }.items()}


def marker(manifest_sha: str) -> dict[str, str]:
    return {"contract": CONTRACT, "preparation_sha256": manifest_sha}


def _within(value: Any) -> float:
    stamp = number(value, "pair elapsed time")
    require(0 <= stamp <= BUDGET_S, "pair deadline")
    return stamp


def read_saved(directory: Path, execution: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify finalized evidence, including a numerical negative or a stopped prefix."""
    files = paths(directory)
    receipt = parse_json(files["receipt"].read_bytes())
    require(receipt["finalization"] == "passed", "pair child finalization")
    for part in ("report", "journal"):
        same(receipt[part + "_sha256"], digest(files[part]), "pair " + part + " hash")
    report = parse_json(files["report"].read_bytes())
    same([report["contract"], report["execution"], report["budget_s"]],
         [CONTRACT, execution, BUDGET_S], "pair contract")
    same({key: report[key] for key in SCOPE}, SCOPE, "pair scope")
    outcome = report["outcome"]
    require(outcome in (*COMPLETE, "incomplete"), "pair outcome")
    same(report["status"], "passed" if outcome == "confirmed" else "failed", "pair status")
    same(receipt["status"], report["status"], "pair receipt status")
    same(receipt["external_start_s"], report["external_start_s"], "pair receipt start")
    cursor = _within(report["child_start_elapsed_s"])
    report_time = _within(report["elapsed_before_report_s"])
    require(cursor <= report_time <= _within(receipt["elapsed_before_receipt_s"]), "pair receipt timeline")

    ledger, rows = report["ledger"], report["rows"]
    require(type(ledger) is list and type(rows) is list, "pair evidence arrays")
    ordinals = [row["observation_ordinal"] for row in rows]
    same(ordinals, list(ORDINALS[:len(rows)]), "pair observation prefix")
    complete_rows = [row for row in rows if row["outcome"] in COMPLETE]
    require(rows[:len(complete_rows)] == complete_rows and len(rows) <= len(complete_rows) + 1,
            "pair unfinished row placement")
    same(report["unavailable"], list(ORDINALS[len(complete_rows):]), "pair unavailable observations")
    if outcome == "incomplete":
        stopped = report["stopped"]
        require(type(stopped) is dict and all(type(stopped.get(key)) is str and stopped[key]
                                             for key in ("stage", "type", "message")), "pair stopped stage")
    expected = [(ordinal, op) for ordinal in ORDINALS for op in ORDER]
    require(len(ledger) <= len(expected), "pair ledger cap")
    counts = {op: dict.fromkeys(("attempted", "returned", "completed"), 0) for op in CAPS}
    journal = []
    for index, (entry, (ordinal, op)) in enumerate(zip(ledger, expected)):
        args = entry["args"]
        same([entry["operation"], entry["api"], args[0]],
             [op, "admit_frozen_pair" if op == "observation" else "moon_point_mass", ordinal],
             "pair ledger operation order")
        keys = {"operation", "api", "args", "attempted_s"}
        if "raw" in entry:
            keys.update(("raw", "returned_s"))
            if "completed_s" in entry:
                keys.add("completed_s")
        require(set(entry) == keys, "pair ledger fields")
        require("completed_s" in entry or index == len(ledger) - 1, "work after an incomplete operation")
        for field, count in (("attempted_s", "attempted"), ("returned_s", "returned"), ("completed_s", "completed")):
            if field in entry:
                stamp = number(entry[field], "pair event time")
                require(cursor <= stamp <= report_time, "pair ledger timeline")
                cursor = stamp
                counts[op][count] += 1
        journal.extend(journal_rows(index, entry))
    same(report["counts"], counts, "pair ledger counts")
    require(files["journal"].read_bytes() == b"".join(map(encode, journal)), "pair durable journal")
    if outcome in COMPLETE:
        same(counts, {op: dict.fromkeys(("attempted", "returned", "completed"), count)
                      for op, count in CAPS.items()}, "pair completion counts")
        require(not report["unavailable"] and len(report["rows"]) == len(ORDINALS), "pair missing rows")
        same(report["final_identity_pin"], report["identity_pin"], "pair final preparation")
        if execution == "archived":
            require(report["final_archive_identity_complete"] is True, "pair final archive identity")
    require(("error" in report) == (outcome != "confirmed"), "pair earliest failure")
    return report, receipt


def run_pair(
    directory: Path, start_s: float, *, execution: str,
    input_loader: Callable[[Callable[[], Any]], dict[str, Any]],
    pin_loader: Callable[[Callable[[], Any]], dict[str, Any]],
    clock: Callable[[], float] = monotonic, boot_s: float = PROCESS_START,
) -> bool:
    """Finalize one child phase; clock and loaders are injectable only for tests."""
    require(execution in ("archived", "synthetic"), "pair execution mode")
    files = paths(directory)
    require(all(not files[part].exists() for part in ("report", "journal", "receipt")), "existing pair evidence")
    report: dict[str, Any] = {
        "contract": CONTRACT, "execution": execution, "status": "failed", "outcome": "incomplete",
        "external_start_s": start_s, "child_start_elapsed_s": wire(boot_s - start_s),
        "rows": [], "unavailable": list(ORDINALS), **SCOPE,
    }
    with ExitStack() as stack:
        streams = {part: stack.enter_context(files[part].open("x", encoding="utf-8"))
                   for part in ("report", "journal", "receipt")}
        recorder = Recorder(report, CAPS, start_s, BUDGET_S, clock=clock, journal=streams["journal"])
        stage = "preparation"
        try:
            if execution == "archived":
                require_offline()
            recorder.check(boot_s - start_s)
            pin = pin_loader(recorder.check)
            report["identity_pin"] = pin
            stage = "archived inputs"
            bundle = input_loader(recorder.check)
            report["input_identity"] = bundle["identity"]
            recorder.check()
            stage = "paired force"
            analyze(bundle, report, recorder)
            require(report["outcome"] in COMPLETE, "missing complete pair verdict")
            stage = "final preparation identity"
            report["final_identity_pin"] = pin_loader(recorder.check)
            same(report["final_identity_pin"], pin, "pair preparation changed")
            if execution == "archived":
                stage = "final archive identity"
                verify_bound_inputs(ROOT, report["input_identity"], recorder.check)
                require_offline()
                report["final_archive_identity_complete"] = True
            recorder.check()
        except FAILURES as exc:
            record_failure(report, stage, exc)
            report["outcome"] = "incomplete"
            report.setdefault("stopped", {"stage": stage, "type": type(exc).__name__, "message": str(exc)})
        return finish(report, recorder, files, streams)


class _EndOfSavedWork(Exception):
    """Stop replay at a saved prefix rather than evaluate a missing field."""


class _Replay:
    def __init__(self, entries: list[dict[str, Any]]) -> None:
        self.entries: Iterator[dict[str, Any]] = iter(entries)
        self.invalid = False

    @staticmethod
    def check() -> float:
        return 0.0

    def call(self, operation: str, api: str, args: list[Any], _invoke: Callable[[], Any],
             validate: Callable[[Any], None] | None = None) -> Any:
        entry = next(self.entries, None)
        if entry is None:
            raise _EndOfSavedWork
        try:
            same([entry["operation"], entry["api"], entry["args"]], wire([operation, api, args]),
                 "pair saved operands or order")
            if "completed_s" not in entry:
                raise _EndOfSavedWork
            raw = entry["raw"]
            if operation == "decimal_field":
                require(type(raw) is list and len(raw) == 3 and all(type(x) is str for x in raw),
                        "saved Decimal Moon field")
                result = tuple(Decimal(x) for x in raw)
            elif operation == "binary64_field":
                require(type(raw) is list and len(raw) == 3 and all(type(x) is float for x in raw),
                        "saved binary64 Moon field")
                result = tuple(raw)
            else:
                same(raw, args[0], "saved admission ordinal")
                result = raw
            if validate is not None:
                validate(result)
            return result
        except FAILURES:
            self.invalid = True
            raise



def audit(directory: Path, execution: str, pin: dict[str, Any],
          bundle: dict[str, Any]) -> dict[str, Any]:
    """Check receipts and reproduce saved verdicts; do not call a field evaluator."""
    report, receipt = read_saved(directory, execution)
    files = paths(directory)
    attempt = marker(pin["preparation_sha256"])
    same(parse_json(files["attempt"].read_bytes()), attempt, "pair attempt marker")
    parent = parse_json(files["parent"].read_bytes())
    same({key: parent[key] for key in attempt}, attempt, "pair parent marker")
    same([parent["returncode"], parent["finalization"], parent["external_start_s"],
          parent["attempt_sha256"], parent["child_receipt_sha256"]],
         [0 if report["status"] == "passed" else 2, "passed", receipt["external_start_s"],
          digest(files["attempt"]), digest(files["receipt"])], "pair parent receipt binding")
    require(_within(parent["external_elapsed_s"]) >= receipt["elapsed_before_receipt_s"], "pair parent timeline")
    if "identity_pin" in report:
        same(report["identity_pin"], pin, "pair saved preparation")
    if "input_identity" in report:
        same(report["input_identity"], bundle["identity"], "pair saved input identity")
    if report["outcome"] in COMPLETE:
        require("identity_pin" in report and "input_identity" in report, "missing pair identities")
    if "final_identity_pin" in report:
        same(report["final_identity_pin"], pin, "pair saved final preparation")
    if not report["ledger"]:
        require(report["outcome"] == "incomplete" and not report["rows"], "pair missing ledger")
        same(report["error"], report["stopped"], "pair stop before work")
        return report

    require("input_identity" in report, "missing paired input identity")
    replay, reconstructed = _Replay(report["ledger"]), {}
    try:
        analyze(bundle, reconstructed, replay)
    except _EndOfSavedWork:
        require(report["outcome"] == "incomplete", "truncated pair evidence")
        if reconstructed["rows"] and reconstructed["rows"][-1]["outcome"] == "pending":
            reconstructed["rows"][-1]["outcome"] = "incomplete"
    except FAILURES:
        require(report["outcome"] == "incomplete" and "stopped" in reconstructed,
                "pair replay failed")
    require(not replay.invalid and next(replay.entries, None) is None, "invalid or unused pair ledger entries")
    if report["outcome"] in COMPLETE:
        for key in ("rows", "status", "outcome", "unavailable", "error"):
            same(report.get(key), wire(reconstructed.get(key)), "saved pair " + key)
    else:
        same(report["rows"], wire(reconstructed["rows"]), "saved pair prefix")
        if "stopped" in reconstructed:
            same(report["stopped"], wire(reconstructed["stopped"]), "saved pair stop")
        same(report["error"], wire(reconstructed.get("error", report["stopped"])), "saved pair earliest failure")
    return report


def supervise(directory: Path, manifest_sha: str) -> bool:
    """Allocate one fresh attempt and enforce the external deadline."""
    require(re.fullmatch(r"[0-9a-f]{64}", manifest_sha) is not None, "preparation manifest SHA-256 required")
    require_offline()
    directory.mkdir(mode=0o700)
    files = paths(directory)
    attempt = marker(manifest_sha)
    with files["attempt"].open("x", encoding="utf-8") as stream:
        store(stream, attempt)
    start = monotonic()
    result: dict[str, Any] = {**attempt, "finalization": "failed", "returncode": None, "external_start_s": start}
    try:
        child = subprocess.run(
            [str(PINNED_PYTHON), "-I", "-S", "-B", str(HERE / Path(__file__).name),
             "_child", manifest_sha, repr(start)],
            cwd=ROOT, capture_output=True, text=True, timeout=WATCHDOG_S, check=False,
        )
        result.update(returncode=child.returncode, stderr=child.stderr)
        report, receipt = read_saved(directory, "archived")
        same(report["external_start_s"], start, "pair parent start")
        if "identity_pin" in report:
            same(report["identity_pin"]["preparation_sha256"], manifest_sha, "pair parent preparation")
        require(child.returncode == (0 if report["status"] == "passed" else 2), "pair parent/child verdict")
        require(_within(monotonic() - start) >= receipt["elapsed_before_receipt_s"], "pair parent timeline")
        result.update(finalization="passed", attempt_sha256=digest(files["attempt"]),
                      child_receipt_sha256=digest(files["receipt"]))
    except (*FAILURES, subprocess.TimeoutExpired) as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    result["external_elapsed_s"] = monotonic() - start
    with files["parent"].open("x", encoding="utf-8") as stream:
        store(stream, result)
        elapsed_s = monotonic() - start
        if elapsed_s > BUDGET_S:
            result.update(finalization="failed", external_elapsed_s=elapsed_s)
            result.setdefault("error", {"message": "pair deadline after parent receipt flush"})
            stream.seek(0)
            stream.truncate()
            store(stream, result)
    return result["returncode"] == 0 and result["finalization"] == "passed"


def main(args: list[str]) -> int:
    require(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,
            "paired Moon check requires -I -S -B")
    require_offline()
    if len(args) == 1:
        prep_pin(ROOT, args[0], lambda: None)
        return 0 if supervise(LIVE_DIR, args[0]) else 2
    if len(args) == 3 and args[0] == "--readback":
        pin = prep_pin(ROOT, args[2], lambda: None)
        bundle = load_inputs(ROOT, lambda: None)
        report = audit(Path(args[1]), "archived", pin, bundle)
        require_offline()
        print(encode({"outcome": report["outcome"], "counts": report["counts"],
                      "unavailable": report["unavailable"]}).decode().strip())
        return 0 if report["status"] == "passed" else 2
    require(len(args) == 3 and args[0] == "_child", "expected R5.29 preparation manifest SHA-256")
    _, manifest_sha, started = args
    same(parse_json(paths(LIVE_DIR)["attempt"].read_bytes()), marker(manifest_sha), "pair child attempt")
    return 0 if run_pair(
        LIVE_DIR, float(started), execution="archived",
        input_loader=lambda check: load_inputs(ROOT, check),
        pin_loader=lambda check: prep_pin(ROOT, manifest_sha, check),
    ) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except FAILURES as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
