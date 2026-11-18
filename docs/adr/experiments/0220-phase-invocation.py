"""Bind the fixed R5.59i archive to the qualified inter-node study."""

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
type Check = Callable[[], None]

HERE = Path(__file__).resolve()
RETAINED = HERE.with_name("0215-r559f")
AUDIT = HERE.with_name("0217-saved-grid-audit.json")
OUTPUT = HERE.with_name("0221-r559i")
PINS = {
    "attempt.json": "ac1d02f445ebed82ac5b4f728193ea8533890188ed2422117523db50d087bf0a",
    "report.json": "323c2c71e17168a46e9dd5280015a3fecb0865016b9b6954dcb051de4def1800",
    "receipt.json": "395d20ab4771b9a9e4743e038e5c50338d12b8d890018befc3879bf3de21a18b",
    "audit.json": "bdc9eb8225a4af912327d0c8cd62231bf4f625991f6d4233ea58a5e9481172d5",
}
NAMES = tuple(PINS)
SAVED_FILES = (*NAMES[:3], "completion.json")
CAP = 4 * 1024**2
SMALL = 4096
WALL_NS = 30_000_000_000
METHODS = {
    "io": ("0206-readiness-runner.py", "ff1cd800a74f40f3bc91f74550c4b49205713f391d436e37360e92a9740c1a1e"),
    "core": ("0208-seed-worksheet.py", "4907db44f0ef53cb657cd563a6fa27df8a138442807c703a66c1343bde4788ba"),
    "oracle": ("0208-seed-oracle.py", "cf4041c69e5204f79ab6786be5e393c0dbc0977317e693587eb1a85e8265e475"),
    "reader": ("0210-retained-readback.py", "a6e1b9a32f0c46c9e03974c1367a8b04d2849eca86d807907a3bcefa1f0e8920"),
    "orbit": ("0213-phase-orbit.py", "ba78ca47097703cb27ed7dca8d844b9be34c61b1fee9a5668fae97db039979c3"),
    "screen": ("0213-phase-screen.py", "39d59baecb394f759ef6a775ce6cca548e4828dbfef94207b47c9e048d1d0f2b"),
    "interval": ("0219-interval.py", "3243ec83031b8bc873dfae47076e0bbb086640893e396b1e56c2dbcf5d865329"),
    "bounds": ("0219-phase-bounds.py", "b1a2673aa5516533320febed3efddeb27edece1f3f60b775323520e71324f83e"),
    "points": ("0219-phase-points.py", "a9eca487527068c8114ff00353846e39fcf6eb7212009c5046b4df0cc23af223"),
    "study": ("0219-phase-study.py", "9ba27b0419a24e16209b646c8f0adb4c4ad55e938fadc5816c4944a72a01fc60"),
    "archive": ("0220-phase-archive.py", "43c4c3b7fe1f82324a4833ea74a22aaed9922e8c0f9ea67fa0aa76161062dcf8"),
    "anchors": ("0220-phase-anchors.py", "7fadcb3fc9de4a43aa1ce80efd30d2e6499f76ee4918519cf8783d50bca2057e"),
}
FLAGS = dict(live_authorized=False, physical_launch_authorized=False, commands=None, spice_queries=0,
             kernel_accesses=0, force_evaluations=0, integrations=0,
             r559f_replays=0, r560_attempts=0, physical_status="physical-join-not-established")


def need(condition: object, reason: str) -> None:
    if not condition:
        raise ValueError(f"R5.59i: {reason}")


def _elapsed(started: int, wall: int) -> int:
    now = monotonic_ns()-started
    need(0 <= now < wall <= 30_000_000_000, "shared deadline")
    return now


def _paths(artificial: Artificial | None, output: Path | None) -> tuple[dict[str, Path], dict[str, str], Path]:
    if artificial is None:
        need(output is None or (output.resolve() == OUTPUT and not output.is_symlink()), "fixed retained output")
        need(not (RETAINED.is_symlink() or AUDIT.is_symlink() or OUTPUT.is_symlink()), "retained symlink")
        return {**{name: RETAINED / name for name in NAMES[:3]}, "audit.json": AUDIT}, dict(PINS), OUTPUT
    source, pins = artificial
    need(output is not None and not output.is_symlink() and not source.is_symlink(), "artificial destination")
    src, dest = source.resolve(), output.resolve()
    need(src.parent == dest.parent and src != dest
         and not any(p == q or p.is_relative_to(q) for p in (src, dest) for q in (RETAINED, AUDIT, OUTPUT))
         and set(pins) == set(NAMES) and not set(pins.values()) & set(PINS.values()), "artificial-only archive")
    return {name: src / name for name in NAMES}, dict(pins), dest


