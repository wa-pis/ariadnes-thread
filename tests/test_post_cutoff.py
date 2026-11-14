"""Exercise the cutoff restart with synthetic source states and native histories."""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from decimal import Decimal, localcontext
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from test_earth_coast_native import Array
from test_split_coast_study import artificial_bundle, artificial_state

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/adr/experiments"
type Row = dict[str, Any]


def load(role: str, stem: str = "0189-post-cutoff") -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"test_{stem}_{role}", ART / f"{stem}-{role}.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


study = load("study")


def fixture(speed: float, *, bad_telemetry: bool = False) -> tuple[Row, ModuleType, list[float]]:
    bundle = artificial_bundle()
    t0 = bundle["initial"]["epoch_tdb_s"] + 4096.
    bundle["initial"] = {"epoch_tdb_s": t0, "position_m": [1e6, 0., 0.], "velocity_m_s": [speed, 0., 0.]}
    bundle["offsets_s"] = list(range(0, 601, 50))
    for source in bundle["source_rows_template"].values():
        for record in source["segments"]:
            record.update(first_tdb_s=t0-1024, last_tdb_s=t0+1024)
            record["words"][:2] = [t0, 1024.]
    bundle["gm_m3_s2"] = gm = {"Sun": 1e3, "Moon": 1e3, "Earth": 1e5}
    bundle["cutoff"] = {"label": "departure-cutoff", "origin": "SSB", "orientation": "J2000",
                        **bundle["initial"]}
    span = 2860.75
    with localcontext() as ctx:
        ctx.prec = 80
        consumed = Decimal(1000)*Decimal(span)/(Decimal("9.80665")*450)
        prediction = Decimal(2000)-consumed
        bundle["mass_kg"] = mass = float(prediction)
        bundle["mass_arithmetic"] = {
            "g0_m_s2": "9.80665", "dry_mass_kg": 500., "requested_duration_s": span,
            "represented_duration_s": str(Decimal(span)), "predicted_mass_kg": str(prediction),
            "predicted_minus_stored_mass_kg": str(prediction-Decimal.from_float(mass)),
            "limit_kg": str(max(Decimal("1e-8"),Decimal("1e-11")*consumed)),
        }
    bundle["burn"] = {"burn_id": "departure", "start_epoch_tdb_s": t0-span, "end_epoch_tdb_s": t0,
                      "initial_mass_kg": 2000., "final_mass_kg": mass, "thrust_n": 1000., "isp_s": 450.}
    bundle["coast"] = {"constant_mass_metadata_kg": mass, "thrust_n": 0., "mass_flow_kg_s": 0.}
    bundle["b_runtime"] = bundle["historical_identity"]
    bundle["b_archive_sha256"] = "a"*64
    bundle.pop("native_samples")
    native = load("native", "0186-long-b").load_adapter()
    native.GM, native.GUARDS = gm, bundle["radii_m"]
    launched: list[float] = []

    def body_si(body: str, epoch: float) -> list[float]:
        return [x*1000. for x in artificial_state(body, epoch, "J2000", "NONE", "SSB")]

    prepared = SimpleNamespace(
        included=tuple(gm), gravity_parameters_m3_s2=gm,
        accelerations={"Spacecraft": {b: [object()] for b in gm}},
        bodies=SimpleNamespace(global_frame_origin=lambda: "SSB", global_frame_orientation=lambda: "J2000",
                               get=lambda b: SimpleNamespace(gravity_field_model=SimpleNamespace(
                                   gravitational_parameter=gm[b]), ephemeris=SimpleNamespace(
                                   cartesian_state=lambda at: Array(body_si(b, at))))),
    )

    def build_model(model: str, check: Callable[[], None]) -> Any:
        assert model == "B"
        check()
        return prepared

    def propagate(handle: Any, initial: tuple[float, ...], epoch: float, length: float, step: float,
                  offsets: tuple[float, ...], context: Any,
                  guard: Callable[[float, tuple[float, ...]], None]) -> Row:
        assert handle is prepared and epoch == t0 and length == 600.
        assert initial == (1e6, 0., 0., speed, 0., 0.)
        launched.append(step)
        guard(epoch, initial)
        context.arcs_attempted += 1
        states, forces = {}, {}
        for j in range(round(length/step)+1):
            elapsed = j*step
            t = t0+elapsed
            # Unperturbed straight line; the artificial fields are weak enough
            # for this reference approximation to meet the profile gates.
            cur = [1e6 + speed*elapsed, 0., 0., speed, 0., 0.]
            per_source = []
            for body, mu in gm.items():
                d = [p-q for p, q in zip(body_si(body, t)[:3], cur[:3], strict=True)]
                per_source.append([mu*x/math.hypot(*d)**3 for x in d])
            states[t] = Array(cur)
            force = [math.fsum(c) for c in zip(*per_source, strict=True)] + sum(per_source, [])
            if bad_telemetry and j == 0:
                force[0] += .001
                force[3] += .001
            forces[t] = Array(force)
        raw = {"state_history": states, "dependent_variable_history": forces, "integration_completed": True}
        context.arcs_returned += 1
        context.last_returned = raw
        completed = native.validate_history(raw, initial, epoch, length, step, offsets,
                                            handle.included, context.check, guard)
        context.arcs_completed += 1
        return completed

    native.build_model, native.propagate = build_model, propagate
    return bundle, native, launched


