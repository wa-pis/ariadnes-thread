"""Qualify the R5.59e phase screen using only fabricated archived evidence."""

from collections.abc import Callable
from hashlib import sha256
import json
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
WALL_S = 30
NS = 10**9
INPUT_CAP = 128*1024
OUTPUT_CAP = 4*1024*1024
SMALL = 4096
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
SCHEMA = "ariadna-r559e-phase-evidence-v1"
PROTECTED = HERE.with_name("0211-r559c")
PROTECTED_PINS = frozenset((
    "8df6fdaa9e1ecdb75d1e9def89d14da51dde6b34817065836d9b9bfda26570f5",
    "421fb33a5ba76750e5524cd9734e2729f4e222b8a7838bd44fc8edfd86e29781",
    "627396cd7ba4e4934fda33c8c62fa611c0b7918fed74c035f568e4a222ab4189",
    "bb0e6bf9eddcd77aebf698f2c8a55d339e2e84d91d6ce6df4166b3f2519d82b5",
))
METHODS = {
    "io": ("0206-readiness-runner.py", "ff1cd800a74f40f3bc91f74550c4b49205713f391d436e37360e92a9740c1a1e"),
    "core": ("0208-seed-worksheet.py", "4907db44f0ef53cb657cd563a6fa27df8a138442807c703a66c1343bde4788ba"),
    "oracle": ("0208-seed-oracle.py", "cf4041c69e5204f79ab6786be5e393c0dbc0977317e693587eb1a85e8265e475"),
    "previous": ("0210-retained-runner.py", "77043cd3e4323d0af272d173d35cc0bbf18fa8275791e004c57963d39cee19df"),
    "reader": ("0210-retained-readback.py", "a6e1b9a32f0c46c9e03974c1367a8b04d2849eca86d807907a3bcefa1f0e8920"),
    "orbit": ("0213-phase-orbit.py", None),
    "screen": ("0213-phase-screen.py", None),
    "runner": (HERE.name, None),
}
FLAGS = dict(synthetic=True, spice_queries=0, kernel_accesses=0, force_evaluations=0, integrations=0,
             r559f_attempts=0, r560_attempts=0, live_authorized=False, physical_launch_authorized=False,
             physical_status="physical-join-not-established")


def _need(ok: object, why: str) -> None:
    if not ok:
        raise ValueError(f"R5.59e: {why}")


def _elapsed(started: int, wall: int) -> int:
    elapsed = monotonic_ns()-started
    _need(0 <= elapsed < wall <= 30*NS, "shared deadline")
    return elapsed


def _io() -> ModuleType:
    return _load("io", _raw_io())


def _raw_io() -> bytes:
    name, pin = METHODS["io"]
    # Authenticate the bounded I/O primitives before loading other experiment bytes.
    fd = os.open(HERE.with_name(name), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        _need(stat.S_ISREG(info.st_mode) and info.st_size <= 64*1024, "I/O method file")
        raw = stream.read(64*1024+1)
    _need(len(raw) == info.st_size and sha256(raw).hexdigest() == pin, "I/O method pin")
    return raw


def _load(name: str, raw: bytes) -> ModuleType:
    module = ModuleType("_r559e_"+name)
    module.__file__ = str(HERE.with_name(METHODS[name][0]))
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, "exec"), vars(module))
    return module


def _methods(io: ModuleType) -> dict[str, bytes]:
    raw = {key: io._read(HERE.with_name(filename), 64*1024) for key, (filename, _) in METHODS.items()}
    _need(all(pin is None or io._sha(raw[key]) == pin for key, (_, pin) in METHODS.items()), "method pin")
    return raw


def _pins(pins: dict[str, str], io: ModuleType) -> None:
    _need(set(pins) == set(FILES) and not (set(pins.values()) & PROTECTED_PINS), "artificial archive pins")
    for value in pins.values():
        io._pin(value)


def _guard(source: Path, output: Path) -> list[str]:
    inputs = {str(source/name): name for name in FILES}
    methods = {str(HERE.with_name(name)) for name, _ in METHODS.values()}
    outputs = {str(output/name) for name in FILES}
    stdlib = str(Path(sys.base_prefix)/"lib"/f"python{sys.version_info.major}.{sys.version_info.minor}")+os.sep
    opened: list[str] = []

    def deny(event: str, args: tuple[Any, ...]) -> None:
        if event == "import":
            root = str(args[0]).split(".", 1)[0]
            _need(root in sys.stdlib_module_names and root not in {"ctypes", "_ctypes"}, f"out-of-scope import {root}")
        elif event == "open" and not isinstance(args[0], int):
            name = os.path.normpath(os.fsdecode(args[0]))
            read = not int(args[2]) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            if name in inputs:
                _need(read and inputs[name] not in opened, "artificial archives must be opened at most once")
                opened.append(inputs[name])
            else:
                _need(name in outputs or (read and (name in methods or name in {str(output), str(output.parent)}
                      or (name.startswith(stdlib) and name.endswith((".py", ".pyc", ".so"))))),
                      f"out-of-scope file {Path(name).name}")
        else:
            _need(event not in {"subprocess.Popen", "os.system", "os.fork", "os.exec", "os.posix_spawn",
                                "socket.__new__", "ctypes.dlopen"}, f"out-of-scope event {event}")

    sys.addaudithook(deny)
    return opened


