"""Verified M2 handoff for physical trajectory refinement."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime
from decimal import Context, Decimal, ROUND_CEILING, localcontext
from fractions import Fraction
from hashlib import file_digest
import math
from numbers import Real
from pathlib import Path
import time
from typing import Any, Literal, NoReturn, cast

from . import ephemeris
from .ephemeris import CartesianState
from .errors import EphemerisError, TrajectoryRefinementError, TransferSearchError
from .models import (
    _PHYSICAL_FORCE_MODEL_ID,
    ImpulsiveTransferCandidate,
    OrbitSpec,
    Scenario,
    SpacecraftSpec,
    TrajectoryBoundaryState,
)
from .transfer import (
    MARS_REFERENCE_RADIUS_M,
    MOON_REFERENCE_RADIUS_M,
    STANDARD_GRAVITY_M_S2,
    _search_impulsive_transfers,
    search_impulsive_transfers,
)


_TIME_TOLERANCE_S = 1e-6
_VELOCITY_TOLERANCE_M_S = 1e-6
_MASS_RELATIVE_TOLERANCE = 1e-12

MOON_ORBIT_SHAPE_RADIUS_M = MOON_REFERENCE_RADIUS_M
MARS_ORBIT_SHAPE_RADIUS_M = MARS_REFERENCE_RADIUS_M
MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2 = 4_902_800_121_846.8
MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2 = 42_828_375_815_756.1
MOON_HARMONIC_NORMALIZATION_RADIUS_M = 1_738_000.0
MARS_HARMONIC_NORMALIZATION_RADIUS_M = 3_396_000.0
MOON_HARMONIC_COEFFICIENT_SHA256 = (
    "3f4652c01db58e14a4e4c67fe8225874d10120a29cbd7699f5068469ef65b21d"
)
MARS_HARMONIC_COEFFICIENT_SHA256 = (
    "d13b31d46862838abe62ebab3cef8209244588abe14e4e5e481c0fb64354e980"
)
PHYSICAL_MODEL_IDENTIFIER = _PHYSICAL_FORCE_MODEL_ID
PHYSICAL_BODY_NAMES = (
    "Sun",
    "Mercury",
    "Venus",
    "Earth",
    "Moon",
    "Mars",
    "Jupiter",
    "Saturn",
)
EPHEMERIS_TIME_STEP_S = 300.0  # Historical v1 qualification tables only.

_FIELD_GM_RELATIVE_TOLERANCE = 1e-15
_DIRECT_GRAVITY_BODY_NAMES = (
    "Sun",
    "Mercury",
    "Venus",
    "Earth",
    "Jupiter",
    "Saturn",
)
_HARMONIC_GRAVITY_BODY_NAMES = ("Moon", "Mars")
_POINT_MASS_GRAVITY_TYPE = "point-mass-gravity"
_SPHERICAL_HARMONIC_GRAVITY_TYPE = "spherical-harmonic-gravity"
SPACECRAFT_BODY_NAME = "Spacecraft"
SUN_LUMINOSITY_W = 3.828e26
_SPEED_OF_LIGHT_M_S = 299_792_458.0
SOLAR_RADIATION_OCCULTING_BODY_NAMES = ("Moon", "Earth", "Mars")
_SOLAR_RADIATION_SOURCE_BODY = "Sun"
_SOLAR_RADIATION_PRESSURE_TYPE = "cannonball-radiation-pressure"
_RELATIVITY_SOURCE_BODY = "Sun"
_RELATIVISTIC_ACCELERATION_TYPE = "schwarzschild-relativistic-correction"
_PPN_BETA = 1.0
_PPN_GAMMA = 1.0
_COLLISION_PCK_KERNEL_NAME = "pck00010.tpc"
_COLLISION_PCK_EXPECTED_SHA256 = (
    "59468328349aa730d18bf1f8d7e86efe6e40b75dfb921908f99321b3a7a701d2"
)
_COLLISION_RADIUS_TOLERANCE_M = 0.001
_TNW_DEGENERACY_THRESHOLD = 1e-12
_VECTOR_TOLERANCE = 1e-12
_BURN_CENTRAL_BODIES = {
    "departure": "Moon",
    "arrival": "Mars",
}
_PINNED_COLLISION_RADII_M = (
    ("Sun", (696_000_000.0, 696_000_000.0, 696_000_000.0)),
    ("Mercury", (2_439_700.0, 2_439_700.0, 2_439_700.0)),
    ("Venus", (6_051_800.0, 6_051_800.0, 6_051_800.0)),
    ("Earth", (6_378_136.6, 6_378_136.6, 6_356_751.9)),
    ("Moon", (1_737_400.0, 1_737_400.0, 1_737_400.0)),
    ("Mars", (3_396_190.0, 3_396_190.0, 3_376_200.0)),
    ("Jupiter", (71_492_000.0, 71_492_000.0, 66_854_000.0)),
    ("Saturn", (60_268_000.0, 60_268_000.0, 54_364_000.0)),
)

Cartesian6 = tuple[float, float, float, float, float, float]
Vector3 = tuple[float, float, float]
StateQuery = Callable[[str, float], CartesianState]
ElementConverter = Callable[
    [float, float, float, float, float, float, float], object
]


@dataclass(slots=True)
class _RefinementBudget:
    """Mutable internal work accounting, not a public scientific result.

    Construct once before handoff/resources. Check around native work; this
    cooperative deadline cannot interrupt a native call already in progress.
    """

    candidate_id: str
    runtime_seconds: float
    monotonic: Callable[[], float] = time.monotonic
    # Explicit override for bounded safety qualification; production keeps 3.
    max_arcs_per_evaluation: int = dataclass_field(default=3, kw_only=True)
    deadline_monotonic_s: float = dataclass_field(init=False)
    control_attempts: int = dataclass_field(default=0, init=False)
    propagation_evaluations: int = dataclass_field(default=0, init=False)
    native_arc_propagations: int = dataclass_field(default=0, init=False)
    _arcs_in_evaluation: int = dataclass_field(default=0, init=False)
    _last_monotonic_s: float = dataclass_field(init=False)

    def __post_init__(self) -> None:
        try:
            if (isinstance(self.max_arcs_per_evaluation, bool)
                    or not isinstance(self.max_arcs_per_evaluation, int)
                    or not 1 <= self.max_arcs_per_evaluation <= 32):
                raise ValueError("max_arcs_per_evaluation must be an integer in [1, 32]")
            self.runtime_seconds = _positive_finite("runtime_seconds", self.runtime_seconds)
            self._last_monotonic_s = _finite_float("monotonic clock", self.monotonic())
            self.deadline_monotonic_s = _finite_float(
                "deadline_monotonic_s", self._last_monotonic_s + self.runtime_seconds,
            )
        except (TypeError, ValueError) as exc:
            _raise_refinement_error(self.candidate_id, "budget-construction", str(exc), exc)

    def _fail(self, operation: str, detail: str) -> NoReturn:
        cause = RuntimeError(detail)
        _raise_refinement_error(
            self.candidate_id, operation,
            f"{detail}; runtime limit {self.runtime_seconds:g} s; "
            f"control_attempts={self.control_attempts}, "
            f"propagation_evaluations={self.propagation_evaluations}, "
            f"native_arc_propagations={self.native_arc_propagations}; "
            "no partial result is returned", cause,
        )

    def check(self) -> None:
        try:
            now_s = _finite_float("monotonic clock", self.monotonic())
        except (TypeError, ValueError) as exc:
            _raise_refinement_error(self.candidate_id, "deadline", str(exc), exc)
        if now_s < self._last_monotonic_s:
            self._fail("deadline", "monotonic clock moved backward")
        self._last_monotonic_s = now_s
        if now_s >= self.deadline_monotonic_s:
            self._fail("deadline", "shared deadline reached")

    def begin_control(self) -> None:
        """Count before analytic validation, even if the control is rejected."""
        self.check()
        if self.control_attempts >= 73:
            self._fail("work-limit", "control-attempt limit 73 reached")
        self.control_attempts += 1

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        """Count immediately before a native arc, including early-terminated arcs."""
        self.check()
        if not isinstance(first_in_evaluation, bool):
            self._fail("work-limit", "first_in_evaluation must be boolean")
        if self.native_arc_propagations >= 228:
            self._fail("work-limit", "native-arc limit 228 reached")
        if first_in_evaluation:
            if self.propagation_evaluations >= 76:
                self._fail("work-limit", "propagation-evaluation limit 76 reached")
            self.propagation_evaluations += 1
            self._arcs_in_evaluation = 0
        elif not 1 <= self._arcs_in_evaluation < self.max_arcs_per_evaluation:
            self._fail("work-limit", "continuation requires a started evaluation below "
                       f"its limit {self.max_arcs_per_evaluation}")
        self._arcs_in_evaluation += 1
        self.native_arc_propagations += 1


@dataclass(frozen=True, slots=True)
class _HarmonicFieldSpec:
    body: str
    model: str
    file_name: str
    degree: int
    order: int
    expected_sha256: str
    gravitational_parameter_m3_s2: float
    normalization_radius_m: float
    orbit_shape_radius_m: float
    associated_frame: str


@dataclass(frozen=True, slots=True)
class _HarmonicFieldResource:
    body: str
    model: str
    file_name: str
    degree: int
    order: int
    expected_sha256: str
    actual_sha256: str
    associated_frame: str
    rotation_base_frame: str
    rotation_target_frame: str
    gravitational_parameter_m3_s2: float
    normalization_radius_m: float
    orbit_shape_radius_m: float


@dataclass(frozen=True, slots=True)
class _GravityAccelerationResource:
    source_body: str
    acceleration_type: str
    degree: int | None
    order: int | None


@dataclass(frozen=True, slots=True)
class _SolarRadiationPressureResource:
    source_body: str
    target_body: str
    luminosity_w: float
    reference_area_m2: float
    reflectivity_coefficient: float
    initial_mass_kg: float
    occulting_bodies: tuple[str, ...]
    acceleration_type: str
    uses_current_body_mass: bool


@dataclass(frozen=True, slots=True)
class _SolarRadiationPressureSetup:
    source_settings: Any
    target_settings: Any
    acceleration_settings_by_source: dict[str, tuple[Any, ...]]
    resource: _SolarRadiationPressureResource


@dataclass(frozen=True, slots=True)
class _RelativityResource:
    source_body: str
    target_body: str
    acceleration_type: str
    ppn_beta: float
    ppn_gamma: float
    schwarzschild_enabled: bool
    lense_thirring_enabled: bool
    de_sitter_enabled: bool
    einstein_infeld_hoffmann_enabled: bool


@dataclass(frozen=True, slots=True)
class _CollisionSurfaceResource:
    body: str
    expected_radius_vector_m: tuple[float, float, float]
    actual_radius_vector_m: tuple[float, float, float]
    guard_radius_m: float


@dataclass(frozen=True, slots=True)
class _CollisionResource:
    kernel_name: str
    expected_sha256: str
    actual_sha256: str
    radius_tolerance_m: float
    surfaces: tuple[_CollisionSurfaceResource, ...]


@dataclass(frozen=True, slots=True)
class _TnwBasis:
    t_hat: Vector3
    n_hat: Vector3
    w_hat: Vector3

    def __post_init__(self) -> None:
        for name in ("t_hat", "n_hat", "w_hat"):
            object.__setattr__(
                self, name, _finite_vector3_values(getattr(self, name), name),
            )
        _validate_tnw_basis(self)


@dataclass(frozen=True, slots=True)
class _PhysicalEnvironment:
    model_id: str
    initial_epoch_tdb_s: float
    final_epoch_tdb_s: float
    origin: str
    orientation: str
    bodies: Any
    harmonic_fields: tuple[_HarmonicFieldResource, ...]
    gravity_acceleration_settings: dict[str, tuple[Any, ...]]
    gravity_acceleration_inventory: tuple[_GravityAccelerationResource, ...]
    solar_radiation_pressure_acceleration_settings: dict[
        str, tuple[Any, ...]
    ]
    solar_radiation_pressure: _SolarRadiationPressureResource
    relativistic_acceleration_settings: dict[str, tuple[Any, ...]]
    relativity: _RelativityResource
    collision_resource: _CollisionResource


_HARMONIC_FIELD_SPECS = (
    _HarmonicFieldSpec(
        body="Moon",
        model="gggrx1200",
        file_name="gggrx_1200l_sha.tab",
        degree=200,
        order=200,
        expected_sha256=MOON_HARMONIC_COEFFICIENT_SHA256,
        gravitational_parameter_m3_s2=(
            MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2
        ),
        normalization_radius_m=MOON_HARMONIC_NORMALIZATION_RADIUS_M,
        orbit_shape_radius_m=MOON_ORBIT_SHAPE_RADIUS_M,
        associated_frame="IAU_Moon",
    ),
    _HarmonicFieldSpec(
        body="Mars",
        model="jgmro120d",
        file_name="jgmro120d.txt",
        degree=120,
        order=120,
        expected_sha256=MARS_HARMONIC_COEFFICIENT_SHA256,
        gravitational_parameter_m3_s2=(
            MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2
        ),
        normalization_radius_m=MARS_HARMONIC_NORMALIZATION_RADIUS_M,
        orbit_shape_radius_m=MARS_ORBIT_SHAPE_RADIUS_M,
        associated_frame="IAU_Mars",
    ),
)


def _raise_refinement_error(
    candidate_id: object,
    operation: str,
    detail: str,
    cause: Exception,
) -> NoReturn:
    raise TrajectoryRefinementError(
        f"Candidate {candidate_id!r} failed during {operation}: {detail}"
    ) from cause


def _raise_handoff_error(
    candidate_id: object,
    detail: str,
    cause: Exception,
) -> NoReturn:
    _raise_refinement_error(
        candidate_id,
        "candidate-verification",
        detail,
        cause,
    )


def _tudat_keplerian_to_cartesian(
    semi_major_axis_m: float,
    eccentricity: float,
    inclination_rad: float,
    argument_of_periapsis_rad: float,
    raan_rad: float,
    true_anomaly_rad: float,
    gravitational_parameter_m3_s2: float,
) -> object:
    """Call TudatPy lazily so importing the M3 API has no kernel side effects."""

    try:
        from tudatpy.astro import element_conversion

        return element_conversion.keplerian_to_cartesian_elementwise(
            semi_major_axis_m,
            eccentricity,
            inclination_rad,
            argument_of_periapsis_rad,
            raan_rad,
            true_anomaly_rad,
            gravitational_parameter_m3_s2,
        )
    except Exception as exc:
        raise RuntimeError("TudatPy Keplerian conversion failed") from exc


def _finite_cartesian_values(raw_state: object, source: str) -> Cartesian6:
    try:
        flatten = getattr(raw_state, "reshape", None)
        flat_state = flatten(-1) if callable(flatten) else raw_state
        if not isinstance(flat_state, Iterable):
            raise TypeError("state is not iterable")
        raw_values = tuple(flat_state)
    except Exception as exc:
        raise ValueError(f"{source} must return six numeric values") from exc
    if len(raw_values) != 6 or any(
        not isinstance(value, Real) or isinstance(value, bool)
        for value in raw_values
    ):
        raise ValueError(f"{source} must return six numeric values")
    try:
        values = tuple(float(value) for value in raw_values)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{source} must return six numeric values") from exc
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"{source} must return six finite values")
    return cast(Cartesian6, values)


def _finite_vector3_values(
    raw_vector: object,
    source: str,
) -> tuple[float, float, float]:
    try:
        if not isinstance(raw_vector, Iterable):
            raise TypeError("vector is not iterable")
        raw_values = tuple(raw_vector)
    except Exception as exc:
        raise ValueError(f"{source} must contain three numeric values") from exc
    if len(raw_values) != 3 or any(
        not isinstance(value, Real) or isinstance(value, bool)
        for value in raw_values
    ):
        raise ValueError(f"{source} must contain three numeric values")
    try:
        values = tuple(float(value) for value in raw_values)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{source} must contain three numeric values") from exc
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"{source} must contain three finite values")
    return cast(tuple[float, float, float], values)


def _finite_float(name: str, value: object) -> float:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def _positive_finite(name: str, value: object) -> float:
    number = _finite_float(name, value)
    if number <= 0.0:
        raise ValueError(f"{name} must be a positive finite number")
    return number


def _orbit_to_body_relative_state(
    orbit: OrbitSpec,
    shape_radius_m: float,
    gravitational_parameter_m3_s2: float,
    *,
    element_converter: ElementConverter | None = None,
) -> Cartesian6:
    """Convert body-relative J2000 osculating elements to an SI state."""

    shape_radius_m = _positive_finite("shape_radius_m", shape_radius_m)
    gravitational_parameter_m3_s2 = _positive_finite(
        "gravitational_parameter_m3_s2",
        gravitational_parameter_m3_s2,
    )
    periapsis_radius_m = shape_radius_m + orbit.periapsis_altitude_m
    apoapsis_radius_m = shape_radius_m + orbit.apoapsis_altitude_m
    semi_major_axis_m = (periapsis_radius_m + apoapsis_radius_m) / 2.0

    argument_of_periapsis_rad = orbit.argument_of_periapsis_rad
    true_anomaly_rad = orbit.true_anomaly_rad
    if orbit.eccentricity == 0.0:
        true_anomaly_rad = (argument_of_periapsis_rad + true_anomaly_rad) % math.tau
        argument_of_periapsis_rad = 0.0

    converter = element_converter or _tudat_keplerian_to_cartesian
    try:
        raw_state = converter(
            semi_major_axis_m,
            orbit.eccentricity,
            orbit.inclination_rad,
            argument_of_periapsis_rad,
            orbit.raan_rad,
            true_anomaly_rad,
            gravitational_parameter_m3_s2,
        )
    except Exception as exc:
        raise RuntimeError("Keplerian element conversion failed") from exc
    state = _finite_cartesian_values(raw_state, "element conversion")
    if math.hypot(*state[:3]) == 0.0:
        raise ValueError("element conversion produced a body-centre position")
    return state


def _build_boundary_state(
    *,
    label: str,
    expected_body: str,
    orbit: OrbitSpec,
    epoch_utc: str,
    epoch_tdb_s: float,
    shape_radius_m: float,
    gravitational_parameter_m3_s2: float,
    state_query: StateQuery,
    element_converter: ElementConverter | None,
) -> TrajectoryBoundaryState:
    if orbit.central_body != expected_body:
        raise ValueError(
            f"{label} orbit central_body must be {expected_body!r}, "
            f"got {orbit.central_body!r}"
        )
    relative_state = _orbit_to_body_relative_state(
        orbit,
        shape_radius_m,
        gravitational_parameter_m3_s2,
        element_converter=element_converter,
    )
    body_state = state_query(expected_body, epoch_tdb_s)
    if not isinstance(body_state, CartesianState):
        raise TypeError("state query must return CartesianState")
    if (
        body_state.body != expected_body
        or body_state.epoch_utc != epoch_utc
        or body_state.epoch_tdb_s != epoch_tdb_s
    ):
        raise ValueError(
            "state query returned the wrong body or exact UTC/TDB epoch"
        )
    return TrajectoryBoundaryState(
        label=label,
        epoch_utc=epoch_utc,
        epoch_tdb_s=epoch_tdb_s,
        origin="SSB",
        orientation="J2000",
        position_m=(
            body_state.position_m[0] + relative_state[0],
            body_state.position_m[1] + relative_state[1],
            body_state.position_m[2] + relative_state[2],
        ),
        velocity_m_s=(
            body_state.velocity_m_s[0] + relative_state[3],
            body_state.velocity_m_s[1] + relative_state[4],
            body_state.velocity_m_s[2] + relative_state[5],
        ),
    )


def _build_boundary_states(
    scenario: Scenario,
    candidate: ImpulsiveTransferCandidate,
    moon_gravitational_parameter_m3_s2: float,
    mars_gravitational_parameter_m3_s2: float,
    *,
    state_query: StateQuery | None = None,
    element_converter: ElementConverter | None = None,
) -> tuple[TrajectoryBoundaryState, TrajectoryBoundaryState]:
    """Build departure-ignition and arrival-cutoff SSB/J2000 states."""

    query = state_query or ephemeris._query_body_state_tdb
    definitions = (
        (
            "departure-ignition",
            "Moon",
            scenario.departure_orbit,
            candidate.departure_epoch_utc,
            candidate.departure_epoch_tdb_s,
            MOON_ORBIT_SHAPE_RADIUS_M,
            moon_gravitational_parameter_m3_s2,
        ),
        (
            "arrival-cutoff",
            "Mars",
            scenario.target_orbit,
            candidate.arrival_epoch_utc,
            candidate.arrival_epoch_tdb_s,
            MARS_ORBIT_SHAPE_RADIUS_M,
            mars_gravitational_parameter_m3_s2,
        ),
    )
    boundaries = []
    for label, body, orbit, epoch_utc, epoch_tdb_s, shape_radius_m, gm in definitions:
        try:
            boundaries.append(
                _build_boundary_state(
                    label=label,
                    expected_body=body,
                    orbit=orbit,
                    epoch_utc=epoch_utc,
                    epoch_tdb_s=epoch_tdb_s,
                    shape_radius_m=shape_radius_m,
                    gravitational_parameter_m3_s2=gm,
                    state_query=query,
                    element_converter=element_converter,
                )
            )
        except (EphemerisError, RuntimeError, TypeError, ValueError) as exc:
            _raise_refinement_error(
                candidate.candidate_id,
                "boundary-state-construction",
                f"{label} for {body!r} at TDB epoch {epoch_tdb_s!r}: {exc}",
                exc,
            )
    return boundaries[0], boundaries[1]


def _import_tudat_environment_setup() -> Any:
    try:
        from tudatpy.dynamics import environment_setup
    except Exception as exc:
        raise RuntimeError(
            "TudatPy environment setup is unavailable in the pinned environment"
        ) from exc
    return environment_setup


def _import_tudat_propagation_setup() -> Any:
    try:
        from tudatpy.dynamics import propagation_setup
    except Exception as exc:
        raise RuntimeError(
            "TudatPy propagation setup is unavailable in the pinned environment"
        ) from exc
    return propagation_setup


def _import_tudat_parameters_setup() -> Any:
    try:
        from tudatpy.dynamics import parameters_setup
    except Exception as exc:
        raise RuntimeError(
            "TudatPy parameter setup is unavailable in the pinned environment"
        ) from exc
    return parameters_setup


def _default_gravity_models_path() -> Path:
    try:
        from tudatpy import data

        return Path(data.get_gravity_models_path())
    except Exception as exc:
        raise RuntimeError("Tudat gravity-resource path is unavailable") from exc


def _coefficient_sha256(path: Path) -> str:
    try:
        with path.open("rb") as stream:
            return file_digest(stream, "sha256").hexdigest()
    except OSError as exc:
        raise OSError(f"missing or unreadable coefficient file {path}") from exc


def _verified_coefficient_files(
    gravity_models_path: Path,
) -> tuple[tuple[_HarmonicFieldSpec, Path, str], ...]:
    verified = []
    for spec in _HARMONIC_FIELD_SPECS:
        path = gravity_models_path / spec.body / spec.file_name
        actual_sha256 = _coefficient_sha256(path)
        if actual_sha256 != spec.expected_sha256:
            raise ValueError(
                f"{spec.body} {spec.model} coefficient SHA-256 mismatch for "
                f"{path}: expected {spec.expected_sha256}, got {actual_sha256}"
            )
        verified.append((spec, path, actual_sha256))
    return tuple(verified)


def _pinned_pck_sha256(kernel_metadata: object) -> str:
    if not isinstance(kernel_metadata, dict):
        raise ValueError("SPICE kernel manifest must be an object")
    kernels = kernel_metadata.get("kernels")
    if not isinstance(kernels, list):
        raise ValueError("SPICE kernel manifest must contain a kernel list")
    matches = [
        entry
        for entry in kernels
        if isinstance(entry, dict)
        and entry.get("name") == _COLLISION_PCK_KERNEL_NAME
    ]
    if not matches:
        raise ValueError(
            f"required SPICE kernel {_COLLISION_PCK_KERNEL_NAME!r} is missing"
        )
    hashes = tuple(entry.get("sha256") for entry in matches)
    if any(digest != _COLLISION_PCK_EXPECTED_SHA256 for digest in hashes):
        raise ValueError(
            f"{_COLLISION_PCK_KERNEL_NAME} SHA-256 mismatch: expected "
            f"{_COLLISION_PCK_EXPECTED_SHA256}, got {hashes!r}"
        )
    return _COLLISION_PCK_EXPECTED_SHA256


def _build_collision_resource(candidate_id: object) -> _CollisionResource:
    """Verify the pinned PCK and build exact conservative collision spheres."""

    try:
        metadata = ephemeris.kernel_metadata()
    except EphemerisError as exc:
        _raise_refinement_error(
            candidate_id,
            "resource-validation",
            f"SPICE kernel inventory failed: {exc}",
            exc,
        )
    try:
        actual_sha256 = _pinned_pck_sha256(metadata)
    except (TypeError, ValueError) as exc:
        _raise_refinement_error(
            candidate_id,
            "resource-validation",
            str(exc),
            exc,
        )

    try:
        spice = ephemeris._ensure_standard_kernels()
    except EphemerisError as exc:
        _raise_refinement_error(
            candidate_id,
            "resource-validation",
            f"SPICE radius lookup initialization failed: {exc}",
            exc,
        )

    surfaces = []
    for body, expected_radius_vector_m in _PINNED_COLLISION_RADII_M:
        try:
            has_radii = spice.check_body_property_in_kernel_pool(body, "RADII")
        except Exception as exc:
            _raise_refinement_error(
                candidate_id,
                "resource-validation",
                f"{body} SPICE RADII availability check failed: {exc}",
                exc,
            )
        if not has_radii:
            cause = ValueError(f"SPICE RADII are missing for {body}")
            _raise_refinement_error(
                candidate_id,
                "resource-validation",
                str(cause),
                cause,
            )
        try:
            raw_radius_vector_km = spice.get_body_properties(body, "RADII", 3)
        except Exception as exc:
            _raise_refinement_error(
                candidate_id,
                "resource-validation",
                f"{body} SPICE RADII read failed: {exc}",
                exc,
            )
        try:
            radius_vector_km = _finite_vector3_values(
                raw_radius_vector_km,
                f"{body} SPICE RADII",
            )
            actual_radius_vector_m = _finite_vector3_values(
                tuple(value * 1_000.0 for value in radius_vector_km),
                f"{body} SPICE RADII in meters",
            )
            if any(value <= 0.0 for value in actual_radius_vector_m):
                raise ValueError(
                    f"{body} SPICE RADII must contain three positive values"
                )
            for actual, expected in zip(
                actual_radius_vector_m,
                expected_radius_vector_m,
                strict=True,
            ):
                if not math.isclose(
                    actual,
                    expected,
                    rel_tol=0.0,
                    abs_tol=_COLLISION_RADIUS_TOLERANCE_M,
                ):
                    raise ValueError(
                        f"{body} SPICE RADII drift: expected "
                        f"{expected_radius_vector_m}, got "
                        f"{actual_radius_vector_m}"
                    )
        except (OverflowError, TypeError, ValueError) as exc:
            _raise_refinement_error(
                candidate_id,
                "resource-validation",
                str(exc),
                exc,
            )
        surfaces.append(
            _CollisionSurfaceResource(
                body=body,
                expected_radius_vector_m=expected_radius_vector_m,
                actual_radius_vector_m=actual_radius_vector_m,
                guard_radius_m=max(actual_radius_vector_m),
            )
        )

    return _CollisionResource(
        kernel_name=_COLLISION_PCK_KERNEL_NAME,
        expected_sha256=_COLLISION_PCK_EXPECTED_SHA256,
        actual_sha256=actual_sha256,
        radius_tolerance_m=_COLLISION_RADIUS_TOLERANCE_M,
        surfaces=tuple(surfaces),
    )


def _collision_resource_manifest(resource: _CollisionResource) -> dict[str, Any]:
    return {
        "pck_kernel": {
            "name": resource.kernel_name,
            "expected_sha256": resource.expected_sha256,
            "actual_sha256": resource.actual_sha256,
        },
        "radius_tolerance_m": resource.radius_tolerance_m,
        "radii_unit": "m",
        "impact_condition": "distance_m <= guard_radius_m",
        "surfaces": [
            {
                "body": surface.body,
                "expected_radius_vector_m": list(
                    surface.expected_radius_vector_m
                ),
                "actual_radius_vector_m": list(surface.actual_radius_vector_m),
                "guard_radius_m": surface.guard_radius_m,
            }
            for surface in resource.surfaces
        ],
    }


def _crosses_collision_surface(
    spacecraft_position_m: object,
    body_position_m: object,
    guard_radius_m: object,
) -> bool:
    spacecraft_position = _finite_vector3_values(
        spacecraft_position_m,
        "spacecraft_position_m",
    )
    body_position = _finite_vector3_values(body_position_m, "body_position_m")
    guard_radius = _positive_finite("guard_radius_m", guard_radius_m)
    return math.dist(spacecraft_position, body_position) <= guard_radius


def _classify_trial_state(
    candidate_id: object,
    state: object,
    mass_kg: object,
    dry_mass_kg: object,
    body_positions_m: dict[str, object],
    collision_resource: _CollisionResource,
) -> str | None:
    """Classify one SI/SSB/J2000 sample, never retain or clamp its state.

    Validate all inputs before rejection. Dry mass takes precedence, then the
    first impact in physical-body order. None means this sample is safe only;
    it does not establish safety between samples or select a public status.
    """
    try:
        cartesian = _finite_cartesian_values(state, "trial_state")
        mass = _finite_float("mass_kg", mass_kg)
        dry_mass = _positive_finite("dry_mass_kg", dry_mass_kg)
        if set(body_positions_m) != set(PHYSICAL_BODY_NAMES):
            raise ValueError("body_positions_m must contain exactly eight physical bodies")
        if tuple(surface.body for surface in collision_resource.surfaces) != (
            PHYSICAL_BODY_NAMES
        ):
            raise ValueError("collision surfaces must follow exact physical-body order")
        impacts = []
        for surface in collision_resource.surfaces:
            position = _finite_vector3_values(
                body_positions_m[surface.body], f"{surface.body}.position_m",
            )
            if _crosses_collision_surface(
                cartesian[:3], position, surface.guard_radius_m,
            ):
                impacts.append(surface.body)
    except (TypeError, ValueError) as exc:
        _raise_refinement_error(candidate_id, "trial-safety", str(exc), exc)
    if mass < dry_mass:
        return "rejected-dry-mass"
    if impacts:
        return f"rejected-impact:{impacts[0]}"
    return None


def _classify_environment_trial_state(
    budget: _RefinementBudget,
    environment: _PhysicalEnvironment,
    epoch_tdb_s: object,
    state: object,
    mass_kg: object,
    dry_mass_kg: object,
) -> str | None:
    """Check one SI/SSB/J2000 state against the environment at its TDB epoch.

    Suitable for pre-arc checks without starting/counting a native arc. None
    establishes safety only at this sample, never between integration steps.
    """
    budget.check()
    try:
        epoch = _finite_float("epoch_tdb_s", epoch_tdb_s)
        cartesian = _finite_cartesian_values(state, "trial_state")
        mass = _finite_float("mass_kg", mass_kg)
        dry_mass = _positive_finite("dry_mass_kg", dry_mass_kg)
        if (environment.origin, environment.orientation) != ("SSB", "J2000"):
            raise ValueError("physical environment must use SSB/J2000")
        if not environment.initial_epoch_tdb_s <= epoch <= environment.final_epoch_tdb_s:
            raise ValueError("epoch_tdb_s is outside the physical environment interval")
    except (TypeError, ValueError) as exc:
        _raise_refinement_error(budget.candidate_id, "trial-safety", str(exc), exc)
    positions: dict[str, object] = {}
    for body in PHYSICAL_BODY_NAMES:
        budget.check()
        try:
            raw = environment.bodies.get(body).ephemeris.cartesian_state(epoch)
        except Exception as exc:
            _raise_refinement_error(
                budget.candidate_id, "trial-safety",
                f"{body} at {epoch} TDB s: environment ephemeris failed: {exc}", exc,
            )
        budget.check()
        try:
            positions[body] = _finite_cartesian_values(raw, f"{body} ephemeris")[:3]
        except (TypeError, ValueError) as exc:
            _raise_refinement_error(budget.candidate_id, "trial-safety", str(exc), exc)
    result = _classify_trial_state(
        budget.candidate_id, cartesian, mass, dry_mass, positions,
        environment.collision_resource,
    )
    budget.check()
    return result


def _dot_product(left: Vector3, right: Vector3) -> float:
    return sum(left[index] * right[index] for index in range(3))


def _cross_product(left: Vector3, right: Vector3) -> Vector3:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _validate_tnw_basis(basis: _TnwBasis) -> None:
    if not isinstance(basis, _TnwBasis):
        raise ValueError("basis must be a _TnwBasis")
    axes = (
        _finite_vector3_values(basis.t_hat, "TNW T axis"),
        _finite_vector3_values(basis.n_hat, "TNW N axis"),
        _finite_vector3_values(basis.w_hat, "TNW W axis"),
    )
    if any(
        not math.isclose(
            math.hypot(*axis),
            1.0,
            rel_tol=0.0,
            abs_tol=_VECTOR_TOLERANCE,
        )
        for axis in axes
    ):
        raise ValueError("TNW basis axes must be unit vectors")
    if any(
        abs(_dot_product(axes[left], axes[right])) > _VECTOR_TOLERANCE
        for left, right in ((0, 1), (0, 2), (1, 2))
    ):
        raise ValueError("TNW basis axes must be mutually orthogonal")
    if math.dist(_cross_product(axes[0], axes[1]), axes[2]) > _VECTOR_TOLERANCE:
        raise ValueError("TNW basis must satisfy T cross N equals W")


def _build_tnw_basis(
    relative_position_m: object,
    relative_velocity_m_s: object,
) -> _TnwBasis:
    """Build a right-handed central-body-relative TNW basis."""

    position = _finite_vector3_values(
        relative_position_m,
        "relative_position_m",
    )
    velocity = _finite_vector3_values(
        relative_velocity_m_s,
        "relative_velocity_m_s",
    )
    position_norm = math.hypot(*position)
    velocity_norm = math.hypot(*velocity)
    if not math.isfinite(position_norm) or position_norm == 0.0:
        raise ValueError("relative_position_m must have finite nonzero norm")
    if not math.isfinite(velocity_norm) or velocity_norm == 0.0:
        raise ValueError("relative_velocity_m_s must have finite nonzero norm")

    position_hat = cast(
        Vector3,
        tuple(value / position_norm for value in position),
    )
    t_hat = cast(Vector3, tuple(value / velocity_norm for value in velocity))
    radial_cross_track = _cross_product(position_hat, t_hat)
    separation = math.hypot(*radial_cross_track)
    if separation <= _TNW_DEGENERACY_THRESHOLD:
        raise ValueError(
            "TNW basis is degenerate: normalized cross-product norm must be "
            f"greater than {_TNW_DEGENERACY_THRESHOLD}"
        )
    w_hat = cast(
        Vector3,
        tuple(value / separation for value in radial_cross_track),
    )
    n_axis = _cross_product(w_hat, t_hat)
    n_norm = math.hypot(*n_axis)
    n_hat = cast(Vector3, tuple(value / n_norm for value in n_axis))
    return _TnwBasis(t_hat=t_hat, n_hat=n_hat, w_hat=w_hat)


def _direction_tnw_from_angles(
    azimuth_rad: object,
    elevation_rad: object,
) -> Vector3:
    azimuth = _finite_float("azimuth_rad", azimuth_rad)
    elevation = _finite_float("elevation_rad", elevation_rad)
    cosine_elevation = math.cos(elevation)
    return (
        cosine_elevation * math.cos(azimuth),
        cosine_elevation * math.sin(azimuth),
        math.sin(elevation),
    )


def _map_tnw_direction_to_inertial(
    basis: _TnwBasis,
    direction_tnw: object,
) -> Vector3:
    _validate_tnw_basis(basis)
    direction = _finite_vector3_values(direction_tnw, "direction_tnw")
    if not math.isclose(
        math.hypot(*direction),
        1.0,
        rel_tol=0.0,
        abs_tol=_VECTOR_TOLERANCE,
    ):
        raise ValueError("direction_tnw must be a unit vector")
    inertial = cast(
        Vector3,
        tuple(
            direction[0] * basis.t_hat[index]
            + direction[1] * basis.n_hat[index]
            + direction[2] * basis.w_hat[index]
            for index in range(3)
        ),
    )
    inertial = _finite_vector3_values(inertial, "inertial thrust direction")
    inertial_norm = math.hypot(*inertial)
    if not math.isclose(
        inertial_norm,
        1.0,
        rel_tol=0.0,
        abs_tol=_VECTOR_TOLERANCE,
    ):
        raise ValueError("inertial thrust direction must be a unit vector")
    return cast(Vector3, tuple(value / inertial_norm for value in inertial))


def _build_tnw_direction_callback(
    candidate_id: object,
    bodies: Any,
    burn_id: Literal["departure", "arrival"],
    azimuth_rad: object,
    elevation_rad: object,
) -> Callable[[float], Vector3]:
    """Return guidance that rebuilds the selected relative TNW frame per call."""

    if not isinstance(burn_id, str) or burn_id not in _BURN_CENTRAL_BODIES:
        cause = ValueError("burn_id must be departure or arrival")
        _raise_refinement_error(
            candidate_id,
            "finite-burn-guidance",
            str(cause),
            cause,
        )
    central_body = _BURN_CENTRAL_BODIES[burn_id]
    try:
        direction_tnw = _direction_tnw_from_angles(
            azimuth_rad,
            elevation_rad,
        )
    except ValueError as exc:
        _raise_refinement_error(
            candidate_id,
            "finite-burn-guidance",
            f"{burn_id} burn relative to {central_body}: {exc}",
            exc,
        )

    def direction_callback(epoch_tdb_s: float) -> Vector3:
        context = (
            f"{burn_id} burn relative to {central_body} at TDB epoch "
            f"{epoch_tdb_s!r}"
        )
        try:
            spacecraft_state_raw = bodies.get(SPACECRAFT_BODY_NAME).state
            central_body_state_raw = bodies.get(central_body).state
        except Exception as exc:
            _raise_refinement_error(
                candidate_id,
                "finite-burn-guidance",
                f"{context}: current body state is unavailable: {exc}",
                exc,
            )
        try:
            spacecraft_state = _finite_cartesian_values(
                spacecraft_state_raw,
                f"{SPACECRAFT_BODY_NAME} current state",
            )
            central_body_state = _finite_cartesian_values(
                central_body_state_raw,
                f"{central_body} current state",
            )
            relative_position_m = cast(
                Vector3,
                tuple(
                    spacecraft_state[index] - central_body_state[index]
                    for index in range(3)
                ),
            )
            relative_velocity_m_s = cast(
                Vector3,
                tuple(
                    spacecraft_state[index] - central_body_state[index]
                    for index in range(3, 6)
                ),
            )
            basis = _build_tnw_basis(
                relative_position_m,
                relative_velocity_m_s,
            )
            inertial_direction = _map_tnw_direction_to_inertial(
                basis,
                direction_tnw,
            )
        except ValueError as exc:
            _raise_refinement_error(
                candidate_id,
                "finite-burn-guidance",
                f"{context}: {exc}",
                exc,
            )
        return inertial_direction

    return direction_callback


def _build_initial_burn_controls(
    scenario: Scenario,
    candidate: ImpulsiveTransferCandidate,
    moon_gravitational_parameter_m3_s2: float,
    mars_gravitational_parameter_m3_s2: float,
) -> tuple[float, ...] | str:
    """Build initial controls from verified candidate and harmonic-field GMs.

    Use the same body-relative J2000 orbit conversion as physical boundaries;
    avoid subtracting large SSB positions to reconstruct a small local orbit.
    No propagation, correction or public status is produced here.
    """
    durations_s = _seed_burn_durations_s(
        candidate.candidate_id, scenario.spacecraft,
        candidate.departure_delta_v_m_s, candidate.arrival_delta_v_m_s,
    )
    controls: list[float] = []
    for burn_id, body, orbit, radius_m, gm_m3_s2, excess, duration_s in (
        ("departure", "Moon", scenario.departure_orbit, MOON_ORBIT_SHAPE_RADIUS_M,
         moon_gravitational_parameter_m3_s2, candidate.departure_v_infinity_m_s, durations_s[0]),
        ("arrival", "Mars", scenario.target_orbit, MARS_ORBIT_SHAPE_RADIUS_M,
         mars_gravitational_parameter_m3_s2, candidate.arrival_v_infinity_m_s, durations_s[1]),
    ):
        try:
            if orbit.central_body != body:
                raise ValueError(f"{burn_id} orbit central_body must be {body}")
            relative_state = _orbit_to_body_relative_state(orbit, radius_m, gm_m3_s2)
        except (TypeError, ValueError, RuntimeError) as exc:
            _raise_refinement_error(candidate.candidate_id, "burn-seed", str(exc), exc)
        angles_rad = _seed_burn_angles_rad(
            candidate.candidate_id, cast(Literal["departure", "arrival"], burn_id),
            excess, relative_state,
        )
        controls.extend((*angles_rad, duration_s))
    return _prepare_burn_controls(
        candidate.candidate_id, scenario.spacecraft,
        candidate.departure_epoch_tdb_s, candidate.arrival_epoch_tdb_s, tuple(controls),
    )


def _prepare_burn_controls(
    candidate_id: object,
    spacecraft: SpacecraftSpec,
    departure_epoch_tdb_s: object,
    arrival_epoch_tdb_s: object,
    controls: tuple[object, ...],
) -> tuple[float, ...] | str:
    """Return canonical (a_d, e_d, tau_d, a_a, e_a, tau_a), or rejection reason.

    Angles are radians, durations seconds. This analytic gate runs before
    propagation; it does not select a public status or guarantee impact safety.
    Malformed/non-finite inputs remain fatal rather than rejected trials.
    """
    try:
        if not isinstance(spacecraft, SpacecraftSpec):
            raise TypeError("spacecraft must be a SpacecraftSpec")
        departure = _finite_float("departure_epoch_tdb_s", departure_epoch_tdb_s)
        arrival = _finite_float("arrival_epoch_tdb_s", arrival_epoch_tdb_s)
        if arrival <= departure:
            raise ValueError("arrival_epoch_tdb_s must follow departure_epoch_tdb_s")
        names = (
            "departure_azimuth_rad", "departure_elevation_rad", "departure_duration_s",
            "arrival_azimuth_rad", "arrival_elevation_rad", "arrival_duration_s",
        )
        if len(controls) != len(names):
            raise ValueError("controls must contain exactly six values")
        values = [_finite_float(name, value) for name, value in zip(names, controls)]
        for index in (0, 3):
            values[index] = math.remainder(values[index], math.tau)
            if values[index] == math.pi:
                values[index] = -math.pi
        if (
            abs(values[1]) > math.pi / 2 or abs(values[4]) > math.pi / 2
            or values[2] <= 0.0 or values[5] <= 0.0
        ):
            return "rejected-control-bounds"
        cutoff = _finite_float("departure_cutoff_tdb_s", departure + values[2])
        ignition = _finite_float("arrival_ignition_tdb_s", arrival - values[5])
        if cutoff <= departure or ignition >= arrival or cutoff >= ignition:
            return "rejected-control-bounds"
        exhaust_m_s = _positive_finite(
            "exhaust_velocity_m_s", STANDARD_GRAVITY_M_S2 * spacecraft.isp_s,
        )
        mass_rate_kg_s = _positive_finite(
            "mass_rate_kg_s", spacecraft.max_thrust_n / exhaust_m_s,
        )
        terminal_mass_kg = _finite_float(
            "analytic_terminal_mass_kg",
            spacecraft.initial_mass_kg - mass_rate_kg_s * (values[2] + values[5]),
        )
        if terminal_mass_kg < spacecraft.dry_mass_kg:
            return "rejected-dry-mass"
        return tuple(values)
    except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
        _raise_refinement_error(candidate_id, "control-validation", str(exc), exc)


def _seed_burn_angles_rad(
    candidate_id: object,
    burn_id: Literal["departure", "arrival"],
    excess_velocity_m_s: object,
    body_relative_state: object,
) -> tuple[float, float]:
    """Project signed excess velocity into boundary TNW; return azimuth/elevation.

    Inputs use J2000 and SI. Supply Moon-relative ignition state for departure,
    Mars-relative target-cutoff state for arrival. Angles are radians, with
    azimuth in [-pi, pi); arrival uses the negative excess-velocity direction.
    """
    try:
        if not isinstance(burn_id, str) or burn_id not in _BURN_CENTRAL_BODIES:
            raise ValueError("burn_id must be departure or arrival")
        state = _finite_cartesian_values(body_relative_state, "body_relative_state")
        basis = _build_tnw_basis(state[:3], state[3:])
        excess = _finite_vector3_values(excess_velocity_m_s, "excess_velocity_m_s")
        norm_m_s = math.hypot(*excess)
        if not math.isfinite(norm_m_s) or norm_m_s <= 1e-12:
            raise ValueError("excess_velocity_m_s norm must be finite and above 1e-12 m/s")
        sign = 1.0 if burn_id == "departure" else -1.0
        direction = cast(Vector3, tuple(sign * value / norm_m_s for value in excess))
        tangent, normal, cross_track = (
            _dot_product(direction, axis)
            for axis in (basis.t_hat, basis.n_hat, basis.w_hat)
        )
        azimuth_rad = math.atan2(normal, tangent)
        if azimuth_rad == math.pi:
            azimuth_rad = -math.pi
        return azimuth_rad, math.atan2(cross_track, math.hypot(tangent, normal))
    except (TypeError, ValueError) as exc:
        _raise_refinement_error(candidate_id, "burn-seed", f"{burn_id}: {exc}", exc)


def _seed_burn_durations_s(
    candidate_id: object,
    spacecraft: SpacecraftSpec,
    departure_delta_v_m_s: object,
    arrival_delta_v_m_s: object,
) -> tuple[float, float]:
    """Return sequential rocket-equation departure/arrival duration seeds in s.

    This is an ideal seed, not proof of dry-mass, window or trajectory safety.
    Zero durations remain zero for later control-domain rejection.
    """
    try:
        if not isinstance(spacecraft, SpacecraftSpec):
            raise TypeError("spacecraft must be a SpacecraftSpec")
        departure_dv = _finite_float("departure_delta_v_m_s", departure_delta_v_m_s)
        arrival_dv = _finite_float("arrival_delta_v_m_s", arrival_delta_v_m_s)
        if departure_dv < 0.0 or arrival_dv < 0.0:
            raise ValueError("burn delta_v_m_s must be nonnegative")
        exhaust_m_s = _positive_finite(
            "exhaust_velocity_m_s", STANDARD_GRAVITY_M_S2 * spacecraft.isp_s,
        )
        mass_rate_kg_s = _positive_finite(
            "mass_rate_kg_s", spacecraft.max_thrust_n / exhaust_m_s,
        )
        initial_kg = spacecraft.initial_mass_kg
        departure_kg = initial_kg * math.exp(-departure_dv / exhaust_m_s)
        arrival_kg = departure_kg * math.exp(-arrival_dv / exhaust_m_s)
        return (
            _finite_float("departure_duration_s", (initial_kg - departure_kg) / mass_rate_kg_s),
            _finite_float("arrival_duration_s", (departure_kg - arrival_kg) / mass_rate_kg_s),
        )
    except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
        _raise_refinement_error(candidate_id, "burn-seed", str(exc), exc)


def _install_tnw_engine(
    candidate_id: object,
    bodies: Any,
    spacecraft: SpacecraftSpec,
    burn_id: Literal["departure", "arrival"],
    azimuth_rad: object,
    elevation_rad: object,
) -> str:
    """Install one maximum-thrust TNW engine on a fresh SSB/J2000 arc system.

    Preserve current mass for arc handoff. Discard the body system on failure;
    native setup can partially mutate it. Coast arcs must not use this engine.
    """
    try:
        if not isinstance(spacecraft, SpacecraftSpec):
            raise TypeError("spacecraft must be a SpacecraftSpec")
        thrust_n = _positive_finite(
            "spacecraft.max_thrust_n", spacecraft.max_thrust_n,
        )
        isp_s = _positive_finite("spacecraft.isp_s", spacecraft.isp_s)
    except (TypeError, ValueError) as exc:
        _raise_refinement_error(candidate_id, "engine-construction", str(exc), exc)
    direction = _build_tnw_direction_callback(
        candidate_id, bodies, burn_id, azimuth_rad, elevation_rad,
    )

    def thrust(epoch_tdb_s: float) -> float:
        return thrust_n

    try:
        environment_setup = _import_tudat_environment_setup()
        propagation_setup = _import_tudat_propagation_setup()
    except RuntimeError as exc:
        _raise_refinement_error(candidate_id, "engine-construction", str(exc), exc)
    engine_name = f"{burn_id}-main"
    try:
        if (
            bodies.global_frame_origin() != "SSB"
            or bodies.global_frame_orientation() != "J2000"
        ):
            raise ValueError("engine body system must use SSB/J2000")
        rotation = environment_setup.rotation_model.custom_inertial_direction_based(
            direction, "J2000", "VehicleFixed",
        )
        magnitude = propagation_setup.thrust.custom_thrust_magnitude_fixed_isp(
            thrust, isp_s,
        )
        environment_setup.add_rotation_model(bodies, SPACECRAFT_BODY_NAME, rotation)
        environment_setup.add_engine_model(
            SPACECRAFT_BODY_NAME, engine_name, magnitude, bodies, (1.0, 0.0, 0.0),
        )
    except Exception as exc:
        _raise_refinement_error(
            candidate_id, "engine-construction",
            f"{burn_id} engine installation failed: {exc}", exc,
        )
    return engine_name


def _sum_force_acceleration_bounds(
    budget: _RefinementBudget,
    gravity_bounds_m_s2: dict[str, float],
    thrust_bound_m_s2: float,
    srp_bound_m_s2: float,
    schwarzschild_bound_m_s2: float,
    *,
    thrust_enabled: bool,
) -> float:
    """Sum all declared force-norm enclosures in m/s^2 under the shared budget.

    Inputs must already bound their components over the requested interval.
    This neither proves those premises nor accounts for body/numerical errors.
    """
    budget.check()
    try:
        if not isinstance(gravity_bounds_m_s2, dict) or tuple(gravity_bounds_m_s2) != PHYSICAL_BODY_NAMES:
            raise ValueError("gravity bounds must contain exactly the ordered eight bodies")
        if not isinstance(thrust_enabled, bool):
            raise ValueError("thrust_enabled must be boolean")
        values_m_s2 = []
        for body, value in gravity_bounds_m_s2.items():
            budget.check()
            values_m_s2.append(_positive_finite(f"{body} gravity bound_m_s2", value))
        thrust_m_s2 = _finite_float("thrust bound_m_s2", thrust_bound_m_s2)
        if (thrust_enabled and thrust_m_s2 <= 0) or (not thrust_enabled and thrust_m_s2 != 0):
            raise ValueError("thrust bound must be positive for burn and exactly zero for coast")
        values_m_s2.extend((
            thrust_m_s2, _positive_finite("srp bound_m_s2", srp_bound_m_s2),
            _positive_finite("Schwarzschild bound_m_s2", schwarzschild_bound_m_s2),
        ))
        budget.check()
        with localcontext(Context(prec=50, rounding=ROUND_CEILING)):
            total_m_s2 = sum((Decimal.from_float(value) for value in values_m_s2), Decimal(0))
            result_m_s2 = _positive_finite(
                "total force bound_m_s2", math.nextafter(float(total_m_s2), math.inf),
            )
    except (ArithmeticError, TypeError, ValueError) as exc:
        _raise_refinement_error(budget.candidate_id, "force-bound-sum", str(exc), exc)
    budget.check()
    return result_m_s2


def _build_arc_force_models(
    candidate_id: object,
    environment: _PhysicalEnvironment,
    *,
    burn_id: Literal["departure", "arrival"] | None = None,
) -> Any:
    """Assemble SSB/J2000 forces and optional installed-engine thrust per arc.

    None selects coast, even if engines remain installed. A burn requires its
    TNW engine to be installed first. Native SPICE/PPN mutation must be serialized
    with other simulations; the returned models do not freeze global state.
    """
    try:
        if burn_id is not None and (
            not isinstance(burn_id, str) or burn_id not in {"departure", "arrival"}
        ):
            raise ValueError("burn_id must be departure, arrival or None for coast")
        _validate_gravity_acceleration_inventory(
            environment.gravity_acceleration_settings,
            environment.gravity_acceleration_inventory,
            environment.harmonic_fields,
        )
        settings = dict(environment.gravity_acceleration_settings)
        for extra in (
            environment.solar_radiation_pressure_acceleration_settings,
            environment.relativistic_acceleration_settings,
        ):
            if tuple(extra) != ("Sun",) or len(extra["Sun"]) != 1:
                raise ValueError("SRP and relativity must each contain one Sun term")
            settings["Sun"] += extra["Sun"]
        propagation_setup = _import_tudat_propagation_setup()
    except (TypeError, ValueError, RuntimeError) as exc:
        _raise_refinement_error(candidate_id, "force-model-construction", str(exc), exc)
    _set_general_relativity_ppn_parameters(candidate_id, environment.bodies)
    try:
        if burn_id is not None:
            settings[SPACECRAFT_BODY_NAME] = (
                propagation_setup.acceleration.thrust_from_engine(f"{burn_id}-main"),
            )
        return propagation_setup.create_acceleration_models(
            environment.bodies,
            {SPACECRAFT_BODY_NAME: settings},
            [SPACECRAFT_BODY_NAME],
            ["SSB"],
        )
    except Exception as exc:
        _raise_refinement_error(
            candidate_id, "force-model-construction",
            f"arc acceleration assembly failed (burn_id={burn_id!r}): {exc}", exc,
        )


def _build_arc_integrator(
    candidate_id: object,
    arc: Literal["departure-burn", "coast", "arrival-burn"],
    *,
    tighter: bool = False,
) -> Any:
    """Build pinned seven-state SI translation/mass integration settings."""
    if not isinstance(arc, str) or arc not in {
        "departure-burn", "coast", "arrival-burn",
    } or not isinstance(tighter, bool):
        cause = ValueError("arc must name a burn/coast and tighter must be boolean")
        _raise_refinement_error(candidate_id, "integrator-construction", str(cause), cause)
    coast = arc == "coast"
    if tighter:
        relative = 1e-13
        absolute = (1e-5,) * 3 + (1e-8,) * 3 + (1e-11,)
        initial_s, minimum_s, maximum_s = (
            (75.0, 1e-5, 21600.0) if coast else (0.25, 1e-8, 7.5)
        )
    else:
        relative = 1e-11
        absolute = (1e-3,) * 3 + (1e-6,) * 3 + (1e-9,)
        initial_s, minimum_s, maximum_s = (
            (300.0, 1e-3, 86400.0) if coast else (1.0, 1e-6, 30.0)
        )
    try:
        propagation_setup = _import_tudat_propagation_setup()
    except RuntimeError as exc:
        _raise_refinement_error(candidate_id, "integrator-construction", str(exc), exc)
    try:
        integrator = propagation_setup.integrator
        coefficient = (
            integrator.CoefficientSets.rkdp_87 if tighter
            else integrator.CoefficientSets.rkf_78
        )
        control = integrator.step_size_control_elementwise_matrix_tolerance(
            ((relative,),) * 7, tuple((value,) for value in absolute),
        )
        validation = integrator.step_size_validation(
            minimum_s, maximum_s,
            integrator.MinimumIntegrationTimeStepHandling.throw_exception_below_minimum,
            accept_infinity_step=False, accept_nan_step=False,
        )
        return integrator.runge_kutta_variable_step(
            initial_s, coefficient, control, validation,
            assess_termination_on_minor_steps=False,
        )
    except Exception as exc:
        _raise_refinement_error(
            candidate_id, "integrator-construction",
            f"{arc} integrator setup failed: {exc}", exc,
        )


def _build_coupled_arc_settings(
    candidate_id: object,
    bodies: Any,
    accelerations: Any,
    initial_state: object,
    initial_mass_kg: object,
    initial_epoch_tdb_s: object,
    integrator: Any,
    termination: Any,
    *,
    thrust_enabled: bool,
) -> Any:
    """Couple SI/SSB/J2000 translation and mass without resetting handoff mass.

    The caller supplies matching engine/force and safety-termination settings.
    This constructs settings only; it neither runs nor certifies a safe arc.
    """
    try:
        state = _finite_cartesian_values(initial_state, "initial_state")
        mass_kg = _positive_finite("initial_mass_kg", initial_mass_kg)
        epoch_tdb_s = _finite_float("initial_epoch_tdb_s", initial_epoch_tdb_s)
        if not isinstance(thrust_enabled, bool):
            raise ValueError("thrust_enabled must be boolean")
        propagation_setup = _import_tudat_propagation_setup()
    except (TypeError, ValueError, RuntimeError) as exc:
        _raise_refinement_error(candidate_id, "arc-construction", str(exc), exc)

    def coast_mass_rate(epoch_tdb_s: float) -> float:
        return 0.0

    try:
        if (
            bodies.global_frame_origin() != "SSB"
            or bodies.global_frame_orientation() != "J2000"
        ):
            raise ValueError("arc body system must use SSB/J2000")
        mass_rate = (
            propagation_setup.mass_rate.from_thrust(True) if thrust_enabled
            else propagation_setup.mass_rate.custom(coast_mass_rate)
        )
        mass_rates = propagation_setup.create_mass_rate_models(
            bodies, {SPACECRAFT_BODY_NAME: [mass_rate]}, accelerations,
        )
        translation = propagation_setup.propagator.translational(
            ["SSB"], accelerations, [SPACECRAFT_BODY_NAME], state,
            epoch_tdb_s, integrator, termination,
        )
        mass = propagation_setup.propagator.mass(
            [SPACECRAFT_BODY_NAME], mass_rates, (mass_kg,),
            epoch_tdb_s, integrator, termination,
        )
        return propagation_setup.propagator.multitype(
            [translation, mass], integrator, epoch_tdb_s, termination,
        )
    except Exception as exc:
        _raise_refinement_error(
            candidate_id, "arc-construction",
            f"coupled arc at TDB epoch {epoch_tdb_s!r} failed: {exc}", exc,
        )


def _import_tudat_simulator() -> Any:
    try:
        from tudatpy.dynamics import simulator
    except ImportError as exc:
        raise RuntimeError("TudatPy simulator is unavailable") from exc
    return simulator


def _run_native_arc(
    budget: _RefinementBudget,
    bodies: Any,
    propagator_settings: Any,
    *,
    first_in_evaluation: bool,
) -> Any:
    """Run one native arc under the existing cooperative budget.

    Returned native output is unclassified: callers must reject safety stops
    before completion/epoch checks and must discard failed or unsafe history.
    """
    budget.check()
    try:
        simulator_module = _import_tudat_simulator()
    except RuntimeError as exc:
        _raise_refinement_error(budget.candidate_id, "native-integration", str(exc), exc)
    budget.begin_arc(first_in_evaluation=first_in_evaluation)
    try:
        simulator = simulator_module.create_dynamics_simulator(bodies, propagator_settings)
    except Exception as exc:
        _raise_refinement_error(
            budget.candidate_id, "native-integration",
            f"native_arc_propagations={budget.native_arc_propagations}: {exc}", exc,
        )
    budget.check()
    return simulator


def _read_trial_arc_outcome(
    candidate_id: object,
    arc: Literal["departure-burn", "coast", "arrival-burn"],
    simulator: Any,
    expected_epoch_tdb_s: object,
    safety_rejection: str | None,
) -> tuple[Cartesian6, float] | str:
    """Consume an independently classified arc, without exposing unsafe history.

    The caller must establish safety (including between-step crossings) first
    and discard the native simulator after a rejection/error. None is not a
    safety certificate. Native failure remains fatal even with a safety reason.
    """
    if safety_rejection is None:
        return _read_completed_arc_state(candidate_id, arc, simulator, expected_epoch_tdb_s)
    allowed = {"rejected-dry-mass"} | {
        f"rejected-impact:{body}" for body in PHYSICAL_BODY_NAMES
    }
    if not isinstance(safety_rejection, str) or safety_rejection not in allowed:
        cause = ValueError(f"invalid physical safety rejection: {safety_rejection!r}")
        _raise_refinement_error(candidate_id, "arc-safety", f"{arc}: {cause}", cause)
    try:
        completed = simulator.integration_completed_successfully
    except Exception as exc:
        _raise_refinement_error(candidate_id, "arc-completion", f"{arc}: {exc}", exc)
    if completed is not True:
        cause = RuntimeError("native integration failed despite a safety rejection")
        _raise_refinement_error(candidate_id, "arc-completion", f"{arc}: {cause}", cause)
    return safety_rejection


def _read_completed_arc_state(
    candidate_id: object,
    arc: Literal["departure-burn", "coast", "arrival-burn"],
    simulator: Any,
    expected_epoch_tdb_s: object,
) -> tuple[Cartesian6, float]:
    """Read completed SI/SSB/J2000 translation and mass, never a partial result.

    Call only after classifying safety termination; impact/dry-mass trials must
    be rejected before this completion check. Discard simulator history on error.
    """
    context = f"{arc} arc expected TDB epoch {expected_epoch_tdb_s!r}"
    try:
        if not isinstance(arc, str) or arc not in {
            "departure-burn", "coast", "arrival-burn",
        }:
            raise ValueError("arc must name a burn or coast")
        expected = _finite_float("expected_epoch_tdb_s", expected_epoch_tdb_s)
    except ValueError as exc:
        _raise_refinement_error(candidate_id, "arc-completion", f"{context}: {exc}", exc)
    try:
        completed = simulator.integration_completed_successfully
    except Exception as exc:
        _raise_refinement_error(candidate_id, "arc-completion", f"{context}: {exc}", exc)
    if completed is not True:
        cause = RuntimeError("native integration did not complete successfully")
        _raise_refinement_error(candidate_id, "arc-completion", f"{context}: {cause}", cause)
    try:
        history = simulator.state_history
        epochs = tuple(history.keys())
    except Exception as exc:
        _raise_refinement_error(candidate_id, "arc-completion", f"{context}: {exc}", exc)
    try:
        if not epochs:
            raise ValueError("native history is empty")
        terminal_epoch = max(_finite_float("history epoch", epoch) for epoch in epochs)
        if abs(terminal_epoch - expected) > _TIME_TOLERANCE_S:
            raise ValueError(f"final epoch mismatch: got {terminal_epoch} TDB s")
    except ValueError as exc:
        _raise_refinement_error(candidate_id, "arc-completion", f"{context}: {exc}", exc)
    try:
        raw_state = history[terminal_epoch]
        flatten = getattr(raw_state, "reshape", None)
        values = tuple(flatten(-1) if callable(flatten) else raw_state)
    except Exception as exc:
        _raise_refinement_error(candidate_id, "arc-completion", f"{context}: {exc}", exc)
    try:
        if len(values) != 7:
            raise ValueError("terminal state must contain six SI components and mass_kg")
        cartesian = _finite_cartesian_values(values[:6], "terminal state")
        mass_kg = _positive_finite("terminal mass_kg", values[6])
    except ValueError as exc:
        _raise_refinement_error(candidate_id, "arc-completion", f"{context}: {exc}", exc)
    return cartesian, mass_kg


def _ephemeris_cell_chord_bound(
    budget: _RefinementBudget,
    node_epochs_tdb_s: tuple[float, ...],
    node_positions_m: tuple[tuple[float, float, float], ...],
    initial_epoch_tdb_s: float,
    final_epoch_tdb_s: float,
) -> float:
    """Bound exact six-node position polynomial chord deviation in metres.

    Nodes must be SI/SSB/J2000; the interval lies inside the middle node pair.
    This excludes native evaluation, SPICE approximation and trajectory errors.
    """
    budget.check()
    try:
        if len(node_epochs_tdb_s) != 6 or len(node_positions_m) != 6:
            raise ValueError("exactly six epochs and position nodes are required")
        epochs = [Fraction(_finite_float(f"node[{i}] epoch_tdb_s", value))
                  for i, value in enumerate(node_epochs_tdb_s)]
        if any(right <= left for left, right in zip(epochs, epochs[1:])):
            raise ValueError("node epochs must be strictly increasing")
        positions = []
        for index, position in enumerate(node_positions_m):
            if len(position) != 3:
                raise ValueError(f"node[{index}] position_m must have three components")
            positions.append([Fraction(_finite_float(f"node[{index}] position_m", value))
                              for value in position])
        start = Fraction(_finite_float("initial_epoch_tdb_s", initial_epoch_tdb_s))
        end = Fraction(_finite_float("final_epoch_tdb_s", final_epoch_tdb_s))
        if not epochs[2] <= start < end <= epochs[3]:
            raise ValueError("interval must have positive duration within the middle node pair")
        nodes = [(epoch - start) / (end - start) for epoch in epochs]
        power_m = [[Fraction(0) for _ in range(3)] for _ in range(6)]
        for selected, node in enumerate(nodes):
            budget.check()
            basis = [Fraction(1)]
            for other_index, other in enumerate(nodes):
                if other_index == selected:
                    continue
                product = [Fraction(0) for _ in range(len(basis) + 1)]
                for degree, coefficient in enumerate(basis):
                    product[degree] -= coefficient * other / (node - other)
                    product[degree + 1] += coefficient / (node - other)
                basis = product
            for degree, coefficient in enumerate(basis):
                for axis in range(3):
                    power_m[degree][axis] += coefficient * positions[selected][axis]
        # Subtract p(0) + u*(p(1)-p(0)) exactly, including large SSB offsets.
        for axis in range(3):
            power_m[0][axis] = Fraction(0)
            power_m[1][axis] -= sum(row[axis] for row in power_m[1:])
        bound_m = Fraction(0)
        for index in range(6):
            budget.check()
            bernstein_m = [sum(
                power_m[degree][axis] * Fraction(math.comb(index, degree), math.comb(5, degree))
                for degree in range(index + 1)
            ) for axis in range(3)]
            # ponytail: L1 hull is conservative; use a certified L2 norm only
            # if measured subdivision costs justify the added arithmetic.
            bound_m = max(bound_m, sum(abs(value) for value in bernstein_m))
        result_m = 0.0 if bound_m == 0 else _positive_finite(
            "cell chord bound_m", math.nextafter(float(bound_m), math.inf),
        )
    except (ArithmeticError, TypeError, ValueError) as exc:
        _raise_refinement_error(budget.candidate_id, "ephemeris-cell-bound", str(exc), exc)
    budget.check()
    return result_m


def _compose_ephemeris_chord_bounds(
    budget: _RefinementBudget,
    knot_epochs_tdb_s: tuple[float, ...],
    knot_positions_m: tuple[tuple[float, float, float], ...],
    cell_bounds_m: tuple[float, ...],
) -> float:
    """Compose local Euclidean chord bounds into a global bound in metres.

    Cells must share the supplied SI/SSB/J2000 endpoints at ordered TDB epochs.
    Validity of local bounds and all endpoint/native/SPICE errors remain external.
    """
    budget.check()
    try:
        count = len(knot_epochs_tdb_s)
        if count < 2 or len(knot_positions_m) != count or len(cell_bounds_m) != count - 1:
            raise ValueError("require at least two knots, matching positions and one bound per cell")
        epochs: list[Fraction] = []
        positions: list[tuple[Fraction, ...]] = []
        local_bounds_m: list[Fraction] = []
        for index, epoch in enumerate(knot_epochs_tdb_s):
            budget.check()
            epochs.append(Fraction(_finite_float(f"knot[{index}] epoch_tdb_s", epoch)))
            if index and epochs[-1] <= epochs[-2]:
                raise ValueError("knot epochs must be strictly increasing")
            positions.append(tuple(Fraction(value) for value in _finite_vector3_values(
                knot_positions_m[index], f"knot[{index}] position_m",
            )))
            if index:
                local_m = _finite_float(f"cell[{index - 1}] bound_m", cell_bounds_m[index - 1])
                if local_m < 0:
                    raise ValueError(f"cell[{index - 1}] bound_m must be nonnegative")
                local_bounds_m.append(Fraction(local_m))
        residuals_m: list[Fraction] = []
        for epoch, position in zip(epochs, positions):
            budget.check()
            fraction = (epoch - epochs[0]) / (epochs[-1] - epochs[0])
            residuals_m.append(sum((abs(
                position[axis] - positions[0][axis]
                - fraction * (positions[-1][axis] - positions[0][axis])
            ) for axis in range(3)), Fraction(0)))
        bound_m = Fraction(0)
        for index, local_m in enumerate(local_bounds_m):
            budget.check()
            bound_m = max(bound_m, local_m + max(residuals_m[index:index + 2]))
        result_m = 0.0 if bound_m == 0 else _positive_finite(
            "composed chord bound_m", math.nextafter(float(bound_m), math.inf),
        )
    except (ArithmeticError, TypeError, ValueError) as exc:
        _raise_refinement_error(budget.candidate_id, "ephemeris-chord-composition", str(exc), exc)
    budget.check()
    return result_m


def _spk_position_rate_bound(
    budget: _RefinementBudget,
    coefficients_km: tuple[tuple[float, ...], ...],
    radius_s: float,
) -> float:
    """Bound an exact SPK position polynomial's rate norm in m/s on one record.

    Three Chebyshev coefficient rows are in km; normalized time is in [-1, 1].
    The bound excludes record jumps, native rounding and center-chain motion.
    It is not the independently stored type-3 velocity polynomial.
    """
    budget.check()
    try:
        radius = Fraction(_positive_finite("SPK record radius_s", radius_s))
        if len(coefficients_km) != 3 or not coefficients_km[0]:
            raise ValueError("SPK position coefficients_km require three nonempty rows")
        bound_m_s = Fraction(0)
        for axis, row in enumerate(coefficients_km):
            budget.check()
            if len(row) != len(coefficients_km[0]):
                raise ValueError("SPK position coefficient rows must have equal degree")
            for degree, value in enumerate(row):
                coefficient_m = 1000 * Fraction(_finite_float(
                    f"SPK position coefficient_km[{axis}][{degree}]", value,
                ))
                # |T'_k(x)| <= k^2 on [-1,1]; L1 also bounds the Euclidean norm.
                bound_m_s += abs(coefficient_m) * degree ** 2 / radius
        result_m_s = 0.0 if bound_m_s == 0 else _positive_finite(
            "SPK position rate bound_m_s", math.nextafter(float(bound_m_s), math.inf),
        )
    except (ArithmeticError, TypeError, ValueError) as exc:
        _raise_refinement_error(budget.candidate_id, "spk-position-rate-bound", str(exc), exc)
    budget.check()
    return result_m_s


def _validate_direct_spice_coverage(
    candidate_id: str,
    initial_epoch_tdb_s: float,
    final_epoch_tdb_s: float,
    budget: _RefinementBudget | None = None,
) -> None:
    """Require geometric SSB/J2000 SPK chain coverage, not an accuracy bound."""
    try:
        start = _finite_float("initial_epoch_tdb_s", initial_epoch_tdb_s)
        end = _finite_float("final_epoch_tdb_s", final_epoch_tdb_s)
        if start >= end:
            raise ValueError("SPK coverage requires initial_epoch_tdb_s < final_epoch_tdb_s")
    except ValueError as exc:
        _raise_refinement_error(candidate_id, "ephemeris-coverage", str(exc), exc)
    if budget is not None:
        budget.check()
    try:
        import spiceypy as spice
        from spiceypy.utils.support_types import SPICEDOUBLE_CELL

        # These fixed center chains are qualified against named Tudat states.
        centers = {10: 0, 1: 0, 2: 0, 399: 0, 301: 399,
                   499: 4, 4: 0, 599: 5, 5: 0, 699: 6, 6: 0}
        coverage = {target: SPICEDOUBLE_CELL(10000) for target in centers}
        registrations = [spice.kdata(i, "SPK") for i in range(spice.ktotal("SPK"))]
        files = {str(Path(entry[0]).resolve()): entry for entry in registrations}
        if not files:
            raise ValueError("no loaded SPK files")
        for path, entry in files.items():
            if budget is not None:
                budget.check()
            if not Path(path).is_file():
                raise ValueError(f"missing loaded SPK file: {path}")
            spice.dafbfs(entry[3])
            while spice.daffna():
                if budget is not None:
                    budget.check()
                target, center, frame, kind, first, last, begin, finish = spice.spkuds(
                    spice.dafgs()[:5],
                )
                if target not in centers:
                    continue
                if not (math.isfinite(first) and math.isfinite(last) and first <= last
                        and 0 < begin <= finish):
                    raise ValueError(f"SPK target {target}: invalid segment descriptor in {path}")
                if first > end or last < start:
                    continue
                if center != centers[target] or frame != 1 or kind not in (2, 3):
                    raise ValueError(
                        f"SPK target {target}: unsupported center/frame/type "
                        f"{center}/{frame}/{kind} in {path}"
                    )
                spice.wninsd(max(first, start), min(last, end), coverage[target])
        for target, window in coverage.items():
            if not spice.wnincd(start, end, window):
                raise ValueError(
                    f"SPK target {target} relative to {centers[target]}: "
                    f"missing or gapped coverage for TDB interval [{start}, {end}]"
                )
    except TrajectoryRefinementError:
        raise
    except Exception as exc:
        # Translate only this untyped SPICE inspection boundary; never reload.
        _raise_refinement_error(candidate_id, "ephemeris-coverage", str(exc), exc)
    if budget is not None:
        budget.check()


def _create_direct_body_settings(environment_setup: Any) -> Any:
    """Configure direct geometric SPICE explicitly for all eight bodies."""
    try:
        settings = environment_setup.get_default_body_settings(
            PHYSICAL_BODY_NAMES, base_frame_origin="SSB", base_frame_orientation="J2000",
        )
        for body in PHYSICAL_BODY_NAMES:
            settings.get(body).ephemeris_settings = environment_setup.ephemeris.direct_spice(
                "SSB", "J2000", body,
            )
        return settings
    except Exception as exc:
        raise RuntimeError("Tudat could not configure direct SSB/J2000 SPICE bodies") from exc


def _validate_direct_body_settings(environment_setup: Any, body_settings: Any) -> None:
    if (body_settings.frame_origin, body_settings.frame_orientation) != ("SSB", "J2000"):
        raise ValueError("Tudat body settings must use global frame SSB/J2000")
    for body in PHYSICAL_BODY_NAMES:
        settings = body_settings.get(body).ephemeris_settings
        if not isinstance(settings, environment_setup.ephemeris.DirectSpiceEphemerisSettings):
            raise ValueError(f"{body} ephemeris must use direct SPICE")
        if (settings.frame_origin, settings.frame_orientation) != ("SSB", "J2000"):
            raise ValueError(f"{body} ephemeris settings must use frame SSB/J2000")
        if (settings.correct_for_light_time_aberration or settings.correct_for_stellar_aberration
                or settings.converge_light_time_aberration):
            raise ValueError(f"{body} direct SPICE ephemeris must be geometric, without aberration")


def _create_time_limited_body_settings(
    environment_setup: Any,
    initial_epoch_tdb_s: float,
    final_epoch_tdb_s: float,
) -> Any:
    try:
        return environment_setup.get_default_body_settings_time_limited(
            PHYSICAL_BODY_NAMES,
            initial_epoch_tdb_s,
            final_epoch_tdb_s,
            base_frame_origin="SSB",
            base_frame_orientation="J2000",
            time_step=EPHEMERIS_TIME_STEP_S,
        )
    except Exception as exc:
        raise RuntimeError(
            "Tudat could not configure the time-limited SSB/J2000 body settings "
            f"for TDB interval [{initial_epoch_tdb_s}, {final_epoch_tdb_s}]"
        ) from exc


def _validate_time_limited_body_settings(
    body_settings: Any,
    initial_epoch_tdb_s: float,
    final_epoch_tdb_s: float,
) -> None:
    if (
        body_settings.frame_origin != "SSB"
        or body_settings.frame_orientation != "J2000"
    ):
        raise ValueError("Tudat body settings must use global frame SSB/J2000")
    for body_name in PHYSICAL_BODY_NAMES:
        ephemeris_settings = body_settings.get(body_name).ephemeris_settings
        if (
            ephemeris_settings.frame_origin != "SSB"
            or ephemeris_settings.frame_orientation != "J2000"
        ):
            raise ValueError(
                f"{body_name} ephemeris settings must use frame SSB/J2000"
            )
        available_start_tdb_s = _finite_float(
            f"{body_name} ephemeris initial_time",
            ephemeris_settings.initial_time,
        )
        available_end_tdb_s = _finite_float(
            f"{body_name} ephemeris final_time",
            ephemeris_settings.final_time,
        )
        if (
            available_start_tdb_s > initial_epoch_tdb_s
            or available_end_tdb_s < final_epoch_tdb_s
        ):
            raise ValueError(
                f"{body_name} ephemeris settings do not cover TDB interval "
                f"[{initial_epoch_tdb_s}, {final_epoch_tdb_s}]"
            )


def _load_harmonic_field_settings(
    environment_setup: Any,
    spec: _HarmonicFieldSpec,
    coefficient_path: Path,
) -> Any:
    try:
        return environment_setup.gravity_field.from_file_spherical_harmonic(
            str(coefficient_path),
            spec.degree,
            spec.order,
            spec.associated_frame,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Tudat could not load {spec.body} {spec.model} coefficients from "
            f"{coefficient_path}"
        ) from exc


def _harmonic_acceleration_upper_bound(
    candidate_id: object,
    gravitational_parameter_m3_s2: float,
    normalization_radius_m: float,
    minimum_distance_m: float,
    normalized_cosine_coefficients: Iterable[Iterable[float]],
    normalized_sine_coefficients: Iterable[Iterable[float]],
) -> float:
    """Bound finite 4pi-normalized gravity in m/s^2 for r >= minimum_distance_m.

    Rotation invariant, including degree zero once. The caller must prove the
    distance floor; native evaluation error and other forces are not included.
    See the active M3 design for the addition-theorem/Frobenius derivation.
    """
    try:
        gm_m3_s2 = Decimal.from_float(_positive_finite(
            "gravitational_parameter_m3_s2", gravitational_parameter_m3_s2,
        ))
        radius_m = Decimal.from_float(_positive_finite(
            "normalization_radius_m", normalization_radius_m,
        ))
        distance_m = Decimal.from_float(_positive_finite("minimum_distance_m", minimum_distance_m))
        matrices = []
        for name, values in (("cosine", normalized_cosine_coefficients),
                             ("sine", normalized_sine_coefficients)):
            matrix = tuple(tuple(Decimal.from_float(_finite_float(
                f"{name}[{n}][{m}]", value,
            )) for m, value in enumerate(row)) for n, row in enumerate(values))
            if not matrix or any(len(row) != len(matrix) for row in matrix):
                raise ValueError(f"{name} coefficients must be a nonempty square matrix")
            for n, row in enumerate(matrix):
                if any(row[n + 1:]) or (name == "sine" and row[0] != 0):
                    raise ValueError(f"{name}[{n}] contains nonzero unused coefficients")
            matrices.append(matrix)
        cosine, sine = matrices
        if len(cosine) != len(sine):
            raise ValueError("cosine and sine coefficient dimensions must match")
        # A fresh context prevents the caller's precision, rounding or traps
        # from changing the enclosure. All rounded arithmetic is nonnegative.
        with localcontext(Context(prec=50, rounding=ROUND_CEILING)):
            inverse_distance_m_inv = Decimal(1) / distance_m
            ratio = radius_m * inverse_distance_m_inv
            radial_power = Decimal(1)
            total = Decimal(0)
            for n, (c_row, s_row) in enumerate(zip(cosine, sine, strict=True)):
                power = sum((c * c + s * s for c, s in
                             zip(c_row[:n + 1], s_row[:n + 1], strict=True)), Decimal(0))
                if power:
                    # sqrt is half-even regardless of the context rounding.
                    root_upper = ((n + 1) * power).sqrt().next_plus()
                    total += radial_power * (2 * n + 1) * root_upper
                radial_power *= ratio
            bound_m_s2 = gm_m3_s2 * inverse_distance_m_inv * inverse_distance_m_inv * total
            result_m_s2 = 0.0 if not bound_m_s2 else math.nextafter(float(bound_m_s2), math.inf)
        return _finite_float("harmonic acceleration upper bound_m_s2", result_m_s2)
    except (ArithmeticError, TypeError, ValueError) as exc:
        _raise_refinement_error(candidate_id, "gravity-bound", str(exc), exc)


def _validate_harmonic_field_settings(
    spec: _HarmonicFieldSpec,
    gravity_settings: Any,
    rotation_settings: Any,
    actual_sha256: str,
) -> _HarmonicFieldResource:
    gravitational_parameter_m3_s2 = _positive_finite(
        f"{spec.body} harmonic gravitational_parameter_m3_s2",
        gravity_settings.gravitational_parameter,
    )
    if not math.isclose(
        gravitational_parameter_m3_s2,
        spec.gravitational_parameter_m3_s2,
        rel_tol=_FIELD_GM_RELATIVE_TOLERANCE,
        abs_tol=0.0,
    ):
        raise ValueError(
            f"{spec.body} {spec.model} gravitational parameter mismatch: "
            f"expected {spec.gravitational_parameter_m3_s2}, got "
            f"{gravitational_parameter_m3_s2}"
        )
    normalization_radius_m = _positive_finite(
        f"{spec.body} harmonic normalization_radius_m",
        gravity_settings.reference_radius,
    )
    if normalization_radius_m != spec.normalization_radius_m:
        raise ValueError(
            f"{spec.body} {spec.model} normalization radius mismatch: expected "
            f"{spec.normalization_radius_m}, got {normalization_radius_m}"
        )

    expected_shape = (spec.degree + 1, spec.order + 1)
    cosine_shape = tuple(gravity_settings.normalized_cosine_coefficients.shape)
    sine_shape = tuple(gravity_settings.normalized_sine_coefficients.shape)
    if cosine_shape != expected_shape or sine_shape != expected_shape:
        raise ValueError(
            f"{spec.body} {spec.model} coefficient degree/order dimensions must be "
            f"{expected_shape}, got cosine {cosine_shape} and sine {sine_shape}"
        )

    associated_frame = gravity_settings.associated_reference_frame
    rotation_base_frame = rotation_settings.base_frame
    rotation_target_frame = rotation_settings.target_frame
    if associated_frame != spec.associated_frame:
        raise ValueError(
            f"{spec.body} {spec.model} associated frame must be "
            f"{spec.associated_frame}, got {associated_frame}"
        )
    if rotation_base_frame != "J2000" or rotation_target_frame != associated_frame:
        raise ValueError(
            f"{spec.body} frame mismatch: gravity uses {associated_frame}, "
            f"rotation uses {rotation_base_frame}->{rotation_target_frame}"
        )
    if spec.orbit_shape_radius_m == normalization_radius_m:
        raise ValueError(
            f"{spec.body} orbit shape and harmonic normalization radii must differ"
        )
    return _HarmonicFieldResource(
        body=spec.body,
        model=spec.model,
        file_name=spec.file_name,
        degree=spec.degree,
        order=spec.order,
        expected_sha256=spec.expected_sha256,
        actual_sha256=actual_sha256,
        associated_frame=associated_frame,
        rotation_base_frame=rotation_base_frame,
        rotation_target_frame=rotation_target_frame,
        gravitational_parameter_m3_s2=gravitational_parameter_m3_s2,
        normalization_radius_m=normalization_radius_m,
        orbit_shape_radius_m=spec.orbit_shape_radius_m,
    )


def _create_gravity_acceleration_setting(
    propagation_setup: Any,
    resource: _GravityAccelerationResource,
) -> Any:
    try:
        if resource.acceleration_type == _POINT_MASS_GRAVITY_TYPE:
            return propagation_setup.acceleration.point_mass_gravity()
        if resource.acceleration_type == _SPHERICAL_HARMONIC_GRAVITY_TYPE:
            return propagation_setup.acceleration.spherical_harmonic_gravity(
                resource.degree,
                resource.order,
            )
    except Exception as exc:
        raise RuntimeError(
            f"Tudat could not configure {resource.acceleration_type} from "
            f"{resource.source_body}"
        ) from exc
    raise ValueError(
        f"unsupported gravity acceleration type {resource.acceleration_type!r} "
        f"for {resource.source_body}"
    )


def _validate_gravity_acceleration_inventory(
    settings_by_source: dict[str, tuple[Any, ...]],
    inventory: tuple[_GravityAccelerationResource, ...],
    harmonic_fields: tuple[_HarmonicFieldResource, ...],
) -> None:
    expected_sources = PHYSICAL_BODY_NAMES
    if tuple(settings_by_source) != expected_sources:
        raise ValueError(
            "gravity settings must contain the exact ordered physical body set"
        )
    if tuple(entry.source_body for entry in inventory) != expected_sources:
        raise ValueError(
            "gravity inventory must contain each physical body exactly once"
        )
    if any(len(settings_by_source[source]) != 1 for source in expected_sources):
        raise ValueError("each gravity source must have exactly one acceleration")

    harmonic_bodies = tuple(field.body for field in harmonic_fields)
    if harmonic_bodies != _HARMONIC_GRAVITY_BODY_NAMES:
        raise ValueError(
            "harmonic resources must contain exactly Moon then Mars"
        )
    fields_by_body = {field.body: field for field in harmonic_fields}
    entries_by_body = {entry.source_body: entry for entry in inventory}

    for body in _DIRECT_GRAVITY_BODY_NAMES:
        entry = entries_by_body[body]
        if (
            entry.acceleration_type != _POINT_MASS_GRAVITY_TYPE
            or entry.degree is not None
            or entry.order is not None
        ):
            raise ValueError(f"{body} must have one direct point-mass acceleration")
    for body in _HARMONIC_GRAVITY_BODY_NAMES:
        entry = entries_by_body[body]
        field = fields_by_body[body]
        if (
            entry.acceleration_type != _SPHERICAL_HARMONIC_GRAVITY_TYPE
            or entry.degree != field.degree
            or entry.order != field.order
        ):
            raise ValueError(
                f"{body} must have one {field.degree}x{field.order} "
                "spherical-harmonic acceleration"
            )


def _build_gravity_acceleration_settings(
    candidate_id: object,
    harmonic_fields: tuple[_HarmonicFieldResource, ...],
) -> tuple[
    dict[str, tuple[Any, ...]],
    tuple[_GravityAccelerationResource, ...],
]:
    """Build the exact direct SSB gravity inventory for one spacecraft."""

    try:
        propagation_setup = _import_tudat_propagation_setup()
    except RuntimeError as exc:
        _raise_refinement_error(
            candidate_id,
            "force-model-construction",
            str(exc),
            exc,
        )

    try:
        harmonic_by_body = {field.body: field for field in harmonic_fields}
        if tuple(harmonic_by_body) != _HARMONIC_GRAVITY_BODY_NAMES:
            raise ValueError(
                "harmonic resources must contain exactly Moon then Mars"
            )

        settings_by_source: dict[str, tuple[Any, ...]] = {}
        inventory = []
        for source_body in PHYSICAL_BODY_NAMES:
            field = harmonic_by_body.get(source_body)
            if field is None:
                if source_body not in _DIRECT_GRAVITY_BODY_NAMES:
                    raise ValueError(
                        f"no declared gravity model for {source_body}"
                    )
                resource = _GravityAccelerationResource(
                    source_body=source_body,
                    acceleration_type=_POINT_MASS_GRAVITY_TYPE,
                    degree=None,
                    order=None,
                )
            else:
                resource = _GravityAccelerationResource(
                    source_body=source_body,
                    acceleration_type=_SPHERICAL_HARMONIC_GRAVITY_TYPE,
                    degree=field.degree,
                    order=field.order,
                )
            setting = _create_gravity_acceleration_setting(
                propagation_setup,
                resource,
            )
            settings_by_source[source_body] = (setting,)
            inventory.append(resource)

        frozen_inventory = tuple(inventory)
        _validate_gravity_acceleration_inventory(
            settings_by_source,
            frozen_inventory,
            harmonic_fields,
        )
    except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
        _raise_refinement_error(
            candidate_id,
            "force-model-construction",
            str(exc),
            exc,
        )
    return settings_by_source, frozen_inventory


def _thrust_and_srp_upper_bounds(
    candidate_id: object,
    spacecraft: SpacecraftSpec,
    minimum_sun_distance_m: float,
    *,
    thrust_enabled: bool,
) -> tuple[float, float]:
    """Return (thrust, fully lit SRP) norm bounds in m/s^2, in any orientation.

    Requires mass >= dry_mass and Sun distance >= the supplied positive floor.
    Other forces and native/numerical errors are excluded. Shadows cannot
    increase the bound; the caller must establish the mass/distance floors.
    """
    try:
        if not isinstance(spacecraft, SpacecraftSpec):
            raise TypeError("spacecraft must be a SpacecraftSpec")
        if not isinstance(thrust_enabled, bool):
            raise ValueError("thrust_enabled must be boolean")
        mass_kg, thrust_n, area_m2, cr = (
            Decimal.from_float(_positive_finite(f"spacecraft.{name}", getattr(spacecraft, name)))
            for name in ("dry_mass_kg", "max_thrust_n", "srp_area_m2", "reflectivity_coefficient")
        )
        distance_m = Decimal.from_float(_positive_finite(
            "minimum_sun_distance_m", minimum_sun_distance_m,
        ))
        with localcontext(Context(prec=50, rounding=ROUND_CEILING)):
            inverse_mass_kg_inv = Decimal(1) / mass_kg
            inverse_distance_m_inv = Decimal(1) / distance_m
            thrust_bound_m_s2 = thrust_n * inverse_mass_kg_inv if thrust_enabled else Decimal(0)
            # ponytail: pi > 3 gives a 4.72% conservative SRP envelope; tighten
            # this rational enclosure only if interval-guard cost requires it.
            srp_bound_m_s2 = (
                Decimal.from_float(SUN_LUMINOSITY_W) * area_m2 * cr * inverse_mass_kg_inv
                * inverse_distance_m_inv * inverse_distance_m_inv
                / Decimal(12 * int(_SPEED_OF_LIGHT_M_S))
            )
            bounds = tuple(
                _finite_float(f"{name} upper bound_m_s2", 0.0 if not bound else
                              math.nextafter(float(bound), math.inf))
                for name, bound in (("thrust", thrust_bound_m_s2), ("srp", srp_bound_m_s2))
            )
            return bounds[0], bounds[1]
    except (ArithmeticError, TypeError, ValueError) as exc:
        _raise_refinement_error(candidate_id, "thrust-srp-bound", str(exc), exc)


def _build_solar_radiation_pressure_setup(
    candidate_id: object,
    spacecraft: SpacecraftSpec,
) -> _SolarRadiationPressureSetup:
    """Build explicit Sun-source and cannonball-target Tudat settings."""

    try:
        if not isinstance(spacecraft, SpacecraftSpec):
            raise TypeError("spacecraft must be a SpacecraftSpec")
        initial_mass_kg = _positive_finite(
            "spacecraft.initial_mass_kg",
            spacecraft.initial_mass_kg,
        )
        reference_area_m2 = _positive_finite(
            "spacecraft.srp_area_m2",
            spacecraft.srp_area_m2,
        )
        reflectivity_coefficient = _positive_finite(
            "spacecraft.reflectivity_coefficient",
            spacecraft.reflectivity_coefficient,
        )
    except (TypeError, ValueError) as exc:
        _raise_refinement_error(
            candidate_id,
            "force-model-construction",
            str(exc),
            exc,
        )

    try:
        environment_setup = _import_tudat_environment_setup()
        propagation_setup = _import_tudat_propagation_setup()
    except RuntimeError as exc:
        _raise_refinement_error(
            candidate_id,
            "force-model-construction",
            str(exc),
            exc,
        )

    try:
        radiation_pressure = environment_setup.radiation_pressure
        luminosity_settings = radiation_pressure.constant_luminosity(
            SUN_LUMINOSITY_W
        )
        source_settings = radiation_pressure.isotropic_radiation_source(
            luminosity_settings
        )
        target_settings = radiation_pressure.cannonball_radiation_target(
            reference_area_m2,
            reflectivity_coefficient,
            {
                _SOLAR_RADIATION_SOURCE_BODY: list(
                    SOLAR_RADIATION_OCCULTING_BODY_NAMES
                )
            },
        )
        acceleration_setting = (
            propagation_setup.acceleration.radiation_pressure()
        )
    except Exception as exc:
        _raise_refinement_error(
            candidate_id,
            "force-model-construction",
            f"explicit Sun cannonball radiation-pressure setup failed: {exc}",
            exc,
        )

    resource = _SolarRadiationPressureResource(
        source_body=_SOLAR_RADIATION_SOURCE_BODY,
        target_body=SPACECRAFT_BODY_NAME,
        luminosity_w=SUN_LUMINOSITY_W,
        reference_area_m2=reference_area_m2,
        reflectivity_coefficient=reflectivity_coefficient,
        initial_mass_kg=initial_mass_kg,
        occulting_bodies=SOLAR_RADIATION_OCCULTING_BODY_NAMES,
        acceleration_type=_SOLAR_RADIATION_PRESSURE_TYPE,
        uses_current_body_mass=True,
    )
    return _SolarRadiationPressureSetup(
        source_settings=source_settings,
        target_settings=target_settings,
        acceleration_settings_by_source={
            _SOLAR_RADIATION_SOURCE_BODY: (acceleration_setting,)
        },
        resource=resource,
    )


def _schwarzschild_acceleration_upper_bound(
    candidate_id: object,
    gravitational_parameter_m3_s2: float,
    minimum_distance_m: float,
    maximum_relative_speed_m_s: float,
) -> float:
    """Bound the declared Sun Schwarzschild norm in m/s^2 for PPN beta=gamma=1.

    The caller must prove distance >= its floor and Sun-relative speed <= its
    ceiling throughout the interval. No native error or other force is included.
    """
    try:
        gm_m3_s2 = Decimal.from_float(_positive_finite(
            "gravitational_parameter_m3_s2", gravitational_parameter_m3_s2,
        ))
        distance_m = Decimal.from_float(_positive_finite("minimum_distance_m", minimum_distance_m))
        speed_m_s = Decimal.from_float(_finite_float(
            "maximum_relative_speed_m_s", maximum_relative_speed_m_s,
        ))
        if speed_m_s < 0:
            raise ValueError("maximum_relative_speed_m_s must be nonnegative")
        with localcontext(Context(prec=50, rounding=ROUND_CEILING)):
            inverse_distance_m_inv = Decimal(1) / distance_m
            # The exact orientation maximum is radial: 4*GM/r + 3*|v|^2.
            bound_m_s2 = (
                gm_m3_s2 * inverse_distance_m_inv * inverse_distance_m_inv
                * (4 * gm_m3_s2 * inverse_distance_m_inv + 3 * speed_m_s * speed_m_s)
                / Decimal(int(_SPEED_OF_LIGHT_M_S)**2)
            )
            result_m_s2 = math.nextafter(float(bound_m_s2), math.inf)
        return _finite_float("Schwarzschild upper bound_m_s2", result_m_s2)
    except (ArithmeticError, TypeError, ValueError) as exc:
        _raise_refinement_error(candidate_id, "schwarzschild-bound", str(exc), exc)


def _build_relativistic_acceleration_settings(
    candidate_id: object,
) -> tuple[dict[str, tuple[Any, ...]], _RelativityResource]:
    """Build the Sun Schwarzschild correction with all other terms disabled."""

    try:
        propagation_setup = _import_tudat_propagation_setup()
    except RuntimeError as exc:
        _raise_refinement_error(
            candidate_id,
            "force-model-construction",
            str(exc),
            exc,
        )

    try:
        setting = propagation_setup.acceleration.relativistic_correction(
            use_schwarzschild=True,
            use_lense_thirring=False,
            use_de_sitter=False,
            de_sitter_central_body="",
        )
    except Exception as exc:
        _raise_refinement_error(
            candidate_id,
            "force-model-construction",
            f"Sun Schwarzschild relativistic correction setup failed: {exc}",
            exc,
        )

    resource = _RelativityResource(
        source_body=_RELATIVITY_SOURCE_BODY,
        target_body=SPACECRAFT_BODY_NAME,
        acceleration_type=_RELATIVISTIC_ACCELERATION_TYPE,
        ppn_beta=_PPN_BETA,
        ppn_gamma=_PPN_GAMMA,
        schwarzschild_enabled=True,
        lense_thirring_enabled=False,
        de_sitter_enabled=False,
        einstein_infeld_hoffmann_enabled=False,
    )
    return {_RELATIVITY_SOURCE_BODY: (setting,)}, resource


def _set_general_relativity_ppn_parameters(
    candidate_id: object,
    bodies: Any,
) -> None:
    """Reset Tudat's mutable global PPN gamma and beta values to general relativity."""

    try:
        parameters_setup = _import_tudat_parameters_setup()
    except RuntimeError as exc:
        _raise_refinement_error(
            candidate_id,
            "force-model-construction",
            str(exc),
            exc,
        )

    try:
        parameter_set = parameters_setup.create_parameter_set(
            [
                parameters_setup.ppn_parameter_gamma(),
                parameters_setup.ppn_parameter_beta(),
            ],
            bodies,
        )
        parameter_set.parameter_vector = (_PPN_GAMMA, _PPN_BETA)
        ppn_gamma, ppn_beta = (
            float(value) for value in parameter_set.parameter_vector
        )
        if (ppn_gamma, ppn_beta) != (_PPN_GAMMA, _PPN_BETA):
            raise ValueError(
                "Tudat PPN parameter readback must equal gamma=1 and beta=1"
            )
    except Exception as exc:
        _raise_refinement_error(
            candidate_id,
            "force-model-construction",
            f"general-relativity PPN parameter setup failed: {exc}",
            exc,
        )


