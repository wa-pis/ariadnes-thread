"""Independent rational fixtures; no native clock or physical certificate."""

from __future__ import annotations

import builtins
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path
from typing import Any, cast

import pytest

from space_nav import _realized_clock_packet as subject


_RATE = Fraction.from_float(1000.0 / (9.80665 * 450.0))
_BASIS = {"domain": "fabricated", "derivation": "explicit-rational",
          "evidence": "inline", "qualification_scope": "fabricated-only"}
_ERROR_UNITS = {
    "join_position_m": "m", "join_velocity_m_s": "m/s", "join_mass_kg": "kg",
    "target_position_m": "m", "target_velocity_m_s": "m/s",
    "clock_position_m": "m", "clock_velocity_m_s": "m/s", "clock_mass_kg": "kg",
}


def _pair(value: Fraction | int) -> list[int]:
    exact = Fraction(value)
    return [exact.numerator, exact.denominator]


def _interval(lower: Fraction | int, upper: Fraction | int | None = None) -> list[list[int]]:
    return [_pair(lower), _pair(lower if upper is None else upper)]


def _bound(value: Fraction | int, unit: str, upper: Fraction | int | None = None) -> dict[str, object]:
    return {"interval": {"lower": _pair(value), "upper": _pair(value if upper is None else upper),
                         "unit": unit, "basis": dict(_BASIS)}, "unavailable_reason": None}


def _packet(direction: int = 1, *, duration_s: float = 1.0) -> dict[str, Any]:
    """Build declared words and independently derived artificial operands."""
    duration = Fraction.from_float(duration_s)
    finish = float(2.0 * duration_s + 2.0)
    events = (Fraction(0), duration, Fraction.from_float(finish) - duration,
              Fraction.from_float(finish))
    commanded = (Fraction(2000), Fraction(2000) - _RATE * duration,
                 Fraction(2000) - _RATE * duration, Fraction(2000) - 2 * _RATE * duration)
    state_words = [[float(value).hex() for value in
                    (10000000.0, float(index), 0.0, 0.0, 1000.0, 0.0, float(mass))]
                   for index, mass in enumerate(commanded)]
    identity = {
        "units": "SI", "time_scale": "TDB seconds since J2000", "origin": "SSB",
        "orientation": "J2000",
        "hashes": {name: "a" * 64 for name in
                   ("boundary", "commands", "source", "runtime", "model", "kernels")},
        "endpoints_hex": [(0.0).hex(), finish.hex()],
        "boundary_states_hex": [state_words[0][:6], state_words[3][:6]],
        "initial_mass_hex": (2000.0).hex(), "dry_mass_hex": (500.0).hex(),
        "rate_hex": float(_RATE).hex(),
    }
    requested = [{"id": f"E{i}", "exact_s": _pair(epoch),
                  "label_hex": float(epoch).hex(),
                  "label_error_s": _pair(Fraction.from_float(float(epoch)) - epoch)}
                 for i, epoch in enumerate(events)]
    nodes = [{"id": f"E{i}", "state_hex": words,
              "mass_bound": _bound(Fraction.from_float(float.fromhex(words[6])), "kg")}
             for i, words in enumerate(state_words)]
    order = (0, 1, 2, 3) if direction == 1 else (3, 2, 1, 0)
    modes = ("departure-burn", "coast", "arrival-burn")
    observations: list[dict[str, object]] = []
    arcs = []
    for index, (start, end) in enumerate(zip(order[:-1], order[1:], strict=True)):
        for event_index in (start, end):
            epoch = events[event_index]
            assert Fraction.from_float(float(epoch)) == epoch
            hours = int(epoch // 3600)
            remainder = epoch - 3600 * hours
            observations.append({
                "event_id": f"E{event_index}", "token": f"artificial-event-{event_index}",
                "state_hex": state_words[event_index].copy(),
                "readback": {"route": "fabricated-split-binary64",
                             "component_types": ["int", "float"],
                             "components": [hours, float(remainder).hex()],
                             "comparison_target_hex": float(epoch).hex(),
                             "native_equal": True, "difference_hex": (0.0).hex(),
                             "roundtrip_equal": True, "abi": "fabricated",
                             "rounding": "explicit-rational", "normalization": "hours-remainder",
                             "source_sha256": "a" * 64},
                "epoch_bound": _bound(epoch, "s"),
            })
        arcs.append({"name": modes[min(start, end)], "start": f"E{start}", "end": f"E{end}",
                     "start_observation": 2 * index, "end_observation": 2 * index + 1,
                     "handoff_equal": True, "complete": True, "domain_ok": True})
    return {"schema": "ariadna-realized-clock-v1", "scope": "fabricated",
            "direction": direction, "identity": identity,
            "controls_hex": [(0.0).hex(), (0.0).hex(), duration_s.hex(),
                             (0.0).hex(), (0.0).hex(), duration_s.hex()],
            "requested_events": requested, "native_observations": observations,
            "arcs": arcs, "nodes": nodes,
            "bounds": {name: _bound(0, unit) for name, unit in _ERROR_UNITS.items()},
            "counts": {"native": 0, "provider": 0, "reported_rhs": 0},
            "outcome": {"complete": True, "physical_admission": "unavailable"}}


def _raw(packet: dict[str, Any]) -> bytes:
    return json.dumps(packet, sort_keys=True, allow_nan=False).encode()


def _check(packet: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], subject.check_packet(_raw(packet)))


