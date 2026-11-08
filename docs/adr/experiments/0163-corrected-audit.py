"""Independent ADR0162 saved-data audit; no candidate or scientific imports."""
from __future__ import annotations

# ruff: noqa: E402 -- Include the remaining imports in the process budget.
from time import monotonic
PROCESS_START = monotonic()

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
BODIES = ("Sun", "Moon", "Earth")
PROFILES = ("normal", "tighter")
OFFSETS = (0.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0)
CAPS = {"rhs": 10000, "trials": 1000, "binary64_fields": 20028,
        "body_checks": 84, "source_rows": 56, "reference_fields": 448,
        "model_totals": 28, "native_guards": 42}
HELPERS = ("0163-corrected-inputs.py", "0163-corrected-reference.py",
           "0163-corrected-integrator.py", "0163-corrected-study.py",
           "0163-corrected-audit.py")
FAILURES = (ValueError, TypeError, KeyError, IndexError, AttributeError,
            OSError, ImportError, RuntimeError, ArithmeticError)


def idle() -> None:
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def number(value: Any, field: str) -> float:
    require(type(value) in (int, float), field + ": finite nonboolean number")
    result = float(value)
    require(math.isfinite(result), field + ": finite number")
    return result


def vector(value: Any, size: int, field: str) -> list[float]:
    require(type(value) in (list, tuple) and len(value) == size, field + ": dimension")
    return [number(v, field) for v in value]


def same(actual: Any, expected: Any, field: str) -> None:
    # JSON comparison keeps booleans distinct from numeric components.
    require(json.dumps(actual, sort_keys=True, allow_nan=False)
            == json.dumps(expected, sort_keys=True, allow_nan=False), field)


def finite_tree(value: Any) -> None:
    if type(value) is float:
        require(math.isfinite(value), "nonfinite JSON")
    elif type(value) in (list, tuple):
        for child in value:
            finite_tree(child)
    elif type(value) is dict:
        require(all(type(k) is str for k in value), "JSON keys")
        for child in value.values():
            finite_tree(child)
    else:
        require(value is None or type(value) in (str, int, bool), "JSON type")


def _pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in values:
        require(name not in result, "duplicate JSON key: " + name)
        result[name] = value
    return result


def _constant(value: str) -> None:
    raise ValueError("nonfinite JSON constant: " + value)


def parse(raw: bytes) -> dict[str, Any]:
    result = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    require(type(result) is dict, "JSON report mapping")
    finite_tree(result)
    return result


class Budget:
    """Independent actual-work counters; no scientific deadline extension."""

    def __init__(self, clock: Callable[[], float], start_s: float) -> None:
        self.clock = clock
        self.start_s = number(start_s, "start_s")
        self.counts = {k: {"attempted": 0, "completed": 0} for k in CAPS}
        self.ledger: list[dict[str, str]] = []

    def elapsed(self) -> float:
        return number(self.clock(), "clock") - self.start_s

    def check(self) -> None:
        require(0 <= self.elapsed() < 10.0, "audit deadline/clock")

    def event(self, operation: str, phase: str) -> None:
        require(operation in CAPS and phase in ("attempt", "complete"), "audit event")
        count = self.counts[operation]
        if phase == "attempt":
            self.check()
            require(count["attempted"] < CAPS[operation], "audit cap: " + operation)
            count["attempted"] += 1
        else:
            require(count["completed"] < count["attempted"], "audit completion")
            count["completed"] += 1
        self.ledger.append({"operation": operation, "phase": phase})
        self.check()


def noop_event(_operation: str, _phase: str) -> None:
    pass


def settings(name: str) -> dict[str, Any]:
    require(name in PROFILES, "profile name")
    tight = name == "tighter"
    return {"rtol": 1e-13 if tight else 1e-12,
            "atol": [1e-8 if tight else 1e-7] * 3 + [1e-11 if tight else 1e-10] * 3,
            "max_step": 2.5 if tight else 5.0, "first_step": 0.5 if tight else 1.0}


