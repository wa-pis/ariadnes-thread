"""Artificial ADR0199 inputs, with optional full selected-member volume."""

from __future__ import annotations

from base64 import b64encode
from copy import deepcopy
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
from random import Random
from typing import Any

type Row = dict[str, Any]

HERE = Path(__file__).resolve().parent
TIME = "TDB seconds since J2000"
FRAME = {"origin": "SSB", "orientation": "J2000"}
LABELS = {**FRAME, "time_scale": TIME, "units": "SI"}
CANDIDATE = "d0001-t0035"
START, STOP, MASS = 900_000_000.0, 900_016_000.0, 1234.5
REF, REF_AUDIT = "0129-reference-coast.json", "0129-reference-coast-audit.json"
R1 = "0119-m2-reference.json"
BASELINE, CORRECTION = "0079-research-reference.json", "0098-central-correction-study.json"
COAST, STEPS = "0082-identical-start-coast.json", "0083-coast-step-study.json"
BOUNDARY = "0136-retained-boundary-audit.json"
DESIGN, VERIFIED = "0196-design-inputs.json", "0198-verification.json"
BODIES = ("Sun", "Moon", "Earth")
BODY_STATES = {
    "Sun": [0.0] * 6,
    "Moon": [1e11, -2e10, 3e9, 1000.0, 0.0, 0.0],
    "Earth": [1e11, -2.1e10, 3e9, 1000.0, 0.0, 0.0],
}
STATE = [100_020_000_000.0, -2e10, 3e9, 2000.0, 0.0, 0.0]
GM = dict(zip(BODIES, (1e20, 4e12, 4e14), strict=True))
RADII = dict(zip(BODIES, (6e8, 1.7e6, 6e6), strict=True))
MODEL = "r5-ssb-sun-moon-earth-point-v1"
VARIANTS = {"valid", "state", "epoch", "mass", "metric", "receiver", "ideal", "signed-zero", "moon-words"}


def _wire(value: object) -> bytes:
    return (json.dumps(value, allow_nan=False, separators=(",", ":")) + "\n").encode()


def _write(path: Path, value: Row) -> str:
    raw = _wire(value)
    with path.open("xb") as stream:
        stream.write(raw)
    return sha256(raw).hexdigest()


def _state(epoch: float, **extra: object) -> Row:
    return {
        **FRAME, "epoch_tdb_s": epoch, "epoch_utc": "fixture-only",
        "position_m": STATE[:3], "velocity_m_s": STATE[3:], **extra,
    }


