"""Qualify artificial observations without opening retained scientific evidence."""

from collections.abc import Callable
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
from runpy import run_path
import sys
from types import ModuleType
from typing import Any

import pytest

ART = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
type Row = dict[str, Any]
type Methods = dict[str, ModuleType]


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def runner() -> Row:
    return run_path(str(ART / "0223-artificial-trace.py"))


@pytest.fixture(scope="module")
def methods(runner: Row) -> Methods:
    return runner["_methods"]()


@pytest.fixture(scope="module")
def outcome(runner: Row, tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Row]:
    output = tmp_path_factory.mktemp("r559k-unit") / "r559k-artificial-result"
    return output, runner["run"](output)


def test_full_matrix_matches_unchanged_controls_and_saved_readback(
    runner: Row, methods: Methods, outcome: tuple[Path, Row],
) -> None:
    output, report = outcome
    assert report["status"] == "artificial-trace-qualified"
    assert report["scope"] == "artificial" and report["commands"] is None
    assert set(report["fixtures"]) == {"witness", "refusal"}
    assert report["work"]["bounds"] == 48
    assert report["work"]["points"] == 12
    assert 0 < report["work"]["events"] <= 8192
    expected = {
        (case, lo, hi, sign, independent)
        for case in ("witness", "refusal")
        for lo, hi in (("151", "152"), ("151", "4833/32"), ("9665/64", "9665/64"))
        for sign in ("positive", "negative")
        for independent in (False, True)
    }
    assert {(row["case"], row["lo_deg"], row["hi_deg"], row["sign"], row["independent"])
            for row in report["rows"]} == expected
    assert len(report["rows"]) == 24
    for row in report["rows"]:
        assert methods["io"]._wire(row["trace"]["result"]) == methods["io"]._wire(row["control"])
        methods["trace"].verify_trace(row["trace"], row["control"])
        assert row["containment"] and all(proof["status"] == "verified" for proof in row["containment"])
    expected_pins = {name: digest(Path(module.__file__)) for name, module in methods.items()}
    expected_pins["runner"] = digest(ART / "0223-artificial-trace.py")
    assert report["source_pins"] == expected_pins
    assert {path.name for path in output.iterdir()} == {
        "attempt.json", "report.json", "receipt.json", "completion.json",
    }
    assert sum(path.stat().st_size for path in output.iterdir()) <= 4 * 1024**2
    saved = runner["audit"](output, digest(output / "completion.json"))
    assert saved == report
    assert saved["independent_readback"]["status"] == "artificial-trace-qualified"
    assert saved["independent_readback"]["rows"] == 24
    assert saved["independent_readback"]["new_bounds"] == saved["independent_readback"]["new_points"] == 0
    assert all(report[key] == 0 for key in ("spice_queries", "kernel_accesses", "force_evaluations",
                                           "integrations", "r559i_attempts", "r560_attempts"))


def test_output_reuse_and_wrong_completion_pin_cannot_change_evidence(
    runner: Row, outcome: tuple[Path, Row],
) -> None:
    output, _ = outcome
    before = {path.name: digest(path) for path in output.iterdir()}
    with pytest.raises(ValueError):
        runner["run"](output)
    with pytest.raises(ValueError):
        runner["audit"](output, "0" * 64)
    assert {path.name: digest(path) for path in output.iterdir()} == before


def test_runner_rejects_unapproved_scope_and_caller_payload(runner: Row, tmp_path: Path) -> None:
    output = tmp_path / "retained-output"
    with pytest.raises(ValueError):
        runner["run"](output)
    assert not output.exists()
    artificial = tmp_path / "r559k-artificial-payload"
    with pytest.raises(TypeError):
        runner["run"](artificial, reference={"scope": "retained"})
    assert not artificial.exists()


def test_changed_source_pin_prevents_method_loading(runner: Row, monkeypatch: pytest.MonkeyPatch) -> None:
    namespace = runner["_methods"].__globals__
    pins = dict(namespace["METHODS"])
    filename, _ = pins["bounds"]
    pins["bounds"] = filename, "0" * 64
    monkeypatch.setitem(namespace, "METHODS", pins)
    with pytest.raises(ValueError, match="bounds method pin"):
        runner["_methods"]()


@pytest.mark.parametrize("field", ["wall_ns", "bound_cap", "point_cap", "event_cap", "byte_cap"])
def test_each_resource_cap_prevents_completion(runner: Row, tmp_path: Path, field: str) -> None:
    output = tmp_path / ("r559k-artificial-" + field)
    with pytest.raises(ValueError):
        budget = runner["Budget"](**{field: 0})
        runner["run"](output, budget=budget)
    assert not (output / "completion.json").exists()


