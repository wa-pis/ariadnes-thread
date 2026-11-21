"""Exercise exact dispatcher commands using isolated, explicitly fabricated inputs."""

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
from time import monotonic_ns
from types import ModuleType
from typing import Any

import pytest

from matched_norm_fixtures import wire, write_artificial_pack

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs/adr/experiments/0235-matched-norm.py"
HARNESS = Path(__file__).with_name("matched_norm_dispatch_harness.py")
COUNTS = dict(event_visits=1248, boxes=72, methods=144, oracles=72,
              diagonals=72, comparisons=72, descriptors=72)
type Row = dict[str, Any]


def load_dispatcher() -> ModuleType:
    module = ModuleType("_matched_norm_dispatch_tests")
    module.__file__ = str(SCRIPT)
    sys.modules[module.__name__] = module
    exec(compile(SCRIPT.read_bytes(), str(SCRIPT), "exec"), module.__dict__)
    return module


def prepare_dispatch_case(
    folder: Path, *, forbid_archive_reads: bool = False,
    fail_worker_after_success: tuple[str, ...] = (),
) -> Row:
    """Expose the same test-only bootstrap/configuration API to qualification drivers."""
    folder.mkdir()
    module = load_dispatcher()
    profile = write_artificial_pack(folder / "inputs")
    bootstrap = folder / "bootstrap.py"
    shutil.copyfile(HARNESS, bootstrap)
    config_path = bootstrap.with_suffix(".json")
    output, audit = folder / "result", folder / "audit.json"
    config = dict(
        script=str(SCRIPT), profile=profile, output=str(output), audit=str(audit),
        forbidden_real_inputs=[str(SCRIPT.parent / name) for name in module.DATA_NAMES],
        forbid_archive_reads=forbid_archive_reads,
        fail_worker_after_success=list(fail_worker_after_success),
    )
    config_path.write_bytes(wire(config))
    return dict(profile=profile, bootstrap=bootstrap, config=config_path, output=output, audit=audit)


def invoke(case: Row, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(case["bootstrap"]), *args],
        capture_output=True, text=True, timeout=35, check=False,
    )


def telemetry(result: subprocess.CompletedProcess[str]) -> list[Row]:
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _saved(output: Path) -> dict[str, str]:
    return {path.name: _digest(path) for path in output.iterdir()}


def _inventory_bytes(case: Row) -> int:
    module = load_dispatcher()
    design = json.loads(module.CONTRACT.read_bytes())
    paths = {case["bootstrap"], case["config"], module.CONTRACT, module.DESIGN}
    paths.update(Path(path) for path in case["profile"]["inputs"].values())
    paths.update(SCRIPT.with_name(name) for name in module.PRIVATE)
    paths.update(ROOT / path for path in design["source_bindings"].values())
    return sum(path.stat().st_size for path in paths)


def _assert_dispatch(case: Row, result: subprocess.CompletedProcess[str], command: list[str]) -> None:
    rows = telemetry(result)
    dispatch = next(row for row in rows if row.get("harness_dispatch"))
    worker = next(row for row in rows if row.get("harness_entry") and row["role"] == "worker")
    parent_budget = next(row for row in rows if row.get("harness_budget") and row["role"] == "parent")
    worker_budget = next(row for row in rows if row.get("harness_budget") and row["role"] == "worker")
    expected = ["worker", str(parent_budget["started_ns"]), parent_budget["invocation_id"], *command]
    assert dispatch["argv"] == worker["argv"] == expected
    assert len(expected) == (4 if command == ["retained"] else 5)
    assert dispatch["script"] == worker["script"] == str(SCRIPT)
    assert parent_budget["started_ns"] == parent_budget["bootstrap_entry_ns"]
    assert worker_budget["started_ns"] == parent_budget["started_ns"]
    assert worker_budget["invocation_id"] == parent_budget["invocation_id"]
    assert len(parent_budget["invocation_id"]) == 32
    expected_charge = case["bootstrap"].stat().st_size + case["config"].stat().st_size
    for row in rows:
        if row.get("harness_budget"):
            assert row["charged_bytes"] == expected_charge
            assert row["bootstrap_sha256"] == _digest(case["bootstrap"])
            assert row["config_sha256"] == _digest(case["config"])
        if row.get("harness_complete"):
            assert row["real_input_reads"] == 0
            assert row["artificial_input_reads"] == (7 if row["role"] == "worker" else 0)
    work = next(row for row in rows if "scientific_work" in row)
    assert {key: work["work"][key] for key in COUNTS} == COUNTS
    assert 0 < work["work"]["directed_primitives"] <= 8192
    assert all(value == 0 for value in work["scientific_work"].values())
    dispatcher = next(row for row in rows if "dispatcher_elapsed_ns" in row)
    assert 0 <= dispatcher["dispatcher_elapsed_ns"] < 30_000_000_000


