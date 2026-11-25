"""Independent stdlib audit of ADR0267's fixed serial-owner fixture.

Saved words qualify synthetic fixture conformance only, never native event identity,
concurrency, prior arithmetic, event carry or physical trajectory admission.
"""

from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from time import monotonic
from typing import cast


class OracleError(ValueError):
    """The fixed owner packet failed independent conformance or admission."""


_SCHEMA = "cartesian-position-m_velocity-m-s_mass-kg"
_INITIAL = {
    "forward": (10000000.0, 0.0, 0.0, 0.0, 1000.0, 0.0, 2000.0),
    "reverse": (10000000.0, 1050000.0, 0.0, 0.0, 1100.0, 0.0, 2000.0),
}
_CALLS = (
    ("never-run", "never-run", True, "refused", None),
    ("forward-start", "forward", False, "accepted", 0),
    ("forward-end", "forward", True, "accepted", 1000),
    ("wrong-schema", "forward", True, "refused", None),
    ("retained-bound", "forward", True, "accepted", 1000),
    ("cleared", "forward", True, "refused", None),
    ("reverse-end", "reverse", False, "accepted", 0),
    ("reverse-start", "reverse", True, "accepted", 1000),
)
_METADATA_KEYS = {
    "processed_state_ids", "propagated_state_ids", "propagated_state_vector_length",
    "propagation_is_performed", "integration_completed_successfully", "termination_reason",
    "clear_numerical_solution", "set_integrated_result", "origin", "orientation",
    "terminated_on_exact_condition",
}
_TOP_KEYS = {
    "schema", "scope", "frame", "time_scale", "mode", "status", "failure",
    "native_context", "calls", "arcs", "retained_rows_after_clear", "counts", "provenance",
}


def _need(condition: bool, field: str) -> None:
    if not condition:
        raise OracleError(field)


def _mapping(value: object, keys: set[str], field: str) -> dict[str, object]:
    _need(type(value) is dict, field + ": JSON object required")
    result = cast(dict[str, object], value)
    _need(set(result) == keys, field + ": unexpected or missing fields")
    return result


def _list(value: object, length: int, field: str) -> list[object]:
    _need(type(value) is list and len(cast(list[object], value)) == length,
          field + f": {length}-entry list required")
    return cast(list[object], value)


def _number(value: object, field: str) -> float:
    _need(type(value) in (int, float), field + ": finite nonboolean number required")
    try:
        result = float(cast(float, value))
    except (ValueError, OverflowError) as exc:
        raise OracleError(field + ": finite number required") from exc
    _need(math.isfinite(result), field + ": finite number required")
    return result


def _same(actual: object, expected: object, field: str) -> None:
    if type(expected) is dict:
        desired = cast(dict[str, object], expected)
        source = _mapping(actual, set(desired), field)
        for name, value in desired.items():
            _same(source[name], value, field + "." + name)
    elif type(expected) in (list, tuple):
        desired_list = cast(list[object], expected)
        source_list = _list(actual, len(desired_list), field)
        for index, value in enumerate(desired_list):
            _same(source_list[index], value, field + f"[{index}]")
    elif type(expected) in (float, int):
        _need(_number(actual, field) == expected, field + ": fixed value differs")
    else:
        _need(type(actual) is type(expected) and actual == expected,
              field + ": fixed value differs")


def _word(value: object, field: str) -> float:
    _need(type(value) is str and len(cast(str, value)) <= 32,
          field + ": bounded canonical float hex required")
    try:
        result = float.fromhex(cast(str, value))
    except (ValueError, OverflowError) as exc:
        raise OracleError(field + ": finite canonical float hex required") from exc
    _need(math.isfinite(result) and result.hex() == value,
          field + ": finite canonical float hex required")
    return result


def _state(value: object, field: str) -> tuple[float, ...]:
    return tuple(_word(item, field + f"[{i}]")
                 for i, item in enumerate(_list(value, 7, field)))


