"""Immutable normalized mission-scenario values."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import math
from numbers import Real
import re
from typing import Any, Literal


_UTC_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
_CANDIDATE_ID_PATTERN = re.compile(r"^d\d{4}-t\d{4}$")


def _finite_number(name: str, value: object, *, nonnegative: bool = False) -> None:
    if (
        not isinstance(value, Real)
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError(f"{name} must be finite")
    if nonnegative and value < 0:
        raise ValueError(f"{name} must be nonnegative")


def _finite_vector(name: str, value: object) -> None:
    if (
        not isinstance(value, tuple)
        or len(value) != 3
        or any(
            not isinstance(component, Real)
            or isinstance(component, bool)
            or not math.isfinite(component)
            for component in value
        )
    ):
        raise ValueError(f"{name} must contain three finite values")


def _normalized_utc(name: str, value: object) -> datetime:
    if not isinstance(value, str) or not _UTC_PATTERN.fullmatch(value):
        raise ValueError(f"{name} must be normalized ISO-8601 UTC text")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be normalized ISO-8601 UTC text") from exc
    normalized = parsed.astimezone(UTC).isoformat(timespec="microseconds")
    normalized = normalized.removesuffix("+00:00")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    if value != normalized + "Z":
        raise ValueError(f"{name} must be normalized ISO-8601 UTC text")
    return parsed


@dataclass(frozen=True, slots=True)
class SearchSpec:
    departure_start_utc: str
    departure_end_utc: str
    time_of_flight_min_s: float
    time_of_flight_max_s: float


@dataclass(frozen=True, slots=True)
class OrbitSpec:
    central_body: str
    periapsis_altitude_m: float
    apoapsis_altitude_m: float
    eccentricity: float
    inclination_rad: float
    raan_rad: float
    argument_of_periapsis_rad: float
    true_anomaly_rad: float


@dataclass(frozen=True, slots=True)
class SpacecraftSpec:
    initial_mass_kg: float
    dry_mass_kg: float
    max_thrust_n: float
    isp_s: float
    srp_area_m2: float
    reflectivity_coefficient: float
    maneuver_magnitude_sigma_fraction: float
    maneuver_pointing_sigma_rad: float


@dataclass(frozen=True, slots=True)
class TrackingSpec:
    stations: tuple[str, ...]
    cadence_s: float
    range_sigma_m: float
    range_rate_sigma_m_s: float
    angular_sigma_rad: float
    min_elevation_rad: float


@dataclass(frozen=True, slots=True)
class LimitsSpec:
    runtime_seconds: float
    random_seed: int
    max_candidates: int


@dataclass(frozen=True, slots=True)
class Scenario:
    search: SearchSpec
    departure_orbit: OrbitSpec
    target_orbit: OrbitSpec
    spacecraft: SpacecraftSpec
    tracking: TrackingSpec
    limits: LimitsSpec

    def to_dict(self) -> dict[str, Any]:
        """Return the normalized values in a JSON-serializable mapping."""

        return asdict(self)


@dataclass(frozen=True, slots=True)
class ImpulsiveTransferCandidate:
    """One solved first-order Moon-to-Mars transfer candidate."""

    candidate_id: str
    departure_epoch_utc: str
    arrival_epoch_utc: str
    departure_epoch_tdb_s: float
    arrival_epoch_tdb_s: float
    flight_time_s: float
    departure_v_infinity_m_s: tuple[float, float, float]
    arrival_v_infinity_m_s: tuple[float, float, float]
    departure_delta_v_m_s: float
    arrival_delta_v_m_s: float
    total_delta_v_m_s: float
    propellant_mass_kg: float
    final_mass_kg: float
    mass_feasible: bool

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not _CANDIDATE_ID_PATTERN.fullmatch(
            self.candidate_id
        ):
            raise ValueError("candidate_id must match dIIII-tJJJJ")

        departure_utc = _normalized_utc(
            "departure_epoch_utc", self.departure_epoch_utc
        )
        arrival_utc = _normalized_utc("arrival_epoch_utc", self.arrival_epoch_utc)
        if arrival_utc <= departure_utc:
            raise ValueError("arrival_epoch_utc must be after departure_epoch_utc")

        for name in (
            "departure_epoch_tdb_s",
            "arrival_epoch_tdb_s",
            "flight_time_s",
        ):
            _finite_number(name, getattr(self, name))
        if self.flight_time_s <= 0:
            raise ValueError("flight_time_s must be positive")
        if not math.isclose(
            self.arrival_epoch_tdb_s - self.departure_epoch_tdb_s,
            self.flight_time_s,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ValueError("TDB epochs must be consistent with flight_time_s")

        _finite_vector(
            "departure_v_infinity_m_s", self.departure_v_infinity_m_s
        )
        _finite_vector("arrival_v_infinity_m_s", self.arrival_v_infinity_m_s)
        for name in (
            "departure_delta_v_m_s",
            "arrival_delta_v_m_s",
            "total_delta_v_m_s",
            "propellant_mass_kg",
            "final_mass_kg",
        ):
            _finite_number(name, getattr(self, name), nonnegative=True)
        if not math.isclose(
            self.total_delta_v_m_s,
            self.departure_delta_v_m_s + self.arrival_delta_v_m_s,
            rel_tol=1e-12,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "total_delta_v_m_s must equal departure plus arrival delta-v"
            )
        if not isinstance(self.mass_feasible, bool):
            raise ValueError("mass_feasible must be a Boolean")


@dataclass(frozen=True, slots=True)
class TransferSearchResult:
    """A complete bounded transfer search and its ordered Pareto front."""

    ephemeris_origin: Literal["SSB"]
    transfer_central_body: Literal["Sun"]
    orientation: Literal["J2000"]
    time_scale: Literal["TDB seconds since J2000"]
    evaluated_candidates: int
    solved_candidates: int
    failed_candidates: int
    mass_feasible_candidates: int
    pareto_front: tuple[ImpulsiveTransferCandidate, ...]

    def __post_init__(self) -> None:
        if self.ephemeris_origin != "SSB":
            raise ValueError("ephemeris_origin must be SSB")
        if self.transfer_central_body != "Sun":
            raise ValueError("transfer_central_body must be Sun")
        if self.orientation != "J2000":
            raise ValueError("orientation must be J2000")
        if self.time_scale != "TDB seconds since J2000":
            raise ValueError("time_scale must be TDB seconds since J2000")

        for name in (
            "evaluated_candidates",
            "solved_candidates",
            "failed_candidates",
            "mass_feasible_candidates",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.evaluated_candidates > 2000:
            raise ValueError("evaluated_candidates must not exceed 2000")
        if self.solved_candidates + self.failed_candidates != self.evaluated_candidates:
            raise ValueError(
                "solved_candidates plus failed_candidates must equal "
                "evaluated_candidates"
            )
        if self.mass_feasible_candidates > self.solved_candidates:
            raise ValueError(
                "mass_feasible_candidates must not exceed solved_candidates"
            )
        if not isinstance(self.pareto_front, tuple) or not all(
            isinstance(candidate, ImpulsiveTransferCandidate)
            for candidate in self.pareto_front
        ):
            raise ValueError(
                "pareto_front must be a tuple of ImpulsiveTransferCandidate values"
            )
        if self.solved_candidates == 0 or not self.pareto_front:
            raise ValueError("a completed search must contain a solved Pareto candidate")
        if len(self.pareto_front) > self.solved_candidates:
            raise ValueError("pareto_front cannot contain more entries than were solved")
        if len({item.candidate_id for item in self.pareto_front}) != len(
            self.pareto_front
        ):
            raise ValueError("pareto_front candidate identifiers must be unique")
        if sum(item.mass_feasible for item in self.pareto_front) > (
            self.mass_feasible_candidates
        ):
            raise ValueError(
                "pareto_front contains more feasible entries than the search count"
            )
        expected_order = tuple(
            sorted(
                self.pareto_front,
                key=lambda item: (
                    item.flight_time_s,
                    item.propellant_mass_kg,
                    item.departure_epoch_tdb_s,
                    item.candidate_id,
                ),
            )
        )
        if self.pareto_front != expected_order:
            raise ValueError("pareto_front must use the documented stable order")