def reconstruct_row(row: dict[str, Any], bundle: dict[str, Any], *,
                    check: Callable[[], None] = idle,
                    event: Callable[[str, str], None] = noop_event) -> dict[str, Any]:
    """Rebuild actual solver operands/fields, without manufactured corrections."""
    require(type(row) is dict, "row mapping")
    initial = bundle["initial"]
    r0 = vector(initial["position_m"], 3, "initial position")
    v0 = vector(initial["velocity_m_s"], 3, "initial velocity")
    s = number(row["elapsed_s"], "elapsed_s")
    require(0 <= s <= 300, "elapsed outside interval")
    exact = Fraction(number(initial["epoch_tdb_s"], "epoch")) + Fraction(s)
    hi = float(exact)
    lo = float(exact - Fraction(hi))
    require(Fraction(hi) + Fraction(lo) == exact, "split exact epoch")
    same(row["hi_tdb_s"], hi, "rounded epoch hi")
    same(row["lo_s"], lo, "signed epoch lo")
    correction = vector(row["correction"], 6, "correction")
    q, w = correction[:3], correction[3:]
    drift = [v * s for v in v0]
    motion = {"elapsed_s": s, "q_m": q, "w_m_s": w, "drift_m": drift,
              "position_m": [math.fsum((r0[j], drift[j], q[j])) for j in range(3)],
              "velocity_m_s": [math.fsum((v0[j], w[j])) for j in range(3)]}
    for key, value in motion.items():
        same(row["motion"][key], value, "motion " + key)
    require(tuple(row["bodies"]) == BODIES, "source body order")
    require(tuple(row["geometry"]) == BODIES, "geometry body order")
    geometry: dict[str, Any] = {}
    # Guard all three sources before evaluating even the first field.
    for body in BODIES:
        check()
        source = row["bodies"][body]
        require(source["body"] == body, "source body identity")
        same(source["epoch_tdb_s"], hi, "source query epoch")
        for key, value in (("origin", "SSB"), ("orientation", "J2000"),
                           ("aberration_correction", "NONE")):
            if key in source:
                require(source[key] == value, "source " + key)
        raw = vector(source["state_km_km_s"], 6, "raw source")
        state = [v * 1000 for v in raw]
        same(source["state_si"], state, "source SI conversion")
        c = [v * lo for v in state[3:]]
        d = [math.fsum((state[j], -r0[j], -drift[j], -q[j], c[j])) for j in range(3)]
        radius = number(bundle["radii_m"][body], "radius")
        require(radius > 0, "positive guard radius")
        require(sum((Fraction(v) ** 2 for v in d), Fraction()) > Fraction(radius) ** 2,
                "runtime exterior guard: " + body)
        geometry[body] = {"rephasing_m": c, "separation_m": d, "distance_m": math.hypot(*d)}
        for key, value in geometry[body].items():
            same(row["geometry"][body][key], value, body + " " + key)
    for body in BODIES[:2]:
        event("binary64_fields", "attempt")
        d = geometry[body]["separation_m"]
        rho = math.hypot(*d)
        mu = number(bundle["gm_m3_s2"][body], "GM")
        require(mu > 0 and math.isfinite(rho * rho), "positive finite field operands")
        force = [mu * (d[j] / rho) / (rho * rho) for j in range(3)]
        vector(force, 3, "field")
        geometry[body]["acceleration_m_s2"] = force
        same(row["geometry"][body]["acceleration_m_s2"], force, body + " field")
        event("binary64_fields", "complete")
    require("acceleration_m_s2" not in row["geometry"]["Earth"], "Earth force omitted")
    acceleration = [math.fsum(geometry[b]["acceleration_m_s2"][j] for b in BODIES[:2])
                    for j in range(3)]
    derivative = w + acceleration
    same(row["derivative"], derivative, "RHS derivative")
    return {"motion": motion, "geometry": geometry, "derivative": derivative}


def node_bodies(node: dict[str, Any]) -> dict[str, Any]:
    bodies = node["bodies"]
    if type(bodies) is list:
        require(len(bodies) == 3, "node body count")
        bodies = {body["body"]: body for body in bodies}
    require(type(bodies) is dict and tuple(bodies) == BODIES, "node body order")
    return bodies


