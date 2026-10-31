"""Native-free private R2.2 verifier tests with independent analytic states."""

from __future__ import annotations

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
import io
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0128-reference-coast.py"
spec = spec_from_file_location("r2_reference_coast", PATH)
assert spec and spec.loader
r2 = module_from_spec(spec)
sys.modules[spec.name] = r2
spec.loader.exec_module(r2)
REFERENCE = json.loads(r2.REFERENCE.read_text())
A, E = 149597870700.0, 0.2
N = math.sqrt(r2.MU / A**3)
P, Q = (0.36, 0.48, 0.8), (-0.8, 0.6, 0.0)


def analytic(phase: float, direction: int = 1) -> tuple[float, ...]:
    sine, cosine = math.sin(phase), math.cos(phase)
    q = tuple(direction * x for x in Q)
    beta = math.sqrt(1 - E * E)
    return tuple(
        A * (cosine - E) * P[i] + A * beta * sine * q[i] for i in range(3)
    ) + tuple(
        -A * sine * N / (1 - E * cosine) * P[i]
        + A * beta * cosine * N / (1 - E * cosine) * q[i]
        for i in range(3)
    )


def record(state: tuple[float, ...], epoch: float, body: str) -> dict[str, Any]:
    return {
        "body": body,
        "epoch_tdb_s": epoch,
        "epoch_utc": "2031-01-01T00:00:00Z",
        **r2.FRAME,
        "position_m": state[:3],
        "velocity_m_s": state[3:],
    }


def synthetic() -> tuple[dict[str, Any], dict[float, dict[str, Any]], dict[str, Any]]:
    reference = deepcopy(REFERENCE)
    run = reference["runs"][0]
    candidate = run["selected"]
    # Integer epoch grid; independent Newton solver supplies the reference states.
    start, flight = 1000000000.0, 1200.0
    candidate.update(
        departure_epoch_tdb_s=start,
        arrival_epoch_tdb_s=start + flight,
        flight_time_s=flight,
        departure_v_infinity_m_s=[100.0, 200.0, 300.0],
    )
    seed = analytic(0.0)
    ell = r2.derive(seed)
    # Expected states from independent specified eccentric phases, not the verifier.
    # Form epochs from uniform time and solve Kepler by independent Newton updates.
    suns = {}
    states = []
    for k in range(121):
        epoch = start + flight * k / 120
        mean = N * (epoch - start)
        phase = mean
        for _ in range(10):
            phase -= (phase - E * math.sin(phase) - mean) / (1 - E * math.cos(phase))
        relative = analytic(phase)
        sun = (1e8 + k * 100.0, -2e8 + k * 200.0, 3e8 - k * 50.0, 10.0, 20.0, -5.0)
        suns[epoch] = record(sun, epoch, "Sun")
        states.append(
            record(tuple(x + y for x, y in zip(relative, sun)), epoch, "Spacecraft")
        )
    sun0 = suns[start]["position_m"] + suns[start]["velocity_m_s"]
    moon = tuple(seed[i] + sun0[i] for i in range(3)) + tuple(
        seed[i + 3] + sun0[i + 3] - candidate["departure_v_infinity_m_s"][i]
        for i in range(3)
    )
    run["states"] = states
    run["endpoints"]["departure"]["body_state"] = record(moon, start, "Moon")
    run["endpoints"]["arrival"]["body_state"] = record(
        (1.0, 2.0, 3.0, 4.0, 5.0, 6.0), start + flight, "Mars"
    )
    identity = {
        "kernels": deepcopy(reference["provenance"]["manifest"]["spice"]),
        "test_identity": "synthetic",
    }
    assert ell.eccentricity == pytest.approx(E)
    return reference, suns, identity


