"""Fabricate four bound input records without replaying a historical study."""

from collections import Counter
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

type Row = dict[str, Any]
type Methods = dict[str, ModuleType]
type Source = tuple[Path, dict[str, str]]

ARTIFACTS = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
NAMES = ("attempt.json", "report.json", "receipt.json", "audit.json")
PINS = {
    "io": ("0206-readiness-runner.py", "ff1cd800a74f40f3bc91f74550c4b49205713f391d436e37360e92a9740c1a1e"),
    "core": ("0208-seed-worksheet.py", "4907db44f0ef53cb657cd563a6fa27df8a138442807c703a66c1343bde4788ba"),
    "oracle": ("0208-seed-oracle.py", "cf4041c69e5204f79ab6786be5e393c0dbc0977317e693587eb1a85e8265e475"),
    "reader": ("0210-retained-readback.py", "a6e1b9a32f0c46c9e03974c1367a8b04d2849eca86d807907a3bcefa1f0e8920"),
    "orbit": ("0213-phase-orbit.py", "ba78ca47097703cb27ed7dca8d844b9be34c61b1fee9a5668fae97db039979c3"),
    "screen": ("0213-phase-screen.py", "39d59baecb394f759ef6a775ce6cca548e4828dbfef94207b47c9e048d1d0f2b"),
    "archive": ("0220-phase-archive.py", "43c4c3b7fe1f82324a4833ea74a22aaed9922e8c0f9ea67fa0aa76161062dcf8"),
    "anchors": ("0220-phase-anchors.py", "7fadcb3fc9de4a43aa1ce80efd30d2e6499f76ee4918519cf8783d50bca2057e"),
}


