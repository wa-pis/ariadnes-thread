"""Check the saved departure packet and receiving-side inventory without dynamics."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import math
from typing import Any

type Row = dict[str, Any]
type Vector = list[float]
type Check = Callable[[], None]

BODIES = ("Sun", "Moon", "Earth")
FRAME = {"origin": "SSB", "orientation": "J2000"}
TIME = "TDB seconds since J2000"
MODEL = "r5-ssb-sun-moon-earth-point-v1"
IDEAL_MODEL = "sun-centered-zero-revolution-patched-conic-v1"
LIVE = "0198-verification.json"
DESIGN = "0196-design-inputs.json"
R1 = "0119-m2-reference.json"
R2 = "0129-reference-coast.json"
R2_AUDIT = "0129-reference-coast-audit.json"
NOMINAL = "0079-research-reference.json"
CENTRAL = "0098-central-correction-study.json"
OLD_COAST = "0082-identical-start-coast.json"
STEP_STUDY = "0083-coast-step-study.json"
ENDPOINTS = "0136-retained-boundary-audit.json"


def need(ok: object, message: str) -> None:
    if not ok:
        raise ValueError(message)


def number(value: object, label: str) -> float:
    need(type(value) in (int, float), f"{label}: finite number required")
    result = float(value)  # type: ignore[arg-type]
    need(math.isfinite(result), f"{label}: finite number required")
    return result


def word(v: object, label: str) -> str:
    return number(v, label).hex()


def same_word(v: object, w: object, label: str) -> None:
    need(word(v, label) == word(w, label), f"{label}: binary64 words differ")


def vector(value: object, n: int, label: str) -> Vector:
    if not isinstance(value, list) or len(value) != n:
        raise ValueError(f"{label}: expected {n} components")
    return [number(v, label) for v in value]


def words(state: Vector) -> list[str]:
    return [x.hex() for x in state]


def framed(value: Row, label: str) -> None:
    need(all(value[k] == v for k, v in FRAME.items()), f"{label}: SSB/J2000 required")


def cartesian(value: Row, label: str) -> Vector:
    framed(value, label)
    return vector(value["position_m"], 3, label) + vector(value["velocity_m_s"], 3, label)


def decimal_text(v: object, label: str) -> Decimal:
    if not isinstance(v, str) or len(v) > 128:
        raise ValueError(f"{label}: Decimal string required")
    result = Decimal(v)
    need(result.is_finite(), f"{label}: finite Decimal required")
    return result


def sign(x: Fraction | Decimal) -> int:
    return int(x > 0) - int(x < 0)


def direction(sc: Vector, moon: Vector, marker_m: float, saved: Row) -> Row:
    """Rebuild the radius and radial rate from the exact stored binary64 operands."""
    p, v = ([Fraction(sc[j]) - Fraction(moon[j]) for j in indexes]
            for indexes in (range(3), range(3, 6)))
    square, dot = sum(x*x for x in p), sum(x*y for x, y in zip(p, v, strict=True))
    need(square > 0, "lunar radius must be positive")
    range_sign, radial_sign = sign(square-Fraction(marker_m)**2), sign(dot)
    with localcontext() as context:
        context.prec, context.rounding = 80, ROUND_HALF_EVEN
        pd, vd = ([Decimal.from_float(sc[j])-Decimal.from_float(moon[j]) for j in indexes]
                  for indexes in (range(3), range(3, 6)))
        sd, dd = sum(x*x for x in pd), sum(x*y for x, y in zip(pd, vd, strict=True))
        need((sign(sd-Decimal.from_float(marker_m)**2), sign(dd)) == (range_sign, radial_sign),
             "exact and Decimal80 direction signs differ")
        radius_m = sd.sqrt()
        speed_m_s = dd/radius_m
        for key, expected_sign in (("range_sign", range_sign), ("radial_sign", radial_sign)):
            need(type(saved[key]) is int and saved[key] == expected_sign, f"audited {key} differs")
        for metric, precise, result, gate in (
            ("radius_m", "decimal80_radius_m", radius_m, Decimal("1e-6")),
            ("radial_speed_m_s", "decimal80_radial_speed_m_s", speed_m_s, Decimal("1e-9")),
        ):
            recorded = Decimal.from_float(number(saved[metric], metric))
            need(abs(result-recorded) <= gate and abs(result-decimal_text(saved[precise], precise)) <= gate,
                 f"audited {metric} exceeds arithmetic gate")
    return {"radius_m": float(radius_m), "radial_speed_m_s": float(speed_m_s),
            "range_sign": range_sign, "radial_sign": radial_sign}


def paired_cutoff(inputs: dict[str, Row]) -> tuple[Row, float]:
    nominal = inputs[NOMINAL]["science"]["nominal"]
    trial = inputs[CENTRAL]["science"]["runs"][0]
    base = trial["run"]
    left, right = nominal["boundaries"][1], base["boundaries"][1]
    label = "shared nominal departure cutoff"
    need(trial["role"] == "baseline" and left["label"] == right["label"] == "departure-cutoff", label)
    need(words(cartesian(left, label)) == words(cartesian(right, label)), f"{label}: state words differ")
    same_word(left["epoch_tdb_s"], right["epoch_tdb_s"], f"{label} epoch")
    mass_kg = number(nominal["boundary_masses_kg"][1], f"{label} mass")
    same_word(base["boundary_masses_kg"][1], mass_kg, f"{label} mass")
    return left, mass_kg


def outgoing(pins: Row, inputs: dict[str, Row], selected: list[tuple[str, Row]], check: Check) -> Row:
    packet = pins["export_selector"]
    framed(packet, "export selector")
    need([packet[k] for k in ("model", "profile", "time_scale", "units", "mass_kind")] ==
         ["B", "RK4 tighter", TIME, ["m", "m/s", "kg"], "constant coast metadata"], "export selector contract")
    design, live = inputs[DESIGN], inputs[LIVE]
    fixed, plan = design["fixed_model"], design["plan"]
    epoch_tdb_s = number(packet["epoch_tdb_s"], "export epoch")
    mass_kg = number(packet["mass_kg"], "export mass")
    marker_m = number(plan["marker_radius_m"], "lunar marker radius")
    need(epoch_tdb_s.hex() == packet["epoch_binary64_hex"], "pinned epoch word")
    need(mass_kg > 0 and mass_kg.hex() == packet["mass_binary64_hex"], "pinned coast mass word")
    need(marker_m == 18_374_000 and live["marker_m"] == marker_m, "pinned lunar marker radius")
    need([fixed[k] for k in ("id", "geometry", "thrust_n", "mass_flow_kg_s")] ==
         [MODEL, f"SI, SSB, J2000, {TIME}, NONE", 0, 0], "pinned model B geometry or thrust")
    need(live["model"] == "B" and plan["horizon_s"] == live["duration_s"] == 16_000, "pinned model B duration")
    for label, value in (("design stop epoch", plan["stop_tdb_s"]), ("R5.51 stop epoch", live["stop_tdb_s"])):
        same_word(value, epoch_tdb_s, label)
    same_word(design["restart"]["epoch_tdb_s"], live["restart_tdb_s"], "R5.51 start epoch")
    need(epoch_tdb_s-number(live["restart_tdb_s"], "R5.51 start epoch") == 16_000, "R5.51 interval")
    cutoff, cutoff_mass_kg = paired_cutoff(inputs)
    for label, value in (("design coast mass", design["restart"]["mass_kg"]), ("R5.51 coast mass", live["mass_kg"]),
                         ("nominal cutoff mass", cutoff_mass_kg)):
        same_word(value, mass_kg, label)

    expected = ("node", "native_start", "native_raw", "native_guard", "native_guard", "native_guard",
                "native_sample", "direction", "direction")
    need(tuple(k for k, _ in selected) == expected, "terminal record sequence")
    node, start, raw, sun, moon, earth, sample, mesh, common = (row for _, row in selected)
    need(node["index"] == 320 and node["elapsed_s"] == 16_000, "terminal common node")
    same_word(node["hi_tdb_s"], epoch_tdb_s, "terminal common epoch")
    need(start["name"] == "tighter" and start["step_s"] == 0.5, "tight native profile")
    same_word(start["coast_mass_kg"], mass_kg, "native cutoff mass")
    inventory = start["inventory"]
    framed(inventory, "native inventory")
    need([inventory[k] for k in ("model", "aberration", "force_order", "force_counts")] ==
         ["B", "NONE", ["total", *BODIES], dict.fromkeys(BODIES, 1)], "native model B force inventory")
    gm, exclusion = fixed["gm_m3_s2"], fixed["exclusion_radii_m"]
    need(set(gm) == set(exclusion) == set(inventory["gm_m3_s2"]) == set(BODIES), "native three-body inventory")
    for body in BODIES:
        ref_mu = number(gm[body], f"{body} pinned GM")
        native_mu = number(inventory["gm_m3_s2"][body], f"{body} native GM")
        need(ref_mu > 0 and abs(native_mu-ref_mu) <= 1e-15*ref_mu, f"{body} native GM")

    state = vector(raw["state"], 6, "raw terminal state")
    state_hex = words(state)
    for row, name_key, name, index, field in (
        (raw, "name", "tighter", 32_000, "state"),
        (sample, "name", "tighter", 320, "state"),
        (mesh, "grid", "mesh_tighter", 32_000, "spacecraft_si"),
        (common, "grid", "rk4_tighter", 320, "spacecraft_si"),
    ):
        need((row[name_key], row["index"]) == (name, index), f"terminal selector {name}:{index}")
        same_word(row["epoch_tdb_s"], epoch_tdb_s, "terminal epoch")
        need(words(vector(row[field], 6, f"terminal {name}:{index}")) == state_hex, "terminal state words differ")
        check()

    common_bodies: dict[str, Vector] = {}
    guards: dict[str, Vector] = {}
    need(set(node["bodies"]) == set(BODIES), "terminal common body inventory")
    for body, row in zip(BODIES, (sun, moon, earth), strict=True):
        need((row["name"], row["group"], row["body"]) == ("tighter", 32_001, body)
             and row["passed"] is True, "ordered terminal guard group")
        same_word(row["epoch_tdb_s"], epoch_tdb_s, f"{body} guard epoch")
        guards[body] = vector(row["state_si"], 6, f"{body} guard state")
        distance_m = math.dist(state[:3], guards[body][:3])
        need(math.isfinite(distance_m) and distance_m > number(exclusion[body], "exclusion radius") > 0,
             f"{body} exterior guard")
        same_word(row["distance_m"], distance_m, f"{body} guard distance")
        item = node["bodies"][body]
        need((item["body"], item["observer"], item["frame"], item["aberration"]) ==
             (body, "SSB", "J2000", "NONE"), f"{body} common source labels")
        same_word(item["epoch_tdb_s"], epoch_tdb_s, f"{body} common source epoch")
        common_bodies[body] = vector(item["state_si"], 6, f"{body} common state")
        check()

    directions = {}
    for kind, saved, moon_state in (
        ("mesh", mesh, guards["Moon"]), ("common", common, common_bodies["Moon"]),
    ):
        need(words(vector(saved["moon_si"], 6, f"{kind} audited Moon")) == words(moon_state),
             f"{kind} audited Moon words differ")
        directions[kind] = direction(state, moon_state, marker_m, saved)
        check()
    need(all(directions["mesh"][key] == directions["common"][key] for key in ("range_sign", "radial_sign")),
         "independent archived direction signs disagree")
    return {**packet, "candidate_id": pins["candidate_id"], "force_model_id": MODEL,
            "state_si": state, "state_binary64_hex": state_hex, "cutoff_tdb_s": cutoff["epoch_tdb_s"],
            "direction": directions}


def ideal(pins: Row, inputs: dict[str, Row], check: Check) -> Row:
    original, study, audit = inputs[R1], inputs[R2], inputs[R2_AUDIT]
    r1 = original["runs"][0]
    digest = pins["input_sha256"]
    candidate = pins["candidate_id"]
    need(r1["selected"]["candidate_id"] == candidate == inputs[DESIGN]["candidate"], "reference candidate")
    need(original["provenance"]["transfer_model"]["identifier"] == IDEAL_MODEL, "ideal reference model")
    need(study["original"] == r1 and study["reference_sha256"] == digest[R1] and study["status"] == "passed"
         and study["contract"] == "ADR0127", "independent ideal reference binding")
    need(study["frame"] == FRAME and study["units"] ==
         {"position_units": "m", "velocity_units": "m/s", "time": TIME}, "ideal reference frame and units")
    need(audit["evidence_sha256"] == digest[R2] and audit["result"] == {
        "audit": "passed", "study_status": "passed", "arithmetic_nodes_checked": 121,
        "reference_coast_verified": True,
    } and audit["native_calls"] == 0, "ideal reference audit receipt")
    saved, tested = r1["states"], study["points"]
    p = pins["ideal_inventory"]
    need(len(saved) == len(tested) == p["node_count"] == 121, "expected 121 audited ideal epochs")
    start, stop = vector(p["r551_extent_tdb_s"], 2, "pinned R5.51 interval")
    same_word(inputs[LIVE]["restart_tdb_s"], start, "inventory start epoch")
    same_word(inputs[LIVE]["stop_tdb_s"], stop, "inventory stop epoch")
    epochs = []
    for i, (a, b) in enumerate(zip(saved, tested, strict=True)):
        need(a["body"] == "Spacecraft" and b["index"] == i and b["status"] == "passed", "ideal node identity")
        cartesian(a, f"R1 state {i}")
        same_word(a["epoch_tdb_s"], b["epoch_tdb_s"], f"ideal coeval epoch {i}")
        t = number(b["epoch_tdb_s"], "ideal epoch")
        need(not epochs or epochs[-1] < t, "ideal epoch ordering")
        epochs.append(t)
        check()
    need(p["bounding_indices"] == [0, 1] and epochs[0] < start < stop < epochs[1],
         "frozen ideal epoch gap does not contain R5.51")
    need(words(epochs[:2]) == words(vector(p["bounding_epochs_tdb_s"], 2, "ideal gap labels")),
         "pinned ideal gap words")
    return {"model": IDEAL_MODEL, "node_count": len(epochs), "exact_coepochs": 0,
            "terminal_coepoch_count": 0, "bounding_indices": [0, 1], "bounding_epochs_tdb_s": epochs[:2],
            "r551_extent_tdb_s": [start, stop], "eligible": False,
            "reasons": ["no-exact-coepoch", "force-model-mismatch", "coast-mass-unavailable"]}


def physical(pins: Row, inputs: dict[str, Row], source: Row, check: Check) -> Row:
    r1 = inputs[R1]
    core = {f: inputs[f]["science"] for f in (NOMINAL, CENTRAL, OLD_COAST, STEP_STUDY)}
    endpoints = inputs[ENDPOINTS]
    baseline = core[CENTRAL]["runs"][0]["run"]
    cutoff, mass_kg = paired_cutoff(inputs)
    for f, entry in core.items():
        framed(entry, f)
        need(entry["time_scale"] == TIME and entry["units"] == "SI", f"{f}: incorrect units or time")
        need(entry["scenario"] == r1["normalized_scenario"], f"{f}: scenario drift")
        if f == NOMINAL:
            need(entry["candidate_id"] == pins["candidate_id"], f"{f}: candidate drift")
        else:
            need(entry["candidate"] == r1["runs"][0]["selected"] and
                 entry["reference_sha256"] == pins["input_sha256"][NOMINAL], f"{f}: reference binding")
    need(core[STEP_STUDY]["step_baseline_sha256"] == pins["input_sha256"][OLD_COAST],
         "maximum-step study baseline binding")
    need(endpoints["status"] == "passed" and endpoints["contract"] == "ADR0135"
         and endpoints["frames"]["absolute"] == "SSB/J2000" and endpoints["units"] ==
         {"position": "m", "velocity": "m/s", "gm": "m^3/s^2", "epoch": TIME}
         and endpoints["input_sha256"] ==
         {name: pins["input_sha256"][name] for name in (R1, CENTRAL)}, "R4 endpoints audit binding")
    endpoint_rows = [row["stored_endpoint"] for row in endpoints["rows"]]
    need(endpoint_rows == [baseline["boundaries"][0], baseline["target_state"]], "R4 baseline target binding")
    model = core[NOMINAL]["force_model_id"]
    need(isinstance(model, str) and model and model != source["force_model_id"], "historical full-model identifier")
    inputs_by_name: dict[str, list[Row]] = {f: [] for f in (*core, ENDPOINTS)}

    def add(name: str, value: Row, event: str, mass: object = None) -> None:
        t = number(value["epoch_tdb_s"], f"{name}: epoch")
        cartesian(value, name)
        m = None if mass is None else number(mass, f"{name}: mass")
        need(m is None or m > 0, f"{name}: positive mass")
        coepoch = t.hex() == source["epoch_binary64_hex"]
        # The retained full-model/target reports have no designated independent receiving record.
        reasons = [] if coepoch else ["no-exact-coepoch"]
        if event != "departure-cutoff":
            reasons.append("not-coast-entry")
        elif t.hex() == word(cutoff["epoch_tdb_s"], "historical cutoff epoch"):
            reasons.append("shared-cutoff-ancestry")
        reasons.extend(("force-model-mismatch", "not-independent"))
        if m is None:
            reasons.append("coast-mass-unavailable")
        elif m.hex() != source["mass_binary64_hex"]:
            reasons.append("coast-mass-mismatch")
        inputs_by_name[name].append({"record_event": event, "epoch_tdb_s": t, "mass_kg": m,
                                     "exact_coepoch": coepoch, "eligible": False, "reasons": reasons})
        check()

    for name, runs in (
        (NOMINAL, [core[NOMINAL][key] for key in ("nominal", "tighter")]),
        (CENTRAL, [r["run"] for r in core[CENTRAL]["runs"]]),
    ):
        for run in runs:
            for row, mass in zip(run["boundaries"], run["boundary_masses_kg"], strict=True):
                add(name, row, row["label"], mass)
            target = run["target_state"]
            need(target["label"] == "arrival-cutoff", f"{name}: target label")
            add(name, target, "arrival-cutoff-target")
    for name in (OLD_COAST, STEP_STUDY):
        obj = core[name]
        initial = obj["initial"]
        need(initial["label"] == cutoff["label"] and
             words(cartesian(initial, name)) == words(cartesian(cutoff, "cutoff")), f"{name} cutoff state")
        same_word(initial["epoch_tdb_s"], cutoff["epoch_tdb_s"], f"{name} cutoff epoch")
        same_word(obj["initial_mass_kg"], mass_kg, f"{name} cutoff mass")
        add(name, initial, "departure-cutoff", obj["initial_mass_kg"])
        for profile in obj["profiles"]:
            state = vector(profile["endpoint"], 7, f"{name}: retained arrival ignition")
            add(name, dict(FRAME, epoch_tdb_s=obj["end_epoch_tdb_s"], position_m=state[:3], velocity_m_s=state[3:6]),
                "arrival-ignition", state[6])
    for i, row in enumerate(endpoint_rows):
        add(ENDPOINTS, row, ("configured-departure-ignition", "arrival-cutoff-target")[i])

    inventory = pins["physical_reference_inventory"]
    need(set(inventory) == set(inputs_by_name), "frozen physical reference inventory")
    results = {}
    for name, records in inputs_by_name.items():
        dates = sorted({r["epoch_tdb_s"] for r in records})
        pinned_dates = inventory[name]["distinct_epochs_tdb_s"]
        need(words(dates) == words(vector(pinned_dates, len(dates), name)), f"{name}: pinned epoch inventory differs")
        results[name] = {"force_model_id": None if name == ENDPOINTS else model, **FRAME, "time_scale": TIME,
                         "units": ["m", "m/s", "kg"], "eligible": False, "records": records}
    return results


def inspect(pins: Row, inputs: dict[str, Row], selected: list[tuple[str, Row]], check: Check) -> Row:
    """Return separately scoped verdicts for the outgoing packet and receiving data."""
    source = outgoing(pins, inputs, selected, check)
    r1_r2 = ideal(pins, inputs, check)
    boundaries = physical(pins, inputs, source, check)
    return {"source_status": "source-state-authenticated",
            "ideal_status": "ideal-reference-coepoch-unavailable",
            "physical_status": "physical-join-not-established",
            "continuity_residuals": dict.fromkeys(("epoch_s", "position_m", "velocity_m_s", "mass_kg")),
            "outgoing": source, "receiving": {"ideal": r1_r2, "physical": boundaries}}
