from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys
import time

import pytest

from space_nav.scenario import load_scenario


ROOT = Path(__file__).parents[1]
REFERENCE = ROOT / "examples" / "reference_mission.toml"
BASELINE = ROOT / "tests" / "data" / "reference_kernel_baseline.json"


def test_full_reference_plan_matches_pinned_scientific_baseline() -> None:
    pytest.importorskip("tudatpy")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    scenario = load_scenario(REFERENCE)

    started = time.monotonic()
    completed = subprocess.run(
        [sys.executable, "-m", "space_nav", "plan", str(REFERENCE), "--json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=scenario.limits.runtime_seconds + 10,
    )
    elapsed = time.monotonic() - started
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)

    assert payload["evaluated_candidates"] == 1980
    assert payload["solved_candidates"] == 1980
    assert payload["failed_candidates"] == 0
    assert payload["mass_feasible_candidates"] == 0
    assert payload["pareto_front"]
    assert all(not candidate["mass_feasible"] for candidate in payload["pareto_front"])
    minimum_delta_v = min(
        candidate["total_delta_v_m_s"] for candidate in payload["pareto_front"]
    )
    assert minimum_delta_v == pytest.approx(
        baseline["minimum_total_delta_v_m_s"], abs=0.01
    )
    assert elapsed <= scenario.limits.runtime_seconds

    model = payload["manifest"]["transfer_model"]
    assert model["identifier"] == "sun-centered-zero-revolution-patched-conic-v1"
    assert model["tudat_resources_version"] == baseline["tudat_resources_version"]
    assert model["grid"] == {
        "candidate_budget": 2000,
        "departure_count": 44,
        "flight_time_count": 45,
        "attempted_candidates": 1980,
    }
    assert model["reference_radii_m"] == {"Moon": 1_737_400.0, "Mars": 3_389_500.0}
    assert model["standard_gravity_m_s2"] == 9.80665
    assert model["solver"] == {
        "targeter": "ZeroRevolutionLambertTargeterIzzo",
        "revolutions": 0,
        "branch": "prograde",
        "tolerance": 1e-9,
        "maximum_iterations": 50,
    }
    assert model["gravitational_parameters"]["units"] == "m^3/s^2"
    assert model["gravitational_parameters"]["source"] == "SPICE"
    assert set(model["gravitational_parameters"]["values"]) == {
        "Sun",
        "Moon",
        "Mars",
    }
    assert all(
        math.isfinite(value) and value > 0.0
        for value in model["gravitational_parameters"]["values"].values()
    )
    assert "departure_orbit.inclination_deg" in model["ignored_scenario_fields"]
    assert "limits.random_seed" in model["ignored_scenario_fields"]

    spice = payload["manifest"]["spice"]
    actual_kernels = [
        {"name": item["name"], "sha256": item["sha256"]}
        for item in spice["kernels"]
    ]
    assert spice["kernel_source"] == baseline["kernel_source"]
    assert spice["loaded_kernel_count"] == baseline["loaded_kernel_count"]
    assert actual_kernels == baseline["kernels"], (
        "SPICE kernel baseline changed; review the scientific baseline before "
        "accepting new reference values"
    )

    json.dumps(payload, allow_nan=False, sort_keys=True)
    assert payload["manifest"]["scenario_sha256"]
    assert payload["manifest"]["versions"]["space_nav"] == "0.2.0"
    assert payload["manifest"]["versions"]["tudatpy"] == "1.0.0"
    assert payload["manifest"]["spice"]["kernel_list_status"] == "complete"
    assert payload["manifest"]["transfer_model"] == model