def test_exact_retained_and_audit_commands_reach_independent_verifier_on_fake_data(tmp_path: Path) -> None:
    case = prepare_dispatch_case(tmp_path / "case")
    first = invoke(case, "retained")
    assert first.returncode == 0, first.stderr
    _assert_dispatch(case, first, ["retained"])
    pin = _digest(case["output"] / "completion.json")
    second = invoke(case, "audit", pin)
    assert second.returncode == 0, second.stderr
    _assert_dispatch(case, second, ["audit", pin])
    report = json.loads((case["output"] / "report.json").read_bytes())
    audit = json.loads(case["audit"].read_bytes())
    expected_bytes = _inventory_bytes(case)
    assert 3_784_677 <= expected_bytes <= 4 * 1024**2
    assert report["source_inventory_bytes"] == expected_bytes
    assert report["scope"] == "artificial-matched-norm" and report["stage"] == "R5.59w"
    assert report["source_pins"] == case["profile"]["pins"]
    assert report["commands"] is None and report["physical_status"] == "physical-join-not-established"
    assert report["status"] == "matched-norm-qualified-local-only"
    assert report["work"] == audit["work"] == audit["proof"]["counts"]
    assert {key: report["work"][key] for key in COUNTS} == COUNTS
    assert audit["status"] == "matched-norm-independently-verified"
    assert sum(path.stat().st_size for path in case["output"].iterdir()) <= 1048576 - 65536
    assert case["audit"].stat().st_size <= 65536
    assert sum(path.stat().st_size for path in case["output"].iterdir()) + case["audit"].stat().st_size <= 1048576
    before, audit_before = _saved(case["output"]), _digest(case["audit"])
    for args in (("retained",), ("audit", pin)):
        refused = invoke(case, *args)
        assert refused.returncode == 3
        assert not any(row.get("harness_dispatch") for row in telemetry(refused))
        assert all(row["artificial_input_reads"] == row["real_input_reads"] == 0
                   for row in telemetry(refused) if row.get("harness_complete"))
    assert _saved(case["output"]) == before and _digest(case["audit"]) == audit_before


@pytest.mark.parametrize("args", [(), ("retained", "extra"), ("audit",), ("audit", "pin", "extra"), ("unknown",)])
def test_malformed_outer_commands_do_not_read_any_archive(tmp_path: Path, args: tuple[str, ...]) -> None:
    case = prepare_dispatch_case(tmp_path / "case", forbid_archive_reads=True)
    result = invoke(case, *args)
    assert result.returncode == 3
    assert not any(row.get("harness_dispatch") for row in telemetry(result))
    assert all(row["artificial_input_reads"] == row["real_input_reads"] == 0
               for row in telemetry(result) if row.get("harness_complete"))
    assert not case["output"].exists() and not case["audit"].exists()