def _compact_inputs(directory: Path, pins: Row, variant: str) -> None:
    digests = pins["input_sha256"]

    def save(name: str, value: Row) -> None:
        digests[name] = _write(directory / name, value)

    depart, cutoff, arrival, final = START - 4000, START - 650, START + 1_000_000, START + 1_001_000
    candidate = {
        "candidate_id": CANDIDATE, "departure_epoch_tdb_s": depart, "arrival_epoch_tdb_s": final,
        "departure_epoch_utc": "fixture-only", "arrival_epoch_utc": "fixture-only",
        "flight_time_s": final - depart,
    }
    scenario = {"synthetic": True}
    epochs = [depart + k * (final - depart) / 120 for k in range(121)]
    # This adversarial fixture hashes an on-epoch ideal sample; it cannot qualify a physical join.
    if variant == "ideal":
        epochs[2] = STOP
        epochs[1] = START - 100.0
    else:
        epochs[1] = STOP + 10_000.0
        epochs[2] = STOP + 20_000.0
    epochs[3] = STOP + 30_000.0
    for k in range(4, 121):
        epochs[k] = epochs[3] + (final - epochs[3]) * (k - 3) / 117
    states = [_state(t, body="Spacecraft") for t in epochs]
    ideal = {
        "selected": candidate, "states": states, "number": 1,
        "provenance": {"transfer_model": {"identifier": "sun-centered-zero-revolution-patched-conic-v1"}},
    }
    save(R1, {
        "status": "passed", "contract": "ADR 0118", "normalized_scenario": scenario, "runs": [ideal],
        "provenance": ideal["provenance"],
    })
    save(REF, {
        "contract": "ADR0127", "reference_sha256": digests[R1], "status": "passed", "frame": FRAME,
        "units": {"time": TIME, "position_units": "m", "velocity_units": "m/s"},
        "original": ideal, "points": [
            {"index": i, "status": "passed", "epoch_tdb_s": t} for i, t in enumerate(epochs)
        ],
    })
    save(REF_AUDIT, {
        "evidence_sha256": digests[REF], "native_calls": 0,
        "result": {
            "audit": "passed", "study_status": "passed", "arithmetic_nodes_checked": 121,
            "reference_coast_verified": True,
        },
    })
    pins["ideal_inventory"]["bounding_epochs_tdb_s"] = epochs[:2]

    coast_entry = _state(cutoff, label="departure-cutoff")
    target = _state(final, label="arrival-cutoff")
    nominal = {
        "boundaries": [
            _state(depart, label="departure-ignition"), coast_entry, _state(arrival, label="arrival-ignition"),
            _state(final, label="arrival-cutoff"),
        ],
        "boundary_masses_kg": [2000.0, MASS, MASS, 850.0],
        "target_state": target,
    }
    tighter = deepcopy(nominal)
    if variant == "receiver":
        # Same epoch but an arrival target (neither achieved nor using the model B contract).
        tighter["target_state"] = _state(STOP, label="arrival-cutoff")
    save(BASELINE, {"science": {
        **LABELS, "candidate_id": CANDIDATE, "scenario": scenario, "nominal": nominal, "tighter": tighter,
        "force_model_id": "ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-cannonball-srp-schwarzschild-direct-spice-v2",
        "research_only": True, "outcome": "targeting-failed",
    }})
    trial = deepcopy(nominal)
    trial["boundaries"][1] = _state(cutoff - 600, label="departure-cutoff")
    trial["boundaries"][2] = _state(arrival + 64, label="arrival-ignition")
    save(CORRECTION, {"science": {
        **LABELS, "candidate": candidate, "scenario": scenario, "reference_sha256": digests[BASELINE],
        "runs": [{"role": "baseline", "run": nominal}, {"role": "central-trial", "run": trial}],
    }})
    common = {
        **LABELS, "candidate": candidate, "scenario": scenario, "reference_sha256": digests[BASELINE],
        "initial": coast_entry, "initial_mass_kg": MASS, "end_epoch_tdb_s": arrival,
    }
    sample = {"endpoint": [*STATE, MASS]}
    save(COAST, {"science": {
        **common, "profiles": [{**sample, "profile": label} for label in ("nominal", "tighter")],
    }})
    save(STEPS, {"science": {
        **common, "step_baseline_sha256": digests[COAST], "profiles": [
            {**sample, "profile": f"step-{i}", "saved_mesh": {"epoch_sequence_sha256": "a" * 64}}
            for i in (21600, 10800, 5400)
        ],
    }})
    save(BOUNDARY, {
        "status": "passed", "contract": "ADR0135", "record": "R4.3", "native_imports_or_calls": 0,
        "spacecraft_propagations": 0,
        "units": {"position": "m", "velocity": "m/s", "gm": "m^3/s^2", "epoch": TIME},
        "frames": {"relative": "body-relative J2000", "absolute": "SSB/J2000"},
        "input_sha256": {n: digests[n] for n in (R1, CORRECTION)},
        "rows": [{"stored_endpoint": nominal["boundaries"][0]}, {"stored_endpoint": target}],
    })
    save(DESIGN, {
        "stage": "R5.49", "contract": "ADR0196", "candidate": CANDIDATE,
        "restart": {"epoch_tdb_s": START, "mass_kg": MASS, "mass_binary64_hex": MASS.hex()},
        "plan": {"stop_tdb_s": STOP, "horizon_s": 16_000, "marker_radius_m": 18_374_000},
        "fixed_model": {
            "id": MODEL, "geometry": "SI, SSB, J2000, TDB seconds since J2000, NONE",
            "gm_m3_s2": GM, "exclusion_radii_m": RADII, "thrust_n": 0, "mass_flow_kg_s": 0,
        },
    })
    times = {
        BASELINE: [depart, cutoff, arrival, final, *([STOP] if variant == "receiver" else [])],
        CORRECTION: [depart, cutoff - 600, cutoff, arrival, arrival + 64, final],
        COAST: [cutoff, arrival], STEPS: [cutoff, arrival], BOUNDARY: [depart, final],
    }
    for name, values in times.items():
        pins["physical_reference_inventory"][name]["distinct_epochs_tdb_s"] = sorted(values)


