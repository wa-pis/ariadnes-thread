"""Private D14 Moon-only finite-thrust diagnostic, never a mission solution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
import hashlib
from importlib import import_module
import json
import math
from pathlib import Path
import time
from typing import Any

from . import ephemeris, trajectory as physical
from .errors import EphemerisError, TrajectoryRefinementError
from .lunar_departure import _lunar_departure_reference, _unit
from .models import OrbitSpec, SpacecraftSpec


_REFERENCE_SHA256 = "bbcfa37e2e259af0f5545aeb12e9784f8826122f1ad5a66c52698aef856b7134"
_MODEL = "local-moon-point-mass-finite-burn-v1"
State7 = tuple[float, ...]


@dataclass(frozen=True, slots=True)
class _LocalCommand:
    mu_m3_s2: float
    shape_radius_m: float
    dry_mass_kg: float
    thrust_n: float
    isp_s: float
    direction_j2000: tuple[float, float, float]
    ignition_epoch_tdb_s: float
    cutoff_after_ignition_s: float
    match_after_ignition_s: float
    initial_state_si: State7
    target_state_si: State7
    match_radius_m: float

    def __post_init__(self) -> None:
        for name in ("mu_m3_s2", "shape_radius_m", "dry_mass_kg", "thrust_n", "isp_s",
                     "cutoff_after_ignition_s", "match_after_ignition_s", "match_radius_m"):
            physical._positive_finite(name, getattr(self, name))
        physical._finite_float("ignition epoch", self.ignition_epoch_tdb_s)
        direction = physical._finite_vector3_values(self.direction_j2000, "inertial direction")
        if (not isinstance(self.direction_j2000, tuple) or abs(math.hypot(*direction)-1) > 1e-12
                or not isinstance(self.initial_state_si, tuple)
                or not isinstance(self.target_state_si, tuple)):
            raise ValueError("D14 immutable states and unit inertial direction required")
        _check_local_state(self, self.initial_state_si)
        _check_local_state(self, self.target_state_si)
        if self.match_after_ignition_s <= self.cutoff_after_ignition_s:
            raise ValueError("D14 match must follow cutoff")
        if self.match_radius_m <= self.shape_radius_m:
            raise ValueError("D14 match radius inside Moon")


@dataclass(slots=True)
class _LocalBudget(physical._RefinementBudget):
    completed_arcs: int = field(default=0, init=False)

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check()
        if (self.control_attempts != 1 or self.max_arcs_per_evaluation != 2
                or self.native_arc_propagations >= 4
                or self.completed_arcs != self.native_arc_propagations
                or first_in_evaluation != (self.native_arc_propagations % 2 == 0)):
            self._fail("D14 budget", "four ordered arcs only; no retry")
        super(_LocalBudget, self).begin_arc(first_in_evaluation=first_in_evaluation)


def _local_profile(tighter: bool) -> dict[str, Any]:
    if not isinstance(tighter, bool):
        raise ValueError("tighter must be boolean")
    return {
        "coefficient_set": "rkdp_87" if tighter else "rkf_78",
        "relative_tolerance": 1e-13 if tighter else 1e-11,
        "absolute_tolerances_si": ((1e-5,)*3+(1e-8,)*3+(1e-11,) if tighter
                                   else (1e-3,)*3+(1e-6,)*3+(1e-9,)),
        "initial_step_s": .25 if tighter else 1.,
        "minimum_step_s": 1e-8 if tighter else 1e-6,
        "maximum_step_s": 2. if tighter else 10.,
        "minimum_step_handling": "throw_exception_below_minimum",
        "assess_termination_on_minor_steps": False,
        "accept_infinity_step": False,
        "accept_nan_step": False,
    }


def _make_local_command(
    reference: dict[str, Any], launch_window_tdb_s: tuple[float, float],
) -> _LocalCommand:
    """Reconstruct the pinned branch before using any retained scientific value."""
    candidate = reference["candidate"]
    scenario = reference["scenario"]
    resource = reference["lunar_field_provenance"]
    if candidate["candidate_id"] != "d0001-t0035":
        raise ValueError("D14 candidate identity mismatch")
    spacecraft = SpacecraftSpec(**scenario["spacecraft"])
    rebuilt = _lunar_departure_reference(
        OrbitSpec(**scenario["departure_orbit"]),
        resource["gravitational_parameter_m3_s2"],
        resource["orbit_shape_radius_m"]+scenario["departure_orbit"]["periapsis_altitude_m"],
        tuple(candidate["departure_v_infinity_m_s"]), candidate["departure_epoch_tdb_s"],
        phase_policy="free", spacecraft=spacecraft,
        provisional_arrival_delta_v_m_s=candidate["arrival_delta_v_m_s"],
        flight_time_s=candidate["flight_time_s"],
    )
    if json.loads(json.dumps(asdict(rebuilt), allow_nan=False)) != reference["results"]["free"]:
        raise ValueError("D14 complete reference/branch reconstruction mismatch")
    branch = rebuilt.branches[0]
    if branch.estimate_status != "ideal-estimate-only":
        raise ValueError("D14 provisional mass/window rejected")
    mu, rp = rebuilt.gravitational_parameter_m3_s2, rebuilt.parking_radius_m
    rmatch = 10*rp
    duration = branch.departure_duration_s
    ti = rebuilt.virtual_periapsis_epoch_tdb_s-duration/2
    lower, upper = (physical._finite_float("launch bound", x) for x in launch_window_tdb_s)
    if lower >= upper or not lower <= ti <= upper:
        raise ValueError("D14 actual ignition outside original launch window")
    u = _unit(branch.position_m)
    parking_tangent = _unit(branch.parking_velocity_m_s)
    angle = -math.sqrt(mu/rp**3)*duration/2
    r = tuple(rp*(a*math.cos(angle)+b*math.sin(angle)) for a, b in zip(u, parking_tangent))
    v = tuple(math.sqrt(mu/rp)*(-a*math.sin(angle)+b*math.cos(angle)) for a, b in zip(u, parking_tangent))
    a = mu/math.hypot(*rebuilt.excess_velocity_m_s)**2
    e = branch.eccentricity
    h_anomaly = math.acosh((rmatch/a+1)/e)
    flight_s = math.sqrt(a**3/mu)*(e*math.sinh(h_anomaly)-h_anomaly)
    parameter = rp*(1+e)
    cosine = (parameter/rmatch-1)/e
    sine = math.sqrt(1-cosine**2)
    # Independent area-law quadrature, rather than another hyperbolic anomaly.
    angle_step = math.acos(cosine)/4096
    h = math.hypot(*branch.angular_momentum_m2_s)
    integral = 0.
    for i in range(4097):
        weight = 1 if i in (0, 4096) else 4 if i % 2 else 2
        integral += weight*(parameter/(1+e*math.cos(i*angle_step)))**2/h
    if abs(integral*angle_step/3-flight_s) > .001:
        raise ValueError("D14 independent time-of-flight check failed")
    tangent = _unit(branch.hyperbolic_velocity_m_s)
    target_r = tuple(rmatch*(cosine*x+sine*y) for x, y in zip(u, tangent))
    target_v = tuple(math.sqrt(mu/parameter)*(-sine*x+(e+cosine)*y) for x, y in zip(u, tangent))
    match_s = duration/2+flight_s
    if not math.isfinite(match_s) or match_s <= duration:
        raise ValueError("D14 comparison epoch must follow cutoff")
    energy = math.hypot(*target_v)**2/2-mu/rmatch
    momentum = physical._cross_product(target_r, target_v)
    if (abs(math.hypot(*target_r)-rmatch) > .001
            or abs(energy-branch.specific_energy_m2_s2) > 1e-10*max(mu/rp, abs(energy))
            or math.dist(momentum, branch.angular_momentum_m2_s) > 1e-10*math.hypot(*momentum)
            or physical._dot_product(target_r, target_v) <= 0):
        raise ValueError("D14 analytic target invariant failed")
    if branch.post_departure_mass_kg <= spacecraft.dry_mass_kg:
        raise ValueError("D14 cutoff mass must exceed dry mass")
    command = _LocalCommand(mu, resource["orbit_shape_radius_m"], spacecraft.dry_mass_kg,
        spacecraft.max_thrust_n, spacecraft.isp_s, _unit(branch.delta_v_m_s), ti,
        duration, match_s, r+v+(spacecraft.initial_mass_kg,),
        target_r+target_v+(branch.post_departure_mass_kg,), rmatch)
    _check_local_state(command, command.initial_state_si)
    _check_local_state(command, command.target_state_si)
    return command


def _check_local_state(command: _LocalCommand, state: State7) -> None:
    if len(state) != 7:
        raise ValueError("D14 state must contain seven SI components")
    for value in state:
        physical._finite_float("D14 state component", value)
    radius = physical._positive_finite("D14 state radius", math.hypot(*state[:3]))
    if radius <= command.shape_radius_m:
        raise ValueError("D14 detected lunar impact; sampled guard only")
    if state[6] <= command.dry_mass_kg:
        raise ValueError("D14 detected dry-mass violation")


def _native_local_arc(
    command: _LocalCommand, initial: State7, start_s: float, end_s: float,
    burn: bool, tighter: bool, budget: _LocalBudget,
) -> tuple[State7, int]:
    """Tudat coupled translation/mass; relative seconds avoid large-epoch loss.

    Guard derivative stages and saved states. No continuous-interval certificate.
    Native exceptions are translated here, never replaced with conic data.
    """
    budget.check()
    if not isinstance(burn, bool) or not isinstance(tighter, bool):
        raise ValueError("D14 arc flags must be boolean")
    start_s = physical._finite_float("arc start", start_s)
    end_s = physical._finite_float("arc end", end_s)
    if end_s <= start_s:
        raise ValueError("D14 arc end must follow start")
    _check_local_state(command, initial)
    try:
        import numpy as np
        from tudatpy.dynamics import environment_setup, propagation_setup, simulator

        # This isolated two-body model anchors Moon at zero. These are not
        # Solar-System ephemerides, nor a fallback for missing SPICE data.
        body_settings = environment_setup.BodyListSettings("SSB", "J2000")
        body_settings.add_empty_settings("Moon")
        body_settings.get("Moon").ephemeris_settings = environment_setup.ephemeris.constant(
            np.zeros(6), "SSB", "J2000")
        body_settings.get("Moon").gravity_field_settings = environment_setup.gravity_field.central(command.mu_m3_s2)
        body_settings.add_empty_settings("Spacecraft")
        body_settings.get("Spacecraft").constant_mass = initial[6]
        bodies = environment_setup.create_system_of_bodies(body_settings)

        def thrust(at: float) -> Any:
            budget.check()
            body = bodies.get("Spacecraft")
            state = tuple(float(x) for x in np.asarray(body.state).reshape(-1))+(float(body.mass),)
            _check_local_state(command, state)
            force = command.thrust_n if burn else 0.
            return np.asarray(command.direction_j2000)*force/state[6]

        def mass_rate(at: float) -> float:
            budget.check()
            return -command.thrust_n/(physical.STANDARD_GRAVITY_M_S2*command.isp_s) if burn else 0.

        acceleration_settings = {"Spacecraft": {
            "Moon": [propagation_setup.acceleration.point_mass_gravity()],
            "Spacecraft": [propagation_setup.acceleration.custom(thrust)],
        }}
        accelerations = propagation_setup.create_acceleration_models(
            bodies, acceleration_settings, ["Spacecraft"], ["Moon"])
        rates = propagation_setup.create_mass_rate_models(bodies,
            {"Spacecraft": [propagation_setup.mass_rate.custom(mass_rate)]}, accelerations)

        termination = propagation_setup.propagator.time_termination(
            end_s, terminate_exactly_on_final_condition=True)
        integrator = physical._build_integrator_from_profile("D14", "local", _local_profile(tighter))
        translation = propagation_setup.propagator.translational(
            ["Moon"], accelerations, ["Spacecraft"], initial[:6], start_s, integrator, termination)
        mass = propagation_setup.propagator.mass(["Spacecraft"], rates, (initial[6],),
            start_s, integrator, termination)
        settings = propagation_setup.propagator.multitype(
            [translation, mass], integrator, start_s, termination)
        budget.check()
        budget.begin_arc(first_in_evaluation=burn)
        result = simulator.create_dynamics_simulator(bodies, settings)
        budget.check()
        if result.integration_completed_successfully is not True:
            raise ValueError("D14 native integration failed")
        samples = sorted(result.state_history.items())
        if not samples or samples[0][0] != start_s or samples[-1][0] != end_s:
            raise ValueError("D14 native history epoch mismatch")
        parsed = []
        for at, raw in samples:
            budget.check()
            physical._finite_float("D14 history time", at)
            state = tuple(float(x) for x in np.asarray(raw).reshape(-1))
            _check_local_state(command, state)
            if not burn and state[6] != initial[6]:
                raise ValueError("D14 coast mass changed")
            parsed.append(state)
        if parsed[0] != initial:
            raise ValueError("D14 native initial-state/handoff reset")
        expected_mass = initial[6]-(command.thrust_n*(end_s-start_s)/(
            physical.STANDARD_GRAVITY_M_S2*command.isp_s) if burn else 0.)
        if abs(parsed[-1][6]-expected_mass) > 1e-6:
            raise ValueError("D14 native analytic mass disagreement")
    except Exception as exc:
        # The untyped native boundary includes callbacks and native output access.
        raise TrajectoryRefinementError(f"D14 native local arc: {exc}") from exc
    budget.completed_arcs += 1
    return parsed[-1], len(parsed)


def _closure(command: _LocalCommand, final: State7) -> dict[str, Any]:
    _check_local_state(command, final)
    residual = tuple(x-y for x, y in zip(final[:6], command.target_state_si[:6]))
    position, velocity = math.hypot(*residual[:3]), math.hypot(*residual[3:])
    for value in (*residual, position, velocity):
        physical._finite_float("D14 residual", value)
    return {"residual_si": residual, "position_error_m": position,
            "velocity_error_m_s": velocity,
            "closure": "pass" if position <= 10 and velocity <= .01 else "fail"}


def _run_local_burn(
    reference_path: Path, *, monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Prepare and execute one four-arc diagnostic; caller saves new evidence.

    No reference-case execution belongs to D14.2; D14.3 invokes this separately.
    """
    budget = _LocalBudget("d0001-t0035", 300., monotonic, max_arcs_per_evaluation=2)
    runs: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "candidate_id": "d0001-t0035", "branch_phase_rad": None,
        "model_id": _MODEL, "origin": "Moon", "orientation": "J2000", "units": "SI",
        "time_scale": "TDB seconds since J2000", "mission_qualified": False,
        "outcome": "failed", "agreement": "unavailable", "omissions": "Earth/Sun, harmonics, SRP, relativity, Mars; no continuous safety certificate",
        "reference_sha256": _REFERENCE_SHA256, "runs": runs,
        "profiles": {"nominal": _local_profile(False), "tighter": _local_profile(True)},
        "command": None,
    }
    for name in ("nominal", "tighter"):
        runs.append({"profile": name, "outcome": "skipped", "reason": "previous stage not completed",
                     "closure": "unavailable", "cutoff_state_si": None, "final_state_si": None})
    try:
        budget.check()
        raw = reference_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != _REFERENCE_SHA256:
            raise ValueError("D14 reference SHA256 mismatch")
        reference = json.loads(raw)
        search = reference["scenario"]["search"]
        window = tuple(ephemeris.utc_to_tdb(search[key]) for key in
                       ("departure_start_utc", "departure_end_utc"))
        budget.check()
        command = _make_local_command(reference, window)
        report["command"] = asdict(command)
        report["branch_phase_rad"] = reference["results"]["free"]["branches"][0]["phase_rad"]
        report["launch_window_tdb_s"] = window
        report["reference_path"] = str(reference_path)
        report["kernels"] = ephemeris.kernel_metadata()
        try:
            report["runtime_versions"] = {name: str(import_module(name).__version__)
                                          for name in ("numpy", "tudatpy")}
        except (ImportError, AttributeError) as exc:
            raise TrajectoryRefinementError(f"D14 runtime provenance unavailable: {exc}") from exc
        report["retained_lunar_resource"] = reference["lunar_field_provenance"]
        report["source_sha256"] = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                   for name in ("local_burn.py", "lunar_departure.py", "models.py", "trajectory.py", "ephemeris.py")}
        for tighter, run in zip((False, True), runs):
            run["outcome"] = "failed"
            run["reason"] = "arc did not complete"
            budget.check()
            if not tighter:
                budget.begin_control()
            cutoff, checks = _native_local_arc(command, command.initial_state_si, 0.,
                command.cutoff_after_ignition_s, True, tighter, budget)
            run["cutoff_state_si"] = cutoff
            mass_error = abs(cutoff[6]-command.target_state_si[6])
            run["cutoff_mass_error_kg"] = mass_error
            if mass_error > 1e-6:
                raise ValueError("D14 analytic cutoff mass disagreement")
            final, coast_checks = _native_local_arc(command, cutoff,
                command.cutoff_after_ignition_s, command.match_after_ignition_s,
                False, tighter, budget)
            run.update(_closure(command, final))
            run.update(outcome="completed", reason=None, final_state_si=final,
                       checked_saved_states=checks+coast_checks)
        nominal, tighter_state = (run["final_state_si"] for run in runs)
        differences = (math.dist(nominal[:3], tighter_state[:3]),
                       math.dist(nominal[3:6], tighter_state[3:6]),
                       abs(nominal[6]-tighter_state[6]))
        for value in differences:
            physical._finite_float("D14 agreement difference", value)
        report["agreement_differences_si"] = differences
        report["agreement"] = "pass" if all(x <= y for x, y in zip(differences, (1., .001, 1e-6))) else "fail"
        budget.check()
        report["outcome"] = "completed"
    except (ValueError, TypeError, KeyError, OSError, OverflowError, EphemerisError,
            TrajectoryRefinementError) as exc:
        report["reason"] = f"D14 stopped: {exc}"
        report["agreement"] = "unavailable"
    report.update(native_arc_propagations=budget.native_arc_propagations,
                  completed_arcs=budget.completed_arcs,
                  elapsed_wall_s=budget._last_monotonic_s-(budget.deadline_monotonic_s-300.))
    return report
