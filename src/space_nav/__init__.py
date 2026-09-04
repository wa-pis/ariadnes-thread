"""Public API for the Moon-to-Mars navigation planner."""

__version__ = "0.2.0"

from .ephemeris import CartesianState, query_body_state, tdb_to_utc, utc_to_tdb
from .errors import (
    EphemerisError,
    ScenarioValidationError,
    TrajectoryRefinementError,
    TransferSearchError,
)
from .models import (
    FiniteBurnRecord,
    ImpulsiveTransferCandidate,
    LimitsSpec,
    OrbitSpec,
    PhysicalTrajectoryResult,
    Scenario,
    SearchSpec,
    SpacecraftSpec,
    TrackingSpec,
    TrajectoryBoundaryDifference,
    TrajectoryBoundaryState,
    TransferSearchResult,
)
from .scenario import load_scenario
from .transfer import search_impulsive_transfers

__all__ = [
    "CartesianState",
    "EphemerisError",
    "FiniteBurnRecord",
    "ImpulsiveTransferCandidate",
    "LimitsSpec",
    "OrbitSpec",
    "PhysicalTrajectoryResult",
    "Scenario",
    "ScenarioValidationError",
    "SearchSpec",
    "SpacecraftSpec",
    "TrackingSpec",
    "TrajectoryBoundaryDifference",
    "TrajectoryBoundaryState",
    "TrajectoryRefinementError",
    "TransferSearchError",
    "TransferSearchResult",
    "load_scenario",
    "query_body_state",
    "search_impulsive_transfers",
    "tdb_to_utc",
    "utc_to_tdb",
    "__version__",
]
