"""Exercise independent outward arithmetic using artificial lunar-relative states."""

from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

EXPERIMENTS = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
STUDY = run_path(str(EXPERIMENTS / "0189-post-cutoff-direction.py"))["compute"]
AUDIT = run_path(str(EXPERIMENTS / "0189-post-cutoff-direction-audit.py"))["verify"]
PROFILES = ("native_normal", "native_tighter", "dop853_normal", "dop853_tighter")
MU = 4e12
SURFACE = 1737400.0
type Row = dict[str, Any]


def observations(step: float = 25.0, radial: float = 0.5) -> list[Row]:
    rows = []
    for profile in PROFILES:
        for j in range(13):
            moon = [1e11 + 100*j, -1e11, 5e10, 2e4, -3e4, 0.0]
            rows.append({"profile": profile, "index": j, "epoch_tdb_s": 1e9 + 50*j,
                         "moon": moon,
                         "spacecraft": [moon[0] + 2e6 + step*j, *moon[1:3],
                                        moon[3] + radial, moon[4] + 2.0, moon[5]]})
    return rows


@pytest.mark.parametrize(("step", "speed", "radial_sign", "net_sign"), [
    (25.0, 0.5, 1, 1),
    (0.0, 0.0, 0, 0),
    (-25.0, -0.5, -1, -1),
    (-25.0, 0.5, 1, -1),
    (0.0, 0.5, 1, 0),
    (25.0, 0.0, 0, 1),
])
def test_outbound_classification_is_separate(
    step: float, speed: float, radial_sign: int, net_sign: int,
) -> None:
    rows = observations(step, speed)
    recorded = STUDY(rows, MU, SURFACE)
    result = AUDIT(rows, MU, SURFACE, recorded)
    assert len(result["rows"]) == 52
    assert result["classification"] == (
        "outbound-at-samples" if (radial_sign, net_sign) == (1, 1) else "outbound-not-established"
    )
    for row in result["rows"]:
        range_m = 2e6 + row["index"]*step
        assert row["radius_m"] == range_m
        assert row["radial_speed_m_s"] == speed
        assert row["radial_sign"] == radial_sign
        assert row["specific_energy_m2_s2"] == pytest.approx((speed**2 + 4.0)/2 - MU/range_m)
        # Positive outward motion is possible even at negative two-body energy.
        assert row["specific_energy_m2_s2"] < 0
    assert len(result["net_ranges"]) == 4
    for r in result["net_ranges"]:
        assert r["net_range_sign"] == net_sign
        assert r["net_range_change_m"] == step*12


def test_exact_sign_survives_binary64_relative_subtraction_cancellation() -> None:
    raw = observations()
    # x position difference rounds to +2097152; the exact difference is a
    # hair smaller. y contributes the exact opposite to the rounded dot.
    for offset in range(0, 52, 13):
        row = raw[offset]
        row["moon"] = [2.0**-35, 0.0, 0.0, 0.0, 0.0, 0.0]
        row["spacecraft"] = [2.0**21, 2.0**21, 0.0, 1.0, -1.0, 0.0]
    recorded = STUDY(raw, MU, SURFACE)
    assert recorded["rows"][0]["radial_speed_m_s"] == 0.0
    audited = AUDIT(raw, MU, SURFACE, recorded)
    assert audited["rows"][0]["radial_speed_m_s"] < 0.0
    assert audited["rows"][0]["radial_sign"] == -1
    assert audited["classification"] == "outbound-not-established"


@pytest.mark.parametrize(("target", "key", "value", "reason"), [
    ("row", "radial_sign", True, "radial sign"),
    ("row", "radial_speed_m_s", 0.500000002, "radial_speed"),
    ("row", "radius_m", 2000000.000002, "radius"),
    ("row", "specific_energy_m2_s2", float("nan"), "nonfinite"),
    ("row", "epoch_tdb_s", 1e9+50., "wrong coepoch"),
    ("row", "index", True, "wrong profile or node"),
    ("net", "net_range_change_m", 300.000002, "net range change"),
    ("net", "net_range_sign", 0, "net range sign"),
    ("payload", "classification", "outbound-not-established", "classification"),
])
def test_audit_rejects_corrupted_saved_fields(target: str, key: str, value: Any, reason: str) -> None:
    raw = observations()
    claimed = STUDY(raw, MU, SURFACE)
    record = {"row": claimed["rows"][0], "net": claimed["net_ranges"][0], "payload": claimed}[target]
    record[key] = value
    with pytest.raises(ValueError, match=reason):
        AUDIT(raw, MU, SURFACE, claimed)


def test_raw_identity_is_bitwise_and_compares_with_saved_ephemeris_node() -> None:
    raw = observations()
    claimed = STUDY(raw, MU, SURFACE)
    claimed["rows"][0]["moon"][-1] = -0.0
    with pytest.raises(ValueError, match="raw state identity mismatch"):
        AUDIT(raw, MU, SURFACE, claimed)
    raw[13]["moon"][0] += math.ulp(raw[13]["moon"][0])
    with pytest.raises(ValueError, match="same Moon state"):
        STUDY(raw, MU, SURFACE)
    claimed["rows"][0]["moon"][-1] = 0.0
    claimed["rows"][13]["moon"][0] = raw[13]["moon"][0]
    with pytest.raises(ValueError, match="noncommon Moon"):
        AUDIT(raw, MU, SURFACE, claimed)


def test_study_rejects_invalid_coverage_surface_and_epochs() -> None:
    raw = observations()
    for bad, msg in [(raw[:-1], "52 rows"), ([raw[0]]*52, "profile or node")]:
        with pytest.raises(ValueError, match=msg):
            STUDY(bad, MU, SURFACE)
    with pytest.raises(ValueError, match="exterior guard"):
        STUDY(raw, MU, 2e6)
    original = deepcopy(raw)
    raw[3]["epoch_tdb_s"] = raw[2]["epoch_tdb_s"]
    with pytest.raises(ValueError, match="non-coepoch"):
        STUDY(raw, MU, SURFACE)
    raw = original
    raw[0]["spacecraft"][0] = True
    with pytest.raises(ValueError, match="invalid binary64"):
        STUDY(raw, MU, SURFACE)


def test_direction_budget_checks_bound_work() -> None:
    raw = observations()
    saved = STUDY(raw, MU, SURFACE)
    for func, args in ((STUDY, (raw, MU, SURFACE)), (AUDIT, (raw, MU, SURFACE, saved))):
        clock = iter([False, False, True])

        def deadline() -> None:
            if next(clock):
                raise ValueError("budget expired")

        with pytest.raises(ValueError, match="budget expired"):
            func(*args, check=deadline)