def _assign_sun_radiation_source(
    candidate_id: object,
    body_settings: Any,
    source_settings: Any,
) -> None:
    try:
        body_settings.get(_SOLAR_RADIATION_SOURCE_BODY).radiation_source_settings = (
            source_settings
        )
    except Exception as exc:
        _raise_refinement_error(
            candidate_id,
            "force-model-construction",
            f"explicit Sun radiation source installation failed: {exc}",
            exc,
        )


def _install_spacecraft_radiation_target(
    candidate_id: object,
    environment_setup: Any,
    bodies: Any,
    setup: _SolarRadiationPressureSetup,
) -> None:
    resource = setup.resource
    try:
        if bodies.does_body_exist(resource.target_body):
            raise ValueError(f"{resource.target_body} already exists")
        bodies.create_empty_body(resource.target_body)
        mass_settings = environment_setup.rigid_body.constant_rigid_body_properties(
            resource.initial_mass_kg
        )
        environment_setup.add_mass_properties_model(
            bodies,
            resource.target_body,
            mass_settings,
        )
        environment_setup.add_radiation_pressure_target_model(
            bodies,
            resource.target_body,
            setup.target_settings,
        )
    except Exception as exc:
        _raise_refinement_error(
            candidate_id,
            "force-model-construction",
            f"{resource.target_body} radiation target installation failed: {exc}",
            exc,
        )

    try:
        expected_bodies = set(PHYSICAL_BODY_NAMES) | {resource.target_body}
        if set(bodies.list_of_bodies()) != expected_bodies:
            raise ValueError(
                "radiation-pressure environment must contain exactly the eight "
                "physical sources and Spacecraft"
            )
        source_model = bodies.get(resource.source_body).radiation_pressure_source_model
        if source_model is None:
            raise ValueError("Sun radiation source model is missing")
        target_body = bodies.get(resource.target_body)
        current_mass_kg = _positive_finite(
            f"{resource.target_body}.current_mass_kg",
            target_body.mass,
        )
        if current_mass_kg != resource.initial_mass_kg:
            raise ValueError(
                f"{resource.target_body} current mass does not match initial mass"
            )
        target_models = target_body.radiation_pressure_target_models
        if len(target_models) != 1:
            raise ValueError(
                f"{resource.target_body} must have exactly one radiation target"
            )
        runtime_coefficient = _positive_finite(
            f"{resource.target_body}.reflectivity_coefficient",
            target_models[0].radiation_pressure_coefficient,
        )
        if runtime_coefficient != resource.reflectivity_coefficient:
            raise ValueError(
                f"{resource.target_body} radiation coefficient mismatch"
            )
    except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
        _raise_refinement_error(
            candidate_id,
            "force-model-construction",
            str(exc),
            exc,
        )


