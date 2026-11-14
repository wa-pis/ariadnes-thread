"""Check the new 600 s native boundary using only synthetic arrays and settings."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from test_earth_coast_native import Array, Budget

BASE = Path(__file__).resolve().parents[1] / "docs/adr/experiments"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"fixture_r539_{name}", BASE / f"0186-long-b-{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


native, replay = (load(name) for name in ("native", "native-replay"))
type Row = dict[str, Any]


def setup_native(monkeypatch: pytest.MonkeyPatch, *, earth_intersection_s: float | None = None
                 ) -> tuple[Row, list[tuple[float, float]], list[str]]:
    """Inject only the settings and return boundary; run the actual native wiring."""
    adapter = native.load_adapter()
    t0 = 2.**30
    x0 = (2e9, 3e9, -4e9, 0., 0., 0.)
    deltas = (1e10, 2e7, -3e7)
    states, measured = {}, []
    for j, body in enumerate(native.BODIES):
        v = list(x0)
        v[j] += deltas[j]
        states[body] = v
        measured.extend(adapter.GM[body]/(deltas[j]*abs(deltas[j])) if k == j else 0.
                        for k in range(3))
    total = [math.fsum(measured[k::3]) for k in range(3)]
    reads: list[str] = []
    solves: list[tuple[float, float]] = []

    def body_state(body: str, at: float) -> Array:
        assert t0 <= at <= t0+600.
        reads.append(body)
        bad = body == "Earth" and earth_intersection_s == at-t0
        return Array(list(x0) if bad else states[body])

    class FakeBodies:
        def global_frame_origin(self) -> str:
            return "SSB"

        def global_frame_orientation(self) -> str:
            return "J2000"

        def get(self, body: str) -> SimpleNamespace:
            return SimpleNamespace(
                gravity_field_model=SimpleNamespace(gravitational_parameter=adapter.GM[body]),
                ephemeris=SimpleNamespace(cartesian_state=lambda at: body_state(body, at)),
            )

    prepared = adapter.Prepared(FakeBodies(), {"Spacecraft": {b: [object()] for b in native.BODIES}},
                                native.BODIES, dict(adapter.GM))

    def build_model(model: str, check: Any) -> Any:
        assert model == "B"
        check()
        return prepared

    monkeypatch.setattr(adapter, "build_model", build_model)
    monkeypatch.setattr(native, "load_adapter", lambda: adapter)

    def scheme(step: float, coeffs: str, *, assess_termination_on_minor_steps: bool) -> float:
        assert coeffs == "rk_4" and assess_termination_on_minor_steps is False
        return step

    def termination(tf: float, *, terminate_exactly_on_final_condition: bool) -> float:
        assert terminate_exactly_on_final_condition is True
        return tf

    def translational(centres: list[str], accelerations: Any, targets: list[str],
                      initial: tuple[float, ...], epoch: float, step: float, end: float,
                      *, propagator: str, output_variables: list[Any]) -> tuple[float, float]:
        assert centres == ["SSB"] and targets == ["Spacecraft"] and propagator == "cowell"
        assert accelerations is prepared.accelerations
        assert epoch == t0 and initial == x0 and end == t0+600.
        assert output_variables == [("total", "Spacecraft"), *(
            ("point", "Spacecraft", b) for b in native.BODIES)]
        return step, end

    def simulate(bodies: Any, settings: tuple[float, float]) -> SimpleNamespace:
        assert bodies is prepared.bodies
        step, end = settings
        solves.append(settings)
        epochs = [t0 + j*step for j in range(int((end-t0)/step)+1)]
        return SimpleNamespace(
            state_history={t: Array(list(x0)) for t in epochs},
            dependent_variable_history={t: Array(total + measured) for t in epochs},
            integration_completed_successfully=True,
        )

    dynamics = ModuleType("tudatpy.dynamics")
    dynamics.propagation_setup = SimpleNamespace(
        integrator=SimpleNamespace(runge_kutta_fixed_step=scheme,
                                   CoefficientSets=SimpleNamespace(rk_4="rk_4")),
        propagator=SimpleNamespace(translational=translational, time_termination=termination,
                                   cowell="cowell"),
        dependent_variable=SimpleNamespace(
            total_acceleration=lambda sat: ("total", sat),
            single_acceleration=lambda kind, sat, body: (kind, sat, body)),
        acceleration=SimpleNamespace(point_mass_gravity_type="point"),
    )
    dynamics.simulator = SimpleNamespace(create_dynamics_simulator=simulate)
    monkeypatch.setitem(sys.modules, "tudatpy.dynamics", dynamics)
    bundle = {"initial": {"epoch_tdb_s": t0, "position_m": list(x0[:3]),
                          "velocity_m_s": list(x0[3:])}, "offsets_s": native.OFFSETS,
              "gm_m3_s2": adapter.GM, "radii_m": adapter.GUARDS}
    return bundle, solves, reads


def test_native_checks_all_600_s_states_and_audit_last_node(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle, solves, reads = setup_native(monkeypatch)
    report: Row = {}
    counts = Budget()
    for name in native.ORDER:
        native.solve_profile(bundle, name, report, counts)
    t0 = bundle["initial"]["epoch_tdb_s"]
    assert solves == [(1., t0+600.), (.5, t0+600.)]
    assert [r["result"]["retained_states"] for r in report["native_profiles"]] == [601, 1201]
    assert reads == list(native.BODIES)*1804 and native.GUARD_READS == 5412
    assert all(counts.events["native_guard_reads", k] == 5412 for k in ("attempt", "return", "complete"))
    audit_counts = Budget()
    nodes = replay.replay(report["native_profiles"], bundle, event=audit_counts.event)
    assert [x["epoch_tdb_s"] for x in nodes["tighter"]] == [t0 + s for s in native.OFFSETS]
    assert audit_counts.events["native_telemetry", "complete"] == 26
    assert audit_counts.events["native_reference_fields", "complete"] == 156

    corrupted = deepcopy(report["native_profiles"])
    profile = corrupted[-1]
    force = profile["raw_returned"]["dependent_variable_history"][str(t0+600.)]
    force[2] *= -1
    force[11] *= -1
    profile["result"]["samples"][-1]["acceleration_m_s2"] = force.copy()
    with pytest.raises(ValueError, match="Earth telemetry envelope|total telemetry envelope"):
        replay.replay(corrupted, bundle)

    corrupted = deepcopy(report["native_profiles"])
    corrupted[-1]["guards"][-5]["epoch_tdb_s"] = t0 + 300.
    with pytest.raises(ValueError, match="native guard sequence"):
        replay.replay(corrupted, bundle)
    with pytest.raises(ValueError, match="order/cap"):
        native.solve_profile(bundle, "tighter", report, counts)


def test_native_stops_in_extension_and_preserves_partial_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle, solves, _ = setup_native(monkeypatch, earth_intersection_s=450.)
    report: Row = {}
    counts = Budget()
    with pytest.raises(ValueError, match="Earth exclusion"):
        native.solve_profile(bundle, "normal", report, counts)
    profile, = report["native_profiles"]
    assert len(solves) == 1 and profile["arc"] == {"attempted": 1, "returned": 1, "completed": 0}
    assert profile["guards"][-1]["passed"] is False
    assert len(profile["raw_returned"]["state_history"]) == 601
    assert replay.replay([profile], bundle, complete=False) == {}
    with pytest.raises(ValueError, match="order/cap"):
        native.solve_profile(bundle, "tighter", report, counts)


def test_return_deadline_records_raw_600_s_history(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle, _, reads = setup_native(monkeypatch)
    report: Row = {}
    with pytest.raises(ValueError, match="boundary deadline"):
        native.solve_profile(bundle, "normal", report, Budget(fail=("native_arcs", "return")))
    profile, = report["native_profiles"]
    assert reads == list(native.BODIES)
    assert len(profile["raw_returned"]["state_history"]) == 601
    assert replay.replay([profile], bundle, complete=False) == {}
