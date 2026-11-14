"""Synthetic command/boundary tests and a metadata-only check of the frozen archives."""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from decimal import Decimal, localcontext
from hashlib import sha256
from pathlib import Path
import runpy
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
A = runpy.run_path(str(ROOT / "docs/adr/experiments/0189-post-cutoff-inputs.py"))
type Row = dict[str, Any]


def samples() -> tuple[Row, Row, Row, Row]:
    start = 1000000000.125
    duration = 32.500000001
    cutoff = start+duration
    initial_mass, dry_mass, thrust, isp = 100.0, 60.0, 35.0, 240.0
    with localcontext() as ctx:
        ctx.prec = 80
        dt = Decimal.from_float(cutoff)-Decimal.from_float(start)
        consumed = Decimal(35)*dt/(Decimal("9.80665")*Decimal(240))
        predicted = Decimal(100)-consumed
        final_mass = float(predicted)
        recorded = {"g0_m_s2": "9.80665", "dry_mass_kg": dry_mass, "requested_duration_s": duration,
                    "represented_duration_s": str(dt), "predicted_mass_kg": str(predicted),
                    "predicted_minus_stored_mass_kg": str(predicted-Decimal.from_float(final_mass)),
                    "limit_kg": "1e-8"}
    states = [{"label": name, "origin": "SSB", "orientation": "J2000", "epoch_tdb_s": t,
               "position_m": [1.0, 2.0, 3.0], "velocity_m_s": [0.0, -0.0, 6.0]}
              for name, t in (("departure-ignition", start), ("departure-cutoff", cutoff))]
    burn = {"burn_id": "departure", "direction_frame": "Moon-relative TNW", "direction_tnw": [1., 0., 0.],
            "thrust_n": thrust, "isp_s": isp, "initial_mass_kg": initial_mass, "final_mass_kg": final_mass,
            "start_epoch_tdb_s": start, "end_epoch_tdb_s": cutoff}
    run = {"profile": "nominal", "outcome": "completed", "boundaries": states,
           "boundary_masses_kg": [initial_mass, final_mass], "burns": [burn]}
    selected = {"candidate_id": "d0001-t0035", "departure_epoch_tdb_s": start}
    scenario = {"spacecraft": {"dry_mass_kg": dry_mass, "initial_mass_kg": initial_mass,
                               "max_thrust_n": thrust, "isp_s": isp}}
    common = {"research_only": True, "time_scale": "TDB seconds since J2000", "units": "SI",
              "orientation": "J2000", "origin": "SSB", "scenario": scenario}
    forces = "simulated-full-force-fixture"
    diff = {"label": "departure-cutoff", "position_difference_m": .02, "velocity_difference_m_s": 0.,
            "mass_difference_kg": 0.}
    original = {"science": {**common, "nominal": run, "candidate_id": selected["candidate_id"],
                            "force_model_id": forces, "provenance": {"candidate": selected},
                            "seed_commands": {"departure_duration_s": duration}, "numerical_agreement": False,
                            "integration_differences": [{}, diff]}}
    repeat = {"science": {**common, "runs": [{"role": "baseline", "run": run}], "candidate": selected}}
    candidate = {"runs": [{"selected": selected}], "normalized_scenario": scenario}
    offsets = list(range(0, 601, 50))
    coast = {"model_id": "r5-ssb-sun-moon-earth-point-v1", "sources": ["Sun", "Moon", "Earth"],
             "geometry": "SI, SSB, J2000, TDB seconds since J2000, NONE", "duration_s": 600,
             "offsets_s": offsets, "coepochs_tdb_s": [cutoff+s for s in offsets],
             "constant_mass_metadata_kg": final_mass, "thrust_n": 0, "mass_flow_kg_s": 0}
    design = {"stage": "R5.41", "contract": "ADR0188", "candidate": selected["candidate_id"],
              "historical_baseline_target_closed": False, "boundary_original_force_model_id": forces,
              "boundary_state": states[1], "boundary_mass_kg": final_mass, "stored_burn": burn,
              "mass_arithmetic": recorded, "history_boundary_profile_differences": diff,
              "cutoff_binary64_hex": {
                  "epoch_tdb_s": cutoff.hex(), "position_m": ["0x1.0000000000000p+0",
                      "0x1.0000000000000p+1", "0x1.8000000000000p+1"],
                  "velocity_m_s": ["0x0.0p+0","-0x0.0p+0","0x1.8000000000000p+2"],
                  "mass_kg": final_mass.hex(),
              },
              "coast": coast}
    return tuple(deepcopy(v) for v in (design, original, repeat, candidate))


def test_selects_saved_cutoff_and_represented_time() -> None:
    design, original, repeat, candidate = samples()
    bundle = A["bind_cutoff"](design, original, repeat, candidate)
    t = float.fromhex(design["cutoff_binary64_hex"]["epoch_tdb_s"])
    assert bundle["initial"]["epoch_tdb_s"] == t
    assert bundle["initial"]["velocity_m_s"][1].hex() == "-0x0.0p+0"
    assert bundle["mass_kg"] == bundle["burn"]["final_mass_kg"] == bundle["coast"]["constant_mass_metadata_kg"]
    assert bundle["mass_arithmetic"]["represented_duration_s"] != str(
        bundle["mass_arithmetic"]["requested_duration_s"])
    assert bundle["coast"]["coepochs_tdb_s"][-1] == t+600
    assert "b_prefix" not in bundle


