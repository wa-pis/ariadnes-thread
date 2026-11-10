"""ADR0169's once-only offline screen; imports perform no scientific work."""
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
    sys.path[:0] = [str(HERE), str(HERE.parent / "0167")]

from ariadna_split_common import (
    FAILURES, Recorder, digest, encode, journal_rows, number, parse_json, require, same, wire,
)
from ariadna_split_run import finish, record_failure, store

BUDGET_S = 10.0
WATCHDOG_S = 15.0
CAPS = {"observation": 28, "reference_epoch": 29, "record": 58, "binary64_field": 28, "decimal_field": 224}
LIVE_DIR = Path("/private/tmp/ariadna-r524")
PINNED_PYTHON = Path("/opt/homebrew/Caskroom/miniforge/base/envs/space-nav/bin/python")
MANIFEST = "docs/adr/experiments/0170-verification.json"
DESIGN_INPUTS = "docs/adr/experiments/0169-inputs.json"
DESIGN_SHA256 = "9a983ef4af96b4458559869fd4e35fdff4aabcbeb20135f4d2d373e99777eb93"
TESTED = {
    *(f"docs/adr/experiments/0170/ariadna_frozen_moon_{name}.py" for name in ("inputs", "math", "run")),
    *(f"tests/test_frozen_moon_{name}.py" for name in ("inputs", "math", "run")),
}
REUSED = {f"docs/adr/experiments/0167/ariadna_split_{name}.py"
          for name in ("common", "analysis", "capture", "inputs", "run")}
FORBIDDEN = {"spiceypy", "tudatpy", "numpy", "scipy", "space_nav"}


def require_offline() -> None:
    require(not any(name.split(".", 1)[0] in FORBIDDEN for name in sys.modules),
            "screen must use a fresh standard-library-only process")


def prep_pin(root: Path, manifest_sha: str, check: Callable[[], Any]) -> dict[str, Any]:
    check()
    raw = (root / MANIFEST).read_bytes()
    require(sha256(raw).hexdigest() == manifest_sha, "R5.23 preparation manifest SHA-256")
    proof = parse_json(raw)
    require(proof["preparation_complete"] is True, "R5.23 preparation not verified")
    require(proof["design_inputs_sha256"] == DESIGN_SHA256 == digest(root / DESIGN_INPUTS),
            "ADR0169 input inventory hash")
    tested, reused = proof["tested_source_sha256"], proof["reused_source_sha256"]
    require(set(tested) == TESTED and set(reused) == REUSED, "prepared source inventory")
    for name, sha in (tested | reused).items():
        check()
        require(digest(root / name) == sha, "tested or reused source hash: " + name)
    check()
    return {"preparation_sha256": manifest_sha, "design_inputs_sha256": DESIGN_SHA256,
            "tested_source_sha256": tested, "reused_source_sha256": reused}


def verify_bound_inputs(root: Path, identity: dict[str, Any], check: Callable[[], Any]) -> None:
    """Rehash the bound archives without opening SPK or repeating arithmetic."""
    hashes = identity["archive_and_evidence_sha256"]
    require(hashes and identity["inputs_sha256"] == DESIGN_SHA256, "screen archive identity")
    for name, expected in hashes.items():
        check()
        require(digest(root / name) == expected, "screen final archive hash: " + name)
    check()


def paths(directory: Path) -> dict[str, Path]:
    return {part: directory / f"screen.{suffix}" for part, suffix in {
        "report": "json", "journal": "ledger.jsonl", "receipt": "receipt.json",
        "attempt": "attempt.json", "parent": "parent-receipt.json",
    }.items()}


def within_budget(value: Any, field: str) -> float:
    elapsed_s = number(value, field)
    require(0 <= elapsed_s <= BUDGET_S, field)
    return elapsed_s