def _metadata(value: object, field: str) -> None:
    metadata = _mapping(value, _METADATA_KEYS, field)
    _same({key: item for key, item in metadata.items()
           if key not in {"processed_state_ids", "propagated_state_ids"}}, {
        "propagated_state_vector_length": 7, "propagation_is_performed": True,
        "integration_completed_successfully": True,
        "termination_reason": "termination_condition_reached",
        "terminated_on_exact_condition": True,
        "clear_numerical_solution": False, "set_integrated_result": False,
        "origin": "SSB", "orientation": "J2000",
    }, field)
    for name in ("processed_state_ids", "propagated_state_ids"):
        entries = _list(metadata[name], 2, field + "." + name)
        for index, (start, size) in enumerate(((0, 6), (6, 1))):
            row = _mapping(entries[index], {"start", "size", "description"}, field + "." + name)
            _need(type(row["start"]) is int and row["start"] == start
                  and type(row["size"]) is int and row["size"] == size,
                  field + "." + name + ": state ranges differ")
            descriptions = {
                "processed_state_ids": (
                    "Translational state, in Cartesian elements, of body Spacecraft w.r.t. SSB",
                    "Mass state of body Spacecraft"),
                "propagated_state_ids": (
                    "Translational state (Cowell formulation) of body Spacecraft w.r.t. SSB",
                    "Mass state of body Spacecraft"),
            }
            _same(row["description"], descriptions[name][index], field + "." + name + ".description")



def _integrator(direction: str) -> dict[str, object]:
    return {
        "coefficient_set": "rkdp_87", "relative_tolerance": 1e-13,
        "absolute_tolerances_si": [1e-5, 1e-5, 1e-5, 1e-8, 1e-8, 1e-8, 1e-11],
        "initial_step_s": 75.0 if direction == "forward" else -75.0,
        "minimum_step_s": 1e-5, "maximum_step_s": 21600.0,
        "assess_termination_on_minor_steps": False,
        "minimum_step_handling": "throw_exception_below_minimum",
        "accept_infinity_step": False, "accept_nan_step": False,
    }


