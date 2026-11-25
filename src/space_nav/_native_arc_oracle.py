"""Independent Decimal/Fraction checks for the fixed synthetic native witness.

Native Time equality is producer-observed evidence. Float labels cannot certify it.
No candidate, guidance, scientific-library or native module is imported here.
"""

from collections.abc import Callable, Mapping
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from time import monotonic
from typing import cast

from ._coupled_benchmark_oracle import reference as _physical_reference


class OracleError(ValueError):
    """The fixed synthetic packet or its independent checks did not qualify."""


_INITIAL = (10000000.0, 0.0, 0.0, 0.0, 1000.0, 0.0, 2000.0)
_EPOCHS = (0, 1000, 9000, 10000)
_CONTROLS = [0.0, 0.0, 1000.0, 0.0, 0.0, 1000.0]
_WORD_VALUES = {"thrust_n": 1000.0, "g0_m_s2": 9.80665, "isp_s": 450.0,
                "gravity_y_m_s2": 0.1, "rate_kg_s": 1000.0 / (9.80665 * 450.0)}
_LIMITS = {"position_m": Decimal("0.001"), "velocity_m_s": Decimal("1e-6"),
           "mass_kg": Decimal("1e-9"), "epoch_s": Decimal("1e-6")}
_PRECISION_LIMITS = {"position_m": Decimal("1e-9"), "velocity_m_s": Decimal("1e-12"),
                     "mass_kg": Decimal("1e-15")}
_LABELS = {"frame": "SYNTHETIC_INERTIAL", "time_scale": "elapsed_seconds"}
_PRODUCER_BYTES = 1024 * 1024
_SOURCE_PATHS = {"src/space_nav/_native_arc_conformance.py",
                 "src/space_nav/_native_arc_oracle.py", "src/space_nav/trajectory.py"}
_ZERO = ("native_propagations", "spice_queries", "kernel_reads", "real_archive_reads",
         "optimizer_entries")
_HEX = re.compile(r"[0-9a-f]{64}\Z")


def _need(condition: bool, field: str) -> None:
    if not condition:
        raise OracleError(field)


def _number(value: object, field: str) -> float:
    _need(type(value) in (int, float), field + ": finite nonboolean number required")
    try:
        result = float(cast(float, value))
    except OverflowError as exc:
        raise OracleError(field + ": finite nonboolean number required") from exc
    _need(math.isfinite(result), field + ": finite nonboolean number required")
    return result


def _mapping(value: object, field: str, keys: set[str] | None = None) -> Mapping[str, object]:
    _need(isinstance(value, Mapping), field + ": mapping required")
    result = cast(Mapping[str, object], value)
    _need(all(type(key) is str for key in result), field + ": string keys required")
    _need(keys is None or set(result) == keys, field + ": unexpected or missing fields")
    return result


def _list(value: object, length: int, field: str) -> list[object]:
    _need(type(value) is list and len(cast(list[object], value)) == length,
          field + f": {length}-entry list required")
    return cast(list[object], value)


def _same(actual: object, expected: object, field: str) -> None:
    if isinstance(expected, Mapping):
        source = cast(Mapping[str, object], expected)
        target = _mapping(actual, field, set(source))
        for key, value in source.items():
            _same(target[key], value, field + "." + key)
    elif type(expected) is list:
        values = cast(list[object], expected)
        target_list = _list(actual, len(values), field)
        for index, value in enumerate(values):
            _same(target_list[index], value, field + f"[{index}]")
    elif type(expected) in (float, int):
        _need(_number(actual, field) == expected, field + ": identity mismatch")
    else:
        _need(type(actual) is type(expected) and actual == expected, field + ": identity mismatch")


def _integer(value: object, field: str, maximum: int) -> int:
    _need(type(value) is int and 0 <= cast(int, value) <= maximum,
          field + ": integer count outside cap")
    return cast(int, value)