def source_rows(row: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for body in BODIES:
        raw = deepcopy(bundle["source_rows_template"][body])
        raw.pop("assessment", None)
        state = row["bodies"][body]
        raw.update(body=body, elapsed_s=row["elapsed_s"], hi_tdb_s=row["hi_tdb_s"],
                   lo_s=row["lo_s"], state_km_km_s=state["state_km_km_s"],
                   state_si=state["state_si"])
        result[body] = raw
    return result



def validate_partial_sources(row: dict[str, Any], bundle: dict[str, Any]) -> None:
    """Validate returned source prefixes without interpreting invalid returns as data."""
    if "elapsed_s" not in row:
        require(not row.get("bodies"), "sources without epoch")
        return
    s = number(row["elapsed_s"], "partial elapsed")
    require(0 <= s <= 300, "partial epoch interval")
    exact = Fraction(bundle["initial"]["epoch_tdb_s"]) + Fraction(s)
    hi = float(exact)
    lo = float(exact-Fraction(hi))
    same(row["hi_tdb_s"], hi, "partial rounded epoch")
    same(row["lo_s"], lo, "partial signed epoch")
    bodies = row.get("bodies", {})
    require(type(bodies) is dict and tuple(bodies) == BODIES[:len(bodies)], "partial body prefix")
    for body, source in bodies.items():
        require(source["body"] == body and source["epoch_tdb_s"] == hi, "partial source identity")
        raw = source["state_km_km_s"]
        if "state_si" in source:
            same(source["state_si"], [v*1000 for v in vector(raw, 6, "partial raw state")], "partial source SI")
        else:
            require(body == tuple(bodies)[-1], "only final source may lack SI")


def validate_partial_row(row: dict[str, Any], bundle: dict[str, Any],
                         check: Callable[[], None] = idle,
                         event: Callable[[str, str], None] = noop_event) -> None:
    validate_partial_sources(row, bundle)
    if "correction" not in row:
        require(not row.get("motion") and not row.get("geometry"), "geometry without correction")
        return
    y = vector(row["correction"], 6, "partial correction")
    if "motion" not in row:
        require(not row.get("geometry"), "geometry without motion")
        return
    s = number(row["elapsed_s"], "partial elapsed")
    initial = bundle["initial"]
    r0 = vector(initial["position_m"], 3, "initial position")
    v0 = vector(initial["velocity_m_s"], 3, "initial velocity")
    drift = [v*s for v in v0]
    expected = {"elapsed_s": s, "q_m": y[:3], "w_m_s": y[3:], "drift_m": drift,
                "position_m": [math.fsum((r0[j], drift[j], y[j])) for j in range(3)],
                "velocity_m_s": [math.fsum((v0[j], y[j+3])) for j in range(3)]}
    same(row["motion"], expected, "partial motion assembly")
    geometry = row.get("geometry", {})
    require(tuple(geometry) == BODIES[:len(geometry)], "partial geometry prefix")
    for body, raw in geometry.items():
        state = vector(row["bodies"][body]["state_si"], 6, "partial source SI")
        c = [v*row["lo_s"] for v in state[3:]]
        d = [math.fsum((state[j], -r0[j], -drift[j], -y[j], c[j])) for j in range(3)]
        same(raw["rephasing_m"], c, "partial source rephasing")
        same(raw["separation_m"], d, "partial relative assembly")
        same(raw["distance_m"], math.hypot(*d), "partial separation norm")
    included = [body for body in BODIES[:2] if "acceleration_m_s2" in geometry.get(body, {})]
    require(included == list(BODIES[:len(included)]), "partial field order")
    require("acceleration_m_s2" not in geometry.get("Earth", {}), "no partial Earth field")
    if included:
        require(tuple(geometry) == BODIES, "all guards precede partial fields")
        require(all(geometry[body]["distance_m"] > bundle["radii_m"][body] for body in BODIES), "partial exterior guards before fields")
    for body in included:
        check()
        event("binary64_fields", "attempt")
        raw = geometry[body]
        d = raw["separation_m"]
        rho = math.hypot(*d)
        mu = number(bundle["gm_m3_s2"][body], "partial GM")
        require(mu > 0 and math.isfinite(rho*rho) and rho*rho > 0, "partial field domain")
        force = [mu*(v/rho)/(rho*rho) for v in d]
        same(raw["acceleration_m_s2"], force, "partial binary64 force")
        event("binary64_fields", "complete")


def check_profiles(report: dict[str, Any], bundle: dict[str, Any], reference: Any,
                   check: Callable[[], None], event: Callable[[str, str], None]) -> tuple[dict[str, list[dict[str, Any]]], dict[int, dict[str, Any]]]:
    profiles = report["profiles"]
    require(type(profiles) is list and len(profiles) <= 2, "profile cap")
    full = report["status"] == "passed"
    if full:
        require(len(profiles) == 2, "two complete profiles required")
    groups = {name: [] for name in PROFILES}
    cache: dict[int, dict[str, Any]] = {}
    for index, row in enumerate(report["rhs"]):
        check()
        require(row["profile"] in PROFILES, "RHS profile")
        require(row["global_index"] == index, "global RHS index")
        require(row["index"] == len(groups[row["profile"]]), "profile RHS index")
        groups[row["profile"]].append(row)
        if "derivative" in row:
            event("rhs", "attempt")
            cache[id(row)] = reconstruct_row(row, bundle, check=check, event=event)
            event("rhs", "complete")
        else:
            require(not full and index == len(report["rhs"]) - 1, "partial final RHS only")
            validate_partial_row(row, bundle, check, event)
    seen = []
    for index, profile in enumerate(profiles):
        name = profile["name"]
        require(name == PROFILES[index], "profile execution order")
        same(profile["settings"], settings(name), "profile settings")
        seen.append(name)
        raw = profile.get("raw_returned")
        outputs = profile.get("outputs", [])
        require(len(outputs) <= 7, "output count")
        if raw is None:
            require(not full and index == len(profiles) - 1, "missing complete raw arrays")
            continue
        require(type(raw["success"]) is bool, "solver success type")
        t = vector(raw["t"], len(raw["t"]), "raw solver t")
        require(len(t) <= 7 and t == list(OFFSETS[:len(t)]), "raw output epoch grid")
        y = raw["y"]
        require(type(y) is list and len(y) == 6, "raw y shape")
        y = [vector(values, len(t), "raw y row") for values in y]
        require(type(raw["nfev"]) is int and raw["nfev"] >= 0, "nfev")
        completed = [row for row in groups[name] if "derivative" in row]
        same(raw["nfev"], len(completed), "solver nfev versus completed RHS")
        if raw["success"]:
            require(t == list(OFFSETS), "complete solver returned times")
            require(len(outputs) == 7 or not full, "complete solver exported outputs")
            require(all(values[0] == 0 for values in y), "zero initial correction")
        else:
            require(not full and index == len(profiles) - 1, "failed solver fail-stop")
        for j, output in enumerate(outputs):
            check()
            if "derivative" not in output:
                require(not full and j == len(outputs)-1, "partial last output only")
                if "correction" in output:
                    same(output["correction"], [y[k][j] for k in range(6)], "partial raw/output correction parity")
                validate_partial_row(output, bundle, check, event)
                continue
            same(output["elapsed_s"], t[j], "output elapsed")
            same(output["correction"], [y[k][j] for k in range(6)], "raw/output q-w parity")
            same(output["bodies"], node_bodies(report["node_table"][j]), "shared node table")
            cache[id(output)] = reconstruct_row(output, bundle, check=check, event=event)
            if "motion_assessment" in output:
                motion_assessment = reference.assess_motion(bundle["initial"], output["motion"])
                same(output["motion_assessment"], motion_assessment, "output assembly assessment")
                require(motion_assessment["passed"], "output assembly gate")
        if full:
            require(raw["success"] and raw["status"] == 0, "successful solver status")
            require(len(completed) >= 7, "seven RHS observations available")
            require(any(row["lo_s"] != 0 for row in completed[:7]), "nonzero-lo sample required")
    require(all(not groups[name] for name in PROFILES if name not in seen), "orphan RHS profile")
    return groups, cache


def expected_comparisons(report: dict[str, Any], bundle: dict[str, Any], reference: Any) -> list[dict[str, Any]]:
    profiles = {p["name"]: p for p in report["profiles"]}
    result = []
    for name, left, right, rp, rv in (
        ("native_step", bundle["native_samples"]["normal"], bundle["native_samples"]["tighter"], 0.01, 1e-5),
        ("native_tighter", bundle["native_samples"]["tighter"],
         [r["motion"]["position_m"] + r["motion"]["velocity_m_s"]
          for r in profiles.get("tighter", {}).get("outputs", [])], 0.01, 1e-5),
        ("oracle_step", [r["motion"]["position_m"] + r["motion"]["velocity_m_s"]
          for r in profiles.get("normal", {}).get("outputs", [])],
         [r["motion"]["position_m"] + r["motion"]["velocity_m_s"]
          for r in profiles.get("tighter", {}).get("outputs", [])], 0.001, 1e-6),
    ):
        for index, (a, b) in enumerate(zip(left, right)):
            assessment = reference.compare_states(a, b, rp, rv)
            result.append({"name": name, "index": index, "assessment": assessment})
    if len(result) > 7:
        result = result[:7] + [item for index in range(7) for item in result[7:] if item["index"] == index]
    return result


def validate_counts(report: dict[str, Any]) -> None:
    counts = report["counts"]
    require(type(counts) is dict, "counts mapping")
    for name, counter in counts.items():
        require(type(counter) is dict, "counter mapping")
        for phase, value in counter.items():
            require(phase in ("attempted", "returned", "completed")
                    and type(value) is int and value >= 0, "finite integer counter")
        require(counter.get("completed", 0) <= counter["attempted"], "counter completion order")
        if "returned" in counter:
            if name in ("states", "solves", "identities", "metadata", "initializations"):
                require(counter.get("completed", 0) <= counter["returned"] <= counter["attempted"], "counter return order")
            else:
                require(counter["returned"] == 0, "nonopaque return count")
    for name, cap in {"rhs": 10000, "trials": 1000, "states": 30021,
                      "binary64_fields": 20028, "dynamic_totals": 10014,
                      "body_checks": 84, "source_rows": 56, "reference_fields": 448,
                      "model_totals": 28, "native_guards": 42, "solves": 2, "initializations": 1, "identities": 2, "metadata": 30}.items():
        if name in counts:
            require(counts[name]["attempted"] <= cap, "saved count cap: " + name)
    if "rhs" in counts and "states" in counts:
        require(counts["states"]["attempted"] <= 3 * counts["rhs"]["attempted"] + 21, "saved source count relation")



def check_ledger(report: dict[str, Any]) -> None:
    """Reconcile every saved counter with its ordered operation ledger."""
    counts = report["counts"]
    rebuilt = {name: {"attempted": 0, "returned": 0, "completed": 0} for name in counts}
    phases = {"attempt": "attempted", "return": "returned", "complete": "completed"}
    for row in report["ledger"]:
        require(type(row) is dict and row["operation"] in rebuilt and row["phase"] in phases, "saved ledger event")
        name, phase = row["operation"], row["phase"]
        c = rebuilt[name]
        c[phases[phase]] += 1
        require(c["completed"] <= c["attempted"] and c["returned"] <= c["attempted"], "saved ledger operation order")
        if name in ("states", "solves", "identities", "metadata", "initializations"):
            require(c["completed"] <= c["returned"], "saved ledger opaque completion")
    same(counts, rebuilt, "saved ledger counters")


def check_completed_counts(report: dict[str, Any], full: bool) -> None:
    if not full:
        return
    counts = report["counts"]
    n = len(report["rhs"])
    fixed = {"rhs": n, "states": 3*n+21, "trials": len(report["trials"]),
             "binary64_fields": 2*(n+14), "dynamic_totals": n+14,
             "body_checks": 84, "source_rows": 56, "reference_fields": 448,
             "model_totals": 28, "native_guards": 42, "solves": 2,
             "initializations": 1, "identities": 2, "metadata": 30}
    for name, value in fixed.items():
        if name in ("initializations", "metadata") and report.get("adapter_mode") != "reference":
            continue
        require(counts[name]["attempted"] == counts[name]["completed"] == value, "complete count: " + name)


def check_trials(report: dict[str, Any], check: Callable[[], None],
                 event: Callable[[str, str], None]) -> None:
    require(len(report["trials"]) <= 1000, "trial cap")
    rhs = report["rhs"]
    full = report["status"] == "passed"
    prior = {name: (0.0, [0.0]*6, -1) for name in PROFILES}
    for i, trial in enumerate(report["trials"]):
        check()
        event("trials", "attempt")
        require(trial["index"] == i and trial["profile"] in PROFILES, "trial ordinal/profile")
        name = trial["profile"]
        left, right = trial["rhs_start"], trial["rhs_end"]
        require(type(left) is int and type(right) is int and 0 <= left <= right <= len(rhs), "trial RHS range")
        require(all(row["profile"] == name for row in rhs[left:right]), "trial source profile")
        start = number(trial["t_before_s"], "trial start")
        old_t, old_y, last_end = prior[name]
        require(start == old_t and left >= last_end, "trial controller continuity")
        if trial["accepted"] is None:
            require(not full and i == len(report["trials"])-1 and trial["decision"] == "unavailable", "unavailable final trial")
            require(0 <= start < 300 and right-left <= 12, "partial trial stage range")
            continue
        end = number(trial["t_new_s"], "trial end")
        h = number(trial["h_s"], "trial h")
        require(0 <= start < end <= 300 and end-start == h, "trial step interval")
        require(right-left == 12, "pinned twelve-stage trial range")
        error = number(trial["error_norm"], "error norm")
        require(error >= 0 and type(trial["accepted"]) is bool, "error norm/decision")
        accepted = error < 1.0
        require(trial["accepted"] == accepted and trial["decision"] == ("accepted" if accepted else "rejected"), "trial acceptance decision")
        endpoint = rhs[right-1]
        same(endpoint["elapsed_s"], end, "trial endpoint RHS epoch")
        y = vector(endpoint["correction"], 6, "trial endpoint correction")
        cfg = settings(name)
        scale = [cfg["atol"][j] + max(abs(old_y[j]), abs(y[j])) * cfg["rtol"] for j in range(6)]
        same(trial["scale"], scale, "independent trial scale")
        require(all(v > 0 for v in scale), "positive scale")
        prior[name] = (end, y, right) if accepted else (old_t, old_y, right)
        event("trials", "complete")
    if full:
        require(all(prior[name][0] == 300 for name in PROFILES), "accepted final trial endpoint")


def check_native_guards(report: dict[str, Any], bundle: dict[str, Any],
                        check: Callable[[], None], event: Callable[[str, str], None]) -> None:
    rows = report["native_guards"]
    require(len(rows) <= 42, "native guard cap")
    expected = [(name, i, body) for i in range(7) for name in PROFILES for body in BODIES]
    for row, (name, index, body) in zip(rows, expected, strict=False):
        check()
        event("native_guards", "attempt")
        same([row["profile"], row["index"], row["body"]], [name, index, body], "native guard selection")
        point = vector(bundle["native_samples"][name][index], 6, "native state")[:3]
        source = node_bodies(report["node_table"][index])[body]["state_si"][:3]
        distance = math.dist(point, source)
        same(row["distance_m"], distance, "native guard distance")
        passed = distance > bundle["radii_m"][body]
        require(row["passed"] is passed, "native guard classification")
        if not passed:
            require(report["status"] != "passed" and row is rows[-1] and not report["profiles"], "failed native guard stops downstream work")
        event("native_guards", "complete")
    if report["status"] == "passed":
        require(len(rows) == 42, "complete native guards")



def partial_value(actual: Any, expected: Any, label: str) -> None:
    if type(actual) is dict:
        require(type(expected) is dict and set(actual) <= set(expected), label)
        for key in actual:
            partial_value(actual[key], expected[key], label + "." + key)
    elif type(actual) is list:
        require(type(expected) is list and len(actual) <= len(expected), label)
        for a, b in zip(actual, expected):
            partial_value(a, b, label)
    else:
        same(actual, expected, label)


def check_saved(report: dict[str, Any], bundle: dict[str, Any], reference: Any,
                check: Callable[[], None] = idle,
                event: Callable[[str, str], None] = noop_event) -> dict[str, Any]:
    """Recompute available evidence; incomplete input can never qualify science."""
    finite_tree(report)
    require(report["contract"] == "ADR0162", "contract")
    require(report["status"] in ("passed", "failed", "partial"), "study status")
    require(report["origin"] == "SSB" and report["orientation"] == "J2000"
            and report["time_scale"] == "TDB", "state conventions")
    require(report["budget_s"] == 60.0, "study budget")
    for key, value in (("aberration_correction", "NONE"), ("position_units", "m"),
                       ("velocity_units", "m/s"), ("acceleration_units", "m/s^2")):
        require(report[key] == value, "public " + key)
    for key in ("native_propagations", "gm_acquisitions", "optimizer_calls"):
        require(type(report[key]) is int and report[key] == 0, "forbidden operation: " + key)
    for key in ("historical_final_identity_complete", "mission_accuracy_verified", "continuous_safety_verified", "scientific_verified"):
        require(report[key] is False, "unqualified claim: " + key)
    same(report["inputs"], bundle, "frozen input identity")
    validate_counts(report)
    full = report["status"] == "passed"
    if not full:
        require(type(report.get("error")) is dict, "partial earliest error")
    table = report["node_table"]
    require(type(table) is list and len(table) <= 7, "node table cap")
    for i, node in enumerate(table):
        same(node["elapsed_s"], OFFSETS[i], "node epoch")
        validate_partial_sources(node, bundle)
        if full or i < len(table)-1:
            node_bodies(node)
        else:
            validate_partial_sources(node, bundle)
    if full:
        require(len(table) == 7, "complete node table")
        same(report["identities"]["before"], report["identities"]["after"], "before/after identity")
        require(report["finalization_gate"] == "passed", "study finalization")
        if report.get("adapter_mode") == "reference":
            identity = report["identities"]["before"]
            same(identity["kernels"], bundle["kernel_manifest"], "frozen ordered kernels")
            for key in ("versions", "imports", "native_binary", "conda_build", "resource_build",
                        "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime"):
                same(identity[key], bundle["historical_identity"][key], "frozen runtime " + key)
            require(bundle["kernel_manifest"]["loaded_kernel_count"] == 13, "kernel count")
    groups, cache = check_profiles(report, bundle, reference, check, event)
    check_trials(report, check, event)
    check_native_guards(report, bundle, check, event)
    check_ledger(report)
    comparisons = expected_comparisons(report, bundle, reference)
    if full:
        same(report["comparisons"], comparisons, "independent trajectory comparisons")
    else:
        require(len(report["comparisons"]) <= len(comparisons), "partial comparison prefix")
        same(report["comparisons"], comparisons[:len(report["comparisons"])], "partial trajectory comparisons")
    if full:
        require(len(comparisons) == 21 and all(c["assessment"]["passed"] for c in comparisons), "trajectory gates")
    expected_selection = []
    for profile in report["profiles"]:
        name = profile["name"]
        expected_selection += [(name, "output", i, row) for i, row in enumerate(profile.get("outputs", []))]
        expected_selection += [(name, "rhs", i, row) for i, row in enumerate([r for r in groups[name] if "derivative" in r][:7])]
    observations = report["observations"]
    require(len(observations) <= len(expected_selection), "observation cap")
    for ordinal, (saved, (name, kind, index, row)) in enumerate(zip(observations, expected_selection, strict=False)):
        check()
        same([saved["profile"], saved["kind"], saved["index"]], [name, kind, index], "fixed observation selection")
        rebuilt = cache[id(row)]
        progress: dict[str, Any] = {}
        try:
            assessment = reference.assess_observation(bundle["initial"], rebuilt["motion"], source_rows(row, bundle),
                                                     rebuilt["geometry"], bundle["gm_m3_s2"], bundle["radii_m"], event, check=check, progress=progress)
        except FAILURES:
            require(not full and ordinal == len(observations)-1 and "assessment" not in saved, "unexpected reference failure")
            partial_value(saved.get("progress", {}), progress, "partial sampled reference")
            continue
        if "assessment" in saved:
            same(saved["assessment"], assessment, "independent sampled force assessment")
            require(assessment["passed"] or (not full and ordinal == len(observations)-1
                    and report["error"]["stage"] == "selected-force-reference"), "required sampled force gate")
        else:
            require(not full and ordinal == len(observations)-1, "missing completed reference")
            partial_value(saved.get("progress", {}), progress, "partial sampled reference")
        if "progress" in saved and "assessment" in saved:
            same(saved["progress"], progress, "saved reference progress")
    if full:
        require(len(observations) == 28, "complete observations")
    check_completed_counts(report, full)
    return {"passed": full, "complete_profiles": len(report["profiles"]),
            "observations": len(observations), "comparisons": len(comparisons),
            "historical_final_identity_repaired": False,
            "continuous_safety_verified": False}


def load_helper(root: Path, name: str, expected: str, check: Callable[[], None]) -> ModuleType:
    path = root / "docs/adr/experiments" / name
    check()
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == expected, "audit helper SHA256: " + name)
    spec = importlib.util.spec_from_file_location("corrected_audit_" + name.replace("-", "_"), path)
    require(spec is not None and spec.loader is not None, "audit loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    check()
    return module


def helper_hashes(root: Path, check: Callable[[], None] = idle) -> dict[str, str]:
    result = {}
    for name in HELPERS:
        check()
        result[name] = sha256((root / "docs/adr/experiments" / name).read_bytes()).hexdigest()
    return result


def fresh() -> None:
    require(not any(name.split(".")[0] in ("numpy", "scipy", "spiceypy", "tudatpy") for name in sys.modules), "audit scientific imports")


def _elapsed(budget: Budget) -> float | None:
    try:
        return number(budget.elapsed(), "elapsed")
    except FAILURES:
        return None


def save(result: dict[str, Any], stream: TextIO, budget: Budget) -> dict[str, Any]:
    result["elapsed_before_flush_s"] = _elapsed(budget)
    result["finalization_gate"] = "passed"
    try:
        budget.check()
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.flush()
        budget.check()
    except FAILURES as error:
        if "error" in result:
            result.setdefault("first_error", result["error"])
        result.update(audit_status="rejected", scientific_verified=False,
                      finalization_gate="failed", error={"stage": "finalization",
                      "type": type(error).__name__, "message": str(error)})
        stream.seek(0)
        stream.truncate()
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.flush()
    return result


def audit(path: Path, output: Path, *, root: Path = ROOT,
          clock: Callable[[], float] = monotonic, started_s: float | None = None,
          inputs_loader: Any = None, references: Any = None) -> dict[str, Any]:
    """Audit exclusive saved evidence; injected tests never qualify real science."""
    start = (PROCESS_START if clock is monotonic else clock()) if started_s is None else started_s
    budget = Budget(clock, start)
    injected = inputs_loader is not None or references is not None or clock is not monotonic
    if not injected:
        require(started_s is not None and started_s <= PROCESS_START, "external pre-child baseline required")
    result: dict[str, Any] = {"contract": "ADR0162", "audit_status": "rejected", "scientific_verified": False,
                              "adapter_mode": "injected-test" if injected else "reference", "budget_s": 10.0,
                              "counts": budget.counts, "ledger": budget.ledger, "native_calls": 0,
                              "scientific_imports": 0, "kernel_loads": 0, "spacecraft_propagations": 0}
    receipt = output.with_suffix(".receipt.json")
    require(not output.exists() and not receipt.exists(), "exclusive audit evidence exists")
    with output.open("x", encoding="utf-8") as stream, receipt.open("x", encoding="utf-8") as receipt_stream:
        stage = "inputs"
        try:
            budget.check()
            if not injected:
                require(start <= PROCESS_START, "audit process-start baseline reset")
                fresh()
            raw = path.read_bytes()
            report = parse(raw)
            result["evidence_sha256"] = sha256(raw).hexdigest()
            hashes = helper_hashes(root, budget.check) if not injected else {}
            if inputs_loader is None:
                inputs_loader = load_helper(root, HELPERS[0], hashes[HELPERS[0]], budget.check).load_inputs
            if references is None:
                references = load_helper(root, HELPERS[1], hashes[HELPERS[1]], budget.check)
            bundle = inputs_loader(root, budget.check)
            if not injected:
                same(report["helper_sha256"], hashes, "saved helper identities")
                study_receipt = parse(path.with_suffix(".receipt.json").read_bytes())
                require(study_receipt["finalization_gate"] == report["finalization_gate"], "study receipt finalization")
                require(study_receipt["status"] == report["status"], "study receipt status")
                if report["status"] == "passed":
                    require(0 <= number(report["elapsed_before_flush_s"], "study elapsed")
                            <= number(study_receipt["elapsed_s"], "study receipt elapsed") < 60,
                            "study inclusive finalization time")
                manifest_path = root / "docs/adr/experiments/0163-verification.json"
                manifest_raw = manifest_path.read_bytes()
                require(sha256(manifest_raw).hexdigest() == report["preparation_manifest_sha256"], "preparation manifest identity")
                manifest = parse(manifest_raw)
                require(manifest["preparation_complete"] is True, "verified preparation")
                for name, digest in hashes.items():
                    same(manifest["tested_source_sha256"]["docs/adr/experiments/"+name], digest, "tested helper bytes")
                snapshot_check = load_helper(root, "0145-short-coast-evidence.py",
                    bundle["protected_sha256"]["docs/adr/experiments/0145-short-coast-evidence.py"], budget.check)
                if report.get("identities", {}).get("before") is not None:
                    snapshot = deepcopy(report["identities"]["before"])
                    for name in HELPERS:
                        snapshot["source_sha256"].pop("docs/adr/experiments/"+name)
                    result["snapshot_checks"] = snapshot_check.verify_snapshot(snapshot, bundle["kernel_manifest"], budget.check, checkout=root)
            stage = "saved-data"
            result["checks"] = check_saved(report, bundle, references, budget.check, budget.event)
            if not injected:
                stage = "identity"
                same(helper_hashes(root, budget.check), hashes, "audit final helper identity")
                same(inputs_loader(root, budget.check), bundle, "audit final input identity")
                fresh()
            result["audit_status"] = "passed" if result["checks"]["passed"] else "partial"
            result["scientific_verified"] = not injected and report.get("adapter_mode") == "reference" and result["audit_status"] == "passed"
        except FAILURES as error:
            result["error"] = {"stage": stage, "type": type(error).__name__, "message": str(error)}
        save(result, stream, budget)
        receipt_data = {"evidence_sha256": sha256(output.read_bytes()).hexdigest(), "finalization_gate": result["finalization_gate"], "elapsed_s": _elapsed(budget)}
        try:
            budget.check()
            json.dump(receipt_data, receipt_stream, indent=2, allow_nan=False)
            receipt_stream.flush()
            budget.check()
        except FAILURES as error:
            result.update(audit_status="rejected", scientific_verified=False, finalization_gate="failed")
            result.setdefault("first_error", result.get("error"))
            result["error"] = {"stage": "receipt-finalization", "type": type(error).__name__, "message": str(error)}
            stream.seek(0)
            stream.truncate()
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.flush()
            receipt_stream.seek(0)
            receipt_stream.truncate()
            json.dump({"finalization_gate": "failed", "evidence_sha256": sha256(output.read_bytes()).hexdigest()}, receipt_stream, allow_nan=False)
            receipt_stream.flush()
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--started-s", type=float, required=True)
    args = parser.parse_args()
    answer = audit(args.study, args.output, started_s=args.started_s)
    raise SystemExit(0 if answer["audit_status"] == "passed" and answer["finalization_gate"] == "passed" else 2)
