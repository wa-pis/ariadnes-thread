"""Synthetic moving arithmetic/orchestration checks; no retained source study."""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0160-moving-study.py"
spec = importlib.util.spec_from_file_location("moving_study_tests", PATH)
assert spec is not None and spec.loader is not None
study = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = study
spec.loader.exec_module(study)
GM = {"Sun": 1.327124400420322e20, "Moon": 4902800121846.8, "Earth": 398600435468295.9}
DISTANCE = {"Sun": float(2**40), "Earth": float(2**41), "Moon": float(3 * 2**40)}


def initial() -> dict[str, Any]:
    return {"position_m": [0.0] * 3, "velocity_m_s": [0.0] * 3}


def bundle() -> dict[str, Any]:
    source = {
        body: {
            "separation_m": [d, 0.0, 0.0],
            "rephasing_m": [0.0] * 3,
            "acceleration_m_s2": [GM[body] / (d * d), 0.0, 0.0],
        }
        for body, d in DISTANCE.items()
    }
    return {
        "position_m": [0.0] * 3,
        "initial": initial(),
        "gm_m3_s2": dict(GM),
        "rows": [
            {
                "body": body,
                "elapsed_s": float(i),
                "lo_s": 0.0,
                "state_si": [DISTANCE[body], 0.0, 0.0, 0.0, 0.0, 0.0],
            }
            for i in range(7)
            for body in ("Sun", "Earth", "Moon")
        ],
        "input_sha256": {"synthetic": "only"},
        "source_provenance": {"synthetic": True},
        "identity": {"synthetic": True},
        "zero_reference": {
            "sources": source,
            "totals": {
                model: {
                    "acceleration_m_s2": [
                        math.fsum(source[b]["acceleration_m_s2"][0] for b in bodies),
                        0.0,
                        0.0,
                    ]
                }
                for model, bodies in study.MODELS.items()
            },
        },
    }


class References:
    def __init__(
        self,
        *,
        fail_motion: bool = False,
        fail_source: bool = False,
        fail_model: bool = False,
        clock: Any = None,
        invalid: Any = None,
    ) -> None:
        self.fail_motion, self.fail_source, self.fail_model = (
            fail_motion,
            fail_source,
            fail_model,
        )
        self.clock, self.invalid = clock, invalid
        self.source_calls = 0

    def assess_motion(self, _initial: Any, _motion: Any) -> dict[str, Any]:
        return {"passed": not self.fail_motion, "invalid": self.invalid}

    def preflight_source(
        self,
        _row: Any,
        _initial: Any,
        _motion: Any,
        _gm: Any,
        _radius: Any,
        _arms: Any,
        *,
        progress: Any,
    ) -> None:
        progress["reference"] = {"80": {}, "100": {}}

    def assess_source(
        self,
        row: Any,
        _initial: Any,
        _motion: Any,
        _gm: Any,
        _radius: Any,
        _arms: Any,
        consume: Any,
        *,
        progress: Any,
    ) -> dict[str, Any]:
        self.source_calls += 1
        progress["reference"] = {"80": {}, "100": {}}
        for precision in ("80", "100"):
            for geometry in ("d0", "d1", "d2", "d3"):
                consume("attempt")
                progress["reference"][precision][geometry] = ["0", "0", "0"]
                if self.clock is not None:
                    self.clock.now = 11.0
                consume("complete")
        return {"body": row["body"], "passed": not self.fail_source}

    def assess_totals(
        self, _sources: Any, _arms: Any, *, consume_model: Any, progress: Any
    ) -> dict[str, Any]:
        for model in study.MODELS:
            consume_model("attempt")
            progress[model] = {"passed": not self.fail_model}
            consume_model("complete")
            if self.fail_model:
                break
        return progress


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def hashes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(study, "fingerprints", lambda root, check: {})


def execute(tmp_path: Path, refs: Any = None, **kwargs: Any) -> dict[str, Any]:
    return study.execute(
        tmp_path / "out.json",
        inputs_loader=lambda root, check: bundle(),
        references=References() if refs is None else refs,
        clock=kwargs.pop("clock", lambda: 0.0),
        **kwargs,
    )


