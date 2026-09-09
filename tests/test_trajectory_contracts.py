from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
import json
import math

import pytest

from space_nav.models import (
    FiniteBurnRecord,
    PhysicalTrajectoryResult,
    TrajectoryBoundaryDifference,
    TrajectoryBoundaryState,
)


_FORCE_MODEL_ID = (
    "ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-"
    "cannonball-srp-schwarzschild-direct-spice-v2"
)
_G0_M_S2 = 9.80665


def _state(
    *,
    label: str = "departure-ignition",
    epoch_utc: str = "2031-01-01T00:00:00Z",
    epoch_tdb_s: float = 100.0,
) -> TrajectoryBoundaryState:
    return TrajectoryBoundaryState(
        label=label,
        epoch_utc=epoch_utc,
        epoch_tdb_s=epoch_tdb_s,
        origin="SSB",
        orientation="J2000",
        position_m=(1.0, 2.0, 3.0),
        velocity_m_s=(4.0, 5.0, 6.0),
    )


def _burn(
    burn_id: str,
    *,
    initial_mass_kg: float,
    start_epoch_tdb_s: float,
    end_epoch_tdb_s: float,
    thrust_n: float = 98.0665,
    isp_s: float = 1000.0,
) -> FiniteBurnRecord:
    duration_s = end_epoch_tdb_s - start_epoch_tdb_s
    propellant_mass_kg = thrust_n * duration_s / (_G0_M_S2 * isp_s)
    final_mass_kg = initial_mass_kg - propellant_mass_kg
    frame = "Moon-relative TNW" if burn_id == "departure" else "Mars-relative TNW"
    return FiniteBurnRecord(
        burn_id=burn_id,  # type: ignore[arg-type]
        start_epoch_tdb_s=start_epoch_tdb_s,
        end_epoch_tdb_s=end_epoch_tdb_s,
        direction_frame=frame,  # type: ignore[arg-type]
        direction_tnw=(1.0, 0.0, 0.0),
        thrust_n=thrust_n,
        isp_s=isp_s,
        initial_mass_kg=initial_mass_kg,
        final_mass_kg=final_mass_kg,
        propellant_mass_kg=propellant_mass_kg,
        ideal_equivalent_delta_v_m_s=(
            _G0_M_S2 * isp_s * math.log(initial_mass_kg / final_mass_kg)
        ),
    )


def _differences(
    *,
    position_difference_m: float,
    velocity_difference_m_s: float,
    mass_difference_kg: float,
) -> tuple[TrajectoryBoundaryDifference, ...]:
    values = (
        "departure-ignition",
        "departure-cutoff",
        "arrival-ignition",
        "arrival-cutoff",
    )
    return tuple(
        TrajectoryBoundaryDifference(
            label=label,  # type: ignore[arg-type]
            position_difference_m=position_difference_m,
            velocity_difference_m_s=velocity_difference_m_s,
            mass_difference_kg=mass_difference_kg,
        )
        for label in values
    )


