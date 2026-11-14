"""ADR0196 synthetic capacity inputs and adapters; never call SPICE or a solver."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import importlib.util
import math
from pathlib import Path
import sys
from time import monotonic
from types import ModuleType, SimpleNamespace
from typing import Any, Protocol

HERE = Path(__file__).resolve().parent
DURATION_S = 16_000.
OFFSETS = tuple(float(s) for s in range(0, 16_001, 50))
BODIES = ("Sun", "Moon", "Earth")
MARKER_M = 18_374_000.
START_TDB_S = 978998965.9635216
MID_TDB_S = START_TDB_S
RADIUS_S = float(2**18)
MASS_KG = 1351.7475727997967
GM = {"Sun": 8.7e16, "Moon": 2.3e7, "Earth": 5.1e9}
type Row = dict[str, Any]
type Vector = tuple[float, ...]
type Check = Callable[[], None]


class Writer(Protocol):
    def append(self, kind: str, row: Row) -> None: ...


def _coefficients(centre: Vector, degree: int, seed: int) -> list[list[float]]:
    # Dyadic perturbations: genuine SPK degree, bounded acceleration and
    # reproducible source cancellation at an SSB-scale position.
    return [
        [v, *(math.ldexp(float((seed * k + 13 * j) % 31 - 15), 4 - k)
              for k in range(1, degree + 1))]
        for j, v in enumerate(centre)
    ]


SUN = _coefficients((462_178.25, -312_889.125, 72_896.75), 10, 4)
EARTH = _coefficients((-47_123_456.25, 128_296_813.5, 55_953_993.875), 12, 9)
MOON_EARTH = _coefficients((28_452.125, 181_497.75, 315_461.375), 12, 15)
RECORDS = {(10, 0): SUN, (399, 0): EARTH, (301, 399): MOON_EARTH}


def _value(coefficients: list[list[float]], at_tdb_s: float) -> list[float]:
    # Binary64 Chebyshev evaluation independent of exact Fraction replay.
    u = (at_tdb_s - MID_TDB_S) / RADIUS_S
    basis, rate = [1., u], [0., 1.]
    for _ in range(2, len(coefficients[0])):
        rate.append(2*basis[-1] + 2*u*rate[-1] - rate[-2])
        basis.append(2*u*basis[-1] - basis[-2])
    positions = [math.fsum(c * f for c, f in zip(block, basis, strict=True)) for block in coefficients]
    speeds = [math.fsum(c * f for c, f in zip(block, rate, strict=True)) / RADIUS_S for block in coefficients]
    return positions + speeds


def provider(body: str, epoch: float, frame: str, aberration: str, observer: str) -> list[float]:
    """Return varied generated positions and velocities in km and km/s."""
    if (frame, aberration) != ("J2000", "NONE"):
        raise ValueError("synthetic state frame or aberration")
    if body == "Moon" and observer == "SSB":
        return [a+b for a, b in zip(_value(EARTH, epoch), _value(MOON_EARTH, epoch), strict=True)]
    choices = {("Sun", "SSB"): SUN, ("Earth", "SSB"): EARTH, ("Moon", "Earth"): MOON_EARTH}
    return _value(choices[(body, observer)], epoch)


def _body_si(body: str, epoch: float) -> list[float]:
    return [x*1000. for x in provider(body, epoch, "J2000", "NONE", "SSB")]


def bundle(*, outcome: str = "positive") -> Row:
    """Generate an independent artificial input bundle with the fixed far interval."""
    try:
        range_m, radial_m_s = {
            "positive": (3_497_227.25, 1217.123456789),
            "no-crossing": (3_497_227.25, 115.125),
            "inward": (MARKER_M + 1_100_000.125, -950.123456789),
            "equality": (MARKER_M, 150.125),
            "guard-failure": (3_497_227.25, 1217.123456789),
            "telemetry-failure": (3_497_227.25, 1217.123456789),
        }[outcome]
    except KeyError as exc:
        raise ValueError("unknown synthetic outcome") from exc
    moon = _body_si("Moon", START_TDB_S)
    launch_delta_m = [range_m, 0., 0.] if outcome == "equality" else [range_m, -1234.25, 999.125]
    launch_delta_m_s = [radial_m_s, 53.7654321, -78.23456789]
    templates: dict[str, Row] = {}
    for body, chain in (("Sun", ((10, 0),)), ("Moon", ((301, 399), (399, 0))), ("Earth", ((399, 0),))):
        templates[body] = {"body": body, "segments": [
            {"body": b, "centre": c, "frame": 1, "type": 2,
             "first_tdb_s": MID_TDB_S-RADIUS_S, "last_tdb_s": MID_TDB_S+RADIUS_S,
             "words": [MID_TDB_S, RADIUS_S, *sum(RECORDS[(b, c)], [])]}
            for b, c in chain
        ]}
    return {
        "initial": {"epoch_tdb_s": START_TDB_S,
                    "position_m": [a+b for a, b in zip(moon[:3], launch_delta_m, strict=True)],
                    "velocity_m_s": [a+b for a, b in zip(moon[3:], launch_delta_m_s, strict=True)]},
        "offsets_s": list(OFFSETS),
        "mass_kg": MASS_KG, "marker_radius_m": MARKER_M, "restart_moon_state_si": moon,
        "gm_m3_s2": dict(GM),
        "radii_m": {"Sun": 6.9e8, "Moon": 4e6 if outcome == "guard-failure" else 1_737_400.,
                    "Earth": 6_400_000.},
        "source_rows_template": templates,
        "coast": {"constant_mass_metadata_kg": MASS_KG, "thrust_n": 0., "mass_flow_kg_s": 0.,
                  "candidate": "synthetic-capacity-fixture"},
        "adapter_mode": "synthetic",
    }


class _Array:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def tolist(self) -> list[Any]:
        return self._values


def _correction(elapsed_s: float) -> list[float]:
    # Bounded smooth artificial q and w with distinct nonzero components; the
    # prescribed path is a test operand, not a dynamical solution.
    amplitudes = (2.3456789e-9, -1.23456789e-9, 3.456789e-9)
    return ([v * elapsed_s**2 for v in amplitudes] + [2*v*elapsed_s for v in amplitudes]
            if elapsed_s else [0.]*6)


def _state(si: Vector, offset_s: float) -> list[float]:
    q = _correction(offset_s)
    return [math.fsum((si[j], si[j+3]*offset_s, q[j])) for j in range(3)] + [
        math.fsum((si[j], q[j])) for j in range(3, 6)
    ]


def _native_adapter(frozen: ModuleType, inputs: Row, outcome: str) -> ModuleType:
    # Reuse the frozen raw-history and inventory validation on generated returns.
    gm, radii = inputs["gm_m3_s2"], inputs["radii_m"]
    frozen.GM, frozen.GUARDS = gm, radii
    prepared = SimpleNamespace(
        model="B", included=BODIES, gravity_parameters_m3_s2=gm,
        accelerations={"Spacecraft": {b: [object()] for b in BODIES}},
        bodies=SimpleNamespace(
            global_frame_origin=lambda: "SSB", global_frame_orientation=lambda: "J2000",
            get=lambda body: SimpleNamespace(
                gravity_field_model=SimpleNamespace(gravitational_parameter=gm[body]),
                ephemeris=SimpleNamespace(cartesian_state=lambda at: _body_si(body, at)),
            ),
        ),
    )

    def build(model: str, check: Check) -> Any:
        if model != "B":
            raise ValueError("only artificial model B")
        check()
        return prepared

    def propagate(handle: Any, initial: Vector, at: float, length: float, step: float,
                  offsets: tuple[float, ...], context: Any,
                  guard: Callable[[float, Vector], None]) -> Row:
        if handle is not prepared or at != START_TDB_S or length != DURATION_S or offsets != OFFSETS:
            raise ValueError("synthetic native path grid")
        guard(at, initial)
        context.arcs_attempted += 1
        states, forces = {}, {}
        for j in range(int(length / step) + 1):
            context.check()
            elapsed = j * step
            epoch = at + elapsed
            state = _state(initial, elapsed)
            fields = []
            for body in BODIES:
                displacement = [a-b for a, b in zip(_body_si(body, epoch)[:3], state[:3], strict=True)]
                distance_m = math.hypot(*displacement)
                fields.append([gm[body]*x/distance_m**3 for x in displacement])
            if outcome == "telemetry-failure" and j == 0:
                fields[0][0] += 1e-3
            states[epoch], forces[epoch] = _Array(state), _Array(
                [math.fsum(c) for c in zip(*fields, strict=True)] + sum(fields, []))
        raw = {"state_history": states, "dependent_variable_history": forces, "integration_completed": True}
        context.arcs_returned += 1
        context.last_returned = raw
        result = frozen.validate_history(raw, initial, at, length, step, offsets,
                                         handle.included, context.check, guard)
        context.arcs_completed += 1
        return result

    frozen.build_model, frozen.propagate = build, propagate
    return frozen


class _ScriptedController:
    """Emit DOP853-shaped synthetic callbacks without calling an integrator."""

    n_stages = 12

    def __init__(self, rhs: Callable[[float, _Array], list[float]], max_step: float, first_step: float,
                 atol: list[float], rtol: float, rejects: int) -> None:
        self.atol, self.rtol = atol, rtol
        self.max_step, self.first_step = max_step, first_step
        self.rejects = rejects
        self.t, self.y, self.status, self.nfev = 0., _Array([0.]*6), "running", 0.

        def fun(elapsed_s: float, y: _Array) -> list[float]:
            self.nfev += 1
            return rhs(elapsed_s, y)

        self.fun = fun
        self.fun(0., self.y)

    def _estimate_error_norm(self, error: float, _h: float, _scale: _Array) -> float:
        return error

    def _step_impl(self) -> tuple[bool, None]:
        width = min(self.first_step if not self.t else self.max_step, DURATION_S-self.t)
        widths = ((width, 1.2), (width*.875, .17)) if self.rejects else ((width, .17),)
        self.rejects = max(0, self.rejects - 1)
        for attempted_width, error in widths:
            end = self.t + attempted_width
            h_s = end-self.t
            # Use non-dyadic stages so early observations and later windows
            # exercise rounded high epochs, signed low parts and polynomial work.
            for stage in range(1, 13):
                at = end if stage == 12 else self.t + h_s*stage/13.
                y = _Array(_correction(at))
                self.fun(at, y)
            scale = [atol+max(abs(a), abs(b))*self.rtol for atol, a, b in
                     zip(self.atol, self.y.tolist(), y.tolist(), strict=True)]
            if self._estimate_error_norm(error, h_s, _Array(scale)) < 1.:
                self.t, self.y = end, y
                return True, None
        raise AssertionError("script contains no accepted trial")

    def step(self) -> None:
        self._step_impl()
        if self.t == DURATION_S:
            self.status = "finished"


def _solve(full_cap: bool) -> Callable[..., Any]:
    def solve(rhs: Callable[[float, _Array], list[float]], interval: tuple[float, float],
              initial: list[float], *, method: type, t_eval: Iterable[float],
              rtol: float, atol: list[float], max_step: float, first_step: float) -> Any:
        times = list(t_eval)
        if interval != (0., DURATION_S) or initial != [0.]*6 or times != list(OFFSETS):
            raise ValueError("synthetic adaptive path grid")
        # 9,980 accepted (including the reduced-width steps) and 3,020
        # rejected: 13,000 complete trials across the two full-cap profiles.
        rejects = (1000 if max_step == 5. else 2020) if full_cap else (3 if max_step == 5. else 2)
        solver = method(rhs, max_step, first_step, atol, rtol, rejects)
        tick, columns = 0, [[] for _ in initial]
        while solver.status == "running":
            before = solver.t
            solver.step()
            if tick < len(times) and times[tick] <= solver.t:
                for c in (.1, .2, .7777777777777778):
                    s = before + c*(solver.t - before)
                    solver.fun(s, _Array(_correction(s)))
                while tick < len(times) and times[tick] <= solver.t:
                    for col, value in zip(columns, _correction(times[tick]), strict=True):
                        col.append(value)
                    tick += 1
        if tick != len(times):
            raise ValueError("incomplete synthetic dense output grid")
        return SimpleNamespace(success=True, status=0, message="scripted artificial path", nfev=solver.nfev,
                               t=_Array(times), y=_Array(columns))

    return solve


def _load_study() -> ModuleType:
    path = HERE / "0197-far-study.py"
    spec = importlib.util.spec_from_file_location("r550_fixture_study", path)
    if spec is None or spec.loader is None:
        raise ValueError("synthetic study loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def produce(writer: Writer, *, full_cap: bool = False, outcome: str = "positive",
            budget: Any = None) -> Row:
    """Produce through the real study arithmetic and stream only artificial data."""
    study = _load_study()
    inputs = bundle(outcome=outcome)
    if budget is None:
        budget = study.new_budget(monotonic, monotonic())

    class CapacityWriter:
        def __init__(self) -> None:
            self.rhs = 0

        def append(self, kind: str, row: Row) -> None:
            if kind == "rhs":
                self.rhs += 1
            if full_cap and kind == "study_summary":
                if self.rhs != 157_928:
                    raise ValueError("synthetic complete-profile RHS cadence")
                for i in range(160_000 - self.rhs):
                    offset_s = 31_247.*(i + .43123456789) % DURATION_S
                    payload = {"profile": "capacity", "index": i, "global_index": self.rhs + i,
                               "usage": "capacity-only"}
                    study.build_rhs(inputs, provider, budget, payload, offset_s, _correction(offset_s))
                    writer.append("capacity_rhs", payload)
                row["counts"] = budget.counts
            writer.append(kind, row)

    adapter = _native_adapter(study.NATIVE.load_adapter(), inputs, outcome)
    return study.run(inputs, CapacityWriter(), budget, provider, adapter, solve=_solve(full_cap),
                     base_solver=_ScriptedController)
