"""ADR0137 bounded orchestration. Reference execution waits for verified offline audit."""

from __future__ import annotations

# ruff: noqa: E402 -- Start the process budget before remaining imports.

from time import monotonic

PROCESS_START = monotonic()

from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable, TextIO

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE_SHA = {
    "0141-short-coast-inputs.py": "4457d9094afe3e8b674a46704b6789fdd724469cb8e1efe5cc054ce39d34c37c",
    "0140-short-coast-native.py": "8bc888d6e1c638251d8379d6d4c896393b5cd76fb71e85c65c7faf9aab9294e2",
    "0138-short-coast-oracle.py": "d6a624f727e17de364f188f0941f2e1889741204ad035aefd9263728cf95e029",
}


def load(name: str) -> ModuleType:
    path = HERE / name
    if sha256(path.read_bytes()).hexdigest() != SOURCE_SHA[name]:
        raise ImportError(f"prepared adapter changed: {name}")
    spec = importlib.util.spec_from_file_location("r5_runner_" + name[:4], path)
    if spec is None or spec.loader is None:
        raise ImportError(name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


inputs = load("0141-short-coast-inputs.py")
native = load("0140-short-coast-native.py")
oracle = load("0138-short-coast-oracle.py")
common = inputs.common


class Budget(common.Budget):
    """Reuse R2 retention/timing events, with the frozen R5 sixty-second cap."""

    def check(self, stage: str = "") -> None:
        elapsed = common.number(self.clock()) - self.start
        common.require(0 <= elapsed < 60.0, f"deadline/clock at {stage}")


def wire(value: Any) -> Any:
    """Finite partial JSON; preserve nonfinite/unknown values as explicit markers."""
    if isinstance(value, dict):
        return {str(k): wire(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [wire(v) for v in value]
    if hasattr(value, "tolist"):
        return wire(value.tolist())
    return common.safe_json(value)


def difference(left: object, right: object) -> dict[str, Any]:
    a, b = common.vector(left, 6), common.vector(right, 6)
    delta = tuple(y - x for x, y in zip(a, b, strict=True))
    common.vector(delta, 6)
    return {
        "right_minus_left_si": delta,
        "position_norm_m": common.number(math.hypot(*delta[:3])),
        "velocity_norm_m_s": common.number(math.hypot(*delta[3:])),
    }


def within(value: dict[str, Any], position_m: float, velocity_m_s: float) -> bool:
    return (
        value["position_norm_m"] <= position_m
        and value["velocity_norm_m_s"] <= velocity_m_s
    )


def states(result: dict[str, Any], bundle: dict[str, Any]) -> list[tuple[float, ...]]:
    points = result["samples"]
    common.require(len(points) == 7, "seven samples required")
    common.require(
        tuple(common.number(p["epoch_tdb_s"]) for p in points)
        == tuple(bundle["nodes_tdb_s"]),
        "sample epoch mismatch",
    )
    parsed = [common.vector(p["state"], 6) for p in points]
    common.require(
        parsed[0] == common.vector(bundle["state_si"], 6), "initial state mismatch"
    )
    return parsed


def compare_model(
    results: dict[str, Any], bundle: dict[str, Any], rows: list[dict[str, Any]]
) -> None:
    values = {name: states(value, bundle) for name, value in results.items()}
    for j, epoch in enumerate(bundle["nodes_tdb_s"]):
        row = {
            "epoch_tdb_s": epoch,
            "native_profile": difference(
                values["native-normal"][j], values["native-tight"][j]
            ),
            "native_oracle": difference(
                values["native-tight"][j], values["oracle-tight"][j]
            ),
            "oracle_profile": difference(
                values["oracle-normal"][j], values["oracle-tight"][j]
            ),
        }
        row["gates"] = {
            key: within(row[key], *limits)
            for key, limits in [
                ("native_profile", (0.01, 1e-5)),
                ("native_oracle", (0.01, 1e-5)),
                ("oracle_profile", (0.001, 1e-6)),
            ]
        }
        rows.append(row)
        common.require(
            all(row["gates"].values()), f"numerical agreement failed at {epoch}"
        )


def snapshot(native_context: Any, oracle_context: Any) -> dict[str, Any]:
    return {
        "native_arcs_attempted": native_context.arcs_attempted,
        "native_arcs_returned": native_context.arcs_returned,
        "native_arcs_completed": native_context.arcs_completed,
        "native_guard_reads_attempted": native_context.guard_reads_attempted,
        "native_guard_reads_returned": native_context.guard_reads_returned,
        "oracle": oracle_context.counts(),
    }


def identity(check: Callable[[], None]) -> dict[str, Any]:
    return inputs.runtime_identity(
        check,
        extra_sources=(Path(__file__), ROOT / "tests/test_r5_short_coast_runner.py"),
    )


def run(
    stream: TextIO,
    *,
    clock: Callable[[], float] = monotonic,
    start_s: float | None = None,
    loader: Callable[..., dict[str, Any]] = inputs.load_inputs,
    identity_provider: Callable[..., dict[str, Any]] = identity,
    native_solver: Callable[..., dict[str, Any]] = native.solve_model,
    oracle_solver: Callable[..., dict[str, Any]] = oracle.solve_model,
    provider: Callable[..., dict[str, Any]] = oracle.spice_provider,
) -> dict[str, Any]:
    """Shared-budget run; injected adapters are labelled tests, never reference evidence.

    execute() supplies a process-start baseline including this module's imports.
    No reference call belongs in preparation tests, even though this private API exists.
    """
    budget = Budget(clock)
    if start_s is not None:
        budget.start = common.number(start_s)
    nc, oc = native.Context(budget.check), oracle.Context(budget.check)
    report: dict[str, Any] = {
        "contract": "ADR0137",
        "study": "r5-short-coast-earth-gravity-v1",
        "adapter_mode": "reference"
        if (
            loader is inputs.load_inputs
            and identity_provider is identity
            and native_solver is native.solve_model
            and oracle_solver is oracle.solve_model
            and provider is oracle.spice_provider
            and clock is monotonic
        )
        else "injected-test",
        "status": "failed",
        "budget_s": 60.0,
        "research_only": True,
        "mission_accuracy_verified": False,
        "continuous_safety_verified": False,
        "origin": "SSB",
        "orientation": "J2000",
        "time_units": "TDB seconds since J2000",
        "position_units": "m",
        "velocity_units": "m/s",
        "acceleration_units": "m/s^2",
        "constant_mass_metadata_kg": 2000.0,
        "omissions": [
            "other planets",
            "lunar/Martian harmonics",
            "SRP/shadows",
            "relativity",
            "thrust",
        ],
        "calls": budget.calls,
        "body_table": [],
        "models": {},
        "signed_model_differences": [],
        "interpretation": "unavailable until every numerical gate passes",
        "finalization_gate": "pending",
    }
    stage = "setup"
    try:
        budget.check(stage)
        for name, expected in SOURCE_SHA.items():
            budget.check("prepared adapter source")
            common.require(
                common.digest(HERE / name) == expected,
                "prepared adapter identity drift",
            )
        if report["adapter_mode"] == "reference":
            common.require(
                start_s == PROCESS_START, "reference process-start baseline required"
            )
        bundle = budget.call(
            "inputs",
            lambda: loader(budget.check),
            lambda v: report.__setitem__("inputs", wire(v)),
        )
        before = budget.call(
            "initial identity",
            lambda: identity_provider(budget.check),
            lambda v: report.__setitem__("identity", wire(v)),
        )
        common.check_inventory(before["kernels"], bundle["original_kernel_manifest"])
        for epoch in bundle["nodes_tdb_s"]:
            point = {"epoch_tdb_s": epoch, "states": {}}
            report["body_table"].append(point)
            for body in oracle.BODIES:
                stage = f"node table {epoch} {body}"
                point["request"] = {
                    "body": body,
                    "epoch_tdb_s": epoch,
                    "origin": "SSB",
                    "orientation": "J2000",
                    "aberration_correction": "NONE",
                }
                budget.call(
                    stage,
                    lambda b=body, t=epoch: oc.query(b, t, provider),
                    lambda v, b=body: point["states"].__setitem__(b, wire(v)),
                )
        for model in ("A", "B"):
            block = {
                "model_id": f"r5-ssb-sun-moon{'-earth' if model == 'B' else ''}-point-v1",
                "included_sources": oracle.included(model),
                "gm_m3_s2": dict(oracle.GM),
                "profiles": {},
                "numerical_comparison": [],
                "node_forces": [],
            }
            report["models"][model] = block
            for engine, tighter in [
                ("native", False),
                ("native", True),
                ("oracle", False),
                ("oracle", True),
            ]:
                stage = f"{model} {engine} {'tight' if tighter else 'normal'}"
                tag = f"{engine}-{'tight' if tighter else 'normal'}"
                entry: dict[str, Any] = {}
                block["profiles"][tag] = entry

                def retain(value: dict[str, Any]) -> None:
                    entry["result"] = wire(value)
                    if engine == "native":
                        entry["raw_returned"] = wire(nc.last_returned)

                def solve() -> dict[str, Any]:
                    if engine == "native":
                        return native_solver(
                            bundle["state_si"],
                            bundle["epoch_tdb_s"],
                            model,
                            tighter,
                            nc,
                        )
                    common.require(
                        report.get("oracle_solves_attempted", 0) < 4,
                        "oracle solve cap4",
                    )
                    report["oracle_solves_attempted"] = (
                        report.get("oracle_solves_attempted", 0) + 1
                    )
                    value = oracle_solver(
                        bundle["state_si"],
                        bundle["epoch_tdb_s"],
                        model,
                        tighter,
                        oc,
                        provider,
                    )
                    report["oracle_solves_returned"] = (
                        report.get("oracle_solves_returned", 0) + 1
                    )
                    return value

                result = budget.call(stage, solve, retain)
                parsed = states(result, bundle)
                common.require(result["model"] == model, "returned model mismatch")
                if engine == "native":
                    common.require(
                        (
                            result["origin"],
                            result["orientation"],
                            result["position_units"],
                            result["velocity_units"],
                            result["time_units"],
                        )
                        == ("SSB", "J2000", "m", "m/s", "TDB seconds since J2000"),
                        "native output labels mismatch",
                    )
                    common.require(
                        common.number(result["step_s"]) == (0.5 if tighter else 1.0)
                        and result["retained_states"] == (601 if tighter else 301)
                        and result["guarded_states"] == result["retained_states"],
                        "native profile/coverage mismatch",
                    )
                    common.require(
                        result["gravity_parameters_m3_s2"] == oracle.GM
                        and tuple(result["force_order"])
                        == ("total",) + oracle.included(model),
                        "native force metadata mismatch",
                    )
                else:
                    common.require(
                        result["tighter"] is tighter, "oracle profile mismatch"
                    )
                    counts_before, counts_after = (
                        result["counts_before"],
                        result["counts_after"],
                    )
                    common.require(
                        type(result["nfev"]) is int
                        and result["nfev"] > 0
                        and counts_after == oc.counts()
                        and counts_after["rhs_attempted"]
                        - counts_before["rhs_attempted"]
                        == result["nfev"],
                        "oracle solver counts mismatch",
                    )
                if engine == "oracle":
                    report["oracle_solves_completed"] = (
                        report.get("oracle_solves_completed", 0) + 1
                    )
                for j, state in enumerate(parsed):
                    budget.check("node force operands")
                    body_states = report["body_table"][j]["states"]
                    parts = {
                        body: oracle.acceleration(
                            state[:3],
                            {body: body_states[body]["position_m"]},
                            {body: oracle.GM[body]},
                        )
                        for body in oracle.included(model)
                    }
                    total = tuple(
                        math.fsum(v[d] for v in parts.values()) for d in range(3)
                    )
                    block["node_forces"].append(
                        {
                            "profile": tag,
                            "epoch_tdb_s": bundle["nodes_tdb_s"][j],
                            "spacecraft_position_m": state[:3],
                            "per_source_m_s2": parts,
                            "total_m_s2": total,
                        }
                    )
            stage = f"{model} numerical comparison"
            compare_model(
                {k: v["result"] for k, v in block["profiles"].items()},
                bundle,
                block["numerical_comparison"],
            )
        stage = "signed model comparison"
        for j, epoch in enumerate(bundle["nodes_tdb_s"]):
            row = {"epoch_tdb_s": epoch}
            for engine in ("native", "oracle"):
                a = report["models"]["A"]["profiles"][engine + "-tight"]["result"][
                    "samples"
                ][j]["state"]
                b = report["models"]["B"]["profiles"][engine + "-tight"]["result"][
                    "samples"
                ][j]["state"]
                row[engine + "_B_minus_A"] = difference(a, b)
            row["oracle_minus_native_sensitivity"] = difference(
                row["native_B_minus_A"]["right_minus_left_si"],
                row["oracle_B_minus_A"]["right_minus_left_si"],
            )
            row["gate"] = within(row["oracle_minus_native_sensitivity"], 0.02, 2e-5)
            report["signed_model_differences"].append(row)
            common.require(row["gate"], "signed model sensitivity disagreement")
        stage = "final counts"
        counts = snapshot(nc, oc)
        common.require(
            counts["native_arcs_attempted"]
            == counts["native_arcs_returned"]
            == counts["native_arcs_completed"]
            == 4,
            "native call counts mismatch",
        )
        common.require(
            report["oracle_solves_attempted"]
            == report["oracle_solves_returned"]
            == report["oracle_solves_completed"]
            == 4,
            "oracle call counts mismatch",
        )
        c = oc.counts()
        common.require(
            0 < c["rhs_attempted"] == c["rhs_completed"] <= 10000
            and c["states_attempted"]
            == c["states_completed"]
            == 3 * c["rhs_attempted"] + 21
            <= 30021,
            "oracle RHS/query counts mismatch",
        )
        if report["adapter_mode"] == "reference":
            common.require(
                nc.guard_reads_attempted == nc.guard_reads_returned == 5424,
                "retained-state guard coverage mismatch",
            )
        stage = "final identity"
        after = budget.call(
            stage,
            lambda: identity_provider(budget.check),
            lambda v: report.__setitem__("final_identity", wire(v)),
        )
        common.require(
            report["identity"] == wire(after), "source/runtime/resource identity drift"
        )
        common.check_inventory(after["kernels"], bundle["original_kernel_manifest"])
        budget.check("all comparisons")
        report.update(
            status="passed",
            interpretation="restricted300s model sensitivity; empirical numerical comparison only",
        )
    except (
        RuntimeError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        ImportError,
        OSError,
    ) as exc:
        report["error"] = {
            "stage": stage,
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if isinstance(
            exc, (native.ReturnedNativeFailure, oracle.ReturnedOracleFailure)
        ):
            report["failed_solver_returned"] = wire(exc.returned)
    report["counts"] = snapshot(nc, oc)
    report["native_minimum_checked_distances_m"] = dict(nc.minimum_checked_distances_m)
    report["oracle_minimum_checked_distances_m"] = dict(oc.minimum_checked_distances_m)
    report["guard_minimum_scope"] = (
        "cumulative whole study; sampled states/RHS only, not continuous safety"
    )
    if report["status"] != "passed":
        report["partial_raw"] = {
            "native": nc.last_returned,
            "native_guard": nc.last_guard_state,
            "oracle_body": oc.last_returned_state,
        }
        report["downstream_checks"] = "unavailable after first failure; no retries"
    report["elapsed_sample_before_flush_s"] = clock() - budget.start
    report["finalization_gate"] = "passed"
    json.dump(wire(report), stream, indent=2, allow_nan=False)
    stream.flush()
    try:
        budget.check("evidence flush")
    except common.GateFailure as exc:
        if "error" in report:
            report["first_error"] = dict(report["error"])
        report.update(
            status="failed",
            finalization_gate="failed",
            interpretation="unavailable: finalization failed",
            error={
                "stage": "evidence flush",
                "type": type(exc).__name__,
                "message": str(exc),
            },
            actual_elapsed_after_flush_s=clock() - budget.start,
        )
        stream.seek(0)
        stream.truncate()
        json.dump(wire(report), stream, indent=2, allow_nan=False)
        stream.flush()
    return wire(report)


def execute(path: Path) -> dict[str, Any]:
    """Fresh-process exclusive output; invoke only after all R5 preparation passes."""
    common.require(
        not any(
            k.startswith(("space_nav", "numpy", "scipy", "tudatpy", "spiceypy"))
            for k in sys.modules
        ),
        "reference execution requires a fresh process",
    )
    with path.open("x", encoding="utf-8") as stream:
        return run(stream, start_s=PROCESS_START)
