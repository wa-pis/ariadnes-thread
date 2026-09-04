"""Verified M2 handoff for physical trajectory refinement."""

from __future__ import annotations

from datetime import datetime
import math
from typing import NoReturn

from .errors import TrajectoryRefinementError, TransferSearchError
from .models import ImpulsiveTransferCandidate, Scenario
from .transfer import search_impulsive_transfers


_TIME_TOLERANCE_S = 1e-6
_VELOCITY_TOLERANCE_M_S = 1e-6
_MASS_RELATIVE_TOLERANCE = 1e-12


def _raise_handoff_error(
    candidate_id: object,
    detail: str,
    cause: Exception,
) -> NoReturn:
    raise TrajectoryRefinementError(
        f"Candidate {candidate_id!r} failed during candidate-verification: {detail}"
    ) from cause


def _require_match(
    matches: bool,
    candidate_id: str,
    field: str,
) -> None:
    if not matches:
        cause = ValueError(f"{field} differs from the reproduced Pareto candidate")
        _raise_handoff_error(candidate_id, str(cause), cause)


def _utc_difference_s(left: str, right: str) -> float:
    left_utc = datetime.fromisoformat(left.removesuffix("Z") + "+00:00")
    right_utc = datetime.fromisoformat(right.removesuffix("Z") + "+00:00")
    return abs((left_utc - right_utc).total_seconds())


def _verify_candidate_values(
    supplied: ImpulsiveTransferCandidate,
    reproduced: ImpulsiveTransferCandidate,
) -> None:
    candidate_id = supplied.candidate_id
    _require_match(
        supplied.candidate_id == reproduced.candidate_id,
        candidate_id,
        "candidate_id",
    )
    for field in ("departure_epoch_utc", "arrival_epoch_utc"):
        _require_match(
            _utc_difference_s(
                getattr(supplied, field),
                getattr(reproduced, field),
            )
            <= _TIME_TOLERANCE_S,
            candidate_id,
            field,
        )
    _require_match(
        supplied.mass_feasible == reproduced.mass_feasible,
        candidate_id,
        "mass_feasible",
    )
    for field in (
        "departure_epoch_tdb_s",
        "arrival_epoch_tdb_s",
        "flight_time_s",
    ):
        _require_match(
            math.isclose(
                getattr(supplied, field),
                getattr(reproduced, field),
                rel_tol=0.0,
                abs_tol=_TIME_TOLERANCE_S,
            ),
            candidate_id,
            field,
        )
    for field in (
        "departure_delta_v_m_s",
        "arrival_delta_v_m_s",
        "total_delta_v_m_s",
    ):
        _require_match(
            math.isclose(
                getattr(supplied, field),
                getattr(reproduced, field),
                rel_tol=0.0,
                abs_tol=_VELOCITY_TOLERANCE_M_S,
            ),
            candidate_id,
            field,
        )
    for field in ("departure_v_infinity_m_s", "arrival_v_infinity_m_s"):
        _require_match(
            math.dist(getattr(supplied, field), getattr(reproduced, field))
            <= _VELOCITY_TOLERANCE_M_S,
            candidate_id,
            field,
        )
    for field in ("propellant_mass_kg", "final_mass_kg"):
        supplied_mass = getattr(supplied, field)
        reproduced_mass = getattr(reproduced, field)
        _require_match(
            abs(supplied_mass - reproduced_mass)
            <= abs(reproduced_mass) * _MASS_RELATIVE_TOLERANCE,
            candidate_id,
            field,
        )


def _verify_candidate_handoff(
    scenario: Scenario,
    candidate: ImpulsiveTransferCandidate,
) -> ImpulsiveTransferCandidate:
    """Return the authoritative reproduced candidate after exact M2 comparison."""

    if not isinstance(candidate, ImpulsiveTransferCandidate):
        cause = TypeError("candidate must be an ImpulsiveTransferCandidate")
        _raise_handoff_error(
            getattr(candidate, "candidate_id", "<invalid>"),
            str(cause),
            cause,
        )
    try:
        result = search_impulsive_transfers(scenario)
    except TransferSearchError as exc:
        _raise_handoff_error(candidate.candidate_id, str(exc), exc)

    reproduced = next(
        (
            item
            for item in result.pareto_front
            if item.candidate_id == candidate.candidate_id
        ),
        None,
    )
    if reproduced is None:
        cause = LookupError("candidate is not on the reproduced Pareto front")
        _raise_handoff_error(candidate.candidate_id, str(cause), cause)
    _verify_candidate_values(candidate, reproduced)
    return reproduced
