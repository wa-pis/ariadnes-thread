"""Immutable normalized mission-scenario values."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import math
from numbers import Real
import re
from typing import Any, Literal


_UTC_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
_CANDIDATE_ID_PATTERN = re.compile(r"^d\d{4}-t\d{4}$")
_BOUNDARY_DIFFERENCE_LABELS = (
    "departure-ignition",
    "departure-cutoff",
    "arrival-ignition",
    "arrival-cutoff",
)
_PHYSICAL_FORCE_MODEL_ID = (
    "ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-"
    "cannonball-srp-schwarzschild-v1"
)
_STANDARD_GRAVITY_M_S2 = 9.80665


def _is_finite_real(value: object) -> bool:
    if not isinstance(value, Real) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _finite_number(name: str, value: object, *, nonnegative: bool = False) -> None:
    if not _is_finite_real(value):
        raise ValueError(f"{name} must be finite")
    if nonnegative and value < 0:
        raise ValueError(f"{name} must be nonnegative")


def _finite_vector(name: str, value: object) -> None:
    if (
        not isinstance(value, tuple)
        or len(value) != 3
        or any(not _is_finite_real(component) for component in value)
    ):
        raise ValueError(f"{name} must contain three finite values")


def _nonempty_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be nonempty text without surrounding whitespace")


def _nonnegative_integer(name: str, value: object, maximum: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > maximum
    ):
        raise ValueError(f"{name} must be an integer from 0 through {maximum}")


def _numbers_match(
    left: float,
    right: float,
    *,
    absolute_tolerance: float = 1e-9,
    relative_tolerance: float = 1e-12,
) -> bool:
    return math.isclose(
        left,
        right,
        rel_tol=relative_tolerance,
        abs_tol=absolute_tolerance,
    )


def _json_real(value: object) -> float:
    if isinstance(value, Real) and not isinstance(value, bool):
        return float(value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


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


@dataclass(frozen=True, slots=True)
class TrajectoryBoundaryState:
    """One public SSB/J2000 Cartesian state at a normalized UTC/TDB epoch."""

    label: str
    epoch_utc: str
    epoch_tdb_s: float
    origin: Literal["SSB"]
    orientation: Literal["J2000"]
    position_m: tuple[float, float, float]
    velocity_m_s: tuple[float, float, float]

    def __post_init__(self) -> None:
        _nonempty_text("label", self.label)
        _normalized_utc("epoch_utc", self.epoch_utc)
        _finite_number("epoch_tdb_s", self.epoch_tdb_s)
        if self.origin != "SSB":
            raise ValueError("origin must be SSB")
        if self.orientation != "J2000":
            raise ValueError("orientation must be J2000")
        _finite_vector("position_m", self.position_m)
        _finite_vector("velocity_m_s", self.velocity_m_s)


@dataclass(frozen=True, slots=True)
class FiniteBurnRecord:
    """One maximum-thrust finite burn with TDB epochs and SI values."""

    burn_id: Literal["departure", "arrival"]
    start_epoch_tdb_s: float
    end_epoch_tdb_s: float
    direction_frame: Literal["Moon-relative TNW", "Mars-relative TNW"]
    direction_tnw: tuple[float, float, float]
    thrust_n: float
    isp_s: float
    initial_mass_kg: float
    final_mass_kg: float
    propellant_mass_kg: float
    ideal_equivalent_delta_v_m_s: float

    def __post_init__(self) -> None:
        expected_frames = {
            "departure": "Moon-relative TNW",
            "arrival": "Mars-relative TNW",
        }
        if not isinstance(self.burn_id, str) or self.burn_id not in expected_frames:
            raise ValueError("burn_id must be departure or arrival")
        if self.direction_frame != expected_frames[self.burn_id]:
            raise ValueError("direction_frame must match burn_id")

        _finite_number("start_epoch_tdb_s", self.start_epoch_tdb_s)
        _finite_number("end_epoch_tdb_s", self.end_epoch_tdb_s)
        if self.end_epoch_tdb_s <= self.start_epoch_tdb_s:
            raise ValueError("end_epoch_tdb_s must be after start_epoch_tdb_s")

        _finite_vector("direction_tnw", self.direction_tnw)
        direction_norm = math.sqrt(
            sum(component * component for component in self.direction_tnw)
        )
        if not math.isclose(direction_norm, 1.0, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("direction_tnw must be a unit vector")

        for name in ("thrust_n", "isp_s", "initial_mass_kg", "final_mass_kg"):
            _finite_number(name, getattr(self, name))
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.final_mass_kg >= self.initial_mass_kg:
            raise ValueError("final_mass_kg must be below initial_mass_kg")

        for name in ("propellant_mass_kg", "ideal_equivalent_delta_v_m_s"):
            _finite_number(name, getattr(self, name))
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")

        consumed_mass_kg = self.initial_mass_kg - self.final_mass_kg
        mass_tolerance_kg = max(1e-8, 1e-11 * consumed_mass_kg)
        if not math.isclose(
            self.propellant_mass_kg,
            consumed_mass_kg,
            rel_tol=0.0,
            abs_tol=mass_tolerance_kg,
        ):
            raise ValueError("propellant_mass_kg must match the burn mass change")

        duration_s = self.end_epoch_tdb_s - self.start_epoch_tdb_s
        expected_consumed_mass_kg = (
            self.thrust_n * duration_s / (_STANDARD_GRAVITY_M_S2 * self.isp_s)
        )
        flow_tolerance_kg = max(1e-8, 1e-11 * expected_consumed_mass_kg)
        if not math.isclose(
            consumed_mass_kg,
            expected_consumed_mass_kg,
            rel_tol=0.0,
            abs_tol=flow_tolerance_kg,
        ):
            raise ValueError("burn masses must match constant-thrust mass flow")

        expected_delta_v_m_s = _STANDARD_GRAVITY_M_S2 * self.isp_s * math.log(
            self.initial_mass_kg / self.final_mass_kg
        )
        if not math.isclose(
            self.ideal_equivalent_delta_v_m_s,
            expected_delta_v_m_s,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ValueError(
                "ideal_equivalent_delta_v_m_s must match the rocket equation"
            )


@dataclass(frozen=True, slots=True)
class TrajectoryBoundaryDifference:
    """A nonnegative SI difference at one fixed trajectory boundary."""

    label: Literal[
        "departure-ignition",
        "departure-cutoff",
        "arrival-ignition",
        "arrival-cutoff",
    ]
    position_difference_m: float
    velocity_difference_m_s: float
    mass_difference_kg: float

    def __post_init__(self) -> None:
        if self.label not in _BOUNDARY_DIFFERENCE_LABELS:
            raise ValueError("label must identify a fixed trajectory boundary")
        for name in (
            "position_difference_m",
            "velocity_difference_m_s",
            "mass_difference_kg",
        ):
            _finite_number(name, getattr(self, name), nonnegative=True)


def _validate_boundary_differences(
    name: str,
    differences: object,
    *,
    required: bool,
) -> None:
    if not isinstance(differences, tuple) or not all(
        isinstance(item, TrajectoryBoundaryDifference) for item in differences
    ):
        raise ValueError(f"{name} must be a tuple of TrajectoryBoundaryDifference")
    if required:
        labels = tuple(item.label for item in differences)
        if labels != _BOUNDARY_DIFFERENCE_LABELS:
            raise ValueError(f"{name} must contain the four boundaries in fixed order")
    elif differences:
        raise ValueError(f"{name} must be empty unless status is converged")


@dataclass(frozen=True, slots=True)
class PhysicalTrajectoryResult:
    """A classified physical trajectory using SSB/J2000, TDB, and SI units."""

    candidate_id: str
    status: Literal["converged", "mass-infeasible", "targeting-failed"]
    termination_reason: str
    origin: Literal["SSB"]
    orientation: Literal["J2000"]
    time_scale: Literal["TDB seconds since J2000"]
    force_model_id: str
    initial_state: TrajectoryBoundaryState
    target_final_state: TrajectoryBoundaryState
    terminal_state: TrajectoryBoundaryState | None
    burns: tuple[FiniteBurnRecord, ...]
    initial_mass_kg: float
    dry_mass_kg: float
    final_mass_kg: float | None
    propellant_mass_kg: float | None
    ideal_m2_final_mass_kg: float
    required_propellant_mass_kg: float
    available_propellant_mass_kg: float
    propellant_shortfall_kg: float
    terminal_position_error_m: float | None
    terminal_velocity_error_m_s: float | None
    integration_differences: tuple[TrajectoryBoundaryDifference, ...]
    lunar_harmonic_differences: tuple[TrajectoryBoundaryDifference, ...]
    martian_harmonic_differences: tuple[TrajectoryBoundaryDifference, ...]
    correction_iterations: int
    control_attempts: int
    propagation_evaluations: int
    native_arc_propagations: int
    rejection_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        self._validate_identity_and_boundaries()
        self._validate_mass_budget()
        self._validate_counts()

        complete = self.status == "converged" or (
            self.status == "targeting-failed"
            and self.termination_reason == "nonconvergence"
        )
        if complete:
            self._validate_complete_trajectory()
        else:
            self._validate_absent_trajectory()

        converged = self.status == "converged"
        _validate_boundary_differences(
            "integration_differences",
            self.integration_differences,
            required=converged,
        )
        _validate_boundary_differences(
            "lunar_harmonic_differences",
            self.lunar_harmonic_differences,
            required=converged,
        )
        _validate_boundary_differences(
            "martian_harmonic_differences",
            self.martian_harmonic_differences,
            required=converged,
        )
        if converged:
            self._validate_converged_claim()

    def _validate_identity_and_boundaries(self) -> None:
        if not isinstance(
            self.candidate_id, str
        ) or not _CANDIDATE_ID_PATTERN.fullmatch(self.candidate_id):
            raise ValueError("candidate_id must match dIIII-tJJJJ")
        if self.status not in ("converged", "mass-infeasible", "targeting-failed"):
            raise ValueError("status must be a physical trajectory status")
        _nonempty_text("termination_reason", self.termination_reason)
        expected_reasons = {
            "converged": {"target-closure-and-validation-passed"},
            "mass-infeasible": {"preflight-m2-propellant-shortfall"},
            "targeting-failed": {"nonconvergence", "no-safe-complete-trial"},
        }
        if self.termination_reason not in expected_reasons[self.status]:
            raise ValueError("termination_reason must match status")
        if self.origin != "SSB":
            raise ValueError("origin must be SSB")
        if self.orientation != "J2000":
            raise ValueError("orientation must be J2000")
        if self.time_scale != "TDB seconds since J2000":
            raise ValueError("time_scale must be TDB seconds since J2000")
        if self.force_model_id != _PHYSICAL_FORCE_MODEL_ID:
            raise ValueError("force_model_id must identify the pinned M3 force model")
        if not isinstance(self.initial_state, TrajectoryBoundaryState):
            raise ValueError("initial_state must be a TrajectoryBoundaryState")
        if not isinstance(self.target_final_state, TrajectoryBoundaryState):
            raise ValueError("target_final_state must be a TrajectoryBoundaryState")
        if self.target_final_state.epoch_tdb_s <= self.initial_state.epoch_tdb_s:
            raise ValueError("target_final_state must be after initial_state")
        initial_utc = _normalized_utc(
            "initial_state.epoch_utc", self.initial_state.epoch_utc
        )
        target_utc = _normalized_utc(
            "target_final_state.epoch_utc", self.target_final_state.epoch_utc
        )
        if target_utc <= initial_utc:
            raise ValueError("target_final_state UTC must be after initial_state UTC")

    def _validate_mass_budget(self) -> None:
        for name in ("initial_mass_kg", "dry_mass_kg"):
            _finite_number(name, getattr(self, name))
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.initial_mass_kg <= self.dry_mass_kg:
            raise ValueError("initial_mass_kg must be greater than dry_mass_kg")
        for name in (
            "ideal_m2_final_mass_kg",
            "required_propellant_mass_kg",
            "available_propellant_mass_kg",
            "propellant_shortfall_kg",
        ):
            _finite_number(name, getattr(self, name), nonnegative=True)
        if self.ideal_m2_final_mass_kg > self.initial_mass_kg:
            raise ValueError("ideal_m2_final_mass_kg cannot exceed initial_mass_kg")

        required_mass_kg = self.initial_mass_kg - self.ideal_m2_final_mass_kg
        available_mass_kg = self.initial_mass_kg - self.dry_mass_kg
        shortfall_kg = max(0.0, required_mass_kg - available_mass_kg)
        expected = (
            (
                "required_propellant_mass_kg",
                self.required_propellant_mass_kg,
                required_mass_kg,
            ),
            (
                "available_propellant_mass_kg",
                self.available_propellant_mass_kg,
                available_mass_kg,
            ),
            ("propellant_shortfall_kg", self.propellant_shortfall_kg, shortfall_kg),
        )
        for name, actual, expected_value in expected:
            if not _numbers_match(actual, expected_value):
                raise ValueError(f"{name} must match the preflight mass budget")

        if self.status == "mass-infeasible":
            if self.ideal_m2_final_mass_kg >= self.dry_mass_kg or shortfall_kg <= 0:
                raise ValueError(
                    "mass-infeasible requires a preflight propellant shortfall"
                )
        elif self.ideal_m2_final_mass_kg < self.dry_mass_kg or shortfall_kg > 1e-9:
            raise ValueError("propagated statuses require a feasible M2 mass budget")

    def _validate_counts(self) -> None:
        _nonnegative_integer("correction_iterations", self.correction_iterations, 8)
        _nonnegative_integer("control_attempts", self.control_attempts, 73)
        _nonnegative_integer(
            "propagation_evaluations", self.propagation_evaluations, 76
        )
        _nonnegative_integer(
            "native_arc_propagations", self.native_arc_propagations, 228
        )
        diagnostic_evaluations = 3 if self.status == "converged" else 0
        if self.propagation_evaluations > (
            self.control_attempts + diagnostic_evaluations
        ):
            raise ValueError(
                "propagation_evaluations cannot exceed control_attempts "
                "plus status-appropriate diagnostics"
            )
        if not (
            self.propagation_evaluations <= self.native_arc_propagations
            <= 3 * self.propagation_evaluations
        ):
            raise ValueError("native_arc_propagations must match evaluation counts")

        if not isinstance(self.rejection_counts, tuple):
            raise ValueError("rejection_counts must be a sorted tuple")
        keys: list[str] = []
        for item in self.rejection_counts:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("rejection_counts entries must be key/count pairs")
            key, count = item
            _nonempty_text("rejection_counts key", key)
            if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
                raise ValueError("rejection_counts values must be positive integers")
            keys.append(key)
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ValueError("rejection_counts must have unique keys in sorted order")
        if sum(count for _key, count in self.rejection_counts) > self.control_attempts:
            raise ValueError("rejection_counts cannot exceed control_attempts")

        if self.status == "mass-infeasible":
            if any(
                value != 0
                for value in (
                    self.correction_iterations,
                    self.control_attempts,
                    self.propagation_evaluations,
                    self.native_arc_propagations,
                )
            ) or self.rejection_counts:
                raise ValueError(
                    "preflight mass-infeasible results cannot contain work"
                )
        elif self.control_attempts == 0:
            raise ValueError("targeted statuses require at least one control attempt")

        if (
            self.status == "targeting-failed"
            and self.termination_reason == "no-safe-complete-trial"
            and (
                self.correction_iterations != 0
                or self.control_attempts != 1
                or self.propagation_evaluations > 1
            )
        ):
            raise ValueError(
                "no-safe-complete-trial must stop after the single seed attempt"
            )

    def _validate_absent_trajectory(self) -> None:
        absent_values = (
            self.terminal_state,
            self.final_mass_kg,
            self.propellant_mass_kg,
            self.terminal_position_error_m,
            self.terminal_velocity_error_m_s,
        )
        if (
            any(value is not None for value in absent_values)
            or not isinstance(self.burns, tuple)
            or self.burns
        ):
            raise ValueError("this status cannot contain propagated-result values")
        if self.status == "targeting-failed" and not self.rejection_counts:
            raise ValueError("no-safe-complete-trial requires a rejection count")

    def _validate_complete_trajectory(self) -> None:
        if not isinstance(self.terminal_state, TrajectoryBoundaryState):
            raise ValueError("a complete trajectory requires terminal_state")
        if not math.isclose(
            self.terminal_state.epoch_tdb_s,
            self.target_final_state.epoch_tdb_s,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ValueError("terminal_state must use the target cutoff epoch")
        if self.terminal_state.epoch_utc != self.target_final_state.epoch_utc:
            raise ValueError("terminal_state UTC must use the target cutoff epoch")
        if not isinstance(self.burns, tuple) or len(self.burns) != 2 or not all(
            isinstance(burn, FiniteBurnRecord) for burn in self.burns
        ):
            raise ValueError("a complete trajectory requires exactly two burns")
        departure, arrival = self.burns
        if departure.burn_id != "departure" or arrival.burn_id != "arrival":
            raise ValueError("burns must be ordered departure then arrival")
        if not math.isclose(
            departure.start_epoch_tdb_s,
            self.initial_state.epoch_tdb_s,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ValueError("departure burn must start at the initial epoch")
        if not math.isclose(
            arrival.end_epoch_tdb_s,
            self.target_final_state.epoch_tdb_s,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ValueError("arrival burn must end at the target epoch")
        if departure.end_epoch_tdb_s >= arrival.start_epoch_tdb_s:
            raise ValueError("burns must leave a positive coast interval")
        if not _numbers_match(
            departure.initial_mass_kg,
            self.initial_mass_kg,
            absolute_tolerance=1e-9,
            relative_tolerance=0.0,
        ):
            raise ValueError("departure burn must start at initial_mass_kg")
        if not _numbers_match(
            arrival.initial_mass_kg,
            departure.final_mass_kg,
            absolute_tolerance=1e-9,
            relative_tolerance=0.0,
        ):
            raise ValueError("burn masses must remain continuous across coast")
        if not _numbers_match(arrival.thrust_n, departure.thrust_n):
            raise ValueError("both burns must use the same maximum thrust")
        if not _numbers_match(arrival.isp_s, departure.isp_s):
            raise ValueError("both burns must use the same specific impulse")
        minimum_evaluations = 4 if self.status == "converged" else 1
        completed_arc_excess = 8 if self.status == "converged" else 2
        minimum_native_arcs = self.propagation_evaluations + completed_arc_excess
        if (
            self.propagation_evaluations < minimum_evaluations
            or self.native_arc_propagations < minimum_native_arcs
        ):
            raise ValueError(
                "a complete trajectory must include its complete propagation history"
            )

        optional_numbers = (
            ("final_mass_kg", self.final_mass_kg),
            ("propellant_mass_kg", self.propellant_mass_kg),
            ("terminal_position_error_m", self.terminal_position_error_m),
            ("terminal_velocity_error_m_s", self.terminal_velocity_error_m_s),
        )
        for name, value in optional_numbers:
            _finite_number(name, value, nonnegative=True)
        assert self.final_mass_kg is not None
        assert self.propellant_mass_kg is not None
        assert self.terminal_position_error_m is not None
        assert self.terminal_velocity_error_m_s is not None
        position_error_m = math.dist(
            self.terminal_state.position_m,
            self.target_final_state.position_m,
        )
        velocity_error_m_s = math.dist(
            self.terminal_state.velocity_m_s,
            self.target_final_state.velocity_m_s,
        )
        if not _numbers_match(self.terminal_position_error_m, position_error_m):
            raise ValueError(
                "terminal_position_error_m must match terminal and target states"
            )
        if not _numbers_match(
            self.terminal_velocity_error_m_s,
            velocity_error_m_s,
        ):
            raise ValueError(
                "terminal_velocity_error_m_s must match terminal and target states"
            )
        if self.final_mass_kg < self.dry_mass_kg:
            raise ValueError("final_mass_kg cannot be below dry_mass_kg")
        if not _numbers_match(
            self.final_mass_kg,
            arrival.final_mass_kg,
            absolute_tolerance=1e-9,
            relative_tolerance=0.0,
        ):
            raise ValueError("final_mass_kg must match the arrival burn")
        consumed_mass_kg = self.initial_mass_kg - self.final_mass_kg
        if not _numbers_match(
            self.propellant_mass_kg,
            consumed_mass_kg,
            absolute_tolerance=1e-8,
            relative_tolerance=1e-11,
        ) or not _numbers_match(
            self.propellant_mass_kg,
            departure.propellant_mass_kg + arrival.propellant_mass_kg,
            absolute_tolerance=1e-8,
            relative_tolerance=1e-11,
        ):
            raise ValueError("propellant_mass_kg must match the two-burn mass change")
        if (
            self.status == "targeting-failed"
            and self.terminal_position_error_m <= 1000.0
            and self.terminal_velocity_error_m_s <= 0.01
        ):
            raise ValueError("nonconvergence must exceed a target-closure bound")

    def _validate_converged_claim(self) -> None:
        assert self.terminal_position_error_m is not None
        assert self.terminal_velocity_error_m_s is not None
        if self.terminal_position_error_m > 1000.0:
            raise ValueError("converged position error must not exceed 1000 m")
        if self.terminal_velocity_error_m_s > 0.01:
            raise ValueError("converged velocity error must not exceed 0.01 m/s")
        for item in self.integration_differences:
            if (
                item.position_difference_m > 10.0
                or item.velocity_difference_m_s > 0.0001
                or item.mass_difference_kg > 0.000001
            ):
                raise ValueError("integration_differences exceed the numerical budget")
        for item in self.lunar_harmonic_differences:
            if (
                item.position_difference_m > 500.0
                or item.velocity_difference_m_s > 0.0001
            ):
                raise ValueError("lunar_harmonic_differences exceed the model budget")
    def to_dict(self) -> dict[str, Any]:
        """Return a finite JSON-native representation of the result."""

        return json.loads(
            json.dumps(asdict(self), allow_nan=False, default=_json_real)
        )