def _nodes(precision: int, *, binary: bool, reverse_start: list[Decimal] | None = None) -> list[list[Decimal]]:
    """Evaluate the before-arc closed form, including signed reverse durations."""
    with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN)):
        if binary:
            thrust = Decimal.from_float(_WORD_VALUES["thrust_n"])
            rate = Decimal.from_float(_WORD_VALUES["rate_kg_s"])
            exhaust = thrust / rate
            gravity = Decimal.from_float(_WORD_VALUES["gravity_y_m_s2"])
        else:
            exhaust = Decimal("9.80665") * Decimal("450")
            rate = Decimal("1000") / exhaust
            gravity = Decimal("0.1")
        state = ([Decimal.from_float(value) for value in _INITIAL] if reverse_start is None
                 else reverse_start.copy())
        rows = [state.copy()]
        direction = 1 if reverse_start is None else -1
        for seconds, burn in ((1000, True), (8000, False), (1000, True)):
            dt = Decimal(direction * seconds)
            before = state.copy()
            mass = before[6] - rate * dt if burn else before[6]
            _need(mass >= Decimal(500), "reference mass below dry mass")
            logarithm = (before[6] / mass).ln() if burn else Decimal(0)
            displacement = exhaust * (dt - mass / rate * logarithm) if burn else Decimal(0)
            state[1] = before[1] + before[4] * dt + gravity * dt * dt / 2 + displacement
            state[4] = before[4] + gravity * dt + exhaust * logarithm
            state[6] = mass
            rows.append(state.copy())
        return rows


def _differences(left: list[list[Decimal]], right: list[list[Decimal]]) -> dict[str, Decimal]:
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        return {"position_m": max(sum((a[i] - b[i]) ** 2 for i in range(3)).sqrt()
                                  for a, b in zip(left, right, strict=True)),
                "velocity_m_s": max(sum((a[i] - b[i]) ** 2 for i in range(3, 6)).sqrt()
                                    for a, b in zip(left, right, strict=True)),
                "mass_kg": max(abs(a[6] - b[6]) for a, b in zip(left, right, strict=True))}


def _signed(left: list[list[Decimal]], right: list[list[Decimal]]) -> list[list[str]]:
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        return [[str(x - y) for x, y in zip(a, b, strict=True)]
                for a, b in zip(left, right, strict=True)]