def run(path: Path, bundle: Row, native: ModuleType, **kwargs: Any) -> Row:
    return study.execute(path, inputs_loader=lambda r,c: deepcopy(bundle),
                         identity_provider=lambda: bundle["historical_identity"],
                         provider=artificial_state, native_adapter=native, **kwargs)


def inherited_audit() -> tuple[ModuleType, ModuleType, ModuleType]:
    return (load("audit"), load("reference", "0186-long-b"), load("native-replay", "0186-long-b"))


@pytest.fixture(scope="module")
def outward(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Row, Row]:
    path = tmp_path_factory.mktemp("r542-outward") / "study.json"
    bundle, native, launched = fixture(100.)
    report = run(path, bundle, native)
    assert report["status"] == "passed", report.get("error")
    assert launched == [1., .5]
    return path, report, bundle


def test_synthetic_b_study_and_saved_audit(outward: tuple[Path, Row, Row], tmp_path: Path) -> None:
    path, report, bundle = outward
    assert report["model_a_propagations"] == 0 and report["outward_status"] == "unavailable"
    assert not report["scientific_verified"] and not report["mission_accuracy_verified"]
    assert len(report["comparisons"]) == 39 and len(report["observations"]) == 52
    assert report["counts"]["native_guard_reads"]["completed"] == 5412
    assert report["counts"]["native_telemetry"]["completed"] == 26
    assert len(report["direction"]["rows"]) == 52
    assert report["direction"]["classification"] == "outbound-at-samples"
    assert all(r["net_range_change_m"] == pytest.approx(60e3, abs=.001) for r in report["direction"]["net_ranges"])
    assert report["coast_mass_kg"] == bundle["mass_kg"]
    assert all(p["coast_mass_kg"] == bundle["mass_kg"] for p in report["native_profiles"]+report["profiles"])
    audit, references, native = inherited_audit()
    result = audit.audit(path, path.with_name("audit.json"), inputs_loader=lambda r,c: deepcopy(bundle),
                         references=references, native=native)
    assert result["audit_status"] == result["finalization_gate"] == "passed", result.get("error")
    assert result["outward_status"] == "outbound-at-samples"
    assert all(result[k] == 0 for k in ("native_calls","scientific_imports","kernel_loads","spacecraft_propagations"))
    with pytest.raises(ValueError, match="exclusive"):
        audit.audit(path, path.with_name("audit.json"), inputs_loader=lambda r,c: deepcopy(bundle),
                    references=references, native=native)
    with pytest.raises(ValueError, match="exclusive"):
        study.execute(path, inputs_loader=lambda r,c: bundle, identity_provider=dict,
                      provider=artificial_state, native_adapter=native)
    bad = audit.audit(path, tmp_path/"late-audit.json", started_s=0., clock=lambda:10.00001,
                      inputs_loader=lambda r,c: bundle, references=references, native=native)
    assert bad["audit_status"] != "passed" and bad["finalization_gate"] == "failed"
    assert bad["outward_status"] == "unavailable"


