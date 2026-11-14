"""Independent stdlib replay for ADR0193's saved 50 s extension."""

from __future__ import annotations

from collections.abc import Callable
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import math
from pathlib import Path
import sys
from types import FunctionType, ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OFFSETS = tuple(float(i) for i in range(0, 51, 5))
PROFILES = ("normal", "tighter")
SOURCES = ("Sun", "Moon", "Earth")
MARKER_M = 3_474_800
PINS = {
    "0186-long-b-audit.py": "ae44501220b4cff1366de5182ec3b1985bd3dbcdeeabf328e46c142291cdd04a",
    "0186-long-b-reference.py": "4fb366b232c1515e4d6f96d2bc14b77249ed09bed909bbe3d79ac9a29b59e7c5",
    "0183-earth-native-replay.py": "3ddff9eb6b4ee320aae9cd8dddc89f5f9dbe82bbcea3758dad1d17f3e396eba6",
}
SAMPLE_COUNTS = {"body_checks": 108, "moon_earth_checks": 36, "source_rows": 108,
                 "reference_fields": 864, "model_totals": 36}
CAPS = SAMPLE_COUNTS | {
    "record_evaluations": 216, "native_telemetry": 22, "native_reference_fields": 132,
    "rhs": 10_000, "trials": 1_000, "states": 40_044, "native_guard_reads": 462,
    "native_arcs": 2, "solves": 2, "identities": 2, "initializations": 1, "metadata": 30,
    "binary64_fields": 30_066, "dynamic_totals": 10_022,
}
type Row = dict[str, Any]
type Check = Callable[[], None]
type Event = Callable[[str, str], None]
type Vector = tuple[float, ...]
type Operand = tuple[float, Vector, Vector]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("extension audit: " + message)


def _load(name: str) -> ModuleType:
    path = HERE / name
    source = path.read_bytes()
    require(sha256(source).hexdigest() == PINS[name], "frozen helper " + name)
    module = ModuleType("range_extension_audit_" + path.stem.replace("-", "_"))
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


OLD = _load("0186-long-b-audit.py")
REF = _load("0186-long-b-reference.py")
NATIVE = _load("0183-earth-native-replay.py")
same, number, vector = OLD.same, OLD.number, OLD.vector
same_words = NATIVE.same_words


def _bounded_trial_replay() -> FunctionType:
    # Sharing the pinned trial arithmetic does not share any study code.
    # Replace only the horizon in a separate function namespace.
    trials = OLD.check_trials
    return FunctionType(trials.__code__, trials.__globals__ | {"DURATION_S": 50.0})