@pytest.mark.parametrize("tail", [None, "start-only", (), ("audit",), ("retained", "extra"), ("audit", "pin", "extra"), ("unknown",)])
def test_truncated_and_malformed_worker_commands_do_not_read_any_archive(
    tmp_path: Path, tail: tuple[str, ...] | str | None,
) -> None:
    case = prepare_dispatch_case(tmp_path / "case", forbid_archive_reads=True)
    if tail is None:
        args = ["worker"]
    elif tail == "start-only":
        args = ["worker", str(monotonic_ns())]
    else:
        assert type(tail) is tuple
        args = ["worker", str(monotonic_ns()), "c" * 32, *tail]
    result = invoke(case, *args)
    assert result.returncode == 3
    assert not any(row.get("harness_dispatch") for row in telemetry(result))
    assert all(row["artificial_input_reads"] == row["real_input_reads"] == 0
               for row in telemetry(result) if row.get("harness_complete"))
    assert not case["output"].exists() and not case["audit"].exists()


@pytest.mark.parametrize("mode", ["retained", "audit"])
def test_parent_removes_only_owned_success_marker_after_child_failure(tmp_path: Path, mode: str) -> None:
    case = prepare_dispatch_case(tmp_path / "case", fail_worker_after_success=(mode,))
    first = invoke(case, "retained")
    if mode == "retained":
        assert first.returncode == 3, first.stderr
        _assert_dispatch(case, first, ["retained"])
        assert set(_saved(case["output"])) == {"attempt.json", "report.json", "receipt.json"}
        before = _saved(case["output"])
        refused = invoke(case, "retained")
        assert refused.returncode == 3 and _saved(case["output"]) == before
        assert not any(row.get("harness_dispatch") for row in telemetry(refused))
    else:
        assert first.returncode == 0, first.stderr
        before = _saved(case["output"])
        pin = _digest(case["output"] / "completion.json")
        failed = invoke(case, "audit", pin)
        assert failed.returncode == 3, failed.stderr
        _assert_dispatch(case, failed, ["audit", pin])
        assert _saved(case["output"]) == before
    assert not case["audit"].exists()


def test_existing_artificial_cli_modes_still_dispatch_without_bootstrap(tmp_path: Path) -> None:
    profile = write_artificial_pack(tmp_path / "inputs")
    profile_path = tmp_path / "profile.json"
    profile_path.write_bytes(wire(profile))
    output, audit_path = tmp_path / "out", tmp_path / "audit.json"
    base = [sys.executable, "-I", "-S", "-B", str(SCRIPT)]
    first = subprocess.run([*base, "artificial", str(profile_path), str(output)],
                           capture_output=True, text=True, timeout=35, check=False)
    assert first.returncode == 0, first.stderr
    pin = _digest(output / "completion.json")
    second = subprocess.run([*base, "audit-artificial", str(profile_path), str(output), pin, str(audit_path)],
                            capture_output=True, text=True, timeout=35, check=False)
    assert second.returncode == 0, second.stderr
    for result in (first, second):
        work = next(row for row in telemetry(result) if "scientific_work" in row)
        assert {key: work["work"][key] for key in COUNTS} == COUNTS
        assert all(value == 0 for value in work["scientific_work"].values())
    assert json.loads(audit_path.read_bytes())["status"] == "matched-norm-independently-verified"


