"""Observed RK4 profiles for the private 600 s model B check."""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Protocol

HERE = Path(__file__).resolve().parent
BODIES = ("Sun", "Moon", "Earth")
ORDER = ("normal", "tighter")
DURATION_S = 600.
OFFSETS = tuple(float(s) for s in range(0, 601, 50))
GUARD_READS = 3 * (1 + 601 + 1 + 1201)
type Row = dict[str, Any]
type Vector = tuple[float, ...]
type Guard = Callable[[float, Vector], None]


class Budget(Protocol):
    def check(self) -> None: ...
    def event(self, operation: str, phase: str) -> None: ...


def _load(filename: str, expected: str) -> ModuleType:
    path = HERE / filename
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected:
        raise ValueError(f"immutable native helper digest: {filename}")
    module = ModuleType("r539_" + path.stem.replace("-", "_"))
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


_OBSERVER = _load("0183-earth-native.py",
                  "6730fe7aa4d9b3407a6c16e3a4232277860db261f65130a12166de1721fa7060")
require, wire, Arc, inventory = (_OBSERVER.require, _OBSERVER.wire,
                                  _OBSERVER.Arc, _OBSERVER.inventory)


def load_adapter() -> ModuleType:
    """Load the immutable native model builder and history validator."""
    return _OBSERVER.load_adapter()


def _propagate(adapter: ModuleType, prepared: Any, initial: Vector, t0: float,
               step_s: float, context: Any, guard: Guard) -> Row:
    """One explicit B-only Cowell RK4 arc, with the frozen 600 s duration."""
    require(prepared.included == BODIES and step_s in (1., .5),
            "long-coast native model/profile")
    require(all((t0+s)-t0 == s for s in (*OFFSETS, step_s)), "native epoch grid not representable")
    context.check()
    guard(t0, initial)
    from tudatpy.dynamics import propagation_setup, simulator

    try:
        adapter.validate_inventory(prepared)
        integral = propagation_setup.integrator
        scheme = integral.runge_kutta_fixed_step(step_s, integral.CoefficientSets.rk_4,
                                                 assess_termination_on_minor_steps=False)
        prop = propagation_setup.propagator
        endpoint = prop.time_termination(t0 + DURATION_S, terminate_exactly_on_final_condition=True)
        dependent = propagation_setup.dependent_variable
        output = [dependent.total_acceleration("Spacecraft"), *(
            dependent.single_acceleration(propagation_setup.acceleration.point_mass_gravity_type,
                                          "Spacecraft", body) for body in BODIES)]
        settings = prop.translational(["SSB"], prepared.accelerations, ["Spacecraft"], initial, t0,
                                     scheme, endpoint, propagator=prop.cowell, output_variables=output)
    except Exception as exc:  # Untyped native settings boundary.
        raise adapter.NativeError(f"native propagation setup failed: {exc}") from exc
    context.check()
    context.arcs_attempted += 1
    try:
        engine = simulator.create_dynamics_simulator(prepared.bodies, settings)
        raw = {"state_history": engine.state_history,
               "dependent_variable_history": engine.dependent_variable_history,
               "integration_completed": engine.integration_completed_successfully}
    except Exception as exc:  # Untyped native simulator boundary.
        raise adapter.NativeError(f"native integration failed: {exc}") from exc
    context.arcs_returned += 1
    context.last_returned = raw
    result = adapter.validate_history(raw, initial, t0, DURATION_S, step_s, OFFSETS, BODIES,
                                      context.check, guard)
    context.arcs_completed += 1
    return result


def solve_profile(bundle: Row, name: str, report: Row, budget: Budget, *,
                  adapter: ModuleType | None = None) -> Row:
    """Run the next B profile and keep the guard return from each actual read."""
    profiles = report.setdefault("native_profiles", [])
    require(len(profiles) < 2 and name == ORDER[len(profiles)]
            and all(p["arc"]["completed"] == 1 for p in profiles), "native B profile order/cap")
    injected = adapter is not None
    adapter = load_adapter() if adapter is None else adapter
    require(tuple(bundle["offsets_s"]) == OFFSETS and bundle["gm_m3_s2"] == adapter.GM
            and bundle["radii_m"] == adapter.GUARDS, "native B frozen controls")
    raw_initial = bundle["initial"]
    t0 = adapter.number(raw_initial["epoch_tdb_s"])
    initial = adapter.vector(raw_initial["position_m"] + raw_initial["velocity_m_s"], 6)
    step_s = 1. if name == "normal" else .5
    states = int(DURATION_S / step_s) + 1
    row: Row = {"name": name, "step_s": step_s, "guards": [],
                "arc": {"attempted": 0, "returned": 0, "completed": 0}}
    profiles.append(row)
    prepared = adapter.build_model("B", budget.check)
    row["inventory"] = inventory(adapter, prepared, bundle["gm_m3_s2"])
    context = Arc(budget, row)
    radii = bundle["radii_m"]

    def guard(at: float, state: Vector) -> None:
        reads = row["guards"]
        group, remainder = divmod(len(reads), len(BODIES))
        require(not remainder and at == t0 + max(0, group-1)*step_s and group <= states,
                "native guard order/grid")
        for body in BODIES:
            budget.event("native_guard_reads", "attempt")
            entry = {"body": body, "epoch_tdb_s": at, "group": group}
            reads.append(entry)
            try:
                raw = prepared.bodies.get(body).ephemeris.cartesian_state(at)
                flat = raw.reshape(-1) if hasattr(raw, "reshape") else raw
            except Exception as exc:  # Untyped native ephemeris boundary.
                raise ValueError(f"native guard failed: {body} at {at}: {exc}") from exc
            entry["state_si"] = wire(flat)
            budget.event("native_guard_reads", "return")
            position = adapter.vector(entry["state_si"], 6)[:3]
            distance_m = math.dist(state[:3], position)
            require(math.isfinite(distance_m), "native guard distance nonfinite")
            entry["distance_m"] = distance_m
            entry["passed"] = distance_m > radii[body]
            require(entry["passed"], f"native {body} exclusion sphere at {at}")
            budget.event("native_guard_reads", "complete")

    if injected:
        result = adapter.propagate(prepared, initial, t0, DURATION_S, step_s, OFFSETS, context, guard)
    else:
        result = _propagate(adapter, prepared, initial, t0, step_s, context, guard)
    require(context.arcs_completed == 1 and context.arcs_returned == 1,
            "native arc did not finalize its history")
    require(len(row["guards"]) == 3*(1+states), "native guard coverage")
    row["result"] = wire(result)
    row["arc"]["completed"] = 1
    budget.event("native_arcs", "complete")
    return row
