"""Independently check 600 s native B histories and raw telemetry operands."""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

BODIES = ("Sun", "Moon", "Earth")
ORDER = ("normal", "tighter")
OFFSETS = tuple(float(s) for s in range(0, 601, 50))
FORCE_ORDER = ["total", *BODIES]
LABELS = {"origin": "SSB", "orientation": "J2000", "position_units": "m",
          "velocity_units": "m/s", "time_units": "TDB seconds since J2000"}
type Row = dict[str, Any]
type Check = Callable[[], None]
type Event = Callable[[str, str], None]
type Vector = tuple[float, ...]


def _reference() -> ModuleType:
    path = Path(__file__).resolve().with_name("0183-earth-native-replay.py")
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != "3ddff9eb6b4ee320aae9cd8dddc89f5f9dbe82bbcea3758dad1d17f3e396eba6":
        raise ValueError("immutable native Decimal replay digest")
    module = ModuleType("r539_prior_native_telemetry")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


_PRIMITIVES = _reference()
require, number, vector, same_words = (_PRIMITIVES.require, _PRIMITIVES.number,
                                       _PRIMITIVES.vector, _PRIMITIVES.same_words)
idle, no_event = _PRIMITIVES.idle, _PRIMITIVES.no_event
telemetry, TelemetryFailure = _PRIMITIVES.telemetry, _PRIMITIVES.TelemetryFailure


def steps(profile: Row, t0: float, step_s: float, initial: Vector, *, complete: bool,
          check: Check) -> tuple[list[Vector], list[Vector]]:
    raw = profile["raw_returned"]
    require(type(raw["integration_completed"]) is bool, "native integration completion type")
    if complete:
        require(raw["integration_completed"], "native integration incomplete")
    count = int(600/step_s)+1
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
    require(type(reads) is list and len(reads) <= 3*(2+int(600/step_s)),
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
        require(group <= len(states), "native guard without a returned state")
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
    require(isinstance(samples, list) and len(samples) == len(OFFSETS), "native exact sample count")
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