def test_inward_motion_does_not_fail_numerical_acceptance(tmp_path: Path) -> None:
    path = tmp_path/"study.json"
    bundle, adapter, _ = fixture(-100.)
    report = run(path, bundle, adapter)
    assert report["status"] == "passed", report.get("error")
    assert report["direction"]["classification"] == "outbound-not-established"
    audit, references, native = inherited_audit()
    result = audit.audit(path, tmp_path/"audit.json", inputs_loader=lambda r,c: deepcopy(bundle),
                         references=references, native=native)
    assert result["audit_status"] == "passed", result.get("error")
    assert result["outward_status"] == "outbound-not-established"


@pytest.mark.parametrize("issue", ["speed","direction","mass","profile_mass","shifted_start","parking_prefix"])
def test_independent_audit_rejects_corruption(
    outward: tuple[Path, Row, Row], issue: str,
) -> None:
    path, _, bundle = outward
    data = json.loads(path.read_bytes())
    if issue == "speed":
        data["direction"]["rows"][0]["radial_speed_m_s"] += .01
    elif issue == "direction":
        data["direction"]["classification"] = "outbound-not-established"
    elif issue == "mass":
        data["coast_mass_kg"] += 1.
    elif issue == "profile_mass":
        data["native_profiles"][1]["coast_mass_kg"] += 1.
    elif issue == "shifted_start":
        data["inputs"]["initial"]["epoch_tdb_s"] += .5
    else:
        data["comparisons"][0]["name"] = "prefix_native_normal"
    audit, references, native = inherited_audit()
    with pytest.raises(ValueError):
        audit.check_saved(data, bundle, references, native)


def test_invalid_handoff_and_deadline_stop_before_native_work(tmp_path: Path) -> None:
    bundle, native, launched = fixture(100.)
    late = run(tmp_path/"late-study.json", bundle, native, started_s=0., clock=lambda:60.)
    assert late["status"] == late["finalization_gate"] == "failed" and not launched
    bundle["cutoff"]["label"] = "departure-ignition"
    invalid = run(tmp_path/"invalid-study.json", bundle, native)
    assert invalid["status"] == "failed" and invalid["outward_status"] == "unavailable" and not launched
    assert "handoff" in invalid["error"]["message"]
    with pytest.raises(ValueError, match="external launcher"):
        study.execute(tmp_path/"not-authorized.json")
    with pytest.raises(ValueError, match="synthetic adapters"):
        study.execute(tmp_path/"mixed-adapters.json", provider=artificial_state)


