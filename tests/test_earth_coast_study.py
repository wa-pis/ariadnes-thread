"""Exercise the full B study and its separate audit with analytic source data."""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
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


def module(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location("test_r536_" + name, ART/f"0183-earth-{name}.py")
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


study = module("study")


def fixture() -> tuple[Row, ModuleType]:
    bundle = artificial_bundle()
    # Synthetic Earth is distant but observable in an independent direct field.
    # Its small trajectory effect leaves generous margins for a closed-form native stub.
    bundle["gm_m3_s2"]["Earth"] = 1e13
    source = bundle["gm_m3_s2"]
    initial = bundle["initial"]
    t0 = initial["epoch_tdb_s"]
    omega = initial["velocity_m_s"][1] / initial["position_m"][0]
    bundle["a_samples"] = {"native": deepcopy(bundle["native_samples"]["tighter"]),
                           "dop853": deepcopy(bundle["native_samples"]["tighter"])}
    adapter = module("native").load_adapter()
    adapter.GM = source
    adapter.GUARDS = bundle["radii_m"]

    def state(b: str, t: float) -> list[float]:
        return [x * 1000 for x in artificial_state(b, t, "J2000", "NONE", "SSB")]

    prepared = SimpleNamespace(
        included=("Sun", "Moon", "Earth"),
        gravity_parameters_m3_s2=source,
        accelerations={"Spacecraft": {body: [object()] for body in source}},
        bodies=SimpleNamespace(
            global_frame_origin=lambda: "SSB",
            global_frame_orientation=lambda: "J2000",
            get=lambda b: SimpleNamespace(
                gravity_field_model=SimpleNamespace(gravitational_parameter=source[b]),
                ephemeris=SimpleNamespace(cartesian_state=lambda t: Array(state(b, t))),
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
        assert handle is prepared and epoch == t0 and length == 300.
        guard(epoch, start)
        context.arcs_attempted += 1
        states, forces = {}, {}
        for index in range(round(length / step) + 1):
            s = index*step
            t = t0+s
            x, y = 1e6*math.cos(omega*s), 1e6*math.sin(omega*s)
            # Linear vertical response (z'' + omega² z = az) for this fixture.
            az = source["Earth"]/1e18
            z = az/omega**2 * (1-math.cos(omega*s))
            vz = az/omega * math.sin(omega*s)
            cur = [x, y, z, -omega*y, omega*x, vz] if index else list(start)
            cols = []
            for body, gm in source.items():
                d = [p-q for p, q in zip(state(body,t)[:3], cur[:3], strict=True)]
                denom = sum(z*z for z in d)**1.5
                cols.append([gm*z/denom for z in d])
            states[t] = Array(cur)
            forces[t] = Array([math.fsum(c) for c in zip(*cols, strict=True)] + sum(cols, []))
        raw = {"state_history": states, "dependent_variable_history": forces, "integration_completed": True}
        context.arcs_returned += 1
        context.last_returned = raw
        res = adapter.validate_history(raw, start, epoch, length, step, offsets, handle.included, context.check, guard)
        context.arcs_completed += 1
        return res

    adapter.build_model = build_model
    adapter.propagate = propagate
    return bundle, adapter


def run_fixture(path: Path, bundle: Row, adapter: ModuleType, **kwargs: Any) -> Row:
    return study.execute(path, inputs_loader=lambda root, check: deepcopy(bundle),
                         identity_provider=lambda: bundle["historical_identity"],
                         provider=artificial_state, native_adapter=adapter, **kwargs)


def test_complete_synthetic_b_study_and_audit(tmp_path: Path) -> None:
    bundle, adapter = fixture()
    path = tmp_path/"study.json"
    report = run_fixture(path, bundle, adapter)
    assert report["status"] == "passed", report.get("error")
    assert report["adapter_mode"] == "injected-test" and report["scientific_verified"] is False
    assert len(report["observations"]) == 28
    assert len(report["comparisons"]) == 21 and len(report["effects"]) == 7
    assert report["effects"][-1]["position_above_scale"]
    limit_omega = math.sqrt(2e-6)
    expected_z = 1e-5/limit_omega**2 * (1-math.cos(300*limit_omega))
    assert report["effects"][-1]["dop853"]["vector"][2] == pytest.approx(expected_z, abs=7e-5)
    assert report["counts"]["native_guard_reads"]["completed"] == 2712
    assert report["counts"]["native_reference_fields"]["completed"] == 84
    assert report["counts"]["reference_fields"]["completed"] == 672
    audit = module("audit")
    checked = audit.audit(path, tmp_path/"audit.json", inputs_loader=lambda root, check: deepcopy(bundle),
                          references=module("reference"), native=module("native-replay"))
    assert checked["audit_status"] == "passed", checked.get("error")
    assert not checked["scientific_verified"]
    assert checked["native_calls"] == 0 and checked["spacecraft_propagations"] == 0
    tampered = json.loads(path.read_bytes())
    tampered["effects"][-1]["dop853"]["vector"][2] *= -1
    with pytest.raises(ValueError, match="effect|rounded|difference|component|subtraction"):
        audit.check_saved(tampered, bundle, module("reference"), module("native-replay"))
    with pytest.raises(ValueError, match="exclusive"):
        run_fixture(path, bundle, adapter)


@pytest.mark.parametrize("delta, passed", [(0.02, True), (math.nextafter(.02, math.inf), False)])
def test_signed_gate_boundary(delta: float, passed: bool) -> None:
    zero = [0.]*6
    row = study.effect(1, 1., zero, zero, zero, [delta,*zero[1:]])
    assert row["passed"] is passed


def test_equal_norm_opposite_directions_are_a_failure() -> None:
    zero = [0.]*6
    effect = study.effect(1, 1., zero, [.015,*zero[1:]], zero, [-.015,*zero[1:]])
    assert effect["native"]["position_norm_m"] == effect["dop853"]["position_norm_m"]
    assert effect["discrepancy"]["position_norm_m"] == .03
    assert not effect["passed"]
    assert not study.effect(0, 0., zero, [1e-9,*zero[1:]], zero, zero)["passed"]


def test_startup_deadline_and_missing_injections_do_not_use_reference(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires all"):
        study.execute(tmp_path/"not-started.json", clock=lambda: 0.)
    bundle, adapter = fixture()
    path = tmp_path/"partial.json"
    row = run_fixture(path, bundle, adapter, started_s=0., clock=lambda: 60.)
    assert row["status"] == "failed" and row["finalization_gate"] == "failed"
    assert not row["native_profiles"] and not row["state_requests"]
    marker = json.loads(path.with_suffix(".attempt.json").read_bytes())
    assert marker["adapter_mode"] == "injected-test"


def test_saved_a_baselines_validate_without_physics() -> None:
    bundle = module("inputs").load_inputs(ROOT)
    assert bundle["offsets_s"] == [0.,50.,100.,150.,200.,250.,300.]
    assert len(bundle["a_samples"]["native"]) == len(bundle["a_samples"]["dop853"]) == 7
    assert bundle["a_samples"]["native"][0] == bundle["a_samples"]["dop853"][0]
    assert bundle["historical_final_identity_available"] is False


@pytest.mark.parametrize("tamper", [False, True])
def test_parent_replay_and_exclusive_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: bool) -> None:
    launch = module("launch")
    from hashlib import sha256

    checkout = tmp_path/"workspace"
    helper = checkout/"docs/adr/experiments/0183-earth-study.py"
    helper.parent.mkdir(parents=True)
    helper.write_bytes(b"this is a mock program, not executable Python")
    manifest = helper.with_name("0183-verification.json")
    manifest.write_text(json.dumps(
        {"preparation_complete": True, "design_input_sha256": {},
         "tested_source_sha256": {str(helper.relative_to(checkout)): sha256(helper.read_bytes()).hexdigest()}}))
    stated = sha256(manifest.read_bytes()).hexdigest()
    evidence = tmp_path/"outside"
    evidence.mkdir()
    monkeypatch.setattr(launch, "ROOT", checkout)
    monkeypatch.setattr(launch, "HERE", helper.parent)
    monkeypatch.setattr(launch, "MANIFEST", manifest)
    monkeypatch.setattr(launch, "git", lambda *args: {
        ("branch", "--show-current"): b"dev\n", ("status", "--porcelain"): b"",
    }.get(args, b"f"*40+b"\n"))
    monkeypatch.setattr(launch, "snapshot", lambda: {})
    invoked = []

    def fake_child(command: list[str], watchdog_s: float) -> Row:
        invoked.append(command)
        assert watchdog_s == 65.
        raw = b'{"test":true}'
        output = evidence/"study.json"
        output.write_bytes(raw)
        output.with_suffix(".attempt.json").write_text("{}")
        output.with_suffix(".receipt.json").write_text(json.dumps({
            "status": "passed", "finalization_gate": "passed", "elapsed_s": 0.,
            "started_s": float(command[-5]), "evidence_sha256": "0"*64 if tamper else sha256(raw).hexdigest()}))
        return {"returncode": 0, "stderr": ""}

    monkeypatch.setattr(launch, "run_child", fake_child)
    result = launch.launch("study", evidence, stated)
    assert result["finalization_gate"] == ("failed" if tamper else "passed")
    assert result["checkout_frozen"]
    with pytest.raises(ValueError, match="once-only"):
        launch.launch("study", evidence, stated)
    assert len(invoked) == 1