def invoke(
    reference: dict[str, Any] | None = None, **kwargs: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    ref, suns, identity = synthetic()
    stream = io.StringIO()
    report = r2.run(
        stream,
        reference_loader=lambda: ref if reference is None else reference,
        identity=kwargs.pop("identity", lambda: deepcopy(identity)),
        provider=kwargs.pop("provider", lambda epoch: deepcopy(suns[epoch])),
        **kwargs,
    )
    return report, json.loads(stream.getvalue())


def test_real_reference_offline_identity() -> None:
    assert r2.load_reference()["status"] == "passed"
    r2.self_check()


@pytest.mark.parametrize("direction", [-1, 1])
@pytest.mark.parametrize("initial_phase", [0.0, math.pi / 2, math.pi, -math.pi / 2])
def test_forward_closed_form_and_conservation(
    initial_phase: float, direction: int
) -> None:
    initial = analytic(initial_phase, direction)
    ellipse = r2.derive(initial)
    for advance in (0.3, math.pi, 2 * math.pi):
        target_phase = initial_phase + advance
        dt = (advance - E * (math.sin(target_phase) - math.sin(initial_phase))) / N
        actual = r2.oracle(ellipse, dt)
        expected = analytic(target_phase, direction)
        assert math.dist(actual["state"][:3], expected[:3]) <= 0.01
        assert math.dist(actual["state"][3:], expected[3:]) <= 1e-8
        r2.check_comparison(r2.compare(actual["state"], expected, initial))
        assert actual["bracket_width_rad"] <= 2e-14
        assert actual["residual_rad"] <= 2e-14
        assert actual["updates"] <= 64


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), "1", None])
def test_invalid_numbers(value: object) -> None:
    with pytest.raises(r2.GateFailure):
        r2.number(value)
    with pytest.raises(r2.GateFailure):
        r2.oracle(r2.derive(analytic(0)), value)


@pytest.mark.parametrize(
    "state",
    [
        (),
        (1.0,) * 5,
        (True,) * 6,
        (float("nan"),) * 6,
        (0.0,) * 6,
        (1e11, 0.0, 0.0, 0.0, 0.0, 0.0),
        (1e11, 0.0, 0.0, 0.0, 1e9, 0.0),
        (1e11, 0.0, 0.0, 0.0, math.sqrt(r2.MU / 1e11), 0.0),
    ],
)
def test_bad_seed(state: object) -> None:
    with pytest.raises(r2.GateFailure):
        r2.derive(state)


def test_all_nodes_and_translation() -> None:
    report, written = invoke()
    assert report == written
    assert report["status"] == "passed", report.get("error")
    assert report["attempted_sun_calls"] == report["completed_sun_calls"] == 121
    assert report["native_spacecraft_propagations"] == 0
    assert len(report["points"]) == 121
    assert all(p["status"] == "passed" for p in report["points"])
    assert [e["label"] for e in report["calls"] if e["label"].startswith("Sun ")] == [
        f"Sun {k}" for k in range(121)
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r["runs"][0]["states"].pop(),
        lambda r: r["runs"][0]["states"].reverse(),
        lambda r: r["runs"][0]["states"][1].update(epoch_tdb_s=0.0),
        lambda r: r["runs"][0]["states"][0].update(origin="Sun"),
        lambda r: r["runs"][0]["states"][0].update(orientation="ECLIPJ2000"),
        lambda r: r["runs"][0]["selected"].update(candidate_id="other"),
        lambda r: r["runs"][0]["selected"].update(flight_time_s=-1.0),
        lambda r: r["provenance"]["manifest"]["reference"].update(time="UTC"),
        lambda r: r["provenance"]["manifest"]["reference"].update(position_units="km"),
        lambda r: r["provenance"]["transfer_model"]["gravitational_parameters"][
            "values"
        ].update(Sun=1.0),
        lambda r: r["runs"][0]["provenance"]["normalized_scenario"]["limits"].update(
            random_seed=99
        ),
    ],
)
def test_reference_errors_before_reads(mutation: Any) -> None:
    ref, _, _ = synthetic()
    mutation(ref)
    report, _ = invoke(ref)
    assert report["status"] == "failed"
    assert report["attempted_sun_calls"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("origin", "Sun"),
        ("body", "Mars"),
        ("orientation", "BAD"),
        ("epoch_tdb_s", 0.0),
        ("velocity_m_s", [0.0, True, 0.0]),
        ("position_m", [1.0, 2.0]),
    ],
)
def test_sun_identity_errors(field: str, value: object) -> None:
    _, suns, _ = synthetic()

    def provider(epoch: float) -> dict[str, Any]:
        return deepcopy(suns[epoch]) | {field: value}

    report, _ = invoke(provider=provider)
    assert report["status"] == "failed"
    assert report["attempted_sun_calls"] == report["completed_sun_calls"] == 1
    assert len(report["points"]) == 1


