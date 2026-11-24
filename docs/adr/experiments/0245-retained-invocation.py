"""One bounded saved attempt, qualified through the same fabricated lifecycle."""
from collections.abc import Callable
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic_ns
from types import ModuleType
from typing import Any
from uuid import uuid4

Row = dict[str, Any]
Read = Callable[[Path, int], bytes]
Check = Callable[[], None]
HERE = Path(__file__).resolve()
CAP = 4 * 1024**2
WALL_NS = 30_000_000_000
LAUNCH_CAP = 4096
AUDIT_CAP = 64 * 1024
PRODUCER_CAP = CAP - LAUNCH_CAP - AUDIT_CAP
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
ARCHIVE_FILES = (*FILES[:3], "audit.json")
OUTPUT = HERE.with_name("0243-p3-retained")
BINDING = HERE.with_name("0245-binding.json")
READINESS = HERE.with_name("0245-readiness.json")
METHODS: dict[str, tuple[str, str | None]] = {
    "io": ("0206-readiness-runner.py", "ff1cd800a74f40f3bc91f74550c4b49205713f391d436e37360e92a9740c1a1e"),
    "core": ("0208-seed-worksheet.py", "4907db44f0ef53cb657cd563a6fa27df8a138442807c703a66c1343bde4788ba"),
    "oracle": ("0208-seed-oracle.py", "cf4041c69e5204f79ab6786be5e393c0dbc0977317e693587eb1a85e8265e475"),
    "reader": ("0210-retained-readback.py", "a6e1b9a32f0c46c9e03974c1367a8b04d2849eca86d807907a3bcefa1f0e8920"),
    "orbit": ("0213-phase-orbit.py", "ba78ca47097703cb27ed7dca8d844b9be34c61b1fee9a5668fae97db039979c3"),
    "screen": ("0213-phase-screen.py", "39d59baecb394f759ef6a775ce6cca548e4828dbfef94207b47c9e048d1d0f2b"),
    "archive": ("0220-phase-archive.py", "43c4c3b7fe1f82324a4833ea74a22aaed9922e8c0f9ea67fa0aa76161062dcf8"),
    "anchors": ("0220-phase-anchors.py", "7fadcb3fc9de4a43aa1ce80efd30d2e6499f76ee4918519cf8783d50bca2057e"),
    "points": ("0244-phase-points.py", "5c8d8b549419ba93199fc7c42db99b7160e15e30a9ba54562ae97061918e5440"),
    "search": ("0241-bounded-search.py", "dba342eadc49a34e0cdc0ec6bed06fdb8e3595457cb250d36b7b2d38ecffcbdd"),
    "runtime": ("0241-runtime.py", "3863f812f210d162c9834e73b6f15672d9a2ff4d4c2d3fc5df0eb83e50f86ff1"),
    "trace": ("0241-trace-audit.py", "f564df19de8c4b614d69af26fd0df7774a8b73e48954e0d857b4d74a17c22f14"),
    "legacy_audit": ("0241-bounded-invocation.py", "ed7956d5ec65d5693309773a2361295fe097ff5357cca5b27cb0a74c4f64c524"),
    "invocation": (HERE.name, None),
}
SAVED: dict[str, tuple[str, int, str]] = {
    "attempt.json": ("0215-r559f/attempt.json", 1508, "ac1d02f445ebed82ac5b4f728193ea8533890188ed2422117523db50d087bf0a"),
    "report.json": ("0215-r559f/report.json", 1059325, "323c2c71e17168a46e9dd5280015a3fecb0865016b9b6954dcb051de4def1800"),
    "receipt.json": ("0215-r559f/receipt.json", 1727, "395d20ab4771b9a9e4743e038e5c50338d12b8d890018befc3879bf3de21a18b"),
    "audit.json": ("0217-saved-grid-audit.json", 3398, "bdc9eb8225a4af912327d0c8cd62231bf4f625991f6d4233ea58a5e9481172d5"),
}
RUNTIME_PINS = {
    "producer": "e72b42dcd8caeb40e27f2f46c90bcb60b230069deb1efd516636e7c1e8c0f4e9",
    "audit": "69d1a5784fec1c9e17bd2e02e7a733507837b76b7fadf30834f1386802ff6d2d",
}
SOLVER_PINS = {
    "_minimize.py": "5afd3ecbeaba6606c27f5f9f298782c0dae80dd0e3e01d98d4249922ede6b7ea",
    "_optimize.py": "041a1807ccaa68115c93b07bed497d25c294a7d730ce5a7cb1f21fc5a185fa61",
}


