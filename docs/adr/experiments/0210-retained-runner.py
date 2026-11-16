"""Generate and seal at most one retained analytic two-command seed offline."""

from collections.abc import Callable
from decimal import Decimal, localcontext
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
type Artificial = tuple[Path, dict[str, str], tuple[str, str, str]]

HERE = Path(__file__).resolve()
RETAINED_OUTPUT = HERE.with_name("0211-r559c")
WALL_S = 15
NS = 10**9
OUTPUT_CAP = 128 * 1024
SMALL = 4096
REPORT_CAP = OUTPUT_CAP - 3 * SMALL
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
METHODS = {
    "adapter": ("0209-archive-adapter.py", "b9f581321d825fd258067111e3513df0b89e84976a2a734db4345129a5eec25c"),
    "binary64": ("0208-seed-worksheet.py", "4907db44f0ef53cb657cd563a6fa27df8a138442807c703a66c1343bde4788ba"),
    "decimal": ("0208-seed-oracle.py", "cf4041c69e5204f79ab6786be5e393c0dbc0977317e693587eb1a85e8265e475"),
    "io": ("0206-readiness-runner.py", "ff1cd800a74f40f3bc91f74550c4b49205713f391d436e37360e92a9740c1a1e"),
    "readback": ("0210-retained-readback.py", None),
    "runner": (HERE.name, None),
}
PROPOSALS = {"retained": "analytic-command-proposal", "artificial": "artificial-command-proposal"}
REFUSAL = "command-seed-unavailable"
INVALID = "invalid-evidence"
ZERO = dict(spice_queries=0, kernel_accesses=0, force_evaluations=0, integrations=0, r560_attempts=0)
NO_AUTHORITY = dict(live_authorized=False, physical_launch_authorized=False,
                    physical_status="physical-join-not-established",
                    physical_residuals=dict.fromkeys(("epoch_s", "position_m", "velocity_m_s", "mass_kg")))


def _need(ok: object, why: str) -> None:
    if not ok:
        raise ValueError(why)


def _elapsed(started: int, wall: int) -> int:
    elapsed = monotonic_ns() - started
    _need(0 <= elapsed < wall <= 15 * NS, "R5.59c shared deadline")
    return elapsed


def _read_method(name: str) -> bytes:
    filename, pin = METHODS[name]
    fd = os.open(HERE.with_name(filename), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        _need(stat.S_ISREG(info.st_mode) and info.st_size <= 64 * 1024, f"{name}: method file type or size")
        raw = source.read(64 * 1024 + 1)
    _need(len(raw) == info.st_size and (pin is None or sha256(raw).hexdigest() == pin), f"{name}: method pin")
    return raw


def _load(name: str, raw: bytes) -> ModuleType:
    module = ModuleType("_r559c_" + name)
    module.__file__ = str(HERE.with_name(METHODS[name][0]))
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, "exec"), vars(module))
    return module


def _inputs(adapter: ModuleType, artificial: Artificial | None) -> tuple[dict[str, Path], Row, Any]:
    retained = {name: (HERE.parent.parent if name == adapter.CONTRACT else HERE.parent) / name
                for name in adapter.RETAINED_PINS}
    if artificial is None:
        return retained, dict(adapter.RETAINED_PINS), adapter.RETAINED_PROFILE
    directory, pins, words = artificial
    root = directory.resolve()
    paths = {name: root / name for name in retained}
    _need(not (set(paths.values()) & set(retained.values())) and set(pins) == set(paths)
          and not set(pins.values()) & set(adapter.RETAINED_PINS.values()), "artificial paths or pins")
    return paths, pins, adapter.ArchiveProfile("artificial-moon-mars", tuple(words))


