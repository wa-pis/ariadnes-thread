"""Independent, stdlib-only oracle for ADR0248's artificial finite-burn test."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, localcontext
import math
from time import monotonic
from typing import cast


class OracleError(ValueError):
    """The artificial reference or independent verification did not qualify."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.counts: dict[str, int] = {}


_LABELS = {"frame": "SYNTHETIC_INERTIAL", "time_scale": "elapsed_seconds"}
_FIXTURE: dict[str, object] = {
    "r0_m": [10000000.0, 0.0, 0.0], "v0_m_s": [0.0, 1000.0, 0.0],
    "initial_mass_kg": 2000.0, "dry_mass_kg": 500.0,
    "thrust_n": 1000.0, "isp_s": 450.0, "g0_m_s2": 9.80665,
    "gravity_m_s2": [0.0, 0.1, 0.0], "start_s": 0.0, "final_s": 10000.0,
}
_INITIAL = [10000000.0, 0.0, 0.0, 0.0, 1000.0, 0.0, 2000.0]
_WITNESS = [0.0, 0.0, 1000.0, 0.0, 0.0, 1000.0]
_RATE = 1000.0 / (9.80665 * 450.0)
_ZERO_ACCESS = ("native_propagations", "spice_queries", "kernel_reads", "real_archive_reads")
_REPORT_KEYS = {
    "schema", "frame", "time_scale", "reference", "controls", "shooting_nodes",
    "initial_defects", "defects", "arc_start_states", "arc_end_states", "witness",
    "recovered", "counts", "solver", "status",
}
_EVENT_LIMITS = {"position_m": 0.001, "velocity_m_s": 1e-6,
                 "mass_kg": 1e-9, "epoch_s": 1e-6}


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise OracleError(message)


def _number(value: object, field: str) -> float:
    _need(type(value) in (int, float), f"{field}: finite number required")
    try:
        result = float(cast(float, value))
    except OverflowError as exc:
        raise OracleError(f"{field}: finite number required") from exc
    _need(math.isfinite(result), f"{field}: finite number required")
    return result


def _mapping(value: object, field: str, keys: set[str] | None = None) -> Mapping[str, object]:
    _need(isinstance(value, Mapping), f"{field}: mapping required")
    result = cast(Mapping[str, object], value)
    _need(all(type(key) is str for key in result), f"{field}: string field names required")
    if keys is not None:
        _need(set(result) == keys, f"{field}: unexpected or missing fields")
    return result


def _vector(value: object, size: int, field: str) -> list[float]:
    _need(type(value) is list and len(cast(list[object], value)) == size,
          f"{field}: {size}-entry list required")
    return [_number(item, field) for item in cast(list[object], value)]


def _rows(value: object, count: int, size: int, field: str) -> list[list[float]]:
    _need(type(value) is list and len(cast(list[object], value)) == count,
          f"{field}: {count} rows required")
    return [_vector(row, size, field) for row in cast(list[object], value)]


def _same(actual: object, expected: object, field: str) -> None:
    """Bind the finite JSON packet, including field names and nonboolean numbers."""
    if isinstance(expected, Mapping):
        source = cast(Mapping[str, object], expected)
        target = _mapping(actual, field, set(source))
        for key, value in source.items():
            _same(target[key], value, f"{field}.{key}")
    elif type(expected) is list:
        source_list = cast(list[object], expected)
        _need(type(actual) is list and len(cast(list[object], actual)) == len(source_list),
              f"{field}: list identity mismatch")
        for index, value in enumerate(source_list):
            _same(cast(list[object], actual)[index], value, f"{field}[{index}]")
    elif type(expected) in (int, float):
        _need(_number(actual, field) == expected, f"{field}: value identity mismatch")
    else:
        _need(type(actual) is type(expected) and actual == expected, f"{field}: identity mismatch")