def test_production_profile_remains_fixed_without_retained_input_reads(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    module = load_dispatcher()
    forbidden = {SCRIPT.parent / name for name in module.DATA_NAMES}
    read = module.Budget.read

    def metadata_only(self: Any, path: Path, **kwargs: Any) -> bytes:
        assert path not in forbidden, "fixed-profile inspection must not open retained observations"
        return read(self, path, **kwargs)

    monkeypatch.setattr(module.Budget, "read", metadata_only)
    profile = module.retained_profile()
    assert profile["scope"] == "retained" and profile["candidate_id"] == "d0001-t0035"
    assert {Path(path) for path in profile["inputs"].values()} == forbidden
    profile["reference_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="fixed retained profile"):
        module.profile_check(profile, module.OUTPUT)
    with pytest.raises(ValueError, match="arity"):
        module.cli(["retained", str(tmp_path / "injected-profile.json")], module.Budget())


def test_all_work_source_time_and_output_caps_precharge_or_fail_closed(tmp_path: Path) -> None:
    module = load_dispatcher()
    limits = dict(event_visits=32768, boxes=72, methods=144, oracles=72,
                  diagonals=72, comparisons=72, descriptors=1024, directed_primitives=8192)
    for key, cap in limits.items():
        budget = module.Budget()
        budget.charge(key, cap)
        with pytest.raises(ValueError, match="cap exhausted"):
            budget.charge(key)
        assert budget.used[key] == cap + 1
    expired = module.Budget(started_ns=0, clock=lambda: module.WALL_NS)
    with pytest.raises(ValueError, match="deadline"):
        expired.charge("methods")
    assert expired.used["methods"] == 0
    small = tmp_path / "too-many-bytes"
    small.write_bytes(b"12345")
    with pytest.raises(ValueError, match="file byte cap"):
        module.Budget().read(small, cap=4)
    budget = module.Budget(source_bytes=4194304)
    with pytest.raises(ValueError, match="source inventory cap"):
        budget.read(small)
    out = tmp_path / "exclusive.json"
    with pytest.raises(ValueError, match="evidence byte cap"):
        module.save(out, {"a":"long"}, module.Budget(), cap=1)
    assert not out.exists()
    module.save(out, {"a":1}, module.Budget(), cap=1024)
    saved = out.read_bytes()
    with pytest.raises(FileExistsError):
        module.save(out, {"a":2}, module.Budget(), cap=1024)
    assert out.read_bytes() == saved


def test_scope_parse_and_source_pin_fail_before_any_output(tmp_path: Path) -> None:
    module = load_dispatcher()
    for raw in (b'{"a":1,"a":2}\n', b'{"a":NaN}\n', b'{"a":1e999}\n'):
        with pytest.raises(ValueError):
            module.decode(raw)
    case = prepare_dispatch_case(tmp_path / "tamper")
    input_path = Path(case["profile"]["inputs"]["report"])
    input_path.write_bytes(input_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="raw pin"):
        module.run(case["output"], case["profile"])
    assert not case["output"].exists()


def test_rechained_outer_status_cannot_disagree_with_independent_analysis(tmp_path: Path) -> None:
    module = load_dispatcher()
    case = prepare_dispatch_case(tmp_path / "status-tamper")
    module.run(case["output"], case["profile"])
    output = case["output"]
    report = json.loads((output / "report.json").read_bytes())
    report["status"] = "inconclusive"
    (output / "report.json").write_bytes(wire(report))
    receipt = json.loads((output / "receipt.json").read_bytes())
    receipt["report_sha256"] = _digest(output / "report.json")
    (output / "receipt.json").write_bytes(wire(receipt))
    completion = json.loads((output / "completion.json").read_bytes())
    completion["receipt_sha256"] = _digest(output / "receipt.json")
    (output / "completion.json").write_bytes(wire(completion))
    with pytest.raises(ValueError, match="completion/status"):
        module.audit(output, case["profile"], _digest(output / "completion.json"),
                     audit_path=case["audit"])
    assert not case["audit"].exists()


def test_late_arithmetic_failure_preserves_first_complete_box_and_progress(tmp_path: Path) -> None:
    module = load_dispatcher()
    case = prepare_dispatch_case(tmp_path / "partial-result")

    class StopAfterOneBox(module.Budget):
        def charge(self, key: str, count: int = 1) -> None:
            super().charge(key, count)
            if key == "methods" and self.used[key] == 3:
                raise ValueError("artificial late method failure")

    with pytest.raises(ValueError, match="artificial late method failure"):
        module.run(case["output"], case["profile"], budget=StopAfterOneBox())
    failure = json.loads((case["output"] / "failure.json").read_bytes())
    assert failure["status"] == "incomplete" and failure["completed_rows"] == 1
    assert failure["partial_rows"][0]["id"] == 0
    assert failure["partial_rows"][0]["diagonal"]["matches"] is True
    assert failure["progress"]["methods"] == dict(attempted=3, charged=2, completed=2)
    assert failure["attempted_work"]["methods"] == 3
    assert failure["charged_work"]["methods"] == 2
    assert not (case["output"] / "completion.json").exists()
    before = _saved(case["output"])
    with pytest.raises(ValueError, match="existing output"):
        module.run(case["output"], case["profile"])
    assert _saved(case["output"]) == before
