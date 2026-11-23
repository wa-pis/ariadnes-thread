"""Artificial-only bounded witness preparation; no retained command exists."""
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
HERE = Path(__file__).resolve()
CAP = 4 * 1024**2
WALL_NS = 30_000_000_000
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
ARCHIVE_FILES = (*FILES[:3], "audit.json")
METHODS: dict[str, tuple[str, str | None]] = {
    "io": ("0206-readiness-runner.py", "ff1cd800a74f40f3bc91f74550c4b49205713f391d436e37360e92a9740c1a1e"),
    "core": ("0208-seed-worksheet.py", "4907db44f0ef53cb657cd563a6fa27df8a138442807c703a66c1343bde4788ba"),
    "oracle": ("0208-seed-oracle.py", "cf4041c69e5204f79ab6786be5e393c0dbc0977317e693587eb1a85e8265e475"),
    "reader": ("0210-retained-readback.py", "a6e1b9a32f0c46c9e03974c1367a8b04d2849eca86d807907a3bcefa1f0e8920"),
    "orbit": ("0213-phase-orbit.py", "ba78ca47097703cb27ed7dca8d844b9be34c61b1fee9a5668fae97db039979c3"),
    "screen": ("0213-phase-screen.py", "39d59baecb394f759ef6a775ce6cca548e4828dbfef94207b47c9e048d1d0f2b"),
    "archive": ("0220-phase-archive.py", "43c4c3b7fe1f82324a4833ea74a22aaed9922e8c0f9ea67fa0aa76161062dcf8"),
    "anchors": ("0220-phase-anchors.py", "7fadcb3fc9de4a43aa1ce80efd30d2e6499f76ee4918519cf8783d50bca2057e"),
    "points": ("0241-phase-points.py", None),
    "search": ("0241-bounded-search.py", None),
    "runtime": ("0241-runtime.py", None),
    "trace": ("0241-trace-audit.py", None),
    "invocation": (HERE.name, None),
}
FLAGS = dict(scope="artificial", synthetic=True, live_authorized=False,
             physical_launch_authorized=False, commands=None,
             physical_status="physical-join-not-established", spice_queries=0,
             kernel_accesses=0, force_evaluations=0, integrations=0,
             retained_attempts=0, r560_attempts=0, interval_cells=0, signed_bounds=0)


def need(value: object, reason: str) -> None:
    if not value:
        raise ValueError("bounded artificial study: " + reason)


def _load(name: str, raw: bytes, path: Path) -> ModuleType:
    module = ModuleType("_bounded_" + name)
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), vars(module))
    return module


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
        number = float(value)
        need(math.isfinite(number), "nonfinite JSON number")
        return number

    try:
        row = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite)
    except RecursionError as error:
        raise ValueError("JSON nesting limit") from error
    need(type(row) is dict, "JSON object required")
    return row


def _private() -> set[Path]:
    paths = {HERE.with_name(name) for name, _ in METHODS.values()}
    import sysconfig
    solver = Path(sysconfig.get_path("purelib")) / "scipy" / "optimize"
    paths.update(solver / name for name in ("_minimize.py", "_optimize.py"))
    tests = HERE.parents[3] / "tests"
    paths.add(tests / "bounded_witness_fixtures.py")
    return paths


def _sources(io: ModuleType, check: Callable[[], None], expected: Row | None = None) -> tuple[dict[str, ModuleType], Row]:
    methods, pins = {}, {}
    for key, (name, pin) in METHODS.items():
        check()
        raw = io._read(HERE.with_name(name), CAP)
        digest = io._sha(raw)
        need(pin is None or digest == pin, "immutable method pin: " + key)
        need(expected is None or expected.get(key) == digest, "qualified source drift: " + key)
        pins[key] = digest
        if key not in {"runtime", "invocation"}:
            methods[key] = _load(key, raw, HERE.with_name(name))
    fixture = HERE.parents[3] / "tests" / "bounded_witness_fixtures.py"
    pins["artificial_bootstrap"] = io._sha(io._read(fixture, CAP))
    return methods, pins


