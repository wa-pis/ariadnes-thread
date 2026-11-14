"""Independently check native B histories and telemetry on captured SI operands."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, localcontext
import math
from typing import Any

BODIES = ("Sun", "Moon", "Earth")
ORDER = ("normal", "tighter")
OFFSETS = (0., 50., 100., 150., 200., 250., 300.)
FORCE_ORDER = ["total", *BODIES]
LABELS = {"origin": "SSB", "orientation": "J2000", "position_units": "m",
          "velocity_units": "m/s", "time_units": "TDB seconds since J2000"}
type Row = dict[str, Any]
type Check = Callable[[], None]
type Event = Callable[[str, str], None]
type Vector = tuple[float, ...]
type DecimalVector = tuple[Decimal, ...]


class TelemetryFailure(ValueError):
    """An independently reconstructed telemetry check missed its bound."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def number(raw: object) -> float:
    require(type(raw) in (float, int), "finite nonboolean native number required")
    try:
        value = float(raw)
    except OverflowError as exc:
        raise ValueError("native number outside binary64") from exc
    require(math.isfinite(value), "finite native number required")
    return value


def vector(raw: object, size: int) -> Vector:
    require(isinstance(raw, (tuple, list)) and len(raw) == size, "native vector shape")
    return tuple(number(v) for v in raw)


def same_words(a: object, b: object, size: int) -> bool:
    return tuple(v.hex() for v in vector(a, size)) == tuple(v.hex() for v in vector(b, size))


def idle() -> None:
    pass


def no_event(_operation: str, _phase: str) -> None:
    pass


def telemetry(
    state: Vector, force: Vector, positions: list[Vector], gm_m3_s2: Row, event: Event,
) -> None:
    """Check base-10 point gravity and per-source/total telemetry at an exact node."""
    event("native_telemetry", "attempt")

    def norm(values: DecimalVector) -> Decimal:
        return sum((v*v for v in values), Decimal()).sqrt()

    def field(pos: Vector, gm: float) -> DecimalVector:
        delta = tuple(Decimal.from_float(y)-Decimal.from_float(x)
                      for x, y in zip(state[:3], pos, strict=True))
        squared = sum((v*v for v in delta), Decimal())
        require(squared > 0 and gm > 0, "native reference field domain")
        denom = squared*squared.sqrt()
        return tuple(Decimal.from_float(gm)*v/denom for v in delta)

    tables: dict[int, list[DecimalVector]] = {}
    for digits in (80, 100):
        with localcontext() as ctx:
            ctx.prec = digits
            values = []
            for body, pos in zip(BODIES, positions, strict=True):
                event("native_reference_fields", "attempt")
                values.append(field(pos, number(gm_m3_s2[body])))
                event("native_reference_fields", "complete")
            total = tuple(sum((value[j] for value in values), Decimal()) for j in range(3))
            tables[digits] = [total, *values]
            scales = [sum((norm(v) for v in values), Decimal()), *map(norm, values)]
            for i, (reference, scale) in enumerate(zip(tables[digits], scales, strict=True)):
                measured = force[3*i:3*i+3]
                error = norm(tuple(Decimal.from_float(f)-r
                                   for f, r in zip(measured, reference, strict=True)))
                if error > max(Decimal("1e-15"), Decimal("1e-11")*scale):
                    raise TelemetryFailure(f"native {FORCE_ORDER[i]} telemetry envelope at {digits} digits")
    with localcontext() as ctx:
        ctx.prec = 100
        for a, b in zip(tables[80], tables[100], strict=True):
            if norm(tuple(y-x for x, y in zip(a, b, strict=True))) > Decimal("1e-60")*norm(b):
                raise TelemetryFailure("native telemetry precision stability")
    event("native_telemetry", "complete")


def steps(profile: Row, t0: float, step_s: float, initial: Vector, *, complete: bool,
          check: Check) -> tuple[list[Vector], list[Vector]]:
    raw = profile["raw_returned"]
    require(type(raw["integration_completed"]) is bool, "native integration completion type")
    if complete:
        require(raw["integration_completed"], "native integration incomplete")
    count = int(300/step_s)+1
    history, forces = raw["state_history"], raw["dependent_variable_history"]
    require(type(history) is dict and type(forces) is dict and len(history) <= count
            and len(forces) <= count, "native raw grid shape/cap")
    epochs = [t0 + j*step_s for j in range(count)]
    state_keys = [float(k) for k in history]
    force_keys = [float(k) for k in forces]
    require(state_keys == epochs[:len(history)] and force_keys == epochs[:len(forces)],
            "native returned grid/order")
    if complete:
        require(len(history) == len(forces) == count, "native grid incomplete")
    states = []
    for j, value in enumerate(history.values()):
        check()
        state = vector(value, 6)
        require(j != 0 or same_words(state, initial, 6), "native exact initial state")
        states.append(state)
    accelerations = []
    for force in forces.values():
        check()
        values = vector(force, 12)
        summed = tuple(math.fsum(values[j+i] for i in (3, 6, 9)) for j in range(3))
        require(math.dist(values[:3], summed) <= 1e-12, "native total/source consistency")
        accelerations.append(values)
    return states, accelerations