def _set_mass(packet: dict[str, Any], index: int, value: float,
              lower: Fraction | int | None = None, upper: Fraction | int | None = None) -> None:
    words = packet["nodes"][index]["state_hex"]
    words[6] = value.hex()
    center = Fraction.from_float(value)
    packet["nodes"][index]["mass_bound"] = _bound(center if lower is None else lower, "kg", upper)
    for observation in packet["native_observations"]:
        if observation["event_id"] == f"E{index}":
            observation["state_hex"] = words.copy()


@pytest.mark.parametrize("direction", [1, -1])
def test_fixed_packet_derives_exact_directed_spans_and_both_ledgers(direction: int) -> None:
    packet = _packet(direction)
    result = _check(packet)
    assert result["schema"] == "ariadna-realized-clock-check-v1"
    assert result["structural_status"] == "valid" and result["status"] == "passed"
    assert set(result["gates"].values()) == {"passed"}
    assert result["first_nonpass"] is None
    assert result["scientific_admission"] == result["physical_admission"] == "unavailable"
    command = [Fraction(2000), Fraction(2000) - _RATE,
               Fraction(2000) - _RATE, Fraction(2000) - 2 * _RATE]
    assert result["derived"]["commanded_mass_kg"] == [_pair(value) for value in command]
    assert result["derived"]["epoch_errors_s"] == [_interval(0)] * 4
    spans = [Fraction(direction), Fraction(2 * direction), Fraction(direction)]
    assert result["derived"]["spans_s"] == [_interval(value) for value in spans]
    assert result["derived"]["span_errors_s"] == [_interval(0)] * 3
    if direction == 1:
        effective = command
        starts = [Fraction(2000), Fraction.from_float(float(command[1])),
                  Fraction.from_float(float(command[2]))]
    else:
        anchor = Fraction.from_float(float(command[3]))
        effective = [anchor + 2 * _RATE, anchor + _RATE, anchor + _RATE, anchor]
        starts = [anchor, Fraction.from_float(float(command[2])),
                  Fraction.from_float(float(command[1]))]
    assert result["derived"]["effective_mass_kg"] == [_interval(value) for value in effective]
    locals_expected = [starts[0] - _RATE * spans[0], starts[1], starts[2] - _RATE * spans[2]]
    assert result["derived"]["local_mass_kg"] == [_interval(value) for value in locals_expected]


def test_signed_nonzero_epoch_error_is_not_f5_exact_identity() -> None:
    packet = _packet()
    shift = Fraction(1, 2**30)
    for observation in packet["native_observations"]:
        event = int(observation["event_id"][1:])
        exact = Fraction(*packet["requested_events"][event]["exact_s"]) + shift
        observation["readback"]["components"][1] = float(exact).hex()
        observation["readback"]["native_equal"] = False
        observation["readback"]["difference_hex"] = float(shift).hex()
        observation["epoch_bound"] = _bound(exact, "s")
    result = _check(packet)
    assert result["status"] == "passed"
    assert result["derived"]["epoch_errors_s"] == [_interval(shift)] * 4
    assert result["derived"]["span_errors_s"] == [_interval(0)] * 3
    assert result["physical_admission"] == "unavailable"


