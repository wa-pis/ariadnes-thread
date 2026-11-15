"""Run one synthetic fixed-command worksheet under a shared deadline."""

from hashlib import sha256
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
from time import monotonic_ns
from types import ModuleType
from typing import Any
from uuid import uuid4

type Row = dict[str, Any]

HERE = Path(__file__).resolve()
CORE = HERE.with_name("0208-seed-worksheet.py")
ORACLE = HERE.with_name("0208-seed-oracle.py")
IO = HERE.with_name("0206-readiness-runner.py")
IO_SHA256 = "ff1cd800a74f40f3bc91f74550c4b49205713f391d436e37360e92a9740c1a1e"
WALL_S = 15
NS = 10**9
INPUT_CAP = 512 * 2**10
OUTPUT_CAP = 128 * 2**10
SMALL_RECORD_CAP = 4096
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
PROPOSAL = "synthetic-command-proposal"
STATUSES = (PROPOSAL, "command-seed-unavailable", "invalid-evidence")
PROFILE = dict(synthetic=True, live_authorized=False, physical_launch_authorized=False,
               physical_status="physical-join-not-established",
               physical_residuals=dict.fromkeys(("epoch_s", "position_m", "velocity_m_s", "mass_kg")),
               spice_queries=0, kernel_accesses=0, force_evaluations=0, integrations=0,
               retained_archive_reads=0, r559c_attempts=0, r560_attempts=0)


def _need(ok: object, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _elapsed(started_ns: int, wall_ns: int) -> int:
    elapsed_ns = monotonic_ns() - started_ns
    _need(0 <= elapsed_ns < wall_ns, "synthetic seed deadline")
    return elapsed_ns


def _load(path: Path, source: bytes, name: str) -> ModuleType:
    module = ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(source, str(path), "exec"), vars(module))
    return module


