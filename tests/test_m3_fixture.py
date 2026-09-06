from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tomllib

from space_nav.scenario import load_scenario
from space_nav.transfer import search_impulsive_transfers


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "examples" / "reference_mission.toml"
PROVISIONAL = ROOT / "examples" / "m3_feasible_mission.toml"


def test_provisional_fixture_changes_only_dry_mass() -> None:
    reference_raw = tomllib.loads(REFERENCE.read_text(encoding="utf-8"))
    provisional_raw = tomllib.loads(PROVISIONAL.read_text(encoding="utf-8"))
    assert reference_raw["spacecraft"]["dry_mass_kg"] == 1000.0
    assert provisional_raw["spacecraft"]["dry_mass_kg"] == 500.0
    provisional_raw["spacecraft"]["dry_mass_kg"] = 1000.0
    assert provisional_raw == reference_raw

    reference = load_scenario(REFERENCE)
    provisional = load_scenario(PROVISIONAL)
    assert provisional == replace(
        reference,
        spacecraft=replace(reference.spacecraft, dry_mass_kg=500.0),
    )


def test_provisional_fixture_changes_budget_flag_not_candidate_physics() -> None:
    reference = search_impulsive_transfers(load_scenario(REFERENCE))
    provisional = search_impulsive_transfers(load_scenario(PROVISIONAL))
    reference_candidate = next(
        candidate for candidate in reference.pareto_front
        if candidate.candidate_id == "d0001-t0035"
    )
    provisional_candidate = next(
        candidate for candidate in provisional.pareto_front
        if candidate.candidate_id == "d0001-t0035"
    )

    # Exact equality covers every epoch, vector, delta-v, and ideal mass.
    # This tests the M2 budget filter, not finite-burn convergence.
    assert reference_candidate.mass_feasible is False
    assert provisional_candidate.mass_feasible is True
    assert provisional_candidate == replace(
        reference_candidate, mass_feasible=True,
    )
    assert 500.0 <= provisional_candidate.final_mass_kg < 1000.0
