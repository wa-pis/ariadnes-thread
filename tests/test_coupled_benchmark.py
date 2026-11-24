"""Artificial ADR0248 candidate checks; no real ephemerides or native flow."""

from collections.abc import Callable
from copy import deepcopy
import math
from types import SimpleNamespace
import time
from typing import Any

import pytest

from space_nav import _coupled_benchmark as candidate
from space_nav._coupled_benchmark_oracle import reference


@pytest.fixture(scope="module")
def solved() -> dict[str, object]:
    return candidate.run(reference(), deadline=time.monotonic() + 210.0)


def test_perturbed_seed_recovers_unreset_synthetic_target(solved: dict[str, Any]) -> None:
    assert solved["status"] == "passed"
    assert solved["reference"] == reference()
    assert not candidate._closed(solved["initial_defects"])
    assert candidate._closed(solved["defects"])
    assert len(solved["controls"]) == 6
    assert len(solved["shooting_nodes"]) == 2
    for actual, expected in zip(solved["witness"]["states"], reference()["states"], strict=True):
        candidate._compare(actual, expected, 0.001, 1e-6, "witness")
    final = solved["recovered"]["states"][-1]
    target = reference()["states"][-1]
    assert math.dist(final[:3], target[:3]) <= 0.1
    assert math.dist(final[3:6], target[3:6]) <= 1e-5
    counts = solved["counts"]
    assert 1 < counts["residual_calls"] <= 400
    assert counts["synthetic_arc_attempts"] == 3 * counts["residual_calls"] + 6
    assert 0 < counts["rhs_attempts"] <= 1000000
    assert all(counts[key] == 0 for key in (
        "spice_queries", "kernel_reads", "real_archive_reads", "native_propagations",
    ))
    assert solved["solver"]["nfev"] <= 20
    assert counts["residual_calls"] > solved["solver"]["nfev"]


@pytest.mark.parametrize("name,limit", [
    ("residual_calls", 400), ("synthetic_arc_attempts", 1206), ("rhs_attempts", 1000000),
])
def test_budget_counts_last_attempt_and_stops_before_extra_work(name: str, limit: int) -> None:
    budget = candidate._Budget(10.0, clock=lambda: 0.0)
    setattr(budget, name, limit - 1)
    budget.charge(name)
    assert getattr(budget, name) == limit
    with pytest.raises(candidate.BenchmarkError, match="work limit"):
        budget.charge(name)
    assert getattr(budget, name) == limit


def test_deadline_and_backwards_clock() -> None:
    with pytest.raises(candidate.BenchmarkError, match="deadline"):
        candidate._Budget(1.0, clock=lambda: 1.0).check()
    ticks = iter([1.0, 0.9])
    budget = candidate._Budget(10.0, clock=lambda: next(ticks))
    budget.check()
    with pytest.raises(candidate.BenchmarkError, match="backwards"):
        budget.check()


@pytest.mark.parametrize("value", [True, "1", math.nan, math.inf, 10 ** 1000],
                         ids=["bool", "string", "nan", "infinity", "overflow"])
def test_nonfinite_boolean_and_nonnumeric_values_rejected(value: object) -> None:
    with pytest.raises(candidate.BenchmarkError, match="finite number"):
        candidate._number(value, "test")


@pytest.mark.parametrize("field,value", [
    ("gravity_m_s2", [0, 0, 0]), ("initial_mass_kg", True),
    ("thrust_n", math.nan), ("final_s", 9999),
])
def test_changed_fixture_rejected_before_any_propagation(field: str, value: object) -> None:
    packet = reference()
    packet["fixture"][field] = value
    with pytest.raises(candidate.BenchmarkError) as captured:
        candidate.run(packet, deadline=time.monotonic() + 210)
    assert captured.value.counts["synthetic_arc_attempts"] == 0
    assert captured.value.counts["rhs_attempts"] == 0


def test_reference_precision_and_configuration_size_guards() -> None:
    packet = reference()
    packet["precision_differences"]["position_m"] = 1.0001e-9
    with pytest.raises(candidate.BenchmarkError, match="precision agreement"):
        candidate._reference(packet)
    packet = reference()
    packet["padding"] = "x" * 65536
    with pytest.raises(candidate.BenchmarkError, match="64 KiB"):
        candidate._reference(packet)