def _archive(config: Row, io: ModuleType, methods: dict[str, ModuleType],
             check: Callable[[], None]) -> Row:
    root = Path(config["source_dir"]).resolve()
    need(not root.is_relative_to(HERE.parents[3]), "repository data path forbidden")
    expected = config["source_pins"]
    need(type(expected) is dict and set(expected) == set(ARCHIVE_FILES), "four archive pins")
    records = {}
    for name in ARCHIVE_FILES:
        check()
        io._pin(expected[name])
        raw = io._read(root / name, CAP)
        need(io._sha(raw) == expected[name], "artificial archive pin: " + name)
        records[name] = _json(raw), io._sha(raw)
    return methods["archive"].bind(records, io, retained=False)


def _read_result(path: Path, io: ModuleType, check: Callable[[], None],
                 completion_pin: str | None = None) -> tuple[Row, int]:
    """Structural/hash readback only; no phase, conic or optimizer calls."""
    need(not path.is_symlink(), "symlink evidence")
    with os.scandir(path) as contents:
        names = {entry.name for _, entry in zip(range(len(FILES)+1), contents)}
    need(names == set(FILES), "exact evidence inventory")
    entries, size = [], 0
    for name in FILES:
        check()
        raw = io._read(path / name, CAP - size)
        size += len(raw)
        row = _json(raw)
        need(io._wire(row) == raw, "noncanonical evidence")
        entries.append((row, io._sha(raw)))
    (attempt, a), (report, r), (receipt, s), (completion, c) = entries
    need(completion_pin is None or c == completion_pin, "external completion pin")
    need(receipt["attempt_sha256"] == report["attempt_sha256"] == a
         and receipt["report_sha256"] == r and completion["receipt_sha256"] == s,
         "evidence chain")
    need(all(row["run_id"] == attempt["run_id"] for row in (report, receipt, completion)), "run identity")
    need(all(type(row.get(key)) is type(value) and row[key] == value
             for row in (attempt, report) for key, value in FLAGS.items()), "scope or prohibited work")
    need(attempt["schema"] == "ariadna-bounded-preparation-v1"
         and attempt["mode"] in {"profile-producer", "profile-audit", "artificial", "audit"}, "evidence schema/mode")
    need(report["status"] in {"verified-analytical-witness", "inconclusive/invalid", "artificial-invalid",
                              "artificial-audit-verified", "artificial-profile-verified"}, "known result status")
    if attempt["mode"] == "artificial" and report["status"] != "artificial-invalid":
        need(report["status"] == report["result"]["status"], "outer/numerical disposition")
    wall = attempt["wall_ns"]
    need(type(wall) is int and 0 < wall <= WALL_NS
         and type(receipt["elapsed_ns"]) is int and 0 <= receipt["elapsed_ns"] < wall
         and type(completion["elapsed_ns"]) is int
         and receipt["elapsed_ns"] <= completion["elapsed_ns"] < wall, "saved deadline")
    need(type(completion["exit_code"]) is int and completion["exit_code"] in (0, 2)
         and receipt["status"] == report["status"], "result disposition")
    need(all(report[key] == attempt[key] for key in attempt), "attempt/report identity")
    successful = report["status"] in {"verified-analytical-witness", "artificial-audit-verified", "artificial-profile-verified"}
    need(completion["exit_code"] == (0 if successful else 2), "exit/status mapping")
    return report, size


