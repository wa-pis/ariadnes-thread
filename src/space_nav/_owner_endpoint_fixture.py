"""Private ADR0267 serial owner fixture; native execution requires separate authority.

Injected owners qualify plumbing only. No native imports occur on module import.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import gc
import hashlib
import math
from pathlib import Path
import time
from typing import Any

SCHEMA = "cartesian-position-m_velocity-m-s_mass-kg"
_KERNEL_SHA256 = "04f7af4c8429c09aec9a21f50888e7e4a979e69184e8abc530e17e88e4cb4941"
_INITIAL = (10000000.0, 0.0, 0.0, 0.0, 1000.0, 0.0, 2000.0)
_REVERSE = (10000000.0, 1050000.0, 0.0, 0.0, 1100.0, 0.0, 2000.0)
_UNAVAILABLE = "completed original results unavailable"
_SCHEMA_ERROR = "explicit Cartesian position/velocity/mass schema required"


class FixtureError(RuntimeError):
    """The fixed fixture failed before any physical qualification."""


def _number(value: object, field: str) -> float:
    if type(value) not in (int, float):
        raise FixtureError(field + ": finite nonboolean number required")
    try:
        result = float(value)
    except OverflowError as exc:
        raise FixtureError(field + ": finite number required") from exc
    if not math.isfinite(result):
        raise FixtureError(field + ": finite number required")
    return result


@dataclass(slots=True)
class Budget:
    started_s: float
    clock: Callable[[], float] = time.monotonic
    factory_attempts: int = 0
    integration_attempts: int = 0
    visitor_calls: int = 0
    acceleration_callbacks: int = 0
    spice_queries: int = 0
    kernel_reads: int = 0
    real_archive_reads: int = 0
    failed: bool = False
    previous_s: float | None = None

    def check(self) -> None:
        if self.failed:
            raise FixtureError("fixture already failed")
        try:
            now = _number(self.clock(), "monotonic clock")
            started = _number(self.started_s, "started_s")
            if now < started or (self.previous_s is not None and now < self.previous_s):
                raise FixtureError("monotonic clock moved backwards")
            self.previous_s = now
            if now - started >= 45.0:
                raise FixtureError("producer45s deadline exhausted")
        except (FixtureError, OSError, ValueError, TypeError, RuntimeError):
            self.failed = True
            raise

    def _charge(self, name: str, maximum: int) -> None:
        self.check()
        count = getattr(self, name)
        if type(count) is not int or not 0 <= count < maximum:
            self.failed = True
            raise FixtureError(f"{name} cap{maximum}")
        setattr(self, name, count + 1)

    def charge_factory(self, simulate: bool) -> None:
        if type(simulate) is not bool:
            self.failed = True
            raise FixtureError("simulate: boolean required")
        self._charge("factory_attempts", 3)
        if simulate:
            self._charge("integration_attempts", 2)

    def charge_visitor(self) -> None:
        self._charge("visitor_calls", 8)

    def charge_acceleration(self) -> None:
        self._charge("acceleration_callbacks", 100000)

    def snapshot(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in (
            "factory_attempts", "integration_attempts", "visitor_calls",
            "acceleration_callbacks", "spice_queries", "kernel_reads", "real_archive_reads",
        )} | {"optimizer_entries": 0, "native_reported_function_evaluations": []}


def integrator_profile(arc_id: str) -> dict[str, object]:
    """Reuse the existing tighter coast profile without importing native modules."""
    from .trajectory import _arc_integrator_profile
    if arc_id not in {"never-run", "forward", "reverse"}:
        raise FixtureError("unknown fixed arc")
    profile = _arc_integrator_profile("owner-endpoint-fixture", "coast", tighter=True)
    if arc_id == "reverse":
        profile["initial_step_s"] *= -1
    profile["absolute_tolerances_si"] = list(profile["absolute_tolerances_si"])
    return profile


def _native_context() -> list[int]:
    from tudatpy import kernel
    if hashlib.sha256(Path(kernel.__file__).read_bytes()).hexdigest() != _KERNEL_SHA256:
        raise FixtureError("private kernel identity mismatch; no operational fallback")
    context = kernel.dynamics.simulator._ariadna_endpoint_native_context
    if type(context) is not tuple or context != (53, 53, 8):
        raise FixtureError("private native context mismatch")
    return list(context)


def _native_factory(arc_id: str, simulate: bool, budget: Budget) -> object:
    """Build only the fixed coast settings; never called by artificial tests."""
    import numpy as np
    import tudatpy
    from tudatpy.dynamics import environment_setup, propagation_setup, simulator
    from . import trajectory
    if tudatpy.__version__ != "1.0.0" or np.__version__ != "1.26.4":
        raise FixtureError("pinned native runtime mismatch")
    reverse = arc_id == "reverse"
    start_s, stop_s = (1000.0, 0.0) if reverse else (0.0, 1000.0)
    initial = _REVERSE if reverse else _INITIAL
    settings = environment_setup.BodyListSettings("SSB", "J2000")
    settings.add_empty_settings("Spacecraft")
    settings.get("Spacecraft").constant_mass = 2000.0
    bodies = environment_setup.create_system_of_bodies(settings)
    if bodies.global_frame_origin() != "SSB" or bodies.global_frame_orientation() != "J2000":
        raise FixtureError("actual native body frame mismatch")

    def acceleration(epoch_s: float) -> Any:
        budget.charge_acceleration()
        _number(epoch_s, "acceleration epoch")
        return np.asarray((0.0, 0.1, 0.0))

    forces = [propagation_setup.acceleration.custom_acceleration(acceleration)]
    accelerations = propagation_setup.create_acceleration_models(
        bodies, {"Spacecraft": {"Spacecraft": forces}}, ["Spacecraft"], ["SSB"])
    integrator = trajectory._build_integrator_from_profile(
        "owner-endpoint-fixture", "coast", integrator_profile(arc_id))
    termination = propagation_setup.propagator.time_termination(
        stop_s, terminate_exactly_on_final_condition=True)
    coupled = trajectory._build_coupled_arc_settings(
        "owner-endpoint-fixture", bodies, accelerations, initial[:6], initial[6],
        start_s, integrator, termination, thrust_enabled=False)
    types = coupled.propagator_settings_per_type
    expected_types = {propagation_setup.propagator.translational_type: initial[:6],
                      propagation_setup.propagator.mass_type: (initial[6],)}
    if not isinstance(types, Mapping) or set(types) != set(expected_types):
        raise FixtureError("actual native translation/mass settings types mismatch")
    for state_type, expected in expected_types.items():
        entries = types[state_type]
        if type(entries) is not list or len(entries) != 1:
            raise FixtureError("actual native settings require one entry per type")
        values = np.asarray(entries[0].initial_states).reshape(-1)
        words = [float(v).hex() for v in values]
        if words != [v.hex() for v in expected]:
            raise FixtureError("actual native typed initial state words mismatch")
    processing = coupled.processing_settings
    processing.clear_numerical_solution = False
    processing.set_integrated_result = False
    if processing.clear_numerical_solution is not False or processing.set_integrated_result is not False:
        raise FixtureError("actual native processing retention mismatch")
    return simulator.create_dynamics_simulator(
        bodies, coupled, simulate_dynamics_on_creation=simulate)


def _ids(value: object, *, propagated: bool) -> list[dict[str, object]]:
    if (not isinstance(value, Mapping) or set(value) != {(0, 6), (6, 1)}
            or any(type(key) is not tuple or len(key) != 2
                   or any(type(part) is not int for part in key) for key in value)):
        raise FixtureError("state metadata ranges must be integer pairs (0,6),(6,1)")
    rows = []
    for key in ((0, 6), (6, 1)):
        description = value[key]
        if (type(description) is not str or not 0 < len(description) <= 256
                or not description.isascii()):
            raise FixtureError("state description must be bounded ASCII")
        expected = ("Mass state of body Spacecraft" if key == (6, 1) else
                    "Translational state (Cowell formulation) of body Spacecraft w.r.t. SSB" if propagated else
                    "Translational state, in Cartesian elements, of body Spacecraft w.r.t. SSB")
        if description != expected:
            raise FixtureError("actual state metadata meaning mismatch")
        rows.append({"start": key[0], "size": key[1], "description": description})
    return rows


def _metadata(owner: Any) -> tuple[dict[str, object], int]:
    results = owner.propagation_results
    details = results.termination_details
    reason = str(details.termination_reason).rsplit(".", 1)[-1]
    if (results.propagation_is_performed is not True
            or results.integration_completed_successfully is not True
            or reason != "termination_condition_reached"
            or details.terminated_on_exact_condition is not True
            or type(results.propagated_state_vector_length) is not int
            or results.propagated_state_vector_length != 7):
        raise FixtureError("successful exact condition termination/seven-state metadata required")
    count = _number(results.total_number_of_function_evaluations, "reported function count")
    if count < 0 or not count.is_integer():
        raise FixtureError("reported function count must be nonnegative integer")
    metadata = {
        "processed_state_ids": _ids(results.processed_state_ids, propagated=False),
        "propagated_state_ids": _ids(results.propagated_state_ids, propagated=True),
        "propagated_state_vector_length": 7, "propagation_is_performed": True,
        "integration_completed_successfully": True, "termination_reason": reason,
        "terminated_on_exact_condition": True,
        # Native factory checks actual settings/body frame; injected setup is only a fabricated premise.
        "clear_numerical_solution": False, "set_integrated_result": False,
        "origin": "SSB", "orientation": "J2000",
    }
    return metadata, int(count)


def _endpoint(value: object) -> dict[str, object]:
    if type(value) is not tuple or len(value) != 3:
        raise FixtureError("endpoint must be a native primitive three-tuple")
    hour, remainder, state = value
    if type(hour) is not int or hour != 0:
        raise FixtureError("fixed endpoint hour must be integer0")
    if type(remainder) is not float or not math.isfinite(remainder) or remainder not in (0.0, 1000.0):
        raise FixtureError("fixed endpoint remainder must be finite0or1000")
    if type(state) is not tuple or len(state) != 7:
        raise FixtureError("endpoint requires seven primitive state words")
    if any(type(v) is not float or not math.isfinite(v) for v in state):
        raise FixtureError("endpoint requires seven finite binary64 values")
    return {"hour": hour, "remainder_hex": remainder.hex(), "state_hex": [v.hex() for v in state]}


def _provenance() -> dict[str, str]:
    files = {"producer_sha256": "_owner_endpoint_fixture.py",
             "auditor_sha256": "_owner_endpoint_audit.py", "trajectory_sha256": "trajectory.py"}
    return {key: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for key, name in files.items()}


def produce(*, factory: Callable[[str, bool, Budget], object] | None = None,
            budget: Budget | None = None) -> dict[str, object]:
    """Retain one fixed serial owner chain, or its first failed partial chain.

    A supplied factory is explicitly injected evidence, never native qualification.
    The default native route requires the exact private kernel and separate F18.3 authority.
    """
    budget = Budget(time.monotonic()) if budget is None else budget
    packet: dict[str, Any] = {
        "schema": "ariadna-owner-fixture-v1", "scope": "synthetic-owner-conformance-only",
        "frame": "SYNTHETIC_INERTIAL", "time_scale": "elapsed_seconds",
        "mode": "native" if factory is None else "injected", "status": "failed", "failure": None,
        "native_context": [], "calls": [], "arcs": [], "retained_rows_after_clear": {},
        "counts": budget.snapshot(), "provenance": {},
    }
    selected = _native_factory if factory is None else factory

    def make(arc_id: str, simulate: bool) -> Any:
        budget.charge_factory(simulate)
        try:
            owner = selected(arc_id, simulate, budget)
            if not callable(owner._ariadna_original_endpoint):
                raise FixtureError("actual owner method unavailable")
        except Exception as exc:  # Untyped third-party/injected owner boundary only.
            raise FixtureError(f"{arc_id} factory failed: {type(exc).__name__}: {exc}") from exc
        budget.check()
        return owner

    def visit(method: Callable[[bool, str], object], call_id: str, owner_id: str,
              selector: bool, *, rejection: tuple[type[Exception], str] | None = None) -> object:
        budget.charge_visitor()
        schema = "invalid" if call_id == "wrong-schema" else SCHEMA
        row: dict[str, Any] = {"id": call_id, "owner": owner_id, "selector": selector,
                               "schema": schema, "outcome": "accepted", "endpoint": None,
                               "exception": None}
        try:
            value = method(selector, schema)
        except Exception as exc:  # Capture the exact untyped native-method result/refusal.
            row["outcome"] = "refused"
            row["exception"] = {"type": type(exc).__name__, "message": str(exc)}
            packet["calls"].append(row)
            if rejection is None or type(exc) is not rejection[0] or str(exc) != rejection[1]:
                raise FixtureError(f"{call_id}: unexpected native refusal: {exc}") from exc
            budget.check()
            return None
        row["endpoint"] = _endpoint(value)
        packet["calls"].append(row)
        if rejection is not None:
            raise FixtureError(call_id + ": expected refusal missing")
        budget.check()
        return value

    def arc(owner: Any, arc_id: str) -> None:
        try:
            metadata, count = _metadata(owner)
        except Exception as exc:  # Validate only the untyped results boundary here.
            raise FixtureError(f"{arc_id} metadata failed: {exc}") from exc
        reverse = arc_id == "reverse"
        packet["arcs"].append({"id": arc_id, "start_s": 1000 if reverse else 0,
                               "end_s": 0 if reverse else 1000,
                               "initial_state_hex": [v.hex() for v in (_REVERSE if reverse else _INITIAL)],
                               "integrator": integrator_profile(arc_id), "metadata": metadata})
        reports.append(count)

    reports: list[int] = []
    try:
        budget.check()
        packet["provenance"] = _provenance()
        packet["native_context"] = [53, 53, 8] if factory is not None else _native_context()
        never_run = make("never-run", False)
        visit(never_run._ariadna_original_endpoint, "never-run", "never-run", True,
              rejection=(RuntimeError, _UNAVAILABLE))
        del never_run
        forward = make("forward", True)
        arc(forward, "forward")
        first = visit(forward._ariadna_original_endpoint, "forward-start", "forward", False)
        last = visit(forward._ariadna_original_endpoint, "forward-end", "forward", True)
        visit(forward._ariadna_original_endpoint, "wrong-schema", "forward", True,
              rejection=(ValueError, _SCHEMA_ERROR))
        retained = forward._ariadna_original_endpoint
        results = forward.propagation_results
        del forward
        gc.collect()
        same = visit(retained, "retained-bound", "forward", True)
        if _endpoint(same) != _endpoint(last):
            raise FixtureError("retained bound method changed terminal words")
        results.clear_data()
        visit(retained, "cleared", "forward", True, rejection=(RuntimeError, _UNAVAILABLE))
        packet["retained_rows_after_clear"] = {
            "forward-start": _endpoint(first), "forward-end": _endpoint(last),
            "retained-bound": _endpoint(same),
        }
        for key, row in packet["retained_rows_after_clear"].items():
            prior = next(c["endpoint"] for c in packet["calls"] if c["id"] == key)
            if row != prior:
                raise FixtureError("returned primitive words changed after clear")
        del retained, results
        reverse = make("reverse", True)
        arc(reverse, "reverse")
        visit(reverse._ariadna_original_endpoint, "reverse-end", "reverse", False)
        visit(reverse._ariadna_original_endpoint, "reverse-start", "reverse", True)
        del reverse
        budget.check()
        packet["status"] = "passed"
    except (FixtureError, OSError, ValueError, TypeError, RuntimeError, AttributeError) as exc:
        budget.failed = True
        packet["failure"] = f"{type(exc).__name__}: {exc}"
    packet["counts"] = budget.snapshot()
    packet["counts"]["native_reported_function_evaluations"] = reports
    return packet
