"""Generate only artificial archives for the ADR0202 worksheet."""

from __future__ import annotations

from base64 import b64encode
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
from random import Random
import runpy
from typing import Any

type Row = dict[str, Any]

HERE = Path(__file__).resolve().parent
TIME = "TDB seconds since J2000"
FRAME = {"origin": "SSB", "orientation": "J2000"}
UNITS = {"time": TIME, "position_units": "m", "velocity_units": "m/s"}
CANDIDATE = "d0001-t0035"
IDEAL_MODEL = "sun-centered-zero-revolution-patched-conic-v1"
COAST_MODEL = "r5-ssb-sun-moon-earth-point-v1"
MU = 1.327124400420322e20
DEPART, RESTART, CHECK, FINAL = 900_000_000.0, 900_003_450.0, 900_019_450.0, 925_173_818.0
MASS = 1234.5
SEMIMAJOR, ECCENTRICITY, INITIAL_ANOMALY = 149_597_870_700.0, 0.2, 0.35
BASIS_P, BASIS_Q = (0.36, 0.48, 0.8), (-0.8, 0.6, 0.0)
MODEL_DELTA = (7125.0, -4225.0, 875.0, 27.5, -16.25, 0.75)
R1, R2, R2_AUDIT = "0119-m2-reference.json", "0129-reference-coast.json", "0129-reference-coast-audit.json"
DESIGN, R551, CERT = "0199-design-inputs.json", "0198-verification.json", "0201-verification.json"
VARIANTS = {"valid", "sun-request-epoch", "sun-return-epoch", "kernel-identity", "end-velocity", "state-label"}
KERNELS = {
    "kernel_source": "artificial inventory", "loaded_kernel_count": 13,
    "spiceypy_version": "fixture-only", "kernel_list_status": "available",
    "kernels": [{"path": f"artificial-{i:02}.bsp", "name": f"artificial-{i:02}.bsp", "type": "SPK",
                 "sha256": sha256(f"artificial kernel {i}".encode()).hexdigest()} for i in range(13)],
}


def _wire(value: object) -> bytes:
    return (json.dumps(value, allow_nan=False, separators=(",", ":")) + "\n").encode()


def _write(path: Path, value: Row) -> str:
    raw = _wire(value)
    with path.open("xb") as stream:
        stream.write(raw)
    return sha256(raw).hexdigest()


def _words(values: list[float]) -> list[str]:
    return [x.hex() for x in values]


def expected_relative(epoch: float) -> list[float]:
    """Generate a known ellipse from its declared geometry using Newton's method."""
    a, e = SEMIMAJOR, ECCENTRICITY
    n = math.sqrt(MU / a**3)
    mean = INITIAL_ANOMALY - e * math.sin(INITIAL_ANOMALY) + n * (epoch - DEPART)
    anomaly = mean
    for _ in range(12):
        anomaly -= (anomaly - e * math.sin(anomaly) - mean) / (1 - e * math.cos(anomaly))
    c, s = math.cos(anomaly), math.sin(anomaly)
    if abs(anomaly - e * s - mean) > 2e-15:
        raise AssertionError("artificial Newton root")
    beta = math.sqrt(1 - e * e)
    x, y = a * (c - e), a * beta * s
    speed = a * n / (1 - e * c)
    vx, vy = -speed * s, speed * beta * c
    return [x * p + y * q for p, q in zip(BASIS_P, BASIS_Q, strict=True)] + [
        vx * p + vy * q for p, q in zip(BASIS_P, BASIS_Q, strict=True)
    ]


def _sun(epoch: float) -> list[float]:
    speed = [3.5, -7.25, 4.5]
    return [p + v * (epoch - DEPART) for p, v in zip((4e8, -2e8, 1e8), speed, strict=True)] + speed


def _sum(a: list[float], b: list[float]) -> list[float]:
    return [x + y for x, y in zip(a, b, strict=True)]


