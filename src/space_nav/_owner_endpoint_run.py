"""Private ADR0267 process controls; qualification uses injected workers only.

A same-clock external supervisor must cover this parent's cold import and opaque
I/O through fsync. The local watcher also supervises process groups with exited
leaders; no native run is authorized by importing this module.
"""

from __future__ import annotations

from collections.abc import Sequence
import importlib.abc
import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
from typing import Any

from ._coupled_benchmark_run import RunError, _install_import_guard

INPUT_BYTES = 64 * 1024
PRODUCER_BYTES = 1024 * 1024
AUDIT_BYTES = 512 * 1024
LOG_BYTES = 64 * 1024
EVIDENCE_BYTES = 2 * 1024 * 1024
REPORT_BYTES = 64 * 1024
_INPUT = {"schema": "ariadna-owner-fixture-input-v1", "scope": "synthetic-owner-conformance-only"}


def _now() -> float:
    value = time.monotonic()
    if type(value) not in (int, float) or not math.isfinite(value):
        raise RunError("finite monotonic clock required")
    return float(value)


def _check(deadline_s: float, minimum_s: float) -> float:
    now = _now()
    if now < minimum_s:
        raise RunError("monotonic clock moved backwards")
    if now >= deadline_s:
        raise RunError("absolute deadline exhausted")
    return now


def _json_bytes(value: object) -> bytes:
    try:
        return (json.dumps(value, allow_nan=False, sort_keys=True) + "\n").encode()
    except (TypeError, ValueError, RecursionError) as exc:
        raise RunError("finite bounded JSON required") from exc


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RunError("duplicate JSON field")
        result[key] = value
    return result


def _decode(raw: bytes, limit: int) -> dict[str, Any]:
    if type(raw) is not bytes or len(raw) > limit:
        raise RunError("input bytes exceed fixed byte cap")
    try:
        value = json.loads(raw, object_pairs_hook=_unique)
        _json_bytes(value)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise RunError("invalid finite JSON") from exc
    if not isinstance(value, dict):
        raise RunError("JSON object required")
    return value


def _read(path: Path, limit: int) -> dict[str, Any]:
    with path.open("rb") as stream:
        return _decode(stream.read(limit + 1), limit)


class _Evidence:
    """Account streamed stdout separately from the combined two-worker stderr."""

    def __init__(self, directory: Path, log_cap: int = LOG_BYTES) -> None:
        self.log_cap = log_cap
        self.directory = directory
        self.used: dict[str, int] = {}
        self.structured = 0
        self.logs = 0
        self.caps = {"input.json": INPUT_BYTES, "producer.json": PRODUCER_BYTES,
                     "audit.json": AUDIT_BYTES, "receipt.json": REPORT_BYTES,
                     "producer.stderr.log": LOG_BYTES, "audit.stderr.log": LOG_BYTES}

    def write(self, path: Path, data: bytes) -> None:
        name = path.name
        if path.parent != self.directory or name not in self.caps:
            raise RunError("unknown evidence path")
        is_log = name.endswith(".log")
        used = self.used.get(name, 0)
        reserve = 0 if name == "receipt.json" else REPORT_BYTES
        remaining = min(self.caps[name] - used,
                        self.log_cap - self.logs if is_log else EVIDENCE_BYTES - reserve - self.structured)
        retained = data[:max(0, remaining)]
        with path.open("ab" if name in self.used else "xb") as stream:
            stream.write(retained)
        self.used[name] = used + len(retained)
        if is_log:
            self.logs += len(retained)
        else:
            self.structured += len(retained)
        if len(retained) != len(data):
            raise RunError("streamed log byte cap" if is_log else "structured evidence byte cap")


