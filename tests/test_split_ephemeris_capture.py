"""Exercise ADR0166 capture with injected returns, without initializing SPICE."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import gzip
import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "docs/adr/experiments"


def synthetic_capture_bundle() -> dict[str, Any]:
    """Use saved identity/coverage metadata, with injected states for every capture."""
    bundle = json.loads((EXPERIMENTS / "0166-inputs.json").read_bytes())
    study = json.loads(gzip.decompress((EXPERIMENTS / "0164-corrected-study.json.gz").read_bytes()))
    bundle["historical_identity"] = study["identities"]["before"]
    return bundle


class FakeCaptureAdapter:
    """Test data source with no native imports or ephemeris evaluation."""

    def __init__(self, bundle: dict[str, Any],
                 states: list[dict[str, list[float]]] | None = None) -> None:
        self.bundle = bundle
        self.states = states if states is not None else [
            {"E": [10000.0, -0.0, float(i), 1.0, 0.0, -1.0],
             "G": [2000.0, 1.0, 2.0, 0.0, -2.0, 0.0],
             "B": [12000.0, 1.0, float(i + 2), 1.0, -2.0, -1.0]}
            for i in range(3)
        ]
        self.calls: list[str] = []
        self.mutations: dict[tuple[str, int], Callable[[Any], Any]] = {}
        parent = Path(bundle["records"][0]["path"]).parent
        self.paths = {
            str(parent / row["name"]): row
            for row in bundle["original_ordered_pool_manifest"]["kernels"]
        }
        self.kernels = [
            (path, row["type"], row["source"] or "", i + 1 if row["type"] == "SPK" else 0)
            for i, (path, row) in enumerate(self.paths.items())
        ]

    def _return(self, api: str, raw: Any) -> Any:
        self.calls.append(api)
        mutation = self.mutations.get((api, self.calls.count(api)))
        return mutation(raw) if mutation is not None else raw

    def identity(self, bundle: dict[str, Any], check: Callable[[], None]) -> dict[str, Any]:
        from ariadna_split_capture import _runtime_pin

        check()
        return self._return("identity", deepcopy(_runtime_pin(bundle)))

    def load_standard_kernels(self) -> Any:
        return self._return("load_standard_kernels", None)

    def ktotal(self, kind: str) -> Any:
        assert kind == "ALL"
        return self._return("ktotal", 13)

    def kdata(self, index: int, kind: str) -> Any:
        assert kind == "ALL"
        return self._return("kdata", self.kernels[index])

    def get_total_count_of_kernels_loaded(self) -> Any:
        return self._return("get_total_count_of_kernels_loaded", 13)

    def kernel_metadata(self, path: str, kind: str, source: str,
                        check: Callable[[], None]) -> dict[str, Any]:
        check()
        return self._return("kernel_metadata", {"path": path, "metadata": deepcopy(self.paths[path])})

    def spkezr(self, target: str, hi: float, frame: str, abcorr: str, observer: str) -> Any:
        assert (frame, abcorr) == ("J2000", "NONE")
        index = [row["hi_tdb_s"] for row in self.bundle["samples_in_probe_order"]].index(hi)
        key = {("Earth", "SSB"): "E", ("Moon", "Earth"): "G", ("Moon", "SSB"): "B"}[target, observer]
        return self._return("spkezr", (self.states[index][key].copy(), 1.25))

    def spksfs(self, body: int, hi: float, idlen: int) -> Any:
        assert idlen == 128
        record = next(row for row in self.bundle["records"] if row["body"] == body)
        assert record["record_interval_tdb_s"][0] <= hi < record["record_interval_tdb_s"][1]
        handle = next(row[3] for row in self.kernels if row[0] == record["path"])
        return self._return("spksfs", (handle, [float.fromhex(h) for h in record["descriptor_hex"]],
                                        record["label"]))


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture(scope="module")
def bundle() -> dict[str, Any]:
    return synthetic_capture_bundle()


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any]:
    monkeypatch.syspath_prepend(str(EXPERIMENTS / "0167"))
    import ariadna_split_capture
    import ariadna_split_common

    return ariadna_split_capture, ariadna_split_common


@pytest.fixture
def setup_capture(modules: tuple[Any, Any], bundle: dict[str, Any]) -> tuple[Any, ...]:
    capture, common = modules
    clock = Clock()
    report: dict[str, Any] = {}
    recorder = common.Recorder(report, common.CAPTURE_CAPS, clock.now, 15.0, clock=clock)
    pin = {"helpers": {"capture": "fixture-hash"}, "input_sha256": "fixture-input"}
    adapter = FakeCaptureAdapter(bundle)
    return capture, clock, report, recorder, pin, adapter


def test_exact_sample_order_and_capture_replay(setup_capture: tuple[Any, ...],
                                              bundle: dict[str, Any]) -> None:
    capture, _clock, report, recorder, pin, adapter = setup_capture
    capture.capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    assert capture.validate_capture(bundle, report, pin) == adapter.states
    assert report["capture_phase"] == "complete"
    assert len(report["ledger"]) == 46
    assert report["counts"] == {
        "setup": dict.fromkeys(("attempted", "returned", "completed"), 1),
        "inventory": dict.fromkeys(("attempted", "returned", "completed"), 30),
        "state": dict.fromkeys(("attempted", "returned", "completed"), 9),
        "selector": dict.fromkeys(("attempted", "returned", "completed"), 6),
    }
    assert [entry["operation"] for entry in report["ledger"]] == (
        ["setup"] + ["inventory"] * 15 + ["state"] * 9 + ["selector"] * 6 + ["inventory"] * 15
    )
    expected_hi = [978995455.4804223, 978995455.2304223, 978995705.2304223]
    assert [entry["args"] for entry in report["ledger"][16:25]] == [
        [target, hi, "J2000", "NONE", observer] for hi in expected_hi
        for target, observer in (("Earth", "SSB"), ("Moon", "Earth"), ("Moon", "SSB"))
    ]
    assert [entry["args"] for entry in report["ledger"][25:31]] == [
        [body, hi, 128] for hi in expected_hi for body in (399, 301)
    ]
    assert report["ledger"][16]["raw"][1] == 1.25
    assert report["ledger"][16]["raw"][0][1].hex() == "-0x0.0p+0"


@pytest.mark.parametrize(("api", "ordinal", "bad", "reason", "attempts"), (
    ("ktotal", 1, 12, "thirteen-kernel", 2),
    ("ktotal", 1, 14, "thirteen-kernel", 2),
    ("ktotal", 1, True, "thirteen-kernel", 2),
    ("kdata", 1, ("/somewhere", "TEXT", "", 0, False), "not found", 3),
    ("kdata", 1, ("/somewhere", "TEXT", "", True), "raw identity", 3),
    ("get_total_count_of_kernels_loaded", 1, 12, "thirteen-kernel", 16),
    ("spkezr", 1, ([0.0] * 5, 1.25), "six components", 17),
    ("spkezr", 2, ([0.0] * 6, True), "binary64", 18),
    ("spkezr", 3, ([0.0] * 5 + [float("nan")], 1.25), "binary64", 19),
    ("spksfs", 1, (0, [0.0] * 5, "Earth"), "handle or label", 26),
    ("spksfs", 6, (8, [0.0] * 5, "Moon", False), "not found", 31),
    ("ktotal", 2, 14, "thirteen-kernel", 32),
))
def test_retains_invalid_raw_before_failing(setup_capture: tuple[Any, ...], bundle: dict[str, Any],
                                            api: str, ordinal: int, bad: Any, reason: str,
                                            attempts: int) -> None:
    capture, _clock, report, recorder, pin, adapter = setup_capture
    adapter.mutations[api, ordinal] = lambda _: bad
    with pytest.raises(ValueError, match=reason):
        capture.capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    assert len(report["ledger"]) == attempts
    last = report["ledger"][-1]
    assert last["api"] == api and "raw" in last and "returned_s" in last
    assert "completed_s" not in last
    assert json.dumps(last, allow_nan=False)


@pytest.mark.parametrize("phase", (1, 2))
def test_detects_native_library_change_before_or_after_states(
    setup_capture: tuple[Any, ...], bundle: dict[str, Any], phase: int
) -> None:
    capture, _clock, report, recorder, pin, adapter = setup_capture

    def change(raw: dict[str, Any]) -> dict[str, Any]:
        raw["files"]["cspice"]["sha256"] = "wrong digest"
        return raw

    adapter.mutations["identity", phase] = change
    with pytest.raises(ValueError, match="runtime/library/build"):
        capture.capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    assert len(report["ledger"]) == (0 if phase == 1 else 31)
    assert report["identities"]["before" if phase == 1 else "after"]["runtime"]["files"][
        "cspice"
    ]["sha256"] == "wrong digest"


def test_rejects_wrong_kernel_digest_before_state_calls(setup_capture: tuple[Any, ...],
                                                       bundle: dict[str, Any]) -> None:
    capture, _clock, report, recorder, pin, adapter = setup_capture

    def change(raw: dict[str, Any]) -> dict[str, Any]:
        raw["metadata"]["sha256"] = "changed kernel"
        return raw

    adapter.mutations["kernel_metadata", 8] = change
    with pytest.raises(ValueError, match="inventory digest"):
        capture.capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    assert report["identities"]["before"]["kernels"][-1]["metadata"]["sha256"] == "changed kernel"
    assert report["counts"]["state"]["attempted"] == 0


def test_retains_a_late_state_and_stops(setup_capture: tuple[Any, ...], bundle: dict[str, Any]) -> None:
    capture, clock, report, recorder, pin, adapter = setup_capture

    def late(raw: Any) -> Any:
        clock.now += 15.01
        return raw

    adapter.mutations["spkezr", 1] = late
    with pytest.raises(ValueError, match="deadline"):
        capture.capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    assert len(report["ledger"]) == 17
    assert report["ledger"][-1]["raw"][0] == adapter.states[0]["E"]
    assert report["ledger"][-1]["returned_s"] == pytest.approx(15.01)
    assert "completed_s" not in report["ledger"][-1]


def test_retains_attempt_on_adapter_exception(setup_capture: tuple[Any, ...],
                                             bundle: dict[str, Any]) -> None:
    capture, _clock, report, recorder, pin, adapter = setup_capture

    def reject(_raw: Any) -> Any:
        raise ValueError("injected return error")

    adapter.mutations["spkezr", 1] = reject
    with pytest.raises(ValueError, match="injected"):
        capture.capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    assert len(report["ledger"]) == 17
    assert set(report["ledger"][-1]) == {"operation", "api", "args", "attempted_s"}


@pytest.mark.parametrize(("entry", "key", "value", "reason"), (
    (16, "args", ["Earth", 978995455.2304223, "J2000", "NONE", "SSB"], "ordered call/args"),
    (17, "args", ["Earth", 978995455.4804223, "J2000", "NONE", "Moon"], "ordered call/args"),
    (18, "args", ["Moon", 978995455.4804223, "J2000", "LT", "SSB"], "ordered call/args"),
    (25, "args", [301, 978995455.4804223, 128], "ordered call/args"),
    (25, "args", [399, 978995455.4804223, 64], "ordered call/args"),
    (16, "returned_s", -0.01, "ordered ledger/deadline"),
    (45, "completed_s", 15.01, "ordered ledger/deadline"),
    (17, "raw", [[0.0] * 6, False], "binary64"),
    (25, "raw", [8, [0.0] * 5, "Earth"], "descriptor bytes"),
    (26, "raw", [8, [0.0] * 5, "Earth"], "handle or label"),
    (32, "raw", ["/tmp/pck00010.tpc", "TEXT", "", 0], "inventory path/type"),
))
def test_offline_replay_rejects_mutated_raw_capture(setup_capture: tuple[Any, ...],
                                                   bundle: dict[str, Any], entry: int, key: str,
                                                   value: Any, reason: str) -> None:
    capture, _clock, report, recorder, pin, adapter = setup_capture
    capture.capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    report["ledger"][entry][key] = value
    with pytest.raises(ValueError, match=reason):
        capture.validate_capture(bundle, report, pin)


def test_offline_detects_forged_counts_and_pins(setup_capture: tuple[Any, ...],
                                               bundle: dict[str, Any]) -> None:
    capture, _clock, report, recorder, pin, adapter = setup_capture
    capture.capture(bundle, report, recorder, adapter=adapter, identity_pin=pin)
    wrong_pin = dict(pin, input_sha256="changed")
    with pytest.raises(ValueError, match="tested helper/input identity"):
        capture.validate_capture(bundle, report, wrong_pin)
    report["counts"]["selector"]["completed"] -= 1
    with pytest.raises(ValueError, match="exact counts"):
        capture.validate_capture(bundle, report, pin)


@pytest.mark.parametrize(("key", "value"), (
    ("lo_hex", "-0x0.0p+0"), ("hi_tdb_s", 978995455.2304223), ("source_index", 0),
))
def test_blocks_wrong_sample_before_loading(setup_capture: tuple[Any, ...], bundle: dict[str, Any],
                                            key: str, value: Any) -> None:
    capture, _clock, report, recorder, pin, adapter = setup_capture
    changed = dict(bundle, samples_in_probe_order=deepcopy(bundle["samples_in_probe_order"]))
    changed["samples_in_probe_order"][0][key] = value
    with pytest.raises(ValueError, match="sample"):
        capture.capture(changed, report, recorder, adapter=adapter, identity_pin=pin)
    assert not adapter.calls and not report["ledger"]


def test_independently_decodes_segment_center_and_record_bounds(modules: tuple[Any, Any],
                                                                bundle: dict[str, Any]) -> None:
    from struct import pack, unpack

    capture, _common = modules
    record = deepcopy(bundle["records"][1])
    descriptor = [float.fromhex(h) for h in record["descriptor_hex"]]
    # Keep the forged descriptor's hex consistent so the independent decode must reject it.
    descriptor[2] = unpack("<d", pack("<2i", 399, 301))[0]
    record["descriptor_hex"] = [value.hex() for value in descriptor]
    with pytest.raises(ValueError, match="decoded centre"):
        capture._selector([8, descriptor, "Earth"], 8, 978995455.4804223, record)
    record = deepcopy(bundle["records"][1])
    descriptor = [float.fromhex(h) for h in record["descriptor_hex"]]
    with pytest.raises(ValueError, match="record coverage"):
        capture._selector([8, descriptor, "Earth"], 8, 979084800.0, record)
