"""Pure D7 correction arithmetic; no propagation or mission qualification."""

from __future__ import annotations

from dataclasses import dataclass
import math

from . import trajectory as physical
from .models import SpacecraftSpec


_PROBE_STEPS = (1e-5, 1e-5, 1.0) * 2  # rad, rad, s per burn
_TRUST_SCALES = (0.25, 0.25, 600.0) * 2  # rad, rad, s per burn
_RESIDUAL_SCALES = (1000.0,) * 3 + (0.01,) * 3  # m, m/s


@dataclass(frozen=True, slots=True)
class _Residual:
    values: tuple[float, ...]  # signed propagated-minus-target SI components
    scaled: tuple[float, ...]
    position_m: float
    velocity_m_s: float
    score: float
    closes: bool


def _residual(values: tuple[float, ...]) -> _Residual:
    raw = physical._finite_cartesian_values(values, "terminal residual")
    scaled = physical._finite_cartesian_values(
        tuple(v / s for v, s in zip(raw, _RESIDUAL_SCALES)), "scaled residual",
    )
    position, velocity, score = (
        physical._finite_float("residual norm", math.hypot(*v))
        for v in (raw[:3], raw[3:], scaled)
    )
    return _Residual(raw, scaled, position, velocity, score,
                     position <= 1000.0 and velocity <= 0.01)


@dataclass(frozen=True, slots=True)
class _Correction:
    residual_changes: tuple[tuple[float, ...], ...]  # probe-major SI
    jacobian: tuple[tuple[float, ...], ...]  # residual rows, control columns
    rank: int
    singular_values: tuple[float, ...]
    control_step: tuple[float, ...] | None  # rad, rad, s per burn
    reason: str | None


def _correction(
    baseline: tuple[float, ...], probes: tuple[tuple[float, ...], ...],
) -> _Correction:
    """One forward-difference solve; rank loss is a stopped result, not a retry."""
    base = _residual(baseline)
    if len(probes) != 6:
        raise ValueError("six ordered probe residuals required")
    measured = tuple(_residual(probe) for probe in probes)
    changes = tuple(physical._finite_cartesian_values(
        tuple(a - b for a, b in zip(probe.values, base.values)), "probe residual change",
    ) for probe in measured)
    columns = tuple(physical._finite_cartesian_values(
        tuple((a - b) / (h / s) for a, b in zip(probe.scaled, base.scaled)),
        "scaled Jacobian column",
    ) for probe, h, s in zip(measured, _PROBE_STEPS, _TRUST_SCALES))
    matrix = tuple(zip(*columns))
    result = _solve_matrix(matrix, base.scaled)
    return _Correction(changes, matrix, result.rank, result.singular_values,
                       result.control_step, result.reason)


@dataclass(frozen=True, slots=True)
class _MatrixStep:
    rank: int
    singular_values: tuple[float, ...]
    uncapped: tuple[float, ...]
    divisor: float | None
    capped: tuple[float, ...] | None
    control_step: tuple[float, ...] | None
    reason: str | None


def _solve_matrix(matrix: tuple[tuple[float, ...], ...], residual: tuple[float, ...]) -> _MatrixStep:
    """Shared D7/D11 dimensionless least-squares solve and physical trust cap."""
    import numpy as np

    if len(matrix) != 6:
        raise ValueError("six matrix rows required")
    rows = tuple(physical._finite_cartesian_values(row, "matrix row") for row in matrix)
    scaled = physical._finite_cartesian_values(residual, "scaled residual")
    try:
        solution, _, rank, singular = np.linalg.lstsq(rows, -np.array(scaled), rcond=1e-12)
    except np.linalg.LinAlgError as exc:
        raise ValueError("D7 least-squares solve failed") from exc
    dz = physical._finite_cartesian_values(solution, "least-squares solution")
    singular_values = physical._finite_cartesian_values(singular, "singular values")
    if rank < 6:
        return _MatrixStep(int(rank), singular_values, dz, None, None, None, "rank-deficient")
    divisor = max(1.0, max(abs(v) for v in dz))
    capped = physical._finite_cartesian_values(tuple(v/divisor for v in dz), "capped solution")
    step = physical._finite_cartesian_values(
        tuple(v / divisor * s for v, s in zip(dz, _TRUST_SCALES)), "control step",
    )
    return _MatrixStep(int(rank), singular_values, dz, divisor, capped, step, None)


def _central_correction(
    matrix: tuple[tuple[float, ...], ...], baseline: tuple[float, ...],
) -> dict[str, object]:
    """D11 solve with a recorded prediction; guards apply only to this mode."""
    from dataclasses import asdict

    base = _residual(baseline)
    result = _solve_matrix(matrix, base.scaled)
    data: dict[str, object] = dict(asdict(result), jacobian=matrix, predicted_change=None,
                                  predicted_residual=None, predicted_score=None)
    if result.control_step is None:
        return data
    try:
        change = physical._finite_cartesian_values(tuple(math.fsum(v*z for v, z in zip(row, result.capped))
                                                       for row in matrix), "predicted change")
    except OverflowError as exc:
        raise ValueError("prediction overflow") from exc
    predicted = physical._finite_cartesian_values(tuple(r+d for r, d in zip(base.scaled, change)), "predicted residual")
    score = physical._finite_float("predicted score", math.hypot(*predicted))
    data.update(predicted_change=change, predicted_residual=predicted, predicted_score=score)
    if not any(result.control_step):
        data["reason"] = "zero-control-step"
    elif score >= base.score:
        data["reason"] = "no-predicted-decrease"
    return data


def _trial_controls(
    candidate_id: str, spacecraft: SpacecraftSpec, departure_tdb_s: float,
    arrival_tdb_s: float, seed: tuple[float, ...], step: tuple[float, ...],
) -> tuple[float, ...] | str:
    """Apply one step through the existing angle/window/propellant gate."""
    checked = physical._prepare_burn_controls(
        candidate_id, spacecraft, departure_tdb_s, arrival_tdb_s, seed,
    )
    if isinstance(checked, str):
        return checked
    delta = physical._finite_cartesian_values(step, "control step")
    if any(abs(v) > s for v, s in zip(delta, _TRUST_SCALES)):
        raise ValueError("control step exceeds D7 trust scales")
    return physical._prepare_burn_controls(
        candidate_id, spacecraft, departure_tdb_s, arrival_tdb_s,
        tuple(a + b for a, b in zip(checked, delta)),
    )


def _improvement(
    baseline: tuple[float, ...], trial: tuple[float, ...], *, alpha: float = 1.0,
) -> tuple[bool, float | None, str | None]:
    """Return improvement, score ratio, unavailable-ratio reason; not accuracy."""
    alpha = physical._finite_float("damping alpha", alpha)
    if alpha not in (1.0, 0.5, 0.25):
        raise ValueError("damping alpha must be 1, 0.5 or 0.25")
    base, result = _residual(baseline), _residual(trial)
    ratio = result.score / base.score if base.score else None
    reason = "zero-baseline-score" if ratio is None else None
    if ratio is not None and not math.isfinite(ratio):
        ratio, reason = None, "nonfinite-score-ratio"
    return result.closes or result.score <= base.score * (1 - 1e-4 * alpha), ratio, reason