def _watch_worker(command: Sequence[str], output: Path, errors: Path,
                  deadline_s: float, evidence: _Evidence, *,
                  inherited_group: bool = False) -> dict[str, object]:
    """Kill the entire child group even when its leader has already exited."""
    last = _check(deadline_s, 0.0)
    began = last
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=not inherited_group)
    assert process.stdout is not None and process.stderr is not None
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, output)
            selector.register(process.stderr, selectors.EVENT_READ, errors)
            while selector.get_map():
                last = _check(deadline_s, last)
                for key, _ in selector.select(min(0.05, deadline_s - last)):
                    data = os.read(key.fileobj.fileno(), 8192)
                    if data:
                        evidence.write(key.data, data)
                    else:
                        selector.unregister(key.fileobj)
            last = _check(deadline_s, last)
            try:
                code = process.wait(timeout=deadline_s - last)
            except subprocess.TimeoutExpired as exc:
                raise RunError("worker stalled after closing pipes") from exc
            last = _check(deadline_s, last)
        return {"exit_code": code, "elapsed_s": last - began}
    finally:
        try:
            if inherited_group:
                if process.poll() is None:
                    process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        finally:
            process.wait(timeout=1.0)
            process.stdout.close()
            process.stderr.close()


def _worker_command(kind: str, source: Path, started_s: float, deadline_s: float) -> list[str]:
    return [sys.executable, "-m", "space_nav._owner_endpoint_run", "--worker", kind,
            str(source), repr(started_s), repr(deadline_s)]


