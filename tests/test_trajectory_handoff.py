from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys

import pytest

import space_nav
from space_nav.errors import TrajectoryRefinementError, TransferSearchError
from space_nav.models import (
    FiniteBurnRecord,
    ImpulsiveTransferCandidate,
    PhysicalTrajectoryResult,
    TrajectoryBoundaryDifference,
    TrajectoryBoundaryState,
    TransferSearchResult,
)
from space_nav.scenario import load_scenario
from space_nav import trajectory


ROOT = Path(__file__).resolve().parents[1]
SCENARIO = load_scenario(ROOT / "examples" / "reference_mission.toml")


def _candidate(**changes: object) -> ImpulsiveTransferCandidate:
    values: dict[str, object] = {
        "candidate_id": "d0001-t0035",
        "departure_epoch_utc": "2031-01-01T00:00:00Z",
        "arrival_epoch_utc": "2031-01-02T00:00:00Z",
        "departure_epoch_tdb_s": 100.0,
        "arrival_epoch_tdb_s": 200.0,
        "flight_time_s": 100.0,
        "departure_v_infinity_m_s": (1.0, 2.0, 3.0),
        "arrival_v_infinity_m_s": (4.0, 5.0, 6.0),
        "departure_delta_v_m_s": 10.0,
        "arrival_delta_v_m_s": 20.0,
        "total_delta_v_m_s": 30.0,
        "propellant_mass_kg": 100.0,
        "final_mass_kg": 1400.0,
        "mass_feasible": True,
    }
    values.update(changes)
    return ImpulsiveTransferCandidate(**values)  # type: ignore[arg-type]


def _search_result(candidate: ImpulsiveTransferCandidate) -> TransferSearchResult:
    return TransferSearchResult(
        ephemeris_origin="SSB",
        transfer_central_body="Sun",
        orientation="J2000",
        time_scale="TDB seconds since J2000",
        evaluated_candidates=1,
        solved_candidates=1,
        failed_candidates=0,
        mass_feasible_candidates=int(candidate.mass_feasible),
        pareto_front=(candidate,),
    )


def test_m3_contracts_are_public_package_exports() -> None:
    assert space_nav.TrajectoryBoundaryState is TrajectoryBoundaryState
    assert space_nav.FiniteBurnRecord is FiniteBurnRecord
    assert space_nav.TrajectoryBoundaryDifference is TrajectoryBoundaryDifference
    assert space_nav.PhysicalTrajectoryResult is PhysicalTrajectoryResult
    assert space_nav.TrajectoryRefinementError is TrajectoryRefinementError
    assert {
        "TrajectoryBoundaryState",
        "FiniteBurnRecord",
        "TrajectoryBoundaryDifference",
        "PhysicalTrajectoryResult",
        "TrajectoryRefinementError",
    } <= set(space_nav.__all__)


