"""Pure fabricated-packet qualification; no native or mission run is performed."""

import builtins
from decimal import Decimal, ROUND_DOWN, localcontext
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
from time import monotonic
from typing import cast

import pytest

from space_nav import _native_arc_oracle as oracle

ROOT = Path(__file__).resolve().parents[1]


def _event(epoch: int) -> dict[str, object]:
    return {"requested": [epoch, 1], "label_hex": float(epoch).hex(),
            "observed_label_s": float(epoch), "native_equal": True, "residual_s": 0.0}


def _packet() -> dict[str, object]:
    """Invent native telemetry around independent closed-form endpoint values."""
    reference = oracle.reference()
    paths: dict[str, object] = {}
    reported = []
    for path, direction, modes in (("forward", 1, ("departure-burn", "coast", "arrival-burn")),
                                   ("reverse", -1, ("arrival-burn", "coast", "departure-burn"))):
        states = cast(list[list[float]], reference[path + "_states"])
        epochs = cast(list[int], reference[path + "_epochs_s"])
        rows = []
        for index, mode in enumerate(modes):
            functions = 100 + len(reported)
            reported.append(functions)
            rows.append({"mode": mode, "direction": direction,
                         "start_event": _event(epochs[index]), "end_event": _event(epochs[index + 1]),
                         "start_state": states[index].copy(), "end_state": states[index + 1].copy(),
                         "provider_attempts": 10, "native_reported_function_evaluations": functions,
                         "samples_checked": 3})
        paths[path] = rows
    return {"schema": "ariadna-native-conformance-v1", "frame": "SYNTHETIC_INERTIAL",
            "time_scale": "elapsed_seconds", "controls": [0.0, 0.0, 1000.0, 0.0, 0.0, 1000.0],
            "words": reference["words"], "reference": reference["original_reference"], "paths": paths,
            "counts": {"native_attempts": 6, "provider_attempts": 60, "contexts_created": 6,
                       "contexts_closed": 6, "native_reported_function_evaluations": reported,
                       "spice_queries": 0, "kernel_reads": 0, "real_archive_reads": 0,
                       "optimizer_entries": 0},
            "status": "passed", "failure": None,
            "runtime": {"python": "3.12.14", "tudatpy": "1.0.0", "numpy": "1.26.4",
                        "source_sha256": {path: sha256((ROOT / path).read_bytes()).hexdigest()
                                          for path in oracle._SOURCE_PATHS}}}


def _row(packet: dict[str, object], path: str = "forward", index: int = 0) -> dict[str, object]:
    paths = cast(dict[str, list[dict[str, object]]], packet["paths"])
    return paths[path][index]


def _audit(packet: object) -> dict[str, object]:
    return oracle.audit(packet, deadline=monotonic() + 10.0)


def test_binary_reference_has_exact_mass_ledger_and_independent_speed_invariant() -> None:
    reference = oracle.reference()
    words = cast(dict[str, str], reference["words"])
    force = float.fromhex(words["thrust_n"])
    rate = float.fromhex(words["rate_kg_s"])
    gravity = float.fromhex(words["gravity_y_m_s2"])
    exhaust = force / rate
    nodes = cast(dict[str, list[list[str]]], reference["decimal100"])
    ledgers = cast(dict[str, list[list[int]]], reference["mass_ledgers"])
    initial_mass = 2000.0
    for path in ("forward", "reverse"):
        states = cast(list[list[float]], reference[path + "_states"])
        epochs = cast(list[int], reference[path + "_epochs_s"])
        for index, (epoch, row) in enumerate(zip(epochs, states, strict=True)):
            exact_mass = Fraction(*ledgers[path][index])
            assert Fraction(Decimal(nodes["binary_" + path][index][6])) == exact_mass
            elapsed = epoch - epochs[0]
            expected_speed = states[0][4] + gravity * elapsed + exhaust * math.log(states[0][6] / row[6])
            assert row[4] == pytest.approx(expected_speed, abs=2e-12)
            assert row[0] == 10000000.0 and row[2] == row[3] == row[5] == 0.0
        if path == "forward":
            assert states[0][6] == initial_mass
        else:
            assert states[-1][6] == pytest.approx(initial_mass, abs=1e-12)
    precision = cast(dict[str, dict[str, float]], reference["precision_differences"])
    for checks in precision.values():
        assert checks["position_m"] <= 1e-9
        assert checks["velocity_m_s"] <= 1e-12
        assert checks["mass_kg"] <= 1e-15
    with localcontext() as context:
        context.prec = 100
        expected = Decimal.from_float(force) / Decimal.from_float(rate)
        assert Decimal(cast(str, reference["effective_exhaust_m_s_decimal100"])) == expected
        assert expected != Decimal("9.80665") * Decimal(450)


