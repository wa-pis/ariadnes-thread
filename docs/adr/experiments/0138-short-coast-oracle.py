"""Private ADR0137 oracle; importing this file loads no scientific libraries."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable

BODIES = ("Sun", "Moon", "Earth")
GM = {"Sun": 1.327124400420322e20, "Moon": 4902800121846.8, "Earth": 398600435468295.9}
GUARDS = {"Sun": 696000000.0, "Moon": 1737400.0, "Earth": 6378136.6}
OFFSETS = (0.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0)
Vector = tuple[float, ...]
Provider = Callable[[str, float], dict[str, Any]]
Check = Callable[[], None]


class OracleError(ValueError):
    """Stop without changed settings, inputs or retries."""


class OracleUnavailable(OracleError):
    """Pinned native input could not be read."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise OracleError(message)


def number(value: object) -> float:
    require(type(value) in (int, float) and math.isfinite(value), "finite nonboolean number required")
    return float(value)


def vector(value: object, size: int) -> Vector:
    require(isinstance(value, (list, tuple)) and len(value) == size, f"expected vector length{size}")
    return tuple(number(v) for v in value)


@dataclass(frozen=True, slots=True)
class Profile:
    rtol: float
    atol: tuple[float, ...]
    max_step_s: float
    first_step_s: float


def profile(tighter: bool) -> Profile:
    require(type(tighter) is bool, "profile must be boolean")
    if tighter:
        return Profile(1e-13, (1e-8,)*3+(1e-11,)*3, 2.5, 0.5)
    return Profile(1e-12, (1e-7,)*3+(1e-10,)*3, 5.0, 1.0)


def included(model: str) -> tuple[str, ...]:
    require(model in ("A", "B"), "model must be A or B")
    return BODIES[:2] if model == "A" else BODIES


def acceleration(position_m: object, positions_m: dict[str, object], gm: dict[str, float]) -> Vector:
    """Direct SSB gravity, separately written unit-vector/squared-distance form.

    Explicit dictionaries also permit analytic one-body fixtures; the R5 adapter
    below fixes its included bodies and constants. No indirect-origin field.
    """
    x = vector(position_m, 3)
    terms = []
    require(bool(gm), "at least one point source required")
    for body, mu_value in gm.items():
        require(body in positions_m, f"missing source {body}")
        mu = number(mu_value)
        require(mu > 0, "positive GM required")
        b = vector(positions_m[body], 3)
        d = tuple(bi-xi for bi, xi in zip(b, x, strict=True))
        radius = math.hypot(*d)
        require(math.isfinite(radius) and radius > 0, "positive finite source separation required")
        radius_squared = radius*radius
        require(math.isfinite(radius_squared) and radius_squared > 0, "squared distance outside numeric range")
        strength = mu/radius_squared
        require(math.isfinite(strength) and strength > 0, "acceleration strength outside numeric range")
        terms.append(tuple(strength*(di/radius) for di in d))
    result = tuple(math.fsum(t[j] for t in terms) for j in range(3))
    return vector(result, 3)


def spice_provider(body: str, epoch_tdb_s: float) -> dict[str, Any]:
    """Independent geometric CSPICE SSB/J2000 query; km/km/s converted to SI."""
    require(body in BODIES, "unsupported body")
    epoch = number(epoch_tdb_s)
    import spiceypy

    try:
        raw, _light_time = spiceypy.spkezr(body, epoch, "J2000", "NONE", "SSB")
        values = raw.tolist() if hasattr(raw, "tolist") else list(raw)
    except Exception as exc:  # Untyped CSPICE boundary only.
        raise OracleUnavailable(f"{body} state unavailable at{epoch}TDBs: {exc}") from exc
    values_si = vector(tuple(v*1000 for v in vector(values, 6)), 6)
    return {"body": body, "epoch_tdb_s": epoch, "origin": "SSB", "orientation": "J2000",
            "aberration_correction": "NONE", "position_m": values_si[:3], "velocity_m_s": values_si[3:]}


@dataclass(slots=True)
class Context:
    """Shared across four oracle solves and the once-only seven-node body table."""

    check: Check
    rhs_attempted: int = 0
    rhs_completed: int = 0
    states_attempted: int = 0
    states_completed: int = 0
    last_returned_state: object | None = None
    minimum_checked_distances_m: dict[str, float] = field(default_factory=dict)

    def query(self, body: str, epoch_tdb_s: float, provider: Provider) -> dict[str, Any]:
        require(body in BODIES, "unsupported body")
        epoch = number(epoch_tdb_s)
        self.check()
        require(self.states_attempted < 30021, "Python state-query cap30021")
        self.states_attempted += 1
        raw = provider(body, epoch)
        self.states_completed += 1
        self.last_returned_state = raw
        self.check()  # Returned raw data survives an after-call deadline failure.
        require(isinstance(raw, dict), "body state must be a record")
        require(raw.get("body") == body and number(raw.get("epoch_tdb_s")) == epoch,
                "body/epoch mismatch")
        require((raw.get("origin"), raw.get("orientation"), raw.get("aberration_correction"))
                == ("SSB", "J2000", "NONE"), "body-state frame/aberration mismatch")
        vector(raw.get("position_m"), 3)
        vector(raw.get("velocity_m_s"), 3)
        return raw

    def guard(self, position_m: object, states: dict[str, dict[str, Any]]) -> None:
        position = vector(position_m, 3)
        require(tuple(states) == BODIES, "all three guard sources in frozen order required")
        for body in BODIES:
            source = vector(states[body]["position_m"], 3)
            distance = math.dist(position, source)
            self.minimum_checked_distances_m[body] = min(
                distance, self.minimum_checked_distances_m.get(body, math.inf))
            require(math.isfinite(distance) and distance > GUARDS[body], f"{body} exclusion sphere")

    def counts(self) -> dict[str, int]:
        return {"rhs_attempted": self.rhs_attempted, "rhs_completed": self.rhs_completed,
                "states_attempted": self.states_attempted, "states_completed": self.states_completed}