def need(value: object, reason: str) -> None:
    if not value:
        raise ValueError("bounded retained invocation: " + reason)


def _wire(row: Row) -> bytes:
    return (json.dumps(row, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _pin(value: object) -> None:
    need(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value), "SHA-256 required")


def _json(raw: bytes) -> Row:
    def pairs(values: list[tuple[str, Any]]) -> Row:
        result: Row = {}
        for key, value in values:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ValueError("nonfinite JSON: " + value)

    def finite(value: str) -> float:
        result = float(value)
        need(math.isfinite(result), "nonfinite JSON number")
        return result

    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite)
    except RecursionError as error:
        raise ValueError("JSON nesting limit") from error
    need(type(result) is dict, "JSON object required")
    return result


def _load(name: str, raw: bytes, path: Path) -> ModuleType:
    module = ModuleType("_retained_bounded_" + name)
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), vars(module))
    return module


def _raw_read(path: Path, cap: int) -> bytes:
    """Bound bootstrap reads before the pinned I/O module can be loaded."""
    need(type(cap) is int and cap >= 0, "bootstrap remaining byte cap")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        entry = os.fstat(stream.fileno())
        need(entry.st_mode & 0o170000 == 0o100000 and entry.st_size <= cap,
             "bootstrap file type/byte cap")
        raw = stream.read(cap + 1)
    need(len(raw) <= cap and len(raw) == entry.st_size, "bootstrap input changed")
    return raw


def _bootstrap(read: Read | None = None) -> ModuleType:
    path = HERE.with_name(METHODS["io"][0])
    raw = (read or _raw_read)(path, CAP)
    need(sha256(raw).hexdigest() == METHODS["io"][1], "I/O bootstrap pin")
    return _load("io_bootstrap", raw, path)


def source_map(read: Read | None = None) -> dict[str, str]:
    """Authenticate executable sources only; never open saved scientific inputs."""
    reader = read or _bootstrap()._read
    result = {}
    for role, (name, pin) in METHODS.items():
        raw = reader(HERE.with_name(name), CAP)
        digest = sha256(raw).hexdigest()
        need(pin is None or digest == pin, "immutable source pin: " + role)
        result[role] = digest
    return result


def _flags(scope: str) -> Row:
    return dict(scope=scope, synthetic=scope == "artificial", live_authorized=False,
                physical_launch_authorized=False, commands=None,
                physical_status="physical-join-not-established", spice_queries=0,
                kernel_accesses=0, force_evaluations=0, integrations=0,
                retained_attempts=int(scope == "retained"), r560_attempts=0,
                interval_cells=0, signed_bounds=0)


def _paths(config: Row) -> dict[str, Path]:
    if config["scope"] == "retained":
        paths = {name: HERE.parent / row[0] for name, row in SAVED.items()}
        need(all(not path.is_symlink() and not path.parent.is_symlink() for path in paths.values()),
             "retained scientific symlink")
        return paths
    root = Path(config["source_dir"]).absolute()
    need(not root.is_symlink() and not root.resolve().is_relative_to(HERE.parents[3]), "external artificial source")
    return {name: root / name for name in ARCHIVE_FILES}


