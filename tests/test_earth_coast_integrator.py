"""Synthetic direct Earth gravity and observer invariants, without native ephemerides."""

from __future__ import annotations

from decimal import Decimal, localcontext
import math
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

EXPERIMENTS = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
B = run_path(str(EXPERIMENTS / "0183-earth-integrator.py"))
A = run_path(str(EXPERIMENTS / "0180-split-integrator.py"))
Row = dict[str, Any]


def bundle() -> Row:
    return {
        "initial": {
            "epoch_tdb_s": 978995455.2304223,
            "position_m": [1e6, 0., 0.],
            "velocity_m_s": [0., 1e3, 0.],
        },
        "offsets_s": list(B["OFFSETS"]),
        "gm_m3_s2": dict.fromkeys(B["BODIES"], 1e12),
        "radii_m": dict.fromkeys(B["BODIES"], 1.),
    }


def source(body: str, epoch: float, frame: str, abcorr: str, observer: str) -> list[float]:
    assert math.isfinite(epoch)
    assert (body, observer) in B["REQUESTS"] and (frame, abcorr) == ("J2000", "NONE")
    z = -1e6 if observer == "Earth" else (1e6 if body == "Earth" else 0.)
    return [0., 0., z, 0., 0., 0.]


def row(core: Row, inputs: Row, offset: float) -> tuple[Row, Any]:
    budget = core["Budget"](lambda: 0., 0.)
    data: Row = {}
    bodies = core["query_bodies"](offset, inputs["initial"], source, budget, data, [])
    core["build_row"](inputs["initial"], offset, [0., 2., 3., 4., 5., 6.],
                      bodies, inputs["gm_m3_s2"], inputs["radii_m"], budget, data,
                      moon_earth=data["moon_earth"])
    return data, budget


@pytest.mark.parametrize("offset", [.123, .3])
def test_b_adds_only_direct_earth_field(offset: float) -> None:
    inputs = bundle()
    b, budget = row(B, inputs, offset)
    a, _ = row(A, inputs, offset)
    assert b["motion"] == a["motion"] and b["lo_s"] == a["lo_s"] != 0.
    assert b["geometry"]["Sun"] == a["geometry"]["Sun"]
    assert b["geometry"]["Moon"] == a["geometry"]["Moon"]
    earth = b["geometry"]["Earth"]
    assert all(earth[k] == v for k, v in a["geometry"]["Earth"].items())
    with localcontext() as ctx:
        ctx.prec = 80
        d = list(map(Decimal.from_float, earth["separation_m"]))
        d2 = sum(x * x for x in d)
        mu = Decimal.from_float(inputs["gm_m3_s2"]["Earth"])
        expected = [float(mu * x / (d2 * d2.sqrt())) for x in d]
    assert math.dist(expected, earth["acceleration_m_s2"]) < 1e-21
    assert earth["acceleration_m_s2"][0] < 0 and earth["acceleration_m_s2"][2] > 0
    assert b["derivative"][:3] == a["derivative"][:3]
    assert b["derivative"][3:] == [
        math.fsum(b["geometry"][body]["acceleration_m_s2"][j] for body in B["BODIES"])
        for j in range(3)
    ]
    assert budget.counts["binary64_fields"]["completed"] == 3


def test_zero_term_preserves_a_path_without_bypassing_earth_guard() -> None:
    inputs = bundle()
    inputs["gm_m3_s2"]["Earth"] = math.ulp(0.)
    b, budget = row(B, inputs, .123)
    a, _ = row(A, inputs, .123)
    assert b["derivative"] == a["derivative"]
    assert budget.counts["binary64_fields"]["completed"] == 3
    inputs["radii_m"]["Earth"] = b["geometry"]["Earth"]["distance_m"]
    with pytest.raises(ValueError, match="exterior guard: Earth"):
        row(B, inputs, .123)


@pytest.mark.parametrize("name", ["normal", "tighter"])
def test_observer_keeps_b_solution_and_records_four_sources(name: str) -> None:
    inputs = bundle()
    results = []
    for observed in (True, False):
        report = {key: [] for key in ("rhs", "trials", "node_table", "profiles", "state_requests")}
        budget = B["Budget"](lambda: 0., 0.)
        B["fill_node_table"](inputs, report, source, budget)
        with pytest.raises(ValueError, match="already started"):
            B["fill_node_table"](inputs, report, source, budget)
        out = B["solve_profile"](inputs, name, report, source, budget, observed=observed)
        assert budget.counts["states"]["completed"] == 4 * (len(report["rhs"]) + 7)
        assert budget.counts["binary64_fields"]["completed"] == 3 * (len(report["rhs"]) + 7)
        assert any(abs(x) > 1 for x in out["raw_returned"]["y"][0][1:])
        assert any(r["lo_s"] for r in report["rhs"][:7])
        assert bool(report["trials"]) is observed
        results.append(out["raw_returned"])
    assert results[0] == results[1]


def test_shared_table_retains_late_return_without_completing() -> None:
    inputs = bundle()
    clock = [0.]
    budget = B["Budget"](lambda: clock[0], 0.)
    report: Row = {"node_table": [], "state_requests": []}

    def late(body: str, epoch: float, frame: str, abcorr: str, observer: str) -> list[float]:
        if observer == "Earth":
            clock[0] = 60.
        return source(body, epoch, frame, abcorr, observer)

    with pytest.raises(ValueError, match="deadline"):
        B["fill_node_table"](inputs, report, late, budget)
    assert report["node_table"][0]["moon_earth"]["state_km_km_s"][2] == -1e6
    assert budget.counts["states"] == {"attempted": 4, "returned": 4, "completed": 3}
    assert len(report["state_requests"]) == 4
    clock[0] = 0.
    with pytest.raises(ValueError, match="already started"):
        B["fill_node_table"](inputs, report, source, budget)
