"""Independent literal artificial packets; no producer or native execution."""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from space_nav import _owner_endpoint_audit as candidate


_SCHEMA = "cartesian-position-m_velocity-m-s_mass-kg"
_FORWARD = (10000000.0, 0.0, 0.0, 0.0, 1000.0, 0.0, 2000.0)
_REVERSE = (10000000.0, 1050000.0, 0.0, 0.0, 1100.0, 0.0, 2000.0)


def _endpoint(epoch: int, state: tuple[float, ...]) -> dict[str, object]:
    return {"hour": 0, "remainder_hex": float(epoch).hex(),
            "state_hex": [value.hex() for value in state]}


def _metadata() -> dict[str, object]:
    return {
        "processed_state_ids": [
            {"start": 0, "size": 6,
             "description": "Translational state, in Cartesian elements, of body Spacecraft w.r.t. SSB"},
            {"start": 6, "size": 1, "description": "Mass state of body Spacecraft"}],
        "propagated_state_ids": [
            {"start": 0, "size": 6,
             "description": "Translational state (Cowell formulation) of body Spacecraft w.r.t. SSB"},
            {"start": 6, "size": 1, "description": "Mass state of body Spacecraft"}],
        "propagated_state_vector_length": 7, "propagation_is_performed": True,
        "integration_completed_successfully": True,
        "termination_reason": "termination_condition_reached",
        "terminated_on_exact_condition": True,
        "clear_numerical_solution": False, "set_integrated_result": False,
        "origin": "SSB", "orientation": "J2000",
    }


def packet() -> dict[str, Any]:
    """Full fixed packet from independently chosen literal polynomial endpoints."""
    forward_start, forward_end = _endpoint(0, _FORWARD), _endpoint(1000, _REVERSE)
    reverse_end, reverse_start = _endpoint(0, _FORWARD), _endpoint(1000, _REVERSE)
    calls = []
    for name, owner, selector, endpoint in (
        ("never-run", "never-run", True, None),
        ("forward-start", "forward", False, forward_start),
        ("forward-end", "forward", True, forward_end),
        ("wrong-schema", "forward", True, None),
        ("retained-bound", "forward", True, forward_end),
        ("cleared", "forward", True, None),
        ("reverse-end", "reverse", False, reverse_end),
        ("reverse-start", "reverse", True, reverse_start),
    ):
        wrong = name == "wrong-schema"
        calls.append({
            "id": name, "owner": owner, "selector": selector,
            "schema": "invalid" if wrong else _SCHEMA,
            "outcome": "refused" if endpoint is None else "accepted",
            "endpoint": deepcopy(endpoint),
            "exception": ({"type": "ValueError" if wrong else "RuntimeError",
                           "message": ("explicit Cartesian position/velocity/mass schema required"
                                       if wrong else "completed original results unavailable")}
                          if endpoint is None else None),
        })
    arcs = []
    for direction, start, end, initial in (("forward", 0, 1000, _FORWARD),
                                            ("reverse", 1000, 0, _REVERSE)):
        profile = {
            "coefficient_set": "rkdp_87", "relative_tolerance": 1e-13,
            "absolute_tolerances_si": [1e-5] * 3 + [1e-8] * 3 + [1e-11],
            "initial_step_s": 75.0 if direction == "forward" else -75.0,
            "minimum_step_s": 1e-5, "maximum_step_s": 21600.0,
            "assess_termination_on_minor_steps": False,
            "minimum_step_handling": "throw_exception_below_minimum",
            "accept_infinity_step": False, "accept_nan_step": False,
        }
        arcs.append({"id": direction, "start_s": start, "end_s": end,
                     "initial_state_hex": [value.hex() for value in initial],
                     "integrator": profile, "metadata": _metadata()})
    source = Path(candidate.__file__).parent
    return {
        "schema": "ariadna-owner-fixture-v1", "scope": "synthetic-owner-conformance-only",
        "frame": "SYNTHETIC_INERTIAL", "time_scale": "elapsed_seconds", "mode": "injected",
        "status": "passed", "failure": None, "native_context": [53, 53, 8],
        "calls": calls, "arcs": arcs,
        "retained_rows_after_clear": {"forward-start": deepcopy(forward_start),
                                      "forward-end": deepcopy(forward_end),
                                      "retained-bound": deepcopy(forward_end)},
        "counts": {"factory_attempts": 3, "integration_attempts": 2, "visitor_calls": 8,
                   "acceleration_callbacks": 12, "native_reported_function_evaluations": [6, 6],
                   "spice_queries": 0, "kernel_reads": 0, "real_archive_reads": 0,
                   "optimizer_entries": 0},
        "provenance": {key: sha256((source / name).read_bytes()).hexdigest() for key, name in (
            ("producer_sha256", "_owner_endpoint_fixture.py"),
            ("auditor_sha256", "_owner_endpoint_audit.py"), ("trajectory_sha256", "trajectory.py"))},
    }


