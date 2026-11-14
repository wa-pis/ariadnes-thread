"""Independent ADR0182 saved-data audit. Import no candidate or scientific code."""

from __future__ import annotations

# ruff: noqa: E402 -- Include imports in the external process budget.
from time import monotonic

PROCESS_START = monotonic()

from collections.abc import Callable
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = Path("docs/adr/experiments")
CONTRACT = "ADR0182"
PURE_PINS = {
    "0180-split-audit.py": "b3782c15db3cc36121781d4b243e6f7ae8a8627db17efe527f8f84e9fb046487",
    "0145-short-coast-evidence.py": "426fe4e0abe9b9dfcf6380d09e86e8dbf5748f66875f74b26b45dceb6ba5da14",
}
PURE_HELPERS = ("0183-earth-inputs.py", "0183-earth-reference.py", "0183-earth-native-replay.py")
PREPARATION = ARTIFACTS / "0183-verification.json"
COMMON_IDENTITY = ("versions", "imports", "native_binary", "conda_build", "resource_build",
                   "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime", "kernels")
type Row = dict[str, Any]
type Check = Callable[[], None]
type Event = Callable[[str, str], None]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def idle() -> None:
    pass


def noop_event(_operation: str, _phase: str) -> None:
    pass


def load_pure(root: Path, name: str, expected: str, check: Check = idle) -> ModuleType:
    require(name in (*PURE_PINS, *PURE_HELPERS), "audit cannot import candidate code")
    check()
    path = root / ARTIFACTS / name
    raw = path.read_bytes()
    require(digest(raw) == expected, "pure helper SHA256: " + name)
    module = ModuleType("earth_audit_" + path.stem.replace("-", "_"))
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    check()
    return module


split = load_pure(ROOT, "0180-split-audit.py", PURE_PINS["0180-split-audit.py"])
base = split.base
number, vector, same, parse = base.number, base.vector, base.same, base.parse
FAILURES = split.FAILURES
BODIES, PROFILES, OFFSETS = split.BODIES, split.PROFILES, split.OFFSETS
CAPS = {**split.CAPS, "binary64_fields": 30042, "source_rows": 84, "reference_fields": 672,
        "native_reference_fields": 84, "native_telemetry": 14}
