"""Native B boundary and independent replay on analytic data, without Tudat or SPICE."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

BASE = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
type Row = dict[str, Any]
type Mutation = Callable[[Row], None]


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, BASE / f"0183-earth-{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


native = load("native")
replay = load("native-replay")


class Array:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def tolist(self) -> list[float]:
        return self.values


class Budget:
    def __init__(self, *, fail: tuple[str, str] | None = None) -> None:
        self.events: Counter[tuple[str, str]] = Counter()
        self.fail = fail

    def check(self) -> None:
        pass

    def event(self, operation: str, phase: str) -> None:
        key = (operation, phase)
        self.events[key] += 1
        if key == self.fail:
            raise ValueError("boundary deadline")


def fixture(*, wrong_earth: bool = False) -> tuple[Row, ModuleType, list[str]]:
    adapter = native.load_adapter()
    initial = [2e9, 3e9, -4e9, 0., 0., 0.]
    t0 = 2.**30
    bundle = {"initial": {"epoch_tdb_s": t0, "position_m": initial[:3],
                          "velocity_m_s": initial[3:]},
              "gm_m3_s2": adapter.GM, "radii_m": adapter.GUARDS,
              "offsets_s": adapter.OFFSETS}
    reads: list[str] = []
    steps: list[float] = []
    distances = (1e10, 2e7, -3e7)
    body_states = {b: [*initial[:i], initial[i]+distances[i], *initial[i+1:]]
                   for i, b in enumerate(native.BODIES)}
    if wrong_earth:
        body_states["Earth"] = initial.copy()

    def body_state(name: str, epoch: float) -> Array:
        assert t0 <= epoch <= t0+300.
        reads.append(name)
        return Array(body_states[name])

    prepared = SimpleNamespace(
        included=native.BODIES,
        gravity_parameters_m3_s2=dict(adapter.GM),
        accelerations={"Spacecraft": {name: [object()] for name in native.BODIES}},
        bodies=SimpleNamespace(
            global_frame_origin=lambda: "SSB",
            global_frame_orientation=lambda: "J2000",
            get=lambda name: SimpleNamespace(
                gravity_field_model=SimpleNamespace(gravitational_parameter=adapter.GM[name]),
                ephemeris=SimpleNamespace(cartesian_state=lambda epoch: body_state(name, epoch)),
            ),
        ),
    )

    def build_model(model: str, check: Callable[[], None]) -> Any:
        assert model == "B"
        check()
        return prepared

    def propagate(
        handle: Any, state: tuple[float, ...], epoch: float, duration: float, step: float,
        offsets: tuple[float, ...], context: native.Arc,
        guard: Callable[[float, tuple[float, ...]], None],
    ) -> Row:
        assert handle is prepared and state == tuple(initial) and epoch == t0 and duration == 300.
        # Synthetic fixed-state telemetry uses exact axis directions. Do not solve a trajectory.
        forces = []
        total = []
        for i, body in enumerate(native.BODIES):
            d = distances[i]
            a = adapter.GM[body]/(d*abs(d))
            forces.extend([a if j == i else 0. for j in range(3)])
            total.append(a)
        epochs = [epoch + i*step for i in range(int(duration/step)+1)]
        raw = {"state_history": {at: Array(initial) for at in epochs},
               "dependent_variable_history": {at: Array(total+forces) for at in epochs},
               "integration_completed": True}
        guard(epoch, state)
        context.arcs_attempted += 1
        steps.append(step)  # Simulated simulator entry, after the attempt event.
        context.arcs_returned += 1
        context.last_returned = raw
        result = adapter.validate_history(raw, state, epoch, duration, step,
                                          offsets, handle.included, context.check, guard)
        context.arcs_completed += 1
        return result

    adapter.build_model = build_model
    adapter.propagate = propagate
    adapter.simulator_steps = steps
    return bundle, adapter, reads


def test_native_b_records_reads_once_and_replays_both_profiles() -> None:
    bundle, adapter, reads = fixture()
    report: Row = {}
    budget = Budget()
    for name in native.ORDER:
        native.solve_profile(bundle, name, report, budget, adapter=adapter)
    assert adapter.simulator_steps == [1., .5]
    assert reads == list(native.BODIES) * 904
    assert budget.events["native_guard_reads", "attempt"] == 2712
    assert budget.events["native_guard_reads", "return"] == 2712
    assert budget.events["native_guard_reads", "complete"] == 2712
    replay_budget = Budget()
    nodes = replay.replay(report["native_profiles"], bundle, event=replay_budget.event)
    assert nodes["normal"] == nodes["tighter"]
    assert nodes["tighter"][-1]["acceleration_m_s2"][-1] < 0
    assert replay_budget.events["native_reference_fields", "complete"] == 84
    assert replay_budget.events["native_telemetry", "complete"] == 14
    with pytest.raises(ValueError, match="order/cap"):
        native.solve_profile(bundle, "tighter", report, budget, adapter=adapter)


@pytest.mark.parametrize("phase", ["attempt", "return"])
def test_arc_deadline_at_boundary_retains_available_prefix(phase: str) -> None:
    bundle, adapter, reads = fixture()
    report: Row = {}
    budget = Budget(fail=("native_arcs", phase))
    with pytest.raises(ValueError, match="boundary deadline"):
        native.solve_profile(bundle, "normal", report, budget, adapter=adapter)
    arc, = report["native_profiles"]
    assert reads == list(native.BODIES)
    assert "result" not in arc
    assert (adapter.simulator_steps == [1.]) is (phase == "return")
    assert ("raw_returned" in arc) is (phase == "return")
    assert replay.replay([arc], bundle, complete=False) == {}
    with pytest.raises(ValueError, match="incomplete"):
        replay.replay([arc], bundle)


def test_failed_earth_guard_stops_before_simulator() -> None:
    bundle, adapter, reads = fixture(wrong_earth=True)
    report: Row = {}
    budget = Budget()
    with pytest.raises(ValueError, match="Earth exclusion"):
        native.solve_profile(bundle, "normal", report, budget, adapter=adapter)
    arc, = report["native_profiles"]
    assert arc["guards"][-1]["passed"] is False
    assert reads == list(native.BODIES) and not adapter.simulator_steps
    assert budget.events["native_arcs", "attempt"] == 0
    assert replay.replay([arc], bundle, complete=False) == {}


def corrupt_earth_force(profile: Row) -> None:
    at = next(iter(profile["raw_returned"]["dependent_variable_history"]))
    raw_force = profile["raw_returned"]["dependent_variable_history"][at]
    # Flip both Earth and total consistently: a source-sum-only check cannot detect this.
    raw_force[2] *= -1.
    raw_force[11] *= -1.
    profile["result"]["samples"][0]["acceleration_m_s2"] = raw_force.copy()


@pytest.mark.parametrize(("mutate", "diagnostic"), [
    (lambda p: p["guards"].pop(4), "native guard sequence"),
    (lambda p: p["guards"][4].update(body="Earth"), "native guard sequence"),
    (lambda p: p["guards"][4].pop("state_si"), "native guard return missing"),
    (lambda p: p["inventory"]["gm_m3_s2"].update(Earth=0.), "native inventory GM"),
    (lambda p: p["inventory"]["force_counts"].update(Earth=True), "native model/force inventory"),
    (lambda p: p["result"]["samples"][0]["state"].__setitem__(5, -0.), "sample differs"),
    (corrupt_earth_force, "telemetry envelope"),
])
def test_replay_rejects_guard_inventory_and_telemetry_corruption(
    mutate: Mutation, diagnostic: str,
) -> None:
    bundle, adapter, _ = fixture()
    report: Row = {}
    profile = native.solve_profile(bundle, "normal", report, Budget(), adapter=adapter)
    corrupt = deepcopy(profile)
    mutate(corrupt)
    with pytest.raises(ValueError, match=diagnostic):
        replay.replay([corrupt], bundle, complete=False)



def test_partial_telemetry_requires_independent_match() -> None:
    bundle, adapter, _ = fixture()
    report: Row = {}
    profile = native.solve_profile(bundle, "normal", report, Budget(), adapter=adapter)
    corrupt = deepcopy(profile)
    corrupt_earth_force(corrupt)
    with pytest.raises(replay.TelemetryFailure) as exc:
        replay.replay_profile(corrupt, bundle, check=replay.idle, event=replay.no_event)
    expected = ("normal", str(exc.value))
    assert replay.replay([corrupt], bundle, complete=False, expected_telemetry_failure=expected) == {}
    with pytest.raises(ValueError, match="did not recur"):
        replay.replay([profile], bundle, complete=False, expected_telemetry_failure=expected)