def _guard(paths: dict[str, Path], output: Path) -> list[str]:
    sources = {str(path): name for name, path in paths.items()}
    attempts: list[str] = []
    method_files = {str(HERE.with_name(filename)) for filename, _ in METHODS.values()}
    output_files = {str(output / name) for name in FILES}
    stdlib = str(Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}") + os.sep

    def deny(event: str, args: tuple[Any, ...]) -> None:
        if event == "import":
            name = str(args[0]).split(".", 1)[0]
            _need(name in sys.stdlib_module_names and name not in {"ctypes", "_ctypes"}, f"out-of-scope module: {name}")
        elif event == "open" and not isinstance(args[0], int):
            path = os.path.normpath(os.fsdecode(args[0]))
            reading = not int(args[2]) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            if path in sources:
                _need(reading and sources[path] not in attempts, "archive read must be unique and read-only")
                attempts.append(sources[path])
            else:
                _need(path in output_files or (reading and (path in method_files
                      or path in {str(output), str(output.parent)}
                      or (path.startswith(stdlib) and path.endswith((".py", ".pyc", ".so"))))),
                      f"out-of-scope file: {Path(path).name}")
        else:
            _need(event not in {"subprocess.Popen", "os.system", "socket.__new__", "ctypes.dlopen",
                                "os.fork", "os.exec", "os.posix_spawn"}, f"out-of-scope operation: {event}")

    sys.addaudithook(deny)
    return attempts


def _identity(methods: dict[str, bytes], pins: Row, profile: Any, mode: str) -> Row:
    return dict(schema="ariadna-r559c-evidence-v1", stage="R5.59c", mode=mode,
                candidate_id=profile.candidate_id, epoch_words=list(profile.epoch_words), source_pins=pins,
                source_sha256={name: sha256(raw).hexdigest() for name, raw in methods.items()},
                arithmetic="local-point-mass-impulse-surrogate",
                command_order=["departure_azimuth_rad", "departure_elevation_rad", "departure_duration_s",
                               "arrival_azimuth_rad", "arrival_elevation_rad", "arrival_duration_s"])


def _evaluate(normalized: Row, core: ModuleType, oracle: ModuleType,
              check_deadline: Callable[[], None]) -> Row:
    audits: Row = {}
    roots = []
    evidence = dict(status=REFUSAL, command_words=None, branch_decisions=audits, pairs=[])
    for endpoint in normalized["endpoints"]:
        check_deadline()
        body = endpoint["body"]
        try:
            accepted, audits[body] = core.audited_roots(endpoint, endpoint["v_infinity_m_s"], oracle,
                                                       arrival=body == "Mars")
        except core.Unavailable as error:
            accepted, audits[body] = {}, dict(rejected=str(error))
        roots.append(accepted)
    if any("rejected" in group or any(branch["reason"] not in (None, "guard", "degenerate")
                                      for branch in group.values()) for group in audits.values()):
        return evidence | dict(reason="unresolved-geometry")
    excluded = {tuple(float.fromhex(word) for word in row) for row in normalized["rejected_command_words"]}
    for a_sign, a in roots[0].items():
        for b_sign, b in roots[1].items():
            check_deadline()
            speeds = tuple(Decimal(audits[body][sign]["independent_speed_m_s"])
                           for body, sign in (("Moon", a_sign), ("Mars", b_sign)))
            with localcontext(prec=96):
                oracle_total = str(speeds[0] + speeds[1])
            pair: Row = dict(roots=[a_sign, b_sign], reason=None, total_delta_v_m_s=a.speed + b.speed,
                             oracle_total_delta_v_m_s=oracle_total)
            evidence["pairs"].append(pair)
            durations, masses = core.sequence(a.speed, b.speed)
            other_durations, other_masses = oracle.mass(*speeds)
            duration_error = max(abs(x - float(y)) for x, y in zip(durations, other_durations, strict=True))
            mass_error = max(abs(x - float(y)) for x, y in zip(masses, other_masses, strict=True))
            pair["independent_mass_discrepancies"] = dict(duration_s=duration_error, mass_kg=mass_error)
            if duration_error > core.DURATION_LIMIT_S or mass_error > core.MASS_LIMIT_KG:
                pair["reason"] = "independent-mass"
                continue
            try:
                pair["ledgers"] = core.ledgers(normalized["epochs_tdb_s"], durations)
            except core.Unavailable as error:
                pair["reason"] = str(error)
                continue
            commands = (*core.angles_of(a.tnw), durations[0], *core.angles_of(b.tnw), durations[1])
            if commands in excluded:
                pair["reason"] = "historically-rejected"
                continue
            pair["command_words"] = [value.hex() for value in commands]
            pair["ideal_end_masses_kg"] = masses
    if any(pair["reason"] == "independent-mass" for pair in evidence["pairs"]):
        return evidence | dict(reason="unresolved-mass")
    try:
        selected = core.rank(evidence["pairs"])
    except core.Unavailable as error:
        return evidence | dict(reason=str(error))
    return evidence | dict(status=PROPOSALS[normalized["scope"]], command_words=selected["command_words"],
                           selected_roots=selected["roots"])