def expected_ssb(epoch: float = CHECK) -> list[float]:
    """Analytic expectation used only by the artificial tests."""
    return _sum(expected_relative(epoch), _sun(epoch))


def _state(body: str, epoch: float, state: list[float]) -> Row:
    return {"body": body, "epoch_utc": "fixture-only", "epoch_tdb_s": epoch,
            **FRAME, "position_m": state[:3], "velocity_m_s": state[3:]}


def _r1_r2(inputs: Path, variant: str, full: bool) -> dict[str, str]:
    epochs = [DEPART + k * (FINAL - DEPART) / 120 for k in range(121)]
    states = [_state("Spacecraft", epoch, expected_ssb(epoch)) for epoch in epochs]
    s0, s120 = expected_ssb(DEPART), expected_ssb(FINAL)
    moon = s0[:3] + [12_345.0, -8_765.0, 4_321.0]
    mars = s120[:3] + [-17_350.0, 10_015.0, -8_860.0]
    relative, sun0 = expected_relative(DEPART), _sun(DEPART)
    excess = [relative[i] - (moon[i] - sun0[i]) for i in range(3, 6)]
    initial = [moon[i] - sun0[i] for i in range(3)] + [
        (moon[i] - sun0[i]) + excess[i - 3] for i in range(3, 6)
    ]
    if variant == "end-velocity":
        states[-1]["velocity_m_s"] = mars[3:]
    if variant == "state-label":
        states[-1]["body"] = "Mars"
    candidate = {
        "candidate_id": CANDIDATE, "departure_epoch_tdb_s": DEPART, "arrival_epoch_tdb_s": FINAL,
        "departure_epoch_utc": "fixture-only", "arrival_epoch_utc": "fixture-only",
        "flight_time_s": FINAL - DEPART, "departure_v_infinity_m_s": excess,
        "arrival_v_infinity_m_s": [x - y for x, y in zip(s120[3:], mars[3:], strict=True)],
    }
    model = {"identifier": IDEAL_MODEL, "gravitational_parameters": {
        "units": "m^3/s^2", "source": "SPICE", "values": {"Sun": MU},
    }}
    run = {
        "number": 1, "selected": candidate, "states": states, "provenance": {"transfer_model": model},
        "endpoints": {"departure": {"body_state": _state("Moon", DEPART, moon)},
                      "arrival": {"body_state": _state("Mars", FINAL, mars)}},
    }
    refs = {R1: _write(inputs / R1, {"status": "passed", "contract": "ADR 0118", "runs": [run]})}
    points = [{
        "index": k, "epoch_tdb_s": epoch, "elapsed_s": epoch - DEPART, "status": "passed",
        "sun_request": {**FRAME, "body": "Sun", "aberration_correction": "NONE", "epoch_tdb_s": epoch},
        "sun": _state("Sun", epoch, _sun(epoch)),
    } for k, epoch in enumerate(epochs)]
    identity = {"kernels": KERNELS}
    refs[R2] = _write(inputs / R2, {
        "comparison": "r2-reference-coast-v1", "oracle": "cartesian-ellipse-bisection-v1",
        "contract": "ADR0127", "status": "passed", "reference_sha256": refs[R1], "original": run,
        "frame": FRAME, "units": UNITS, "attempted_sun_calls": 121, "completed_sun_calls": 121,
        "native_spacecraft_propagations": 0, "points": points, "identity": identity, "final_identity": identity,
        "seed_operands": {"moon": moon, "sun0": sun0, "excess_m_s": excess}, "initial_state": initial,
    })
    audit = {
        "evidence_sha256": refs[R2], "native_calls": 0,
        "audit_source_sha256": "138d6c98b9f914dbcc7b26355e0e8c2019bece997f1d18b089a90b3cce095ad9",
        "result": {"audit": "passed", "study_status": "passed", "arithmetic_nodes_checked": 121,
                   "reference_coast_verified": True},
    }
    if full:
        audit["artificial_padding"] = "a" * (1_970_000 - sum((inputs / name).stat().st_size for name in refs))
    refs[R2_AUDIT] = _write(inputs / R2_AUDIT, audit)
    return refs


