from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
import math
from pathlib import Path
from typing import Literal

import pytest

from space_nav.models import (
    FiniteBurnRecord,
    PhysicalTrajectoryResult,
    TrajectoryBoundaryState,
)
from space_nav.research import ResearchProgress, ResearchReport, ResearchRun
from space_nav.scenario import load_scenario


def _run(profile: Literal["nominal", "tighter"] = "nominal") -> ResearchRun:
    labels = (
        "departure-ignition",
        "departure-cutoff",
        "arrival-ignition",
        "arrival-cutoff",
    )
    states = tuple(
        TrajectoryBoundaryState(
            label=label,
            epoch_utc=f"2031-01-01T00:{index:02d}:00Z",
            epoch_tdb_s=epoch,
            origin="SSB",
            orientation="J2000",
            position_m=(0.0, 0.0, 0.0),
            velocity_m_s=(0.0, 0.0, 0.0),
        )
        for index, (label, epoch) in enumerate(
            zip(labels, (100.0, 110.0, 190.0, 200.0))
        )
    )
    # Manufactured accounting fixture, not a UTC/TDB or physical orbit oracle.
    masses = (2000.0, 1999.9, 1999.9, 1999.8)
    burns = tuple(
        FiniteBurnRecord(
            burn_id=burn_id,
            start_epoch_tdb_s=states[offset].epoch_tdb_s,
            end_epoch_tdb_s=states[offset + 1].epoch_tdb_s,
            direction_frame=frame,
            direction_tnw=(1.0, 0.0, 0.0),
            thrust_n=98.0665,
            isp_s=1000.0,
            initial_mass_kg=masses[offset],
            final_mass_kg=masses[offset + 1],
            propellant_mass_kg=masses[offset] - masses[offset + 1],
            ideal_equivalent_delta_v_m_s=9806.65
            * math.log(masses[offset] / masses[offset + 1]),
        )
        for burn_id, frame, offset in (
            ("departure", "Moon-relative TNW", 0),
            ("arrival", "Mars-relative TNW", 2),
        )
    )
    return ResearchRun(
        profile=profile,
        outcome="completed",
        reason=None,
        progress=ResearchProgress(3, 3),
        checked_state_count=4,
        check_coverage="Four manufactured boundary checks only; no native events.",
        integrator_settings_json=json.dumps({"profile": profile, "manufactured": True}),
        boundaries=states,
        boundary_masses_kg=masses,
        burns=burns,
        target_state=replace(
            states[-1],
            label="target",
            position_m=(3.0, 4.0, 0.0),
            velocity_m_s=(0.003, 0.004, 0.0),
        ),
    )


def _unavailable(profile: Literal["nominal", "tighter"]) -> ResearchRun:
    return ResearchRun(
        profile=profile,
        outcome="unavailable",
        reason="not-started",
        progress=ResearchProgress(0, 0),
        checked_state_count=0,
        check_coverage="No states or events checked.",
    )


def _report() -> ResearchReport:
    scenario = load_scenario(
        Path(__file__).parents[1] / "examples/m3_feasible_mission.toml"
    )
    scenario = replace(
        scenario,
        spacecraft=replace(
            scenario.spacecraft,
            initial_mass_kg=2000.0,
            dry_mass_kg=500.0,
            max_thrust_n=98.0665,
            isp_s=1000.0,
        ),
    )
    return ResearchReport(
        candidate_id="d0001-t0035",
        scenario=scenario,
        seed_controls=(0.0, 0.0, 10.0, 0.0, 0.0, 10.0),
        provenance_json='{"fixture": "manufactured; not verified resources"}',
        nominal=_run(),
        tighter=_run("tighter"),
        elapsed_wall_s=1.0,
    )


def test_completed_report_is_research_only_with_derived_residuals() -> None:
    report = _report()
    assert not isinstance(report, PhysicalTrajectoryResult)
    assert report.nominal.terminal_errors == pytest.approx((5.0, 0.005), abs=1e-15)
    assert report.numerical_agreement is True  # agreement despite nonzero target miss
    assert len(report.integration_differences) == 4
    assert report.progress == ResearchProgress(6, 6)
    payload = report.to_dict()
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
    science = payload["science"]
    assert science["research_only"] is True
    assert science["outcome"] == "completed"
    assert science["seed_commands"]["departure_duration_s"] == 10.0
    assert science["continuous_safety_verified"] is False
    assert science["nominal"]["terminal_position_error_m"] == 5.0
    assert science["time_scale"] == "TDB seconds since J2000"
    assert (science["origin"], science["orientation"], science["units"]) == (
        "SSB",
        "J2000",
        "SI",
    )
    assert "between-check impacts" in science["coverage_limitation"]
    assert "small bodies and debris" in science["coverage_limitation"]
    assert "elapsed_wall_s" not in science
    assert payload["wall_clock"] == {"elapsed_s": 1.0}
    assert replace(report, elapsed_wall_s=2.0).to_dict()["science"] == science
    science["scenario"]["spacecraft"]["dry_mass_kg"] = 0
    science["provenance"]["fixture"] = "tampered"
    assert report.to_dict()["science"]["scenario"]["spacecraft"]["dry_mass_kg"] == 500
    assert report.to_dict()["science"]["provenance"]["fixture"] != "tampered"
    with pytest.raises(FrozenInstanceError):
        report.candidate_id = "d0000-t0000"  # type: ignore[misc]
    with pytest.raises(ValueError, match="init=False"):
        replace(report, continuous_safety_verified=True)


