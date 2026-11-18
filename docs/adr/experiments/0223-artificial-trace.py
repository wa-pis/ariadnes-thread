"""Qualify observational interval traces exclusively on fixed artificial fixtures."""

from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import sys
from time import monotonic_ns
from types import ModuleType
from typing import Any

type Row = dict[str, Any]
HERE = Path(__file__).resolve()
CAP = 4*1024**2
SMALL = 4096
STATUS = "artificial-trace-qualified"
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
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
    "trace": ("0223-bound-trace.py", "e50876ce72c8e80a74d7d615b4f67f6d69ab9a259a10663b041ee56d78730091"),
    "containment": ("0223-trace-oracle.py", "bb9024663cb1b6642d0417ff73236ba47fa1eb9f48b3981db89d6aaf0c547973"),
}
CASES = ("witness", "refusal")
CELLS = ((Fraction(151), Fraction(152)), (Fraction(151), Fraction(4833, 32)),
         (Fraction(9665, 64), Fraction(9665, 64)))
SIGNS = ("positive", "negative")
FIXTURE_PINS = {
    "witness": "cf20fb7d66cb6efe54b809519d1c0ca8f3031aee83c8532de4a20e2c6f0b1cec",
    "refusal": "5316e28ef1c7c27035ba9ef08c2fa26ac9d600d04ba8a06af1dc69fe6c4c5467",
}
FLAGS = dict(scope="artificial", commands=None, live_authorized=False, physical_launch_authorized=False,
             spice_queries=0, kernel_accesses=0, r559f_replays=0,
             integrations=0, force_evaluations=0, r559i_attempts=0, r560_attempts=0,
             physical_status="physical-join-not-established")


def need(ok: object, reason: str) -> None:
    if not ok:
        raise ValueError(f"R5.59k: {reason}")


def _wire(row: Any) -> bytes:
    return (json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)+"\n").encode()


@dataclass(slots=True)
class Budget:
    wall_ns: int = 30_000_000_000
    bound_cap: int = 64
    point_cap: int = 32
    event_cap: int = 8192
    byte_cap: int = CAP
    started_ns: int = field(default_factory=monotonic_ns)
    used: dict[str, int] = field(default_factory=lambda: dict(bounds=0, points=0, events=0))
    event_bytes: int = 0

    def __post_init__(self) -> None:
        for name, ceiling in (("wall_ns", 30_000_000_000), ("bound_cap", 64), ("point_cap", 32),
                              ("event_cap", 8192), ("byte_cap", CAP)):
            value = getattr(self, name)
            need(type(value) is int and 0 <= value <= ceiling, f"{name} cap")
        need(set(self.used) == {"bounds", "points", "events"}
             and all(type(v) is int and v == 0 for v in self.used.values()), "fresh work budget")

    def check(self) -> None:
        need(0 <= monotonic_ns()-self.started_ns < self.wall_ns, "wall cap")

    def charge(self, kind: str, n: int = 1) -> None:
        self.check()
        caps = dict(bounds=self.bound_cap, points=self.point_cap, events=self.event_cap)
        need(kind in caps and type(n) is int and n > 0
             and self.used[kind]+n <= caps[kind], f"{kind} cap")
        self.used[kind] += n

    def emit(self, event: Row) -> None:
        self.charge("events")
        size = len(_wire(event))
        need(self.event_bytes+size <= self.byte_cap, "trace byte cap")
        self.event_bytes += size


