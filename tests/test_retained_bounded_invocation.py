"""Qualify the new dispatcher with fabricated archives; never consume P6."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from runpy import run_path
import subprocess
import sys
import sysconfig
from time import monotonic_ns
from types import SimpleNamespace
from typing import Any

import pytest

from retained_bounded_fixtures import FIXED_INPUT_BYTES, source_archive


type Row = dict[str, Any]
ART = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
SCRIPT = ART / "0245-retained-invocation.py"
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
CAP = 4 * 1024**2
WALL_NS = 30_000_000_000


def pin(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def read(path: Path, name: str = "report.json") -> Row:
    return json.loads((path / name).read_bytes())


def write_config(path: Path, row: Row) -> tuple[Path, str]:
    path.write_text(json.dumps(row, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path, pin(path)


@pytest.fixture(scope="module")
def harness(tmp_path_factory: pytest.TempPathFactory) -> Row:
    root = tmp_path_factory.mktemp("retained-dispatch-artificial")
    old = run_path(str(ART / "0241-bounded-invocation.py"))
    profiles = {}
    for mode in ("producer", "audit"):
        output = root / ("profile-" + mode)
        assert old["launch"]("profile-" + mode, output) == 0, read(output)
        # These platform-local fabricated profiles never replace retained0242 tables.
        profiles[mode] = read(output)["result"]
        fixed = json.loads((ART / f"0242-{mode}-runtime.json").read_bytes())["runtime"]
        observed = profiles[mode]["runtime"]
        if (sys.platform == "darwin" and observed["identity"]["prefix"] == fixed["identity"]["prefix"]
                and observed["host"] == fixed["host"]):
            assert observed == fixed, "new profile cannot migrate retained runtime"
    return dict(root=root, runner=run_path(str(SCRIPT)), profiles=profiles)


def binding(harness: Row, root: Path, case: str, *, full_size: bool = False,
            driver: str = "bounded") -> Row:
    source, source_pins = source_archive(root / "source", case, full_size=full_size)
    return dict(schema="ariadna-p3-retained-binding-v1", scope="artificial",
                source_dir=str(source), source_pins=source_pins,
                source_sha256=harness["runner"]["source_map"](), driver=driver,
                producer_profile={key: deepcopy(harness["profiles"]["producer"][key])
                                  for key in ("runtime", "solver_sources")},
                audit_profile={key: deepcopy(harness["profiles"]["audit"][key])
                               for key in ("runtime", "solver_sources")})


def launch(harness: Row, root: Path, row: Row, *, name: str = "run",
           wall_ns: int = WALL_NS) -> tuple[int, Path]:
    config, digest = write_config(root / (name + "-binding.json"), row)
    output = root / name
    code = harness["runner"]["launch"](config, digest, output, wall_ns=wall_ns)
    return code, output


@pytest.mark.parametrize(("case", "driver", "expected"), [
    ("witness", "bounded", "verified-analytical-witness"),
    ("refusal", "bounded", "inconclusive/invalid"),
    ("full-volume", "artificial-full-volume", "inconclusive/invalid"),
])
def test_cold_parent_producer_and_completion_bound_independent_audit(
    harness: Row, tmp_path: Path, case: str, driver: str, expected: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    full = driver == "artificial-full-volume"
    row = binding(harness, tmp_path, case, full_size=full, driver=driver)
    source_bytes = sum(path.stat().st_size for path in Path(row["source_dir"]).iterdir())
    before = {name: pin(Path(row["source_dir"]) / name) for name in row["source_pins"]}
    audit_raw = (Path(row["source_dir"]) / "audit.json").read_bytes()
    assert audit_raw != harness["runner"]["_wire"](json.loads(audit_raw))
    assert audit_raw == (json.dumps(json.loads(audit_raw), sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    started = monotonic_ns()
    code, output = launch(harness, tmp_path, row)
    terminal = json.loads(capsys.readouterr().out.strip())
    assert terminal["schema"] == "ariadna-p3-retained-terminal-v1"
    assert terminal["exit_code"] == code
    assert terminal["parent_source_bytes"] <= CAP
    assert terminal["parent_elapsed_ns"] < 2 * WALL_NS
    (tmp_path / "observed-terminal.json").write_text(json.dumps(terminal, sort_keys=True) + "\n")
    assert code == (0 if expected == "verified-analytical-witness" else 2)
    assert monotonic_ns() - started < 2 * WALL_NS
    assert set(path.name for path in output.iterdir()) == {"invocation.json", "producer", "audit"}
    assert (output / "invocation.json").stat().st_size <= 4096
    producer, audit = output / "producer", output / "audit"
    p, a = read(producer), read(audit)
    assert p["status"] == expected, p.get("error", p)
    assert a["result"]["analytical_status"] == expected, a.get("error", a)
    assert a["result"]["optimizer_calls"] == 0
    assert a["runtime"]["identity"]["numpy"] is None
    assert a["runtime"]["identity"]["scipy"] is None
    for report, mode in ((p, "producer"), (a, "audit")):
        assert report["runtime"] == row[mode + "_profile"]["runtime"]
        assert report["scope"] == "artificial" and report["synthetic"] is True
        assert source_bytes <= report["source_bytes"] <= CAP
        assert report["runtime_read_bytes"] <= report["runtime"]["runtime_read_cap_bytes"]
        for key in ("spice_queries", "kernel_accesses", "force_evaluations", "integrations",
                    "retained_attempts", "r560_attempts", "interval_cells", "signed_bounds"):
            assert type(report[key]) is int and report[key] == 0
    for directory in (producer, audit):
        assert set(path.name for path in directory.iterdir()) == set(FILES)
        completion = read(directory, "completion.json")
        receipt = read(directory, "receipt.json")
        attempt = read(directory, "attempt.json")
        assert 0 <= receipt["elapsed_ns"] <= completion["elapsed_ns"] < attempt["wall_ns"] <= WALL_NS
    assert sum(path.stat().st_size for path in producer.iterdir()) <= CAP - 4096 - 64 * 1024
    assert sum(path.stat().st_size for path in audit.iterdir()) <= 64 * 1024
    assert sum(path.stat().st_size for path in output.rglob("*.json")) <= CAP
    assert before == {name: pin(Path(row["source_dir"]) / name) for name in row["source_pins"]}
    if full:
        assert source_bytes >= FIXED_INPUT_BYTES
        assert len(read(Path(row["source_dir"]))["rows"]) == 360
        counts = p["result"]["counters"]
        assert counts["phases"] == 129 and counts["root_slots"] == counts["pair_slots"] == 258
        assert counts["objective"] == {"positive": 62, "negative": 62} and counts["finals"] == 2
        assert a["result"]["counters"] == counts


@pytest.mark.parametrize("fault", ["source-hash", "archive-hash", "runtime-hash", "solver-hash", "scope", "role-encoding"])
def test_identity_fault_consumes_output_without_numerical_audit(
    harness: Row, tmp_path: Path, fault: str,
) -> None:
    row = binding(harness, tmp_path, "refusal")
    if fault == "source-hash":
        row["source_sha256"]["points"] = "0" * 64
    elif fault == "archive-hash":
        row["source_pins"]["report.json"] = "0" * 64
    elif fault == "runtime-hash":
        files = row["producer_profile"]["runtime"]["files"]
        files[next(iter(files))]["sha256"] = "0" * 64
    elif fault == "solver-hash":
        row["producer_profile"]["solver_sources"]["_minimize.py"] = "0" * 64
    elif fault == "role-encoding":
        path = Path(row["source_dir"]) / "audit.json"
        write_config(path, json.loads(path.read_bytes()))
        row["source_pins"]["audit.json"] = pin(path)
    else:
        row["scope"] = "retained"
    code, output = launch(harness, tmp_path, row)
    assert code in (2, 3)
    assert not (output / "audit").exists()
    if output.exists():
        preserved = {str(p.relative_to(output)): pin(p) for p in output.rglob("*") if p.is_file()}
        config, digest = write_config(tmp_path / "retry-binding.json", row)
        with pytest.raises((ValueError, FileExistsError), match="exclusive|exist|consum"):
            harness["runner"]["launch"](config, digest, output)
        assert preserved == {str(p.relative_to(output)): pin(p) for p in output.rglob("*") if p.is_file()}


def test_artificial_source_directory_cannot_point_into_repository(harness: Row, tmp_path: Path) -> None:
    row = binding(harness, tmp_path, "refusal")
    row["source_dir"] = str(ART)
    code, output = launch(harness, tmp_path, row)
    assert code in (2, 3) and not (output / "audit").exists()


def test_empty_or_extra_cli_arguments_do_not_dispatch(harness: Row, monkeypatch: pytest.MonkeyPatch) -> None:
    main = harness["runner"]["main"]
    calls = []
    monkeypatch.setitem(main.__globals__, "launch", lambda *args, **kwargs: calls.append((args, kwargs)) or 0)
    for args in ([], ["artificial"], ["artificial", "a", "b"], ["retained", "override"],
                 ["audit", "a", "b", "c"], ["profile-producer", "a"], ["worker"]):
        assert main(args) == 2
    assert not calls


@pytest.mark.parametrize("outcome", ["partial", "timeout", "late"])
def test_failed_envelope_preserves_bytes_and_never_launches_auditor(
    harness: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str,
) -> None:
    """Orchestration-only fake: no point, optimizer or numerical audit is executed."""
    row = binding(harness, tmp_path, "refusal")
    config, digest = write_config(tmp_path / "binding.json", row)
    output = tmp_path / "run"
    namespace = harness["runner"]["launch"].__globals__
    calls: list[list[str]] = []
    elapsed = [10_000]
    preserved: dict[str, bytes] = {}

    def run(command: list[str], **options: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        assert command[1:4] == ["-I", "-S", "-B"]
        assert command[5:7] == ["worker", "producer"]
        assert len(command) == 14 and command[13] == "-"
        destination = Path(command[9]) / "producer"
        destination.mkdir()
        preserved.update({"report.json": b'{"partial":true}\n',
                          "completion.json": b'{"partial-completion":true}\n'})
        for name, raw in preserved.items():
            (destination / name).write_bytes(raw)
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(command, options["timeout"])
        if outcome == "late":
            elapsed[0] += WALL_NS
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

    monkeypatch.setitem(namespace, "monotonic_ns", lambda: elapsed[0])
    monkeypatch.setattr(namespace["subprocess"], "run", run)
    assert harness["runner"]["launch"](config, digest, output) == 3
    assert len(calls) == 1 and not (output / "audit").exists()
    assert (output / "invocation.json").is_file()
    assert preserved == {name: (output / "producer" / name).read_bytes() for name in preserved}
    with pytest.raises((ValueError, FileExistsError), match="exclusive|exist|consum"):
        harness["runner"]["launch"](config, digest, output)
    assert len(calls) == 1


def test_parent_clock_precedes_reservation_and_configuration_reads(
    harness: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inspect only an intentionally incomplete orchestration envelope."""
    row = binding(harness, tmp_path, "refusal")
    config, digest = write_config(tmp_path / "binding.json", row)
    output = tmp_path / "run"
    namespace = harness["runner"]["launch"].__globals__
    events: list[str] = []
    old_mkdir, old_read = Path.mkdir, namespace["_raw_read"]

    def clock() -> int:
        events.append("clock")
        return 42_000

    def mkdir(path: Path, *args: Any, **kwargs: Any) -> None:
        if path == output:
            events.append("reserve")
        old_mkdir(path, *args, **kwargs)

    def opened(path: Path, cap: int) -> bytes:
        if path == config:
            events.append("config-read")
        return old_read(path, cap)

    def run(command: list[str], **options: Any) -> subprocess.CompletedProcess[bytes]:
        events.append("dispatch")
        assert int(command[11]) == 42_000
        assert 0 < options["timeout"] <= WALL_NS / 1e9
        return subprocess.CompletedProcess(command, 1, stdout=b"", stderr=b"orchestration-only refusal")

    monkeypatch.setitem(namespace, "monotonic_ns", clock)
    monkeypatch.setattr(Path, "mkdir", mkdir)
    monkeypatch.setitem(namespace, "_raw_read", opened)
    monkeypatch.setattr(namespace["subprocess"], "run", run)
    assert harness["runner"]["launch"](config, digest, output) == 3
    assert events.index("clock") < events.index("reserve") < events.index("dispatch")
    assert events.index("clock") < events.index("config-read")