def test_unavailable_and_aborted_runs_have_no_invented_endpoint() -> None:
    report = replace(
        _report(),
        nominal=_unavailable("nominal"),
        tighter=_unavailable("tighter"),
        seed_controls=None,
        provenance_json=None,
    )
    assert report.numerical_agreement is None
    assert report.outcome == "unavailable"
    assert report.progress == ResearchProgress(0, 0)
    aborted = replace(
        report.nominal,
        outcome="aborted",
        reason="deadline: departure arc",
        progress=ResearchProgress(1, 0),
        checked_state_count=2,
        integrator_settings_json='{"profile":"nominal"}',
    )
    report = replace(
        report,
        nominal=aborted,
        seed_controls=_report().seed_controls,
        provenance_json='{"fixture":true}',
    )
    science = report.to_dict()["science"]
    assert science["outcome"] == "aborted"
    assert science["nominal"]["boundaries"] == []
    assert science["nominal"]["terminal_position_error_m"] is None
    assert science["nominal"]["terminal_velocity_error_m_s"] is None
    assert science["integration_differences"] == []
    with pytest.raises(ValueError, match="incomplete"):
        replace(aborted, boundaries=(_run().boundaries[0],))


def test_tighter_failure_keeps_nominal_but_not_numerical_qualification() -> None:
    tighter = replace(
        _unavailable("tighter"),
        outcome="aborted",
        reason="native failure: coast",
        progress=ResearchProgress(2, 1),
        checked_state_count=10,
        integrator_settings_json='{"profile":"tighter"}',
    )
    report = replace(_report(), tighter=tighter)
    assert report.progress == ResearchProgress(5, 4)
    assert report.nominal.terminal_errors is not None
    assert report.numerical_agreement is None
    science = report.to_dict()["science"]
    assert science["comparison_reason"] == "native failure: coast"
    assert science["tighter"]["terminal_position_error_m"] is None


@pytest.mark.parametrize("value,expected", [(10.0, True), (10.000001, False)])
@pytest.mark.parametrize("index", [1, 2, 3])
def test_agreement_checks_each_boundary_position(
    index: int, value: float, expected: bool
) -> None:
    report = _report()
    states = list(report.tighter.boundaries)
    states[index] = replace(states[index], position_m=(value, 0.0, 0.0))
    report = replace(report, tighter=replace(report.tighter, boundaries=tuple(states)))
    assert report.numerical_agreement is expected
    assert report.to_dict()["science"]["comparison_reason"] == (
        None if expected else "integration-threshold-exceeded"
    )


@pytest.mark.parametrize("value,expected", [(0.0001, True), (0.000100001, False)])
def test_velocity_agreement_threshold(value: float, expected: bool) -> None:
    report = _report()
    states = list(report.tighter.boundaries)
    states[1] = replace(states[1], velocity_m_s=(value, 0.0, 0.0))
    report = replace(report, tighter=replace(report.tighter, boundaries=tuple(states)))
    assert report.numerical_agreement is expected


