"""Qualify native sampling behavior; this is not a production collision guard."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
import pytest

from space_nav import trajectory


@pytest.mark.parametrize("latch_stages", [False, True])
def test_native_full_step_guard_can_miss_an_internal_crossing(
    latch_stages: bool,
) -> None:
    from tudatpy.dynamics import environment_setup, propagation_setup

    resource = trajectory._build_collision_resource("safety-sampling-control")
    radius_m = next(s.guard_radius_m for s in resource.surfaces if s.body == "Moon")
    # Test-only straight line through a stationary Moon sphere in 0.25..0.75 s.
    # Other bodies are deliberately far away; no mission ephemeris is replaced.
    positions: dict[str, object] = {
        body: (1e12, 0.0, 0.0) for body in trajectory.PHYSICAL_BODY_NAMES
    }
    positions["Moon"] = (0.0, 0.0, 0.0)
    settings = environment_setup.BodyListSettings("SSB", "J2000")
    settings.add_empty_settings("Spacecraft")
    settings.get("Spacecraft").constant_mass = 2000.0
    bodies = environment_setup.create_system_of_bodies(settings)
    initial = np.asarray([-2.0 * radius_m, 0.0, 0.0, 4.0 * radius_m, 0.0, 0.0])
    stage_impacts: list[float] = []
    rejection: str | None = None

    def current_rejection() -> str | None:
        return trajectory._classify_trial_state(
            "safety-sampling-control", bodies.get("Spacecraft").state,
            2000.0, 1000.0, positions, resource,
        )

    def acceleration(epoch_tdb_s: float) -> NDArray[np.float64]:
        nonlocal rejection
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
        "safety-sampling-control", "departure-burn",
    )
    termination = propagation_setup.propagator.hybrid_termination([
        propagation_setup.propagator.custom_termination(stop),
        propagation_setup.propagator.time_termination(
            2.0, terminate_exactly_on_final_condition=True,
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
    assert stage_impacts
    assert all(0.25 - 1e-12 <= epoch <= 0.75 + 1e-12 for epoch in stage_impacts)
    # The zero-force analytic solution makes the crossing unambiguous.
    for epoch, raw in history.items():
        state = np.asarray(raw).reshape(7)
        assert abs(state[0] - (-2.0 + 4.0 * epoch) * radius_m) <= 1e-6
        assert np.linalg.norm(state[:3]) > radius_m
    if latch_stages:
        assert rejection == "rejected-impact:Moon"
        assert max(history) < 2.0
        # The outcome gate must not mistake the known early stop for epoch failure.
        assert trajectory._read_trial_arc_outcome(
            "safety-sampling-control", "departure-burn", simulator, 2.0, rejection,
        ) == "rejected-impact:Moon"
    else:
        assert rejection is None
        assert abs(max(history) - 2.0) <= 1e-6
    # Stage latching alone is NOT a continuous safety proof: crossings can lie
    # between stages, and rejected adaptive trials may contain unsafe stages.
