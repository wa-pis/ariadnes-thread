"""ADR0255 fabricated interval arithmetic; never a native or physical certificate."""
from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction
import json
import math
import re
from time import monotonic
from typing import cast

INPUT_BYTES = 64 * 1024
Interval = tuple[Fraction, Fraction]
_IDS = ("E0", "E1", "E2", "E3")
_ARCS = ("departure-burn", "coast", "arrival-burn")
_BASIS = {"domain": "fabricated", "derivation": "explicit-rational",
          "evidence": "inline", "qualification_scope": "fabricated-only"}
_RATE = 1000.0 / float(9.80665 * 450.0)
_LIMITS = {"join_position_m": ("m", Fraction(0.001)),
           "join_velocity_m_s": ("m/s", Fraction(1e-6)),
           "join_mass_kg": ("kg", Fraction(1e-9)),
           "target_position_m": ("m", Fraction(1000)),
           "target_velocity_m_s": ("m/s", Fraction(0.01)),
           "clock_position_m": ("m", Fraction(0.001)),
           "clock_velocity_m_s": ("m/s", Fraction(1e-6)),
           "clock_mass_kg": ("kg", Fraction(1e-9))}


class PacketError(ValueError):
    """Malformed evidence or an exhausted pure-check limit; no partial pass."""


def _need(condition: bool, field: str) -> None:
    if not condition:
        raise PacketError(field)


def _dict(value: object, keys: set[str], field: str) -> dict[str, object]:
    _need(type(value) is dict, field + ": object required")
    result = cast(dict[str, object], value)
    _need(set(result) == keys, field + ": unexpected or missing fields")
    return result


def _list(value: object, size: int, field: str) -> list[object]:
    _need(type(value) is list and len(cast(list[object], value)) == size,
          field + f": exactly {size} entries required")
    return cast(list[object], value)


def _text(value: object, field: str) -> str:
    _need(type(value) is str and bool(value), field + ": nonempty string required")
    return cast(str, value)


def _boolean(value: object, field: str) -> bool:
    _need(type(value) is bool, field + ": boolean required")
    return cast(bool, value)


def _word(value: object, field: str) -> float:
    text = _text(value, field)
    try:
        result = float.fromhex(text)
    except (ValueError, OverflowError) as exc:
        raise PacketError(field + ": finite canonical binary64 word required") from exc
    _need(math.isfinite(result) and result.hex() == text,
          field + ": finite canonical binary64 word required")
    return result


def _words(value: object, size: int, field: str) -> list[object]:
    result = _list(value, size, field)
    for index, word in enumerate(result):
        _word(word, field + f"[{index}]")
    return result


def _rational(value: object, field: str) -> Fraction:
    pair = _list(value, 2, field)
    _need(all(type(number) is int for number in pair), field + ": integer rational required")
    numerator, denominator = cast(list[int], pair)
    _need(denominator > 0 and math.gcd(numerator, denominator) == 1,
          field + ": reduced rational with positive denominator required")
    return Fraction(numerator, denominator)


def _bound(value: object, unit: str, field: str, artificial: bool, *,
           contains: Fraction | None = None, nonnegative: bool = False) -> Interval | None:
    row = _dict(value, {"interval", "unavailable_reason"}, field)
    if row["interval"] is None:
        _text(row["unavailable_reason"], field + ".unavailable_reason")
        return None
    _need(row["unavailable_reason"] is None, field + ": known bound has unavailable reason")
    interval = _dict(row["interval"], {"lower", "upper", "unit", "basis"}, field + ".interval")
    lo = _rational(interval["lower"], field + ".lower")
    hi = _rational(interval["upper"], field + ".upper")
    _need(lo <= hi and interval["unit"] == unit, field + ": interval order or units")
    _need(contains is None or lo <= contains <= hi, field + ": actual word outside enclosure")
    _need(not nonnegative or lo >= 0, field + ": nonnegative norm/error required")
    basis = _dict(interval["basis"], set(_BASIS), field + ".basis")
    for key, item in basis.items():
        _text(item, field + ".basis." + key)
    return (lo, hi) if artificial and basis == _BASIS else None


def _add(left: Interval | None, right: Interval | None) -> Interval | None:
    return None if left is None or right is None else (left[0] + right[0], left[1] + right[1])


def _sub(left: Interval | None, right: Interval | None) -> Interval | None:
    return None if left is None or right is None else (left[0] - right[1], left[1] - right[0])


def _scale(value: Interval | None, factor: Fraction) -> Interval | None:
    return None if value is None else (min(value[0]*factor, value[1]*factor),
                                      max(value[0]*factor, value[1]*factor))