def _result(
    status: str = "converged",
    **changes: object,
) -> PhysicalTrajectoryResult:
    initial_state = _state()
    target_state = _state(
        label="arrival-cutoff-target",
        epoch_utc="2031-01-02T00:00:00Z",
        epoch_tdb_s=200.0,
    )
    terminal_state = replace(
        target_state,
        label="arrival-cutoff",
        position_m=(1001.0, 2.0, 3.0),
        velocity_m_s=(4.01, 5.0, 6.0),
    )
    departure = _burn(
        "departure",
        initial_mass_kg=2000.0,
        start_epoch_tdb_s=100.0,
        end_epoch_tdb_s=101.0,
    )
    arrival = _burn(
        "arrival",
        initial_mass_kg=departure.final_mass_kg,
        start_epoch_tdb_s=199.0,
        end_epoch_tdb_s=200.0,
    )
    actual_propellant_mass_kg = 2000.0 - arrival.final_mass_kg
    values: dict[str, object] = {
        "candidate_id": "d0001-t0035",
        "status": status,
        "termination_reason": "target-closure-and-validation-passed",
        "origin": "SSB",
        "orientation": "J2000",
        "time_scale": "TDB seconds since J2000",
        "force_model_id": _FORCE_MODEL_ID,
        "initial_state": initial_state,
        "target_final_state": target_state,
        "terminal_state": terminal_state,
        "burns": (departure, arrival),
        "initial_mass_kg": 2000.0,
        "dry_mass_kg": 1000.0,
        "final_mass_kg": arrival.final_mass_kg,
        "propellant_mass_kg": actual_propellant_mass_kg,
        "ideal_m2_final_mass_kg": 1500.0,
        "required_propellant_mass_kg": 500.0,
        "available_propellant_mass_kg": 1000.0,
        "propellant_shortfall_kg": 0.0,
        "terminal_position_error_m": 1000.0,
        "terminal_velocity_error_m_s": 0.01,
        "integration_differences": _differences(
            position_difference_m=10.0,
            velocity_difference_m_s=0.0001,
            mass_difference_kg=0.000001,
        ),
        "lunar_harmonic_differences": _differences(
            position_difference_m=500.0,
            velocity_difference_m_s=0.0001,
            mass_difference_kg=0.0,
        ),
        "martian_harmonic_differences": _differences(
            position_difference_m=750.0,
            velocity_difference_m_s=0.001,
            mass_difference_kg=0.0,
        ),
        "correction_iterations": 0,
        "control_attempts": 1,
        "propagation_evaluations": 4,
        "native_arc_propagations": 12,
        "rejection_counts": (),
    }
    if status == "mass-infeasible":
        values.update(
            termination_reason="preflight-m2-propellant-shortfall",
            terminal_state=None,
            burns=(),
            final_mass_kg=None,
            propellant_mass_kg=None,
            ideal_m2_final_mass_kg=900.0,
            required_propellant_mass_kg=1100.0,
            available_propellant_mass_kg=1000.0,
            propellant_shortfall_kg=100.0,
            terminal_position_error_m=None,
            terminal_velocity_error_m_s=None,
            integration_differences=(),
            lunar_harmonic_differences=(),
            martian_harmonic_differences=(),
            control_attempts=0,
            propagation_evaluations=0,
            native_arc_propagations=0,
        )
    elif status == "targeting-failed":
        values.update(
            termination_reason="nonconvergence",
            terminal_state=replace(
                terminal_state,
                position_m=(1001.001, 2.0, 3.0),
            ),
            terminal_position_error_m=1000.001,
            integration_differences=(),
            lunar_harmonic_differences=(),
            martian_harmonic_differences=(),
            propagation_evaluations=1,
            native_arc_propagations=3,
        )
    values.update(changes)
    return PhysicalTrajectoryResult(**values)  # type: ignore[arg-type]


def _no_safe_result(**changes: object) -> PhysicalTrajectoryResult:
    values: dict[str, object] = {
        "termination_reason": "no-safe-complete-trial",
        "terminal_state": None,
        "burns": (),
        "final_mass_kg": None,
        "propellant_mass_kg": None,
        "terminal_position_error_m": None,
        "terminal_velocity_error_m_s": None,
        "control_attempts": 1,
        "propagation_evaluations": 1,
        "native_arc_propagations": 1,
        "rejection_counts": (("rejected-impact:Mars", 1),),
    }
    values.update(changes)
    return _result("targeting-failed", **values)


