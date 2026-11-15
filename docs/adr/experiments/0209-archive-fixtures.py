"""Fabricate the six archive shapes from the unchanged R5.59b synthetic geometry."""

from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
from runpy import run_path
from typing import Any

type Files = dict[str, bytes]
type Row = dict[str, Any]
type Vector = tuple[float, float, float]

R1 = "0119-m2-reference.json"
R4 = "0098-central-correction-study.json"
AUDIT = "0136-retained-boundary-audit.json"
BASELINE = "0079-research-reference.json"
FRACTIONS = "0101-central-damping-study.json"
CONTRACT = "0205-design-fixed-command-physical-join.md"
MODEL = ("ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120"
         "-cannonball-srp-schwarzschild-direct-spice-v2")
TIME_SCALE = "TDB seconds since J2000"
SPACECRAFT = dict(initial_mass_kg=2000.0, dry_mass_kg=500.0, max_thrust_n=1000.0, isp_s=450.0,
                  srp_area_m2=20.0, reflectivity_coefficient=1.3, maneuver_magnitude_sigma_fraction=0.1,
                  maneuver_pointing_sigma_rad=0.01)
UTC_EPOCHS = ("2034-01-09T01:00:00.000000Z", "2034-01-09T14:53:20.000000Z")
CONTROL_ORDER = tuple(f"{prefix}_{quantity}" for prefix in ("departure", "arrival")
                      for quantity in ("azimuth_rad", "elevation_rad", "duration_s"))
BASE_CONTROLS = (0.15, -0.03, 1210.0, -0.25, 0.12, 1350.0)
CORRECTION_CONTROLS = (0.18, -0.04, 1290.0, -0.35, 0.16, 1390.0)
HALF_CONTROLS = (0.165, -0.035, 1250.0, -0.3, 0.14, 1370.0)
QUARTER_CONTROLS = (0.1575, -0.0325, 1230.0, -0.275, 0.13, 1360.0)


def _seed() -> Row:
    return run_path(str(Path(__file__).with_name("0208-seed-fixtures.py")))["build"]()


def profile_words() -> tuple[str, str, str]:
    a, b, c = _seed()["sections"]["contract"]["epochs_tdb_s"]
    return a.hex(), b.hex(), c.hex()


