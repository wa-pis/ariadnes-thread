"""Exercise R5.20 evidence handling without loading any scientific adapter."""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
import io
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

HELPERS = Path(__file__).resolve().parents[1] / "docs/adr/experiments/0167"


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any]:
    monkeypatch.syspath_prepend(str(HELPERS))
    import ariadna_split_common
    import ariadna_split_run

    return ariadna_split_common, ariadna_split_run


def test_call_limits_count_failed_attempts(modules: tuple[Any, Any]) -> None:
    common, _ = modules
    report: dict[str, Any] = {}
    journal = io.StringIO()
    recorder = common.Recorder(report, {"state": 1}, 0., 15., clock=lambda: 0., journal=journal)

    def fail() -> None:
        raise ValueError("fake provider")

    with pytest.raises(ValueError, match="fake provider"):
        recorder.call("state", "spkezr", [], fail)
    with pytest.raises(ValueError, match="cap"):
        recorder.call("state", "spkezr", [], lambda: pytest.fail("second call"))
    assert report["counts"]["state"] == {"attempted": 1, "returned": 0, "completed": 0}
    assert len(journal.getvalue().splitlines()) == 1


def test_late_raw_and_invalid_numbers_retained_first(modules: tuple[Any, Any]) -> None:
    common, _ = modules
    report: dict[str, Any] = {}
    stamp = 1.
    journal = io.StringIO()
    recorder = common.Recorder(report, {"state": 1}, 0., 15., clock=lambda: stamp, journal=journal)

    def late() -> list[float]:
        nonlocal stamp
        stamp = 15.0001
        return [-0., float("nan")]

    with pytest.raises(ValueError, match="deadline"):
        recorder.call("state", "spkezr", ["fake"], late, lambda raw: pytest.fail("late validation"))
    assert report["counts"]["state"] == {"attempted": 1, "returned": 1, "completed": 0}
    raw = common.parse_json(journal.getvalue().splitlines()[-1].encode())["entry"]["raw"]
    assert raw[0].hex() == "-0x0.0p+0" and raw[1] == {"invalid_numeric": "nan"}


@pytest.mark.parametrize("malformed", [b'{"a":1,"a":2}', b'{"a":1e999}', b'{"a":NaN}', b"[]"])
def test_reject_malformed_json(modules: tuple[Any, Any], malformed: bytes) -> None:
    common, _ = modules
    with pytest.raises(ValueError):
        common.parse_json(malformed)


def test_analysis_cannot_run_without_complete_capture(
    modules: tuple[Any, Any], tmp_path: Path,
) -> None:
    common, run = modules
    assert not run.run_phase(tmp_path, "analysis", 0., execution="synthetic",
                             pin_loader=lambda _: {}, input_loader=lambda _: {},
                             clock=lambda: 0., boot_s=0.)
    report, receipt = run.read_phase(tmp_path, "analysis", "synthetic")
    assert receipt["finalization"] == "passed"
    assert report["error"]["stage"] == "capture verification"
    assert report["unavailable"] == ["state parity", "position closure", "static force"]
    assert report["ledger"] == []
    saved = common.digest(run.paths(tmp_path, "analysis")["report"])
    with pytest.raises(ValueError, match="existing phase evidence"):
        run.run_phase(tmp_path, "analysis", 0., execution="synthetic",
                      pin_loader=lambda _: {}, input_loader=lambda _: {}, clock=lambda: 0., boot_s=0.)
    assert common.digest(run.paths(tmp_path, "analysis")["report"]) == saved