def test_nonzero_motion_matches_independent_rational_targets() -> None:
    raw = {"position_m": [1e16, -1e16, 3.0], "velocity_m_s": [1.0, -2.0, 0.5]}
    m = study.assemble_motion(raw, 0.5)
    assert m["q_m"] == [-0.125, 0.0625, -0.03125]
    assert m["w_m_s"] == [-0.5, 0.25, -0.125]
    assert m["drift_m"] == [0.5, -1.0, 0.25]
    for j in range(3):
        exact = (
            Fraction.from_float(raw["position_m"][j])
            + Fraction.from_float(raw["velocity_m_s"][j]) / 2
            + Fraction.from_float(m["q_m"][j])
        )
        assert m["position_m"][j] == float(exact)
    assert m["velocity_m_s"] == [0.5, -1.75, 0.375]


def test_relative_sum_keeps_small_terms_lost_in_absolute_export() -> None:
    raw = {"position_m": [1e16, 0.0, 0.0], "velocity_m_s": [1.0, 0.0, 0.0]}
    m = study.assemble_motion(raw, 1.0)
    row = {
        "body": "Moon",
        "state_si": [1e16 + 4.0, 4.0, 0.0, 0.5, 0.0, 0.0],
        "lo_s": 0.5,
    }
    a = study.calculate_arms(row, raw, m, 1.0, 1.0, lambda phase: None)
    assert a["compensated"]["separation_m"] == [3.75, 3.75, 0.125]
    assert a["flattened_craft"]["separation_m"][0] == 4.25
    assert a["omitted_q"]["separation_m"][0] == 3.25


@pytest.mark.parametrize("bad", [True, math.nan, math.inf, -1.0, 301.0, "1"])
def test_bad_elapsed_rejected(bad: Any) -> None:
    with pytest.raises((ValueError, TypeError)):
        study.assemble_motion(initial(), bad)


@pytest.mark.parametrize(
    "part", ["r0", "v0", "source", "gm", "radius", "inside", "surface", "lo"]
)
def test_invalid_force_operands_fail(part: str) -> None:
    raw, m = initial(), study.assemble_motion(initial(), 0.0)
    row = {"body": "Moon", "state_si": [3.0, 4.0, 0.0, 0.0, 0.0, 0.0], "lo_s": 0.0}
    gm, radius = 25.0, 1.0
    if part == "r0":
        raw["position_m"][0] = True
    elif part == "v0":
        m["drift_m"][0] = math.inf
    elif part == "source":
        row["state_si"][0] = math.nan
    elif part == "gm":
        gm = 0.0
    elif part == "radius":
        radius = -1.0
    elif part == "inside":
        radius = 6.0
    elif part == "surface":
        radius = 5.0
    else:
        row["lo_s"] = "bad"
    with pytest.raises((ValueError, TypeError)):
        study.calculate_arms(row, raw, m, gm, radius, lambda phase: None)


def test_analytic_three_four_five_force() -> None:
    row = {"body": "Moon", "state_si": [3.0, 4.0, 0.0, 0.0, 0.0, 0.0], "lo_s": 0.0}
    m = study.assemble_motion(initial(), 0.0)
    arms = study.calculate_arms(row, initial(), m, 25.0, 1.0, lambda phase: None)
    assert all(v["acceleration_m_s2"] == [0.6, 0.8, 0.0] for v in arms.values())


def test_complete_synthetic_counts_and_exclusivity(
    tmp_path: Path, hashes: None
) -> None:
    report = execute(tmp_path)
    assert report["status"] == "passed" and report["adapter_mode"] == "injected-test"
    assert (
        len(report["motions"]) == 7
        and len(report["rows"]) == 21
        and len(report["totals"]) == 7
    )
    assert all(
        report["counts"][k] == {"attempted": cap, "completed": cap}
        for k, cap in study.CAPS.items()
    )
    assert json.loads((tmp_path / "out.json").read_text()) == report
    assert report["identity_after"] == report["inputs"]
    with pytest.raises(FileExistsError):
        execute(tmp_path)