def _ledger(study: Row, check: Check) -> None:
    counts = study["counts"]
    require(isinstance(counts, dict) and counts.keys() <= CAPS.keys(), "counter inventory")
    rebuilt = {name: {"attempted": 0, "returned": 0, "completed": 0} for name in counts}
    phases = {"attempt": "attempted", "return": "returned", "complete": "completed"}

    def done(name: str) -> int:
        return rebuilt.get(name, {}).get("completed", 0)

    for i, item in enumerate(study["ledger"]):
        if i % 256 == 0:
            check()
        op, phase = item["operation"], phases[item["phase"]]
        row = rebuilt[op]
        if phase == "attempted":
            if op in ("states", "native_arcs", "native_guard_reads"):
                require(row["attempted"] == row["completed"], "overlapping " + op + " work")
                require(done("identities") == 1, "initial identity before science")
            elif op == "solves":
                require(done("native_arcs") == 2 and done("native_telemetry") == 22,
                        "native checks before DOP853")
                if row["attempted"]:
                    require(done("solves") == 1 and all(done(k) == v//2 for k, v in SAMPLE_COUNTS.items()),
                            "normal force checks before tighter DOP853")
            elif op == "identities" and row["attempted"]:
                require(done("solves") == 2 and all(done(k) == v for k, v in SAMPLE_COUNTS.items()),
                        "completed science before final identity")
        row[phase] += 1
        require(row["completed"] <= row["attempted"] <= CAPS[op], "work cap on " + op)
        if op in OLD.OPAQUE:
            require(row["completed"] <= row["returned"] <= row["attempted"], "return order on " + op)
        else:
            require(not row["returned"], "nonopaque return on " + op)
    same(counts, rebuilt, "independent work ledger")


def _native_profiles(study: Row, bundle: Row, check: Check,
                     event: Event) -> tuple[dict[str, list[Vector]], dict[str, list[Operand]]]:
    t0 = bundle["initial"]["epoch_tdb_s"]
    initial = bundle["initial"]["position_m"] + bundle["initial"]["velocity_m_s"]
    gm, radii = bundle["gm_m3_s2"], bundle["radii_m"]
    samples, meshes = {}, {}
    for profile, name, step in zip(study["native_profiles"], PROFILES, (1.0, 0.5), strict=True):
        require(profile["name"] == name and number(profile["step_s"], "step") == step, "native profile")
        same(profile["arc"], {"attempted": 1, "returned": 1, "completed": 1}, "native arc")
        same(profile["coast_mass_kg"], bundle["mass_kg"], "native fixed mass")
        inventory = profile["inventory"]
        same([inventory[k] for k in ("model", "origin", "orientation", "aberration", "force_order")],
             ["B", "SSB", "J2000", "NONE", ["total", *SOURCES]], "native inventory")
        same(inventory["force_counts"], dict.fromkeys(SOURCES, 1), "one field per body")
        require(set(inventory["gm_m3_s2"]) == set(SOURCES), "native GM inventory")
        for body in SOURCES:
            require(abs(number(inventory["gm_m3_s2"][body], "native GM") - gm[body]) <= 1e-15*gm[body],
                    "native GM " + body)
        raw = profile["raw_returned"]
        require(raw["integration_completed"] is True, "native integration incomplete")
        epochs = [t0 + j*step for j in range(int(50/step)+1)]
        history, accelerations = raw["state_history"], raw["dependent_variable_history"]
        for table in (history, accelerations):
            require(isinstance(table, dict) and [float(k) for k in table] == epochs, "native raw grid/order")
        states = [NATIVE.vector(value, 6) for value in history.values()]
        require(same_words(initial, states[0], 6), "native exact initial state")
        forces = [NATIVE.vector(value, 12) for value in accelerations.values()]
        for force in forces:
            check()
            summed = tuple(math.fsum(force[j+i] for i in (3, 6, 9)) for j in range(3))
            require(math.dist(force[:3], summed) <= 1e-12, "native total/source consistency")
        guards = profile["guards"]
        n = len(epochs)
        require(len(guards) == 3*(n+1), "native guard count")
        bodies: list[Vector] = []
        for index, guard in enumerate(guards):
            check()
            group, j = divmod(index, 3)
            mesh_index = max(0, group-1)
            body = SOURCES[j]
            same([guard["group"], guard["body"], guard["epoch_tdb_s"]],
                 [group, body, epochs[mesh_index]], "ordered mesh guard")
            state = NATIVE.vector(guard["state_si"], 6)
            distance = math.dist(states[mesh_index][:3], state[:3])
            same(guard["distance_m"], distance, "guard distance")
            require(guard["passed"] is True and distance > radii[body] > 0, "native exterior guard")
            bodies.append(state)
        result = profile["result"]
        same([result[k] for k in ("origin", "orientation", "position_units", "velocity_units", "time_units",
                                  "force_order", "step_s", "retained_states", "guarded_states")],
             ["SSB", "J2000", "m", "m/s", "TDB seconds since J2000",
              ["total", *SOURCES], step, n, n], "native sample labels")
        coepochs: list[Vector] = []
        for offset, saved in zip(OFFSETS, result["samples"], strict=True):
            check()
            index = int(offset/step)
            same(saved["epoch_tdb_s"], t0+offset, "native sample epoch")
            require(same_words(saved["state"], states[index], 6)
                    and same_words(saved["acceleration_m_s2"], forces[index], 12),
                    "native sample differs from raw output")
            edge = 3*(index+1)
            NATIVE.telemetry(states[index], forces[index], [v[:3] for v in bodies[edge:edge+3]], gm, event)
            coepochs.append(states[index])
        samples[name] = coepochs
        meshes[name] = [(epoch, states[i], bodies[3*(i+1)+1]) for i, epoch in enumerate(epochs)]
    return samples, meshes


def _adaptive_profiles(study: Row, bundle: Row, check: Check,
                       event: Event) -> tuple[dict[str, list[Vector]], list[tuple[str, str, int, Row, Row]]]:
    profiles, rhs = study["profiles"], study["rhs"]
    same([profile["name"] for profile in profiles], list(PROFILES), "ordered adaptive profiles")
    require(len(rhs) <= CAPS["rhs"], "RHS cap")
    expected = []
    for offset, node in zip(OFFSETS, study["node_table"], strict=True):
        check()
        same(node["elapsed_s"], offset, "fixed common grid")
        expected.extend(OLD.validate_sources(node, bundle["initial"], complete=True))
        if offset == 0:
            require(same_words(node["bodies"]["Moon"]["state_si"], bundle["restart_moon_state_si"], 6),
                    "shared start Moon differs from frozen operand")
    groups: dict[str, list[tuple[Row, Row]]] = {name: [] for name in PROFILES}
    order = -1
    for i, row in enumerate(rhs):
        check()
        name = row["profile"]
        require(name in PROFILES and PROFILES.index(name) >= order, "RHS profile order")
        order = PROFILES.index(name)
        same([row["global_index"], row["index"]], [i, len(groups[name])], "RHS ordinal")
        require(row["completed"] is True and 0 <= number(row["elapsed_s"], "RHS epoch") <= 50,
                "RHS completion/time")
        expected.extend(OLD.validate_sources(row, bundle["initial"], complete=True))
        event("rhs", "attempt")
        groups[name].append((row, OLD.reconstruct_row(row, bundle, check=check, event=event)))
        event("rhs", "complete")
    same(study["state_requests"], expected, "ordered node and RHS queries")

    profiles_out: dict[str, list[Vector]] = {}
    selected: list[tuple[str, str, int, Row, Row]] = []
    rhs_start = 0
    for profile in profiles:
        name = profile["name"]
        callbacks = groups[name]
        check()
        same(profile["settings"], OLD.base.settings(name), "adaptive settings")
        same(profile["rhs_start"], rhs_start, "adaptive RHS start")
        rhs_start += len(callbacks)
        same(profile["coast_mass_kg"], bundle["mass_kg"], "adaptive fixed mass")
        require(len(callbacks) >= 7 and any(row["lo_s"] != 0 for row, _ in callbacks[:7]),
                "required first seven RHS and one nonzero residual")
        raw = profile["raw_returned"]
        require(raw["success"] is True and type(raw["status"]) is int and raw["status"] == 0,
                "adaptive completion")
        same(raw["t"], list(OFFSETS), "raw adaptive time grid")
        same(raw["nfev"], len(callbacks), "raw completed RHS count")
        y = [vector(r, len(OFFSETS), "raw adaptive correction") for r in raw["y"]]
        require(len(y) == 6 and all(r[0] == 0 for r in y), "adaptive zero initial correction")
        solver = profile["solver_state"]
        same([solver["t_s"], solver["status"], solver["y"]], [50.0, "finished", [r[-1] for r in y]],
             "adaptive internal endpoint")
        require(type(solver["nfev"]) is int and len(callbacks)-solver["nfev"] in (0, 3),
                "step versus dense callback count")
        vectors = []
        for j, (node, output) in enumerate(zip(study["node_table"], profile["outputs"], strict=True)):
            check()
            same([output["profile"], output["index"], output["elapsed_s"]], [name, j, OFFSETS[j]],
                 "adaptive output membership")
            same([output["bodies"], output["moon_earth"]], [node["bodies"], node["moon_earth"]],
                 "common node source operands")
            same(output["correction"], [r[j] for r in y], "solver/output correction")
            built = OLD.reconstruct_row(output, bundle, check=check, event=event)
            motion = built["motion"]
            assessment = REF.assess_motion(bundle["initial"], motion)
            same(output["motion_assessment"], assessment, "independent output assembly")
            require(assessment["passed"] is True, "output assembly gate")
            vectors.append(NATIVE.vector(motion["position_m"] + motion["velocity_m_s"], 6))
            selected.append((name, "output", j, output, built))
        initial = bundle["initial"]
        require(same_words(vectors[0], initial["position_m"] + initial["velocity_m_s"], 6),
                "adaptive exact initial state")
        profiles_out[name] = vectors
        selected.extend((name, "rhs", row["index"], row, built) for row, built in callbacks[:7])
    return profiles_out, selected


def _observations(study: Row, bundle: Row, selected: list[tuple[str, str, int, Row, Row]],
                  membership: dict[int, int], check: Check, event: Event) -> None:
    require(len(selected) == len(study["observations"]) == 36, "force observation count")
    for (name, kind, index, row, built), saved in zip(selected, study["observations"], strict=True):
        check()
        trial = membership.get(row["global_index"]) if kind == "rhs" else None
        hi, lo = row["hi_tdb_s"], row["lo_s"]
        same([saved[k] for k in ("profile", "kind", "index", "trial_index", "hi_tdb_s", "exact_tdb_s")],
             [name, kind, index, trial, hi, str(Fraction(hi)+Fraction(lo))], "force observation membership")
        progress: Row = {}
        computed = REF.assess_observation(
            bundle["initial"], built["motion"], OLD.split.source_rows(row, bundle), built["geometry"],
            bundle["gm_m3_s2"], bundle["radii_m"], event, check=check, progress=progress)
        same(saved["progress"], progress, "independent source and force progress")
        same(saved["assessment"], computed, "independent source and force assessment")
        require(computed["passed"] is True, "source and force gate")


def _comparisons(study: Row, bundle: Row, native: dict[str, list[Vector]],
                 adaptive: dict[str, list[Vector]], check: Check) -> Row:
    t0 = bundle["initial"]["epoch_tdb_s"]
    expected = [("native_step", i, a, b, .01, 1e-5)
                for i, (a, b) in enumerate(zip(native["normal"], native["tighter"], strict=True))]
    for i, (a, b, c) in enumerate(zip(native["tighter"], adaptive["normal"], adaptive["tighter"], strict=True)):
        expected.extend((("native_tighter", i, a, c, .01, 1e-5), ("oracle_step", i, b, c, .001, 1e-6)))
    require(len(study["comparisons"]) == len(expected) == 33, "trajectory comparison count")
    summary: Row = {}
    for saved, (name, i, left, right, p, v) in zip(study["comparisons"], expected, strict=True):
        check()
        same([saved["name"], saved["index"], saved["epoch_tdb_s"]],
             [name, i, t0+OFFSETS[i]], "comparison membership")
        assessment = REF.compare_states(list(left), list(right), p, v)
        same(saved["assessment"], assessment, "independent trajectory assessment")
        require(assessment["passed"] is True, "trajectory gate")
        difference = OLD.previous._difference(right, left, saved["difference"])
        row = summary.setdefault(name, {"max_position_norm_m": 0.0, "max_velocity_norm_m_s": 0.0,
                                        "endpoint": None})
        for key in ("position_norm_m", "velocity_norm_m_s"):
            row["max_"+key] = max(row["max_"+key], difference[key])
        if i == len(OFFSETS)-1:
            row["endpoint"] = difference
    same(study["comparison_summary"], summary, "independent comparison summary")
    return summary


def _direction(operand: Operand) -> Row:
    epoch, spacecraft, moon = operand
    q = [Fraction(a)-Fraction(b) for a, b in zip(spacecraft[:3], moon[:3], strict=True)]
    v = [Fraction(a)-Fraction(b) for a, b in zip(spacecraft[3:], moon[3:], strict=True)]
    square, dot = sum(a*a for a in q), sum(a*b for a, b in zip(q, v, strict=True))
    require(square > 0, "undefined radial direction")

    def sign(value: Fraction | Decimal) -> int:
        return (value > 0) - (value < 0)

    signs = [sign(square-MARKER_M**2), sign(dot)]
    with localcontext() as context:
        context.prec, context.rounding = 80, ROUND_HALF_EVEN
        sc, centre = ([Decimal.from_float(w) for w in state] for state in (spacecraft, moon))
        qd = [sc[j]-centre[j] for j in range(3)]
        vd = [sc[j]-centre[j] for j in range(3, 6)]
        sd, dd = sum(x*x for x in qd), sum(x*y for x, y in zip(qd, vd, strict=True))
        require([sign(sd-MARKER_M**2), sign(dd)] == signs, "independent sign disagreement")
        radius_d = sd.sqrt()
        radial_d = dd/radius_d
    qb = [a-b for a, b in zip(spacecraft[:3], moon[:3], strict=True)]
    vb = [a-b for a, b in zip(spacecraft[3:], moon[3:], strict=True)]
    radius = math.hypot(*qb)
    radial = math.fsum(a/radius*b for a, b in zip(qb, vb, strict=True))
    require(abs(radius-float(radius_d)) <= 1e-6 and abs(radial-float(radial_d)) <= 1e-9,
            "independent radius or radial metric disagreement")
    return {"epoch_tdb_s": epoch, "spacecraft_si": list(spacecraft), "moon_si": list(moon),
            "range_sign": signs[0], "radial_sign": signs[1], "radius_m": radius,
            "radial_speed_m_s": radial, "decimal80_radius_m": str(radius_d),
            "decimal80_radial_speed_m_s": str(radial_d)}


def _brackets(rows: list[Row]) -> Row:
    outward, inward, nonpositive = [], [], []
    for left, right in zip(rows, rows[1:]):
        a, b = left["range_sign"], right["range_sign"]
        pair = [left["epoch_tdb_s"], right["epoch_tdb_s"]]
        if (a, b) == (-1, 1):
            outward.append(pair)
            if min(left["radial_sign"], right["radial_sign"]) <= 0:
                nonpositive.append(pair)
        elif (a, b) == (1, -1):
            inward.append(pair)
    zero = [row["epoch_tdb_s"] for row in rows if row["range_sign"] == 0]
    reasons = [label for label, condition in (
        ("exact-equality", bool(zero)), ("inward-pair", bool(inward)),
        ("nonpositive-radial-endpoint", bool(nonpositive)),
        ("multiple-outward-pairs", len(outward) > 1),
        ("no-outward-pair", not outward)) if condition]
    return {"rows": rows, "outward_pairs_tdb_s": outward, "inward_pairs_tdb_s": inward,
            "exact_equality_tdb_s": zero, "nonpositive_endpoint_pairs_tdb_s": nonpositive,
            "reasons": reasons}


def _direction_grids(study: Row, bundle: Row, native: dict[str, list[Vector]],
                     meshes: dict[str, list[Operand]], adaptive: dict[str, list[Vector]],
                     report: Row, check: Check) -> None:
    t0 = bundle["initial"]["epoch_tdb_s"]
    moon_states = [NATIVE.vector(node["bodies"]["Moon"]["state_si"], 6)
                   for node in study["node_table"]]
    grid_records: Row = {}
    report.update(direction_grids=grid_records, common_direction_rows=0, mesh_direction_rows=0)
    for family, states in (("rk4", native), ("dop853", adaptive)):
        for name, vector_rows in states.items():
            rows = []
            for offset, sc, moon in zip(OFFSETS, vector_rows, moon_states, strict=True):
                check()
                rows.append(_direction((t0+offset, sc, moon)))
                report["common_direction_rows"] += 1
            grid_records[f"{family}_{name}"] = _brackets(rows)
    for name, operands in meshes.items():
        rows = []
        common = {r["epoch_tdb_s"]: r for r in grid_records[f"rk4_{name}"]["rows"]}
        for entry in operands:
            check()
            measured = _direction(entry)
            if measured["epoch_tdb_s"] in common:
                ref = common[measured["epoch_tdb_s"]]
                require(all(measured[key] == ref[key] for key in ("range_sign", "radial_sign"))
                        and abs(ref["radius_m"] - measured["radius_m"]) <= 1e-6
                        and abs(ref["radial_speed_m_s"] - measured["radial_speed_m_s"]) <= 1e-9,
                        "common/native mesh geometry mismatch")
            rows.append(measured)
            report["mesh_direction_rows"] += 1
        grid_records[f"mesh_{name}"] = _brackets(rows)
    require((report["common_direction_rows"], report["mesh_direction_rows"]) == (44, 152),
            "direction counts")
    reasons = {name: grid["reasons"] for name, grid in grid_records.items() if grid["reasons"]}
    status, reason, common_bracket, overlap = "marker-not-established", None, None, None
    if reasons:
        reason = reasons
    else:
        brackets = [grid["outward_pairs_tdb_s"][0] for grid in grid_records.values()]
        common_bracket = brackets[0]
        left, right = common_bracket
        native_brackets = brackets[4:]
        if any(pair != common_bracket for pair in brackets[1:4]):
            reason = "common-brackets-disagree"
            common_bracket = None
        elif not all(left <= a < b <= right for a, b in native_brackets):
            reason = "mesh-bracket-outside-common"
        else:
            lo, hi = max(a for a, _ in native_brackets), min(b for _, b in native_brackets)
            if lo >= hi:
                reason = "mesh-brackets-do-not-overlap"
            else:
                status, overlap = "marker-bracketed", [lo, hi]
    report.update(marker_status=status, marker_reason=reason, common_bracket_tdb_s=common_bracket,
                  native_overlap_tdb_s=overlap)


def _counts(study: Row, recomputed: dict[str, dict[str, int]]) -> None:
    n_rhs = len(study["rhs"])
    records = sum(3 if obs["exact_tdb_s"] == str(Fraction(obs["hi_tdb_s"])) else 6
                  for obs in study["observations"])
    expected = SAMPLE_COUNTS | {
        "record_evaluations": records, "native_telemetry": 22, "native_reference_fields": 132,
        "rhs": n_rhs, "trials": len(study["trials"]), "states": 4*(n_rhs+len(OFFSETS)),
        "native_guard_reads": 462, "native_arcs": 2, "solves": 2, "identities": 2,
        "binary64_fields": 3*(n_rhs+22), "dynamic_totals": n_rhs+22,
    }
    if study["adapter_mode"] == "reference":
        expected.update(initializations=1, metadata=30)
    same(study["counts"], {key: {"attempted": count, "completed": count,
                                  "returned": count if key in OLD.OPAQUE else 0}
                           for key, count in expected.items()}, "complete work counts")
    same(recomputed, {key: {"attempted": count, "completed": count}
                      for key, count in expected.items() if key not in OLD.OPAQUE},
         "independent replay counts")


def verify(bundle: Row, study_report: Row, report: Row, check: Check) -> None:
    """Audit saved arithmetic and assign a marker verdict only after all gates."""
    study = study_report
    report.update(marker_status="unavailable", numerical_status="unavailable",
                  continuous_safety_verified=False)
    require(study["status"] in ("passed", "partial", "failed")
            and study["adapter_mode"] in ("reference", "injected-test"),
            "saved study status or mode")
    for key, expected in (
        ("model", "B"), ("duration_s", 50.0), ("budget_s", 60.0),
        ("origin", "SSB"), ("orientation", "J2000"), ("time_scale", "TDB"),
        ("aberration_correction", "NONE"), ("position_units", "m"),
        ("velocity_units", "m/s"), ("acceleration_units", "m/s^2"),
        ("model_a_propagations", 0), ("gm_acquisitions", 0), ("optimizer_calls", 0),
        ("scientific_verified", False), ("mission_accuracy_verified", False),
        ("continuous_safety_verified", False),
    ):
        same(study[key], expected, "scientific boundary: " + key)
    _ledger(study, check)
    full = study["status"] == "passed"
    if "inputs" not in study:
        require(not full and not any(study.get(key) for key in ("rhs", "identities", "node_table",
                                                                "profiles", "native_profiles")),
                "work without frozen inputs")
        report["partial_study_error"] = study["error"]
        return
    same(study["inputs"], bundle, "frozen start/forces/metadata identity")
    same([float(x) for x in bundle["offsets_s"]], list(OFFSETS), "extension grid")
    if "coast_mass_kg" in study:
        same(study["coast_mass_kg"], bundle["mass_kg"], "fixed cutoff mass")
    OLD.previous._check_metadata(study, bundle, full)
    OLD.previous._check_native_counts(study, full)
    if not full:
        # A partial study never supplies an acceptance verdict. Preserve its
        # first error with the independently checked input/ledger evidence.
        report["partial_study_error"] = study["error"]
        return
    require("coast_mass_kg" in study and not study.get("unavailable") and not study.get("error"),
            "successful study metadata")
    require(tuple(study["identities"]) == ("before", "after")
            and study["identities"]["before"] == study["identities"]["after"], "endpoint identity")
    recomputed: dict[str, dict[str, int]] = {}

    def event(operation: str, phase: str) -> None:
        check()
        require(operation in CAPS and phase in ("attempt", "complete"), "audit operation")
        row = recomputed.setdefault(operation, {"attempted": 0, "completed": 0})
        row["attempted" if phase == "attempt" else "completed"] += 1
        require(row["completed"] <= row["attempted"] <= CAPS[operation], "audit cap on " + operation)

    report["recomputed_counts"] = recomputed
    native, meshes = _native_profiles(study, bundle, check, event)
    report["native_telemetry"] = 22
    adaptive, selected = _adaptive_profiles(study, bundle, check, event)
    membership = _bounded_trial_replay()(study, check, event)
    _observations(study, bundle, selected, membership, check, event)
    report["observations"] = 36
    report["comparison_summary"] = _comparisons(study, bundle, native, adaptive, check)
    report["comparisons"] = 33
    _counts(study, recomputed)
    # Finalized receipt and resource identity checks are performed by the caller.
    _direction_grids(study, bundle, native, meshes, adaptive, report, check)
    check()
    report["numerical_status"] = "passed"