def _fraction(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def audit(packet: object, *, deadline_s: float | None = None,
          clock: Callable[[], float] = monotonic) -> dict[str, object]:
    """Audit complete fixed words with an independent binary-word polynomial.

    The caller must additionally enforce the cold process-group watchdog and raw
    input byte cap. Source hashes bind saved claims, not actual native execution.
    """
    started = _number(clock(), "audit clock")
    finish = started + 10.0 if deadline_s is None else min(
        _number(deadline_s, "audit deadline"), started + 10.0)
    previous = started

    def check() -> None:
        nonlocal previous
        now = _number(clock(), "audit clock")
        _need(now >= previous, "audit clock moved backwards")
        _need(now < finish, "audit deadline exceeded")
        previous = now

    check()
    source = _mapping(packet, _TOP_KEYS, "packet")
    try:
        raw = json.dumps(source, allow_nan=False, sort_keys=True).encode()
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise OracleError("packet: finite acyclic JSON required") from exc
    _need(len(raw) <= 1024 * 1024, "packet: producer byte cap1MiB")
    check()
    for key, expected in {
        "schema": "ariadna-owner-fixture-v1", "scope": "synthetic-owner-conformance-only",
        "frame": "SYNTHETIC_INERTIAL", "time_scale": "elapsed_seconds",
        "status": "passed", "failure": None, "native_context": [53, 53, 8],
    }.items():
        _same(source[key], expected, "packet." + key)
    _need(type(source["mode"]) is str and source["mode"] in {"injected", "native"},
          "packet.mode: explicit injected/native scope required")
    paths = {"producer_sha256": "_owner_endpoint_fixture.py",
             "auditor_sha256": "_owner_endpoint_audit.py", "trajectory_sha256": "trajectory.py"}
    provenance = _mapping(source["provenance"], set(paths), "provenance")
    for key, filename in paths.items():
        check()
        digest = provenance[key]
        _need(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", cast(str, digest)) is not None,
              "provenance." + key + ": SHA256 required")
        try:
            actual = sha256(Path(__file__).with_name(filename).read_bytes()).hexdigest()
        except OSError as exc:
            raise OracleError("provenance source unavailable: " + filename) from exc
        _need(digest == actual, "provenance." + key + ": source differs")
    arcs = _list(source["arcs"], 2, "arcs")
    for index, direction in enumerate(("forward", "reverse")):
        check()
        arc = _mapping(arcs[index], {"id", "start_s", "end_s", "initial_state_hex",
                                    "integrator", "metadata"}, "arcs")
        _same(arc["id"], direction, "arcs.id")
        start, end = (0, 1000) if direction == "forward" else (1000, 0)
        _same(arc["start_s"], start, "arcs.start_s")
        _same(arc["end_s"], end, "arcs.end_s")
        _same(arc["initial_state_hex"], [x.hex() for x in _INITIAL[direction]],
              "arcs.initial_state_hex")
        _same(arc["integrator"], _integrator(direction), "arcs.integrator")
        _metadata(arc["metadata"], "arcs.metadata")
    rows: dict[str, dict[str, object]] = {}
    for value, (name, owner, selector, outcome, epoch) in zip(
            _list(source["calls"], 8, "calls"), _CALLS, strict=True):
        check()
        row = _mapping(value, {"id", "owner", "selector", "schema", "outcome",
                               "endpoint", "exception"}, "calls")
        _same({key: row[key] for key in ("id", "owner", "selector", "schema", "outcome")}, {
            "id": name, "owner": owner, "selector": selector,
            "schema": "invalid" if name == "wrong-schema" else _SCHEMA, "outcome": outcome,
        }, "calls." + name)
        if outcome == "refused":
            _same(row["endpoint"], None, "calls." + name + ".endpoint")
            _same(row["exception"], {
                "type": "ValueError" if name == "wrong-schema" else "RuntimeError",
                "message": ("explicit Cartesian position/velocity/mass schema required"
                            if name == "wrong-schema" else "completed original results unavailable"),
            }, "calls." + name + ".exception")
            continue
        _same(row["exception"], None, "calls." + name + ".exception")
        endpoint = _mapping(row["endpoint"], {"hour", "remainder_hex", "state_hex"},
                            "calls." + name + ".endpoint")
        _need(type(endpoint["hour"]) is int and endpoint["hour"] == 0,
              "endpoint.hour: integer zero required")
        _need(_word(endpoint["remainder_hex"], "endpoint.remainder_hex") == epoch,
              "endpoint.remainder_hex: selected epoch differs")
        _state(endpoint["state_hex"], "endpoint.state_hex")
        rows[name] = endpoint
    for name, direction in (("forward-start", "forward"), ("reverse-start", "reverse")):
        _same(rows[name]["state_hex"], [x.hex() for x in _INITIAL[direction]],
              name + ": initial words changed")
    _same(rows["retained-bound"], rows["forward-end"], "retained bound method row changed")
    retained = _mapping(source["retained_rows_after_clear"], {
        "forward-start", "forward-end", "retained-bound"}, "retained_rows_after_clear")
    for name, endpoint in retained.items():
        _same(endpoint, rows[name], "retained_rows_after_clear." + name)
    errors = []
    for direction, seconds in (("forward", 1000), ("reverse", -1000)):
        check()
        initial = tuple(Fraction(x) for x in _INITIAL[direction])
        acceleration = (Fraction(0), Fraction(0.1), Fraction(0))
        expected = tuple(initial[i] + initial[i + 3] * seconds
                         + acceleration[i] * seconds * seconds / 2 for i in range(3))
        expected += tuple(initial[i + 3] + acceleration[i] * seconds for i in range(3))
        expected += (initial[6],)
        actual = tuple(Fraction(x) for x in _state(rows[direction + "-end"]["state_hex"], direction))
        squared_r = sum((actual[i] - expected[i]) ** 2 for i in range(3))
        squared_v = sum((actual[i] - expected[i]) ** 2 for i in range(3, 6))
        mass_error = abs(actual[6] - expected[6])
        _need(squared_r <= Fraction(1, 1000) ** 2, direction + ": position norm exceeds0.001m")
        _need(squared_v <= Fraction(1, 1000000) ** 2, direction + ": velocity norm exceeds1e-6m/s")
        _need(mass_error <= Fraction(1, 1000000000), direction + ": mass exceeds1e-9kg")
        errors.append({"id": direction, "position_error_squared_m2": _fraction(squared_r),
                       "velocity_error_squared_m2_s2": _fraction(squared_v),
                       "mass_error_kg": _fraction(mass_error)})
    fixed_counts = {"factory_attempts": 3, "integration_attempts": 2, "visitor_calls": 8,
                    "spice_queries": 0, "kernel_reads": 0, "real_archive_reads": 0,
                    "optimizer_entries": 0}
    counts = _mapping(source["counts"], set(fixed_counts) | {
        "acceleration_callbacks", "native_reported_function_evaluations"}, "counts")
    for key, expected_count in fixed_counts.items():
        _need(type(counts[key]) is int and counts[key] == expected_count,
              "counts." + key + ": fixed integer count differs")
    callbacks = counts["acceleration_callbacks"]
    _need(type(callbacks) is int and 0 <= cast(int, callbacks) <= 100000,
          "counts.acceleration_callbacks: cap100000")
    for count in _list(counts["native_reported_function_evaluations"], 2, "native telemetry"):
        _need(type(count) is int and 0 <= cast(int, count), "native telemetry: nonnegative integer required")
    check()
    return {"schema": "ariadna-owner-audit-v1", "status": "passed", "mode": source["mode"],
            "calls_checked": 8, "analytic_arcs_checked": 2, "gates": errors,
            "physical_admission": "unavailable",
            "scope": "Saved serial synthetic owner words only; no native Time identity/carry/concurrency proof.",
            "provenance": dict(provenance)}
