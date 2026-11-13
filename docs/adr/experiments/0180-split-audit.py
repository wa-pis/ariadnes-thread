"""Independent ADR0179 saved-data audit; no candidate or scientific imports."""
from __future__ import annotations

# ruff: noqa: E402 -- Include imports in the process budget.
from time import monotonic
PROCESS_START = monotonic()

import argparse
from collections.abc import Callable
from copy import deepcopy
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
ARTIFACTS = Path("docs/adr/experiments")
CONTRACT = "ADR0179"
BODIES = ("Sun", "Moon", "Earth")
PROFILES = ("normal", "tighter")
OFFSETS = (0., 50., 100., 150., 200., 250., 300.)
CAPS = {"rhs": 10000, "trials": 1000, "binary64_fields": 20028, "dynamic_totals": 10014,
        "body_checks": 84, "moon_earth_checks": 28, "record_evaluations": 168,
        "source_rows": 56, "reference_fields": 448, "model_totals": 28, "native_guards": 42}
OPAQUE = {"states", "solves", "identities", "metadata", "initializations"}
STUDY_CAPS = CAPS | {"states": 40028, "solves": 2, "identities": 2, "metadata": 30, "initializations": 1}
HELPERS = ("0163-corrected-inputs.py", "0180-split-reference.py", "0180-split-integrator.py",
           "0180-split-study.py", "0180-split-audit.py", "0180-split-launch.py")
BASE_AUDIT = "0163-corrected-audit.py"
BASE_SHA256 = "18d8bcae5f544f5176be5c9070e7cfc4fc00accadc634dee45ea952e4c265bc5"
ARCHIVE_SHA256 = "e4fbf8a12006c79efd2a3dab447ac8adde0703218aaf5210544926400a0710f1"
SAMPLES = {"body_checks": 84, "moon_earth_checks": 28, "source_rows": 56,
           "reference_fields": 448, "model_totals": 28}
FAILURES = (ValueError, TypeError, KeyError, IndexError, AttributeError, OSError, ImportError,
            RuntimeError, ArithmeticError)