def _create_system_of_bodies(environment_setup: Any, body_settings: Any) -> Any:
    try:
        return environment_setup.create_system_of_bodies(body_settings)
    except Exception as exc:
        raise RuntimeError(
            "Tudat could not create the physical body system; verify SPICE "
            "coverage for the requested TDB interval"
        ) from exc


def _validate_created_environment(
    environment_setup: Any,
    bodies: Any,
    resources: tuple[_HarmonicFieldResource, ...],
    initial_epoch_tdb_s: float,
    final_epoch_tdb_s: float,
) -> None:
    if (
        bodies.global_frame_origin() != "SSB"
        or bodies.global_frame_orientation() != "J2000"
    ):
        raise ValueError("Tudat body system must use global frame SSB/J2000")
    if set(bodies.list_of_bodies()) != set(PHYSICAL_BODY_NAMES):
        raise ValueError(
            "Tudat body system does not contain the exact physical body set"
        )

    for body_name in PHYSICAL_BODY_NAMES:
        body = bodies.get(body_name)
        if (
            body.ephemeris.frame_origin != "SSB"
            or body.ephemeris.frame_orientation != "J2000"
        ):
            raise ValueError(f"{body_name} runtime ephemeris must use SSB/J2000")
        # Full SPK-chain coverage is checked before construction. The table
        # safe-interval API is not a coverage certificate for direct SPICE.
        for epoch_tdb_s in (initial_epoch_tdb_s, final_epoch_tdb_s):
            state = body.ephemeris.cartesian_state(epoch_tdb_s)
            _finite_cartesian_values(
                state,
                f"{body_name} ephemeris at TDB epoch {epoch_tdb_s}",
            )

    for resource in resources:
        body = bodies.get(resource.body)
        gravity_model = body.gravity_field_model
        rotation_model = body.rotation_model
        if (
            gravity_model.maximum_degree != resource.degree
            or gravity_model.maximum_order != resource.order
        ):
            raise ValueError(
                f"{resource.body} runtime harmonic degree/order mismatch"
            )
        gravitational_parameter_m3_s2 = _positive_finite(
            f"{resource.body} runtime gravitational_parameter_m3_s2",
            gravity_model.gravitational_parameter,
        )
        if not math.isclose(
            gravitational_parameter_m3_s2,
            resource.gravitational_parameter_m3_s2,
            rel_tol=_FIELD_GM_RELATIVE_TOLERANCE,
            abs_tol=0.0,
        ):
            raise ValueError(
                f"{resource.body} runtime gravitational parameter mismatch"
            )
        if gravity_model.reference_radius != resource.normalization_radius_m:
            raise ValueError(f"{resource.body} runtime normalization radius mismatch")
        if (
            rotation_model.inertial_frame_name != resource.rotation_base_frame
            or rotation_model.body_fixed_frame_name != resource.rotation_target_frame
        ):
            raise ValueError(f"{resource.body} runtime rotation frame mismatch")