def _operands(variant: str) -> list[list[tuple[str, Row]]]:
    source = {
        "body": "Moon", "observer": "SSB", "frame": "J2000", "aberration": "NONE", "epoch_tdb_s": STOP,
    }
    bodies = {name: {**source, "body": name, "state_si": vec} for name, vec in BODY_STATES.items()}
    native_start = {
        "name": "tighter", "step_s": 0.5, "coast_mass_kg": MASS,
        "inventory": {
            "model": "B", **FRAME, "aberration": "NONE", "force_order": ["total", *BODIES],
            "force_counts": dict.fromkeys(BODIES, 1), "gm_m3_s2": GM,
        },
    }
    raw = {"name": "tighter", "index": 32000, "epoch_tdb_s": STOP, "state": STATE.copy()}
    sample = {**raw, "index": 320, "state": STATE.copy()}
    guard = [
        ("native_guard", {
            "name": "tighter", "group": 32001, "body": name, "epoch_tdb_s": STOP, "state_si": vec,
            "distance_m": math.dist(STATE[:3], vec[:3]), "passed": True,
        })
        for name, vec in BODY_STATES.items()
    ]
    direction = {
        "grid": "mesh_tighter", "index": 32000, "edge": None, "epoch_tdb_s": STOP,
        "spacecraft_si": STATE.copy(), "moon_si": BODY_STATES["Moon"].copy(),
        "radius_m": 20_000_000.0, "radial_speed_m_s": 1000.0, "range_sign": 1, "radial_sign": 1,
        "decimal80_radius_m": "20000000", "decimal80_radial_speed_m_s": "1000",
    }
    common = deepcopy(direction) | {"grid": "rk4_tighter", "index": 320}
    if variant == "state":
        sample["state"][0] += 0.001
    if variant == "signed-zero":
        common["spacecraft_si"][-1] = -0.0
    if variant == "epoch":
        sample["epoch_tdb_s"] = math.nextafter(STOP, math.inf)
    if variant == "mass":
        native_start["coast_mass_kg"] = math.nextafter(MASS, math.inf)
    if variant == "metric":
        direction["radius_m"] += 1.0
    if variant == "moon-words":
        common["moon_si"][-1] = -0.0
    return [
        [("node", {"index": 320, "elapsed_s": 16_000.0, "hi_tdb_s": STOP, "bodies": bodies})],
        [("native_start", native_start)], [("native_raw", raw)],
        [*guard, ("native_sample", sample)], [("direction", direction), ("direction", common)],
    ]


