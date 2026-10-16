"""Private D13 two-body impulse references; no propagation or mission selection."""

from __future__ import annotations

from dataclasses import dataclass
import math

from . import trajectory as physical
from .errors import TrajectoryRefinementError
from .models import OrbitSpec, SpacecraftSpec


Vector3 = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class _DepartureBranch:
    phase_rad: float
    phase_change_rad: float
    position_m: Vector3
    parking_velocity_m_s: Vector3
    hyperbolic_velocity_m_s: Vector3
    delta_v_m_s: Vector3
    delta_v_norm_m_s: float
    eccentricity: float
    angular_momentum_m2_s: Vector3
    specific_energy_m2_s2: float
    position_error_m: float
    velocity_error_m_s: float
    asymptote_error_m_s: float
    radial_velocity_m_s: float
    energy_error_m2_s2: float
    post_departure_mass_kg: float
    provisional_final_mass_kg: float
    departure_propellant_kg: float
    provisional_arrival_propellant_kg: float
    departure_duration_s: float
    provisional_arrival_duration_s: float
    estimate_status: str


@dataclass(frozen=True, slots=True)
class _DepartureReference:
    status: str
    phase_policy: str
    virtual_periapsis_epoch_tdb_s: float
    gravitational_parameter_m3_s2: float
    parking_radius_m: float
    excess_velocity_m_s: Vector3
    provisional_arrival_delta_v_m_s: float
    branches: tuple[_DepartureBranch, ...]
    origin: str = "Moon"
    orientation: str = "J2000"
    units: str = "SI"
    time_scale: str = "TDB seconds since J2000"
    interpretation: str = "Local impulsive reference only; no finite-burn or mission feasibility."


def _unit(values: Vector3) -> Vector3:
    norm = physical._positive_finite("vector norm", math.hypot(*values))
    return physical._finite_vector3_values(tuple(v/norm for v in values), "unit vector")


def _branch(
    phase: float, initial_phase: float, p: Vector3, q: Vector3, s: Vector3,
    excess: Vector3, mu: float, radius: float, eccentricity: float,
    spacecraft: SpacecraftSpec, arrival_delta_v: float, flight_time: float,
) -> _DepartureBranch:
    dot, cross = physical._dot_product, physical._cross_product
    u = tuple(a*math.cos(phase)+b*math.sin(phase) for a, b in zip(p, q))
    tangent = tuple((v+r/eccentricity)/math.sqrt(1-1/eccentricity**2) for v, r in zip(s, u))
    if abs(dot(u, s)+1/eccentricity) > 1e-12 or abs(math.hypot(*tangent)-1) > 1e-12:
        raise ValueError("periapsis/asymptote unit geometry failed")
    position = tuple(radius*v for v in u)
    parking = tuple(math.sqrt(mu/radius)*(-a*math.sin(phase)+b*math.cos(phase)) for a, b in zip(p, q))
    speed = math.sqrt(math.hypot(*excess)**2+2*mu/radius)
    velocity = tuple(speed*v for v in tangent)
    delta = tuple(a-b for a, b in zip(velocity, parking))
    position, parking, velocity, delta = (
        physical._finite_vector3_values(v, name)
        for v, name in ((position, "position"), (parking, "parking velocity"),
                        (velocity, "hyperbolic velocity"), (delta, "vector impulse")))
    # Reconstruct the conic from r,v, independently of the phase construction.
    h = physical._finite_vector3_values(cross(position, velocity), "angular momentum")
    ev = tuple(v/mu-r for v, r in zip(cross(velocity, h), u))
    actual_e = math.hypot(*ev)
    if actual_e <= 1:
        raise ValueError("reconstructed conic is not hyperbolic")
    eh, hh = _unit(ev), _unit(h)
    qh = cross(hh, eh)
    parameter = dot(h, h)/mu
    reconstructed_position = tuple(parameter/(1+actual_e)*v for v in eh)
    reconstructed_velocity = tuple(math.sqrt(mu/parameter)*(1+actual_e)*v for v in qh)
    energy = physical._finite_float("specific energy", dot(velocity, velocity)/2-mu/radius)
    if energy <= 0:
        raise ValueError("reconstructed energy must be positive")
    infinity_angle = math.acos(-1/actual_e)
    reconstructed_excess = tuple(math.sqrt(2*energy)*(math.cos(infinity_angle)*a+math.sin(infinity_angle)*b)
                                 for a, b in zip(eh, qh))
    position_error = math.dist(position, reconstructed_position)
    velocity_error = math.dist(velocity, reconstructed_velocity)
    asymptote_error = math.dist(excess, reconstructed_excess)
    radial = dot(velocity, u)
    energy_error = abs(energy-math.hypot(*excess)**2/2)
    diagnostics = (position_error, velocity_error, asymptote_error, radial, energy_error)
    for value in diagnostics:
        physical._finite_float("invariant residual", value)
    if (position_error > .001 or velocity_error > 1e-6 or asymptote_error > 1e-6
            or abs(radial) > 1e-6 or energy_error > 1e-10*max(mu/radius, math.hypot(*excess)**2/2)):
        raise ValueError("independent departure invariant check failed")
    dv = physical._positive_finite("vector impulse norm", math.hypot(*delta))
    durations = physical._seed_burn_durations_s("D13", spacecraft, dv, arrival_delta_v)
    exhaust = physical.STANDARD_GRAVITY_M_S2*spacecraft.isp_s
    after = spacecraft.initial_mass_kg*math.exp(-dv/exhaust)
    final = after*math.exp(-arrival_delta_v/exhaust)
    status = ("rejected-dry-mass" if final < spacecraft.dry_mass_kg else
              "rejected-window" if sum(durations) >= flight_time else "ideal-estimate-only")
    return _DepartureBranch(phase, math.remainder(phase-initial_phase, math.tau), position,
        parking, velocity, delta, dv, eccentricity, h, energy, *diagnostics, after, final,
        spacecraft.initial_mass_kg-after, after-final, *durations, status)


