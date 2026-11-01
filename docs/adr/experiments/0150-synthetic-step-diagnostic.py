"""Private synthetic every-trial diagnostic; never imports SPICE or Tudat."""

from __future__ import annotations

# ruff: noqa: E402 -- Include remaining imports in the cooperative budget.
from time import monotonic

PROCESS_START = monotonic()

from decimal import Decimal, localcontext
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from typing import Any, Callable, Sequence

MODES = ("relative", "absolute-local", "absolute-rounded")
RADIUS_M = 1837400.0
MU = 4902800121846.8
ORIGIN = (-47000000000.0, 128000000000.0, 55000000000.0)
VELOCITY = (31246.224457, 0.0, 0.0)
T0 = 978995455.2304223
DURATION_S = 10.0
SPEED = math.sqrt(MU / RADIUS_M)
Check = Callable[[], None]


class TraceLimit(ValueError):
    """Retain the trace without changing the declared diagnostic limits."""


def idle() -> None:
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def number(value: object) -> float:
    require(
        type(value) in (int, float) and math.isfinite(value), "finite number required"
    )
    return float(value)


def elapsed(value: object) -> float:
    result = number(value)
    require(0 <= result <= DURATION_S, "elapsed outside synthetic interval")
    return result


def vector(value: object) -> tuple[float, ...]:
    require(
        isinstance(value, (list, tuple)) and len(value) == 6, "six corrections required"
    )
    return tuple(number(x) for x in value)


def analytic_state(elapsed_s: float) -> tuple[float, ...]:
    """Independent Decimal circular corrections; binary64 initial-speed rounding only."""
    s = elapsed(elapsed_s)
    with localcontext() as ctx:
        ctx.prec = 80
        d = Decimal.from_float
        radius, speed = d(RADIUS_M), d(SPEED)
        theta = speed * d(s) / radius
        sine, cosine = theta, Decimal(1)
        sin_term, cos_term = theta, Decimal(1)
        for k in range(1, 30):
            sin_term *= -(theta * theta) / ((2 * k) * (2 * k + 1))
            cos_term *= -(theta * theta) / ((2 * k - 1) * (2 * k))
            sine += sin_term
            cosine += cos_term
        return tuple(
            float(v)
            for v in (
                radius * (cosine - 1),
                radius * sine - speed * d(s),
                Decimal(0),
                -speed * sine,
                speed * (cosine - 1),
                Decimal(0),
            )
        )


def field(elapsed_s: float, q: Sequence[float], mode: str) -> tuple[float, ...]:
    s, state = elapsed(elapsed_s), vector(q)
    require(mode in MODES, "unknown synthetic mode")
    if mode == "relative":
        delta = (
            -math.fsum((RADIUS_M, state[0])),
            -math.fsum((SPEED * s, state[1])),
            -state[2],
        )
    else:
        source_s = ((T0 + s) - T0) if mode == "absolute-rounded" else s
        initial = (ORIGIN[0] + RADIUS_M, ORIGIN[1], ORIGIN[2])
        velocity = (VELOCITY[0], SPEED, 0.0)
        craft = tuple(
            math.fsum((initial[j], velocity[j] * s, state[j])) for j in range(3)
        )
        body = tuple(math.fsum((ORIGIN[j], VELOCITY[j] * source_s)) for j in range(3))
        delta = tuple(b - x for b, x in zip(body, craft, strict=True))
    radius = math.hypot(*delta)
    require(math.isfinite(radius) and radius > 0, "positive finite source distance")
    result = tuple(MU * (x / radius) / (radius * radius) for x in delta)
    require(all(math.isfinite(x) for x in result), "nonfinite synthetic force")
    return result


def force_reference(elapsed_s: float, q: Sequence[float]) -> tuple[Decimal, ...]:
    s, state = elapsed(elapsed_s), vector(q)
    with localcontext() as ctx:
        ctx.prec = 80
        d = Decimal.from_float
        delta = (
            -d(RADIUS_M) - d(state[0]),
            -d(SPEED) * d(s) - d(state[1]),
            -d(state[2]),
        )
        radius = sum(x * x for x in delta).sqrt()
        require(radius > 0, "positive reference distance")
        return tuple(d(MU) * x / radius**3 for x in delta)


def first_failure(flags: list[bool]) -> dict[str, Any]:
    """Search cumulative failures, never a nonmonotone raw error or a new solve."""
    require(
        isinstance(flags, list) and all(type(x) is bool for x in flags),
        "boolean flags required",
    )
    prefix: list[bool] = []
    bad = False
    for flag in flags:
        bad = bad or flag
        prefix.append(bad)
    lo, hi = 0, len(prefix)
    probes = []
    while lo < hi:
        mid = (lo + hi) // 2
        probes.append({"lo": lo, "hi": hi, "mid": mid, "prefix_bad": prefix[mid]})
        if prefix[mid]:
            hi = mid
        else:
            lo = mid + 1
    index = lo if lo < len(prefix) else None
    # A separate direct scan checks search bookkeeping, not the physics.
    require(
        index == next((j for j, flag in enumerate(flags) if flag), None),
        "binary search parity",
    )
    return {
        "index": index,
        "previous_index": index - 1 if index is not None and index else None,
        "probes": probes,
    }