def test_m3_imports_do_not_import_tudatpy_or_load_kernels() -> None:
    code = """
import sys
import space_nav
from space_nav import (
    FiniteBurnRecord,
    PhysicalTrajectoryResult,
    TrajectoryBoundaryDifference,
    TrajectoryBoundaryState,
    TrajectoryRefinementError,
)
from space_nav import ephemeris, trajectory

assert not any(
    name == "tudatpy" or name.startswith("tudatpy.") for name in sys.modules
)
assert not ephemeris._kernels_loaded
assert "moon_to_mars" not in sys.modules
"""
    environment = os.environ | {"PYTHONPATH": str(ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_matching_candidate_is_reproduced_once_and_canonicalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reproduced = _candidate()
    supplied = replace(
        reproduced,
        departure_epoch_utc="2031-01-01T00:00:00.000001Z",
        arrival_epoch_utc="2031-01-02T00:00:00.000001Z",
        departure_epoch_tdb_s=reproduced.departure_epoch_tdb_s + 0.4e-6,
        arrival_epoch_tdb_s=reproduced.arrival_epoch_tdb_s + 0.8e-6,
        flight_time_s=reproduced.flight_time_s + 0.4e-6,
        departure_v_infinity_m_s=(1.0 + 0.5e-6, 2.0, 3.0),
        arrival_v_infinity_m_s=(4.0, 5.0 + 0.5e-6, 6.0),
        departure_delta_v_m_s=reproduced.departure_delta_v_m_s + 0.25e-6,
        arrival_delta_v_m_s=reproduced.arrival_delta_v_m_s + 0.25e-6,
        total_delta_v_m_s=reproduced.total_delta_v_m_s + 0.5e-6,
        propellant_mass_kg=reproduced.propellant_mass_kg * (1.0 + 0.5e-12),
        final_mass_kg=reproduced.final_mass_kg * (1.0 + 0.5e-12),
    )
    calls = 0

    def search(scenario: object) -> TransferSearchResult:
        nonlocal calls
        calls += 1
        assert scenario is SCENARIO
        return _search_result(reproduced)

    monkeypatch.setattr(trajectory, "search_impulsive_transfers", search)

    assert trajectory._verify_candidate_handoff(SCENARIO, supplied) is reproduced
    assert calls == 1


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        (
            {"departure_epoch_utc": "2031-01-01T00:00:00.000002Z"},
            "departure_epoch_utc",
        ),
        (
            {"arrival_epoch_utc": "2031-01-02T00:00:00.000002Z"},
            "arrival_epoch_utc",
        ),
        (
            {
                "departure_epoch_tdb_s": 100.0 + 2e-6,
                "arrival_epoch_tdb_s": 200.0 + 2e-6,
            },
            "departure_epoch_tdb_s",
        ),
        (
            {
                "arrival_epoch_tdb_s": 200.0 + 2e-6,
                "flight_time_s": 100.0 + 2e-6,
            },
            "arrival_epoch_tdb_s",
        ),
        (
            {
                "departure_epoch_tdb_s": 100.0 - 0.4e-6,
                "arrival_epoch_tdb_s": 200.0 + 0.4e-6,
                "flight_time_s": 100.0 + 1.2e-6,
            },
            "flight_time_s",
        ),
        (
            {"departure_v_infinity_m_s": (1.0 + 2e-6, 2.0, 3.0)},
            "departure_v_infinity_m_s",
        ),
        (
            {
                "departure_delta_v_m_s": 10.0 + 2e-6,
                "total_delta_v_m_s": 30.0 + 2e-6,
            },
            "departure_delta_v_m_s",
        ),
        (
            {
                "arrival_delta_v_m_s": 20.0 + 2e-6,
                "total_delta_v_m_s": 30.0 + 2e-6,
            },
            "arrival_delta_v_m_s",
        ),
        (
            {
                "departure_delta_v_m_s": 10.0 + 0.6e-6,
                "arrival_delta_v_m_s": 20.0 + 0.6e-6,
                "total_delta_v_m_s": 30.0 + 1.2e-6,
            },
            "total_delta_v_m_s",
        ),
        ({"propellant_mass_kg": 100.0 * (1.0 + 3e-12)}, "propellant_mass_kg"),
        (
            {"arrival_v_infinity_m_s": (4.0, 5.0 + 2e-6, 6.0)},
            "arrival_v_infinity_m_s",
        ),
        ({"final_mass_kg": 1400.0 * (1.0 + 3e-12)}, "final_mass_kg"),
        ({"mass_feasible": False}, "mass_feasible"),
    ],
)
def test_altered_candidate_is_rejected_before_refinement(
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, object],
    field: str,
) -> None:
    reproduced = _candidate()
    supplied = replace(reproduced, **changes)
    monkeypatch.setattr(
        trajectory,
        "search_impulsive_transfers",
        lambda _scenario: _search_result(reproduced),
    )

    with pytest.raises(
        TrajectoryRefinementError,
        match=rf"d0001-t0035.*candidate-verification.*{field}",
    ) as caught:
        trajectory._verify_candidate_handoff(SCENARIO, supplied)

    assert isinstance(caught.value.__cause__, ValueError)
    assert field in str(caught.value.__cause__)


def test_missing_malformed_and_search_failure_are_contextual_and_chained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reproduced = _candidate()
    monkeypatch.setattr(
        trajectory,
        "search_impulsive_transfers",
        lambda _scenario: _search_result(reproduced),
    )
    with pytest.raises(
        TrajectoryRefinementError,
        match="d9999-t9999.*candidate-verification.*Pareto",
    ) as missing:
        trajectory._verify_candidate_handoff(
            SCENARIO,
            replace(reproduced, candidate_id="d9999-t9999"),
        )
    assert isinstance(missing.value.__cause__, LookupError)

    def must_not_search(_scenario: object) -> TransferSearchResult:
        raise AssertionError("malformed candidate started M2 search")

    monkeypatch.setattr(trajectory, "search_impulsive_transfers", must_not_search)
    with pytest.raises(
        TrajectoryRefinementError,
        match="malformed.*candidate-verification",
    ) as malformed:
        trajectory._verify_candidate_handoff(
            SCENARIO,
            SimpleNamespace(candidate_id="malformed"),  # type: ignore[arg-type]
        )
    assert isinstance(malformed.value.__cause__, TypeError)

    failure = TransferSearchError("M2 search failed")

    def fail(_scenario: object) -> TransferSearchResult:
        raise failure

    monkeypatch.setattr(trajectory, "search_impulsive_transfers", fail)
    with pytest.raises(
        TrajectoryRefinementError,
        match="d0001-t0035.*candidate-verification.*M2 search failed",
    ) as search_failure:
        trajectory._verify_candidate_handoff(SCENARIO, reproduced)
    assert search_failure.value.__cause__ is failure
