"""Use a synthetic data source for the 16-epoch holdout and all capture failures."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any

import pytest

from test_split_ephemeris_capture import Clock, FakeCaptureAdapter, synthetic_capture_bundle

EXPERIMENTS = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
sys.path[:0] = [str(EXPERIMENTS / "0173"), str(EXPERIMENTS / "0167")]

from ariadna_moon_holdout_capture import CAPTURE_CAPS, capture, validate_capture  # noqa: E402
from ariadna_split_common import Recorder  # noqa: E402

HI_TDB_S = [978995505.25 - i for i in range(16)]


def synthetic_holdout_bundle() -> dict[str, Any]:
    """Inject analytic states; use saved identity metadata without loading a kernel."""
    bundle = synthetic_capture_bundle()
    bundle["epochs"] = [
        {"hi_tdb_s": hi, "observation_ordinals": [i, i + 16] if i < 5 else [i],
         "reference_si": [str((2000 + i) * 1000), "1250", "0", "0", "-125", "1000"],
         "proxy_position_km": [2000.0 + i, 1.25, -0.0],
         "earth_ssb_km_km_s": [10000.0, 0.0, 3.0, 1.0, 0.0, -1.0],
         "moon_ssb_km_km_s": [12000.0 + i, 1.25, 3.0, 1.0, -0.125, 0.0]}
        for i, hi in enumerate(HI_TDB_S)
    ]
    return bundle


class FakeHoldoutAdapter(FakeCaptureAdapter):
    """Reuse the old synthetic inventory and return only geocentric states."""

    def __init__(self, bundle: dict[str, Any]) -> None:
        super().__init__(bundle)
        self.geocentric = [row["proxy_position_km"] + [0.0, -0.125, 1.0] for row in bundle["epochs"]]

    def spkezr(self, target: str, hi: float, frame: str, abcorr: str, observer: str) -> Any:
        assert (target, frame, abcorr, observer) == ("Moon", "J2000", "NONE", "Earth")
        assert self.calls[-1] == "spksfs"
        index = [row["hi_tdb_s"] for row in self.bundle["epochs"]].index(hi)
        return self._return("spkezr", (self.geocentric[index].copy(), 1.25))

    def spksfs(self, body: int, hi: float, idlen: int) -> Any:
        assert body == 301
        return super().spksfs(body, hi, idlen)


@pytest.fixture(scope="module")
def bundle() -> dict[str, Any]:
    return synthetic_holdout_bundle()


@pytest.fixture
def case(bundle: dict[str, Any]) -> tuple[dict[str, Any], Recorder, dict[str, str], FakeHoldoutAdapter, Clock]:
    clock = Clock()
    report: dict[str, Any] = {}
    recorder = Recorder(report, CAPTURE_CAPS, clock.now, 15.0, clock=clock)
    return report, recorder, {"preparation_sha256": "fixture-pin"}, FakeHoldoutAdapter(bundle), clock


def test_order_and_complete_offline_replay(bundle: dict[str, Any], case: tuple[Any, ...]) -> None:
    report, recorder, pin, adapter, _clock = case
    capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    assert report["capture_phase"] == "complete" and report["unavailable"] == []
    assert len(report["ledger"]) == 63
    assert [entry["operation"] for entry in report["ledger"]] == (
        ["setup"] + ["inventory"] * 15 + ["selector", "state"] * 16 + ["inventory"] * 15
    )
    expected_args = [args for hi in HI_TDB_S for args in ([301, hi, 128], ["Moon", hi, "J2000", "NONE", "Earth"])]
    assert [entry["args"] for entry in report["ledger"][16:48]] == expected_args
    states = validate_capture(bundle, report, pin)
    assert states == adapter.geocentric
    assert states[0][2].hex() == "-0x0.0p+0"
    assert report["ledger"][17]["raw"][1] == 1.25


@pytest.mark.parametrize(("api", "ordinal", "bad", "reason", "retained"), [
    ("ktotal", 1, True, "thirteen-kernel", 2),
    ("spksfs", 1, (0, [0.0] * 5, "Moon", False), "not found", 17),
    ("spksfs", 1, (0, [0.0] * 5, "Earth"), "handle or label", 17),
    ("spkezr", 1, ([0.0] * 6, True), "binary64", 18),
    ("spkezr", 2, ([0.0] * 5 + [float("nan")], 1.25), "binary64", 20),
    ("ktotal", 2, 14, "thirteen-kernel", 49),
])
def test_malformed_return_stops_before_next_call(
    bundle: dict[str, Any], case: tuple[Any, ...], api: str, ordinal: int, bad: Any,
    reason: str, retained: int,
) -> None:
    report, recorder, pin, adapter, _clock = case
    adapter.mutations[api, ordinal] = lambda _: bad
    with pytest.raises(ValueError, match=reason):
        capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    assert len(report["ledger"]) == retained
    last = report["ledger"][-1]
    assert last["api"] == api and "raw" in last and "returned_s" in last and "completed_s" not in last
    assert json.dumps(last, allow_nan=False)
    completed = report["counts"]["state"]["completed"]
    assert report["unavailable"] == list(range(completed, 16))


@pytest.mark.parametrize("phase", [1, 2])
def test_runtime_identity_drift_is_preserved(
    bundle: dict[str, Any], case: tuple[Any, ...], phase: int,
) -> None:
    report, recorder, pin, adapter, _clock = case

    def bad_runtime(snapshot: dict[str, Any]) -> dict[str, Any]:
        snapshot["files"]["cspice"]["sha256"] = "changed library"
        return snapshot

    adapter.mutations["identity", phase] = bad_runtime
    with pytest.raises(ValueError, match="runtime/library/build"):
        capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    assert report["counts"]["state"]["completed"] == (0 if phase == 1 else 16)
    assert report["capture_phase"] == ("before_identity" if phase == 1 else "after_identity")
    with pytest.raises(ValueError, match="incomplete"):
        validate_capture(bundle, report, pin)


def test_incomplete_state_retains_late_return(bundle: dict[str, Any], case: tuple[Any, ...]) -> None:
    report, recorder, pin, adapter, clock = case

    def late(raw: Any) -> Any:
        clock.now += 15.01
        return raw

    adapter.mutations["spkezr", 2] = late
    with pytest.raises(ValueError, match="deadline"):
        capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    last = report["ledger"][-1]
    assert last["raw"][0] == adapter.geocentric[1]
    assert last["returned_s"] == pytest.approx(15.01)
    assert "completed_s" not in last and report["unavailable"] == list(range(1, 16))


@pytest.mark.parametrize(("entry", "key", "value", "reason"), [
    (16, "args", [399, HI_TDB_S[0], 128], "ordered call/args"),
    (17, "args", ["Moon", HI_TDB_S[1], "J2000", "NONE", "Earth"], "ordered call/args"),
    (17, "args", ["Moon", HI_TDB_S[0], "J2000", "NONE", "SSB"], "ordered call/args"),
    (17, "returned_s", -0.01, "ordered ledger/deadline"),
    (62, "completed_s", 15.01, "ordered ledger/deadline"),
    (17, "raw", [[0.0] * 6, False], "binary64"),
])
def test_replay_rejects_mutated_native_event(
    bundle: dict[str, Any], case: tuple[Any, ...], entry: int, key: str, value: Any, reason: str,
) -> None:
    report, recorder, pin, adapter, _clock = case
    capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    report["ledger"][entry][key] = value
    with pytest.raises(ValueError, match=reason):
        validate_capture(bundle, report, pin)


@pytest.mark.parametrize(("hi", "reason"), [
    (HI_TDB_S[1], "duplicate"), (979084800.0, "record coverage"), (978995505, "binary64"),
])
def test_bad_coepoch_cannot_reach_adapter(
    bundle: dict[str, Any], case: tuple[Any, ...], hi: float, reason: str,
) -> None:
    report, recorder, pin, adapter, _clock = case
    changed = dict(bundle, epochs=deepcopy(bundle["epochs"]))
    changed["epochs"][0]["hi_tdb_s"] = hi
    with pytest.raises(ValueError, match=reason):
        capture(changed, report, recorder, adapter=adapter, identity_pin=pin)
    assert not adapter.calls and not report["ledger"]


def test_replay_requires_frozen_identity_and_counts(bundle: dict[str, Any], case: tuple[Any, ...]) -> None:
    report, recorder, pin, adapter, _clock = case
    capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    with pytest.raises(ValueError, match="tested helper/input identity"):
        validate_capture(bundle, report, {})
    report["counts"]["state"]["completed"] -= 1
    with pytest.raises(ValueError, match="exact counts"):
        validate_capture(bundle, report, pin)


def test_oversized_epoch_schedule_cannot_reach_setup(bundle: dict[str, Any], case: tuple[Any, ...]) -> None:
    report, recorder, pin, adapter, _clock = case
    changed = dict(bundle, epochs=[*bundle["epochs"], {"hi_tdb_s": 978995550.25}])
    with pytest.raises(ValueError, match="fixed 16 holdout epochs"):
        capture(changed, report, recorder, adapter=adapter, identity_pin=pin)
    assert not adapter.calls and not report["ledger"]


def test_changed_native_handle_invalidates_final_snapshot(bundle: dict[str, Any], case: tuple[Any, ...]) -> None:
    report, recorder, pin, adapter, _clock = case
    selected = next(i for i, row in enumerate(adapter.kernels) if row[0] == bundle["records"][0]["path"])
    adapter.mutations["kdata", 14 + selected] = lambda row: (*row[:3], row[3] + 1000)
    with pytest.raises(ValueError, match="before/after raw inventory"):
        capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    assert report["counts"]["state"]["completed"] == 16
    assert report["capture_phase"] == "after_inventory"
    with pytest.raises(ValueError, match="incomplete"):
        validate_capture(bundle, report, pin)