def _configuration(raw: bytes, pin: str, config_path: Path, output: Path, sources: Row) -> Row:
    _pin(pin)
    need(sha256(raw).hexdigest() == pin, "external configuration pin")
    config = _json(raw)
    need(_wire(config) == raw and config["schema"] == "ariadna-p3-retained-binding-v1", "canonical binding schema")
    scope = config["scope"]
    need(scope in {"artificial", "retained"}, "binding scope")
    need(type(config["source_pins"]) is dict and set(config["source_pins"]) == set(ARCHIVE_FILES), "four scientific roles")
    for value in config["source_pins"].values():
        _pin(value)
    need(config["source_sha256"] == sources, "qualified executable source map")
    need(config["driver"] in {"bounded", "artificial-full-volume"}, "qualification driver")
    for mode in ("producer", "audit"):
        profile = config[mode + "_profile"]
        need(type(profile) is dict and set(profile) == {"runtime", "solver_sources"}, "runtime profile fields")
        runtime = profile["runtime"]
        need(type(runtime) is dict and runtime["schema"] == "ariadna-bounded-runtime-v1", "runtime profile schema")
        need(profile["solver_sources"] == (SOLVER_PINS if mode == "producer" else {}), "fixed selected solver sources")
    if scope == "retained":
        need(config_path.absolute() == BINDING and output.absolute() == OUTPUT
             and config["source_dir"] == str(HERE.parent) and config["driver"] == "bounded", "fixed retained paths/method")
        need(config["source_pins"] == {name: row[2] for name, row in SAVED.items()}, "fixed four retained pins")
        for mode in ("producer", "audit"):
            digest = sha256(_wire(config[mode + "_profile"]["runtime"])).hexdigest()
            need(digest == RUNTIME_PINS[mode], "unchanged qualified runtime table: " + mode)
    else:
        need(not config_path.resolve().is_relative_to(HERE.parents[3])
             and not output.resolve().is_relative_to(HERE.parents[3]), "external artificial configuration/output")
        need(not set(config["source_pins"].values()) & {row[2] for row in SAVED.values()}, "artificial/retained pin overlap")
    _paths(config)
    return config


def _read_result(path: Path, io: ModuleType, check: Check,
                 completion_pin: str | None = None, *, read: Read | None = None) -> tuple[Row, int]:
    """Authenticate a completed process structurally, without numerical replay."""
    reader = read or io._read
    need(not path.is_symlink(), "symlink evidence")
    with os.scandir(path) as contents:
        names = {entry.name for _, entry in zip(range(len(FILES) + 1), contents)}
    need(names == set(FILES), "exact evidence inventory")
    entries, size = [], 0
    for name in FILES:
        check()
        raw = reader(path / name, CAP - size)
        size += len(raw)
        row = _json(raw)
        need(_wire(row) == raw, "noncanonical evidence")
        entries.append((row, sha256(raw).hexdigest()))
    (attempt, a), (report, r), (receipt, s), (completion, c) = entries
    need(completion_pin is None or c == completion_pin, "external completion pin")
    need(report["attempt_sha256"] == receipt["attempt_sha256"] == a
         and receipt["report_sha256"] == r and completion["receipt_sha256"] == s, "evidence chain")
    need(attempt["schema"] == "ariadna-p3-retained-process-v1" and attempt["mode"] in {"producer", "audit"}, "process schema/mode")
    need(all(report.get(key) == value and type(report.get(key)) is type(value) for key, value in attempt.items()), "attempt/report identity")
    scope = attempt["scope"]
    need(scope in {"artificial", "retained"}, "evidence scope")
    need(all(row.get(key) == value and type(row.get(key)) is type(value)
             for row in (attempt, report) for key, value in _flags(scope).items()), "scope or prohibited work")
    need(all(row["run_id"] == attempt["run_id"] for row in (report, receipt, completion)), "run identity")
    wall = attempt["wall_ns"]
    need(type(wall) is int and 0 < wall <= WALL_NS
         and type(receipt["elapsed_ns"]) is int and 0 <= receipt["elapsed_ns"] < wall
         and type(completion["elapsed_ns"]) is int
         and receipt["elapsed_ns"] <= completion["elapsed_ns"] < wall, "saved deadline")
    status = report["status"]
    need(status in {"verified-analytical-witness", "inconclusive/invalid", "recorded-point-audit-verified", "process-invalid"}, "process status")
    successful = status in {"verified-analytical-witness", "recorded-point-audit-verified"}
    need(type(completion["exit_code"]) is int and completion["exit_code"] == (0 if successful else 2)
         and receipt["status"] == status, "process exit/status mapping")
    budget = PRODUCER_CAP if attempt["mode"] == "producer" else AUDIT_CAP
    need(size <= budget and report["readback_bytes"] == size
         and type(report["source_bytes"]) is int and size <= report["source_bytes"] <= CAP, "process byte accounting")
    if attempt["mode"] == "producer" and status != "process-invalid":
        result = report["result"]
        need(status == result["status"] and result["disposition"] in {"witness", "inconclusive"}, "complete producer disposition")
        need(type(result["phases"]) is list and 3 <= len(result["phases"]) <= 129
             and all(type(row) is dict and type(row.get("point")) is dict and row.get("error") is None
                     for row in result["phases"]), "partial producer transcript")
    check()
    return report, size


