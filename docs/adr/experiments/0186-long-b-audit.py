"""Independent ADR0185 saved-data audit. Import no candidate or scientific code."""

from __future__ import annotations

# ruff: noqa: E402 -- Include imports in the external process budget.
from time import monotonic

PROCESS_START = monotonic()

from collections.abc import Callable
from copy import deepcopy
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
CONTRACT = "ADR0185"
PURE_PINS = {
    "0183-earth-audit.py": "6cace255c1eb11e7c2c33aa05d9195325aeabadb3586d512ee272e2095c36b50",
    "0145-short-coast-evidence.py": "426fe4e0abe9b9dfcf6380d09e86e8dbf5748f66875f74b26b45dceb6ba5da14",
}
PURE_HELPERS = ("0186-long-b-inputs.py", "0186-long-b-reference.py", "0186-long-b-native-replay.py")
PREPARATION = ARTIFACTS / "0186-verification.json"
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
    module = ModuleType("long_b_audit_" + path.stem.replace("-", "_"))
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    check()
    return module


previous = load_pure(ROOT, "0183-earth-audit.py", PURE_PINS["0183-earth-audit.py"])
split = previous.split
base = previous.base
number, vector, same, parse = base.number, base.vector, base.same, base.parse
FAILURES = split.FAILURES
BODIES, PROFILES = split.BODIES, split.PROFILES
DURATION_S = 600.0
OFFSETS = tuple(float(s) for s in range(0, 601, 50))
EXTENSION_INTERVALS = tuple(zip(OFFSETS[6:-1], OFFSETS[7:], strict=True))
SAMPLES = {"body_checks": 156, "moon_earth_checks": 52, "source_rows": 156,
           "reference_fields": 1248, "model_totals": 52}
CAPS = {"rhs": 10000, "trials": 1000, "binary64_fields": 30078, "dynamic_totals": 10026,
        "native_reference_fields": 156, "native_telemetry": 26, "record_evaluations": 312, **SAMPLES}
OPAQUE = previous.OPAQUE
STUDY_CAPS = CAPS | {"states": 40052, "solves": 2, "identities": 2, "metadata": 30,
                     "initializations": 1, "native_arcs": 2, "native_guard_reads": 5412}