def test_late_child_receipt_cannot_qualify_report(
    modules: tuple[Any, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    common, run = modules
    stamp = 0.
    original = run.store

    def store(stream: Any, data: dict[str, Any]) -> None:
        nonlocal stamp
        original(stream, data)
        if stream.name.endswith("receipt.json"):
            stamp = 10.0001

    monkeypatch.setattr(run, "store", store)
    assert not run.run_phase(tmp_path, "analysis", 0., execution="synthetic",
                             pin_loader=lambda _: {}, input_loader=lambda _: {},
                             clock=lambda: stamp, boot_s=0.)
    files = run.paths(tmp_path, "analysis")
    report = common.parse_json(files["report"].read_bytes())
    receipt = common.parse_json(files["receipt"].read_bytes())
    assert report["error"]["stage"] == "capture verification"
    assert receipt["finalization"] == "failed"
    assert "deadline" in receipt["finalization_error"]
    with pytest.raises(ValueError, match="finalization"):
        run.read_phase(tmp_path, "analysis", "synthetic")


@pytest.mark.parametrize("phase,flags,budget", [
    ("capture", ["-I", "-B"], 20.),
    ("analysis", ["-I", "-S", "-B"], 15.),
])
def test_watchdog_retains_attempt_and_refuses_retry(
    modules: tuple[Any, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    phase: str, flags: list[str], budget: float,
) -> None:
    common, run = modules
    manifest_sha = "1" * 64

    def timed_out(command: list[str], **kwargs: Any) -> None:
        assert command[1:1 + len(flags)] == flags
        assert kwargs["timeout"] == budget
        assert command[-3:-1] == [phase, manifest_sha]
        raise subprocess.TimeoutExpired(command, budget)

    if phase == "analysis":
        run.paths(tmp_path, "capture")["parent"].write_text("{}")
    monkeypatch.setattr(run.subprocess, "run", timed_out)
    assert not run.supervise(tmp_path, phase, manifest_sha)
    files = run.paths(tmp_path, phase)
    receipt = common.parse_json(files["parent"].read_bytes())
    assert receipt["finalization"] == "failed" and receipt["returncode"] is None
    assert receipt["error"]["type"] == "TimeoutExpired"
    assert common.parse_json(files["attempt"].read_bytes())["preparation_sha256"] == manifest_sha
    with pytest.raises(ValueError, match="existing phase evidence"):
        run.supervise(tmp_path, phase, manifest_sha)


def test_late_parent_receipt_fails_even_with_successful_child(
    modules: tuple[Any, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    common, run = modules
    stamp = 0.
    original = run.store

    def store(stream: Any, data: dict[str, Any]) -> None:
        nonlocal stamp
        original(stream, data)
        if stream.name.endswith("parent-receipt.json"):
            stamp = 15.001

    pin = {"preparation_sha256": "2" * 64}
    monkeypatch.setattr(run, "store", store)
    monkeypatch.setattr(run, "monotonic", lambda: stamp)
    monkeypatch.setattr(run, "read_phase", lambda *a: ({"external_start_s": 0., "status": "passed"}, {}))

    def child(*args: Any, **kwargs: Any) -> Any:
        run.paths(tmp_path, "capture")["receipt"].write_text("{}")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(run.subprocess, "run", child)
    assert not run.supervise(tmp_path, "capture", pin["preparation_sha256"])
    parent = common.parse_json(run.paths(tmp_path, "capture")["parent"].read_bytes())
    assert parent["finalization"] == "failed"
    assert parent["external_elapsed_s"] == 15.001 and parent["returncode"] == 0


def test_import_is_stdlib_only_in_fresh_process() -> None:
    code = """import sys
sys.path.insert(0, sys.argv[1])
import ariadna_split_run, ariadna_split_analysis, ariadna_split_capture, ariadna_split_inputs
assert not {'spiceypy','tudatpy','numpy','scipy','space_nav'} & set(sys.modules)
"""
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code, str(HELPERS)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_saved_capture_to_independent_static_analysis(
    modules: tuple[Any, Any], tmp_path: Path,
) -> None:
    from test_split_ephemeris_capture import FakeCaptureAdapter, synthetic_capture_bundle

    common, run = modules
    bundle = synthetic_capture_bundle()
    earth = [100_000_000., -40_000_000., 20_000_000., 1., 2., 3.]
    geocentric = [300_000., 10., -2., 4., -1., 0.]
    moon = [e + g for e, g in zip(earth, geocentric, strict=True)]
    states = [dict(E=earth, G=geocentric, B=moon) for _ in range(3)]
    moon_m = [1000. * x for x in moon[:3]]
    separation_m = 2_000_000
    position_m = [moon_m[0] - separation_m, *moon_m[1:]]
    velocity_m_s = [32., -16., 8.]
    bundle["frozen_initial"].update(position_m=position_m, velocity_m_s=velocity_m_s)
    reference: dict[str, Any] = {
        "earth_state_si": [Fraction(x) * 1000 for x in earth],
        "moon_state_si": [Fraction(x) * 1000 for x in moon],
        "d0_m": list(map(Fraction, (separation_m, 0, 0))),
        "saved_moon_m": moon_m,
        "saved_moon_source_residual_m": [Fraction(0)] * 3,
        "a0": {},
        "a0_norm": {},
    }
    for digits in (80, 100):
        with localcontext() as ctx:
            ctx.prec = digits
            force = Decimal.from_float(bundle["moon_gm_m3_s2"]) / separation_m**2
        reference["a0"][digits] = [force, Decimal(0), Decimal(0)]
        reference["a0_norm"][digits] = force
    bundle["references"] = [reference] * 3
    for sample in bundle["samples_in_probe_order"]:
        drift = [v * sample["elapsed_s"] for v in velocity_m_s]
        sample.update(frozen_drift_m=drift, frozen_q_m=[-x for x in drift],
                      raw_hex={"Earth": [x.hex() for x in earth], "Moon": [x.hex() for x in moon]})

    kwargs = {"execution": "synthetic", "input_loader": lambda _: bundle,
              "pin_loader": lambda _: {"fixture": "axis-aligned analytic"},
              "clock": lambda: 0., "boot_s": 0.}
    assert run.run_phase(tmp_path, "capture", 0., **kwargs,
                         adapter_factory=lambda: FakeCaptureAdapter(bundle, states))
    capture, _ = run.read_phase(tmp_path, "capture", "synthetic")
    assert len(capture["ledger"]) == 46
    assert run.run_phase(tmp_path, "analysis", 0., **kwargs)
    analysis, receipt = run.read_phase(tmp_path, "analysis", "synthetic")
    assert receipt["finalization"] == "passed"
    assert analysis["position_closure_passed"] is True
    assert analysis["static_force_passed"] is True
    assert analysis["production_or_mission_verified"] is False
    assert len(analysis["ledger"]) == 21
    assert analysis["capture_receipt_sha256"] == common.digest(run.paths(tmp_path, "capture")["receipt"])

    # A self-consistent hash and journal do not excuse impossible timestamps.
    files = run.paths(tmp_path, "capture")
    capture["ledger"][-1]["completed_s"] = 1.
    files["report"].write_bytes(common.encode(capture))
    files["journal"].write_bytes(b"".join(
        common.encode(row) for i, entry in enumerate(capture["ledger"])
        for row in common.journal_rows(i, entry)
    ))
    mutated = common.parse_json(files["receipt"].read_bytes())
    mutated.update(report_sha256=common.digest(files["report"]), journal_sha256=common.digest(files["journal"]))
    files["receipt"].write_bytes(common.encode(mutated))
    with pytest.raises(ValueError, match="ledger timeline"):
        run.read_capture(tmp_path, "synthetic", capture["identity_pin"])


def test_changed_final_helper_pin_leaves_capture_unqualified(
    modules: tuple[Any, Any], tmp_path: Path,
) -> None:
    from test_split_ephemeris_capture import FakeCaptureAdapter, synthetic_capture_bundle

    _, run = modules
    bundle = synthetic_capture_bundle()
    pins = iter(({"helper": "before"}, {"helper": "after"}))
    assert not run.run_phase(
        tmp_path, "capture", 0., execution="synthetic", input_loader=lambda _: bundle,
        pin_loader=lambda _: next(pins), adapter_factory=lambda: FakeCaptureAdapter(bundle),
        clock=lambda: 0., boot_s=0.,
    )
    capture, _ = run.read_phase(tmp_path, "capture", "synthetic")
    assert capture["error"]["stage"] == "final preparation identity"
    assert capture["final_identity_pin"] == {"helper": "after"}
    assert len(capture["ledger"]) == 46
    with pytest.raises(ValueError, match="capture incomplete"):
        run.read_capture(tmp_path, "synthetic", {"helper": "before"})


def test_bad_raw_shape_stays_in_ledger(modules: tuple[Any, Any]) -> None:
    common, _ = modules
    report: dict[str, Any] = {}
    recorder = common.Recorder(report, {"state": 1}, 0., 15., clock=lambda: 0.)

    def reject(raw: Any) -> None:
        raise ValueError("invalid state shape")

    with pytest.raises(ValueError, match="state shape"):
        recorder.call("state", "spkezr", [], lambda: {1: float("nan")}, reject)
    assert report["ledger"][0]["raw"] == {"invalid_type": "dict", "representation": "{1: nan}"}
    assert report["counts"]["state"] == {"attempted": 1, "returned": 1, "completed": 0}