def _binding(report: Row, config: Row, invocation: Row, mode: str, started: int,
             wall: int, completion_pin: str | None) -> None:
    need(report["mode"] == mode and report["run_id"] == invocation[mode + "_run_id"]
         and report["launch_id"] == invocation["launch_id"] and report["started_ns"] == started
         and report["wall_ns"] == wall and report["config_sha256"] == invocation["config_sha256"]
         and report["scope"] == config["scope"] and report["source_sha256"] == config["source_sha256"]
         and report["source_pins"] == config["source_pins"], "process/parent/source/input binding")
    profile = config[mode + "_profile"]
    need(report["runtime"] == profile["runtime"] and report["solver_sources"] == profile["solver_sources"], "process runtime binding")
    runtime_reads = report["runtime_read_bytes"]
    need(type(runtime_reads) is int and 0 <= runtime_reads <= profile["runtime"]["runtime_read_cap_bytes"],
         "process runtime read-byte accounting")
    need(report["producer_completion_sha256"] == completion_pin, "audit producer completion binding")
    need(report["status"] != "process-invalid", "failed process is not auditable")


def _private() -> set[Path]:
    import sysconfig
    solver = Path(sysconfig.get_path("purelib")) / "scipy" / "optimize"
    return {HERE.with_name(name) for name, _ in METHODS.values()} | {solver / name for name in SOLVER_PINS}


def _methods(io: ModuleType, expected: Row, check: Check) -> dict[str, ModuleType]:
    methods = {}
    for role, (name, pin) in METHODS.items():
        check()
        raw = io._read(HERE.with_name(name), CAP)
        digest = sha256(raw).hexdigest()
        need((pin is None or digest == pin) and expected.get(role) == digest, "qualified source drift: " + role)
        if role not in {"runtime", "invocation"}:
            methods[role] = _load(role, raw, HERE.with_name(name))
    need(set(expected) == set(METHODS), "source role inventory")
    return methods


