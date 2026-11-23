"""Qualify actual isolated P3 commands exclusively with fabricated archives."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from runpy import run_path
import subprocess
import sys
from time import monotonic_ns
from typing import Any

import pytest

from bounded_witness_fixtures import load_methods, source_artificial_archive

Row = dict[str, Any]
ART = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
SCRIPT = ART / "0241-bounded-invocation.py"
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")


def read(path: Path, name: str = "report.json") -> Row:
    return json.loads((path / name).read_bytes())


def pin(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def config_file(path: Path, row: Row) -> tuple[Path, str]:
    path.write_text(json.dumps(row, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path, pin(path)


@pytest.fixture(scope="module")
def harness(tmp_path_factory: pytest.TempPathFactory) -> Row:
    root = tmp_path_factory.mktemp("bounded-artificial-wrapper")
    runner = run_path(str(SCRIPT))
    profiles = {}
    for mode in ("producer", "audit"):
        destination = root / ("profile-" + mode)
        code = runner["launch"]("profile-" + mode, destination)
        report = read(destination)
        assert code == 0, report.get("error", report)
        profiles[mode] = report["result"]
    return dict(root=root, runner=runner, profiles=profiles, methods=load_methods())


def study_config(harness: Row, root: Path, case: str, *, driver: str = "bounded") -> Row:
    source, pins = source_artificial_archive(root / "source", case, methods=harness["methods"])
    profile = harness["profiles"]["producer"]
    return dict(scope="artificial", mode="artificial", source_dir=str(source), source_pins=pins,
                runtime=profile["runtime"], source_sha256=profile["source_sha256"],
                solver_sources=profile["solver_sources"], driver=driver)


def launch_config(harness: Row, root: Path, row: Row, name: str = "study") -> tuple[int, Path]:
    config, digest = config_file(root / (name + "-config.json"), row)
    output = root / name
    code = harness["runner"]["launch"](row["mode"], output, config=config, config_pin=digest)
    return code, output


def audit_config(harness: Row, row: Row, producer: Path) -> Row:
    profile = harness["profiles"]["audit"]
    return row | dict(mode="audit", producer=str(producer), completion_sha256=pin(producer / "completion.json"),
                      runtime=profile["runtime"], solver_sources=profile["solver_sources"],
                      producer_runtime=row["runtime"], producer_solver_sources=row["solver_sources"])


@pytest.mark.parametrize(("case", "driver", "expected"), [
    ("witness", "bounded", "verified-analytical-witness"),
    ("refusal", "bounded", "inconclusive/invalid"),
    ("refusal", "artificial-full-volume", "inconclusive/invalid"),
])
def test_actual_producer_independent_audit_and_full_volume(
    harness: Row, tmp_path: Path, case: str, driver: str, expected: str,
) -> None:
    row = study_config(harness, tmp_path, "full-volume" if driver == "artificial-full-volume" else case, driver=driver)
    started = monotonic_ns()
    code, output = launch_config(harness, tmp_path, row)
    external = monotonic_ns() - started
    report = read(output)
    assert code == (0 if expected == "verified-analytical-witness" else 2), report.get("error", report)
    assert report["status"] == expected, report.get("error", report)
    assert report["result"]["qualification_driver"] == driver
    assert external < 30_000_000_000
    assert report["source_bytes"] <= 4 * 1024**2
    assert report["runtime_read_bytes"] <= report["runtime"]["runtime_read_cap_bytes"]
    for key in ("spice_queries", "kernel_accesses", "force_evaluations", "integrations",
                "retained_attempts", "r560_attempts", "interval_cells", "signed_bounds"):
        assert type(report[key]) is int and report[key] == 0
    if driver == "artificial-full-volume":
        counts = report["result"]["counters"]
        assert counts["phases"] == 129 and counts["root_slots"] == counts["pair_slots"] == 258
        assert counts["objective"] == {"positive": 62, "negative": 62} and counts["finals"] == 2
    before = {name: pin(output / name) for name in FILES}
    code, audit = launch_config(harness, tmp_path, audit_config(harness, row, output), "audit")
    checked = read(audit)
    assert code == 0 and checked["status"] == "artificial-audit-verified", checked.get("error", checked)
    assert checked["result"]["optimizer_calls"] == 0
    assert checked["runtime"]["identity"]["numpy"] is None
    assert checked["runtime"]["identity"]["scipy"] is None
    assert before == {name: pin(output / name) for name in FILES}
    assert sum((directory / name).stat().st_size for directory in (output, audit) for name in FILES) <= 4 * 1024**2
    assert set(path.name for path in output.iterdir()) == set(FILES)


@pytest.mark.parametrize("fault", ["source-hash", "archive-hash", "scope", "runtime-hash", "solver-hash", "native-file-bypass"])
def test_artificial_identity_failures_never_publish_a_witness(
    harness: Row, tmp_path: Path, fault: str, capsys: pytest.CaptureFixture[str],
) -> None:
    row = study_config(harness, tmp_path, "refusal")
    row = deepcopy(row)
    if fault == "source-hash":
        row["source_sha256"]["points"] = "0" * 64
    elif fault == "archive-hash":
        row["source_pins"]["report.json"] = "0" * 64
    elif fault == "scope":
        row["scope"] = "retained"
    elif fault == "runtime-hash":
        first = next(iter(row["runtime"]["files"]))
        row["runtime"]["files"][first]["sha256"] = "0" * 64
    elif fault == "solver-hash":
        row["solver_sources"]["_minimize.py"] = "0" * 64
    else:
        # A repository source path must never be read as a supposed native image.
        row["runtime"]["native_files"].append(str(SCRIPT.resolve()))
        row["runtime"]["files"][str(SCRIPT.resolve())] = dict(bytes=1, sha256="0" * 64)
    code, output = launch_config(harness, tmp_path, row)
    if fault in {"scope", "native-file-bypass"}:
        assert code == 3 and not (output / "report.json").exists()
        reason = "artificial mode required" if fault == "scope" else "unqualified native image root/type"
        assert reason in capsys.readouterr().err
    else:
        report = read(output)
        assert code == 2 and report["status"] == "artificial-invalid"
        reason = {"source-hash": "qualified source drift", "archive-hash": "artificial archive pin",
                  "runtime-hash": "runtime artifact drift", "solver-hash": "selected scalar-solver sources"}[fault]
        assert reason in report["error"]


def test_exact_parent_worker_argument_forms(harness: Row, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    main = harness["runner"]["main"]
    namespace = main.__globals__
    called = []
    monkeypatch.setitem(namespace, "_worker", lambda *args: called.append(args) or 0)
    assert main(["worker", "profile-audit", "-", "-", str(tmp_path / "out"), "a" * 32, "1", "30000000000"]) == 0
    assert len(called) == 1 and called[0][0] == "profile-audit"
    for args in (["worker"], ["worker"] * 7, ["worker"] * 9, ["retained", "x", "y", "z"]):
        assert main(args) == 2
    assert len(called) == 1


def test_config_cap_output_exclusivity_and_external_deadline(harness: Row, tmp_path: Path) -> None:
    row = study_config(harness, tmp_path, "refusal")
    source, digest = config_file(tmp_path / "config.json", row)
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(ValueError, match="exclusive"):
        harness["runner"]["launch"]("artificial", existing, config=source, config_pin=digest)
    assert harness["runner"]["launch"]("artificial", tmp_path / "late", config=source, config_pin=digest, wall_ns=1) == 3
    assert not (tmp_path / "late" / "completion.json").exists()
    oversized = tmp_path / "large.json"
    oversized.write_bytes(b" " * (4 * 1024**2 + 1))
    assert harness["runner"]["launch"]("artificial", tmp_path / "oversized", config=oversized, config_pin=pin(oversized)) == 3


def test_cli_rejects_retained_mode_without_dispatch(tmp_path: Path) -> None:
    done = subprocess.run([sys.executable, "-I", "-S", "-B", str(SCRIPT), "retained"],
                          capture_output=True, check=False, timeout=5)
    assert done.returncode == 2
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("fault", ["extra-file", "boolean-exit", "schema", "late", "unknown-status"])
def test_structural_readback_rejects_metadata_tampering(harness: Row, tmp_path: Path, fault: str) -> None:
    source = harness["root"] / "profile-audit"
    for name in FILES:
        (tmp_path / name).write_bytes((source / name).read_bytes())
    if fault == "extra-file":
        (tmp_path / "extra.txt").write_text("unexpected")
    else:
        attempt, report, receipt, completion = (read(tmp_path, name) for name in FILES)
        if fault == "boolean-exit":
            completion["exit_code"] = True
        elif fault == "schema":
            attempt["schema"] = report["schema"] = "wrong"
        elif fault == "late":
            receipt["elapsed_ns"] = attempt["wall_ns"]
        else:
            report["status"] = receipt["status"] = "made-up-refusal"
            completion["exit_code"] = 2
        config_file(tmp_path / "attempt.json", attempt)
        report["attempt_sha256"] = receipt["attempt_sha256"] = pin(tmp_path / "attempt.json")
        config_file(tmp_path / "report.json", report)
        receipt["report_sha256"] = pin(tmp_path / "report.json")
        config_file(tmp_path / "receipt.json", receipt)
        completion["receipt_sha256"] = pin(tmp_path / "receipt.json")
        config_file(tmp_path / "completion.json", completion)
    with pytest.raises(ValueError):
        harness["runner"]["_read_result"](tmp_path, harness["methods"]["io"], lambda: None)


@pytest.mark.parametrize("raw", [b'{"x":1e999}', b'{"x":NaN}', b'{"x":1,"x":2}'])
def test_strict_finite_json(harness: Row, raw: bytes) -> None:
    with pytest.raises(ValueError):
        harness["runner"]["_json"](raw)


@pytest.mark.parametrize("event,args", [
    ("import", ("spiceypy", None)),
    ("import", ("tudatpy", None)),
    ("ctypes.dlopen", ("/tmp/libcspice.dylib",)),
    ("os.remove", ("/tmp/unrelated", -1)),
    ("os.rename", ("/tmp/a", "/tmp/b", -1, -1)),
    ("os.mkdir", ("/tmp/unrelated", 448, -1)),
])
def test_guard_rejects_mission_access_and_unrelated_mutation(tmp_path: Path, event: str, args: tuple[Any, ...]) -> None:
    runtime = run_path(str(ART / "0241-runtime.py"))
    guard = runtime["Guard"](set(), set(), tmp_path / "out", lambda: None, None, scientific=True)
    with pytest.raises(ValueError):
        guard.hook(event, args)


def test_global_source_cap_counts_repeated_reads(tmp_path: Path) -> None:
    runtime = run_path(str(ART / "0241-runtime.py"))
    source = tmp_path / "source.json"
    source.write_bytes(b"x" * 1024)
    guard = runtime["Guard"](set(), {source}, tmp_path / "out", lambda: None, None, scientific=True)
    guard.source_bytes = 4 * 1024**2 - 1024
    guard.hook("open", (str(source), "r", 0))
    assert guard.source_bytes == 4 * 1024**2
    with pytest.raises(ValueError, match="byte cap"):
        guard.hook("open", (str(source), "r", 0))


@pytest.mark.parametrize("fault", [None, "metadata-cap", "source-cap"])
def test_linux_loader_metadata_uses_canonical_current_process_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str | None,
) -> None:
    runtime = run_path(str(ART / "0241-runtime.py"))
    guard = runtime["Guard"](set(), set(), tmp_path / "out", lambda: None, None, scientific=True)
    maps = tmp_path / "current-maps"
    alias = tmp_path / "self-maps"
    alias.symlink_to(maps)
    extension = Path(sys.modules["_hashlib"].__file__).resolve()
    data_file = Path(runtime["sysconfig"].__file__).resolve()
    raw = (f"1000-2000 r-xp 0000 00:00 1 {sys.executable}\n"
           f"2000-3000 r-xp 0000 00:00 2 {extension}\n"
           f"3000-4000 r--p 0000 00:00 3 {data_file}\n"
           "4000-5000 r--p 0000 00:00 4 /usr/lib/locale/C.utf8/LC_CTYPE\n"
           "5000-6000 r--p 0000 00:00 5 /unrelated/data\n").encode()
    if fault == "metadata-cap":
        raw = b"x" * (512 * 1024 + 1)
    maps.write_bytes(raw)
    if fault == "source-cap":
        guard.source_bytes = 4 * 1024**2 - 2 * len(raw) + 1
    original_open = Path.open

    def checked_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path.resolve() == maps:
            guard.hook("open", (str(path), "rb", 0))
        return original_open(path, *args, **kwargs)

    # Simulate proc's self symlink on either host, retaining real hook accounting.
    monkeypatch.setitem(runtime["_native_images"].__globals__, "Path",
                        lambda value: alias if value == "/proc/self/maps" else Path(value))
    monkeypatch.setattr(runtime["sys"], "platform", "linux")
    monkeypatch.setattr(Path, "open", checked_open)
    if fault:
        reason = "native metadata input cap" if fault == "source-cap" else "native image metadata cap"
        with pytest.raises(ValueError, match=reason):
            runtime["_native_images"](guard)
        return
    images, opaque = runtime["_native_images"](guard)
    assert str(maps) in guard.private and str(alias) not in guard.private
    assert images == {str(Path(sys.executable).resolve()), str(extension)} and opaque == []
    assert str(data_file) not in guard.native_files
    assert guard.source_bytes >= len(raw)
    for name in ("other-pid-maps", "environ", "unrelated.json"):
        with pytest.raises(ValueError, match="out-of-scope"):
            guard.hook("open", (str(tmp_path / name), "rb", 0))
    with pytest.raises(ValueError, match="input mutation"):
        guard.hook("open", (str(maps), "wb", runtime["os"].O_WRONLY))


def test_cli_early_worker_error_has_bounded_diagnostics(tmp_path: Path) -> None:
    done = subprocess.run([sys.executable, "-I", "-S", "-B", str(SCRIPT), "worker",
                           "profile-audit", "-", "-", str(tmp_path / "out"), "a" * 32, "1", "0"],
                          capture_output=True, check=False, timeout=5)
    assert done.returncode == 3 and b"worker deadline" in done.stderr
    assert len(done.stderr) <= 1025 and list(tmp_path.iterdir()) == []
