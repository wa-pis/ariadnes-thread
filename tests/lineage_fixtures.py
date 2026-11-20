"""Manually fabricate saved observations without evaluating a scientific helper."""

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/adr/experiments"
SCOPE = "artificial-saved-lineage"
CANDIDATE = "artificial-saved-lineage-case"
REFERENCE = sha256(b"manually fabricated saved-lineage reference").hexdigest()
ROLES = ("attempt", "report", "receipt", "completion", "audit", "manifest", "selection_contract")
STAGES = ("bounds", "_ellipse", "_reverse", "_unit", "_cross", "_norm2", "_mass_exclusion", "_clearance", "_binary64")
SELECTION = (
    dict(row_index=62, lo_deg="150", hi_deg="4801/32", midpoint_deg="9601/64"),
    dict(row_index=94, lo_deg="151", hi_deg="4833/32", midpoint_deg="9665/64"),
    dict(row_index=125, lo_deg="4863/32", hi_deg="152", midpoint_deg="9727/64"),
)
SCALARS = {
    "_ellipse": "anomaly mu peri e sin_i cos_i sin_o cos_o sin_u cos_u sin_nu cos_nu a p h radius u t return[2]",
    "_reverse": "mu radius linear constant discriminant_sq disc root",
    "_norm2": "return",
    "_mass_exclusion": "departure arrival init coast final rate durations[0] durations[1] observed_duration_binary64[0] observed_duration_binary64[1]",
    "_clearance": "mu surface radius radial minimum return[0] return[1] return[2]",
    "bounds": "anomaly mu speed", "_cross": "", "_unit": "", "_binary64": "",
}
VECTORS = {
    "_ellipse": "node normal onto_plane radial_hat transverse_hat return[0] return[1]",
    "_reverse": "r given v_inf r_hat direction normal signed_h e_inf return",
    "_norm2": "v", "_unit": "v return", "_cross": "a b return",
    "_clearance": "r v r_hat", "bounds": "r orbital future", "_mass_exclusion": "", "_binary64": "",
}
CHILDREN = {
    "_ellipse": ("_cross", "_cross"), "_unit": ("_norm2",), "_cross": (), "_norm2": (), "_binary64": (),
    "_reverse": ("_unit", "_unit", "_cross", "_norm2", "_norm2", "_cross", "_norm2", "_norm2", "_unit", "_cross", "_cross", "_norm2"),
    "_mass_exclusion": ("_binary64", "_binary64"), "_clearance": ("_norm2", "_unit"),
}
type Row = dict[str, Any]