def _audit(value: object) -> dict[str, object]:
    return candidate.audit(value, deadline_s=10.0, clock=lambda: 0.0)


def _terminal(value: dict[str, Any], direction: str, component: int, number: float) -> None:
    row = value["calls"][2 if direction == "forward" else 6]["endpoint"]
    row["state_hex"][component] = number.hex()
    if direction == "forward":
        value["calls"][4]["endpoint"] = deepcopy(row)
        for name in ("forward-end", "retained-bound"):
            value["retained_rows_after_clear"][name] = deepcopy(row)


def test_literal_packet_passes_independent_binary_word_polynomials() -> None:
    value = packet()
    result = _audit(value)
    assert result["status"] == "passed" and result["mode"] == "injected"
    assert result["calls_checked"] == 8 and result["analytic_arcs_checked"] == 2
    assert result["physical_admission"] == "unavailable"
    assert {entry["id"] for entry in result["gates"]} == {"forward", "reverse"}
    # Binary0.1 is deliberately not rational1/10; audit does not accept a decimal oracle.
    assert Fraction(0.1) != Fraction(1, 10)
    for row in result["gates"]:
        assert row["position_error_squared_m2"][0] > 0
        assert row["velocity_error_squared_m2_s2"][0] > 0
        assert row["mass_error_kg"] == [0, 1]


@pytest.mark.parametrize("mode", ["native", "injected"])
def test_mode_is_preserved_without_promoting_saved_claims(mode: str) -> None:
    value = packet()
    value["mode"] = mode
    result = _audit(value)
    assert result["mode"] == mode and result["physical_admission"] == "unavailable"


@pytest.mark.parametrize("key,value", [
    ("status", "failed"), ("failure", "partial"), ("mode", "physical"),
    ("frame", "J2000"), ("time_scale", "TDB"), ("native_context", [64, 53, 16]),
    ("scope", "mission"), ("schema", "wrong"),
])
def test_top_level_scope_status_and_context_are_fixed(key: str, value: object) -> None:
    source = packet()
    source[key] = value
    with pytest.raises(candidate.OracleError):
        _audit(source)


@pytest.mark.parametrize("missing", ["calls", "arcs", "provenance", "counts", "retained_rows_after_clear"])
def test_missing_complete_evidence_is_not_a_passing_packet(missing: str) -> None:
    source = packet()
    del source[missing]
    with pytest.raises(candidate.OracleError, match="fields"):
        _audit(source)


@pytest.mark.parametrize("mutate", [
    lambda p: p["calls"].reverse(),
    lambda p: p["calls"][0].update(selector=False),
    lambda p: p["calls"][3].update(schema=_SCHEMA),
    lambda p: p["calls"][5]["exception"].update(type="ValueError"),
    lambda p: p["calls"][0]["exception"].update(message="different"),
    lambda p: p["calls"][2].update(owner="reverse"),
    lambda p: p["calls"].pop(),
    lambda p: p["calls"][1].update(outcome="refused"),
    lambda p: p["calls"][0].update(endpoint={}),
    lambda p: p["calls"][1].update(exception={"type": "RuntimeError", "message": "x"}),
])
def test_eight_call_identity_order_schema_and_exception_tampering(mutate: Any) -> None:
    source = packet()
    mutate(source)
    with pytest.raises(candidate.OracleError):
        _audit(source)


@pytest.mark.parametrize("word", ["nan", "inf", "-inf", "0x1p0", "1", True, "x" * 33,
                                   "0x1p+999999999999999999999999"])
def test_invalid_or_noncanonical_words_fail_before_fraction_arithmetic(word: object) -> None:
    source = packet()
    source["calls"][2]["endpoint"]["state_hex"][0] = word
    with pytest.raises(candidate.OracleError, match="hex"):
        _audit(source)


@pytest.mark.parametrize("hour,remainder", [(True, 0.0), (0.0, 0.0), (1, 0.0), (0, 1000.0)])
def test_integer_hour_and_selected_epoch_are_checked(hour: object, remainder: float) -> None:
    source = packet()
    source["calls"][1]["endpoint"].update(hour=hour, remainder_hex=remainder.hex())
    with pytest.raises(candidate.OracleError):
        _audit(source)


