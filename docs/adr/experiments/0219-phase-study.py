"""R5.59h bounded phase certificates; the only invocation accepts artificial evidence."""

from collections import deque
from collections.abc import Callable
from fractions import Fraction
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic_ns
from types import ModuleType
from typing import Any
from uuid import uuid4

type Row = dict[str, Any]
type Cell = tuple[Fraction, Fraction, int]
type Check = Callable[[], None]

HERE = Path(__file__).resolve()
METHODS = {
    "io": ("0206-readiness-runner.py", "ff1cd800a74f40f3bc91f74550c4b49205713f391d436e37360e92a9740c1a1e"),
    "core": ("0208-seed-worksheet.py", "4907db44f0ef53cb657cd563a6fa27df8a138442807c703a66c1343bde4788ba"),
    "oracle": ("0208-seed-oracle.py", "cf4041c69e5204f79ab6786be5e393c0dbc0977317e693587eb1a85e8265e475"),
    "reader": ("0210-retained-readback.py", "a6e1b9a32f0c46c9e03974c1367a8b04d2849eca86d807907a3bcefa1f0e8920"),
    "orbit": ("0213-phase-orbit.py", "ba78ca47097703cb27ed7dca8d844b9be34c61b1fee9a5668fae97db039979c3"),
    "screen": ("0213-phase-screen.py", "39d59baecb394f759ef6a775ce6cca548e4828dbfef94207b47c9e048d1d0f2b"),
    "interval": ("0219-interval.py", None),
    "bounds": ("0219-phase-bounds.py", None),
    "points": ("0219-phase-points.py", None),
    "study": (HERE.name, None),
}
SIGNS = ("positive", "negative")
ANCHORS = tuple(map(Fraction, (150, 151, 152)))
CELLS = tuple((a, b, 0) for a, b in zip(ANCHORS[:-1], ANCHORS[1:], strict=True))
CAPS = {"cells": 126, "bounds": 252, "points": 129, "point_roots": 258, "point_pairs": 258}
DEPTH = 5
CAP = 4 * 1024**2
SMALL = 4096
WALL_NS = 30_000_000_000
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
WITNESS, REFUSAL, UNKNOWN = "eligible-off-grid-witness", "no-eligible-pair-on-local-interval", "inconclusive"
FLAGS = dict(stage="R5.59h", scope="artificial", live_authorized=False, physical_launch_authorized=False,
             commands=None, spice_queries=0, kernel_accesses=0, force_evaluations=0, integrations=0,
             r559i_attempts=0, r560_attempts=0)


def need(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(f"R5.59h: {message}")


def _load(name: str, raw: bytes) -> ModuleType:
    module = ModuleType("_r559h_" + name)
    module.__file__ = str(HERE.with_name(METHODS[name][0]))
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, "exec"), vars(module))
    return module