@pytest.mark.parametrize("phase", ["motion", "source", "model"])
def test_first_required_failure_stops_downstream(
    tmp_path: Path, hashes: None, phase: str
) -> None:
    report = execute(tmp_path, References(**{"fail_" + phase: True}))
    assert report["status"] == "partial"
    if phase == "motion":
        assert len(report["motions"]) == 1 and not report["rows"]
        assert report["first_error"]["stage"] == "motion:0"
    elif phase == "source":
        assert len(report["rows"]) == 1 and not report["totals"]
        assert report["first_error"]["stage"] == "source:0"
    else:
        assert len(report["rows"]) == 3 and set(report["totals"][0]["assessment"]) == {
            "A"
        }
        assert report["counts"]["model_totals"] == {"attempted": 1, "completed": 1}
        assert report["first_error"]["stage"] == "totals:0:A"


def test_returned_reference_field_retained_on_clock_overrun(
    tmp_path: Path, hashes: None
) -> None:
    clock = Clock()
    report = execute(tmp_path, References(clock=clock), clock=clock, start_s=0.0)
    assert report["status"] == "partial" and report["finalization_gate"] == "failed"
    assert report["first_error"]["stage"] == "source:0"
    assert report["error"]["stage"] == "finalization"
    assert report["counts"]["reference_fields"] == {"attempted": 1, "completed": 1}
    assert report["rows"][0]["reference_progress"]["reference"]["80"]["d0"] == ["0"] * 3


@pytest.mark.parametrize("bad", [math.nan, math.inf, True, "0"])
def test_invalid_start_has_no_empty_evidence(tmp_path: Path, bad: Any) -> None:
    with pytest.raises((ValueError, TypeError)):
        execute(tmp_path, start_s=bad)
    assert not (tmp_path / "out.json").exists()