@pytest.mark.parametrize("index", [0, 1, 60, 120])
def test_first_numeric_failure_no_more_queries(index: int) -> None:
    ref, _, _ = synthetic()
    ref["runs"][0]["states"][index]["position_m"] = tuple(
        x + 100.0 for x in ref["runs"][0]["states"][index]["position_m"]
    )
    report, _ = invoke(ref)
    assert report["status"] == "failed"
    assert report["attempted_sun_calls"] == index + 1
    assert report["points"][-1]["relative"]["position_error_m"] > 1


def test_incorrect_phase_velocity_and_units() -> None:
    for factor in (0.0, 1000.0, -1.0):
        ref, _, _ = synthetic()
        ref["runs"][0]["states"][5]["velocity_m_s"] = [
            x * factor for x in ref["runs"][0]["states"][5]["velocity_m_s"]
        ]
        report, _ = invoke(ref)
        assert report["status"] == "failed"
        assert report["attempted_sun_calls"] == 6


@pytest.mark.parametrize("change", ["reverse", "hash", "extra", "missing", "version"])
def test_inventory_admission(change: str) -> None:
    _, _, identity = synthetic()
    manifest = identity["kernels"]
    if change == "reverse":
        manifest["kernels"].reverse()
    elif change == "hash":
        manifest["kernels"][0]["sha256"] = "0" * 64
    elif change == "extra":
        manifest["kernels"].append(deepcopy(manifest["kernels"][0]))
    elif change == "missing":
        manifest["kernels"].pop()
    else:
        manifest["spiceypy_version"] = "unknown"
    report, _ = invoke(identity=lambda: identity)
    assert report["status"] == "unavailable"
    assert report["attempted_sun_calls"] == 0


def test_final_identity_drift() -> None:
    _, _, identity = synthetic()
    count = 0

    def read() -> dict[str, Any]:
        nonlocal count
        count += 1
        return identity | {"revision": str(count)}

    report, _ = invoke(identity=read)
    assert report["status"] == "failed"
    assert report["completed_sun_calls"] == 121


def test_failed_provider_attempt_is_not_completed() -> None:
    def bad(epoch: float) -> dict[str, Any]:
        raise r2.Unavailable(f"missing coverage {epoch}")

    report, _ = invoke(provider=bad)
    assert report["status"] == "unavailable"
    assert report["attempted_sun_calls"] == 1 and report["completed_sun_calls"] == 0


@pytest.mark.parametrize(
    "overrun_stage", ["setup", "provider", "final_identity", "serialization"]
)
def test_budget(overrun_stage: str) -> None:
    _, suns, identity = synthetic()
    now = [0.0]
    identity_calls = 0

    class SlowStream(io.StringIO):
        def flush(self) -> None:
            if overrun_stage == "serialization":
                now[0] = 31.0

    def identities() -> dict[str, Any]:
        nonlocal identity_calls
        identity_calls += 1
        if overrun_stage == "final_identity" and identity_calls == 2:
            now[0] = 31.0
        return identity

    def provider(epoch: float) -> dict[str, Any]:
        if overrun_stage == "provider":
            now[0] = 31.0
        return suns[epoch]

    ref, _, _ = synthetic()

    def loader() -> dict[str, Any]:
        if overrun_stage == "setup":
            now[0] = 31.0
        return ref

    stream = SlowStream()
    report = r2.run(
        stream,
        clock=lambda: now[0],
        identity=identities,
        provider=provider,
        reference_loader=loader,
    )
    assert report["status"] == "failed"
    assert json.loads(stream.getvalue())["status"] == "failed"
    if overrun_stage == "provider":
        assert report["completed_sun_calls"] == 1
        assert "sun" in report["points"][0]
    if overrun_stage == "setup":
        assert report["attempted_sun_calls"] == 0