def _audit(source: Row, producer: Row, methods: dict[str, ModuleType], check: Callable[[], None]) -> Row:
    """Independently check recorded literal points, not the optimizer trajectory."""
    result = producer["result"]
    structural = methods["trace"].verify(result)
    need(structural["verified"] is True, "partial/invalid method transcript")
    rows = result["phases"]
    need(type(rows) is list and 3 <= len(rows) <= 129, "phase transcript count")
    counters = dict(anchors=0, objective=dict(positive=0, negative=0), finals=0,
                    phases=0, root_slots=0, pair_slots=0, blocked_attempts=0)
    witness = None
    verified = []
    for index, row in enumerate(rows):
        check()
        need(witness is None, "phase after witness")
        counters["phases"] += 1
        counters["root_slots"] += 2
        counters["pair_slots"] += 2
        stage, sign = row["stage"], row["sign"]
        if stage == "anchor":
            need(index < 3 and sign is None, "anchor order")
            counters["anchors"] += 1
            degree = (150, 151, 152)[index]
            need(row["phase_word"] == float(degree).hex() and row["compared"] is True, "anchor binding")
            methods["anchors"].verify_anchor(source["anchors"][index], row["point"], degree, methods["reader"])
        else:
            need(index >= 3 and sign in ("positive", "negative") and stage in {"objective", "final"},
                 "phase stage/sign")
            if stage == "objective":
                counters["objective"][sign] += 1
                need(counters["objective"][sign] <= 62, "callback cap")
            else:
                counters["finals"] += 1
                need(counters["finals"] <= 2, "final cap")
                previous = [old for old in rows[:index] if old["stage"] == "objective" and old["sign"] == sign]
                need(any(old["phase_word"] == row["phase_word"] for old in previous), "new final phase")
                saved = result["searches"][sign]["result"]
                need(saved is not None and saved["x_word"] == row["phase_word"], "final result binding")
        point = row["point"]
        need(point is not None and row["error"] is None, "partial phase cannot be numerically verified")
        need(row["phase_word"] == point["phase_word"] and row["phase_ratio"] == point["phase_ratio"],
             "exact phase transcript binding")
        verdict = methods["points"].audit_point(source["reference"], point, methods)
        need(verdict["eligible"] == point["eligible"] and verdict["unresolved"] == point["unresolved"],
             "independent point disposition")
        verified.append(verdict)
        if stage != "anchor" and verdict["eligible"]:
            witness = dict(phase_index=index, phase_word=row["phase_word"], phase_ratio=row["phase_ratio"],
                           sign=verdict["eligible"][0], eligible=verdict["eligible"])
        if stage == "objective" and row["objective_word"] is not None:
            pairs = [pair for pair in point["pairs"] if pair["roots"] == ["positive", sign]]
            need(len(pairs) == 1 and type(pairs[0]["total_delta_v_m_s"]) is float
                 and pairs[0]["total_delta_v_m_s"].hex() == row["objective_word"], "objective cost binding")
    blocked = result.get("blocked_attempt")
    if blocked is not None:
        counters["blocked_attempts"] = 1
    need(result["counters"] == counters == structural["counters"] and counters["anchors"] == 3, "work accounting")
    need(result["witness"] == witness, "witness transcript binding")
    if witness:
        need(result["status"] == "verified-analytical-witness" and result["disposition"] == "witness", "witness status")
    else:
        need(result["status"] == "inconclusive/invalid", "false refusal or witness")
    return dict(status="artificial-audit-verified", analytical_status=result["status"],
                witness=witness, points=verified, counters=counters, optimizer_calls=0)


