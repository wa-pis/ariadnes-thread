"""Private synthetic compensated-time check; no real ephemeris adapter."""

from __future__ import annotations

# ruff: noqa: E402 -- Include remaining imports in the cooperative budget.
from time import monotonic

PROCESS_START = monotonic()

from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "0150-synthetic-step-diagnostic.py"
MANIFEST_PATH = HERE / "0150-verification.json"
TRACE_PATH = HERE / "0150-synthetic-trace.json"
MANIFEST_SHA256 = "5e8c7942931a3cf3a40f05c115b241f53315e60d5f81444bd05896b0752df1ae"
TRACE_SHA256 = "7c8843f85771a5b98aee542ad2bac7c8f6ee65d0650c00b9811c24f98aca1242"
Check = Callable[[], None]


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def load_base() -> ModuleType:
    """Load a hash-pinned private instance; never mutate the historical source."""
    require(
        sha256(MANIFEST_PATH.read_bytes()).hexdigest() == MANIFEST_SHA256,
        "baseline manifest identity",
    )
    expected = json.loads(MANIFEST_PATH.read_text())["new_source_sha256"]
    require(
        sha256(BASE_PATH.read_bytes()).hexdigest() == expected,
        "baseline helper identity",
    )
    spec = importlib.util.spec_from_file_location("compensated_private_base", BASE_PATH)
    require(spec is not None and spec.loader is not None, "baseline loader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_base()


def split_epoch(epoch: object, elapsed: object) -> tuple[float, float]:
    """Error-free binary64 sum, hi+lo, for finite inputs without overflow."""
    a, b = BASE.number(epoch), BASE.number(elapsed)
    hi = a + b
    require(math.isfinite(hi), "epoch sum overflow")
    virtual = hi - a
    lo = (a - (hi - virtual)) + (b - virtual)
    require(math.isfinite(lo), "epoch low part outside numeric range")
    return hi, lo


def sample_geometry(elapsed: object, correction: object) -> dict[str, Any]:
    """Keep rounded provider positions; compensate directly in relative separation."""
    s, q = BASE.elapsed(elapsed), BASE.vector(correction)
    hi, lo = split_epoch(BASE.T0, s)
    source_local = hi - BASE.T0
    body = tuple(
        math.fsum((BASE.ORIGIN[j], BASE.VELOCITY[j] * source_local)) for j in range(3)
    )
    initial = (BASE.ORIGIN[0] + BASE.RADIUS_M, BASE.ORIGIN[1], BASE.ORIGIN[2])
    craft_velocity = (BASE.VELOCITY[0], BASE.SPEED, 0.0)
    rephasing = tuple(v * lo for v in BASE.VELOCITY)
    delta = tuple(
        math.fsum((body[j], -initial[j], -craft_velocity[j] * s, -q[j], rephasing[j]))
        for j in range(3)
    )
    radius = math.hypot(*delta)
    require(math.isfinite(radius) and radius > 0, "positive finite source separation")
    force = tuple(BASE.MU * (x / radius) / (radius * radius) for x in delta)
    require(all(math.isfinite(x) for x in force), "finite compensated force")
    return {
        "elapsed_s": s,
        "q": list(q),
        "epoch_high_tdb_s": hi,
        "epoch_low_s": lo,
        "source_local_s": source_local,
        "source_position_m": list(body),
        "source_velocity_m_s": list(BASE.VELOCITY),
        "rephasing_m": list(rephasing),
        "separation_m": list(delta),
        "force_m_s2": list(force),
    }


def compensated_field(elapsed: object, correction: object) -> tuple[float, ...]:
    """Three acceleration components in m/s²; synthetic one-body fixture only."""
    return tuple(sample_geometry(elapsed, correction)["force_m_s2"])


def run_candidate(
    *,
    traced: bool = True,
    check: Check = BASE.idle,
    rhs_limit: int = 3000,
    trial_limit: int = 300,
) -> dict[str, Any]:
    """Reuse the unchanged controller in an isolated private instance."""
    engine = load_base()
    original_field = engine.field
    records: list[dict[str, Any]] = []
    attempts = 0

    def field(s: float, q: tuple[float, ...], mode: str) -> tuple[float, ...]:
        nonlocal attempts
        require(mode == "absolute-rounded", "internal synthetic adapter mode")
        attempts += 1
        geometry = sample_geometry(s, q)
        records.append(geometry)
        return tuple(geometry["force_m_s2"])

    engine.field = field
    try:
        result = engine.run_case(
            "absolute-rounded",
            traced=traced,
            check=check,
            rhs_limit=rhs_limit,
            trial_limit=trial_limit,
        )
    finally:
        engine.field = original_field
    result.update(
        mode="compensated",
        internal_mode="absolute-rounded",
        adapter="binary64-two-sum-and-relative-assembly-v1",
        geometry_records=records,
        synthetic_provider_calls=attempts,
        synthetic_provider_returned=len(records),
        provider_position_floor_retained=True,
        raw_phase_residual_scope="before compensation; epoch_low_s is the applied opposite correction",
    )
    if result["status"] == "finished":
        try:
            require(
                attempts == len(records) == result["rhs_evaluations"],
                "completed geometry/RHS reconciliation",
            )
            require(
                all(
                    a["elapsed_s"] == b["elapsed_s"]
                    and a["q"] == b["q"]
                    and a["force_m_s2"] == b["force_m_s2"]
                    for a, b in zip(records, result["rhs"], strict=True)
                ),
                "completed saved operands reconciliation",
            )
        except ValueError as exc:
            result.update(
                status="failed",
                error={"type": type(exc).__name__, "message": str(exc)},
                failure_context={"phase": "adapter-reconciliation"},
            )
    return result


def execute(path: Path) -> dict[str, Any]:
    """One exclusive candidate; compare saved controls without their reintegration."""
    require(
        not any(
            k.startswith(("numpy", "scipy", "spiceypy", "tudatpy", "space_nav"))
            for k in sys.modules
        ),
        "fresh process required",
    )

    def check() -> None:
        require(0 <= monotonic() - PROCESS_START < 10.0, "candidate process deadline")

    report: dict[str, Any] = {
        "contract": "ADR0152",
        "status": "partial",
        "research_only": True,
        "fixture": "synthetic-translating-one-body-v1",
        "adapter": "binary64-two-sum-and-relative-assembly-v1",
        "budget_s": 10.0,
        "completed_rhs_cap": 3000,
        "trial_record_cap": 300,
        "spice_queries": 0,
        "tudat_propagations": 0,
        "r5_reference_replays": 0,
        "real_ephemeris_fix_verified": False,
        "historical_r5_causality_proven": False,
        "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "baseline_helper_sha256": sha256(BASE_PATH.read_bytes()).hexdigest(),
        "baseline_trace_sha256": TRACE_SHA256,
        "units": {
            "position": "m",
            "velocity": "m/s",
            "acceleration": "m/s^2",
            "time": "local s; absolute TDB epoch for arithmetic only",
        },
        "candidate": None,
        "scientific_gates": None,
        "behavioral_targets": None,
    }
    with path.open("x", encoding="utf-8") as stream:
        try:
            check()
            require(
                sha256(TRACE_PATH.read_bytes()).hexdigest() == TRACE_SHA256,
                "retained baseline trace identity",
            )
            baseline = json.loads(TRACE_PATH.read_text())
            report["baseline_rhs"] = {
                c["mode"]: c["rhs_evaluations"] for c in baseline["cases"]
            }
            require(
                report["baseline_rhs"]
                == {"relative": 37, "absolute-local": 73, "absolute-rounded": 2413},
                "fixed comparison baselines",
            )
            check()
            case = run_candidate(check=check)
            report["candidate"] = case
            check()
            require(
                case["status"] == "finished",
                "candidate incomplete: " + case.get("error", {}).get("message", ""),
            )
            relative = baseline["cases"][0]
            position_difference = math.dist(
                case["final_q"][:3], relative["final_q"][:3]
            )
            velocity_difference = math.dist(
                case["final_q"][3:], relative["final_q"][3:]
            )
            report["final_control_difference"] = {
                "position_m": position_difference,
                "velocity_m_s": velocity_difference,
            }
            report["scientific_gates"] = {
                "completed_ten_seconds": case["final_t_s"] == BASE.DURATION_S,
                "all_retained_forces": bool(case["rhs"])
                and not any(r["force_bad"] for r in case["rhs"]),
                "all_accepted_analytic": bool(case["accepted"])
                and not any(r["analytic_bad"] for r in case["accepted"]),
                "final_control_position": position_difference <= 1e-6,
                "final_control_velocity": velocity_difference <= 1e-8,
            }
            report["behavioral_targets"] = {
                "first_trial_accepted": bool(case["trials"])
                and case["trials"][0]["accepted"],
                "rhs_at_most_241": case["rhs_evaluations"] <= 241,
            }
            report["rhs_reduction_factor"] = 2413 / case["rhs_evaluations"]
            report["status"] = (
                "passed"
                if all(report["scientific_gates"].values())
                and all(report["behavioral_targets"].values())
                else "failed"
            )
            check()
        except (ValueError, RuntimeError, ImportError, OSError, ArithmeticError) as exc:
            report["status"] = "partial"
            report["error"] = {"type": type(exc).__name__, "message": str(exc)}
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
                elapsed_after_flush_s=monotonic() - PROCESS_START,
            )
            stream.seek(0)
            stream.truncate()
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.flush()
    return report