@pytest.mark.parametrize(
    "changes",
    [
        {"candidate_id": "wrong"},
        {"elapsed_wall_s": True},
        {"elapsed_wall_s": -1},
        {"elapsed_wall_s": math.nan},
        {"seed_controls": None},
        {"provenance_json": None},
        {"provenance_json": "[]"},
        {"provenance_json": '{"bad": NaN}'},
        {"provenance_json": '{"bad": 1e400}'},
        {"provenance_json": {}},
        {"seed_controls": (0.0, 0.0, 0.0, 0.0, 0.0, 10.0)},
        {"seed_controls": (0.0, 0.0, 10.0, 0.0, math.inf, 10.0)},
        {"seed_controls": (False, 0.0, 10.0, 0.0, 0.0, 10.0)},
        {"seed_controls": (0.0, 0.0, 11.0, 0.0, 0.0, 10.0)},
        {"seed_controls": (1.0, 0.0, 10.0, 0.0, 0.0, 10.0)},
    ],
)
def test_report_invalid_inputs(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        replace(_report(), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"outcome": "converged"},
        {"reason": "failure"},
        {"checked_state_count": True},
        {"checked_state_count": -1},
        {"checked_state_count": 3},
        {"check_coverage": ""},
        {"integrator_settings_json": None},
        {"integrator_settings_json": '{"bad": Infinity}'},
        {"boundaries": ()},
        {"boundary_masses_kg": (2000.0,)},
        {"burns": ()},
        {"target_state": None},
        {"progress": ResearchProgress(2, 2)},
    ],
)
def test_run_invalid_inputs(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        replace(_run(), **changes)


def test_run_order_epoch_mass_and_replay_invariants() -> None:
    report = _report()
    run = report.nominal
    with pytest.raises(ValueError, match="order"):
        replace(run, boundaries=tuple(reversed(run.boundaries)))
    with pytest.raises(ValueError, match="target epoch"):
        replace(run, target_state=run.boundaries[0])
    with pytest.raises(ValueError, match="burn masses"):
        replace(run, boundary_masses_kg=(2000.0, 1999.8, 1999.9, 1999.8))
    with pytest.raises(ValueError, match="requires completed nominal"):
        replace(report, nominal=_unavailable("nominal"))
    with pytest.raises(ValueError, match="initial state"):
        states = report.tighter.boundaries
        replace(
            report,
            tighter=replace(
                report.tighter,
                boundaries=(
                    replace(states[0], position_m=(1.0, 0.0, 0.0)),
                    *states[1:],
                ),
            ),
        )
    with pytest.raises(ValueError, match="dry mass"):
        replace(
            report,
            scenario=replace(
                report.scenario,
                spacecraft=replace(
                    report.scenario.spacecraft,
                    dry_mass_kg=1999.8,
                ),
            ),
        )


def test_prelaunch_failure_and_impossible_counts() -> None:
    run = _unavailable("nominal")
    assert (
        replace(run, outcome="aborted", reason="invalid initial state").terminal_errors
        is None
    )
    for progress in (
        ResearchProgress(1, 0),
        ResearchProgress(2, 0),
        ResearchProgress(3, 3),
        ResearchProgress(4, 3),
    ):
        with pytest.raises(ValueError):
            replace(run, progress=progress, integrator_settings_json='{"fixture":true}')
    with pytest.raises(ValueError, match="nonempty"):
        replace(run, reason=None)


@pytest.mark.parametrize("delta,expected", [(0.0000005, True), (0.000002, False)])
def test_mass_comparison_with_large_manufactured_burn(
    delta: float, expected: bool
) -> None:
    # Large mass flow makes a sub-microgram difference representable and within
    # FiniteBurnRecord's existing relative mass-flow allowance. Not a mission.
    report = _report()
    scenario = replace(
        report.scenario,
        spacecraft=replace(
            report.scenario.spacecraft,
            initial_mass_kg=3000000.0,
            max_thrust_n=980665000.0,
        ),
    )

    def scaled(run: ResearchRun, offset_kg: float) -> ResearchRun:
        # 100000 kg/s, two ten-second burns, ample remaining propellant.
        masses = (
            3000000.0,
            2000000.0 + offset_kg,
            2000000.0 + offset_kg,
            1000000.0 + offset_kg,
        )
        burns = tuple(
            replace(
                burn,
                thrust_n=980665000.0,
                initial_mass_kg=masses[index],
                final_mass_kg=masses[index + 1],
                propellant_mass_kg=masses[index] - masses[index + 1],
                ideal_equivalent_delta_v_m_s=9806.65
                * math.log(masses[index] / masses[index + 1]),
            )
            for index, burn in zip((0, 2), run.burns)
        )
        return replace(run, boundary_masses_kg=masses, burns=burns)

    report = replace(
        report,
        scenario=scenario,
        nominal=scaled(report.nominal, 0.0),
        tighter=scaled(report.tighter, delta),
    )
    assert report.integration_differences[1].mass_difference_kg == pytest.approx(
        delta, abs=3e-10
    )
    assert report.numerical_agreement is expected


def test_finite_input_overflow_is_not_serialized_as_infinity() -> None:
    run = _run()
    states = (
        *run.boundaries[:-1],
        replace(run.boundaries[-1], position_m=(1e308, 0.0, 0.0)),
    )
    with pytest.raises(ValueError, match="finite"):
        replace(
            run,
            boundaries=states,
            target_state=replace(run.target_state, position_m=(-1e308, 0.0, 0.0)),
        )


def test_replay_rejects_even_small_direction_change() -> None:
    report = _report()
    departure, arrival = report.tighter.burns
    departure = replace(departure, direction_tnw=(1.0, 5e-13, 0.0))
    with pytest.raises(ValueError, match="identical burn directions"):
        replace(report, tighter=replace(report.tighter, burns=(departure, arrival)))
