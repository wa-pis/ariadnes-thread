"""Synthetic orchestration checks; never execute retained real-source forces."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/adr/experiments"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fixed_study_tests", HERE / "0157-fixed-gravity-study.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


study = load()


def bundle() -> dict[str, Any]:
    rows = []
    for s in range(7):
        for body in ("Sun", "Earth", "Moon"):
            rows.append({"body": body, "elapsed_s": float(s), "lo_s": 0.25,
                         "state_si": [2e9, -3e9, 4e9, 10.0, -20.0, 30.0]})
    return {"position_m": [0.0, 0.0, 0.0], "initial": {"fixture": True},
            "gm_m3_s2": {k: v for k, v in zip(("Sun", "Earth", "Moon"), (1e15, 2e15, 3e15))},
            "rows": rows, "input_sha256": {"fixture": "f"*64},
            "source_provenance": {"scope": "synthetic only"}, "identity": {"fixture": True}}


class References:
    def __init__(self, fail_source: bool = False, fail_total: bool = False) -> None:
        self.fail_source = fail_source
        self.fail_total = fail_total
        self.sources = 0

    def assess_source(self, raw: dict[str, Any], position: object, gm: object,
                      radius: object, arms: object, event: Any, **kwargs: Any) -> dict[str, Any]:
        self.sources += 1
        for _ in range(8):
            event("attempt")
            event("complete")
        return {"body": raw["body"], "passed": not self.fail_source}

    def assess_totals(self, rows: object, arms: object, *, consume_model: Any, **kwargs: Any) -> dict[str, Any]:
        result = {}
        for model in ("A", "B"):
            consume_model("attempt")
            result[model] = {"passed": not self.fail_total}
            consume_model("complete")
            if self.fail_total:
                break
        return result


@pytest.fixture
def fingerprints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(study, "fingerprints", lambda root, check: {"fixture": "f"*64})


def execute(tmp_path: Path, refs: Any = None, **kwargs: Any) -> dict[str, Any]:
    return study.execute(tmp_path / "result.json", inputs_loader=lambda root, check: bundle(),
                         references=References() if refs is None else refs, clock=lambda: 0.0, **kwargs)


def test_analytic_3d_field_and_controls() -> None:
    # Radius5m, mu25: acceleration equals the (3,4,0)/5 direction exactly.
    row = {"body": "Moon", "state_si": [3.0, 4.0, 0.0, 0.0, 0.0, 0.0], "lo_s": 0.0}
    arms = study.calculate_arms(row, [0.0]*3, 25.0, 1.0, lambda phase: None)
    for arm in arms.values():
        assert arm["acceleration_m_s2"] == [0.6, 0.8, 0.0]


def test_rephasing_remains_separate_at_large_absolute_coordinates() -> None:
    row = {"body": "Moon", "state_si": [1e16+2, 3.0, 0.0, 1.0, 0.0, 0.0], "lo_s": 0.25}
    arms = study.calculate_arms(row, [1e16, 0.0, 0.0], 1.0, 1.0, lambda phase: None)
    assert arms["compensated"]["separation_m"] == [2.25, 3.0, 0.0]
    assert arms["uncorrected"]["separation_m"] == [2.0, 3.0, 0.0]
    assert arms["wrong_sign"]["separation_m"] == [1.75, 3.0, 0.0]
    assert (row["state_si"][0] + 0.25) - 1e16 == 2.0


@pytest.mark.parametrize("change", ["boolean", "nonfinite", "gm", "inside", "surface"])
def test_invalid_field_operands_rejected(change: str) -> None:
    row = {"body": "Moon", "state_si": [3.0, 4.0, 0.0, 0.0, 0.0, 0.0], "lo_s": 0.0}
    gm, radius = 25.0, 1.0
    if change == "boolean":
        row["state_si"][0] = True
    elif change == "nonfinite":
        row["lo_s"] = math.inf
    elif change == "gm":
        gm = -1.0
    elif change == "inside":
        radius = 6.0
    else:
        radius = 5.0
    with pytest.raises(ValueError):
        study.calculate_arms(row, [0.0]*3, gm, radius, lambda phase: None)


def test_complete_synthetic_counts_and_exclusive_json(tmp_path: Path, fingerprints: None) -> None:
    report = execute(tmp_path)
    assert report["status"] == "passed"
    assert report["adapter_mode"] == "injected-test"
    assert len(report["rows"]) == 21 and len(report["totals"]) == 7
    for key, cap in study.CAPS.items():
        assert report["counts"][key] == {"attempted": cap, "completed": cap}
    assert json.loads((tmp_path / "result.json").read_text()) == report
    with pytest.raises(FileExistsError):
        execute(tmp_path)


def test_false_required_source_gate_keeps_failing_row_stops(tmp_path: Path, fingerprints: None) -> None:
    refs = References(fail_source=True)
    report = execute(tmp_path, refs)
    assert report["status"] == "partial" and refs.sources == 1
    assert len(report["rows"]) == 1 and not report["totals"]
    assert report["rows"][0]["assessment"]["passed"] is False
    assert report["first_error"]["stage"] == "source:0"
    assert report["counts"]["source_rows"]["completed"] == 1


def test_failed_first_model_leaves_second_unavailable(tmp_path: Path, fingerprints: None) -> None:
    report = execute(tmp_path, References(fail_total=True))
    assert report["status"] == "partial" and len(report["rows"]) == 3
    assert set(report["totals"][0]["assessment"]) == {"A"}
    assert report["counts"]["model_totals"] == {"attempted": 1, "completed": 1}
    assert report["error"]["stage"] == "totals:0:A"


def test_returned_arm_survives_after_call_clock_failure(tmp_path: Path, fingerprints: None) -> None:
    class Late:
        value = 0.0
        def __call__(self) -> float: return self.value
    clock = Late()
    original = study.calculate_arms
    def late(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = original(*args, **kwargs)
        clock.value = 11.0
        return result
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(study, "calculate_arms", late)
        report = study.execute(tmp_path / "late.json", clock=clock, start_s=0.0,
            inputs_loader=lambda root, check: bundle(), references=References())
    assert report["status"] == "partial" and report["finalization_gate"] == "failed"
    assert len(report["rows"][0]["arms"]) == 3
    assert report["counts"]["reference_fields"]["attempted"] == 0
    assert json.loads((tmp_path / "late.json").read_text())["status"] == "partial"


def test_invalid_input_and_changed_identity_stop(tmp_path: Path, fingerprints: None) -> None:
    calls = 0
    def drift(root: Path, check: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        result = bundle()
        if calls == 2:
            result["identity"]["drift"] = True
        return result
    report = study.execute(tmp_path / "drift.json", inputs_loader=drift,
                           references=References(), clock=lambda: 0.0)
    assert report["status"] == "partial" and report["error"]["stage"] == "identity"
    bad = deepcopy(bundle())
    bad["rows"][0]["body"] = "Earth"
    report = study.execute(tmp_path / "bad.json", inputs_loader=lambda root, check: bad,
                           references=References(), clock=lambda: 0.0)
    assert report["status"] == "partial" and report["counts"]["binary64_fields"]["attempted"] == 0


def test_counts_cap_and_unattempted_completion() -> None:
    budget = study.Budget(lambda: 0.0, 0.0)
    with pytest.raises(ValueError, match="unattempted"):
        budget.event("source_rows", "complete")
    for _ in range(21):
        budget.event("source_rows", "attempt")
    with pytest.raises(ValueError, match="cap"):
        budget.event("source_rows", "attempt")
    assert budget.counts["source_rows"]["attempted"] == 21


def test_final_flush_overrun_cannot_persist_passed_result(tmp_path: Path) -> None:
    class Clock:
        value = 0.0
        def __call__(self) -> float: return self.value
    clock = Clock()
    class Stream:
        def __init__(self, stream: Any) -> None: self.stream = stream
        def write(self, value: str) -> Any: return self.stream.write(value)
        def flush(self) -> None:
            self.stream.flush()
            clock.value = 10.0
        def seek(self, value: int) -> Any: return self.stream.seek(value)
        def truncate(self) -> Any: return self.stream.truncate()
    report = {"status": "passed"}
    with (tmp_path / "flush.json").open("x") as stream:
        study.flush_result(Stream(stream), report, study.Budget(clock, 0.0))
    saved = json.loads((tmp_path / "flush.json").read_text())
    assert saved["status"] == "partial" and saved["finalization_gate"] == "failed"


def test_import_isolation_in_fresh_interpreter() -> None:
    code = "import runpy,sys;runpy.run_path(sys.argv[1]);assert not any(k.split('.')[0] in {'numpy','scipy','spiceypy','tudatpy','space_nav'} for k in sys.modules)"
    subprocess.run([sys.executable, "-c", code, str(HERE / "0157-fixed-gravity-study.py")],
                   check=True, timeout=10, capture_output=True)


def test_nonfinite_hypot_rejected_before_zero_force() -> None:
    row = {"body": "Sun", "state_si": [1.7e308]*3+[0.0]*3, "lo_s": 0.0}
    with pytest.raises(ValueError, match="finite positive separation"):
        study.calculate_arms(row, [0.0]*3, 1.0, 1.0, lambda phase: None)


def test_invalid_clock_retains_finite_partial_json(tmp_path: Path, fingerprints: None) -> None:
    report = study.execute(tmp_path / "clock.json", clock=lambda: math.nan, start_s=0.0,
        inputs_loader=lambda root, check: bundle(), references=References())
    assert report["status"] == "partial" and report["finalization_gate"] == "failed"
    assert report["elapsed_before_flush_s"] is None
    assert json.loads((tmp_path / "clock.json").read_text()) == report


def test_actual_reference_integrates_with_synthetic_study(tmp_path: Path, fingerprints: None) -> None:
    fixture_path = ROOT / "tests/test_fixed_gravity_reference.py"
    spec = importlib.util.spec_from_file_location("fixed_reference_fixtures", fixture_path)
    assert spec is not None and spec.loader is not None
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    value = bundle()
    value["rows"] = []
    for time_index in range(7):
        for body in ("Sun", "Earth", "Moon"):
            row = fixtures._row((2e6, 3e6, 6e6), body=body)
            row["elapsed_s"] = float(time_index)
            value["rows"].append(row)
    report = study.execute(tmp_path / "integrated.json", clock=lambda: 0.0,
        inputs_loader=lambda root, check: deepcopy(value), references=fixtures.reference)
    assert report["status"] == "passed", report.get("error")
    assert report["counts"]["reference_fields"]["completed"] == 168
    assert len(report["totals"]) == 7
    spec = importlib.util.spec_from_file_location("fixed_actual_auditor", HERE / "0157-fixed-gravity-audit.py")
    assert spec is not None and spec.loader is not None
    auditor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auditor)
    audited = auditor.audit(tmp_path / "integrated.json", tmp_path / "audit.json",
        clock=lambda: 0.0, start_s=0.0, inputs_loader=lambda root, check: deepcopy(value),
        references=fixtures.reference)
    assert audited["audit_status"] == "passed", audited.get("error")
    assert audited["scientific_verified"] is False
    assert audited["counts"]["reference_fields"]["completed"] == 168


def test_reference_cannot_reset_process_start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    current = study.monotonic()
    monkeypatch.setattr(study, "PROCESS_START", current - 1.0)
    report = study.execute(tmp_path / "reset.json", start_s=current)
    assert report["status"] == "partial"
    assert "baseline" in report["error"]["message"]
    assert not report["rows"]


def test_reference_rejects_preloaded_scientific_modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(study, "PROCESS_START", study.monotonic())
    monkeypatch.setitem(sys.modules, "scipy", ModuleType("scipy"))
    report = study.execute(tmp_path / "not-fresh.json")
    assert report["status"] == "partial"
    assert "fresh" in report["error"]["message"]
    assert not report["rows"]


@pytest.mark.parametrize("kwargs", [{"start_s": math.nan}, {"clock": lambda: math.nan}])
def test_invalid_initial_baseline_rejected_before_creating_output(tmp_path: Path, kwargs: dict[str, Any]) -> None:
    path = tmp_path / "invalid-start.json"
    with pytest.raises(ValueError, match="start_s"):
        study.execute(path, **kwargs)
    assert not path.exists()


def test_checked_source_bytes_bypass_stale_same_timestamp_pyc(tmp_path: Path) -> None:
    from hashlib import sha256
    import os
    import py_compile
    path = tmp_path / "docs/adr/experiments/fixture.py"
    path.parent.mkdir(parents=True)
    path.write_text("VALUE=1\n")
    stat = path.stat()
    py_compile.compile(str(path), doraise=True)
    path.write_text("VALUE=2\n")
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    module = study.load(tmp_path, "fixture.py", sha256(path.read_bytes()).hexdigest())
    assert module.VALUE == 2


def test_failure_stage_tracks_attempted_work_at_deadline_boundary() -> None:
    budget = study.Budget(lambda: 10.0, 0.0)
    budget.stage = "source:2"
    with pytest.raises(ValueError, match="deadline"):
        budget.event("model_totals", "attempt", stage="totals:0:A")
    assert budget.stage == "source:2" and not budget.ledger
    calls = iter((0.0, 10.0))
    budget.clock = lambda: next(calls)
    with pytest.raises(ValueError, match="deadline"):
        budget.event("model_totals", "attempt", stage="totals:0:A")
    assert budget.stage == "totals:0:A"
    assert budget.counts["model_totals"] == {"attempted": 1, "completed": 0}
