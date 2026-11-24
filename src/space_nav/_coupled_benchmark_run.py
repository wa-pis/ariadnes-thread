"""Private, bounded ADR0248 artificial qualification; never a mission CLI."""

from __future__ import annotations

import argparse
import builtins
from collections.abc import Mapping, Sequence
from hashlib import sha256
import importlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import selectors
import signal
import subprocess
import sys
import time
from typing import Any

INPUT_BYTES = 64 * 1024
EVIDENCE_BYTES = 2 * 1024 * 1024
REPORT_RESERVE = 16 * 1024
PRODUCER_SECONDS = 210.0
AUDIT_SECONDS = 60.0
AUDIT_FINISH_SECONDS = 270.0
TOTAL_SECONDS = 300.0


class RunError(RuntimeError):
    """A fixed process, input or evidence boundary prevented qualification."""


def _check_time(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise RunError("monotonic deadline exhausted")


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, allow_nan=False, sort_keys=True) + "\n").encode()


def _read_packet(path: Path, limit: int) -> dict[str, Any]:
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise RunError(f"{path.name}: input exceeds {limit} bytes")
    value = json.loads(data, parse_constant=_reject_constant)
    _json_bytes(value)
    if not isinstance(value, dict):
        raise RunError(f"{path.name}: expected a JSON object")
    return value


def _reject_constant(value: str) -> None:
    raise RunError(f"nonfinite JSON number: {value}")


class _Evidence:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.used = 0

    def write(self, path: Path, data: bytes) -> None:
        available = EVIDENCE_BYTES - REPORT_RESERVE - self.used
        retained = data[:max(available, 0)]
        with path.open("ab") as stream:
            stream.write(retained)
        self.used += len(retained)
        if len(retained) != len(data):
            raise RunError("combined result/audit/log evidence byte cap exhausted")


def _worker_command(kind: str, source: Path, deadline: float) -> list[str]:
    return [sys.executable, "-m", "space_nav._coupled_benchmark_run",
            "--worker", kind, str(source), "--deadline", repr(deadline)]


def _watch_worker(command: Sequence[str], output: Path, errors: Path,
                  deadline: float, evidence: _Evidence) -> dict[str, object]:
    _check_time(deadline)
    started = time.monotonic()
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    assert process.stdout is not None and process.stderr is not None
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, output)
            selector.register(process.stderr, selectors.EVENT_READ, errors)
            while selector.get_map():
                _check_time(deadline)
                for key, _ in selector.select(max(0.0, min(0.05, deadline - time.monotonic()))):
                    data = os.read(key.fileobj.fileno(), 8192)
                    if data:
                        evidence.write(key.data, data)
                    else:
                        selector.unregister(key.fileobj)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RunError("worker exceeded its absolute deadline")
            try:
                returncode = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired as exc:
                raise RunError("worker stalled after closing output") from exc
            _check_time(deadline)
        return {"exit_code": returncode,
                "elapsed_s": time.monotonic() - started}
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=1.0)
        process.stdout.close()
        process.stderr.close()


def _install_import_guard(auditor: bool) -> None:
    original = builtins.__import__
    denied = ("tudatpy", "spiceypy", "cspyce", "space_nav.research_propagation")
    if auditor:
        denied += ("numpy", "scipy", "space_nav._coupled_benchmark",
                   "space_nav.trajectory", "space_nav.ephemeris")

    def guarded(name: str, globals: Mapping[str, Any] | None = None,
                locals: Mapping[str, Any] | None = None,
                fromlist: Sequence[str] = (), level: int = 0) -> Any:
        resolved = name
        if level and globals:
            resolved = importlib.util.resolve_name("." * level + name,
                                                   globals["__package__"])
        requested = [resolved] + [resolved + "." + item for item in fromlist or ()]
        if any(candidate == item or candidate.startswith(item + ".")
               for candidate in requested for item in denied):
            raise ImportError(f"artificial benchmark forbids import {resolved}")
        return original(name, globals, locals, fromlist, level)

    class ImportGuard:
        def find_spec(self, fullname: str, path: object = None,
                      target: object = None) -> None:
            if any(fullname == item or fullname.startswith(item + ".")
                   for item in denied):
                raise ImportError(f"artificial benchmark forbids import {fullname}")

    sys.meta_path.insert(0, ImportGuard())
    builtins.__import__ = guarded