def _guard(paths: dict[str, Path], dest: Path, *, read_only: bool = False) -> None:
    inputs = {str(path) for path in paths.values()}
    scripts = {str(HERE.with_name(filename)) for filename, _ in METHODS.values()} | {str(HERE)}
    outputs = {str(dest / name) for name in SAVED_FILES}
    dirs = {str(dest), str(dest.parent), *(str(p.parent) for p in paths.values())}
    stdlib = str(Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}") + os.sep

    def scope(event: str, args: tuple[Any, ...]) -> None:
        if event == "open" and not isinstance(args[0], int):
            name = os.path.normpath(os.fsdecode(args[0]))
            read = not int(args[2]) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            need((name in outputs and (read or not read_only)) or (read and
                 (name in inputs | scripts | dirs or name.startswith(stdlib) and
                  name.endswith((".py", ".pyc", ".so", ".dylib")))), "out-of-scope file")
        if event in {"os.scandir", "os.listdir"}:
            directory = os.path.normpath(os.fsdecode(args[0]))
            need(directory in dirs or directory.startswith(stdlib), "out-of-scope inventory")
        if event == "import":
            root = str(args[0]).partition(".")[0]
            need(root in sys.stdlib_module_names and root not in {"ctypes", "_ctypes"}, "out-of-scope import")
        need(event not in {"subprocess.Popen", "os.system", "os.fork", "os.exec", "os.posix_spawn",
                           "socket.__new__", "ctypes.dlopen"}, f"out-of-scope event {event}")

    sys.addaudithook(scope)


def _load(key: str, raw: bytes) -> ModuleType:
    module = ModuleType("_r559i_" + key)
    module.__file__ = str(HERE.with_name(METHODS[key][0]))
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, "exec"), vars(module))
    return module


def _io() -> ModuleType:
    filename, pin = METHODS["io"]
    fd = os.open(HERE.with_name(filename), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        entry = os.fstat(stream.fileno())
        need(stat.S_ISREG(entry.st_mode) and entry.st_size <= 64*1024, "I/O method size or type")
        raw = stream.read(64*1024+1)
    need(len(raw) == entry.st_size and sha256(raw).hexdigest() == pin, "I/O method pin")
    return _load("io", raw)


def _methods() -> tuple[ModuleType, dict[str, ModuleType], dict[str, str]]:
    io = _io()
    filename, pin = METHODS["study"]
    source = io._read(HERE.with_name(filename), 64*1024)
    need(io._sha(source) == pin, "qualified study pin")
    study = _load("study", source)
    need(set(study.METHODS) == set(METHODS) - {"archive", "anchors"} and study.WALL_NS == 30_000_000_000,
         "study method inventory or deadline")
    study.METHODS = {name: METHODS[name] for name in study.METHODS}
    methods, digests = study._methods()
    for name in ("archive", "anchors"):
        filename, pin = METHODS[name]
        raw = io._read(HERE.with_name(filename), 64*1024)
        digest = io._sha(raw)
        need(digest == pin, f"{name} method pin")
        methods[name], digests[name] = _load(name, raw), digest
    digests["invocation"] = io._sha(io._read(HERE, 64*1024))

    def anchors(source: Row, methods: dict[str, ModuleType], work: Row, check: Check) -> None:
        for angle, previous in zip(study.ANCHORS, source["anchors"], strict=True):
            current = study._phase(source["reference"], angle, methods, work, check)
            methods["anchors"].verify_anchor(previous, current, angle.numerator, methods["reader"])

    study._anchors = anchors
    return study, methods, digests


def _read_archive(paths: dict[str, Path], pins: dict[str, str], methods: dict[str, ModuleType],
                  *, retained: bool, check: Check) -> tuple[Row, int]:
    directory = paths["attempt.json"].parent
    expected = set(NAMES[:3] if retained else NAMES)
    with os.scandir(directory) as entries:
        need({entry.name for _, entry in zip(range(len(expected)+1), entries)} == expected, "archive inventory")
    io = methods["io"]
    records, size = {}, 0
    for name in NAMES:
        check()
        io._pin(pins[name])
        raw = io._read(paths[name], CAP-size)
        digest = io._sha(raw)
        need(digest == pins[name], f"{name} hash")
        record = io._row(raw)
        wire = ((json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
                if name == "audit.json" else io._wire(record))
        need(wire == raw, f"{name} canonical encoding")
        records[name] = record, digest
        size += len(raw)
    return methods["archive"].bind(records, io, retained=retained), size


def _identity(retained: bool, pins: dict[str, str], digests: dict[str, str], run_id: str, size: int) -> Row:
    return FLAGS | dict(schema="ariadna-r559i-phase-evidence-v1", stage="R5.59i" if retained else "R5.59i-preparation",
                        scope="retained" if retained else "artificial", r559i_attempts=int(retained),
                        source_pins=pins, methods_sha256=digests, run_id=run_id, source_bytes=size)


def _worker(artificial: Artificial | None, output: Path | None, run_id: str, started: int, wall: int) -> int:
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "worker requires -I -S -B")
    paths, pins, dest = _paths(artificial, output)
    _guard(paths, dest)
    study, methods, digests = _methods()
    io, retained = methods["io"], artificial is None

    def check() -> None:
        _elapsed(started, wall)

    source, size = _read_archive(paths, pins, methods, retained=retained, check=check)
    check()
    head = _identity(retained, pins, digests, run_id, size)
    dest.mkdir(mode=0o700)
    io._sync(dest.parent)
    a_sha = io._put(dest / SAVED_FILES[0], head | {"wall_ns": wall}, SMALL)
    report = study._scan(source, methods, check)
    check()
    r_sha = io._put(dest / SAVED_FILES[1], head | report | {"attempt_sha256": a_sha}, CAP-3*SMALL)
    c_sha = io._put(dest / SAVED_FILES[2], head | {"attempt_sha256": a_sha, "report_sha256": r_sha,
                   "elapsed_ns": _elapsed(started, wall)}, SMALL)
    fresh, reread = _read_archive(paths, pins, methods, retained=retained, check=check)
    need(reread == size, "audit archive size")
    proof = study._saved(fresh, study._records(dest, SAVED_FILES[:3], io), head, methods, check)
    code = 0 if proof["status"] == study.WITNESS else 2
    io._put(dest / SAVED_FILES[3], {"receipt_sha256": c_sha, "proof": proof, "run_id": run_id, "exit_code": code,
                                   "elapsed_ns": _elapsed(started, wall)}, SMALL)
    check()
    return code


def launch(*, artificial: Artificial | None = None, output: Path | None = None) -> int:
    """Dispatch once; an existing result directory blocks dispatch."""
    started = monotonic_ns()
    _, pins, dest = _paths(artificial, output)
    if os.path.lexists(dest):
        return 3
    run_id, wall = uuid4().hex, WALL_NS
    profile = [] if artificial is None else [str(artificial[0].resolve()), str(dest), json.dumps(pins)]
    try:
        child = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(HERE), "worker", run_id, str(started), str(wall), *profile],
            stdin=subprocess.DEVNULL, timeout=(wall-_elapsed(started, wall))/1e9, check=False)
        _elapsed(started, wall)
        if child.returncode in (0, 2):
            return child.returncode
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    completion = dest / SAVED_FILES[3]
    try:
        io = _io()
        if io._row(io._read(completion, SMALL)).get("run_id") == run_id:
            completion.unlink()
            io._sync(dest)
    except (OSError, ValueError):
        pass
    return 3