def test_deadline_exact_boundary_and_clock_reversal() -> None:
    now = [0.0]
    budget = r2.Budget(lambda: now[0])
    for v in (30.0, 31.0, -1.0, float("nan")):
        now[0] = v
        with pytest.raises(r2.GateFailure):
            budget.call("blocked", lambda: None)


def test_exclusive_output(tmp_path: Path) -> None:
    path = tmp_path / "reserved.json"
    path.write_text("preserve")
    with pytest.raises(FileExistsError):
        r2.execute(path)
    assert path.read_text() == "preserve"


def test_no_native_imports_or_production_oracle_helpers() -> None:
    code = f"""
import runpy,sys
m=runpy.run_path({str(PATH)!r})
m['self_check']()
assert not any(k.startswith(('space_nav','tudatpy','numpy','scipy','spiceypy')) for k in sys.modules)
"""
    subprocess.run(
        [sys.executable, "-I", "-c", code], check=True, capture_output=True, text=True
    )


AUDIT_PATH = PATH.with_name("0128-audit-reference-coast.py")
audit_spec = spec_from_file_location("r2_reference_audit", AUDIT_PATH)
assert audit_spec and audit_spec.loader
audit_module = module_from_spec(audit_spec)
audit_spec.loader.exec_module(audit_module)


def test_independent_offline_audit() -> None:
    ref, _, _ = synthetic()
    _, written = invoke(ref)
    result = audit_module.audit(written, ref)
    assert result["reference_coast_verified"] is True
    assert result["arithmetic_nodes_checked"] == 121


@pytest.mark.parametrize(
    "corruption",
    [
        lambda r: r.update(completed_sun_calls=120),
        lambda r: r.update(reference_sha256="wrong"),
        lambda r: r.update(native_spacecraft_propagations=1),
        lambda r: r.update(elapsed_seconds=31.0),
        lambda r: r["points"][1]["sun"].update(origin="Sun"),
        lambda r: r["points"][1].update(elapsed_s=0.0),
        lambda r: r["points"][1]["oracle"]["state"].__setitem__(0, 0.0),
        lambda r: r["points"][1]["relative"].update(position_error_m=0.0),
        lambda r: r["points"][1]["relative"]["invariants"]["saved"].update(energy=1.0),
        lambda r: r["ellipse"].update(eccentricity=0.3),
        lambda r: r["initial_state"].__setitem__(0, 0.0),
        lambda r: r["points"].pop(),
        lambda r: r["calls"].reverse(),
    ],
)
def test_audit_rejects_corruption(corruption: Any) -> None:
    ref, _, _ = synthetic()
    _, written = invoke(ref)
    corruption(written)
    with pytest.raises(ValueError):
        audit_module.audit(written, ref)


def test_audit_failed_partial_numeric_result() -> None:
    ref, _, _ = synthetic()
    ref["runs"][0]["states"][5]["position_m"] = [
        v + 100.0 for v in ref["runs"][0]["states"][5]["position_m"]
    ]
    _, written = invoke(ref)
    result = audit_module.audit(written, ref)
    assert result["audit"] == "passed" and not result["reference_coast_verified"]
    assert result["arithmetic_nodes_checked"] == 6


@pytest.fixture(autouse=True)
def no_native_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    original = builtins.__import__

    def guarded(name: str, *args: Any, **kwargs: Any) -> Any:
        assert not name.startswith(("tudatpy", "spiceypy", "numpy", "scipy")), name
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)


def test_extra_point_cannot_make_122nd_attempt() -> None:
    ref, _, _ = synthetic()
    ref["runs"][0]["states"].append(deepcopy(ref["runs"][0]["states"][-1]))
    report, _ = invoke(ref)
    assert report["status"] == "failed" and report["attempted_sun_calls"] == 0


