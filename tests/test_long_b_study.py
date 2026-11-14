"""Run R5.39's actual adaptive profiles and offline audit on synthetic data only."""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from test_earth_coast_native import Array
from test_split_coast_study import artificial_bundle, artificial_state

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/adr/experiments"
type Row = dict[str, Any]


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location("test_r539_" + name, ART / f"0186-long-b-{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


study = load("study")


def fixture() -> tuple[Row, ModuleType, list[tuple[float, float]]]:
    bundle = artificial_bundle()
    bundle["offsets_s"] = list(range(0, 601, 50))
    for row in bundle["source_rows_template"].values():
        for record in row["segments"]:
            t0 = record["words"][0]
            record.update(first_tdb_s=t0-1024, last_tdb_s=t0+1024)
            record["words"][1] = 1024.
    # Nonzero, analytically observable Earth perturbation; the linearized
    # formula is independent of either the force assembly or the ODE solver.
    bundle["gm_m3_s2"]["Earth"] = 1e12
    source = bundle["gm_m3_s2"]
    initial = bundle["initial"]
    t0 = initial["epoch_tdb_s"]
    omega = initial["velocity_m_s"][1]/initial["position_m"][0]

    def expected(s: float) -> list[float]:
        if not s:
            return initial["position_m"] + initial["velocity_m_s"]
        c, v = math.cos(omega*s), math.sin(omega*s)
        az = source["Earth"]/1e18
        return [1e6*c, 1e6*v, az/omega**2*(1-c), -1e6*omega*v, 1e6*omega*c, az/omega*v]

    bundle["b_prefix"] = {family: {name: [expected(s) for s in bundle["offsets_s"][:7]]
                                    for name in ("normal", "tighter")} for family in ("native", "dop853")}
    bundle["b_runtime"] = bundle["historical_identity"]
    bundle["b_archive_sha256"] = "a"*64
    adapter = load("native").load_adapter()
    adapter.GM, adapter.GUARDS = source, bundle["radii_m"]
    launched: list[tuple[float, float]] = []

    def body_state(body: str, t: float) -> list[float]:
        return [x*1000 for x in artificial_state(body, t, "J2000", "NONE", "SSB")]

    prepared = SimpleNamespace(
        included=("Sun", "Moon", "Earth"), gravity_parameters_m3_s2=source,
        accelerations={"Spacecraft": {body: [object()] for body in source}},
        bodies=SimpleNamespace(
            global_frame_origin=lambda: "SSB", global_frame_orientation=lambda: "J2000",
            get=lambda b: SimpleNamespace(
                gravity_field_model=SimpleNamespace(gravitational_parameter=source[b]),
                ephemeris=SimpleNamespace(cartesian_state=lambda t: Array(body_state(b,t))),
            ),
        ),
    )

    def build_model(model: str, check: Callable[[], None]) -> Any:
        assert model == "B"
        check()
        return prepared

    def propagate(handle: Any, start: tuple[float, ...], epoch: float, length: float, step: float,
                  offsets: tuple[float, ...], context: Any,
                  guard: Callable[[float, tuple[float, ...]], None]) -> Row:
        assert handle is prepared and epoch == t0 and length == 600.
        launched.append((length,step))
        guard(epoch, start)
        context.arcs_attempted += 1
        states, forces = {}, {}
        for index in range(round(length/step)+1):
            s, t = index*step, t0+index*step
            cur = expected(s)
            cols = []
            for body, gm in source.items():
                d = [p-q for p, q in zip(body_state(body,t)[:3], cur[:3], strict=True)]
                denom = math.hypot(*d)**3
                cols.append([gm*x/denom for x in d])
            states[t] = Array(cur)
            forces[t] = Array([math.fsum(c) for c in zip(*cols, strict=True)] + sum(cols, []))
        raw = {"state_history": states, "dependent_variable_history": forces, "integration_completed": True}
        context.arcs_returned += 1
        context.last_returned = raw
        result = adapter.validate_history(raw, start, epoch, length, step, offsets, handle.included,
                                          context.check, guard)
        context.arcs_completed += 1
        return result

    adapter.build_model = build_model
    adapter.propagate = propagate
    return bundle, adapter, launched


def run(path: Path, bundle: Row, adapter: ModuleType, **kwargs: Any) -> Row:
    return study.execute(path, inputs_loader=lambda root, check: deepcopy(bundle),
                         identity_provider=lambda: bundle["historical_identity"],
                         provider=artificial_state, native_adapter=adapter, **kwargs)


@pytest.fixture(scope="module")
def complete(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Row, Row]:
    bundle, adapter, launched = fixture()
    path = tmp_path_factory.mktemp("r539")/"study.json"
    report = run(path, bundle, adapter)
    assert report["status"] == "passed", report.get("error")
    assert launched == [(600.,1.),(600.,.5)]
    return path, report, bundle


def test_two_600_s_synthetic_profiles_and_independent_saved_audit(complete: tuple[Path, Row, Row],
                                                               tmp_path: Path) -> None:
    path, report, bundle = complete
    assert report["model_a_propagations"] == 0 and not report["scientific_verified"]
    assert len(report["comparisons"]) == 67 and len(report["observations"]) == 52
    end = report["profiles"][-1]["outputs"][-1]
    assert end["elapsed_s"] == 600 and [p["solver_state"]["t_s"] for p in report["profiles"]] == [600.,600.]
    omega = math.sqrt(2e-6)
    expected_z_m = 1e-6/omega**2*(1-math.cos(600*omega))
    expected_vz_m_s = 1e-6/omega*math.sin(600*omega)
    assert end["motion"]["position_m"][2] == pytest.approx(expected_z_m, abs=2e-6)
    assert end["motion"]["velocity_m_s"][2] == pytest.approx(expected_vz_m_s, abs=1e-8)
    assert report["counts"]["native_guard_reads"]["completed"] == 5412
    assert report["counts"]["native_reference_fields"]["completed"] == 156
    assert report["counts"]["reference_fields"]["completed"] == 1248
    assert report["comparison_summary"]["native_tighter"]["extension"]["position_norm_m"] < .01
    assert report["comparison_summary"]["prefix_native_tighter"]["extension"] is None
    auditor, reference, native = (load(x) for x in ("audit", "reference", "native-replay"))
    saved = tmp_path/"audit.json"
    audit = auditor.audit(path, saved, inputs_loader=lambda root, check: deepcopy(bundle),
                          references=reference, native=native)
    assert audit["audit_status"] == "passed", audit.get("error")
    assert audit["checks"]["comparisons"] == 67
    assert audit["checks"]["observations"] == 52
    assert audit["checks"]["native_telemetry"] == 26
    assert audit["adapter_mode"] == "injected-test" and not audit["scientific_verified"]
    assert [audit[k] for k in ("native_calls","scientific_imports","kernel_loads","spacecraft_propagations")] == [0]*4
    with pytest.raises(ValueError, match="exclusive"):
        auditor.audit(path, saved, inputs_loader=lambda root, check: deepcopy(bundle), references=reference, native=native)


@pytest.mark.parametrize("fault", ["vector","trial","force","counter","initial","identity"])
def test_saved_audit_rejects_tampering(complete: tuple[Path, Row, Row], fault: str) -> None:
    path, _, bundle = complete
    data = json.loads(path.read_bytes())
    if fault == "vector":
        data["comparisons"][-1]["difference"]["vector"][0] = .01
    elif fault == "trial":
        data["observations"][-1]["trial_index"] = -1
    elif fault == "force":
        rows = [r for r in data["rhs"] if r["elapsed_s"] > 500]
        rows[-1]["geometry"]["Earth"]["acceleration_m_s2"][2] *= -1
    elif fault == "counter":
        data["counts"]["states"]["completed"] -= 1
    elif fault == "initial":
        data["inputs"]["initial"]["position_m"][0] += 1.
    else:
        data["identities"]["after"]["versions"]["unexpected"] = "tampered"
    auditor, reference, native = (load(n) for n in ("audit", "reference", "native-replay"))
    with pytest.raises(ValueError):
        auditor.check_saved(data, bundle, reference, native)


def test_window_selection_uses_ordinal_not_time_and_refuses_missing_bin() -> None:
    times = [0.,.1,.2,.3,.4,.5,.6,300.,350.,345.,350.,398.,351.,450.,500.,550.,600.]
    rows = [{"profile":"normal", "index":j, "global_index":j, "elapsed_s":s,
             "lo_s":1e-9 if j == 2 else 0., "completed":True} for j,s in enumerate(times)]
    report = {"rhs": rows, "trials": [{"index":0,"rhs_start":8,"rhs_end":11,"accepted":False}]}
    profile = {"name":"normal","outputs":[{"index":j} for j in range(13)]}
    pick = study.select_samples(profile, report)
    assert [(r["index"], owner) for _,r,owner in pick[-6:]] == [
        (8,0),(11,None),(13,None),(14,None),(15,None),(16,None)]
    rows[-1]["completed"] = False
    with pytest.raises(ValueError, match=r"missing RHS extension interval \(550,600\]"):
        study.select_samples(profile, report)


def test_prefix_gate_fails_before_tighter_or_adaptive_and_preserves_report(tmp_path: Path) -> None:
    bundle, adapter, launched = fixture()
    bundle["b_prefix"]["native"]["normal"][1][2] += .0101
    path = tmp_path/"failed.json"
    report = run(path, bundle, adapter)
    assert report["status"] == "failed" and report["error"]["stage"] == "native-prefix-normal"
    assert launched == [(600.,1.)] and not report["profiles"] and not report["state_requests"]
    assert report["comparisons"][-1]["assessment"]["passed"] is False
    assert json.loads(path.read_bytes())["error"] == report["error"]
    with pytest.raises(ValueError, match="exclusive"):
        run(path, bundle, adapter)


def test_startup_deadline_counts_no_work_and_injection_is_explicit(tmp_path: Path) -> None:
    bundle, adapter, launched = fixture()
    failed = run(tmp_path/"late.json", bundle, adapter, started_s=0., clock=lambda:60.)
    assert failed["status"] == "failed" and failed["finalization_gate"] == "failed"
    assert not failed["counts"] and not launched
    with pytest.raises(ValueError, match="injected mode requires all"):
        study.execute(tmp_path/"missing.json", clock=lambda:0.)
    with pytest.raises(ValueError, match="external launcher"):
        study.execute(tmp_path/"not-authorized.json")


def test_saved_b_loads_only_metadata_and_detects_hash_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = load("inputs")
    bundle = inputs.load_inputs(ROOT)
    assert len(bundle["offsets_s"]) == 13 and bundle["offsets_s"][-1] == 600
    assert set(bundle["b_prefix"]) == {"native","dop853"} and "a_samples" not in bundle
    assert bundle["b_prefix"]["native"]["normal"][0] == bundle["b_prefix"]["dop853"]["tighter"][0]
    monkeypatch.setattr(inputs, "DESIGN_SHA", "0"*64)
    with pytest.raises(ValueError, match="SHA256"):
        inputs.load_inputs(ROOT)


@pytest.mark.parametrize("tampered", [False, True])
def test_mock_parent_watchdog_and_receipt_binding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                 tampered: bool) -> None:
    launcher = load("launch")
    checkout = tmp_path/"repo"
    child = checkout/"docs/adr/experiments/0186-long-b-study.py"
    child.parent.mkdir(parents=True)
    child.write_bytes(b"never executed, mocked below")
    manifest = child.with_name("0186-verification.json")
    manifest.write_text(json.dumps({
        "preparation_complete":True, "design_input_sha256":{},
        "tested_source_sha256":{str(child.relative_to(checkout)):sha256(child.read_bytes()).hexdigest()}
    }))
    evidence = tmp_path/"evidence"
    evidence.mkdir()
    for key,value in (("ROOT",checkout),("HERE",child.parent),("MANIFEST",manifest),
                      ("snapshot",lambda:{}),
                      ("git",lambda *args: {("branch","--show-current"):b"dev\n",
                                               ("status","--porcelain"):b""}.get(args,b"e"*40+b"\n"))):
        monkeypatch.setattr(launcher,key,value)
    ticks = iter([5.,6.,7.,8.,9.,10.])
    monkeypatch.setattr(launcher,"monotonic", lambda:next(ticks))
    invoked = []

    def fake_child(command: list[str], watchdog_s: float) -> Row:
        assert watchdog_s == 58. and float(command[-5]) == 5.
        invoked.append(command)
        out = evidence/"study.json"
        out.write_bytes(b'{"model":"B"}')
        out.with_suffix(".attempt.json").write_text("{}")
        out.with_suffix(".receipt.json").write_text(json.dumps({
            "status":"passed","started_s":5.,"elapsed_s":1.,"finalization_gate":"passed",
            "evidence_sha256":"0"*64 if tampered else sha256(out.read_bytes()).hexdigest(),
        }))
        return {"returncode":0,"stderr":""}

    monkeypatch.setattr(launcher,"run_child",fake_child)
    pin = sha256(manifest.read_bytes()).hexdigest()
    parent = launcher.launch("study",evidence,pin)
    assert parent["contract"] == "ADR0185" and parent["finalization_gate"] == ("failed" if tampered else "passed")
    with pytest.raises(ValueError,match="once-only"):
        launcher.launch("study",evidence,pin)
    assert len(invoked) == 1
