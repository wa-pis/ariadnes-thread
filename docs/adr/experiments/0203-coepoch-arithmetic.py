"""Evaluate one ideal coepoch with the frozen R2 elliptic arithmetic."""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

type Row = dict[str, Any]
type State = tuple[float, ...]

R2_SOURCE = Path(__file__).resolve().with_name("0128-reference-coast.py")
R2_SHA256 = "027d0b4e45f9ebd941249e427963e365fd7205f9594a96365a587eb0e8cd7e81"
IDEAL_MODEL = "sun-centered-zero-revolution-patched-conic-v1"
OUTGOING_MODEL = "r5-ssb-sun-moon-earth-point-v1"


def _r2() -> Row:
    with R2_SOURCE.open("rb") as stream:
        raw = stream.read(64 * 1024)
    if sha256(raw).hexdigest() != R2_SHA256:
        raise ValueError("pinned R2 arithmetic source digest")
    module = ModuleType("_r556_r2_arithmetic")
    module.__file__ = str(R2_SOURCE)
    sys.modules[module.__name__] = module
    try:
        exec(compile(raw, str(R2_SOURCE), "exec"), module.__dict__)
    finally:
        del sys.modules[module.__name__]
    return vars(module)


def _flip_velocity(state: State) -> State:
    return state[:3] + tuple(-value for value in state[3:])


def _difference(left: State, right: State) -> Row:
    delta = tuple(a - b for a, b in zip(left, right, strict=True))
    position, velocity = math.hypot(*delta[:3]), math.hypot(*delta[3:])
    if not (math.isfinite(position) and math.isfinite(velocity)):
        raise ValueError("non-finite state difference")
    return {"position_si": delta[:3], "velocity_si": delta[3:],
            "position_norm_m": position, "velocity_norm_m_s": velocity}


def _solve(
    r2: Row,
    seed: State,
    seed_tdb_s: float,
    elapsed_s: float,
    sun: State,
    reverse: bool,
    check: Callable[[], None],
) -> Row:
    check()
    ellipse = r2["derive"](_flip_velocity(seed) if reverse else seed)
    root = r2["oracle"](ellipse, elapsed_s)
    raw = root.pop("state")
    relative = _flip_velocity(raw) if reverse else raw
    ssb = r2["vector"](tuple(a + b for a, b in zip(relative, sun, strict=True)), 6)
    energy0, h0 = r2["invariants"](seed)
    energy, h = r2["invariants"](relative)
    errors = {"energy": abs(energy - energy0) / abs(energy0),
              "angular_momentum": math.dist(h, h0) / math.hypot(*h0)}
    if not all(r2["number"](e) <= 1e-12 for e in errors.values()):
        raise ValueError("R2 energy or angular-momentum invariant mismatch")
    if not (type(root["updates"]) is int and 1 <= root["updates"] <= 64
            and all(0 <= r2["number"](root[key]) <= 2e-14 for key in ("bracket_width_rad", "residual_rad"))):
        raise ValueError("R2 root diagnostics invalid")
    check()
    return {"seed_epoch_tdb_s": seed_tdb_s, "seed_relative_si": seed, "elapsed_s": elapsed_s,
            "relative_si": relative, "ssb_si": ssb, "semimajor_axis_m": ellipse.a_m,
            "eccentricity": ellipse.eccentricity, "relative_invariant_errors": errors, "root": root}


def evaluate(
    checkpoint_tdb_s: float,
    departure_tdb_s: float,
    arrival_tdb_s: float,
    departure_relative_si: State,
    arrival_relative_si: State,
    checkpoint_sun_ssb_si: State,
    outgoing_ssb_si: State,
    check: Callable[[], None],
) -> Row:
    """Compare two ideal constructions at one SI/TDB/J2000 coast epoch."""
    check()
    r2 = _r2()
    epoch, departure, arrival = map(r2["number"], (checkpoint_tdb_s, departure_tdb_s, arrival_tdb_s))
    if not departure < epoch < arrival:
        raise ValueError("checkpoint must be strictly between departure and arrival epochs")
    start, stop, sun = [r2["vector"](state, 6)
                        for state in (departure_relative_si, arrival_relative_si, checkpoint_sun_ssb_si)]
    forward = _solve(r2, start, departure, epoch - departure, sun, False, check)
    backward = _solve(r2, stop, arrival, arrival - epoch, sun, True, check)
    agreement = {frame: _difference(backward[key], forward[key])
                 for frame, key in (("sun_relative", "relative_si"), ("ssb", "ssb_si"))}
    for name, difference in agreement.items():
        if difference["position_norm_m"] > 1 or difference["velocity_norm_m_s"] > 1e-6:
            raise ValueError(f"R2 {name} coepoch agreement exceeds 1 m / 1e-6 m/s")

    # The backward receiver is fixed before the outgoing state participates in any arithmetic.
    outgoing = r2["vector"](outgoing_ssb_si, 6)
    model_difference = _difference(backward["ssb_si"], outgoing)
    check()
    return {
        "ideal_status": "ideal-reference-coepoch-computed",
        "physical_status": "physical-join-not-established",
        "ideal_mass_kg": None,
        "continuity_residuals": dict.fromkeys(("epoch_s", "position_m", "velocity_m_s", "mass_kg")),
        "epoch_tdb_s": epoch, "epoch_binary64_hex": epoch.hex(),
        "orientation": "J2000", "relative_origin": "Sun", "ssb_origin": "SSB",
        "units": r2["UNITS"], "solar_gm_m3_s2": r2["MU"], "ideal_force_model_id": IDEAL_MODEL,
        "checkpoint_sun_ssb_si": sun,
        "analytic_evaluations": 2, "root_updates": sum(p["root"]["updates"] for p in (forward, backward)),
        "forward": forward, "backward": backward, "agreement": agreement,
        "model_difference": {"sign": "backward ideal minus outgoing model B",
                             "outgoing_force_model_id": OUTGOING_MODEL, **model_difference},
    }
