"""ADR0143 independent saved-node arithmetic. File/provenance entry point pending.

No runner, scientific-library or production imports; never propagates a state.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
import math
from typing import Any

GM = {"Sun": 1.327124400420322e20, "Moon": 4902800121846.8, "Earth": 398600435468295.9}
GUARDS = {"Sun": 696000000.0, "Moon": 1737400.0, "Earth": 6378136.6}
TAGS = ("native-normal", "native-tight", "oracle-normal", "oracle-tight")
OFFSETS = tuple(50.0 * j for j in range(7))
LABELS = {
    "origin": "SSB",
    "orientation": "J2000",
    "position_units": "m",
    "velocity_units": "m/s",
    "time_units": "TDB seconds since J2000",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def number(raw: object) -> float:
    require(type(raw) in (int, float), "finite nonboolean number required")
    try:
        value = float(raw)
    except OverflowError as exc:
        raise ValueError("number outside binary64") from exc
    require(math.isfinite(value), "finite number required")
    return value


def vector(raw: object, size: int) -> tuple[float, ...]:
    require(isinstance(raw, (list, tuple)) and len(raw) == size, "vector shape")
    return tuple(number(v) for v in raw)


def norm(values: tuple[Decimal, ...]) -> Decimal:
    return sum((v * v for v in values), Decimal(0)).sqrt()


def direct_force(
    position_m: object, body_m: object, mu_m3_s2: object, precision: int
) -> tuple[Decimal, ...]:
    """Independent inverse-cube Decimal field; zero GM supports analytic fixtures."""
    position, body = vector(position_m, 3), vector(body_m, 3)
    mu = number(mu_m3_s2)
    require(
        mu >= 0 and type(precision) is int and precision in (80, 100), "force domain"
    )
    with localcontext() as ctx:
        ctx.prec = precision
        delta = tuple(
            Decimal.from_float(b) - Decimal.from_float(a)
            for a, b in zip(position, body, strict=True)
        )
        squared = sum((v * v for v in delta), Decimal(0))
        require(squared > 0, "zero force distance")
        denominator = squared * squared.sqrt()
        return tuple(Decimal.from_float(mu) * v / denominator for v in delta)


def reference_force(
    position_m: object, body_m: object, mu_m3_s2: object
) -> tuple[tuple[Decimal, ...], list[str]]:
    normal = direct_force(position_m, body_m, mu_m3_s2, 80)
    tighter = direct_force(position_m, body_m, mu_m3_s2, 100)
    with localcontext() as ctx:
        ctx.prec = 100
        delta = tuple(a - b for a, b in zip(normal, tighter, strict=True))
        require(
            norm(delta) <= Decimal("1e-60") * norm(tighter), "Decimal force stability"
        )
        return tighter, [str(v) for v in delta]


def check_force(
    saved: object, expected: tuple[Decimal, ...], scale: Decimal | None = None
) -> dict[str, Any]:
    values = vector(saved, 3)
    with localcontext() as ctx:
        ctx.prec = 100
        magnitude = norm(expected) if scale is None else scale
        require(magnitude >= 0, "force scale")
        limit = max(Decimal("1e-15"), Decimal("1e-11") * magnitude)
        delta = tuple(
            Decimal.from_float(a) - b for a, b in zip(values, expected, strict=True)
        )
        error = norm(delta)
        require(error <= limit, "saved force arithmetic mismatch")
        return {
            "signed_error_m_s2": [str(v) for v in delta],
            "error_norm_m_s2": str(error),
            "limit_m_s2": str(limit),
        }


def check_difference(
    row: dict[str, Any], left: object, right: object
) -> dict[str, Any]:
    """Check signed rounded components and norms, retaining the expression tree."""
    a, b = vector(left, 6), vector(right, 6)
    with localcontext() as ctx:
        ctx.prec = 80
        expected = tuple(
            float(Decimal.from_float(y) - Decimal.from_float(x))
            for x, y in zip(a, b, strict=True)
        )
        vector(expected, 6)
        require(
            vector(row["right_minus_left_si"], 6) == expected, "signed state difference"
        )
        result: dict[str, Any] = {"right_minus_left_si": expected}
        for key, values in (
            ("position_norm_m", expected[:3]),
            ("velocity_norm_m_s", expected[3:]),
        ):
            binary = math.hypot(*values)
            decimal = norm(tuple(Decimal.from_float(v) for v in values))
            saved = number(row[key])
            require(saved == binary, "binary norm replay")
            error = abs(Decimal.from_float(saved) - decimal)
            require(
                error <= 4 * Decimal.from_float(math.ulp(saved)),
                "Decimal norm cross-check",
            )
            result[key] = saved
            result[key + "_decimal"] = str(decimal)
            result[key + "_rounding_error"] = str(error)
        return result


def check_gate(
    saved: object, difference: dict[str, Any], position_m: float, velocity_m_s: float
) -> bool:
    actual = (
        number(difference["position_norm_m"]) <= position_m
        and number(difference["velocity_norm_m_s"]) <= velocity_m_s
    )
    require(type(saved) is bool and saved is actual, "scientific gate mismatch")
    return actual


def history(raw: object, epoch: float, step: float) -> dict[float, Any]:
    require(isinstance(raw, dict), "history mapping required")
    result: dict[float, Any] = {}
    for key, value in raw.items():
        require(isinstance(key, str), "saved history string epoch required")
        at = number(float(key))
        require(at not in result, "numeric epoch-key collision")
        result[at] = value
    require(
        list(result) == [epoch + step * j for j in range(int(300 / step) + 1)],
        "exact history epoch grid",
    )
    return result


def check_profile(
    entry: dict[str, Any], model: str, tag: str, initial: object, epoch_tdb_s: object
) -> list[tuple[float, ...]]:
    """Validate saved native arrays or oracle corrections, without solver calls."""
    require(model in ("A", "B") and tag in TAGS, "model/profile name")
    initial_state, epoch = vector(initial, 6), number(epoch_tdb_s)
    result = entry["result"]
    require(result["model"] == model, "profile model")
    points = result["samples"]
    require(isinstance(points, list) and len(points) == 7, "seven profile samples")
    require(
        [number(p["epoch_tdb_s"]) for p in points] == [epoch + s for s in OFFSETS],
        "sample epochs",
    )
    values = [vector(p["state"], 6) for p in points]
    require(values[0] == initial_state, "initial state reset")
    tight = tag.endswith("tight")
    if tag.startswith("native"):
        sources = ("Sun", "Moon", "Earth") if model == "B" else ("Sun", "Moon")
        step, count = (0.5, 601) if tight else (1.0, 301)
        require(all(result[k] == v for k, v in LABELS.items()), "native labels")
        require(
            number(result["step_s"]) == step
            and type(result["retained_states"]) is int
            and result["retained_states"] == count
            and type(result["guarded_states"]) is int
            and result["guarded_states"] == count,
            "native profile/coverage",
        )
        require(
            tuple(result["force_order"]) == ("total",) + sources
            and result["gravity_parameters_m3_s2"] == GM,
            "native source/GM inventory",
        )
        for value in result["gravity_parameters_m3_s2"].values():
            number(value)
        raw = entry["raw_returned"]
        require(raw["integration_completed"] is True, "native integration incomplete")
        states = history(raw["state_history"], epoch, step)
        forces = history(raw["dependent_variable_history"], epoch, step)
        for at in states:
            vector(states[at], 6)
            force = vector(forces[at], 3 * (1 + len(sources)))
            total = tuple(
                math.fsum(force[3 + 3 * k + d] for k in range(len(sources)))
                for d in range(3)
            )
            require(math.dist(force[:3], total) <= 1e-12, "native force source sum")
        for point, state in zip(points, values, strict=True):
            at = point["epoch_tdb_s"]
            require(vector(states[at], 6) == state, "native raw/sample state parity")
            require(
                vector(point["acceleration_m_s2"], 3 * (1 + len(sources)))
                == vector(forces[at], 3 * (1 + len(sources))),
                "native raw/sample force parity",
            )
    else:
        require(
            result["tighter"] is tight and result["success"] is True,
            "oracle profile/success",
        )
        require(type(result["nfev"]) is int and result["nfev"] > 0, "oracle nfev")
        require(vector(result["offsets_s"], 7) == OFFSETS, "oracle offsets")
        corrections = result["corrections"]
        require(
            isinstance(corrections, list) and len(corrections) == 7,
            "oracle correction count",
        )
        require(vector(corrections[0], 6) == (0.0,) * 6, "zero initial correction")
        with localcontext() as ctx:
            ctx.prec = 80
            for offset, raw_q, state in zip(OFFSETS, corrections, values, strict=True):
                q = vector(raw_q, 6)
                position = tuple(
                    float(
                        Decimal.from_float(initial_state[j])
                        + Decimal.from_float(initial_state[j + 3] * offset)
                        + Decimal.from_float(q[j])
                    )
                    for j in range(3)
                )
                velocity = tuple(
                    float(
                        Decimal.from_float(initial_state[j]) + Decimal.from_float(q[j])
                    )
                    for j in range(3, 6)
                )
                require(position + velocity == state, "oracle correction/state parity")
    return values


def check_node_forces(
    block: dict[str, Any],
    model: str,
    body_table: object,
    states: dict[str, list[tuple[float, ...]]],
    epoch_tdb_s: object,
) -> list[dict[str, Any]]:
    """Check explanatory fields and actual native telemetry against saved bodies."""
    require(model in ("A", "B"), "force model")
    epoch = number(epoch_tdb_s)
    sources = tuple(GM) if model == "B" else ("Sun", "Moon")
    require(
        tuple(block["included_sources"]) == sources and block["gm_m3_s2"] == GM,
        "model source/GM metadata",
    )
    require(
        block["model_id"]
        == f"r5-ssb-sun-moon{'-earth' if model == 'B' else ''}-point-v1",
        "restricted model identity",
    )
    require(isinstance(body_table, list) and len(body_table) == 7, "seven body nodes")
    for j, node in enumerate(body_table):
        at = epoch + OFFSETS[j]
        require(
            number(node["epoch_tdb_s"]) == at and tuple(node["states"]) == tuple(GM),
            "body table epoch/inventory",
        )
        for body, value in node["states"].items():
            require(
                value["body"] == body
                and number(value["epoch_tdb_s"]) == at
                and value["origin"] == "SSB"
                and value["orientation"] == "J2000"
                and value["aberration_correction"] == "NONE",
                "body labels/epoch",
            )
            vector(value["position_m"], 3)
            vector(value["velocity_m_s"], 3)
    rows = block["node_forces"]
    require(isinstance(rows, list) and len(rows) == 28, "four by seven force rows")
    checked = []
    for index, row in enumerate(rows):
        tag, j = TAGS[index // 7], index % 7
        position = states[tag][j][:3]
        require(
            row["profile"] == tag
            and number(row["epoch_tdb_s"]) == epoch + OFFSETS[j]
            and vector(row["spacecraft_position_m"], 3) == position,
            "force operands",
        )
        require(tuple(row["per_source_m_s2"]) == sources, "force source inventory")
        raw_bodies = body_table[j]["states"]
        for body, radius in GUARDS.items():
            require(
                math.dist(position, raw_bodies[body]["position_m"]) > radius,
                "saved-node domain",
            )
        refs, diagnostics = {}, {}
        with localcontext() as ctx:
            ctx.prec = 100
            for body in sources:
                reference, stability = reference_force(
                    position, raw_bodies[body]["position_m"], GM[body]
                )
                refs[body] = reference
                diagnostics[body] = check_force(row["per_source_m_s2"][body], reference)
                diagnostics[body]["decimal80_minus100_m_s2"] = stability
            total = tuple(
                sum((v[d] for v in refs.values()), Decimal(0)) for d in range(3)
            )
            scale = sum((norm(v) for v in refs.values()), Decimal(0))
            diagnostics["total"] = check_force(row["total_m_s2"], total, scale)
            if tag.startswith("native"):
                sample = block["profiles"][tag]["result"]["samples"][j]
                raw_force = vector(sample["acceleration_m_s2"], 3 * (1 + len(sources)))
                diagnostics["native_total"] = check_force(raw_force[:3], total, scale)
                for k, body in enumerate(sources):
                    diagnostics["native_" + body] = check_force(
                        raw_force[3 + 3 * k : 6 + 3 * k], refs[body]
                    )
        checked.append(
            {"profile": tag, "epoch_tdb_s": epoch + OFFSETS[j], "forces": diagnostics}
        )
    return checked
