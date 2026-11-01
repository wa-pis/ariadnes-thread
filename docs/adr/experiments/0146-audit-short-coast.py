"""Private ADR0143 offline audit. Never queries a body or propagates a state."""

from __future__ import annotations

# ruff: noqa: E402 -- Include remaining imports in the cooperative process budget.
from time import monotonic

PROCESS_START = monotonic()

from decimal import Decimal, localcontext
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any, Callable, TextIO

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PINS = {
    "0144-short-coast-audit.py": "307ad5abb4b56c93abb9843ba5d657ab54d6a7954af238b07c21e342dcfbbdea",
    "0145-short-coast-evidence.py": "426fe4e0abe9b9dfcf6380d09e86e8dbf5748f66875f74b26b45dceb6ba5da14",
}


def load(name: str) -> ModuleType:
    path = HERE / name
    if sha256(path.read_bytes()).hexdigest() != PINS[name]:
        raise ImportError("offline prepared source changed: " + name)
    spec = importlib.util.spec_from_file_location("r5_offline_" + name[:4], path)
    if spec is None or spec.loader is None:
        raise ImportError(name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load("0144-short-coast-audit.py")
files = load("0145-short-coast-evidence.py")
require, number, vector = core.require, core.number, core.vector
OMISSIONS = [
    "other planets",
    "lunar/Martian harmonics",
    "SRP/shadows",
    "relativity",
    "thrust",
]
FAILURES = (
    ValueError,
    TypeError,
    KeyError,
    IndexError,
    AttributeError,
    OSError,
    RuntimeError,
    ArithmeticError,
    subprocess.SubprocessError,
)


class Budget:
    def __init__(self, clock: Callable[[], float], start_s: float) -> None:
        self.clock = clock
        self.start = number(start_s)

    def elapsed(self) -> float:
        return number(self.clock()) - self.start

    def check(self) -> None:
        require(0 <= self.elapsed() < 10.0, "offline deadline/clock")


def integer(value: object, cap: int) -> int:
    require(type(value) is int and 0 <= value <= cap, "bounded integer count required")
    return value


def header(report: dict[str, Any]) -> bool:
    require(
        report["contract"] == "ADR0137"
        and report["study"] == "r5-short-coast-earth-gravity-v1",
        "study contract",
    )
    require(report["status"] in ("passed", "failed"), "source study status")
    require(report["adapter_mode"] in ("reference", "injected-test"), "adapter mode")
    require(
        report["research_only"] is True
        and report["mission_accuracy_verified"] is False
        and report["continuous_safety_verified"] is False,
        "research/safety labels",
    )
    require(
        all(report[k] == v for k, v in core.LABELS.items())
        and report["acceleration_units"] == "m/s^2",
        "state/force labels",
    )
    require(
        number(report["budget_s"]) == 60.0
        and number(report["constant_mass_metadata_kg"]) == 2000.0
        and report["omissions"] == OMISSIONS,
        "restricted physical contract",
    )
    require(
        report["guard_minimum_scope"]
        == "cumulative whole study; sampled states/RHS only, not continuous safety",
        "guard scope",
    )
    complete = report["status"] == "passed"
    expected_interpretation = (
        "restricted300s model sensitivity; empirical numerical comparison only"
    )
    require(
        report["interpretation"] == expected_interpretation
        if complete
        else report["interpretation"]
        in (
            "unavailable until every numerical gate passes",
            "unavailable: finalization failed",
        ),
        "interpretation scope",
    )
    require(report["finalization_gate"] in ("passed", "failed"), "source flush status")
    if complete:
        require(
            report["finalization_gate"] == "passed"
            and "error" not in report
            and "first_error" not in report
            and "partial_raw" not in report,
            "false success",
        )
    else:
        error = report["error"]
        require(
            all(isinstance(error[k], str) for k in ("stage", "type", "message")),
            "source error",
        )
        if "first_error" in report:
            require(
                all(
                    isinstance(report["first_error"][k], str)
                    for k in ("stage", "type", "message")
                ),
                "first source error",
            )
    return complete


def body_table(report: dict[str, Any], bundle: dict[str, Any], complete: bool) -> int:
    table = report["body_table"]
    require(
        isinstance(table, list)
        and len(table) <= 7
        and (not complete or len(table) == 7),
        "body table length",
    )
    checked = 0
    for j, row in enumerate(table):
        epoch = bundle["nodes_tdb_s"][j]
        require(number(row["epoch_tdb_s"]) == epoch, "body node epoch")
        require(
            list(row["states"]) == list(core.GM)[: len(row["states"])]
            and (not complete or len(row["states"]) == 3),
            "body node inventory",
        )
        require(
            j == len(table) - 1 or len(row["states"]) == 3, "partial body node order"
        )
        for name, state in row["states"].items():
            require(
                state["body"] == name
                and number(state["epoch_tdb_s"]) == epoch
                and state["origin"] == "SSB"
                and state["orientation"] == "J2000"
                and state["aberration_correction"] == "NONE",
                "body metadata",
            )
            vector(state["position_m"], 3)
            vector(state["velocity_m_s"], 3)
            checked += 1
        request = row["request"]
        allowed = list(core.GM)[
            max(0, len(row["states"]) - 1) : min(3, len(row["states"]) + 1)
        ]
        require(
            request["body"] in allowed
            and number(request["epoch_tdb_s"]) == epoch
            and request["origin"] == "SSB"
            and request["orientation"] == "J2000"
            and request["aberration_correction"] == "NONE",
            "body request metadata",
        )
    return checked


def force_rows(
    block: dict[str, Any],
    model: str,
    table: list[dict[str, Any]],
    states: dict[str, Any],
    bundle: dict[str, Any],
    complete: bool,
    check: Callable[[], None],
) -> list[dict[str, Any]]:
    sources = list(core.GM) if model == "B" else ["Sun", "Moon"]
    require(
        block["included_sources"] == sources
        and block["gm_m3_s2"] == core.GM
        and block["model_id"]
        == f"r5-ssb-sun-moon{'-earth' if model == 'B' else ''}-point-v1",
        "model inventory",
    )
    rows = block["node_forces"]
    require(
        isinstance(rows, list)
        and len(rows) <= 28
        and (not complete or len(rows) == 28),
        "force row coverage",
    )
    result = []
    for k, row in enumerate(rows):
        check()
        tag, j = core.TAGS[k // 7], k % 7
        require(
            tag in states
            and row["profile"] == tag
            and number(row["epoch_tdb_s"]) == bundle["nodes_tdb_s"][j],
            "force row order",
        )
        position = states[tag][j][:3]
        require(
            vector(row["spacecraft_position_m"], 3) == position
            and list(row["per_source_m_s2"]) == sources,
            "force operands",
        )
        bodies = table[j]["states"]
        require(set(bodies) == set(core.GM), "complete force body operands")
        for body, radius in core.GUARDS.items():
            require(
                math.dist(position, bodies[body]["position_m"]) > radius,
                "saved-node domain",
            )
        diagnostics, reference = {}, {}
        with localcontext() as ctx:
            ctx.prec = 100
            for body in sources:
                ref, stability = core.reference_force(
                    position, bodies[body]["position_m"], core.GM[body]
                )
                reference[body] = ref
                diagnostics[body] = core.check_force(row["per_source_m_s2"][body], ref)
                diagnostics[body]["decimal80_minus100_m_s2"] = stability
            total = tuple(
                sum((v[d] for v in reference.values()), Decimal(0)) for d in range(3)
            )
            scale = sum((core.norm(v) for v in reference.values()), Decimal(0))
            diagnostics["total"] = core.check_force(row["total_m_s2"], total, scale)
            if tag.startswith("native"):
                sample = block["profiles"][tag]["result"]["samples"][j]
                force = vector(sample["acceleration_m_s2"], 3 * (1 + len(sources)))
                diagnostics["native_total"] = core.check_force(force[:3], total, scale)
                for n, body in enumerate(sources):
                    diagnostics["native_" + body] = core.check_force(
                        force[3 + 3 * n : 6 + 3 * n], reference[body]
                    )
        result.append(
            {"profile": tag, "epoch_tdb_s": row["epoch_tdb_s"], "forces": diagnostics}
        )
    return result


def model_comparisons(
    rows: list[dict[str, Any]],
    states: dict[str, Any],
    bundle: dict[str, Any],
    complete: bool,
) -> tuple[list[dict[str, Any]], bool]:
    require(
        len(rows) <= 7 and (not complete or len(rows) == 7),
        "numerical comparison coverage",
    )
    result, passed = [], True
    for j, row in enumerate(rows):
        require(
            number(row["epoch_tdb_s"]) == bundle["nodes_tdb_s"][j], "comparison epoch"
        )
        require(
            set(row["gates"]) == {"native_profile", "native_oracle", "oracle_profile"},
            "gate inventory",
        )
        diagnostics = {}
        for key, left, right, pos, vel in [
            ("native_profile", "native-normal", "native-tight", 0.01, 1e-5),
            ("native_oracle", "native-tight", "oracle-tight", 0.01, 1e-5),
            ("oracle_profile", "oracle-normal", "oracle-tight", 0.001, 1e-6),
        ]:
            value = core.check_difference(row[key], states[left][j], states[right][j])
            flag = core.check_gate(row["gates"][key], value, pos, vel)
            diagnostics[key] = value | {"gate": flag}
            passed = passed and flag
        require(
            passed or (not complete and j == len(rows) - 1),
            "data after failed numerical gate",
        )
        result.append({"epoch_tdb_s": row["epoch_tdb_s"], "comparisons": diagnostics})
    return result, passed


def sensitivity(
    rows: list[dict[str, Any]],
    states: dict[str, Any],
    bundle: dict[str, Any],
    complete: bool,
) -> tuple[list[dict[str, Any]], bool]:
    require(len(rows) <= 7 and (not complete or len(rows) == 7), "sensitivity coverage")
    result, passed = [], True
    for j, row in enumerate(rows):
        require(
            number(row["epoch_tdb_s"]) == bundle["nodes_tdb_s"][j], "sensitivity epoch"
        )
        values = {}
        for engine in ("native", "oracle"):
            key = engine + "_B_minus_A"
            values[key] = core.check_difference(
                row[key],
                states["A"][engine + "-tight"][j],
                states["B"][engine + "-tight"][j],
            )
        key = "oracle_minus_native_sensitivity"
        values[key] = core.check_difference(
            row[key],
            values["native_B_minus_A"]["right_minus_left_si"],
            values["oracle_B_minus_A"]["right_minus_left_si"],
        )
        flag = core.check_gate(row["gate"], values[key], 0.02, 2e-5)
        passed = passed and flag
        require(
            passed or (not complete and j == len(rows) - 1),
            "data after failed sensitivity gate",
        )
        result.append(
            {"epoch_tdb_s": row["epoch_tdb_s"], "values": values, "gate": flag}
        )
    return result, passed


def counts(report: dict[str, Any], node_reads: int, complete: bool) -> None:
    c = report["counts"]
    for stem, cap in (("native_arcs", 4),):
        a, r, n = [
            integer(c[stem + "_" + k], cap)
            for k in ("attempted", "returned", "completed")
        ]
        require(n <= r <= a and (not complete or n == r == a == 4), "native counters")
    a, r = [
        integer(c["native_guard_reads_" + k], 5424) for k in ("attempted", "returned")
    ]
    require(r <= a and (not complete or r == a == 5424), "native guard counters")
    a, r, n = [
        integer(report.get("oracle_solves_" + k, 0), 4)
        for k in ("attempted", "returned", "completed")
    ]
    require(n <= r <= a and (not complete or n == r == a == 4), "oracle solve counters")
    q = c["oracle"]
    ra, rc, sa, sc = [
        integer(q[k], cap)
        for k, cap in (
            ("rhs_attempted", 10000),
            ("rhs_completed", 10000),
            ("states_attempted", 30021),
            ("states_completed", 30021),
        )
    ]
    require(
        rc <= ra and node_reads + 3 * rc <= sc <= sa <= 3 * ra + 21,
        "RHS/query counters",
    )
    if complete:
        require(0 < ra == rc and sa == sc == 3 * ra + 21, "complete RHS/query counters")


def ledger(
    report: dict[str, Any],
    bundle: dict[str, Any],
    complete: bool,
    states: dict[str, Any],
) -> dict[str, Any]:
    labels = ["inputs", "initial identity"]
    labels += [
        f"node table {epoch} {body}"
        for epoch in bundle["nodes_tdb_s"]
        for body in core.GM
    ]
    profiles = [f"{m} {tag.replace('-', ' ')}" for m in ("A", "B") for tag in core.TAGS]
    labels += profiles + ["final identity"]
    events = report["calls"]
    require(
        isinstance(events, list)
        and [v["label"] for v in events] == labels[: len(events)]
        and (not complete or len(events) == len(labels)),
        "call ledger order/coverage",
    )
    end = 0.0
    timing_valid = True
    for event in events:
        start, stop = number(event["start_s"]), number(event["end_s"])
        require(type(event["returned"]) is bool, "call return flag")
        timing_valid = timing_valid and 0 <= end <= start <= stop < 60
        end = stop
        if complete:
            require(event["returned"] is True, "complete call did not return")
    elapsed = number(report["elapsed_sample_before_flush_s"])
    timing_valid = timing_valid and 0 <= end <= elapsed < 60
    require(not complete or timing_valid, "study timing gate")
    native_events = [
        v for v in events if v["label"] in profiles and " native " in v["label"]
    ]
    oracle_events = [
        v for v in events if v["label"] in profiles and " oracle " in v["label"]
    ]
    require(
        report["counts"]["native_arcs_attempted"] <= len(native_events),
        "native attempt ledger",
    )
    require(
        report.get("oracle_solves_attempted", 0) == len(oracle_events),
        "oracle attempt ledger",
    )
    by_label = {e["label"]: e for e in events}
    native_valid = 0
    for model, profiles_valid in states.items():
        for tag in profiles_valid:
            label = f"{model} {tag.replace('-', ' ')}"
            require(
                label in by_label and by_label[label]["returned"] is True,
                "validated profile return ledger",
            )
            native_valid += int(tag.startswith("native"))
    require(
        native_valid <= report["counts"]["native_arcs_completed"],
        "native completion ledger",
    )
    body_returns = sum(
        e["returned"] is True for e in events if e["label"].startswith("node table ")
    )
    node_reads = sum(len(p["states"]) for p in report["body_table"])
    require(body_returns == node_reads, "body return ledger")
    prior = {
        "rhs_attempted": 0,
        "rhs_completed": 0,
        "states_attempted": 21,
        "states_completed": 21,
    }
    valid_oracles = 0
    for model in ("A", "B"):
        for tag in core.TAGS:
            if not tag.startswith("oracle") or tag not in states.get(model, {}):
                continue
            r = report["models"][model]["profiles"][tag]["result"]
            files.same(r["counts_before"], prior, "oracle before counters")
            nfev = integer(r["nfev"], 10000)
            after = {
                key: value + (3 * nfev if key.startswith("states") else nfev)
                for key, value in prior.items()
            }
            files.same(r["counts_after"], after, "oracle after counters")
            prior = after
            valid_oracles += 1
    if complete:
        files.same(prior, report["counts"]["oracle"], "final oracle counters")
        require(valid_oracles == 4, "four validated oracle results")
    return {
        "events_checked": len(events),
        "timing_assertions_consistent": timing_valid,
        "oracle_results_with_reconciled_counts": valid_oracles,
        "internal_native_reads_recounted": False,
        "historical_flush_remeasured": False,
    }


def check_saved(
    report: dict[str, Any], bundle: dict[str, Any], check: Callable[[], None]
) -> dict[str, Any]:
    """Pure injected fixture boundary; never grants study_verified=true."""
    complete = header(report)
    if "inputs" in report:
        files.same(report["inputs"], bundle, "frozen wire inputs")
    else:
        require(
            not complete and not report["body_table"] and not report["models"],
            "missing input evidence",
        )
    nodes = body_table(report, bundle, complete)
    counts(report, nodes, complete)
    models = report["models"]
    require(
        list(models) == ["A", "B"][: len(models)]
        and (not complete or len(models) == 2),
        "model order",
    )
    error_stage = report.get("first_error", report.get("error", {})).get("stage")
    result: dict[str, Any] = {"models": {}, "unavailable": [], "study_verified": False}
    all_states, all_gates = {}, True
    minima: dict[str, dict[str, float]] = {}
    for model, block in models.items():
        check()
        require(nodes == 21, "models require complete body table")
        if model == "B":
            require(
                all_gates
                and len(result["models"]["A"]["numerical_comparisons"]) == 7
                and len(all_states["A"]) == 4,
                "downstream data after incomplete model A",
            )
        require(
            list(block["profiles"]) == list(core.TAGS)[: len(block["profiles"])]
            and (not complete or len(block["profiles"]) == 4),
            "profile order",
        )
        parsed = {}
        for tag, entry in block["profiles"].items():
            check()
            try:
                parsed[tag] = core.check_profile(
                    entry, model, tag, bundle["state_si"], bundle["epoch_tdb_s"]
                )
            except FAILURES as exc:
                label = f"{model} {tag.replace('-', ' ')}"
                require(
                    not complete and error_stage == label,
                    "invalid nonfailing profile: " + label,
                )
                result["unavailable"].append({"profile": label, "reason": str(exc)})
                continue
            engine = tag.split("-")[0]
            distances = entry["result"]["minimum_checked_distances_m"]
            require(set(distances) == set(core.GUARDS), "profile minimum inventory")
            parsed_minima = {b: number(distances[b]) for b in core.GUARDS}
            require(
                all(parsed_minima[b] > core.GUARDS[b] for b in core.GUARDS),
                "profile exclusion guard",
            )
            if engine in minima:
                require(
                    all(parsed_minima[b] <= minima[engine][b] for b in core.GUARDS),
                    "cumulative minima",
                )
            minima[engine] = parsed_minima
        all_states[model] = parsed
        fields = force_rows(
            block, model, report["body_table"], parsed, bundle, complete, check
        )
        comparisons, passed = model_comparisons(
            block["numerical_comparison"], parsed, bundle, complete
        )
        all_gates = all_gates and passed
        result["models"][model] = {
            "profiles_checked": list(parsed),
            "node_forces": fields,
            "numerical_comparisons": comparisons,
        }
    differences, passed = sensitivity(
        report["signed_model_differences"], all_states, bundle, complete
    )
    all_gates = all_gates and passed
    require(not complete or all_gates, "falsely successful numerical gates")
    result["signed_model_differences"] = differences
    result["ledger"] = ledger(report, bundle, complete, all_states)
    for engine, last in minima.items():
        saved = report[engine + "_minimum_checked_distances_m"]
        if complete:
            files.same(saved, last, "final cumulative minima")
    check()
    result["complete_saved_data_checked"] = complete
    result["source_study_status"] = report["status"]
    return result


def fresh() -> None:
    require(
        not any(
            k.startswith(("numpy", "scipy", "spiceypy", "tudatpy", "space_nav"))
            for k in sys.modules
        ),
        "offline execution requires fresh process",
    )


def audit_file(
    path: Path, *, clock: Callable[[], float] = monotonic, start_s: float | None = None
) -> dict[str, Any]:
    """Read-only reference audit; injected clocks cannot grant reference verification."""
    budget = Budget(clock, PROCESS_START if start_s is None else start_s)
    reference = clock is monotonic and budget.start == PROCESS_START
    result: dict[str, Any] = {
        "contract": "ADR0143",
        "audit_status": "rejected",
        "study_verified": False,
        "audit_mode": "reference" if reference else "injected-test",
        "source_study_status": "unavailable",
        "native_calls": 0,
        "budget_s": 10.0,
    }
    try:
        budget.check()
        if clock is monotonic:
            require(reference, "process-start baseline required")
            fresh()
        for name, expected in PINS.items():
            require(
                files.digest(HERE / name, budget.check) == expected,
                "prepared offline helper drift",
            )
        raw = path.read_bytes()
        budget.check()
        result["evidence_sha256"] = sha256(raw).hexdigest()
        report = files.parse(raw)
        result["source_study_status"] = report.get("status", "unavailable")
        require(
            report.get("adapter_mode") == "reference", "injected study cannot verify R5"
        )
        bundle = files.load_inputs(budget.check)
        checked = check_saved(report, bundle, budget.check)
        if "identity" in report:
            result["file_identity_checks"] = files.verify_snapshot(
                report["identity"], bundle["original_kernel_manifest"], budget.check
            )
        if "final_identity" in report:
            require("identity" in report, "final identity without initial identity")
            files.same(
                report["identity"], report["final_identity"], "before/after identity"
            )
        if report["status"] == "passed":
            require(
                "identity" in report and "final_identity" in report,
                "complete identity evidence",
            )
        result["checks"] = checked
        result["source_sha256"] = {
            Path(__file__).name: files.digest(Path(__file__), budget.check),
            **PINS,
        }
        result["audit_revision"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=1
        ).strip()
        budget.check()
        result["audit_status"] = "passed" if report["status"] == "passed" else "partial"
        result["study_verified"] = reference and result["audit_status"] == "passed"
    except FAILURES as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    try:
        result["elapsed_before_flush_s"] = budget.elapsed()
    except (ValueError, TypeError, ArithmeticError):
        result["elapsed_before_flush_s"] = None
    return result


def save(result: dict[str, Any], stream: TextIO, budget: Budget) -> dict[str, Any]:
    """Exclusive caller-owned stream; retain failed finalization without science retries."""
    result["finalization_gate"] = "passed"
    json.dump(result, stream, indent=2, allow_nan=False)
    stream.flush()
    try:
        budget.check()
    except (ValueError, TypeError, ArithmeticError) as exc:
        if "error" in result:
            result["first_error"] = dict(result["error"])
        result.update(
            audit_status="rejected",
            study_verified=False,
            finalization_gate="failed",
            error={"type": type(exc).__name__, "message": str(exc)},
        )
        try:
            result["actual_elapsed_after_flush_s"] = budget.elapsed()
        except (ValueError, TypeError, ArithmeticError):
            result["actual_elapsed_after_flush_s"] = None
        stream.seek(0)
        stream.truncate()
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.flush()
    return result


def execute(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Fresh-process, exclusive finite output. No scientific imports or native calls."""
    fresh()
    with output_path.open("x", encoding="utf-8") as stream:
        return save(audit_file(input_path), stream, Budget(monotonic, PROCESS_START))