@pytest.mark.parametrize(("where", "value", "message"), [
    (("baseline", "velocity_m_s"), [0., 0., 6.], "cutoff replay"),
    (("baseline", "epoch_tdb_s"), 1000000032.625001, "cutoff replay"),
    (("design", "label"), "departure-ignition", "frozen position"),
    (("design", "origin"), "Moon", "frozen position"),
    (("design", "epoch_tdb_s"), 1000000032.625001, "frozen position"),
    (("burn", "isp_s"), 239., "event/mass linkage"),
    (("arithmetic", "represented_duration_s"), "32.500000001", "documented mass arithmetic"),
    (("coast", "constant_mass_metadata_kg"), 61., "coast contract"),
    (("coast", "mass_flow_kg_s"), 1, "coast contract"),
])
def test_rejects_semantic_drift_despite_finite_shapes(
    where: tuple[str, str], value: Any, message: str,
) -> None:
    design, original, repeat, candidate = samples()
    name, key = where
    targets = {"baseline": repeat["science"]["runs"][0]["run"]["boundaries"][1],
               "design": design["boundary_state"], "burn": design["stored_burn"],
               "arithmetic": design["mass_arithmetic"], "coast": design["coast"]}
    targets[name][key] = value
    with pytest.raises(ValueError, match=message):
        A["bind_cutoff"](design, original, repeat, candidate)


def test_rejects_consistent_but_physically_wrong_cutoff_mass() -> None:
    design, original, repeat, candidate = samples()
    wrong = 98.0
    design["boundary_mass_kg"] = design["stored_burn"]["final_mass_kg"] = wrong
    design["cutoff_binary64_hex"]["mass_kg"] = wrong.hex()
    for run in (original["science"]["nominal"], repeat["science"]["runs"][0]["run"]):
        run["boundary_masses_kg"][1] = run["burns"][0]["final_mass_kg"] = wrong
    with pytest.raises(ValueError, match="violates burn law"):
        A["bind_cutoff"](design, original, repeat, candidate)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e500}', b'[]'])
def test_strict_json_rejects_duplicate_nonfinite_and_nonobject(raw: bytes) -> None:
    with pytest.raises(ValueError):
        A["parse"](raw)


def test_read_rejects_changed_hash_and_checkout_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "fixture.json"
    data = b'{}'
    target.write_bytes(data)
    sha = sha256(data).hexdigest()
    assert A["read"](root, target.name, sha) == data
    target.write_bytes(b'{"changed":true}')
    with pytest.raises(ValueError, match="input SHA256"):
        A["read"](root, target.name, sha)
    outside = tmp_path / "outside.json"
    outside.write_bytes(data)
    (root / "linked.json").symlink_to(outside)
    with pytest.raises(ValueError, match="outside checkout"):
        A["read"](root, "linked.json", sha)


def test_archive_read_checks_inherited_profiles_and_guard_metadata_only() -> None:
    native = {"space_nav", "tudatpy", "spiceypy", "scipy", "numpy"}

    def imported() -> set[str]:
        return {n for n in sys.modules if n.partition(".")[0] in native}

    before = imported()
    calls = 0

    def check() -> None:
        nonlocal calls
        calls += 1

    loader: Callable[[Path, Callable[[], None]], Row] = A["load"]
    bundle = loader(ROOT, check)
    assert bundle["initial"]["epoch_tdb_s"] == float.fromhex("0x1.d2d2a15fb54adp+29")
    assert bundle["cutoff"]["label"] == "departure-cutoff"
    assert bundle["mass_kg"] == 1351.7475727997967
    assert bundle["burn"]["end_epoch_tdb_s"] == bundle["coast"]["coepochs_tdb_s"][0]
    assert bundle["coast"]["coepochs_tdb_s"][-1] == 978998915.9635216
    assert bundle["coast"]["native_steps_s"] == [1, .5]
    assert bundle["coast"]["dop853_settings"][1]["max_step"] == 2.5
    assert bundle["kernel_manifest"]["loaded_kernel_count"] == 13
    assert bundle["b_archive_sha256"] == "45ccd5b6470992770c17c8285a9f4697077ac6505f4e6582498b7455f4fcc2b5"
    assert calls > 44 and "b_prefix" not in bundle and imported() == before

    design = A["parse"]((ROOT / A["DESIGN"]).read_bytes())
    template = bundle["source_rows_template"]
    stale = deepcopy(design["retained_record_metadata"])
    boundary = bundle["coast"]["coepochs_tdb_s"]
    stale[1]["record_interval_tdb_s"][1] = boundary[-1]
    with pytest.raises(ValueError, match="does not cover"):
        A["_coverage"](stale, template, boundary)
    with pytest.raises(ValueError, match="unique pinned"):
        A["_coverage"]([*stale, stale[0]], template, boundary)