@pytest.mark.parametrize("interval,status", [
    ((Fraction(500), Fraction(500)), "passed"),
    ((Fraction(500) - Fraction(1, 10**10), Fraction(500) + Fraction(1, 10**10)), "inconclusive"),
    ((Fraction(500) - Fraction(2, 10**10), Fraction(500) - Fraction(1, 10**10)), "failed"),
])
def test_actual_floor_is_independent_of_the_mass_matching_tolerance(
    interval: tuple[Fraction, Fraction], status: str,
) -> None:
    duration = math.nextafter(1500.0 / (2.0 * float(_RATE)), 0.0)
    packet = _packet(duration_s=duration)
    low, high = interval
    actual = 500.0 if high >= 500 else math.nextafter(500.0, 0.0)
    # The deficit case encloses its actual binary64 word and remains <1 ng.
    if status == "failed":
        low, high = Fraction.from_float(actual), Fraction.from_float(actual)
    _set_mass(packet, 3, actual, low, high)
    result = _check(packet)
    assert result["gates"]["floor:actual:E3"] == status
    assert result["gates"]["floor:command:E3"] == "passed"
    assert result["gates"]["mass:global:E3"] == "passed"
    assert result["scientific_admission"] == result["physical_admission"] == "unavailable"


@pytest.mark.parametrize("kind", ["null", "basis", "roundtrip", "route", "physical"])
def test_unknown_or_unqualified_evidence_never_defaults_to_zero(kind: str) -> None:
    packet = _packet()
    if kind == "null":
        packet["bounds"]["clock_position_m"] = {"interval": None, "unavailable_reason": "not derived"}
    elif kind == "basis":
        packet["bounds"]["clock_position_m"]["interval"]["basis"]["evidence"] = "caller says verified"
    elif kind == "physical":
        packet["scope"] = "physical-unqualified"
    else:
        for observation in packet["native_observations"]:
            if kind == "roundtrip":
                observation["readback"]["roundtrip_equal"] = False
            else:
                observation["readback"]["route"] = "uninspected-native-export"
    result = _check(packet)
    assert result["status"] == "unavailable"
    assert result["first_nonpass"] is not None
    assert result["scientific_admission"] == result["physical_admission"] == "unavailable"


@pytest.mark.parametrize("name,unit,limit", [
    ("join_position_m", "m", 0.001), ("join_velocity_m_s", "m/s", 1e-6),
    ("join_mass_kg", "kg", 1e-9), ("target_position_m", "m", 1000.0),
    ("target_velocity_m_s", "m/s", 0.01), ("clock_position_m", "m", 0.001),
    ("clock_velocity_m_s", "m/s", 1e-6), ("clock_mass_kg", "kg", 1e-9),
])
@pytest.mark.parametrize("offset,expected", [(Fraction(0), "passed"),
                                             (Fraction(1, 10**30), "failed")])
def test_existing_bound_gate_has_no_hidden_tolerance(
    name: str, unit: str, limit: float, offset: Fraction, expected: str,
) -> None:
    packet = _packet()
    packet["bounds"][name] = _bound(Fraction.from_float(limit) + offset, unit)
    assert _check(packet)["gates"][name] == expected


def test_interval_straddling_a_gate_is_inconclusive() -> None:
    packet = _packet()
    packet["bounds"]["target_velocity_m_s"] = _bound(Fraction(9, 1000), "m/s", Fraction(11, 1000))
    result = _check(packet)
    assert result["gates"]["target_velocity_m_s"] == "inconclusive"
    assert result["status"] == "inconclusive"


@pytest.mark.parametrize("kind", ["token", "signed-zero", "epoch", "source"])
def test_shared_handoff_requires_actual_word_and_observation_binding(kind: str) -> None:
    packet = _packet()
    following = packet["native_observations"][2]
    if kind == "token":
        following["token"] = "different event"
    elif kind == "signed-zero":
        following["state_hex"][2] = (-0.0).hex()
    elif kind == "epoch":
        following["epoch_bound"] = _bound(Fraction(1), "s", Fraction(1000001, 1000000))
    else:
        following["readback"]["source_sha256"] = "b" * 64
    with pytest.raises(subject.PacketError):
        _check(packet)


@pytest.mark.parametrize("field", ["handoff_equal", "complete", "domain_ok"])
def test_explicit_failed_arc_observation_is_a_gate_failure(field: str) -> None:
    packet = _packet()
    packet["arcs"][1][field] = False
    result = _check(packet)
    assert result["structural_status"] == "valid"
    assert result["status"] == result["gates"]["arc:1"] == "failed"
    assert result["physical_admission"] == "unavailable"


