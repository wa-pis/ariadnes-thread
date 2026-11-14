"""Independent ordered stdlib replay of the ADR0196 saved operands."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from fractions import Fraction
from hashlib import sha256
import math
from pathlib import Path
import sys
from types import FunctionType, ModuleType, SimpleNamespace
from typing import Any

DURATION_S = 16_000.0
OFFSETS = tuple(float(x) for x in range(0, 16_001, 50))
PROFILES = ("normal", "tighter")
BODIES = ("Sun", "Moon", "Earth")
STEPS_S = (1.0, .5)
MARKER_M = 18_374_000
N = len(OFFSETS)
OBSERVATIONS = 1284
WINDOWS = 314
RHS_CAP = 160_000
TRIAL_CAP = 13_000
GUARD_READS = 144_012
SAMPLE_COUNTS = {
    "body_checks": 3*OBSERVATIONS, "moon_earth_checks": OBSERVATIONS,
    "source_rows": 3*OBSERVATIONS, "reference_fields": 24*OBSERVATIONS,
    "model_totals": OBSERVATIONS,
}
CAPS = SAMPLE_COUNTS | {
    "rhs": RHS_CAP, "trials": TRIAL_CAP, "states": 4*(RHS_CAP+N),
    "native_guard_reads": GUARD_READS, "native_arcs": 2, "solves": 2,
    "native_telemetry": 2*N, "native_reference_fields": 12*N,
    "binary64_fields": 3*(RHS_CAP+2*N), "dynamic_totals": RHS_CAP+2*N,
    "record_evaluations": 6*OBSERVATIONS,
}
type Row = dict[str, Any]
type Check = Callable[[], None]
type Event = Callable[[str, str], None]
type Emit = Callable[[str, Row], None]
type Record = tuple[str, Row]
type Vector = tuple[float, ...]


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError("far audit: " + reason)


def _load() -> ModuleType:
    path = Path(__file__).with_name("0194-extension-audit.py")
    source = path.read_bytes()
    require(sha256(source).hexdigest() ==
            "73d27292aa0a1e5443c58e07ea89a87587d61cc85069d3b047b764283596bcfd", "pinned offline replay")
    module = ModuleType("ariadna_far_saved_replay")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


LEGACY = _load()
OLD, REF, NATIVE = LEGACY.OLD, LEGACY.REF, LEGACY.NATIVE
number, vector, words = OLD.number, NATIVE.vector, NATIVE.same_words
OPAQUE = OLD.OPAQUE
START_META = {"identities": 1, "metadata": 15, "initializations": 1}


def _equal(left: Any, right: Any) -> bool:
    # Same wire semantics as historical JSON comparison without re-encoding each RHS field.
    t = type(left)
    if t in (list, tuple) and type(right) in (list, tuple):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right, strict=True))
    if t is not type(right):
        return False
    if t is dict:
        return left.keys() == right.keys() and all(_equal(left[k], v) for k, v in right.items())
    if t is float:
        return left == right and math.isfinite(left) and (left != 0.0 or
               math.copysign(1.0, left) == math.copysign(1.0, right))
    return left == right


def same(left: Any, right: Any, reason: str) -> None:
    require(_equal(left, right), reason)


def _bind(function: FunctionType, scope: Row) -> FunctionType:
    result = FunctionType(function.__code__, scope, function.__name__, function.__defaults__, function.__closure__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result


# Bind only the new horizon and equivalent wire equality in fresh namespaces.
# None of the pinned helpers or their callers sees changed historical globals.
_source_scope = OLD.split.validate_source.__globals__ | {"same": same}
_source_validator = SimpleNamespace(request=OLD.split.request,
                                    validate_source=_bind(OLD.split.validate_source, _source_scope))
_replay_scope = OLD.epoch.__globals__ | {"DURATION_S": DURATION_S, "same": same, "split": _source_validator}
for _fn in (OLD.epoch, OLD.validate_sources, OLD.reconstruct_geometry, OLD.reconstruct_row):
    _replay_scope[_fn.__name__] = _bind(_fn, _replay_scope)
reconstruct = _replay_scope["reconstruct_row"]
validate_sources = _replay_scope["validate_sources"]

_ref_scope = REF.assess_observation.__globals__.copy()


def _motion_operands(initial: Row, motion: Row) -> Row:
    """Independently assemble exact dyadic motion on the extended horizon."""
    m = REF.MOTION
    r0, v0 = m._vector(initial["position_m"], "position"), m._vector(initial["velocity_m_s"], "velocity")
    s = m._exact(motion["elapsed_s"], "elapsed")
    require(0 <= s <= DURATION_S, "motion elapsed outside interval")
    q, w = m._vector(motion["q_m"], "q"), m._vector(motion["w_m_s"], "w")
    drift = m._vector(motion["drift_m"], "drift")
    position = m._vector(motion["position_m"], "position")
    velocity = m._vector(motion["velocity_m_s"], "velocity")
    exact_drift = tuple(v*s for v in v0)
    return {
        "r0": r0, "v0": v0, "s": s, "q": q, "w": w, "drift": drift,
        "position": position, "velocity": velocity, "exact_drift": exact_drift,
        "exact_position": tuple(r+d+c for r, d, c in zip(r0, exact_drift, q, strict=True)),
        "exact_velocity": tuple(v+c for v, c in zip(v0, w, strict=True)),
    }


_ref_scope["_motion_operands"] = _motion_operands
_ref_scope["assess_motion"] = assess_motion = _bind(REF.assess_motion, _ref_scope)
assess_observation = _bind(REF.assess_observation, _ref_scope)
_direction = _bind(LEGACY._direction, LEGACY._direction.__globals__ | {"MARKER_M": MARKER_M})


@dataclass(slots=True)
class Cursor:
    records: Iterator[Record]
    check: Check
    head: Record | None = None

    def kind(self) -> str | None:
        self.check()
        if self.head is None:
            self.head = next(self.records, None)
        return None if self.head is None else self.head[0]

    def take(self, expected: str) -> Row:
        actual = self.kind()
        require(actual == expected and self.head is not None, f"expected {expected}, found {actual}")
        assert self.head is not None
        _, result = self.head
        self.head = None
        require(type(result) is dict, expected + " payload")
        return result


@dataclass(slots=True)
class RhsReplay:
    bundle: Row
    check: Check
    event: Event

    def rhs(self, row: Row) -> Row:
        """Replay one completed RHS without a substitute scientific module."""
        require(row["completed"] is True, "RHS completion")
        self.event("rhs", "attempt")
        built = reconstruct(row, self.bundle, check=self.check, event=self.event)
        # reconstruct already validates each raw return against these same descriptors.
        requests = [OLD.split.request(body, "SSB", row["hi_tdb_s"]) for body in BODIES]
        requests.append(OLD.split.request("Moon", "Earth", row["hi_tdb_s"]))
        same(row["requests"], requests, "ordered RHS source requests")
        self.event("rhs", "complete")
        return built


@dataclass(slots=True)
class Directions:
    name: str
    emit: Emit
    previous: Row | None = None
    count: int = 0
    signs: Counter[str] = field(default_factory=Counter)
    first_outward: list[float] | None = None

    def add(self, row: Row) -> None:
        """Preserve each operand and every qualifying or contrary sampled edge."""
        left = self.previous
        edge = None
        if row["range_sign"] == 0:
            self.signs["exact-equality"] += 1
        if left is not None:
            pair = (left["range_sign"], row["range_sign"])
            times = [left["epoch_tdb_s"], row["epoch_tdb_s"]]
            if pair == (-1, 1):
                self.signs["outward"] += 1
                if self.first_outward is None:
                    self.first_outward = times
                positive = min(left["radial_sign"], row["radial_sign"]) > 0
                if not positive:
                    self.signs["nonpositive-radial-endpoint"] += 1
                edge = {"kind": "outward", "positive_endpoints": positive, "bracket_tdb_s": times}
            elif pair == (1, -1):
                self.signs["inward-pair"] += 1
                edge = {"kind": "inward", "bracket_tdb_s": times}
        self.emit("direction", {"grid": self.name, "index": self.count, "edge": edge, **row})
        self.previous = row
        self.count += 1

    def summary(self) -> Row:
        reasons = [s for s in ("exact-equality", "inward-pair", "nonpositive-radial-endpoint") if self.signs[s]]
        if self.signs["outward"] != 1:
            reasons.append("no-outward-pair" if not self.signs["outward"] else "multiple-outward-pairs")
        return {"rows": self.count, "edge_counts": dict(self.signs), "reasons": reasons,
                "first_outward_tdb_s": self.first_outward}


def _guard(stream: Cursor, bundle: Row, name: str, epoch: float,
           group: int, state: Vector) -> list[Vector]:
    result = []
    for body in BODIES:
        saved = stream.take("native_guard")
        same([saved["name"], saved["group"], saved["body"], saved["epoch_tdb_s"]],
             [name, group, body, epoch], "native guard identity")
        v = vector(saved["state_si"], 6)
        radius = bundle["radii_m"][body]
        distance = math.dist(state[:3], v[:3])
        same(saved["distance_m"], distance, "native measured distance")
        require(math.isfinite(distance) and distance > radius > 0 and saved["passed"] is True,
                "native exterior guard " + body)
        result.append(v)
    return result


def _native(stream: Cursor, bundle: Row, nodes: list[Row], name: str, step: float,
            event: Event, emit: Emit) -> tuple[list[Vector], Row, Row]:
    initial = bundle["initial"]
    start, x0 = initial["epoch_tdb_s"], initial["position_m"] + initial["velocity_m_s"]
    header = stream.take("native_start")
    same([header["name"], header["step_s"], header["coast_mass_kg"]],
         [name, step, bundle["mass_kg"]], "native profile header")
    inv = header["inventory"]
    same([inv[k] for k in ("model", "origin", "orientation", "aberration", "force_order", "force_counts")],
         ["B", "SSB", "J2000", "NONE", ["total", *BODIES], dict.fromkeys(BODIES, 1)], "native inventory")
    gm = bundle["gm_m3_s2"]
    require(set(inv["gm_m3_s2"]) == set(BODIES), "native GM inventory")
    for body in BODIES:
        require(abs(number(inv["gm_m3_s2"][body], "native GM")-gm[body]) <= 1e-15*gm[body],
                "native GM " + body)

    count = int(DURATION_S/step)+1
    _guard(stream, bundle, name, start, 0, vector(x0, 6))
    ret = stream.take("native_return")
    same([ret["name"], ret["integration_completed"]], [name, True], "native returned status")
    raw: list[tuple[Vector, Vector]] = []
    for i in range(count):
        saved = stream.take("native_raw")
        same([saved["name"], saved["index"], saved["epoch_tdb_s"]],
             [name, i, start+i*step], "native raw mesh")
        state, force = vector(saved["state"], 6), vector(saved["acceleration_m_s2"], 12)
        require(i or words(state, x0, 6), "native exact initial words")
        summed = tuple(math.fsum(force[j+k] for k in (3, 6, 9)) for j in range(3))
        require(math.dist(force[:3], summed) <= 1e-12, "native total/source consistency")
        raw.append((state, force))

    mesh, common = Directions(f"mesh_{name}", emit), Directions(f"rk4_{name}", emit)
    coepochs: list[tuple[Vector, Vector, list[Vector]]] = []
    spacing = int(50/step)
    for i, (state, force) in enumerate(raw):
        epoch = start+i*step
        bodies = _guard(stream, bundle, name, epoch, i+1, state)
        direction = _direction((epoch, state, bodies[1]))
        mesh.add(direction)
        if i % spacing == 0:
            j = i//spacing
            same(nodes[j]["hi_tdb_s"], epoch, "common/native epoch")
            rebuilt = _direction((epoch, state, vector(nodes[j]["bodies"]["Moon"]["state_si"], 6)))
            require(all(rebuilt[k] == direction[k] for k in ("range_sign", "radial_sign"))
                    and abs(rebuilt["radius_m"]-direction["radius_m"]) <= 1e-6
                    and abs(rebuilt["radial_speed_m_s"]-direction["radial_speed_m_s"]) <= 1e-9,
                    "native/coepoch direction")
            common.add(rebuilt)
            coepochs.append((state, force, list(bodies)))

    states = []
    for i, (state, force, bodies) in enumerate(coepochs):
        sample = stream.take("native_sample")
        same([sample["name"], sample["index"], sample["epoch_tdb_s"]],
             [name, i, start+OFFSETS[i]], "native sample")
        require(words(sample["state"], state, 6) and words(sample["acceleration_m_s2"], force, 12),
                "native sample differs from raw mesh")
        NATIVE.telemetry(state, force, [b[:3] for b in bodies], gm, event)
        states.append(state)
    end = stream.take("native_end")
    same([end["name"], end["arc"]], [name, {"attempted": 1, "returned": 1, "completed": 1}], "native arc")
    result = end["result"]
    keys = ("origin", "orientation", "position_units", "velocity_units", "time_units",
            "force_order", "step_s", "retained_states", "guarded_states")
    same([result[k] for k in keys],
         ["SSB", "J2000", "m", "m/s", "TDB seconds since J2000", ["total", *BODIES], step, count, count],
         "native return labels/counts")
    return states, common.summary(), mesh.summary()


@dataclass(slots=True)
class Trials:
    profile: str
    start: int
    accepted_t_s: float = 0.0
    accepted_y: list[float] = field(default_factory=lambda: [0.0]*6)
    last_span_s: tuple[float, float] | None = None
    expected_dense: int = 0
    output_cursor: int = 0
    dense: int = 0
    since_trial: int = 0
    endpoint: Row | None = None

    def add(self, row: Row, ordinal: int) -> bool:
        """Validate callback role as each group is consumed; retain at most one endpoint."""
        kind = row["usage"]
        if ordinal == self.start:
            same([kind, row["elapsed_s"], row["correction"]],
                 ["initial", 0.0, [0.0]*6], "adaptive initial callback")
        elif kind == "dense":
            span = self.last_span_s
            require(self.since_trial == 0 and span is not None and self.dense < self.expected_dense
                    and span[0] <= row["elapsed_s"] <= span[1], "dense callback outside accepted step")
            self.dense += 1
        else:
            require(kind == "trial" and self.dense == self.expected_dense and self.since_trial < 12,
                    "trial/dense callback order or size")
            self.since_trial += 1
            self.endpoint = row
        return kind == "trial"

    def close(self, row: Row, index: int, right: int, config: Row) -> None:
        require(self.since_trial == 12 and self.endpoint is not None, "trial missing its twelve RHS")
        left = right-12
        same([row["profile"], row["index"], row["rhs_start"], row["rhs_end"],
              row["nfev"], row["t_before_s"]],
             [self.profile, index, left, right, right-self.start, self.accepted_t_s],
             "trial closure/continuity")
        end = number(row["t_new_s"], "trial end")
        h = number(row["h_s"], "trial step")
        require(0 <= self.accepted_t_s < end <= DURATION_S and end-self.accepted_t_s == h
                and h <= config["max_step"] + math.ulp(end), "trial step interval")
        if left == self.start+1:
            same(h, config["first_step"], "frozen initial trial step")
        error = number(row["error_norm"], "trial error")
        accepted = error < 1.0
        require(error >= 0.0 and row["accepted"] is accepted, "trial error/decision")
        same(row["decision"], "accepted" if accepted else "rejected", "trial decision label")
        same(self.endpoint["elapsed_s"], end, "trial endpoint RHS epoch")
        y = list(vector(self.endpoint["correction"], 6))
        scale = [a+max(abs(p), abs(q))*config["rtol"]
                 for a, p, q in zip(config["atol"], self.accepted_y, y, strict=True)]
        require(all(s > 0 for s in scale), "positive trial scale")
        same(row["scale"], scale, "independent trial scale")
        self.last_span_s = (self.accepted_t_s, end) if accepted else None
        self.expected_dense = 0
        if accepted:
            output_end = bisect_right(OFFSETS, end, lo=self.output_cursor)
            self.expected_dense = 3 if output_end > self.output_cursor else 0
            self.output_cursor = output_end
            self.accepted_t_s, self.accepted_y = end, y
        self.endpoint = None
        self.dense = self.since_trial = 0


def _observation(stream: Cursor, bundle: Row, row: Row, built: Row, kind: str, window: int | None,
                 owner: int | None, event: Event) -> None:
    saved = stream.take("observation")
    hi, lo = row["hi_tdb_s"], row["lo_s"]
    keys = ("profile", "kind", "index", "trial_index", "hi_tdb_s", "exact_tdb_s", "window")
    same([saved[k] for k in keys],
         [row["profile"], kind, row["index"], owner, hi, str(Fraction(hi)+Fraction(lo)), window],
         "source/force observation membership")
    progress: Row = {}
    computed = assess_observation(
        bundle["initial"], built["motion"], OLD.split.source_rows(row, bundle), built["geometry"],
        bundle["gm_m3_s2"], bundle["radii_m"], event, stream.check, progress=progress)
    same(saved["assessment"], computed, "independent sampled source/force arithmetic")
    require(computed["passed"] is True and "progress" not in saved, "sampled source/force gate")


def _adaptive(stream: Cursor, bundle: Row, nodes: list[Row], name: str, rhs_index: int, trial_index: int,
              event: Event, emit: Emit) -> tuple[list[Vector], int, int, Row]:
    initial = bundle["initial"]
    t0 = initial["epoch_tdb_s"]
    cfg = OLD.base.settings(name)
    header = stream.take("profile_start")
    same([header["name"], header["settings"], header["rhs_start"], header["coast_mass_kg"]],
         [name, cfg, rhs_index, bundle["mass_kg"]], "adaptive profile header")
    trail = Trials(name, rhs_index)
    rhs = RhsReplay(bundle, stream.check, event)
    first, windows = [], {}
    while stream.kind() in ("rhs", "trial"):
        if stream.kind() == "trial":
            row = stream.take("trial")
            event("trials", "attempt")
            trail.close(row, trial_index, rhs_index, cfg)
            event("trials", "complete")
            trial_index += 1
            continue
        row = stream.take("rhs")
        same([row["profile"], row["index"], row["global_index"]],
             [name, rhs_index-trail.start, rhs_index], "ordered RHS ordinal")
        rebuilt = rhs.rhs(row)
        in_trial = trail.add(row, rhs_index)
        owner = trial_index if in_trial else None
        sample = (row, rebuilt, owner)
        local = rhs_index-trail.start
        if local < 7:
            first.append(sample)
        if row["elapsed_s"] > 300.0:
            j = bisect_left(OFFSETS, row["elapsed_s"], lo=7)-7
            # Integer windows, including exact right endpoints. Verify membership
            # against the original binary64 callback rather than a rounded label.
            require(0 <= j < WINDOWS and 300+50*j < row["elapsed_s"] <= 350+50*j,
                    "RHS window epoch")
            if j not in windows:
                require(local >= 7, "RHS initial and window selectors overlap")
                windows[j] = sample
        rhs_index += 1
    require(len(first) == 7 and any(row["lo_s"] != 0 for row, _, _ in first)
            and set(windows) == set(range(WINDOWS)), "required RHS selectors")
    ordered_windows = [(*windows[j], j) for j in range(WINDOWS)]

    ret = stream.take("profile_return")
    nfev = rhs_index-trail.start
    require(ret["success"] is True and type(ret["status"]) is int and ret["status"] == 0,
            "adaptive successful completion")
    same([ret["name"], ret["nfev"], ret["t"]], [name, nfev, list(OFFSETS)], "raw adaptive output grid/count")
    require(type(ret["y"]) is list and len(ret["y"]) == 6, "raw adaptive array shape")
    columns = [vector(v, N) for v in ret["y"]]
    require(all(v[0].hex() == "0x0.0p+0" for v in columns), "adaptive exact initial correction")
    require(trail.accepted_t_s == DURATION_S and trail.since_trial == 0
            and trail.dense == trail.expected_dense and trail.output_cursor == N,
            "adaptive accepted terminal step and dense completion")
    solver = ret["solver_state"]
    same([solver["t_s"], solver["status"], solver["y"], solver["nfev"]],
         [DURATION_S, "finished", trail.accepted_y, nfev-trail.dense], "terminal solver/trace identity")
    require(words([v[-1] for v in columns], trail.accepted_y, 6), "adaptive exact terminal correction")

    direction = Directions(f"dop853_{name}", emit)
    outputs = []
    states = []
    for i, (offset, node) in enumerate(zip(OFFSETS, nodes, strict=True)):
        row = stream.take("output")
        same([row["profile"], row["index"], row["elapsed_s"]],
             [name, i, offset], "adaptive output identity")
        require("bodies" not in row and "moon_earth" not in row, "adaptive output uses pinned common sources")
        same(row["correction"], [v[i] for v in columns], "adaptive raw/output correction")
        full = row | {"bodies": node["bodies"], "moon_earth": node["moon_earth"]}
        rebuilt = reconstruct(full, bundle, check=stream.check, event=event)
        motion = rebuilt["motion"]
        assessment = assess_motion(initial, motion)
        same(row["motion_assessment"], assessment, "independent output assembly")
        require(assessment["passed"] is True, "adaptive output arithmetic gate")
        state = vector(motion["position_m"] + motion["velocity_m_s"], 6)
        require(i or words(state, initial["position_m"] + initial["velocity_m_s"], 6),
                "adaptive exact archived restart")
        direction.add(_direction((t0+offset, state, vector(node["bodies"]["Moon"]["state_si"], 6))))
        states.append(state)
        outputs.append((full, rebuilt))

    for row, built in outputs:
        _observation(stream, bundle, row, built, "output", None, None, event)
    for row, built, owner in first:
        _observation(stream, bundle, row, built, "rhs", None, owner, event)
    for row, built, owner, j in ordered_windows:
        _observation(stream, bundle, row, built, "rhs", j, owner, event)
    same(stream.take("profile_end")["name"], name, "adaptive profile end")
    return states, rhs_index, trial_index, direction.summary()


def _comparisons(stream: Cursor, bundle: Row, native: dict[str, list[Vector]],
                 adaptive: dict[str, list[Vector]], emit: Emit) -> Row:
    t0 = bundle["initial"]["epoch_tdb_s"]
    summary: Row = {}

    def compare(family: str, i: int, a: Vector, b: Vector, pos: float, vel: float) -> None:
        saved = stream.take("comparison")
        same([saved["name"], saved["index"], saved["epoch_tdb_s"]],
             [family, i, t0+OFFSETS[i]], "comparison membership")
        result = REF.compare_states(list(a), list(b), pos, vel)
        same(saved["assessment"], result, "independent state comparison")
        difference = OLD.previous._difference(b, a, saved["difference"])
        row = summary.setdefault(family, {"max_position_norm_m": 0.0, "max_velocity_norm_m_s": 0.0,
                                          "endpoint": None})
        for key in ("position_norm_m", "velocity_norm_m_s"):
            row["max_"+key] = max(row["max_"+key], difference[key])
        if i == N-1:
            row["endpoint"] = difference
        emit("comparison", {**saved, "assessment": result, "difference": difference})
        require(result["passed"] is True, "trajectory gate: " + family)

    for i, (a, b) in enumerate(zip(native["normal"], native["tighter"], strict=True)):
        compare("native_step", i, a, b, .01, 1e-5)
    for i, (a, b, c) in enumerate(zip(native["tighter"], adaptive["normal"], adaptive["tighter"], strict=True)):
        compare("native_tighter", i, a, c, .01, 1e-5)
        compare("oracle_step", i, b, c, .001, 1e-6)
    return summary


def _marker(grids: dict[str, Row]) -> Row:
    common = [grids[f"{k}_{p}"] for k in ("rk4", "dop853") for p in PROFILES]
    meshes = [grids[f"mesh_{p}"] for p in PROFILES]
    require(all(row["rows"] == N for row in common)
            and [row["rows"] for row in meshes] == [16001, 32001], "direction row completeness")
    reasons = {k: v["reasons"] for k, v in grids.items() if v["reasons"]}
    report: Row = {"marker_status": "marker-not-established", "marker_reason": reasons or None,
                   "common_bracket_tdb_s": None, "native_overlap_tdb_s": None}
    if reasons:
        return report
    pair = common[0]["first_outward_tdb_s"]
    if any(row["first_outward_tdb_s"] != pair for row in common[1:]):
        report["marker_reason"] = "common-brackets-disagree"
        return report
    report["common_bracket_tdb_s"] = pair
    a, b = meshes[0]["first_outward_tdb_s"], meshes[1]["first_outward_tdb_s"]
    if any(not pair[0] <= left < right <= pair[1] for left, right in (a, b)):
        report["marker_reason"] = "mesh-bracket-outside-common"
        return report
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    if lo >= hi:
        report["marker_reason"] = "mesh-brackets-do-not-overlap"
    else:
        report.update(marker_status="marker-bracketed", native_overlap_tdb_s=[lo, hi])
    return report


def _counts(saved: Row, recomputed: dict[str, dict[str, int]], rhs: int, trials: int) -> None:
    expected = SAMPLE_COUNTS | {
        "record_evaluations": recomputed["record_evaluations"]["completed"],
        "rhs": rhs, "trials": trials, "states": 4*(rhs+N),
        "native_guard_reads": GUARD_READS, "native_arcs": 2, "solves": 2,
        "native_telemetry": 2*N, "native_reference_fields": 12*N,
        "binary64_fields": 3*(rhs+2*N), "dynamic_totals": rhs+2*N,
    }
    expected_local = {k: {"attempted": n, "completed": n} for k, n in expected.items() if k not in OPAQUE}
    same(recomputed, expected_local, "independently replayed operation counts")
    if saved.keys() & START_META.keys():
        # The launch envelope independently verifies the closing snapshot.
        expected.update(START_META)
    expected_full = {k: {"attempted": n, "completed": n, "returned": n if k in OPAQUE else 0}
                     for k, n in expected.items()}
    same(saved, expected_full, "saved operation counters")


def verify(bundle: Row, records: Iterable[Record], emit: Emit, check: Check, *, status: str) -> Row:
    """Check one bounded complete stream; partial data never qualifies a marker."""
    require(status in ("passed", "partial", "capacity"), "invalid study status")
    report: Row = {
        "audit_status": "partial", "numerical_status": "unavailable", "marker_status": "unavailable",
        "scientific_verified": False, "continuous_safety_verified": False,
        "native_calls": 0, "kernel_loads": 0, "spacecraft_propagations": 0, "scientific_imports": 0,
    }
    if status == "partial":
        # Drain the whole prefix so independent shard and finalization checks still run.
        prefix: Counter[str] = Counter()
        for kind, _ in records:
            check()
            prefix[kind] += 1
        report["partial_record_counts"] = dict(prefix)
        return report

    recomputed: dict[str, dict[str, int]] = {}

    def event(operation: str, phase: str) -> None:
        check()
        require(operation in CAPS and phase in ("attempt", "complete"), "audit operation")
        row = recomputed.setdefault(operation, {"attempted": 0, "completed": 0})
        row["attempted" if phase == "attempt" else "completed"] += 1
        require(row["completed"] <= row["attempted"] <= CAPS[operation], "audit operation cap: " + operation)

    stream = Cursor(iter(records), check)
    same(bundle["offsets_s"], list(OFFSETS), "fixed common grid")
    nodes = []
    for i, offset in enumerate(OFFSETS):
        row = stream.take("node")
        same([row["index"], row["elapsed_s"]], [i, offset], "node index and elapsed epoch")
        same(row["requests"], validate_sources(row, bundle["initial"], complete=True), "ordered node requests")
        if i == 0:
            require(words(row["bodies"]["Moon"]["state_si"], bundle["restart_moon_state_si"], 6),
                    "exact archived Moon restart")
        nodes.append(row)

    native: dict[str, list[Vector]] = {}
    grids: dict[str, Row] = {}
    for name, step in zip(PROFILES, STEPS_S, strict=True):
        native[name], grids[f"rk4_{name}"], grids[f"mesh_{name}"] = _native(stream, bundle, nodes, name, step, event, emit)
    adaptive: dict[str, list[Vector]] = {}
    rhs, trials = 0, 0
    for name in PROFILES:
        adaptive[name], rhs, trials, grids[f"dop853_{name}"] = _adaptive(
            stream, bundle, nodes, name, rhs, trials, event, emit)
    comparison = _comparisons(stream, bundle, native, adaptive, emit)

    n_capacity = 0
    replay = RhsReplay(bundle, check, event)
    if status == "capacity":
        while stream.kind() == "capacity_rhs":
            row = stream.take("capacity_rhs")
            same([row["profile"], row["usage"], row["index"], row["global_index"]],
                 ["capacity", "capacity-only", n_capacity, rhs], "artificial cap-only tail order")
            replay.rhs(row)
            rhs, n_capacity = rhs+1, n_capacity+1
        require((rhs, trials) == (RHS_CAP, TRIAL_CAP), "full artificial cap accounting")

    saved = stream.take("study_summary")
    same(saved["comparison_summary"], comparison, "independent comparison summary")
    _counts(saved["counts"], recomputed, rhs, trials)
    require(stream.kind() is None, "trailing study record")
    verdict = _marker(grids)
    check()
    return report | verdict | {
        "audit_status": "passed", "numerical_status": "passed", "direction_grids": grids,
        "comparison_summary": comparison, "recomputed_counts": recomputed, "comparisons": 3*N,
        "native_telemetry": 2*N, "adaptive_observations": OBSERVATIONS,
        "common_direction_rows": 4*N, "mesh_direction_rows": 48_002,
        "rhs": rhs, "trials": trials, "capacity_rhs": n_capacity,
    }