PROFILE_CAPS = {name: count//2 for name, count in SAMPLES.items()}


class Budget(split.Budget):
    """Independent 10 s limiter with the B-only actual-work ceilings."""

    def __init__(self, clock: Callable[[], float], start_s: float) -> None:
        self.clock = clock
        self.start_s = number(start_s, "audit start")
        self.counts: dict[str, dict[str, int]] = {}
        self.ledger: list[dict[str, str]] = []

    def check(self) -> None:
        require(0 <= self.elapsed() <= 10., "audit deadline/clock")

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


def epoch(row: Row, initial: Row) -> tuple[float, float, float, Fraction]:
    s = number(row["elapsed_s"], "elapsed_s")
    require(0 <= s <= DURATION_S, "elapsed outside interval")
    exact = Fraction(number(initial["epoch_tdb_s"], "initial epoch")) + Fraction(s)
    hi = float(exact)
    lo = float(exact - Fraction(hi))
    require(Fraction(hi) + Fraction(lo) == exact, "split exact epoch")
    same(row["hi_tdb_s"], hi, "rounded epoch hi")
    same(row["lo_s"], lo, "signed epoch lo")
    return s, hi, lo, exact


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
        metadata = split.request(body, "SSB", hi)
        split.validate_source(raw, metadata, complete=complete or has_geocentric or body != tuple(bodies)[-1])
        requests.append(metadata)
    if has_geocentric:
        metadata = split.request("Moon", "Earth", hi)
        split.validate_source(row["moon_earth"], metadata, complete=complete)
        requests.append(metadata)
    return requests


def reconstruct_geometry(row: Row, bundle: Row, *, complete: bool, check: Check) -> Row:
    """Rebuild geometry from raw returns without using study calculations."""
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
    require(fields == BODIES[:len(fields)], "Sun/Moon/Earth field order")
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
    return {"motion": motion, "geometry": geometry}


def reconstruct_row(row: Row, bundle: Row, *, complete: bool = True,
                    check: Check = idle, event: Event = noop_event) -> Row:
    """Rebuild the common split geometry, then validate the three B fields and sum."""
    result = reconstruct_geometry(row, bundle, complete=complete, check=check)
    saved = row.get("geometry", {})
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
            require(done("native_arcs") == 2 and done("native_telemetry") == 26,
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


def check_request_sequence(report: Row, bundle: Row, check: Check) -> None:
    """Bind native attempts to an ordered stream of shared-node then RHS tuples."""
    recorded = report["state_requests"]
    counts = report["counts"].get("states", {"attempted": 0, "returned": 0, "completed": 0})
    n = report["counts"].get("rhs", {}).get("attempted", 0)
    require(type(recorded) is list and counts["attempted"] <= 4*(n+13), "state attempts cap")
    require(len(recorded) <= counts["attempted"] <= len(recorded)+1, "state attempt record count")
    require(report["status"] != "passed" or len(recorded) == counts["attempted"], "state attempts complete")
    expected: list[Row] = []
    returned = 0
    table, rhs = report["node_table"], report["rhs"]
    require(len(table) <= 13 and (not rhs or len(table) == 13), "shared table before RHS")
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
            queries = [split.request(body, "SSB", hi) for body in BODIES] + [split.request("Moon", "Earth", hi)]
            if len(recorded) == returned+1:
                expected.append(queries[len(prefix)])
    same(recorded, expected, "ordered state request/return evidence")
    require(returned == counts["returned"] and returned-counts["completed"] in (0, 1),
            "returned/completed state evidence")
    ssb = sum(item["observer"] == "SSB" for item in recorded)
    require(ssb <= 3*(n+13) and len(recorded)-ssb <= n+13, "separate SSB and Moon/Earth caps")


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
        require(type(outputs) is list and len(outputs) <= 13, "output count")
        if raw is None:
            require(not full and last and not outputs, "missing complete raw arrays")
            continue
        require(type(raw["success"]) is bool and type(raw["status"]) is int, "solver status types")
        t = vector(raw["t"], len(raw["t"]), "raw solver times")
        require(len(t) <= 13 and t == list(OFFSETS[:len(t)]), "raw output epoch grid")
        require(type(raw["y"]) is list and len(raw["y"]) == 6, "raw solver y shape")
        y = [vector(values, len(t), "raw y row") for values in raw["y"]]
        completed = [row for row in groups[name] if row.get("completed")]
        same(raw["nfev"], len(completed), "nfev versus completed RHS")
        if raw["success"]:
            require(t == list(OFFSETS) and raw["status"] == 0, "complete solver return")
            solver = profile["solver_state"]
            same(solver["t_s"], DURATION_S, "solver internal endpoint")
            same(solver["status"], "finished", "solver internal final status")
            # The step observer runs before SciPy's dense-output callbacks.
            require(type(solver["nfev"]) is int and len(completed)-solver["nfev"] in (0, 3),
                    "solver internal nfev/dense-output count")
            same(solver["y"], [values[-1] for values in y], "solver internal final correction")
            require(all(values[0] == 0 for values in y), "zero initial correction")
        else:
            require(not full and last and not outputs, "solver fail-stop")
        for j, output in enumerate(outputs):
            check()
            same([output["profile"], output["index"]], [name, j], "output profile/index")
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
            require(len(outputs) == 13 and len(completed) >= 7
                    and any(row["lo_s"] != 0 for row in completed[:7]),
                    "complete outputs and nonzero-lo RHS sample")
    return groups, cache


def check_trials(report: Row, check: Check,
                 event: Event) -> dict[int, int]:
    require(len(report["trials"]) <= CAPS["trials"], "trial cap")
    rhs = report["rhs"]
    full = report["status"] == "passed"
    membership: dict[int, int] = {}
    previous = -1
    starts = {p["name"]: p["rhs_start"] for p in report["profiles"]}
    prior = {name: (0.0, [0.0]*6, -1) for name in PROFILES}
    for i, trial in enumerate(report["trials"]):
        check()
        event("trials", "attempt")
        require(trial["index"] == i and trial["profile"] in PROFILES, "trial ordinal/profile")
        name = trial["profile"]
        require(name in starts and PROFILES.index(name) >= previous, "ordered trial profile")
        previous = PROFILES.index(name)
        left, right = trial["rhs_start"], trial["rhs_end"]
        require(type(left) is int and type(right) is int and 0 <= left <= right <= len(rhs), "trial RHS range")
        require(all(row["profile"] == name for row in rhs[left:right]), "trial source profile")
        start = number(trial["t_before_s"], "trial start")
        old_t, old_y, last_end = prior[name]
        require(start == old_t and left >= max(starts[name]+1, last_end),
                "trial controller continuity")
        for rhs_index in range(left, right):
            require(rhs_index not in membership, "overlapping trial stage range")
            membership[rhs_index] = i
        if trial["accepted"] is None:
            require(not full and i == len(report["trials"])-1 and trial["decision"] == "unavailable", "unavailable final trial")
            require(0 <= start < DURATION_S and right-left <= 12, "partial trial stage range")
            continue
        end = number(trial["t_new_s"], "trial end")
        h = number(trial["h_s"], "trial h")
        require(0 <= start < end <= DURATION_S and end-start == h, "trial step interval")
        require(right-left == 12, "pinned twelve-stage trial range")
        error = number(trial["error_norm"], "error norm")
        require(error >= 0 and type(trial["accepted"]) is bool, "error norm/decision")
        accepted = error < 1.0
        require(trial["accepted"] == accepted and trial["decision"] == ("accepted" if accepted else "rejected"), "trial acceptance decision")
        same(trial["nfev"], right-starts[name], "trial nfev")
        endpoint = rhs[right-1]
        same(endpoint["elapsed_s"], end, "trial endpoint RHS epoch")
        y = vector(endpoint["correction"], 6, "trial endpoint correction")
        cfg = base.settings(name)
        scale = [cfg["atol"][j] + max(abs(old_y[j]), abs(y[j])) * cfg["rtol"] for j in range(6)]
        same(trial["scale"], scale, "independent trial scale")
        require(all(v > 0 for v in scale), "positive scale")
        prior[name] = (end, y, right) if accepted else (old_t, old_y, right)
        event("trials", "complete")
    for profile in report["profiles"]:
        raw = profile.get("raw_returned")
        if raw is not None and raw["success"]:
            name = profile["name"]
            same(profile["solver_state"]["nfev"], prior[name][2]-starts[name],
                 "solver final step nfev and trial trace")
    if full:
        require(all(prior[name][0] == DURATION_S for name in PROFILES), "accepted final trial endpoint")
    return membership


def _state(row: Row) -> list[float]:
    motion = row["motion"]
    return motion["position_m"] + motion["velocity_m_s"]


def replay_comparisons(report: Row, bundle: Row, natives: dict[str, list[Row]],
                       cache: dict[int, Row], reference: ModuleType, check: Check) -> list[Row]:
    """Bind saved comparisons to same-profile archive operands and exact coepochs."""
    full = report["status"] == "passed"
    saved = report["comparisons"]
    require(type(saved) is list and len(saved) <= 67, "comparison cap")
    dop = {p["name"]: [_state(cache[id(row)]) for row in p["outputs"] if "derivative" in row]
           for p in report["profiles"]}
    native = {name: [row["state"] for row in rows] for name, rows in natives.items()}
    expected: list[tuple[str, int, list[float], list[float], float, float]] = []

    def prefix(engine: str, profiles: dict[str, list[list[float]]],
               name: str, p: float, v: float) -> None:
        if not profiles.get(name):
            return
        archived = bundle["b_prefix"][engine][name]
        require(len(archived) == 7, "archive comparison grid")
        for j, (a, b) in enumerate(zip(archived, profiles[name][:7])):
            expected.append((f"prefix_{engine}_{name}", j, a, b, p, v))

    n_step = .01, 1e-5
    d_step = .001, 1e-6
    prefix("native", native, "normal", *n_step)
    prefix("native", native, "tighter", *n_step)
    for j, (a, b) in enumerate(zip(native.get("normal", ()), native.get("tighter", ()))):
        expected.append(("native_step", j, a, b, *n_step))
    prefix("dop853", dop, "normal", *d_step)
    prefix("dop853", dop, "tighter", *d_step)
    for j, (a, b, c) in enumerate(zip(native.get("tighter", ()), dop.get("normal", ()), dop.get("tighter", ()))):
        expected.append(("native_tighter", j, a, c, *n_step))
        expected.append(("oracle_step", j, b, c, *d_step))

    if report["profiles"]:
        require(len(saved) >= 27 and len(expected) >= 27, "native prefix and step gates before DOP853")
    if len(report["profiles"]) == 2:
        require(len(saved) >= 34 and expected[33][0] == "prefix_dop853_normal",
                "normal DOP853 prefix gates before tighter")
    require(len(saved) <= len(expected), "comparison without required operands")
    require(not full or len(saved) == len(expected) == 67, "all 67 comparisons required")

    summary: Row = {}
    for j, (row, (name, index, left, right, p, v)) in enumerate(zip(saved, expected)):
        check()
        require(set(row) == {"name", "index", "epoch_tdb_s", "assessment", "difference"}, "comparison shape")
        epoch_tdb_s = bundle["initial"]["epoch_tdb_s"] + OFFSETS[index]
        same([row["name"], row["index"], row["epoch_tdb_s"]], [name, index, epoch_tdb_s],
             "fixed comparison selection")
        assessment = reference.compare_states(left, right, p, v)
        same(row["assessment"], assessment, "independent trajectory comparison")
        difference = previous._difference(right, left, row["difference"])
        may_fail = not full and j == len(saved)-1
        require(assessment["passed"] or may_fail, "trajectory gate fail-stop")
        values = summary.setdefault(name, {"prefix": None, "extension": None, "endpoint": None})
        segment = "prefix" if index <= 6 else "extension"
        maxima = values[segment] or {"position_norm_m": 0., "velocity_norm_m_s": 0.}
        values[segment] = {key: max(value, difference[key]) for key, value in maxima.items()}
        if index == (6 if name.startswith("prefix_") else 12):
            values["endpoint"] = difference

    same(report["comparison_summary"], summary, "independent comparison summary")
    return saved


def replay_observations(report: Row, bundle: Row, reference: ModuleType, cache: dict[int, Row],
                        groups: dict[str, list[Row]], trial_membership: dict[int, int],
                        check: Check, event: Event) -> int:
    """Select actual completed callbacks by ordinal, independently of stored selection."""
    full = report["status"] == "passed"
    selected: list[tuple[str, str, int, Row]] = []
    profiles = report["profiles"]
    for j, profile in enumerate(profiles):
        name = profile["name"]
        rows = groups[name]
        outputs = [row for row in profile["outputs"] if "derivative" in row]
        complete = full or j != len(profiles)-1
        if complete:
            require(len(outputs) == 13 and len(rows) >= 7
                    and all(row["completed"] for row in rows[:7])
                    and any(row["lo_s"] != 0 for row in rows[:7]), "complete initial samples")
        if not outputs:
            continue
        # An incomplete final solve can legitimately have no force samples.
        extra = []
        for lo, hi in EXTENSION_INTERVALS:
            hit = next((row for row in rows if row.get("completed") and lo < row["elapsed_s"] <= hi), None)
            if hit is None:
                break
            extra.append(hit)
        if len(extra) != 6 or len(outputs) != 13 or len(rows) < 7:
            require(not complete, "extension RHS observation unavailable")
            continue
        selected.extend((name, "output", row["index"], row) for row in outputs)
        selected.extend((name, "rhs", row["index"], row) for row in (*rows[:7], *extra))
    observations = report["observations"]
    require(type(observations) is list and len(observations) <= min(52, len(selected)), "observation cap")
    if full:
        require(len(observations) == 52, "52 complete observations")
    if len(profiles) == 2:
        require(len(observations) >= 26, "normal force gates before tighter")
    completed = 0
    for ordinal, (saved, (name, kind, i, row)) in enumerate(zip(observations, selected)):
        check()
        trial = trial_membership.get(row["global_index"]) if kind == "rhs" else None
        same([saved["profile"], saved["kind"], saved["index"], saved["trial_index"]],
             [name, kind, i, trial], "fixed observation epoch/ordinal/trial")
        _, hi, _, exact = epoch(row, bundle["initial"])
        same(saved["hi_tdb_s"], hi, "sample hi")
        same(saved["exact_tdb_s"], str(exact), "sample exact epoch")
        if ordinal < 26 and len(profiles) == 2:
            require(name == "normal" and "assessment" in saved, "normal sample required before tighter")
        built = cache[id(row)]
        progress: Row = {}
        may_fail = (not full and ordinal == len(observations)-1
                    and not (ordinal < 26 and len(profiles) == 2))
        try:
            assessment = reference.assess_observation(
                bundle["initial"], built["motion"], split.source_rows(row, bundle), built["geometry"],
                bundle["gm_m3_s2"], bundle["radii_m"], event, check=check, progress=progress)
        except FAILURES:
            check()
            require(may_fail and "assessment" not in saved, "unexpected reference failure")
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


def check_saved(report: Row, bundle: Row, references: ModuleType, native: ModuleType,
                check: Check = idle, event: Event = noop_event) -> Row:
    """Rebuild the longer B evidence; a partial prefix cannot qualify."""
    require(report["contract"] == CONTRACT and report["model"] == "B"
            and report["adapter_mode"] in ("reference", "injected-test"), "B study mode/contract")
    require(report["status"] in ("passed", "failed", "partial"), "study status")
    full = report["status"] == "passed"
    for key, value in (("origin", "SSB"), ("orientation", "J2000"), ("time_scale", "TDB"),
                       ("duration_s", DURATION_S), ("budget_s", 60.), ("aberration_correction", "NONE"),
                       ("position_units", "m"), ("velocity_units", "m/s"),
                       ("acceleration_units", "m/s^2"), ("model_a_propagations", 0),
                       ("gm_acquisitions", 0), ("optimizer_calls", 0), ("mission_accuracy_verified", False),
                       ("continuous_safety_verified", False), ("scientific_verified", False)):
        same(report[key], value, "scientific boundary: " + key)
    require("effects" not in report, "no A/B effects in a B-only study")
    require(type(report["unavailable"]) is list, "unavailable study checks")
    if full:
        require(not report["unavailable"] and "error" not in report and report["finalization_gate"] == "passed",
                "successful study finalization/inventory")
        same(report["identities"]["before"], report["identities"]["after"], "before/after identity")
    else:
        require(type(report.get("error")) is dict, "partial earliest error")
    check_ledger(report, check)
    result: Row = {"passed": full, "complete_native_profiles": 0, "complete_profiles": 0,
                   "native_telemetry": 0, "observations": 0, "comparisons": 0,
                   "prefix_comparisons": 0, "comparison_summary": {},
                   "continuous_safety_verified": False}
    if "inputs" not in report:
        require(not full and not any(report[key] for key in (
            "state_requests", "node_table", "rhs", "profiles", "comparisons", "trials",
            "observations", "native_profiles", "identities", "comparison_summary")),
            "work without frozen inputs")
        return result
    same(report["inputs"], bundle, "frozen input identity")
    previous._check_metadata(report, bundle, full)
    error = report.get("error", {})
    native_kwargs: Row = {}
    if not full and error.get("type") == "TelemetryFailure":
        stage = error["stage"]
        require(stage in ("native-normal", "native-tighter"), "native telemetry failure stage")
        native_kwargs["expected_telemetry_failure"] = (stage.removeprefix("native-"), error["message"])
    native_rows = native.replay(report["native_profiles"], bundle, check=check, event=event,
                                complete=full, **native_kwargs)
    previous._check_native_counts(report, full)
    check_request_sequence(report, bundle, check)
    groups, cache = replay_profiles(report, bundle, references, check, event)
    trial_membership = check_trials(report, check, event)
    observed = replay_observations(report, bundle, references, cache, groups, trial_membership, check, event)
    compared = replay_comparisons(report, bundle, native_rows, cache, references, check)
    prefixes = sum(row["name"].startswith("prefix_") for row in compared)
    if full:
        require(len(compared) == 67 and prefixes == 28 and observed == 52, "complete longer B results")
        n_rhs = len(report["rhs"])
        counts = report["counts"]
        expected = {"rhs": n_rhs, "states": 4*(n_rhs+13), "trials": len(report["trials"]),
                    "binary64_fields": 3*(n_rhs+26), "dynamic_totals": n_rhs+26,
                    "solves": 2, "identities": 2, "native_arcs": 2, "native_guard_reads": 5412,
                    "native_reference_fields": 156, "native_telemetry": 26, **SAMPLES}
        if report["adapter_mode"] == "reference":
            expected.update(initializations=1, metadata=30)
        else:
            require(not any(name in counts for name in ("initializations", "metadata")),
                    "unexpected native metadata counters in injected study")
        for name, value in expected.items():
            row = counts[name]
            same(row, {"attempted": value, "completed": value, "returned": value if name in OPAQUE else 0},
                 "complete count: " + name)
        evaluations = sum(3 if row["exact_tdb_s"] == str(Fraction(row["hi_tdb_s"])) else 6
                          for row in report["observations"])
        same(counts["record_evaluations"], {"attempted": evaluations, "returned": 0,
                                           "completed": evaluations}, "exact sampled record count")
    result.update(complete_native_profiles=sum(len(rows) == 13 for rows in native_rows.values()),
                  complete_profiles=sum(p.get("raw_returned", {}).get("success") is True
                                        and len(p["outputs"]) == 13 and all("derivative" in row for row in p["outputs"])
                                        for p in report["profiles"]),
                  native_telemetry=report["counts"].get("native_telemetry", {}).get("completed", 0),
                  observations=observed, comparisons=len(compared), prefix_comparisons=prefixes,
                  comparison_summary=report["comparison_summary"])
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
                <= number(parent["elapsed_s"], "study parent elapsed") <= 60, "study inclusive timing")
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
    extras = {name: value for name, value in tested.items() if name.startswith(str(ARTIFACTS / "0186-long-b-"))}
    result = {}
    for when, wire in identities.items():
        check()
        same(wire["dirty"], [], "clean saved study checkout")
        for key in COMMON_IDENTITY:
            same(wire[key], bundle["historical_identity"][key], "original scientific identity " + key)
            same(wire[key], bundle["b_runtime"][key], "saved B scientific identity " + key)
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
                names = (*PURE_HELPERS, "0186-long-b-audit.py")
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
            result["checks"] = check_saved(report, bundle, references, native, budget.check, budget.event)
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
