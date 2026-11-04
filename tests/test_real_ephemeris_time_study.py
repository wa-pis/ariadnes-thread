"""Bounded acquisition fixtures; no native imports, state reads or propagation."""
from __future__ import annotations

from fractions import Fraction as F
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/adr/experiments"


def module(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location("study_test_" + name[:4] + name[5:10], HERE / name)
    assert spec is not None and spec.loader is not None
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


study = module("0153-real-ephemeris-study.py")
oracle = module("0153-real-ephemeris-oracle.py")
compensated = module("0152-compensated-time-diagnostic.py")


class FakeSpice:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.kind = 2
        self.calls = 0
        self.records = {target: [study.T0, 1000.0,
            100000.0 * target, 30000.0 + target, 50.0, -500.0, 6.0, 4.0]
            for target in (10, 399, 301)}

    def spksfs(self, body: int, hi: float, length: int) -> tuple[int, list[float], str]:
        return 1, [float(body)], "linear fixture"

    def spkuds(self, descriptor: list[float]) -> tuple[Any, ...]:
        target = int(descriptor[0])
        start = target * 100
        return (target, study.CENTRES[target], 1, self.kind,
                study.T0 - 1000, study.T0 + 1000, start, start + 11)

    def kinfo(self, path: str) -> tuple[str, str, int]:
        assert path == str(self.path)
        return "SPK", "", 1

    def dafgda(self, handle: int, begin: int, end: int) -> list[float]:
        self.calls += 1
        target = begin // 100
        if begin % 100 == 8:
            return [study.T0 - 1000, 2000.0, 8.0, 1.0]
        return self.records[target]

    def spkezr(self, body: str, hi: float, frame: str, aberration: str,
               origin: str) -> tuple[list[float], float]:
        assert (frame, aberration, origin) == ("J2000", "NONE", "SSB")
        totals = [F(0)] * 6
        for target in study.CHAINS[body]:
            record = self.records[target]
            for j in range(3):
                constant, slope = map(F.from_float, record[2 + 2*j:4 + 2*j])
                totals[j] += constant + slope * (F.from_float(hi) - F.from_float(study.T0)) / 1000
                totals[j+3] += slope / 1000
        return [float(v) for v in totals], 0.0


@pytest.fixture
def spice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeSpice:
    path = tmp_path / "inpop19a_TDB_m100_p100_spice.bsp"
    path.write_bytes(b"native-free linear fixture")
    monkeypatch.setattr(study, "KERNEL_SHA", sha256(path.read_bytes()).hexdigest())
    monkeypatch.setattr(study, "KERNEL_PATH", path)
    return FakeSpice(path)


def test_collect_exact_counts_and_both_signs(spice: FakeSpice) -> None:
    result: dict[str, Any] = {"rows": []}
    budget = study.Budget(lambda: 0.0)
    study.collect(spice, oracle, compensated.split_epoch, budget, result)
    assert len(result["rows"]) == 21
    assert budget.counts == {"selections": 28, "selections_returned": 28,
        "descriptors": 28, "descriptors_returned": 28, "paths": 1,
        "paths_returned": 1, "arrays": 6, "arrays_returned": 6,
        "states": 21, "states_returned": 21}
    assert spice.calls == 6
    assert {math.copysign(1, r["lo_s"]) for r in result["rows"] if r["lo_s"]} == {-1, 1}
    assert all(len(r["segments"]) == len(study.CHAINS[r["body"]]) for r in result["rows"])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("value", [[True], [math.nan], [math.inf], ["1"]])
def test_nonfinite_array_rejected(value: list[Any]) -> None:
    with pytest.raises(ValueError, match="finite"):
        study.finite(value)


@pytest.mark.parametrize("kind", [3, 20])
def test_unsupported_type_stops_before_array(spice: FakeSpice, kind: int) -> None:
    spice.kind = kind
    budget = study.Budget(lambda: 0.0)
    with pytest.raises(ValueError, match="unsupported"):
        study.chain_records(spice, oracle, (10,), study.T0, 0.0, budget, {}, {})
    assert budget.counts["selections"] == 1
    assert "arrays" not in budget.counts


def test_cached_record_coverage_rechecked(spice: FakeSpice) -> None:
    budget = study.Budget(lambda: 0.0)
    cache: dict[Any, Any] = {}
    paths: dict[int, str] = {}
    study.chain_records(spice, oracle, (10,), study.T0, 0.0, budget, cache, paths)
    with pytest.raises(ValueError, match="coverage"):
        study.chain_records(spice, oracle, (10,), study.T0, 1001.0, budget, cache, paths)
    assert budget.counts["arrays"] == 2


def test_bad_directory_layout_rejected(spice: FakeSpice, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(spice, "dafgda", lambda *args: [study.T0-1000, 2000., 9., 1.])
    with pytest.raises(ValueError, match="layout"):
        study.chain_records(spice, oracle, (10,), study.T0, 0., study.Budget(lambda: 0.), {}, {})


def test_wrong_kernel_rejected(spice: FakeSpice, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(study, "KERNEL_SHA", "0" * 64)
    with pytest.raises(ValueError, match="kernel identity"):
        study.chain_records(spice, oracle, (10,), study.T0, 0., study.Budget(lambda: 0.), {}, {})
    assert spice.calls == 0


def test_call_cap_and_native_failure_counts() -> None:
    budget = study.Budget(lambda: 0.)
    budget.limits["states"] = 1
    def fail() -> None:
        raise OSError("fixture source unavailable")
    with pytest.raises(RuntimeError, match="native states"):
        budget.call("states", fail)
    with pytest.raises(ValueError, match="cap"):
        budget.call("states", fail)
    assert budget.counts == {"states": 1}


@pytest.mark.parametrize("later", [-1., 60., math.nan, math.inf])
def test_clock_deadline(later: float) -> None:
    values = iter([0., 0., later])
    budget = study.Budget(lambda: next(values))
    with pytest.raises(ValueError, match="deadline"):
        budget.check()


def test_source_pin_and_exclusive_output(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="identity"):
        study.load("0152-compensated-time-diagnostic.py", "0"*64)
    path = tmp_path / "exists.json"
    path.write_text("keep")
    with pytest.raises(FileExistsError):
        study.execute(path, clock=lambda: 0.)
    assert path.read_text() == "keep"


def configure(monkeypatch: pytest.MonkeyPatch, spice: FakeSpice,
              *, changed: bool = False) -> None:
    identities = iter([{"kernels": {"fixed": 13}},
                       {"kernels": {"fixed": 12 if changed else 13}}])
    runtime = SimpleNamespace(inputs=SimpleNamespace(
        load_inputs=lambda check: {"original_kernel_manifest": {"fixed": 13}},
        runtime_identity=lambda *args, **kwargs: next(identities)))
    sources = {"0153-real-ephemeris-oracle.py": oracle,
        "0152-compensated-time-diagnostic.py": compensated,
        "0142-short-coast-runner.py": runtime}
    monkeypatch.setattr(study, "load", lambda name, expected=None: sources[name])
    monkeypatch.setitem(sys.modules, "spiceypy", spice)


@pytest.mark.parametrize("changed", [False, True])
def test_execute_complete_or_identity_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                             spice: FakeSpice, changed: bool) -> None:
    configure(monkeypatch, spice, changed=changed)
    path = tmp_path / "result.json"
    result = study.execute(path, clock=lambda: 0.)
    assert result["status"] == ("partial" if changed else "passed")
    assert json.loads(path.read_text()) == result
    assert len(result["rows"]) == 21
    assert result["force_evaluations"] == result["spacecraft_propagations"] == 0
    if not changed:
        assert study.audit_saved(path)["status"] == "passed"
        assert study.audit_saved(path)["native_calls"] == 0


def test_failed_query_retains_record_and_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                               spice: FakeSpice) -> None:
    configure(monkeypatch, spice)
    def fail(*args: Any) -> None:
        raise OSError("fixture")
    monkeypatch.setattr(spice, "spkezr", fail)
    result = study.execute(tmp_path / "partial.json", clock=lambda: 0.)
    assert result["status"] == "partial"
    assert result["counts"]["states"] == 1
    assert "states_returned" not in result["counts"]
    assert len(result["rows"]) == 1 and result["rows"][0]["segments"]
    assert "state_si" not in result["rows"][0]


@pytest.mark.parametrize("mutation", ["state", "record", "epoch", "counts", "assessment", "status"])
def test_saved_mutations_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                 spice: FakeSpice, mutation: str) -> None:
    configure(monkeypatch, spice)
    path = tmp_path / "result.json"
    result = study.execute(path, clock=lambda: 0.)
    if mutation == "state":
        result["rows"][0]["state_si"][0] += 1
    elif mutation == "record":
        result["rows"][0]["segments"][0]["words"][2] += 1
    elif mutation == "epoch":
        result["rows"][0]["hi_tdb_s"] += 1
    elif mutation == "counts":
        result["counts"]["states"] += 1
    elif mutation == "assessment":
        result["rows"][0]["assessment"]["passed"] = False
    else:
        result["status"] = "partial"
    path.write_text(json.dumps(result, allow_nan=False))
    with pytest.raises(ValueError, match="saved"):
        study.audit_saved(path)


