"""Independent stdlib-only saved-data audit of the ADR0156 fixed probe.

The saved SI operands use TDB seconds from J2000, SSB and J2000. This auditor
never imports the study or its binary64 candidate implementation.
"""
from __future__ import annotations

# ruff: noqa: E402 -- All later imports belong to the process-wide budget.
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
HERE = Path(__file__).resolve().parent
ARM_NAMES = ("compensated", "uncorrected", "wrong_sign")
SOURCE_ORDER = ("Sun", "Earth", "Moon")
MODELS = {"A": ("Sun", "Moon"), "B": ("Sun", "Moon", "Earth")}
RADII_M = {"Sun": 696000000.0, "Earth": 6378136.6, "Moon": 1737400.0}
LIMITS = {"source_rows": 21, "reference_fields": 168,
          "binary64_fields": 63, "model_totals": 14}
INPUT_KEYS = ("position_m", "initial", "gm_m3_s2", "input_sha256",
              "source_provenance", "identity")
HELPERS = ("0157-fixed-gravity-inputs.py", "0157-fixed-gravity-reference.py",
           "0157-fixed-gravity-study.py", "0157-fixed-gravity-audit.py",
           "0153-real-ephemeris-oracle.py", "0145-short-coast-evidence.py")
FAILURES = (ValueError, TypeError, KeyError, IndexError, AttributeError,
            OSError, ImportError, RuntimeError, ArithmeticError)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def number(value: Any, field: str) -> float:
    require(type(value) in (int, float), field + ": finite nonboolean number required")
    result = float(value)
    require(math.isfinite(result), field + ": finite number required")
    return result


def vector(value: Any, field: str) -> list[float]:
    require(type(value) is list and len(value) == 3, field + ": three components required")
    return [number(item, field) for item in value]


def same(actual: Any, expected: Any, field: str) -> None:
    """Exact JSON operand equality, including binary64 signed zero and types."""
    require(type(actual) is type(expected), field + ": value type changed")
    if type(expected) is dict:
        require(actual.keys() == expected.keys(), field + ": object fields changed")
        for key in expected:
            same(actual[key], expected[key], field + "." + key)
    elif type(expected) is list:
        require(len(actual) == len(expected), field + ": vector/list length changed")
        for index, (left, right) in enumerate(zip(actual, expected, strict=True)):
            same(left, right, f"{field}[{index}]")
    elif type(expected) is float:
        require(math.isfinite(actual) and actual.hex() == expected.hex(),
                field + ": binary64 operand changed")
    else:
        require(actual == expected, field + ": value changed")


def _pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError("nonfinite JSON constant: " + value)


def _finite_tree(value: Any) -> None:
    if type(value) is dict:
        require(all(type(key) is str for key in value), "JSON object string keys required")
        for item in value.values():
            _finite_tree(item)
    elif type(value) is list:
        for item in value:
            _finite_tree(item)
    elif type(value) is float:
        require(math.isfinite(value), "nonfinite JSON number")
    else:
        require(value is None or type(value) in (str, bool, int), "unsupported JSON value")


def parse(raw: bytes) -> dict[str, Any]:
    result = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
    require(type(result) is dict, "saved study must be a JSON object")
    _finite_tree(result)
    return result


class Budget:
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
            require(counter["attempted"] < LIMITS[operation], "audit work cap: " + operation)
            counter["attempted"] += 1
        else:
            require(counter["completed"] < counter["attempted"], "audit completion ledger")
            counter["completed"] += 1
        self.ledger.append({"operation": operation, "phase": phase})
        if phase == "complete":
            self.check()

    def consume_reference(self, phase: str) -> None:
        self.event("reference_fields", phase)

    def consume_model(self, phase: str) -> None:
        self.event("model_totals", phase)


def fresh() -> None:
    require(not any(name.startswith(("numpy", "scipy", "spiceypy", "tudatpy", "space_nav"))
                    for name in sys.modules), "audit requires a fresh stdlib-only process")


def helper_hashes(root: Path, check: Callable[[], None]) -> dict[str, str]:
    directory = root / "docs/adr/experiments"
    result = {}
    for name in HELPERS:
        check()
        result[name] = sha256((directory / name).read_bytes()).hexdigest()
        check()
    return result