def _methods() -> tuple[dict[str, ModuleType], dict[str, str]]:
    # Bootstrap from the already qualified I/O implementation.
    name, pin = METHODS["io"]
    fd = os.open(HERE.with_name(name), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        raw = stream.read(64 * 1024 + 1)
    need(sha256(raw).hexdigest() == pin, "I/O method pin")
    io = _load("io", raw)
    modules, digests = {"io": io}, {"io": pin}
    for key, (name, pin) in METHODS.items():
        if key == "io":
            continue
        data = io._read(HERE.with_name(name), 64 * 1024)
        digest = io._sha(data)
        need(pin is None or digest == pin, f"{name} method pin")
        digests[key] = digest
        if key != "study":
            modules[key] = _load(key, data)
    return modules, digests


def _paths(source: Path, output: Path) -> tuple[Path, Path]:
    need(not source.is_symlink() and not output.is_symlink(), "symlink source or destination")
    src, dest = source.resolve(), output.resolve()
    need(src.name == "r559h-artificial.json" and src.parent == dest.parent
         and dest.name.startswith("r559h-artificial-"), "artificial-only source and sibling destination")
    return src, dest


def _guard(source: Path, output: Path) -> None:
    methods = {str(HERE.with_name(name)) for name, _ in METHODS.values()}
    evidence = {str(output / name) for name in FILES}
    stdlib = str(Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}") + os.sep

    def scope(event: str, args: tuple[Any, ...]) -> None:
        if event == "open" and not isinstance(args[0], int):
            name = os.path.normpath(os.fsdecode(args[0]))
            read = not int(args[2]) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            need(name in evidence or read and (name in methods or name in {str(source), str(output), str(output.parent)}
                  or name.startswith(stdlib) and name.endswith((".py", ".pyc", ".so", ".dylib"))),
                 f"file outside artificial scope: {Path(name).name}")
        if event in {"os.scandir", "os.listdir"}:
            path = os.path.normpath(os.fsdecode(args[0]))
            need(path == str(output) or path.startswith(stdlib), "inventory outside scope")
        if event == "import":
            name = str(args[0]).partition(".")[0]
            need(name in sys.stdlib_module_names and name not in {"ctypes", "_ctypes"}, "out-of-scope import")
        need(event not in {"subprocess.Popen", "os.system", "os.fork", "os.exec", "os.posix_spawn",
                           "socket.__new__", "ctypes.dlopen"}, f"out-of-scope event {event}")

    sys.addaudithook(scope)


def _source(source: Path, pin: str, io: ModuleType) -> tuple[Row, int]:
    io._pin(pin)
    raw = io._read(source, CAP)
    need(io._sha(raw) == pin, "artificial input hash")
    doc = io._row(raw)
    need(io._wire(doc) == raw and doc.get("scope") == "artificial", "artificial encoding or scope")
    ref = doc["reference"]
    need(ref["normalized"]["scope"] == "artificial"
         and ref["normalized"]["candidate_id"].startswith("artificial-"), "non-artificial scientific operands")
    return doc, len(raw)


def _charge(work: Row, key: str, check: Check, count: int = 1) -> None:
    check()
    need(work[key] + count <= CAPS[key], f"{key} cap")
    work[key] += count


def _phase(ref: Row, degree: Fraction, methods: dict[str, ModuleType], work: Row, check: Check) -> Row:
    _charge(work, "points", check)
    _charge(work, "point_roots", check, 2)
    _charge(work, "point_pairs", check, 2)  # Charge the upper bound even if a root is rejected.
    row = methods["points"].point(ref, degree, methods)
    need(isinstance(row["eligible"], list) and len(set(row["eligible"])) == len(row["eligible"])
         and all(sign in SIGNS for sign in row["eligible"]), "eligible point inventory")
    return row


def _anchors(source: Row, methods: dict[str, ModuleType], work: Row, check: Check) -> None:
    io = methods["io"]
    saved = source["anchors"]
    need(isinstance(saved, list) and len(saved) == len(ANCHORS), "three artificial anchors")
    for degree, old in zip(ANCHORS, saved, strict=True):
        current = _phase(source["reference"], degree, methods, work, check)
        need(not current["eligible"] and io._wire(current) == io._wire(old), "anchor mismatch or eligible anchor")


def _split(cell: Cell) -> tuple[Cell, Cell]:
    lo, hi, depth = cell
    mid = (lo + hi) / 2
    return (lo, mid, depth+1), (mid, hi, depth+1)


def _enclosures(ref: Row, cell: Cell, methods: dict[str, ModuleType], work: Row,
                check: Check, *, independent: bool) -> Row:
    _charge(work, "bounds", check, 2)
    lo, hi, _ = cell
    return {sign: methods["bounds"].bounds(ref, lo, hi, sign, methods["interval"], independent=independent)
            for sign in SIGNS}


def _excludes(bounds: Row) -> bool:
    need(isinstance(bounds, dict) and set(bounds) == set(SIGNS), "two signed bounds required")
    reasons = [bounds[sign]["reason"] for sign in SIGNS]
    need(all(reason in (None, "mass", "guard") for reason in reasons), "unknown bound disposition")
    return all(reason is not None for reason in reasons)


def _scan(source: Row, methods: dict[str, ModuleType], check: Check) -> Row:
    work = dict.fromkeys(CAPS, 0)
    _anchors(source, methods, work, check)
    queue = deque(CELLS)
    ref, rows = source["reference"], []
    witness = None
    unresolved = False
    while queue:
        cell = queue.popleft()
        lo, hi, depth = cell
        _charge(work, "cells", check)
        bounds = _enclosures(ref, cell, methods, work, check, independent=False)
        row = {"lo_deg": str(lo), "hi_deg": str(hi), "depth": depth, "bounds": bounds, "point": None}
        rows.append(row)
        if _excludes(bounds):
            row["action"] = "excluded"
            continue
        degree = (lo+hi)/2
        point = _phase(ref, degree, methods, work, check)
        row["point"] = point
        if point["eligible"]:
            witness = {"phase_deg": str(degree), "signs": point["eligible"]}
            row["action"] = "witness"
            break
        if depth < DEPTH:
            row["action"] = "split"
            queue.extend(_split(cell))
        else:
            row["action"] = "unresolved"
            unresolved = True
    status = WITNESS if witness is not None else UNKNOWN if unresolved else REFUSAL
    return {"status": status, "witness": witness, "rows": rows, "work": work}


def _audit(source: Row, report: Row, methods: dict[str, ModuleType], check: Check) -> Row:
    """Audit the transcript and independently prove each excluded leaf."""
    io = methods["io"]
    work = dict.fromkeys(CAPS, 0)
    _anchors(source, methods, work, check)
    queue = deque(CELLS)
    leaves: list[tuple[Fraction, Fraction]] = []
    witness = None
    unresolved = 0
    for row in report["rows"]:
        _charge(work, "cells", check)
        need(queue and witness is None, "excess rows or rows after witness")
        cell = queue.popleft()
        lo, hi, depth = cell
        need(row["lo_deg"] == str(lo) and row["hi_deg"] == str(hi) and type(row["depth"]) is int
             and row["depth"] == depth, "cell order or gap")
        excluded = _excludes(row["bounds"])
        for sign in SIGNS:
            methods["bounds"].validate_claim(row["bounds"][sign])
        independent = _enclosures(source["reference"], cell, methods, work, check, independent=True)
        if excluded:
            if _excludes(independent):
                # The independent interval's reason can differ; either proves the same exclusion.
                leaves.append((lo, hi))
            else:
                unresolved += 1
            need(row["action"] == "excluded" and row["point"] is None, "invalid exclusion transcript")
            continue
        degree = (lo+hi)/2
        point = _phase(source["reference"], degree, methods, work, check)
        need(isinstance(row["point"], dict) and io._wire(point) == io._wire(row["point"]), "point mismatch")
        if point["eligible"]:
            need(row["action"] == "witness", "missed witness")
            witness = {"phase_deg": str(degree), "signs": point["eligible"]}
        elif depth < DEPTH:
            need(row["action"] == "split", "premature leaf")
            queue.extend(_split(cell))
        else:
            need(row["action"] == "unresolved", "unresolved leaf disposition")
            unresolved += 1
    need(witness is not None or not queue, "missing cell coverage")
    need(io._wire(report["work"]) == io._wire(work), "producer work accounting")
    need(report["witness"] == witness, "witness binding")
    if witness is not None:
        need(report["status"] == WITNESS, "witness disposition")
        return {"status": WITNESS, "work": work, "verified_leaves": len(leaves), "unresolved": unresolved}
    cursor = ANCHORS[0]
    for lo, hi in sorted(leaves):
        if lo > cursor:
            break
        cursor = max(cursor, hi)
    if unresolved or cursor != ANCHORS[-1]:
        need(report["status"] in (REFUSAL, UNKNOWN), "invalid producer disposition")
        return {"status": UNKNOWN, "work": work, "verified_leaves": len(leaves), "unresolved": unresolved}
    need(report["status"] == REFUSAL, "refusal disposition")
    return {"status": REFUSAL, "work": work, "verified_leaves": len(leaves), "unresolved": unresolved}


def _clock(started: int, wall: int) -> int:
    elapsed = monotonic_ns()-started
    need(0 <= elapsed < wall <= WALL_NS, "shared deadline")
    return elapsed


def _records(dest: Path, names: tuple[str, ...], io: ModuleType) -> list[tuple[Row, str]]:
    with os.scandir(dest) as listing:
        need({item.name for _, item in zip(range(len(names)+1), listing)} == set(names), "evidence inventory")
    records = []
    for name in names:
        raw = io._read(dest / name, CAP-3*SMALL if name == "report.json" else SMALL)
        doc = io._row(raw)
        need(io._wire(doc) == raw, "evidence encoding")
        records.append((doc, io._sha(raw)))
    return records


def _saved(source: Row, records: list[tuple[Row, str]], head: Row, methods: dict[str, ModuleType],
           check: Check) -> Row:
    (attempt, a_sha), (report, r_sha), (receipt, _) = records
    io = methods["io"]
    run_id = head["run_id"]
    need(type(run_id) is str and len(run_id) == 32 and all(c in "0123456789abcdef" for c in run_id),
         "attempt identifier")
    need(all(io._wire({k: row[k] for k in head}) == io._wire(head) for row in (attempt, report, receipt)),
         "method, input or authority binding")
    need(report["attempt_sha256"] == receipt["attempt_sha256"] == a_sha and receipt["report_sha256"] == r_sha,
         "receipt hash chain")
    need(type(attempt["wall_ns"]) is type(receipt["elapsed_ns"]) is int
         and 0 <= receipt["elapsed_ns"] < attempt["wall_ns"] <= WALL_NS, "receipt time")
    return _audit(source, report, methods, check)


def _worker(src: Path, dest: Path, pin: str, run_id: str, started: int, wall: int) -> int:
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "use -I -S -B")
    src, dest = _paths(src, dest)
    _guard(src, dest)
    methods, digests = _methods()
    io = methods["io"]

    def check() -> None:
        _clock(started, wall)

    check()
    source, size = _source(src, pin, io)
    head = FLAGS | {"source_sha256": pin, "source_bytes": size, "methods_sha256": digests, "run_id": run_id}
    dest.mkdir(mode=0o700)
    io._sync(dest.parent)
    a_sha = io._put(dest / FILES[0], head | {"wall_ns": wall}, SMALL)
    result = _scan(source, methods, check)
    check()
    r_sha = io._put(dest / FILES[1], head | result | {"attempt_sha256": a_sha}, CAP-3*SMALL)
    rec_sha = io._put(dest / FILES[2], head | {"attempt_sha256": a_sha, "report_sha256": r_sha,
                     "elapsed_ns": _clock(started, wall)}, SMALL)
    readback_source, _ = _source(src, pin, io)
    proof = _saved(readback_source, _records(dest, FILES[:3], io), head, methods, check)
    code = 0 if proof["status"] == WITNESS else 2
    io._put(dest / FILES[3], {"receipt_sha256": rec_sha, "proof": proof, "run_id": run_id, "exit_code": code,
                            "elapsed_ns": _clock(started, wall)}, SMALL)
    check()
    return code