def _archive(config: Row, io: ModuleType, methods: dict[str, ModuleType], check: Check) -> Row:
    records = {}
    paths = _paths(config)
    expected = set(FILES[:3] if config["scope"] == "retained" else ARCHIVE_FILES)
    with os.scandir(paths["attempt.json"].parent) as contents:
        need({entry.name for _, entry in zip(range(len(expected) + 1), contents)} == expected,
             "exact scientific archive inventory")
    for name, path in paths.items():
        check()
        raw = io._read(path, CAP)
        digest = sha256(raw).hexdigest()
        need(digest == config["source_pins"][name], "scientific role pin: " + name)
        if config["scope"] == "retained":
            need(len(raw) == SAVED[name][1], "fixed scientific role size: " + name)
        row = _json(raw)
        canonical = ((json.dumps(row, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
                     if name == "audit.json" else _wire(row))
        need(raw == canonical, "historical role encoding: " + name)
        records[name] = row, digest
    return methods["archive"].bind(records, io, retained=config["scope"] == "retained")


def _finalize(output: Path, attempt: Row, attempt_pin: str, report: Row, io: ModuleType,
              guard: Any, started: int, check: Check) -> int:
    """Reserve and charge every own-output read before writing immutable evidence."""
    status, run_id = report["status"], attempt["run_id"]
    code = 0 if status in {"verified-analytical-witness", "recorded-point-audit-verified"} else 2
    receipt = dict(run_id=run_id, attempt_sha256=attempt_pin, status=status, elapsed_ns=monotonic_ns() - started)
    completion = dict(run_id=run_id, exit_code=code, elapsed_ns=receipt["elapsed_ns"])
    before, size = guard.source_bytes, 0
    for _ in range(12):
        report["source_bytes"] = before + size
        report["readback_bytes"] = size
        receipt["report_sha256"] = sha256(_wire(report)).hexdigest()
        completion["receipt_sha256"] = sha256(_wire(receipt)).hexdigest()
        updated = sum(len(_wire(row)) for row in (attempt, report, receipt, completion))
        if updated == size:
            break
        size = updated
    else:
        raise ValueError("evidence accounting did not settle")
    budget = PRODUCER_CAP if attempt["mode"] == "producer" else AUDIT_CAP
    need(size <= budget and before + size <= CAP, "finalization evidence/source byte cap")
    check()
    io._put(output / FILES[1], report, budget - 3 * LAUNCH_CAP)
    io._put(output / FILES[2], receipt, LAUNCH_CAP)
    io._put(output / FILES[3], completion, LAUNCH_CAP)
    guard.source_bytes += size
    checked, actual = _read_result(output, io, check)
    need(actual == size and checked["source_bytes"] == guard.source_bytes, "durable readback accounting")
    check()
    return code


def _worker(mode: str, config_path: Path, config_pin: str, output: Path, run_id: str,
            started: int, wall: int, completion_pin: str | None) -> int:
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "isolated cold worker required")
    need(mode in {"producer", "audit"} and type(wall) is int and 0 < wall <= WALL_NS, "worker mode/deadline")

    def check() -> None:
        need(0 <= monotonic_ns() - started < wall, "shared deadline")

    check()
    need(not config_path.is_symlink() and not output.is_symlink()
         and output.is_dir() and not (output / mode).exists(), "reserved exclusive worker output")
    initial = HERE.stat().st_size

    def bootstrap_read(path: Path, cap: int) -> bytes:
        nonlocal initial
        check()
        raw = _raw_read(path, min(cap, CAP - initial))
        initial += len(raw)
        return raw

    io = _bootstrap(bootstrap_read)
    runtime_path = HERE.with_name(METHODS["runtime"][0])
    runtime_raw = bootstrap_read(runtime_path, CAP)
    need(sha256(runtime_raw).hexdigest() == METHODS["runtime"][1], "runtime bootstrap pin")
    runtime = _load("runtime_bootstrap", runtime_raw, runtime_path)
    config_raw = bootstrap_read(config_path, CAP)
    raw = bootstrap_read(output / "invocation.json", LAUNCH_CAP)
    invocation = _json(raw)
    need(_wire(invocation) == raw and invocation["schema"] == "ariadna-p3-retained-launch-v1"
         and invocation["config_sha256"] == config_pin and invocation[mode + "_run_id"] == run_id,
         "reserved invocation identity")
    # Bootstrap reads share the same remaining-byte ledger as guarded inputs.
    config = _configuration(config_raw, config_pin, config_path, output, _json(config_raw)["source_sha256"])
    need(invocation["scope"] == config["scope"]
         and invocation["source_sha256"] == config["source_sha256"]
         and invocation["source_pins"] == config["source_pins"]
         and invocation["producer_cap_bytes"] == PRODUCER_CAP
         and invocation["audit_cap_bytes"] == AUDIT_CAP and invocation["total_cap_bytes"] == CAP,
         "fixed launcher binding")
    need(mode == "audit" or invocation["started_ns"] == started,
         "producer parent clock binding")
    need(invocation["wall_ns"] == wall and type(invocation["started_ns"]) is int
         and invocation["started_ns"] <= started, "launcher deadline binding")
    inputs = {config_path, output / "invocation.json", *_paths(config).values()}
    if config["scope"] == "retained":
        raw = bootstrap_read(READINESS, LAUNCH_CAP)
        readiness = _json(raw)
        need(_wire(readiness) == raw and readiness["schema"] == "ariadna-p3-retained-readiness-v1"
             and readiness["status"] == "qualified" and readiness["binding_sha256"] == config_pin,
             "fixed retained readiness receipt")
        inputs.add(READINESS)
    if mode == "audit":
        _pin(completion_pin)
        inputs.update(output / "producer" / name for name in FILES)
    else:
        need(completion_pin is None, "producer cannot supply a prior completion")
    destination = output / mode
    profile = config[mode + "_profile"]
    guard = runtime.Guard(_private(), inputs, destination, check, profile["runtime"], scientific=mode == "producer")
    guard.source_bytes += initial
    need(guard.source_bytes <= CAP, "bootstrap source/input byte cap")
    sys.addaudithook(guard.hook)
    destination.mkdir(mode=0o700)
    io._sync(output)
    attempt = _flags(config["scope"]) | dict(schema="ariadna-p3-retained-process-v1", mode=mode,
        run_id=run_id, launch_id=invocation["launch_id"], started_ns=started, wall_ns=wall,
        config_sha256=config_pin, producer_completion_sha256=completion_pin)
    attempt_pin = io._put(destination / FILES[0], attempt, LAUNCH_CAP)
    result: Row = {}
    report = attempt | dict(attempt_sha256=attempt_pin, status="process-invalid", result=result)
    try:
        methods = _methods(io, config["source_sha256"], check)
        runtime.authenticate(guard)
        if mode == "producer":
            minimize, identity = runtime.prepare(guard)
        else:
            minimize = None
            identity = dict(python=list(sys.version_info[:3]), prefix=str(Path(sys.base_prefix).resolve()), numpy=None, scipy=None)
        solver_sources = {}
        if mode == "producer":
            import sysconfig
            for name in SOLVER_PINS:
                path = Path(sysconfig.get_path("purelib")) / "scipy" / "optimize" / name
                solver_sources[name] = sha256(io._read(path, CAP)).hexdigest()
        need(solver_sources == profile["solver_sources"], "selected solver source identity")
        manifest = runtime.fingerprint(guard, identity)
        source = _archive(config, io, methods, check)
        if mode == "producer":
            def point(phase: float) -> Row:
                check()
                return methods["points"].point(source["reference"], phase, methods)

            def anchor(row: Row, degree: int) -> None:
                methods["anchors"].verify_anchor(source["anchors"][degree - 150], row, degree, methods["reader"])

            if config["driver"] == "artificial-full-volume":
                def stress(objective: Callable[[float], float], **options: Any) -> Row:
                    cost = 0.0
                    for _ in range(62):
                        cost = objective(151.0)
                    return dict(x=151.0, fun=cost, success=False, nfev=62, nit=62, status=1,
                                message="Artificial full-volume driver; not a Brent result")
                minimize = stress
            result = methods["search"].search(point, anchor, minimize=minimize, check=check)
            result["qualification_driver"] = config["driver"]
            status = result["status"]
        else:
            producer, _ = _read_result(output / "producer", io, check, completion_pin)
            _binding(producer, config, invocation, "producer", invocation["started_ns"], invocation["wall_ns"], None)
            result = methods["legacy_audit"]._audit(source, producer, methods, check)
            result["status"] = "recorded-point-audit-verified"
            status = result["status"]
        report = attempt | dict(attempt_sha256=attempt_pin, status=status, result=result,
            source_sha256=config["source_sha256"], source_pins=config["source_pins"],
            runtime=manifest, solver_sources=solver_sources, runtime_read_bytes=guard.runtime_read_bytes)
    except (OSError, ValueError, ArithmeticError, KeyError, TypeError, AttributeError, ImportError) as error:
        report = attempt | dict(attempt_sha256=attempt_pin, status="process-invalid", result=result,
            error=f"{type(error).__name__}: {error}"[:1024], runtime_read_bytes=guard.runtime_read_bytes)
    return _finalize(destination, attempt, attempt_pin, report, io, guard, started, check)


def launch(config_path: Path, config_pin: str | None, output: Path, *,
           wall_ns: int = WALL_NS, retained: bool = False) -> int:
    """Reserve one attempt, then authenticate and audit its sole complete producer."""
    started = monotonic_ns()
    need(type(wall_ns) is int and 0 < wall_ns <= WALL_NS and type(retained) is bool,
         "parent deadline/route")
    config_path, output = config_path.absolute(), output.absolute()
    need(not output.is_symlink() and not config_path.is_symlink(), "symlink launch path")
    if retained:
        need(config_path == BINDING and output == OUTPUT and config_pin is None,
             "fixed retained command arguments")
    else:
        need(not config_path.resolve().is_relative_to(HERE.parents[3])
             and not output.resolve().is_relative_to(HERE.parents[3]), "external artificial route")
        _pin(config_pin)
    read_bytes = HERE.stat().st_size
    stage_started = started

    def check() -> None:
        need(0 <= monotonic_ns() - stage_started < wall_ns, "parent shared deadline")

    def read(path: Path, cap: int) -> bytes:
        nonlocal read_bytes
        check()
        raw = _raw_read(path, min(cap, CAP - read_bytes))
        read_bytes += len(raw)
        need(read_bytes <= CAP, "parent source/input byte cap")
        return raw

    io = _bootstrap(read)
    if retained:
        # Missing qualification is unavailable preparation, not a reserved attempt.
        raw = read(READINESS, LAUNCH_CAP)
        readiness = _json(raw)
        need(_wire(readiness) == raw and readiness["schema"] == "ariadna-p3-retained-readiness-v1"
             and readiness["status"] == "qualified", "retained binding not qualified")
        config_pin = readiness["binding_sha256"]
        _pin(config_pin)
    check()
    output.mkdir(mode=0o700)
    io._sync(output.parent)
    # An existing namespace is never resumed, even if it contains no evidence.
    launch_size = 0
    stage_records: list[Row] = []

    def terminal(code: int, status: str) -> int:
        evidence_bytes = sum(path.stat().st_size for path in
            [output / "invocation.json", *(output / mode / name
             for mode in ("producer", "audit") for name in FILES)] if path.is_file())
        if stage_records:
            stage_records[-1]["elapsed_ns"] = monotonic_ns() - stage_started
        if code in (0, 2):
            check()
        summary = dict(schema="ariadna-p3-retained-terminal-v1", terminal_status=status,
            exit_code=code, parent_source_bytes=read_bytes, evidence_bytes=evidence_bytes,
            parent_elapsed_ns=monotonic_ns() - started, stages=stage_records)
        raw = _wire(summary)
        need(len(raw) + launch_size <= LAUNCH_CAP and evidence_bytes + len(raw) <= CAP,
             "terminal telemetry/evidence reserve")
        if code in (0, 2):
            check()
        sys.stdout.write(raw.decode())
        sys.stdout.flush()
        if code in (0, 2):
            try:
                check()
            except ValueError:
                print("Parent deadline expired while flushing terminal telemetry", file=sys.stderr)
                return 3
        return code

    try:
        sources = source_map(read)
        config = _configuration(read(config_path, CAP), config_pin, config_path, output, sources)
        need(config["scope"] == ("retained" if retained else "artificial"), "command/binding scope")
        invocation = dict(schema="ariadna-p3-retained-launch-v1", launch_id=uuid4().hex,
            producer_run_id=uuid4().hex, audit_run_id=uuid4().hex, scope=config["scope"],
            config_sha256=config_pin, started_ns=started, wall_ns=wall_ns,
            source_sha256=sources, source_pins=config["source_pins"],
            producer_cap_bytes=PRODUCER_CAP, audit_cap_bytes=AUDIT_CAP, total_cap_bytes=CAP)
        io._put(output / "invocation.json", invocation, LAUNCH_CAP)
        launch_size = (output / "invocation.json").stat().st_size
        producer: Row = {}
        producer_pin = None
        for mode in ("producer", "audit"):
            if mode == "audit":
                stage_started = monotonic_ns()
            check()
            command = [sys.executable, "-I", "-S", "-B", str(HERE), "worker", mode,
                str(config_path), config_pin, str(output), invocation[mode + "_run_id"],
                str(stage_started), str(wall_ns), producer_pin or "-"]
            remaining = (wall_ns - (monotonic_ns() - stage_started)) / 1e9
            need(remaining > 0, "deadline before dispatch")
            try:
                done = subprocess.run(command, capture_output=True, timeout=remaining, check=False)
            except subprocess.TimeoutExpired:
                stage_records.append(dict(mode=mode, exit_code=None, elapsed_ns=monotonic_ns() - stage_started))
                raise
            stage_records.append(dict(mode=mode, exit_code=done.returncode, elapsed_ns=monotonic_ns() - stage_started))
            check()
            need(done.returncode in (0, 2), "worker exit code")
            report, size = _read_result(output / mode, io, check, read=read)
            _binding(report, config, invocation, mode, stage_started, wall_ns,
                     producer_pin if mode == "audit" else None)
            need(done.returncode == (0 if report["status"] in {"verified-analytical-witness", "recorded-point-audit-verified"} else 2),
                 "process exit/evidence mismatch")
            if mode == "producer":
                trace_path = HERE.with_name(METHODS["trace"][0])
                trace_raw = read(trace_path, CAP)
                need(sha256(trace_raw).hexdigest() == METHODS["trace"][1], "parent trace checker source")
                trace = _load("parent_trace", trace_raw, trace_path)
                need(trace.verify(report["result"])["verified"] is True,
                     "partial/invalid producer cannot receive numerical audit")
                producer = report
                producer_bytes = size
                producer_pin = sha256(read(output / mode / "completion.json", LAUNCH_CAP)).hexdigest()
                check()
                stage_records[-1]["elapsed_ns"] = monotonic_ns() - stage_started
            else:
                need(launch_size + producer_bytes + size <= CAP, "combined new evidence byte cap")
                result = report["result"]
                need(result["analytical_status"] == producer["status"]
                     and result["witness"] == producer["result"]["witness"]
                     and result["counters"] == producer["result"]["counters"]
                     and result["optimizer_calls"] == 0, "independent terminal agreement")
                check()
                stage_records[-1]["elapsed_ns"] = monotonic_ns() - stage_started
                return terminal(0 if producer["status"] == "verified-analytical-witness" else 2,
                                producer["status"])
    except subprocess.TimeoutExpired:
        return terminal(3, "invalid/unverified")
    except (OSError, ValueError, ArithmeticError, KeyError, TypeError, AttributeError) as error:
        print(f"{type(error).__name__}: {error}"[:1024], file=sys.stderr)
        return terminal(3, "invalid/unverified")
    return terminal(3, "invalid/unverified")


def main(args: list[str]) -> int:
    if len(args) == 9 and args[0] == "worker":
        _, mode, config, pin, output, run_id, started, wall, completion = args
        return _worker(mode, Path(config), pin, Path(output), run_id, int(started), int(wall),
                       None if completion == "-" else completion)
    if len(args) == 4 and args[0] == "artificial":
        _, config, pin, output = args
        return launch(Path(config), pin, Path(output))
    if args == ["retained"]:
        return launch(BINDING, None, OUTPUT, retained=True)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, ArithmeticError, KeyError, TypeError, AttributeError) as error:
        print(f"{type(error).__name__}: {error}"[:1024], file=sys.stderr)
        raise SystemExit(3)