def _worker(kind: str, source: Path, deadline: float) -> int:
    _check_time(deadline)
    _install_import_guard(kind == "audit")
    packet = _read_packet(source, INPUT_BYTES if kind == "producer" else EVIDENCE_BYTES)
    if kind == "producer":
        from . import _coupled_benchmark as implementation
        expected = implementation.BenchmarkError
        operation = implementation.run
    else:
        from . import _coupled_benchmark_oracle as implementation
        expected = implementation.OracleError
        operation = implementation.audit
    try:
        result = operation(packet, deadline=deadline)
        _check_time(deadline)
    except (expected, RunError) as exc:
        result = {"status": "failed", "error_type": type(exc).__name__,
                  "error": str(exc), "counts": getattr(exc, "counts", None)}
        sys.stdout.buffer.write(_json_bytes(result))
        return 2
    sys.stdout.buffer.write(_json_bytes(result))
    return 0


def _validate_candidate(packet: Mapping[str, Any], reference: object) -> None:
    required = {"controls", "shooting_nodes", "initial_defects", "defects",
                "arc_start_states", "arc_end_states", "witness", "recovered",
                "counts", "solver"}
    if (packet.get("schema") != "ariadna-coupled-synthetic-v1"
            or packet.get("frame") != "SYNTHETIC_INERTIAL"
            or packet.get("time_scale") != "elapsed_seconds"
            or packet.get("reference") != reference or not required <= packet.keys()):
        raise RunError("producer packet violates the fixed benchmark contract")


def _counts(path: Path) -> object:
    try:
        return _read_packet(path, EVIDENCE_BYTES).get("counts")
    except (OSError, ValueError, RunError):
        return None


