"""Artificial serial owners only; never execute the private native packet."""

from __future__ import annotations

from dataclasses import dataclass
import math
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any
import weakref

import pytest

from space_nav import _owner_endpoint_fixture as producer

_INITIAL = (10000000.0, 0.0, 0.0, 0.0, 1000.0, 0.0, 2000.0)
_END = (10000000.0, 1050000.0, 0.0, 0.0, 1100.0, 0.0, 2000.0)
_METADATA = {(0, 6): "Translational state, in Cartesian elements, of body Spacecraft w.r.t. SSB",
             (6, 1): "Mass state of body Spacecraft"}
_PROPAGATED = {(0, 6): "Translational state (Cowell formulation) of body Spacecraft w.r.t. SSB",
               (6, 1): "Mass state of body Spacecraft"}


@dataclass
class Clock:
    value: float = 0.0

    def __call__(self) -> float:
        return self.value


class Results:
    def __init__(self, simulate: bool) -> None:
        self.cleared = False
        self.propagation_is_performed = simulate
        self.integration_completed_successfully = simulate
        self.propagated_state_vector_length = 7
        self.processed_state_ids = _METADATA.copy()
        self.propagated_state_ids = _PROPAGATED.copy()
        self.total_number_of_function_evaluations = 15.0
        self.termination_details = SimpleNamespace(
            termination_reason="termination_condition_reached", terminated_on_exact_condition=True)

    def clear_data(self) -> None:
        self.cleared = True


class Owner:
    def __init__(self, arc_id: str, simulate: bool) -> None:
        self.arc_id = arc_id
        self.propagation_results = Results(simulate)

    @property
    def state_history_time_object(self) -> object:
        raise AssertionError("converted history is forbidden")

    @property
    def state_history(self) -> object:
        raise AssertionError("converted history is forbidden")

    def _ariadna_original_endpoint(self, forward: bool, schema: str) -> object:
        if not self.propagation_results.propagation_is_performed or self.propagation_results.cleared:
            raise RuntimeError("completed original results unavailable")
        if schema != producer.SCHEMA:
            raise ValueError("explicit Cartesian position/velocity/mass schema required")
        return (0, 1000.0, _END) if forward else (0, -0.0, _INITIAL)


def _factory(arc_id: str, simulate: bool, budget: producer.Budget) -> Owner:
    if simulate:
        budget.charge_acceleration()
    return Owner(arc_id, simulate)


def _produce(factory: Any = _factory, budget: producer.Budget | None = None) -> dict[str, Any]:
    return producer.produce(factory=factory, budget=budget or producer.Budget(0.0, Clock()))


def test_eight_ordered_owner_calls_and_primitive_retention_without_history_export() -> None:
    packet = _produce()
    assert packet["status"] == "passed", packet["failure"]
    assert packet["mode"] == "injected" and packet["native_context"] == [53, 53, 8]
    calls = packet["calls"]
    assert [row["id"] for row in calls] == [
        "never-run", "forward-start", "forward-end", "wrong-schema",
        "retained-bound", "cleared", "reverse-end", "reverse-start",
    ]
    assert sum(row["outcome"] == "accepted" for row in calls) == 5
    assert calls[1]["endpoint"]["remainder_hex"] == (-0.0).hex()
    assert calls[4]["endpoint"] == calls[2]["endpoint"]
    assert packet["retained_rows_after_clear"] == {
        row["id"]: row["endpoint"] for row in (calls[1], calls[2], calls[4])}
    assert packet["counts"] == {
        "factory_attempts": 3, "integration_attempts": 2, "visitor_calls": 8,
        "acceleration_callbacks": 2, "native_reported_function_evaluations": [15, 15],
        "spice_queries": 0, "kernel_reads": 0, "real_archive_reads": 0, "optimizer_entries": 0,
    }
    assert packet["arcs"][0]["integrator"]["initial_step_s"] == 75.0
    assert packet["arcs"][1]["integrator"]["initial_step_s"] == -75.0
    assert packet["arcs"][1]["initial_state_hex"] == [v.hex() for v in _END]