def _analytic(precision: int) -> list[list[Decimal]]:
    with localcontext() as context:
        context.prec = precision
        zero = Decimal(0)
        state = [Decimal("10000000"), zero, zero, zero, Decimal("1000"), zero, Decimal("2000")]
        rows = [state.copy()]
        exhaust = Decimal("9.80665") * Decimal("450")
        rate = Decimal("1000") / exhaust
        gravity = Decimal("0.1")
        for duration, burn in ((1000, True), (8000, False), (1000, True)):
            dt = Decimal(duration)
            before = state.copy()
            final_mass = before[6] - rate * dt if burn else before[6]
            logarithm = (before[6] / final_mass).ln() if burn else zero
            displacement = exhaust * (dt - final_mass / rate * logarithm) if burn else zero
            state[1] = before[1] + before[4] * dt + gravity * dt * dt / 2 + displacement
            state[4] = before[4] + gravity * dt + exhaust * logarithm
            state[6] = final_mass
            rows.append(state.copy())
        return rows


def reference() -> dict[str, object]:
    """Return the independent Decimal80/100 synthetic target in SI/elapsed seconds."""
    low, high = _analytic(80), _analytic(100)
    with localcontext() as context:
        context.prec = 100
        differences = {
            "position_m": max(sum((a[i] - b[i]) ** 2 for i in range(3)).sqrt()
                              for a, b in zip(low, high, strict=True)),
            "velocity_m_s": max(sum((a[i] - b[i]) ** 2 for i in range(3, 6)).sqrt()
                                for a, b in zip(low, high, strict=True)),
            "mass_kg": max(abs(a[6] - b[6]) for a, b in zip(low, high, strict=True)),
        }
        limits = {"position_m": Decimal("1e-9"), "velocity_m_s": Decimal("1e-12"),
                  "mass_kg": Decimal("1e-15")}
        _need(all(value <= limits[key] for key, value in differences.items()), "Decimal reference disagreement")
        consumed = float(high[0][6] - high[-1][6])
    gravity = _vector(_FIXTURE["gravity_m_s2"], 3, "fixture.gravity_m_s2")
    velocity = _vector(_FIXTURE["v0_m_s"], 3, "fixture.v0_m_s")
    elapsed = _number(_FIXTURE["final_s"], "final_s") - _number(_FIXTURE["start_s"], "start_s")
    gravity_speed, initial_speed = math.hypot(*gravity) * elapsed, math.hypot(*velocity)
    initial_mass = _number(_FIXTURE["initial_mass_kg"], "initial_mass_kg")
    _need(consumed >= 0.1 * initial_mass and gravity_speed >= 0.5 * initial_speed,
          "negligible witness effects")
    return {"schema": "ariadna-coupled-reference-v1", **_LABELS,
            "fixture": {key: value.copy() if isinstance(value, list) else value
                        for key, value in _FIXTURE.items()},
            "epochs_s": [0.0, 1000.0, 9000.0, 10000.0],
            "states": [[float(item) for item in row] for row in high],
            "precision_differences": {key: float(value) for key, value in differences.items()},
            "relevance": {"gravity_speed_m_s": gravity_speed, "initial_speed_m_s": initial_speed,
                          "consumed_mass_kg": consumed, "initial_mass_kg": initial_mass}}


@dataclass(slots=True)
class _Work:
    deadline: float
    rhs_attempts: int = 0
    synthetic_arc_attempts: int = 0

    def check(self) -> None:
        _need(monotonic() < self.deadline, "audit deadline exceeded")

    def rhs(self) -> None:
        self.check()
        _need(self.rhs_attempts < 300000, "audit RHS cap exceeded")
        self.rhs_attempts += 1

    def arc(self) -> None:
        self.check()
        _need(self.synthetic_arc_attempts < 12, "audit arc cap exceeded")
        self.synthetic_arc_attempts += 1


def _unit(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(item * item for item in vector))
    _need(math.isfinite(norm) and norm > 0.0, "degenerate TNW basis")
    return [item / norm for item in vector]


def _cross(left: list[float], right: list[float]) -> list[float]:
    return [left[1] * right[2] - left[2] * right[1],
            left[2] * right[0] - left[0] * right[2],
            left[0] * right[1] - left[1] * right[0]]