def test_zero_sign_is_retained_but_not_used_as_native_time_identity() -> None:
    source = packet()
    source["calls"][1]["endpoint"]["remainder_hex"] = (-0.0).hex()
    source["retained_rows_after_clear"]["forward-start"] = deepcopy(source["calls"][1]["endpoint"])
    result = _audit(source)
    assert result["status"] == "passed"
    source["retained_rows_after_clear"]["forward-start"]["remainder_hex"] = (0.0).hex()
    with pytest.raises(candidate.OracleError, match="retained_rows_after_clear"):
        _audit(source)


@pytest.mark.parametrize("direction,component,value", [
    ("forward", 0, 10000000.01), ("forward", 4, 1100.00001), ("forward", 6, 2000.000001),
    ("reverse", 0, 10000000.01), ("reverse", 4, 1100.0), ("reverse", 6, 2000.000001),
])
def test_terminal_polynomial_uses_own_start_and_all_si_gates(
        direction: str, component: int, value: float) -> None:
    source = packet()
    _terminal(source, direction, component, value)
    with pytest.raises(candidate.OracleError, match="exceeds"):
        _audit(source)


@pytest.mark.parametrize("components,shift,error", [((0, 2), 0.0008, "position norm"),
                                                      ((3, 5), 0.0000008, "velocity norm")])
def test_euclidean_norm_rejects_two_individually_small_component_errors(
        components: tuple[int, int], shift: float, error: str) -> None:
    source = packet()
    for component in components:
        _terminal(source, "forward", component, _REVERSE[component] + shift)
    with pytest.raises(candidate.OracleError, match=error):
        _audit(source)


def test_position_boundary_uses_exact_rational_squared_gate() -> None:
    source = packet()
    _terminal(source, "forward", 2, math.nextafter(0.001, 0.0))
    assert _audit(source)["status"] == "passed"
    _terminal(source, "forward", 2, math.nextafter(0.001, math.inf))
    with pytest.raises(candidate.OracleError, match="position norm"):
        _audit(source)


@pytest.mark.parametrize("name,index", [("forward", 1), ("reverse", 7)])
def test_initial_words_are_exact_even_when_change_is_within_terminal_tolerance(name: str, index: int) -> None:
    source = packet()
    source["calls"][index]["endpoint"]["state_hex"][0] = math.nextafter(1e7, math.inf).hex()
    with pytest.raises(candidate.OracleError, match="initial words"):
        _audit(source)


@pytest.mark.parametrize("key,value", [
    ("propagation_is_performed", False), ("integration_completed_successfully", False),
    ("terminated_on_exact_condition", False), ("termination_reason", "runtime_error_caught_in_propagation"),
    ("clear_numerical_solution", True), ("set_integrated_result", True),
    ("origin", "Earth"), ("orientation", "ECLIPJ2000"), ("propagated_state_vector_length", 6),
])
def test_success_retention_termination_and_frame_metadata_required(key: str, value: object) -> None:
    source = packet()
    source["arcs"][0]["metadata"][key] = value
    with pytest.raises(candidate.OracleError, match="metadata"):
        _audit(source)


@pytest.mark.parametrize("name,index,key,value", [
    ("processed_state_ids", 0, "start", 1), ("processed_state_ids", 0, "size", True),
    ("processed_state_ids", 0, "description", "translation of body Mars"),
    ("processed_state_ids", 0, "description", "Wrong state, in Cartesian elements, of body Spacecraft w.r.t. SSB"),
    ("processed_state_ids", 1, "description", "Wrong state of body Spacecraft"),
    ("propagated_state_ids", 0, "description", "Translational state (wrong formulation) of body Spacecraft w.r.t. SSB"),
    ("processed_state_ids", 1, "description", "mass of body Mars"),
    ("propagated_state_ids", 0, "description", "x" * 257),
    ("propagated_state_ids", 0, "description", "x\n (Cowell formulation) of body Spacecraft w.r.t. SSB"),
    ("propagated_state_ids", 0, "description", "translation of body Spacecraft w.r.t. SSB"),
])
def test_actual_processed_and_propagated_state_ids_ranges_and_body_meaning(
        name: str, index: int, key: str, value: object) -> None:
    source = packet()
    source["arcs"][0]["metadata"][name][index][key] = value
    with pytest.raises(candidate.OracleError, match="metadata"):
        _audit(source)