def _files(output: Path, io: ModuleType, names: tuple[str, ...]) -> list[tuple[Row, str]]:
    with os.scandir(output) as entries:
        found = {entry.name for _, entry in zip(range(len(names) + 1), entries)}
    _need(found == set(names), "evidence missing, extra or incomplete")
    result: list[tuple[Row, str]] = []
    for name in names:
        raw = io._read(output / name, REPORT_CAP if name == FILES[1] else SMALL)
        row = io._row(raw)
        _need(io._wire(row) == raw, "evidence encoding")
        result.append((row, io._sha(raw)))
    return result


def _exit_code(status: str) -> int:
    return 0 if status in PROPOSALS.values() else 2 if status == REFUSAL else 3


def _audit(records: list[tuple[Row, str]], identity: Row, io: ModuleType, reader: ModuleType) -> tuple[Row, str, Row]:
    (attempt, a_sha), (report, r_sha), (receipt, c_sha) = records
    run_id = attempt.get("run_id")
    for row in (attempt, report, receipt):
        _need(all(row.get(key) == value for key, value in identity.items()), "source or method identity")
        _need(row.get("run_id") == run_id, "attempt identity")
    _need(type(run_id) is str and len(run_id) == 32 and all(c in "0123456789abcdef" for c in run_id),
          "invalid attempt identifier")
    _need(a_sha == report.get("attempt_sha256") == receipt.get("attempt_sha256")
          and r_sha == receipt.get("report_sha256") and report.get("status") == receipt.get("status"),
          "report or receipt binding")
    wall, checked = attempt.get("wall_ns"), receipt.get("elapsed_before_receipt_ns")
    _need(type(wall) is int and type(checked) is int and 0 <= checked < wall <= 15 * NS, "receipt deadline")
    required = ZERO | NO_AUTHORITY | dict(r559c_attempts=int(identity["mode"] == "retained"))
    _need(all(type(report.get(key)) is type(value) and report[key] == value for key, value in required.items()),
          "offline work or authority binding")
    attempts = report.get("archive_open_attempts")
    _need(isinstance(attempts, list) and len(attempts) <= len(identity["source_pins"])
          and all(type(name) is str and name in identity["source_pins"] for name in attempts)
          and len(set(attempts)) == len(attempts)
          and (report.get("status") == INVALID or set(attempts) == set(identity["source_pins"])),
          "archive open count")
    reader.validate_science(report, io)
    return report, c_sha, attempt


