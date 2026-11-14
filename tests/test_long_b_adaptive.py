"""Check the longer adaptive dynamics without real ephemerides or archived fields."""

from __future__ import annotations

import math
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

EXPERIMENTS = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
ORIGINAL = run_path(str(EXPERIMENTS / "0183-earth-integrator.py"))
LONGER = run_path(str(EXPERIMENTS / "0186-long-b-integrator.py"))
ORIGINAL_REFERENCE = run_path(str(EXPERIMENTS / "0183-earth-reference.py"))
LONGER_REFERENCE = run_path(str(EXPERIMENTS / "0186-long-b-reference.py"))

INITIAL = {
    "epoch_tdb_s": 978995455.2304223,
    "position_m": [-4.7e10, 1.29e11, 5.57e10],
    "velocity_m_s": [-3e4, -9e3, -2.4e3],
}
type Row = dict[str, Any]


def source(body: str, epoch: float, frame: str, aberration: str, observer: str) -> list[float]:
    assert (body, observer) in LONGER["REQUESTS"] and (frame, aberration) == ("J2000", "NONE")
    assert math.isfinite(epoch)
    return [3e7, -1.2e8, 5e7, 30., 12., -.5] if observer == "SSB" else [150., 864., -9., 1., 0., .9]


def evaluate(core: Row, s: float, guards: dict[str, float]) -> Row:
    bud = core["Budget"](lambda: 0., 0.)
    row: Row = {}
    core["query_bodies"](s, INITIAL, source, bud, row, [])
    core["build_row"](INITIAL, s, [1., -3., 5., 0., 10., 50.], row["bodies"],
                      dict.fromkeys(LONGER["BODIES"], 1e12), guards, bud, row, moon_earth=row["moon_earth"])
    return row


@pytest.mark.parametrize("elapsed_s", [0., .123, 50., 300.])
def test_original_dynamics_and_independent_gates_preserved(elapsed_s: float) -> None:
    radii = dict.fromkeys(LONGER["BODIES"], 1.)
    old = evaluate(ORIGINAL, elapsed_s, radii)
    new = evaluate(LONGER, elapsed_s, radii)
    assert new == old
    assert LONGER_REFERENCE["assess_motion"](INITIAL, new["motion"]) == ORIGINAL_REFERENCE["assess_motion"](
        INITIAL, old["motion"])


def test_end_epoch_and_strict_earth_guard() -> None:
    radii = dict.fromkeys(LONGER["BODIES"], 1.)
    row = evaluate(LONGER, 600., radii)
    assert row["hi_tdb_s"] == INITIAL["epoch_tdb_s"] + 600.
    assert LONGER_REFERENCE["assess_motion"](INITIAL, row["motion"])["passed"]
    radii["Earth"] = row["geometry"]["Earth"]["distance_m"]
    with pytest.raises(ValueError, match="exterior guard: Earth"):
        evaluate(LONGER, 600., radii)
    with pytest.raises(ValueError, match="elapsed_s outside"):
        evaluate(LONGER, math.nextafter(600., math.inf), radii)
    with pytest.raises(ValueError, match="elapsed_s outside"):
        LONGER_REFERENCE["assess_motion"](INITIAL, {**row["motion"], "elapsed_s": 601.})
