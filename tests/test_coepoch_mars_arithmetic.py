"""Known-anomaly controls for the private coepoch worksheet."""

from __future__ import annotations

from collections.abc import Callable
import math
from pathlib import Path
import runpy
from typing import Any

import pytest

type State = tuple[float, ...]
type Evaluate = Callable[..., dict[str, Any]]

EXPERIMENTS = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
CORE = EXPERIMENTS / "0203-coepoch-arithmetic.py"
MU = 1.327124400420322e20


@pytest.fixture
def evaluate(monkeypatch: pytest.MonkeyPatch) -> Evaluate:
    module = runpy.run_path(str(CORE))
    fn = module["evaluate"]
    monkeypatch.setitem(fn.__globals__, "R2_SOURCE", EXPERIMENTS / "0128-reference-coast.py")
    return fn


def ellipse(e: float, anomaly: float, *, a: float = 1.4e11) -> tuple[float, State]:
    """Construct exact-phase test vectors in a fixed, generic tilted frame."""
    p, q = (0.6, 0.8, 0.0), (-0.48, 0.36, 0.8)
    ca, sa = math.cos(anomaly), math.sin(anomaly)
    minor = math.sqrt(1 - e**2)
    motion = math.sqrt(MU / a**3)
    epoch = 970_000_000.0 + (anomaly - e * sa) / motion
    radius = a * (1 - e * ca)
    speed_coefficient = math.sqrt(MU * a) / radius
    pos = tuple(a * ((ca - e) * px + minor * sa * qx) for px, qx in zip(p, q, strict=True))
    vel = tuple(speed_coefficient * (-sa * px + minor * ca * qx) for px, qx in zip(p, q, strict=True))
    return epoch, pos + vel


def no_op() -> None:
    pass


@pytest.mark.parametrize(("e", "phase"), [(0.2, -0.3), (0.65, 0.5), (0.33, 3.4)])
def test_known_tilted_orbit(evaluate: Evaluate, e: float, phase: float) -> None:
    departure, start = ellipse(e, phase - 0.2)
    checkpoint, expected = ellipse(e, phase)
    arrival, stop = ellipse(e, phase + 1.1)
    sun = (8e8, -3.7e8, 4e8, 17.0, -33.0, 2.0)
    delta = (3.0, -5.0, 7.0, -0.4, 0.8, -1.2)
    expected_ssb = tuple(a + b for a, b in zip(expected, sun, strict=True))
    outgoing = tuple(a - b for a, b in zip(expected_ssb, delta, strict=True))
    report = evaluate(checkpoint, departure, arrival, start, stop, sun, outgoing, no_op)
    assert report["epoch_binary64_hex"] == checkpoint.hex()
    assert report["analytic_evaluations"] == 2
    for direction in ("forward", "backward"):
        assert report[direction]["relative_si"][:3] == pytest.approx(expected[:3], abs=0.003, rel=0)
        assert report[direction]["relative_si"][3:] == pytest.approx(expected[3:], abs=1e-8, rel=0)
        assert report[direction]["ssb_si"][:3] == pytest.approx(expected_ssb[:3], abs=0.003, rel=0)
        assert report[direction]["ssb_si"][3:] == pytest.approx(expected_ssb[3:], abs=1e-8, rel=0)
        assert 1 <= report[direction]["root"]["updates"] <= 64
    assert report["model_difference"]["position_si"] == pytest.approx(delta[:3], abs=0.003, rel=0)
    assert report["model_difference"]["velocity_si"] == pytest.approx(delta[3:], abs=1e-8, rel=0)
    assert report["model_difference"]["position_norm_m"] == pytest.approx(math.hypot(*delta[:3]), abs=0.003)
    assert report["model_difference"]["velocity_norm_m_s"] == pytest.approx(math.hypot(*delta[3:]), abs=1e-8)
    assert report["ideal_mass_kg"] is None
    assert report["physical_status"] == "physical-join-not-established"
    assert report["continuity_residuals"] == {
        "epoch_s": None, "position_m": None, "velocity_m_s": None, "mass_kg": None,
    }


@pytest.mark.parametrize("control", ["early", "late", "equal-departure", "equal-arrival", "swapped", "nonfinite"])
def test_bad_epoch(evaluate: Evaluate, control: str) -> None:
    departure, start = ellipse(0.32, 0.2)
    checkpoint, state = ellipse(0.32, 0.5)
    arrival, stop = ellipse(0.32, 1.0)
    if control == "swapped":
        departure, arrival = arrival, departure
    checkpoint = {
        "early": departure - 1, "late": arrival + 1, "equal-departure": departure,
        "equal-arrival": arrival, "nonfinite": math.nan, "swapped": checkpoint,
    }[control]
    with pytest.raises((ValueError, RuntimeError), match="checkpoint|finite number"):
        evaluate(checkpoint, departure, arrival, start, stop, (0.0,) * 6, state, no_op)


@pytest.mark.parametrize("control", ["negated-arrival-velocity", "arrival-epoch-slip", "perturbed-velocity"])
def test_two_sided_gate_rejects_wrong_endpoint(evaluate: Evaluate, control: str) -> None:
    departure, start = ellipse(0.32, 0.2)
    checkpoint, state = ellipse(0.32, 0.5)
    arrival, stop = ellipse(0.32, 1.0)
    if control == "negated-arrival-velocity":
        stop = stop[:3] + tuple(-v for v in stop[3:])
    elif control == "arrival-epoch-slip":
        arrival += 0.1
    else:
        stop = (*stop[:4], stop[4] + 0.01, stop[5])
    with pytest.raises(ValueError, match="coepoch agreement"):
        evaluate(checkpoint, departure, arrival, start, stop, (0.0,) * 6, state, no_op)


def test_changed_frozen_source_stops_before_execution(
    evaluate: Evaluate, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "fake.py"
    source.write_text("raise AssertionError('untrusted source ran')\n")
    monkeypatch.setitem(evaluate.__globals__, "R2_SOURCE", source)
    with pytest.raises(ValueError, match="source digest"):
        evaluate(2.0, 1.0, 3.0, (0.0,) * 6, (0.0,) * 6, (0.0,) * 6, (0.0,) * 6, no_op)