def _child(artificial: Artificial | None, output: Path, run_id: str, started: int, wall: int) -> int:
    _need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "worker must use -I -S -B")
    _elapsed(started, wall)
    mode = "retained" if artificial is None else "artificial"
    _need((output == RETAINED_OUTPUT) == (mode == "retained"), "retained evidence destination")
    adapter_raw = _read_method("adapter")
    adapter = _load("adapter", adapter_raw)
    paths, pins, profile = _inputs(adapter, artificial)
    opened = _guard(paths, output)
    methods = {"adapter": adapter_raw} | {name: _read_method(name) for name in METHODS if name != "adapter"}
    identity = _identity(methods, pins, profile, mode)
    io = _load("io", methods["io"])
    reader = _load("readback", methods["readback"])
    header = identity | dict(run_id=run_id)

    def check_deadline() -> None:
        _elapsed(started, wall)

    check_deadline()
    output.mkdir(mode=0o700)
    io._sync(output.parent)
    a_sha = io._put(output / FILES[0], header | dict(wall_ns=wall), SMALL)
    common = header | ZERO | NO_AUTHORITY | dict(attempt_sha256=a_sha, r559c_attempts=int(mode == "retained"))
    try:
        normalized = adapter.prepare(paths, pins, profile, check_deadline=check_deadline)
        core, oracle = (_load(name, methods[name]) for name in ("binary64", "decimal"))
        verdict = _evaluate(normalized, core, oracle, check_deadline)
        report = verdict | common | dict(normalized=normalized, normalized_sha256=io._sha(io._wire(normalized)),
                                         archive_open_attempts=opened)
        _need(len(io._wire(report)) <= REPORT_CAP, "report byte cap")
    except (OSError, ValueError, ArithmeticError, RecursionError) as error:
        report = common | dict(status=INVALID, command_words=None, normalized=None, normalized_sha256=None,
                               branch_decisions={}, pairs=[], archive_open_attempts=opened,
                               error=f"{type(error).__name__}: {error}"[:512])
    check_deadline()
    r_sha = io._put(output / FILES[1], report, REPORT_CAP)
    receipt = header | dict(attempt_sha256=a_sha, report_sha256=r_sha, status=report["status"],
                            elapsed_before_receipt_ns=_elapsed(started, wall))
    c_sha = io._put(output / FILES[2], receipt, SMALL)
    saved, saved_receipt, saved_attempt = _audit(_files(output, io, FILES[:3]), identity, io, reader)
    _need(c_sha == saved_receipt and saved_attempt["run_id"] == run_id and saved_attempt["wall_ns"] == wall,
          "saved result binding")
    code = _exit_code(saved["status"])
    io._put(output / FILES[3], dict(run_id=run_id, receipt_sha256=c_sha, exit_code=code,
                                    elapsed_through_readback_ns=_elapsed(started, wall)), SMALL)
    check_deadline()
    return code


def verify_result(output: Path, *, artificial: Artificial | None = None,
                  expected_completion_sha256: str | None = None) -> Row:
    """Authenticate saved evidence without reading archives or evaluating roots."""
    methods = {name: _read_method(name) for name in METHODS}
    adapter = _load("adapter", methods["adapter"])
    _, pins, profile = _inputs(adapter, artificial)
    identity = _identity(methods, pins, profile, "retained" if artificial is None else "artificial")
    io, reader = (_load(name, methods[name]) for name in ("io", "readback"))
    records = _files(output, io, FILES)
    report, c_sha, attempt = _audit(records[:3], identity, io, reader)
    completion, digest = records[3]
    elapsed = completion.get("elapsed_through_readback_ns")
    code = completion.get("exit_code")
    _need(completion.get("receipt_sha256") == c_sha and completion.get("run_id") == attempt["run_id"]
          and type(elapsed) is int and records[2][0]["elapsed_before_receipt_ns"] <= elapsed < attempt["wall_ns"]
          and type(code) is int and code == _exit_code(report["status"]), "completion binding")
    if expected_completion_sha256 is not None:
        _need(digest == expected_completion_sha256, "completion hash")
    return report


def _discard_late_witness(output: Path, run_id: str) -> None:
    try:
        io = _load("io", _read_method("io"))
        witness = output / FILES[3]
        if io._row(io._read(witness, SMALL)).get("run_id") == run_id:
            witness.unlink()
            io._sync(output)
    except (OSError, ValueError):
        pass


def launch(output: Path, *, artificial: Artificial | None = None) -> int:
    """Watch one worker through startup, saved audit, and durable completion."""
    started = monotonic_ns()
    wall = int(WALL_S * NS)
    output = output.absolute()
    _need((output == RETAINED_OUTPUT) == (artificial is None), "retained evidence destination")
    if os.path.lexists(output):
        return 3
    fake_args = [] if artificial is None else [str(artificial[0].absolute()),
                                                json.dumps(artificial[1]), json.dumps(artificial[2])]
    run_id = uuid4().hex
    try:
        process = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(HERE), "child", str(output), run_id, str(started), str(wall),
             *fake_args], timeout=(wall - _elapsed(started, wall)) / NS,
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
    if args == ["retained"]:
        return launch(RETAINED_OUTPUT)
    if len(args) in (5, 8) and args[0] == "child":
        _, output, run_id, started, wall, *fake = args
        artificial = (Path(fake[0]), json.loads(fake[1]), tuple(json.loads(fake[2]))) if fake else None
        return _child(artificial, Path(output), run_id, int(started), int(wall))
    raise ValueError("usage: python -I -S -B 0210-retained-runner.py retained")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(4) from None