def verify_result(*, completion_sha256: str, artificial: Artificial | None = None, output: Path | None = None) -> Row:
    """Check saved provenance and independently replay only the local point and interval audit."""
    started = monotonic_ns()
    paths, pins, dest = _paths(artificial, output)
    study, methods, digests = _methods()
    retained, io = artificial is None, methods["io"]

    def check() -> None:
        _elapsed(started, 30_000_000_000)

    source, size = _read_archive(paths, pins, methods, retained=retained, check=check)
    records = study._records(dest, SAVED_FILES, io)
    attempt, report, receipt, completion = (item[0] for item in records)
    head = _identity(retained, pins, digests, attempt["run_id"], size)
    need(records[3][1] == completion_sha256 and completion["run_id"] == head["run_id"]
         and completion["receipt_sha256"] == records[2][1] and type(completion["elapsed_ns"]) is int
         and receipt["elapsed_ns"] <= completion["elapsed_ns"] < attempt["wall_ns"], "completion binding")
    proof = study._saved(source, records[:3], head, methods, check)
    need(io._wire(proof) == io._wire(completion["proof"]) and type(completion["exit_code"]) is int
         and completion["exit_code"] == (0 if proof["status"] == study.WITNESS else 2), "completion proof")
    check()
    return report | {"producer_status": report["status"], "status": proof["status"], "independent_readback": proof}


def main(args: list[str]) -> int:
    if args == ["retained"]:
        return launch()
    if len(args) == 2 and args[0] == "audit":
        need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "audit requires -I -S -B")
        paths, _, dest = _paths(None, None)
        _guard(paths, dest, read_only=True)
        print(json.dumps(verify_result(completion_sha256=args[1]), sort_keys=True, allow_nan=False))
        return 0
    if args and args[0] == "worker" and len(args) in (4, 7):
        _, run_id, started, wall, *fake = args
        profile = (Path(fake[0]), json.loads(fake[2])) if fake else None
        return _worker(profile, Path(fake[1]) if fake else None, run_id, int(started), int(wall))
    raise ValueError("usage: 0220-phase-invocation.py retained | audit COMPLETION_SHA256")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, TypeError, KeyError, IndexError, ArithmeticError, RecursionError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(3) from None
