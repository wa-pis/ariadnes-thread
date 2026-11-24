"""Private ADR0248 artificial shooting test; no ephemerides or mission model."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
import math
from numbers import Real
import time
from typing import Any

from .trajectory import (
    _build_tnw_basis,
    _direction_tnw_from_angles,
    _map_tnw_direction_to_inertial,
)

_INITIAL = (10000000.0, 0.0, 0.0, 0.0, 1000.0, 0.0, 2000.0)
_GRAVITY = (0.0, 0.1, 0.0)
_RATE = 1000.0 / (9.80665 * 450.0)
_ATOL = (1e-6, 1e-6, 1e-6, 1e-10, 1e-10, 1e-10, 1e-10)
_SCALES = (1000.0, 1000.0, 1000.0, 0.01, 0.01, 0.01) * 3
_X_SCALE = (0.1, 0.1, 100.0, 0.1, 0.1, 100.0) + (
    1000.0, 1000.0, 1000.0, 1.0, 1.0, 1.0,
) * 2
_SETTINGS = {
    "method": "trf", "jac": "2-point", "tr_solver": "exact", "loss": "linear",
    "ftol": 1e-12, "xtol": 1e-12, "gtol": 1e-12, "diff_step": None,
    "max_nfev": 20, "verbose": 0, "workers": None,
}


class BenchmarkError(RuntimeError):
    """Artificial qualification stopped; counts include attempted failed work."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.counts: dict[str, int] = {}


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise BenchmarkError(f"{label}: expected a finite number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise BenchmarkError(f"{label}: expected a finite number") from exc
    if not math.isfinite(result):
        raise BenchmarkError(f"{label}: expected a finite number")
    return result


def _vector(value: object, length: int, label: str) -> list[float]:
    if isinstance(value, (str, bytes, Mapping)):
        raise BenchmarkError(f"{label}: expected {length} numbers")
    try:
        values = list(value)  # type: ignore[arg-type]  # validated untyped boundary
    except TypeError as exc:
        raise BenchmarkError(f"{label}: expected {length} numbers") from exc
    if len(values) != length:
        raise BenchmarkError(f"{label}: expected {length} numbers")
    return [_number(item, label) for item in values]


@dataclass(slots=True)
class _Budget:
    deadline: float
    clock: Callable[[], float] = time.monotonic
    residual_calls: int = 0
    synthetic_arc_attempts: int = 0
    rhs_attempts: int = 0
    previous_time: float = -math.inf

    def check(self) -> None:
        now = _number(self.clock(), "monotonic clock")
        if now < self.previous_time:
            raise BenchmarkError("monotonic clock moved backwards")
        self.previous_time = now
        if now >= self.deadline:
            raise BenchmarkError("producer deadline reached")

    def charge(self, name: str) -> None:
        self.check()
        limits = {
            "residual_calls": 400,
            "synthetic_arc_attempts": 1206,
            "rhs_attempts": 1000000,
        }
        count = getattr(self, name)
        if count >= limits[name]:
            raise BenchmarkError(f"{name}: work limit reached")
        setattr(self, name, count + 1)

    def snapshot(self) -> dict[str, int]:
        return {
            "residual_calls": self.residual_calls,
            "synthetic_arc_attempts": self.synthetic_arc_attempts,
            "rhs_attempts": self.rhs_attempts,
            "native_propagations": 0, "spice_queries": 0,
            "kernel_reads": 0, "real_archive_reads": 0,
        }


def _reference(packet: Mapping[str, object]) -> tuple[dict[str, object], list[list[float]]]:
    try:
        encoded = json.dumps(dict(packet), allow_nan=False).encode("utf-8")
        copied = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise BenchmarkError("reference: finite JSON packet required") from exc
    if len(encoded) > 65536:
        raise BenchmarkError("reference exceeds 64 KiB")
    if (copied.get("schema"), copied.get("frame"), copied.get("time_scale")) != (
        "ariadna-coupled-reference-v1", "SYNTHETIC_INERTIAL", "elapsed_seconds",
    ):
        raise BenchmarkError("reference: wrong schema, frame or time scale")
    fixture = copied.get("fixture")
    expected = {
        "r0_m": list(_INITIAL[:3]), "v0_m_s": list(_INITIAL[3:6]),
        "initial_mass_kg": 2000.0, "dry_mass_kg": 500.0,
        "thrust_n": 1000.0, "isp_s": 450.0, "g0_m_s2": 9.80665,
        "gravity_m_s2": list(_GRAVITY), "start_s": 0.0, "final_s": 10000.0,
    }
    if not isinstance(fixture, dict) or fixture.keys() != expected.keys():
        raise BenchmarkError("reference.fixture: unexpected fields")
    for key, value in expected.items():
        actual = fixture[key]
        actual = _vector(actual, 3, key) if isinstance(value, list) else _number(actual, key)
        if actual != value:
            raise BenchmarkError(f"reference.fixture.{key}: changed frozen value")
    if _vector(copied.get("epochs_s"), 4, "reference.epochs_s") != [0, 1000, 9000, 10000]:
        raise BenchmarkError("reference.epochs_s: changed witness epochs")
    raw_states = copied.get("states")
    if not isinstance(raw_states, list) or len(raw_states) != 4:
        raise BenchmarkError("reference.states: expected four states")
    states = [_vector(row, 7, "reference.states") for row in raw_states]
    if states[0] != list(_INITIAL):
        raise BenchmarkError("reference.states: changed initial state")
    for epoch_s, state in zip((0, 1000, 9000, 10000), states, strict=True):
        duration_s = min(epoch_s, 1000) + max(0, epoch_s - 9000)
        if abs(state[6] - (2000 - _RATE * duration_s)) > 1e-9:
            raise BenchmarkError("reference.states: invalid mass ledger")
    precision = copied.get("precision_differences")
    if not isinstance(precision, dict):
        raise BenchmarkError("reference.precision_differences: required")
    for key, limit in (("position_m", 1e-9), ("velocity_m_s", 1e-12), ("mass_kg", 1e-15)):
        value = _number(precision.get(key), f"reference.precision_differences.{key}")
        if not 0 <= value <= limit:
            raise BenchmarkError("reference: independent precision agreement failed")
    relevance = copied.get("relevance")
    if not isinstance(relevance, dict):
        raise BenchmarkError("reference.relevance: required")
    gravity_speed = math.hypot(*_GRAVITY) * 10000.0
    initial_speed = math.hypot(*_INITIAL[3:6])
    consumed_mass = _RATE * 2000.0
    for key, expected_value in (
        ("gravity_speed_m_s", gravity_speed), ("initial_speed_m_s", initial_speed),
        ("consumed_mass_kg", consumed_mass), ("initial_mass_kg", _INITIAL[6]),
    ):
        if abs(_number(relevance.get(key), f"reference.relevance.{key}") - expected_value) > 1e-9:
            raise BenchmarkError("reference: relevance fixture mismatch")
    if gravity_speed < 0.5 * initial_speed or consumed_mass < 0.1 * _INITIAL[6]:
        raise BenchmarkError("reference: gravity or mass change is negligible")
    return copied, states


def _compare(actual: list[float], expected: list[float], position_m: float,
             velocity_m_s: float, label: str) -> None:
    if math.dist(actual[:3], expected[:3]) > position_m:
        raise BenchmarkError(f"{label}: position gate failed")
    if math.dist(actual[3:6], expected[3:6]) > velocity_m_s:
        raise BenchmarkError(f"{label}: velocity gate failed")
    if abs(actual[6] - expected[6]) > 1e-9:
        raise BenchmarkError(f"{label}: mass gate failed")


class _Problem:
    def __init__(self, budget: _Budget, states: list[list[float]],
                 integrator: Callable[..., Any]) -> None:
        self.budget = budget
        self.states = states
        self.integrator = integrator
        self.lower = [-0.1, -0.1, 500, -0.1, -0.1, 500]
        self.upper = [0.1, 0.1, 1500, 0.1, 0.1, 1500]
        for state in states[1:3]:
            extent = [1000000.0] * 3 + [500.0] * 3
            self.lower.extend(value - delta for value, delta in zip(state, extent))
            self.upper.extend(value + delta for value, delta in zip(state, extent))
        self.raw: list[float] = []
        self.starts: list[list[float]] = []
        self.ends: list[list[float]] = []

    def arc(self, initial: list[float], start_s: float, end_s: float,
            angles: tuple[float, float] | None) -> list[float]:
        self.budget.charge("synthetic_arc_attempts")
        initial = _vector(initial, 7, "arc initial state")
        start_s = _number(start_s, "arc start_s")
        end_s = _number(end_s, "arc end_s")
        if not 0 <= start_s < end_s <= 10000 or initial[6] < 500:
            raise BenchmarkError("arc: invalid epoch span or mass")
        rate = 0.0 if angles is None else _RATE
        direction_tnw = None if angles is None else _direction_tnw_from_angles(*angles)

        def rhs(epoch_s: float, raw_state: object) -> list[float]:
            self.budget.charge("rhs_attempts")
            state = _vector(raw_state, 7, "RHS state")
            epoch_s = _number(epoch_s, "RHS epoch_s")
            ledger = initial[6] - rate * (epoch_s - start_s)
            if not start_s - 1e-6 <= epoch_s <= end_s + 1e-6:
                raise BenchmarkError("RHS: epoch outside arc")
            if state[6] < 500 or abs(state[6] - ledger) > 1e-9:
                raise BenchmarkError("RHS: mass floor or integrated ledger failed")
            acceleration = list(_GRAVITY)
            if direction_tnw is not None:
                try:
                    basis = _build_tnw_basis(state[:3], state[3:6])
                    direction = _map_tnw_direction_to_inertial(basis, direction_tnw)
                except ValueError as exc:
                    raise BenchmarkError(f"RHS: invalid TNW: {exc}") from exc
                acceleration = [gravity + 1000.0 / state[6] * component
                                for gravity, component in zip(_GRAVITY, direction, strict=True)]
            return state[3:6] + acceleration + [-rate]

        try:
            result = self.integrator(
                rhs, (start_s, end_s), initial, method="DOP853", rtol=1e-12,
                atol=_ATOL, first_step=1.0, max_step=100.0, t_eval=[end_s],
            )
        except BenchmarkError:
            raise
        except (TypeError, ValueError, RuntimeError, FloatingPointError, OverflowError) as exc:
            raise BenchmarkError(f"arc integration: {exc}") from exc
        self.budget.check()
        if result.success is not True:
            raise BenchmarkError("arc: integration failed")
        epochs = _vector(result.t, 1, "arc returned epoch")
        if abs(epochs[0] - end_s) > 1e-6:
            raise BenchmarkError("arc: endpoint epoch mismatch")
        try:
            rows = list(result.y)
            if len(rows) != 7:
                raise BenchmarkError("arc: expected seven-state output")
            final = [_vector(row, 1, "arc returned state")[0] for row in rows]
        except TypeError as exc:
            raise BenchmarkError("arc: invalid state output") from exc
        ledger = initial[6] - rate * (end_s - start_s)
        if final[6] < 500 or abs(final[6] - ledger) > 1e-9:
            raise BenchmarkError("arc: final mass ledger failed")
        return final

    def controls(self, raw: object) -> list[float]:
        values = _vector(raw, 6, "controls")
        if any(not low <= value <= high for value, low, high in
               zip(values, self.lower[:6], self.upper[:6], strict=True)):
            raise BenchmarkError("controls: frozen bounds exceeded")
        return values

    def forward(self, raw: object) -> dict[str, object]:
        controls = self.controls(raw)
        az_d, el_d, duration_d, az_a, el_a, duration_a = controls
        epochs = [0.0, duration_d, 10000.0 - duration_a, 10000.0]
        states = [list(_INITIAL)]
        for index, angles in enumerate(((az_d, el_d), None, (az_a, el_a))):
            states.append(self.arc(states[-1], epochs[index], epochs[index + 1], angles))
        return {"epochs_s": epochs, "states": states}

    def residual(self, raw: object) -> list[float]:
        self.budget.charge("residual_calls")
        values = _vector(raw, 18, "shooting unknowns")
        if any(not low <= value <= high for value, low, high in
               zip(values, self.lower, self.upper, strict=True)):
            raise BenchmarkError("shooting unknowns: frozen bounds exceeded")
        az_d, el_d, duration_d, az_a, el_a, duration_a = values[:6]
        mass = 2000.0 - _RATE * duration_d
        epochs = [0.0, duration_d, 10000.0 - duration_a, 10000.0]
        starts = [list(_INITIAL), values[6:12] + [mass], values[12:18] + [mass]]
        targets = [values[6:12], values[12:18], self.states[3][:6]]
        ends = []
        for index, angles in enumerate(((az_d, el_d), None, (az_a, el_a))):
            ends.append(self.arc(starts[index], epochs[index], epochs[index + 1], angles))
        self.raw = [actual - desired for state, target in zip(ends, targets, strict=True)
                    for actual, desired in zip(state[:6], target, strict=True)]
        self.starts, self.ends = starts, ends
        return [value / scale for value, scale in zip(self.raw, _SCALES, strict=True)]


def _closed(defects: list[float]) -> bool:
    return all(math.hypot(*defects[index:index + 3]) <= 0.001 and
               math.hypot(*defects[index + 3:index + 6]) <= 1e-6
               for index in (0, 6, 12))


def run(reference: Mapping[str, object], *, deadline: float) -> dict[str, object]:
    """Recover an artificial command within the shared parent's monotonic deadline."""
    started = time.monotonic()
    budget = _Budget(min(_number(deadline, "deadline"), started + 210.0))
    try:
        budget.check()
        copied, states = _reference(reference)
        import numpy
        import scipy
        from scipy.integrate import solve_ivp
        from scipy.optimize import least_squares

        if numpy.__version__ != "1.26.4" or scipy.__version__ != "1.17.1":
            raise BenchmarkError("benchmark requires pinned NumPy 1.26.4/SciPy 1.17.1")
        problem = _Problem(budget, states, solve_ivp)
        witness = problem.forward([0, 0, 1000, 0, 0, 1000])
        for actual, expected in zip(witness["states"], states, strict=True):
            _compare(actual, expected, 0.001, 1e-6, "candidate witness")
        seed = [0.02, -0.01, 900.0, -0.02, 0.01, 1100.0]
        for state, offset in zip(states[1:3], (
            (1000, -1000, 500, 1, -1, 0.5),
            (-1000, 1000, -500, -1, 1, -0.5),
        ), strict=True):
            seed.extend(value + delta for value, delta in zip(state, offset))
        problem.residual(seed)
        initial_defects = list(problem.raw)
        if _closed(initial_defects):
            raise BenchmarkError("seed is already closed; recovery was not tested")
        result = least_squares(
            problem.residual, seed, bounds=(problem.lower, problem.upper),
            x_scale=_X_SCALE, **_SETTINGS,
        )
        # This extra counted evaluation checks the actual returned variables,
        # independently of the optimizer's cached/reported residual.
        problem.residual(result.x)
        unknowns = _vector(result.x, 18, "solver returned unknowns")
        defects = list(problem.raw)
        if not _closed(defects):
            raise BenchmarkError("recovered shooting defects exceed dimensioned gates")
        starts, ends = problem.starts, problem.ends
        if any(abs(ends[index][6] - starts[index + 1][6]) > 1e-9 for index in (0, 1)):
            raise BenchmarkError("recovered mass continuity failed")
        recovered = problem.forward(unknowns[:6])
        target = states[3][:6] + [2000.0 - _RATE * (unknowns[2] + unknowns[5])]
        _compare(recovered["states"][-1], target, 0.1, 1e-5, "unreset recovered target")
        budget.check()
        solver = dict(_SETTINGS)
        solver.update({
            "status": int(result.status), "success": bool(result.success),
            "message": str(result.message), "nfev": int(result.nfev),
            "njev": None if result.njev is None else int(result.njev),
            "integration_method": "DOP853", "rtol": 1e-12, "atol": list(_ATOL),
            "first_step_s": 1.0, "max_step_s": 100.0,
        })
        packet = {
            "schema": "ariadna-coupled-synthetic-v1", "frame": "SYNTHETIC_INERTIAL",
            "time_scale": "elapsed_seconds", "reference": copied,
            "controls": unknowns[:6], "shooting_nodes": [unknowns[6:12], unknowns[12:]],
            "initial_defects": initial_defects, "defects": defects,
            "arc_start_states": starts, "arc_end_states": ends,
            "witness": witness, "recovered": recovered, "counts": budget.snapshot(),
            "solver": solver, "status": "passed",
        }
        json.dumps(packet, allow_nan=False)
        return packet
    except BenchmarkError as exc:
        exc.counts = budget.snapshot()
        raise