def _sync(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def run(raw: bytes, directory: Path, *, started_s: float | None = None,
        inherited_group: bool = False) -> dict[str, object]:
    """Use a fresh namespace once; external supervision must bound parent I/O.

    The default worker command is the proposed native F18.3 path. F18.2 tests
    replace it with artificial subprocesses; this function is not run natively.
    """
    entered = _now()
    if inherited_group and (os.getpid() != os.getpgrp() or os.getpid() != os.getsid(0)):
        raise RunError("inherited workers require isolated supervised parent session")
    if _decode(raw, INPUT_BYTES) != _INPUT:
        raise RunError("fixed owner-fixture input mismatch")
    if started_s is None:
        started_s = entered
    if (type(started_s) not in (int, float) or not math.isfinite(started_s)
            or started_s > entered):
        raise RunError("parent start must be finite past monotonic time")
    started_s = float(started_s)
    last = _check(started_s + 60.0, entered)
    # No directory or evidence from an earlier attempt is reused.
    directory.mkdir(parents=False, exist_ok=False)
    evidence = _Evidence(directory, LOG_BYTES - 2048 if inherited_group else LOG_BYTES)
    source = directory / "input.json"
    report: dict[str, Any] = {
        "schema": "ariadna-owner-run-v1", "status": "failed", "failure": None,
        "physical_admission": "unavailable", "workers": [], "producer_mode": None,
        "parent_started_s": started_s, "startup_elapsed_s": entered - started_s,
        "limits": {"total_s": 60, "producer_finish_s": 45, "audit_s": 10,
                   "audit_finish_s": 55, "finalization_reserve_s": 5,
                   "input_bytes": INPUT_BYTES, "logs_bytes": LOG_BYTES,
                   "structured_evidence_bytes": EVIDENCE_BYTES},
        "finalization": "pending-after-fsync-observation",
    }
    try:
        evidence.write(source, raw)
        _sync(source)
        last = _check(started_s + 45.0, last)
        for kind, input_path, cutoff in (("produce", source, started_s + 45.0),
                                         ("audit", directory / "producer.json", started_s + 55.0)):
            if kind == "audit":
                cutoff = min(last + 10.0, cutoff)
            output = directory / ("producer.json" if kind == "produce" else "audit.json")
            errors = directory / ("producer.stderr.log" if kind == "produce" else "audit.stderr.log")
            evidence.write(output, b"")
            evidence.write(errors, b"")
            worker = _watch_worker(_worker_command(kind, input_path, started_s, cutoff),
                                   output, errors, cutoff, evidence, inherited_group=inherited_group)
            report["workers"].append({"kind": kind, **worker})
            last = _check(cutoff, last)
            packet = _read(output, PRODUCER_BYTES if kind == "produce" else AUDIT_BYTES)
            if worker["exit_code"] != 0 or packet.get("status") != "passed":
                raise RunError(str(packet.get("failure") or packet.get("error") or f"{kind} failed")[:2048])
            if kind == "produce":
                if (packet.get("schema") != "ariadna-owner-fixture-v1"
                        or packet.get("mode") not in {"native", "injected"}):
                    raise RunError("producer contract mismatch")
                report["producer_mode"] = packet["mode"]
            elif (packet.get("schema") != "ariadna-owner-audit-v1"
                  or packet.get("mode") != report["producer_mode"]
                  or packet.get("physical_admission") != "unavailable"
                  or type(packet.get("calls_checked")) is not int or packet["calls_checked"] != 8
                  or type(packet.get("analytic_arcs_checked")) is not int or packet["analytic_arcs_checked"] != 2):
                raise RunError("independent audit contract mismatch")
        report["status"] = "passed"
    except (RunError, OSError, ValueError, TypeError) as exc:
        report["failure"] = f"{type(exc).__name__}: {exc}"[:2048]
    report["structured_bytes_before_receipt"] = evidence.structured
    report["log_bytes"] = evidence.logs
    evidence.write(directory / "receipt.json", _json_bytes(report))
    try:
        for path in directory.iterdir():
            _sync(path)
            last = _check(started_s + 60.0, last)
    except (RunError, OSError, ValueError) as exc:
        report["status"] = "failed"
        report["failure"] = report["failure"] or f"{type(exc).__name__}: {exc}"[:2048]
        report["finalization"] = "failed-after-fsync"
    else:
        report["finalization"] = "checked-after-fsync"
    report["structured_bytes"] = evidence.structured
    report["elapsed_at_last_valid_check_s"] = last - started_s
    return report


def _parent_command(source: Path, directory: Path, started_s: float) -> list[str]:
    return [sys.executable, "-m", "space_nav._owner_endpoint_run", "--parent",
            str(source), str(directory), repr(started_s)]


def run_isolated(raw: bytes, directory: Path, *, started_s: float | None = None) -> dict[str, object]:
    """Supervise the cold parent and all inherited worker descendants once.

    Opaque supervisor I/O still requires caller supervision. Native work is
    stopped before the supervisor records its own final receipt, even on failure.
    """
    entered = _now()
    if _decode(raw, INPUT_BYTES) != _INPUT:
        raise RunError("fixed owner-fixture input mismatch")
    if started_s is None:
        started_s = entered
    if (type(started_s) not in (int, float) or not math.isfinite(started_s)
            or started_s > entered):
        raise RunError("parent start must be finite past monotonic time")
    started_s = float(started_s)
    last = _check(started_s + 60.0, entered)
    directory.mkdir(parents=False, exist_ok=False)
    evidence = _Evidence(directory, 2048)
    evidence.caps["producer.json"] = REPORT_BYTES
    source, output, errors = (directory / n for n in
                              ("input.json", "producer.json", "producer.stderr.log"))
    report: dict[str, Any] = {"schema": "ariadna-owner-supervisor-v1", "status": "failed",
                              "failure": None, "parent": None,
                              "physical_admission": "unavailable",
                              "finalization": "pending-after-fsync-observation"}
    try:
        evidence.write(source, raw)
        _sync(source)
        last = _check(started_s + 60.0, last)
        evidence.write(output, b"")
        evidence.write(errors, b"")
        worker = _watch_worker(_parent_command(source, directory / "packet", started_s),
                               output, errors, started_s + 60.0, evidence)
        # The entire parent/worker group is gone before any supervisor recording.
        report["worker"] = worker
        last = _check(started_s + 60.0, last)
        parent = _read(output, REPORT_BYTES)
        report["parent"] = parent
        if (worker["exit_code"] != 0 or parent.get("schema") != "ariadna-owner-run-v1"
                or parent.get("status") != "passed"
                or parent.get("finalization") != "checked-after-fsync"
                or parent.get("physical_admission") != "unavailable"):
            raise RunError("cold parent failed/unfinalized")
        report["status"] = "passed"
    except (RunError, OSError, ValueError, TypeError) as exc:
        report["failure"] = f"{type(exc).__name__}: {exc}"[:2048]
    evidence.write(directory / "receipt.json", _json_bytes(report))
    try:
        for path in directory.iterdir():
            if path.is_file():
                _sync(path)
                last = _check(started_s + 60.0, last)
    except (RunError, OSError, ValueError) as exc:
        report["status"] = "failed"
        report["failure"] = report["failure"] or f"{type(exc).__name__}: {exc}"[:2048]
        report["finalization"] = "failed-after-fsync"
    else:
        report["finalization"] = "checked-after-fsync"
    report["elapsed_at_last_valid_check_s"] = last - started_s
    return report


def _install_audit_guard() -> None:
    _install_import_guard(True)
    forbidden = "space_nav._owner_endpoint_fixture"
    if forbidden in sys.modules:
        raise RunError("independent auditor already imported producer")

    class NoProducer(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname: str, path: object = None,
                      target: object = None) -> None:
            if fullname == forbidden or fullname.startswith(forbidden + "."):
                raise ImportError("independent auditor forbids owner producer")

    sys.meta_path.insert(0, NoProducer())


def _worker(kind: str, source: Path, started_s: float, deadline_s: float) -> int:
    _check(deadline_s, started_s)
    if kind == "produce":
        if deadline_s > started_s + 45.0:
            raise RunError("producer deadline exceeds fixed phase")
        if _read(source, INPUT_BYTES) != _INPUT:
            raise RunError("fixed input mismatch")
        from ._owner_endpoint_fixture import Budget, produce
        budget = Budget(started_s)
        from ._native_arc_conformance import _guard_spice, _source_guard
        sys.addaudithook(lambda event, args: _source_guard(budget, event, args))
        from tudatpy.interface import spice
        _guard_spice(budget, spice)
        result = produce(budget=budget)
        limit = PRODUCER_BYTES
    else:
        if deadline_s > started_s + 55.0 or deadline_s > _now() + 10.0:
            raise RunError("audit deadline exceeds fixed phase")
        _install_audit_guard()
        from ._owner_endpoint_audit import audit
        result = audit(_read(source, PRODUCER_BYTES), deadline_s=deadline_s)
        if {"tudatpy", "numpy", "scipy", "spiceypy", "space_nav._owner_endpoint_fixture"} & set(sys.modules):
            raise RunError("independent auditor imported producer/scientific runtime")
        limit = AUDIT_BYTES
    raw = _json_bytes(result)
    if len(raw) > limit:
        raise RunError("worker output byte partition")
    _check(deadline_s, started_s)
    sys.stdout.buffer.write(raw)
    return 0 if result.get("status") == "passed" else 2


def main(argv: Sequence[str] | None = None) -> int:
    """Private worker entry only; no automatic native qualification command."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == 4 and args[0] == "--parent":
        try:
            with Path(args[1]).open("rb") as stream:
                raw = stream.read(INPUT_BYTES + 1)
            report = run(raw, Path(args[2]), started_s=float(args[3]), inherited_group=True)
            sys.stdout.buffer.write(_json_bytes(report))
            return 0 if report["status"] == "passed" else 2
        except (RunError, OSError, ValueError, TypeError) as exc:
            sys.stderr.write(f"{type(exc).__name__}: {str(exc)[:1024]}\n")
            return 2
    if len(args) != 5 or args[0] != "--worker" or args[1] not in {"produce", "audit"}:
        raise RunError("private worker requires kind/input/inherited start/deadline")
    try:
        started, deadline = (float(value) for value in args[3:])
        if not math.isfinite(started) or not math.isfinite(deadline):
            raise RunError("finite inherited clock required")
        return _worker(args[1], Path(args[2]), started, deadline)
    except (RunError, OSError, ValueError, TypeError, RuntimeError) as exc:
        sys.stderr.write(f"{type(exc).__name__}: {str(exc)[:1024]}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