@pytest.mark.parametrize(("field", "cap"), [
    ("bound_cap", 47), ("point_cap", 11), ("event_cap", 1), ("byte_cap", 16_384),
])
def test_undersized_positive_caps_restore_original_methods(
    runner: Row, methods: Methods, outcome: tuple[Path, Row], tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch, field: str, cap: int,
) -> None:
    _, report = outcome
    ref = report["fixtures"]["witness"]
    bounds, interval = methods["bounds"], methods["interval"]
    original_functions = {name: getattr(bounds, name)
                          for name in ("bounds", "_ellipse", "_reverse", "_norm2", "_mass_exclusion")}
    original_conversion, original_profile = interval.binary64_lower, sys.getprofile()
    before = bounds.bounds(ref, Fraction(151), Fraction(152), "positive", interval)
    monkeypatch.setitem(runner["run"].__globals__, "_methods", lambda: methods)
    output = tmp_path / ("r559k-artificial-positive-" + field)
    with pytest.raises(ValueError, match="cap"):
        runner["run"](output, budget=runner["Budget"](**{field: cap}))
    assert not (output / "completion.json").exists()
    assert sys.getprofile() is original_profile
    assert all(getattr(bounds, name) is function for name, function in original_functions.items())
    assert interval.binary64_lower is original_conversion
    after = bounds.bounds(ref, Fraction(151), Fraction(152), "positive", interval)
    assert methods["io"]._wire(after) == methods["io"]._wire(before)