@pytest.mark.parametrize("kind", ["root", "shape", "bool", "word", "rational", "interval", "unit", "boundary", "duration", "admission"])
def test_malformed_or_inconsistent_packets_are_invalid(kind: str) -> None:
    packet = _packet()
    if kind == "root":
        packet["unexpected"] = True
    elif kind == "shape":
        packet["nodes"].append(deepcopy(packet["nodes"][0]))
    elif kind == "bool":
        packet["counts"]["native"] = True
    elif kind == "word":
        packet["controls_hex"][0] = "0x0p+0"
    elif kind == "rational":
        packet["requested_events"][0]["exact_s"] = [0, 2]
    elif kind == "interval":
        packet["bounds"]["join_mass_kg"] = _bound(1, "kg", 0)
    elif kind == "unit":
        packet["bounds"]["join_mass_kg"]["interval"]["unit"] = "m"
    elif kind == "boundary":
        packet["identity"]["boundary_states_hex"][0][0] = (9.0).hex()
    elif kind == "duration":
        packet["controls_hex"][2] = (2.0).hex()
    else:
        packet["outcome"]["physical_admission"] = "passed"
    with pytest.raises(subject.PacketError):
        _check(packet)


@pytest.mark.parametrize("raw", [b"{", b"[]", b'{"schema":1,"schema":2}',
                                  b'{"n":NaN}', b'{"n":Infinity}', b'{"n":1e999}',
                                  b"\xff", b" " * (64 * 1024 + 1)])
def test_invalid_json_and_excess_input_are_rejected_before_scientific_work(raw: bytes) -> None:
    with pytest.raises(subject.PacketError):
        subject.check_packet(raw)


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le", "utf-32", "utf-32-be"])
def test_only_utf8_json_bytes_are_admitted(encoding: str) -> None:
    raw = _raw(_packet()).decode("utf-8").encode(encoding)
    with pytest.raises(subject.PacketError):
        subject.check_packet(raw)


@pytest.mark.parametrize("scope", ["unqualified-basis", "physical-scope"])
def test_negative_norm_interval_is_structurally_invalid_before_qualification(scope: str) -> None:
    packet = _packet()
    packet["bounds"]["join_position_m"] = _bound(-1, "m")
    if scope == "unqualified-basis":
        packet["bounds"]["join_position_m"]["interval"]["basis"]["evidence"] = "not independently qualified"
    else:
        packet["scope"] = "physical-unqualified"
    with pytest.raises(subject.PacketError):
        _check(packet)


@pytest.mark.parametrize("scope", ["unqualified-basis", "physical-scope"])
def test_declared_mass_interval_must_contain_actual_word_before_qualification(scope: str) -> None:
    packet = _packet()
    outside = Fraction(2000) + Fraction(1, 10**10)
    packet["nodes"][0]["mass_bound"] = _bound(outside, "kg")
    if scope == "unqualified-basis":
        packet["nodes"][0]["mass_bound"]["interval"]["basis"]["evidence"] = "not independently qualified"
    else:
        packet["scope"] = "physical-unqualified"
    with pytest.raises(subject.PacketError):
        _check(packet)


@pytest.mark.parametrize("clock_value", [10.0, math.nan, math.inf, True])
def test_deadline_or_nonfinite_clock_cannot_yield_a_pass(clock_value: object) -> None:
    with pytest.raises(subject.PacketError):
        subject.check_packet(_raw(_packet()), deadline_s=10.0, clock=lambda: cast(float, clock_value))


def test_exact_input_byte_limit_keeps_the_same_fixed_mathematical_packet() -> None:
    raw = _raw(_packet()).ljust(64 * 1024, b" ")
    assert len(raw) == 64 * 1024
    assert subject.check_packet(raw)["status"] == "passed"


def test_fixed_endpoint_word_preserves_negative_zero_without_changing_exact_event() -> None:
    packet = _packet()
    negative_zero = (-0.0).hex()
    packet["identity"]["endpoints_hex"][0] = negative_zero
    packet["requested_events"][0]["label_hex"] = negative_zero
    for observation in packet["native_observations"]:
        if observation["event_id"] == "E0":
            observation["readback"]["comparison_target_hex"] = negative_zero
            observation["readback"]["components"][1] = negative_zero
    assert _check(packet)["status"] == "passed"


def test_checker_never_imports_scientific_code_or_opens_referenced_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _raw(_packet())
    original_import = builtins.__import__

    def guarded_import(name: str, *args: object, **kwargs: object) -> object:
        if name.split(".")[0] in {"numpy", "scipy", "tudatpy", "spiceypy"}:
            raise AssertionError("fabricated checker attempted a scientific import")
        return original_import(name, *args, **kwargs)

    def forbidden_read(*args: object, **kwargs: object) -> object:
        raise AssertionError("a declared evidence hash must not open a reference")

    with monkeypatch.context() as guarded:
        guarded.setattr(builtins, "__import__", guarded_import)
        guarded.setattr(builtins, "open", forbidden_read)
        guarded.setattr(Path, "open", forbidden_read)
        assert subject.check_packet(raw)["status"] == "passed"