def _io() -> ModuleType:
    # Reuse only the pinned bounded-read/exclusive-write primitives.
    fd = os.open(IO, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        entry = os.fstat(stream.fileno())
        _need(stat.S_ISREG(entry.st_mode) and entry.st_size <= 32 * 2**10, "seed I/O helper type or size")
        raw = stream.read(32 * 2**10 + 1)
    _need(sha256(raw).hexdigest() == IO_SHA256, "seed I/O helper hash")
    return _load(IO, raw, "_seed_io")


def _sources(io: ModuleType, pin: str) -> tuple[Row, bytes, bytes]:
    core = io._read(CORE, INPUT_CAP)
    oracle = io._read(ORACLE, INPUT_CAP)
    identity = dict(stage="R5.59b", mode="synthetic", fixture_sha256=pin,
                    runner_sha256=io._sha(io._read(HERE, INPUT_CAP)), core_sha256=io._sha(core),
                    oracle_sha256=io._sha(oracle), io_sha256=IO_SHA256)
    return identity, core, oracle


def _guard(fixture: Path, output: Path) -> None:
    allowed = {os.path.normpath(p) for p in (HERE, CORE, ORACLE, IO, fixture, output, output.parent,
                                             *(output / name for name in FILES))}
    stdlib = str(Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}") + os.sep

    def deny(event: str, args: tuple[Any, ...]) -> None:
        if event == "import":
            name = str(args[0]).split(".", 1)[0]
            _need(name in sys.stdlib_module_names and name not in {"ctypes", "_ctypes"},
                  f"out-of-scope import: {name}")
        elif event == "open" and not isinstance(args[0], int):
            name = os.path.normpath(os.fsdecode(args[0]))
            reading = not int(args[2]) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            _need(name in allowed or (reading and name.startswith(stdlib) and
                                      name.endswith((".py", ".pyc", ".so"))),
                  f"out-of-scope file: {Path(name).name}")
        else:
            _need(event not in {"subprocess.Popen", "os.system", "socket.__new__",
                                "ctypes.dlopen", "os.fork", "os.exec", "os.posix_spawn"},
                  f"out-of-scope operation: {event}")

    sys.addaudithook(deny)


def _command_words(status: str, words: object) -> None:
    if status != PROPOSAL:
        _need(words is None, "unexpected synthetic command")
        return
    if not isinstance(words, list) or len(words) != 6 or any(type(word) is not str for word in words):
        raise ValueError("six synthetic command words required")
    try:
        values = [float.fromhex(word) for word in words]
    except (ValueError, OverflowError) as error:
        raise ValueError("invalid synthetic command word") from error
    _need(all(math.isfinite(value) and value.hex() == word for value, word in zip(values, words, strict=True)),
          "noncanonical synthetic command word")
    a_d, e_d, tau_d, a_a, e_a, tau_a = values
    _need(-math.pi <= a_d < math.pi and -math.pi <= a_a < math.pi
          and abs(e_d) <= math.pi / 2 and abs(e_a) <= math.pi / 2
          and tau_d > 0 and tau_a > 0, "synthetic command domain")


def _files(output: Path, io: ModuleType, names: tuple[str, ...]) -> list[tuple[Row, str]]:
    with os.scandir(output) as entries:
        found = {entry.name for _, entry in zip(range(len(names) + 1), entries)}
    _need(found == set(names), "synthetic evidence absent, late or incomplete")
    remaining = OUTPUT_CAP
    records: list[tuple[Row, str]] = []
    for name in names:
        raw = io._read(output / name, remaining)
        row = io._row(raw)
        _need(io._wire(row) == raw, "noncanonical synthetic evidence")
        records.append((row, io._sha(raw)))
        remaining -= len(raw)
    return records


def _audit(records: list[tuple[Row, str]], identity: Row) -> tuple[Row, str, str, int, int]:
    (attempt, a_sha), (report, r_sha), (receipt, c_sha) = records
    for row in (attempt, report, receipt):
        _need(all(row.get(k) == v for k, v in identity.items()), "synthetic source or fixture binding")
    run_id = attempt.get("run_id")
    _need(type(run_id) is str and len(run_id) == 32 and all(c in "0123456789abcdef" for c in run_id)
          and run_id == report.get("run_id") == receipt.get("run_id")
          and a_sha == report.get("attempt_sha256") == receipt.get("attempt_sha256")
          and r_sha == receipt.get("report_sha256"), "synthetic evidence hash binding")
    wall, before = attempt.get("wall_ns"), receipt.get("elapsed_before_receipt_ns")
    _need(type(wall) is int and type(before) is int and 0 <= before < wall <= 15 * NS,
          "synthetic result deadline")
    status = report.get("status")
    _need(status in STATUSES and status == receipt.get("status")
          and all(type(report.get(k)) is type(v) and report[k] == v for k, v in PROFILE.items()),
          "synthetic result status or work count")
    _need("command_words" in report, "missing synthetic command field")
    _command_words(status, report["command_words"])
    if status != "invalid-evidence":
        size = report.get("fixture_bytes")
        _need(type(size) is int and 0 < size <= INPUT_CAP
              and report.get("actual_fixture_sha256") == identity["fixture_sha256"], "evaluated fixture binding")
    return report, c_sha, run_id, wall, before


def _child(fixture: Path, pin: str, output: Path, run_id: str, started_ns: int, wall_ns: int) -> int:
    _need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "seed child isolation")
    _need(0 < wall_ns <= 15 * NS, "invalid synthetic seed budget")
    _guard(fixture, output)
    io = _io()
    io._pin(pin)
    identity, core, oracle = _sources(io, pin)
    header = identity | dict(run_id=run_id)
    _elapsed(started_ns, wall_ns)
    output.mkdir(mode=0o700)
    io._sync(output.parent)
    a_sha = io._put(output / FILES[0], header | dict(wall_ns=wall_ns), SMALL_RECORD_CAP)
    actual_sha, fixture_bytes = None, None
    try:
        raw = io._read(fixture, INPUT_CAP)
        actual_sha, fixture_bytes = io._sha(raw), len(raw)
        _need(actual_sha == pin, "fixture SHA-256 mismatch")
        oracle_mod = _load(ORACLE, oracle, "_seed_oracle")
        verdict = _load(CORE, core, "_seed_core").evaluate(raw, pin, oracle_mod)
        _need(isinstance(verdict, dict) and verdict.get("status") in STATUSES[:2],
              "unrecognized synthetic seed verdict")
        _need("command_words" in verdict, "missing synthetic command field")
        _command_words(verdict["status"], verdict["command_words"])
        _need(len(io._wire(verdict)) <= OUTPUT_CAP - 4 * SMALL_RECORD_CAP, "synthetic report byte cap")
    except (OSError, ValueError, OverflowError, RecursionError) as error:
        verdict = dict(status="invalid-evidence", command_words=None, error=f"{type(error).__name__}: {error}"[:512])
    report = verdict | header | PROFILE | dict(attempt_sha256=a_sha, actual_fixture_sha256=actual_sha,
                                             fixture_bytes=fixture_bytes)
    _elapsed(started_ns, wall_ns)
    r_sha = io._put(output / FILES[1], report, OUTPUT_CAP - 3 * SMALL_RECORD_CAP)
    receipt = header | dict(attempt_sha256=a_sha, report_sha256=r_sha, status=report["status"],
                            elapsed_before_receipt_ns=_elapsed(started_ns, wall_ns))
    c_sha = io._put(output / FILES[2], receipt, SMALL_RECORD_CAP)
    # Audit saved bytes independently of the evaluator result under the same watchdog.
    audited, checked_sha, checked_id, checked_wall, _ = _audit(_files(output, io, FILES[:3]), identity)
    _need(c_sha == checked_sha and run_id == checked_id and wall_ns == checked_wall, "saved seed audit binding")
    exit_code = 0 if audited["status"] == PROPOSAL else 2
    io._put(output / FILES[3], dict(run_id=run_id, receipt_sha256=c_sha, exit_code=exit_code,
                                    elapsed_through_readback_ns=_elapsed(started_ns, wall_ns)), SMALL_RECORD_CAP)
    _elapsed(started_ns, wall_ns)
    return exit_code


