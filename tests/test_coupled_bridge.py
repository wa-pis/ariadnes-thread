"""Independent artificial ADR0250 checks; no native dynamics or ephemerides."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from decimal import Decimal, localcontext
from fractions import Fraction
import math

import pytest

from space_nav import _coupled_bridge as bridge
from space_nav.models import SpacecraftSpec
from space_nav.trajectory import _prepare_burn_controls

State = tuple[float, float, float, float, float, float]
ResponseHook = Callable[[bridge.ArcRequest, bridge.ArcResponse], bridge.ArcResponse]


def _values() -> tuple[float, ...]:
    return (0.125, -0.0625, 1000.125, -0.25, 0.125, 1200.375) + (0.0,) * 12


def _event(exact_s: Fraction) -> bridge.ExactEvent:
    label_s = float(exact_s)
    return bridge.ExactEvent(exact_s, label_s, Fraction(label_s) - exact_s)


def _affine_step(
    state: State, mass_kg: float, duration_s: Fraction,
    angles_rad: tuple[float, float] | None, mass_rate_kg_s: float,
) -> tuple[State, float]:
    """Closed-form test-data transform, deliberately not a TNW/force model."""
    acceleration = (
        (Fraction(angles_rad[0]) / 16, Fraction(angles_rad[1]) / 32, Fraction(1, 64))
        if angles_rad is not None else (Fraction(0),) * 3
    )
    result = tuple(
        float(Fraction(state[i]) + Fraction(state[i + 3]) * duration_s
              + acceleration[i] * duration_s * duration_s / 2)
        for i in range(3)
    ) + tuple(
        float(Fraction(state[i + 3]) + acceleration[i] * duration_s)
        for i in range(3)
    )
    next_mass = Fraction(mass_kg)
    if angles_rad is not None:
        next_mass -= Fraction(mass_rate_kg_s) * duration_s
    return result, float(next_mass)


def _translate(state: State, elapsed_s: Fraction) -> State:
    position_shift = (2 ** 37, -(2 ** 37), 2 ** 37)
    velocity_shift = (2 ** 14, -(2 ** 14), 2 ** 14)
    return tuple(
        float(Fraction(state[i]) + position_shift[i] + velocity_shift[i] * elapsed_s)
        for i in range(3)
    ) + tuple(float(Fraction(state[i + 3]) + velocity_shift[i]) for i in range(3))


def _spec(*, shifted: bool = False, **changes: object) -> bridge.BridgeSpec:
    values = _values()
    duration_d = Fraction(values[2])
    duration_a = Fraction(values[5])
    duration_total = Fraction(10000.25)
    initial: State = (10000000.0, -20000000.0, 30000000.0, 1000.0, 2000.0, -1500.0)
    rate = 1000.0 / (9.80665 * 450.0)
    first, first_mass = _affine_step(initial, 2000.0, duration_d, values[:2], rate)
    second, second_mass = _affine_step(
        first, first_mass, duration_total - duration_d - duration_a, None, rate,
    )
    final, _ = _affine_step(second, second_mass, duration_a, values[3:5], rate)
    if shifted:
        initial = _translate(initial, Fraction(0))
        first = _translate(first, duration_d)
        second = _translate(second, duration_total - duration_a)
        final = _translate(final, duration_total)
    epoch = 1e9 if shifted else 0.0
    data: dict[str, object] = {
        "initial_state": initial, "target_state": final,
        "t0_s": epoch, "tf_s": epoch + float(duration_total),
        "initial_mass_kg": 2000.0, "dry_mass_kg": 500.0,
        "thrust_n": 1000.0, "isp_s": 450.0, "anchors": (first, second),
        "artificial": True,
    }
    data.update(changes)
    return bridge.BridgeSpec(**data)


@dataclass
class _Clock:
    now_s: float = 0.0

    def __call__(self) -> float:
        return self.now_s


def _budget(clock: _Clock | None = None) -> bridge.Budget:
    return bridge.Budget(started_s=0.0, monotonic=clock or _Clock())


@dataclass
class _AffineFactory:
    spec: bridge.BridgeSpec
    response_hook: ResponseHook | None = None
    requests: list[bridge.ArcRequest] = field(default_factory=list)
    responses: list[bridge.ArcResponse] = field(default_factory=list)
    opened: int = 0
    closed: int = 0

    @contextmanager
    def __call__(self) -> Iterator[Callable[[bridge.ArcRequest], bridge.ArcResponse]]:
        self.opened += 1
        def flow(request: bridge.ArcRequest) -> bridge.ArcResponse:
            return self.run(request)
        try:
            yield flow
        finally:
            self.closed += 1

    def run(self, request: bridge.ArcRequest) -> bridge.ArcResponse:
        self.requests.append(request)
        state, mass = _affine_step(
            request.start_state, request.start_mass_kg,
            request.end_event.exact_s - request.start_event.exact_s,
            request.angles_rad, self.spec.thrust_n / (9.80665 * self.spec.isp_s),
        )
        response = bridge.ArcResponse(state, mass, _event(request.end_event.exact_s), True, True)
        if self.response_hook is not None:
            response = self.response_hook(request, response)
        self.responses.append(response)
        return response


def _evaluate(
    spec: bridge.BridgeSpec | None = None, values: tuple[float, ...] | None = None,
    *, mode: str = "shooting", factory: _AffineFactory | None = None,
    budget: bridge.Budget | None = None, diagnostic: bool = False,
) -> tuple[bridge.BridgeResult, _AffineFactory, bridge.Budget]:
    problem = spec or _spec()
    flow = factory or _AffineFactory(problem)
    limits = budget or _budget()
    result = bridge.evaluate(
        problem, values or _values(), mode=mode, arc_factory=flow,
        budget=limits, diagnostic=diagnostic,
    )
    return result, flow, limits


def test_exact_decoder_matches_independent_decimal_affine_map() -> None:
    spec = _spec(shifted=True)
    offsets = (0.1, -0.3, 1 / 3, -0.2, 0.7, 0.125) * 2
    plan = bridge.decode(spec, _values()[:6] + offsets)
    with localcontext() as context:
        context.prec = 200
        for node, anchor, values in zip(plan.nodes, spec.anchors, (offsets[:6], offsets[6:]), strict=True):
            for i, (actual, origin, offset) in enumerate(zip(node, anchor, values, strict=True)):
                scale = 1000.0 if i < 3 else 1.0
                expected = float(
                    Decimal.from_float(origin)
                    + Decimal.from_float(scale) * Decimal.from_float(offset)
                )
                assert actual.hex() == expected.hex()


def test_reconstruction_rounds_once_instead_of_rounding_product_first() -> None:
    spec = _spec(anchors=((1.0,) + _spec().anchors[0][1:], _spec().anchors[1]))
    values = list(_values())
    values[6] = -0.001
    plan = bridge.decode(spec, tuple(values))
    with localcontext() as context:
        context.prec = 200
        expected = float(Decimal(1) + Decimal(1000) * Decimal.from_float(-0.001))
    assert expected != 1.0 + 1000.0 * -0.001
    assert plan.nodes[0][0].hex() == expected.hex()


def test_zero_offsets_preserve_all_anchor_words_including_negative_zero() -> None:
    first: State = (-0.0, 0.0, -0.0, 0.0, -0.0, 0.0)
    second: State = (0.0, -0.0, 0.0, -0.0, 0.0, -0.0)
    plan = bridge.decode(_spec(anchors=(first, second)), _values()[:6] + (-0.0,) * 12)
    assert tuple(x.hex() for node in plan.nodes for x in node) == tuple(
        x.hex() for node in (first, second) for x in node
    )


def test_fractional_epochs_keep_exact_identity_and_signed_conversion_error() -> None:
    spec = _spec(shifted=True)
    values = list(_values())
    values[2] = math.nextafter(values[2], math.inf)
    plan = bridge.decode(spec, tuple(values))
    expected = (
        Fraction(spec.t0_s), Fraction(spec.t0_s) + Fraction(values[2]),
        Fraction(spec.tf_s) - Fraction(values[5]), Fraction(spec.tf_s),
    )
    assert tuple(event.exact_s for event in plan.events) == expected
    assert plan.events[0].label_s.hex() == spec.t0_s.hex()
    assert plan.events[-1].label_s.hex() == spec.tf_s.hex()
    assert plan.events[1].exact_s != Fraction(plan.events[1].label_s)
    for event, exact in zip(plan.events, expected, strict=True):
        assert event.rounding_error_s == Fraction(event.label_s) - exact
        assert abs(event.rounding_error_s) <= Fraction(1, 1000000)


def test_collapsed_float_labels_retain_exact_artificial_span() -> None:
    spec = _spec(shifted=True)
    values = list(_values())
    values[2] = 2 ** -30
    plan = bridge.decode(spec, tuple(values))
    assert plan.events[1].exact_s > plan.events[0].exact_s
    assert plan.events[1].label_s == plan.events[0].label_s
    assert plan.float_labels_preserve_events is False
    result, flow, _ = _evaluate(spec, tuple(values))
    assert len(flow.requests) == 3
    assert result.plan.events[1].exact_s == Fraction(spec.t0_s) + Fraction(values[2])


def test_binary64_mass_rate_and_exact_sequential_ledger_are_not_decimal_recomputed() -> None:
    spec = _spec()
    plan = bridge.decode(spec, _values())
    rate = spec.thrust_n / (9.80665 * spec.isp_s)
    expected = (
        Fraction(spec.initial_mass_kg),
        Fraction(spec.initial_mass_kg) - Fraction(rate) * Fraction(_values()[2]),
        Fraction(spec.initial_mass_kg) - Fraction(rate) * Fraction(_values()[2]),
        Fraction(spec.initial_mass_kg) - Fraction(rate) * (Fraction(_values()[2]) + Fraction(_values()[5])),
    )
    assert plan.mass_rate_kg_s.hex() == rate.hex()
    assert plan.exact_masses == expected
    assert plan.masses == tuple(float(mass) for mass in expected)
    assert plan.mass_conversion_errors == tuple(
        Fraction(actual) - exact for actual, exact in zip(plan.masses, expected, strict=True)
    )
    decimal_rate = Fraction(Decimal("1000")) / (Fraction(Decimal("9.80665")) * 450)
    wrong = (
        Fraction(2000), Fraction(2000) - decimal_rate * Fraction(_values()[2]),
        Fraction(2000) - decimal_rate * Fraction(_values()[2]),
        Fraction(2000) - decimal_rate * (Fraction(_values()[2]) + Fraction(_values()[5])),
    )
    assert wrong != expected
    with pytest.raises(bridge.BridgeError):
        replace(plan, exact_masses=wrong)


def test_exact_dry_mass_equality_admitted_but_sub_ulp_shortfall_rejected() -> None:
    spec = _spec(thrust_n=9.80665, isp_s=1.0)
    values = (0.0, 0.0, 1499.0, 0.0, 0.0, 1.0) + (0.0,) * 12
    plan = bridge.decode(spec, values)
    assert plan.mass_rate_kg_s == 1.0
    assert plan.exact_masses[-1] == Fraction(500)
    short_values = values[:5] + (math.nextafter(1.0, math.inf),) + values[6:]
    short_mass = Fraction(2000) - (Fraction(1499) + Fraction(short_values[5]))
    assert short_mass < Fraction(500) and float(short_mass) == 500.0
    with pytest.raises(bridge.BridgeError):
        bridge.decode(spec, short_values)


@pytest.mark.parametrize("index", range(18))
def test_each_declared_physical_forward_increment_survives(index: int) -> None:
    spec = _spec(shifted=True)
    original = _values()
    perturbed = bridge.perturb(spec, original, index)
    assert len(perturbed) == 18
    assert all(a == b for i, (a, b) in enumerate(zip(original, perturbed, strict=True)) if i != index)
    before = bridge.decode(spec, original)
    after = bridge.decode(spec, perturbed)
    if index < 6:
        step = 1.0 if index in (2, 5) else 1e-5
        assert after.controls[index] != before.controls[index]
        assert after.controls[index] - before.controls[index] == pytest.approx(step, abs=1e-12)
    else:
        node, component = divmod(index - 6, 6)
        step = 1.0 if component < 3 else 1e-4
        assert after.nodes[node][component] != before.nodes[node][component]
        assert after.nodes[node][component] - before.nodes[node][component] == pytest.approx(step, abs=1e-6)


def test_collapsed_forward_increment_fails_without_step_enlargement() -> None:
    anchor = (float(2 ** 60),) + _spec().anchors[0][1:]
    spec = _spec(anchors=(anchor, _spec().anchors[1]))
    with pytest.raises(bridge.BridgeError):
        bridge.perturb(spec, _values(), 6)


@pytest.mark.parametrize("index", [True, -1, 18, 0.5])
def test_invalid_perturbation_index_is_rejected(index: object) -> None:
    with pytest.raises(bridge.BridgeError):
        bridge.perturb(_spec(), _values(), index)


@pytest.mark.parametrize("index", range(18))
@pytest.mark.parametrize("value", [True, math.nan], ids=["boolean", "nan"])
def test_every_input_field_rejects_boolean_or_nonfinite(index: int, value: object) -> None:
    values = list(_values())
    values[index] = value
    with pytest.raises(bridge.BridgeError):
        bridge.decode(_spec(), tuple(values))


@pytest.mark.parametrize("values", [_values()[:-1], _values() + (0.0,), ()])
def test_wrong_unknown_vector_size_is_rejected(values: tuple[float, ...]) -> None:
    with pytest.raises(bridge.BridgeError):
        bridge.decode(_spec(), values)


@pytest.mark.parametrize("index,value", [(1, math.pi), (4, -math.pi), (2, 0.0), (5, -1.0), (2, 9000.0)])
def test_control_domain_is_checked_before_factory_work(index: int, value: float) -> None:
    spec = _spec()
    values = list(_values())
    values[index] = value
    factory = _AffineFactory(spec)
    budget = _budget()
    with pytest.raises(bridge.BridgeError):
        _evaluate(spec, tuple(values), factory=factory, budget=budget)
    assert budget.snapshot()["control_attempts"] == 1
    assert budget.snapshot()["propagation_evaluations"] == 0
    assert budget.snapshot()["simulated_arc_slots"] == 0
    assert factory.requests == []


@pytest.mark.parametrize("controls", [
    _values()[:6], (math.pi, 0.0, 1000.0, 2 * math.pi, 0.0, 1200.0),
    (0.0, math.pi, 1000.0, 0.0, 0.0, 1200.0),
    (0.0, 0.0, 0.0, 0.0, 0.0, 1200.0),
    (0.0, 0.0, 9000.0, 0.0, 0.0, 1200.0),
    (0.0, 0.0, 4000.0, 0.0, 0.0, 4000.0),
])
def test_existing_pure_control_guard_parity_where_float_events_agree(
    controls: tuple[float, ...],
) -> None:
    spec = _spec()
    spacecraft = SpacecraftSpec(
        spec.initial_mass_kg, spec.dry_mass_kg, spec.thrust_n, spec.isp_s,
        20.0, 1.3, 0.01, 0.001,
    )
    expected = _prepare_burn_controls("fabricated-bridge", spacecraft, spec.t0_s, spec.tf_s, controls)
    if isinstance(expected, str):
        with pytest.raises(bridge.BridgeError):
            bridge.decode(spec, controls + (0.0,) * 12)
    else:
        assert bridge.decode(spec, controls + (0.0,) * 12).controls == expected


def test_azimuth_canonicalization_preserves_equivalent_control() -> None:
    values = list(_values())
    values[0] = math.pi
    values[3] = 2 * math.pi
    plan = bridge.decode(_spec(), tuple(values))
    assert plan.controls[0] == -math.pi
    assert plan.controls[3] == 0.0


@pytest.mark.parametrize("field_name,value", [
    ("artificial", False), ("t0_s", True), ("tf_s", math.inf),
    ("initial_mass_kg", math.nan), ("dry_mass_kg", -1.0),
    ("thrust_n", 0.0), ("isp_s", True), ("anchors", ((0.0,) * 5, (0.0,) * 6)),
])
def test_invalid_problem_boundary_or_hardware_is_rejected(field_name: str, value: object) -> None:
    with pytest.raises(bridge.BridgeError):
        _spec(**{field_name: value})


def test_shooting_arcs_and_raw_defects_follow_independent_reference() -> None:
    spec = _spec()
    result, flow, budget = _evaluate(spec)
    assert result.mode == "shooting"
    assert len(flow.requests) == 3 and flow.opened == flow.closed == 1
    assert tuple(request.arc for request in flow.requests) == ("departure-burn", "coast", "arrival-burn")
    assert tuple(request.burn_id for request in flow.requests) == ("departure", None, "arrival")
    assert tuple(request.mode for request in flow.requests) == ("burn", "coast", "burn")
    assert tuple(request.guidance_reference_body for request in flow.requests) == ("Moon", None, "Mars")
    assert tuple(request.guidance_frame for request in flow.requests) == ("TNW", None, "TNW")
    for request in flow.requests:
        with pytest.raises((AttributeError, TypeError)):
            request.guidance_reference_body = "Earth"
        with pytest.raises((AttributeError, TypeError)):
            request.guidance_frame = "J2000"
    assert all(request.frame == "SSB/J2000" and request.time_scale == "TDB seconds since J2000" for request in flow.requests)
    assert all(request.artificial is True for request in flow.requests)
    assert tuple(request.start_state for request in flow.requests) == (spec.initial_state,) + spec.anchors
    assert tuple(request.start_mass_kg for request in flow.requests) == result.plan.masses[:3]
    assert tuple(request.start_event.exact_s for request in flow.requests) == tuple(e.exact_s for e in result.plan.events[:3])
    assert tuple(request.end_event.exact_s for request in flow.requests) == tuple(e.exact_s for e in result.plan.events[1:])
    references = spec.anchors + (spec.target_state,)
    expected = tuple(actual - target for response, target in zip(flow.responses, references, strict=True) for actual, target in zip(response.state, target, strict=True))
    assert result.raw_defects == expected
    assert result.scaled_defects == tuple(value / (1000.0 if i % 6 < 3 else 0.01) for i, value in enumerate(expected))
    counts = budget.snapshot()
    assert counts["control_attempts"] == counts["propagation_evaluations"] == 1
    assert counts["simulated_arc_slots"] == 3
    assert all(counts[name] == 0 for name in ("native_propagations", "spice_queries", "kernel_reads", "real_archive_reads", "integrations", "optimizer_calls"))
    with pytest.raises(TypeError):
        result.counts["native_propagations"] = 1


def test_large_affine_coordinate_and_epoch_shift_preserves_defects_and_replay() -> None:
    values = _values()[:6] + (0.25, -0.5, 0.75, 0.5, -0.25, 0.125) * 2
    plain, _, _ = _evaluate(_spec(), values)
    shifted, _, _ = _evaluate(_spec(shifted=True), values)
    for arc in range(3):
        start = arc * 6
        assert math.dist(plain.raw_defects[start:start + 3], shifted.raw_defects[start:start + 3]) <= 0.001
        assert math.dist(plain.raw_defects[start + 3:start + 6], shifted.raw_defects[start + 3:start + 6]) <= 1e-6
    plain_replay, _, _ = _evaluate(_spec(), values, mode="replay")
    shifted_replay, _, _ = _evaluate(_spec(shifted=True), values, mode="replay")
    for actual, reference in zip(shifted_replay.ends, plain_replay.ends, strict=True):
        elapsed = reference.event.exact_s
        expected = _translate(reference.state, elapsed)
        assert math.dist(actual.state[:3], expected[:3]) <= 0.001
        assert math.dist(actual.state[3:], expected[3:]) <= 1e-6
        assert actual.mass_kg == reference.mass_kg
        assert actual.event.exact_s - reference.event.exact_s == Fraction(1000000000)


def test_replay_does_not_inject_nodes_or_replace_actual_mass_by_ledger() -> None:
    spec = _spec()
    def change_mass(request: bridge.ArcRequest, response: bridge.ArcResponse) -> bridge.ArcResponse:
        return replace(response, mass_kg=response.mass_kg + math.ulp(response.mass_kg)) if request.arc == "departure-burn" else response
    flow = _AffineFactory(spec, change_mass)
    result, _, _ = _evaluate(spec, mode="replay", factory=flow)
    assert len(flow.requests) == 3
    assert flow.requests[1].start_state == flow.responses[0].state
    assert flow.requests[2].start_state == flow.responses[1].state
    assert flow.requests[1].start_mass_kg.hex() == flow.responses[0].mass_kg.hex()
    assert flow.requests[1].start_mass_kg != result.plan.masses[1]
    assert flow.requests[2].start_mass_kg.hex() == flow.responses[1].mass_kg.hex()
    changed = _values()[:6] + (13.0, -7.0, 9.0, 2.0, -3.0, 4.0) * 2
    first, _, _ = _evaluate(spec, mode="replay")
    second, _, _ = _evaluate(spec, changed, mode="replay")
    assert tuple(response.state for response in first.ends) == tuple(response.state for response in second.ends)
    assert tuple(response.mass_kg for response in first.ends) == tuple(response.mass_kg for response in second.ends)
    assert first.plan.nodes != second.plan.nodes


def test_context_is_fresh_for_each_evaluation() -> None:
    spec = _spec()
    flow = _AffineFactory(spec)
    budget = _budget()
    _evaluate(spec, factory=flow, budget=budget)
    _evaluate(spec, factory=flow, budget=budget)
    assert flow.opened == flow.closed == 2 and len(flow.requests) == 6


@pytest.mark.parametrize("failure", ["unsafe", "incomplete", "mass", "missing-event", "nonfinite", "rounded-event", "late-label"])
def test_first_bad_arc_discards_context_without_retry_or_later_work(failure: str) -> None:
    spec = _spec(shifted=True)
    values = list(_values())
    values[2] = math.nextafter(values[2], math.inf)
    def corrupt(request: bridge.ArcRequest, response: bridge.ArcResponse) -> bridge.ArcResponse:
        if failure == "unsafe":
            return replace(response, safe=False)
        if failure == "incomplete":
            return replace(response, complete=False)
        if failure == "mass":
            return replace(response, mass_kg=response.mass_kg - 1e-6)
        if failure == "missing-event":
            return replace(response, event=None)
        if failure == "nonfinite":
            return replace(response, state=(math.nan,) + response.state[1:])
        if failure == "late-label":
            label = response.event.label_s + 1e-4
            event = bridge.ExactEvent(response.event.exact_s, label, Fraction(label) - response.event.exact_s)
            return replace(response, event=event)
        reduced = Fraction(request.end_event.label_s)
        assert reduced != request.end_event.exact_s
        assert abs(reduced - request.end_event.exact_s) < Fraction(1, 1000000)
        return replace(response, event=_event(reduced))
    flow = _AffineFactory(spec, corrupt)
    budget = _budget()
    with pytest.raises(bridge.BridgeError):
        _evaluate(spec, tuple(values), factory=flow, budget=budget)
    assert flow.opened == flow.closed == 1 and len(flow.requests) == 1
    assert budget.snapshot()["simulated_arc_slots"] == 1
    with pytest.raises(bridge.BridgeError):
        _evaluate(spec, factory=flow, budget=budget)
    assert len(flow.requests) == 1


def test_injected_exception_closes_context_and_counts_failed_slot() -> None:
    spec = _spec()
    def fail(request: bridge.ArcRequest, response: bridge.ArcResponse) -> bridge.ArcResponse:
        raise bridge.BridgeError("injected first failure")
    flow = _AffineFactory(spec, fail)
    budget = _budget()
    with pytest.raises(bridge.BridgeError, match="injected first failure"):
        _evaluate(spec, factory=flow, budget=budget)
    assert len(flow.requests) == 1 and flow.closed == 1
    assert budget.snapshot()["simulated_arc_slots"] == 1


@pytest.mark.parametrize("field_name,limit", [("control_attempts", 73), ("propagation_evaluations", 76), ("simulated_arc_slots", 228)])
def test_capacity_refuses_next_work_before_arc_callable(field_name: str, limit: int) -> None:
    spec = _spec()
    budget = _budget()
    setattr(budget, field_name, limit)
    flow = _AffineFactory(spec)
    with pytest.raises(bridge.BridgeError):
        _evaluate(spec, factory=flow, budget=budget)
    assert flow.requests == []
    assert budget.snapshot()[field_name] == limit


def test_final_slot_counts_even_when_next_arc_is_refused() -> None:
    spec = _spec()
    budget = _budget()
    budget.simulated_arc_slots = 227
    flow = _AffineFactory(spec)
    with pytest.raises(bridge.BridgeError):
        _evaluate(spec, factory=flow, budget=budget)
    assert budget.snapshot()["simulated_arc_slots"] == 228
    assert len(flow.requests) == 1 and flow.closed == 1


def test_diagnostic_is_explicit_replay_of_the_last_completed_controls() -> None:
    spec = _spec()
    budget = _budget()
    flow = _AffineFactory(spec)
    _evaluate(spec, factory=flow, budget=budget)
    result, _, _ = _evaluate(spec, mode="replay", factory=flow, budget=budget, diagnostic=True)
    assert result.mode == "replay"
    assert budget.snapshot()["control_attempts"] == 1
    assert budget.snapshot()["diagnostic_attempts"] == 1
    assert len(flow.requests) == 6
    changed = list(_values())
    changed[0] += 1e-5
    with pytest.raises(bridge.BridgeError):
        _evaluate(spec, tuple(changed), mode="replay", factory=flow, budget=budget, diagnostic=True)
    assert len(flow.requests) == 6


@pytest.mark.parametrize("mode,diagnostic", [("shooting", True), ("unknown", False)])
def test_unknown_or_implicit_diagnostic_modes_fail_before_flow(mode: str, diagnostic: bool) -> None:
    spec = _spec()
    flow = _AffineFactory(spec)
    with pytest.raises(bridge.BridgeError):
        _evaluate(spec, mode=mode, factory=flow, diagnostic=diagnostic)
    assert flow.requests == []


def test_parent_start_is_not_reset_by_late_budget_construction() -> None:
    clock = _Clock(9.0)
    budget = _budget(clock)
    clock.now_s = 9.999
    budget.check_producer()
    clock.now_s = 10.0
    with pytest.raises(bridge.BridgeError):
        budget.check_producer()
    clock.now_s = 14.999
    budget.check_finalization()
    clock.now_s = 15.0
    with pytest.raises(bridge.BridgeError):
        budget.check_finalization()


def test_backwards_clock_cannot_extend_work() -> None:
    clock = _Clock()
    budget = _budget(clock)
    budget.check_producer()
    clock.now_s = -0.001
    with pytest.raises(bridge.BridgeError):
        budget.check_producer()


def test_byte_caps_measure_utf8_bytes_and_reserve_finalization_time() -> None:
    clock = _Clock()
    budget = _budget(clock)
    exact_input = "я".encode() * (65536 // 2)
    budget.check_input_bytes(exact_input)
    assert budget.snapshot()["input_bytes"] == 65536
    with pytest.raises(bridge.BridgeError):
        _budget().check_input_bytes(exact_input + b"x")
    clock.now_s = 14.0
    exact_output = b"x" * 131072
    budget.check_output_bytes(exact_output)
    assert budget.snapshot()["output_bytes"] == 131072
    with pytest.raises(bridge.BridgeError):
        _budget().check_output_bytes(exact_output + b"x")


@pytest.mark.parametrize("exact,label,error", [
    (1.0, 1.0, Fraction(0)), (Fraction(1), math.nan, Fraction(0)),
    (Fraction(1), 1.0, 0.0), (Fraction(1), 1.0, Fraction(1, 1000)),
])
def test_event_packet_requires_exact_identity_and_coherent_signed_error(
    exact: object, label: object, error: object,
) -> None:
    with pytest.raises(bridge.BridgeError):
        bridge.ExactEvent(exact, label, error)


@pytest.mark.parametrize("field_name,value", [
    ("burn_id", "arrival"), ("mode", "coast"), ("angles_rad", None),
    ("frame", "EME2000"), ("time_scale", "UTC"), ("artificial", False),
])
def test_request_refuses_changed_burn_mode_or_coordinate_contract(
    field_name: str, value: object,
) -> None:
    result, _, _ = _evaluate()
    with pytest.raises(bridge.BridgeError):
        replace(result.starts[0], **{field_name: value})
    with pytest.raises(bridge.BridgeError):
        replace(result.starts[0], start_event=result.starts[0].end_event)
    with pytest.raises(bridge.BridgeError):
        replace(result.starts[1], angles_rad=(0.0, 0.0))


@pytest.mark.parametrize("field_name,value", [
    ("mass_kg", True), ("complete", 1), ("safe", 1),
])
def test_response_numeric_and_boolean_fields_remain_distinct(
    field_name: str, value: object,
) -> None:
    result, _, _ = _evaluate()
    with pytest.raises(bridge.BridgeError):
        replace(result.ends[0], **{field_name: value})


def test_reused_context_is_refused_before_another_arc_call() -> None:
    spec = _spec()
    flow = _AffineFactory(spec)
    context = flow()
    budget = _budget()
    bridge.evaluate(spec, _values(), mode="shooting", arc_factory=lambda: context, budget=budget)
    with pytest.raises(bridge.BridgeError, match="fresh mutable context"):
        bridge.evaluate(spec, _values(), mode="shooting", arc_factory=lambda: context, budget=budget)
    assert len(flow.requests) == 3 and flow.opened == flow.closed == 1
    assert budget.snapshot()["simulated_arc_slots"] == 3


def test_fresh_context_cannot_reuse_the_same_yielded_mutable_flow() -> None:
    spec = _spec()
    spy = _AffineFactory(spec)
    saved_flow = spy.run
    lifecycle: list[str] = []
    @contextmanager
    def fresh_context() -> Iterator[Callable[[bridge.ArcRequest], bridge.ArcResponse]]:
        lifecycle.append("open")
        try:
            yield saved_flow
        finally:
            lifecycle.append("close")
    budget = _budget()
    bridge.evaluate(spec, _values(), mode="shooting", arc_factory=fresh_context, budget=budget)
    with pytest.raises(bridge.BridgeError, match="fresh yielded arc callable"):
        bridge.evaluate(spec, _values(), mode="shooting", arc_factory=fresh_context, budget=budget)
    assert len(spy.requests) == 3
    assert lifecycle == ["open", "close", "open", "close"]
    assert budget.snapshot()["simulated_arc_slots"] == 3


def test_frozen_diagnostic_accepts_an_independent_identical_word_spec_copy() -> None:
    spec = _spec()
    budget = _budget()
    flow = _AffineFactory(spec)
    _evaluate(spec, factory=flow, budget=budget)
    copied = replace(spec)
    assert copied is not spec
    result, _, _ = _evaluate(copied, mode="replay", factory=flow, budget=budget, diagnostic=True)
    assert result.mode == "replay" and len(flow.requests) == 6


@pytest.mark.parametrize("field_name", [
    "initial_state", "target_state", "anchors", "thrust_n", "isp_s",
    "initial_mass_kg", "dry_mass_kg", "t0_s", "tf_s",
])
def test_frozen_diagnostic_refuses_any_fixed_input_word_drift(field_name: str) -> None:
    spec = _spec()
    budget = _budget()
    flow = _AffineFactory(spec)
    _evaluate(spec, factory=flow, budget=budget)
    if field_name in ("initial_state", "target_state"):
        original = getattr(spec, field_name)
        changed = (math.nextafter(original[0], math.inf),) + original[1:]
    elif field_name == "anchors":
        first = spec.anchors[0]
        changed = ((math.nextafter(first[0], math.inf),) + first[1:], spec.anchors[1])
    elif field_name == "t0_s":
        changed = -0.0
        assert changed == spec.t0_s and changed.hex() != spec.t0_s.hex()
    else:
        changed = math.nextafter(getattr(spec, field_name), math.inf)
    altered = replace(spec, **{field_name: changed})
    with pytest.raises(bridge.BridgeError, match="frozen spec words"):
        _evaluate(altered, mode="replay", factory=flow, budget=budget, diagnostic=True)
    assert len(flow.requests) == 3
    assert budget.snapshot()["simulated_arc_slots"] == 3


def test_frozen_diagnostic_preserves_the_signed_zero_control_word() -> None:
    spec = _spec()
    values = (0.0,) + _values()[1:]
    flow = _AffineFactory(spec)
    budget = _budget()
    _evaluate(spec, values, factory=flow, budget=budget)
    with pytest.raises(bridge.BridgeError):
        _evaluate(spec, (-0.0,) + values[1:], mode="replay", factory=flow, budget=budget, diagnostic=True)
    assert len(flow.requests) == 3


@pytest.mark.parametrize("invalid", [math.nan, math.inf, True])
def test_invalid_clock_word_poisoning_prevents_a_later_valid_retry(invalid: object) -> None:
    clock = _Clock()
    budget = _budget(clock)
    clock.now_s = invalid
    with pytest.raises(bridge.BridgeError):
        budget.check_producer()
    clock.now_s = 1.0
    with pytest.raises(bridge.BridgeError, match="earlier failure"):
        budget.check_producer()
    budget.check_finalization()
    assert budget.snapshot()["control_attempts"] == 0


@pytest.mark.parametrize("exception_type", [RuntimeError, ValueError])
def test_clock_callback_failure_poisoning_prevents_retry(exception_type: type[Exception]) -> None:
    fail = False
    def clock() -> float:
        if fail:
            raise exception_type("injected clock failure")
        return 1.0
    budget = bridge.Budget(started_s=0.0, monotonic=clock)
    fail = True
    with pytest.raises(bridge.BridgeError):
        budget.check_producer()
    fail = False
    with pytest.raises(bridge.BridgeError, match="earlier failure"):
        budget.check_producer()
    budget.check_finalization()


def test_slot_lifecycle_refuses_missing_first_or_fourth_arc() -> None:
    empty = _budget()
    with pytest.raises(bridge.BridgeError):
        empty.begin_arc(first_in_evaluation=False)
    assert empty.snapshot()["simulated_arc_slots"] == 0
    budget = _budget()
    budget.begin_arc(first_in_evaluation=True)
    budget.begin_arc(first_in_evaluation=False)
    budget.begin_arc(first_in_evaluation=False)
    with pytest.raises(bridge.BridgeError):
        budget.begin_arc(first_in_evaluation=False)
    assert budget.snapshot()["propagation_evaluations"] == 1
    assert budget.snapshot()["simulated_arc_slots"] == 3


def test_fourth_frozen_diagnostic_is_refused_before_counting() -> None:
    budget = _budget()
    for _ in range(3):
        budget.begin_diagnostic()
    with pytest.raises(bridge.BridgeError):
        budget.begin_diagnostic()
    assert budget.snapshot()["diagnostic_attempts"] == 3


def test_byte_limits_are_cumulative_across_separate_chunks() -> None:
    budget = _budget()
    budget.check_input_bytes(b"x" * 32768)
    budget.check_input_bytes(b"x" * 32768)
    with pytest.raises(bridge.BridgeError):
        budget.check_input_bytes(b"x")
    assert budget.snapshot()["input_bytes"] == 65536
    budget.check_output_bytes(b"x" * 65536)
    budget.check_output_bytes(b"x" * 65536)
    with pytest.raises(bridge.BridgeError):
        budget.check_output_bytes(b"x")
    assert budget.snapshot()["output_bytes"] == 131072