def _point(value: Fraction) -> Interval:
    return value, value


def _absolute(value: Interval | None) -> Interval | None:
    if value is None:
        return None
    lo, hi = value
    return (Fraction(0) if lo <= 0 <= hi else min(abs(lo), abs(hi)), max(abs(lo), abs(hi)))


def _decision(value: Interval | None, limit: Fraction, *, floor: bool = False) -> str:
    if value is None:
        return "unavailable"
    lo, hi = value
    if floor:
        return "passed" if lo >= limit else "failed" if hi < limit else "inconclusive"
    return "passed" if hi <= limit else "failed" if lo > limit else "inconclusive"


def _pack(value: Interval | None) -> list[list[int]] | None:
    return None if value is None else [[number.numerator, number.denominator] for number in value]


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        _need(key not in result, "JSON: duplicate key " + key)
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise PacketError("JSON: nonfinite constant " + value)


def check_packet(raw: bytes, *, deadline_s: float | None = None,
                 clock: Callable[[], float] = monotonic) -> dict[str, object]:
    """Check one inline fabricated packet; SI/TDB-J2000/SSB/J2000 only.

    The isolated harness supplies the inclusive parent deadline. Pure calls also
    check that deadline around bounded parsing/arithmetic; neither route admits
    physical certificates, loads references or imports a scientific runtime.
    """
    began = clock()
    _need(type(began) in (int, float) and math.isfinite(began), "clock: finite value required")
    deadline = began + 15.0 if deadline_s is None else deadline_s
    _need(type(deadline) in (int, float) and math.isfinite(deadline) and deadline <= began + 15.0,
          "deadline: finite inherited limit no more than15s required")
    last = began

    def checkpoint() -> None:
        nonlocal last
        now = clock()
        _need(type(now) in (int, float) and math.isfinite(now) and last <= now < deadline,
              "clock/deadline: backwards, invalid or exhausted")
        last = now

    checkpoint()
    _need(type(raw) is bytes and len(raw) <= INPUT_BYTES, "input:64KiB bytes cap before decode")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise PacketError("JSON: " + str(exc)) from exc
    checkpoint()
    packet = _dict(value, {"schema", "scope", "direction", "identity", "controls_hex",
                          "requested_events", "native_observations", "arcs", "nodes",
                          "bounds", "counts", "outcome"}, "packet")
    _need(packet["schema"] == "ariadna-realized-clock-v1", "schema: unsupported")
    _need(packet["scope"] in ("fabricated", "physical-unqualified"), "scope: unsupported")
    artificial = packet["scope"] == "fabricated"
    direction = packet["direction"]
    _need(type(direction) is int and direction in (-1, 1), "direction: +1 or-1 required")
    identity = _dict(packet["identity"], {"units", "time_scale", "origin", "orientation",
                       "hashes", "endpoints_hex", "boundary_states_hex", "initial_mass_hex",
                       "dry_mass_hex", "rate_hex"}, "identity")
    for key, expected in (("units", "SI"), ("time_scale", "TDB seconds since J2000"),
                          ("origin", "SSB"), ("orientation", "J2000")):
        _need(identity[key] == expected, "identity." + key)
    hashes = _dict(identity["hashes"], {"boundary", "commands", "source", "runtime", "model", "kernels"}, "identity.hashes")
    for key, digest in hashes.items():
        _need(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
              "identity.hashes." + key)
    for key, expected in (("initial_mass_hex", 2000.0), ("dry_mass_hex", 500.0), ("rate_hex", _RATE)):
        _need(_word(identity[key], "identity." + key).hex() == expected.hex(), "identity." + key + ": fixed word mismatch")
    endpoint_words = _words(identity["endpoints_hex"], 2, "identity.endpoints_hex")
    boundaries = [_words(row, 6, "identity.boundary_states_hex") for row in
                  _list(identity["boundary_states_hex"], 2, "identity.boundary_states_hex")]
    controls = [_word(word, "controls_hex") for word in _words(packet["controls_hex"], 6, "controls_hex")]
    _need(controls[2] > 0 and controls[5] > 0, "controls_hex: positive burn durations required")
    t0, tf = (Fraction(_word(word, "endpoints_hex")) for word in endpoint_words)
    exact = [t0, t0 + Fraction(controls[2]), tf - Fraction(controls[5]), tf]
    _need(all(a < b for a, b in zip(exact, exact[1:])), "requested_events: order/durations")
    for index, item in enumerate(_list(packet["requested_events"], 4, "requested_events")):
        row = _dict(item, {"id", "exact_s", "label_hex", "label_error_s"}, "requested_events")
        _need(row["id"] == _IDS[index] and _rational(row["exact_s"], "exact_s") == exact[index],
              "requested_events: exact event/duration identity")
        label = _word(row["label_hex"], "label_hex")
        try:
            nearest = (_word(endpoint_words[0], "endpoint label") if index == 0 else
                       _word(endpoint_words[1], "endpoint label") if index == 3 else float(exact[index]))
        except OverflowError as exc:
            raise PacketError("requested_events: label overflow") from exc
        _need(label.hex() == nearest.hex() and Fraction(label)-exact[index] == _rational(row["label_error_s"], "label_error_s"),
              "requested_events: label or signed conversion error mismatch")
    mass: list[Fraction] = []
    mass_bounds: list[Interval | None] = []
    states: list[list[object]] = []
    for index, item in enumerate(_list(packet["nodes"], 4, "nodes")):
        row = _dict(item, {"id", "state_hex", "mass_bound"}, "nodes")
        _need(row["id"] == _IDS[index], "nodes: chronological identity")
        state = _words(row["state_hex"], 7, "nodes.state_hex")
        m = Fraction(_word(state[6], "nodes.mass"))
        _need(m > 0, "nodes.mass: positive mass required")
        bound = _bound(row["mass_bound"], "kg", "nodes.mass_bound", artificial, contains=m)
        mass.append(m)
        mass_bounds.append(bound)
        states.append(state)
    _need(states[0][:6] == boundaries[0] and states[3][:6] == boundaries[1], "nodes: original boundary state words")
    rate = Fraction(_RATE)
    commanded = [Fraction(2000), Fraction(2000)-rate*Fraction(controls[2])]
    commanded += [commanded[1], commanded[1]-rate*Fraction(controls[5])]
    anchor = 0 if direction == 1 else 3
    _need(states[anchor][6] == float(commanded[anchor]).hex(), "nodes: original declared start mass word")
    traversal = (0, 1, 2, 3) if direction == 1 else (3, 2, 1, 0)
    observations: list[dict[str, object]] = []
    epochs: list[Interval | None] = [None] * 4
    event_rows: dict[int, dict[str, object]] = {}
    for position, item in enumerate(_list(packet["native_observations"], 6, "native_observations")):
        checkpoint()
        index = traversal[(position+1)//2]
        row = _dict(item, {"event_id", "token", "state_hex", "readback", "epoch_bound"}, "native_observations")
        _need(row["event_id"] == _IDS[index], "native_observations: directed event identity")
        _text(row["token"], "native_observations.token")
        _need(_words(row["state_hex"], 7, "native_observations.state_hex") == states[index], "native_observations: actual seven-state word handoff")
        readback = _dict(row["readback"], {"route", "component_types", "components", "comparison_target_hex", "native_equal", "difference_hex", "roundtrip_equal", "abi", "rounding", "normalization", "source_sha256"}, "readback")
        for key in ("route", "abi", "rounding", "normalization"):
            _text(readback[key], "readback." + key)
        _need(readback["component_types"] == ["int", "float"], "readback.component_types")
        components = _list(readback["components"], 2, "readback.components")
        _need(type(components[0]) is int, "readback.hours: integer required")
        remainder = _word(components[1], "readback.remainder")
        _word(readback["comparison_target_hex"], "readback.comparison_target_hex")
        difference = _word(readback["difference_hex"], "readback.difference_hex")
        equal = _boolean(readback["native_equal"], "readback.native_equal")
        roundtrip = _boolean(readback["roundtrip_equal"], "readback.roundtrip_equal")
        _need(not equal or difference == 0, "readback: equality with nonzero residual")
        _need(readback["source_sha256"] == hashes["source"], "readback: wrong source identity")
        enclosure = _bound(row["epoch_bound"], "s", "epoch_bound", artificial)
        if readback["route"] != "fabricated-split-binary64" or not roundtrip:
            enclosure = None
        if enclosure is not None:
            fabricated = Fraction(cast(int, components[0])*3600) + Fraction(remainder)
            _need(enclosure[0] <= fabricated <= enclosure[1], "epoch_bound: fabricated operand outside enclosure")
        if index in event_rows:
            _need(row == event_rows[index], "native_observations: shared actual event/readback/state handoff")
        event_rows[index] = row
        epochs[index] = enclosure
        observations.append(row)
    gates: dict[str, str] = {}
    for index, epoch in enumerate(epochs):
        gates["time:" + _IDS[index]] = _decision(_absolute(_sub(epoch, _point(exact[index]))), Fraction(1e-6))
    spans: list[Interval | None] = []
    span_errors: list[Interval | None] = []
    effective: list[Interval | None] = [None] * 4
    effective[anchor] = _point(mass[anchor])
    local: list[Interval | None] = []
    clock_mass: Interval | None = _point(Fraction(0))
    for index, item in enumerate(_list(packet["arcs"], 3, "arcs")):
        checkpoint()
        start, end = traversal[index:index+2]
        name = _ARCS[min(start, end)]
        row = _dict(item, {"name", "start", "end", "start_observation", "end_observation", "handoff_equal", "complete", "domain_ok"}, "arcs")
        _need(row["name"] == name and row["start"] == _IDS[start] and row["end"] == _IDS[end], "arcs: mode/direction/event identity")
        _need(type(row["start_observation"]) is int and row["start_observation"] == 2*index and type(row["end_observation"]) is int and row["end_observation"] == 2*index+1,
              "arcs: observation indices")
        handoff = _boolean(row["handoff_equal"], "arcs.handoff_equal")
        complete = _boolean(row["complete"], "arcs.complete")
        domain = _boolean(row["domain_ok"], "arcs.domain_ok")
        gates[f"arc:{index}"] = "passed" if handoff and complete and domain else "failed"
        span = _sub(epochs[end], epochs[start])
        error = _sub(span, _point(exact[end]-exact[start]))
        spans.append(span)
        span_errors.append(error)
        signed_span = _scale(span, Fraction(cast(int, direction)))
        gates[f"order:{index}"] = ("unavailable" if signed_span is None else
                                    "passed" if signed_span[0] > 0 else
                                    "failed" if signed_span[1] <= 0 else "inconclusive")
        burn_rate = rate if name != "coast" else Fraction(0)
        consumption = _scale(span, burn_rate) if burn_rate else _point(Fraction(0))
        effective[end] = _sub(effective[start], consumption)
        # Local comparison starts at the actual returned word, never a ledger reset.
        prediction = _sub(_point(mass[start]), consumption)
        local.append(prediction)
        gates[f"mass:local:{index}"] = _decision(_absolute(_sub(mass_bounds[end], prediction)), Fraction(1e-9))
        if burn_rate:
            clock_mass = _add(clock_mass, _scale(error, -burn_rate))
    for index in range(4):
        label = _IDS[index]
        for name, interval in (("command", _point(commanded[index])), ("effective", effective[index]), ("actual", mass_bounds[index])):
            gates[f"floor:{name}:{label}"] = _decision(interval, Fraction(500), floor=True)
        gates["mass:command:"+label] = _decision(_absolute(_sub(mass_bounds[index], _point(commanded[index]))), Fraction(1e-9))
        gates["mass:global:"+label] = _decision(_absolute(_sub(mass_bounds[index], effective[index])), Fraction(1e-9))
    gates["clock:mass"] = _decision(_absolute(clock_mass), Fraction(1e-9))
    bounds = _dict(packet["bounds"], set(_LIMITS), "bounds")
    for name, (unit, limit) in _LIMITS.items():
        interval = _bound(bounds[name], unit, "bounds."+name, artificial, nonnegative=True)
        gates[name] = _decision(interval, limit)
    counts = _dict(packet["counts"], {"native", "provider", "reported_rhs"}, "counts")
    _need(all(type(value) is int and cast(int, value) >= 0 for value in counts.values()), "counts: nonnegative nonboolean integers required")
    outcome = _dict(packet["outcome"], {"complete", "physical_admission"}, "outcome")
    _need(outcome["physical_admission"] == "unavailable", "outcome: physical admission unavailable")
    gates["complete"] = "passed" if _boolean(outcome["complete"], "outcome.complete") else "failed"
    checkpoint()
    first = next((name for name, status in gates.items() if status != "passed"), None)
    status = next((status for status in ("failed", "unavailable", "inconclusive") if status in gates.values()), "passed")
    return {"schema": "ariadna-realized-clock-check-v1", "structural_status": "valid", "status": status,
            "gates": gates, "first_nonpass": first,
            "derived": {"epoch_errors_s": [_pack(_sub(epoch, _point(event))) for epoch, event in zip(epochs, exact, strict=True)],
                        "spans_s": [_pack(span) for span in spans],
                        "span_errors_s": [_pack(error) for error in span_errors],
                        "commanded_mass_kg": [[number.numerator, number.denominator] for number in commanded],
                        "effective_mass_kg": [_pack(value) for value in effective],
                        "local_mass_kg": [_pack(value) for value in local],
                        "clock_mass_error_kg": _pack(clock_mass)},
            "scientific_admission": "unavailable", "physical_admission": "unavailable"}
