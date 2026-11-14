"""Independently audit ADR0188's saved handoff, propagation and direction."""

from __future__ import annotations

# ruff: noqa: E402 -- Include imports in the phase budget.
from time import monotonic

PROCESS_START = monotonic()

from collections.abc import Callable
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, TextIO

ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = Path("docs/adr/experiments")
CONTRACT = "ADR0188"
PREPARATION = ARTIFACTS / "0189-verification.json"
DIRECTION = "0189-post-cutoff-direction-audit.py"
INPUTS = "0189-post-cutoff-inputs.py"
PREPARE = "0189-post-cutoff-prepare.py"
PINNED = {
    "0186-long-b-audit.py": "ae44501220b4cff1366de5182ec3b1985bd3dbcdeeabf328e46c142291cdd04a",
    "0186-long-b-reference.py": "4fb366b232c1515e4d6f96d2bc14b77249ed09bed909bbe3d79ac9a29b59e7c5",
    "0186-long-b-native-replay.py": "6306c4626d555429e091341190de0d092f8f6f1d419e305d188fa0ed6eef3833",
}
type Row = dict[str, Any]
type Check = Callable[[], None]
type Event = Callable[[str, str], None]


def idle() -> None:
    pass


def require(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError(label)


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def load_pure(root: Path, name: str, expected: str | None, check: Check = idle) -> ModuleType:
    """Load only approved saved-data helpers, never any study or solver code."""
    require(name in (*PINNED, PREPARE, INPUTS, DIRECTION), "audit helper allowlist")
    check()
    path = root / ARTIFACTS / name
    raw = path.read_bytes()
    pinned = PINNED.get(name)
    require((pinned is None or pinned == digest(raw)) and
            (expected is None or expected == digest(raw)), "pure helper SHA256: " + name)
    module = ModuleType("post_cutoff_audit_" + path.stem.replace("-", "_"))
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    check()
    return module


r540 = load_pure(ROOT, "0186-long-b-audit.py", None)
number, same, parse = r540.number, r540.same, r540.parse
OFFSETS, PROFILES = r540.OFFSETS, r540.PROFILES
FAILURES = r540.FAILURES


def check_handoff(report: Row, bundle: Row, complete: bool) -> None:
    """Use the frozen event and a separate rational mass-law check."""
    initial, cutoff = bundle["initial"], bundle["cutoff"]
    same([cutoff["label"], cutoff["origin"], cutoff["orientation"]],
         ["departure-cutoff", "SSB", "J2000"], "cutoff event")
    same({key: cutoff[key] for key in ("epoch_tdb_s", "position_m", "velocity_m_s")},
         initial, "cutoff six-state and epoch")
    mass = number(bundle["mass_kg"], "cutoff mass")
    burn, arith, coast = (bundle[key] for key in ("burn", "mass_arithmetic", "coast"))
    same([coast["constant_mass_metadata_kg"], burn["final_mass_kg"], report["coast_mass_kg"]],
         [mass, mass, mass], "unchanged cutoff mass")
    require(mass > number(arith["dry_mass_kg"], "dry mass") > 0, "coast above dry mass")
    require(all(number(coast[key], key) == 0 for key in ("thrust_n", "mass_flow_kg_s")),
            "unpowered coast and no mass flow")
    same(burn["burn_id"], "departure", "departure burn identity")
    same(burn["end_epoch_tdb_s"], initial["epoch_tdb_s"], "represented cutoff epoch")
    same(arith["g0_m_s2"], "9.80665", "standard gravity")
    start = number(burn["start_epoch_tdb_s"], "ignition epoch")
    end = number(burn["end_epoch_tdb_s"], "cutoff epoch")
    requested = number(arith["requested_duration_s"], "requested duration")
    require(requested > 0 and start + requested == end, "requested duration/cutoff binding")
    span = Fraction(end) - Fraction(start)
    thrust, isp = (number(burn[key], key) for key in ("thrust_n", "isp_s"))
    m0 = number(burn["initial_mass_kg"], "ignition mass")
    require(span > 0 and thrust > 0 and isp > 0 and m0 > mass, "positive finite burn operands")
    # Use binary64 thrust as an exact operand, never round the represented span.
    consumed = Fraction(thrust) * span / (Fraction("9.80665") * Fraction(isp))
    calculated = Fraction(m0) - consumed
    delta = calculated - Fraction(mass)
    limit = max(Fraction("1e-8"), Fraction("1e-11") * consumed)
    require(abs(delta) <= limit, "retained burn mass-law gate")
    # The original manifest rounds intermediates at 80 digits. These wire
    # strings are independently bounded, not required to match last digits.
    require(Fraction(arith["represented_duration_s"]) == span, "represented burn span")
    for name, expected in (("predicted_mass_kg", calculated),
                           ("predicted_minus_stored_mass_kg", delta), ("limit_kg", limit)):
        require(abs(Fraction(arith[name])-expected) <= Fraction("1e-70"),
                "retained burn arithmetic: " + name)

    for kind in ("native_profiles", "profiles"):
        profiles = report[kind]
        for i, row in enumerate(profiles):
            if "coast_mass_kg" in row:
                same(row["coast_mass_kg"], mass, "profile cutoff mass")
            else:
                # The frozen solver may retain its result before a budget
                # exception. Only the last interrupted profile can lack a label.
                followed = i != len(profiles)-1 or (kind == "native_profiles" and report["profiles"])
                require(not complete and not followed, "missing profile cutoff mass")


def _state(row: Row) -> list[float]:
    motion = row["motion"]
    return motion["position_m"] + motion["velocity_m_s"]


def replay_comparisons(report: Row, native: dict[str, list[list[float]]],
                       dop: dict[str, list[list[float]]], reference: ModuleType, check: Check) -> int:
    """Replay the three same-start comparisons; no parking-prefix operands."""
    full = report["status"] == "passed"
    expected = [("native_step", i, a, b, .01, 1e-5) for i, (a, b) in enumerate(
        zip(native.get("normal", ()), native.get("tighter", ())))]
    for i, (a, b, c) in enumerate(zip(native.get("tighter", ()), dop.get("normal", ()), dop.get("tighter", ()))):
        expected += [("native_tighter", i, a, c, .01, 1e-5), ("oracle_step", i, b, c, .001, 1e-6)]
    saved = report["comparisons"]
    require(type(saved) is list and len(saved) <= len(expected) <= 39, "comparison cap and operands")
    require(not report["profiles"] or len(saved) >= 13, "native comparison before DOP853")
    require(not full or len(saved) == len(expected) == 39, "all 39 comparisons required")
    summary: Row = {}
    t0 = report["inputs"]["initial"]["epoch_tdb_s"]
    for j, (row, (name, index, left, right, p, v)) in enumerate(zip(saved, expected)):
        check()
        require(set(row) == {"name", "index", "epoch_tdb_s", "assessment", "difference"}, "comparison shape")
        same([row["name"], row["index"], row["epoch_tdb_s"]], [name, index, t0+OFFSETS[index]],
             "fixed comparison selection")
        assessment = reference.compare_states(left, right, p, v)
        same(row["assessment"], assessment, "independent trajectory comparison")
        require(assessment["passed"] or (not full and j == len(saved)-1), "trajectory gate fail-stop")
        difference = r540.previous._difference(right, left, row["difference"])
        values = summary.setdefault(name, {"prefix": None, "extension": None, "endpoint": None})
        segment = "prefix" if index <= 6 else "extension"
        maxima = values[segment] or {"position_norm_m": 0., "velocity_norm_m_s": 0.}
        values[segment] = {key: max(value, difference[key]) for key, value in maxima.items()}
        if index == 12:
            values["endpoint"] = difference
    same(report["comparison_summary"], summary, "independent comparison summary")
    return len(saved)


def replay_direction(report: Row, bundle: Row, native: dict[str, list[list[float]]],
                     dop: dict[str, list[list[float]]], direction: ModuleType, check: Check) -> Row:
    """Use independently replayed profiles and canonical returned node states."""
    t0 = bundle["initial"]["epoch_tdb_s"]
    rows = []
    for family, profiles in (("native", native), ("dop853", dop)):
        for profile in PROFILES:
            states = profiles[profile]
            require(len(states) == 13, "all direction states")
            for i, state in enumerate(states):
                check()
                node = report["node_table"][i]
                epoch = t0 + OFFSETS[i]
                same(node["hi_tdb_s"], epoch, "direction Moon epoch")
                rows.append({"profile": f"{family}_{profile}", "index": i, "epoch_tdb_s": epoch,
                             "spacecraft": state, "moon": node["bodies"]["Moon"]["state_si"]})
    return direction.verify(rows, bundle["gm_m3_s2"]["Moon"], bundle["radii_m"]["Moon"],
                            report["direction"], check=check)


def check_saved(report: Row, bundle: Row, references: ModuleType, native: ModuleType,
                check: Check = idle, event: Event = r540.noop_event, *, root: Path = ROOT,
                direction: ModuleType | None = None) -> Row:
    """Rebuild every available check; partial data can never qualify."""
    require(report["contract"] == CONTRACT and report["model"] == "B"
            and report["adapter_mode"] in ("reference", "injected-test"), "B study mode/contract")
    require(report["status"] in ("passed", "failed", "partial"), "study status")
    full = report["status"] == "passed"
    for key, value in (("origin", "SSB"), ("orientation", "J2000"), ("time_scale", "TDB"),
                       ("duration_s", 600.), ("budget_s", 60.), ("aberration_correction", "NONE"),
                       ("position_units", "m"), ("velocity_units", "m/s"), ("acceleration_units", "m/s^2"),
                       ("model_a_propagations", 0), ("gm_acquisitions", 0), ("optimizer_calls", 0),
                       ("mission_accuracy_verified", False), ("continuous_safety_verified", False),
                       ("scientific_verified", False), ("outward_status", "unavailable")):
        same(report[key], value, "scientific boundary: " + key)
    require("effects" not in report and "b_prefix" not in bundle, "no parking or A/B evidence")
    require(type(report["unavailable"]) is list, "unavailable study checks")
    if full:
        require(not report["unavailable"] and "error" not in report and report["finalization_gate"] == "passed",
                "successful study finalization/inventory")
        same(report["identities"]["before"], report["identities"]["after"], "before/after identity")
    else:
        require(type(report.get("error")) is dict, "partial earliest error")
    r540.check_ledger(report, check)
    result: Row = {"passed": full, "complete_native_profiles": 0, "complete_profiles": 0,
                   "native_telemetry": 0, "observations": 0, "comparisons": 0,
                   "comparison_summary": {}, "direction_rows": 0, "net_range_signs": 0,
                   "direction": None, "outward_status": "unavailable",
                   "continuous_safety_verified": False}
    if "inputs" not in report:
        require(not full and not any(report[key] for key in (
            "state_requests", "node_table", "rhs", "profiles", "comparisons", "trials",
            "observations", "native_profiles", "identities", "comparison_summary")),
            "work without frozen inputs")
        require(report.get("direction") is None and report.get("coast_mass_kg") is None,
                "direction or mass without frozen inputs")
        return result
    same(report["inputs"], bundle, "frozen input identity")
    check_handoff(report, bundle, full)
    r540.previous._check_metadata(report, bundle, full)
    error = report.get("error", {})
    native_kwargs: Row = {}
    if not full and error.get("type") == "TelemetryFailure":
        stage = error["stage"]
        require(stage in ("native-normal", "native-tighter"), "native telemetry failure stage")
        native_kwargs["expected_telemetry_failure"] = (stage.removeprefix("native-"), error["message"])
    native_rows = native.replay(report["native_profiles"], bundle, check=check, event=event,
                                complete=full, **native_kwargs)
    r540.previous._check_native_counts(report, full)
    r540.check_request_sequence(report, bundle, check)
    groups, cache = r540.replay_profiles(report, bundle, references, check, event)
    trial_membership = r540.check_trials(report, check, event)
    observed = r540.replay_observations(report, bundle, references, cache, groups, trial_membership, check, event)
    native_states = {name: [row["state"] for row in rows] for name, rows in native_rows.items()}
    dop = {p["name"]: [_state(cache[id(row)]) for row in p["outputs"] if "derivative" in row]
           for p in report["profiles"]}
    for states in dop.values():
        if states:
            initial = bundle["initial"]
            same(states[0], initial["position_m"] + initial["velocity_m_s"], "adaptive exact initial state")
    compared = replay_comparisons(report, native_states, dop, references, check)
    if full:
        require(compared == 39 and observed == 52, "complete post-cutoff B results")
        check_complete_counts(report)
    if full or report.get("direction") is not None:
        require(compared == 39 and observed == 52, "direction requires all trajectory and force operands")
        if direction is None:
            require(report["adapter_mode"] == "injected-test", "verified direction auditor required")
            direction = load_pure(root, DIRECTION, None, check)
        checked = replay_direction(report, bundle, native_states, dop, direction, check)
        result.update(direction=checked, direction_rows=len(checked["rows"]),
                      net_range_signs=len(checked["net_ranges"]))
        if full:
            result["outward_status"] = checked["classification"]
    result.update(complete_native_profiles=sum(len(rows) == 13 for rows in native_rows.values()),
                  complete_profiles=sum(p.get("raw_returned", {}).get("success") is True
                                        and len(p["outputs"]) == 13 and all("derivative" in row for row in p["outputs"])
                                        for p in report["profiles"]),
                  native_telemetry=report["counts"].get("native_telemetry", {}).get("completed", 0),
                  observations=observed, comparisons=compared, comparison_summary=report["comparison_summary"])
    return result


def check_complete_counts(report: Row) -> None:
    n_rhs = len(report["rhs"])
    counts = report["counts"]
    expected = {"rhs": n_rhs, "states": 4*(n_rhs+13), "trials": len(report["trials"]),
                "binary64_fields": 3*(n_rhs+26), "dynamic_totals": n_rhs+26,
                "solves": 2, "identities": 2, "native_arcs": 2, "native_guard_reads": 5412,
                "native_reference_fields": 156, "native_telemetry": 26, **r540.SAMPLES}
    if report["adapter_mode"] == "reference":
        expected.update(initializations=1, metadata=30)
    else:
        require(not any(name in counts for name in ("initializations", "metadata")),
                "unexpected native metadata counters in injected study")
    for name, value in expected.items():
        same(counts[name], {"attempted": value, "completed": value,
                            "returned": value if name in r540.OPAQUE else 0}, "complete count: " + name)
    evaluations = sum(3 if row["exact_tdb_s"] == str(Fraction(row["hi_tdb_s"])) else 6
                      for row in report["observations"])
    same(counts["record_evaluations"], {"attempted": evaluations, "returned": 0,
                                       "completed": evaluations}, "exact sampled record count")


def check_study_receipts(path: Path, report: Row, raw: bytes, check: Check = idle) -> Row:
    hashes: dict[str, str] = {}
    entries: dict[str, Row] = {}
    for name in ("attempt", "receipt", "parent-attempt", "parent-receipt"):
        check()
        data = path.with_suffix("." + name + ".json").read_bytes()
        hashes[name + "_sha256"] = digest(data)
        entries[name] = parse(data)
    attempt, child, marker, parent = entries.values()
    for item in (attempt, marker, parent):
        same(item["contract"], CONTRACT, "study receipt contract")
    same(attempt["adapter_mode"], "reference", "real study attempt")
    same(child["status"], report["status"], "study child status")
    same(child["finalization_gate"], report["finalization_gate"], "study child finalization")
    for key, value in (("attempt_sha256", hashes["attempt_sha256"]),
                       ("child_receipt_sha256", hashes["receipt_sha256"]),
                       ("parent_attempt_sha256", hashes["parent-attempt_sha256"]),
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
                <= number(parent["elapsed_s"], "study parent elapsed") <= 60, "study inclusive timing")
        same(report["identities"]["before"]["revision"], parent["revision"], "study snapshot revision")
    else:
        require(parent["returncode"] != 0, "failed study exit code")
    return hashes


def verify_identities(root: Path, report: Row, bundle: Row, tested: dict[str, str], check: Check) -> Row:
    identities = report["identities"]
    if not identities:
        require(report["status"] != "passed" and not report["state_requests"] and not report["native_profiles"],
                "initial identity required before science")
        return {}
    require(set(identities) <= {"before", "after"} and "before" in identities, "snapshot order")
    evidence = "0145-short-coast-evidence.py"
    pinned = r540.PURE_PINS[evidence]
    same(bundle["protected_sha256"][str(ARTIFACTS / evidence)], pinned, "pinned snapshot helper")
    snapshot_checker = r540.load_pure(root, evidence, pinned, check)
    prefixes = tuple(str(ARTIFACTS / name) for name in ("0186-long-b-", "0189-post-cutoff-"))
    extras = {name: value for name, value in tested.items() if name.startswith(prefixes) and name.endswith(".py")}
    result = {}
    for when, wire in identities.items():
        check()
        same(wire["dirty"], [], "clean saved study checkout")
        for key in r540.COMMON_IDENTITY:
            same(wire[key], bundle["historical_identity"][key], "original scientific identity " + key)
            same(wire[key], bundle["b_runtime"][key], "saved B scientific identity " + key)
        snapshot = deepcopy(wire)
        for name, expected in extras.items():
            same(snapshot["source_sha256"].pop(name), expected, "snapshot tested helper " + name)
        result[when] = snapshot_checker.verify_snapshot(snapshot, bundle["kernel_manifest"], check, checkout=root)
    return result


def write_result(result: Row, stream: TextIO, receipt: TextIO, output: Path, budget: Any) -> None:
    """Revoke a direction verdict on failure to serialize and finalize evidence."""
    def rewrite(target: TextIO, payload: Row) -> None:
        target.seek(0)
        target.truncate()
        json.dump(payload, target, allow_nan=False, separators=(",", ":"))
        target.flush()

    try:
        result.update(finalization_gate="passed", elapsed_before_flush_s=budget.elapsed())
        budget.check()
        rewrite(stream, result)
        budget.check()
        rewrite(receipt, {"finalization_gate": "passed", "status": result["audit_status"],
                          "evidence_sha256": digest(output.read_bytes()),
                          "started_s": budget.start_s, "elapsed_s": budget.elapsed()})
        budget.check()
    except FAILURES as error:
        result.setdefault("error", {"stage": "finalization", "type": type(error).__name__, "message": str(error)})
        result.update(audit_status="rejected", finalization_gate="failed", outward_status="unavailable")
        if "checks" in result:
            result["checks"].update(passed=False, outward_status="unavailable")
        rewrite(stream, result)
        rewrite(receipt, {"finalization_gate": "failed", "status": "rejected",
                          "evidence_sha256": digest(output.read_bytes()), "started_s": budget.start_s})


def audit(path: Path, output: Path, *, root: Path = ROOT, clock: Callable[[], float] = monotonic,
          started_s: float | None = None, manifest_sha256: str | None = None,
          inputs_loader: Callable[[Path, Check], Row] | None = None,
          references: ModuleType | None = None, native: ModuleType | None = None) -> Row:
    """One separate audit; only the external launcher may bind a reference run."""
    injected = inputs_loader is not None or references is not None or native is not None or clock is not monotonic
    if injected:
        require(inputs_loader is not None and references is not None and native is not None,
                "injected audit needs all synthetic adapters")
    else:
        require(started_s is not None and started_s <= PROCESS_START and manifest_sha256 is not None,
                "external audit baseline and manifest digest required")
    start = started_s if started_s is not None else clock()
    budget = r540.Budget(clock, start)
    mode = "injected-test" if injected else "reference"
    result: Row = {"contract": CONTRACT, "audit_status": "rejected", "scientific_verified": False,
                   "adapter_mode": mode, "budget_s": 10.0, "counts": budget.counts, "ledger": budget.ledger,
                   "native_calls": 0, "scientific_imports": 0, "kernel_loads": 0, "spacecraft_propagations": 0,
                   "outward_status": "unavailable"}
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
            direction, prepare = None, None
            tested: dict[str, str] = {}
            if not injected:
                r540.split.fresh()
                same(report["adapter_mode"], "reference", "study mode for real audit")
                same(report["preparation_manifest_sha256"], manifest_sha256, "bound study/preparation")
                result["study_receipts"] = check_study_receipts(path, report, raw, budget.check)
                preparation = (root / PREPARATION).read_bytes()
                same(digest(preparation), manifest_sha256, "external preparation digest")
                tested = parse(preparation)["tested_source_sha256"]
                same(report["tested_source_sha256"], tested, "study tested source identities")

                def bound_helper(name: str) -> ModuleType:
                    return load_pure(root, name, tested[str(ARTIFACTS / name)], budget.check)

                prepare = bound_helper(PREPARE)
                same(prepare.verify(root, manifest_sha256, budget.check), tested, "verified preparation")
                assets, references, native, direction = (bound_helper(name) for name in (
                    INPUTS, "0186-long-b-reference.py", "0186-long-b-native-replay.py", DIRECTION))
                inputs_loader = assets.load
            else:
                same(report["adapter_mode"], "injected-test", "only injected study data in test audit")
            assert inputs_loader is not None and references is not None and native is not None
            bundle = inputs_loader(root, budget.check)
            stage = "saved-data"
            result["checks"] = check_saved(report, bundle, references, native, budget.check, budget.event,
                                           root=root, direction=direction)
            if not injected:
                stage = "identities"
                assert prepare is not None
                result["snapshot_checks"] = verify_identities(root, report, bundle, tested, budget.check)
                same(prepare.verify(root, manifest_sha256, budget.check), tested, "final tested source identities")
                same(digest(path.read_bytes()), result["study_sha256"], "study readback identity")
                same(check_study_receipts(path, report, raw, budget.check), result["study_receipts"],
                     "final study receipt identities")
                r540.split.fresh()
            result["audit_status"] = "passed" if result["checks"]["passed"] else "partial"
            result["outward_status"] = result["checks"]["outward_status"]
        except FAILURES as error:
            result["error"] = {"stage": stage, "type": type(error).__name__, "message": str(error)}
            if "checks" in result:
                result["checks"].update(passed=False, outward_status="unavailable")
        write_result(result, stream, receipt_stream, output, budget)
    return result