del CAPS["native_guards"]
OPAQUE = split.OPAQUE | {"native_arcs", "native_guard_reads"}
STUDY_CAPS = CAPS | {name: split.STUDY_CAPS[name] for name in split.OPAQUE} | {
    "native_arcs": 2, "native_guard_reads": 2712,
}
SAMPLES = split.SAMPLES | {"source_rows": 84, "reference_fields": 672}
PROFILE_CAPS = {name: count//2 for name, count in SAMPLES.items()}
POSITION_LIMIT_M = 0.02
VELOCITY_LIMIT_M_S = 2e-5


class Budget(split.Budget):
    """Independent 10 s limiter with the B-only actual-work ceilings."""

    def __init__(self, clock: Callable[[], float], start_s: float) -> None:
        self.clock = clock
        self.start_s = number(start_s, "audit start")
        self.counts: dict[str, dict[str, int]] = {}
        self.ledger: list[dict[str, str]] = []

    def check(self) -> None:
        require(0 <= self.elapsed() < 10., "audit deadline/clock")

    def event(self, operation: str, phase: str) -> None:
        require(operation in CAPS and phase in ("attempt", "complete"), "audit event")
        self.check()
        counts = self.counts.setdefault(operation, {"attempted": 0, "completed": 0})
        if phase == "attempt":
            require(counts["attempted"] < CAPS[operation], "audit cap: " + operation)
            counts["attempted"] += 1
        else:
            require(counts["completed"] < counts["attempted"], "audit unmatched completion")
            counts["completed"] += 1
        self.ledger.append({"operation": operation, "phase": phase})
        self.check()


def reconstruct_row(row: Row, bundle: Row, *, complete: bool = True,
                    check: Check = idle, event: Event = noop_event) -> Row:
    """Rebuild the common split geometry, then validate the three B fields and sum."""
    # Use the prior independent reconstruction for geometry only. It does not
    # process any B force or derivative and does not need the candidate module.
    saved = row.get("geometry", {})
    require(type(saved) is dict, "geometry mapping")
    stripped = {k: v for k, v in row.items() if k != "derivative"}
    if "geometry" in row:
        stripped["geometry"] = {body: {k: v for k, v in values.items() if k != "acceleration_m_s2"}
                                for body, values in saved.items()}
    result = split.reconstruct_row(stripped, bundle, complete=False, check=check)
    if not result:
        require(not complete and "derivative" not in row, "work before motion")
        return result
    geometry = result["geometry"]
    fields = tuple(body for body in saved if "acceleration_m_s2" in saved[body])
    require(fields == BODIES[:len(fields)], "Sun/Moon/Earth field order")
    if fields or complete:
        require(tuple(geometry) == BODIES, "all geometry guards before fields")
        require(all(math.isfinite(geometry[body]["distance_m"])
                    and geometry[body]["distance_m"] > bundle["radii_m"][body] for body in BODIES),
                "exterior geometry before fields")
        exact_moon = map(Fraction, geometry["Moon"]["pre_round_separation_m"])
        require(sum(value*value for value in exact_moon) > Fraction(bundle["radii_m"]["Moon"])**2,
                "exact Moon exterior geometry before fields")
    for body in fields:
        event("binary64_fields", "attempt")
        g = geometry[body]
        rho = g["distance_m"]
        mu = number(bundle["gm_m3_s2"][body], "GM")
        square = rho*rho
        require(mu > 0 and math.isfinite(square) and square > 0, "positive finite field operands")
        parts = vector([mu*(d/rho)/square for d in g["separation_m"]], 3, "B force")
        same(saved[body]["acceleration_m_s2"], parts, body + " field")
        g["acceleration_m_s2"] = parts
        event("binary64_fields", "complete")
    if complete or "derivative" in row:
        require(fields == BODIES, "three fields before B derivative")
        event("dynamic_totals", "attempt")
        derivative = result["motion"]["w_m_s"] + [
            math.fsum(geometry[body]["acceleration_m_s2"][j] for body in BODIES) for j in range(3)
        ]
        same(row["derivative"], derivative, "B RHS derivative")
        result["derivative"] = derivative
        event("dynamic_totals", "complete")
    return result


def check_ledger(report: Row, check: Check) -> None:
    counts = report["counts"]
    require(type(counts) is dict and set(counts) <= STUDY_CAPS.keys(), "study counter inventory")
    rebuilt = {name: {"attempted": 0, "returned": 0, "completed": 0} for name in counts}
    phases = {"attempt": "attempted", "return": "returned", "complete": "completed"}

    def done(name: str) -> int:
        return rebuilt.get(name, {}).get("completed", 0)

    def attempts(name: str) -> int:
        return rebuilt.get(name, {}).get("attempted", 0)

    for index, row in enumerate(report["ledger"]):
        if index % 512 == 0:
            check()
        name, phase = row["operation"], phases[row["phase"]]
        require(name in rebuilt, "saved ledger event")
        c = rebuilt[name]
        if phase == "attempted" and name in ("states", "native_arcs", "native_guard_reads"):
            require(c["attempted"] == c["completed"], "overlapping " + name + " attempts")
        if phase == "attempted" and name == "solves":
            require(done("native_arcs") == 2 and done("native_telemetry") == 14,
                    "both native B profiles before DOP853")
            if c["attempted"]:
                require(done("solves") == 1 and all(done(key) == cap for key, cap in PROFILE_CAPS.items()),
                        "normal force gates before tighter")
        if phase == "attempted" and name == "identities" and c["attempted"]:
            require(done("solves") == 2 and all(done(key) == cap for key, cap in SAMPLES.items()),
                    "all sampled B gates before final identity")
        if name in ("states", "native_arcs", "native_guard_reads") and attempts(name) == 0:
            require(done("identities") == 1, "initial identity before science")
        c[phase] += 1
        require(c["completed"] <= c["attempted"] <= STUDY_CAPS[name], "saved counter cap: " + name)
        if name in OPAQUE:
            require(c["completed"] <= c["returned"] <= c["attempted"], "saved opaque return order")
        else:
            require(c["returned"] == 0, "unexpected opaque return")
    same(counts, rebuilt, "saved ledger counters")


def replay_profiles(report: Row, bundle: Row, reference: ModuleType, check: Check,
                    event: Event) -> tuple[dict[str, list[Row]], dict[int, Row]]:
    full = report["status"] == "passed"
    profiles = report["profiles"]
    require(type(profiles) is list and len(profiles) <= 2, "profile cap")
    names = tuple(profile["name"] for profile in profiles)
    require(names == PROFILES[:len(names)], "profile execution order")
    require(not full or names == PROFILES, "both profiles required")
    groups: dict[str, list[Row]] = {name: [] for name in names}
    cache: dict[int, Row] = {}
    previous = -1
    rhs = report["rhs"]
    require(type(rhs) is list and len(rhs) <= CAPS["rhs"], "RHS row cap")
    for ordinal, row in enumerate(rhs):
        check()
        name = row["profile"]
        require(name in groups and names.index(name) >= previous, "RHS profile order")
        previous = names.index(name)
        same([row["global_index"], row["index"]], [ordinal, len(groups[name])], "RHS indices")
        completed = row.get("completed", False)
        require(type(completed) is bool, "RHS completion type")
        if completed:
            event("rhs", "attempt")
        else:
            require(not full and ordinal == len(rhs)-1, "only final RHS may be partial")
        cache[id(row)] = reconstruct_row(row, bundle, complete=completed, check=check, event=event)
        if completed:
            event("rhs", "complete")
        groups[name].append(row)
    prior_count = 0
    for i, profile in enumerate(profiles):
        name = profile["name"]
        same(profile["settings"], base.settings(name), "profile settings")
        same(profile["rhs_start"], prior_count, "profile RHS start")
        prior_count += len(groups[name])
        last = i == len(profiles)-1
        raw = profile.get("raw_returned")
        outputs = profile["outputs"]
        require(type(outputs) is list and len(outputs) <= 7, "output count")
        if raw is None:
            require(not full and last and not outputs, "missing complete raw arrays")
            continue
        require(type(raw["success"]) is bool and type(raw["status"]) is int, "solver status types")
        t = vector(raw["t"], len(raw["t"]), "raw solver times")
        require(len(t) <= 7 and t == list(OFFSETS[:len(t)]), "raw output epoch grid")
        require(type(raw["y"]) is list and len(raw["y"]) == 6, "raw solver y shape")
        y = [vector(values, len(t), "raw y row") for values in raw["y"]]
        completed = [row for row in groups[name] if row.get("completed")]
        same(raw["nfev"], len(completed), "nfev versus completed RHS")
        if raw["success"]:
            require(t == list(OFFSETS) and raw["status"] == 0, "complete solver return")
            require(all(values[0] == 0 for values in y), "zero initial correction")
        else:
            require(not full and last and not outputs, "solver fail-stop")
        for j, output in enumerate(outputs):
            check()
            complete = "derivative" in output
            if "correction" in output:
                same(output["correction"], [values[j] for values in y], "solver/output correction")
            if "elapsed_s" in output:
                node = report["node_table"][j]
                same(output["elapsed_s"], t[j], "output elapsed")
                same(output["bodies"], node["bodies"], "shared SSB node operands")
                same(output["moon_earth"], node["moon_earth"], "shared Moon/Earth node operand")
            if not complete:
                require(not full and last and j == len(outputs)-1, "only final output may be partial")
            cache[id(output)] = reconstruct_row(output, bundle, complete=complete, check=check, event=event)
            if "motion_assessment" in output:
                assessment = reference.assess_motion(bundle["initial"], cache[id(output)]["motion"])
                same(output["motion_assessment"], assessment, "independent output assembly")
                require(assessment["passed"] or (not full and last), "required output assembly")
            elif full or not last:
                raise ValueError("missing required output assembly")
        if full or not last:
            require(len(outputs) == 7 and len(completed) >= 7
                    and any(row["lo_s"] != 0 for row in completed[:7]),
                    "complete outputs and nonzero-lo RHS sample")
    return groups, cache


def _state(row: Row) -> list[float]:
    motion = row["motion"]
    return motion["position_m"] + motion["velocity_m_s"]


def _difference(left: list[float], right: list[float], record: Row) -> Row:
    """Independently round the staged component differences and validate norms."""
    lhs = vector(left, 6, "effect lhs")
    rhs = vector(right, 6, "effect rhs")
    with localcontext() as ctx:
        # Exact for finite binary64 words and their fractions, including subnormals.
        ctx.prec = 1200
        dv = [Decimal.from_float(a)-Decimal.from_float(b) for a, b in zip(lhs, rhs, strict=True)]
        # The exact result is zero for equal operands, but subtraction of signed
        # zero operands still carries an orientation in a retained binary64 word.
        words = [float(v) if v else a-b for v, a, b in zip(dv, lhs, rhs, strict=True)]
    require(set(record) == {"vector", "position_norm_m", "velocity_norm_m_s"}, "signed vector shape")
    same(record["vector"], words, "signed effect component roundings")
    result: Row = {"vector": words}
    with localcontext() as ctx:
        ctx.prec = 100
        for name, part in (("position_norm_m", words[:3]), ("velocity_norm_m_s", words[3:])):
            binary = math.hypot(*part)
            decimal = float(sum(Decimal.from_float(x)**2 for x in part).sqrt())
            saved = number(record[name], name)
            require(abs(decimal-binary) <= 4*math.ulp(binary)
                    and abs(saved-decimal) <= 4*math.ulp(decimal), "four-ULP effect norm: " + name)
            same(saved, binary, "binary64 effect norm: " + name)
            result[name] = binary
    return result


def check_effects(report: Row, bundle: Row, native: dict[str, list[Row]], dop_tighter: list[Row]) -> int:
    saved = report["effects"]
    full = report["status"] == "passed"
    require(type(saved) is list and len(saved) <= 7, "effect row cap")
    if not saved:
        require(not full, "missing complete effects")
        return 0
    require(len(report["comparisons"]) == 21 and all(
        item["assessment"]["passed"] for item in report["comparisons"]), "numerical gates before effects")
    nodes = native["tighter"]
    require(len(dop_tighter) == len(nodes) == 7, "both tighter grids before effects")
    baseline = bundle["a_samples"]
    for i, row in enumerate(saved):
        epoch = nodes[i]["epoch_tdb_s"]
        same(row["index"], i, "effect index")
        same(row["epoch_tdb_s"], epoch, "effect node epoch")
        n = _difference(nodes[i]["state"], baseline["native"][i], row["native"])
        d = _difference(_state(dop_tighter[i]), baseline["dop853"][i], row["dop853"])
        residual = _difference(d["vector"], n["vector"], row["discrepancy"])
        if i == 0:
            require(not any(n["vector"]) and not any(d["vector"]), "zero initial effect")
        p_above = min(n["position_norm_m"], d["position_norm_m"]) > POSITION_LIMIT_M
        v_above = min(n["velocity_norm_m_s"], d["velocity_norm_m_s"]) > VELOCITY_LIMIT_M_S
        passed = (residual["position_norm_m"] <= POSITION_LIMIT_M
                  and residual["velocity_norm_m_s"] <= VELOCITY_LIMIT_M_S)
        same(row["position_above_scale"], p_above, "position comparison scale")
        same(row["velocity_above_scale"], v_above, "velocity comparison scale")
        same(row["passed"], passed, "signed sensitivity gate")
        require(passed or (not full and i == len(saved)-1), "effect gate fail-stop")
    require(not full or len(saved) == 7, "seven signed effect comparisons")
    return len(saved)


def _check_native_counts(report: Row, complete: bool) -> None:
    counts = report["counts"]
    native_arcs = {key: 0 for key in ("attempted", "returned", "completed")}
    native_guards = dict.fromkeys(native_arcs, 0)
    for profile in report["native_profiles"]:
        guards = profile["guards"]
        native_arcs = {key: count + profile["arc"][key] for key, count in native_arcs.items()}
        native_guards["attempted"] += len(guards)
        native_guards["returned"] += sum("state_si" in row for row in guards)
        native_guards["completed"] += sum(row.get("passed") is True for row in guards)
    for name, rebuilt in (("native_arcs", native_arcs), ("native_guard_reads", native_guards)):
        saved = counts.get(name, dict.fromkeys(rebuilt, 0))
        if complete:
            same(saved, rebuilt, name + " counts from preserved records")
        else:
            # A deadline fired after event publication may precede retention of
            # its operand or validation; at most the last physical read is affected.
            require(all(0 <= saved[k]-rebuilt[k] <= 1 for k in rebuilt), name + " partial counts")


def _check_metadata(report: Row, bundle: Row, full: bool) -> None:
    """Check ordered captured inventory metadata without reading any kernel."""
    actual = report["native_metadata_returns"]
    require(type(actual) is list, "native metadata inventory")
    if report["adapter_mode"] == "injected-test":
        require(not actual, "no native metadata in an injected study")
        return
    kernels = bundle["kernel_manifest"]["kernels"]
    require(len(kernels) == 13, "frozen kernel count")
    tags = [("load_standard_kernels", "initializations", [])]
    inventory = [("ktotal", "metadata", ["ALL"]), *[
        ("kdata", "metadata", [i, "ALL"]) for i in range(len(kernels))],
        ("get_total_count_of_kernels_loaded", "metadata", [])]
    tags += inventory * 2
    require(len(actual) <= len(tags) and (not full or len(actual) == len(tags)), "metadata return count")
    returned = {"metadata": 0, "initializations": 0}
    for row, (api, op, args) in zip(actual, tags):
        same([row["api"], row["operation"], row["args"]], [api, op, args], "metadata API order")
        value = row["value"]
        if op == "initializations":
            require(value is None, "kernel setup result")
        elif api == "kdata":
            require(type(value) is list and len(value) in (4, 5) and type(value[3]) is int
                    and (len(value) == 4 or value[4] is True), "kdata retained return")
            target = kernels[args[0]]
            same([Path(value[0]).name, value[1], value[2] or None],
                 [target["name"], target["type"], target["source"]], "ordered kernel return")
        else:
            same(value, len(kernels), "retained kernel call count")
        returned[op] += 1
    for name, n in returned.items():
        saved = report["counts"].get(name, {}).get("returned", 0)
        require(n == saved if full else saved <= n <= saved+1, "metadata return ledger: " + name)


def check_saved(report: Row, bundle: Row, references: ModuleType, native: ModuleType,
                check: Check = idle, event: Event = noop_event,
                archive: frozenset[str] | None = None) -> Row:
    """Rebuild recorded B checks; a provable partial prefix is never a pass."""
    require(report["contract"] == CONTRACT and report["model"] == "B"
            and report["adapter_mode"] in ("reference", "injected-test"),
            "B study mode/contract")
    require(report["status"] in ("passed", "failed", "partial"), "study status")
    full = report["status"] == "passed"
    for key, value in (("origin", "SSB"), ("orientation", "J2000"), ("time_scale", "TDB"),
                       ("budget_s", 60.), ("aberration_correction", "NONE"), ("position_units", "m"),
                       ("velocity_units", "m/s"), ("acceleration_units", "m/s^2"),
                       ("gm_acquisitions", 0), ("optimizer_calls", 0),
                       ("historical_final_identity_complete", False), ("mission_accuracy_verified", False),
                       ("continuous_safety_verified", False), ("scientific_verified", False)):
        same(report[key], value, "scientific boundary: " + key)
    require(type(report["unavailable"]) is list, "unavailable study checks")
    if full:
        require(not report["unavailable"] and "error" not in report and report["finalization_gate"] == "passed",
                "successful study finalization/inventory")
        same(report["identities"]["before"], report["identities"]["after"], "before/after identity")
    else:
        require(type(report.get("error")) is dict, "partial earliest error")
    check_ledger(report, check)
    result = {"passed": full, "complete_native_profiles": 0, "complete_profiles": 0,
              "native_telemetry": 0, "observations": 0, "comparisons": 0, "effects": 0,
              "historical_final_identity_repaired": False, "continuous_safety_verified": False}
    if "inputs" not in report:
        require(not full and not any(report[key] for key in (
            "state_requests", "node_table", "rhs", "profiles", "comparisons", "trials",
            "observations", "native_profiles", "identities", "effects")), "work without frozen inputs")
        return result
    same(report["inputs"], bundle, "frozen input identity")
    _check_metadata(report, bundle, full)
    # Independently check all returned native retained states/guards and telemetry.
    error = report.get("error", {})
    native_kwargs: Row = {}
    if not full and error.get("type") == "TelemetryFailure":
        stage = error["stage"]
        require(stage in ("native-normal", "native-tighter"), "native telemetry failure stage")
        native_kwargs["expected_telemetry_failure"] = (stage.removeprefix("native-"), error["message"])
    native_rows = native.replay(report["native_profiles"], bundle, check=check, event=event,
                                complete=full, **native_kwargs)
    _check_native_counts(report, full)
    split.check_request_sequence(report, bundle, check)
    groups, cache = replay_profiles(report, bundle, references, check, event)
    base.check_trials(report, check, event)
    comparison_inputs = dict(bundle, native_samples={
        name: [row["state"] for row in native_rows.get(name, ())] for name in PROFILES
    })
    compared = split.replay_comparisons(report, comparison_inputs, references, cache)
    if report["profiles"]:
        require(len(compared) >= 7 and all(row["assessment"]["passed"] for row in compared[:7]),
                "native numerical gates before DOP853")
    observed = split.replay_observations(report, bundle, references, cache, groups,
                                         archive if archive is not None else split.archived_hi_words(ROOT),
                                         check, event)
    dop_tighter = [cache[id(row)] for p in report["profiles"] if p["name"] == "tighter"
                   for row in p["outputs"] if "derivative" in row]
    effects = check_effects(report, bundle, native_rows, dop_tighter)
    if full:
        require(len(compared) == 21 and observed == 28 and effects == 7, "complete B results")
        n_rhs = len(report["rhs"])
        counts = report["counts"]
        expected = {"rhs": n_rhs, "states": 4*(n_rhs+7), "trials": len(report["trials"]),
                    "binary64_fields": 3*(n_rhs+14), "dynamic_totals": n_rhs+14,
                    "solves": 2, "identities": 2, "native_arcs": 2, "native_guard_reads": 2712,
                    "native_reference_fields": 84, "native_telemetry": 14, **SAMPLES}
        if report["adapter_mode"] == "reference":
            expected.update(initializations=1, metadata=30)
        for name, value in expected.items():
            row = counts[name]
            require(row["attempted"] == row["completed"] == value, "complete count: " + name)
        evaluation_count = sum(3 if row["exact_tdb_s"] == str(Fraction(row["hi_tdb_s"])) else 6
                               for row in report["observations"])
        same(counts["record_evaluations"], {"attempted": evaluation_count, "returned": 0,
                                           "completed": evaluation_count}, "exact sampled record count")
    result.update(complete_native_profiles=sum(len(rows) == 7 for rows in native_rows.values()),
                  complete_profiles=sum(p.get("raw_returned", {}).get("success") is True
                                        and len(p["outputs"]) == 7 and all("derivative" in row for row in p["outputs"])
                                        for p in report["profiles"]),
                  native_telemetry=report["counts"].get("native_telemetry", {}).get("completed", 0),
                  observations=observed, comparisons=len(compared), effects=effects)
    return result


def check_study_receipts(path: Path, report: Row, raw: bytes, check: Check = idle) -> Row:
    receipts = {}
    for name in ("attempt", "receipt", "parent-attempt", "parent-receipt"):
        check()
        receipts[name] = path.with_suffix("." + name + ".json").read_bytes()
    attempt, child, marker, parent = map(parse, receipts.values())
    for item in (attempt, marker, parent):
        same(item["contract"], CONTRACT, "study receipt contract")
    same(attempt["adapter_mode"], "reference", "real study attempt")
    same(child["status"], report["status"], "study child status")
    same(child["finalization_gate"], report["finalization_gate"], "study child finalization")
    for key, value in (("attempt_sha256", digest(receipts["attempt"])),
                       ("child_receipt_sha256", digest(receipts["receipt"])),
                       ("parent_attempt_sha256", digest(receipts["parent-attempt"])),
                       ("evidence_sha256", digest(raw)), ("phase", "study"),
                       ("preparation_sha256", report["preparation_manifest_sha256"])):
        same(parent[key], value, "study parent " + key)
    same(child["evidence_sha256"], digest(raw), "study child evidence")
    for key in ("phase", "revision", "preparation_sha256"):
        same(marker[key], parent[key], "study parent marker " + key)
    start = number(attempt["started_s"], "study start")
    same(child["started_s"], start, "study child start")
    same(parent["started_s"], start, "study parent start")
    require(type(parent["checkout_frozen"]) is bool and type(parent["elapsed_s"]) in (float, int)
            and (type(parent["returncode"]) is int or parent["returncode"] is None),
            "study parent outcome types")
    if report["status"] == "passed":
        require(parent["returncode"] == 0 and parent["checkout_frozen"]
                and child["finalization_gate"] == parent["finalization_gate"] == "passed"
                and not parent["stderr"], "study parent finalization")
        require(0 <= number(report["elapsed_before_flush_s"], "study preflush elapsed")
                <= number(child["elapsed_s"], "study child elapsed")
                <= number(parent["elapsed_s"], "study parent elapsed") < 60, "study inclusive timing")
        same(report["identities"]["before"]["revision"], parent["revision"], "study snapshot revision")
    else:
        require(parent["returncode"] != 0, "failed study exit code")
    return {name + "_sha256": digest(data) for name, data in receipts.items()}


def verify_identities(root: Path, report: Row, bundle: Row, tested: dict[str, str], check: Check) -> Row:
    identities = report["identities"]
    if not identities:
        require(report["status"] != "passed" and not report["state_requests"] and not report["native_profiles"],
                "initial identity required before science")
        return {}
    require(set(identities) <= {"before", "after"} and "before" in identities, "snapshot order")
    evidence = "0145-short-coast-evidence.py"
    pinned = PURE_PINS[evidence]
    same(bundle["protected_sha256"][str(ARTIFACTS / evidence)], pinned, "pinned snapshot helper")
    snapshot_checker = load_pure(root, evidence, pinned, check)
    extras = {name: value for name, value in tested.items() if name.startswith(str(ARTIFACTS / "0183-earth-"))}
    result = {}
    for when, wire in identities.items():
        check()
        same(wire["dirty"], [], "clean saved study checkout")
        for key in COMMON_IDENTITY:
            same(wire[key], bundle["historical_identity"][key], "original scientific identity " + key)
            same(wire[key], bundle["a_runtime"][key], "saved A scientific identity " + key)
        snapshot = deepcopy(wire)
        for name, expected in extras.items():
            same(snapshot["source_sha256"].pop(name), expected, "snapshot tested B helper " + name)
        result[when] = snapshot_checker.verify_snapshot(snapshot, bundle["kernel_manifest"], check, checkout=root)
    return result


def audit(path: Path, output: Path, *, root: Path = ROOT, clock: Callable[[], float] = monotonic,
          started_s: float | None = None, manifest_sha256: str | None = None,
          inputs_loader: Callable[[Path, Check], Row] | None = None,
          references: ModuleType | None = None, native: ModuleType | None = None) -> Row:
    """Audit once from saved data; any injected path remains synthetic-only."""
    injected = inputs_loader is not None or references is not None or native is not None or clock is not monotonic
    if injected:
        require(inputs_loader is not None and references is not None and native is not None,
                "injected audit needs all synthetic adapters")
    else:
        require(started_s is not None and started_s <= PROCESS_START and manifest_sha256 is not None,
                "external audit baseline and manifest digest required")
    start = started_s if started_s is not None else clock()
    budget = Budget(clock, start)
    mode = "injected-test" if injected else "reference"
    result: Row = {"contract": CONTRACT, "audit_status": "rejected", "scientific_verified": False,
                   "adapter_mode": mode, "budget_s": 10.0, "counts": budget.counts, "ledger": budget.ledger,
                   "native_calls": 0, "scientific_imports": 0, "kernel_loads": 0, "spacecraft_propagations": 0}
    attempt, receipt = (output.with_suffix(s) for s in (".attempt.json", ".receipt.json"))
    require(not any(p.exists() for p in (output, attempt, receipt)), "exclusive audit evidence exists")
    with attempt.open("x", encoding="utf-8") as stream:
        json.dump({"contract": CONTRACT, "started_s": start, "adapter_mode": mode}, stream, allow_nan=False)
        stream.flush()
    with output.open("x", encoding="utf-8") as stream, receipt.open("x", encoding="utf-8") as receipt_stream:
        stage = "inputs"
        try:
            budget.check()
            raw = path.read_bytes()
            report = parse(raw)
            result["study_sha256"] = digest(raw)
            assets = None
            tested: dict[str, str] = {}
            if not injected:
                split.fresh()
                same(report["adapter_mode"], "reference", "study mode for real audit")
                same(report["preparation_manifest_sha256"], manifest_sha256, "bound study/preparation")
                result["study_receipts"] = check_study_receipts(path, report, raw, budget.check)
                preparation = (root / PREPARATION).read_bytes()
                same(digest(preparation), manifest_sha256, "external preparation digest")
                tested = parse(preparation)["tested_source_sha256"]
                same(report["tested_source_sha256"], tested, "study tested source identities")
                names = (*PURE_HELPERS, "0183-earth-audit.py")
                # Rehash all code before executing helpers, not just the digest
                # of the helper that checks the rest of the manifest.
                for name in names:
                    target = root / ARTIFACTS / name
                    expected = tested[str(ARTIFACTS / name)]
                    same(digest(target.read_bytes()), expected, "pure tested helper SHA256: " + name)
                    budget.check()
                assets, references, native = (load_pure(root, name, tested[str(ARTIFACTS / name)], budget.check)
                                               for name in PURE_HELPERS)
                same(assets.preparation(root, budget.check), (manifest_sha256, tested), "verified B preparation")
                inputs_loader = assets.load_inputs
            else:
                same(report["adapter_mode"], "injected-test", "only injected study data in test audit")
            assert inputs_loader is not None and references is not None and native is not None
            bundle = inputs_loader(root, budget.check)
            stage = "saved-data"
            result["checks"] = check_saved(report, bundle, references, native, budget.check, budget.event,
                                           split.archived_hi_words(root))
            if not injected:
                stage = "identities"
                assert assets is not None
                result["snapshot_checks"] = verify_identities(root, report, bundle, tested, budget.check)
                same(assets.preparation(root, budget.check), (manifest_sha256, tested), "final tested/source identities")
                same(digest(path.read_bytes()), result["study_sha256"], "study readback identity")
                same(check_study_receipts(path, report, raw, budget.check), result["study_receipts"],
                     "final study receipt identities")
                split.fresh()
            result["audit_status"] = "passed" if result["checks"]["passed"] else "partial"
        except FAILURES as error:
            result["error"] = {"stage": stage, "type": type(error).__name__, "message": str(error)}
        split.write_result(result, stream, receipt_stream, output, budget)
    return result