def load_helper(root: Path, name: str, expected: str, check: Callable[[], None]) -> ModuleType:
    path = root / "docs/adr/experiments" / name
    check()
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == expected, "audit helper SHA256: " + name)
    spec = importlib.util.spec_from_file_location("fixed_gravity_audit_" + name[19:-3], path)
    require(spec is not None and spec.loader is not None, "audit helper loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    check()
    return module


def reconstruct_arm(source: dict[str, Any], position_m: list[float], gm_m3_s2: float,
                    arm: str) -> dict[str, list[float]]:
    """Independently replay the frozen binary64 expression from saved raw state."""
    require(arm in ARM_NAMES, "candidate arm inventory")
    state = source["state_si"]
    require(type(state) is list and len(state) == 6, "raw SI state length")
    values = [number(item, "raw SI state") for item in state]
    position = vector(position_m, "fixed position_m")
    lo = number(source["lo_s"], "lo_s")
    gm = number(gm_m3_s2, "gm_m3_s2")
    require(gm > 0, "positive GM required")
    correction = [values[index + 3] * lo for index in range(3)]
    require(all(math.isfinite(item) for item in correction), "nonfinite rephasing")
    if arm == "uncorrected":
        correction = [0.0, 0.0, 0.0]
    elif arm == "wrong_sign":
        correction = [-item for item in correction]
    separation = [math.fsum((values[index], -position[index], correction[index]))
                  for index in range(3)]
    radius = RADII_M[source["body"]]
    require(sum((Fraction.from_float(item) ** 2 for item in separation), Fraction())
            > Fraction.from_float(radius) ** 2, "candidate source exclusion guard")
    rho = math.hypot(*separation)
    require(math.isfinite(rho) and rho > 0, "candidate finite nonzero distance")
    acceleration = [gm * (item / rho) / (rho * rho) for item in separation]
    require(all(math.isfinite(item) for item in acceleration), "nonfinite candidate field")
    return {"separation_m": separation, "acceleration_m_s2": acceleration,
            "rephasing_m": correction}


def reconstruct_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    require(len(rows) == 3 and [row["source_row"]["body"] for row in rows]
            == list(SOURCE_ORDER), "model source inventory")
    sources = {row["source_row"]["body"]: row["arms"] for row in rows}
    return {model: {arm: {"acceleration_m_s2": [math.fsum(
        sources[body][arm]["acceleration_m_s2"][axis] for body in order)
        for axis in range(3)]} for arm in ARM_NAMES} for model, order in MODELS.items()}


def expected_ledger() -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for index in range(21):
        result.append({"operation": "source_rows", "phase": "attempt"})
        for operation, count in (("binary64_fields", 3), ("reference_fields", 8)):
            for _ in range(count):
                result.extend({"operation": operation, "phase": phase}
                              for phase in ("attempt", "complete"))
        result.append({"operation": "source_rows", "phase": "complete"})
        if index % 3 == 2:
            for _ in MODELS:
                result.extend({"operation": "model_totals", "phase": phase}
                              for phase in ("attempt", "complete"))
    return result


def check_ledger(report: dict[str, Any]) -> dict[str, Any]:
    ledger = report["ledger"]
    require(type(ledger) is list, "source ledger must be a list")
    expected = expected_ledger()
    require(len(ledger) <= len(expected), "source ledger count cap")
    same(ledger, expected[:len(ledger)], "source operation prefix")
    counts = {name: {"attempted": 0, "completed": 0} for name in LIMITS}
    for entry in ledger:
        counts[entry["operation"]]["attempted" if entry["phase"] == "attempt"
                                     else "completed"] += 1
    same(report["counts"], counts, "source counters")
    for name, limit in LIMITS.items():
        require(counts[name]["completed"] <= counts[name]["attempted"] <= limit,
                "source count limit: " + name)
    if report["status"] == "passed":
        same(ledger, expected, "complete source operation coverage")
    return counts


def check_header(report: dict[str, Any]) -> None:
    constants: dict[str, Any] = {
        "contract": "ADR0156", "study": "fixed-position-real-gravity-v1",
        "research_only": True, "mission_accuracy_verified": False,
        "continuous_safety_verified": False, "origin": "SSB", "orientation": "J2000",
        "time_scale": "TDB", "aberration_correction": "NONE", "acceleration_units": "m/s^2",
        "budget_s": 10.0, "reference_replayed": False,
    }
    constants.update({name: 0 for name in ("native_calls", "kernel_loads", "gm_acquisitions",
                                          "spacecraft_propagations", "scientific_imports")})
    for key, value in constants.items():
        same(report[key], value, "source " + key)
    require(report["adapter_mode"] in ("reference", "injected-test"), "source adapter mode")
    require(report["status"] in ("passed", "partial"), "source status")
    require(report["finalization_gate"] in ("passed", "failed"), "source finalization gate")
    raw_elapsed = report["elapsed_before_flush_s"]
    if raw_elapsed is None:
        require(report["status"] == "partial" and report["finalization_gate"] == "failed"
                and "clock" in report.get("error", {}).get("message", "").lower(),
                "unknown elapsed requires explicit failed clock evidence")
        elapsed = None
    else:
        elapsed = number(raw_elapsed, "source elapsed_before_flush_s")
    if report["status"] == "passed":
        require(report["finalization_gate"] == "passed" and elapsed is not None and 0 <= elapsed < 10.0
                and "error" not in report and "first_error" not in report,
                "false successful source finalization")
    else:
        for key in ("error", *(["first_error"] if "first_error" in report else [])):
            error = report[key]
            require(type(error) is dict and set(error) == {"stage", "type", "message"}
                    and all(type(value) is str and value for value in error.values()),
                    "source failure evidence")
        if report["finalization_gate"] == "failed":
            require(report["error"]["stage"] == "finalization", "source late failure stage")


def _failed_stage(report: dict[str, Any]) -> str | None:
    return report.get("first_error", report.get("error", {})).get("stage")


def check_failure_prefix(report: dict[str, Any], counts: dict[str, Any]) -> None:
    if report["status"] == "passed":
        return
    stage = _failed_stage(report)
    require(type(stage) is str, "missing first failure stage")
    if "first_error" in report and report["error"]["stage"] != "finalization":
        same(report["first_error"], report["error"], "earliest failure changed")
    if stage == "inputs":
        require(not report["ledger"] and not report["rows"] and not report["totals"],
                "input failure after scientific work")
    elif stage == "identity":
        same(report["ledger"], expected_ledger(), "identity failure before work completed")
    elif stage != "finalization":
        require(bool(report["ledger"]), "work failure without an attempt")
        last = report["ledger"][-1]
        if last["operation"] == "model_totals":
            index = counts["source_rows"]["completed"] // 3 - 1
            model = ("A", "B")[(counts["model_totals"]["attempted"] - 1) % 2]
            expected = f"totals:{index}:{model}"
        else:
            expected = f"source:{counts['source_rows']['attempted'] - 1}"
        require(stage == expected, "failure stage does not match operation prefix")


def reference_progress(value: Any) -> list[tuple[str, str, Any]]:
    require(type(value) is dict and set(value) <= {"reference"}, "reference progress object")
    fields = value.get("reference", {})
    require(type(fields) is dict and set(fields) <= {"80", "100"}, "reference precision prefix")
    result = []
    for profile in ("80", "100"):
        current = fields.get(profile, {})
        require(type(current) is dict and list(current) == list(("d0", "d1", "d2", "d3"))[:len(current)],
                "reference geometry prefix")
        for geometry, vector_value in current.items():
            result.append((profile, geometry, vector_value))
    require([(profile, geometry) for profile, geometry, _value in result]
            == [(profile, geometry) for profile in ("80", "100")
                for geometry in ("d0", "d1", "d2", "d3")][:len(result)],
            "reference field order")
    return result


def row_reference_counts(ledger: list[dict[str, str]]) -> dict[int, dict[str, int]]:
    result: dict[int, dict[str, int]] = {}
    index = -1
    for entry in ledger:
        if entry == {"operation": "source_rows", "phase": "attempt"}:
            index += 1
            result[index] = {"attempted": 0, "completed": 0}
        elif entry["operation"] == "reference_fields":
            result[index]["attempted" if entry["phase"] == "attempt" else "completed"] += 1
    return result


def matched_failure(report: dict[str, Any], stage: str, error: BaseException,
                    budget: Budget) -> dict[str, str]:
    budget.check()
    actual = {"stage": stage, "type": type(error).__name__, "message": str(error)}
    require(report["status"] == "partial", "independent reconstruction failed for passed study")
    same(actual, report.get("first_error", report["error"]), "reproduced source failure")
    return actual


def check_saved(report: dict[str, Any], bundle: dict[str, Any], references: Any,
                budget: Budget) -> dict[str, Any]:
    """Reconstruct operands, fields and gates; a valid failed prefix stays partial."""
    check_header(report)
    counts = check_ledger(report)
    check_failure_prefix(report, counts)
    if "identity_after" in report:
        same(report["identity_after"], report["inputs"], "source final identity")
    elif report["status"] == "passed":
        raise ValueError("complete source final identity unavailable")
    if "inputs" in report:
        same(report["inputs"], {key: bundle[key] for key in INPUT_KEYS}, "frozen inputs")
    else:
        require(report["status"] == "partial" and not report["rows"] and not report["totals"]
                and all(value["attempted"] == 0 for value in counts.values()),
                "missing frozen input evidence")
    raw_rows = bundle["rows"]
    require(type(raw_rows) is list and len(raw_rows) == 21, "frozen source row coverage")
    rows, totals = report["rows"], report["totals"]
    require(type(rows) is list and type(totals) is list and len(rows) <= 21
            and len(totals) <= 7, "saved row/total limits")
    require(counts["source_rows"]["completed"] <= len(rows)
            <= counts["source_rows"]["attempted"]
            <= len(rows) + 1, "source row availability ledger")
    require(len(rows) - counts["source_rows"]["completed"] <= 1,
            "only the final source row may be incomplete")
    require(len(totals) <= len(rows) // 3, "totals require three source rows")
    source_results: list[dict[str, Any]] = []
    checked_rows: list[dict[str, Any]] = []
    checked_totals: list[dict[str, Any]] = []
    available_binary = 0
    reference_counts = row_reference_counts(report["ledger"])
    first_failure: str | None = None
    for index, row in enumerate(rows):
        budget.event("source_rows", "attempt")
        require(first_failure is None, "source data after first required gate failure")
        same(row["index"], index, "source row index")
        same(row["source_row"], raw_rows[index], "raw source row")
        body = raw_rows[index]["body"]
        require(body == SOURCE_ORDER[index % 3], "frozen source body order")
        arms = row["arms"]
        require(type(arms) is dict and list(arms) == list(ARM_NAMES)[:len(arms)],
                "source arm prefix")
        require(len(arms) == 3 or index == len(rows) - 1, "incomplete earlier source arms")
        rebuilt: dict[str, Any] = {}
        for arm in arms:
            budget.event("binary64_fields", "attempt")
            rebuilt[arm] = reconstruct_arm(raw_rows[index], bundle["position_m"],
                                           bundle["gm_m3_s2"][body], arm)
            budget.event("binary64_fields", "complete")
            same(arms[arm], rebuilt[arm], f"source {index} {arm}")
            available_binary += 1
        assessment: dict[str, Any] | None = None
        progress: dict[str, Any] = {}
        independent_error: dict[str, str] | None = None
        if len(arms) == 3:
            before = dict(budget.counts["reference_fields"])
            try:
                assessment = references.assess_source(raw_rows[index], bundle["position_m"],
                    bundle["gm_m3_s2"][body], RADII_M[body], rebuilt, budget.consume_reference,
                    progress=progress)
                require(type(assessment) is dict and type(assessment.get("passed")) is bool,
                        "recomputed source gate type")
                _finite_tree(assessment)
            except FAILURES as error:
                require(index == len(rows) - 1 and "assessment" not in row,
                        "independent failure with retained source assessment")
                independent_error = matched_failure(report, f"source:{index}", error, budget)
                same({key: budget.counts["reference_fields"][key] - before[key] for key in before},
                     reference_counts[index], "reproduced reference failure counters")
            if "assessment" in row:
                require(assessment is not None, "missing independent source result")
                same(row["assessment"], assessment, f"source {index} independent assessment")
                source_results.append(assessment)
                budget.event("source_rows", "complete")
                if not assessment["passed"]:
                    first_failure = f"source:{index}"
            else:
                require(index == len(rows) - 1, "missing completed source assessment")
        else:
            require("assessment" not in row, "assessment without all source arms")
        retained_progress = reference_progress(row.get("reference_progress", {}))
        require(len(retained_progress) == reference_counts[index]["completed"],
                "retained reference field completion coverage")
        recomputed_progress = {(profile, geometry): value
            for profile, geometry, value in reference_progress(progress)}
        for profile, geometry, value in retained_progress:
            same(value, recomputed_progress[(profile, geometry)],
                 f"source {index} retained reference {profile} {geometry}")
        checked_row: dict[str, Any] = {"index": index, "arms": rebuilt,
            "assessment_checked": "assessment" in row}
        if assessment is not None:
            checked_row["assessment"] = assessment
        checked_row["reference_progress"] = progress
        if independent_error is not None:
            checked_row["reproduced_failure"] = independent_error
        checked_rows.append(checked_row)
        if index % 3 == 2 and index // 3 < len(totals):
            require(first_failure is None and len(source_results) == index + 1,
                    "model totals after missing/failed source assessment")
            block = totals[index // 3]
            same(block["index"], index // 3, "model time index")
            same(block["elapsed_s"], raw_rows[index - 2]["elapsed_s"], "model elapsed time")
            total_arms = reconstruct_totals(rows[index - 2:index + 1])
            same(block["arms"], total_arms, "binary64 model totals")
            total_progress: dict[str, Any] = {}
            try:
                assessment = references.assess_totals(source_results[-3:], total_arms,
                    consume_model=budget.consume_model, progress=total_progress)
                _finite_tree(assessment)
            except FAILURES as error:
                require(index == len(rows) - 1, "independent model failure before later source data")
                model_number = budget.counts["model_totals"]["attempted"] - 1
                model_stage = f"totals:{index // 3}:{('A', 'B')[model_number % 2]}"
                matched_failure(report, model_stage, error, budget)
                assessment = total_progress
            require(type(assessment) is dict and list(assessment) in ([], ["A"], ["A", "B"]),
                    "recomputed model assessment prefix")
            if list(assessment) == ["A"] and assessment["A"].get("passed") is False:
                require(counts["model_totals"]["attempted"] <= 2 * (index // 3) + 1,
                        "model B attempted after required model A failure")
            saved = block.get("assessment", {})
            require(type(saved) is dict and list(saved) == list(assessment)[:len(saved)],
                    "saved model assessment prefix")
            for model in saved:
                same(saved[model], assessment[model], f"model {index // 3} {model} assessment")
                require(type(assessment[model].get("passed")) is bool,
                        "recomputed model gate type")
                if not assessment[model]["passed"]:
                    first_failure = f"totals:{index // 3}:{model}"
            if len(saved) < len(assessment):
                require(index == len(rows) - 1 and report["status"] == "partial",
                        "missing earlier model assessment")
            checked_totals.append({"index": index // 3, "arms": total_arms,
                                   "models_checked": list(saved), "assessment": assessment})
    require(available_binary == counts["binary64_fields"]["completed"],
            "returned binary64 field availability")
    assessments = sum("assessment" in row for row in rows)
    require(assessments == counts["source_rows"]["completed"], "source assessment completions")
    require(counts["reference_fields"]["completed"] >= 8 * assessments,
            "source reference completion coverage")
    completed_total_models = sum(len(block.get("assessment", {})) for block in totals)
    require(completed_total_models == counts["model_totals"]["completed"]
            and counts["model_totals"]["attempted"] <= 2 * len(totals) + 1,
            "model assessment availability ledger")
    if first_failure is not None:
        require(report["status"] == "partial" and _failed_stage(report) == first_failure,
                "first required gate failure stage")
    if report["status"] == "passed":
        require(len(rows) == 21 and len(totals) == 7 and assessments == 21
                and completed_total_models == 14 and first_failure is None,
                "complete source/model gate coverage")
    budget.check()
    return {"source_rows": checked_rows, "model_totals": checked_totals,
            "source_counts": counts, "first_required_gate_failure": first_failure,
            "complete_saved_data_checked": report["status"] == "passed"}


def _safe_elapsed(budget: Budget) -> float | None:
    try:
        return budget.elapsed()
    except FAILURES:
        return None


def save(result: dict[str, Any], stream: TextIO, budget: Budget) -> dict[str, Any]:
    """Include serialization, flush and the post-flush check in the same budget."""
    result["elapsed_before_flush_s"] = _safe_elapsed(budget)
    result["finalization_gate"] = "passed"
    try:
        budget.check()
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.flush()
        budget.check()
    except FAILURES as error:
        if "error" in result:
            result.setdefault("first_error", dict(result["error"]))
        result.update(audit_status="rejected", scientific_verified=False,
                      finalization_gate="failed", error={"stage": "finalization",
                      "type": type(error).__name__, "message": str(error)})
        result["elapsed_after_failed_flush_s"] = _safe_elapsed(budget)
        stream.seek(0)
        stream.truncate()
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.flush()
    return result


def audit(path: Path, output: Path, *, root: Path = ROOT,
          clock: Callable[[], float] = monotonic, start_s: float | None = None,
          inputs_loader: Any = None, references: Any = None) -> dict[str, Any]:
    """Audit saved finite SI evidence into a fresh exclusive JSON result."""
    start = (PROCESS_START if clock is monotonic else clock()) if start_s is None else start_s
    budget = Budget(clock, start)
    injected = inputs_loader is not None or references is not None or clock is not monotonic
    result: dict[str, Any] = {"contract": "ADR0156", "audit_status": "rejected",
        "scientific_verified": False, "adapter_mode": "injected-test" if injected else "reference",
        "source_study_status": "unavailable", "native_calls": 0, "kernel_loads": 0,
        "gm_acquisitions": 0, "spacecraft_propagations": 0, "scientific_imports": 0,
        "budget_s": 10.0, "counts": budget.counts, "ledger": budget.ledger}
    with output.open("x", encoding="utf-8") as stream:
        stage = "inputs"
        try:
            budget.check()
            if not injected:
                require(budget.start_s <= PROCESS_START, "audit process-start baseline was reset")
                fresh()
            raw = path.read_bytes()
            budget.check()
            result["evidence_sha256"] = sha256(raw).hexdigest()
            report = parse(raw)
            result["source_study_status"] = report.get("status", "unavailable")
            if not injected:
                hashes = helper_hashes(root, budget.check)
                if "helper_sha256" in report:
                    same(report["helper_sha256"], hashes, "saved helper identity")
                else:
                    require(report.get("status") == "partial" and _failed_stage(report) == "inputs"
                            and report.get("rows") == report.get("totals") == report.get("ledger") == [],
                            "saved helper identity unavailable after work")
                result["helper_sha256"] = hashes
            else:
                hashes = helper_hashes(root, budget.check) if inputs_loader is None or references is None else {}
            if inputs_loader is None:
                module = load_helper(root, HELPERS[0], hashes[HELPERS[0]], budget.check)
                inputs_loader = module.load_inputs
            if references is None:
                references = load_helper(root, HELPERS[1], hashes[HELPERS[1]], budget.check)
            bundle = inputs_loader(root, budget.check)
            stage = "saved-data"
            result["checks"] = check_saved(report, bundle, references, budget)
            if not injected:
                stage = "identity"
                same(helper_hashes(root, budget.check), hashes, "audit helper final identity")
                same(inputs_loader(root, budget.check), bundle, "audit input final identity")
            result["audit_status"] = "passed" if report["status"] == "passed" else "partial"
            result["scientific_verified"] = (not injected and report["adapter_mode"] == "reference"
                                               and result["audit_status"] == "passed")
            budget.check()
        except FAILURES as error:
            result.update(audit_status="rejected", scientific_verified=False,
                          error={"stage": stage, "type": type(error).__name__, "message": str(error)})
        return save(result, stream, budget)


if __name__ == "__main__":
    require(len(sys.argv) == 3, "usage: audit.py SAVED_STUDY EXCLUSIVE_AUDIT")
    audited = audit(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps({key: audited[key] for key in
                      ("audit_status", "scientific_verified", "source_study_status")}, allow_nan=False))
    raise SystemExit(0 if audited["audit_status"] in ("passed", "partial") else 1)
