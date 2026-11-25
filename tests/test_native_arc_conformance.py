"""Synthetic native seam checks; no mission ephemerides or trajectory search."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from fractions import Fraction
import json
import math
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from typing import cast

import pytest

from space_nav import _coupled_benchmark_oracle as physical_oracle
from space_nav import _native_arc_conformance as candidate

State = tuple[float, float, float, float, float, float, float]
_INITIAL: State = (10000000.0, 0.0, 0.0, 0.0, 1000.0, 0.0, 2000.0)


@dataclass(frozen=True, slots=True, order=True)
class _Time:
    exact_s: Fraction

    def __sub__(self, other: _Time) -> _Time:
        return _Time(self.exact_s - other.exact_s)

    def to_float(self) -> float:
        return float(self.exact_s)


def _time(word: float) -> _Time:
    return _Time(Fraction(word))


@dataclass
class _Simulator:
    state_history_time_object: Mapping[_Time, State]
    integration_completed_successfully: bool = True
    cumulative_number_of_function_evaluations: Mapping[float, int] | None = None

    def __post_init__(self) -> None:
        if self.cumulative_number_of_function_evaluations is None:
            self.cumulative_number_of_function_evaluations = {0.0: 7, 1.0: 31, 2.0: 11}

    @property
    def state_history(self) -> object:
        raise AssertionError("float-keyed history cannot replace native event identity")


@dataclass
class _Clock:
    now_s: float = 0.0

    def __call__(self) -> float:
        return self.now_s


def _budget(clock: _Clock | None = None) -> candidate.Budget:
    return candidate.Budget(started_s=0.0, clock=clock or _Clock())


@pytest.fixture
def synthetic_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(candidate, "_runtime", lambda: {"scope": "fabricated runtime; no native import"})


def _request(
    *, mode: str = "departure-burn", start_s: Fraction = Fraction(0),
    end_s: Fraction = Fraction(1000), start_state: State = _INITIAL,
) -> candidate.NativeRequest:
    return candidate.NativeRequest(mode, start_s, end_s, start_state)


def _read(
    request: candidate.NativeRequest | None = None,
    *, end_state: State | None = None, end_delta_s: Fraction = Fraction(0),
    start_delta_s: Fraction = Fraction(0),
) -> dict[str, object]:
    arc = request or _request()
    end = end_state or (10000000.0, 2000000.0, 0.0, 0.0, 1100.0, 0.0, 1750.0)
    # Reverse insertion order intentionally disagrees with propagation direction.
    history = {
        _Time(arc.end_s + end_delta_s): end,
        _Time(arc.start_s + start_delta_s): arc.start_state,
    }
    return candidate.read_arc(_Simulator(history), arc, _time)


def _fake_runner(
    reference: Mapping[str, object], calls: list[candidate.NativeRequest],
    *, unequal_at: int | None = None, failure_at: int | None = None,
    endpoint_word_shift: bool = False,
) -> Callable[[candidate.NativeRequest, candidate.Budget], dict[str, object]]:
    rows = cast(list[list[float]], reference["states"])
    by_epoch = dict(zip((Fraction(0), Fraction(1000), Fraction(9000), Fraction(10000)), rows, strict=True))
    rate = Fraction(1000.0 / (9.80665 * 450.0))
    def run(request: candidate.NativeRequest, budget: candidate.Budget) -> dict[str, object]:
        budget.charge_native()
        budget.charge_provider()
        calls.append(request)
        if failure_at == len(calls):
            raise candidate.ConformanceError("injected native failure")
        values = list(by_epoch[request.end_s])
        duration = request.end_s - request.start_s
        values[6] = float(Fraction(request.start_state[6]) - (rate * duration if request.mode != "coast" else 0))
        if endpoint_word_shift:
            values[0] = math.nextafter(values[0], math.inf)
            values[6] = math.nextafter(values[6], math.inf)
        result = _read(request, end_state=cast(State, tuple(values)))
        result["provider_attempts"] = 1
        if unequal_at == len(calls):
            cast(dict[str, object], result["end_event"])["native_equal"] = False
        return result
    return run


@pytest.mark.parametrize("start,end,direction", [(0, 1000, 1), (10000, 9000, -1)])
def test_exact_integer_transport_accepts_both_directions(start: int, end: int, direction: int) -> None:
    request = _request(start_s=Fraction(start), end_s=Fraction(end))
    candidate.admit_transport(request)
    assert request.direction == direction
    assert request.start_s == Fraction(start) and request.end_s == Fraction(end)


@pytest.mark.parametrize("start,end", [
    (Fraction(1000000000), Fraction(1000000000) + Fraction(1, 2 ** 30)),
    (Fraction(0), Fraction(1, 10)),
    (Fraction(1, 10), Fraction(1)),
])
def test_inexact_or_collapsed_transport_is_unavailable_without_quantizing(
    start: Fraction, end: Fraction,
) -> None:
    request = _request(start_s=start, end_s=end)
    frozen = (request.start_s, request.end_s)
    with pytest.raises(candidate.ConformanceError):
        candidate.admit_transport(request)
    assert (request.start_s, request.end_s) == frozen


@pytest.mark.parametrize("field_name,value", [
    ("mode", "burn"), ("start_s", 0.0), ("end_s", True),
    ("end_s", Fraction(0)), ("start_state", _INITIAL[:-1]),
    ("start_state", (math.nan,) + _INITIAL[1:]),
    ("start_state", (True,) + _INITIAL[1:]),
    ("start_state", _INITIAL[:-1] + (499.0,)),
    ("start_state", (0.0, 0.0, 0.0) + _INITIAL[3:]),
])
def test_malformed_request_refuses_native_entry(field_name: str, value: object) -> None:
    with pytest.raises(candidate.ConformanceError):
        replace(_request(), **{field_name: value})


@pytest.mark.parametrize("direction", [1, -1])
def test_native_reader_binds_directional_endpoint_state_to_native_key(direction: int) -> None:
    request = _request(start_s=Fraction(0 if direction == 1 else 1000), end_s=Fraction(1000 if direction == 1 else 0))
    end: State = (10000000.0, 1000000.0, 0.0, 0.0, 1100.0, 0.0, 1750.0)
    row = _read(request, end_state=end)
    assert row["direction"] == direction and row["mode"] == request.mode
    assert tuple(cast(list[float], row["start_state"])) == request.start_state
    assert tuple(cast(list[float], row["end_state"])) == end
    assert row["samples_checked"] == 2
    assert row["native_reported_function_evaluations"] == 31
    for key, exact in (("start_event", request.start_s), ("end_event", request.end_s)):
        event = cast(dict[str, object], row[key])
        assert event["requested"] == [exact.numerator, exact.denominator]
        assert event["label_hex"] == float(exact).hex()
        assert event["native_equal"] is True and event["residual_s"] == 0.0


@pytest.mark.parametrize("which", ["start", "end"])
def test_native_inequality_cannot_hide_behind_equal_float_labels(which: str) -> None:
    request = _request(start_s=Fraction(1000000000), end_s=Fraction(1000001000))
    delta = Fraction(1, 2 ** 40)
    row = _read(request, start_delta_s=delta if which == "start" else Fraction(0), end_delta_s=delta if which == "end" else Fraction(0))
    event = cast(dict[str, object], row[which + "_event"])
    exact = request.start_s if which == "start" else request.end_s
    assert event["observed_label_s"] == float(exact)
    assert event["native_equal"] is False
    assert event["residual_s"] == float(delta)
    assert 0.0 < cast(float, event["residual_s"]) <= 1e-6


@pytest.mark.parametrize("flag", [False, None, 1, "True"])
def test_failed_or_nonboolean_completion_has_no_normal_endpoint(flag: object) -> None:
    request = _request()
    simulator = _Simulator({_time(0.0): _INITIAL, _time(1000.0): _INITIAL})
    simulator.integration_completed_successfully = flag
    with pytest.raises(candidate.ConformanceError):
        candidate.read_arc(simulator, request, _time)


@pytest.mark.parametrize("bad", [
    (math.inf,) + _INITIAL[1:], _INITIAL[:-1] + (499.0,),
    (0.0, 0.0, 0.0) + _INITIAL[3:], (10000000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2000.0),
])
def test_every_native_history_sample_must_be_finite_mass_safe_and_tnw_valid(bad: State) -> None:
    simulator = _Simulator({_time(0.0): _INITIAL, _time(500.0): bad, _time(1000.0): _INITIAL})
    with pytest.raises(candidate.ConformanceError):
        candidate.read_arc(simulator, _request(), _time)


def test_missing_native_history_cannot_fall_back_to_float_history() -> None:
    with pytest.raises(candidate.ConformanceError):
        candidate.read_arc(_Simulator({}), _request(), _time)


def test_native_function_telemetry_uses_largest_count_value_not_latest_epoch() -> None:
    history = {1000.0: 7, 900.0: 47, 0.0: 11, 700.0: 3}
    assert candidate.reported_functions(history) == 47


@pytest.mark.parametrize("history", [{}, {0.0: True}, {0.0: -1}, {0.0: math.inf}, {0.0: 1.5}])
def test_malformed_native_function_telemetry_is_not_provider_accounting(history: Mapping[float, object]) -> None:
    with pytest.raises(candidate.ConformanceError):
        candidate.reported_functions(history)


def test_fixed_producer_carries_actual_states_and_masses_and_independent_reverse_seed(synthetic_runtime: None) -> None:
    reference = physical_oracle.reference()
    calls: list[candidate.NativeRequest] = []
    packet = candidate.produce(reference, _budget(), arc_runner=_fake_runner(reference, calls, endpoint_word_shift=True))
    assert packet["status"] == "passed" and len(calls) == 6
    paths = cast(dict[str, list[dict[str, object]]], packet["paths"])
    assert [request.mode for request in calls] == ["departure-burn", "coast", "arrival-burn", "arrival-burn", "coast", "departure-burn"]
    assert [request.direction for request in calls] == [1, 1, 1, -1, -1, -1]
    for offset, path in ((0, paths["forward"]), (3, paths["reverse"])):
        for index in (1, 2):
            actual = tuple(cast(list[float], path[index - 1]["end_state"]))
            assert calls[offset + index].start_state == actual
    rows = cast(list[list[float]], reference["states"])
    assert calls[3].start_state == tuple(rows[-1])
    assert calls[3].start_state != tuple(cast(list[float], paths["forward"][-1]["end_state"]))
    counts = cast(dict[str, object], packet["counts"])
    assert counts["native_attempts"] == counts["provider_attempts"] == 6
    assert counts["contexts_created"] == counts["contexts_closed"] == 6
    assert counts["native_reported_function_evaluations"] == [31] * 6
    assert all(counts[key] == 0 for key in ("spice_queries", "kernel_reads", "real_archive_reads", "optimizer_entries"))
    assert packet["frame"] == "SYNTHETIC_INERTIAL" and packet["time_scale"] == "elapsed_seconds"


@pytest.mark.parametrize("failure_at", [1, 3, 4, 6])
def test_first_native_failure_retains_only_completed_rows_and_disposes_context(failure_at: int, synthetic_runtime: None) -> None:
    reference = physical_oracle.reference()
    calls: list[candidate.NativeRequest] = []
    budget = _budget()
    packet = candidate.produce(reference, budget, arc_runner=_fake_runner(reference, calls, failure_at=failure_at))
    assert packet["status"] != "passed" and len(calls) == failure_at
    paths = cast(dict[str, list[dict[str, object]]], packet["paths"])
    assert len(paths["forward"]) + len(paths["reverse"]) == failure_at - 1
    counts = cast(dict[str, object], packet["counts"])
    assert counts["native_attempts"] == failure_at
    assert counts["contexts_created"] == counts["contexts_closed"] == failure_at
    assert packet["failure"] is not None
    with pytest.raises(candidate.ConformanceError):
        budget.charge_native()
    assert len(calls) == failure_at


def test_inexact_observed_native_identity_retains_diagnostic_row_then_stops(synthetic_runtime: None) -> None:
    reference = physical_oracle.reference()
    calls: list[candidate.NativeRequest] = []
    packet = candidate.produce(reference, _budget(), arc_runner=_fake_runner(reference, calls, unequal_at=1))
    assert packet["status"] == "unavailable-transport" and len(calls) == 1
    paths = cast(dict[str, list[dict[str, object]]], packet["paths"])
    assert len(paths["forward"]) == 1 and paths["reverse"] == []
    assert cast(dict[str, object], paths["forward"][0]["end_event"])["native_equal"] is False


@pytest.mark.parametrize("counter,limit,method_name", [("native_attempts", 6, "charge_native"), ("provider_attempts", 100000, "charge_provider")])
def test_attempt_caps_charge_before_work_and_refuse_the_next_entry(counter: str, limit: int, method_name: str) -> None:
    budget = _budget()
    setattr(budget, counter, limit - 1)
    charge = getattr(budget, method_name)
    charge()
    assert getattr(budget, counter) == limit
    with pytest.raises(candidate.ConformanceError):
        charge()
    assert getattr(budget, counter) == limit
    with pytest.raises(candidate.ConformanceError):
        budget.check()


def test_producer_and_finalization_share_inherited_start_and_finite_deadlines() -> None:
    clock = _Clock(44.0)
    budget = _budget(clock)
    clock.now_s = 44.999
    budget.check()
    clock.now_s = 45.0
    with pytest.raises(candidate.ConformanceError):
        budget.check()
    clock.now_s = 59.999
    budget.check_finalization()
    clock.now_s = 60.0
    with pytest.raises(candidate.ConformanceError):
        budget.check_finalization()


@pytest.mark.parametrize("bad_clock", [-0.1, math.nan, math.inf, True])
def test_clock_failure_cannot_be_repaired_to_continue_producer_work(bad_clock: object) -> None:
    clock = _Clock()
    budget = _budget(clock)
    clock.now_s = bad_clock
    with pytest.raises(candidate.ConformanceError):
        budget.check()
    clock.now_s = 1.0
    with pytest.raises(candidate.ConformanceError):
        budget.check()


def test_input_byte_boundary_is_checked_before_json_decoding() -> None:
    raw = b"{}".ljust(65536, b" ")
    assert candidate.decode_input(raw) == {}
    with pytest.raises(candidate.ConformanceError):
        candidate.decode_input(raw + b" ")
    with pytest.raises(candidate.ConformanceError):
        candidate.decode_input(b"{")


def test_output_byte_boundary_and_finite_json_are_enforced() -> None:
    base = len(candidate.encode_packet({"padding": ""}))
    assert len(candidate.encode_packet({"padding": "x" * (2 * 1024 * 1024 - base)})) == 2 * 1024 * 1024
    with pytest.raises(candidate.ConformanceError):
        candidate.encode_packet({"padding": "x" * (2 * 1024 * 1024 - base + 1)})
    with pytest.raises(candidate.ConformanceError):
        candidate.encode_packet({"not_finite": math.nan})


def test_durable_packets_are_exclusive_and_share_a_total_byte_cap(tmp_path: Path) -> None:
    budget = _budget()
    target = tmp_path / "packet.json"
    candidate.write_packet(target, {"stage": "producer"}, budget)
    assert json.loads(target.read_bytes()) == {"stage": "producer"}
    original = target.read_bytes()
    with pytest.raises(candidate.ConformanceError):
        candidate.write_packet(target, {"stage": "changed"}, budget)
    assert target.read_bytes() == original


def test_external_watchdog_stops_the_actual_launcher_child() -> None:
    with pytest.raises(candidate.ConformanceError, match="watchdog") as caught:
        candidate._child([sys.executable, "-c", "import time; time.sleep(30)"], time.monotonic() + 0.1, 1024)
    assert set(caught.value.logs) == {"stdout", "stderr"}
    assert all(isinstance(value, str) for value in caught.value.logs.values())


def test_launcher_caps_the_combined_stdout_and_stderr_bytes() -> None:
    command = [sys.executable, "-c", "import os; os.write(1, b'x'*8); os.write(2, b'y'*8)"]
    with pytest.raises(candidate.ConformanceError, match="log byte cap") as caught:
        candidate._child(command, time.monotonic() + 5.0, 15)
    assert sum(len(value.encode()) for value in caught.value.logs.values()) <= 15


def test_launcher_retains_both_bounded_pipes_and_return_code() -> None:
    command = [sys.executable, "-c", "import os; os.write(1, b'out'); os.write(2, b'err')"]
    report = candidate._child(command, time.monotonic() + 5.0, 6)
    assert report == {"returncode": 0, "stdout": "out", "stderr": "err"}


@pytest.mark.live
def test_fixed_six_arc_native_fixture(
    tmp_path: Path, record_testsuite_property: Callable[[str, object], None],
) -> None:
    """One bounded cold native fixture; this test deliberately loads no SPICE."""
    report = candidate.run_isolated(tmp_path)
    assert cast(dict[str, object], report["producer"])["status"] == "passed"
    assert cast(dict[str, object], report["audit"])["status"] == "passed"
    record_testsuite_property("ariadna_f7_native_conformance", json.dumps(report, sort_keys=True, allow_nan=False))


@pytest.mark.parametrize("changed", [_INITIAL[:-1] + (1999.0,), (_INITIAL[0], -0.0) + _INITIAL[2:]])
def test_native_initial_seven_words_cannot_reset_the_request(changed: State) -> None:
    simulator = _Simulator({_time(0.0): changed, _time(1000.0): _INITIAL})
    with pytest.raises(candidate.ConformanceError):
        candidate.read_arc(simulator, _request(), _time)


def test_durable_output_cap_accumulates_across_different_files(tmp_path: Path) -> None:
    budget = _budget()
    packet = {"padding": ""}
    overhead = len(candidate.encode_packet(packet))
    packet["padding"] = "x" * (1024 * 1024 - overhead)
    assert len(candidate.encode_packet(packet)) == 1024 * 1024
    candidate.write_packet(tmp_path / "first.json", packet, budget)
    candidate.write_packet(tmp_path / "second.json", packet, budget)
    assert budget.output_bytes == 2 * 1024 * 1024
    with pytest.raises(candidate.ConformanceError):
        candidate.write_packet(tmp_path / "third.json", {}, budget)
    assert not (tmp_path / "third.json").exists()
    assert sum(path.stat().st_size for path in tmp_path.iterdir()) == 2 * 1024 * 1024


@pytest.mark.parametrize("end_s", [Fraction(1, 10), Fraction(1000000000) + Fraction(1, 2 ** 30)])
def test_native_entry_refuses_unsupported_events_before_import_or_charge(end_s: Fraction) -> None:
    start_s = Fraction(0) if end_s < 1 else Fraction(1000000000)
    request = _request(start_s=start_s, end_s=end_s)
    budget = _budget()
    with pytest.raises(candidate.ConformanceError, match="unavailable-transport"):
        candidate.native_arc(request, budget)
    assert budget.native_attempts == budget.provider_attempts == 0


def test_provider_refusal_closes_the_first_context_without_another_arc(synthetic_runtime: None) -> None:
    reference = physical_oracle.reference()
    budget = _budget()
    budget.provider_attempts = 100000
    calls: list[candidate.NativeRequest] = []
    packet = candidate.produce(reference, budget, arc_runner=_fake_runner(reference, calls))
    assert packet["status"] == "failed" and calls == []
    counts = cast(dict[str, object], packet["counts"])
    assert counts["native_attempts"] == 1 and counts["provider_attempts"] == 100000
    assert counts["contexts_created"] == counts["contexts_closed"] == 1
    assert packet["paths"] == {"forward": [], "reverse": []}


@pytest.mark.parametrize("exception_type", [ValueError, RuntimeError])
def test_clock_callback_exception_poisoning_prevents_later_producer_work(exception_type: type[Exception]) -> None:
    fail = False
    def clock() -> float:
        if fail:
            raise exception_type("injected clock failure")
        return 1.0
    budget = candidate.Budget(started_s=0.0, clock=clock)
    fail = True
    with pytest.raises(candidate.ConformanceError):
        budget.check()
    fail = False
    with pytest.raises(candidate.ConformanceError):
        budget.check()



def test_isolated_parent_stops_after_first_failed_producer_and_retains_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    stages: list[str] = []
    first = {"status": "failed", "reason": "fabricated first native failure"}
    def child(command: list[str], deadline_s: float, log_cap: int) -> dict[str, object]:
        stages.append(command[3])
        assert command[3] == "produce"
        Path(command[5]).write_bytes(candidate.encode_packet(first))
        return {"returncode": 2, "stdout": "partial diagnostic", "stderr": "first failure"}
    monkeypatch.setattr(candidate, "_child", child)
    report = candidate.run_isolated(tmp_path)
    assert stages == ["produce"] and report["status"] == "failed"
    assert report["producer"] == first and report["audit"] is None
    assert "producer failed" in cast(str, report["failure"])
    assert cast(list[dict[str, object]], report["children"])[0]["stderr"] == "first failure"
    assert json.loads((tmp_path / "receipt.json").read_bytes()) == report
    assert json.loads((tmp_path / "producer.json").read_bytes()) == first


def test_isolated_parent_retains_capped_logs_on_child_watchdog_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    stages: list[str] = []
    def child(command: list[str], deadline_s: float, log_cap: int) -> dict[str, object]:
        stages.append(command[3])
        error = candidate.ConformanceError("injected external watchdog deadline")
        error.logs = {"stdout": "before watchdog", "stderr": "first callback failure"}
        raise error
    monkeypatch.setattr(candidate, "_child", child)
    report = candidate.run_isolated(tmp_path)
    assert stages == ["produce"] and report["status"] == "failed"
    assert report["producer"] is report["audit"] is None
    assert "watchdog" in cast(str, report["failure"])
    assert report["children"] == [{"returncode": None, "stdout": "before watchdog", "stderr": "first callback failure"}]
    assert json.loads((tmp_path / "receipt.json").read_bytes()) == report


def test_isolated_child_phases_share_parent_start_and_bounded_deadlines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    stages: list[tuple[str, float, float, float]] = []
    def child(command: list[str], deadline_s: float, log_cap: int) -> dict[str, object]:
        stages.append((command[3], float(command[-1]), deadline_s, time.monotonic()))
        assert log_cap == 128 * 1024
        Path(command[5]).write_bytes(candidate.encode_packet({"status": "passed"}))
        return {"returncode": 0, "stdout": "", "stderr": ""}
    monkeypatch.setattr(candidate, "_child", child)
    report = candidate.run_isolated(tmp_path)
    assert report["status"] == "passed" and [row[0] for row in stages] == ["produce", "audit"]
    assert stages[0][1] == stages[1][1]
    assert stages[0][2] == stages[0][1] + 45.0
    assert stages[1][2] <= stages[1][1] + 55.0
    assert stages[1][2] <= stages[1][3] + 10.0


def test_isolated_fixture_never_overwrites_an_existing_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved = tmp_path / "producer.json"
    saved.write_bytes(b"historical evidence")
    def forbidden_child(command: list[str], deadline_s: float, log_cap: int) -> dict[str, object]:
        raise AssertionError("existing evidence must refuse before any child")
    monkeypatch.setattr(candidate, "_child", forbidden_child)
    with pytest.raises(candidate.ConformanceError, match="empty"):
        candidate.run_isolated(tmp_path)
    assert saved.read_bytes() == b"historical evidence"


@pytest.mark.parametrize("component,drift", [(0, 0.002), (4, 2e-6), (6, 2e-9)])
def test_first_analytic_endpoint_failure_is_retained_before_any_continuation(
    component: int, drift: float, synthetic_runtime: None,
) -> None:
    reference = physical_oracle.reference()
    calls: list[candidate.NativeRequest] = []
    ordinary = _fake_runner(reference, calls)
    def bad_endpoint(request: candidate.NativeRequest, budget: candidate.Budget) -> dict[str, object]:
        row = ordinary(request, budget)
        state = cast(list[float], row["end_state"])
        state[component] += drift
        return row
    budget = _budget()
    packet = candidate.produce(reference, budget, arc_runner=bad_endpoint)
    assert packet["status"] == "failed" and len(calls) == 1
    paths = cast(dict[str, list[dict[str, object]]], packet["paths"])
    assert len(paths["forward"]) == 1 and paths["reverse"] == []
    retained = cast(list[float], paths["forward"][0]["end_state"])
    expected = cast(list[list[float]], reference["states"])[1]
    assert retained[component] > expected[component]
    counts = cast(dict[str, object], packet["counts"])
    assert counts["native_attempts"] == counts["contexts_created"] == counts["contexts_closed"] == 1
    assert budget.failed is True and packet["failure"] is not None


@pytest.mark.parametrize("name,counter", [
    ("/tmp/forbidden.BSP", "kernel_reads"),
    (b"/tmp/forbidden.tls", "kernel_reads"),
    ("/tmp/forbidden.tpc", "kernel_reads"),
    ("/tmp/forbidden.bpc", "kernel_reads"),
    ("/tmp/forbidden.bc", "kernel_reads"),
    ("/tmp/forbidden.tf", "kernel_reads"),
    ("/tmp/forbidden.ti", "kernel_reads"),
    ("/tmp/forbidden.tm", "kernel_reads"),
    ("/tmp/forbidden.tsc", "kernel_reads"),
    ("/project/docs/adr/experiments/retained.json", "real_archive_reads"),
    (r"C:\project\docs\adr\experiments\retained.json", "real_archive_reads"),
])
def test_source_guard_charges_forbidden_attempt_before_rejecting_without_read(
    name: str | bytes, counter: str,
) -> None:
    budget = _budget()
    with pytest.raises(candidate.ConformanceError, match="archive/kernel"):
        candidate._source_guard(budget, "open", (name, "r", 0))
    counts = budget.snapshot()
    assert counts[counter] == 1 and budget.failed is True
    assert counts["native_attempts"] == counts["provider_attempts"] == 0
    assert counts["spice_queries"] == 0
    with pytest.raises(candidate.ConformanceError):
        budget.check()
    budget.check_finalization()


@pytest.mark.parametrize("event,args", [
    ("open", ("/tmp/new-fixture.json", "r", 0)),
    ("open", ("/project/src/space_nav/trajectory.py", "r", 0)),
    ("open", (0, "r", 0)), ("open", ()),
    ("os.listdir", ("/tmp/forbidden.bsp",)),
])
def test_source_guard_leaves_ordinary_fixture_io_unmodified(
    event: str, args: tuple[object, ...],
) -> None:
    budget = _budget()
    candidate._source_guard(budget, event, args)
    assert budget.failed is False
    counts = budget.snapshot()
    assert all(counts[key] == 0 for key in ("spice_queries", "kernel_reads", "real_archive_reads"))


@pytest.mark.parametrize("name", ["get_body_state", "load_kernel"])
def test_spice_guard_counts_and_rejects_public_calls_before_fake_native_work(name: str) -> None:
    actual_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    def original(*args: object, **kwargs: object) -> object:
        actual_calls.append((args, kwargs))
        return "must never execute"
    fake_spice = SimpleNamespace(get_body_state=original, load_kernel=original, constant=42, _private=original)
    budget = _budget()
    candidate._guard_spice(budget, fake_spice)
    assert fake_spice.constant == 42 and fake_spice._private is original
    with pytest.raises(candidate.ConformanceError, match="SPICE"):
        getattr(fake_spice, name)("fabricated", epoch_s=0.0)
    assert actual_calls == [] and budget.failed is True
    counts = budget.snapshot()
    assert counts["spice_queries"] == 1
    assert counts["native_attempts"] == counts["provider_attempts"] == 0
    with pytest.raises(candidate.ConformanceError):
        budget.check()