def _worker(mode: str, config_path: Path | None, config_pin: str | None, output: Path,
            run_id: str, started: int, wall: int) -> int:
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "isolated worker required")
    need(type(wall) is int and 0 < wall <= WALL_NS, "worker deadline")

    def check() -> None:
        elapsed = monotonic_ns() - started
        need(0 <= elapsed < wall, "shared deadline")

    check()
    need(mode in {"profile-producer", "profile-audit", "artificial", "audit"}, "worker mode")
    need((config_path is None) == mode.startswith("profile-"), "worker mode arguments")
    need(not output.exists() and not output.is_symlink()
         and not output.resolve().is_relative_to(HERE.parents[3]), "external exclusive worker output")
    if config_path is not None:
        need(not config_path.is_symlink() and not config_path.resolve().is_relative_to(HERE.parents[3]),
             "external worker configuration")
    runtime_path = HERE.with_name("0241-runtime.py")
    runtime = _load("runtime_bootstrap", runtime_path.read_bytes(), runtime_path)
    io_path = HERE.with_name(METHODS["io"][0])
    raw = io_path.read_bytes()
    need(sha256(raw).hexdigest() == METHODS["io"][1], "I/O bootstrap pin")
    io = _load("io_bootstrap", raw, io_path)
    config: Row = {}
    initial_bytes = HERE.stat().st_size + runtime_path.stat().st_size + len(raw)
    if config_path is not None:
        raw = io._read(config_path, CAP - initial_bytes)
        initial_bytes += len(raw)
        io._pin(config_pin)
        need(io._sha(raw) == config_pin, "configuration pin")
        config = _json(raw)
        need(config["scope"] == "artificial" and config["mode"] == mode, "artificial mode required")
    inputs = {config_path} if config_path else set()
    if config:
        source = Path(config["source_dir"]).resolve()
        need(not source.is_relative_to(HERE.parents[3]), "repository data path forbidden")
        inputs.update(source / name for name in ARCHIVE_FILES)
        if mode == "audit":
            producer = Path(config["producer"])
            need(not producer.is_symlink() and not producer.resolve().is_relative_to(HERE.parents[3])
                 and producer.resolve() != output.resolve(), "external producer evidence required")
            inputs.update(producer / name for name in FILES)
    scientific = mode in {"profile-producer", "artificial"}
    profile = config.get("runtime")
    guard = runtime.Guard(_private(), inputs, output, check, profile, scientific=scientific)
    guard.source_bytes = initial_bytes
    need(initial_bytes <= CAP, "bootstrap/config byte cap")
    sys.addaudithook(guard.hook)
    prior_bytes = (sum((Path(config["producer"]) / name).stat().st_size for name in FILES)
                   if mode == "audit" else 0)
    output_budget = CAP - prior_bytes
    need(output_budget >= 4 * 4096, "combined evidence reserve")
    output.mkdir(mode=0o700)
    io._sync(output.parent)
    attempt = FLAGS | dict(schema="ariadna-bounded-preparation-v1", run_id=run_id, mode=mode,
                           wall_ns=wall, config_sha256=config_pin)
    a = io._put(output / FILES[0], attempt, 4096)
    result: Row = {}
    status = "artificial-invalid"
    try:
        methods, sources = _sources(io, check, config.get("source_sha256"))
        if config:
            runtime.authenticate(guard)
        if config:
            need(config["source_sha256"] == sources, "qualified private source identity")
        if scientific:
            minimize, identity = runtime.prepare(guard)
        else:
            minimize = None
            identity = dict(python=list(sys.version_info[:3]), prefix=str(Path(sys.base_prefix).resolve()),
                            numpy=None, scipy=None)
        # Authenticate selected wrapper/solver source as charged scientific code.
        solver_sources = {}
        if scientific:
            import sysconfig
            for name in ("_minimize.py", "_optimize.py"):
                path = Path(sysconfig.get_path("purelib")) / "scipy" / "optimize" / name
                guard.private.add(str(path.resolve()))
                solver_sources[name] = io._sha(io._read(path, CAP))
        manifest = runtime.fingerprint(guard, identity)
        if mode.startswith("profile-"):
            result = dict(runtime=manifest, source_sha256=sources, solver_sources=solver_sources)
            status = "artificial-profile-verified"
        else:
            need(config["solver_sources"] == solver_sources, "selected scalar-solver sources")
            source = _archive(config, io, methods, check)
            if mode == "artificial":
                def point(phase: float) -> Row:
                    check()
                    return methods["points"].point(source["reference"], phase, methods)

                def anchor(row: Row, degree: int) -> None:
                    methods["anchors"].verify_anchor(source["anchors"][degree-150], row, degree, methods["reader"])

                driver = config.get("driver", "bounded")
                need(driver in {"bounded", "artificial-full-volume"}, "artificial qualification driver")
                if driver == "artificial-full-volume":
                    def stress(objective: Callable[[float], float], **options: Any) -> Row:
                        # Test-only maximum workload, explicitly not a Brent result.
                        cost = 0.
                        for _ in range(62):
                            cost = objective(151.)
                        return dict(x=151., fun=cost, success=False, nfev=62, nit=62, status=1,
                                    message="Artificial full-volume driver; not a Brent result")
                    minimize = stress
                result = methods["search"].search(point, anchor, minimize=minimize, check=check)
                result["qualification_driver"] = driver
                status = result["status"]
            else:
                producer, producer_bytes = _read_result(Path(config["producer"]), io, check, config["completion_sha256"])
                need(producer["mode"] == "artificial" and producer["source_pins"] == config["source_pins"]
                     and producer["source_sha256"] == sources
                     and producer["runtime"] == config["producer_runtime"]
                     and producer["solver_sources"] == config["producer_solver_sources"],
                     "producer/input/source/runtime binding")
                need(producer_bytes < CAP, "producer evidence input cap")
                result = _audit(source, producer, methods, check)
                status = result["status"]
        check()
        report = attempt | dict(attempt_sha256=a, status=status, result=result,
                                source_sha256=sources, source_pins=config.get("source_pins"),
                                runtime=manifest, solver_sources=solver_sources,
                                source_bytes=guard.source_bytes, runtime_read_bytes=guard.runtime_read_bytes)
    except (OSError, ValueError, ArithmeticError, KeyError, TypeError, AttributeError, ImportError) as error:
        report = attempt | dict(attempt_sha256=a, status="artificial-invalid", result=result,
                                error=f"{type(error).__name__}: {error}",
                                source_bytes=guard.source_bytes, runtime_read_bytes=guard.runtime_read_bytes)
        status = report["status"]
    check()
    r = io._put(output / FILES[1], report, output_budget - 3 * 4096)
    receipt = dict(run_id=run_id, attempt_sha256=a, report_sha256=r, status=status,
                   elapsed_ns=monotonic_ns() - started)
    s = io._put(output / FILES[2], receipt, 4096)
    code = 0 if status in {"verified-analytical-witness", "artificial-audit-verified", "artificial-profile-verified"} else 2
    io._put(output / FILES[3], dict(run_id=run_id, receipt_sha256=s, exit_code=code,
                                   elapsed_ns=monotonic_ns() - started), 4096)
    _read_result(output, io, check)
    check()
    if config.get("producer"):
        total = sum((Path(config["producer"]) / name).stat().st_size for name in FILES)
        total += sum((output / name).stat().st_size for name in FILES)
        need(total <= CAP, "combined new evidence byte cap")
    return code


