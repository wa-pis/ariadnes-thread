from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


@pytest.mark.parametrize("tighter", [False, True])
def test_native_minimum_step_failure_rejects_partial_result(
    tighter: bool, capfd: pytest.CaptureFixture[str],
) -> None:
    """A synthetic unstable ODE forces rejection, not a mission calculation."""
    from tudatpy import dynamics
    from tudatpy.dynamics import environment_setup, propagation_setup

    settings = environment_setup.BodyListSettings("SSB", "J2000")
    settings.add_empty_settings("Spacecraft")
    settings.get("Spacecraft").constant_mass = 2000.0
    bodies = environment_setup.create_system_of_bodies(settings)

    def acceleration(epoch_tdb_s: float) -> NDArray[np.float64]:
        # dv_x/dt = 1e12/s * v_x, deliberately faster than either minimum step.
        velocity_m_s = float(bodies.get("Spacecraft").state[3])
        return np.asarray([1e12 * velocity_m_s, 0.0, 0.0])

    def mass_rate(epoch_tdb_s: float) -> float:
        return 0.0

    accelerations = propagation_setup.create_acceleration_models(
        bodies, {"Spacecraft": {"Spacecraft": [
            propagation_setup.acceleration.custom(acceleration),
        ]}}, ["Spacecraft"], ["SSB"],
    )
    mass_rates = propagation_setup.create_mass_rate_models(
        bodies, {"Spacecraft": [propagation_setup.mass_rate.custom(mass_rate)]},
        accelerations,
    )
    integrator = trajectory._build_arc_integrator(
        "minimum-step-control", "departure-burn", tighter=tighter,
    )
    termination = propagation_setup.propagator.time_termination(
        10.0, terminate_exactly_on_final_condition=True,
    )
    translation = propagation_setup.propagator.translational(
        ["SSB"], accelerations, ["Spacecraft"],
        np.asarray([1.0, 0.0, 0.0, 1.0, 0.0, 0.0]),
        0.0, integrator, termination,
    )
    mass = propagation_setup.propagator.mass(
        ["Spacecraft"], mass_rates, np.asarray([2000.0]),
        0.0, integrator, termination,
    )
    coupled = propagation_setup.propagator.multitype(
        [translation, mass], integrator, 0.0, termination,
    )
    simulator = dynamics.simulator.create_dynamics_simulator(bodies, coupled)
    output = capfd.readouterr()
    assert "minimum" in (output.out + output.err).lower()
    assert simulator.integration_completed_successfully is False
    with pytest.raises(TrajectoryRefinementError, match="did not complete") as caught:
        trajectory._read_completed_arc_state(
            "minimum-step-control", "departure-burn", simulator, 10.0,
        )
    assert isinstance(caught.value.__cause__, RuntimeError)
