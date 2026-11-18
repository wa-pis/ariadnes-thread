"""Independent saved-point containment checks for artificial observational traces."""

from decimal import Decimal, InvalidOperation
from fractions import Fraction
import math
from types import ModuleType
from typing import Any

type Row = dict[str, Any]
type Bounds = tuple[Decimal, Decimal]


def _need(ok: object, message: str) -> None:
    if not ok:
        raise ValueError(f"artificial trace containment: {message}")


def _row(value: Any, label: str) -> Row:
    _need(type(value) is dict, f"{label} must be a record")
    return value


def _decimal(value: Any, label: str) -> Decimal:
    _need(type(value) is str and 0 < len(value) <= 512, f"{label} decimal text")
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"artificial trace containment: {label} invalid decimal") from error
    _need(number.is_finite() and str(number) == value and abs(number.adjusted()) <= 400,
          f"{label} canonical finite decimal")
    return number


def _range(event: Row, path: str) -> Bounds:
    fields = _row(event.get("fields"), "event fields")
    endpoint = _row(fields.get(path), f"missing numeric range {path}")
    _need(set(endpoint) == {"lo", "hi"}, f"{path} endpoint inventory")
    lo, hi = (_decimal(endpoint[key], f"{path}.{key}") for key in ("lo", "hi"))
    _need(lo <= hi, f"{path} endpoint order")
    return lo, hi


def _contains(event: Row, path: str, value: Decimal) -> None:
    _need(value.is_finite(), f"{path} finite oracle quantity")
    lo, hi = _range(event, path)
    _need(lo <= value <= hi, f"{path} excludes independent quantity {value}")


def _same(left: Row, left_path: str, right: Row, right_path: str) -> None:
    _need(_range(left, left_path) == _range(right, right_path),
          f"disconnected ranges {left_path}/{right_path}")


def _returned(events: list[Row], stage: str) -> Row:
    selected = [event for event in events if event.get("stage") == stage and event.get("event") == "return"]
    _need(len(selected) == 1, f"missing or repeated completed {stage} stage")
    return selected[0]


def _phase(value: Any, label: str) -> Fraction:
    _need(type(value) is str and 0 < len(value) <= 64, f"{label} phase text")
    try:
        phase = Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"artificial trace containment: {label} invalid phase") from error
    _need(str(phase) == value and 150 <= phase <= 152
          and phase.denominator in (1, 2, 4, 8, 16, 32, 64), f"{label} dyadic phase")
    return phase


def _point_gates(ref: Row, point: Row, sign: str, methods: dict[str, ModuleType]) -> tuple[Decimal, Decimal]:
    """Read back existing point parity gates without a phase or conic evaluation."""
    source = _row(ref.get("normalized"), "reference source")
    _need(source.get("scope") == "artificial" and source.get("candidate_id") == "artificial-moon-mars"
          and source.get("command_words") is None and source.get("live_authorized") is False,
          "artificial diagnostic reference required")
    _need(point.get("unresolved") is False, "unresolved point cannot qualify containment")
    endpoints = source.get("endpoints")
    _need(type(endpoints) is list and len(endpoints) == 2, "fixed endpoint inventory")
    moon, mars = (_row(endpoint, "endpoint") for endpoint in endpoints)
    _need(moon.get("body") == "Moon" and mars.get("body") == "Mars", "fixed endpoint order")
    branch = _row(_row(point.get("branches"), "point branches").get(sign), "point branch")
    _need(branch.get("reason") in (None, "guard"), "point branch has failed existing parity gates")
    local = point.get("relative_si")
    _need(type(local) is list and len(local) == 6
          and all(type(value) is float and math.isfinite(value) for value in local), "binary64 point state")
    endpoint = mars | {"relative_si": [str(Decimal.from_float(value)) for value in local]}
    reader = methods["reader"]
    _need(reader._root(ref["lunar"], moon) is None, "fixed lunar point gates")
    _need(reader._root(branch, endpoint) == branch["reason"], "arrival point gates")
    discrepancies = _row(point.get("discrepancies"), "point state discrepancies")
    limits = {"relative_position_m": 0.001, "relative_velocity_m_s": 1e-6,
              "ssb_position_m": 0.001, "ssb_velocity_m_s": 1e-6}
    _need(set(discrepancies) == set(limits), "point state parity inventory")
    _need(all(type(discrepancies[key]) is float and math.isfinite(discrepancies[key])
              and 0 <= discrepancies[key] <= limit for key, limit in limits.items()),
          "point state exceeds existing parity gates")
    departure = _decimal(ref["lunar"]["independent_speed_m_s"], "lunar oracle impulse")
    arrival = _decimal(branch["independent_speed_m_s"], "arrival oracle impulse")
    _need(min(departure, arrival) > 0, "positive independent impulse norms")
    return departure, arrival


