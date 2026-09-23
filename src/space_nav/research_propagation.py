"""Isolated sampled-guard research propagation, not a strict-M3 executor."""

from __future__ import annotations

from dataclasses import replace
import json
import math

from . import ephemeris, trajectory as physical
from .errors import EphemerisError, TrajectoryRefinementError
from .models import (
    FiniteBurnRecord,
    ImpulsiveTransferCandidate,
    Scenario,
    TrajectoryBoundaryState,
)
from .research import (
    ResearchProgress,
    ResearchReport,
    ResearchRun,
    _ResearchBudget,
    _canonical_object,
)


_ARCS = ("departure-burn", "coast", "arrival-burn")
_COVERAGE = (
    "Checks count repeated evaluations, not unique epochs: pre-arc states, "
    "custom full-step termination evaluations within the arc, and saved native "
    "history including endpoints. No RK minor-stage or continuous-interval "
    "guarantee; between-check impacts, small bodies and debris are not excluded."
)


def _environment_identity(
    environment: physical._PhysicalEnvironment,
) -> tuple[object, ...]:
    """Immutable resource/model description, excluding native mutable objects."""
    return tuple(
        getattr(environment, name)
        for name in (
            "model_id",
            "initial_epoch_tdb_s",
            "final_epoch_tdb_s",
            "origin",
            "orientation",
            "harmonic_fields",
            "gravity_acceleration_inventory",
            "solar_radiation_pressure",
            "relativity",
            "collision_resource",
        )
    )


def _compare_research_profiles(
    budget: _ResearchBudget,
    scenario: Scenario,
    candidate: ImpulsiveTransferCandidate,
    environment: physical._PhysicalEnvironment,
    initial_state: TrajectoryBoundaryState,
    target_state: TrajectoryBoundaryState,
    controls: tuple[float, ...],
    provenance_json: str,
) -> ResearchReport:
    """Run nominal then tighter once, with fixed commands and the shared clock.

    Caller verifies candidate/resources, prepares nominal environment under this
    budget and holds the science lock. Tighter preparation uses the same deadline.
    Wall time ends at the last budget observation, before report serialization.
    """
    if (
        candidate.candidate_id != budget.candidate_id
        or candidate.departure_epoch_tdb_s != initial_state.epoch_tdb_s
        or candidate.arrival_epoch_tdb_s != target_state.epoch_tdb_s
    ):
        raise ValueError("candidate identity and epochs must match verified boundaries")
    if not isinstance(controls, tuple):
        raise ValueError("fixed seed controls must be an immutable tuple")
    provenance_json = _canonical_object("provenance_json", provenance_json)
    identity = _environment_identity(environment)
    nominal = _propagate_research_run(
        budget,
        scenario,
        environment,
        initial_state,
        target_state,
        controls,
    )
    tighter = ResearchRun(
        profile="tighter",
        outcome="unavailable",
        reason="nominal-not-completed",
        progress=ResearchProgress(0, 0),
        checked_state_count=0,
        check_coverage="No states or events checked; tighter propagation not started.",
    )
    if nominal.outcome == "completed":
        try:
            budget.check()
            fresh = physical._build_physical_environment(
                candidate, scenario.spacecraft, budget=budget
            )
            budget.check()
            if fresh is environment or fresh.bodies is environment.bodies:
                raise ValueError("tighter profile requires a fresh native environment")
            if _environment_identity(fresh) != identity:
                raise ValueError("tighter environment resource/model identity changed")
        except (TrajectoryRefinementError, ValueError) as exc:
            tighter = replace(tighter, reason=f"tighter preparation: {exc}")
        else:
            tighter = _propagate_research_run(
                budget,
                scenario,
                fresh,
                initial_state,
                target_state,
                controls,
                tighter=True,
            )
    return ResearchReport(
        candidate_id=candidate.candidate_id,
        scenario=scenario,
        seed_controls=controls,
        provenance_json=provenance_json,
        nominal=nominal,
        tighter=tighter,
        elapsed_wall_s=budget._last_monotonic_s
        - (budget.deadline_monotonic_s - budget.runtime_seconds),
    )


