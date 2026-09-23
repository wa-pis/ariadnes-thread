from __future__ import annotations

from dataclasses import replace
import math
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from space_nav import trajectory as physical
from space_nav import research_propagation as propagation
from space_nav.errors import TrajectoryRefinementError
from space_nav.research import ResearchProgress, _ResearchBudget
from test_research_report import _report


def _rig(monkeypatch: pytest.MonkeyPatch, fault: str = "") -> SimpleNamespace:
    """Manufactured adapters exercise composition, not physical fidelity."""
    report = _report()
    initial, target = report.nominal.boundaries[0], report.nominal.target_state
    spacecraft = SimpleNamespace(
        state=initial.position_m + initial.velocity_m_s, mass=2000.0
    )
    bodies = SimpleNamespace(
        get=lambda name: (
            spacecraft
            if name == "Spacecraft"
            else SimpleNamespace(
                ephemeris=SimpleNamespace(
                    cartesian_state=lambda epoch: (1e12, 0.0, 0.0, 0.0, 0.0, 0.0)
                ),
            )
        )
    )
    resource = physical._CollisionResource(
        "fixture",
        "fixture",
        "fixture",
        0.001,
        tuple(
            physical._CollisionSurfaceResource(
                body, (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), 1.0
            )
            for body in physical.PHYSICAL_BODY_NAMES
        ),
    )
    environment = SimpleNamespace(
        model_id=physical.PHYSICAL_MODEL_IDENTIFIER,
        origin="SSB",
        orientation="J2000",
        initial_epoch_tdb_s=100.0,
        final_epoch_tdb_s=200.0,
        bodies=bodies,
        collision_resource=resource,
    )
    clock = [0.0]
    budget = _ResearchBudget(report.candidate_id, 300.0, lambda: clock[0])
    calls: list[tuple[tuple[float, ...], float, float]] = []
    monkeypatch.setattr(physical, "_install_tnw_engine", lambda *args: "fixture-engine")
    monkeypatch.setattr(
        physical, "_build_arc_force_models", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(physical, "_build_arc_integrator", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        physical,
        "_import_tudat_propagation_setup",
        lambda: SimpleNamespace(
            propagator=SimpleNamespace(
                custom_termination=lambda stop: stop,
                time_termination=lambda end, **kwargs: end,
                hybrid_termination=lambda terms, **kwargs: terms,
            )
        ),
    )
    monkeypatch.setattr(
        physical,
        "_build_coupled_arc_settings",
        lambda cid, bodies, forces, state, mass, epoch, integ, terms, **kwargs: (
            state,
            mass,
            epoch,
            terms,
            kwargs["thrust_enabled"],
        ),
    )
    times = {s.epoch_tdb_s: s.epoch_utc for s in report.nominal.boundaries}
    monkeypatch.setattr(propagation.ephemeris, "tdb_to_utc", lambda epoch: times[epoch])

    def native(
        budget: _ResearchBudget,
        bodies: Any,
        settings: tuple,
        *,
        first_in_evaluation: bool,
    ) -> SimpleNamespace:
        budget.begin_arc(first_in_evaluation=first_in_evaluation)
        state, mass, epoch, (stop, end), thrust = settings
        calls.append((state, mass, epoch))
        if fault == "native":
            raise TrajectoryRefinementError("manufactured native failure")
        finish = tuple(x + 1.0 for x in state)
        final_mass = mass - 0.01 * (end - epoch) if thrust else mass
        if len(calls) == 1 and fault in ("event", "dry", "early"):
            end = epoch + 1.0
        if fault == "event":
            finish = (1e12, 0.0, 0.0, *finish[3:])
        if fault == "dry":
            final_mass = report.scenario.spacecraft.dry_mass_kg
        spacecraft.state, spacecraft.mass = finish, final_mass
        if fault != "history-impact":
            stop(end)
        history = {epoch: (*state, mass), end: (*finish, final_mass)}
        if fault == "history-impact":
            history[epoch + 0.5] = (1e12, 0.0, 0.0, 0.0, 0.0, 0.0, mass)
        if fault == "reset":
            history[epoch] = (*state, mass + 1.0)
        if fault == "coast-mass" and len(calls) == 2:
            history[end] = (*finish, mass - 1.0)
        if fault == "coast-intermediate-mass" and len(calls) == 2:
            history[epoch + 0.5] = (*state, mass - 1.0)
        if fault == "deadline":
            clock[0] = 300.0
        native_epoch = MagicMock()
        native_epoch.to_float.return_value = end
        native_epoch.__sub__.side_effect = lambda other: SimpleNamespace(
            to_float=lambda: end - other
        )
        return SimpleNamespace(
            integration_completed_successfully=fault != "failed",
            state_history=history,
            state_history_time_object={native_epoch: None},
        )

    monkeypatch.setattr(physical, "_run_native_arc", native)
    return SimpleNamespace(
        report=report,
        environment=environment,
        initial=initial,
        target=target,
        budget=budget,
        calls=calls,
        clock=clock,
    )


def _run(rig: SimpleNamespace) -> Any:
    return propagation._propagate_research_run(
        rig.budget,
        rig.report.scenario,
        rig.environment,
        rig.initial,
        rig.target,
        rig.report.seed_controls,
    )


def test_three_arcs_carry_exact_state_and_mass(monkeypatch: pytest.MonkeyPatch) -> None:
    rig = _rig(monkeypatch)
    result = _run(rig)
    assert result.outcome == "completed", result.reason
    assert result.progress == ResearchProgress(3, 3)
    assert result.boundary_masses_kg == pytest.approx(
        (2000.0, 1999.9, 1999.9, 1999.8), abs=1e-10
    )
    assert len(rig.calls) == 3
    for call, boundary, mass in zip(
        rig.calls, result.boundaries, result.boundary_masses_kg
    ):
        assert call == (
            boundary.position_m + boundary.velocity_m_s,
            mass,
            boundary.epoch_tdb_s,
        )
    assert result.checked_state_count == 12  # pre-arc + callback + 2 saved states
    assert "No RK minor-stage" in result.check_coverage
    assert result.continuous_safety_verified is False


@pytest.mark.parametrize(
    "fault,reason,attempts,completed",
    [
        ("event", "rejected-impact:Sun", 1, 0),
        ("dry", "rejected-dry-mass", 1, 0),
        ("history-impact", "rejected-impact:Sun", 1, 0),
        ("early", "final epoch mismatch", 1, 0),
        ("native", "native failure", 1, 0),
        ("failed", "native integration failed", 1, 0),
        ("reset", "handoff", 1, 0),
        ("coast-mass", "coast mass changed", 2, 1),
        ("coast-intermediate-mass", "coast mass changed", 2, 1),
        ("deadline", "deadline", 1, 0),
    ],
)
def test_rejection_discards_partial_history(
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    reason: str,
    attempts: int,
    completed: int,
) -> None:
    rig = _rig(monkeypatch, fault)
    result = _run(rig)
    assert result.outcome == "aborted"
    assert reason in result.reason
    if fault in ("event", "dry", "history-impact"):
        assert "final epoch mismatch" not in result.reason
    assert result.progress == ResearchProgress(attempts, completed)
    assert len(rig.calls) == attempts
    assert not result.boundaries and not result.burns and result.terminal_errors is None


@pytest.mark.parametrize("fault", ["impact", "deadline", "controls", "environment"])
def test_preflight_rejection_launches_nothing(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    rig = _rig(monkeypatch)
    if fault == "impact":
        rig.initial = replace(rig.initial, position_m=(1e12, 0.0, 0.0))
    elif fault == "deadline":
        rig.clock[0] = 300.0
    elif fault == "controls":
        result = propagation._propagate_research_run(
            rig.budget,
            rig.report.scenario,
            rig.environment,
            rig.initial,
            rig.target,
            (0.0, 0.0, 1000.0, 0.0, 0.0, 10.0),
        )
        assert result.outcome == "aborted" and result.progress == ResearchProgress(0, 0)
        return
    else:
        rig.environment.model_id = "not-the-pinned-model"
    result = _run(rig)
    assert result.outcome == "aborted", result.reason
    assert result.progress == ResearchProgress(0, 0)
    assert not rig.calls


def test_native_three_arc_composition_matches_rocket_equation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Toy native oracle: stationary far-away bodies, not mission ephemerides."""
    from tudatpy.dynamics import environment_setup, propagation_setup
    import numpy as np

    report = _report()
    budget = _ResearchBudget(report.candidate_id, 300.0)
    settings = environment_setup.BodyListSettings("SSB", "J2000")
    settings.add_empty_settings("Spacecraft")
    settings.get("Spacecraft").constant_mass = 2000.0
    for name in physical.PHYSICAL_BODY_NAMES:
        settings.add_empty_settings(name)
        settings.get(name).ephemeris_settings = environment_setup.ephemeris.constant(
            np.asarray([1e12, 0.0, 0.0, 0.0, 0.0, 0.0]),
            "SSB",
            "J2000",
        )
        settings.get(
            name
        ).gravity_field_settings = environment_setup.gravity_field.central(1.0)
    bodies = environment_setup.create_system_of_bodies(settings)
    environment = SimpleNamespace(
        model_id=physical.PHYSICAL_MODEL_IDENTIFIER,
        origin="SSB",
        orientation="J2000",
        initial_epoch_tdb_s=100.0,
        final_epoch_tdb_s=200.0,
        bodies=bodies,
        collision_resource=physical._build_collision_resource(report.candidate_id),
    )

    def forces(
        candidate_id: object, environment: Any, *, burn_id: str | None = None
    ) -> Any:
        acceleration_settings = {
            name: [propagation_setup.acceleration.point_mass_gravity()]
            for name in physical.PHYSICAL_BODY_NAMES
        }
        if burn_id is not None:
            acceleration_settings["Spacecraft"] = [
                propagation_setup.acceleration.thrust_from_engine(f"{burn_id}-main")
            ]
        return propagation_setup.create_acceleration_models(
            environment.bodies,
            {"Spacecraft": acceleration_settings},
            ["Spacecraft"],
            ["SSB"],
        )

    monkeypatch.setattr(physical, "_build_arc_force_models", forces)
    initial = replace(
        report.nominal.boundaries[0],
        epoch_utc=propagation.ephemeris.tdb_to_utc(100.0),
        position_m=(0.0, 1e7, 0.0),
        velocity_m_s=(1000.0, 0.0, 0.0),
    )
    target = replace(
        initial,
        label="target",
        epoch_tdb_s=200.0,
        epoch_utc=propagation.ephemeris.tdb_to_utc(200.0),
    )
    result = propagation._propagate_research_run(
        budget, report.scenario, environment, initial, target, report.seed_controls
    )
    assert result.outcome == "completed", result.reason
    assert result.progress == ResearchProgress(3, 3)
    assert result.boundary_masses_kg == pytest.approx(
        (2000.0, 1999.9, 1999.9, 1999.8), abs=1e-8
    )
    # Each toy GM=1 m^3/s^2 at ~1e12 m: total gravity over 100 s <1e-20 m/s.
    expected_vx = 1000.0 + 9806.65 * math.log(2000.0 / 1999.8)
    assert result.boundaries[-1].velocity_m_s == pytest.approx(
        (expected_vx, 0.0, 0.0), abs=1e-6
    )
    assert result.checked_state_count > 12
    assert result.continuous_safety_verified is False