def _member(path: Path, full: bool, variant: str) -> Row:
    kernels = KERNELS
    if variant == "kernel-identity":
        kernels = {**kernels, "kernels": list(reversed(kernels["kernels"]))}
    request = {"body": "Sun", "observer": "SSB", "frame": "J2000", "aberration": "NONE", "epoch_tdb_s": CHECK}
    sun = _sun(CHECK)
    returned = {**request, "state_si": sun, "state_km_km_s": [v / 1000 for v in sun]}
    if variant == "sun-request-epoch":
        request["epoch_tdb_s"] = math.nextafter(CHECK, math.inf)
    if variant == "sun-return-epoch":
        returned["epoch_tdb_s"] = math.nextafter(CHECK, math.inf)
    selected = {
        16: _wire(("identity", {"when": "before", "value": {"kernels": kernels}})),
        337: _wire(("node", {"index": 320, "elapsed_s": 16000.0, "hi_tdb_s": CHECK, "lo_s": 0.0,
                             "requests": [request], "bodies": {"Sun": returned}})),
    }
    rng = Random(556_337)
    count = 42_862 if full else 338
    ordinary, extras = divmod(2**24 - sum(map(len, selected.values())), count - len(selected))
    rows = []
    fill_index = 0
    for i in range(count):
        if i in selected:
            rows.append(selected[i])
            continue
        prefix, tail = b'["artificial_row",{"seq":%06d,"payload":"' % i, b'"}]\n'
        size = ordinary + (fill_index < extras) - len(prefix) - len(tail) if full else 0
        entropy = size * 4330 // 10_000
        content = b64encode(rng.randbytes((3 * entropy + 3) // 4))[:entropy]
        rows.append(prefix + content + b"a" * (size - entropy) + tail)
        fill_index += 1
    raw = b"".join(rows)
    packed = gzip.compress(raw, compresslevel=1, mtime=0)
    if (full and len(raw) != 2**24) or len(packed) > 5 * 2**20:
        raise AssertionError(f"artificial member capacity: {len(raw)} raw / {len(packed)} gzip")
    head = {"first": 0, "rows": count, "raw": len(raw), "gzip": len(packed),
            "raw_sha256": sha256(raw).hexdigest(), "gzip_sha256": sha256(packed).hexdigest()}
    with path.open("xb") as stream:
        stream.write(_wire(head))
        stream.write(packed)
    return head


def _certificate(archive: Path, design: str, outgoing: Row) -> Row:
    started = 2.0
    attempt = {"stage": "R5.54", "mode": "retained", "inputs": {"pins_sha256": design},
               "wall_s": 15, "started_s": started}
    ahash = sha256(_wire(attempt)).hexdigest()
    verdict = {
        "status": "passed", "source_status": "source-state-authenticated",
        "ideal_status": "ideal-reference-coepoch-unavailable", "physical_status": "physical-join-not-established",
        "continuity_residuals": dict.fromkeys(("epoch_s", "position_m", "velocity_m_s", "mass_kg")),
        "receiving_records_total": 29,
    }
    report = {**verdict, "stage": "R5.54", "synthetic": False, "pins_sha256": design,
              "attempt_sha256": ahash, "outgoing": outgoing}
    receipt = {"stage": "R5.54", "status": "passed", "returncode": 0, "elapsed_s": 0.25,
               "pins_sha256": design, "attempt_sha256": ahash, "report_sha256": sha256(_wire(report)).hexdigest()}
    rows = {"attempt.json": attempt, "report.json": report, "receipt.json": receipt}
    wire = {name: _wire(value) for name, value in rows.items()}
    return {"stage": "R5.54", "contract": "ADR0199", "design_sha256": design, "launcher_returncode": 0,
            "once_only_location": str(archive), "result": verdict, "original_records": rows,
            "retained_file_checks": {k: {"bytes": len(v), "sha256": sha256(v).hexdigest()} for k, v in wire.items()}}


def build(root: Path, *, full: bool = False, variant: str = "valid") -> Path:
    """Write new fixture inputs with all synthetic contents bound by hash."""
    if variant not in VARIANTS:
        raise ValueError("unknown artificial fixture variant")
    root = root.resolve()
    root.mkdir(exist_ok=True)
    inputs, archive = root / "inputs", root / "archive"
    inputs.mkdir()
    for phase in ("study", "audit"):
        (archive / phase).mkdir(parents=True)
    refs = _r1_r2(inputs, variant, full)
    member = _member(archive / "study" / "00000.shard", full, variant)
    helpers = HERE / "0200-interface-fixtures.py"
    finalize = runpy.run_path(str(helpers))["_finalize"]
    revision, prepared = "65" * 20, "4f" * 32
    study = finalize(archive, "study", [member], prepared, revision, {})
    audit = finalize(archive, "audit", [], prepared, revision, study["finalized"])
    totals = {k: member[k] for k in ("raw", "gzip", "rows")}
    refs[R551] = _write(inputs / R551, {
        "stage": "R5.51", "contract": "ADR0196", "synthetic": True,
        "once_only_location": str(archive), "model": "B", "duration_s": 16_000,
        "measured_revision": revision, "preparation_sha256": prepared,
        "design_sha256": "d1" * 32, "restart_tdb_s": RESTART, "stop_tdb_s": CHECK,
        "mass_kg": MASS, "marker_m": 18_374_000, "phases": {"study": study, "audit": audit},
        "numerical_status": "passed", "marker_status": "marker-bracketed",
        "combined_verified_archive": {**totals, "shards": 1}, "full_independent_audit_passed": True,
    })
    selector = {"model": "B", "profile": "RK4 tighter", "selection": "final retained common node, not the radial event",
                "epoch_tdb_s": CHECK, "epoch_binary64_hex": CHECK.hex(), "mass_kg": MASS,
                "mass_binary64_hex": MASS.hex(), "mass_kind": "constant coast metadata", **FRAME,
                "time_scale": TIME, "units": ["m", "m/s", "kg"]}
    refs[DESIGN] = _write(inputs / DESIGN, {
        "stage": "R5.52", "contract": "ADR0199", "synthetic": True, "candidate_id": CANDIDATE,
        "base_revision": revision, "input_sha256": refs.copy(), "export_selector": selector,
        "ideal_inventory": {"node_count": 121, "bounding_indices": [0, 1],
                            "bounding_epochs_tdb_s": [DEPART, DEPART + (FINAL - DEPART) / 120],
                            "r551_extent_tdb_s": [RESTART, CHECK]},
        "external_r551": {
            "retention_root": str(archive), "selected_member_totals": totals,
            "finalization_sha256": {"study": study["finalized"], "audit": audit["finalized"]},
            "selected_members": [{**member, "phase": "study", "member": "00000.shard", "manifest_index": 0,
                                  "selectors": [{"row_in_member": 16, "kind": "identity", "keys": {"when": "before"}},
                                                {"row_in_member": 337, "kind": "node", "keys": {"index": 320}}]}],
        },
    })
    outgoing = [x - d for x, d in zip(expected_ssb(), MODEL_DELTA, strict=True)]
    refs[CERT] = _write(inputs / CERT, _certificate(archive, refs[DESIGN], {
        **selector, "candidate_id": CANDIDATE, "force_model_id": COAST_MODEL, "state_si": outgoing,
        "state_binary64_hex": _words(outgoing),
    }))
    pins = root / "pins.json"
    _write(pins, {"stage": "R5.56", "synthetic": True, "input_sha256": refs})
    if pins.stat().st_size + sum((inputs / name).stat().st_size for name in refs) > 2**21:
        raise AssertionError("artificial compact inputs exceed cap")
    return pins