@pytest.mark.parametrize("wall", [True, 0, -1, WALL_NS + 1])
def test_invalid_wall_budget_never_dispatches(
    harness: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wall: int,
) -> None:
    namespace = harness["runner"]["launch"].__globals__
    calls = []
    monkeypatch.setattr(namespace["subprocess"], "run", lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError, match="deadline|wall|budget"):
        harness["runner"]["launch"](tmp_path / "missing.json", "0" * 64, tmp_path / "out", wall_ns=wall)
    assert not calls and not (tmp_path / "out").exists()


@pytest.mark.parametrize("role", ["source", "configuration", "producer-evidence"])
def test_per_reader_cap_charges_each_reread(
    tmp_path: Path, role: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = run_path(str(ART / "0241-runtime.py"))
    preloaded = Path(sysconfig.get_path("purelib")) / "numpy" / "__init__.py"
    monkeypatch.setitem(sys.modules, "_ariadna_prior_numpy", SimpleNamespace(__file__=str(preloaded)))
    source = tmp_path / (role + ".json")
    source.write_bytes(b"x" * 1024)
    private = {source} if role == "source" else set()
    inputs = set() if private else {source}
    # Shared reader accounting allows packages already loaded by the surrounding test process.
    guard = runtime["Guard"](private, inputs, tmp_path / "out", lambda: None, None, scientific=True)
    assert str(preloaded.resolve()) in guard.runtime_files
    guard.source_bytes = CAP - 1024
    guard.hook("open", (str(source), "rb", 0))
    assert guard.source_bytes == CAP
    with pytest.raises(ValueError, match="input/private-source byte cap"):
        guard.hook("open", (str(source), "rb", 0))


@pytest.mark.parametrize("raw", [b'{"x":1e999}', b'{"x":NaN}', b'{"x":1,"x":2}'])
def test_new_dispatcher_keeps_strict_finite_json(harness: Row, raw: bytes) -> None:
    with pytest.raises(ValueError):
        harness["runner"]["_json"](raw)


def test_invalid_internal_worker_reports_bounded_error_without_work(tmp_path: Path) -> None:
    done = subprocess.run([sys.executable, "-I", "-S", "-B", str(SCRIPT), "worker", "producer",
                           str(tmp_path / "missing.json"), "0" * 64, str(tmp_path / "out"),
                           "a" * 32, "1", "0", "-"],
                          capture_output=True, check=False, timeout=5)
    assert done.returncode in (2, 3) and len(done.stderr) <= 1025
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("field,bad", [
    ("original", "0"), ("audit_view", "0E-569"),
    ("phase_index", True), ("velocity_component_index", 1),
])
def test_in_memory_historical_zero_view_gate_rejects_metadata_tampering(field: str, bad: Any) -> None:
    """Fabricated metadata plus fake digest exercise a gate, not real readiness."""
    from retained_bounded_fixtures import retained_metadata_gate

    records, fake_io, archive = retained_metadata_gate()
    assert archive.bind(records, fake_io, retained=True)["scope"] == "retained"
    audit = records["audit.json"][0]
    assert audit["zero_encoding"] == {
        "phase_index": 0, "velocity_component_index": 0, "original": "0E-569", "audit_view": "0"}
    audit["zero_encoding"][field] = bad
    with pytest.raises(ValueError, match="exact-zero audit identity"):
        archive.bind(records, fake_io, retained=True)


@pytest.mark.parametrize("fault", ["missing-role", "extra-role", "raw-pin", "upstream-pin"])
def test_in_memory_archive_role_and_sealed_metadata_refusal(fault: str) -> None:
    """No scientific evaluation or real archive authentication occurs in this unit."""
    from retained_bounded_fixtures import retained_metadata_gate

    records, fake_io, archive = retained_metadata_gate()
    if fault == "missing-role":
        records.pop("audit.json")
    elif fault == "extra-role":
        records["extra.json"] = ({}, "f" * 64)
    elif fault == "raw-pin":
        records["report.json"] = (records["report.json"][0], "f" * 64)
    else:
        for name in ("attempt.json", "report.json", "receipt.json"):
            records[name][0]["source_pins"] = dict(archive.UPSTREAM_PINS, **{"attempt.json": "f" * 64})
    with pytest.raises(ValueError):
        archive.bind(records, fake_io, retained=True)


def finalizer_case(harness: Row, output: Path, *, source_bytes: int = 0,
                   padding: int = 0) -> tuple[Row, str, Row, Any, Any]:
    """An intentionally invalid, non-scientific audit envelope for byte tests."""
    from types import SimpleNamespace

    runner = harness["runner"]
    io = runner["_bootstrap"]()
    output.mkdir()
    attempt = runner["_flags"]("artificial") | dict(
        schema="ariadna-p3-retained-process-v1", mode="audit", run_id="a" * 32, wall_ns=WALL_NS)
    attempt_pin = io._put(output / "attempt.json", attempt, 4096)
    report = attempt | dict(attempt_sha256=attempt_pin, status="process-invalid",
                            result={"orchestration_only_padding": "x" * padding})
    return attempt, attempt_pin, report, io, SimpleNamespace(source_bytes=source_bytes)


def test_finalizer_exact_source_limit_then_one_byte_excess(
    harness: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    finish = harness["runner"]["_finalize"]
    monkeypatch.setitem(finish.__globals__, "monotonic_ns", lambda: 0)
    seed = tmp_path / "size"
    args = finalizer_case(harness, seed, source_bytes=CAP - 16384)
    assert finish(seed, *args, 0, lambda: None) == 2
    amount = sum((seed / name).stat().st_size for name in FILES)
    assert amount < 16384
    exact = tmp_path / "exact"
    args = finalizer_case(harness, exact, source_bytes=CAP - amount)
    assert finish(exact, *args, 0, lambda: None) == 2
    assert args[-1].source_bytes == CAP and read(exact)["source_bytes"] == CAP
    excess = tmp_path / "excess"
    args = finalizer_case(harness, excess, source_bytes=CAP - amount + 1)
    with pytest.raises(ValueError, match="finalization evidence/source byte cap"):
        finish(excess, *args, 0, lambda: None)
    assert set(path.name for path in excess.iterdir()) == {"attempt.json"}


def test_audit_output_allocation_refuses_oversized_report_before_publication(harness: Row, tmp_path: Path) -> None:
    output = tmp_path / "audit"
    args = finalizer_case(harness, output, padding=64 * 1024)
    with pytest.raises(ValueError, match="finalization evidence/source byte cap"):
        harness["runner"]["_finalize"](output, *args, monotonic_ns(), lambda: None)
    assert set(path.name for path in output.iterdir()) == {"attempt.json"}


@pytest.mark.parametrize("stage", ["completion-fsync", "final-readback"])
def test_lateness_during_finalization_refuses_but_keeps_written_bytes(
    harness: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str,
) -> None:
    finish = harness["runner"]["_finalize"]
    namespace = finish.__globals__
    output = tmp_path / "audit"
    args = finalizer_case(harness, output)
    io = args[-2]
    expired = [False]
    original_put = io._put
    original_readback = namespace["_read_result"]

    def check() -> None:
        if expired[0]:
            raise ValueError("injected finalization deadline")

    def put(path: Path, row: Row, cap: int) -> str:
        result = original_put(path, row, cap)
        if stage == "completion-fsync" and path.name == "completion.json":
            expired[0] = True
        return result

    def readback(*positional: Any, **keywords: Any) -> Any:
        result = original_readback(*positional, **keywords)
        if stage == "final-readback":
            expired[0] = True
        return result

    monkeypatch.setattr(io, "_put", put)
    monkeypatch.setitem(namespace, "_read_result", readback)
    with pytest.raises(ValueError, match="injected finalization deadline"):
        finish(output, *args, monotonic_ns(), check)
    assert set(path.name for path in output.iterdir()) == set(FILES)
    assert all((output / name).stat().st_size for name in FILES)


@pytest.mark.parametrize("fault", ["extra-file", "wrong-completion-pin", "noncanonical", "chain-hash",
                                   "boolean-exit", "late", "readback-count", "source-cap"])
def test_new_structural_reader_rejects_tampered_process_chain(
    harness: Row, tmp_path: Path, fault: str,
) -> None:
    runner = harness["runner"]
    output = tmp_path / "audit"
    args = finalizer_case(harness, output)
    assert runner["_finalize"](output, *args, monotonic_ns(), lambda: None) == 2
    if fault == "extra-file":
        (output / "extra.json").write_bytes(b"{}\n")
    elif fault == "noncanonical":
        p = output / "report.json"
        p.write_bytes(p.read_bytes() + b" ")
    elif fault == "chain-hash":
        completion = read(output, "completion.json")
        completion["receipt_sha256"] = "0" * 64
        write_config(output / "completion.json", completion)
    elif fault == "boolean-exit":
        completion = read(output, "completion.json")
        completion["exit_code"] = True
        write_config(output / "completion.json", completion)
    elif fault == "late":
        completion = read(output, "completion.json")
        completion["elapsed_ns"] = WALL_NS
        write_config(output / "completion.json", completion)
    elif fault in {"readback-count", "source-cap"}:
        report, receipt, completion = (read(output, name) for name in FILES[1:])
        report["readback_bytes" if fault == "readback-count" else "source_bytes"] = CAP + 1
        write_config(output / "report.json", report)
        receipt["report_sha256"] = pin(output / "report.json")
        write_config(output / "receipt.json", receipt)
        completion["receipt_sha256"] = pin(output / "receipt.json")
        write_config(output / "completion.json", completion)
    expected_pin = "0" * 64 if fault == "wrong-completion-pin" else None
    with pytest.raises(ValueError):
        runner["_read_result"](output, args[-2], lambda: None, expected_pin)


def test_structural_readback_uses_the_supplied_counted_reader(harness: Row, tmp_path: Path) -> None:
    runner = harness["runner"]
    output = tmp_path / "audit"
    args = finalizer_case(harness, output)
    assert runner["_finalize"](output, *args, monotonic_ns(), lambda: None) == 2
    opened: list[str] = []
    total = [0]

    def reader(path: Path, cap: int) -> bytes:
        opened.append(path.name)
        raw = path.read_bytes()
        assert len(raw) <= cap
        total[0] += len(raw)
        return raw

    report, amount = runner["_read_result"](output, args[-2], lambda: None, read=reader)
    assert opened == list(FILES) and total[0] == amount == report["readback_bytes"]


def test_valid_cli_forms_route_without_opening_retained_inputs(
    harness: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = harness["runner"]["main"]
    calls = []

    def launched(*args: Any, **kwargs: Any) -> int:
        calls.append((args, kwargs))
        return 0

    monkeypatch.setitem(main.__globals__, "launch", launched)
    assert main(["retained"]) == 0
    assert calls == [((harness["runner"]["BINDING"], None, harness["runner"]["OUTPUT"]), {"retained": True})]
    assert main(["artificial", str(tmp_path / "binding.json"), "f" * 64, str(tmp_path / "out")]) == 0
    assert calls[1] == ((tmp_path / "binding.json", "f" * 64, tmp_path / "out"), {})
    workers = []
    monkeypatch.setitem(main.__globals__, "_worker", lambda *args: workers.append(args) or 0)
    assert main(["worker", "audit", str(tmp_path / "binding.json"), "f" * 64,
                 str(tmp_path / "out"), "a" * 32, "10", str(WALL_NS), "b" * 64]) == 0
    assert workers == [("audit", tmp_path / "binding.json", "f" * 64, tmp_path / "out",
                        "a" * 32, 10, WALL_NS, "b" * 64)]


def test_retained_metadata_pins_keep_original_four_inputs_and_exact_runtime_tables(harness: Row) -> None:
    """Read source/runtime metadata only, never any of the four scientific files."""
    runner = harness["runner"]
    assert set(runner["SAVED"]) == {"attempt.json", "report.json", "receipt.json", "audit.json"}
    assert [runner["SAVED"][name][1] for name in ("attempt.json", "report.json", "receipt.json", "audit.json")] == [
        1508, 1_059_325, 1727, 3398]
    assert sum(row[1] for row in runner["SAVED"].values()) == FIXED_INPUT_BYTES
    for mode in ("producer", "audit"):
        profile = json.loads((ART / f"0242-{mode}-runtime.json").read_bytes())
        assert sha256(runner["_wire"](profile["runtime"])).hexdigest() == runner["RUNTIME_PINS"][mode]
    assert runner["METHODS"]["points"][0] == "0244-phase-points.py"
    paths = []

    def source_reader(path: Path, cap: int) -> bytes:
        paths.append(path)
        assert cap == CAP
        return path.read_bytes()

    sources = runner["source_map"](source_reader)
    assert set(paths) == {ART / value[0] for value in runner["METHODS"].values()}
    assert set(sources) == set(runner["METHODS"])
    assert all("fixture" not in name and "bootstrap" not in name for name in sources)


def test_parent_reader_limits_each_read_before_one_byte_budget_excess(
    harness: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the new parent accountant without dispatching scientific work."""
    runner = harness["runner"]
    namespace = runner["launch"].__globals__
    strict_read = namespace["_raw_read"]
    initial = SCRIPT.stat().st_size + (ART / runner["METHODS"]["io"][0]).stat().st_size
    payload = tmp_path / "fabricated-source-padding"
    payload.write_bytes(b"x" * (CAP - initial - 1))
    config = tmp_path / "two-byte.json"
    config.write_bytes(b"{}")
    observed: list[tuple[Path, int]] = []
    calls = []

    def counted(path: Path, cap: int) -> bytes:
        observed.append((path, cap))
        return strict_read(path, cap)

    def sources(reader: Any) -> Row:
        assert len(reader(payload, CAP)) == CAP - initial - 1
        return {}

    monkeypatch.setitem(namespace, "_raw_read", counted)
    monkeypatch.setitem(namespace, "source_map", sources)
    monkeypatch.setattr(namespace["subprocess"], "run", lambda *args, **kw: calls.append(args))
    assert runner["launch"](config, pin(config), tmp_path / "out") == 3
    assert observed[-1] == (config, 1)
    assert not calls and not (tmp_path / "out" / "producer").exists()


@pytest.mark.parametrize("counter", [True, -1, 11])
def test_process_binding_rejects_runtime_counter_type_and_cap(harness: Row, counter: int) -> None:
    """Only envelope validation: no worker, runtime read or science is performed."""
    runner = harness["runner"]
    profile = dict(runtime={"runtime_read_cap_bytes": 10}, solver_sources={})
    config = dict(scope="artificial", source_sha256={"stub": "f" * 64},
                  source_pins={"stub": "e" * 64}, producer_profile=profile)
    invocation = dict(producer_run_id="a" * 32, launch_id="b" * 32, config_sha256="c" * 64)
    report = dict(mode="producer", run_id="a" * 32, launch_id="b" * 32,
                  started_ns=100, wall_ns=WALL_NS, config_sha256="c" * 64, scope="artificial",
                  source_sha256=config["source_sha256"], source_pins=config["source_pins"],
                  runtime=profile["runtime"], solver_sources={}, producer_completion_sha256=None,
                  status="inconclusive/invalid", runtime_read_bytes=10)
    runner["_binding"](report, config, invocation, "producer", 100, WALL_NS, None)
    report["runtime_read_bytes"] = counter
    with pytest.raises(ValueError, match="process runtime read-byte accounting"):
        runner["_binding"](report, config, invocation, "producer", 100, WALL_NS, None)