def event(
    rows: list[dict[str, Any]], key: str, rejected: bool = False
) -> dict[str, Any]:
    result = first_failure([not row[key] if rejected else row[key] for row in rows])
    index = result["index"]
    result["record"] = rows[index] if index is not None else None
    previous = result["previous_index"]
    result["previous_record"] = rows[previous] if previous is not None else None
    result["scope"] = (
        "first observed record only; not a continuous or historical R5 crossing"
    )
    return result


def run_case(
    mode: str,
    *,
    traced: bool = True,
    check: Check = idle,
    rhs_limit: int = 3000,
    trial_limit: int = 300,
) -> dict[str, Any]:
    """Synthetic ten-second solve; limits retain partial records, never retry."""
    require(mode in MODES, "unknown synthetic mode")
    require(type(traced) is bool, "traced flag must be boolean")
    require(type(rhs_limit) is int and 0 < rhs_limit <= 3000, "RHS limit")
    require(type(trial_limit) is int and 0 < trial_limit <= 300, "trial limit")
    result: dict[str, Any] = {
        "mode": mode,
        "status": "failed",
        "rhs": [],
        "trials": [],
        "accepted": [],
        "nfev": None,
        "callback_attempts": 0,
        "final_t_s": 0.0,
        "final_q": [0.0] * 6,
        "rhs_limit": rhs_limit,
        "trial_record_limit": trial_limit,
    }
    solver: Any = None
    phase = "setup"
    try:
        check()
        import scipy
        from scipy.integrate._ivp.rk import DOP853

        require(scipy.__version__ == "1.17.1", "pinned SciPy required")
        import numpy
        import scipy.integrate._ivp.rk as rk

        require(numpy.__version__ == "1.26.4", "pinned NumPy required")
        result["runtime"] = {
            "scipy": scipy.__version__,
            "numpy": numpy.__version__,
            "rk_source_sha256": sha256(Path(rk.__file__).read_bytes()).hexdigest(),
        }
        check()

        def rhs(s: float, raw: Any) -> tuple[float, ...]:
            result["callback_attempts"] += 1
            check()
            if len(result["rhs"]) >= rhs_limit:
                raise TraceLimit("synthetic RHS cap")
            at, q = elapsed(float(s)), vector(raw.tolist())
            actual, reference = field(at, q, mode), force_reference(at, q)
            with localcontext() as ctx:
                ctx.prec = 80
                error = sum(
                    (Decimal.from_float(x) - y) ** 2
                    for x, y in zip(actual, reference, strict=True)
                ).sqrt()
                limit = max(
                    Decimal("1e-15"),
                    Decimal("1e-11") * sum(x * x for x in reference).sqrt(),
                )
                residual = (
                    Decimal.from_float(T0 + at)
                    - Decimal.from_float(T0)
                    - Decimal.from_float(at)
                )
            result["rhs"].append(
                {
                    "elapsed_s": at,
                    "q": list(q),
                    "force_m_s2": list(actual),
                    "reference_force_m_s2": [str(x) for x in reference],
                    "force_error_m_s2": float(error),
                    "force_limit_m_s2": float(limit),
                    "force_bad": error > limit,
                    "body_time_residual_s": str(residual),
                }
            )
            check()
            return (*q[3:], *actual)

        class Observed(DOP853):
            def _estimate_error_norm(self, k: Any, h: float, scale: Any) -> float:
                check()
                if len(result["trials"]) >= trial_limit:
                    raise TraceLimit("synthetic retained-trial-record cap")
                error = float(super()._estimate_error_norm(k, h, scale))
                require(
                    math.isfinite(error) and error >= 0, "finite error norm required"
                )
                result["trials"].append(
                    {
                        "t_start_s": float(self.t),
                        "h_s": float(h),
                        "t_end_s": float(self.t + h),
                        "error_norm": error,
                        "accepted": error < 1.0,
                        "scale": [float(v) for v in scale],
                        "error5_scaled": [float(v) for v in (k.T @ self.E5) / scale],
                        "error3_scaled": [float(v) for v in (k.T @ self.E3) / scale],
                        "nfev": int(self.nfev),
                    }
                )
                return error

        cls = Observed if traced else DOP853
        phase = "constructor"
        solver = cls(
            rhs,
            0.0,
            (0.0,) * 6,
            DURATION_S,
            rtol=1e-12,
            atol=(1e-7,) * 3 + (1e-10,) * 3,
            max_step=5.0,
            first_step=1.0,
        )
        while solver.status == "running":
            phase = "between-steps"
            check()
            before, count = float(solver.t), len(result["trials"])
            phase = "step"
            message = solver.step()
            phase = "accepted-reconciliation"
            if solver.status == "failed":
                raise ValueError(str(message))
            rows = result["trials"][count:]
            if traced:
                require(bool(rows) and rows[-1]["accepted"], "missing accepted trial")
                require(
                    all(
                        not row["accepted"] and row["t_start_s"] == before
                        for row in rows[:-1]
                    ),
                    "rejected trial reconciliation",
                )
                require(
                    rows[-1]["t_start_s"] == before
                    and rows[-1]["t_end_s"] == float(solver.t),
                    "accepted trial reconciliation",
                )
            q = vector(solver.y.tolist())
            expected = analytic_state(float(solver.t))
            pos, vel = math.dist(q[:3], expected[:3]), math.dist(q[3:], expected[3:])
            result["accepted"].append(
                {
                    "t_s": float(solver.t),
                    "q": list(q),
                    "position_error_m": pos,
                    "velocity_error_m_s": vel,
                    "analytic_bad": pos > 1e-6 or vel > 1e-8,
                }
            )
            phase = "after-accepted"
            check()
        result["status"] = "finished"
    except (ValueError, RuntimeError, ImportError, OSError, ArithmeticError) as exc:
        result["status"] = "capped" if isinstance(exc, TraceLimit) else "failed"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        result["failure_context"] = {
            "phase": phase,
            "rhs_records_retained": len(result["rhs"]),
            "trial_records_retained": len(result["trials"]),
        }
        if phase == "step":
            result["incomplete_trial"] = {"decision": "unavailable"}
    if solver is not None:
        result.update(
            nfev=int(solver.nfev), final_t_s=float(solver.t), final_q=solver.y.tolist()
        )
    result["rhs_evaluations"] = len(result["rhs"])
    result["callbacks_without_force_record"] = (
        result["callback_attempts"] - result["rhs_evaluations"]
    )
    result["first_events"] = {
        "force": event(result["rhs"], "force_bad"),
        "rejected": event(result["trials"], "accepted", rejected=True),
        "analytic": event(result["accepted"], "analytic_bad"),
    }
    return result