def read_saved(directory: Path, execution: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate durable evidence and finalization without recalculating fields."""
    files = paths(directory)
    receipt = parse_json(files["receipt"].read_bytes())
    require(receipt["finalization"] == "passed", "screen child finalization")
    for part in ("report", "journal"):
        same(receipt[part + "_sha256"], digest(files[part]), "screen " + part + " hash")
    report = parse_json(files["report"].read_bytes())
    same([report["contract"], report["execution"], report["budget_s"]],
         ["ADR0169", execution, BUDGET_S], "screen contract")
    require(report["status"] in ("passed", "failed"), "screen status")
    same([report["native_calls"], report["new_record_acquisitions"], report["propagations"],
          report["r517_requalified"]], [0, 0, 0, False], "screen scope")
    same(receipt["status"], report["status"], "screen receipt status")
    same(receipt["external_start_s"], report["external_start_s"], "screen receipt start")
    first = within_budget(report["child_start_elapsed_s"], "screen child start")
    last = within_budget(report["elapsed_before_report_s"], "screen report deadline")
    flushed = within_budget(receipt["elapsed_before_receipt_s"], "screen receipt deadline")
    require(first <= last <= flushed, "screen receipt timeline")
    counts = {op: dict.fromkeys(("attempted", "returned", "completed"), 0) for op in CAPS}
    cursor = first
    saved_rows = []
    for i, entry in enumerate(report["ledger"]):
        operation = entry["operation"]
        require(operation in CAPS, "screen ledger operation")
        expected = {"operation", "api", "args", "attempted_s"}
        if "raw" in entry:
            expected.update(("raw", "returned_s"))
            if "completed_s" in entry:
                expected.add("completed_s")
        require(set(entry) == expected, "screen ledger entry fields")
        for key, count in (("attempted_s", "attempted"), ("returned_s", "returned"), ("completed_s", "completed")):
            if key in entry:
                stamp = number(entry[key], "screen event stamp")
                require(cursor <= stamp <= last, "screen ledger timeline")
                cursor = stamp
                counts[operation][count] += 1
        saved_rows.extend(journal_rows(i, entry))
    require(all(c["attempted"] <= CAPS[op] for op, c in counts.items()), "screen ledger limits")
    same(report["counts"], counts, "screen recomputed counts")
    require(files["journal"].read_bytes() == b"".join(map(encode, saved_rows)), "screen durable journal mismatch")
    if report["status"] == "passed":
        same(counts, {op: dict.fromkeys(("attempted", "returned", "completed"), count)
                      for op, count in CAPS.items()}, "screen completed counts")
        require("error" not in report and not report["unavailable"], "screen passed report incomplete")
        same(report["final_identity_pin"], report["identity_pin"], "screen final pin")
        if execution == "archived":
            require(report["final_archive_identity_complete"] is True, "screen final archive identity")
        rows = report["rows"]
        require(report["numerical_passed"] is True and len(rows) == CAPS["observation"]
                and all(row["status"] == "passed" for row in rows), "screen row verdicts")
        same(report["epoch_counts"], {"rounded": 19, "exact": 19, "union": 29}, "screen epoch inventory")
        require(sum(row["source_mode"] == "measured" for row in rows) == 7
                and sum(row["source_mode"] == "proxy" for row in rows) == 21
                and sum(row.get("control", {}).get("passed") is True for row in rows) == 3,
                "screen measured/proxy and control verdicts")
    else:
        require("error" in report, "screen failed report lacks earliest failure")
    return report, receipt


def run_screen(
    directory: Path, start_s: float, *, execution: str,
    input_loader: Callable[[Callable[[], Any]], dict[str, Any]],
    pin_loader: Callable[[Callable[[], Any]], dict[str, Any]],
    clock: Callable[[], float] = monotonic, boot_s: float = PROCESS_START,
) -> bool:
    from ariadna_frozen_moon_math import analyze

    files = paths(directory)
    require(execution in ("archived", "synthetic"), "screen execution mode")
    require(all(not files[key].exists() for key in ("report", "journal", "receipt")), "existing screen evidence")
    report: dict[str, Any] = {
        "contract": "ADR0169", "execution": execution, "status": "pending",
        "external_start_s": start_s, "child_start_elapsed_s": wire(boot_s - start_s),
        "rows": [], "unavailable": ["screen"],
        "native_calls": 0, "new_record_acquisitions": 0, "propagations": 0, "r517_requalified": False,
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
            recorder.check()
            pin = pin_loader(recorder.check)
            report["identity_pin"] = pin
            stage = "archived inputs"
            bundle = input_loader(recorder.check)
            if "identity" in bundle:
                report["input_identity"] = bundle["identity"]
            recorder.check()
            stage = "numerical screen"
            analyze(bundle, report, recorder)
            require(report["status"] in ("passed", "failed"), "missing screen verdict")
            if report["status"] == "passed":
                same(report["counts"], {op: dict.fromkeys(("attempted", "returned", "completed"), n)
                                        for op, n in CAPS.items()}, "screen did not complete the fixed sample")
            stage = "final preparation identity"
            report["final_identity_pin"] = pin_loader(recorder.check)
            same(report["final_identity_pin"], pin, "screen helper/input identity changed")
            if execution == "archived":
                stage = "final archive identity"
                verify_bound_inputs(ROOT, report["input_identity"], recorder.check)
                report["final_archive_identity_complete"] = True
                require_offline()
            recorder.check()
        except FAILURES as exc:
            record_failure(report, stage, exc)
            report["execution_incomplete"] = True
        return finish(report, recorder, files, streams)


def supervise(directory: Path, manifest_sha: str) -> bool:
    require(re.fullmatch(r"[0-9a-f]{64}", manifest_sha) is not None, "preparation manifest SHA-256 required")
    require_offline()
    files = paths(directory)
    directory.mkdir(mode=0o700, exist_ok=True)
    require(not directory.is_symlink() and all(not path.exists() for path in files.values()), "existing screen evidence")
    with files["attempt"].open("x", encoding="utf-8") as marker:
        store(marker, {"contract": "ADR0169", "preparation_sha256": manifest_sha})
    start = monotonic()
    result: dict[str, Any] = {
        "contract": "ADR0169", "preparation_sha256": manifest_sha,
        "external_start_s": start, "finalization": "failed", "returncode": None,
    }
    try:
        child = subprocess.run(
            [str(PINNED_PYTHON), "-I", "-S", "-B", str(HERE / Path(__file__).name),
             "_child", manifest_sha, repr(start)], cwd=ROOT, capture_output=True,
            text=True, timeout=WATCHDOG_S, check=False,
        )
        result.update(returncode=child.returncode, stderr=child.stderr)
        report, receipt = read_saved(directory, "archived")
        same(report["external_start_s"], start, "screen parent start")
        if report["status"] == "passed":
            same(report["identity_pin"]["preparation_sha256"], manifest_sha, "screen manifest pin")
        require(child.returncode == (0 if report["status"] == "passed" else 2), "screen parent/child verdict")
        elapsed_s = within_budget(monotonic() - start, "screen external deadline")
        require(elapsed_s >= receipt["elapsed_before_receipt_s"], "screen parent timeline")
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
            result.setdefault("error", {"message": "screen deadline after parent receipt flush"})
            stream.seek(0)
            stream.truncate()
            store(stream, result)
    return result["returncode"] == 0 and result["finalization"] == "passed"


def main(args: list[str]) -> int:
    if len(args) == 1:
        return 0 if supervise(LIVE_DIR, args[0]) else 2
    require(len(args) == 3 and args[0] == "_child", "expected preparation manifest SHA-256")
    _, manifest_sha, started = args
    require(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,
            "screen child requires -I -S -B")
    marker = parse_json(paths(LIVE_DIR)["attempt"].read_bytes())
    same(marker, {"contract": "ADR0169", "preparation_sha256": manifest_sha}, "screen parent attempt")
    from ariadna_frozen_moon_inputs import load_inputs

    return 0 if run_screen(
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
