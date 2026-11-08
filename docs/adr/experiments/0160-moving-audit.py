"""Independent ADR0159 saved-data audit; SI, TDB/J2000, SSB/J2000/NONE.

Only immutable pure validation utilities are shared. Candidate/study modules
are never imported; moving operands and binary64 fields are rebuilt here.
"""

from __future__ import annotations

# ruff: noqa: E402 -- The cooperative clock includes the remaining imports.
from time import monotonic

PROCESS_START = monotonic()

from collections.abc import Callable
from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, TextIO

ROOT = Path(__file__).resolve().parents[3]
ARM_NAMES = ("compensated", "flattened_craft", "omitted_q")
SOURCE_ORDER = ("Sun", "Earth", "Moon")
MODELS = {"A": ("Sun", "Moon"), "B": ("Sun", "Moon", "Earth")}
RADII_M = {"Sun": 696000000.0, "Earth": 6378136.6, "Moon": 1737400.0}
LIMITS = {
    "six_state_assemblies": 7,
    "source_rows": 21,
    "reference_fields": 168,
    "binary64_fields": 63,
    "model_totals": 14,
}
INPUT_KEYS = (
    "position_m",
    "initial",
    "gm_m3_s2",
    "input_sha256",
    "source_provenance",
    "identity",
    "zero_reference",
)
HELPERS = (
    "0160-moving-inputs.py",
    "0160-moving-reference.py",
    "0160-moving-study.py",
    "0160-moving-audit.py",
    "0157-fixed-gravity-inputs.py",
    "0157-fixed-gravity-reference.py",
    "0157-fixed-gravity-audit.py",
    "0153-real-ephemeris-oracle.py",
    "0145-short-coast-evidence.py",
)
FAILURES = (
    ValueError,
    TypeError,
    KeyError,
    IndexError,
    AttributeError,
    OSError,
    ImportError,
    RuntimeError,
    ArithmeticError,
)
BASE_SHA256 = "c53cdbe8b556029dac311a3065bf31a07b0211235fa2af2c548a33387a976ef2"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_helper(
    root: Path, name: str, expected: str, check: Callable[[], None] = lambda: None
) -> ModuleType:
    path = root / "docs/adr/experiments" / name
    check()
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == expected, "audit helper SHA256: " + name)
    spec = importlib.util.spec_from_file_location(
        "moving_audit_" + name.replace("-", "_"), path
    )
    require(spec is not None and spec.loader is not None, "audit helper loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    check()
    return module


BASE = load_helper(ROOT, "0157-fixed-gravity-audit.py", BASE_SHA256)
number = BASE.number
vector = BASE.vector
same = BASE.same
parse = BASE.parse
finite_tree = BASE._finite_tree


class Budget:
    """Count actual audit work, including fields absent from a failed source."""

    def __init__(self, clock: Callable[[], float], start_s: float) -> None:
        self.clock = clock
        self.start_s = number(start_s, "process start")
        self.counts = {name: {"attempted": 0, "completed": 0} for name in LIMITS}
        self.ledger: list[dict[str, str]] = []

    def elapsed(self) -> float:
        return number(self.clock(), "clock") - self.start_s

    def check(self) -> None:
        require(0 <= self.elapsed() < 10.0, "audit deadline/clock")

    def event(self, operation: str, phase: str) -> None:
        require(operation in LIMITS and phase in ("attempt", "complete"), "audit event")
        counter = self.counts[operation]
        if phase == "attempt":
            self.check()
            require(
                counter["attempted"] < LIMITS[operation], "audit work cap: " + operation
            )
            counter["attempted"] += 1
        else:
            require(
                counter["completed"] < counter["attempted"], "audit completion ledger"
            )
            counter["completed"] += 1
        self.ledger.append({"operation": operation, "phase": phase})
        self.check()

    def consume_reference(self, phase: str) -> None:
        self.event("reference_fields", phase)

    def consume_model(self, phase: str) -> None:
        self.event("model_totals", phase)


def helper_hashes(root: Path, check: Callable[[], None]) -> dict[str, str]:
    values = {}
    for name in HELPERS:
        check()
        values[name] = sha256(
            (root / "docs/adr/experiments" / name).read_bytes()
        ).hexdigest()
        check()
    return values


def encoded(values: list[Fraction]) -> list[dict[str, str]]:
    return [
        {"numerator": str(value.numerator), "denominator": str(value.denominator)}
        for value in values
    ]


def reconstruct_motion(initial: dict[str, Any], elapsed_s: float) -> dict[str, Any]:
    """Rebuild the prescribed inputs and actual sums without candidate imports."""
    position = vector(initial["position_m"], "initial position")
    velocity = vector(initial["velocity_m_s"], "initial velocity")
    elapsed = number(elapsed_s, "elapsed_s")
    require(0 <= elapsed <= 300, "elapsed_s: outside probe interval")
    exact_s = Fraction.from_float(elapsed)
    coefficients = (Fraction(-1), Fraction(1, 2), Fraction(-1, 4))
    ideal_q = [a * exact_s * exact_s / 2 for a in coefficients]
    ideal_w = [a * exact_s for a in coefficients]
    q, w = [float(v) for v in ideal_q], [float(v) for v in ideal_w]
    drift = [v * elapsed for v in velocity]
    result = {
        "label": "controlled-kinematic-arithmetic-probe",
        "elapsed_s": elapsed,
        "elapsed_hex": elapsed.hex(),
        "q_ideal_m": encoded(ideal_q),
        "w_ideal_m_s": encoded(ideal_w),
        "q_m": q,
        "q_hex": [v.hex() for v in q],
        "q_ratios": encoded([Fraction.from_float(v) for v in q]),
        "w_m_s": w,
        "w_hex": [v.hex() for v in w],
        "w_ratios": encoded([Fraction.from_float(v) for v in w]),
        "drift_m": drift,
        "position_m": [math.fsum((position[j], drift[j], q[j])) for j in range(3)],
        "velocity_m_s": [math.fsum((velocity[j], w[j])) for j in range(3)],
    }
    finite_tree(result)
    return result


def reconstruct_geometry(
    source: dict[str, Any], initial: dict[str, Any], motion: dict[str, Any], arm: str
) -> dict[str, Any]:
    """Assemble operands and check the domain before evaluating any field."""
    require(arm in ARM_NAMES, "candidate arm inventory")
    raw = source["state_si"]
    require(type(raw) is list and len(raw) == 6, "source SI state length")
    values = [number(v, "source SI state") for v in raw]
    r0 = vector(initial["position_m"], "initial position")
    drift, q = vector(motion["drift_m"], "drift_m"), vector(motion["q_m"], "q_m")
    position = vector(motion["position_m"], "export position_m")
    low = number(source["lo_s"], "lo_s")
    correction = [values[j + 3] * low for j in range(3)]
    if arm == "compensated":
        separation = [
            math.fsum((values[j], -r0[j], -drift[j], -q[j], correction[j]))
            for j in range(3)
        ]
    elif arm == "flattened_craft":
        separation = [
            math.fsum((values[j], -position[j], correction[j])) for j in range(3)
        ]
    else:
        separation = [
            math.fsum((values[j], -r0[j], -drift[j], correction[j])) for j in range(3)
        ]
    guard = Fraction.from_float(RADII_M[source["body"]])
    require(
        sum((Fraction.from_float(v) ** 2 for v in separation), Fraction()) > guard**2,
        "exterior domain: " + str(source["body"]),
    )
    radius = number(math.hypot(*separation), "separation norm")
    squared = number(radius * radius, "squared separation norm")
    require(radius > 0 and squared > 0, "positive separation norms required")
    result = {"separation_m": separation, "rephasing_m": correction}
    finite_tree(result)
    return result


def reconstruct_arm(
    source: dict[str, Any],
    initial: dict[str, Any],
    motion: dict[str, Any],
    gm_m3_s2: float,
    arm: str,
    geometry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay the specified binary64 field independently of the study."""
    geometry = (
        reconstruct_geometry(source, initial, motion, arm)
        if geometry is None
        else geometry
    )
    gm = number(gm_m3_s2, "gm_m3_s2")
    require(gm > 0, "positive GM")
    radius = math.hypot(*geometry["separation_m"])
    force = [
        gm * (component / radius) / (radius * radius)
        for component in geometry["separation_m"]
    ]
    result = {**geometry, "acceleration_m_s2": force}
    finite_tree(result)
    return result


def reconstruct_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    require(
        len(rows) == 3
        and [r["source_row"]["body"] for r in rows] == list(SOURCE_ORDER),
        "model source inventory",
    )
    sources = {r["source_row"]["body"]: r["arms"] for r in rows}
    return {
        model: {
            arm: {
                "acceleration_m_s2": [
                    math.fsum(
                        sources[body][arm]["acceleration_m_s2"][j] for body in bodies
                    )
                    for j in range(3)
                ]
            }
            for arm in ARM_NAMES
        }
        for model, bodies in MODELS.items()
    }


def expected_ledger() -> list[dict[str, str]]:
    result = []
    for _ in range(7):
        for phase in ("attempt", "complete"):
            result.append({"operation": "six_state_assemblies", "phase": phase})
        for _ in SOURCE_ORDER:
            result.append({"operation": "source_rows", "phase": "attempt"})
            for operation, count in (("binary64_fields", 3), ("reference_fields", 8)):
                for _ in range(count):
                    result.extend(
                        {"operation": operation, "phase": phase}
                        for phase in ("attempt", "complete")
                    )
            result.append({"operation": "source_rows", "phase": "complete"})
        for _ in MODELS:
            result.extend(
                {"operation": "model_totals", "phase": phase}
                for phase in ("attempt", "complete")
            )
    return result


def check_ledger(report: dict[str, Any]) -> dict[str, Any]:
    expected, ledger = expected_ledger(), report["ledger"]
    require(type(ledger) is list and len(ledger) <= len(expected), "source ledger cap")
    same(ledger, expected[: len(ledger)], "source operation prefix")
    counts = {name: {"attempted": 0, "completed": 0} for name in LIMITS}
    for entry in ledger:
        counts[entry["operation"]][
            "attempted" if entry["phase"] == "attempt" else "completed"
        ] += 1
    same(report["counts"], counts, "source counters")
    if report["status"] == "passed":
        same(ledger, expected, "complete source operation coverage")
    return counts


def check_header(report: dict[str, Any]) -> None:
    for key, value in {
        "contract": "ADR0159",
        "study": "controlled-moving-assembly-v1",
        "position_units": "m",
        "velocity_units": "m/s",
        "optimizer_calls": 0,
    }.items():
        same(report[key], value, "source " + key)
    # Reuse only unchanged schema/finalization validation, not old fixed-X science.
    BASE.check_header(
        {**report, "contract": "ADR0156", "study": "fixed-position-real-gravity-v1"}
    )


def failed_stage(report: dict[str, Any]) -> str | None:
    return report.get("first_error", report.get("error", {})).get("stage")


def check_failure_prefix(report: dict[str, Any], counts: dict[str, Any]) -> None:
    if report["status"] == "passed":
        return
    stage = failed_stage(report)
    require(type(stage) is str, "missing first failure stage")
    if "first_error" in report and report["error"]["stage"] != "finalization":
        same(report["first_error"], report["error"], "earliest failure changed")
    if stage == "inputs":
        require(
            not report["ledger"]
            and not report["motions"]
            and not report["rows"]
            and not report["totals"],
            "input failure after work",
        )
    elif stage == "identity":
        same(report["ledger"], expected_ledger(), "premature identity failure")
    elif stage != "finalization":
        require(bool(report["ledger"]), "work failure without attempt")
        operation = report["ledger"][-1]["operation"]
        if operation == "six_state_assemblies":
            expected = f"motion:{counts['six_state_assemblies']['attempted'] - 1}"
        elif operation == "model_totals":
            t = counts["source_rows"]["completed"] // 3 - 1
            model = ("A", "B")[(counts["model_totals"]["attempted"] - 1) % 2]
            expected = f"totals:{t}:{model}"
        else:
            expected = f"source:{counts['source_rows']['attempted'] - 1}"
        same(stage, expected, "failure stage/operation prefix")


def partial_value(actual: Any, expected: Any, label: str) -> None:
    """Validate only returned data in a final incomplete construction."""
    require(type(actual) is type(expected), label + ": partial value type")
    if type(expected) is dict:
        require(set(actual) <= set(expected), label + ": unknown partial keys")
        for key in actual:
            partial_value(actual[key], expected[key], label + "." + key)
    elif type(expected) is list:
        require(len(actual) <= len(expected), label + ": partial array length")
        for i, value in enumerate(actual):
            partial_value(value, expected[i], f"{label}[{i}]")
    else:
        same(actual, expected, label)


def progress_fields(progress: Any) -> list[tuple[str, str, Any]]:
    require(type(progress) is dict, "reference progress object")
    return BASE.reference_progress({"reference": progress.get("reference", {})})


def matched_failure(
    report: dict[str, Any], stage: str, error: BaseException, budget: Budget
) -> dict[str, str]:
    budget.check()
    actual = {"stage": stage, "type": type(error).__name__, "message": str(error)}
    require(report["status"] == "partial", "independent failure for successful source")
    same(
        actual, report.get("first_error", report["error"]), "reproduced source failure"
    )
    return actual


def check_saved(
    report: dict[str, Any], bundle: dict[str, Any], references: Any, budget: Budget
) -> dict[str, Any]:
    """Check raw available prefixes independently; partial is never science success."""
    check_header(report)
    counts = check_ledger(report)
    check_failure_prefix(report, counts)
    if "identity_after" in report:
        same(report["identity_after"], report["inputs"], "source final identity")
    else:
        require(report["status"] == "partial", "missing complete final identity")
    if "inputs" in report:
        same(
            report["inputs"], {key: bundle[key] for key in INPUT_KEYS}, "frozen inputs"
        )
    else:
        require(
            report["status"] == "partial" and not report["ledger"],
            "missing frozen inputs",
        )
    motions, rows, totals = report["motions"], report["rows"], report["totals"]
    require(
        all(type(value) is list for value in (motions, rows, totals)),
        "saved list schema",
    )
    require(
        len(motions) <= 7 and len(rows) <= 21 and len(totals) <= 7, "saved list caps"
    )
    for name, values in (("six_state_assemblies", motions), ("source_rows", rows)):
        require(
            counts[name]["completed"]
            <= len(values)
            <= counts[name]["attempted"]
            <= len(values) + 1
            and len(values) - counts[name]["completed"] <= 1,
            "returned availability ledger: " + name,
        )
    require(len(totals) <= len(rows) // 3, "totals require three source rows")
    raw_rows = bundle["rows"]
    require(type(raw_rows) is list and len(raw_rows) == 21, "frozen source coverage")
    checked_motions, checked_rows, checked_totals = [], [], []
    reference_counts = BASE.row_reference_counts(report["ledger"])
    first_failure = None
    for t, block in enumerate(motions):
        require(first_failure is None, "motion after required failure")
        budget.event("six_state_assemblies", "attempt")
        same(block["index"], t, "motion index")
        rebuilt_motion = reconstruct_motion(
            bundle["initial"], raw_rows[3 * t]["elapsed_s"]
        )
        complete_motion = "assessment" in block
        if complete_motion:
            same(block["motion"], rebuilt_motion, f"motion {t} operands")
        else:
            require(
                t == len(motions) - 1 and report["status"] == "partial",
                "incomplete earlier motion",
            )
            partial_value(
                block["motion"], rebuilt_motion, f"motion {t} returned prefix"
            )
        motion_assessment = None
        if complete_motion:
            motion_assessment = references.assess_motion(
                bundle["initial"], rebuilt_motion
            )
            same(
                block["assessment"],
                motion_assessment,
                f"motion {t} independent assessment",
            )
            require(type(motion_assessment.get("passed")) is bool, "motion gate type")
            budget.event("six_state_assemblies", "complete")
            if not motion_assessment["passed"]:
                first_failure = f"motion:{t}"
            if t == 0:
                same(
                    rebuilt_motion["position_m"],
                    bundle["initial"]["position_m"],
                    "zero position",
                )
                same(
                    rebuilt_motion["velocity_m_s"],
                    bundle["initial"]["velocity_m_s"],
                    "zero velocity",
                )
        checked_motions.append(
            {
                "index": t,
                "motion": rebuilt_motion,
                "assessment_checked": complete_motion,
                "assessment": motion_assessment,
            }
        )
        for index in range(3 * t, min(3 * t + 3, len(rows))):
            require(
                complete_motion and first_failure is None,
                "source after incomplete/failed motion",
            )
            budget.event("source_rows", "attempt")
            row, raw = rows[index], raw_rows[index]
            same(row["index"], index, "source index")
            same(row["source_row"], raw, "raw source")
            require(raw["body"] == SOURCE_ORDER[index % 3], "source body order")
            require(
                type(row["arms"]) is dict
                and list(row["arms"]) == list(ARM_NAMES)[: len(row["arms"])],
                "source arm prefix",
            )
            require(
                len(row["arms"]) == 3 or index == len(rows) - 1,
                "earlier incomplete source",
            )
            rebuilt_arms = {}
            assessment, progress, reproduced = None, {}, None
            geometry_arms = {}
            try:
                for arm in ARM_NAMES:
                    geometry_arms[arm] = reconstruct_geometry(
                        raw, bundle["initial"], rebuilt_motion, arm
                    )
                references.preflight_source(
                    raw,
                    bundle["initial"],
                    rebuilt_motion,
                    bundle["gm_m3_s2"][raw["body"]],
                    RADII_M[raw["body"]],
                    geometry_arms,
                    progress=progress,
                )
                finite_tree(progress)
            except FAILURES as error:
                require(
                    index == len(rows) - 1
                    and t == len(motions) - 1
                    and not row["arms"]
                    and "assessment" not in row,
                    "preflight failure before saved field work",
                )
                reproduced = matched_failure(report, f"source:{index}", error, budget)
                first_failure = f"source:{index}"
            if reproduced is None:
                for arm in row["arms"]:
                    budget.event("binary64_fields", "attempt")
                    rebuilt_arms[arm] = reconstruct_arm(
                        raw,
                        bundle["initial"],
                        rebuilt_motion,
                        bundle["gm_m3_s2"][raw["body"]],
                        arm,
                        geometry_arms[arm],
                    )
                    budget.event("binary64_fields", "complete")
                    same(row["arms"][arm], rebuilt_arms[arm], f"source {index} {arm}")
            if len(rebuilt_arms) == 3:
                try:
                    assessment = references.assess_source(
                        raw,
                        bundle["initial"],
                        rebuilt_motion,
                        bundle["gm_m3_s2"][raw["body"]],
                        RADII_M[raw["body"]],
                        rebuilt_arms,
                        budget.consume_reference,
                        progress=progress,
                    )
                    finite_tree(assessment)
                except FAILURES as error:
                    require(
                        index == len(rows) - 1 and "assessment" not in row,
                        "independent source failure before saved completion",
                    )
                    reproduced = matched_failure(
                        report, f"source:{index}", error, budget
                    )
                    first_failure = f"source:{index}"
            if "assessment" in row:
                require(
                    assessment is not None and type(assessment.get("passed")) is bool,
                    "missing independent source gate",
                )
                same(row["assessment"], assessment, f"source {index} assessment")
                budget.event("source_rows", "complete")
                if not assessment["passed"]:
                    first_failure = f"source:{index}"
                if t == 0:
                    same(
                        rebuilt_arms["compensated"],
                        bundle["zero_reference"]["sources"][raw["body"]],
                        "saved elapsed-zero source",
                    )
            else:
                require(
                    index == len(rows) - 1
                    and t == len(motions) - 1
                    and report["status"] == "partial",
                    "missing source completion",
                )
            saved_progress = row.get("reference_progress", {})
            retained_fields = progress_fields(saved_progress)
            same(
                len(retained_fields),
                reference_counts[index]["completed"],
                "retained reference count",
            )
            if "assessment" in row or reproduced is not None:
                same(saved_progress, progress, "completed reference progress")
            else:
                require(
                    set(saved_progress) <= set(progress),
                    "partial reference progress keys",
                )
                if row["arms"] or reference_counts[index]["attempted"]:
                    same(
                        set(saved_progress),
                        set(progress),
                        "completed preflight metadata",
                    )
                if saved_progress:
                    require("reference" in saved_progress, "missing reference prefix")
                for key in saved_progress:
                    if key != "reference":
                        same(
                            saved_progress[key],
                            progress[key],
                            "preflight metadata " + key,
                        )
                for profile, geometry, field in retained_fields:
                    same(
                        field,
                        progress["reference"][profile][geometry],
                        "retained reference field",
                    )
            checked = {
                "index": index,
                "arms": rebuilt_arms,
                "assessment": assessment,
                "reference_progress": progress,
                "assessment_checked": "assessment" in row,
            }
            if reproduced is not None:
                checked["reproduced_failure"] = reproduced
            checked_rows.append(checked)
        if t < len(totals):
            require(
                first_failure is None
                and len(checked_rows) >= 3 * t + 3
                and all(r["assessment_checked"] for r in checked_rows[-3:]),
                "model after incomplete/failed sources",
            )
            block_total = totals[t]
            same(block_total["index"], t, "model time index")
            same(
                block_total["elapsed_s"],
                raw_rows[3 * t]["elapsed_s"],
                "model elapsed_s",
            )
            rebuilt_totals = reconstruct_totals(rows[3 * t : 3 * t + 3])
            same(block_total["arms"], rebuilt_totals, "binary64 model sums")
            model_progress = {}
            try:
                model_results = references.assess_totals(
                    [r["assessment"] for r in checked_rows[-3:]],
                    rebuilt_totals,
                    consume_model=budget.consume_model,
                    progress=model_progress,
                )
                finite_tree(model_results)
            except FAILURES as error:
                require(
                    t == len(totals) - 1 and report["status"] == "partial",
                    "earlier independent model failure",
                )
                n = budget.counts["model_totals"]["attempted"] - 1
                matched_failure(
                    report, f"totals:{t}:{('A', 'B')[n % 2]}", error, budget
                )
                model_results = model_progress
            saved_models = block_total.get("assessment", {})
            require(
                type(saved_models) is dict
                and list(saved_models) == list(model_results)[: len(saved_models)],
                "saved model assessment prefix",
            )
            for model in saved_models:
                same(saved_models[model], model_results[model], f"model {t} {model}")
                require(
                    type(model_results[model].get("passed")) is bool, "model gate type"
                )
                if not model_results[model]["passed"]:
                    first_failure = f"totals:{t}:{model}"
                if t == 0:
                    same(
                        rebuilt_totals[model]["compensated"],
                        bundle["zero_reference"]["totals"][model],
                        "saved elapsed-zero model",
                    )
            require(
                len(saved_models) == len(model_results)
                or t == len(totals) - 1
                and report["status"] == "partial",
                "missing earlier model result",
            )
            checked_totals.append(
                {
                    "index": t,
                    "arms": rebuilt_totals,
                    "assessment": model_results,
                    "models_checked": list(saved_models),
                }
            )
        if t + 1 < len(motions):
            require(
                len(rows) >= 3 * t + 3
                and t < len(totals)
                and len(totals[t].get("assessment", {})) == 2,
                "later motion after incomplete time block",
            )
    same(len(checked_rows), len(rows), "source data beyond motion coverage")
    same(
        sum("assessment" in m for m in motions),
        counts["six_state_assemblies"]["completed"],
        "completed motion availability",
    )
    same(
        sum("assessment" in r for r in rows),
        counts["source_rows"]["completed"],
        "completed source availability",
    )
    same(
        sum(len(r["arms"]) for r in rows),
        counts["binary64_fields"]["completed"],
        "completed binary64 availability",
    )
    same(
        sum(len(t.get("assessment", {})) for t in totals),
        counts["model_totals"]["completed"],
        "completed model availability",
    )
    if first_failure is not None:
        require(
            report["status"] == "partial" and failed_stage(report) == first_failure,
            "earliest required gate failure",
        )
    if report["status"] == "passed":
        require(
            len(motions) == 7
            and len(rows) == 21
            and len(totals) == 7
            and first_failure is None,
            "complete saved data unavailable",
        )
    budget.check()
    return {
        "motions": checked_motions,
        "source_rows": checked_rows,
        "model_totals": checked_totals,
        "source_counts": counts,
        "first_required_gate_failure": first_failure,
        "complete_saved_data_checked": report["status"] == "passed",
    }


def safe_elapsed(budget: Budget) -> float | None:
    try:
        return number(budget.elapsed(), "elapsed clock")
    except FAILURES:
        return None


def save(result: dict[str, Any], stream: TextIO, budget: Budget) -> dict[str, Any]:
    result["elapsed_before_flush_s"] = safe_elapsed(budget)
    result["finalization_gate"] = "passed"
    try:
        budget.check()
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.flush()
        budget.check()
    except FAILURES as error:
        if "error" in result:
            result.setdefault("first_error", dict(result["error"]))
        result.update(
            audit_status="rejected",
            scientific_verified=False,
            finalization_gate="failed",
            error={
                "stage": "finalization",
                "type": type(error).__name__,
                "message": str(error),
            },
        )
        result["elapsed_after_failed_flush_s"] = safe_elapsed(budget)
        stream.seek(0)
        stream.truncate()
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.flush()
    return result


def audit(
    path: Path,
    output: Path,
    *,
    root: Path = ROOT,
    clock: Callable[[], float] = monotonic,
    start_s: float | None = None,
    inputs_loader: Any = None,
    references: Any = None,
) -> dict[str, Any]:
    """Audit a fresh finite result; injected fixtures can never qualify science."""
    start = (
        (PROCESS_START if clock is monotonic else clock())
        if start_s is None
        else start_s
    )
    budget = Budget(clock, start)
    injected = (
        inputs_loader is not None or references is not None or clock is not monotonic
    )
    result: dict[str, Any] = {
        "contract": "ADR0159",
        "audit_status": "rejected",
        "scientific_verified": False,
        "adapter_mode": "injected-test" if injected else "reference",
        "source_study_status": "unavailable",
        "native_calls": 0,
        "kernel_loads": 0,
        "gm_acquisitions": 0,
        "spacecraft_propagations": 0,
        "scientific_imports": 0,
        "optimizer_calls": 0,
        "budget_s": 10.0,
        "counts": budget.counts,
        "ledger": budget.ledger,
    }
    with output.open("x", encoding="utf-8") as stream:
        stage = "inputs"
        try:
            budget.check()
            if not injected:
                require(
                    budget.start_s <= PROCESS_START,
                    "audit process-start baseline was reset",
                )
                BASE.fresh()
            raw = path.read_bytes()
            budget.check()
            result["evidence_sha256"] = sha256(raw).hexdigest()
            report = parse(raw)
            result["source_study_status"] = report.get("status", "unavailable")
            hashes = (
                helper_hashes(root, budget.check)
                if not injected or inputs_loader is None or references is None
                else {}
            )
            if not injected:
                if "helper_sha256" in report:
                    same(report["helper_sha256"], hashes, "saved helper identity")
                else:
                    require(
                        report.get("status") == "partial"
                        and failed_stage(report) == "inputs"
                        and not report["ledger"],
                        "missing saved helper identity",
                    )
                result["helper_sha256"] = hashes
            if inputs_loader is None:
                inputs_loader = load_helper(
                    root, HELPERS[0], hashes[HELPERS[0]], budget.check
                ).load_inputs
            if references is None:
                references = load_helper(
                    root, HELPERS[1], hashes[HELPERS[1]], budget.check
                )
            bundle = inputs_loader(root, budget.check)
            stage = "saved-data"
            result["checks"] = check_saved(report, bundle, references, budget)
            if not injected:
                stage = "identity"
                same(
                    helper_hashes(root, budget.check),
                    hashes,
                    "audit final helper identity",
                )
                same(
                    inputs_loader(root, budget.check),
                    bundle,
                    "audit final input identity",
                )
            result["audit_status"] = (
                "passed" if report["status"] == "passed" else "partial"
            )
            result["scientific_verified"] = (
                not injected
                and report["adapter_mode"] == "reference"
                and result["audit_status"] == "passed"
            )
            budget.check()
        except FAILURES as error:
            result.update(
                audit_status="rejected",
                scientific_verified=False,
                error={
                    "stage": stage,
                    "type": type(error).__name__,
                    "message": str(error),
                },
            )
        return save(result, stream, budget)


if __name__ == "__main__":
    require(len(sys.argv) == 3, "usage: audit.py SAVED_STUDY EXCLUSIVE_AUDIT")
    value = audit(Path(sys.argv[1]), Path(sys.argv[2]))
    print(
        json.dumps(
            {
                k: value[k]
                for k in ("audit_status", "scientific_verified", "source_study_status")
            },
            allow_nan=False,
        )
    )
    raise SystemExit(0 if value["audit_status"] in ("passed", "partial") else 1)