def test_returned_method_owns_object_after_original_name_release() -> None:
    references: list[weakref.ReferenceType[Owner]] = []

    class RetentionOwner(Owner):
        def _ariadna_original_endpoint(self, forward: bool, schema: str) -> object:
            assert references[-1]() is self
            return super()._ariadna_original_endpoint(forward, schema)

    def factory(arc_id: str, simulate: bool, budget: producer.Budget) -> Owner:
        owner = RetentionOwner(arc_id, simulate)
        references.append(weakref.ref(owner))
        return owner

    assert _produce(factory)["status"] == "passed"


@pytest.mark.parametrize("name,value", [
    ("propagation_is_performed", False), ("propagation_is_performed", 1),
    ("integration_completed_successfully", False), ("propagated_state_vector_length", 6),
    ("propagated_state_vector_length", 7.0), ("total_number_of_function_evaluations", -1.0),
    ("total_number_of_function_evaluations", 1.5), ("total_number_of_function_evaluations", math.inf),
    ("processed_state_ids", {(0, 7): "wrong"}),
    ("processed_state_ids", {(0, 6): "wrong", (6, 1): "Mass state of body Spacecraft"}),
    ("propagated_state_ids", {(0, 6): "wrong", (6, 1): "Mass state of body Spacecraft"}),
])
def test_bad_native_result_metadata_stops_before_forward_visitor(name: str, value: object) -> None:
    def factory(arc_id: str, simulate: bool, budget: producer.Budget) -> Owner:
        owner = Owner(arc_id, simulate)
        if simulate:
            setattr(owner.propagation_results, name, value)
        return owner

    packet = _produce(factory)
    assert packet["status"] == "failed" and "metadata failed" in packet["failure"]
    assert [row["id"] for row in packet["calls"]] == ["never-run"]
    assert packet["counts"]["factory_attempts"] == 2
    assert packet["counts"]["visitor_calls"] == 1


@pytest.mark.parametrize("name,value", [
    ("termination_reason", "runtime_error_caught_in_propagation"),
    ("terminated_on_exact_condition", False), ("terminated_on_exact_condition", 1),
])
def test_wrong_termination_is_not_performed_success(name: str, value: object) -> None:
    def factory(arc_id: str, simulate: bool, budget: producer.Budget) -> Owner:
        owner = Owner(arc_id, simulate)
        if simulate:
            setattr(owner.propagation_results.termination_details, name, value)
        return owner

    packet = _produce(factory)
    assert packet["status"] == "failed"
    assert packet["counts"]["visitor_calls"] == 1


@pytest.mark.parametrize("kind", ["factory", "missing-method", "unexpected-refusal", "missing-refusal"])
def test_first_failure_preserves_partial_counts_without_second_attempt(kind: str) -> None:
    invoked: list[str] = []

    class BadOwner(Owner):
        def _ariadna_original_endpoint(self, forward: bool, schema: str) -> object:
            if kind == "unexpected-refusal":
                raise RuntimeError("first original defect")
            if kind == "missing-refusal":
                return (0, 0.0, _INITIAL)
            return super()._ariadna_original_endpoint(forward, schema)

    def factory(arc_id: str, simulate: bool, budget: producer.Budget) -> object:
        invoked.append(arc_id)
        if kind == "factory":
            raise RuntimeError("first original defect")
        if kind == "missing-method":
            return object()
        return BadOwner(arc_id, simulate)

    packet = _produce(factory)
    assert packet["status"] == "failed" and packet["failure"]
    assert invoked == ["never-run"]
    assert packet["counts"]["factory_attempts"] == 1
    assert packet["counts"]["integration_attempts"] == 0


