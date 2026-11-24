"""ADR0250 artificial coordinate bridge; no native adapter or physical solver."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from fractions import Fraction
import math
from numbers import Real
import time
from types import MappingProxyType
from typing import Literal

from .errors import TrajectoryRefinementError
from .transfer import STANDARD_GRAVITY_M_S2


_SCALE = (1000.0, 1000.0, 1000.0, 1.0, 1.0, 1.0)
_RESIDUAL_SCALE = (1000.0, 1000.0, 1000.0, 0.01, 0.01, 0.01) * 3
_ARCS = ("departure-burn", "coast", "arrival-burn")
_MASS_TOLERANCE = Fraction(1e-9)
_TIME_TOLERANCE = Fraction(1e-6)


class BridgeError(TrajectoryRefinementError):
    """An artificial bridge input, endpoint or fixed work limit failed."""


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise BridgeError(f"{field}: finite nonboolean number required")
    try:
        result = float(value)
    except OverflowError as exc:
        raise BridgeError(f"{field}: finite binary64 value required") from exc
    if not math.isfinite(result):
        raise BridgeError(f"{field}: finite binary64 value required")
    return result


def _vector(values: object, length: int, field: str) -> tuple[float, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) != length:
        raise BridgeError(f"{field}: {length} numbers required")
    return tuple(_number(value, field) for value in values)


def _rounded(value: Fraction, field: str) -> float:
    try:
        return _number(float(value), field)
    except OverflowError as exc:
        raise BridgeError(f"{field}: exact value exceeds binary64 range") from exc


@dataclass(frozen=True, slots=True)
class BridgeSpec:
    initial_state: tuple[float, ...]
    target_state: tuple[float, ...]
    t0_s: float
    tf_s: float
    initial_mass_kg: float
    dry_mass_kg: float
    thrust_n: float
    isp_s: float
    anchors: tuple[tuple[float, ...], tuple[float, ...]]
    artificial: bool

    def __post_init__(self) -> None:
        for field in ("initial_state", "target_state"):
            object.__setattr__(self, field, _vector(getattr(self, field), 6, field))
        for field in ("t0_s", "tf_s", "initial_mass_kg", "dry_mass_kg", "thrust_n", "isp_s"):
            object.__setattr__(self, field, _number(getattr(self, field), field))
        if not self.t0_s < self.tf_s:
            raise BridgeError("endpoint words: t0_s must precede tf_s")
        if not self.initial_mass_kg > self.dry_mass_kg > 0 or self.thrust_n <= 0 or self.isp_s <= 0:
            raise BridgeError("vehicle: require initial mass > dry mass > 0 and positive thrust/Isp")
        if not isinstance(self.anchors, Sequence) or len(self.anchors) != 2:
            raise BridgeError("anchors: exactly two six-states required")
        object.__setattr__(self, "anchors", tuple(_vector(row, 6, "anchors") for row in self.anchors))
        if self.artificial is not True:
            raise BridgeError("artificial: explicit True required; native/real data unavailable")


def _spec_words(spec: BridgeSpec) -> tuple[str | bool, ...]:
    values = (*spec.initial_state, *spec.target_state, spec.t0_s, spec.tf_s,
              spec.initial_mass_kg, spec.dry_mass_kg, spec.thrust_n, spec.isp_s,
              *spec.anchors[0], *spec.anchors[1])
    return tuple(value.hex() for value in values) + (spec.artificial,)


@dataclass(frozen=True, slots=True)
class ExactEvent:
    exact_s: Fraction
    label_s: float
    rounding_error_s: Fraction

    def __post_init__(self) -> None:
        if not isinstance(self.exact_s, Fraction) or not isinstance(self.rounding_error_s, Fraction):
            raise BridgeError("event: exact rational epoch and conversion error required")
        object.__setattr__(self, "label_s", _number(self.label_s, "event.label_s"))
        if Fraction(self.label_s) - self.exact_s != self.rounding_error_s:
            raise BridgeError("event: signed conversion error does not match its label")


def _event(exact_s: Fraction, fixed_word: float | None = None) -> ExactEvent:
    label = _rounded(exact_s, "event label") if fixed_word is None else fixed_word
    return ExactEvent(exact_s, label, Fraction(label) - exact_s)


@dataclass(frozen=True, slots=True)
class Plan:
    controls: tuple[float, ...]
    nodes: tuple[tuple[float, ...], tuple[float, ...]]
    events: tuple[ExactEvent, ...]
    exact_masses: tuple[Fraction, ...]
    masses: tuple[float, ...]
    mass_conversion_errors: tuple[Fraction, ...]
    mass_rate_kg_s: float
    float_labels_preserve_events: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "controls", _vector(self.controls, 6, "plan.controls"))
        if not isinstance(self.nodes, Sequence) or len(self.nodes) != 2:
            raise BridgeError("plan.nodes: two nodes required")
        object.__setattr__(self, "nodes", tuple(_vector(row, 6, "plan.nodes") for row in self.nodes))
        for field in ("events", "exact_masses", "masses", "mass_conversion_errors"):
            values = getattr(self, field)
            if not isinstance(values, Sequence) or len(values) != 4:
                raise BridgeError(f"plan.{field}: four entries required")
            object.__setattr__(self, field, tuple(values))
        if not all(isinstance(event, ExactEvent) for event in self.events):
            raise BridgeError("plan.events: exact packets required")
        if not all(isinstance(value, Fraction) for value in self.exact_masses + self.mass_conversion_errors):
            raise BridgeError("plan.mass ledger: exact rational entries required")
        rate = _number(self.mass_rate_kg_s, "plan.mass_rate_kg_s")
        object.__setattr__(self, "mass_rate_kg_s", rate)
        object.__setattr__(self, "masses", _vector(self.masses, 4, "plan.masses"))
        m0, m1, m2, mf = self.exact_masses
        if rate <= 0 or not m0 > m1 == m2 > mf > 0:
            raise BridgeError("plan.mass ledger: invalid sequential mass")
        if m1 != m0 - Fraction(rate) * Fraction(self.controls[2]) or mf != m1 - Fraction(rate) * Fraction(self.controls[5]):
            raise BridgeError("plan.mass ledger: not the pinned binary64-rate ledger")
        if any(Fraction(rounded) - exact != error for exact, rounded, error in
               zip(self.exact_masses, self.masses, self.mass_conversion_errors, strict=True)):
            raise BridgeError("plan.mass ledger: conversion error mismatch")
        t0, t1, t2, tf = (event.exact_s for event in self.events)
        if not t0 < t1 < t2 < tf or t1 != t0 + Fraction(self.controls[2]) or t2 != tf - Fraction(self.controls[5]):
            raise BridgeError("plan.events: duration/order mismatch")
        ready = (all(Fraction(event.label_s) == event.exact_s for event in self.events)
                 and all(left.label_s < right.label_s for left, right in zip(self.events, self.events[1:])))
        if type(self.float_labels_preserve_events) is not bool or self.float_labels_preserve_events != ready:
            raise BridgeError("plan.float_labels_preserve_events: inconsistent rounded spans")


@dataclass(frozen=True, slots=True)
class ArcRequest:
    arc: str
    start_state: tuple[float, ...]
    start_mass_kg: float
    start_event: ExactEvent
    end_event: ExactEvent
    burn_id: Literal["departure", "arrival"] | None
    angles_rad: tuple[float, float] | None
    mode: Literal["burn", "coast"]
    frame: str = "SSB/J2000"
    time_scale: str = "TDB seconds since J2000"
    artificial: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_state", _vector(self.start_state, 6, "arc start_state"))
        object.__setattr__(self, "start_mass_kg", _number(self.start_mass_kg, "arc start_mass_kg"))
        if self.arc not in _ARCS or self.start_mass_kg <= 0:
            raise BridgeError("arc request: invalid arc or mass")
        if not isinstance(self.start_event, ExactEvent) or not isinstance(self.end_event, ExactEvent):
            raise BridgeError("arc request: exact event packets required")
        if self.start_event.exact_s >= self.end_event.exact_s:
            raise BridgeError("arc request: positive exact span required")
        expected_burn = {"departure-burn": "departure", "coast": None, "arrival-burn": "arrival"}[self.arc]
        if self.burn_id != expected_burn or self.mode != ("coast" if expected_burn is None else "burn"):
            raise BridgeError("arc request: explicit burn/coast mode mismatch")
        if expected_burn is None:
            if self.angles_rad is not None:
                raise BridgeError("coast request: no engine/angles allowed")
        else:
            object.__setattr__(self, "angles_rad", _vector(self.angles_rad, 2, "arc angles_rad"))
        if self.frame != "SSB/J2000" or self.time_scale != "TDB seconds since J2000" or self.artificial is not True:
            raise BridgeError("arc request: fixed conventions and artificial=True required")


    @property
    def guidance_reference_body(self) -> str | None:
        return {"departure": "Moon", "arrival": "Mars", None: None}[self.burn_id]

    @property
    def guidance_frame(self) -> str | None:
        return "TNW" if self.burn_id is not None else None


@dataclass(frozen=True, slots=True)
class ArcResponse:
    state: tuple[float, ...]
    mass_kg: float
    event: ExactEvent
    complete: bool
    safe: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", _vector(self.state, 6, "arc response.state"))
        object.__setattr__(self, "mass_kg", _number(self.mass_kg, "arc response.mass_kg"))
        if self.mass_kg <= 0 or not isinstance(self.event, ExactEvent):
            raise BridgeError("arc response: positive mass and exact time information required")
        if type(self.complete) is not bool or type(self.safe) is not bool:
            raise BridgeError("arc response: explicit completion and safety booleans required")


@dataclass(frozen=True, slots=True)
class BridgeResult:
    plan: Plan
    starts: tuple[ArcRequest, ...]
    ends: tuple[ArcResponse, ...]
    raw_defects: tuple[float, ...]
    scaled_defects: tuple[float, ...]
    mode: Literal["shooting", "replay"]
    counts: Mapping[str, int]

    def __post_init__(self) -> None:
        if not isinstance(self.plan, Plan) or self.mode not in ("shooting", "replay"):
            raise BridgeError("result: plan and explicit evaluation mode required")
        for field, kind in (("starts", ArcRequest), ("ends", ArcResponse)):
            values = getattr(self, field)
            if len(values) != 3 or not all(isinstance(value, kind) for value in values):
                raise BridgeError(f"result.{field}: three arc packets required")
            object.__setattr__(self, field, tuple(values))
        for field in ("raw_defects", "scaled_defects"):
            object.__setattr__(self, field, _vector(getattr(self, field), 18, f"result.{field}"))
        if not isinstance(self.counts, Mapping) or not all(type(value) is int and value >= 0 for value in self.counts.values()):
            raise BridgeError("result.counts: nonnegative integer counters required")
        object.__setattr__(self, "counts", MappingProxyType(dict(self.counts)))


class Budget:
    """Inherited artificial fixture clock; simulated slots never count as native."""

    def __init__(self, *, started_s: float, monotonic: Callable[[], float] = time.monotonic) -> None:
        self.started_s = _number(started_s, "budget.started_s")
        self.monotonic = monotonic
        self.control_attempts = 0
        self.propagation_evaluations = 0
        self.simulated_arc_slots = 0
        self.diagnostic_attempts = 0
        self.input_bytes = 0
        self.output_bytes = 0
        self._last_s = self.started_s
        self._arcs_in_evaluation = 0
        self._failed = False
        self._contexts: list[object] = []
        self._flows: list[object] = []
        self._last_controls: tuple[float, ...] | None = None
        self._last_spec_words: tuple[str | bool, ...] | None = None
        self.check_producer()

    def _fail(self, message: str) -> None:
        self._failed = True
        raise BridgeError(f"artificial budget: {message}")

    def _clock(self, seconds: float) -> None:
        previously_failed = self._failed
        # A callback exception must leave a poisoned budget even when a caller
        # catches it directly and later repairs the injected clock.
        self._failed = True
        try:
            now = _number(self.monotonic(), "budget monotonic clock")
        except (RuntimeError, ValueError, TypeError, ArithmeticError) as exc:
            raise BridgeError(f"budget monotonic clock: read failed: {exc}") from exc
        if now < self._last_s:
            self._fail("monotonic clock moved backwards")
        self._last_s = now
        if now >= self.started_s + seconds:
            self._fail(f"inherited {seconds:g}s deadline exhausted")
        self._failed = previously_failed

    def check_producer(self) -> None:
        self._clock(10.0)
        if self._failed:
            raise BridgeError("artificial budget: earlier failure; no retry")

    def check_finalization(self) -> None:
        self._clock(15.0)

    def begin_control(self) -> None:
        self.check_producer()
        if self.control_attempts >= 73:
            self._fail("73 control attempts exhausted")
        self.control_attempts += 1

    def begin_diagnostic(self) -> None:
        self.check_producer()
        if self.diagnostic_attempts >= 3:
            self._fail("3 frozen diagnostic attempts exhausted")
        self.diagnostic_attempts += 1

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check_producer()
        if type(first_in_evaluation) is not bool:
            self._fail("first_in_evaluation must be boolean")
        if self.simulated_arc_slots >= 228:
            self._fail("228 simulated arc slots exhausted")
        if first_in_evaluation:
            if self.propagation_evaluations >= 76:
                self._fail("76 propagation evaluations exhausted")
            self.propagation_evaluations += 1
            self._arcs_in_evaluation = 0
        elif not 1 <= self._arcs_in_evaluation < 3:
            self._fail("continuation requires a pending three-arc evaluation")
        self._arcs_in_evaluation += 1
        self.simulated_arc_slots += 1

    def check_input_bytes(self, raw: bytes) -> None:
        self.check_producer()
        if type(raw) is not bytes or self.input_bytes + len(raw) > 65536:
            self._fail("64 KiB input byte cap exceeded or nonbytes input")
        self.input_bytes += len(raw)

    def check_output_bytes(self, raw: bytes) -> None:
        self.check_finalization()
        if type(raw) is not bytes or self.output_bytes + len(raw) > 131072:
            self._fail("128 KiB output byte cap exceeded or nonbytes output")
        self.output_bytes += len(raw)

    def snapshot(self) -> dict[str, int]:
        return {
            "control_attempts": self.control_attempts,
            "propagation_evaluations": self.propagation_evaluations,
            "simulated_arc_slots": self.simulated_arc_slots,
            "diagnostic_attempts": self.diagnostic_attempts,
            "input_bytes": self.input_bytes, "output_bytes": self.output_bytes,
            "native_propagations": 0, "spice_queries": 0, "kernel_reads": 0,
            "real_archive_reads": 0, "integrations": 0, "optimizer_calls": 0,
        }


def decode(spec: BridgeSpec, unknowns: object) -> Plan:
    """Decode artificial SI nodes and exact input-word event/mass semantics."""
    if not isinstance(spec, BridgeSpec):
        raise BridgeError("spec: immutable artificial BridgeSpec required")
    values = _vector(unknowns, 18, "unknowns")
    controls = list(values[:6])
    for index in (0, 3):
        controls[index] = math.remainder(controls[index], math.tau)
        if controls[index] == math.pi:
            controls[index] = -math.pi
    if abs(controls[1]) > math.pi / 2 or abs(controls[4]) > math.pi / 2 or controls[2] <= 0 or controls[5] <= 0:
        raise BridgeError("controls: elevation bounds and positive durations required")
    t0, tf = Fraction(spec.t0_s), Fraction(spec.tf_s)
    times = (t0, t0 + Fraction(controls[2]), tf - Fraction(controls[5]), tf)
    if not all(left < right for left, right in zip(times, times[1:])):
        raise BridgeError("controls: strictly positive coast and ordered exact events required")
    exhaust = _number(STANDARD_GRAVITY_M_S2 * spec.isp_s, "binary64 exhaust velocity")
    if exhaust <= 0:
        raise BridgeError("binary64 exhaust velocity: positive value required")
    rate = _number(spec.thrust_n / exhaust, "binary64 mass rate")
    if rate <= 0:
        raise BridgeError("binary64 mass rate: positive value required")
    m0 = Fraction(spec.initial_mass_kg)
    m1 = m0 - Fraction(rate) * Fraction(controls[2])
    mf = m1 - Fraction(rate) * Fraction(controls[5])
    exact_masses = (m0, m1, m1, mf)
    if mf < Fraction(spec.dry_mass_kg):
        raise BridgeError("mass ledger: exact terminal mass below dry mass")
    masses = tuple(_rounded(value, "mass ledger") for value in exact_masses)
    events = tuple(_event(value, fixed_word) for value, fixed_word in
                   zip(times, (spec.t0_s, None, None, spec.tf_s), strict=True))
    nodes = []
    for anchor, offsets in zip(spec.anchors, (values[6:12], values[12:18]), strict=True):
        nodes.append(tuple(base if offset == 0 else
                           _rounded(Fraction(base) + Fraction(scale) * Fraction(offset), "decoded node")
                           for base, scale, offset in zip(anchor, _SCALE, offsets, strict=True)))
    return Plan(tuple(controls), tuple(nodes), events, exact_masses, masses,
                tuple(Fraction(rounded) - exact for rounded, exact in zip(masses, exact_masses, strict=True)),
                rate, all(Fraction(event.label_s) == event.exact_s for event in events)
                and all(left.label_s < right.label_s for left, right in zip(events, events[1:])))


def perturb(spec: BridgeSpec, unknowns: object, index: int) -> tuple[float, ...]:
    """Apply one frozen physical forward probe; reject a vanished signal."""
    if type(index) is not int or not 0 <= index < 18:
        raise BridgeError("perturbation index: integer in [0,17] required")
    values = _vector(unknowns, 18, "perturbation unknowns")
    before = decode(spec, values)
    if index < 6:
        step = 1.0 if index in (2, 5) else 1e-5
        normalized_step = Fraction(step)
    else:
        component = (index - 6) % 6
        step = 1.0 if component < 3 else 1e-4
        normalized_step = Fraction(step) / Fraction(_SCALE[component])
    changed = list(values)
    changed[index] = _rounded(Fraction(values[index]) + normalized_step, "physical perturbation")
    after = decode(spec, changed)
    old_value = before.controls[index] if index < 6 else before.nodes[(index - 6) // 6][(index - 6) % 6]
    new_value = after.controls[index] if index < 6 else after.nodes[(index - 6) // 6][(index - 6) % 6]
    if changed[index] == values[index] or new_value == old_value:
        raise BridgeError("physical perturbation collapsed in binary64 reconstruction")
    return tuple(changed)


ArcFlow = Callable[[ArcRequest], ArcResponse]
ArcFactory = Callable[[], AbstractContextManager[ArcFlow]]


def evaluate(spec: BridgeSpec, unknowns: object, *, mode: Literal["shooting", "replay"],
             arc_factory: ArcFactory, budget: Budget, diagnostic: bool = False) -> BridgeResult:
    """Evaluate exactly one artificial three-arc path; never run native dynamics."""
    if not isinstance(budget, Budget):
        raise BridgeError("budget: inherited artificial Budget required")
    try:
        if type(diagnostic) is not bool or mode not in ("shooting", "replay"):
            raise BridgeError("evaluation: explicit shooting/replay mode and diagnostic boolean required")
        if diagnostic:
            budget.begin_diagnostic()
        else:
            budget.begin_control()
        plan = decode(spec, unknowns)
        if diagnostic and (
            mode != "replay" or budget._last_controls is None
            or tuple(value.hex() for value in plan.controls)
            != tuple(value.hex() for value in budget._last_controls)
            or _spec_words(spec) != budget._last_spec_words
        ):
            raise BridgeError("diagnostic: latest complete frozen spec words and controls required")
        budget.check_producer()
        context = arc_factory()
        if len(budget._contexts) >= 76 or any(context is prior for prior in budget._contexts):
            raise BridgeError("arc factory: fresh mutable context required for every evaluation")
        budget._contexts.append(context)
        starts: list[ArcRequest] = []
        ends: list[ArcResponse] = []
        with context as flow:
            budget.check_producer()
            if not callable(flow):
                raise BridgeError("arc factory: context must yield an arc callable")
            if len(budget._flows) >= 76 or any(flow is prior for prior in budget._flows):
                raise BridgeError("arc factory: fresh yielded arc callable required for every evaluation")
            budget._flows.append(flow)
            for index, arc in enumerate(_ARCS):
                state = spec.initial_state if index == 0 else (
                    plan.nodes[index - 1] if mode == "shooting" else ends[-1].state)
                mass = plan.masses[index] if mode == "shooting" or index == 0 else ends[-1].mass_kg
                burn_id = "departure" if index == 0 else "arrival" if index == 2 else None
                angles = tuple(plan.controls[0:2] if index == 0 else plan.controls[3:5]) if burn_id else None
                request = ArcRequest(arc, state, mass, plan.events[index], plan.events[index + 1],
                                     burn_id, angles, "burn" if burn_id else "coast")
                budget.begin_arc(first_in_evaluation=index == 0)
                response = flow(request)
                budget.check_producer()
                if not isinstance(response, ArcResponse):
                    raise BridgeError(f"{arc}: immutable ArcResponse required")
                if not response.complete or not response.safe:
                    raise BridgeError(f"{arc}: failed/partial or unresolved/unsafe arc")
                if response.event.exact_s != request.end_event.exact_s:
                    raise BridgeError(f"{arc}: exact endpoint event identity mismatch")
                if abs(Fraction(response.event.label_s) - request.end_event.exact_s) > _TIME_TOLERANCE:
                    raise BridgeError(f"{arc}: rounded endpoint label exceeds 1e-6 s")
                ledger = plan.exact_masses[index + 1]
                if response.mass_kg < spec.dry_mass_kg or abs(Fraction(response.mass_kg) - ledger) > _MASS_TOLERANCE:
                    raise BridgeError(f"{arc}: dry mass or global mass ledger gate failed")
                duration = request.end_event.exact_s - request.start_event.exact_s
                local_mass = Fraction(request.start_mass_kg) - (Fraction(plan.mass_rate_kg_s) * duration if burn_id else 0)
                if abs(Fraction(response.mass_kg) - local_mass) > _MASS_TOLERANCE:
                    raise BridgeError(f"{arc}: carried mass/coast ledger gate failed")
                starts.append(request)
                ends.append(response)
        budget.check_producer()
        if len(ends) != 3:
            raise BridgeError("arc context suppressed a failure; three completed arcs required")
        targets = (*plan.nodes, spec.target_state)
        defects = tuple(_number(actual - target, "raw defect")
                        for response, desired in zip(ends, targets, strict=True)
                        for actual, target in zip(response.state, desired, strict=True))
        scaled = tuple(_number(value / scale, "scaled defect")
                       for value, scale in zip(defects, _RESIDUAL_SCALE, strict=True))
        if not diagnostic:
            budget._last_controls = plan.controls
            budget._last_spec_words = _spec_words(spec)
        return BridgeResult(plan, tuple(starts), tuple(ends), defects, scaled, mode, budget.snapshot())
    except BridgeError:
        budget._failed = True
        raise
    except (TypeError, ValueError, RuntimeError, ArithmeticError, LookupError) as exc:
        budget._failed = True
        raise BridgeError(f"artificial arc evaluation: {exc}") from exc