@pytest.mark.parametrize("mutate", [
    lambda p: p["arcs"][1].update(initial_state_hex=p["arcs"][0]["initial_state_hex"]),
    lambda p: p["arcs"][1].update(start_s=0),
    lambda p: p["arcs"][1]["integrator"].update(initial_step_s=75),
    lambda p: p["arcs"][0]["integrator"].update(coefficient_set="rkf_78"),
    lambda p: p["arcs"][0]["integrator"].update(relative_tolerance=1e-10),
    lambda p: p["calls"][4]["endpoint"]["state_hex"].__setitem__(0, (9999999.0).hex()),
    lambda p: p["retained_rows_after_clear"]["forward-start"]["state_hex"].__setitem__(6, (1999.0).hex()),
])
def test_arc_and_lifecycle_evidence_tampering(mutate: Any) -> None:
    source = packet()
    mutate(source)
    with pytest.raises(candidate.OracleError):
        _audit(source)


@pytest.mark.parametrize("key,value", [
    ("factory_attempts", 4), ("integration_attempts", 1), ("visitor_calls", 7),
    ("acceleration_callbacks", -1), ("acceleration_callbacks", 100001),
    ("acceleration_callbacks", True), ("spice_queries", 1), ("kernel_reads", 1),
    ("real_archive_reads", 1), ("optimizer_entries", 1),
    ("native_reported_function_evaluations", [1, -1]),
    ("native_reported_function_evaluations", [True, 1]),
])
def test_exact_attempt_counts_and_forbidden_work_and_callback_cap(key: str, value: object) -> None:
    source = packet()
    source["counts"][key] = value
    with pytest.raises(candidate.OracleError):
        _audit(source)


def test_full_callback_cap_is_a_provider_counter_not_a_native_rhs_claim() -> None:
    source = packet()
    source["counts"]["acceleration_callbacks"] = 100000
    source["counts"]["native_reported_function_evaluations"] = [100007, 100013]
    assert _audit(source)["status"] == "passed"


@pytest.mark.parametrize("key", ["producer_sha256", "auditor_sha256", "trajectory_sha256"])
def test_valid_digest_shape_does_not_self_certify_source_identity(key: str) -> None:
    source = packet()
    source["provenance"][key] = "f" * 64
    with pytest.raises(candidate.OracleError, match="source differs"):
        _audit(source)


def test_partial_or_oversized_structured_input_and_nonfinite_json() -> None:
    source = packet()
    source["failure"] = "x" * (1024 * 1024)
    with pytest.raises(candidate.OracleError, match="byte cap"):
        _audit(source)
    source = packet()
    source["counts"]["acceleration_callbacks"] = math.inf
    with pytest.raises(candidate.OracleError, match="finite acyclic JSON"):
        _audit(source)
    source = packet()
    source["failure"] = source
    with pytest.raises(candidate.OracleError, match="finite acyclic JSON"):
        _audit(source)


@pytest.mark.parametrize("clock,deadline,match", [
    (lambda: 10.0, 10.0, "deadline"), (lambda: math.nan, 10.0, "finite"),
    (lambda: True, 10.0, "nonboolean"), (lambda: 0.0, True, "nonboolean"),
])
def test_invalid_or_exhausted_deadline_refuses_before_packet_work(
        clock: Any, deadline: object, match: str) -> None:
    with pytest.raises(candidate.OracleError, match=match):
        candidate.audit({}, deadline_s=deadline, clock=clock)


def test_clock_cannot_move_backwards_or_extend_its_ten_second_window() -> None:
    values = iter((0.0, 0.0, -0.1))
    with pytest.raises(candidate.OracleError, match="backwards"):
        candidate.audit(packet(), deadline_s=10.0, clock=lambda: next(values))
    values = iter((0.0, 0.0, 10.0))
    with pytest.raises(candidate.OracleError, match="deadline"):
        candidate.audit(packet(), deadline_s=100.0, clock=lambda: next(values))


def test_cold_auditor_import_never_loads_producer_or_scientific_modules() -> None:
    code = (
        "import importlib.util,sys; "
        f"spec=importlib.util.spec_from_file_location('owner_audit',{candidate.__file__!r}); "
        "module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
        "assert not any(name.split('.')[0] in {'numpy','scipy','tudatpy','spiceypy'} "
        "or name.endswith('_owner_endpoint_fixture') for name in sys.modules)"
    )
    result = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert json.loads(json.dumps(packet()))["mode"] == "injected"