def _build_physical_environment(
    candidate: ImpulsiveTransferCandidate,
    spacecraft: SpacecraftSpec,
    gravity_models_path: Path | None = None,
    *,
    budget: _RefinementBudget | None = None,
) -> _PhysicalEnvironment:
    """Build the verified SSB/J2000 environment under an optional shared budget.

    Checks are cooperative: native/resource calls are not interrupted, but
    their late results cannot proceed to the next preparation stage.
    """

    if budget is not None:
        budget.check()
    try:
        environment_setup = _import_tudat_environment_setup()
        resource_root = (
            _default_gravity_models_path()
            if gravity_models_path is None
            else Path(gravity_models_path)
        )
    except RuntimeError as exc:
        _raise_refinement_error(
            candidate.candidate_id,
            "environment-construction",
            str(exc),
            exc,
        )

    if budget is not None:
        budget.check()
    solar_radiation_pressure = _build_solar_radiation_pressure_setup(
        candidate.candidate_id,
        spacecraft,
    )
    if budget is not None:
        budget.check()

    try:
        verified_files = _verified_coefficient_files(resource_root)
    except (OSError, ValueError) as exc:
        _raise_refinement_error(
            candidate.candidate_id,
            "resource-validation",
            str(exc),
            exc,
        )

    if budget is not None:
        budget.check()
    try:
        ephemeris._ensure_standard_kernels()
    except EphemerisError as exc:
        _raise_refinement_error(
            candidate.candidate_id,
            "resource-validation",
            f"SPICE kernel initialization failed: {exc}",
            exc,
        )
    if budget is not None:
        budget.check()
    collision_resource = _build_collision_resource(candidate.candidate_id)
    if budget is not None:
        budget.check()

    try:
        _validate_direct_spice_coverage(
            candidate.candidate_id, candidate.departure_epoch_tdb_s,
            candidate.arrival_epoch_tdb_s, budget,
        )
        if budget is not None:
            budget.check()
        body_settings = _create_direct_body_settings(environment_setup)
        if budget is not None:
            budget.check()
        _validate_direct_body_settings(environment_setup, body_settings)
    except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
        _raise_refinement_error(
            candidate.candidate_id,
            "environment-construction",
            str(exc),
            exc,
        )

    resources = []
    for spec, coefficient_path, actual_sha256 in verified_files:
        if budget is not None:
            budget.check()
        try:
            gravity_settings = _load_harmonic_field_settings(
                environment_setup,
                spec,
                coefficient_path,
            )
            if budget is not None:
                budget.check()
            body_setting = body_settings.get(spec.body)
            resource = _validate_harmonic_field_settings(
                spec,
                gravity_settings,
                body_setting.rotation_model_settings,
                actual_sha256,
            )
            body_setting.gravity_field_settings = gravity_settings
            resources.append(resource)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            _raise_refinement_error(
                candidate.candidate_id,
                "resource-validation",
                f"{spec.body} {spec.model}: {exc}",
                exc,
            )

    if budget is not None:
        budget.check()
    harmonic_fields = tuple(resources)
    _assign_sun_radiation_source(
        candidate.candidate_id,
        body_settings,
        solar_radiation_pressure.source_settings,
    )
    if budget is not None:
        budget.check()
    try:
        bodies = _create_system_of_bodies(environment_setup, body_settings)
        if budget is not None:
            budget.check()
        _validate_created_environment(
            environment_setup,
            bodies,
            harmonic_fields,
            candidate.departure_epoch_tdb_s,
            candidate.arrival_epoch_tdb_s,
        )
    except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
        _raise_refinement_error(
            candidate.candidate_id,
            "environment-construction",
            str(exc),
            exc,
        )

    if budget is not None:
        budget.check()
    _install_spacecraft_radiation_target(
        candidate.candidate_id,
        environment_setup,
        bodies,
        solar_radiation_pressure,
    )
    if budget is not None:
        budget.check()
    _set_general_relativity_ppn_parameters(candidate.candidate_id, bodies)
    if budget is not None:
        budget.check()
    gravity_settings, gravity_inventory = _build_gravity_acceleration_settings(
        candidate.candidate_id,
        harmonic_fields,
    )
    if budget is not None:
        budget.check()
    relativity_settings, relativity = (
        _build_relativistic_acceleration_settings(candidate.candidate_id)
    )
    if budget is not None:
        budget.check()
    return _PhysicalEnvironment(
        model_id=PHYSICAL_MODEL_IDENTIFIER,
        initial_epoch_tdb_s=candidate.departure_epoch_tdb_s,
        final_epoch_tdb_s=candidate.arrival_epoch_tdb_s,
        origin="SSB",
        orientation="J2000",
        bodies=bodies,
        harmonic_fields=harmonic_fields,
        gravity_acceleration_settings=gravity_settings,
        gravity_acceleration_inventory=gravity_inventory,
        solar_radiation_pressure_acceleration_settings=(
            solar_radiation_pressure.acceleration_settings_by_source
        ),
        solar_radiation_pressure=solar_radiation_pressure.resource,
        relativistic_acceleration_settings=relativity_settings,
        relativity=relativity,
        collision_resource=collision_resource,
    )


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
    *,
    deadline_monotonic_s: float | None = None,
    monotonic: Callable[[], float] | None = None,
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
        if deadline_monotonic_s is None and monotonic is None:
            result = search_impulsive_transfers(scenario)
        else:
            result = _search_impulsive_transfers(
                scenario, deadline_monotonic_s=deadline_monotonic_s, monotonic=monotonic,
            )
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
