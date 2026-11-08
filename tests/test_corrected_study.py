"""Orchestration and real-engine tests use artificial constant ephemerides only."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0163-corrected-study.py"
SPEC = importlib.util.spec_from_file_location("corrected_study_tests", PATH)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)
core = study.load(ROOT, "0163-corrected-integrator.py")
reference = study.load(ROOT, "0163-corrected-reference.py")


def synthetic_bundle() -> dict[str, Any]:
    t0 = 978995455.2304223
    omega = math.sqrt(2e12/1e18)
    samples = [[1e6*math.cos(omega*s), 1e6*math.sin(omega*s), 0.,
                -1e6*omega*math.sin(omega*s), 1e6*omega*math.cos(omega*s), 0.] for s in core.OFFSETS]
    templates = {}
    for body, chain in (("Sun", ((10, 0, 0.),)),
                        ("Moon", ((301, 399, -1e6), (399, 0, 1e6))),
                        ("Earth", ((399, 0, 1e6),))):
        templates[body] = {"body": body, "segments": [{"body": b, "centre": c, "frame": 1, "type": 2,
            "first_tdb_s": t0-512., "last_tdb_s": t0+512., "words": [t0, 512., 0., 0., z]} for b, c, z in chain]}
    kernel = {"loaded_kernel_count": 13, "fixture": "synthetic-no-kernel-load"}
    identity = {k: {} for k in ("versions", "imports", "native_binary", "conda_build", "resource_build",
        "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime")}
    identity["kernels"] = kernel
    return {"initial": {"epoch_tdb_s": t0, "position_m": [1e6, 0., 0.],
            "velocity_m_s": [0., 1e6*omega, 0.]}, "offsets_s": list(core.OFFSETS),
            "gm_m3_s2": {"Sun": 1e12, "Moon": 1e12, "Earth": 1.},
            "radii_m": dict.fromkeys(core.BODIES, 1.), "source_rows_template": templates,
            "native_samples": {"normal": deepcopy(samples), "tighter": deepcopy(samples)},
            "input_sha256": {}, "protected_sha256": {}, "historical_identity": identity,
            "kernel_manifest": kernel, "retained_guard_metadata": {}}


def provider(body: str, epoch: float) -> list[float]:
    return [0., 0., 1e6 if body == "Earth" else 0., 0., 0., 0.]


@pytest.fixture(scope="module")
def analytic_result(tmp_path_factory: Any) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    data = synthetic_bundle()
    output = tmp_path_factory.mktemp("corrected-analytic")/"study.json"
    result = study.execute(output, inputs_loader=lambda root, check: deepcopy(data), references=reference,
        provider=provider, identity_provider=lambda: deepcopy(data["historical_identity"]))
    return result, output, data


def test_full_artificial_orbit_orchestration(analytic_result: Any) -> None:
    report, path, bundle = analytic_result
    assert report["status"] == "passed", report.get("error")
    assert report["finalization_gate"] == "passed"
    assert report["adapter_mode"] == "injected-test" and report["scientific_verified"] is False
    assert report["mission_accuracy_verified"] is False
    assert len(report["profiles"]) == 2 and len(report["observations"]) == 28
    assert len(report["comparisons"]) == 21 and len(report["native_guards"]) == 42
    for kind, expected in {"body_checks": 84, "source_rows": 56, "reference_fields": 448, "model_totals": 28}.items():
        assert report["counts"][kind]["attempted"] == report["counts"][kind]["completed"] == expected
    assert json.loads(path.read_text())["status"] == "passed"
    assert json.loads(path.with_suffix(".receipt.json").read_text())["finalization_gate"] == "passed"


def test_actual_saved_synthetic_run_passes_independent_arithmetic_replay(analytic_result: Any) -> None:
    report, path, bundle = analytic_result
    auditor = study.load(ROOT, "0163-corrected-audit.py")
    result = auditor.check_saved(report, bundle, reference)
    assert result["passed"] is True
    destination = path.with_name("audit.json")
    audited = auditor.audit(path, destination, inputs_loader=lambda root, check: deepcopy(bundle), references=reference)
    assert audited["audit_status"] == "passed", audited.get("error")
    assert audited["scientific_verified"] is False
    assert audited["counts"]["reference_fields"]["completed"] == 448
    assert audited["native_calls"] == 0


def test_exclusive_outputs_do_not_replay(analytic_result: Any) -> None:
    report, path, data = analytic_result
    previous = path.read_bytes()
    with pytest.raises(ValueError, match="exclusive"):
        study.execute(path, inputs_loader=lambda root, check: data, identity_provider=lambda: {})
    assert path.read_bytes() == previous


@pytest.mark.parametrize("key", ["versions", "imports", "native_binary", "conda_build", "resource_build",
                                  "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime", "kernels"])
def test_identity_mutations_fail(key: str) -> None:
    data = synthetic_bundle()
    actual = deepcopy(data["historical_identity"])
    actual[key] = {"changed": True}
    with pytest.raises(ValueError, match="identity"):
        study.check_identity(actual, data["historical_identity"], data["kernel_manifest"])


def test_first_solve_failure_prevents_tighter_and_preserves_partial(tmp_path: Path) -> None:
    data = synthetic_bundle()
    calls = []
    def fail(bundle: Any, name: str, report: Any, provider: Any, budget: Any) -> Any:
        calls.append(name)
        budget.event("solves", "attempt")
        report["profiles"].append({"name": name, "partial_raw": [123.]})
        raise ValueError("deliberate solve interruption")
    result = study.execute(tmp_path/"failed.json", inputs_loader=lambda root, check: data,
        identity_provider=lambda: data["historical_identity"], provider=provider, references=reference, integrate=fail)
    assert result["status"] == "failed" and calls == ["normal"]
    assert result["profiles"][0]["partial_raw"] == [123.]
    assert result["observations"] == []
    assert result["error"]["stage"] == "solve-normal"


def test_native_gate_failure_does_not_initialize_or_solve(tmp_path: Path) -> None:
    data = synthetic_bundle()
    data["native_samples"]["tighter"][0][0] += 1.
    def forbidden() -> Any:
        raise AssertionError("identity must not execute")
    result = study.execute(tmp_path/"gate.json", inputs_loader=lambda root, check: data,
        identity_provider=forbidden, references=reference)
    assert result["status"] == "failed"
    assert result["identities"] == {} and result["profiles"] == []
    assert result["comparisons"][0]["assessment"]["passed"] is False


def test_late_identity_return_is_retained(tmp_path: Path) -> None:
    data = synthetic_bundle()
    now = [0.]
    def identity() -> dict[str, Any]:
        now[0] = 60.
        return data["historical_identity"]
    result = study.execute(tmp_path/"late.json", clock=lambda: now[0], started_s=0.,
        inputs_loader=lambda root, check: data, identity_provider=identity, references=reference)
    assert result["status"] == "failed"
    assert result["identities"]["before"] == data["historical_identity"]
    assert result["counts"]["identities"] == {"attempted": 1, "returned": 1, "completed": 0}
    assert result["finalization_gate"] == "failed"


def test_finalization_deadline_downgrades_both_outputs() -> None:
    now = [0.]
    class Late(io.StringIO):
        def flush(self) -> None:
            now[0] = 60.
    stream, receipt = Late(), io.StringIO()
    report = {"status": "passed"}
    result = study.finish(stream, receipt, report, core.Budget(lambda: now[0], 0.))
    assert result["status"] == "failed" and result["finalization_gate"] == "failed"
    assert json.loads(stream.getvalue())["status"] == "failed"
    assert json.loads(receipt.getvalue())["finalization_gate"] == "failed"


def test_invalid_raw_values_serialize_as_failed_diagnostics() -> None:
    result = study.finite_wire({"raw": [float("nan"), float("inf"), object()]})
    text = json.dumps(result, allow_nan=False)
    assert 'invalid_numeric' in text and 'invalid_type' in text


def test_native_metadata_observer_counts_and_restores(monkeypatch: Any) -> None:
    calls = []
    sp = SimpleNamespace(ktotal=lambda *a: 13, kdata=lambda *a: ("x", "SPK", "", 0))
    td = SimpleNamespace(load_standard_kernels=lambda: calls.append("load"),
                         get_total_count_of_kernels_loaded=lambda: 13)
    monkeypatch.setitem(sys.modules, "spiceypy", sp)
    monkeypatch.setitem(sys.modules, "tudatpy.interface", SimpleNamespace(spice=td))
    original = sp.ktotal
    budget = core.Budget(lambda: 0., 0.)
    report = {"native_metadata_returns": []}
    with study.native_observer(budget, report):
        td.load_standard_kernels()
        assert sp.ktotal("ALL") == 13
        assert td.get_total_count_of_kernels_loaded() == 13
        for i in range(13):
            sp.kdata(i, "ALL")
    assert calls == ["load"] and sp.ktotal is original
    assert budget.counts["metadata"] == {"attempted": 15, "returned": 15, "completed": 15}
    assert budget.counts["initializations"]["attempted"] == 1
    assert len(report["native_metadata_returns"]) == 16


def test_external_start_is_required_before_real_entry(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="baseline"):
        study.execute(tmp_path/"never.json")
    assert not list(tmp_path.iterdir())



def test_real_provider_calls_geometric_ssb_and_chains_errors(monkeypatch: Any) -> None:
    calls = []
    def spkezr(*args: Any) -> Any:
        calls.append(args)
        return ([1., 2., 3., 4., 5., 6.], 0.)
    monkeypatch.setitem(sys.modules, "spiceypy", SimpleNamespace(spkezr=spkezr))
    assert study.real_provider("Moon", 123.) == [1., 2., 3., 4., 5., 6.]
    assert calls == [("Moon", 123., "J2000", "NONE", "SSB")]
    def unavailable(*args: Any) -> Any:
        raise RuntimeError("kernel unavailable")
    monkeypatch.setitem(sys.modules, "spiceypy", SimpleNamespace(spkezr=unavailable))
    with pytest.raises(ValueError, match="unavailable") as error:
        study.real_provider("Moon", 123.)
    assert isinstance(error.value.__cause__, RuntimeError)


def test_checked_source_bytes_are_the_executed_bytes(tmp_path: Path, monkeypatch: Any) -> None:
    from hashlib import sha256
    folder = tmp_path/"docs/adr/experiments"
    folder.mkdir(parents=True)
    path = folder/"fixture.py"
    raw = b"value = 'checked'\n"
    path.write_bytes(raw)
    original = Path.read_bytes
    calls = []
    def read(p: Path) -> bytes:
        data = original(p)
        if p == path:
            calls.append(p)
            path.write_text("raise AssertionError('unchecked reread')\n")
        return data
    monkeypatch.setattr(Path, "read_bytes", read)
    module = study.load(tmp_path, "fixture.py", sha256(raw).hexdigest())
    assert module.value == "checked" and len(calls) == 1


def test_startup_hash_failure_retains_finite_evidence_without_executing_core(tmp_path: Path) -> None:
    import subprocess
    folder = tmp_path/"docs/adr/experiments"
    folder.mkdir(parents=True)
    flag = tmp_path/"unchecked-code"
    (folder/"0163-corrected-integrator.py").write_text("from pathlib import Path\nPath("+repr(str(flag))+").touch()\n")
    (folder/"0163-verification.json").write_text(json.dumps({"preparation_complete": True,
        "tested_source_sha256": {"docs/adr/experiments/0163-corrected-integrator.py": "0"*64}}))
    out = tmp_path/"startup.json"
    code = "from time import monotonic\nstart=monotonic()\nimport importlib.util\nfrom pathlib import Path\n"
    code += "s=importlib.util.spec_from_file_location('s',"+repr(str(PATH))+")\nm=importlib.util.module_from_spec(s)\ns.loader.exec_module(m)\n"
    code += "r=m.execute(Path("+repr(str(out))+"),root=Path("+repr(str(tmp_path))+"),started_s=start)\nassert r['status']=='failed'\n"
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert not flag.exists()
    report = json.loads(out.read_text())
    assert report["error"]["stage"] == "preflight"
    assert "helper hash" in report["error"]["message"]
    assert report["rhs"] == [] and report["counts"] == {}


def test_final_input_mutation_downgrades_complete_numeric_run(tmp_path: Path) -> None:
    data = synthetic_bundle()
    calls = []
    def identity() -> dict[str, Any]:
        calls.append(True)
        if len(calls) == 2:
            data["input_sha256"]["changed"] = "late mutation"
        return deepcopy(data["historical_identity"])
    report = study.execute(tmp_path/"mutated.json", inputs_loader=lambda root, check: deepcopy(data),
                           identity_provider=identity, provider=provider, references=reference)
    assert report["status"] == "failed"
    assert "before/after input identity" in report["error"]["message"]
    assert len(report["observations"]) == 28
    assert report["scientific_verified"] is False



def test_measured_force_gate_failure_is_independently_audited_as_partial(tmp_path: Path) -> None:
    data = synthetic_bundle()
    def biased(body: str, epoch: float) -> list[float]:
        raw = provider(body, epoch)
        if body == "Sun":
            raw[0] += 1e-7  # 0.1mm source floor: state parity passes; force gate fails.
        return raw
    source = tmp_path/"force-failed.json"
    report = study.execute(source, inputs_loader=lambda root, check: deepcopy(data),
        identity_provider=lambda: deepcopy(data["historical_identity"]), provider=biased, references=reference)
    assert report["status"] == "failed" and report["error"]["stage"] == "selected-force-reference"
    assert len(report["observations"]) == 1
    auditor = study.load(ROOT, "0163-corrected-audit.py")
    checked = auditor.audit(source, tmp_path/"partial-audit.json",
                            inputs_loader=lambda root, check: deepcopy(data), references=reference)
    assert checked["audit_status"] == "partial", checked.get("error")
    assert checked["scientific_verified"] is False
