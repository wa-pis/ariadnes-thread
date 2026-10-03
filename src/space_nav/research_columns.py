"""Pure D10 central-column arithmetic; no solve, propagation or qualification."""

from __future__ import annotations

import math
from typing import Any

from . import trajectory as physical
from .research_correction import _PROBE_STEPS, _TRUST_SCALES


def _ratio(numerator: float, denominator: float) -> dict[str, Any]:
    physical._finite_float("ratio numerator", numerator)
    physical._finite_float("ratio denominator", denominator)
    if denominator == 0:
        return dict(value=None, unavailable_reason="zero-denominator")
    value = numerator / denominator
    return dict(
        value=value if math.isfinite(value) else None,
        unavailable_reason=None if math.isfinite(value) else "nonfinite-ratio",
    )


def _column_pair(
    baseline: tuple[float, ...],
    positive: tuple[float, ...],
    negative: tuple[float, ...],
    index: int,
    historical: tuple[float, ...],
    step: tuple[float, ...],
) -> dict[str, Any]:
    """Return one complete pair in scaled residual/trust coordinates."""
    if isinstance(index, bool) or not isinstance(index, int) or index not in range(6):
        raise ValueError("column index must be an integer from zero to five")
    base, plus, minus, old, delta = (
        physical._finite_cartesian_values(v, "column input")
        for v in (baseline, positive, negative, historical, step)
    )
    h, trust = _PROBE_STEPS[index], _TRUST_SCALES[index]
    checked = physical._finite_cartesian_values
    central = checked(
        tuple((p - m) * trust / (2 * h) for p, m in zip(plus, minus)), "central column"
    )
    forward = checked(
        tuple((p - b) * trust / h for p, b in zip(plus, base)), "forward column"
    )
    even = checked(
        tuple(
            ((p - b) + (m - b)) * trust / (2 * h) for p, m, b in zip(plus, minus, base)
        ),
        "even column",
    )
    result: dict[str, Any] = dict(
        index=index,
        probe_step=h,
        trust_scale=trust,
        central=central,
        forward=forward,
        even=even,
        historical=old,
    )
    for name, values in (("central", central), ("forward", forward), ("even", even)):
        result[name + "_contribution"] = checked(
            tuple(v * delta[index] / trust for v in values),
            "directional column contribution",
        )
    result["central_minus_historical"] = checked(
        tuple(c - o for c, o in zip(central, old)), "column difference"
    )
    result["forward_minus_historical"] = checked(
        tuple(f - o for f, o in zip(forward, old)), "column difference"
    )
    result["identity_defect"] = checked(
        tuple((f - c) - e for f, c, e in zip(forward, central, even)), "column identity"
    )
    return result


def _column_diagnostics(
    pairs: list[dict[str, Any]],
    retained_direction: tuple[float, ...],
    slopes: tuple[tuple[float, ...], ...],
) -> dict[str, Any]:
    """Compare the assembled central prediction to two retained nominal slopes."""
    if (
        len(pairs) != 6
        or [p["index"] for p in pairs] != list(range(6))
        or len(slopes) != 2
    ):
        raise ValueError("six ordered column pairs and two slopes required")
    checked = physical._finite_cartesian_values
    retained = checked(retained_direction, "retained direction")
    norm = physical._finite_float("retained directional norm", math.hypot(*retained))
    if norm == 0:
        raise ValueError("zero-retained-directional-norm")
    result: dict[str, Any] = dict(
        retained_direction=retained, retained_direction_norm=norm
    )
    for name in ("central", "forward", "even"):
        contributions = [
            checked(p[name + "_contribution"], "column contribution") for p in pairs
        ]
        try:
            direction = checked(
                tuple(math.fsum(row) for row in zip(*contributions)), "column direction"
            )
            summed_norms = math.fsum(math.hypot(*v) for v in contributions)
        except OverflowError as exc:
            raise ValueError("column direction overflow") from exc
        result[name + "_direction"] = direction
        result[name + "_cancellation"] = dict(
            sum_contribution_norms=summed_norms,
            direction_norm=math.hypot(*direction),
            **_ratio(summed_norms, math.hypot(*direction)),
        )
    result["direction_identity_defect"] = checked(
        tuple(
            (f - c) - e
            for f, c, e in zip(
                result["forward_direction"],
                result["central_direction"],
                result["even_direction"],
            )
        ),
        "direction identity",
    )
    checks = []
    for alpha, raw in zip((2**-14, 2**-15), slopes):
        slope = checked(raw, "retained nominal slope")
        vector = checked(
            tuple(d - c for d, c in zip(slope, result["central_direction"])),
            "slope discrepancy",
        )
        ratio = _ratio(math.hypot(*vector), norm)
        checks.append(
            dict(
                alpha=alpha,
                vector=vector,
                norm_ratio=ratio["value"],
                threshold=0.10,
                within_threshold=ratio["value"] is not None and ratio["value"] <= 0.10,
                unavailable_reason=ratio["unavailable_reason"],
            )
        )
    result.update(
        checks=checks,
        consistent=all(c["within_threshold"] for c in checks),
        threshold=0.10,
    )
    return result