def _rhs(state: list[float], mass: float, burn: bool, azimuth: float,
         elevation: float, work: _Work) -> list[float]:
    work.rhs()
    _need(all(math.isfinite(value) for value in state) and math.isfinite(mass)
          and mass >= 500.0, "invalid RK stage state or mass")
    acceleration = [0.0, 0.1, 0.0]
    if burn:
        tangent = _unit(state[3:6])
        normal_w = _unit(_cross(state[:3], state[3:6]))
        normal_n = _cross(normal_w, tangent)
        components = (math.cos(elevation) * math.cos(azimuth),
                      math.cos(elevation) * math.sin(azimuth), math.sin(elevation))
        acceleration = [acceleration[i] + 1000.0 / mass * sum(
            factor * axis[i] for factor, axis in zip(components, (tangent, normal_n, normal_w), strict=True)
        ) for i in range(3)]
    return state[3:6] + acceleration


def _replay(controls: list[float], steps: int, work: _Work) -> list[list[float]]:
    """Integrate translation; stage masses follow an independently linear ledger."""
    state = _INITIAL[:6]
    rows = [_INITIAL.copy()]
    mass = 2000.0
    for duration, burn, azimuth, elevation in (
        (controls[2], True, controls[0], controls[1]),
        (10000.0 - controls[2] - controls[5], False, 0.0, 0.0),
        (controls[5], True, controls[3], controls[4]),
    ):
        work.arc()
        _need(duration > 0.0 and steps > 0, "invalid RK arc duration or mesh")
        step = duration / steps
        rate = _RATE if burn else 0.0
        for index in range(steps):
            start = duration * index / steps
            middle = duration * (index + 0.5) / steps
            end = duration * (index + 1) / steps
            k1 = _rhs(state, mass - rate * start, burn, azimuth, elevation, work)
            k2 = _rhs([x + step * k / 2 for x, k in zip(state, k1, strict=True)],
                      mass - rate * middle, burn, azimuth, elevation, work)
            k3 = _rhs([x + step * k / 2 for x, k in zip(state, k2, strict=True)],
                      mass - rate * middle, burn, azimuth, elevation, work)
            k4 = _rhs([x + step * k for x, k in zip(state, k3, strict=True)],
                      mass - rate * end, burn, azimuth, elevation, work)
            state = [x + step * (a + 2 * b + 2 * c + d) / 6
                     for x, a, b, c, d in zip(state, k1, k2, k3, k4, strict=True)]
        mass -= rate * duration
        _need(all(math.isfinite(value) for value in state), "nonfinite RK result")
        rows.append(state + [mass])
    return rows


def _errors(left: list[float], right: list[float], epoch_error: float = 0.0) -> dict[str, float]:
    return {"position_m": math.dist(left[:3], right[:3]),
            "velocity_m_s": math.dist(left[3:6], right[3:6]),
            "mass_kg": abs(left[6] - right[6]), "epoch_s": abs(epoch_error)}


def _accept(errors: Mapping[str, float], label: str, limits: Mapping[str, float] = _EVENT_LIMITS) -> None:
    _need(all(math.isfinite(value) and value <= limits[key] for key, value in errors.items()),
          f"{label}: dimensional gate failed ({dict(errors)})")


def _maximum(rows: list[dict[str, float]]) -> dict[str, float]:
    return {key: max(row[key] for row in rows) for key in _EVENT_LIMITS}


def _trajectory(value: object, field: str, epochs: list[float]) -> list[list[float]]:
    packet = _mapping(value, field, {"epochs_s", "states"})
    actual_epochs = _vector(packet["epochs_s"], 4, f"{field}.epochs_s")
    _need(all(abs(a - b) <= 1e-6 for a, b in zip(actual_epochs, epochs, strict=True)),
          f"{field}: event epoch mismatch")
    states = _rows(packet["states"], 4, 7, f"{field}.states")
    _same(states[0], _INITIAL, f"{field}.initial")
    _need(all(row[6] >= 500.0 for row in states), f"{field}: dry mass violation")
    return states