def execute(path: Path) -> dict[str, Any]:
    """One exclusive synthetic demonstration with all three fixed arms."""
    require(
        not any(
            k.startswith(("numpy", "scipy", "tudatpy", "spiceypy", "space_nav"))
            for k in sys.modules
        ),
        "fresh process required",
    )

    def check() -> None:
        require(0 <= monotonic() - PROCESS_START < 10.0, "synthetic process deadline")

    report: dict[str, Any] = {
        "contract": "ADR0150",
        "status": "partial",
        "research_only": True,
        "fixture": "synthetic-translating-one-body-v1",
        "duration_s": DURATION_S,
        "origin_m": list(ORIGIN),
        "source_velocity_m_s": list(VELOCITY),
        "radius_m": RADIUS_M,
        "mu_m3_s2": MU,
        "epoch_tdb_s": T0,
        "time_units": "local seconds; absolute TDB epoch for rounding arm only",
        "position_units": "m",
        "velocity_units": "m/s",
        "force_units": "m/s^2",
        "cases": [],
        "budget_s": 10.0,
        "total_rhs_cap": 9000,
        "spice_queries": 0,
        "tudat_propagations": 0,
        "r5_reference_replays": 0,
        "historical_r5_causality_proven": False,
        "continuous_crossing_located": False,
    }
    with path.open("x", encoding="utf-8") as stream:
        try:
            check()
            for mode in MODES:
                case = run_case(mode, check=check)
                report["cases"].append(case)
                check()
                require(
                    sum(c["rhs_evaluations"] for c in report["cases"]) <= 9000,
                    "shared synthetic RHS cap",
                )
                if case["status"] == "failed":
                    raise ValueError(
                        "synthetic case failed: "
                        + case.get("error", {}).get("message", "")
                    )
            control = report["cases"][0]
            require(
                control["status"] == "finished"
                and not any(p["analytic_bad"] for p in control["accepted"]),
                "analytic control did not pass",
            )
            report["status"] = (
                "finished"
                if all(c["status"] == "finished" for c in report["cases"])
                else "partial"
            )
        except (ValueError, RuntimeError, ImportError, OSError, ArithmeticError) as exc:
            report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        report["source_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
        report["elapsed_before_flush_s"] = monotonic() - PROCESS_START
        report["finalization_gate"] = "passed"
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.flush()
        try:
            check()
        except ValueError as exc:
            if "error" in report:
                report["first_error"] = report["error"]
            report.update(
                status="partial",
                finalization_gate="failed",
                error={"type": type(exc).__name__, "message": str(exc)},
                actual_elapsed_after_flush_s=monotonic() - PROCESS_START,
            )
            stream.seek(0)
            stream.truncate()
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.flush()
    return report