def verify_result(output: Path, expected_sha256: str, *, expected_completion_sha256: str | None = None) -> Row:
    """Authenticate finalized bytes without recomputing any synthetic branch."""
    io = _io()
    io._pin(expected_sha256)
    identity, _, _ = _sources(io, expected_sha256)
    files = _files(output, io, FILES)
    report, receipt_sha, run_id, wall, before = _audit(files[:3], identity)
    completion, digest = files[3]
    completed = completion.get("elapsed_through_readback_ns")
    _need(completion.get("receipt_sha256") == receipt_sha and completion.get("run_id") == run_id
          and type(completed) is int and before <= completed < wall
          and type(completion.get("exit_code")) is int
          and completion["exit_code"] == (0 if report["status"] == PROPOSAL else 2), "synthetic completion binding")
    if expected_completion_sha256 is not None:
        io._pin(expected_completion_sha256)
        _need(digest == expected_completion_sha256, "completion SHA-256 mismatch")
    return report


def _discard_late_witness(output: Path, run_id: str) -> None:
    # Delete only this invocation's completion, leaving prior/partial evidence available.
    witness = output / FILES[3]
    try:
        io = _io()
        if io._row(io._read(witness, SMALL_RECORD_CAP)).get("run_id") == run_id:
            witness.unlink()
    except (OSError, ValueError):
        pass


def launch(fixture: Path, expected_sha256: str, output: Path) -> bool:
    """Watch a single isolated worker through calculation, finalization and readback."""
    started_ns = monotonic_ns()
    wall_ns = int(WALL_S * NS)
    _need(0 < wall_ns <= 15 * NS, "invalid synthetic seed budget")
    run_id = uuid4().hex
    output = output.absolute()
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(HERE), "child", str(fixture.absolute()),
             expected_sha256, str(output), run_id, str(started_ns), str(wall_ns)],
            timeout=(wall_ns - _elapsed(started_ns, wall_ns)) / NS,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
        _elapsed(started_ns, wall_ns)
        if completed.returncode in (0, 2):
            return completed.returncode == 0
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    _discard_late_witness(output, run_id)
    return False


def main(args: list[str]) -> int:
    if len(args) == 7 and args[0] == "child":
        _, fixture, pin, output, run_id, started, wall = args
        return _child(Path(fixture), pin, Path(output), run_id, int(started), int(wall))
    if len(args) == 3:
        fixture, pin, output = args
        return 0 if launch(Path(fixture), pin, Path(output)) else 2
    raise ValueError("usage: seed-runner FIXTURE_JSON EXPECTED_SHA256 OUTPUT_DIRECTORY")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(3 if sys.argv[1:2] == ["child"] else 2) from None