@pytest.mark.parametrize("exit_mode", ["passed", "corrupt-receipt", "watchdog"])
def test_parent_watchdog_and_receipts_without_launching_a_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_mode: str,
) -> None:
    launch = load("launch")
    checkout = tmp_path/"checkout"
    helpers = checkout/"docs/adr/experiments"
    helpers.mkdir(parents=True)
    child, prepare = (helpers/f"0189-post-cutoff-{name}.py" for name in ("study","prepare"))
    child.write_text("raise RuntimeError('child must be mocked')")
    child_digest = sha256(child.read_bytes()).hexdigest()
    prepare.write_text(f"def verify(root, expected, check):\n    check()\n    return {{{str(child.relative_to(checkout))!r}: {child_digest!r}}}\n")
    manifest = helpers/"0189-verification.json"
    manifest.write_text(json.dumps({
        "preparation_complete": True,
        "tested_source_sha256": {str(prepare.relative_to(checkout)): sha256(prepare.read_bytes()).hexdigest()},
    }))
    directory = tmp_path/"evidence"
    directory.mkdir()
    for key,value in (("ROOT",checkout),("HERE",helpers),("MANIFEST",manifest),("PREPARE",prepare),
                      ("snapshot",lambda:{}),
                      ("git",lambda *args: {("branch","--show-current"):b"dev\n",
                                            ("status","--porcelain"):b""}.get(args,b"e"*40+b"\n"))):
        monkeypatch.setattr(launch,key,value)
    ticks = iter(float(x) for x in range(5,120))
    monkeypatch.setattr(launch,"monotonic",lambda:next(ticks))
    commands = []
    def mocked_run(command: list[str], watchdog_s: float) -> Row:
        assert 0 < watchdog_s < 60. and float(command[-5]) == 5.
        commands.append(command)
        if exit_mode == "watchdog":
            def timeout(*args: Any, **kwargs: Any) -> Row:
                raise subprocess.TimeoutExpired(command, watchdog_s)
            monkeypatch.setattr(launch.subprocess, "run", timeout)
            return original(command, watchdog_s)
        output = directory/"study.json"
        output.write_text('{"model":"B"}')
        output.with_suffix(".attempt.json").write_text("{}")
        output.with_suffix(".receipt.json").write_text(json.dumps({
            "status": "passed", "started_s": 5., "elapsed_s": 1., "finalization_gate": "passed",
            "evidence_sha256": sha256(output.read_bytes()).hexdigest() if exit_mode == "passed" else "0"*64,
        }))
        return {"returncode":0,"stderr":""}

    original = launch.run_child
    monkeypatch.setattr(launch,"run_child",mocked_run)
    pin = sha256(manifest.read_bytes()).hexdigest()
    parent = launch.launch("study",directory,pin)
    assert parent["contract"] == "ADR0188"
    assert parent["finalization_gate"] == ("passed" if exit_mode == "passed" else "failed")
    with pytest.raises(ValueError,match="once-only"):
        launch.launch("study",directory,pin)
    assert len(commands) == 1


def test_native_telemetry_failure_is_independently_audited_without_later_work(tmp_path: Path) -> None:
    path = tmp_path/"study.json"
    bundle, adapter, launched = fixture(100., bad_telemetry=True)
    report = run(path, bundle, adapter)
    assert report["status"] == "failed" and report["error"]["type"] == "TelemetryFailure"
    assert report["error"]["stage"] == "native-normal" and launched == [1.]
    assert not report["profiles"] and not report["state_requests"]
    audit, references, native = inherited_audit()
    received = audit.audit(path, tmp_path/"audit.json", inputs_loader=lambda r,c: deepcopy(bundle),
                           references=references, native=native)
    assert received["audit_status"] == "partial", received.get("error")
    assert received["outward_status"] == "unavailable" and not received["checks"]["passed"]


def test_preparation_requires_all_sources_and_actual_frozen_bytes(tmp_path: Path) -> None:
    prepare = load("prepare")
    old = json.loads((ROOT/prepare.R539).read_bytes())
    design = json.loads((ROOT/prepare.DESIGN).read_bytes())
    guards = (prepare.SCRIPTS + prepare.TESTS + (prepare.GUARD,))
    pins = design["immutable_input_sha256"] | old["design_input_sha256"]
    pins[str(prepare.DESIGN)] = sha256((ROOT/prepare.DESIGN).read_bytes()).hexdigest()
    tested = old["tested_source_sha256"] | {str(p):sha256((ROOT/p).read_bytes()).hexdigest() for p in guards}
    for name in pins.keys() | tested.keys():
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(ROOT/name)
    manifest = tmp_path/prepare.PREPARATION
    data = {"stage":"R5.42","contract":"ADR0188","preparation_complete":True,
            "design_input_sha256":pins,"tested_source_sha256":tested}

    def store() -> str:
        raw = json.dumps(data).encode()
        manifest.write_bytes(raw)
        return sha256(raw).hexdigest()

    assert prepare.verify(tmp_path, store(), lambda:None) == tested
    tested.pop(str(prepare.SCRIPTS[-1]))
    with pytest.raises(ValueError, match="incomplete preparation"):
        prepare.verify(tmp_path, store(), lambda:None)


