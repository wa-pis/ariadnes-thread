"""Pure D9 scaled directional diagnostics; no propagation or correction solve."""

from __future__ import annotations

import math
from typing import Any

from . import trajectory as physical
from .research_correction import _TRUST_SCALES


_ALPHAS = (0.0, 2**-14, -(2**-14), 2**-15, -(2**-15))
_THRESHOLD = 0.10


def _direction(jacobian: tuple[tuple[float, ...], ...], step: tuple[float, ...]) -> tuple[float, ...]:
    """Return J*(dx/trust scales), in dimensionless residual coordinates."""
    delta = physical._finite_cartesian_values(step, "retained direction")
    if len(jacobian) != 6:
        raise ValueError("six Jacobian rows required")
    rows = tuple(physical._finite_cartesian_values(row, "Jacobian row") for row in jacobian)
    try:
        result = physical._finite_cartesian_values(tuple(
            math.fsum(v*d/s for v, d, s in zip(row, delta, _TRUST_SCALES)) for row in rows
        ), "predicted directional response")
    except OverflowError as exc:
        raise ValueError("predicted directional response overflow") from exc
    norm = physical._finite_float("directional norm", math.hypot(*result))
    if norm == 0:
        raise ValueError("zero-predicted-directional-norm; local response unavailable")
    return result


def _response_diagnostics(
    direction: tuple[float, ...], nominal: tuple[tuple[float, ...], ...],
    tighter: tuple[tuple[float, ...], ...],
) -> dict[str, Any]:
    """Compare five scaled residuals per profile; threshold is diagnostic only."""
    g = physical._finite_cartesian_values(direction, "predicted directional response")
    norm = physical._finite_float("directional norm", math.hypot(*g))
    if norm == 0:
        raise ValueError("zero-predicted-directional-norm; local response unavailable")
    checks: list[dict[str, Any]] = []
    profiles: dict[str, Any] = {}

    def checked(values: tuple[float, ...]) -> tuple[float, ...]:
        return physical._finite_cartesian_values(values, "local response arithmetic")

    def check(kind: str, profile: str, alpha: float, vector: tuple[float, ...]) -> None:
        length = physical._finite_float("discrepancy norm", math.hypot(*vector))
        ratio = length/norm
        finite = math.isfinite(ratio)
        checks.append(dict(kind=kind, profile=profile, alpha=alpha, vector=vector,
                           norm_ratio=ratio if finite else None, threshold=_THRESHOLD,
                           within_threshold=finite and ratio <= _THRESHOLD,
                           unavailable_reason=None if finite else "nonfinite-ratio"))

    for name, raw in (("nominal", nominal), ("tighter", tighter)):
        if len(raw) != 5:
            raise ValueError("five ordered scaled residuals per profile required")
        values = tuple(checked(v) for v in raw)
        baseline = values[0]
        samples = []
        for alpha, actual in zip(_ALPHAS, values):
            predicted = checked(tuple(v+alpha*d for v, d in zip(baseline, g)))
            samples.append(dict(alpha=alpha, predicted=predicted, actual=actual,
                                actual_change=checked(tuple(v-b for v, b in zip(actual, baseline))),
                                model_error=checked(tuple(v-p for v, p in zip(actual, predicted)))))
        slopes, curvatures = [], []
        for i in (1, 3):
            alpha = _ALPHAS[i]
            slope = checked(tuple((p-m)/(2*alpha) for p, m in zip(values[i], values[i+1])))
            curvature = checked(tuple(((p-b)+(m-b))/(2*alpha)
                                      for p, m, b in zip(values[i], values[i+1], baseline)))
            slopes.append(slope)
            curvatures.append(curvature)
            check("model", name, alpha, checked(tuple(v-d for v, d in zip(slope, g))))
            check("curvature", name, alpha, curvature)
        check("scale", name, _ALPHAS[1], checked(tuple(a-b for a, b in zip(*slopes))))
        profiles[name] = dict(samples=samples, slopes=slopes, curvatures=curvatures)
    for i, alpha in enumerate((_ALPHAS[1], _ALPHAS[3])):
        check("profile", "nominal-minus-tighter", alpha, checked(tuple(
            a-b for a, b in zip(profiles["nominal"]["slopes"][i], profiles["tighter"]["slopes"][i])
        )))
    return dict(direction=g, direction_norm=norm, profiles=profiles, checks=checks,
                consistent=all(c["within_threshold"] for c in checks), threshold=_THRESHOLD)