def _producer_counts(value: object) -> None:
    keys = {"residual_calls", "synthetic_arc_attempts", "rhs_attempts", *_ZERO_ACCESS}
    counts = _mapping(value, "counts", keys)
    limits = {"residual_calls": 400, "synthetic_arc_attempts": 1206, "rhs_attempts": 1000000,
              **dict.fromkeys(_ZERO_ACCESS, 0)}
    for key, limit in limits.items():
        _need(type(counts[key]) is int and 0 <= cast(int, counts[key]) <= limit,
              f"counts.{key}: invalid or exceeded cap")
    residuals = cast(int, counts["residual_calls"])
    arcs = cast(int, counts["synthetic_arc_attempts"])
    _need(residuals > 0 and arcs == 3 * residuals + 6
          and cast(int, counts["rhs_attempts"]) >= arcs, "incoherent producer counters")


def _solver(value: object) -> None:
    required: dict[str, object] = {"method": "trf", "jac": "2-point", "tr_solver": "exact",
                                   "loss": "linear", "max_nfev": 20,
                                   "ftol": 1e-12, "xtol": 1e-12, "gtol": 1e-12,
                                   "diff_step": None, "verbose": 0, "workers": None,
                                   "integration_method": "DOP853", "rtol": 1e-12,
                                   "atol": [1e-6] * 3 + [1e-10] * 4,
                                   "first_step_s": 1, "max_step_s": 100}
    packet = _mapping(value, "solver", set(required) | {"status", "success", "message", "nfev", "njev"})
    for key, expected in required.items():
        _same(packet[key], expected, f"solver.{key}")
    _need(type(packet["max_nfev"]) is int and type(packet["verbose"]) is int,
          "solver: integer settings required")
    _need(type(packet["status"]) is int and cast(int, packet["status"]) in (-1, 0, 1, 2, 3, 4)
          and type(packet["success"]) is bool and type(packet["message"]) is str,
          "solver: invalid termination metadata")
    _need(type(packet["nfev"]) is int and 1 <= cast(int, packet["nfev"]) <= 20,
          "solver.nfev: invalid count")
    _need(packet["njev"] is None or (type(packet["njev"]) is int
          and 1 <= cast(int, packet["njev"]) <= 20), "solver.njev: invalid count")


def audit(report: Mapping[str, object], *, deadline: float) -> dict[str, object]:
    """Independently check ADR0248's actual command; never replay its optimizer."""
    started = monotonic()
    work = _Work(min(_number(deadline, "deadline"), started + 60.0))
    try:
        return _audit(report, work)
    except OracleError as exc:
        exc.counts = _counts(work)
        raise


def _counts(work: _Work) -> dict[str, int]:
    return {"rhs_attempts": work.rhs_attempts,
            "synthetic_arc_attempts": work.synthetic_arc_attempts, "optimizer_calls": 0,
            **dict.fromkeys(_ZERO_ACCESS, 0)}


