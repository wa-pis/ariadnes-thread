"""Bind ADR0211 to one isolated, offline R5.59f attempt and saved audit."""

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
type Artificial = tuple[Path, dict[str, str]]

HERE = Path(__file__).resolve()
RETAINED_SOURCE = HERE.with_name("0211-r559c")
RETAINED_OUTPUT = HERE.with_name("0215-r559f")
WALL_S = 30
NS = 10**9
INPUT_CAP = 128 * 1024
OUTPUT_CAP = 4 * 1024 * 1024
SMALL = 4096
RETAINED_PINS = {
    "attempt.json": "8df6fdaa9e1ecdb75d1e9def89d14da51dde6b34817065836d9b9bfda26570f5",
    "report.json": "421fb33a5ba76750e5524cd9734e2729f4e222b8a7838bd44fc8edfd86e29781",
    "receipt.json": "627396cd7ba4e4934fda33c8c62fa611c0b7918fed74c035f568e4a222ab4189",
    "completion.json": "bb0e6bf9eddcd77aebf698f2c8a55d339e2e84d91d6ce6df4166b3f2519d82b5",
}
FILES = tuple(RETAINED_PINS)
EPOCH_WORDS = ("0x1.d2d247f9d7e7ap+29", "0x1.d2d4a9afb54adp+29", "0x1.ded341cb4c44bp+29")
REFERENCE_SHA256 = "6b845f74881f658d2eeea28bfdde43c9190a283da5bb166644bb845c4f847c5b"
METHODS = {
    "io": ("0206-readiness-runner.py", "ff1cd800a74f40f3bc91f74550c4b49205713f391d436e37360e92a9740c1a1e"),
    "core": ("0208-seed-worksheet.py", "4907db44f0ef53cb657cd563a6fa27df8a138442807c703a66c1343bde4788ba"),
    "oracle": ("0208-seed-oracle.py", "cf4041c69e5204f79ab6786be5e393c0dbc0977317e693587eb1a85e8265e475"),
    "previous": ("0210-retained-runner.py", "77043cd3e4323d0af272d173d35cc0bbf18fa8275791e004c57963d39cee19df"),
    "reader": ("0210-retained-readback.py", "a6e1b9a32f0c46c9e03974c1367a8b04d2849eca86d807907a3bcefa1f0e8920"),
    "envelope": ("0213-phase-runner.py", "b4f3251a6691469db891a28fd40763ff737a2a9994b08cc3c23ff1015e397011"),
    "screen": ("0213-phase-screen.py", "39d59baecb394f759ef6a775ce6cca548e4828dbfef94207b47c9e048d1d0f2b"),
    "orbit": ("0213-phase-orbit.py", "ba78ca47097703cb27ed7dca8d844b9be34c61b1fee9a5668fae97db039979c3"),
    "audit": ("0214-phase-audit.py", None),
    "binding": (HERE.name, None),
}
FLAGS = dict(spice_queries=0, kernel_accesses=0, force_evaluations=0, integrations=0, r560_attempts=0,
             live_authorized=False, physical_launch_authorized=False,
             physical_status="physical-join-not-established")


def need(ok: object, reason: str) -> None:
    if not ok:
        raise ValueError(f"R5.59f: {reason}")


def _elapsed(started: int, wall: int) -> int:
    elapsed = monotonic_ns()-started
    need(0 <= elapsed < wall <= 30*NS, "shared deadline")
    return elapsed


def _load(name: str, raw: bytes) -> ModuleType:
    module = ModuleType("_r559f_"+name)
    module.__file__ = str(HERE.with_name(METHODS[name][0]))
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, "exec"), vars(module))
    return module