def _json(row: Row) -> bytes:
    return (json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def pins(files: Files) -> dict[str, str]:
    """Generate external fixture SHA-256 pins from exact bytes."""
    return {name: sha256(raw).hexdigest() for name, raw in files.items()}


def write(root: Path, files: Files) -> dict[str, Path]:
    """Write a fresh artificial archive next to the tests."""
    root.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, raw in files.items():
        path = root / name
        with path.open("xb") as handle:
            handle.write(raw)
        result[name] = path
    return result


def relink(files: Files) -> Files:
    """Rebind the synthetic archive graph for structural fault tests."""
    changed = dict(files)
    base_pin = sha256(files[BASELINE]).hexdigest()
    for name in (R4, FRACTIONS):
        record = json.loads(changed[name])
        study = record["science"]
        study["reference_sha256"] = study["expected_reference_sha256"] = base_pin
        if name == FRACTIONS:
            study["central_step_sha256"] = study["expected_central_step_sha256"] = sha256(changed[R4]).hexdigest()
        changed[name] = _json(record)
    audit = json.loads(changed[AUDIT])
    audit["input_sha256"] = {name: sha256(changed[name]).hexdigest() for name in (R1, R4)}
    changed[AUDIT] = _json(audit)
    lines = changed[CONTRACT].decode("utf-8").splitlines(keepends=True)
    for i, line in enumerate(lines):
        for name in (R1, R4, AUDIT):
            if line.startswith(f"| [{name}]("):
                lines[i] = f"| [{name}](experiments/{name}) | `{sha256(changed[name]).hexdigest()}` |\n"
    changed[CONTRACT] = "".join(lines).encode()
    return changed


def _cross(a: Vector, b: Vector) -> Vector:
    x, y, z = a
    u, v, w = b
    return y*w-z*v, z*u-x*w, x*v-y*u


def _orbit(body: str, shape_m: float, relative: list[str]) -> Row:
    x, y, z, u, v, w = map(float, relative)
    r, velocity = (x, y, z), (u, v, w)
    h_vec = _cross(r, velocity)
    h_norm = math.hypot(*h_vec)
    h_unit = tuple(s/h_norm for s in h_vec)
    node_angle = math.atan2(h_unit[0], -h_unit[1])
    node = (math.cos(node_angle), math.sin(node_angle), 0.0)
    q_hat = _cross(h_unit, node)
    anomaly = math.atan2(math.fsum(a*b for a,b in zip(q_hat,r,strict=True)),
                         math.fsum(a*b for a,b in zip(node,r,strict=True)))
    altitude_m = math.hypot(*r)-shape_m
    return dict(central_body=body, periapsis_altitude_m=altitude_m, apoapsis_altitude_m=altitude_m,
                eccentricity=0.0, inclination_rad=math.acos(h_unit[2]), raan_rad=node_angle % math.tau,
                argument_of_periapsis_rad=0.0, true_anomaly_rad=anomaly % math.tau)


def _state(epoch: float, utc: str, values: list[float]) -> Row:
    return dict(epoch_tdb_s=epoch, epoch_utc=utc, origin="SSB", orientation="J2000",
                position_m=values[:3], velocity_m_s=values[3:])


def _contract(epochs: list[float]) -> bytes:
    t0, tx, tf = epochs
    return f"""# 0205 — Artificial fixed-command contract fixture

- Scope: fabricated archive shape only, never a command source.

## Decision and rationale

### Inputs, events and declared mass

| Source | SHA-256 |
| --- | --- |
| [{R1}](experiments/{R1}) | `{'0'*64}` |
| [{R4}](experiments/{R4}) | `{'0'*64}` |
| [{AUDIT}](experiments/{AUDIT}) | `{'0'*64}` |
| [0204-record-the-ideal-mars-checkpoint.md](0204-record-the-ideal-mars-checkpoint.md) | `{'0'*64}` |

The notation below denotes TDB seconds since J2000; the state uses SI,
SSB origin and J2000 orientation.

| Event | Frozen origin and meaning |
| --- | --- |
| t0 = {t0} (`{t0.hex()}`) | 0098 `science.runs[0].run.boundaries[0]`, configured lunar orbit at departure ignition. |
| t1 | Departure cutoff, from t0 + departure duration under the frozen command and time convention. |
| t* = {tx} (`{tx.hex()}`) | R5.51 terminal epoch, comparison inside the coast; no thrust or phase change here. |
| t2 | Arrival ignition, from tf − arrival duration under the same convention. |
| tf = {tf} (`{tf.hex()}`) | 0098 `science.runs[0].run.target_state`, desired Mars orbit at arrival cutoff. |

Use the fixed 2,000 kg initial mass, 500 kg dry mass, 1,000 N maximum
thrust, 450 s Isp, 9.80665 m/s^2 g0, 20 m^2 radiation area and 1.3
reflectivity coefficient.

### Two endpoints in one force model

Bind the [production force and resource spec](../../openspec/changes/refine-physical-trajectory/specs/physical-trajectory-refinement/spec.md#requirement-declared-gravitational-dynamics):
`{MODEL}`.
""".encode()


def build() -> Files:
    """Fabricate files with the exact selector hierarchy but no retained science inputs."""
    sections = _seed()["sections"]
    epochs = sections["contract"]["epochs_tdb_s"]
    t0, _, tf = epochs
    scenario = dict(synthetic=True, spacecraft=SPACECRAFT.copy(), search={}, tracking={}, limits={})
    body_states, endpoints, audit_rows = [], [], []
    for i, (row, shape_m) in enumerate(zip(sections["audit"]["endpoints"], (1737400.0, 3389500.0), strict=True)):
        utc = UTC_EPOCHS[i]
        body = row["body"]
        label = ("departure-ignition", "arrival-cutoff")[i]
        state = _state(row["epoch_tdb_s"], utc, row["endpoint_ssb_si"]) | dict(label=label)
        body_state = _state(row["epoch_tdb_s"], utc, row["body_ssb_si"]) | dict(body=body)
        orbit = _orbit(body, shape_m, row["orbit_relative_si"])
        scenario[("departure_orbit", "target_orbit")[i]] = orbit
        endpoints.append(state)
        body_states.append(body_state)
        audit_rows.append(dict(body=body, stored_endpoint=state, stored_body=body_state, orbit=orbit,
                               gm_m3_s2=row["gm_m3_s2"], shape_radius_m=shape_m,
                               retained_relative_exact=row["relative_si"],
                               binary64_relative=list(map(float, row["orbit_relative_si"])),
                               decimal80_relative=row["orbit_relative_si"],
                               decimal100_relative=row["orbit_relative_si"],
                               oracle_convergence_norms=["0","0"], comparisons=[]))

    departure, arrival = sections["r1"]["excess_m_s"]
    candidate = dict(candidate_id="artificial-moon-mars", departure_epoch_utc=UTC_EPOCHS[0],
                     arrival_epoch_utc=UTC_EPOCHS[1], departure_epoch_tdb_s=t0, arrival_epoch_tdb_s=tf,
                     flight_time_s=tf-t0, departure_v_infinity_m_s=departure, arrival_v_infinity_m_s=arrival,
                     departure_delta_v_m_s=1234.0, arrival_delta_v_m_s=1357.0, total_delta_v_m_s=2591.0,
                     propellant_mass_kg=900.0, final_mass_kg=1100.0, mass_feasible=True)
    ideal_run = dict(selected=candidate, endpoints={
        name: dict(body_state=state, position_error_m=0.0, velocity_error_m_s=0.0)
        for name, state in zip(("departure", "arrival"), body_states, strict=True)
    })
    r1 = dict(reference_id="r1-m2-reserve-reference", status="passed", contract="ADR 0118", normalized_scenario=scenario,
              identical_scientific_payloads=True, runs=[dict(deepcopy(ideal_run), number=i) for i in (1, 2)])
    common = dict(scenario=scenario, origin="SSB", orientation="J2000", time_scale=TIME_SCALE,
                  units="SI", research_only=True)
    unselected = common | dict(outcome="not-improving", candidate=candidate, selected_alpha=None, numerical_agreement=None,
                               control_units=["rad","rad","s","rad","rad","s"], seed_controls=list(BASE_CONTROLS))

    def trial(role: str, controls: tuple[float, ...], alpha: float | None) -> Row:
        end = endpoints[1]
        return dict(role=role, alpha=alpha, controls=list(controls), reason=None,
                    run=dict(boundaries=[endpoints[0], {}, {}, {}], target_state=end))

    r4 = unselected | dict(runs=[trial("baseline", BASE_CONTROLS, None),
                                trial("central-trial", CORRECTION_CONTROLS, 1.0)])
    fractions = unselected | dict(runs=[trial("baseline", BASE_CONTROLS, None),
                                       trial("fraction-0.5", HALF_CONTROLS, 0.5),
                                       trial("fraction-0.25", QUARTER_CONTROLS, 0.25)])
    baseline = common | dict(candidate_id="artificial-moon-mars", force_model_id=MODEL, outcome="completed",
                             numerical_agreement=False, continuous_safety_verified=False,
                             seed_commands=dict(zip(CONTROL_ORDER, BASE_CONTROLS, strict=True)))
    audit = dict(record="ADR0136", contract="ADR0135", status="passed", finalization_gate="passed",
                 input_equality=True, native_imports_or_calls=0, spacecraft_propagations=0,
                 units=dict(position="m", velocity="m/s", gm="m^3/s^2", epoch=TIME_SCALE),
                 frames=dict(relative="body-relative J2000", absolute="SSB/J2000"),
                 rows=audit_rows)
    return relink({R1: _json(r1), R4: _json(dict(science=r4)), AUDIT: _json(audit),
                   BASELINE: _json(dict(science=baseline)), FRACTIONS: _json(dict(science=fractions)),
                   CONTRACT: _contract(epochs)})
