"""R5.59 fixtures exercise metadata gates without a trajectory solver or SPICE."""

from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
from runpy import run_path
import shutil
import time
from typing import Any

import pytest

ART = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
CORE = ART / "0206-readiness.py"
RUNNER = ART / "0206-readiness-runner.py"
type Row = dict[str, Any]


def encode(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def tag(text: str) -> str:
    return sha(("artificial:" + text).encode())


def rebind(packet: Row) -> None:
    binding = sha(encode(packet["binding"]))
    packet["binding_sha256"] = packet["sample_binding_sha256"] = binding
    for key in ("qualification", "budget"):
        packet[key]["binding_sha256"] = binding


def freeze_command(packet: Row, departure_s: float, arrival_s: float, azimuth: float = -math.pi) -> None:
    binding = packet["binding"]
    t0, tx, tf = map(float.fromhex, binding["anchors"])
    binding["command"]["words"] = [v.hex() for v in (azimuth, 0., departure_s, .1, -.2, arrival_s)]
    binding["native_event_words"] = [v.hex() for v in (t0, t0 + departure_s, tx, tf - arrival_s, tf)]
    rebind(packet)


@pytest.fixture
def packet() -> Row:
    t0, tx, tf = (v.hex() for v in (978995455.2304223, 979014965.9635216, 1004169273.4122404))
    solvers = ("RKDP87", "DOP853")
    qualification = {
        "coverage": {
            name: [[t0, tx], [tx, tf]] for name in (
                "10:0", "1:0", "2:0", "399:0", "301:399", "499:4", "4:0", "599:5",
                "5:0", "699:6", "6:0", "J2000:IAU_Moon", "J2000:IAU_Mars",
            )
        },
        "timing_sha256": tag("timing"),
        "solvers": {
            name: dict(reverse="decreasing-time-unchanged-physical-rhs",
                       adapter="artificial-qualification", version="test", **{
                           f"{key}_sha256": tag(f"{name}:{key}") for key in
                           ("source", "settings", "clock_policy", "endpoint_certificate", "force_parity")
                       }, force_controls=["near-Moon", "cruise", "near-Mars"])
            for name in solvers
        },
    }
    sample = {
        "join_event_words": [tx, tx],
        "target_event_words": [tf, tf],
        "join": {key: dict(difference=val, error_bounds=[val, val, val]) for key, val in (
            ("epoch_s", 0.0), ("position_m", 0.0001), ("velocity_m_s", 1e-8), ("mass_kg", 1e-11))},
        "target": {key: dict(difference=val, error_bounds=[val, val]) for key, val in (
            ("position_m", 100), ("velocity_m_s", 0.001))},
    }
    result = {
        "schema": "ariadna-r559-artificial-v1",
        "binding": {
            "candidate": "d0001-t0035",
            "model": ("ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-"
                      "cannonball-srp-schwarzschild-direct-spice-v2"),
            "coordinates": ["SI", "SSB", "J2000", "TDB seconds since J2000"],
            "anchors": [t0, tx, tf],
            "mass": dict(initial_kg=2000, dry_kg=500, thrust_n=1000, isp_s=450, g0_m_s2=9.80665,
                         area_m2=20, reflectivity=1.3),
            "departure_state_sha256": tag("departure"), "target_state_sha256": tag("target"),
            "settings_sha256": tag("settings"), "ordered_resources_sha256": [tag("a"), tag("b")],
            "command": dict(source="independent-artificial", rationale="Metadata test only",
                            source_sha256=tag("command")),
            "native_clock": "artificial-absolute-binary64-tdb",
        },
        "qualification": qualification,
        "budget": dict(
            attempts=1, pairs=1, searches=0, retries=0, audits=1, accounting="charged-upper-bound",
            accounting_sha256=tag("accounting"), work_stopped_s=285, finalized_s=300,
            audit_finalized_s=30, audit_input_bytes=64 * 2**20, audit_output_bytes=128 * 2**10,
            charges=[
                ["RKDP87", "segments", 6, "used"], ["DOP853", "segments", 6, "used"],
                ["RKDP87", "rhs", 300_000, "used"], ["RKDP87", "rhs", 100_000, "rejected"],
                ["DOP853", "rhs", 600_000, "reserved"],
                ["RKDP87", "provider", 16_000_000, "used"], ["DOP853", "provider", 16_000_000, "used"],
                ["DOP853", "evidence_bytes", 64 * 2**20, "used"],
            ],
        ),
        "samples": {name: deepcopy(sample) for name in solvers},
    }
    freeze_command(result, 2800., 1600.)
    return result


@pytest.fixture(scope="module")
def core() -> Row:
    return run_path(str(CORE))


@pytest.fixture(scope="module")
def runner() -> Row:
    return run_path(str(RUNNER))


def evaluate(core: Row, packet: Row) -> Row:
    raw = encode(packet)
    return core["evaluate"](raw, sha(raw))


def no_physical_claim(report: Row) -> None:
    assert report["stage"] == "R5.59"
    assert report["synthetic"] is True and report["live_authorized"] is False
    assert report["physical_status"] == "physical-join-not-established"
    assert report["physical_residuals"] == dict(epoch_s=None, position_m=None, velocity_m_s=None, mass_kg=None)


def test_admits_complete_artificial_packet_at_all_inclusive_caps(core: Row, packet: Row) -> None:
    report = evaluate(core, packet)
    no_physical_claim(report)
    assert report["status"] == "synthetic-ready"
    assert report["synthetic_budget"]["attempt_totals"] == dict(
        segments=12, rhs=1_000_000, provider=32_000_000, evidence_bytes=67_108_864)
    assert report["synthetic_budget"]["by_solver"]["RKDP87"]["rhs"] == 400_000
    assert report["synthetic_verdicts"]["join"]["status"] == report["synthetic_verdicts"]["target"]["status"] == "pass"
    # Independent mass oracle: each burn duration is exactly represented by the native clock here.
    mass = report["synthetic_mass"]
    declared = list(map(Fraction, mass["commanded_coast_coast_final_kg_exact"]))
    expected_rate = Fraction.from_float(1000 / (450 * 9.80665))
    assert declared == [2000 - 2800 * expected_rate] * 2 + [2000 - 4400 * expected_rate]
    assert mass["effective_coast_coast_final_kg_exact"] == mass["commanded_coast_coast_final_kg_exact"]


def test_rehashed_substituted_command_is_rejected_by_independent_pin(core: Row, packet: Row) -> None:
    pin = sha(encode(packet))
    freeze_command(packet, 2801., 1600.)
    with pytest.raises(ValueError, match="fixture size or identity"):
        core["evaluate"](encode(packet), pin)


@pytest.mark.parametrize(("departure", "arrival", "azimuth", "reason"), [
    (0., 1600., 0., "command-domain"),
    (1e-10, 1600., 0., "event-order"),
    (20_000., 1600., 0., "event-order"),
    (2800., 1600., math.pi, "command-domain"),
    (6000., float.fromhex("0x1.35be8f5c28f52p+9"), 0., "commanded-dry-floor"),
    (float.fromhex("0x1.77000000101b3p+12"), float.fromhex("0x1.35be8f5ba81b8p+9"),
     0., "effective-dry-floor"),
])
def test_command_and_mass_gates(core: Row, packet: Row, departure: float, arrival: float,
                                azimuth: float, reason: str) -> None:
    freeze_command(packet, departure, arrival, azimuth)
    report = evaluate(core, packet)
    assert report["reason"] == reason
    no_physical_claim(report)
    if "floor" in reason:
        t0, _, tf = map(float.fromhex, packet["binding"]["anchors"])
        # Independently evaluate exactly once with the frozen production rate.
        q = Fraction(1000 / (9.80665 * 450))
        declared = 2000 - q * (Fraction(departure) + Fraction(arrival))
        native = 2000 - q * (Fraction(t0 + departure) - Fraction(t0) + Fraction(tf) - Fraction(tf - arrival))
        if reason == "commanded-dry-floor":
            assert declared < 500 == float(declared) < native
        else:
            assert native < 500 < declared


@pytest.mark.parametrize(("keys", "value", "reason"), [
    (("binding", "model"), "archived-model-B", "candidate-model-frame"),
    (("binding", "anchors", 1), "0x1.d2d4a9afb54aep+29", "fixed-epochs"),
    (("binding", "native_event_words", 1), "0x1.0p+0", "native-events"),
    (("binding", "command", "source"), "failed-0079", "command-provenance"),
    (("binding", "command", "rationale"), "", "command-provenance"),
    (("binding", "departure_state_sha256"), "bad", "source-binding"),
    (("binding", "ordered_resources_sha256"), [], "resource-identity"),
    (("qualification", "coverage", "J2000:IAU_Mars"), [], "coverage-end"),
    (("qualification", "coverage", "301:399", 1, 0), "0x1.d2d4a9afb54aep+29", "coverage-gap"),
    (("qualification", "solvers", "RKDP87", "reverse"), "negated-rhs", "reverse-qualification"),
    (("qualification", "solvers", "DOP853", "endpoint_certificate_sha256"), None, "missing-endpoint"),
    (("qualification", "solvers", "DOP853", "source_sha256"), tag("RKDP87:source"), "reference-not-independent"),
    (("qualification", "timing_sha256"), None, "timing-proof"),
    (("samples", "DOP853", "join_event_words", 1), "0x1.d2d4a9afb54aep+29", "sample-coepoch"),
    (("samples", "RKDP87", "join", "epoch_s", "difference"), 1e-12, "sample-clock"),
    (("budget", "charges", 0, 2), 7, "segment-cap:RKDP87"),
    (("budget", "charges", 0, 3), "reserved", "incomplete-accounting"),
    (("budget", "retries"), 1, "one-attempt"),
    (("budget", "audits"), 2, "one-attempt"),
    (("budget", "audit_input_bytes"), 64 * 2**20 - 1, "audit-evidence-binding"),
    (("budget", "searches"), 1, "one-attempt"),
    (("budget", "work_stopped_s"), 285.0000000001, "study-deadline"),
    (("budget", "finalized_s"), 300.0000000001, "study-deadline"),
    (("budget", "audit_finalized_s"), 30.0000000001, "audit-deadline"),
    (("budget", "audit_input_bytes"), 64 * 2**20 + 1, "audit-bytes"),
    (("budget", "audit_output_bytes"), 128 * 2**10 + 1, "audit-bytes"),
    (("budget", "charges", 1, 2), 7, "attempt-cap:segments"),
    (("budget", "charges", 3, 2), 100_001, "attempt-cap:rhs"),
    (("budget", "charges", 5, 2), 16_000_001, "attempt-cap:provider"),
    (("budget", "charges", 7, 2), 64 * 2**20 + 1, "attempt-cap:evidence_bytes"),
    (("budget", "charges", 7, 3), "failed", "failed-work-counted"),
    (("budget", "charges", 3, 3), "failed", "work-after-failure"),
    (("budget", "charges", 0, 2), True, "unknown-charge"),
    (("budget", "accounting"), "instrumented", "opaque-unaccounted"),
    (("budget", "accounting_sha256"), None, "budget-proof"),
])
def test_incomplete_or_out_of_bounds_metadata_cannot_admit(
    core: Row, packet: Row, keys: tuple[str | int, ...], value: object, reason: str,
) -> None:
    row = packet
    for key in keys[:-1]:
        row = row[key]
    row[keys[-1]] = value
    rebind(packet)
    report = evaluate(core, packet)
    no_physical_claim(report)
    assert report["status"] == "unavailable" and report["reason"].startswith(reason)


@pytest.mark.parametrize("field", ["command", "native_event_words"])
def test_missing_required_value_is_invalid(core: Row, packet: Row, field: str) -> None:
    del packet["binding"][field]
    rebind(packet)
    with pytest.raises(ValueError, match="missing artificial evidence"):
        evaluate(core, packet)


@pytest.mark.parametrize("value", [True, "inf", "nan", "0x1p+1"])
def test_rejects_noncanonical_or_nonfinite_command_words(core: Row, packet: Row, value: object) -> None:
    packet["binding"]["command"]["words"][0] = value
    rebind(packet)
    with pytest.raises(ValueError, match="invalid or missing"):
        evaluate(core, packet)


@pytest.mark.parametrize(("d", "e", "expected"), [
    (900, 100, "pass"), (1000, 0, "pass"), (1100, 100, "inconclusive"),
    (1101, 100, "fail"), (999, 100, "inconclusive"), (0, None, "inconclusive"),
])
def test_interval_edges_and_separate_target_status(core: Row, packet: Row, d: int,
                                                   e: int | None, expected: str) -> None:
    for solver in packet["samples"].values():
        solver["target"]["position_m"] = dict(difference=d, error_bounds=None if e is None else [e, 0])
    report = evaluate(core, packet)
    groups = report["synthetic_verdicts"]
    assert groups["join"]["status"] == "pass" and groups["target"]["status"] == expected
    result = groups["target"]["solvers"]["DOP853"]["position_m"]
    if e is None:
        assert result["interval"] is None
    else:
        assert list(map(Decimal, result["interval"])) == [max(0, d - e), d + e]


def test_solver_disagreement_and_outward_rounding(core: Row, packet: Row) -> None:
    packet["samples"]["RKDP87"]["join"]["mass_kg"]["difference"] = 2e-9
    report = evaluate(core, packet)["synthetic_verdicts"]["join"]
    a, b = (report["solvers"][name]["mass_kg"] for name in ("RKDP87", "DOP853"))
    assert a["status"] == "fail" and b["status"] == "pass"
    assert report["status"] == "inconclusive"
    lo, hi = (Fraction(x) for x in a["interval"])
    d, E = Fraction(2e-9), 3 * Fraction(1e-11)
    assert lo <= d - E < d + E <= hi


def full_fixture(tmp_path: Path, packet: Row, *, extra_bytes: int = 0) -> tuple[Path, str]:
    raw = encode(packet)
    raw = raw.ljust(2 * 2**20 + extra_bytes, b" ")
    fixture = tmp_path / "packet.json"
    fixture.write_bytes(raw)
    return fixture, sha(raw)


def test_full_input_budget_exclusive_output_and_saved_hash_chain(
    runner: Row, packet: Row, tmp_path: Path,
) -> None:
    fixture, pin = full_fixture(tmp_path, packet)
    output = tmp_path / "result"
    assert runner["launch"](fixture, pin, output)
    report = runner["verify_result"](output, pin)
    no_physical_claim(report)
    assert report["status"] == "synthetic-ready"
    saved = {p.name: p.read_bytes() for p in output.iterdir()}
    assert sum(map(len, saved.values())) <= 128 * 2**10
    assert not runner["launch"](fixture, pin, output)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == saved
    with pytest.raises((ValueError, OSError)):
        runner["verify_result"](output, tag("false-pin"))
    (output / "report.json").write_bytes(saved["report.json"] + b" ")
    with pytest.raises((ValueError, OSError)):
        runner["verify_result"](output, pin)


@pytest.mark.parametrize("mode", ["too-large", "symlink", "digest"])
def test_input_refusal(runner: Row, packet: Row, tmp_path: Path, mode: str) -> None:
    fixture, pin = full_fixture(tmp_path, packet, extra_bytes=mode == "too-large")
    if mode == "symlink":
        link = tmp_path / "symlink.json"
        link.symlink_to(fixture)
        fixture = link
    out = tmp_path / "result"
    assert not runner["launch"](fixture, tag("wrong") if mode == "digest" else pin, out)


def test_watchdog_rejects_a_worker_stall(packet: Row, tmp_path: Path) -> None:
    fixture, pin = full_fixture(tmp_path, packet)
    copy = tmp_path / RUNNER.name
    shutil.copyfile(RUNNER, copy)
    # Standard-library worker remains isolated; only the artificial metadata evaluator stalls.
    (tmp_path / CORE.name).write_text(CORE.read_text() + "\ndef evaluate(raw, expected_sha256):\n"
                                     "    import time\n    time.sleep(5)\n")
    runner = run_path(str(copy))
    launch = runner["launch"]
    launch.__globals__["WALL_S"] = 0.8
    output = tmp_path / "stalled"
    started = time.monotonic()
    assert not launch(fixture, pin, output)
    assert time.monotonic() - started < 5
    with pytest.raises((ValueError, OSError)):
        runner["verify_result"](output, pin)


def test_saved_output_cap_rejects_overlong_report(runner: Row, packet: Row, tmp_path: Path) -> None:
    fixture, pin = full_fixture(tmp_path, packet)
    out = tmp_path / "result"
    assert runner["launch"](fixture, pin, out)
    with (out / "report.json").open("ab") as stream:
        stream.write(b" " * (128 * 2**10))
    with pytest.raises(ValueError, match="byte cap"):
        runner["verify_result"](out, pin)


def test_late_receipt_does_not_certify_a_report(packet: Row, tmp_path: Path) -> None:
    fixture, pin = full_fixture(tmp_path, packet)
    copy = tmp_path / RUNNER.name
    code = RUNNER.read_text()
    needle = "    _sync(path.parent)\n    return _sha(raw)"
    assert code.count(needle) == 1
    copy.write_text(code.replace(needle, "    _sync(path.parent)\n"
                                 "    if path.name == 'receipt.json':\n"
                                 "        import time\n        time.sleep(5)\n"
                                 "    return _sha(raw)"))
    shutil.copyfile(CORE, tmp_path / CORE.name)
    runner = run_path(str(copy))
    launch = runner["launch"]
    launch.__globals__["WALL_S"] = 1.2
    output = tmp_path / "late"
    assert not launch(fixture, pin, output)
    assert (output / "report.json").is_file() and (output / "receipt.json").is_file()
    assert not (output / "completion.json").exists()
    with pytest.raises(ValueError, match="absent, late or incomplete"):
        runner["verify_result"](output, pin)


def test_rehashed_evidence_cannot_claim_a_physical_match(runner: Row, packet: Row, tmp_path: Path) -> None:
    fixture, pin = full_fixture(tmp_path, packet)
    out = tmp_path / "result"
    assert runner["launch"](fixture, pin, out)
    report, receipt, completion = (
        json.loads((out / name).read_bytes()) for name in ("report.json", "receipt.json", "completion.json")
    )
    report["physical_status"] = "physical-join-established"
    report["physical_residuals"]["mass_kg"] = 0.0
    receipt["report_sha256"] = sha(encode(report))
    completion["receipt_sha256"] = sha(encode(receipt))
    for name, data in (("report", report), ("receipt", receipt), ("completion", completion)):
        (out / f"{name}.json").write_bytes(encode(data))
    with pytest.raises(ValueError):
        runner["verify_result"](out, pin)