def test_future_initial_clock_has_no_empty_evidence(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        execute(tmp_path, start_s=1.0)
    assert not (tmp_path / "out.json").exists()


def test_elapsed_deadline_retains_input_failure(tmp_path: Path, hashes: None) -> None:
    report = execute(tmp_path, clock=lambda: 10.0, start_s=0.0)
    assert report["status"] == "partial" and not report["motions"]
    assert report["first_error"]["stage"] == "inputs"


def test_identity_change_rejected(tmp_path: Path, hashes: None) -> None:
    count = 0

    def loader(root: Any, check: Any) -> dict[str, Any]:
        nonlocal count
        count += 1
        value = bundle()
        value["identity"]["call"] = count
        return value

    report = study.execute(
        tmp_path / "out.json",
        inputs_loader=loader,
        references=References(),
        clock=lambda: 0.0,
    )
    assert (
        report["status"] == "partial" and report["first_error"]["stage"] == "identity"
    )


def test_bad_zero_source_stops_before_decimal(tmp_path: Path, hashes: None) -> None:
    b = bundle()
    b["zero_reference"]["sources"]["Sun"]["acceleration_m_s2"][0] += 1.0
    report = study.execute(
        tmp_path / "out.json",
        inputs_loader=lambda root, check: deepcopy(b),
        references=References(),
        clock=lambda: 0.0,
    )
    assert (
        report["status"] == "partial"
        and report["counts"]["reference_fields"]["attempted"] == 0
    )
    assert report["first_error"]["stage"] == "source:0"


def test_bad_zero_model_preserves_source_rows(tmp_path: Path, hashes: None) -> None:
    b = bundle()
    b["zero_reference"]["totals"]["A"]["acceleration_m_s2"][0] += 1.0
    report = study.execute(
        tmp_path / "out.json",
        inputs_loader=lambda root, check: deepcopy(b),
        references=References(),
        clock=lambda: 0.0,
    )
    assert len(report["rows"]) == 3 and report["first_error"]["stage"] == "totals:0:A"
    assert report["counts"]["model_totals"] == {"attempted": 1, "completed": 0}


@pytest.mark.parametrize("invalid", [math.nan, object()])
def test_nonfinite_or_nonjson_reference_does_not_pass(
    tmp_path: Path, hashes: None, invalid: Any
) -> None:
    report = execute(tmp_path, References(invalid=invalid))
    assert report["status"] == "partial" and not report["rows"]
    json.dumps(report, allow_nan=False)


def test_fresh_process_requirement_checks_before_data(tmp_path: Path) -> None:
    # The real process budget starts at module load, so isolate from collection
    # and preceding native tests instead of resetting the production baseline.
    program = """
import importlib.util, sys
from pathlib import Path
path, output = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location("fresh_moving_study", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
sys.modules["numpy"] = object()
module.execute(output)
"""
    output = tmp_path / "out.json"
    subprocess.run(
        [sys.executable, "-c", program, str(PATH), str(output)],
        check=True, capture_output=True, text=True, timeout=10,
    )
    report = json.loads(output.read_text())
    assert (
        report["status"] == "partial"
        and "stdlib-only" in report["first_error"]["message"]
    )
    assert "inputs" not in report


def test_late_real_baseline_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        study.execute(tmp_path / "out.json", start_s=study.PROCESS_START + 1e-8)
    assert not (tmp_path / "out.json").exists()


def test_each_cap_and_completion_ledger() -> None:
    for name, cap in study.CAPS.items():
        budget = study.Budget(lambda: 0.0, 0.0)
        for _ in range(cap):
            budget.event(name, "attempt")
            budget.event(name, "complete")
        with pytest.raises(ValueError):
            budget.event(name, "attempt")
        with pytest.raises(ValueError):
            budget.event(name, "complete")
        assert len(budget.ledger) == cap * 2


def test_serialization_failure_downgrades_pass() -> None:
    class OnceBroken(io.StringIO):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def flush(self) -> None:
            self.calls += 1
            if self.calls == 1:
                raise OSError("flush failure")

    stream = OnceBroken()
    result = study.flush_result(
        stream, {"status": "passed"}, study.Budget(lambda: 0.0, 0.0)
    )
    assert (
        result["status"] == "partial"
        and result["first_error"]["stage"] == "finalization"
    )
    assert json.loads(stream.getvalue())["finalization_gate"] == "failed"


@pytest.mark.parametrize("distance", [1e200, 1.7e308])
def test_norm_overflow_rejects_before_any_field(distance: float) -> None:
    row = {
        "body": "Moon",
        "state_si": [distance, distance, 0.0, 0.0, 0.0, 0.0],
        "lo_s": 0.0,
    }
    events: list[str] = []
    with pytest.raises(ValueError):
        study.calculate_arms(
            row,
            initial(),
            study.assemble_motion(initial(), 0.0),
            1.0,
            1.0,
            events.append,
        )
    assert events == []


def test_later_control_domain_rejects_before_primary_field() -> None:
    raw = {"position_m": [0.0] * 3, "velocity_m_s": [0.0] * 3}
    m = study.assemble_motion(raw, 2.0)
    # Actual compensated separation2.5m is exterior; omitted-q0.5m is not.
    row = {"body": "Moon", "state_si": [0.5, 0.0, 0.0, 0.0, 0.0, 0.0], "lo_s": 0.0}
    events: list[str] = []
    with pytest.raises(ValueError):
        study.calculate_arms(row, raw, m, 1.0, 1.0, events.append)
    assert events == []


def test_independent_exact_domain_preflight_precedes_fields(
    tmp_path: Path, hashes: None
) -> None:
    class StopBeforeFields(References):
        def preflight_source(self, *args: Any, progress: Any) -> None:
            progress["assembly"] = {"domain_guards": {"d0": False}}
            raise ValueError("exact d0 domain")

    report = execute(tmp_path, StopBeforeFields())
    assert report["status"] == "partial"
    assert report["counts"]["binary64_fields"] == {"attempted": 0, "completed": 0}
    assert report["counts"]["reference_fields"] == {"attempted": 0, "completed": 0}
    assert (
        report["rows"][0]["reference_progress"]["assembly"]["domain_guards"]["d0"]
        is False
    )


def test_independent_reference_and_saved_auditor_roundtrip(
    tmp_path: Path, hashes: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Constant synthetic SPK records exercise all modules without real mission data."""

    def module(name: str) -> Any:
        path = ROOT / "docs/adr/experiments" / ("0160-moving-" + name + ".py")
        mspec = importlib.util.spec_from_file_location("moving_roundtrip_" + name, path)
        assert mspec is not None and mspec.loader is not None
        loaded = importlib.util.module_from_spec(mspec)
        sys.modules[mspec.name] = loaded
        mspec.loader.exec_module(loaded)
        return loaded

    reference, auditor = module("reference"), module("audit")
    b = bundle()
    b["initial"]["epoch_tdb_s"] = 1000.0
    b["initial"]["velocity_m_s"] = [0.125, -0.5, 1.0]
    chains = {"Sun": ((10, 0),), "Earth": ((399, 0),), "Moon": ((301, 399), (399, 0))}
    rows = []
    for i in range(7):
        for body in ("Sun", "Earth", "Moon"):
            segments, records = [], []
            for j, (target, centre) in enumerate(chains[body]):
                coefficient = DISTANCE[body] / 1000.0 if j == 0 else 0.0
                words = [1000.0, 100.0, coefficient, 0.0, 0.0, 0.0, 0.0, 0.0]
                records.append(reference.ORACLE.parse_record(words))
                segments.append(
                    {
                        "body": target,
                        "centre": centre,
                        "frame": 1,
                        "type": 2,
                        "first_tdb_s": 900.0,
                        "last_tdb_s": 1100.0,
                        "words": words,
                    }
                )
            state = [DISTANCE[body], 0.0, 0.0, 0.0, 0.0, 0.0]
            hi = 1000.0 + i
            rows.append(
                {
                    "body": body,
                    "elapsed_s": float(i),
                    "hi_tdb_s": hi,
                    "lo_s": 0.0,
                    "hi_hex": hi.hex(),
                    "lo_hex": (0.0).hex(),
                    "state_si": state,
                    "segments": segments,
                    "assessment": reference.ORACLE.assess(state, records, hi, 0.0),
                }
            )
    b["rows"] = rows
    def loader(root: Any, check: Any) -> dict[str, Any]:
        return deepcopy(b)

    report = study.execute(
        tmp_path / "out.json",
        inputs_loader=loader,
        references=reference,
        clock=lambda: 0.0,
    )
    assert report["status"] == "passed", report.get("error")
    audited = auditor.audit(
        tmp_path / "out.json",
        tmp_path / "audit.json",
        inputs_loader=loader,
        references=reference,
        clock=lambda: 0.0,
    )
    assert audited["audit_status"] == "passed", audited.get("error")
    assert audited["scientific_verified"] is False
    assert audited["counts"] == report["counts"]
    assert len(audited["checks"]["motions"]) == 7
    # An independent saved-data check must reject a modified coordinate, not trust its flag.
    corrupted = deepcopy(report)
    corrupted["motions"][1]["motion"]["position_m"][0] += 1.0
    changed = tmp_path / "corrupt.json"
    changed.write_text(json.dumps(corrupted, allow_nan=False))
    rejected = auditor.audit(
        changed,
        tmp_path / "reject.json",
        inputs_loader=loader,
        references=reference,
        clock=lambda: 0.0,
    )
    assert (
        rejected["audit_status"] == "rejected"
        and rejected["scientific_verified"] is False
    )


def test_elapsed_subtraction_overflow_retains_finite_partial(
    tmp_path: Path, hashes: None
) -> None:
    report = study.execute(
        tmp_path / "overflow.json",
        clock=lambda: 1e308,
        start_s=-1e308,
        inputs_loader=lambda root, check: bundle(),
        references=References(),
    )
    assert report["status"] == "partial"
    assert report["first_error"]["stage"] == "inputs"
    assert report["elapsed_before_flush_s"] is None
    assert report["elapsed_after_failed_flush_s"] is None
    assert json.loads((tmp_path / "overflow.json").read_text()) == report