@pytest.mark.parametrize("value", [
    [0, 0.0, _INITIAL], (False, 0.0, _INITIAL), (1, 0.0, _INITIAL),
    (0, 1.0, _INITIAL), (0, math.nan, _INITIAL), (0, 0, _INITIAL),
    (0, 0.0, list(_INITIAL)), (0, 0.0, _INITIAL[:-1]),
    (0, 0.0, (math.inf,) + _INITIAL[1:]), (0, 0.0, (True,) + _INITIAL[1:]),
])
def test_nonprimitive_or_bad_original_endpoint_is_rejected(value: object) -> None:
    class BadOwner(Owner):
        def _ariadna_original_endpoint(self, forward: bool, schema: str) -> object:
            if self.propagation_results.propagation_is_performed:
                return value
            return super()._ariadna_original_endpoint(forward, schema)

    packet = _produce(lambda arc_id, simulate, budget: BadOwner(arc_id, simulate))
    assert packet["status"] == "failed"
    assert packet["counts"]["factory_attempts"] == 2
    assert packet["counts"]["integration_attempts"] == 1


def test_clear_result_must_reject_even_though_performed_stays_true() -> None:
    class BadClearOwner(Owner):
        def __init__(self, arc_id: str, simulate: bool) -> None:
            super().__init__(arc_id, simulate)
            self.propagation_results.clear_data = lambda: None

    packet = _produce(lambda arc_id, simulate, budget: BadClearOwner(arc_id, simulate))
    assert packet["status"] == "failed" and "expected refusal missing" in packet["failure"]
    assert packet["counts"]["factory_attempts"] == 2
    assert packet["counts"]["visitor_calls"] == 6


def test_retained_bound_method_must_return_identical_words() -> None:
    class ChangedOwner(Owner):
        def __init__(self, arc_id: str, simulate: bool) -> None:
            super().__init__(arc_id, simulate)
            self.calls = 0

        def _ariadna_original_endpoint(self, forward: bool, schema: str) -> object:
            self.calls += 1
            row = super()._ariadna_original_endpoint(forward, schema)
            if self.calls == 4:
                return row[:2] + ((_END[0], _END[1] + 1.0) + _END[2:],)
            return row

    packet = _produce(lambda arc_id, simulate, budget: ChangedOwner(arc_id, simulate))
    assert packet["status"] == "failed" and "changed terminal words" in packet["failure"]
    assert packet["counts"]["visitor_calls"] == 5


@pytest.mark.parametrize("name,method,maximum", [
    ("factory_attempts", "charge_factory", 3),
    ("integration_attempts", "charge_factory", 2),
    ("visitor_calls", "charge_visitor", 8),
    ("acceleration_callbacks", "charge_acceleration", 100000),
])
def test_precharged_counter_caps_refuse_before_additional_work(name: str, method: str, maximum: int) -> None:
    budget = producer.Budget(0.0, Clock())
    setattr(budget, name, maximum)
    operation = getattr(budget, method)
    with pytest.raises(producer.FixtureError, match="cap"):
        operation(name == "integration_attempts") if method == "charge_factory" else operation()
    assert getattr(budget, name) == maximum and budget.failed
    with pytest.raises(producer.FixtureError, match="already failed"):
        budget.check()


def test_full_acceleration_callback_volume_and_one_denied_entry() -> None:
    budget = producer.Budget(0.0, Clock())
    for _ in range(100000):
        budget.charge_acceleration()
    assert budget.acceleration_callbacks == 100000
    with pytest.raises(producer.FixtureError, match="100000"):
        budget.charge_acceleration()
    assert budget.acceleration_callbacks == 100000


@pytest.mark.parametrize("value", [-1.0, 45.0, math.nan, math.inf, True])
def test_invalid_exhausted_or_backwards_clock_refuses_before_factory(value: object) -> None:
    clock = Clock(value)
    budget = producer.Budget(0.0, clock)
    invoked: list[str] = []

    def factory(arc_id: str, simulate: bool, budget: producer.Budget) -> Owner:
        invoked.append(arc_id)
        return Owner(arc_id, simulate)

    packet = _produce(factory, budget)
    assert packet["status"] == "failed" and not invoked
    assert packet["counts"]["factory_attempts"] == 0


def test_clock_cannot_move_backwards_between_calls() -> None:
    clock = Clock(10.0)
    budget = producer.Budget(0.0, clock)
    budget.check()
    clock.value = 9.0
    with pytest.raises(producer.FixtureError, match="backwards"):
        budget.check()