def _audit(report: Mapping[str, object], work: _Work) -> dict[str, object]:
    work.check()
    packet = _mapping(report, "report", _REPORT_KEYS)
    _same(packet["schema"], "ariadna-coupled-synthetic-v1", "schema")
    _same(packet["status"], "passed", "status")
    for key, value in _LABELS.items():
        _same(packet[key], value, key)
    ref = reference()
    work.check()
    _same(packet["reference"], ref, "reference")
    reference_states = _rows(ref["states"], 4, 7, "reference.states")
    _producer_counts(packet["counts"])
    _solver(packet["solver"])
    controls = _vector(packet["controls"], 6, "controls")
    for index, value in enumerate(controls):
        low, high = (500.0, 1500.0) if index in (2, 5) else (-0.1, 0.1)
        _need(low <= value <= high, "controls: outside benchmark domain")
    nodes = _rows(packet["shooting_nodes"], 2, 6, "shooting_nodes")
    for node, witness in zip(nodes, reference_states[1:3], strict=True):
        _need(all(abs(value - witness[i]) <= (1000000.0 if i < 3 else 500.0)
                  for i, value in enumerate(node)), "shooting node outside benchmark domain")
    initial = _vector(packet["initial_defects"], 18, "initial_defects")
    _need(any(math.hypot(*initial[i:i + 3]) > (0.001 if i % 6 == 0 else 1e-6)
              for i in range(0, 18, 3)), "initial defects already qualified")
    defects = _vector(packet["defects"], 18, "defects")
    starts = _rows(packet["arc_start_states"], 3, 7, "arc_start_states")
    ends = _rows(packet["arc_end_states"], 3, 7, "arc_end_states")
    m1 = 2000.0 - _RATE * controls[2]
    mf = m1 - _RATE * controls[5]
    epochs = [0.0, controls[2], 10000.0 - controls[5], 10000.0]
    expected_starts = [_INITIAL, nodes[0] + [m1], nodes[1] + [m1]]
    for actual, expected in zip(starts, expected_starts, strict=True):
        _same(actual, expected, "arc start binding")
    targets = [nodes[0], nodes[1], reference_states[-1][:6]]
    actual_defects = [a - b for end, target in zip(ends, targets, strict=True)
                      for a, b in zip(end[:6], target, strict=True)]
    _same(defects, actual_defects, "raw defect binding")
    shooting_errors = []
    for index, (end, target, mass) in enumerate(zip(ends, targets, (m1, m1, mf), strict=True)):
        errors = _errors(end, target + [mass])
        _accept(errors, f"shooting arc {index}")
        shooting_errors.append(errors)
    witness = _trajectory(packet["witness"], "witness", [0.0, 1000.0, 9000.0, 10000.0])
    recovered = _trajectory(packet["recovered"], "recovered", epochs)
    final_limits = _EVENT_LIMITS | {"position_m": 0.1, "velocity_m_s": 1e-5}
    primary_target = _errors(recovered[-1], reference_states[-1][:6] + [mf])
    _accept(primary_target, "candidate unreset target", final_limits)
    witness_errors = [_errors(a, b) for a, b in zip(witness, reference_states, strict=True)]
    for errors in witness_errors:
        _accept(errors, "candidate analytic witness")
    mesh_errors, cross_errors = [], []
    independent_target: dict[str, float] = {}
    for label, command, primary in (("witness", _WITNESS, witness), ("recovered", controls, recovered)):
        coarse = _replay(command, 4096, work)
        tight = _replay(command, 8192, work)
        for errors in [_errors(a, b) for a, b in zip(coarse, tight, strict=True)]:
            _accept(errors, f"{label} RK4 mesh agreement")
            mesh_errors.append(errors)
        for errors in [_errors(a, b) for a, b in zip(primary, tight, strict=True)]:
            _accept(errors, f"{label} candidate/RK4 agreement")
            cross_errors.append(errors)
        if label == "witness":
            for path in (coarse, tight):
                for actual, expected in zip(path, reference_states, strict=True):
                    errors = _errors(actual, expected)
                    _accept(errors, "RK4 analytic witness")
                    witness_errors.append(errors)
        else:
            independent_target = _errors(tight[-1], reference_states[-1][:6] + [mf])
            _accept(independent_target, "independent unreset target", final_limits)
    work.check()
    _need(work.rhs_attempts == 294912 and work.synthetic_arc_attempts == 12,
          "incomplete independent replay inventory")
    return {"schema": "ariadna-coupled-audit-v1", **_LABELS, "status": "passed",
            "controls": controls, "counts": _counts(work),
            "max_errors": {"witness": _maximum(witness_errors), "shooting": _maximum(shooting_errors),
                           "mesh": _maximum(mesh_errors), "candidate_rk4": _maximum(cross_errors),
                           "candidate_target": primary_target, "independent_target": independent_target},
            "scope": "artificial numerical diagnostics; no certified physical error bound"}