def _lunar_departure_reference(
    orbit: OrbitSpec, gravitational_parameter_m3_s2: float, parking_radius_m: float,
    excess_velocity_m_s: Vector3, epoch_tdb_s: float, *, phase_policy: str,
    spacecraft: SpacecraftSpec, provisional_arrival_delta_v_m_s: float, flight_time_s: float,
) -> _DepartureReference:
    """Enumerate a circular lunar seed; radius/mu/epoch/policy are explicit.

    Free phase varies the initial state at fixed epoch, not the original replay.
    Rejected mass/window estimates remain diagnostic, never propagation inputs.
    """
    try:
        if not isinstance(orbit, OrbitSpec) or not isinstance(spacecraft, SpacecraftSpec):
            raise ValueError("explicit OrbitSpec and SpacecraftSpec required")
        if orbit.central_body != "Moon" or orbit.eccentricity != 0 or orbit.periapsis_altitude_m != orbit.apoapsis_altitude_m:
            raise ValueError("only circular Moon parking orbits supported")
        if phase_policy not in ("fixed", "free"):
            raise ValueError("phase_policy must explicitly be fixed or free")
        for name in ("initial_mass_kg", "dry_mass_kg", "isp_s", "max_thrust_n"):
            physical._positive_finite(name, getattr(spacecraft, name))
        if spacecraft.initial_mass_kg <= spacecraft.dry_mass_kg:
            raise ValueError("initial mass must exceed dry mass")
        mu = physical._positive_finite("lunar mu", gravitational_parameter_m3_s2)
        radius = physical._positive_finite("parking radius", parking_radius_m)
        epoch = physical._finite_float("virtual periapsis epoch", epoch_tdb_s)
        excess = physical._finite_vector3_values(excess_velocity_m_s, "excess velocity")
        speed = physical._positive_finite("excess speed", math.hypot(*excess))
        arrival = physical._finite_float("provisional arrival delta-v", provisional_arrival_delta_v_m_s)
        flight_time = physical._positive_finite("flight time", flight_time_s)
        if arrival < 0:
            raise ValueError("provisional arrival delta-v must be nonnegative")
        for name in ("inclination_rad", "raan_rad", "argument_of_periapsis_rad", "true_anomaly_rad"):
            physical._finite_float(name, getattr(orbit, name))
        node, inclination = orbit.raan_rad, orbit.inclination_rad
        p = (math.cos(node), math.sin(node), 0.)
        q = (-math.sin(node)*math.cos(inclination), math.cos(node)*math.cos(inclination), math.sin(inclination))
        initial_phase = (orbit.argument_of_periapsis_rad+orbit.true_anomaly_rad) % math.tau
        eccentricity = physical._finite_float("hyperbolic eccentricity", 1+radius*speed**2/mu)
        if eccentricity <= 1:
            raise ValueError("hyperbolic eccentricity not representably above one")
        s = _unit(excess)
        a, b = physical._dot_product(p, s), physical._dot_product(q, s)
        projection = math.hypot(a, b)
        distance = projection-1/eccentricity
        status, phases = "constructed", ()
        if abs(distance) <= 1e-12:
            status = "near-degenerate-unresolved"
        elif distance < 0:
            status = "infeasible-plane"
        elif phase_policy == "fixed":
            if abs(a*math.cos(initial_phase)+b*math.sin(initial_phase)+1/eccentricity) > 1e-12:
                status = "infeasible-fixed-phase"
            else:
                phases = (initial_phase,)
        else:
            offset = math.acos(-1/(eccentricity*projection))
            centre = math.atan2(b, a)
            phases = tuple(sorted((centre+sign*offset) % math.tau for sign in (-1, 1)))
        branches = tuple(_branch(phi, initial_phase, p, q, s, excess, mu, radius,
            eccentricity, spacecraft, arrival, flight_time) for phi in phases)
        return _DepartureReference(status, phase_policy, epoch, mu, radius, excess, arrival, branches)
    except (ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
        raise TrajectoryRefinementError(f"D13 lunar-departure-geometry: {exc}") from exc