def _io() -> ModuleType:
    name, pin = METHODS["io"]
    fd = os.open(HERE.with_name(name), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        entry = os.fstat(stream.fileno())
        need(stat.S_ISREG(entry.st_mode) and entry.st_size <= 64*1024, "I/O method type or size")
        raw = stream.read(64*1024+1)
    need(len(raw) == entry.st_size and sha256(raw).hexdigest() == pin, "I/O method pin")
    return _load("io", raw)


def _methods(io: ModuleType, pins: dict[str, str], mode: str) -> tuple[Row, dict[str, bytes]]:
    need(set(pins) == set(FILES), "exact four archive pins")
    for pin in pins.values():
        io._pin(pin)
    raw = {name: io._read(HERE.with_name(filename), 64*1024) for name, (filename, _) in METHODS.items()}
    digests = {name: io._sha(data) for name, data in raw.items()}
    need(all(pin is None or digests[name] == pin for name, (_, pin) in METHODS.items()), "method pin")
    identity = FLAGS | dict(schema="ariadna-r559f-phase-evidence-v1", stage="R5.59f", mode=mode,
                            synthetic=mode == "artificial", r559f_attempts=int(mode == "retained"),
                            source_pins=pins, source_sha256=digests)
    return identity, raw


def _paths(output: Path, artificial: Artificial | None) -> tuple[Path, Path, dict[str, str], str]:
    dest = output.resolve()
    if artificial is None:
        need(dest == RETAINED_OUTPUT and not output.is_symlink(), "fixed retained output required")
        return RETAINED_SOURCE, dest, dict(RETAINED_PINS), "retained"
    source, pins = artificial[0].resolve(), dict(artificial[1])
    need(source not in (RETAINED_SOURCE, RETAINED_OUTPUT) and dest not in (RETAINED_SOURCE, RETAINED_OUTPUT)
         and not dest.is_relative_to(source) and not dest.is_relative_to(RETAINED_SOURCE)
         and not dest.is_relative_to(RETAINED_OUTPUT) and not set(pins.values()) & set(RETAINED_PINS.values()),
         "artificial source, destination and pins must be separate")
    return source, dest, pins, "artificial"


def _reference(source: Path, pins: dict[str, str], mode: str, io: ModuleType,
               previous: ModuleType, reader: ModuleType, screen: ModuleType,
               check: Callable[[], None]) -> tuple[Row, int]:
    with os.scandir(source) as entries:
        need({entry.name for _, entry in zip(range(len(FILES)+1), entries)} == set(FILES), "source inventory")
    records, size = [], 0
    for name in FILES:
        check()
        data = io._read(source/name, INPUT_CAP-size)
        digest, record = io._sha(data), io._row(data)
        need(io._wire(record) == data and digest == pins[name], f"{name}: source encoding or pin")
        records.append((record, digest))
        size += len(data)
    attempt = records[0][0]
    retained = mode == "retained"
    expected = dict(schema="ariadna-r559c-evidence-v1", stage="R5.59c", mode=mode,
                    candidate_id="d0001-t0035" if retained else "artificial-moon-mars",
                    arithmetic="local-point-mass-impulse-surrogate")
    for key in ("epoch_words", "source_pins", "source_sha256", "command_order"):
        expected[key] = attempt[key]
    report, receipt, _ = previous._audit(records[:3], expected, io, reader)
    completion = records[3][0]
    elapsed = completion["elapsed_through_readback_ns"]
    need(completion["run_id"] == attempt["run_id"] and completion["receipt_sha256"] == receipt
         and type(completion["exit_code"]) is int and completion["exit_code"] == 2 and type(elapsed) is int
         and records[2][0]["elapsed_before_receipt_ns"] <= elapsed < attempt["wall_ns"], "R5.59c completion")
    if not retained:
        return screen.reference(report), size
    need(tuple(report["epoch_words"]) == EPOCH_WORDS and report["status"] == "command-seed-unavailable"
         and report["reason"] == "no-eligible-pair" and report["command_words"] is None,
         "fixed R5.59c refusal")
    ref = dict(normalized=report["normalized"], lunar=report["branch_decisions"]["Moon"]["positive"],
               zero_branches=report["branch_decisions"]["Mars"],
               zero_pairs=[pair for pair in report["pairs"] if pair["roots"][0] == "positive"])
    need(io._sha(io._wire(ref)) == REFERENCE_SHA256, "retained scientific operands")
    return ref, size


def _code(status: str) -> int:
    if status in ("analytic-phase-proposal", "artificial-phase-proposal"):
        return 0
    return 2 if status in ("no-eligible-pair-on-grid", "inconclusive") else 3


def _audit(records: list[tuple[Row, str]], identity: Row, io: ModuleType, auditor: ModuleType, screen: ModuleType,
           reader: ModuleType, check: Callable[[], None]) -> tuple[Row, str, str, int, int]:
    (attempt, a_sha), (report, r_sha), (receipt, c_sha) = records
    run_id = attempt["run_id"]
    need(type(run_id) is str and len(run_id) == 32 and all(c in "0123456789abcdef" for c in run_id), "attempt id")
    for row in (attempt, report, receipt):
        need(row["run_id"] == run_id and all(type(row.get(k)) is type(v) and row[k] == v for k, v in identity.items()),
             "source, method or authority binding")
    need(a_sha == report["attempt_sha256"] == receipt["attempt_sha256"]
         and r_sha == receipt["report_sha256"] and report["status"] == receipt["status"], "report/receipt chain")
    wall, before = attempt["wall_ns"], receipt["elapsed_before_receipt_ns"]
    need(type(wall) is int and type(before) is int and 0 <= before < wall <= 30*NS, "receipt deadline")
    opened = report["archive_open_attempts"]
    need(isinstance(opened, list) and opened == list(FILES[:len(opened)]), "archive read inventory")
    ref = report["reference"]
    if ref is not None and identity["mode"] == "retained":
        need(io._sha(io._wire(ref)) == REFERENCE_SHA256, "saved frozen operands")
    if report["status"] != screen.INVALID:
        need(opened == list(FILES) and type(report["source_bytes"]) is int
             and 0 < report["source_bytes"] <= INPUT_CAP, "complete archive byte cap")
    auditor.audit(report, screen, reader, check)
    return report, c_sha, run_id, wall, before


def _child(output: Path, run_id: str, started: int, wall: int, artificial: Artificial | None) -> int:
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "worker requires -I -S -B")
    _elapsed(started, wall)
    source, dest, pins, mode = _paths(output, artificial)
    io = _io()
    # The pinned envelope supplies the same explicit open allowlist as the qualified artificial worker.
    name, pin = METHODS["envelope"]
    data = io._read(HERE.with_name(name), 64*1024)
    need(io._sha(data) == pin, "envelope pin")
    envelope = _load("envelope", data)
    envelope.METHODS = METHODS
    opened = envelope._guard(source, dest)
    identity, raw = _methods(io, pins, mode)
    reader, previous, core, oracle, orbit, screen, auditor = (_load(name, raw[name]) for name in
        ("reader", "previous", "core", "oracle", "orbit", "screen", "audit"))
    head = identity | dict(run_id=run_id)

    def check() -> None:
        _elapsed(started, wall)

    check()
    dest.mkdir(mode=0o700)
    io._sync(dest.parent)
    a_sha = io._put(dest/FILES[0], head | dict(wall_ns=wall), SMALL)
    work = dict(phase_positions=0, mars_roots=0, pairs=0)
    rows: list[Row] = []
    ref = size = None
    try:
        ref, size = _reference(source, pins, mode, io, previous, reader, screen, check)
        result = screen.scan(ref, core=core, oracle=oracle, orbit=orbit, check=check, rows=rows, work=work)
        if mode == "retained" and result["status"] == screen.PROPOSAL:
            result["status"] = "analytic-phase-proposal"
    except (OSError, ValueError, TypeError, KeyError, ArithmeticError, RecursionError) as error:
        result = dict(status=screen.INVALID, selected=None, command_words=None, error=f"{type(error).__name__}: {error}"[:512])
    report = result | head | dict(attempt_sha256=a_sha, source_bytes=size, archive_open_attempts=opened,
                                   reference=ref, work=work, rows=rows)
    check()
    r_sha = io._put(dest/FILES[1], report, OUTPUT_CAP-3*SMALL)
    c_sha = io._put(dest/FILES[2], head | dict(status=report["status"], attempt_sha256=a_sha,
                   report_sha256=r_sha, elapsed_before_receipt_ns=_elapsed(started, wall)), SMALL)
    saved, observed_receipt, saved_id, saved_wall, _ = _audit(
        envelope._files(dest, FILES[:3], io), identity, io, auditor, screen, reader, check)
    need((observed_receipt, saved_id, saved_wall) == (c_sha, run_id, wall), "saved audit binding")
    code = _code(saved["status"])
    io._put(dest/FILES[3], dict(run_id=run_id, receipt_sha256=c_sha, exit_code=code,
           elapsed_through_readback_ns=_elapsed(started, wall)), SMALL)
    check()
    return code


