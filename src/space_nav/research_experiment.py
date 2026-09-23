"""Standalone D4 reference experiment; not the production refinement CLI.

Run once with ``python -m space_nav.research_experiment SCENARIO OUTPUT``.
An existing output is never overwritten. Failed research is retained as JSON.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from . import trajectory as physical
from .cli import _runtime_manifest
from .errors import EphemerisError, TrajectoryRefinementError, TransferSearchError
from .explorer import SCIENCE_LOCK
from .models import Scenario
from .research import ResearchProgress, ResearchReport, ResearchRun, _ResearchBudget
from .research_propagation import _compare_research_profiles
from .scenario import load_scenario
from .transfer import _search_impulsive_transfers


_CANDIDATE_ID = "d0001-t0035"


def _run_reference(scenario: Scenario) -> ResearchReport:
    """Reproduce the selected candidate, then run once under one shared clock."""
    budget = _ResearchBudget(_CANDIDATE_ID, scenario.limits.runtime_seconds)
    provenance: dict[str, Any] = {
        "candidate_selection": "Fresh scenario search; no cached physical values",
        "automatic_retries": 0,
        "maximum_native_arcs": 6,
        "deadline_policy": "Shared cooperative deadline, not native-call preemption",
    }
    controls: tuple[float, ...] | None = None
    stage = "candidate-verification"
    # ponytail: reuse the global science lock; concurrent research is out of scope.
    with SCIENCE_LOCK:
        try:
            budget.check()
            result = _search_impulsive_transfers(
                scenario,
                deadline_monotonic_s=budget.deadline_monotonic_s,
                monotonic=budget.monotonic,
            )
            budget.check()
            candidate = next(
                (item for item in result.pareto_front
                 if item.candidate_id == _CANDIDATE_ID), None,
            )
            if candidate is None:
                raise ValueError("selected candidate is absent from reproduced Pareto front")
            provenance["candidate"] = asdict(candidate)
            stage = "resource-preparation"
            provenance["runtime"] = _runtime_manifest(scenario.limits.random_seed)
            budget.check()
            environment = physical._build_physical_environment(
                candidate, scenario.spacecraft, budget=budget,
            )
            provenance["environment"] = {
                "model_id": environment.model_id,
                "origin": environment.origin,
                "orientation": environment.orientation,
                "initial_epoch_tdb_s": environment.initial_epoch_tdb_s,
                "final_epoch_tdb_s": environment.final_epoch_tdb_s,
                "harmonic_fields": [asdict(v) for v in environment.harmonic_fields],
                "gravity": [asdict(v) for v in environment.gravity_acceleration_inventory],
                "solar_radiation_pressure": asdict(environment.solar_radiation_pressure),
                "relativity": asdict(environment.relativity),
                "collision_resource": asdict(environment.collision_resource),
            }
            budget.check()
            stage = "boundary-and-seed-preparation"
            gm = {v.body: v.gravitational_parameter_m3_s2
                  for v in environment.harmonic_fields}
            initial, target = physical._build_boundary_states(
                scenario, candidate, gm["Moon"], gm["Mars"],
            )
            budget.check()
            seed = physical._build_initial_burn_controls(
                scenario, candidate, gm["Moon"], gm["Mars"],
            )
            if isinstance(seed, str):
                raise ValueError(seed)
            controls = seed
            budget.check()
        except (EphemerisError, TransferSearchError, TrajectoryRefinementError,
                ValueError) as exc:
            nominal = ResearchRun(
                profile="nominal", outcome="unavailable", reason=f"{stage}: {exc}",
                progress=ResearchProgress(0, 0), checked_state_count=0,
                check_coverage="Preparation only; no propagated states checked.",
            )
            tighter = ResearchRun(
                profile="tighter", outcome="unavailable", reason="nominal-not-started",
                progress=ResearchProgress(0, 0), checked_state_count=0,
                check_coverage="No states or events checked.",
            )
            return ResearchReport(
                candidate_id=_CANDIDATE_ID, scenario=scenario, seed_controls=controls,
                provenance_json=json.dumps(provenance, allow_nan=False),
                nominal=nominal, tighter=tighter,
                elapsed_wall_s=budget._last_monotonic_s
                - (budget.deadline_monotonic_s - budget.runtime_seconds),
            )
        return _compare_research_profiles(
            budget, scenario, candidate, environment, initial, target, controls,
            json.dumps(provenance, allow_nan=False),
        )


def main(argv: list[str] | None = None) -> int:
    """Persist one report, including unsuccessful scientific outcomes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    scenario = load_scenario(args.scenario)
    # Reserve output before spending computation; never overwrite prior evidence.
    with args.output.open("x", encoding="utf-8") as stream:
        source = Path(__file__).parent
        inputs = {
            "scenario_sha256": sha256(args.scenario.read_bytes()).hexdigest(),
            "source_sha256": {p.name: sha256(p.read_bytes()).hexdigest()
                              for p in sorted(source.glob("*.py"))},
        }
        report = _run_reference(scenario)
        payload = {**report.to_dict(), "reproduction": inputs}
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return 0 if report.numerical_agreement is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
