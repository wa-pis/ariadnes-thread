"""Same-probe endpoint consistency, not resource authentication or safety."""

from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path

import pytest

from test_trajectory_error_transport import _coast_error_envelope, _cubic_reference_endpoint


def _check_endpoint_spk_context(binding: dict, context: dict) -> None:
    """Bind retained source records, not all forces or external data authenticity."""
    assert binding["source_spk_context_sha256"] == sha256(json.dumps(context, sort_keys=True, allow_nan=False).encode()).hexdigest()
    for key in ("start_epoch_tdb_s", "end_epoch_tdb_s", "origin", "orientation", "time_scale"):
        assert binding[key] == context[key]
    start, end = map(Fraction, (context["source_domain_start_tdb_s"], context["source_domain_end_tdb_s"]))
    assert start <= Fraction(binding["start_epoch_tdb_s"]) < Fraction(binding["end_epoch_tdb_s"]) <= end
    expected_chains = {"Sun": [10], "Mercury": [1], "Venus": [2], "Earth": [399], "Moon": [301, 399],
                       "Mars": [499, 4], "Jupiter": [599, 5], "Saturn": [699, 6]}
    assert context["body_chains"] == expected_chains
    records = context["selected_records"]
    expected_targets = {target for chain in expected_chains.values() for target in chain}
    assert len(records) == len(expected_targets) == len({record["target"] for record in records})
    by_target = {record["target"]: record for record in records}
    assert set(by_target) == expected_targets
    for chain in expected_chains.values():
        for target, center in zip(chain, chain[1:]+[0], strict=True):
            assert by_target[target]["center"] == center
    for record in records:
        assert record["frame_id"] == 1 and record["spk_type"] in (2, 3)
        assert record["segment_first_word"] <= record["record_first_word"] <= record["record_last_word"] <= record["segment_last_word"]
        size = record["record_last_word"]-record["record_first_word"]+1
        assert type(record["record_index_zero_based"]) is int and record["record_index_zero_based"] >= 0
        assert record["record_first_word"] == record["segment_first_word"]+size*record["record_index_zero_based"]
        assert Fraction(record["segment_start_tdb_s"]) <= start < end <= Fraction(record["segment_end_tdb_s"])
        mid, radius, guard = map(Fraction, (record["record_midpoint_tdb_s"], record["record_radius_s"], record["record_guard_s"]))
        assert guard == 16*Fraction(math.ulp(float(mid))) and radius > guard > 0
        assert mid-radius+guard <= start < end <= mid+radius-guard
    assert by_target[10]["spk_type"] == 2


