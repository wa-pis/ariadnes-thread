"""Check a retained lunar range marker from already saved SI states."""

from __future__ import annotations

from collections.abc import Callable
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
import math
from typing import Any

MARKER_M = 3_000_000
RANGE_GATE_M = 1e-6
RADIAL_SPEED_GATE_M_S = 1e-9
COEPOCHS = ("native_normal", "native_tighter", "dop853_normal", "dop853_tighter")
MESHES = ("mesh_native_normal", "mesh_native_tighter")
type Sample = tuple[float, list[float], list[float]]
type Evidence = dict[str, Any]


def _finite(value: Any) -> float:
    if type(value) not in (float, int):
        raise ValueError("expected a finite binary64 number")
    try:
        word = float(value)
    except OverflowError as exc:
        raise ValueError("binary64 overflow") from exc
    if not math.isfinite(word):
        raise ValueError("expected a finite binary64 number")
    return word


def _state(values: list[float]) -> list[float]:
    if not isinstance(values, list) or len(values) != 6:
        raise ValueError("expected an SI six-state")
    return [_finite(w) for w in values]


def _sign(value: Fraction | Decimal) -> int:
    return (value > 0) - (value < 0)


def _dyadic_signs(spacecraft: list[float], moon: list[float]) -> tuple[int, int]:
    qx, qy, qz, vx, vy, vz = [
        Fraction(a) - Fraction(b) for a, b in zip(spacecraft, moon, strict=True)
    ]
    return (
        _sign(qx * qx + qy * qy + qz * qz - MARKER_M**2),
        _sign(qx * vx + qy * vy + qz * vz),
    )


def _decimal_geometry(
    spacecraft: list[float], moon: list[float],
) -> tuple[tuple[int, int], Decimal, Decimal]:
    with localcontext() as context:
        context.prec = 80
        context.rounding = ROUND_HALF_EVEN
        s, m = (list(map(Decimal.from_float, state)) for state in (spacecraft, moon))
        q = [s[i] - m[i] for i in range(3)]
        v = [s[i] - m[i] for i in range(3, 6)]
        radius2 = sum((word**2 for word in q), Decimal(0))
        dot = sum((q[i] * v[i] for i in range(3)), Decimal(0))
        if radius2 == 0:
            raise ValueError("undefined radial speed at lunar centre")
        radius = radius2.sqrt()
        return (_sign(radius2 - Decimal(MARKER_M)**2), _sign(dot)), radius, dot / radius


def _metrics_match(r1: float, v1: float, r2: float, v2: float) -> bool:
    return abs(r1 - r2) <= RANGE_GATE_M and abs(v1 - v2) <= RADIAL_SPEED_GATE_M_S


def measure(sample: Sample) -> Evidence:
    """Calculate and independently compare the range and radial signs at one sample."""
    epoch, raw_spacecraft, raw_moon = sample
    spacecraft, moon = _state(raw_spacecraft), _state(raw_moon)
    qx, qy, qz, vx, vy, vz = [a - b for a, b in zip(spacecraft, moon, strict=True)]
    radius = math.hypot(qx, qy, qz)
    if not math.isfinite(radius) or radius == 0:
        raise ValueError("undefined or nonfinite lunar radius")
    try:
        radial_speed = math.fsum((qx / radius * vx, qy / radius * vy, qz / radius * vz))
    except (OverflowError, ValueError) as exc:
        raise ValueError("nonfinite radial speed") from exc
    signs = _dyadic_signs(spacecraft, moon)
    decimal_signs, exact_radius, exact_speed = _decimal_geometry(spacecraft, moon)
    if signs != decimal_signs:
        raise ValueError("independent range or radial sign disagreement")
    if not _metrics_match(radius, radial_speed, float(exact_radius), float(exact_speed)):
        raise ValueError("independent range or radial-speed metric disagreement")
    return {
        "epoch_tdb_s": _finite(epoch),
        "spacecraft": spacecraft,
        "moon": moon,
        "radius_m": radius,
        "radial_speed_m_s": radial_speed,
        "range_sign": signs[0],
        "radial_sign": signs[1],
        "decimal80": {
            "radius_m": str(exact_radius),
            "radial_speed_m_s": str(exact_speed),
            "range_sign": decimal_signs[0],
            "radial_sign": decimal_signs[1],
        },
    }