def test_injected_path_never_imports_private_native_context(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden() -> list[int]:
        raise AssertionError("new native packet is forbidden")

    monkeypatch.setattr(producer, "_native_context", forbidden)
    monkeypatch.setattr(producer, "_native_factory", forbidden)
    assert _produce()["status"] == "passed"


@pytest.mark.parametrize("reverse,simulate,defect", [
    (False, False, None), (False, True, None), (True, True, None),
    (False, True, "wrong-type"), (False, True, "two-entries"),
    (False, True, "wrong-translation"), (False, True, "wrong-mass"),
    (False, True, "wrong-frame"),
])
def test_native_settings_wiring_uses_only_fabricated_modules(
        monkeypatch: pytest.MonkeyPatch, reverse: bool, simulate: bool,
        defect: str | None) -> None:
    from space_nav import trajectory
    captured: dict[str, Any] = {}
    body = SimpleNamespace(constant_mass=None)
    settings = SimpleNamespace(add_empty_settings=lambda name: captured.setdefault("body", name),
                               get=lambda name: body)
    bodies = SimpleNamespace(global_frame_origin=lambda: "Moon" if defect == "wrong-frame" else "SSB",
                             global_frame_orientation=lambda: "J2000")
    processing = SimpleNamespace(clear_numerical_solution=True, set_integrated_result=True)
    initial = _END if reverse else _INITIAL
    type_settings = {"translation": [SimpleNamespace(initial_states=initial[:6])],
                     "mass": [SimpleNamespace(initial_states=(initial[6],))]}
    if defect == "wrong-type":
        type_settings["rotation"] = type_settings.pop("mass")
    elif defect == "two-entries":
        type_settings["mass"] *= 2
    elif defect == "wrong-translation":
        type_settings["translation"][0].initial_states = initial[:5]
    elif defect == "wrong-mass":
        type_settings["mass"][0].initial_states = (1999.0,)
    coupled = SimpleNamespace(processing_settings=processing,
                              propagator_settings_per_type=type_settings)
    sentinel = object()

    def body_settings(origin: str, orientation: str) -> object:
        captured["frame"] = (origin, orientation)
        return settings

    def acceleration_model(bodies_in: object, forces: object, propagated: object, central: object) -> object:
        captured["forces"] = (bodies_in, forces, propagated, central)
        return "acceleration-model"

    def make_integrator(candidate: str, mode: str, profile: object) -> object:
        captured["integrator"] = (candidate, mode, profile)
        return "integrator"

    def make_coupled(*args: object, **kwargs: object) -> object:
        captured["coupled"] = (args, kwargs)
        return coupled

    def make_simulator(bodies_in: object, settings_in: object, **kwargs: object) -> object:
        captured["factory"] = (bodies_in, settings_in, kwargs)
        return sentinel

    environment = SimpleNamespace(BodyListSettings=body_settings,
                                  create_system_of_bodies=lambda value: bodies)
    propagation_setup = SimpleNamespace(
        acceleration=SimpleNamespace(custom_acceleration=lambda callback: callback),
        create_acceleration_models=acceleration_model,
        propagator=SimpleNamespace(time_termination=lambda stop, **kwargs: (stop, kwargs),
                                   translational_type="translation", mass_type="mass"),
    )
    dynamics = SimpleNamespace(environment_setup=environment, propagation_setup=propagation_setup,
                               simulator=SimpleNamespace(create_dynamics_simulator=make_simulator))
    class Array(tuple):
        def reshape(self, count: int) -> Array:
            assert count == -1
            return self

    monkeypatch.setitem(sys.modules, "numpy", SimpleNamespace(__version__="1.26.4", asarray=Array))
    monkeypatch.setitem(sys.modules, "tudatpy", SimpleNamespace(__version__="1.0.0"))
    monkeypatch.setitem(sys.modules, "tudatpy.dynamics", dynamics)
    monkeypatch.setattr(trajectory, "_build_integrator_from_profile", make_integrator)
    monkeypatch.setattr(trajectory, "_build_coupled_arc_settings", make_coupled)
    budget = producer.Budget(0.0, Clock())
    arc_id = "reverse" if reverse else ("forward" if simulate else "never-run")
    if defect is not None:
        with pytest.raises(producer.FixtureError, match="actual native"):
            producer._native_factory(arc_id, simulate, budget)
        assert "factory" not in captured
        return
    result = producer._native_factory(arc_id, simulate, budget)
    assert result is sentinel
    assert captured["frame"] == ("SSB", "J2000") and captured["body"] == "Spacecraft"
    assert body.constant_mass == 2000.0
    assert processing.clear_numerical_solution is False and processing.set_integrated_result is False
    assert captured["factory"] == (bodies, coupled, {"simulate_dynamics_on_creation": simulate})
    args, kwargs = captured["coupled"]
    assert args[3:6] == ((_END if reverse else _INITIAL)[:6], 2000.0, 1000.0 if reverse else 0.0)
    assert kwargs == {"thrust_enabled": False}
    assert args[7] == (0.0 if reverse else 1000.0, {"terminate_exactly_on_final_condition": True})
    callback = captured["forces"][1]["Spacecraft"]["Spacecraft"][0]
    assert callback(50.0) == (0.0, 0.1, 0.0) and budget.acceleration_callbacks == 1
    assert captured["integrator"][2]["initial_step_s"] == (-75.0 if reverse else 75.0)


def test_native_context_refuses_operational_fallback_without_importing_native_modules(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kernel = tmp_path / "fabricated-kernel.so"
    kernel.write_bytes(b"fabricated bytes; never a dynamic library")
    dynamics = SimpleNamespace(simulator=SimpleNamespace(_ariadna_endpoint_native_context=(53, 53, 8)))
    monkeypatch.setitem(sys.modules, "tudatpy", SimpleNamespace(
        kernel=SimpleNamespace(__file__=str(kernel), dynamics=dynamics)))
    monkeypatch.setitem(sys.modules, "tudatpy.dynamics", dynamics)
    with pytest.raises(producer.FixtureError, match="private kernel identity mismatch"):
        producer._native_context()
    monkeypatch.setattr(producer, "_KERNEL_SHA256", hashlib.sha256(kernel.read_bytes()).hexdigest())
    assert producer._native_context() == [53, 53, 8]
    dynamics.simulator._ariadna_endpoint_native_context = (64, 53, 16)
    with pytest.raises(producer.FixtureError, match="context mismatch"):
        producer._native_context()


def test_results_alias_alone_does_not_own_the_fabricated_simulator() -> None:
    owner = Owner("forward", True)
    results = owner.propagation_results
    reference = weakref.ref(owner)
    del owner
    assert reference() is None
    assert not results.cleared


def test_retained_bound_method_alone_owns_fabricated_simulator() -> None:
    owner = Owner("forward", True)
    results = owner.propagation_results
    method = owner._ariadna_original_endpoint
    reference = weakref.ref(owner)
    del owner
    assert reference() is not None
    assert method(True, producer.SCHEMA) == (0, 1000.0, _END)
    del method
    assert reference() is None
    results.clear_data()
    assert results.cleared


def test_producer_fake_chain_passes_separate_independent_polynomial_auditor() -> None:
    from space_nav._owner_endpoint_audit import audit
    packet = _produce()
    result = audit(packet, clock=Clock())
    assert result["status"] == "passed"
    assert result["mode"] == "injected" and result["physical_admission"] == "unavailable"


@pytest.mark.parametrize("propagated", [False, True])
def test_wrong_type_prefix_with_valid_body_suffix_is_rejected(propagated: bool) -> None:
    rows = (_PROPAGATED if propagated else _METADATA).copy()
    rows[(0, 6)] = rows[(0, 6)].replace("Translational state", "Mass state")
    with pytest.raises(producer.FixtureError, match="metadata meaning"):
        producer._ids(rows, propagated=propagated)


@pytest.mark.parametrize("key", [(False, 6), (0.0, 6), (0, 6.0)])
def test_metadata_does_not_relabel_bool_or_float_keys_as_integer_indices(key: object) -> None:
    rows = _METADATA.copy()
    del rows[(0, 6)]
    rows[key] = _METADATA[(0, 6)]
    with pytest.raises(producer.FixtureError, match="integer pairs"):
        producer._ids(rows, propagated=False)