def test_late_readback_failure_removes_completion_and_preserves_partial_evidence(
    runner: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "r559k-artificial-late-readback"
    durable: dict[str, str] = {}

    def late_readback(dest: Path, pin: str, methods: Methods, check: Callable[[], None]) -> Row:
        assert (dest / "completion.json").is_file()
        assert digest(dest / "completion.json") == pin
        durable.update({name: digest(dest / name) for name in ("attempt.json", "report.json", "receipt.json")})
        raise ValueError("wall cap")

    monkeypatch.setitem(runner["run"].__globals__, "_readback", late_readback)
    with pytest.raises(ValueError, match="wall cap"):
        runner["run"](output)
    assert durable and {path.name for path in output.iterdir()} == set(durable)
    assert {path.name: digest(path) for path in output.iterdir()} == durable
    with pytest.raises(ValueError, match="existing artificial output"):
        runner["run"](output)
    assert {path.name: digest(path) for path in output.iterdir()} == durable


def test_failed_completion_flush_removes_owned_file(
    runner: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "r559k-artificial-completion-flush"
    namespace = runner["run"].__globals__
    original_methods = namespace["_methods"]
    durable: dict[str, str] = {}

    def fail_completion_methods() -> Methods:
        loaded = original_methods()
        original_put = loaded["io"]._put

        def fail_after_write(path: Path, row: Row, cap: int) -> str:
            pin = original_put(path, row, cap)
            if path.name == "completion.json":
                assert path.is_file()
                durable.update({name: digest(output / name)
                                for name in ("attempt.json", "report.json", "receipt.json")})
                raise OSError("completion post-write fsync")
            return pin

        monkeypatch.setattr(loaded["io"], "_put", fail_after_write)
        return loaded

    monkeypatch.setitem(namespace, "_methods", fail_completion_methods)
    with pytest.raises(OSError, match="completion post-write fsync"):
        runner["run"](output)
    assert durable and {path.name for path in output.iterdir()} == set(durable)
    assert {path.name: digest(path) for path in output.iterdir()} == durable


def test_point_cache_key_must_match_saved_phase_before_containment(
    runner: Row, methods: Methods, outcome: tuple[Path, Row], monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, original = outcome
    report = deepcopy(original)
    report["points"]["witness"]["151"] = deepcopy(report["points"]["witness"]["303/2"])

    def no_containment(ref: Row, point: Row, trace: Row, sign: str, loaded: Methods) -> Row:
        pytest.fail("point phase identity was not checked before containment")

    monkeypatch.setattr(methods["containment"], "verify_containment", no_containment)
    with pytest.raises(ValueError, match="phase"):
        runner["_validate"](report, methods, lambda: None)


def test_tampered_saved_report_cannot_pass_readback(
    runner: Row, outcome: tuple[Path, Row], tmp_path: Path,
) -> None:
    original, _ = outcome
    output = tmp_path / "r559k-artificial-tampered"
    output.mkdir()
    for path in original.iterdir():
        (output / path.name).write_bytes(path.read_bytes())
    pin = digest(output / "completion.json")
    report = output / "report.json"
    row = json.loads(report.read_bytes())
    row["rows"][0]["trace"]["events"].pop()
    report.write_text(json.dumps(row, allow_nan=False) + "\n")
    with pytest.raises(ValueError):
        runner["audit"](output, pin)


def _complete_trace(report: Row) -> Row:
    return next(row for row in report["rows"]
                if row["trace"]["status"] == "complete" and row["trace"]["stages"]["_clearance"]["status"] == "complete")


@pytest.mark.parametrize("fault", [
    "nonfinite", "reversed", "missing-stage", "missing-event", "result", "disconnected-speed", "duration-image",
])
def test_resealed_malformed_trace_is_invalid(
    methods: Methods, outcome: tuple[Path, Row], fault: str,
) -> None:
    _, report = outcome
    row = _complete_trace(report)
    trace = deepcopy(row["trace"])
    if fault in ("nonfinite", "reversed"):
        field = next(field for event in trace["events"] for field in event["fields"].values())
        field.update(lo="NaN", hi="NaN") if fault == "nonfinite" else field.update(lo="1", hi="0")
    elif fault in ("disconnected-speed", "duration-image"):
        stage, path = (("bounds", "speed") if fault == "disconnected-speed"
                       else ("_mass_exclusion", "observed_duration_binary64[0]"))
        event = next(event for event in trace["events"] if event["stage"] == stage and event["event"] == "return")
        endpoint = event["fields"][path]
        endpoint["hi"] = str(Decimal(endpoint["hi"]) + 1)
    elif fault == "missing-stage":
        del trace["stages"]["_clearance"]
    elif fault == "missing-event":
        trace["events"].pop()
    else:
        trace["result"] = trace["result"] | {"reason": "mass"}
    trace["seal"] = methods["trace"]._seal(trace)
    with pytest.raises(ValueError):
        methods["trace"].verify_trace(trace, row["control"])


def test_saved_independent_point_outside_trace_is_rejected(
    methods: Methods, outcome: tuple[Path, Row],
) -> None:
    _, report = outcome
    row = _complete_trace(report)
    reference = report["fixtures"][row["case"]]
    point = deepcopy(report["points"][row["case"]][row["lo_deg"]])
    point["independent_relative_si"][0] = "1E+100"
    with pytest.raises(ValueError, match="excludes independent quantity"):
        methods["containment"].verify_containment(reference, point, row["trace"], row["sign"], methods)


def test_exact_mass_equality_preserves_the_strict_original_rule(methods: Methods) -> None:
    rate = Fraction(1000 / (9.80665 * 450))
    allowance = Fraction(math.nextafter(1e-6, math.inf))
    equal_duration_s = Fraction(1500) / rate + allowance
    for independent in (False, True):
        exclude = methods["bounds"].dry_floor_exclusion
        assert exclude(Fraction(0), equal_duration_s, independent=independent) == (False, Fraction(1500))
        assert exclude(Fraction(0), equal_duration_s + Fraction(1, 10**12), independent=independent)[0]
        assert not exclude(Fraction(0), equal_duration_s - Fraction(1, 10**12), independent=independent)[0]


def test_guard_transition_and_early_failure_keep_original_dispositions(methods: Methods) -> None:
    original_functions = {name: getattr(methods["bounds"], name)
                          for name in ("bounds", "_ellipse", "_reverse", "_norm2", "_mass_exclusion")}
    original_conversion = methods["interval"].binary64_lower
    fixture = methods["points"].fixture("transition", methods)
    ref = deepcopy(fixture["reference"])
    assert [point["branches"]["positive"]["reason"] for point in fixture["anchors"]] == ["guard", "guard", None]
    for independent in (False, True):
        trace = methods["trace"].trace_bound(
            ref, Fraction(151), Fraction(152), "positive", methods,
            independent=independent, check=lambda: None, emit=lambda event: None,
        )
        control = methods["bounds"].bounds(
            ref, Fraction(151), Fraction(152), "positive", methods["interval"], independent=independent,
        )
        assert control["reason"] != "guard"
        methods["trace"].verify_trace(trace, control)
        broken = deepcopy(ref)
        broken["normalized"]["endpoints"][1]["v_infinity_m_s"] = [0., 0., 0.]
        early = methods["trace"].trace_bound(
            broken, Fraction(151), Fraction(152), "positive", methods,
            independent=independent, check=lambda: None, emit=lambda event: None,
        )
        original = methods["bounds"].bounds(
            broken, Fraction(151), Fraction(152), "positive", methods["interval"], independent=independent,
        )
        methods["trace"].verify_trace(early, original)
        assert early["status"] == "early-failure"
        assert early["stages"]["_mass_exclusion"]["status"] == "not-reached"
        assert early["stages"]["_clearance"]["status"] == "not-reached"
    assert all(getattr(methods["bounds"], name) is function for name, function in original_functions.items())
    assert methods["interval"].binary64_lower is original_conversion