def run(directory: Path, *, started: float | None = None) -> dict[str, object]:
    """Run in a new directory; an outer monotonic start includes cold startup."""
    entered = time.monotonic()
    if started is None:
        started = entered
    if (isinstance(started, bool) or not isinstance(started, (int, float))
            or not math.isfinite(started) or started > entered):
        raise RunError("parent start must be a finite past monotonic time")
    _check_time(started + TOTAL_SECONDS)
    directory.mkdir(parents=False, exist_ok=False)
    evidence = _Evidence(directory)
    report: dict[str, object] = {
        "schema": "ariadna-coupled-run-v1", "status": "failed", "failure": None,
        "scope": "artificial numerical diagnostic; no F0 feasibility or physical error bound",
        "frame": "SYNTHETIC_INERTIAL", "time_scale": "elapsed_seconds",
        "parent_started_monotonic_s": started, "startup_elapsed_s": entered - started,
        "limits": {"overall_s": TOTAL_SECONDS, "producer_finish_s": PRODUCER_SECONDS,
                   "audit_s": AUDIT_SECONDS, "audit_finish_s": AUDIT_FINISH_SECONDS,
                   "input_bytes": INPUT_BYTES, "evidence_bytes": EVIDENCE_BYTES,
                   "producer_residual_calls": 400, "producer_synthetic_arcs": 1206,
                   "producer_rhs_attempts": 1000000, "audit_synthetic_arcs": 12,
                   "audit_rhs_attempts": 300000},
        "runtime": {"python": platform.python_version(),
                    "implementation": platform.python_implementation(),
                    "numpy": None, "scipy": None},
        "workers": {}, "producer_counts": None, "audit_counts": None,
        "source_sha256": {},
    }
    try:
        report["runtime"].update(numpy=version("numpy"), scipy=version("scipy"))
        if (report["runtime"]["python"], report["runtime"]["numpy"],
                report["runtime"]["scipy"]) != ("3.12.14", "1.26.4", "1.17.1"):
            raise RunError("benchmark requires pinned Python3.12.14/NumPy1.26.4/SciPy1.17.1")
        for name in ("_coupled_benchmark_run", "_coupled_benchmark",
                     "_coupled_benchmark_oracle", "trajectory"):
            source = Path(__file__).with_name(name + ".py")
            report["source_sha256"][name] = sha256(source.read_bytes()).hexdigest()
        _check_time(started + PRODUCER_SECONDS)
        from . import _coupled_benchmark_oracle
        reference = _coupled_benchmark_oracle.reference()
        _check_time(started + PRODUCER_SECONDS)
        reference_data = _json_bytes(reference)
        if len(reference_data) > INPUT_BYTES:
            raise RunError("explicit fixture/config exceeds 64 KiB")
        reference_path = directory / "reference.json"
        evidence.write(reference_path, reference_data)
        for kind, source, deadline in (
            ("producer", reference_path, started + PRODUCER_SECONDS),
            ("audit", directory / "producer.json", started + AUDIT_FINISH_SECONDS),
        ):
            if kind == "audit":
                deadline = min(deadline, time.monotonic() + AUDIT_SECONDS)
            output = directory / f"{kind}.json"
            report["workers"][kind] = _watch_worker(
                _worker_command(kind, source, deadline), output,
                directory / f"{kind}.stderr.log", deadline, evidence)
            _check_time(deadline)
            if report["workers"][kind]["exit_code"] != 0:
                raise RunError(f"{kind} worker failed; see retained output/stderr")
            packet = _read_packet(output, EVIDENCE_BYTES)
            if packet.get("status") != "passed":
                raise RunError(f"{kind} worker did not provide passed qualification")
            if kind == "producer":
                _validate_candidate(packet, reference)
            elif (packet.get("schema") != "ariadna-coupled-audit-v1"
                  or packet.get("frame") != "SYNTHETIC_INERTIAL"
                  or packet.get("time_scale") != "elapsed_seconds"
                  or packet.get("controls") != _read_packet(source, EVIDENCE_BYTES)["controls"]):
                raise RunError("audit packet violates the fixed benchmark contract")
        _check_time(started + AUDIT_FINISH_SECONDS)
        report["status"] = "passed"
    except (RunError, OSError, ValueError) as exc:
        report["failure"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        unexpected = sys.exception()
        if unexpected is not None and report["failure"] is None:
            report["failure"] = {"type": type(unexpected).__name__,
                                 "message": str(unexpected)}
            report["status"] = "failed"
        report["producer_counts"] = _counts(directory / "producer.json")
        report["audit_counts"] = _counts(directory / "audit.json")
        report["elapsed_s"] = time.monotonic() - started
        if report["elapsed_s"] >= TOTAL_SECONDS:
            report["status"] = "failed"
            if report["failure"] is None:
                report["failure"] = {"type": "RunError", "message": "overall deadline exhausted"}
        report_path = directory / "report.json"
        report["evidence_bytes"] = evidence.used
        for _ in range(3):
            report["evidence_bytes"] = evidence.used + len(_json_bytes(report))
        data = _json_bytes(report)
        if len(data) > REPORT_RESERVE:
            raise RunError("reserved final report byte cap exhausted")
        with report_path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if time.monotonic() >= started + TOTAL_SECONDS:
            report["status"] = "failed"
            if report["failure"] is None:
                report["failure"] = {"type": "RunError", "message": "durable report deadline exhausted"}
            report["elapsed_s"] = time.monotonic() - started
            for _ in range(3):
                report["evidence_bytes"] = evidence.used + len(_json_bytes(report))
            with report_path.open("wb") as stream:
                stream.write(_json_bytes(report))
                stream.flush()
                os.fsync(stream.fileno())
            raise RunError("durable report deadline exhausted")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    entered = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_or_input", type=Path)
    parser.add_argument("--worker", choices=("producer", "audit"), help=argparse.SUPPRESS)
    parser.add_argument("--deadline", type=float, help=argparse.SUPPRESS)
    parser.add_argument("--parent-start", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        if args.parent_start is not None:
            parser.error("--parent-start belongs to the parent, not a worker")
        if args.deadline is None or not math.isfinite(args.deadline):
            parser.error("worker requires a finite absolute --deadline")
        try:
            return _worker(args.worker, args.output_or_input, args.deadline)
        except (RunError, OSError, ValueError, ImportError) as exc:
            sys.stdout.buffer.write(_json_bytes({"status": "failed", "counts": None,
                "error_type": type(exc).__name__, "error": str(exc)}))
            return 2
    if args.deadline is not None:
        parser.error("--deadline is private to workers")
    try:
        report = run(args.output_or_input,
                     started=entered if args.parent_start is None else args.parent_start)
    except (OSError, RunError) as exc:
        print(f"artificial qualification failed: {exc}", file=sys.stderr)
        return 2
    print(f"artificial qualification {report['status']}: {args.output_or_input / 'report.json'}")
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