def launch(source: Path, pin: str, output: Path) -> int:
    """Run one artificial study under a shared deadline through durable readback."""
    started = monotonic_ns()
    src, dest = _paths(source, output)
    if os.path.lexists(dest):
        return 3
    run_id = uuid4().hex
    wall = WALL_NS
    try:
        child = subprocess.run([sys.executable, "-I", "-S", "-B", str(HERE), "worker", str(src), str(dest),
                                pin, run_id, str(started), str(wall)],
                               stdin=subprocess.DEVNULL, timeout=(wall-_clock(started, wall))/1e9, check=False)
        _clock(started, wall)
        if child.returncode in (0, 2):
            return child.returncode
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    witness = dest / FILES[3]
    try:
        methods, _ = _methods()
        io = methods["io"]
        if io._row(io._read(witness, SMALL)).get("run_id") == run_id:
            witness.unlink()
            io._sync(dest)
    except (OSError, ValueError):
        pass
    return 3


def verify_result(source: Path, pin: str, output: Path, *, completion_sha256: str) -> Row:
    """Independently read a saved artificial certificate; an external completion pin is mandatory."""
    started = monotonic_ns()
    src, dest = _paths(source, output)
    methods, digests = _methods()
    io = methods["io"]
    fixture, size = _source(src, pin, io)
    records = _records(dest, FILES, io)
    attempt, _ = records[0]
    receipt, rec_sha = records[2]
    completion, c_sha = records[3]
    head = FLAGS | {"source_sha256": pin, "source_bytes": size, "methods_sha256": digests, "run_id": attempt["run_id"]}
    need(c_sha == completion_sha256 and completion["run_id"] == head["run_id"]
         and completion["receipt_sha256"] == rec_sha and type(completion["elapsed_ns"]) is int
         and receipt["elapsed_ns"] <= completion["elapsed_ns"] < attempt["wall_ns"], "completion binding")
    proof = _saved(fixture, records[:3], head, methods, lambda: _clock(started, WALL_NS))
    need(io._wire(proof) == io._wire(completion["proof"])
         and type(completion["exit_code"]) is int
         and completion["exit_code"] == (0 if proof["status"] == WITNESS else 2), "completion proof")
    report = records[1][0]
    return report | {"producer_status": report["status"], "status": proof["status"], "independent_readback": proof}


def main(args: list[str]) -> int:
    if len(args) == 4 and args[0] == "artificial":
        return launch(Path(args[1]), args[2], Path(args[3]))
    if len(args) == 7 and args[0] == "worker":
        _, source, output, pin, run_id, started, wall = args
        return _worker(Path(source), Path(output), pin, run_id, int(started), int(wall))
    raise ValueError("usage: 0219-phase-study.py artificial SOURCE SHA256 OUTPUT")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, KeyError, TypeError, IndexError, ArithmeticError, RecursionError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(3) from None