def _fraction(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def reference() -> dict[str, object]:
    """Return both frozen references and signed SI conversion diagnostics.

    The original physical oracle is unchanged. The second closed form uses exact
    binary64 force, gravity and rate words, with effective exhaust speed F/b.
    """
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        original = _physical_reference()
    physical_low, physical = _nodes(80, binary=False), _nodes(100, binary=False)
    physical_floats = [[float(value) for value in row] for row in physical]
    _same(original["states"], physical_floats, "original exact-decimal reference")
    frozen = [Decimal.from_float(value) for value in physical_floats[-1]]
    forward_low, forward = _nodes(80, binary=True), _nodes(100, binary=True)
    reverse_low = _nodes(80, binary=True, reverse_start=frozen)
    reverse = _nodes(100, binary=True, reverse_start=frozen)
    physical_reverse = _nodes(100, binary=False, reverse_start=frozen)
    precision: dict[str, dict[str, float]] = {}
    for name, low, high in (("original_decimal", physical_low, physical),
                            ("binary_forward", forward_low, forward),
                            ("binary_reverse", reverse_low, reverse)):
        differences = _differences(low, high)
        _need(all(value <= _PRECISION_LIMITS[key] for key, value in differences.items()),
              name + ": Decimal80/100 precision gate failed")
        precision[name] = {key: float(value) for key, value in differences.items()}
    rate = Fraction.from_float(_WORD_VALUES["rate_kg_s"])
    reverse_mass = Fraction.from_float(physical_floats[-1][6])
    burn_times = (0, 1000, 1000, 2000)
    ledgers = {"forward": [_fraction(Fraction(2000) - rate * seconds) for seconds in burn_times],
               "reverse": [_fraction(reverse_mass + rate * seconds) for seconds in burn_times]}
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        effective_exhaust = str(Decimal.from_float(_WORD_VALUES["thrust_n"])
                                / Decimal.from_float(_WORD_VALUES["rate_kg_s"]))
    rounded_forward = [[Decimal.from_float(float(value)) for value in row] for row in forward]
    rounded_reverse = [[Decimal.from_float(float(value)) for value in row] for row in reverse]
    return {"schema": "ariadna-native-arc-reference-v1", **_LABELS,
            "words": {key: value.hex() for key, value in _WORD_VALUES.items()},
            "original_reference": original,
            "forward_epochs_s": list(_EPOCHS), "reverse_epochs_s": list(reversed(_EPOCHS)),
            "forward_states": [[float(value) for value in row] for row in forward],
            "reverse_states": [[float(value) for value in row] for row in reverse],
            "decimal100": {"original_forward": [[str(value) for value in row] for row in physical],
                           "binary_forward": [[str(value) for value in row] for row in forward],
                           "binary_reverse": [[str(value) for value in row] for row in reverse]},
            "precision_differences": precision, "mass_ledgers": ledgers,
            "conversion_differences": {
                "forward_binary_constants_minus_original": _signed(forward, physical),
                "reverse_binary_constants_minus_original_same_rounded_start": _signed(reverse, physical_reverse),
                "reverse_target_rounding_response": _signed(physical_reverse, list(reversed(physical))),
                "original_target_rounding": _signed([frozen], [physical[-1]])[0],
                "forward_output_rounding": _signed(rounded_forward, forward),
                "reverse_output_rounding": _signed(rounded_reverse, reverse)},
            "effective_exhaust_m_s_decimal100": effective_exhaust,
            "interpretation": "Synthetic elapsed clock; constant and target-rounding effects remain separate. Native Time equality is not reconstructed from labels."}


def _state(value: object, field: str) -> list[float]:
    state = [_number(item, field) for item in _list(value, 7, field)]
    _need(state[6] >= 500.0, field + ": mass below dry mass")
    r, v = state[:3], state[3:6]
    angular = [r[1] * v[2] - r[2] * v[1], r[2] * v[0] - r[0] * v[2],
               r[0] * v[1] - r[1] * v[0]]
    _need(math.isfinite(math.hypot(*angular)) and math.hypot(*angular) > 0.0
          and math.hypot(*v) > 0.0, field + ": degenerate TNW")
    return state


def _same_state(actual: list[float], expected: list[float], field: str) -> None:
    _need([value.hex() for value in actual] == [value.hex() for value in expected],
          field + ": actual state or mass was reset")


def _event(value: object, requested: int, field: str) -> dict[str, object]:
    event = _mapping(value, field, {"requested", "label_hex", "observed_label_s", "native_equal", "residual_s"})
    exact = _list(event["requested"], 2, field + ".requested")
    _need(type(exact[0]) is int and type(exact[1]) is int
          and exact == [requested, 1], field + ": exact requested event mismatch")
    label = float(requested)
    _need(Fraction.from_float(label) == Fraction(requested), field + ": unavailable exact label transport")
    _same(event["label_hex"], label.hex(), field + ".label_hex")
    observed = _number(event["observed_label_s"], field + ".observed_label_s")
    residual = _number(event["residual_s"], field + ".residual_s")
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        time_error = max(abs(Decimal.from_float(observed) - Decimal(requested)),
                         abs(Decimal.from_float(residual)))
    _need(time_error <= _LIMITS["epoch_s"], field + ": time gate failed")
    _need(type(event["native_equal"]) is bool and event["native_equal"] is True,
          field + ": producer native equality unavailable")
    _need(observed.hex() == label.hex() and residual == 0.0,
          field + ": producer equality/label/residual incoherent")
    return {"requested": exact.copy(), "label_hex": label.hex(),
            "observed_label_s": observed, "residual_s": residual,
            "epoch_error_s": float(time_error),
            "native_equality_evidence": "producer-observed-only"}


def _errors(state: list[float], expected: list[str], field: str) -> dict[str, object]:
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        differences = [Decimal.from_float(value) - Decimal(target)
                       for value, target in zip(state, expected, strict=True)]
        errors = {"position_m": sum(value * value for value in differences[:3]).sqrt(),
                  "velocity_m_s": sum(value * value for value in differences[3:6]).sqrt(),
                  "mass_kg": abs(differences[6])}
        _need(all(value <= _LIMITS[key] for key, value in errors.items()),
              field + ": dimensional gate failed")
        return {"signed_state_difference": [str(value) for value in differences],
                **{key: float(value) for key, value in errors.items()}}


def _runtime(value: object) -> dict[str, object]:
    runtime = _mapping(value, "runtime", {"python", "tudatpy", "numpy", "source_sha256"})
    _need(type(runtime["python"]) is str and cast(str, runtime["python"]).startswith("3.12."),
          "runtime.python: pinned Python3.12 required")
    _same(runtime["tudatpy"], "1.0.0", "runtime.tudatpy")
    _same(runtime["numpy"], "1.26.4", "runtime.numpy")
    sources = _mapping(runtime["source_sha256"], "runtime.source_sha256", _SOURCE_PATHS)
    root = Path(__file__).resolve().parents[2]
    for path, value in sources.items():
        _need(type(value) is str and _HEX.fullmatch(cast(str, value)) is not None,
              "runtime.source_sha256: malformed digest")
        try:
            actual = sha256((root / path).read_bytes()).hexdigest()
        except OSError as exc:
            raise OracleError("runtime.source_sha256: source unavailable") from exc
        _same(value, actual, "runtime.source_sha256." + path)
    return dict(runtime)


def audit(packet: object, *, deadline: float,
          clock: Callable[[], float] = monotonic) -> dict[str, object]:
    """Audit six retained synthetic arcs, without certifying opaque native Time.

    Endpoint/reference/ledger arithmetic is independent. Native equality and full
    history/stage inspection remain explicitly producer-observed evidence.
    """
    end = _number(deadline, "audit deadline")
    previous = -math.inf

    def check() -> None:
        nonlocal previous
        now = _number(clock(), "audit monotonic clock")
        _need(now >= previous, "audit monotonic clock moved backwards")
        previous = now
        _need(now < end, "audit deadline exceeded")

    check()
    data = _mapping(packet, "packet", {"schema", "frame", "time_scale", "controls", "words", "reference",
                                        "paths", "counts", "status", "failure", "runtime"})
    try:
        encoded = json.dumps(dict(data), allow_nan=False, sort_keys=True).encode()
    except (TypeError, ValueError) as exc:
        raise OracleError("packet: finite JSON required") from exc
    _need(len(encoded) <= _PRODUCER_BYTES, "packet: producer evidence exceeds1 MiB")
    _same(data["schema"], "ariadna-native-conformance-v1", "schema")
    for key, value in _LABELS.items():
        _same(data[key], value, key)
    _same(data["controls"], _CONTROLS, "controls")
    _same(data["status"], "passed", "status: incomplete/unavailable result is unqualified")
    _same(data["failure"], None, "failure")
    runtime = _runtime(data["runtime"])
    expected = reference()
    check()
    _same(data["words"], expected["words"], "words")
    _same(data["reference"], expected["original_reference"], "original reference")
    original_packet = _mapping(expected["original_reference"], "generated original reference")
    original_states = cast(list[list[float]], original_packet["states"])
    paths = _mapping(data["paths"], "paths", {"forward", "reverse"})
    counts = _mapping(data["counts"], "counts", {"native_attempts", "provider_attempts", "contexts_created",
        "contexts_closed", "native_reported_function_evaluations", "spice_queries", "kernel_reads",
        "real_archive_reads", "optimizer_entries"})
    for name in ("native_attempts", "contexts_created", "contexts_closed"):
        _need(_integer(counts[name], "counts." + name, 6) == 6,
              "counts." + name + ": complete six-arc count required")
    provider_total = _integer(counts["provider_attempts"], "counts.provider_attempts", 100000)
    _need(provider_total > 0, "counts.provider_attempts: missing native work")
    for name in _ZERO[1:]:
        _need(_integer(counts[name], "counts." + name, 0) == 0, "counts." + name)
    reported = [_integer(value, "counts.native_reported_function_evaluations", 2**53)
                for value in _list(counts["native_reported_function_evaluations"], 6, "reported counts")]
    checks: list[dict[str, object]] = []
    provider_sum, native_reported = 0, []
    decimal_nodes = cast(dict[str, list[list[str]]], expected["decimal100"])
    ledgers = cast(dict[str, list[list[int]]], expected["mass_ledgers"])
    for name, direction, modes in (("forward", 1, ("departure-burn", "coast", "arrival-burn")),
                                    ("reverse", -1, ("arrival-burn", "coast", "departure-burn"))):
        epochs = _EPOCHS if direction == 1 else tuple(reversed(_EPOCHS))
        rows = _list(paths[name], 3, "paths." + name)
        previous_state = list(_INITIAL) if direction == 1 else original_states[-1].copy()
        physical = decimal_nodes["original_forward"] if direction == 1 else list(reversed(decimal_nodes["original_forward"]))
        binary = decimal_nodes["binary_forward" if direction == 1 else "binary_reverse"]
        for index, value in enumerate(rows):
            check()
            label = f"{name}[{index}]"
            row = _mapping(value, label, {"mode", "direction", "start_event", "end_event", "start_state",
                "end_state", "provider_attempts", "native_reported_function_evaluations", "samples_checked"})
            _same(row["mode"], modes[index], label + ".mode")
            _need(type(row["direction"]) is int and row["direction"] == direction,
                  label + ": direction mismatch")
            events = [_event(row["start_event"], epochs[index], label + ".start_event"),
                      _event(row["end_event"], epochs[index + 1], label + ".end_event")]
            start, finish = _state(row["start_state"], label + ".start_state"), _state(row["end_state"], label + ".end_state")
            _same_state(start, previous_state, label + ".carry")
            endpoint_checks = []
            for offset, state in enumerate((start, finish)):
                at = index + offset
                ledger = Fraction(*ledgers[name][at])
                mass_difference = Fraction.from_float(state[6]) - ledger
                _need(abs(mass_difference) <= Fraction(1, 1000000000), label + ": exact mass ledger gate failed")
                endpoint_checks.append({"original_decimal": _errors(state, physical[at], label + ".original"),
                    "binary_words": _errors(state, binary[at], label + ".binary"),
                    "mass_ledger_kg": _fraction(ledger), "signed_mass_minus_ledger_kg": _fraction(mass_difference),
                    "mass_ledger_error_kg": float(abs(mass_difference))})
            providers = _integer(row["provider_attempts"], label + ".provider_attempts", 100000)
            _need(providers > 0, label + ": missing provider attempts")
            provider_sum += providers
            native_reported.append(_integer(row["native_reported_function_evaluations"], label + ".reported functions", 2**53))
            samples = _integer(row["samples_checked"], label + ".samples_checked", 2**53)
            _need(samples >= 2, label + ": missing endpoint/history samples")
            checks.append({"path": name, "arc_index": index, "mode": modes[index], "direction": direction,
                           "events": events, "endpoints": endpoint_checks,
                           "provider_attempts": providers, "samples_checked": samples})
            previous_state = finish
    _need(provider_sum == provider_total, "counts.provider_attempts: arc sum mismatch")
    _need(native_reported == reported, "counts.native_reported_function_evaluations: arc list mismatch")
    check()
    return {"schema": "ariadna-native-conformance-audit-v1", **_LABELS, "status": "passed",
            "arc_checks": checks, "reference": expected, "runtime": runtime,
            "counts": {"audited_arcs": 6, "audited_events": 12, **dict.fromkeys(_ZERO, 0)},
            "native_time_equality": {"evidence": "producer-observed-only", "independently_certified": False},
            "history_domain_evidence": "Retained endpoints independently checked; unretained native stages/history remain producer-observed.",
            "reported_function_evaluations": "Producer post-run maximum values; not a live total-RHS hard limit.",
            "physical_status": "not-established"}