def test_reverse_start_is_original_target_rounded_once_and_differences_are_separate() -> None:
    reference = oracle.reference()
    original = cast(dict[str, object], reference["original_reference"])
    original_states = cast(list[list[float]], original["states"])
    reverse = cast(list[list[float]], reference["reverse_states"])
    assert [value.hex() for value in reverse[0]] == [value.hex() for value in original_states[-1]]
    conversion = cast(dict[str, object], reference["conversion_differences"])
    assert set(conversion) == {"forward_binary_constants_minus_original",
        "reverse_binary_constants_minus_original_same_rounded_start", "reverse_target_rounding_response",
        "original_target_rounding", "forward_output_rounding", "reverse_output_rounding"}
    target = cast(list[str], conversion["original_target_rounding"])
    constants = cast(list[list[str]], conversion["forward_binary_constants_minus_original"])
    assert any(Decimal(value) != 0 for value in target)
    assert any(Decimal(value) != 0 for row in constants for value in row)
    reverse_ledger = cast(dict[str, list[list[int]]], reference["mass_ledgers"])["reverse"]
    assert Fraction(*reverse_ledger[0]) == Fraction.from_float(original_states[-1][6])
    assert oracle.reference() == reference
    cast(list[list[float]], reference["forward_states"])[0][0] = -1.0
    assert cast(list[list[float]], oracle.reference()["forward_states"])[0][0] == 10000000.0


def test_fabricated_six_arc_audit_checks_both_references_and_exact_ledgers() -> None:
    result = _audit(_packet())
    assert result["status"] == "passed"
    assert result["counts"] == {"audited_arcs": 6, "audited_events": 12,
        "native_propagations": 0, "spice_queries": 0, "kernel_reads": 0,
        "real_archive_reads": 0, "optimizer_entries": 0}
    assert result["native_time_equality"] == {"evidence": "producer-observed-only", "independently_certified": False}
    for row in cast(list[dict[str, object]], result["arc_checks"]):
        for event in cast(list[dict[str, object]], row["events"]):
            assert event["native_equality_evidence"] == "producer-observed-only"
            assert event["epoch_error_s"] == 0.0
        for endpoint in cast(list[dict[str, object]], row["endpoints"]):
            assert endpoint["mass_ledger_error_kg"] <= 1e-9
            for key in ("original_decimal", "binary_words"):
                errors = cast(dict[str, object], endpoint[key])
                assert errors["position_m"] <= 0.001
                assert errors["velocity_m_s"] <= 1e-6
                assert errors["mass_kg"] <= 1e-9
    assert result["physical_status"] == "not-established"


@pytest.mark.parametrize(("field", "value"), [
    ("schema", "different"), ("frame", "SSB"), ("time_scale", "TDB"),
    ("status", "failed"), ("status", "unavailable-transport"), ("failure", "failed"),
    ("controls", [False, 0.0, 1000.0, 0.0, 0.0, 1000.0]),
    ("controls", [0.0, 0.0, 1001.0, 0.0, 0.0, 1000.0]),
])
def test_fixed_packet_and_incomplete_outcome_are_not_qualified(field: str, value: object) -> None:
    packet = _packet()
    packet[field] = value
    with pytest.raises(oracle.OracleError):
        _audit(packet)


@pytest.mark.parametrize(("field", "value"), [
    ("native_attempts", 5), ("native_attempts", True), ("native_attempts", 7),
    ("provider_attempts", 61), ("provider_attempts", 100001),
    ("contexts_created", 5), ("contexts_closed", 5),
    ("spice_queries", 1), ("kernel_reads", 1), ("real_archive_reads", 1),
    ("optimizer_entries", 1), ("native_reported_function_evaluations", [0] * 6),
    ("native_reported_function_evaluations", [True] * 6),
])
def test_actual_counter_caps_lifecycle_and_telemetry_list_bindings(field: str, value: object) -> None:
    packet = _packet()
    cast(dict[str, object], packet["counts"])[field] = value
    with pytest.raises(oracle.OracleError):
        _audit(packet)


@pytest.mark.parametrize(("field", "value"), [
    ("requested", [True, 1]), ("requested", [0, 2]), ("requested", [1, 1]),
    ("label_hex", "-0x0.0p+0"), ("native_equal", False), ("native_equal", 1),
    ("residual_s", 1e-9), ("residual_s", 2e-6), ("observed_label_s", 1e-7),
])
def test_float_labels_and_small_residual_cannot_manufacture_native_equality(
    field: str, value: object,
) -> None:
    packet = _packet()
    event = cast(dict[str, object], _row(packet)["start_event"])
    event[field] = value
    with pytest.raises(oracle.OracleError):
        _audit(packet)


@pytest.mark.parametrize(("field", "value"), [
    ("mode", "coast"), ("direction", -1), ("direction", True),
    ("provider_attempts", 0), ("provider_attempts", True),
    ("samples_checked", 1), ("native_reported_function_evaluations", -1),
])
def test_per_arc_mode_direction_work_and_samples_are_bound(field: str, value: object) -> None:
    packet = _packet()
    _row(packet)[field] = value
    with pytest.raises(oracle.OracleError):
        _audit(packet)


@pytest.mark.parametrize(("component", "offset"), [(0, 0.01), (4, 1e-4), (6, 1e-7)])
def test_each_dimensional_endpoint_gate_is_enforced(component: int, offset: float) -> None:
    packet = _packet()
    state = cast(list[float], _row(packet)["end_state"])
    state[component] += offset
    with pytest.raises(oracle.OracleError, match="gate failed"):
        _audit(packet)