def _check_endpoint_binding(binding: dict, cubic: dict, transport: dict, clearance: dict) -> None:
    """Reject independently mismatched reports; caller establishes their physics."""
    for field in ("origin", "orientation", "time_scale", "model_id"):
        assert binding[field] == cubic[field] == transport[field] == clearance[field]
    start, end = binding["start_epoch_tdb_s"], binding["end_epoch_tdb_s"]
    assert math.isfinite(start) and math.isfinite(end) and end > start
    assert start == cubic["epoch_tdb_s"] == transport["epoch_tdb_s"] == clearance["start_epoch_tdb_s"]
    assert end == clearance["end_epoch_tdb_s"]
    assert Fraction(end)-Fraction(start) == Fraction(cubic["duration_s"]) == Fraction(transport["duration_s"])
    initial, final = binding["initial_state_m_m_s_kg"], binding["terminal_state_m_m_s_kg"]
    assert len(initial) == len(final) == 7
    assert all(type(value) is float and math.isfinite(value) for value in initial+final)
    assert initial[:6] == cubic["initial_state_m_m_s"]
    assert initial[6] == final[6] == clearance["coast_mass_kg"] >= clearance["dry_mass_kg"] > 0
    assert clearance["thrust_enabled"] is False
    incoming = binding["incoming_error_m_m_s"]
    assert incoming == [cubic["incoming_position_error_upper_m"], cubic["incoming_velocity_error_upper_m_s"]]
    assert incoming == [transport["inputs_si"]["position_error_m"], transport["inputs_si"]["velocity_error_m_s"]]
    assert incoming == [clearance["incoming_position_error_m"], clearance["incoming_velocity_error_m_s"]]
    assert all(type(value) is float and math.isfinite(value) and value >= 0 for value in incoming)
    endpoint = _cubic_reference_endpoint(
        tuple(map(Fraction, initial[:6])), tuple(map(Fraction, cubic["acceleration_m_s2"])),
        tuple(map(Fraction, cubic["monopole_jerk_m_s3"])), cubic["duration_s"],
    )
    assert list(map(str, endpoint)) == cubic["endpoint_exact_m_m_s"]
    residuals = [sum((abs(Fraction(a)-b) for a, b in zip(final[offset:offset+3], endpoint[offset:offset+3], strict=True)), Fraction(0))
                 for offset in (0, 3)]
    rounded = [math.nextafter(float(value), math.inf) if value else 0.0 for value in residuals]
    assert rounded == transport["native_endpoint_residual_m_m_s"]
    assert rounded == [cubic["native_endpoint_position_residual_l1_upper_m"], cubic["native_endpoint_velocity_residual_l1_upper_m_s"]]
    reference_bounds = _coast_error_envelope(cubic["duration_s"], **{key: Fraction(value) for key, value in transport["inputs_si"].items()})
    for index, component in enumerate(("position", "velocity")):
        unit = "m" if index == 0 else "m_s"
        for kind, exact in (("reference", reference_bounds[index]), ("native_endpoint", reference_bounds[index]+Fraction(rounded[index]))):
            reported = math.nextafter(float(exact), math.inf) if exact else 0.0
            assert transport["outward_bounds_si"][f"{kind}_{component}_error_{unit}"] == reported
        assert binding["outgoing_error_m_m_s"][index] == transport["outward_bounds_si"][f"native_endpoint_{component}_error_{unit}"]


def _synthetic_reports() -> tuple[dict, dict, dict, dict]:
    labels = {"origin": "SSB", "orientation": "J2000", "time_scale": "TDB seconds since J2000", "model_id": "analytic-control"}
    residual_p, residual_v = math.nextafter(0.125, math.inf), math.nextafter(0.25, math.inf)
    bounds = {"reference_position_error_m": math.nextafter(0.375, math.inf), "reference_velocity_error_m_s": math.nextafter(0.25, math.inf),
              "native_endpoint_position_error_m": math.nextafter(float(Fraction(0.375)+Fraction(residual_p)), math.inf),
              "native_endpoint_velocity_error_m_s": math.nextafter(float(Fraction(0.25)+Fraction(residual_v)), math.inf)}
    binding = {**labels, "start_epoch_tdb_s": 8.0, "end_epoch_tdb_s": 9.0,
               "initial_state_m_m_s_kg": [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 2.0],
               "terminal_state_m_m_s_kg": [1.125, 0.0, 0.0, 1.25, 0.0, 0.0, 2.0],
               "incoming_error_m_m_s": [0.125, 0.25],
               "outgoing_error_m_m_s": [bounds["native_endpoint_position_error_m"], bounds["native_endpoint_velocity_error_m_s"]]}
    cubic = {**labels, "epoch_tdb_s": 8.0, "duration_s": 1.0, "initial_state_m_m_s": binding["initial_state_m_m_s_kg"][:6],
             "acceleration_m_s2": [0.0]*3, "monopole_jerk_m_s3": [0.0]*3, "endpoint_exact_m_m_s": ["1", "0", "0", "1", "0", "0"],
             "incoming_position_error_upper_m": 0.125, "incoming_velocity_error_upper_m_s": 0.25,
             "native_endpoint_position_residual_l1_upper_m": residual_p, "native_endpoint_velocity_residual_l1_upper_m_s": residual_v}
    transport = {**labels, "epoch_tdb_s": 8.0, "duration_s": 1.0,
                 "inputs_si": {"position_error_m": 0.125, "velocity_error_m_s": 0.25, "position_sensitivity_s_inv2": 0.0,
                               "velocity_sensitivity_s_inv": 0.0, "acceleration_defect_m_s2": 0.0, "acceleration_defect_rate_m_s3": 0.0},
                 "native_endpoint_residual_m_m_s": [residual_p, residual_v], "outward_bounds_si": bounds}
    clearance = {**labels, "start_epoch_tdb_s": 8.0, "end_epoch_tdb_s": 9.0, "coast_mass_kg": 2.0, "dry_mass_kg": 1.0,
                 "thrust_enabled": False, "incoming_position_error_m": 0.125, "incoming_velocity_error_m_s": 0.25}
    return binding, cubic, transport, clearance