def verify_result(output: Path, *, artificial: Artificial | None = None,
                  expected_completion_sha256: str | None = None) -> Row:
    """Audit saved evidence and bindings without reading inputs or evaluating conics."""
    started = monotonic_ns()
    _, dest, pins, mode = _paths(output, artificial)
    io = _io()
    identity, raw = _methods(io, pins, mode)
    envelope, auditor, screen, reader = (_load(name, raw[name]) for name in ("envelope", "audit", "screen", "reader"))
    records = envelope._files(dest, FILES, io)
    report, receipt, run_id, wall, before = _audit(
        records[:3], identity, io, auditor, screen, reader, lambda: _elapsed(started, 30*NS))
    complete, digest = records[3]
    elapsed, code = complete["elapsed_through_readback_ns"], complete["exit_code"]
    need(complete["run_id"] == run_id and complete["receipt_sha256"] == receipt
         and type(elapsed) is int and before <= elapsed < wall
         and type(code) is int and code == _code(report["status"]), "completion")
    if expected_completion_sha256 is not None:
        need(digest == expected_completion_sha256, "completion hash")
    return report


def _clear_late(output: Path, run_id: str) -> None:
    try:
        io = _io()
        witness = output/FILES[3]
        if io._row(io._read(witness, SMALL)).get("run_id") == run_id:
            witness.unlink()
            io._sync(output)
    except (OSError, ValueError):
        pass


def launch(output: Path, *, artificial: Artificial | None = None) -> int:
    """Supervise a single isolated phase screen, including durable readback."""
    started, wall = monotonic_ns(), int(WALL_S*NS)
    source, dest, pins, mode = _paths(output, artificial)
    if os.path.lexists(output) or os.path.lexists(dest):
        return 3
    fake = [str(source), json.dumps(pins)] if mode == "artificial" else []
    run_id = uuid4().hex
    try:
        process = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(HERE), "child", str(dest), run_id, str(started), str(wall), *fake],
            timeout=(wall-_elapsed(started, wall))/NS, stdin=subprocess.DEVNULL, check=False)
        _elapsed(started, wall)
        if process.returncode in (0, 2, 3):
            return process.returncode
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    _clear_late(dest, run_id)
    return 3


def main(args: list[str]) -> int:
    if args == ["retained"]:
        return launch(RETAINED_OUTPUT)
    if len(args) in (5, 7) and args[0] == "child":
        _, dest, run_id, started, wall, *fake = args
        profile = (Path(fake[0]), json.loads(fake[1])) if fake else None
        return _child(Path(dest), run_id, int(started), int(wall), profile)
    raise ValueError("usage: python -I -S -B 0214-phase-binding.py retained")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(4) from None