@pytest.mark.parametrize("path", ["forward", "reverse"])
def test_actual_state_and_mass_carry_cannot_be_reset_even_within_tolerance(path: str) -> None:
    packet = _packet()
    start = cast(list[float], _row(packet, path, 1)["start_state"])
    start[6] = math.nextafter(start[6], math.inf)
    with pytest.raises(oracle.OracleError, match="reset"):
        _audit(packet)


def test_reverse_start_must_be_the_frozen_original_target() -> None:
    packet = _packet()
    forward_end = cast(list[float], _row(packet, "forward", 2)["end_state"])
    reverse_start = cast(list[float], _row(packet, "reverse")["start_state"])
    # Even a near target selected from the forward numerical output is not the frozen start.
    forward_end[6] = math.nextafter(forward_end[6], math.inf)
    reverse_start[:] = forward_end
    with pytest.raises(oracle.OracleError, match="reset"):
        _audit(packet)


@pytest.mark.parametrize("value", [True, float("nan"), float("inf")])
def test_nonfinite_or_boolean_endpoint_is_rejected(value: object) -> None:
    packet = _packet()
    cast(list[object], _row(packet)["end_state"])[0] = value
    with pytest.raises(oracle.OracleError):
        _audit(packet)


def test_word_original_reference_and_current_source_hashes_are_bound() -> None:
    packet = _packet()
    cast(dict[str, object], packet["words"])["rate_kg_s"] = math.nextafter(1000.0 / (9.80665 * 450.0), math.inf).hex()
    with pytest.raises(oracle.OracleError, match="words"):
        _audit(packet)
    packet = _packet()
    reference = cast(dict[str, object], packet["reference"])
    cast(list[list[float]], reference["states"])[-1][6] += 1.0
    with pytest.raises(oracle.OracleError, match="original reference"):
        _audit(packet)
    packet = _packet()
    runtime = cast(dict[str, object], packet["runtime"])
    sources = cast(dict[str, object], runtime["source_sha256"])
    sources["src/space_nav/_native_arc_conformance.py"] = "0" * 64
    with pytest.raises(oracle.OracleError, match="source_sha256"):
        _audit(packet)


@pytest.mark.parametrize(("field", "value"), [("python", "3.11.9"), ("tudatpy", "2.0"), ("numpy", "2.0")])
def test_runtime_profile_drift_is_rejected(field: str, value: object) -> None:
    packet = _packet()
    cast(dict[str, object], packet["runtime"])[field] = value
    with pytest.raises(oracle.OracleError, match="runtime"):
        _audit(packet)


@pytest.mark.parametrize("section", ["packet", "runtime", "counts", "arc", "event"])
def test_unknown_fields_are_rejected(section: str) -> None:
    packet = _packet()
    target = packet
    if section in ("runtime", "counts"):
        target = cast(dict[str, object], packet[section])
    elif section == "arc":
        target = _row(packet)
    elif section == "event":
        target = cast(dict[str, object], _row(packet)["end_event"])
    target["unlisted"] = 1
    with pytest.raises(oracle.OracleError):
        _audit(packet)


def test_producer_evidence_partition_is_separate_from_initial_fixture_input() -> None:
    packet = _packet()
    packet["failure"] = ""
    overhead = len(json.dumps(packet, sort_keys=True, allow_nan=False).encode())
    packet["failure"] = "x" * (1024 * 1024 - overhead)
    assert len(json.dumps(packet, sort_keys=True, allow_nan=False).encode()) == 1024 * 1024
    # At the byte cap the invalid failure value reaches semantic validation.
    with pytest.raises(oracle.OracleError, match="failure"):
        _audit(packet)
    packet["failure"] += "x"
    with pytest.raises(oracle.OracleError, match="1 MiB"):
        _audit(packet)


def test_deadline_and_backwards_clock_fail_closed() -> None:
    with pytest.raises(oracle.OracleError, match="deadline"):
        oracle.audit(_packet(), deadline=monotonic() - 1.0)
    ticks = iter([1.0, 0.0])
    with pytest.raises(oracle.OracleError, match="backwards"):
        oracle.audit(_packet(), deadline=10.0, clock=lambda: next(ticks))


def test_auditor_imports_no_native_candidate_or_scientific_library(monkeypatch: pytest.MonkeyPatch) -> None:
    packet = _packet()
    original = builtins.__import__

    def guarded(name: str, *args: object, **kwargs: object) -> object:
        assert not any(part in name for part in ("tudat", "numpy", "scipy", "_native_arc_conformance", "trajectory"))
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    assert _audit(packet)["status"] == "passed"


def test_fresh_decimal_contexts_ignore_ambient_rounding_and_precision() -> None:
    expected = oracle.reference()
    packet = _packet()
    with localcontext() as context:
        context.prec = 3
        context.rounding = ROUND_DOWN
        assert oracle.reference() == expected
        assert _audit(packet)["status"] == "passed"