def wire(row: Row) -> bytes:
    return (json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def load_methods() -> Methods:
    """Load authenticated pure helpers and the new point adapter, never old dispatch."""
    methods: Methods = {}
    sources = PINS | {"points": ("0241-phase-points.py", None)}
    for key, (filename, expected) in sources.items():
        path = ARTIFACTS / filename
        raw = path.read_bytes()
        if expected is not None and sha256(raw).hexdigest() != expected:
            raise ValueError(f"artificial fixture method pin: {key}")
        module = ModuleType("_bounded_fixture_" + key)
        module.__file__ = str(path)
        sys.modules[module.__name__] = module
        exec(compile(raw, str(path), "exec"), vars(module))
        methods[key] = module
    return methods


def synthetic_reference(methods: Methods, case: str = "refusal") -> Row:
    """Construct only artificial operands and the one fixed lunar root."""
    profiles = {
        "witness": (5349.349022787791, 224.83586408220995),
        "refusal": (7600., 224.83586408220995),
        "full-volume": (7600., 224.83586408220995),
        "transition": (7600., 97.),
    }
    speed, heading_deg = profiles[case]
    core, oracle, orbit, archive = (methods[key] for key in ("core", "oracle", "orbit", "archive"))
    epochs = (1073741952., 1073766952., 1073791952.)
    moon_r = (1611331.3351188295, 1100538.7023694925, 1467384.9364926568)
    moon_v = (-1064.628656781664, 561.1515742680841, 748.2020990241123)
    moon_excess = (-751.9908311490719, 1466.2085741254025, 1954.9447655005367)
    moon = dict(body="Moon", label="departure-ignition", gm_m3_s2=4_902_800_121_846.8,
                guard_m=1_744_010., shape_radius_m=1_737_400., body_ssb_si=[0.] * 6,
                relative_si=[str(Decimal(x)) for x in (*moon_r, *moon_v)],
                endpoint_ssb_si=[*moon_r, *moon_v], v_infinity_m_s=moon_excess)
    _, lunar = core.audited_roots(moon, moon_excess, oracle, arrival=False)
    mu, shape, radius = 42_828_375_815_756.1, 3_389_500., 3_689_500.
    # A fabricated tiny body keeps both signs available without changing the orbit.
    guard = 3_396_190.
    if case == "full-volume":
        shape = guard = 1.
    inc, node = math.acos(12 / 13), math.atan2(.8, .6)
    body = (149_300_000_000., 15_200_000_000., -1_500_000_000., -3400., 23_900., 1100.)
    relative = orbit._local_state(mu, radius, 0., inc, node, 0., 0.)
    p, q = (.6, .8, 0.), (-48 / 65, 36 / 65, 5 / 13)
    n = core.cross(p, q)
    heading, tilt = math.radians(heading_deg), math.radians(4.)
    excess = tuple(speed * (math.cos(tilt) * (math.cos(heading) * a + math.sin(heading) * b)
                           + math.sin(tilt) * c) for a, b, c in zip(p, q, n, strict=True))
    mars = dict(body="Mars", label="arrival-cutoff", gm_m3_s2=mu, guard_m=guard,
                shape_radius_m=shape, body_ssb_si=body,
                relative_si=[str(Decimal(x)) for x in relative],
                endpoint_ssb_si=tuple(a + b for a, b in zip(relative, body, strict=True)),
                v_infinity_m_s=excess,
                orbit=dict(central_body="Mars", periapsis_altitude_m=radius - shape,
                           apoapsis_altitude_m=radius - shape, eccentricity=0.,
                           inclination_rad=inc, raan_rad=node,
                           argument_of_periapsis_rad=0., true_anomaly_rad=0.))
    for endpoint, epoch in zip((moon, mars), epochs[::2], strict=True):
        endpoint.update(epoch_word=epoch.hex(), epoch_tdb_s=epoch)
    normalized = dict(schema="ariadna-r559c-normalized-input-v1", status="archive-inputs-validated",
                      scope="artificial", candidate_id="artificial-moon-mars", model_id=archive.MODEL,
                      command_words=None, live_authorized=False, origin="SSB", orientation="J2000",
                      units="SI", time_scale="TDB seconds since J2000", epochs_tdb_s=epochs,
                      epoch_words=[value.hex() for value in epochs], endpoints=[moon, mars],
                      spacecraft=dict(archive.SPACECRAFT), rejected_command_words=[])
    reference = dict(normalized=normalized, lunar=lunar["positive"],
                     zero_branches={"positive": {"reason": None}, "negative": {"reason": "guard"}},
                     zero_pairs=[dict(roots=["positive", "positive"], reason="commanded-dry-floor")])
    return json.loads(wire(reference))


def artificial_records(methods: Methods, case: str = "refusal") -> dict[str, Row]:
    """Compute three anchor phases; fabricate every other saved inventory row."""
    archive = methods["archive"]
    reference = synthetic_reference(methods, case)
    anchors = {}
    for degree in (150, 151, 152):
        point = methods["points"].point(reference, float(degree), methods)
        if point["eligible"] or point["unresolved"]:
            raise ValueError("artificial saved anchors must remain resolved refusals")
        row = deepcopy(point) | {"index": degree}
        for pair in row["pairs"]:
            if pair["reason"] != "commanded-dry-floor":
                raise ValueError("artificial saved anchor changed its pair refusal")
            pair["index"] = degree
        anchors[degree] = row
    rows = []
    for index in range(360):
        # These 357 rows bind historical inventory shape, not evaluated conics.
        row = dict(index=index, angle_word=(math.tau * index / 360).hex(),
                   branches={"positive": {"reason": None}, "negative": {"reason": "guard"}},
                   pairs=[dict(index=index, roots=["positive", "positive"], reason="commanded-dry-floor",
                               total_delta_v_m_s=1., oracle_total_delta_v_m_s="1")],
                   fabricated_inventory_only=True)
        rows.append(anchors.get(index, row))
    pairs = [pair for row in rows for pair in row["pairs"]]
    work = dict(phase_positions=360, mars_roots=720, pairs=len(pairs))
    upstream = {name: sha256(("0241 fabricated upstream " + name).encode()).hexdigest()
                for name in archive.UPSTREAM_PINS}
    method_pins = {key: pin for key, (_, pin) in PINS.items()}
    identity = archive.FLAGS | dict(schema="ariadna-r559f-phase-evidence-v1", stage="R5.59f",
                                   mode="artificial", synthetic=True, r559f_attempts=0,
                                   source_pins=upstream, source_sha256=method_pins, run_id="a" * 32)
    attempt = identity | {"wall_ns": archive.WALL_NS}
    attempt_sha = sha256(wire(attempt)).hexdigest()
    report = identity | dict(status=archive.REFUSAL, reason="no-eligible-pair", command_words=None,
                             selected=None, attempt_sha256=attempt_sha, source_bytes=1,
                             archive_open_attempts=list(upstream), reference=reference, rows=rows, work=work)
    receipt = identity | dict(status=archive.REFUSAL, attempt_sha256=attempt_sha,
                              report_sha256=sha256(wire(report)).hexdigest(), elapsed_before_receipt_ns=1)
    records = dict(zip(NAMES[:3], (attempt, report, receipt), strict=True))
    record_pins = {name: sha256(wire(row)).hexdigest() for name, row in records.items()}
    least = min(pairs, key=lambda pair: pair["total_delta_v_m_s"])
    least_fields = {key: least[key] for key in archive.PAIR_FIELDS}
    audit = archive.FLAGS | dict(
        schema="ariadna-r559f-saved-grid-audit-v1", saved_grid_verified=True,
        original_invocation_completed=False, original_new_completion_witness=False,
        source_pins=record_pins, evidence_bytes=sum(len(wire(row)) for row in records.values()),
        archive_reopens=0, new_r559f_attempts=0, new_phase_scans=0, new_conic_solves=0,
        wall_ns=archive.WALL_NS, original_elapsed_before_receipt_ns=1, elapsed_ns=1,
        candidate_id="artificial-moon-mars", work=work, source_bytes=1, source_sha256=method_pins,
        status=archive.REFUSAL, reason="no-eligible-pair", commands=None, state_checks=360, adapter_uses=0,
        branch_decisions={sign: Counter(row["branches"][sign]["reason"] or "passes" for row in rows)
                          for sign in archive.SIGNS},
        pair_decisions={"commanded-dry-floor": len(pairs)}, least_recorded_pair=least_fields,
        least_independent_pair=least_fields, zero_phase_delta_v_m_s=rows[0]["pairs"][0]["total_delta_v_m_s"],
    )
    return records | {"audit.json": audit}


def source_artificial_archive(root: Path, case: str = "refusal", *, methods: Methods | None = None) -> Source:
    """Write fresh canonical four-record artificial inputs and validate their binding."""
    loaded = load_methods() if methods is None else methods
    records = artificial_records(loaded, case)
    root.mkdir()
    pins = {}
    for name, row in records.items():
        raw = ((json.dumps(row, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
               if name == "audit.json" else wire(row))
        (root / name).write_bytes(raw)
        pins[name] = sha256(raw).hexdigest()
    loaded["archive"].bind({name: (row, pins[name]) for name, row in records.items()},
                            loaded["io"], retained=False)
    return root, pins