def launch(mode: str, output: Path, *, config: Path | None = None, config_pin: str | None = None,
           wall_ns: int = WALL_NS) -> int:
    """Dispatch only artificial/profile/audit modes under one external deadline."""
    need(mode in {"profile-producer", "profile-audit", "artificial", "audit"}, "unsupported mode")
    need((config is None) == mode.startswith("profile-"), "mode arguments")
    need(type(wall_ns) is int and 0 < wall_ns <= WALL_NS, "launch deadline")
    output = output.absolute()
    need(not output.exists() and not output.is_symlink()
         and not output.resolve().is_relative_to(HERE.parents[3]), "exclusive external artificial output required")
    if config is not None:
        need(not config.is_symlink() and not config.resolve().is_relative_to(HERE.parents[3]), "external artificial config")
    started, run_id = monotonic_ns(), uuid4().hex
    command = [sys.executable, "-I", "-S", "-B", str(HERE), "worker", mode,
               str(config.absolute()) if config else "-", config_pin or "-", str(output),
               run_id, str(started), str(wall_ns)]
    try:
        done = subprocess.run(command, capture_output=True, timeout=wall_ns / 1e9, check=False)
        if monotonic_ns() - started >= wall_ns or done.returncode not in (0, 2):
            completion = output / "completion.json"
            if completion.exists() and _json(completion.read_bytes()).get("run_id") == run_id:
                completion.unlink()
            return 3
        return done.returncode
    except subprocess.TimeoutExpired:
        completion = output / "completion.json"
        if completion.exists() and _json(completion.read_bytes()).get("run_id") == run_id:
            completion.unlink()
        return 3


def main(args: list[str]) -> int:
    if len(args) == 8 and args[0] == "worker":
        _, mode, config, pin, output, run_id, started, wall = args
        return _worker(mode, None if config == "-" else Path(config), None if pin == "-" else pin,
                       Path(output), run_id, int(started), int(wall))
    if len(args) == 2 and args[0] in {"profile-producer", "profile-audit"}:
        return launch(args[0], Path(args[1]))
    if len(args) == 4 and args[0] in {"artificial", "audit"}:
        mode, config, pin, output = args
        return launch(mode, Path(output), config=Path(config), config_pin=pin)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, ArithmeticError, KeyError, TypeError):
        raise SystemExit(3)
