"""Private ADR0137 native adapter; no reference execution on import."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable

BODIES = ("Sun", "Moon", "Earth")
GM = {"Sun": 1.327124400420322e20, "Moon": 4902800121846.8, "Earth": 398600435468295.9}
GUARDS = {"Sun": 696000000.0, "Moon": 1737400.0, "Earth": 6378136.6}
OFFSETS = (0.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0)
Check = Callable[[], None]


class NativeError(ValueError):
    """Fail without model substitution, changed profiles or retries."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NativeError(message)


def number(value: object) -> float:
    require(type(value) in (float, int), "finite nonboolean number required")
    try:
        result = float(value)
    except OverflowError as exc:
        raise NativeError("number outside binary64 range") from exc
    require(math.isfinite(result), "finite nonboolean number required")
    return result


def vector(value: object, size: int) -> tuple[float, ...]:
    require(
        isinstance(value, (list, tuple)) and len(value) == size,
        "state/vector shape mismatch",
    )
    return tuple(number(v) for v in value)


def selected(model: str) -> tuple[str, ...]:
    require(model in ("A", "B"), "model must be A or B")
    return BODIES[:2] if model == "A" else BODIES


@dataclass(frozen=True, slots=True)
class Prepared:
    """Private native handles; explicitly constructed sources, not a model certificate."""

    bodies: Any
    accelerations: Any
    included: tuple[str, ...]
    gravity_parameters_m3_s2: dict[str, float]


def validate_inventory(prepared: Prepared) -> None:
    require(
        prepared.bodies.global_frame_origin() == "SSB"
        and prepared.bodies.global_frame_orientation() == "J2000",
        "native frame mismatch",
    )
    models = prepared.accelerations
    require(
        set(models) == {"Spacecraft"}
        and set(models["Spacecraft"]) == set(prepared.included),
        "native force sources mismatch",
    )
    require(
        all(len(items) == 1 for items in models["Spacecraft"].values()),
        "native force counts mismatch",
    )
    for body, expected in prepared.gravity_parameters_m3_s2.items():
        actual = number(
            float(prepared.bodies.get(body).gravity_field_model.gravitational_parameter)
        )
        require(
            abs(actual - expected) <= 1e-15 * expected, f"native GM mismatch: {body}"
        )


def build_sources(
    sources: tuple[tuple[str, float, Any], ...],
    included: tuple[str, ...],
    check: Check,
) -> Prepared:
    """Low-level native construction also supports analytic fixture ephemeris settings.

    Only build_model supplies R5 inputs. This function installs no default bodies,
    rotation, harmonics, radiation, mass propagation or spacecraft gravity field.
    """
    check()
    names = tuple(row[0] for row in sources)
    require(
        len(set(names)) == len(names) and all(isinstance(n, str) and n for n in names),
        "source names",
    )
    require("Spacecraft" not in names and "SSB" not in names, "reserved source name")
    require(
        len(set(included)) == len(included) and set(included) <= set(names),
        "included sources",
    )
    parameters = {name: number(mu) for name, mu, _ in sources}
    require(all(mu > 0 for mu in parameters.values()), "positive native GM required")
    from tudatpy.dynamics import environment_setup, propagation_setup

    try:
        settings = environment_setup.BodyListSettings("SSB", "J2000")
        for body, mu, ephemeris in sources:
            require(
                ephemeris.frame_origin == "SSB"
                and ephemeris.frame_orientation == "J2000",
                "native ephemeris frame mismatch",
            )
            settings.add_empty_settings(body)
            settings.get(body).ephemeris_settings = ephemeris
            settings.get(
                body
            ).gravity_field_settings = environment_setup.gravity_field.central(mu)
        settings.add_empty_settings("Spacecraft")
        settings.get("Spacecraft").constant_mass = 2000.0
        bodies = environment_setup.create_system_of_bodies(settings)
        accelerations = propagation_setup.create_acceleration_models(
            bodies,
            {
                "Spacecraft": {
                    body: [propagation_setup.acceleration.point_mass_gravity()]
                    for body in included
                }
            },
            ["Spacecraft"],
            ["SSB"],
        )
        prepared = Prepared(bodies, accelerations, included, parameters)
        validate_inventory(prepared)
    except (
        Exception
    ) as exc:  # Untyped native construction boundary, including native readback.
        raise NativeError(f"native construction failed: {exc}") from exc
    check()
    return prepared