def _summarize(rows: list[Evidence]) -> Evidence:
    equal = [r for r in rows if r["range_sign"] == 0]
    inward, outward, wrong_radial_sign = [], [], []
    for left, right in zip(rows, rows[1:]):
        if left["range_sign"] == -1 and right["range_sign"] == 1:
            if left["radial_sign"] > 0 and right["radial_sign"] > 0:
                outward.append((left, right))
            else:
                wrong_radial_sign.append((left, right))
        elif left["range_sign"] == 1 and right["range_sign"] == -1:
            inward.append((left, right))
    problems = [
        label for label, fails in (
            ("exact-equality", bool(equal)),
            ("inward-pair", bool(inward)),
            ("nonpositive-outward-endpoint", bool(wrong_radial_sign)),
            ("multiple-outward-pairs", len(outward) + len(wrong_radial_sign) > 1),
            ("missing-outward-pair", not outward),
        ) if fails
    ]
    evidence = {
        "status": "unresolved" if problems else "bracketed",
        "problems": problems,
        "equality_samples": equal,
        "inward_pairs": inward,
        "nonpositive_endpoint_pairs": wrong_radial_sign,
        "outward_pairs": outward,
    }
    if not problems:
        evidence.update(epochs_tdb_s=[r["epoch_tdb_s"] for r in outward[0]], endpoints=outward[0])
    return evidence


def _compare_overlapping_rows(common: Evidence, mesh: Evidence) -> None:
    if any(a.hex() != b.hex() for a, b in zip(common["spacecraft"], mesh["spacecraft"], strict=True)):
        raise ValueError("overlapping spacecraft words disagree")
    if (common["range_sign"], common["radial_sign"]) != (mesh["range_sign"], mesh["radial_sign"]):
        raise ValueError("overlapping Moon geometry signs disagree")
    if not _metrics_match(
        common["radius_m"], common["radial_speed_m_s"], mesh["radius_m"], mesh["radial_speed_m_s"],
    ):
        raise ValueError("overlapping Moon geometry metrics disagree")


def _intervals(brackets: dict[str, Evidence]) -> tuple[list[float], list[float]]:
    common = brackets[COEPOCHS[0]]["epochs_tdb_s"]
    if any(brackets[name]["epochs_tdb_s"] != common for name in COEPOCHS[1:]):
        raise ValueError("common-epoch brackets disagree")
    mesh = [brackets[name]["epochs_tdb_s"] for name in MESHES]
    if not all(common[0] <= a < b <= common[1] for a, b in mesh):
        raise ValueError("native bracket falls outside common bracket")
    overlap = [max(a for a, _ in mesh), min(b for _, b in mesh)]
    if overlap[0] >= overlap[1]:
        raise ValueError("native brackets do not overlap with positive width")
    return common, overlap


def analyze(
    grids: dict[str, list[Sample]], report: Evidence, check: Callable[[], None],
) -> None:
    """Check the six prescribed grids, retaining completed checks if a gate fails."""
    brackets: dict[str, Evidence] = {}
    report.update(grids=brackets, coepoch_rows=0, native_rows=0, marker_m=MARKER_M)
    if grids.keys() != set(COEPOCHS + MESHES) or not grids[COEPOCHS[0]]:
        raise ValueError("missing or unexpected retained grids")
    t0 = _finite(grids[COEPOCHS[0]][0][0])
    common_rows: dict[str, list[Evidence]] = {}
    for name, step_s in zip(COEPOCHS + MESHES, (50, 50, 50, 50, 1, 0.5), strict=True):
        check()
        key = "coepoch_rows" if name in COEPOCHS else "native_rows"
        rows: list[Evidence] = []
        detail: Evidence = {"status": "partial", "rows_checked": 0}
        brackets[name] = detail
        samples = grids[name]
        if len(samples) != 1 + int(600 / step_s):
            raise ValueError(f"{name}: wrong grid size")
        for i, sample in enumerate(samples):
            check()
            try:
                epoch, _, _ = sample
                epoch = _finite(epoch)
                if epoch.hex() != (t0 + i * step_s).hex() or (i > 0 and epoch <= rows[-1]["epoch_tdb_s"]):
                    raise ValueError("unexpected or duplicate grid epoch")
                row = measure(sample)
                if name in MESHES:
                    stride = int(50 / step_s)
                    if i % stride == 0:
                        _compare_overlapping_rows(common_rows[name.removeprefix("mesh_")][i // stride], row)
                elif name != COEPOCHS[0] and any(
                    a.hex() != b.hex() for a, b in zip(
                        row["moon"], common_rows[COEPOCHS[0]][i]["moon"], strict=True,
                    )
                ):
                    raise ValueError("noncommon Moon state at coepoch")
            except ValueError as exc:
                raise ValueError(f"{name} row {i}: {exc}") from exc
            rows.append(row)
            detail["rows_checked"] += 1
            report[key] += 1
        if name in COEPOCHS:
            common_rows[name] = rows
        detail.update(_summarize(rows))
        if detail["problems"]:
            raise ValueError(f"{name}: {', '.join(detail['problems'])}")
    common, overlap = _intervals(brackets)
    report.update(common_bracket_tdb_s=common, native_overlap_tdb_s=overlap)
    check()