def _member(
    output: Path, descriptor: Row, records: list[tuple[str, Row]], first: int, full: bool, rng: Random,
) -> Row:
    """Fill non-selected lines with distinct synthetic records at fixed volume."""
    selectors = deepcopy(descriptor["selectors"])
    for i, selector in enumerate(selectors):
        if not full:
            selector["row_in_member"] = i
    special = {s["row_in_member"]: _wire(record) for s, record in zip(selectors, records, strict=True)}
    count = descriptor["rows"] if full else len(special)
    if full:
        blanks = count - len(special)
        total_padding = 2**24 - sum(len(line) for line in special.values())
        size, remainder = divmod(total_padding, blanks)
        chunks: list[bytes] = []
        fill_index = 0
        for index in range(count):
            if index in special:
                chunks.append(special[index])
                continue
            prefix = b'["artificial_row",{"seq":%06d,"payload":"' % index
            tail = b'"}]\n'
            n = size + (fill_index < remainder) - len(prefix) - len(tail)
            entropy = n * 4330 // 10_000
            content = b64encode(rng.randbytes((3 * entropy + 3) // 4))[:entropy]
            chunks.append(prefix + content + b"a" * (n - entropy) + tail)
            fill_index += 1
        raw = b"".join(chunks)
        if len(raw) != 2**24:
            raise AssertionError("fixture raw volume")
    else:
        raw = b"".join(special.values())
    packed = gzip.compress(raw, compresslevel=1, mtime=0)
    header = {
        "first": first, "rows": count, "raw": len(raw), "gzip": len(packed),
        "raw_sha256": sha256(raw).hexdigest(), "gzip_sha256": sha256(packed).hexdigest(),
    }
    with output.open("xb") as stream:
        stream.write(_wire(header))
        stream.write(packed)
    return {**header, "selectors": selectors}


def _finalize(
    root: Path, phase: str, parts: list[Row], prepared: str, revision: str, context: Row,
) -> Row:
    identity = {"contract": "ADR0196", "phase": phase, "revision": revision, "pin_sha256": prepared, "mode": "capacity"}
    started = 20.0 if phase == "study" else 25.0
    totals = {key: sum(part[key] for part in parts) for key in ("raw", "gzip", "rows")}
    summary = {"study_binding": context, "scientific_verified": False, "capacity_only": True, "mode": "capacity"}
    manifest = _write(root / phase / "manifest.json", {
        "schema": "ADR0196/shards-v1", "binding": identity, "status": "passed", "parts": parts,
        "summary": summary, **totals,
    })
    hashes: dict[str, str] = {}
    receipts: dict[str, Row] = {}

    def write(name: str, value: Row) -> None:
        receipts[name] = value
        hashes[name] = _write(root / f"{phase}.{name}.json", value)

    parent_attempt = {"identity": identity, "started_s": started}
    write("parent_attempt", parent_attempt)
    attempt = {**parent_attempt, "parent_attempt_sha256": hashes["parent_attempt"]}
    write("attempt", attempt)
    child = {
        **attempt, "status": "passed", "gate": "passed", "attempt_sha256": hashes["attempt"],
        "manifest_sha256": manifest, "elapsed_s": 0.75, "peak_rss_bytes": 1,
    }
    write("receipt", child)
    parent = {
        **parent_attempt, "elapsed_s": 1.0, "checkout_frozen": True, "returncode": 0,
        "status": "passed", "gate": "passed", "parent_attempt_sha256": hashes["parent_attempt"],
        "attempt_sha256": hashes["attempt"], "child_receipt_sha256": hashes["receipt"],
        "manifest_sha256": manifest, "parent_peak_rss_bytes": 1, "child_peak_rss_bytes": 1, "error": None,
    }
    write("parent_receipt", parent)
    return {
        "finalized": {"manifest_sha256": manifest, "parent_receipt_sha256": hashes["parent_receipt"]},
        "receipt_sha256": hashes, "receipts": receipts, "finalization_error": None,
        "shard_archive": {
            "status": "passed", "readback_verified": True, "prefix_only": False, "manifest_sha256": manifest,
            "shard_count": len(parts), "raw_bytes": totals["raw"], "gzip_bytes": totals["gzip"],
            "rows": totals["rows"], "summary": summary,
        },
    }


def build(root: Path, *, full: bool = False, variant: str = "valid") -> Path:
    """Create a new self-contained synthetic fixture directory."""
    if variant not in VARIANTS:
        raise ValueError("unknown synthetic fixture variant")
    root = root.resolve()
    root.mkdir(exist_ok=True)
    inputs, archive = root / "inputs", root / "archive"
    inputs.mkdir()
    archive.mkdir()
    pins = json.loads((HERE / "0199-design-inputs.json").read_bytes())
    pins["synthetic"] = True
    pins["export_selector"].update(
        epoch_tdb_s=STOP, epoch_binary64_hex=STOP.hex(), mass_kg=MASS, mass_binary64_hex=MASS.hex(),
    )
    pins["ideal_inventory"]["r551_extent_tdb_s"] = [START, STOP]
    _compact_inputs(inputs, pins, variant)

    descriptors = pins["external_r551"]["selected_members"]
    rng = Random(552_553)
    phases: dict[str, Row] = {}
    parts: dict[str, list[Row]] = {"study": [], "audit": []}
    for phase in parts:
        (archive / phase).mkdir()

    for desc, records in zip(descriptors, _operands(variant), strict=True):
        phase = desc["phase"]
        members = parts[phase]
        index = len(members)
        name = f"{index:05d}.shard"
        first = sum(x["rows"] for x in members)
        row = _member(archive / phase / name, desc, records, first, full, rng)
        desc.update(member=name, manifest_index=index, **row)
        members.append({k: v for k, v in row.items() if k != "selectors"})

    revision, prepared = "65" * 20, "4f" * 32
    for phase, members in parts.items():
        binding = phases.get("study", {}).get("finalized", {})
        phases[phase] = _finalize(archive, phase, members, prepared, revision, binding)
    totals = {key: sum(desc[key] for desc in descriptors) for key in ("raw", "gzip", "rows")}
    pins["external_r551"].update(
        retention_root=str(archive), selected_member_totals=totals,
        finalization_sha256={key: row["finalized"] for key, row in phases.items()},
    )
    if totals["gzip"] > pins["future_audit_maxima"]["gzip_payload_bytes"]:
        raise AssertionError("synthetic workload exceeds gzip cap")
    report = {
        "stage": "R5.51", "contract": "ADR0196", "synthetic": True, "measured_revision": revision,
        "preparation_sha256": prepared, "design_sha256": pins["input_sha256"][DESIGN],
        "once_only_location": str(archive), "full_independent_audit_passed": True,
        "model": "B", "duration_s": 16_000, "restart_tdb_s": START, "stop_tdb_s": STOP, "mass_kg": MASS,
        "marker_m": 18_374_000, "numerical_status": "passed", "marker_status": "marker-bracketed", "phases": phases,
        "combined_verified_archive": {**totals, "shards": 5},
    }
    pins["input_sha256"][VERIFIED] = _write(inputs / VERIFIED, report)
    result = root / "pins.json"
    _write(result, pins)
    return result