def _read(path: Path, cap: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        entry = os.fstat(stream.fileno())
        need(stat.S_ISREG(entry.st_mode) and 0 <= entry.st_size <= cap, "input byte cap or type")
        raw = stream.read(cap+1)
    need(len(raw) == entry.st_size, "input byte cap or changed file")
    return raw


def _methods() -> dict[str, ModuleType]:
    methods: dict[str, ModuleType] = {}
    size = 0
    for name, (filename, pin) in METHODS.items():
        raw = _read(HERE.with_name(filename), min(64*1024, CAP-size))
        size += len(raw)
        need(sha256(raw).hexdigest() == pin, f"{name} method pin")
        module = ModuleType("_r559k_"+name)
        module.__file__ = str(HERE.with_name(filename))
        sys.modules[module.__name__] = module
        exec(compile(raw, module.__file__, "exec"), vars(module))
        methods[name] = module
    return methods


def _output(output: Path) -> Path:
    need(not output.is_symlink() and output.name.startswith("r559k-artificial-"), "artificial output scope")
    return output.resolve()


def _identity() -> Row:
    pins = {k: pin for k, (_, pin) in METHODS.items()}
    pins["runner"] = sha256(_read(HERE, 64*1024)).hexdigest()
    return FLAGS | dict(stage="R5.59k", source_pins=pins)


def _inventory(output: Path, io: ModuleType) -> list[tuple[Row, str]]:
    need({p.name for p in output.iterdir()} == set(FILES), "evidence inventory")
    records = []
    for name in FILES:
        raw = _read(output/name, CAP if name == "report.json" else SMALL)
        row = io._row(raw)
        need(_wire(row) == raw, "canonical saved evidence")
        records.append((row, sha256(raw).hexdigest()))
    need(sum((output/n).stat().st_size for n in FILES) <= CAP, "saved evidence byte cap")
    return records


def _validate(report: Row, methods: dict[str, ModuleType], check: Callable[[], None]) -> Row:
    check()
    need(report["status"] == STATUS and set(report["fixtures"]) == set(CASES), "artificial report")
    need(all(sha256(_wire(report["fixtures"][case])).hexdigest() == FIXTURE_PINS[case] for case in CASES),
         "fixed artificial fixture pin")
    phases = {"150", "151", "152", "303/2", "4833/32", "9665/64"}
    need(set(report["points"]) == set(CASES)
         and all(set(report["points"][case]) == phases
                 and all(point["phase_deg"] == phase for phase, point in report["points"][case].items())
                 for case in CASES), "point phase identity or cache inventory")
    rows = report["rows"]
    expected = [(case, str(lo), str(hi), sign, ind) for case in CASES for lo, hi in CELLS
                for sign in SIGNS for ind in (False, True)]
    need(len(rows) == len(expected), "trace matrix inventory")
    events = 0
    for row, key in zip(rows, expected, strict=True):
        check()
        need(tuple(row[k] for k in ("case", "lo_deg", "hi_deg", "sign", "independent")) == key,
             "trace matrix order")
        ref = report["fixtures"][row["case"]]
        need(ref["normalized"]["scope"] == "artificial"
             and ref["normalized"]["candidate_id"] == "artificial-moon-mars", "artificial fixture scope")
        need(type(row["independent"]) is bool
             and tuple(row["trace"][k] for k in ("lo", "hi", "sign", "independent")) == key[1:],
             "trace/cell metadata")
        need(_wire(row["trace"]["result"]) == _wire(row["control"]), "exact traced/control parity")
        methods["trace"].verify_trace(row["trace"], row["control"])
        lo, hi = Fraction(row["lo_deg"]), Fraction(row["hi_deg"])
        points = [report["points"][row["case"]][str(phase)] for phase in sorted({lo, (lo+hi)/2, hi})]
        checks = [methods["containment"].verify_containment(ref, point, row["trace"], row["sign"], methods)
                  for point in points]
        need(_wire(checks) == _wire(row["containment"]), "containment readback")
        events += len(row["trace"]["events"])
    need(0 < events <= 8192 and report["work"] == dict(bounds=48, points=12, events=events), "work accounting")
    return dict(status=STATUS, rows=len(rows), event_count=events, new_bounds=0, new_points=0)


def _readback(output: Path, pin: str, methods: dict[str, ModuleType], check: Callable[[], None]) -> Row:
    (attempt, a), (report, r), (receipt, c), (completion, complete_pin) = _inventory(output, methods["io"])
    head = _identity()
    need(complete_pin == pin and all(_wire({k: row[k] for k in head}) == _wire(head)
                                    for row in (attempt, report, receipt)), "saved source or completion pin")
    need(report["attempt_sha256"] == receipt["attempt_sha256"] == a and receipt["report_sha256"] == r
         and completion["receipt_sha256"] == c, "receipt hash chain")
    need(type(receipt["elapsed_ns"]) is int and type(completion["elapsed_ns"]) is int
         and 0 <= receipt["elapsed_ns"] <= completion["elapsed_ns"] < attempt["wall_ns"] <= 30_000_000_000,
         "saved deadline")
    proof = _validate(report, methods, check)
    need(proof == completion["proof"], "saved trace proof")
    check()
    return report | dict(independent_readback=proof)


def audit(output: Path, completion_sha256: str) -> Row:
    """Read back artificial trace provenance and checks without new bound or phase calls."""
    budget = Budget()
    dest = _output(output)
    return _readback(dest, completion_sha256, _methods(), budget.check)


def run(output: Path, *, budget: Budget | None = None) -> Row:
    """Trace both fixed fabricated cases; no caller-supplied scientific input is accepted."""
    b = budget if budget is not None else Budget()
    b.check()
    dest = _output(output)
    need(not os.path.lexists(dest), "existing artificial output")
    methods = _methods()
    io = methods["io"]
    head = _identity()
    dest.mkdir(mode=0o700)
    io._sync(dest.parent)
    need(b.byte_cap > 3*SMALL, "output byte cap")
    a_sha = io._put(dest/FILES[0], head | dict(wall_ns=b.wall_ns), SMALL)
    fixtures: Row = {}
    points: Row = {}
    rows = []
    for case in CASES:
        b.charge("points", 3)
        fixture = methods["points"].fixture(case, methods)
        need(fixture["scope"] == "artificial", "fixture scope")
        ref = fixtures[case] = fixture["reference"]
        need(sha256(_wire(ref)).hexdigest() == FIXTURE_PINS[case], "fixed artificial fixture pin")
        cache = points[case] = {row["phase_deg"]: row for row in fixture["anchors"]}
        for lo, hi in CELLS:
            sample = sorted({lo, (lo+hi)/2, hi})
            for phase in sample:
                if str(phase) not in cache:
                    b.charge("points")
                    cache[str(phase)] = methods["points"].point(ref, phase, methods)
            for sign in SIGNS:
                for ind in (False, True):
                    b.charge("bounds")
                    control = methods["bounds"].bounds(ref, lo, hi, sign, methods["interval"], independent=ind)
                    b.charge("bounds")
                    trace = methods["trace"].trace_bound(ref, lo, hi, sign, methods, independent=ind,
                                                         check=b.check, emit=b.emit)
                    need(_wire(trace["result"]) == _wire(control), "exact traced/control parity")
                    methods["trace"].verify_trace(trace, control)
                    checks = [methods["containment"].verify_containment(ref, cache[str(phase)], trace, sign, methods)
                              for phase in sample]
                    rows.append(dict(case=case, lo_deg=str(lo), hi_deg=str(hi), sign=sign, independent=ind,
                                     trace=trace, control=control, containment=checks))
    report = head | dict(status=STATUS, fixtures=fixtures, points=points, rows=rows,
                         work=dict(b.used), attempt_sha256=a_sha)
    r_sha = io._put(dest/FILES[1], report, b.byte_cap-3*SMALL)
    b.check()
    c_sha = io._put(dest/FILES[2], head | dict(attempt_sha256=a_sha, report_sha256=r_sha,
                                             elapsed_ns=monotonic_ns()-b.started_ns), SMALL)
    proof = _validate(report, methods, b.check)
    complete = dict(receipt_sha256=c_sha, elapsed_ns=monotonic_ns()-b.started_ns, proof=proof)
    certified = False
    try:
        pin = io._put(dest/FILES[3], complete, SMALL)
        result = _readback(dest, pin, methods, b.check)
        b.check()
        certified = True
        return result
    finally:
        if not certified and os.path.lexists(dest/FILES[3]):
            (dest/FILES[3]).unlink()
            io._sync(dest)


def _guard(output: Path, *, read_only: bool = False) -> None:
    allowed = {str(HERE)} | {str(HERE.with_name(name)) for name, _ in METHODS.values()}
    saved = {str(output/name) for name in FILES}
    dirs = {str(output), str(output.parent)}
    stdlib = str(Path(sys.base_prefix)/"lib"/f"python{sys.version_info.major}.{sys.version_info.minor}")+os.sep

    def scope(event: str, args: tuple[Any, ...]) -> None:
        if event == "open" and not isinstance(args[0], int):
            path = os.path.normpath(os.fsdecode(args[0]))
            write = int(args[2]) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            need(path in saved and (not write or not read_only) or not write and
                 (path in allowed | dirs or path.startswith(stdlib) and path.endswith((".py", ".pyc", ".so", ".dylib"))),
                 "file outside artificial scope")
        if event in {"os.scandir", "os.listdir"}:
            path = os.path.normpath(os.fsdecode(args[0]))
            need(path in dirs or path.startswith(stdlib), "inventory outside artificial scope")
        if event == "import":
            root = str(args[0]).partition(".")[0]
            need(root in sys.stdlib_module_names and root not in {"ctypes", "_ctypes"}, "scientific import")
        need(event not in {"subprocess.Popen", "os.system", "os.fork", "os.exec", "os.posix_spawn",
                           "socket.__new__", "ctypes.dlopen"}, "native or external access")
    sys.addaudithook(scope)


def main(args: list[str]) -> int:
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "use -I -S -B")
    need(len(args) in (2, 3), "usage: run OUTPUT | audit OUTPUT COMPLETION_SHA256")
    output = _output(Path(args[1]))
    _guard(output, read_only=args[0] == "audit")
    if args[0] == "run" and len(args) == 2:
        result = run(output)
    elif args[0] == "audit" and len(args) == 3:
        result = audit(output, args[2])
    else:
        raise ValueError("invalid artificial trace command")
    print(json.dumps(dict(status=result["status"], work=result["work"],
                          readback=result["independent_readback"]), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, TypeError, KeyError, ArithmeticError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(3) from None
