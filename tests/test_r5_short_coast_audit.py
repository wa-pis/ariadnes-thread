"""Independent saved-data fixtures only; no trajectory generation or native imports."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
import importlib.util
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0144-short-coast-audit.py"
spec = importlib.util.spec_from_file_location("r5_offline_arithmetic_tests", PATH)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

INITIAL = (1e9, 0.0, 0.0, 0.0, 0.0, 0.0)
BODIES = {"Sun": (0.0, 0.0, 0.0), "Moon": (2e9, 0.0, 0.0), "Earth": (3e9, 0.0, 0.0)}


def field(model: str) -> tuple[list[float], dict[str, list[float]]]:
    # Analytic collinear constant operands, not an integration or adapter call.
    names = ("Sun", "Moon", "Earth") if model == "B" else ("Sun", "Moon")
    parts = {
        b: [
            math.copysign(
                audit.GM[b] / (BODIES[b][0] - INITIAL[0]) ** 2,
                BODIES[b][0] - INITIAL[0],
            ),
            0.0,
            0.0,
        ]
        for b in names
    }
    total = [math.fsum(v[d] for v in parts.values()) for d in range(3)]
    return total, parts


def profile(model: str, tag: str) -> dict[str, Any]:
    total, parts = field(model)
    samples = [{"epoch_tdb_s": t, "state": list(INITIAL)} for t in audit.OFFSETS]
    result: dict[str, Any] = {"model": model, "samples": samples}
    entry = {"result": result}
    tight = tag.endswith("tight")
    if tag.startswith("native"):
        step, count = (0.5, 601) if tight else (1.0, 301)
        force = total + [x for vector in parts.values() for x in vector]
        for sample in samples:
            sample["acceleration_m_s2"] = list(force)
        result.update(
            audit.LABELS,
            step_s=step,
            retained_states=count,
            guarded_states=count,
            gravity_parameters_m3_s2=dict(audit.GM),
            force_order=["total", *parts],
        )
        entry["raw_returned"] = {
            "integration_completed": True,
            "state_history": {str(j * step): list(INITIAL) for j in range(count)},
            "dependent_variable_history": {
                str(j * step): list(force) for j in range(count)
            },
        }
    else:
        result.update(
            success=True,
            tighter=tight,
            nfev=16,
            offsets_s=list(audit.OFFSETS),
            corrections=[[0.0] * 6 for _ in range(7)],
        )
    return entry


def block(model: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    total, parts = field(model)
    result = {
        "model_id": f"r5-ssb-sun-moon{'-earth' if model == 'B' else ''}-point-v1",
        "included_sources": list(parts),
        "gm_m3_s2": dict(audit.GM),
        "profiles": {tag: profile(model, tag) for tag in audit.TAGS},
        "node_forces": [
            {
                "profile": tag,
                "epoch_tdb_s": t,
                "spacecraft_position_m": list(INITIAL[:3]),
                "per_source_m_s2": deepcopy(parts),
                "total_m_s2": list(total),
            }
            for tag in audit.TAGS
            for t in audit.OFFSETS
        ],
    }
    bodies = [
        {
            "epoch_tdb_s": t,
            "states": {
                b: {
                    "body": b,
                    "epoch_tdb_s": t,
                    "origin": "SSB",
                    "orientation": "J2000",
                    "aberration_correction": "NONE",
                    "position_m": list(p),
                    "velocity_m_s": [0.0] * 3,
                }
                for b, p in BODIES.items()
            },
        }
        for t in audit.OFFSETS
    ]
    return result, bodies


def check_block(
    b: dict[str, Any], bodies: list[dict[str, Any]], model: str
) -> list[dict[str, Any]]:
    values = {
        tag: audit.check_profile(entry, model, tag, INITIAL, 0.0)
        for tag, entry in b["profiles"].items()
    }
    return audit.check_node_forces(b, model, bodies, values, 0.0)


def difference(delta: tuple[float, ...]) -> dict[str, Any]:
    return {
        "right_minus_left_si": list(delta),
        "position_norm_m": math.hypot(*delta[:3]),
        "velocity_norm_m_s": math.hypot(*delta[3:]),
    }


def test_import_never_loads_science_or_adapters() -> None:
    code = f"import runpy,sys;runpy.run_path({str(PATH)!r});assert not any(k.startswith(('numpy','scipy','spiceypy','tudatpy','space_nav','r5_runner')) for k in sys.modules)"
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
    assert not hasattr(audit, "execute") and not hasattr(audit, "audit_file")


@pytest.mark.parametrize("shift", [(0.0, 0.0, 0.0), (1e11, -3e11, 2e11)])
def test_exact_3d_closed_form_and_translation(shift: tuple[float, ...]) -> None:
    body = tuple(s + d for s, d in zip(shift, (2.0, -3.0, 6.0), strict=True))
    result, stability = audit.reference_force(shift, body, 343.0)
    assert result == (Decimal(2), Decimal(-3), Decimal(6))
    assert all(Decimal(x) == 0 for x in stability)
    assert audit.reference_force(shift, body, 0.0)[0] == (Decimal(0),) * 3


def test_irrational_force_80_100_stability_and_independent_norm() -> None:
    value, changes = audit.reference_force((0.0, 0.0, 0.0), (1.0, 2.0, -3.0), 7.0)
    with localcontext() as ctx:
        ctx.prec = 100
        assert abs(audit.norm(value) - Decimal("0.5")) < Decimal("1e-98")
        assert audit.norm(tuple(Decimal(v) for v in changes)) < Decimal("1e-60")
        assert value[0] * 2 == value[1] and value[2] < 0


@pytest.mark.parametrize(
    "position,body,mu,precision",
    [
        ((0.0,) * 3, (0.0,) * 3, 1.0, 80),
        ((True, 0.0, 0.0), (1.0,) * 3, 1.0, 80),
        ((0.0,) * 3, (1.0,) * 3, -1.0, 80),
        ((0.0,) * 3, (1.0,) * 3, float("inf"), 80),
        ((0.0,) * 3, (1.0,) * 3, 1.0, 28),
        ((0.0,) * 3, (1.0, 2.0), 1.0, 100),
    ],
)
def test_force_invalid_domain(
    position: object, body: object, mu: object, precision: int
) -> None:
    with pytest.raises(ValueError):
        audit.direct_force(position, body, mu, precision)


def test_force_tolerance_cancellation_and_wrong_sign() -> None:
    zero = (Decimal(0),) * 3
    audit.check_force((1e-12, 0.0, 0.0), zero, Decimal(2))
    with pytest.raises(ValueError, match="arithmetic"):
        audit.check_force((1e-12, 0.0, 0.0), zero)
    with pytest.raises(ValueError, match="arithmetic"):
        audit.check_force((-1.0, 0.0, 0.0), (Decimal(1), Decimal(0), Decimal(0)))


def test_signed_3d_difference_norm_and_corruption() -> None:
    left, right = (
        (1e11, -2e11, 3e11, 4.0, 5.0, 6.0),
        (1e11 + 3, -2e11 + 4, 3e11, 4.0, 5.0, -6.0),
    )
    row = difference((3.0, 4.0, 0.0, 0.0, 0.0, -12.0))
    checked = audit.check_difference(row, left, right)
    assert checked["position_norm_m"] == 5.0 and checked["velocity_norm_m_s"] == 12.0
    reversed_row = deepcopy(row)
    reversed_row["right_minus_left_si"] = [-v for v in row["right_minus_left_si"]]
    with pytest.raises(ValueError, match="signed"):
        audit.check_difference(reversed_row, left, right)
    row["position_norm_m"] = math.nextafter(5.0, math.inf)
    with pytest.raises(ValueError, match="norm replay"):
        audit.check_difference(row, left, right)


@pytest.mark.parametrize("limit,velocity", [(0.01, 1e-5), (0.001, 1e-6), (0.02, 2e-5)])
def test_exact_adjacent_gate_boundaries_do_not_expand(
    limit: float, velocity: float
) -> None:
    for pos in [math.nextafter(limit, 0.0), limit, math.nextafter(limit, math.inf)]:
        row = difference((pos, 0.0, 0.0, velocity, 0.0, 0.0))
        replay = audit.check_difference(row, (0.0,) * 6, row["right_minus_left_si"])
        expected = pos <= limit
        assert audit.check_gate(expected, replay, limit, velocity) is expected
        with pytest.raises(ValueError, match="gate mismatch"):
            audit.check_gate(not expected, replay, limit, velocity)
        with pytest.raises(ValueError, match="gate mismatch"):
            audit.check_gate(int(expected), replay, limit, velocity)
    row = difference((limit, 0.0, 0.0, math.nextafter(velocity, math.inf), 0.0, 0.0))
    assert audit.check_gate(False, row, limit, velocity) is False


@pytest.mark.parametrize("model", ["A", "B"])
def test_all_profiles_raw_arrays_and_actual_node_telemetry(model: str) -> None:
    data, bodies = block(model)
    before = deepcopy(data)
    checks = check_block(data, bodies, model)
    assert len(checks) == 28 and data == before
    assert all("native_total" in r["forces"] for r in checks[:14])
    assert all("native_total" not in r["forces"] for r in checks[14:])
    assert ("Earth" in checks[-1]["forces"]) is (model == "B")


@pytest.mark.parametrize(
    "fault",
    [
        "count",
        "step",
        "boolean",
        "epoch",
        "state",
        "force",
        "sum",
        "collision",
        "missing",
        "finite",
        "labels",
        "gm",
        "sources",
        "completed",
    ],
)
def test_native_corruption_is_rejected(fault: str) -> None:
    entry = profile("A", "native-normal")
    r, raw = entry["result"], entry["raw_returned"]
    if fault == "count":
        r["retained_states"] = 300
    elif fault == "step":
        r["step_s"] = 0.5
    elif fault == "boolean":
        r["step_s"] = True
    elif fault == "epoch":
        r["samples"][2]["epoch_tdb_s"] += 1
    elif fault == "state":
        raw["state_history"]["50.0"][0] += 1
    elif fault == "force":
        r["samples"][0]["acceleration_m_s2"][0] += 1
    elif fault == "sum":
        raw["dependent_variable_history"]["1.0"][0] += 1
    elif fault == "collision":
        raw["state_history"]["0e0"] = list(INITIAL)
    elif fault == "missing":
        del raw["dependent_variable_history"]["1.0"]
    elif fault == "finite":
        raw["state_history"]["1.0"][0] = float("nan")
    elif fault == "labels":
        r["origin"] = "Sun"
    elif fault == "gm":
        r["gravity_parameters_m3_s2"]["Moon"] += 1
    elif fault == "sources":
        r["force_order"] = ["total", "Moon", "Sun"]
    else:
        raw["integration_completed"] = False
    with pytest.raises(ValueError):
        audit.check_profile(entry, "A", "native-normal", INITIAL, 0.0)


@pytest.mark.parametrize(
    "fault",
    [
        "offset",
        "profile",
        "success",
        "nfev",
        "initial",
        "correction",
        "shape",
        "boolean",
    ],
)
def test_oracle_corruption_is_rejected(fault: str) -> None:
    entry = profile("B", "oracle-tight")
    r = entry["result"]
    if fault == "offset":
        r["offsets_s"][-1] += 1
    elif fault == "profile":
        r["tighter"] = False
    elif fault == "success":
        r["success"] = 1
    elif fault == "nfev":
        r["nfev"] = True
    elif fault == "initial":
        r["corrections"][0][0] = 1.0
    elif fault == "correction":
        r["corrections"][2][1] = 1.0
    elif fault == "shape":
        r["corrections"][2] = [0.0]
    else:
        r["samples"][1]["state"][2] = True
    with pytest.raises(ValueError):
        audit.check_profile(entry, "B", "oracle-tight", INITIAL, 0.0)


def test_oracle_reconstruction_preserves_product_then_exact_sum_rounding() -> None:
    entry = profile("A", "oracle-normal")
    initial = (1e16, 0.0, 0.0, 1.1, 0.0, 0.0)
    r = entry["result"]
    r["samples"][0]["state"] = list(initial)
    for j, elapsed in enumerate(audit.OFFSETS[1:], 1):
        r["corrections"][j] = [-1e16, 0.0, 0.0, 0.125, 0.0, 0.0]
        r["samples"][j]["state"] = [
            math.fsum((1e16, 1.1 * elapsed, -1e16)),
            0.0,
            0.0,
            1.225,
            0.0,
            0.0,
        ]
    audit.check_profile(entry, "A", "oracle-normal", initial, 0.0)
    r["samples"][1]["state"][0] = (1e16 + 1.1 * 50) - 1e16
    with pytest.raises(ValueError, match="correction/state"):
        audit.check_profile(entry, "A", "oracle-normal", initial, 0.0)


@pytest.mark.parametrize(
    "fault",
    [
        "force_sign",
        "total",
        "native",
        "body_epoch",
        "frame",
        "position",
        "inventory",
        "row_order",
        "domain",
    ],
)
def test_node_force_operand_and_telemetry_corruption(fault: str) -> None:
    data, bodies = block("B")
    if fault == "force_sign":
        data["node_forces"][0]["per_source_m_s2"]["Earth"][0] *= -1
    elif fault == "total":
        data["node_forces"][0]["total_m_s2"][0] += 0.1
    elif fault == "native":
        for p in data["profiles"]["native-normal"]["result"]["samples"]:
            p["acceleration_m_s2"][0] += 0.1
            p["acceleration_m_s2"][3] += 0.1
        raw = data["profiles"]["native-normal"]["raw_returned"][
            "dependent_variable_history"
        ]
        for v in raw.values():
            v[0] += 0.1
            v[3] += 0.1
    elif fault == "body_epoch":
        bodies[1]["states"]["Sun"]["epoch_tdb_s"] += 1
    elif fault == "frame":
        bodies[0]["states"]["Earth"]["orientation"] = "ECLIPJ2000"
    elif fault == "position":
        data["node_forces"][0]["spacecraft_position_m"][0] += 1
    elif fault == "inventory":
        data["included_sources"].append("Mars")
    elif fault == "row_order":
        data["node_forces"].reverse()
    else:
        bodies[0]["states"]["Moon"]["position_m"] = list(INITIAL[:3])
    with pytest.raises(ValueError):
        check_block(data, bodies, "B")


@pytest.mark.parametrize("tag", ["native-tight", "oracle-tight"])
def test_exact_reference_epoch_translation_without_time_queries(tag: str) -> None:
    entry = profile("A", tag)
    epoch = 978995455.2304223
    for point in entry["result"]["samples"]:
        point["epoch_tdb_s"] += epoch
    if tag.startswith("native"):
        for name in ("state_history", "dependent_variable_history"):
            original = entry["raw_returned"][name]
            entry["raw_returned"][name] = {
                str(epoch + float(k)): v for k, v in original.items()
            }
    values = audit.check_profile(entry, "A", tag, INITIAL, epoch)
    assert values == [INITIAL] * 7
    entry["result"]["samples"][1]["epoch_tdb_s"] = math.nextafter(epoch + 50, math.inf)
    with pytest.raises(ValueError, match="sample epochs"):
        audit.check_profile(entry, "A", tag, INITIAL, epoch)


def test_erroneous_indirect_origin_term_cannot_pass_force_audit() -> None:
    data, bodies = block("B")
    earth = data["node_forces"][0]["per_source_m_s2"]["Earth"]
    earth[0] -= audit.GM["Earth"] / BODIES["Earth"][0] ** 2
    with pytest.raises(ValueError, match="saved force arithmetic"):
        check_block(data, bodies, "B")