def test_endpoint_binding_replays_analytic_control() -> None:
    _check_endpoint_binding(*_synthetic_reports())


def test_endpoint_binding_replays_retained_physical_reports() -> None:
    directory = Path(__file__).with_name("data")
    names = ("fresh_endpoint_binding", "fresh_cubic_reference", "fresh_error_transport", "fresh_conditional_clearance")
    reports = [json.loads((directory / f"m3_{name}.json").read_text())[name] for name in names]
    _check_endpoint_binding(*reports)


def _retained_spk_reports() -> tuple[dict, dict]:
    directory = Path(__file__).with_name("data")
    return tuple(json.loads((directory / f"m3_{name}.json").read_text())[name]
                 for name in ("fresh_endpoint_binding", "fresh_spk_context"))


def test_endpoint_spk_context_replays_retained_records() -> None:
    _check_endpoint_spk_context(*_retained_spk_reports())


def test_endpoint_spk_context_rejects_changed_kernel_identity() -> None:
    binding, context = _retained_spk_reports()
    context["selected_records"][0]["kernel"]["sha256"] = "0"*64
    with pytest.raises(AssertionError):
        _check_endpoint_spk_context(binding, context)


@pytest.mark.parametrize("field,value", [("center", 1), ("frame_id", 2), ("spk_type", 3),
                                       ("record_radius_s", 0.0), ("record_guard_s", 0.0),
                                       ("record_index_zero_based", -1), ("segment_end_tdb_s", 0.0)])
def test_endpoint_spk_context_rejects_inconsistent_record_even_with_new_digest(field: str, value: object) -> None:
    binding, context = _retained_spk_reports()
    sun = next(record for record in context["selected_records"] if record["target"] == 10)
    sun[field] = value
    binding["source_spk_context_sha256"] = sha256(json.dumps(context, sort_keys=True, allow_nan=False).encode()).hexdigest()
    with pytest.raises(AssertionError):
        _check_endpoint_spk_context(binding, context)


@pytest.mark.parametrize("field,index", [("initial_state_m_m_s_kg", 0), ("terminal_state_m_m_s_kg", 0),
                                        ("terminal_state_m_m_s_kg", 3), ("terminal_state_m_m_s_kg", 6),
                                        ("incoming_error_m_m_s", 0), ("incoming_error_m_m_s", 1),
                                        ("outgoing_error_m_m_s", 0), ("outgoing_error_m_m_s", 1)])
def test_endpoint_binding_rejects_changed_vector(field: str, index: int) -> None:
    binding, *reports = deepcopy(_synthetic_reports())
    binding[field][index] += 1.0
    with pytest.raises(AssertionError):
        _check_endpoint_binding(binding, *reports)


@pytest.mark.parametrize("field,value", [("start_epoch_tdb_s", 7.0), ("end_epoch_tdb_s", 10.0), ("model_id", "other"), ("orientation", "other")])
def test_endpoint_binding_rejects_changed_context(field: str, value: object) -> None:
    binding, *reports = _synthetic_reports()
    binding[field] = value
    with pytest.raises(AssertionError):
        _check_endpoint_binding(binding, *reports)