type Row = dict[str, Any]
type Check = Callable[[], None]
type Event = Callable[[str, str], None]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def load_pure(root: Path, name: str, expected: str, check: Check) -> ModuleType:
    require(name in (BASE_AUDIT, HELPERS[0], HELPERS[1], "0145-short-coast-evidence.py"),
            "audit cannot load candidate code")
    check()
    path = root / ARTIFACTS / name
    raw = path.read_bytes()
    require(digest(raw) == expected, "pure helper SHA256: " + name)
    spec = importlib.util.spec_from_file_location("split_audit_" + name.replace("-", "_"), path)
    require(spec is not None and spec.loader is not None, "audit loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    check()
    return module


def idle() -> None:
    pass


def noop_event(_operation: str, _phase: str) -> None:
    pass


base = load_pure(ROOT, BASE_AUDIT, BASE_SHA256, idle)
number = base.number
vector = base.vector
same = base.same
parse = base.parse


class Budget:
    """Track audit work independently of claims in the study."""

    def __init__(self, clock: Callable[[], float], start_s: float) -> None:
        self.clock = clock
        self.start_s = number(start_s, "start_s")
        self.counts = {name: {"attempted": 0, "completed": 0} for name in CAPS}
        self.ledger: list[dict[str, str]] = []

    def elapsed(self) -> float:
        return number(self.clock(), "clock") - self.start_s

    def check(self) -> None:
        require(0 <= self.elapsed() <= 10.0, "audit deadline/clock")

    def event(self, operation: str, phase: str) -> None:
        require(operation in CAPS and phase in ("attempt", "complete"), "audit event")
        count = self.counts[operation]
        if phase == "attempt":
            self.check()
            require(count["attempted"] < CAPS[operation], "audit cap: " + operation)
            count["attempted"] += 1
        else:
            require(count["completed"] < count["attempted"], "audit unmatched completion")
            count["completed"] += 1
        self.ledger.append({"operation": operation, "phase": phase})
        self.check()


def epoch(row: Row, initial: Row) -> tuple[float, float, float, Fraction]:
    s = number(row["elapsed_s"], "elapsed_s")
    require(0 <= s <= 300, "elapsed outside interval")
    exact = Fraction(number(initial["epoch_tdb_s"], "initial epoch")) + Fraction(s)
    hi = float(exact)
    lo = float(exact - Fraction(hi))
    require(Fraction(hi) + Fraction(lo) == exact, "split exact epoch")
    same(row["hi_tdb_s"], hi, "rounded epoch hi")
    same(row["lo_s"], lo, "signed epoch lo")
    return s, hi, lo, exact


def request(body: str, observer: str, hi: float) -> Row:
    return {"body": body, "observer": observer, "frame": "J2000", "aberration": "NONE", "epoch_tdb_s": hi}


def validate_source(raw: Row, metadata: Row, *, complete: bool) -> None:
    require(type(raw) is dict, "raw source row")
    same({key: raw[key] for key in metadata}, metadata, "state request/source provenance")
    require("state_km_km_s" in raw, "missing raw state")
    if complete or "state_si" in raw:
        values = vector(raw["state_km_km_s"], 6, "raw source")
        if metadata["observer"] == "SSB":
            same(raw["state_si"], [v * 1000 for v in values], "source SI conversion")


def validate_sources(row: Row, initial: Row, *, complete: bool) -> list[Row]:
    if "elapsed_s" not in row:
        require(not complete and not row.get("bodies") and "moon_earth" not in row,
                "sources without epoch")
        return []
    _, hi, _, _ = epoch(row, initial)
    bodies = row.get("bodies", {})
    require(type(bodies) is dict and tuple(bodies) == BODIES[:len(bodies)], "source body order")
    has_geocentric = "moon_earth" in row
    if complete or has_geocentric:
        require(tuple(bodies) == BODIES, "SSB prefix before geocentric return")
    if complete:
        require(has_geocentric, "missing Moon/Earth return")
    requests = []
    for body, raw in bodies.items():
        metadata = request(body, "SSB", hi)
        validate_source(raw, metadata, complete=complete or has_geocentric or body != tuple(bodies)[-1])
        requests.append(metadata)
    if has_geocentric:
        metadata = request("Moon", "Earth", hi)
        validate_source(row["moon_earth"], metadata, complete=complete)
        requests.append(metadata)
    return requests


def reconstruct_row(row: Row, bundle: Row, *, complete: bool = True,
                    check: Check = idle, event: Event = noop_event) -> Row:
    """Rebuild solver operands and fields from raw returns, including partial prefixes."""
    initial = bundle["initial"]
    have_motion = "motion" in row
    have_geometry = "geometry" in row and bool(row["geometry"])
    validate_sources(row, initial, complete=complete or have_motion)
    if not complete and not have_motion:
        require(not have_geometry and "derivative" not in row, "geometry before motion")
        if "correction" in row:
            vector(row["correction"], 6, "partial correction")
        return {}
    s, _, lo, _ = epoch(row, initial)
    y = vector(row["correction"], 6, "correction")
    r0 = vector(initial["position_m"], 3, "initial position")
    v0 = vector(initial["velocity_m_s"], 3, "initial velocity")
    q, w = y[:3], y[3:]
    drift = [v * s for v in v0]
    motion = {"elapsed_s": s, "q_m": q, "w_m_s": w, "drift_m": drift,
              "position_m": [math.fsum((r, d, delta)) for r, d, delta in zip(r0, drift, q, strict=True)],
              "velocity_m_s": [math.fsum((v, delta)) for v, delta in zip(v0, w, strict=True)]}
    same(row["motion"], motion, "independent motion")
    saved = row.get("geometry", {})
    require(type(saved) is dict and tuple(saved) == BODIES[:len(saved)], "geometry prefix")
    if complete:
        require(tuple(saved) == BODIES, "three complete geometries")
    fields = tuple(body for body in saved if "acceleration_m_s2" in saved[body])
    require(fields == BODIES[:len(fields)] and len(fields) <= 2, "Sun/Moon field prefix")
    if fields:
        require(tuple(saved) == BODIES, "all geometry guards before fields")
    geometry: Row = {}
    for body, stored in saved.items():
        check()
        raw = row["bodies"][body]["state_km_km_s"]
        state = [value * 1000 for value in vector(raw, 6, "SSB raw state")]
        c = [v * lo for v in state[3:]]
        g: Row = {"rephasing_m": c}
        radius = number(bundle["radii_m"][body], "radius")
        require(radius > 0, "positive guard radius")
        if body == "Moon":
            e = row["bodies"]["Earth"]["state_km_km_s"][:3]
            m = row["moon_earth"]["state_km_km_s"][:3]
            # Assemble by independently adding the exact barycentric source and
            # subtracting the decomposed spacecraft state, with no intermediate RN.
            d2 = [1000*(Fraction(e[j])+Fraction(m[j])) - sum(
                map(Fraction, (r0[j], drift[j], q[j], -c[j]))) for j in range(3)]
            d = [float(value) for value in d2]
            g["pre_round_separation_m"] = list(map(str, d2))
            exact_guard = sum(value*value for value in d2) > Fraction(radius)**2
        else:
            d = [math.fsum((state[j], -r0[j], -drift[j], -q[j], c[j])) for j in range(3)]
            exact_guard = True
        rho = math.hypot(*d)
        g.update(separation_m=d, distance_m=rho)
        same({key: stored[key] for key in g}, g, body + " geometry")
        require(set(stored) <= set(g) | {"acceleration_m_s2"}, body + " geometry shape")
        geometry[body] = g
        if not (exact_guard and math.isfinite(rho) and rho > radius):
            require(not complete and body == tuple(saved)[-1] and not fields,
                    "runtime exterior guard: " + body)
    for body in fields:
        event("binary64_fields", "attempt")
        g = geometry[body]
        rho = g["distance_m"]
        mu = number(bundle["gm_m3_s2"][body], "GM")
        square = rho*rho
        require(mu > 0 and math.isfinite(square) and square > 0, "positive finite field operands")
        force = vector([mu * (value/rho) / square for value in g["separation_m"]], 3, "force")
        same(saved[body]["acceleration_m_s2"], force, body + " field")
        g["acceleration_m_s2"] = force
        event("binary64_fields", "complete")
    result = {"motion": motion, "geometry": geometry}
    if complete or "derivative" in row:
        require(fields == BODIES[:2], "two fields before derivative")
        event("dynamic_totals", "attempt")
        derivative = w + [math.fsum(geometry[b]["acceleration_m_s2"][j] for b in fields)
                          for j in range(3)]
        same(row["derivative"], derivative, "RHS derivative")
        result["derivative"] = derivative
        event("dynamic_totals", "complete")
    return result


def source_rows(row: Row, bundle: Row) -> dict[str, Row]:
    result = {}
    for body in BODIES:
        template = deepcopy(bundle["source_rows_template"][body])
        template.pop("assessment", None)
        template.update(row["bodies"][body], elapsed_s=row["elapsed_s"],
                        hi_tdb_s=row["hi_tdb_s"], lo_s=row["lo_s"])
        result[body] = template
    result["Moon/Earth"] = dict(row["moon_earth"], elapsed_s=row["elapsed_s"],
                                hi_tdb_s=row["hi_tdb_s"], lo_s=row["lo_s"],
                                segments=[segment for segment in result["Moon"]["segments"]
                                          if (segment["body"], segment["centre"]) == (301, 399)])
    return result


def archived_hi_words(root: Path) -> frozenset[str]:
    raw = (root / ARTIFACTS / "0178-verification.json").read_bytes()
    require(digest(raw) == ARCHIVE_SHA256, "archived sample SHA256")
    rows = parse(raw)["rows_in_r524_order"]
    words = frozenset(row["hi_tdb_s_hex"] for row in rows)
    require(len(rows) == 28 and len(words) == 19, "archived sample inventory")
    return words


def check_ledger(report: Row, check: Check) -> None:
    counts = report["counts"]
    require(type(counts) is dict and set(counts) <= set(STUDY_CAPS), "study counter inventory")
    rebuilt = {name: {"attempted": 0, "returned": 0, "completed": 0} for name in counts}
    phases = {"attempt": "attempted", "return": "returned", "complete": "completed"}
    for index, row in enumerate(report["ledger"]):
        if index % 512 == 0:
            check()
        name = row["operation"]
        require(name in rebuilt and row["phase"] in phases, "saved ledger event")
        phase = phases[row["phase"]]
        c = rebuilt[name]
        if name == "solves" and phase == "attempted" and c["attempted"] == 1:
            require(c["completed"] == 1 and all(
                rebuilt.get(key, {}).get("completed") == limit//2 for key, limit in SAMPLES.items()),
                "normal sampled gates must complete before tighter")
        if name == "states":
            require(phase != "attempted" or c["attempted"] == c["completed"],
                    "overlapping state attempts")
        c[phase] += 1
        require(c["completed"] <= c["attempted"] <= STUDY_CAPS[name], "saved counter order/cap: " + name)
        if name in OPAQUE:
            require(c["completed"] <= c["returned"] <= c["attempted"], "saved opaque return order")
        else:
            require(c["returned"] == 0, "unexpected opaque return")
    same(counts, rebuilt, "saved ledger counters")


def check_request_sequence(report: Row, bundle: Row, check: Check) -> None:
    """Bind native attempts to an ordered stream of shared-node then RHS tuples."""
    recorded = report["state_requests"]
    counts = report["counts"].get("states", {"attempted": 0, "returned": 0, "completed": 0})
    n = report["counts"].get("rhs", {}).get("attempted", 0)
    require(type(recorded) is list and counts["attempted"] <= 4*(n+7), "state attempts cap")
    require(len(recorded) <= counts["attempted"] <= len(recorded)+1, "state attempt record count")
    require(report["status"] != "passed" or len(recorded) == counts["attempted"], "state attempts complete")
    expected: list[Row] = []
    returned = 0
    table, rhs = report["node_table"], report["rhs"]
    require(len(table) <= 7 and (not rhs or len(table) == 7), "shared table before RHS")
    for index, row in enumerate(table + rhs):
        check()
        if index < len(table) and "elapsed_s" in row:
            same(row["elapsed_s"], OFFSETS[index], "fixed node offset")
        complete = index < len(table)+len(rhs)-1 or report["status"] == "passed"
        prefix = validate_sources(row, bundle["initial"], complete=complete)
        returned += len(prefix)
        expected.extend(prefix)
        if index == len(table)+len(rhs)-1 and "elapsed_s" in row and len(prefix) < 4:
            hi = row["hi_tdb_s"]
            queries = [request(body, "SSB", hi) for body in BODIES] + [request("Moon", "Earth", hi)]
            if len(recorded) == returned+1:
                expected.append(queries[len(prefix)])
    same(recorded, expected, "ordered state request/return evidence")
    require(returned == counts["returned"] and returned-counts["completed"] in (0, 1),
            "returned/completed state evidence")
    ssb = sum(item["observer"] == "SSB" for item in recorded)
    require(ssb <= 3*(n+7) and len(recorded)-ssb <= n+7, "separate SSB and Moon/Earth caps")


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


def replay_comparisons(report: Row, bundle: Row, reference: ModuleType, cache: dict[int, Row]) -> list[Row]:
    # Partial geometry rows are not trajectory comparison inputs.
    view = dict(report, profiles=[
        dict(profile, outputs=[{"motion": cache[id(row)]["motion"]} for row in profile["outputs"]
                              if "derivative" in row])
        for profile in report["profiles"]
    ])
    expected = base.expected_comparisons(view, bundle, reference)
    saved = report["comparisons"]
    require(type(saved) is list and len(saved) <= 21, "comparison cap")
    same(saved, expected[:len(saved)], "independent trajectory comparison prefix")
    negatives = [i for i, item in enumerate(saved) if not item["assessment"]["passed"]]
    require(not negatives or (report["status"] != "passed" and negatives == [len(saved)-1]),
            "trajectory comparison fail-stop")
    return saved


def replay_observations(report: Row, bundle: Row, reference: ModuleType, cache: dict[int, Row],
                        groups: dict[str, list[Row]], archive: frozenset[str], check: Check,
                        event: Event) -> int:
    full = report["status"] == "passed"
    selected = []
    for profile in report["profiles"]:
        name = profile["name"]
        outputs = [row for row in profile["outputs"] if "derivative" in row]
        rows = [row for row in groups[name] if row.get("completed")][:7]
        selected.extend((name, kind, i, row)
                        for kind, samples in (("output", outputs), ("rhs", rows))
                        for i, row in enumerate(samples))
    observations = report["observations"]
    require(type(observations) is list and len(observations) <= min(28, len(selected)), "observation cap")
    if full:
        require(len(observations) == 28, "28 complete observations")
    if len(report["profiles"]) == 2:
        require(len(observations) >= 14, "normal force gates before tighter")
    completed = 0
    for ordinal, (saved, (name, kind, i, row)) in enumerate(zip(observations, selected)):
        check()
        same([saved["profile"], saved["kind"], saved["index"]], [name, kind, i], "fixed observation selection")
        _, hi, _, exact = epoch(row, bundle["initial"])
        same(saved["hi_tdb_s"], hi, "sample hi")
        same(saved["exact_tdb_s"], str(exact), "sample exact epoch")
        same(saved["hi_seen_in_r524"], hi.hex() in archive, "sample archive overlap")
        if ordinal < 14 and len(report["profiles"]) == 2:
            require(name == "normal" and "assessment" in saved, "normal sample required before tighter")
        rebuilt = cache[id(row)]
        progress: Row = {}
        may_fail = (not full and ordinal == len(observations)-1
                    and not (ordinal < 14 and len(report["profiles"]) == 2))
        try:
            assessment = reference.assess_observation(
                bundle["initial"], rebuilt["motion"], source_rows(row, bundle), rebuilt["geometry"],
                bundle["gm_m3_s2"], bundle["radii_m"], event, check=check, progress=progress)
        except FAILURES:
            require(may_fail and "assessment" not in saved, "unexpected reference failure")
            # A timeout in this audit is never attributed to the study.
            check()
            base.partial_value(saved["progress"], progress, "partial sampled reference")
            continue
        if "assessment" not in saved:
            require(may_fail, "missing completed assessment")
            base.partial_value(saved["progress"], progress, "partial sampled reference")
            continue
        same(saved["assessment"], assessment, "independent sampled force assessment")
        same(saved["progress"], progress, "independent sampled progress")
        require(assessment["passed"] is True or may_fail, "required sampled force gate")
        completed += 1
    return completed


def check_saved(report: Row, bundle: Row, reference: ModuleType, archive: frozenset[str],
                check: Check = idle, event: Event = noop_event) -> Row:
    """Replay the saved sample and all completed binary64 arithmetic."""
    require(report["contract"] == CONTRACT, "contract")
    require(report["adapter_mode"] in ("reference", "injected-test"), "study adapter mode")
    require(report["status"] in ("passed", "failed", "partial"), "study status")
    full = report["status"] == "passed"
    for key, value in (("origin", "SSB"), ("orientation", "J2000"), ("time_scale", "TDB"),
                       ("budget_s", 60.), ("aberration_correction", "NONE"), ("position_units", "m"),
                       ("velocity_units", "m/s"), ("acceleration_units", "m/s^2"),
                       ("native_propagations", 0), ("gm_acquisitions", 0), ("optimizer_calls", 0),
                       ("historical_final_identity_complete", False), ("mission_accuracy_verified", False),
                       ("continuous_safety_verified", False), ("scientific_verified", False)):
        same(report[key], value, "scientific boundary: " + key)
    require(type(report["unavailable"]) is list, "unavailable study checks")
    if not full:
        require(type(report.get("error")) is dict, "partial earliest error")
    else:
        require(not report["unavailable"] and "error" not in report, "full study has no unavailable checks")
    if "inputs" not in report:
        require(not full and not any(report[name] for name in
                ("state_requests", "node_table", "rhs", "profiles", "comparisons", "trials",
                 "observations", "native_guards", "identities")), "work without frozen inputs")
        check_ledger(report, check)
        return {"passed": False, "complete_profiles": 0, "observations": 0, "comparisons": 0}
    same(report["inputs"], bundle, "frozen input identity")
    check_ledger(report, check)
    check_request_sequence(report, bundle, check)
    if full:
        require(len(report["node_table"]) == 7, "complete node table")
        same(report["identities"]["before"], report["identities"]["after"], "before/after identity")
        require(report["finalization_gate"] == "passed", "study finalization")
    groups, cache = replay_profiles(report, bundle, reference, check, event)
    base.check_trials(report, check, event)
    base.check_native_guards(report, bundle, check, event)
    compared = replay_comparisons(report, bundle, reference, cache)
    observed = replay_observations(report, bundle, reference, cache, groups, archive, check, event)
    if full:
        require(len(compared) == 21 and observed == 28, "complete sampled results")
        rhs_count = len(report["rhs"])
        counts = report["counts"]
        expected = {"rhs": rhs_count, "states": 4*(rhs_count+7), "trials": len(report["trials"]),
                    "binary64_fields": 2*(rhs_count+14), "dynamic_totals": rhs_count+14,
                    "native_guards": 42, "solves": 2, "identities": 2, **SAMPLES}
        if report["adapter_mode"] == "reference":
            expected.update(initializations=1, metadata=30)
        for name, value in expected.items():
            counts_for_name = counts[name]
            require(counts_for_name["attempted"] == counts_for_name["completed"] == value,
                    "complete count: " + name)
        expected_records = sum(3 if row["exact_tdb_s"] == str(Fraction(row["hi_tdb_s"])) else 6
                               for row in report["observations"])
        same(counts["record_evaluations"], {"attempted": expected_records, "returned": 0,
                                          "completed": expected_records}, "exact sampled record count")
    return {"passed": full, "complete_profiles": sum(p.get("raw_returned", {}).get("success") is True
            and len(p["outputs"]) == 7 and all("derivative" in row for row in p["outputs"])
            for p in report["profiles"]),
            "observations": observed, "comparisons": len(compared),
            "historical_final_identity_repaired": False, "continuous_safety_verified": False}


def check_study_receipts(path: Path, report: Row, raw: bytes, check: Check) -> Row:
    receipt_raw = {}
    for name in ("attempt", "receipt", "parent-attempt", "parent-receipt"):
        check()
        receipt_raw[name] = path.with_suffix("." + name + ".json").read_bytes()
    attempt, child, parent_attempt, parent = (parse(data) for data in receipt_raw.values())
    same(attempt["contract"], CONTRACT, "study marker contract")
    same(parent["contract"], CONTRACT, "study parent contract")
    same(attempt["adapter_mode"], "reference", "study marker adapter mode")
    same(child["status"], report["status"], "study child status")
    same(child["finalization_gate"], report["finalization_gate"], "study child finalization")
    for name, value in (("attempt_sha256", digest(receipt_raw["attempt"])),
                        ("child_receipt_sha256", digest(receipt_raw["receipt"])),
                        ("parent_attempt_sha256", digest(receipt_raw["parent-attempt"])),
                        ("evidence_sha256", digest(raw)), ("phase", "study"),
                        ("preparation_sha256", report["preparation_manifest_sha256"])):
        same(parent[name], value, "study parent " + name)
    same(child["evidence_sha256"], digest(raw), "study child evidence")
    for name, value in (("contract", CONTRACT), ("phase", "study"),
                        ("revision", parent["revision"]), ("preparation_sha256", parent["preparation_sha256"])):
        same(parent_attempt[name], value, "study parent marker " + name)
    start = number(attempt["started_s"], "study start")
    same(child["started_s"], start, "study child start")
    same(parent["started_s"], start, "study parent start")
    require(type(parent["returncode"]) is int and type(parent["checkout_frozen"]) is bool,
            "study parent outcome types")
    if report["status"] == "passed":
        require(parent["returncode"] == 0 and parent["checkout_frozen"]
                and child["finalization_gate"] == parent["finalization_gate"] == "passed",
                "study parent finalization")
        require(0 <= number(report["elapsed_before_flush_s"], "study preflush elapsed")
                <= number(child["elapsed_s"], "study child elapsed")
                <= number(parent["elapsed_s"], "study parent elapsed") <= 60, "study inclusive timing")
        same(report["identities"]["before"]["revision"], parent["revision"], "study snapshot revision")
    else:
        require(parent["returncode"] != 0, "failed study exit code")
    return {name + "_sha256": digest(data) for name, data in receipt_raw.items()}


def checkout_inputs(root: Path, report: Row, check: Check) -> tuple[dict[str, str], dict[str, str]]:
    hashes = {name: digest((root / ARTIFACTS / name).read_bytes()) for name in HELPERS}
    same(report["helper_sha256"], hashes, "study helper identities")
    raw = (root / ARTIFACTS / "0180-verification.json").read_bytes()
    same(report["preparation_manifest_sha256"], digest(raw), "study preparation manifest")
    manifest = parse(raw)
    require(manifest["preparation_complete"] is True, "verified preparation required")
    tested = manifest["tested_source_sha256"]
    same(report["tested_source_sha256"], tested, "study tested source identities")
    for name, expected in hashes.items():
        same(tested[str(ARTIFACTS / name)], expected, "tested helper: " + name)
    same(tested[str(ARTIFACTS / BASE_AUDIT)], BASE_SHA256, "tested base audit")
    for name, expected in tested.items():
        check()
        target = (root / name).resolve()
        require(target.is_relative_to(root.resolve()), "tested path outside checkout")
        same(digest(target.read_bytes()), expected, "tested source: " + name)
    return hashes, tested


def verify_identities(root: Path, report: Row, bundle: Row, tested: dict[str, str], check: Check) -> Row:
    before = report["identities"].get("before")
    if before is None:
        require(report["status"] != "passed" and not report["state_requests"], "initial identity required")
        return {}
    snapshot_check = load_pure(root, "0145-short-coast-evidence.py",
        bundle["protected_sha256"][str(ARTIFACTS / "0145-short-coast-evidence.py")], check)
    result = {}
    for when, wire in report["identities"].items():
        require(when in ("before", "after"), "identity snapshot role")
        same(wire["kernels"], bundle["kernel_manifest"], "ordered thirteen-kernel identity")
        for key in ("versions", "imports", "native_binary", "conda_build", "resource_build",
                    "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime"):
            same(wire[key], bundle["historical_identity"][key], "frozen runtime " + key)
        snapshot = deepcopy(wire)
        for name in HELPERS:
            relative = str(ARTIFACTS / name)
            same(snapshot["source_sha256"].pop(relative), tested[relative], "snapshot helper hash: " + name)
        result[when] = snapshot_check.verify_snapshot(snapshot, bundle["kernel_manifest"], check, checkout=root)
    return result


def fresh() -> None:
    banned = {"numpy", "scipy", "spiceypy", "tudatpy", "space_nav"}
    require(not any(name.split(".")[0] in banned for name in sys.modules), "audit scientific imports")


def write_result(result: Row, stream: TextIO, receipt: TextIO, output: Path, budget: Budget) -> None:
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
        result.update(audit_status="rejected", finalization_gate="failed", scientific_verified=False)
        rewrite(stream, result)
        rewrite(receipt, {"finalization_gate": "failed", "status": "rejected",
                          "evidence_sha256": digest(output.read_bytes()), "started_s": budget.start_s})


def audit(path: Path, output: Path, *, root: Path = ROOT, clock: Callable[[], float] = monotonic,
          started_s: float | None = None, inputs_loader: Callable[[Path, Check], Row] | None = None,
          references: ModuleType | None = None) -> Row:
    """Audit exclusive saved evidence; success still requires the parent receipt."""
    injected = inputs_loader is not None or references is not None or clock is not monotonic
    if not injected:
        require(started_s is not None and started_s <= PROCESS_START, "external pre-child baseline required")
    start = started_s if started_s is not None else clock()
    budget = Budget(clock, start)
    mode = "injected-test" if injected else "reference"
    result: Row = {"contract": CONTRACT, "audit_status": "rejected", "scientific_verified": False,
                   "adapter_mode": mode, "budget_s": 10.0, "counts": budget.counts, "ledger": budget.ledger,
                   "native_calls": 0, "scientific_imports": 0, "kernel_loads": 0, "spacecraft_propagations": 0}
    attempt = output.with_suffix(".attempt.json")
    receipt = output.with_suffix(".receipt.json")
    require(not any(file.exists() for file in (output, attempt, receipt)), "exclusive audit evidence exists")
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
            if not injected:
                fresh()
                same(report["adapter_mode"], "reference", "study mode for real audit")
                result["study_receipts"] = check_study_receipts(path, report, raw, budget.check)
                hashes, tested = checkout_inputs(root, report, budget.check)
                inputs_loader = load_pure(root, HELPERS[0], hashes[HELPERS[0]], budget.check).load_inputs
                references = load_pure(root, HELPERS[1], hashes[HELPERS[1]], budget.check)
            require(inputs_loader is not None and references is not None, "audit requires both independent helpers")
            assert inputs_loader is not None and references is not None
            bundle = inputs_loader(root, budget.check)
            archive = archived_hi_words(root)
            stage = "saved-data"
            result["checks"] = check_saved(report, bundle, references, archive, budget.check, budget.event)
            if not injected:
                stage = "identities"
                result["snapshot_checks"] = verify_identities(root, report, bundle, tested, budget.check)
                same(checkout_inputs(root, report, budget.check), (hashes, tested), "final source identities")
                same(inputs_loader(root, budget.check), bundle, "final frozen inputs")
                same(digest(path.read_bytes()), result["study_sha256"], "study readback identity")
                same(check_study_receipts(path, report, raw, budget.check), result["study_receipts"],
                     "final study receipt identities")
                fresh()
            result["audit_status"] = "passed" if result["checks"]["passed"] else "partial"
        except FAILURES as error:
            result["error"] = {"stage": stage, "type": type(error).__name__, "message": str(error)}
        write_result(result, stream, receipt_stream, output, budget)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--started-s", type=float, required=True)
    args = parser.parse_args()
    answer = audit(args.study, args.output, started_s=args.started_s)
    raise SystemExit(0 if answer["audit_status"] == "passed" and answer["finalization_gate"] == "passed" else 2)