def _archive(source: Path, pins: dict[str, str], io: ModuleType, previous: ModuleType, reader: ModuleType,
             check: Callable[[], None]) -> tuple[Row, int]:
    records = []
    size = 0
    with os.scandir(source) as entries:
        _need({x.name for _, x in zip(range(len(FILES)+1), entries)} == set(FILES), "archive inventory")
    for name in FILES:
        check()
        raw = io._read(source/name, INPUT_CAP-size)
        digest, entry = io._sha(raw), io._row(raw)
        _need(digest == pins[name] and raw == io._wire(entry), f"{name}: source hash or encoding")
        size += len(raw)
        records.append((entry, digest))
    attempt = records[0][0]
    expected = dict(schema="ariadna-r559c-evidence-v1", stage="R5.59c", mode="artificial",
                    candidate_id="artificial-moon-mars", arithmetic="local-point-mass-impulse-surrogate")
    for key in ("epoch_words", "source_pins", "source_sha256", "command_order"):
        expected[key] = attempt[key]
    report, receipt, _ = previous._audit(records[:3], expected, io, reader)
    witness = records[3][0]
    elapsed, code = witness["elapsed_through_readback_ns"], witness["exit_code"]
    _need(witness["run_id"] == attempt["run_id"] and witness["receipt_sha256"] == receipt
          and type(code) is int and code == 2 and type(elapsed) is int
          and records[2][0]["elapsed_before_receipt_ns"] <= elapsed < attempt["wall_ns"], "archive completion")
    return report, size


def _identity(raw: dict[str, bytes], pins: dict[str, str], io: ModuleType) -> Row:
    return FLAGS | dict(schema=SCHEMA, stage="R5.59e", mode="artificial", source_pins=pins,
                        source_sha256={name: io._sha(data) for name, data in raw.items()})


def _files(output: Path, names: tuple[str, ...], io: ModuleType) -> list[tuple[Row, str]]:
    with os.scandir(output) as entries:
        _need({x.name for _, x in zip(range(len(names)+1), entries)} == set(names), "incomplete evidence")
    records = []
    for name in names:
        cap = OUTPUT_CAP-3*SMALL if name == "report.json" else SMALL
        raw = io._read(output/name, cap)
        row = io._row(raw)
        _need(io._wire(row) == raw, "evidence encoding")
        records.append((row, io._sha(raw)))
    return records


def _code(status: str) -> int:
    return 0 if status == "artificial-phase-proposal" else 2 if status in ("no-eligible-pair-on-grid", "inconclusive") else 3


def _audit(records: list[tuple[Row, str]], identity: Row, screen: ModuleType, reader: ModuleType,
           check: Callable[[], None]) -> tuple[Row, str, str, int, int]:
    (attempt, a_sha), (report, r_sha), (receipt, c_sha) = records
    run_id = attempt["run_id"]
    _need(type(run_id) is str and len(run_id) == 32 and all(c in "0123456789abcdef" for c in run_id),
          "attempt identifier")
    for row in (attempt, report, receipt):
        _need(row["run_id"] == run_id and all(type(row.get(k)) is type(v) and row[k] == v for k, v in identity.items()),
              "source, method or authority binding")
    _need(a_sha == report["attempt_sha256"] == receipt["attempt_sha256"]
          and r_sha == receipt["report_sha256"] and report["status"] == receipt["status"], "evidence chain")
    wall, duration = attempt["wall_ns"], receipt["elapsed_before_receipt_ns"]
    _need(type(wall) is int and type(duration) is int and 0 <= duration < wall <= 30*NS, "receipt deadline")
    opened = report["archive_open_attempts"]
    _need(isinstance(opened, list) and opened == list(FILES[:len(opened)]), "archive open inventory")
    if report["status"] != screen.INVALID:
        _need(opened == list(FILES) and type(report["source_bytes"]) is int
              and 0 < report["source_bytes"] <= INPUT_CAP, "successful archive byte cap")
    screen.audit(report, reader, check)
    return report, c_sha, run_id, wall, duration