def build_model(model: str, check: Check) -> Prepared:
    """Frozen R5 direct geometric SPICE environment; existing pool only, no loading."""
    included = selected(model)
    check()
    from tudatpy.dynamics import environment_setup

    sources = []
    try:
        for body in BODIES:
            settings = environment_setup.ephemeris.direct_spice("SSB", "J2000", body)
            require(
                not settings.correct_for_light_time_aberration
                and not settings.correct_for_stellar_aberration
                and not settings.converge_light_time_aberration,
                "non-geometric native ephemeris",
            )
            sources.append((body, GM[body], settings))
    except Exception as exc:  # Untyped native settings boundary.
        raise NativeError(f"native SPICE settings failed: {exc}") from exc
    return build_sources(tuple(sources), included, check)


@dataclass(slots=True)
class Context:
    """Runner supplies the shared deadline; arc cap includes attempted failed calls."""

    check: Check
    arcs_attempted: int = 0
    arcs_returned: int = 0
    arcs_completed: int = 0
    last_returned: dict[str, Any] | None = None
    guard_reads_attempted: int = 0
    guard_reads_returned: int = 0
    last_guard_state: object | None = None
    minimum_checked_distances_m: dict[str, float] = field(default_factory=dict)


class ReturnedNativeFailure(NativeError):
    """Native histories returned before a deadline/validation failure."""

    def __init__(self, message: str, returned: dict[str, Any]) -> None:
        super().__init__(message)
        self.returned: dict[str, Any] = returned


def validate_history(
    returned: dict[str, Any],
    initial: tuple[float, ...],
    epoch_tdb_s: float,
    duration_s: float,
    step_s: float,
    offsets_s: tuple[float, ...],
    included: tuple[str, ...],
    check: Check,
    guard: Callable[[float, tuple[float, ...]], None],
) -> dict[str, Any]:
    """Read every retained state, require exact nodes and keep raw operands separately."""
    check()
    require(returned["integration_completed"] is True, "native integration incomplete")
    raw = returned["state_history"]
    require(isinstance(raw, dict), "native history must be a mapping")
    expected_count = int(duration_s / step_s) + 1
    require(len(raw) == expected_count, "native history count/profile mismatch")
    ordered = list(raw)
    require(ordered == sorted(ordered), "native history time order mismatch")
    require(
        ordered[0] == epoch_tdb_s
        and abs(ordered[-1] - (epoch_tdb_s + duration_s)) <= 1e-6,
        "native completion epoch mismatch",
    )
    states = {}
    forces = {}
    dependent = returned["dependent_variable_history"]
    require(isinstance(dependent, dict), "native force history must be a mapping")
    require(set(dependent) == set(raw), "native force-history epochs mismatch")
    for j, (at, value) in enumerate(raw.items()):
        check()
        epoch = number(float(at))
        require(epoch == epoch_tdb_s + j * step_s, "native fixed-step epoch mismatch")
        require(hasattr(value, "tolist"), "native state array required")
        state = vector(value.tolist(), 6)
        require(j != 0 or state == initial, "native initial-state reset")
        require(hasattr(dependent[at], "tolist"), "native force array required")
        force = vector(dependent[at].tolist(), 3 * (1 + len(included)))
        require(
            math.dist(
                force[:3],
                tuple(
                    math.fsum(force[3 + 3 * k + d] for k in range(len(included)))
                    for d in range(3)
                ),
            )
            <= 1e-12,
            "native total/source force mismatch",
        )
        guard(epoch, state)
        states[epoch] = state
        forces[epoch] = force
    nodes = tuple(epoch_tdb_s + s for s in offsets_s)
    require(all(t in states for t in nodes), "native exact sample epoch missing")
    check()
    return {
        "samples": [
            {"epoch_tdb_s": t, "state": states[t], "acceleration_m_s2": forces[t]}
            for t in nodes
        ],
        "retained_states": len(states),
        "guarded_states": len(states),
        "force_order": ("total",) + included,
        "step_s": step_s,
        "origin": "SSB",
        "orientation": "J2000",
        "position_units": "m",
        "velocity_units": "m/s",
        "time_units": "TDB seconds since J2000",
    }


