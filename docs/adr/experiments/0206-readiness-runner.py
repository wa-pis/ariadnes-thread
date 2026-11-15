"""Run and authenticate one isolated R5.59 artificial metadata check."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from time import monotonic_ns
from types import ModuleType
from typing import Any
from uuid import uuid4

type Row = dict[str, Any]

HERE = Path(__file__).resolve()
CORE = HERE.with_name("0206-readiness.py")
STAGE = "R5.59"
WALL_S = 15
INPUT_CAP = 2 * 2**20
OUTPUT_CAP = 128 * 2**10
NANOSECOND = 10**9
RECEIPT_SPACE = 4096
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
STATUSES = ("synthetic-ready", "unavailable", "invalid-evidence")
ZERO_WORK = dict(spice_queries=0, kernel_accesses=0, force_evaluations=0,
                 integrations=0, r560_attempts=0)
PROFILE = dict(synthetic=True, live_authorized=False, physical_launch_authorized=False,
               physical_status="physical-join-not-established",
               physical_residuals=dict.fromkeys(("epoch_s", "position_m", "velocity_m_s", "mass_kg")))


def _need(ok: object, label: str) -> None:
    if not ok:
        raise ValueError(label)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pin(value: str) -> None:
    _need(re.fullmatch("[0-9a-f]{64}", value), "expected SHA-256")


def _read(path: Path, cap: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as f:
        entry = os.fstat(f.fileno())
        _need(stat.S_ISREG(entry.st_mode) and entry.st_size <= cap, f"{path.name}: input byte cap or file type")
        raw = f.read(cap + 1)
    _need(len(raw) <= cap and len(raw) == entry.st_size, f"{path.name}: input size changed")
    return raw


def _row(raw: bytes) -> Row:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def _wire(row: Row) -> bytes:
    return (json.dumps(row, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _sync(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _put(path: Path, row: Row, cap: int) -> str:
    raw = _wire(row)
    _need(len(raw) <= cap, f"{path.name}: output byte cap")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    _sync(path.parent)
    return _sha(raw)


def _elapsed(started: int, wall_ns: int) -> int:
    value = monotonic_ns() - started
    _need(0 <= value < wall_ns, "synthetic readiness deadline")
    return value


def _guard(fixture: Path, output: Path) -> None:
    allowed = {os.path.normpath(p) for p in (HERE, CORE, fixture, output, output.parent,
                                             *(output / name for name in FILES))}
    stdlib = str(Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}") + os.sep
    stdlib_suffixes = (".py", ".pyc", ".so")

    def deny(event: str, args: tuple[object, ...]) -> None:
        if event == "import":
            module = str(args[0]).split(".", 1)[0]
            _need(module in sys.stdlib_module_names and module != "ctypes", f"non-stdlib or native import: {module}")
        elif event == "open" and not isinstance(args[0], int):
            name = os.path.normpath(os.fsdecode(args[0]))
            reading = not int(args[2]) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            _need(name in allowed or (reading and name.startswith(stdlib) and
                                      name.endswith(stdlib_suffixes)), f"out-of-scope file: {Path(name).name}")
        else:
            _need(event not in ("ctypes.dlopen", "subprocess.Popen", "os.system", "socket.__new__"),
                  f"out-of-scope operation: {event}")

    sys.addaudithook(deny)


def _child(fixture: Path, expected_sha256: str, output: Path, run_id: str,
           started: int, wall_ns: int) -> int:
    _need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "readiness child isolation")
    _need(0 < wall_ns <= 15 * NANOSECOND, "invalid synthetic readiness budget")
    _pin(expected_sha256)
    _guard(fixture, output)
    runner_raw, core_raw = _read(HERE, INPUT_CAP), _read(CORE, INPUT_CAP)
    identity = dict(stage=STAGE, mode="synthetic", fixture_sha256=expected_sha256,
                    runner_sha256=_sha(runner_raw), core_sha256=_sha(core_raw), run_id=run_id)
    _elapsed(started, wall_ns)
    output.mkdir(mode=0o700)
    _sync(output.parent)
    attempt = identity | dict(wall_ns=wall_ns, started_ns=started)
    attempt_sha = _put(output / FILES[0], attempt, RECEIPT_SPACE)
    actual_sha, fixture_bytes = None, None
    try:
        raw = _read(fixture, INPUT_CAP)
        actual_sha, fixture_bytes = _sha(raw), len(raw)
        _need(actual_sha == expected_sha256, "fixture SHA-256 mismatch")
        module = ModuleType("r559_readiness_core")
        module.__file__ = str(CORE)
        sys.modules[module.__name__] = module
        exec(compile(core_raw, str(CORE), "exec"), vars(module))
        verdict = module.evaluate(raw, expected_sha256)
        _need(isinstance(verdict, dict) and verdict.get("status") in STATUSES[:2],
              "unrecognized synthetic verdict")
        _need(len(_wire(verdict)) <= OUTPUT_CAP - 4 * RECEIPT_SPACE, "synthetic report byte cap")
    except (OSError, ValueError, OverflowError, RecursionError) as error:
        verdict = dict(status="invalid-evidence", error=f"{type(error).__name__}: {error}"[:512])
    report = verdict | identity | ZERO_WORK | PROFILE | dict(
        attempt_sha256=attempt_sha, actual_fixture_sha256=actual_sha, fixture_bytes=fixture_bytes)
    _elapsed(started, wall_ns)
    report_sha = _put(output / FILES[1], report, OUTPUT_CAP - 3 * RECEIPT_SPACE)
    receipt = identity | dict(attempt_sha256=attempt_sha, report_sha256=report_sha, status=report["status"],
                              elapsed_before_receipt_ns=_elapsed(started, wall_ns))
    receipt_sha = _put(output / FILES[2], receipt, RECEIPT_SPACE)
    through_receipt = _elapsed(started, wall_ns)
    exit_code = 0 if report["status"] == STATUSES[0] else 2
    _put(output / FILES[3], dict(run_id=run_id, receipt_sha256=receipt_sha, exit_code=exit_code,
                               elapsed_through_receipt_ns=through_receipt), RECEIPT_SPACE)
    if monotonic_ns() - started >= wall_ns:
        (output / FILES[3]).unlink()
        _sync(output)
        return 3
    return exit_code


def verify_result(output: Path, expected_sha256: str) -> Row:
    """Read back saved evidence after the launcher exits, without evaluating the fixture again."""
    _pin(expected_sha256)
    remaining = OUTPUT_CAP
    seen: list[tuple[Row, str]] = []
    with os.scandir(output) as contents:
        names = {entry.name for _, entry in zip(range(len(FILES) + 1), contents)}
    _need(names == set(FILES), "synthetic evidence absent, late or incomplete")
    for name in FILES:
        raw = _read(output / name, remaining)
        seen.append((_row(raw), _sha(raw)))
        remaining -= len(raw)
    (attempt, a_sha), (report, r_sha), (receipt, c_sha), (completion, _) = seen
    current = dict(stage=STAGE, mode="synthetic", fixture_sha256=expected_sha256,
                   runner_sha256=_sha(_read(HERE, INPUT_CAP)), core_sha256=_sha(_read(CORE, INPUT_CAP)))
    _need(all(r.get(k) == v for r in (attempt, report, receipt) for k, v in current.items()),
          "synthetic source or fixture binding")
    _need(report.get("attempt_sha256") == receipt.get("attempt_sha256") == a_sha
          and receipt.get("report_sha256") == r_sha and completion.get("receipt_sha256") == c_sha
          and attempt.get("run_id") == report.get("run_id") == receipt.get("run_id") == completion.get("run_id"),
          "synthetic evidence hash binding")
    wall, before, completed = (attempt.get("wall_ns"), receipt.get("elapsed_before_receipt_ns"),
                               completion.get("elapsed_through_receipt_ns"))
    _need(all(type(v) is int for v in (wall, before, completed))
          and 0 <= before <= completed < wall <= 15 * NANOSECOND, "synthetic result deadline")
    status = report.get("status")
    _need(status in STATUSES and receipt.get("status") == status
          and completion.get("exit_code") == (0 if status == STATUSES[0] else 2)
          and all(type(report.get(k)) is type(v) and report[k] == v for k, v in (ZERO_WORK | PROFILE).items()),
          "synthetic result status or work count")
    if status != "invalid-evidence":
        size = report.get("fixture_bytes")
        _need(type(size) is int and 0 <= size <= INPUT_CAP
              and report.get("actual_fixture_sha256") == expected_sha256, "evaluated fixture binding")
    return report


def _discard_late_witness(output: Path, run_id: str) -> None:
    # Subprocess.run has killed and reaped a timed-out worker. Never touch older evidence.
    witness = output / FILES[3]
    try:
        if _row(_read(witness, RECEIPT_SPACE)).get("run_id") == run_id:
            witness.unlink()
    except (OSError, ValueError):
        pass


def launch(fixture: Path, expected_sha256: str, output: Path) -> bool:
    """Watch one isolated worker through receipt and witness finalization."""
    started = monotonic_ns()
    wall_ns = int(WALL_S * NANOSECOND)
    fixture, output = fixture.absolute(), output.absolute()
    _pin(expected_sha256)
    _need(0 < wall_ns <= 15 * NANOSECOND, "invalid synthetic readiness budget")
    run_id = uuid4().hex
    try:
        completed = subprocess.run([sys.executable, "-I", "-S", "-B", str(HERE), "child",
                                    str(fixture), expected_sha256, str(output), run_id, str(started), str(wall_ns)],
                                   timeout=(wall_ns - _elapsed(started, wall_ns)) / NANOSECOND,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        _elapsed(started, wall_ns)
        if completed.returncode not in (0, 2):
            _discard_late_witness(output, run_id)
            return False
        return completed.returncode == 0
    except (OSError, ValueError, subprocess.TimeoutExpired):
        _discard_late_witness(output, run_id)
        return False


def main(args: list[str]) -> int:
    if len(args) == 7 and args[0] == "child":
        _, raw_path, pin, output, run_id, started, wall = args
        return _child(Path(raw_path), pin, Path(output), run_id, int(started), int(wall))
    if len(args) == 3:
        fixture, pin, output = args
        return 0 if launch(Path(fixture), pin, Path(output)) else 2
    raise ValueError("usage: readiness-runner FIXTURE_JSON EXPECTED_SHA256 OUTPUT_DIRECTORY")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(3 if sys.argv[1:2] == ["child"] else 2) from None