def test_completed_return_retained_on_deadline() -> None:
    now = [0.]
    budget = study.Budget(lambda: now[0])
    def late() -> list[float]:
        now[0] = 60.
        return [12.5]
    with pytest.raises(ValueError, match="deadline"):
        budget.call("states", late)
    assert budget.completed == [{"call": "states", "returned": [12.5]}]
    assert budget.counts["states_returned"] == 1


@pytest.mark.parametrize("failure", ["clock", "conversion", "missing_api"])
def test_finite_partial_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                 spice: FakeSpice, failure: str) -> None:
    configure(monkeypatch, spice)
    now = [0.]
    original = spice.spkezr
    def bad(*args: Any) -> Any:
        if failure == "clock":
            now[0] = math.nan
            return original(*args)
        if failure == "conversion":
            return [1e308] * 6, 0.
        raise AttributeError("missing boundary method")
    monkeypatch.setattr(spice, "spkezr", bad)
    path = tmp_path / "partial.json"
    result = study.execute(path, clock=lambda: now[0])
    assert result["status"] == "partial"
    assert json.loads(path.read_text()) == result
    if failure != "missing_api":
        assert result["native_returns"][-1]["call"] == "states"
        assert result["counts"]["states_returned"] == 1
    if failure == "clock":
        assert result["elapsed_before_flush_s"] == {"nonfinite": "nan"}