def correction_rhs(
    elapsed_s: object, correction: object, initial: object, epoch_tdb_s: object,
    model: str, context: Context, provider: Provider,
) -> Vector:
    """Actual R5 RHS: elapsed-time calls may go backward within an adaptive step."""
    context.check()
    require(context.rhs_attempted < 10000, "oracle RHS cap10000")
    context.rhs_attempted += 1
    selected = included(model)
    elapsed = number(elapsed_s)
    require(0 <= elapsed <= 300, "RHS time outside frozen interval")
    q, y0, epoch = vector(correction, 6), vector(initial, 6), number(epoch_tdb_s)
    position = tuple(math.fsum((y0[j], y0[j+3]*elapsed, q[j])) for j in range(3))
    states = {body: context.query(body, epoch+elapsed, provider) for body in BODIES}
    context.guard(position, states)
    result = (*q[3:], *acceleration(position, {b: states[b]["position_m"] for b in selected},
                                 {b: GM[b] for b in selected}))
    context.rhs_completed += 1
    context.check()
    return result


def integrate_corrections(
    initial: object, epoch_tdb_s: object, tighter: bool,
    rhs: Callable[[float, Vector], Vector], check: Check,
) -> dict[str, Any]:
    """Fixed300s DOP853 correction-coordinate solve; callable supports analytic fixtures.

    The scientific adapter solve_model supplies only the frozen R5 RHS. The
    low-level callable exists for independent zero-force/circular invariants.
    """
    y0, epoch, settings = vector(initial, 6), number(epoch_tdb_s), profile(tighter)
    check()
    from scipy.integrate import solve_ivp

    def callback(elapsed: float, raw: Any) -> Vector:
        check()
        result = vector(rhs(float(elapsed), vector(raw.tolist(), 6)), 6)
        check()
        return result

    solution = solve_ivp(callback, (0.0, 300.0), (0.0,)*6, method="DOP853",
                         t_eval=OFFSETS, rtol=settings.rtol, atol=settings.atol,
                         max_step=settings.max_step_s, first_step=settings.first_step_s)
    # Retain returned arrays before the after-solve deadline check. This function
    # returns them through the dedicated exception if a final gate fails.
    returned = {"success": bool(solution.success), "message": str(solution.message),
                "offsets_s": solution.t.tolist(), "corrections": solution.y.T.tolist(),
                "nfev": int(solution.nfev), "tighter": tighter}
    try:
        check()
        require(solution.success, f"DOP853 solver failure: {solution.message}")
        require(tuple(returned["offsets_s"]) == OFFSETS and len(returned["corrections"]) == 7,
                "oracle sample epochs/shape mismatch")
        samples = []
        for elapsed, raw in zip(OFFSETS, returned["corrections"], strict=True):
            q = vector(raw, 6)
            state = (*tuple(math.fsum((y0[j], y0[j+3]*elapsed, q[j])) for j in range(3)),
                     *tuple(y0[j]+q[j] for j in range(3, 6)))
            samples.append({"epoch_tdb_s": epoch+elapsed, "state": vector(state, 6)})
        require(samples[0]["state"] == y0 and tuple(returned["corrections"][0]) == (0.0,)*6,
                "oracle initial state differs")
        returned["samples"] = samples
    except (OracleError, RuntimeError, ValueError) as exc:
        raise ReturnedOracleFailure(str(exc), returned) from exc
    return returned


class ReturnedOracleFailure(OracleError):
    """A solve returned raw data before its final deadline/validation failed."""

    def __init__(self, message: str, returned: dict[str, Any]) -> None:
        super().__init__(message)
        self.returned: dict[str, Any] = returned


def solve_model(
    initial: object, epoch_tdb_s: object, model: str, tighter: bool,
    context: Context, provider: Provider = spice_provider,
) -> dict[str, Any]:
    """Frozen R5 adapter; runner owns order/solve counts/identities/exclusive evidence."""
    included(model)
    y0, epoch = vector(initial, 6), number(epoch_tdb_s)
    before = context.counts()
    result = integrate_corrections(y0, epoch, tighter,
                                  lambda t, q: correction_rhs(t, q, y0, epoch, model, context, provider),
                                  context.check)
    result.update(model=model, counts_before=before, counts_after=context.counts(),
                  minimum_checked_distances_m=dict(context.minimum_checked_distances_m))
    return result