def verify_containment(ref: Row, point: Row, trace: Row, sign: str,
                       methods: dict[str, ModuleType]) -> Row:
    """Check saved Decimal96 points in sealed artificial trace ranges, with no new conic solve.

    Values use SI in J2000 orientation. The separately rounded binary64 geometry
    retains its existing point parity gates; containment uses independent geometry.
    Only the designated mass-comparison durations undergo binary64 containment.
    """
    _need(sign in ("positive", "negative"), "signed branch required")
    methods["trace"].verify_trace(trace)
    _need(trace.get("sign") == sign, "point/trace branch identity")
    phase = _phase(point.get("phase_deg"), "point")
    lo, hi = (_phase(trace.get(key), f"trace {key}") for key in ("lo", "hi"))
    _need(lo <= phase <= hi, "point outside traced phase cell")
    departure, arrival = _point_gates(ref, point, sign, methods)
    events = trace.get("events")
    _need(type(events) is list and all(type(event) is dict for event in events), "event inventory")
    ellipse, reverse, mass, bound = (_returned(events, name) for name in (
        "_ellipse", "_reverse", "_mass_exclusion", "bounds"))
    precise = point.get("independent_relative_si")
    _need(type(precise) is list and len(precise) == 6, "independent ellipse state inventory")
    state = tuple(_decimal(value, "independent ellipse state") for value in precise)
    for index, value in enumerate(state):
        group, component = divmod(index, 3)
        path = f"return[{group}][{component}]"
        _contains(ellipse, path, value)
        _same(ellipse, path, bound, f"{'r' if group == 0 else 'orbital'}[{component}]")
    _contains(ellipse, "anomaly", _decimal(point["independent_angle_rad"], "independent anomaly"))
    _same(ellipse, "return[2]", bound, "mu")
    for index in range(3):
        _same(reverse, f"return[{index}]", bound, f"future[{index}]")
    root_lo, root_hi = _range(reverse, "root")
    _need(root_lo > 0 if sign == "positive" else root_hi < 0, "root enclosure sign")
    _contains(bound, "speed", arrival)
    _contains(mass, "departure", departure)
    _contains(mass, "arrival", arrival)
    _same(mass, "arrival", bound, "speed")
    result = _row(trace.get("result"), "bound result")
    speed_bounds = result.get("arrival_speed_bounds_m_s")
    _need(type(speed_bounds) is list and len(speed_bounds) == 2, "final norm endpoint inventory")
    _need(tuple(_decimal(value, "final norm endpoint") for value in speed_bounds) == _range(bound, "speed"),
          "final norm differs from observed norm")
    durations, masses = methods["oracle"].mass(departure, arrival)
    _need(len(durations) == len(masses) == 2, "independent mass return inventory")
    for path, value in zip(("coast", "final", "durations[0]", "durations[1]"),
                           (*masses, *durations), strict=True):
        _need(type(value) is Decimal, "Decimal96 oracle mass value")
        _contains(mass, path, value)
    words = result.get("duration_comparison_lower_words")
    _need(type(words) is list and len(words) == 2, "comparison duration endpoint inventory")
    comparison_words = []
    mass_scalars = _row(mass.get("scalars"), "mass scalar inventory")
    for index, duration in enumerate(durations):
        comparison = float(duration)
        _need(math.isfinite(comparison), "finite designated binary64 duration")
        _contains(mass, f"observed_duration_binary64[{index}]", Decimal.from_float(comparison))
        word = words[index]
        _need(type(word) is str, "binary64 lower word")
        try:
            lower = float.fromhex(word)
        except ValueError as error:
            raise ValueError("artificial trace containment: malformed binary64 lower word") from error
        _need(math.isfinite(lower) and lower.hex() == word and lower <= comparison,
              "binary64 lower endpoint excludes designated duration")
        _need(mass_scalars.get(f"conversion_lower[{index}]") == word,
              "final comparison lower differs from original conversion")
        comparison_words.append(comparison.hex())
    return dict(status="verified", scope="artificial", phase_deg=str(phase), sign=sign,
                independent_arrival_speed_m_s=str(arrival), independent_relative_si=list(precise),
                independent_durations_s=[str(value) for value in durations],
                independent_masses_kg=[str(value) for value in masses],
                comparison_duration_words=comparison_words,
                containment_checks=16)
