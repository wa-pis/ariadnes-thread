"""Verified M2 handoff for physical trajectory refinement."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from hashlib import file_digest
import math
from numbers import Real
from pathlib import Path
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
EPHEMERIS_TIME_STEP_S = 300.0

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


def _build_arc_force_models(
    candidate_id: object,
    environment: _PhysicalEnvironment,
) -> Any:
    """Assemble external SSB/J2000 forces, resetting global PPN for each arc.

    This excludes engine thrust. Native SPICE/PPN mutation must be serialized
    with other simulations; the returned models do not freeze global state.
    """
    try:
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
        return propagation_setup.create_acceleration_models(
            environment.bodies,
            {SPACECRAFT_BODY_NAME: settings},
            [SPACECRAFT_BODY_NAME],
            ["SSB"],
        )
    except Exception as exc:
        _raise_refinement_error(
            candidate_id, "force-model-construction",
            f"arc external acceleration assembly failed: {exc}", exc,
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
        safe_start_tdb_s, safe_end_tdb_s = (
            environment_setup.get_safe_interpolation_interval(body.ephemeris)
        )
        if (
            safe_start_tdb_s > initial_epoch_tdb_s
            or safe_end_tdb_s < final_epoch_tdb_s
        ):
            raise ValueError(
                f"{body_name} runtime ephemeris does not cover TDB interval "
                f"[{initial_epoch_tdb_s}, {final_epoch_tdb_s}]"
            )
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
) -> _PhysicalEnvironment:
    """Build the verified, time-limited SSB/J2000 force environment."""

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

    solar_radiation_pressure = _build_solar_radiation_pressure_setup(
        candidate.candidate_id,
        spacecraft,
    )

    try:
        verified_files = _verified_coefficient_files(resource_root)
    except (OSError, ValueError) as exc:
        _raise_refinement_error(
            candidate.candidate_id,
            "resource-validation",
            str(exc),
            exc,
        )

    try:
        ephemeris._ensure_standard_kernels()
    except EphemerisError as exc:
        _raise_refinement_error(
            candidate.candidate_id,
            "resource-validation",
            f"SPICE kernel initialization failed: {exc}",
            exc,
        )
    collision_resource = _build_collision_resource(candidate.candidate_id)

    try:
        body_settings = _create_time_limited_body_settings(
            environment_setup,
            candidate.departure_epoch_tdb_s,
            candidate.arrival_epoch_tdb_s,
        )
        _validate_time_limited_body_settings(
            body_settings,
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

    resources = []
    for spec, coefficient_path, actual_sha256 in verified_files:
        try:
            gravity_settings = _load_harmonic_field_settings(
                environment_setup,
                spec,
                coefficient_path,
            )
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

    harmonic_fields = tuple(resources)
    _assign_sun_radiation_source(
        candidate.candidate_id,
        body_settings,
        solar_radiation_pressure.source_settings,
    )
    try:
        bodies = _create_system_of_bodies(environment_setup, body_settings)
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

    _install_spacecraft_radiation_target(
        candidate.candidate_id,
        environment_setup,
        bodies,
        solar_radiation_pressure,
    )
    _set_general_relativity_ppn_parameters(candidate.candidate_id, bodies)
    gravity_settings, gravity_inventory = _build_gravity_acceleration_settings(
        candidate.candidate_id,
        harmonic_fields,
    )
    relativity_settings, relativity = (
        _build_relativistic_acceleration_settings(candidate.candidate_id)
    )
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
