"""Lazy TudatPy/SPICE access using the project's canonical reference frame."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import file_digest
import math
from numbers import Real
from pathlib import Path
import re
from threading import Lock
from typing import Any, Literal

from .errors import EphemerisError

ORIGIN: Literal["SSB"] = "SSB"
ORIENTATION: Literal["J2000"] = "J2000"
ABERRATION_CORRECTION = "NONE"

_J2000_CALENDAR_EPOCH = datetime(2000, 1, 1, 12, tzinfo=UTC)
_UTC_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
_kernel_lock = Lock()
_spice: Any | None = None
_kernels_loaded = False


@dataclass(frozen=True, slots=True)
class CartesianState:
    """A geometric body state in SI units and the SSB/J2000 frame."""

    body: str
    epoch_utc: str
    epoch_tdb_s: float
    origin: Literal["SSB"]
    orientation: Literal["J2000"]
    position_m: tuple[float, float, float]
    velocity_m_s: tuple[float, float, float]

    def __post_init__(self) -> None:
        if not isinstance(self.body, str) or not self.body.strip():
            raise ValueError("body must be a non-empty string")
        if not isinstance(self.epoch_utc, str) or not _UTC_PATTERN.fullmatch(
            self.epoch_utc
        ):
            raise ValueError("epoch_utc must be normalized ISO-8601 UTC text")
        if self.origin != ORIGIN or self.orientation != ORIENTATION:
            raise ValueError("CartesianState must use the SSB/J2000 frame")
        if (
            not isinstance(self.epoch_tdb_s, Real)
            or isinstance(self.epoch_tdb_s, bool)
            or not math.isfinite(self.epoch_tdb_s)
        ):
            raise ValueError("epoch_tdb_s must be finite")
        for name, vector in (
            ("position_m", self.position_m),
            ("velocity_m_s", self.velocity_m_s),
        ):
            if (
                not isinstance(vector, tuple)
                or len(vector) != 3
                or not all(
                    isinstance(value, Real)
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    for value in vector
                )
            ):
                raise ValueError(f"{name} must contain three finite values")


def _import_spice() -> Any:
    try:
        from tudatpy.interface import spice
    except Exception as exc:
        raise EphemerisError(
            "TudatPy/SPICE is unavailable; install the pinned project environment"
        ) from exc
    return spice


def _ensure_standard_kernels() -> Any:
    """Load TudatPy standard kernels once, on the first SPICE-backed request."""

    global _kernels_loaded, _spice
    if _kernels_loaded:
        return _spice
    with _kernel_lock:
        if _kernels_loaded:
            return _spice
        try:
            spice = _import_spice()
            spice.load_standard_kernels()
        except EphemerisError:
            raise
        except Exception as exc:
            raise EphemerisError(
                "TudatPy standard-kernel initialization failed; verify the pinned "
                "environment and its packaged kernel resources"
            ) from exc
        _spice = spice
        _kernels_loaded = True
        return spice


def _normalize_utc(epoch: str) -> str:
    if not isinstance(epoch, str) or not _UTC_PATTERN.fullmatch(epoch):
        raise EphemerisError(
            f"Invalid UTC epoch {epoch!r}; expected ISO-8601 text ending in 'Z'"
        )
    try:
        parsed = datetime.fromisoformat(epoch[:-1] + "+00:00")
    except ValueError as exc:
        raise EphemerisError(
            f"Invalid UTC epoch {epoch!r}; expected ISO-8601 text ending in 'Z'"
        ) from exc
    if parsed.utcoffset() != timedelta(0):
        raise EphemerisError(f"Invalid UTC epoch {epoch!r}; expected UTC ('Z')")
    normalized = parsed.astimezone(UTC).isoformat(timespec="microseconds")
    normalized = normalized.removesuffix("+00:00")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized + "Z"


def _coerce_tdb_epoch(epoch_tdb_s: object) -> float:
    if isinstance(epoch_tdb_s, bool):
        raise EphemerisError("TDB epoch must be a finite number")
    try:
        value = float(epoch_tdb_s)
    except (TypeError, ValueError) as exc:
        raise EphemerisError("TDB epoch must be a finite number") from exc
    if not math.isfinite(value):
        raise EphemerisError("TDB epoch must be a finite number")
    return value


def _tdb_to_utc_text(spice: Any, epoch_tdb_s: float) -> str:
    utc_seconds = float(spice.get_approximate_utc_from_tdb(epoch_tdb_s))
    utc_datetime = _J2000_CALENDAR_EPOCH + timedelta(seconds=utc_seconds)
    text = utc_datetime.isoformat(timespec="microseconds").removesuffix("+00:00")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text + "Z"


def _state_values(spice: Any, body: str, epoch_tdb_s: float) -> tuple[float, ...]:
    raw_state = spice.get_body_cartesian_state_at_epoch(
        target_body_name=body,
        observer_body_name=ORIGIN,
        reference_frame_name=ORIENTATION,
        aberration_corrections=ABERRATION_CORRECTION,
        ephemeris_time=epoch_tdb_s,
    )
    flatten = getattr(raw_state, "reshape", None)
    flat_state = flatten(-1) if callable(flatten) else raw_state
    return tuple(float(value) for value in flat_state)


def utc_to_tdb(epoch: str) -> float:
    """Convert ISO-8601 UTC text to TDB seconds since J2000 using SPICE."""

    normalized = _normalize_utc(epoch)
    try:
        spice = _ensure_standard_kernels()
    except EphemerisError as exc:
        raise EphemerisError(
            f"Could not initialize SPICE while converting UTC epoch {normalized!r}: {exc}"
        ) from exc
    try:
        value = float(spice.convert_date_string_to_ephemeris_time(normalized))
    except Exception as exc:
        raise EphemerisError(
            f"Could not convert UTC epoch {normalized!r} to TDB; verify kernel coverage"
        ) from exc
    if not math.isfinite(value):
        raise EphemerisError(
            f"SPICE returned a non-finite TDB value for UTC epoch {normalized!r}"
        )
    return value


def tdb_to_utc(epoch_tdb_s: float) -> str:
    """Convert TDB seconds since J2000 to normalized UTC text using SPICE."""

    epoch_tdb_s = _coerce_tdb_epoch(epoch_tdb_s)

    try:
        spice = _ensure_standard_kernels()
    except EphemerisError as exc:
        raise EphemerisError(
            f"Could not initialize SPICE while converting TDB epoch {epoch_tdb_s!r}: {exc}"
        ) from exc
    try:
        return _tdb_to_utc_text(spice, epoch_tdb_s)
    except Exception as exc:
        raise EphemerisError(
            f"Could not convert TDB epoch {epoch_tdb_s!r} to UTC; verify kernel coverage"
        ) from exc


def query_body_state(body: str, epoch: str) -> CartesianState:
    """Return a geometric SPICE state relative to SSB in J2000 and SI units."""

    if not isinstance(body, str) or not body.strip():
        raise EphemerisError(f"Unsupported SPICE body {body!r}")
    body = body.strip()
    try:
        normalized_epoch = _normalize_utc(epoch)
    except EphemerisError as exc:
        raise EphemerisError(
            f"Invalid epoch {epoch!r} requested for body {body!r}: {exc}"
        ) from exc

    try:
        spice = _ensure_standard_kernels()
    except EphemerisError as exc:
        raise EphemerisError(
            f"SPICE initialization failed for body {body!r} at {normalized_epoch!r}: {exc}"
        ) from exc
    try:
        epoch_tdb_s = float(
            spice.convert_date_string_to_ephemeris_time(normalized_epoch)
        )
        values = _state_values(spice, body, epoch_tdb_s)
    except Exception as exc:
        raise EphemerisError(
            f"SPICE state unavailable for body {body!r} at {normalized_epoch!r}; "
            "the body may be unsupported or the requested epoch may be outside "
            "available kernel coverage"
        ) from exc

    if len(values) != 6 or not all(math.isfinite(value) for value in values):
        raise EphemerisError(
            f"SPICE returned an invalid state for body {body!r} at {normalized_epoch!r}"
        )

    return CartesianState(
        body=body,
        epoch_utc=normalized_epoch,
        epoch_tdb_s=epoch_tdb_s,
        origin=ORIGIN,
        orientation=ORIENTATION,
        position_m=values[:3],
        velocity_m_s=values[3:],
    )


def _query_body_state_tdb(body: str, epoch_tdb_s: float) -> CartesianState:
    """Return an SSB/J2000 state at an exact TDB epoch without a UTC round-trip."""

    if not isinstance(body, str) or not body.strip():
        raise EphemerisError(f"Unsupported SPICE body {body!r}")
    body = body.strip()
    try:
        epoch_tdb_s = _coerce_tdb_epoch(epoch_tdb_s)
    except EphemerisError as exc:
        raise EphemerisError(
            f"Invalid TDB epoch {epoch_tdb_s!r} requested for body {body!r}: {exc}"
        ) from exc

    try:
        spice = _ensure_standard_kernels()
    except EphemerisError as exc:
        raise EphemerisError(
            f"SPICE initialization failed for body {body!r} at TDB epoch "
            f"{epoch_tdb_s!r}: {exc}"
        ) from exc
    try:
        values = _state_values(spice, body, epoch_tdb_s)
    except Exception as exc:
        raise EphemerisError(
            f"SPICE state unavailable for body {body!r} at TDB epoch "
            f"{epoch_tdb_s!r}; the body may be unsupported or the requested "
            "epoch may be outside available kernel coverage"
        ) from exc
    if len(values) != 6 or not all(math.isfinite(value) for value in values):
        raise EphemerisError(
            f"SPICE returned an invalid state for body {body!r} at TDB epoch "
            f"{epoch_tdb_s!r}"
        )
    try:
        epoch_utc = _tdb_to_utc_text(spice, epoch_tdb_s)
    except Exception as exc:
        raise EphemerisError(
            f"Could not label TDB epoch {epoch_tdb_s!r} as UTC for body "
            f"{body!r}; verify kernel coverage"
        ) from exc
    return CartesianState(
        body=body,
        epoch_utc=epoch_utc,
        epoch_tdb_s=epoch_tdb_s,
        origin=ORIGIN,
        orientation=ORIENTATION,
        position_m=values[:3],
        velocity_m_s=values[3:],
    )


def _get_body_gravitational_parameter(body: str) -> float:
    """Return a positive finite SPICE gravitational parameter in m^3/s^2."""

    if not isinstance(body, str) or not body.strip():
        raise EphemerisError(f"Unsupported SPICE body {body!r} for GM lookup")
    body = body.strip()
    try:
        spice = _ensure_standard_kernels()
    except EphemerisError as exc:
        raise EphemerisError(
            f"SPICE initialization failed while reading GM for body {body!r}: {exc}"
        ) from exc
    try:
        value = float(spice.get_body_gravitational_parameter(body))
    except Exception as exc:
        raise EphemerisError(
            f"SPICE gravitational parameter unavailable for body {body!r}"
        ) from exc
    if not math.isfinite(value) or value <= 0:
        raise EphemerisError(
            f"SPICE returned an invalid gravitational parameter for body {body!r}"
        )
    return value


def kernel_metadata() -> dict[str, Any]:
    """Inventory and hash the actual CSPICE pool initialized by TudatPy."""

    spice = _ensure_standard_kernels()
    try:
        import spiceypy

        pool_count = int(spiceypy.ktotal("ALL"))
        kernels = []
        for index in range(pool_count):
            entry = spiceypy.kdata(index, "ALL")
            path_text, kernel_type, source, _handle, *found = entry
            if found and not found[0]:
                raise RuntimeError(f"CSPICE did not return kernel index {index}")
            path = Path(path_text).resolve()
            with path.open("rb") as stream:
                digest = file_digest(stream, "sha256").hexdigest()
            kernels.append(
                {
                    "name": path.name,
                    "version": path.stem,
                    "type": kernel_type,
                    "source": source or None,
                    "size_bytes": path.stat().st_size,
                    "sha256": digest,
                }
            )
        count = int(spice.get_total_count_of_kernels_loaded())
        if count != pool_count:
            raise RuntimeError(
                f"TudatPy reports {count} kernels but CSPICE exposes {pool_count}"
            )
    except Exception as exc:
        raise EphemerisError(
            "Could not inventory the TudatPy standard kernels; verify the pinned "
            "TudatPy, SpiceyPy, and tudat-resources installation"
        ) from exc
    return {
        "kernel_source": "tudatpy-standard",
        "loaded_kernel_count": count,
        "spiceypy_version": str(getattr(spiceypy, "__version__", "unknown")),
        "kernels": kernels,
        "kernel_list_status": "complete",
    }