def _propagate_research_run(
    budget: _ResearchBudget,
    scenario: Scenario,
    environment: physical._PhysicalEnvironment,
    initial_state: TrajectoryBoundaryState,
    target_state: TrajectoryBoundaryState,
    controls: tuple[float, ...],
    *,
    tighter: bool = False,
) -> ResearchRun:
    """Compose one fixed-seed run using a prepared, verified M3 environment.

    Caller serializes native/global SPICE access and verifies candidate/resources.
    Fresh environment per profile; shared budget spans preparation and both runs.
    Stop on detected invalid states; preserve diagnostics, never partial endpoints.
    """
    if not isinstance(budget, _ResearchBudget) or not isinstance(tighter, bool):
        raise ValueError("research budget and boolean tighter profile required")
    expected = 3 if tighter else 0
    if (
        budget.native_arc_propagations != expected
        or budget.completed_arcs != expected
        or budget.control_attempts != int(tighter)
    ):
        raise ValueError("profile must start once, in nominal/tighter order")
    profile = "tighter" if tighter else "nominal"
    settings_json = json.dumps(
        {
            arc: physical._arc_integrator_profile(
                budget.candidate_id,
                arc,
                tighter=tighter,
            )
            for arc in _ARCS
        }
    )
    checked = 0
    arc = "preflight"
    epoch = initial_state.epoch_tdb_s

    def check_state(at: float, state: object, mass: object) -> None:
        nonlocal checked
        rejection = physical._classify_environment_trial_state(
            budget,
            environment,
            at,
            state,
            mass,
            scenario.spacecraft.dry_mass_kg,
        )
        checked += 1
        # Research contract rejects reaching dry mass, unlike the legacy < gate.
        if mass == scenario.spacecraft.dry_mass_kg:
            rejection = "rejected-dry-mass"
        if rejection is not None:
            raise TrajectoryRefinementError(f"{arc} at {at} TDB s: {rejection}")

    try:
        budget.check()
        if not tighter:
            budget.begin_control()
        if (
            environment.model_id != physical.PHYSICAL_MODEL_IDENTIFIER
            or (environment.origin, environment.orientation) != ("SSB", "J2000")
            or environment.initial_epoch_tdb_s != initial_state.epoch_tdb_s
            or environment.final_epoch_tdb_s != target_state.epoch_tdb_s
        ):
            raise ValueError(
                "verified environment must match the boundary interval and pinned model"
            )
        prepared = physical._prepare_burn_controls(
            budget.candidate_id,
            scenario.spacecraft,
            initial_state.epoch_tdb_s,
            target_state.epoch_tdb_s,
            controls,
        )
        if isinstance(prepared, str):
            raise TrajectoryRefinementError(prepared)
        if prepared != controls:
            raise ValueError("controls must already be canonical")
        epochs = (
            epoch,
            epoch + controls[2],
            target_state.epoch_tdb_s - controls[5],
            target_state.epoch_tdb_s,
        )
        states = [replace(initial_state, label="departure-ignition")]
        masses = [scenario.spacecraft.initial_mass_kg]
        burns: list[FiniteBurnRecord] = []
        state = (*initial_state.position_m, *initial_state.velocity_m_s)
        mass = masses[0]
        propagation_setup = physical._import_tudat_propagation_setup()
        for index, arc in enumerate(_ARCS):
            epoch, end = epochs[index : index + 2]
            check_state(epoch, state, mass)
            burn_id = "departure" if index == 0 else "arrival" if index == 2 else None
            offset = 0 if index == 0 else 3
            if burn_id is not None:
                physical._install_tnw_engine(
                    budget.candidate_id,
                    environment.bodies,
                    scenario.spacecraft,
                    burn_id,
                    *controls[offset : offset + 2],
                )
            accelerations = physical._build_arc_force_models(
                budget.candidate_id,
                environment,
                burn_id=burn_id,
            )
            detected: TrajectoryRefinementError | None = None

            def stop(at: float) -> bool:
                nonlocal detected
                budget.check()
                if detected is not None:
                    return True
                # Exact time termination can evaluate a trial past the arc end.
                # It is outside this requested arc, not counted as checked.
                if at > end:
                    return False
                try:
                    body = environment.bodies.get(physical.SPACECRAFT_BODY_NAME)
                    sample, sample_mass = body.state, body.mass
                except Exception as exc:
                    physical._raise_refinement_error(
                        budget.candidate_id, "research-guard", str(exc), exc
                    )
                try:
                    check_state(at, sample, sample_mass)
                except TrajectoryRefinementError as exc:
                    detected = exc
                    return True
                return False

            try:
                termination = propagation_setup.propagator.hybrid_termination(
                    [
                        propagation_setup.propagator.custom_termination(stop),
                        propagation_setup.propagator.time_termination(
                            end, terminate_exactly_on_final_condition=True
                        ),
                    ],
                    fulfill_single_condition=True,
                )
            except Exception as exc:
                physical._raise_refinement_error(
                    budget.candidate_id, "research-termination", str(exc), exc
                )
            coupled = physical._build_coupled_arc_settings(
                budget.candidate_id,
                environment.bodies,
                accelerations,
                state,
                mass,
                epoch,
                physical._build_arc_integrator(
                    budget.candidate_id, arc, tighter=tighter
                ),
                termination,
                thrust_enabled=burn_id is not None,
            )
            simulator = physical._run_native_arc(
                budget, environment.bodies, coupled, first_in_evaluation=index == 0
            )
            try:
                succeeded = simulator.integration_completed_successfully
            except Exception as exc:
                physical._raise_refinement_error(
                    budget.candidate_id, "research-completion", str(exc), exc
                )
            if succeeded is not True:
                raise TrajectoryRefinementError(
                    f"native integration failed; detected event: {detected}"
                )
            if detected is not None:
                raise detected  # Known event before final-epoch mismatch.
            try:
                history = simulator.state_history
                samples = sorted(history.items())
            except Exception as exc:
                physical._raise_refinement_error(
                    budget.candidate_id, "research-history", str(exc), exc
                )
            for at, raw in samples:
                budget.check()
                try:
                    flatten = getattr(raw, "reshape", None)
                    values = tuple(flatten(-1) if callable(flatten) else raw)
                    if len(values) != 7:
                        raise ValueError("saved state must have seven components")
                    at = physical._finite_float("history epoch", at)
                except (TypeError, ValueError) as exc:
                    physical._raise_refinement_error(
                        budget.candidate_id, "research-history", str(exc), exc
                    )
                check_state(at, values[:6], values[6])
                if burn_id is None and values[6] != mass:
                    raise ValueError("coast mass changed in saved history")
            if not samples or samples[0][0] != epoch:
                raise ValueError("native history must begin at the supplied epoch")
            first = samples[0][1]
            flatten = getattr(first, "reshape", None)
            first = tuple(flatten(-1) if callable(flatten) else first)
            if first != (*state, mass):
                raise ValueError(
                    "native initial state/mass differs from supplied handoff"
                )
            next_state, next_mass = physical._read_completed_arc_state(
                budget.candidate_id,
                arc,
                simulator,
                end,
            )
            if burn_id is None:
                if next_mass != mass:
                    raise ValueError("coast mass changed")
            else:
                burns.append(
                    FiniteBurnRecord(
                        burn_id=burn_id,
                        start_epoch_tdb_s=epoch,
                        end_epoch_tdb_s=end,
                        direction_frame="Moon-relative TNW"
                        if index == 0
                        else "Mars-relative TNW",
                        direction_tnw=physical._direction_tnw_from_angles(
                            *controls[offset : offset + 2]
                        ),
                        thrust_n=scenario.spacecraft.max_thrust_n,
                        isp_s=scenario.spacecraft.isp_s,
                        initial_mass_kg=mass,
                        final_mass_kg=next_mass,
                        propellant_mass_kg=mass - next_mass,
                        ideal_equivalent_delta_v_m_s=physical.STANDARD_GRAVITY_M_S2
                        * scenario.spacecraft.isp_s
                        * math.log(mass / next_mass),
                    )
                )
            states.append(
                TrajectoryBoundaryState(
                    label=("departure-cutoff", "arrival-ignition", "arrival-cutoff")[
                        index
                    ],
                    epoch_utc=ephemeris.tdb_to_utc(end),
                    epoch_tdb_s=end,
                    origin="SSB",
                    orientation="J2000",
                    position_m=next_state[:3],
                    velocity_m_s=next_state[3:],
                )
            )
            masses.append(next_mass)
            state, mass = next_state, next_mass
            if index < 2:
                budget.complete_arc()
        result = ResearchRun(
            profile=profile,
            outcome="completed",
            reason=None,
            progress=ResearchProgress(3, 3),
            checked_state_count=checked,
            check_coverage=_COVERAGE,
            integrator_settings_json=settings_json,
            boundaries=tuple(states),
            boundary_masses_kg=tuple(masses),
            burns=tuple(burns),
            target_state=target_state,
        )
        budget.complete_arc()
        return result
    except (TrajectoryRefinementError, EphemerisError, ValueError, RuntimeError) as exc:
        return ResearchRun(
            profile=profile,
            outcome="aborted",
            reason=f"{arc} from {epoch} TDB s: {exc}",
            progress=ResearchProgress(
                budget.native_arc_propagations - expected,
                budget.completed_arcs - expected,
            ),
            checked_state_count=checked,
            check_coverage=_COVERAGE,
            integrator_settings_json=settings_json,
        )
