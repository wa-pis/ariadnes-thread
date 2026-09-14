"""Analytic qualification only: no full-force acceleration bound is assumed."""

from __future__ import annotations

import json
import time

import numpy as np
from numpy.typing import NDArray
import pytest

from space_nav import trajectory


@pytest.mark.parametrize(("case", "stop"), [
    ("straight-impact", None), ("straight-clear", None), ("curved-impact", None),
    ("curved-clear", None), ("tangent", None), ("tangent", "calls"),
    ("tangent", "deadline"),
])
def test_bounded_subdivision_with_known_relative_acceleration(
    case: str, stop: str | None,
) -> None:
    from tudatpy.dynamics import environment_setup, propagation_setup

    started_s = time.monotonic()
    clock_s = [0.0]
    budget = trajectory._RefinementBudget(
        "adaptive-control", 300.0,
        monotonic=(lambda: clock_s[0]) if stop == "deadline" else time.monotonic,
        max_arcs_per_evaluation=2 if stop == "calls" else 32,
    )
    budget.begin_control()
    resource = trajectory._build_collision_resource("adaptive-control")
    radius_m = next(s.guard_radius_m for s in resource.surfaces if s.body == "Moon")
    duration_s = 300.0
    error_m = 0.001  # Verified below against every analytic endpoint; test-only.
    acceleration_m_s2 = np.zeros(3)
    initial = np.asarray([-2350600.0, 0.0, 0.0, 204400.0, 0.0, 0.0])
    if case == "straight-clear":
        initial[1] = radius_m + 1000.0
    elif case == "tangent":
        initial[1] = radius_m
    elif case.startswith("curved"):
        initial = np.asarray([0.0, (4.0 if case == "curved-clear" else 2.0) * radius_m,
                              0.0, 0.0, -8.0 * radius_m / duration_s, 0.0])
        acceleration_m_s2[1] = 16.0 * radius_m / duration_s**2
    acceleration_bound_m_s2 = float(np.linalg.norm(acceleration_m_s2))
    max_position_error_m = 0.0
    original_initial = initial.copy()
    native_inputs: list[tuple[float, float, NDArray[np.float64]]] = []
    child_handoff_checks = 0
    discarded_parent_checks = 0

    def analytic(epoch_s: float) -> NDArray[np.float64]:
        return np.concatenate((
            initial[:3] + initial[3:] * epoch_s + acceleration_m_s2 * epoch_s**2 / 2.0,
            initial[3:] + acceleration_m_s2 * epoch_s,
        ))

    def advance(start_s: float, end_s: float, state: NDArray[np.float64]) -> NDArray[np.float64]:
        nonlocal max_position_error_m
        original_state = state.copy()
        budget.check()
        settings = environment_setup.BodyListSettings("SSB", "J2000")
        settings.add_empty_settings("Spacecraft")
        settings.get("Spacecraft").constant_mass = 2000.0
        bodies = environment_setup.create_system_of_bodies(settings)

        def acceleration(epoch_tdb_s: float) -> NDArray[np.float64]:
            return acceleration_m_s2

        models = propagation_setup.create_acceleration_models(
            bodies, {"Spacecraft": {"Spacecraft": [
                propagation_setup.acceleration.custom(acceleration),
            ]}}, ["Spacecraft"], ["SSB"],
        )
        coupled = trajectory._build_coupled_arc_settings(
            "adaptive-control", bodies, models, state, 2000.0, start_s,
            trajectory._build_arc_integrator("adaptive-control", "coast"),
            propagation_setup.propagator.time_termination(
                end_s, terminate_exactly_on_final_condition=True,
            ), thrust_enabled=False,
        )
        simulator = trajectory._run_native_arc(
            budget, bodies, coupled, first_in_evaluation=budget.native_arc_propagations == 0,
        )
        assert simulator.integration_completed_successfully is True
        assert np.array_equal(state, original_state)
        native_inputs.append((start_s, end_s, original_state))
        # Experimental trial only: inspect endpoint, then discard the simulator.
        # Do not use the production safe-result reader before interval screening.
        history = simulator.state_history
        assert abs(max(history) - end_s) <= 1e-6
        for epoch, raw in history.items():
            sample = np.asarray(raw).reshape(7)
            delta_m = float(np.linalg.norm(sample[:3] - analytic(epoch)[:3]))
            max_position_error_m = max(max_position_error_m, delta_m)
            assert delta_m <= error_m
            assert np.linalg.norm(sample[3:6] - analytic(epoch)[3:]) <= 1e-6
            assert sample[6] == 2000.0
        if stop == "deadline" and budget.native_arc_propagations == 2:
            clock_s[0] = 300.0
        budget.check()
        return np.asarray(history[max(history)]).reshape(7)[:6].copy()

    def screen(
        start_s: float, end_s: float, start: NDArray[np.float64], depth: int,
    ) -> tuple[str, NDArray[np.float64] | None]:
        nonlocal child_handoff_checks, discarded_parent_checks
        original_start = start.copy()
        end = advance(start_s, end_s, start)
        assert np.array_equal(start, original_start)
        # Inside by more than the verified endpoint error is a definite impact.
        if min(np.linalg.norm(start[:3]), np.linalg.norm(end[:3])) + error_m < radius_m:
            return "impact", None
        chord = end[:3] - start[:3]
        norm_squared = float(chord @ chord)
        fraction = 0.0 if norm_squared == 0.0 else float(np.clip(
            -(start[:3] @ chord) / norm_squared, 0.0, 1.0,
        ))
        closest_m = float(np.linalg.norm(start[:3] + fraction * chord))
        deviation_m = acceleration_bound_m_s2 * (end_s - start_s)**2 / 8.0 + error_m
        if closest_m - deviation_m > radius_m:
            return "clear", end
        if depth == 6:
            return "unresolved", None
        midpoint_s = (start_s + end_s) / 2.0
        assert start_s < midpoint_s < end_s
        discarded_parent_checks += 1
        left_status, midpoint = screen(start_s, midpoint_s, start, depth + 1)
        assert np.array_equal(start, original_start)
        if left_status != "clear":
            assert midpoint is None
            return left_status, None
        assert midpoint is not None
        accepted_midpoint = midpoint.copy()
        right_input_index = len(native_inputs)
        # The discarded parent and both refined children count as native work.
        right_result = screen(midpoint_s, end_s, midpoint, depth + 1)
        right_start_s, right_end_s, right_start_state = native_inputs[right_input_index]
        assert (right_start_s, right_end_s) == (midpoint_s, end_s)
        assert np.array_equal(right_start_state, accepted_midpoint)
        assert np.array_equal(midpoint, accepted_midpoint)
        assert right_result[1] is not end  # Never return the discarded parent endpoint.
        assert (right_result[1] is not None) == (right_result[0] == "clear")
        child_handoff_checks += 1
        return right_result

    if stop is not None:
        terminal = None
        with pytest.raises(trajectory.TrajectoryRefinementError,
                           match="limit 2" if stop == "calls" else "shared deadline"):
            _, terminal = screen(0.0, duration_s, initial, 0)
        assert terminal is None
        assert budget.native_arc_propagations == 2
        assert len(native_inputs) == budget.native_arc_propagations
        assert np.array_equal(initial, original_initial)
        assert budget.control_attempts == budget.propagation_evaluations == 1
        return
    status, terminal = screen(0.0, duration_s, initial, 0)
    expected = "impact" if case.endswith("impact") else "unresolved" if case == "tangent" else "clear"
    assert status == expected
    assert (terminal is not None) == (expected == "clear")
    assert budget.control_attempts == budget.propagation_evaluations == 1
    assert 1 <= budget.native_arc_propagations <= 32
    assert len(native_inputs) == budget.native_arc_propagations
    assert np.array_equal(initial, original_initial)
    assert (native_inputs[0][0], native_inputs[0][1]) == (0.0, duration_s)
    assert np.array_equal(native_inputs[0][2], original_initial)
    if case == "tangent":
        assert child_handoff_checks > 0 and discarded_parent_checks > 0
    if expected != "clear":
        assert budget.native_arc_propagations > 1
    budget.check()
    print(json.dumps({
        "case": case, "status": status, "native_calls": budget.native_arc_propagations,
        "elapsed_s": time.monotonic() - started_s,
        "max_position_error_m": max_position_error_m,
        "recorded_native_inputs": len(native_inputs),
        "child_handoff_checks": child_handoff_checks,
        "discarded_parent_checks": discarded_parent_checks,
        "scope": "analytic control only; no mission safety certificate",
    }, sort_keys=True))