def replay_profile(profile: Row, bundle: Row, *, check: Check, event: Event) -> list[Row] | None:
    """Check one archived profile; return only validated complete sample rows."""
    check()
    name = profile["name"]
    require(name in ORDER, "unknown native B profile")
    step_s = 1. if name == "normal" else .5
    require(number(profile["step_s"]) == step_s, "native step profile")
    require(tuple(bundle["offsets_s"]) == OFFSETS, "native time contract")
    t0 = number(bundle["initial"]["epoch_tdb_s"])
    initial = vector(bundle["initial"]["position_m"]+bundle["initial"]["velocity_m_s"], 6)
    radii, gm = (bundle[k] for k in ("radii_m", "gm_m3_s2"))
    arc = profile["arc"]
    require(set(arc) == {"attempted", "returned", "completed"} and all(
        type(v) is int and 0 <= v <= 1 for v in arc.values()),
        "native arc count shape")
    attempted, returned, completed = (arc[k] for k in ("attempted", "returned", "completed"))
    require(completed <= returned <= attempted
            and bool(returned) == ("raw_returned" in profile)
            and bool(completed) == ("result" in profile), "native arc phase order")
    reads = profile["guards"]
    require(type(reads) is list and len(reads) <= 3*(2+int(300/step_s)),
            "native guard evidence cap")
    if "inventory" not in profile:
        require(attempted == 0 and not reads, "native work without inventory")
        return None
    inv = profile["inventory"]
    require((inv["model"], inv["origin"], inv["orientation"], inv["aberration"])
            == ("B", "SSB", "J2000", "NONE") and inv["force_order"] == FORCE_ORDER
            and set(inv["force_counts"]) == set(inv["gm_m3_s2"]) == set(BODIES)
            and all(type(x) is int and x == 1 for x in inv["force_counts"].values()),
            "native model/force inventory")
    for body in BODIES:
        expected = number(gm[body])
        require(expected > 0 and abs(number(inv["gm_m3_s2"][body])-expected) <= 1e-15*expected,
                f"native inventory GM: {body}")

    states, forces = steps(profile, t0, step_s, initial, complete=bool(completed),
                           check=check) if returned else ([], [])
    require(not attempted or (len(reads) >= 3 and all(r.get("passed") is True for r in reads[:3])),
            "native simulator attempt before preflight guards")
    require(returned or len(reads) <= 3, "native retained-state guards before simulator return")

    positions: list[Vector] = []
    for idx, row in enumerate(reads):
        check()
        group, j = divmod(idx, 3)
        body = BODIES[j]
        require(row["body"] == body and type(row["group"]) is int and row["group"] == group
                and number(row["epoch_tdb_s"]) == t0+max(0, group-1)*step_s,
                "native guard sequence")
        state = initial if group == 0 else states[group-1]
        last = idx == len(reads)-1
        if "state_si" not in row:
            require(not completed and last and "distance_m" not in row and "passed" not in row,
                    "native guard return missing")
            break
        point = vector(row["state_si"], 6)[:3]
        positions.append(point)
        if "distance_m" not in row:
            require(not completed and last and "passed" not in row, "native guard result missing")
            break
        distance = math.dist(state[:3], point)
        radius = number(radii[body])
        passed = math.isfinite(distance) and distance > radius > 0
        require(distance == number(row["distance_m"]) and row["passed"] is passed
                and (passed or (not completed and last)), "native exterior guard mismatch")
    if not completed:
        return None
    require(len(positions) == len(reads) == 3*(len(states)+1), "native guard coverage")

    result = profile["result"]
    require(all(result[k] == value for k, value in LABELS.items())
            and result["force_order"] == FORCE_ORDER and number(result["step_s"]) == step_s
            and type(result["retained_states"]) is int and result["retained_states"] == len(states)
            and type(result["guarded_states"]) is int and result["guarded_states"] == len(states),
            "native result metadata")
    samples = result["samples"]
    require(isinstance(samples, list) and len(samples) == 7, "native exact sample count")
    for sample, offset in zip(samples, OFFSETS, strict=True):
        check()
        index = int(offset/step_s)
        state, force = states[index], forces[index]
        require(number(sample["epoch_tdb_s"]) == t0+offset
                and same_words(sample["state"], state, 6)
                and same_words(sample["acceleration_m_s2"], force, 12),
                "native sample differs from raw history")
        # Group zero is preflight; consume the actual retained-state read at t0 too.
        start = 3*(index+1)
        telemetry(state, force, positions[start:start+3], gm, event)
    return samples


def replay(
    profiles: list[Row], bundle: Row, *, check: Check = idle,
    event: Event = no_event, complete: bool = True,
    expected_telemetry_failure: tuple[str, str] | None = None,
) -> dict[str, list[Row]]:
    """Verify the retained normal/tighter B profiles, or a bounded failed prefix."""
    require(type(profiles) is list and len(profiles) <= 2, "native profile cap")
    result = {}
    for name, profile in zip(ORDER, profiles):
        require(profile["name"] == name and len(result) == ORDER.index(name), "native profile order")
        try:
            profile_samples = replay_profile(profile, bundle, check=check, event=event)
        except TelemetryFailure as exc:
            require(not complete and profile is profiles[-1]
                    and expected_telemetry_failure == (name, str(exc)),
                    "unrecognized native telemetry failure: " + str(exc))
            return result
        if profile_samples is not None:
            result[name] = profile_samples
    require(expected_telemetry_failure is None, "declared native telemetry failure did not recur")
    require(not complete or len(result) == 2, "native study incomplete")
    return result