def test_stdlib_only_audit_replays_saved_artificial_bytes(
    outward: tuple[Path, Row, Row], tmp_path: Path,
) -> None:
    path, _, bundle = outward
    inputs = tmp_path/"inputs.json"
    inputs.write_text(json.dumps(bundle, allow_nan=False))
    output = tmp_path/"independent.json"
    command = """
import json
from pathlib import Path
import runpy
import sys
root, saved, inputs, output = map(Path, sys.argv[1:])
art = root/"docs/adr/experiments"
from types import SimpleNamespace
def load(name):
    return SimpleNamespace(**runpy.run_path(str(art/name)))
audit = load("0189-post-cutoff-audit.py")
ref = load("0186-long-b-reference.py")
native = load("0186-long-b-native-replay.py")
bundle = json.loads(inputs.read_bytes())
report = audit.audit(saved, output, root=root, inputs_loader=lambda *_: bundle,
                     references=ref, native=native)
assert report["audit_status"] == report["finalization_gate"] == "passed", report.get("error")
assert report["outward_status"] == "outbound-at-samples"
assert not {x.split(".")[0] for x in sys.modules} & {"space_nav","numpy","scipy","tudatpy","spiceypy"}
"""
    done = subprocess.run([sys.executable,"-I","-S","-B","-c",command,str(ROOT),str(path),
                           str(inputs),str(output)], capture_output=True,text=True,check=False,timeout=12)
    assert done.returncode == 0, done.stderr
    report = json.loads(output.read_bytes())
    receipt = json.loads(output.with_suffix(".receipt.json").read_bytes())
    assert receipt["evidence_sha256"] == sha256(output.read_bytes()).hexdigest()
    assert report["checks"]["direction_rows"] == 52 and report["checks"]["net_range_signs"] == 4


def test_study_receipt_chain_validates_subject_and_digest(tmp_path: Path) -> None:
    audit, _, _ = inherited_audit()
    path = tmp_path/"study.json"
    subject = {"status":"passed","finalization_gate":"passed","preparation_manifest_sha256":"a"*64,
               "elapsed_before_flush_s":2.,"identities":{"before":{"revision":"d"*40}}}

    def write(target: Path, value: Row) -> str:
        raw = json.dumps(value, allow_nan=False).encode()
        target.write_bytes(raw)
        return sha256(raw).hexdigest()

    raw = json.dumps(subject).encode()
    path.write_bytes(raw)
    report_hash = sha256(raw).hexdigest()
    attempt = write(path.with_suffix(".attempt.json"), {"contract":"ADR0188","adapter_mode":"reference",
                                                        "started_s":5.})
    child = write(path.with_suffix(".receipt.json"), {"status":"passed","finalization_gate":"passed",
                                                      "started_s":5.,"elapsed_s":2.5,
                                                      "evidence_sha256":report_hash})
    parent_marker = {"contract":"ADR0188","phase":"study","revision":"d"*40,"preparation_sha256":"a"*64}
    parent_attempt = write(path.with_suffix(".parent-attempt.json"), parent_marker)
    parent = parent_marker | {"evidence_sha256":report_hash,"parent_attempt_sha256":parent_attempt,
                             "attempt_sha256":attempt,"child_receipt_sha256":child,"started_s":5.,
                             "elapsed_s":3.,"returncode":0,"checkout_frozen":True,
                             "finalization_gate":"passed","stderr":""}
    write(path.with_suffix(".parent-receipt.json"),parent)
    assert len(audit.check_study_receipts(path,subject,raw)) == 4
    parent["evidence_sha256"] = "0"*64
    write(path.with_suffix(".parent-receipt.json"),parent)
    with pytest.raises(ValueError,match="evidence_sha256"):
        audit.check_study_receipts(path,subject,raw)