def _child(source: Path, pins: dict[str, str], output: Path, run_id: str, started: int, wall: int) -> int:
    _need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "worker requires -I -S -B")
    _elapsed(started, wall)
    source, output = source.resolve(), output.absolute()
    _need(source != PROTECTED and output.resolve() != PROTECTED and not output.resolve().is_relative_to(source),
          "artificial source/destination")
    opened = _guard(source, output)
    io = _io()
    _pins(pins, io)
    raw = _methods(io)
    reader, previous, core, oracle, orbit, screen = (_load(name, raw[name]) for name in
                                                     ("reader", "previous", "core", "oracle", "orbit", "screen"))
    identity = _identity(raw, pins, io)
    header = identity | dict(run_id=run_id)

    def check() -> None:
        _elapsed(started, wall)

    check()
    output.mkdir(mode=0o700)
    io._sync(output.parent)
    a_sha = io._put(output/FILES[0], header | dict(wall_ns=wall), SMALL)
    work = dict(phase_positions=0, mars_roots=0, pairs=0)
    rows: list[Row] = []
    size = None
    ref = None
    try:
        before, size = _archive(source, pins, io, previous, reader, check)
        ref = screen.reference(before)
        result = screen.scan(ref, core=core, oracle=oracle, orbit=orbit, check=check, rows=rows, work=work)
    except (OSError, ValueError, TypeError, KeyError, ArithmeticError, RecursionError) as error:
        result = dict(status=screen.INVALID, selected=None, command_words=None, error=f"{type(error).__name__}: {error}"[:512])
    report = result | header | dict(attempt_sha256=a_sha, source_bytes=size, archive_open_attempts=opened,
                                    reference=ref, work=work, rows=rows)
    check()
    r_sha = io._put(output/FILES[1], report, OUTPUT_CAP-3*SMALL)
    c_sha = io._put(output/FILES[2], header | dict(status=report["status"], attempt_sha256=a_sha,
                    report_sha256=r_sha, elapsed_before_receipt_ns=_elapsed(started, wall)), SMALL)
    saved, checked, saved_id, saved_wall, _ = _audit(_files(output, FILES[:3], io), identity, screen, reader, check)
    _need((checked, saved_id, saved_wall) == (c_sha, run_id, wall), "saved readback binding")
    code = _code(saved["status"])
    io._put(output/FILES[3], dict(run_id=run_id, receipt_sha256=c_sha, exit_code=code,
                                 elapsed_through_readback_ns=_elapsed(started, wall)), SMALL)
    check()
    return code


def verify_result(output: Path, pins: dict[str, str], *, expected_completion_sha256: str | None = None) -> Row:
    """Recheck saved artificial evidence without reopening input archives."""
    started = monotonic_ns()
    io = _io()
    _pins(pins, io)
    _need(output.resolve() != PROTECTED, "artificial evidence only")
    raw = _methods(io)
    reader, screen = (_load(name, raw[name]) for name in ("reader", "screen"))
    records = _files(output, FILES, io)
    report, receipt, run_id, wall, before = _audit(
        records[:3], _identity(raw, pins, io), screen, reader, lambda: _elapsed(started, 30*NS))
    complete, digest = records[3]
    value = complete["elapsed_through_readback_ns"]
    _need(complete["run_id"] == run_id and complete["receipt_sha256"] == receipt
          and type(value) is int and before <= value < wall
          and type(complete["exit_code"]) is int and complete["exit_code"] == _code(report["status"]), "completion")
    if expected_completion_sha256 is not None:
        _need(digest == expected_completion_sha256, "completion hash")
    return report


def _discard_late_witness(output: Path, run_id: str) -> None:
    try:
        io = _io()
        witness = output/FILES[3]
        if io._row(io._read(witness, SMALL)).get("run_id") == run_id:
            witness.unlink()
            io._sync(output)
    except (OSError, ValueError):
        pass


def launch(source: Path, pins: dict[str, str], output: Path) -> int:
    """Run one isolated artificial worker underneath the shared parent watchdog."""
    started = monotonic_ns()
    wall = int(WALL_S*NS)
    source, output = source.resolve(), output.absolute()
    _need(source != PROTECTED and output.resolve() != PROTECTED and not output.resolve().is_relative_to(source),
          "artificial source/destination")
    _pins(pins, _io())
    if os.path.lexists(output):
        return 3
    run_id = uuid4().hex
    try:
        process = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(HERE), "child", str(source), json.dumps(pins), str(output),
             run_id, str(started), str(wall)], timeout=(wall-_elapsed(started, wall))/NS,
            stdin=subprocess.DEVNULL, check=False,
        )
        _elapsed(started, wall)
        if process.returncode in (0, 2, 3):
            return process.returncode
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    _discard_late_witness(output, run_id)
    return 3


def main(args: list[str]) -> int:
    if len(args) == 7 and args[0] == "child":
        _, source, pins, output, run_id, started, wall = args
        return _child(Path(source), json.loads(pins), Path(output), run_id, int(started), int(wall))
    raise ValueError("private R5.59e artificial worker only")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, TypeError, KeyError, ArithmeticError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(4) from None