def test_m3_records_are_frozen_slotted_and_all_statuses_are_valid() -> None:
    records = (
        _state(),
        _burn(
            "departure",
            initial_mass_kg=2000.0,
            start_epoch_tdb_s=100.0,
            end_epoch_tdb_s=101.0,
        ),
        _differences(
            position_difference_m=0.0,
            velocity_difference_m_s=0.0,
            mass_difference_kg=0.0,
        )[0],
        _result(),
        _result("mass-infeasible"),
        _result("targeting-failed"),
        _no_safe_result(),
    )

    frozen_fields = (
        "label",
        "burn_id",
        "label",
        "status",
        "status",
        "status",
        "status",
    )
    for record, field in zip(records, frozen_fields, strict=True):
        assert not hasattr(record, "__dict__")
        with pytest.raises(FrozenInstanceError):
            setattr(record, field, "changed")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"label": ""}, "label"),
        ({"label": " padded "}, "label"),
        ({"epoch_utc": "2031-01-01T00:00:00.000Z"}, "normalized"),
        ({"epoch_tdb_s": True}, "finite"),
        ({"epoch_tdb_s": math.nan}, "finite"),
        ({"epoch_tdb_s": 10**10000}, "finite"),
        ({"origin": "Earth"}, "SSB"),
        ({"orientation": "ECLIPJ2000"}, "J2000"),
        ({"position_m": [1.0, 2.0, 3.0]}, "three finite"),
        ({"velocity_m_s": (1.0, math.inf, 3.0)}, "three finite"),
    ],
)
def test_boundary_state_rejects_invalid_fields(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(_state(), **changes)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"burn_id": "middle"}, "burn_id"),
        ({"direction_frame": "Mars-relative TNW"}, "direction_frame"),
        ({"end_epoch_tdb_s": 100.0}, "after"),
        ({"direction_tnw": (1.0, 1.0, 0.0)}, "unit vector"),
        ({"direction_tnw": (1.0, math.nan, 0.0)}, "three finite"),
        ({"thrust_n": 0.0}, "positive"),
        ({"isp_s": True}, "finite"),
        ({"final_mass_kg": 2000.0}, "below"),
        ({"propellant_mass_kg": 1.0}, "mass change"),
        ({"ideal_equivalent_delta_v_m_s": 1.0}, "rocket equation"),
    ],
)
def test_finite_burn_rejects_invalid_fields(
    changes: dict[str, object], message: str
) -> None:
    burn = _burn(
        "departure",
        initial_mass_kg=2000.0,
        start_epoch_tdb_s=100.0,
        end_epoch_tdb_s=101.0,
    )
    with pytest.raises(ValueError, match=message):
        replace(burn, **changes)


def test_finite_burn_rejects_mass_flow_inconsistent_with_duration() -> None:
    burn = _burn(
        "departure",
        initial_mass_kg=2000.0,
        start_epoch_tdb_s=100.0,
        end_epoch_tdb_s=101.0,
    )
    final_mass_kg = burn.final_mass_kg - 0.1
    with pytest.raises(ValueError, match="mass flow"):
        replace(
            burn,
            final_mass_kg=final_mass_kg,
            propellant_mass_kg=burn.initial_mass_kg - final_mass_kg,
            ideal_equivalent_delta_v_m_s=(
                _G0_M_S2
                * burn.isp_s
                * math.log(burn.initial_mass_kg / final_mass_kg)
            ),
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"label": "mid-coast"}, "fixed trajectory boundary"),
        ({"position_difference_m": -1.0}, "nonnegative"),
        ({"velocity_difference_m_s": True}, "finite"),
        ({"mass_difference_kg": math.inf}, "finite"),
    ],
)
def test_boundary_difference_rejects_invalid_fields(
    changes: dict[str, object], message: str
) -> None:
    difference = _differences(
        position_difference_m=0.0,
        velocity_difference_m_s=0.0,
        mass_difference_kg=0.0,
    )[0]
    with pytest.raises(ValueError, match=message):
        replace(difference, **changes)


