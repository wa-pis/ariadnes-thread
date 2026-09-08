"""Qualify native sampling behavior; this is not a production collision guard."""

from __future__ import annotations

from typing import Literal

import numpy as np
from numpy.typing import NDArray
import pytest

from space_nav import trajectory


@pytest.mark.parametrize("latch_stages", [False, True])
@pytest.mark.parametrize(
    ("arc", "entry_s", "exit_s", "final_s"),
    [("departure-burn", 0.25, 0.75, 2.0), ("coast", 3.0, 20.0, 600.0)],
)
def test_native_full_step_guard_can_miss_an_internal_crossing(
    latch_stages: bool,
    arc: Literal["departure-burn", "coast"],
    entry_s: float, exit_s: float, final_s: float,
) -> None:
    from tudatpy.dynamics import environment_setup, propagation_setup

    resource = trajectory._build_collision_resource("safety-sampling-control")
    radius_m = next(s.guard_radius_m for s in resource.surfaces if s.body == "Moon")
    # Test-only straight line through a stationary Moon sphere in entry_s..exit_s.
    # Other bodies are deliberately far away; no mission ephemeris is replaced.
    positions: dict[str, object] = {
        body: (1e12, 0.0, 0.0) for body in trajectory.PHYSICAL_BODY_NAMES
    }
    positions["Moon"] = (0.0, 0.0, 0.0)
    settings = environment_setup.BodyListSettings("SSB", "J2000")
    settings.add_empty_settings("Spacecraft")
    settings.get("Spacecraft").constant_mass = 2000.0
    bodies = environment_setup.create_system_of_bodies(settings)
    speed_m_s = 2.0 * radius_m / (exit_s - entry_s)
    initial_x_m = -radius_m - speed_m_s * entry_s
    initial = np.asarray([initial_x_m, 0.0, 0.0, speed_m_s, 0.0, 0.0])
    sampled_epochs_s: list[float] = []
    stage_impacts: list[float] = []
    rejection: str | None = None

    def current_rejection() -> str | None:
        return trajectory._classify_trial_state(
            "safety-sampling-control", bodies.get("Spacecraft").state,
            2000.0, 1000.0, positions, resource,
        )

    def acceleration(epoch_tdb_s: float) -> NDArray[np.float64]:
        nonlocal rejection
        sampled_epochs_s.append(float(epoch_tdb_s))
        reason = current_rejection()
        if reason is not None:
            stage_impacts.append(float(epoch_tdb_s))
            if latch_stages:
                rejection = reason
        return np.zeros(3)

    def stop(epoch_tdb_s: float) -> bool:
        return rejection is not None if latch_stages else current_rejection() is not None

    models = propagation_setup.create_acceleration_models(
        bodies, {"Spacecraft": {"Spacecraft": [
            propagation_setup.acceleration.custom(acceleration),
        ]}}, ["Spacecraft"], ["SSB"],
    )
    integrator = trajectory._build_arc_integrator(
        "safety-sampling-control", arc,
    )
    termination = propagation_setup.propagator.hybrid_termination([
        propagation_setup.propagator.custom_termination(stop),
        propagation_setup.propagator.time_termination(
            final_s, terminate_exactly_on_final_condition=True,
        ),
    ], fulfill_single_condition=True)
    coupled = trajectory._build_coupled_arc_settings(
        "safety-sampling-control", bodies, models, initial, 2000.0, 0.0,
        integrator, termination, thrust_enabled=False,
    )
    budget = trajectory._RefinementBudget("safety-sampling-control", 300.0)
    simulator = trajectory._run_native_arc(
        budget, bodies, coupled, first_in_evaluation=True,
    )
    assert budget.propagation_evaluations == budget.native_arc_propagations == 1
    assert simulator.integration_completed_successfully is True
    history = simulator.state_history
    assert sampled_epochs_s
    if arc == "coast":
        # This entire crossing lies between stages of the unchanged 300 s step.
        assert stage_impacts == []
        assert not any(entry_s <= epoch <= exit_s for epoch in sampled_epochs_s)
    else:
        assert stage_impacts
    assert all(entry_s - 1e-12 <= epoch <= exit_s + 1e-12 for epoch in stage_impacts)
    assert abs(initial_x_m + speed_m_s * ((entry_s + exit_s) / 2.0)) <= 1e-6
    # The zero-force analytic solution makes the crossing unambiguous.
    for epoch, raw in history.items():
        state = np.asarray(raw).reshape(7)
        assert abs(state[0] - (initial_x_m + speed_m_s * epoch)) <= 1e-6
        assert np.linalg.norm(state[:3]) > radius_m
    if latch_stages and arc == "departure-burn":
        assert rejection == "rejected-impact:Moon"
        assert max(history) < final_s
        # The outcome gate must not mistake the known early stop for epoch failure.
        assert trajectory._read_trial_arc_outcome(
            "safety-sampling-control", arc, simulator, final_s, rejection,
        ) == "rejected-impact:Moon"
    else:
        assert rejection is None
        assert abs(max(history) - final_s) <= 1e-6
    # Stage latching alone is NOT a continuous safety proof: crossings can lie
    # between stages, and rejected adaptive trials may contain unsafe stages.