def test_unavailable_oracle_domain_and_partial_audit() -> None:
    ref, _, _ = synthetic()
    ref["runs"][0]["selected"]["departure_v_infinity_m_s"] = [1e9, 1e9, 1e9]
    _, written = invoke(ref)
    assert written["status"] == "unavailable" and written["completed_sun_calls"] == 1
    result = audit_module.audit(written, ref)
    assert (
        not result["reference_coast_verified"]
        and result["arithmetic_nodes_checked"] == 0
    )


def test_bad_source_before_runtime_import(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(r2, "digest", lambda path: "wrong")
    with pytest.raises(r2.Unavailable, match="identity"):
        r2.load_reference()


def test_runtime_version_guard_before_native_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(r2, "version", lambda name: "wrong")
    with pytest.raises(r2.Unavailable, match="runtime"):
        r2.runtime_identity()


def test_root_failure_cannot_silently_return(monkeypatch: pytest.MonkeyPatch) -> None:
    ellipse = r2.derive(analytic(0.3))
    original = r2.math.sin
    monkeypatch.setattr(r2.math, "sin", lambda x: float("nan"))
    with pytest.raises(r2.GateFailure, match="root"):
        r2.oracle(ellipse, 100.0)
    monkeypatch.setattr(r2.math, "sin", original)


def test_malformed_return_retained_as_finite_json() -> None:
    _, suns, _ = synthetic()

    def provider(epoch: float) -> dict[str, Any]:
        return suns[epoch] | {"position_m": [float("nan"), 0.0, 0.0]}

    report, written = invoke(provider=provider)
    assert report == written
    assert report["status"] == "failed" and report["completed_sun_calls"] == 1
    assert written["points"][0]["sun"]["position_m"][0] == {"nonfinite": "nan"}


def test_comparison_inclusive_gates_and_invariant_rejection() -> None:
    values = {
        "position_error_m": 1.0,
        "velocity_error_m_s": 1e-6,
        "invariants": {"saved": {"energy": 1e-12, "angular_momentum": 1e-12}},
    }
    r2.check_comparison(values)
    values["invariants"]["saved"]["angular_momentum"] = 1.01e-12
    with pytest.raises(r2.GateFailure, match="invariant"):
        r2.check_comparison(values)


def test_fresh_process_requirement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "space_nav.injected", object())
    with pytest.raises(r2.GateFailure, match="fresh process"):
        r2.execute(tmp_path / "new.json")


def test_conda_metadata_without_native_import() -> None:
    for name, expected in (("tudatpy", "1.0.0"), ("tudat-resources", "2.4")):
        path, metadata = r2.conda_metadata(name)
        assert path.is_file() and metadata["version"] == expected


def test_conda_missing_or_ambiguous_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(r2.sys, "prefix", str(tmp_path))
    with pytest.raises(r2.Unavailable):
        r2.conda_metadata("tudatpy")
    folder = tmp_path / "conda-meta"
    folder.mkdir()
    for name in ("tudatpy-a.json", "tudatpy-b.json"):
        (folder / name).write_text(json.dumps({"name": "tudatpy", "version": "1.0.0"}))
    with pytest.raises(r2.Unavailable):
        r2.conda_metadata("tudatpy")


def test_partial_audit_of_comparison_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [0.0]
    checks = 0
    original_check = r2.check_comparison

    def check(values: dict[str, Any], invariants_required: bool = True) -> None:
        nonlocal checks
        original_check(values, invariants_required)
        checks += 1
        if checks == 2:
            now[0] = 31.0

    monkeypatch.setattr(r2, "check_comparison", check)
    ref, _, _ = synthetic()
    report, _ = invoke(ref, clock=lambda: now[0])
    assert report["status"] == "failed" and report["completed_sun_calls"] == 1
    result = audit_module.audit(report, ref)
    assert (
        not result["reference_coast_verified"]
        and result["arithmetic_nodes_checked"] == 1
    )