@pytest.mark.parametrize(
    ("status", "changes", "message"),
    [
        ("converged", {"candidate_id": "candidate"}, "candidate_id"),
        ("converged", {"termination_reason": " "}, "termination_reason"),
        ("converged", {"origin": "Sun"}, "SSB"),
        ("converged", {"orientation": "ICRF"}, "J2000"),
        ("converged", {"time_scale": "UTC"}, "time_scale"),
        ("converged", {"force_model_id": "other"}, "force_model_id"),
        ("converged", {"force_model_id": _FORCE_MODEL_ID.replace("direct-spice-v2", "v1")},
         "force_model_id"),
        ("converged", {"correction_iterations": 9}, "0 through 8"),
        ("converged", {"control_attempts": True}, "0 through 73"),
        ("converged", {"propagation_evaluations": 77}, "0 through 76"),
        ("converged", {"native_arc_propagations": 229}, "0 through 228"),
        (
            "mass-infeasible",
            {"termination_reason": "nonconvergence"},
            "match status",
        ),
        (
            "targeting-failed",
            {"termination_reason": "preflight-m2-propellant-shortfall"},
            "match status",
        ),
        (
            "converged",
            {"termination_reason": "no-safe-complete-trial"},
            "match status",
        ),
        (
            "converged",
            {"termination_reason": "arbitrary-success"},
            "match status",
        ),
    ],
)
def test_result_rejects_invalid_identity_status_and_counts(
    status: str, changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _result(status, **changes)


def test_result_rejects_invalid_mass_and_burn_chains() -> None:
    with pytest.raises(ValueError, match="initial_mass_kg"):
        _result(initial_mass_kg=1000.0)
    with pytest.raises(ValueError, match="required_propellant_mass_kg"):
        _result(required_propellant_mass_kg=499.0)
    with pytest.raises(ValueError, match="final_mass_kg"):
        _result(final_mass_kg=1999.0)

    valid = _result()
    departure, arrival = valid.burns
    discontinuous_arrival = _burn(
        "arrival",
        initial_mass_kg=departure.final_mass_kg - 1.0,
        start_epoch_tdb_s=arrival.start_epoch_tdb_s,
        end_epoch_tdb_s=arrival.end_epoch_tdb_s,
    )
    with pytest.raises(ValueError, match="continuous"):
        replace(valid, burns=(departure, discontinuous_arrival))
    overlapping_arrival = _burn(
        "arrival",
        initial_mass_kg=departure.final_mass_kg,
        start_epoch_tdb_s=departure.end_epoch_tdb_s,
        end_epoch_tdb_s=arrival.end_epoch_tdb_s,
    )
    with pytest.raises(ValueError, match="positive coast"):
        replace(valid, burns=(departure, overlapping_arrival))

    different_engine_arrival = _burn(
        "arrival",
        initial_mass_kg=departure.final_mass_kg,
        start_epoch_tdb_s=arrival.start_epoch_tdb_s,
        end_epoch_tdb_s=arrival.end_epoch_tdb_s,
        thrust_n=49.03325,
    )
    with pytest.raises(ValueError, match="same maximum thrust"):
        replace(
            valid,
            burns=(departure, different_engine_arrival),
            final_mass_kg=different_engine_arrival.final_mass_kg,
            propellant_mass_kg=(
                valid.initial_mass_kg - different_engine_arrival.final_mass_kg
            ),
        )

    different_isp_arrival = _burn(
        "arrival",
        initial_mass_kg=departure.final_mass_kg,
        start_epoch_tdb_s=arrival.start_epoch_tdb_s,
        end_epoch_tdb_s=arrival.end_epoch_tdb_s,
        isp_s=500.0,
    )
    with pytest.raises(ValueError, match="same specific impulse"):
        replace(
            valid,
            burns=(departure, different_isp_arrival),
            final_mass_kg=different_isp_arrival.final_mass_kg,
            propellant_mass_kg=(
                valid.initial_mass_kg - different_isp_arrival.final_mass_kg
            ),
        )

    discontinuous_mass_arrival = _burn(
        "arrival",
        initial_mass_kg=departure.final_mass_kg + 2e-9,
        start_epoch_tdb_s=arrival.start_epoch_tdb_s,
        end_epoch_tdb_s=arrival.end_epoch_tdb_s,
    )
    with pytest.raises(ValueError, match="continuous"):
        replace(
            valid,
            burns=(departure, discontinuous_mass_arrival),
            final_mass_kg=discontinuous_mass_arrival.final_mass_kg,
            propellant_mass_kg=(
                valid.initial_mass_kg - discontinuous_mass_arrival.final_mass_kg
            ),
        )


def test_result_rejects_mass_budget_status_mismatches() -> None:
    with pytest.raises(ValueError, match="propellant shortfall"):
        _result(
            "mass-infeasible",
            ideal_m2_final_mass_kg=1000.0,
            required_propellant_mass_kg=1000.0,
            propellant_shortfall_kg=0.0,
        )
    with pytest.raises(ValueError, match="feasible M2 mass budget"):
        _result(
            ideal_m2_final_mass_kg=999.0,
            required_propellant_mass_kg=1001.0,
            propellant_shortfall_kg=1.0,
        )


def test_result_rejects_nonfinite_result_values() -> None:
    with pytest.raises(ValueError, match="initial_mass_kg"):
        _result(initial_mass_kg=math.nan)
    with pytest.raises(ValueError, match="propellant_shortfall_kg"):
        _result(propellant_shortfall_kg=math.inf)
    with pytest.raises(ValueError, match="final_mass_kg"):
        _result(final_mass_kg=math.nan)
    with pytest.raises(ValueError, match="terminal_position_error_m"):
        _result(terminal_position_error_m=math.nan)


def test_result_rejects_invalid_complete_boundaries_and_burn_shapes() -> None:
    valid = _result()
    assert valid.terminal_state is not None
    departure, arrival = valid.burns
    with pytest.raises(ValueError, match="exactly two burns"):
        replace(valid, burns=(departure,))
    with pytest.raises(ValueError, match="ordered departure then arrival"):
        replace(valid, burns=(arrival, departure))

    shifted_departure = _burn(
        "departure",
        initial_mass_kg=valid.initial_mass_kg,
        start_epoch_tdb_s=99.0,
        end_epoch_tdb_s=100.0,
    )
    with pytest.raises(ValueError, match="start at the initial epoch"):
        replace(valid, burns=(shifted_departure, arrival))

    shifted_arrival = _burn(
        "arrival",
        initial_mass_kg=departure.final_mass_kg,
        start_epoch_tdb_s=198.0,
        end_epoch_tdb_s=199.0,
    )
    with pytest.raises(ValueError, match="end at the target epoch"):
        replace(valid, burns=(departure, shifted_arrival))
    with pytest.raises(ValueError, match="target cutoff epoch"):
        replace(
            valid,
            terminal_state=replace(valid.terminal_state, epoch_tdb_s=199.0),
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"rejection_counts": [("rejected-impact:Mars", 1)]}, "sorted tuple"),
        (
            {
                "rejection_counts": (
                    ("rejected-impact:Mars", 1),
                    ("rejected-control-bounds", 1),
                )
            },
            "sorted order",
        ),
        ({"rejection_counts": (("rejected-impact:Mars", 0),)}, "positive"),
        ({"rejection_counts": (("", 1),)}, "nonempty"),
        (
            {
                "control_attempts": 2,
                "rejection_counts": (
                    ("rejected-impact:Mars", 1),
                    ("rejected-impact:Mars", 1),
                ),
            },
            "unique keys",
        ),
        (
            {
                "control_attempts": 1,
                "propagation_evaluations": 1,
                "native_arc_propagations": 0,
            },
            "match evaluation counts",
        ),
    ],
)
def test_result_rejects_invalid_rejections_and_cross_counts(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _no_safe_result(**changes)


def test_result_enforces_status_shapes_and_closure_claims() -> None:
    with pytest.raises(ValueError, match="propagated-result"):
        _result("mass-infeasible", terminal_state=_state())
    with pytest.raises(ValueError, match="propagated-result"):
        _result("mass-infeasible", burns=[])
    with pytest.raises(ValueError, match="rejection count"):
        _no_safe_result(rejection_counts=())
    converged = _result()
    assert converged.terminal_state is not None
    with pytest.raises(ValueError, match="position error"):
        _result(
            terminal_state=replace(
                converged.terminal_state,
                position_m=(1001.001, 2.0, 3.0),
            ),
            terminal_position_error_m=1000.001,
        )
    with pytest.raises(ValueError, match="velocity error"):
        _result(
            terminal_state=replace(
                converged.terminal_state,
                velocity_m_s=(4.010001, 5.0, 6.0),
            ),
            terminal_velocity_error_m_s=0.010001,
        )
    with pytest.raises(ValueError, match="nonconvergence"):
        _result(
            "targeting-failed",
            terminal_state=converged.terminal_state,
            terminal_position_error_m=1000.0,
        )
    with pytest.raises(ValueError, match="terminal_position_error_m"):
        _result(terminal_position_error_m=0.0)
    with pytest.raises(ValueError, match="terminal_velocity_error_m_s"):
        _result(terminal_velocity_error_m_s=0.0)

    target = converged.target_final_state
    mismatched_utc_terminal = replace(
        converged.terminal_state,
        epoch_utc="2031-01-03T00:00:00Z",
    )
    with pytest.raises(ValueError, match="terminal_state UTC"):
        _result(terminal_state=mismatched_utc_terminal, target_final_state=target)


def test_result_enforces_status_specific_evaluation_counts() -> None:
    with pytest.raises(ValueError, match="status-appropriate diagnostics"):
        _result(
            "targeting-failed",
            control_attempts=1,
            propagation_evaluations=2,
            native_arc_propagations=6,
        )
    with pytest.raises(ValueError, match="single seed attempt"):
        _no_safe_result(control_attempts=2)
    with pytest.raises(ValueError, match="single seed attempt"):
        _no_safe_result(correction_iterations=1)
    with pytest.raises(ValueError, match="complete propagation history"):
        _result(propagation_evaluations=3, native_arc_propagations=9)
    with pytest.raises(ValueError, match="complete propagation history"):
        _result(native_arc_propagations=11)
    with pytest.raises(ValueError, match="complete propagation history"):
        _result(
            "targeting-failed",
            propagation_evaluations=0,
            native_arc_propagations=0,
        )
    with pytest.raises(ValueError, match="complete propagation history"):
        _result(
            "targeting-failed",
            control_attempts=2,
            propagation_evaluations=2,
            native_arc_propagations=3,
        )
    with pytest.raises(ValueError, match="complete propagation history"):
        _result(
            control_attempts=2,
            propagation_evaluations=5,
            native_arc_propagations=12,
        )


def test_no_safe_result_can_reject_seed_before_propagation() -> None:
    result = _no_safe_result(
        propagation_evaluations=0,
        native_arc_propagations=0,
        rejection_counts=(("rejected-control-bounds", 1),),
    )

    assert result.control_attempts == 1
    assert result.terminal_state is None


def test_result_requires_ordered_bounded_convergence_diagnostics() -> None:
    valid = _result()
    reversed_differences = tuple(reversed(valid.integration_differences))
    with pytest.raises(ValueError, match="fixed order"):
        replace(valid, integration_differences=reversed_differences)
    with pytest.raises(ValueError, match="numerical budget"):
        replace(
            valid,
            integration_differences=_differences(
                position_difference_m=10.001,
                velocity_difference_m_s=0.0001,
                mass_difference_kg=0.000001,
            ),
        )
    with pytest.raises(ValueError, match="numerical budget"):
        replace(
            valid,
            integration_differences=_differences(
                position_difference_m=10.0,
                velocity_difference_m_s=0.0001001,
                mass_difference_kg=0.000001,
            ),
        )
    with pytest.raises(ValueError, match="numerical budget"):
        replace(
            valid,
            integration_differences=_differences(
                position_difference_m=10.0,
                velocity_difference_m_s=0.0001,
                mass_difference_kg=0.0000011,
            ),
        )
    with pytest.raises(ValueError, match="model budget"):
        replace(
            valid,
            lunar_harmonic_differences=_differences(
                position_difference_m=500.001,
                velocity_difference_m_s=0.0001,
                mass_difference_kg=0.0,
            ),
        )
    with pytest.raises(ValueError, match="model budget"):
        replace(
            valid,
            lunar_harmonic_differences=_differences(
                position_difference_m=500.0,
                velocity_difference_m_s=0.0001001,
                mass_difference_kg=0.0,
            ),
        )
    with pytest.raises(ValueError, match="empty unless"):
        replace(
            _result("targeting-failed"),
            integration_differences=valid.integration_differences,
        )


def test_result_json_round_trip_is_finite_stable_and_preserves_absence() -> None:
    results = (
        _result(),
        _result("mass-infeasible"),
        _result("targeting-failed"),
        _no_safe_result(),
    )
    for result in results:
        payload = result.to_dict()
        encoded = json.dumps(
            payload, allow_nan=False, sort_keys=True, separators=(",", ":")
        )
        assert json.loads(encoded) == payload
        assert json.dumps(
            result.to_dict(),
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ) == encoded

    payload = results[0].to_dict()
    assert isinstance(payload["burns"], list)
    assert isinstance(payload["integration_differences"], list)

    absent = _result("mass-infeasible").to_dict()
    assert absent["terminal_state"] is None
    assert absent["final_mass_kg"] is None
    assert absent["burns"] == []
    assert absent["integration_differences"] == []

    safe_failure = results[2].to_dict()
    assert safe_failure["terminal_state"] is not None
    assert len(safe_failure["burns"]) == 2
    no_safe_failure = results[3].to_dict()
    assert no_safe_failure["terminal_state"] is None
    assert no_safe_failure["burns"] == []


def test_result_serializes_supported_non_native_real_values() -> None:
    result = _result(terminal_position_error_m=Fraction(1000, 1))

    assert result.to_dict()["terminal_position_error_m"] == 1000.0
