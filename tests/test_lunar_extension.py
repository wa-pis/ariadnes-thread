"""Test the 50 s restart and independent saved-data audit on artificial sources."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from test_earth_coast_native import Array
from test_post_cutoff import load
from test_split_coast_study import artificial_bundle, artificial_state

ROOT = Path(__file__).resolve().parents[1]
MARKER_M = 3_474_800
OFFSETS = tuple(float(n) for n in range(0, 51, 5))
type Row = dict[str, Any]


@pytest.fixture(scope="module")
def launch() -> ModuleType:
    return load("launch", "0194-extension")


def fixture(speed_m_s: float, *, gap_m: float = 3125.0, bad_telemetry: bool = False,
            guard_failure: bool = False) -> tuple[Row, ModuleType, list[float]]:
    """Inject a straight-line reference in a weak constant artificial ephemeris."""
    bundle = artificial_bundle()
    t0 = bundle["initial"]["epoch_tdb_s"] + 4096.0
    radius_m = MARKER_M - gap_m
    initial = {"epoch_tdb_s": t0, "position_m": [radius_m, 0.0, 0.0],
               "velocity_m_s": [speed_m_s, 0.0, 0.0]}
    mass_kg = 1351.7475727997967
    bundle.update(initial=initial, offsets_s=list(OFFSETS), mass_kg=mass_kg,
                  restart_moon_state_si=[0.0]*6, marker_radius_m=MARKER_M,
                  archived_state_minus_restart_signed_si={name: [0.0]*6 for name in (
                      "native_normal", "native_tighter", "dop853_normal", "dop853_tighter")},
                  b_runtime=bundle["historical_identity"])
    bundle.pop("native_samples")
    bundle["coast"] = {"constant_mass_metadata_kg": mass_kg, "thrust_n": 0.0,
                       "mass_flow_kg_s": 0.0, "marker_radius_m": MARKER_M,
                       "horizon_s": 50, "coepoch_offsets_s": list(OFFSETS),
                       "coepochs_tdb_s": [t0+s for s in OFFSETS]}
    radii = bundle["radii_m"]
    radii["Moon"] = MARKER_M / 2
    for source in bundle["source_rows_template"].values():
        for record in source["segments"]:
            record.update(first_tdb_s=t0-1024, last_tdb_s=t0+1024)
            record["words"][:2] = [t0, 1024.0]
    bundle["gm_m3_s2"] = gm = {"Sun": 1e3, "Moon": 1e3, "Earth": 1e5}
    adapter = load("native", "0186-long-b").load_adapter()
    adapter.GM, adapter.GUARDS = gm, radii
    launched: list[float] = []

    def body_si(body: str, epoch_tdb_s: float) -> list[float]:
        return [1000*x for x in artificial_state(body, epoch_tdb_s, "J2000", "NONE", "SSB")]

    def guard_body(body: str, epoch_tdb_s: float) -> Array:
        if guard_failure and body == "Moon":
            return Array([radius_m, 0.0, 0.0, 0.0, 0.0, 0.0])
        return Array(body_si(body, epoch_tdb_s))

    prepared = SimpleNamespace(
        included=tuple(gm), gravity_parameters_m3_s2=gm,
        accelerations={"Spacecraft": {b: [object()] for b in gm}},
        bodies=SimpleNamespace(
            global_frame_origin=lambda: "SSB", global_frame_orientation=lambda: "J2000",
            get=lambda b: SimpleNamespace(
                gravity_field_model=SimpleNamespace(gravitational_parameter=gm[b]),
                ephemeris=SimpleNamespace(cartesian_state=lambda at: guard_body(b, at)),
            ),
        ),
    )

    def build_model(model: str, check: Callable[[], None]) -> Any:
        assert model == "B"
        check()
        return prepared

    def propagate(handle: Any, six: tuple[float, ...], epoch: float, length: float, step: float,
                  offsets: tuple[float, ...], context: Any,
                  guard: Callable[[float, tuple[float, ...]], None]) -> Row:
        assert handle is prepared and epoch == t0 and length == 50.0 and offsets == OFFSETS
        assert six == (radius_m, 0.0, 0.0, speed_m_s, 0.0, 0.0)
        launched.append(step)
        guard(epoch, six)
        context.arcs_attempted += 1
        states, forces = {}, {}
        for j in range(round(length / step) + 1):
            elapsed_s = j * step
            at = t0 + elapsed_s
            state = [radius_m + speed_m_s*elapsed_s, 0.0, 0.0, speed_m_s, 0.0, 0.0]
            per_source = []
            for body, mu in gm.items():
                delta = [a-b for a, b in zip(body_si(body, at)[:3], state[:3], strict=True)]
                per_source.append([mu*x / math.hypot(*delta)**3 for x in delta])
            forces_at = [math.fsum(col) for col in zip(*per_source, strict=True)] + sum(per_source, [])
            if bad_telemetry and j == 0:
                forces_at[0] += 0.001
                forces_at[3] += 0.001
            states[at], forces[at] = Array(state), Array(forces_at)
        raw = {"state_history": states, "dependent_variable_history": forces, "integration_completed": True}
        context.arcs_returned += 1
        context.last_returned = raw
        result = adapter.validate_history(raw, six, epoch, length, step, offsets,
                                          handle.included, context.check, guard)
        context.arcs_completed += 1
        return result

    adapter.build_model, adapter.propagate = build_model, propagate
    return bundle, adapter, launched


def study(launch: ModuleType, bundle: Row, adapter: ModuleType, **options: Any) -> Row:
    """Run only against the injected artificial source and native history."""
    return launch.run_study(bundle, artificial_state, adapter,
                            identity_provider=lambda: deepcopy(bundle["historical_identity"]), **options)


@pytest.fixture(scope="module")
def outward(launch: ModuleType) -> tuple[Row, Row]:
    bundle, adapter, launched = fixture(100.0)
    result = study(launch, bundle, adapter)
    assert result["status"] == "passed", result.get("error")
    assert launched == [1.0, 0.5]
    return bundle, result


def test_crossing_and_independent_audit(launch: ModuleType, outward: tuple[Row, Row]) -> None:
    bundle, result = outward
    assert result["marker_status"] == "unavailable"
    assert len(result["comparisons"]) == 33 and len(result["observations"]) == 36
    assert result["counts"]["native_telemetry"]["completed"] == 22
    assert result["counts"]["native_guard_reads"]["completed"] == 462
    assert [r["index"] for r in result["observations"] if r["kind"] == "rhs"] == list(range(7))*2
    t0 = bundle["initial"]["epoch_tdb_s"]
    expected_start = bundle["initial"]["position_m"] + bundle["initial"]["velocity_m_s"]
    assert all(p["result"]["samples"][0]["state"] == expected_start for p in result["native_profiles"])
    assert all(p["outputs"][0]["hi_tdb_s"] == t0 for p in result["profiles"])
    audit = launch.run_audit(bundle, result)
    assert audit["audit_status"] == "passed", audit.get("error")
    assert audit["marker_status"] == "marker-bracketed"
    assert audit["numerical_status"] == "passed"
    assert [audit[key] for key in ("comparisons", "observations", "native_telemetry",
                                    "common_direction_rows", "mesh_direction_rows")] == [33, 36, 22, 44, 152]
    assert audit["common_bracket_tdb_s"] == [t0 + 30, t0 + 35]
    assert audit["native_overlap_tdb_s"] == [t0 + 31, t0 + 31.5]
    assert all(audit[key] == 0 for key in
               ("native_calls", "scientific_imports", "kernel_loads", "spacecraft_propagations"))


@pytest.mark.parametrize(("speed_m_s", "gap_m"), [(-100.0, 3125.0), (100.0, 3100.0)])
def test_inward_or_equal_marker_keeps_numerical_result(
    launch: ModuleType, speed_m_s: float, gap_m: float,
) -> None:
    bundle, adapter, _ = fixture(speed_m_s, gap_m=gap_m)
    result = study(launch, bundle, adapter)
    assert result["status"] == "passed", result.get("error")
    audit = launch.run_audit(bundle, result)
    assert audit["audit_status"] == "passed", audit.get("error")
    assert audit["marker_status"] == "marker-not-established"
    assert audit["numerical_status"] == "passed"
    assert audit["marker_reason"]


@pytest.mark.parametrize("failure", ["telemetry", "guard"])
def test_first_native_failure_stops_later_work(launch: ModuleType, failure: str) -> None:
    bundle, adapter, launched = fixture(
        100.0, bad_telemetry=failure == "telemetry", guard_failure=failure == "guard",
    )
    result = study(launch, bundle, adapter)
    assert result["status"] == "partial" and result["marker_status"] == "unavailable"
    assert launched == [1.0]
    assert len(result["state_requests"]) == 44  # The shared grid precedes native propagation.
    assert not result["profiles"] and not result["rhs"]
    audit = launch.run_audit(bundle, result)
    assert audit["audit_status"] == "partial" and audit["marker_status"] == "unavailable"
    assert audit["partial_study_error"] == result["error"]


def test_late_cap_stops_before_first_native_call(launch: ModuleType) -> None:
    bundle, adapter, launched = fixture(100.0)
    result = study(launch, bundle, adapter, started_s=0.0, clock=lambda: 60.0001)
    assert result["status"] == "partial" and result["marker_status"] == "unavailable"
    assert not launched
    audit = launch.run_audit(bundle, result)
    assert audit["audit_status"] == "partial" and audit["marker_status"] == "unavailable"
    assert audit["partial_study_error"] == result["error"]


@pytest.mark.parametrize("corruption", ["initial_state", "mesh_epoch", "missing_rhs", "count", "comparison", "frame"])
def test_audit_rejects_altered_saved_evidence(
    launch: ModuleType, outward: tuple[Row, Row], corruption: str,
) -> None:
    bundle, original = outward
    report = deepcopy(original)
    if corruption == "frame":
        report["orientation"] = "IAU_MOON"
    elif corruption == "initial_state":
        report["inputs"]["initial"]["position_m"][0] += 1
    elif corruption == "mesh_epoch":
        report["native_profiles"][0]["guards"][4]["epoch_tdb_s"] += 0.5
    elif corruption == "missing_rhs":
        report["rhs"].pop()
    elif corruption == "count":
        report["counts"]["native_guard_reads"]["completed"] -= 1
    else:
        report["comparisons"][0]["epoch_tdb_s"] += 0.5
    audit = launch.run_audit(bundle, report)
    assert audit["audit_status"] == "partial" and audit["marker_status"] == "unavailable"


def test_independent_audit_runs_without_scientific_libraries(
    outward: tuple[Row, Row], tmp_path: Path,
) -> None:
    bundle, result = outward
    data = tmp_path / "synthetic-report.json"
    data.write_text(json.dumps([bundle, result], allow_nan=False))
    before = sha256(data.read_bytes()).digest()
    source = ROOT / "docs/adr/experiments/0194-extension-launch.py"
    script = """
import json
from pathlib import Path
from runpy import run_path
import sys
source, data = map(Path, sys.argv[1:])
bundle, study = json.loads(data.read_bytes())
checked = run_path(str(source))["run_audit"](bundle, study)
assert checked["audit_status"] == "passed", checked.get("error")
assert checked["marker_status"] == "marker-bracketed"
blocked = {"space_nav", "numpy", "scipy", "tudatpy", "spiceypy"}
assert blocked.isdisjoint(name.split(".", 1)[0] for name in sys.modules)
print(checked["marker_status"])
"""
    done = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", script, str(source), str(data)],
                          check=False, capture_output=True, text=True, timeout=12)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "marker-bracketed"
    assert sha256(data.read_bytes()).digest() == before