def _problem(integrator: Callable[..., Any]) -> candidate._Problem:
    _, states = candidate._reference(reference())
    return candidate._Problem(candidate._Budget(time.monotonic() + 210), states, integrator)


def test_burn_endpoint_uses_burn_mode_and_coast_uses_no_thrust() -> None:
    observed: list[list[float]] = []

    def integrator(rhs: Callable[..., list[float]], span: tuple[float, float],
                   initial: list[float], **settings: object) -> SimpleNamespace:
        end_state = list(initial)
        if span[0] == 0:
            end_state[6] -= candidate._RATE * (span[1] - span[0])
        observed.append(rhs(span[1], end_state))
        assert settings["t_eval"] == [span[1]]
        return SimpleNamespace(success=True, t=[span[1]], y=[[value] for value in end_state])

    problem = _problem(integrator)
    burned = problem.arc(list(candidate._INITIAL), 0, 1000, (0, 0))
    problem.arc(burned, 1000, 9000, None)
    assert observed[0][4] == pytest.approx(0.1 + 1000 / burned[6], abs=1e-15)
    assert observed[0][6] == -candidate._RATE
    assert observed[1][3:7] == [0, 0.1, 0, 0]
    assert problem.budget.synthetic_arc_attempts == 2
    assert problem.budget.rhs_attempts == 2


@pytest.mark.parametrize("fault", ["failure", "epoch", "nonfinite", "mass"])
def test_bad_integrator_result_fails_without_retry(fault: str) -> None:
    def integrator(rhs: Callable[..., list[float]], span: tuple[float, float],
                   initial: list[float], **settings: object) -> SimpleNamespace:
        values = list(initial)
        values[6] -= candidate._RATE * (span[1] - span[0])
        if fault == "nonfinite":
            values[0] = math.nan
        if fault == "mass":
            values[6] += 2e-9
        return SimpleNamespace(success=fault != "failure",
                               t=[span[1] + (1 if fault == "epoch" else 0)],
                               y=[[value] for value in values])

    problem = _problem(integrator)
    with pytest.raises(candidate.BenchmarkError):
        problem.arc(list(candidate._INITIAL), 0, 1000, (0, 0))
    assert problem.budget.synthetic_arc_attempts == 1


def test_invalid_tnw_is_counted_and_stops() -> None:
    def integrator(rhs: Callable[..., list[float]], span: tuple[float, float],
                   initial: list[float], **settings: object) -> None:
        radial = list(initial)
        radial[3:6] = [1000, 0, 0]
        rhs(span[0], radial)
        pytest.fail("degenerate TNW was accepted")

    problem = _problem(integrator)
    with pytest.raises(candidate.BenchmarkError, match="TNW"):
        problem.arc(list(candidate._INITIAL), 0, 1000, (0, 0))
    assert problem.budget.rhs_attempts == 1


def test_residual_checks_bounds_before_launch_and_counts_failure() -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("invalid controls reached integration")

    problem = _problem(forbidden)
    values = [0, 0, 499, 0, 0, 1000] + problem.states[1][:6] + problem.states[2][:6]
    with pytest.raises(candidate.BenchmarkError, match="bounds"):
        problem.residual(values)
    assert problem.budget.residual_calls == 1
    assert problem.budget.synthetic_arc_attempts == 0


def test_solver_cached_fun_cannot_hide_actual_defect(monkeypatch: pytest.MonkeyPatch,
                                                    solved: dict[str, Any]) -> None:
    import scipy.optimize

    values = solved["controls"] + solved["shooting_nodes"][0] + solved["shooting_nodes"][1]
    values = deepcopy(values)
    values[6] += 1.0

    def dishonest_solver(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(x=values, fun=[0.0] * 18, status=1, success=True,
                               message="cached zeros", nfev=1, njev=0)

    monkeypatch.setattr(scipy.optimize, "least_squares", dishonest_solver)
    with pytest.raises(candidate.BenchmarkError, match="shooting defects") as captured:
        candidate.run(reference(), deadline=time.monotonic() + 210)
    assert captured.value.counts["residual_calls"] == 2
    assert captured.value.counts["synthetic_arc_attempts"] == 9