def propagate(
    prepared: Prepared,
    initial: object,
    epoch_tdb_s: object,
    duration_s: object,
    step_s: object,
    offsets_s: tuple[float, ...],
    context: Context,
    guard: Callable[[float, tuple[float, ...]], None],
) -> dict[str, Any]:
    """Low-level RK4 component; fixtures may change geometry but solve_model cannot."""
    y0, epoch, duration, step = (
        vector(initial, 6),
        number(epoch_tdb_s),
        number(duration_s),
        number(step_s),
    )
    require(
        0 < duration <= 300
        and step in (1.0, 0.5)
        and duration / step == int(duration / step),
        "native profile mismatch",
    )
    offsets = vector(offsets_s, len(offsets_s))
    require(
        bool(offsets)
        and offsets[0] == 0
        and offsets[-1] == duration
        and all(a < b for a, b in zip(offsets, offsets[1:])),
        "native sample offsets mismatch",
    )
    require(
        epoch + step > epoch
        and epoch + duration > epoch
        and all(epoch + s != epoch for s in offsets[1:]),
        "native time resolution",
    )
    context.check()
    guard(epoch, y0)
    from tudatpy.dynamics import propagation_setup, simulator

    try:
        validate_inventory(prepared)
        integrator = propagation_setup.integrator.runge_kutta_fixed_step(
            step,
            propagation_setup.integrator.CoefficientSets.rk_4,
            assess_termination_on_minor_steps=False,
        )
        termination = propagation_setup.propagator.time_termination(
            epoch + duration, terminate_exactly_on_final_condition=True
        )
        output = [propagation_setup.dependent_variable.total_acceleration("Spacecraft")]
        output += [
            propagation_setup.dependent_variable.single_acceleration(
                propagation_setup.acceleration.point_mass_gravity_type,
                "Spacecraft",
                body,
            )
            for body in prepared.included
        ]
        settings = propagation_setup.propagator.translational(
            ["SSB"],
            prepared.accelerations,
            ["Spacecraft"],
            y0,
            epoch,
            integrator,
            termination,
            propagator=propagation_setup.propagator.cowell,
            output_variables=output,
        )
    except Exception as exc:  # Untyped native settings/readback boundary.
        raise NativeError(f"native propagation setup failed: {exc}") from exc
    context.check()
    require(context.arcs_attempted < 4, "native arc cap4")
    context.arcs_attempted += 1
    try:
        engine = simulator.create_dynamics_simulator(prepared.bodies, settings)
        raw = {
            "state_history": engine.state_history,
            "dependent_variable_history": engine.dependent_variable_history,
            "integration_completed": engine.integration_completed_successfully,
        }
    except Exception as exc:  # Untyped native integration/output boundary.
        raise NativeError(f"native integration failed: {exc}") from exc
    context.arcs_returned += 1
    context.last_returned = (
        raw  # Preserve before any after-call deadline/shape/finite gates.
    )
    try:
        result = validate_history(
            raw,
            y0,
            epoch,
            duration,
            step,
            offsets,
            prepared.included,
            context.check,
            guard,
        )
    except (NativeError, RuntimeError, ValueError) as exc:
        raise ReturnedNativeFailure(str(exc), raw) from exc
    context.arcs_completed += 1
    return result


def solve_model(
    initial: object, epoch_tdb_s: object, model: str, tighter: bool, context: Context
) -> dict[str, Any]:
    """Fresh fixed-model R5 arc; runner owns cross-engine ordering and identities."""
    require(type(tighter) is bool, "profile must be boolean")
    vector(initial, 6)
    number(epoch_tdb_s)
    prepared = build_model(model, context.check)

    def guard(at: float, state: tuple[float, ...]) -> None:
        for body in BODIES:
            context.check()
            context.guard_reads_attempted += 1
            try:
                raw = prepared.bodies.get(body).ephemeris.cartesian_state(at)
                context.guard_reads_returned += 1
                context.last_guard_state = raw
                position = vector(raw.reshape(-1).tolist(), 6)[:3]
            except Exception as exc:  # Untyped native ephemeris boundary.
                raise NativeError(
                    f"native guard ephemeris failed: {body} at {at}: {exc}"
                ) from exc
            context.check()
            distance = math.dist(state[:3], position)
            require(math.isfinite(distance), "native guard distance nonfinite")
            context.minimum_checked_distances_m[body] = min(
                distance, context.minimum_checked_distances_m.get(body, math.inf)
            )
            require(distance > GUARDS[body], f"{body} exclusion sphere")

    result = propagate(
        prepared,
        initial,
        epoch_tdb_s,
        300.0,
        0.5 if tighter else 1.0,
        OFFSETS,
        context,
        guard,
    )
    result.update(
        model=model,
        gravity_parameters_m3_s2=dict(prepared.gravity_parameters_m3_s2),
        minimum_checked_distances_m=dict(context.minimum_checked_distances_m),
    )
    return result