def wire(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(value: Any) -> str:
    return sha256(wire(value)).hexdigest()


def contract() -> Row:
    """Read only the design metadata, never retained observation operands."""
    return json.loads((ART / "0229-saved-lineage-contract.json").read_bytes())


def source_pins(design: Row) -> dict[str, str]:
    return {role: sha256((ROOT / path).read_bytes()).hexdigest()
            for role, path in design["source_bindings"].items()}


def _endpoint(seed: int) -> str:
    integer = str(seed)
    tail = ("123456789012345678901234567890" * 4)[:96 - len(integer)]
    return integer + "." + tail


def _box(seed: int, *, width: int = 1, exponent: int | None = None) -> Row:
    if exponent is not None:
        tail = ("1234567890" * 10)[:95]
        return dict(lo="1." + tail + f"E{exponent:+d}", hi="2." + tail + f"E{exponent:+d}")
    return dict(lo=_endpoint(seed), hi=_endpoint(seed + width))


def _fields(stage: str, seed: int, *, domain: str) -> Row:
    names = SCALARS[stage].split() + [f"{name}[{i}]" for name in VECTORS[stage].split() for i in range(3)]
    result = {name: _box(seed + i * 3, width=2 if domain == "cell" else 1)
              for i, name in enumerate(names)}
    if stage == "_ellipse" and domain == "singleton":
        result["radius"]["hi"] = result["radius"]["lo"]
    if stage == "_reverse":
        result["discriminant_sq"] = _box(seed, exponent=120)
        result["disc"] = _box(seed, exponent=-90)
    return result


def _flatten(value: Any, prefix: str = "return") -> Row:
    if type(value) is dict:
        return {key: part for name, item in value.items() for key, part in _flatten(item, prefix + "." + name).items()}
    if type(value) is list:
        return {key: part for i, item in enumerate(value) for key, part in _flatten(item, prefix + f"[{i}]").items()}
    return {prefix: value}


def reseal(trace: Row) -> None:
    content = {key: value for key, value in trace.items() if key != "seal"}
    trace["seal"] = sha256(json.dumps(content, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _trace(spec: Row, domain: str, sign: str, independent: bool, *, early: str | None) -> Row:
    lo, hi = (spec["lo_deg"], spec["hi_deg"]) if domain == "cell" else (spec["midpoint_deg"],) * 2
    seed = 1000 + spec["row_index"] * 10 + (100 if sign == "negative" else 0)
    fields = {stage: _fields(stage, seed + i * 200, domain=domain) for i, stage in enumerate(STAGES)}
    ellipse, reverse, bound, mass = (fields[name] for name in ("_ellipse", "_reverse", "bounds", "_mass_exclusion"))
    anomaly = deepcopy(ellipse["anomaly"])
    for i in range(3):
        reverse[f"r[{i}]"] = deepcopy(ellipse[f"return[0][{i}]"])
        bound[f"r[{i}]"] = deepcopy(ellipse[f"return[0][{i}]"])
        bound[f"orbital[{i}]"] = deepcopy(ellipse[f"return[1][{i}]"])
        bound[f"future[{i}]"] = deepcopy(reverse[f"return[{i}]"])
    reverse["mu"] = deepcopy(ellipse["return[2]"])
    bound["mu"] = deepcopy(ellipse["return[2]"])
    bound["anomaly"] = deepcopy(anomaly)
    mass["arrival"] = deepcopy(bound["speed"])
    reason = "mass" if sign == "negative" or early == "mass-exit" else None
    result = dict(reason=reason, arrival_speed_bounds_m_s=[bound["speed"]["lo"], bound["speed"]["hi"]])
    if early == "before-reverse":
        result = dict(reason=None, detail="fabricated failure before reverse")
    events: list[Row] = []
    next_call = 0

    def add(stage: str, parent: int | None, *, parent_stage: str | None = None, ordinal: int = 0) -> None:
        nonlocal next_call
        call = next_call
        next_call += 1
        returned = deepcopy(fields[stage])
        start: Row = {}
        scalars: Row = dict(independent=independent)
        if stage == "bounds":
            scalars |= dict(lo=lo, hi=hi, sign=sign)
        elif stage == "_ellipse":
            start["anomaly"] = deepcopy(anomaly)
        elif stage == "_reverse":
            start = {key: deepcopy(value) for key, value in reverse.items() if key == "mu" or key.startswith("r[")}
            scalars["sign"] = sign
        elif stage == "_mass_exclusion":
            start = {key: deepcopy(mass[key]) for key in ("departure", "arrival")}
        elif stage == "_norm2":
            start = {f"v[{i}]": deepcopy(returned[f"v[{i}]"]) for i in range(3)}
            if parent_stage == "_reverse" and ordinal == 1:
                start = {f"v[{i}]": deepcopy(reverse[f"r[{i}]"]) for i in range(3)}
                if independent:
                    returned["return"] = _box(seed + 7010, width=2)
            elif parent_stage == "_reverse" and ordinal == 4 and independent:
                start["v[0]"] = _box(seed + 7020)
            returned.update(deepcopy(start))
        events.append(dict(index=len(events), call=call, parent=parent, stage=stage, event="call", fields=start, scalars=deepcopy(scalars)))
        children = CHILDREN.get(stage, ())
        if stage == "bounds":
            children = ("_ellipse",) if early == "before-reverse" else ("_ellipse", "_reverse", "_norm2", "_mass_exclusion") + (() if reason == "mass" else ("_clearance",))
        if stage == "_ellipse" and early == "before-reverse":
            children = ()
        child_ordinals: Counter[str] = Counter()
        for child in children:
            child_ordinal = child_ordinals[child]
            child_ordinals[child] += 1
            add(child, call, parent_stage=stage, ordinal=child_ordinal)
        kind = "error" if stage == "_ellipse" and early == "before-reverse" else "return"
        if kind == "error":
            returned = deepcopy(start)
        if stage == "bounds":
            if early == "before-reverse":
                returned = dict(anomaly=deepcopy(anomaly))
            scalars |= _flatten(result)
        events.append(dict(index=len(events), call=call, parent=parent, stage=stage, event=kind, fields=returned, scalars=scalars))

    add("bounds", None)
    stages = {}
    for stage in STAGES:
        counts = {name: sum(event["stage"] == stage and event["event"] == kind for event in events)
                  for name, kind in (("calls", "call"), ("returns", "return"), ("errors", "error"))}
        stages[stage] = counts | dict(status="error" if counts["errors"] else "complete" if counts["returns"] else "not-reached")
    trace = dict(lo=lo, hi=hi, sign=sign, independent=independent, events=events, stages=stages,
                 status="early-failure" if early == "before-reverse" else "complete", result=result)
    reseal(trace)
    return trace


def fabricated_archive(*, early: str | None = None) -> Row:
    """Create a complete declared matrix from saved-looking records, not formulas."""
    assert early in (None, "before-reverse", "mass-exit")
    design = contract()
    sources = source_pins(design)
    head = dict(scope=SCOPE, candidate_id=CANDIDATE, reference_sha256=REFERENCE,
                invocation_id="a" * 32, method_sha256=sources,
                contract_sha256=design["inherited_contract_sha256"], stage="R5.59n")
    rows = []
    for spec in SELECTION:
        for domain in ("cell", "singleton"):
            for sign in ("positive", "negative"):
                for independent in (False, True):
                    trace = _trace(spec, domain, sign, independent, early=early)
                    rows.append(dict(row_index=spec["row_index"], domain=domain, sign=sign, independent=independent,
                                     lo_deg=trace["lo"], hi_deg=trace["hi"], trace=trace, control=deepcopy(trace["result"]),
                                     containment=dict(status="verified", containment_checks=16)))
    events = sum(len(row["trace"]["events"]) for row in rows)
    proof = dict(status="observations-verified-attribution-unresolved", rows=24, event_count=events)
    attempt = head | dict(wall_ns=30_000_000_000)
    report = head | dict(status=proof["status"], rows=rows, attempt_sha256=digest(attempt),
                         work=dict(bounds=48, points=0, oracle_mass=12, events=events),
                         fixture_semantics=("Every endpoint and event in this archive is manually fabricated for parser and lineage qualification. "
                                            "No interval, norm, root, orbit, mass, scientific helper or retained observation was evaluated to create it. "
                                            "The descriptor catalog mirrors saved numeric snapshots and their distinct source origins; equal numbers "
                                            "do not establish an alias or a physical relationship. Historical counters are fixture metadata only."))
    # Mirror the complete saved endpoint descriptor volume, including primitive
    # snapshots. These are source pointers, never aliases inferred from equality.
    report["saved_endpoint_descriptors"] = [
        dict(pointer=f"/report/rows/{row_index}/trace/events/{event['index']}/fields/{field}",
             stage=event["stage"], field=field, endpoint_kind="saved-canonical-interval",
             lo=value["lo"], hi=value["hi"])
        for row_index, row in enumerate(rows) for event in row["trace"]["events"]
        for field, value in event["fields"].items()
    ]
    receipt = head | dict(attempt_sha256=digest(attempt), report_sha256=digest(report), elapsed_ns=1_000_000)
    completion = dict(receipt_sha256=digest(receipt), proof=proof, invocation_id=head["invocation_id"], elapsed_ns=2_000_000)
    audit = dict(scope=SCOPE, completion_sha256=digest(completion), proof=proof,
                 work=dict(bounds=0, points=0, events=0, oracle_mass=6), invocation_id="b" * 32, elapsed_ns=3_000_000)
    archive = dict(attempt=attempt, report=report, receipt=receipt, completion=completion, audit=audit,
                   manifest={}, selection_contract=dict(scope=SCOPE, reference_sha256=REFERENCE, selection=list(SELECTION)))
    rechain(archive)
    archive["_context"] = dict(scope=SCOPE, source_pins=sources, expected_events=events,
                               context_assumption=design["context_provenance"], context_justified=True)
    return archive


def rechain(archive: Row) -> None:
    """Refresh fabricated byte chains after an intentional test mutation."""
    archive["report"]["attempt_sha256"] = digest(archive["attempt"])
    archive["receipt"]["attempt_sha256"] = digest(archive["attempt"])
    archive["receipt"]["report_sha256"] = digest(archive["report"])
    archive["completion"]["receipt_sha256"] = digest(archive["receipt"])
    archive["audit"]["completion_sha256"] = digest(archive["completion"])
    archive["manifest"] = dict(scope=SCOPE, artifact_sha256={role: dict(sha256=digest(archive[role]), bytes=len(wire(archive[role])))
                                                           for role in ROLES[:5]})


def write_artificial_pack(folder: Path, *, early: str | None = None) -> Row:
    """Write seven exclusive artificial records; source files are only hashed as bytes."""
    archive = fabricated_archive(early=early)
    folder.mkdir()
    inputs, pins = {}, {}
    for role in ROLES:
        path = folder / (role + ".json")
        raw = wire(archive[role])
        path.write_bytes(raw)
        inputs[role] = str(path.absolute())
        pins[role] = dict(sha256=sha256(raw).hexdigest(), bytes=len(raw))
    return dict(scope=SCOPE, inputs=inputs, pins=pins,
                expected_events=archive["_context"]["expected_events"], reference_sha256=REFERENCE,
                candidate_id=CANDIDATE, completion_sha256=pins["completion"]["sha256"])
