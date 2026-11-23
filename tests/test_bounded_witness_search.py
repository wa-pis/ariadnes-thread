"""Qualify the ADR0240 proposer with fabricated points and the pinned solver."""

from collections.abc import Callable
from copy import deepcopy
from fractions import Fraction
import math
from pathlib import Path
from runpy import run_path
from types import SimpleNamespace
from typing import Any

import pytest

type Row = dict[str, Any]
ART = Path(__file__).resolve().parents[1] / "docs/adr/experiments"


@pytest.fixture(scope="module")
def proposer() -> Row:
    return run_path(str(ART / "0241-bounded-search.py"))


def point(phase: float) -> Row:
    return dict(phase_word=phase.hex(), phase_ratio=list(phase.as_integer_ratio()),
                branches={sign: dict(reason=None) for sign in ("positive", "negative")},
                pairs=[dict(roots=["positive", sign], reason="commanded-dry-floor",
                            total_delta_v_m_s=7000.0+(phase-151.2)**2)
                       for sign in ("positive", "negative")], eligible=[], unresolved=False)


def anchor(row: Row, degree: int) -> None:
    assert row == point(float(degree))


def solver(phases: list[float], *, success: bool = True) -> Callable[..., SimpleNamespace]:
    def minimize(objective: Callable[[float], float], **kwargs: Any) -> SimpleNamespace:
        assert kwargs == dict(method="bounded", bounds=(150.0, 152.0),
                              options=dict(xatol=1e-5, maxiter=62, disp=0))
        values = [(objective(phase), phase) for phase in phases]
        cost, phase = min(values)
        return SimpleNamespace(x=phase, fun=cost, success=success, nfev=len(phases),
                               nit=len(phases), status=0 if success else 1, message="fabricated")
    return minimize


def test_full_129_slots_charge_duplicates_and_final_repeats(proposer: Row) -> None:
    visits = []

    def counted(phase: float) -> Row:
        visits.append(phase)
        return point(phase)

    result = proposer["search"](counted, anchor, minimize=solver([150.125]*62, success=False))
    assert result["status"] == proposer["UNKNOWN"]
    assert result["disposition"] == "inconclusive" and result["witness"] is None
    assert result["counters"] == dict(anchors=3, objective=dict(positive=62, negative=62),
                                       finals=2, phases=129, root_slots=258, pair_slots=258,
                                       blocked_attempts=0)
    assert len(result["phases"]) == len(visits) == 129
    assert visits[:3] == [150.0, 151.0, 152.0]
    assert sum(row["stage"] == "final" for row in result["phases"]) == 2
    assert all(row["compared"] for row in result["phases"][:3])
    assert all(row["status"] == "completed" and row["result"]["success"] is False
               for row in result["searches"].values())


def test_callback_cap_stops_before_extra_scientific_work(proposer: Row) -> None:
    result = proposer["search"](point, anchor, minimize=solver([150.25]*63))
    assert result["disposition"] == "invalid"
    assert result["counters"]["objective"] == dict(positive=62, negative=0)
    assert result["counters"]["phases"] == 65
    assert result["counters"]["blocked_attempts"] == 1
    assert result["blocked_attempt"] == dict(stage="objective", sign="positive")


def test_all_three_frozen_anchors_precede_the_first_scalar_call(proposer: Row) -> None:
    order = []

    def compare(row: Row, degree: int) -> None:
        anchor(row, degree)
        order.append(degree)

    def minimize(objective: Callable[[float], float], **kwargs: Any) -> SimpleNamespace:
        assert order == [150, 151, 152]
        return solver([150.2])(objective, **kwargs)

    result = proposer["search"](point, compare, minimize=minimize)
    assert result["disposition"] == "inconclusive"


@pytest.mark.parametrize("failure", ["eligible", "mismatch"])
def test_anchor_refusal_drift_is_invalid_without_search(proposer: Row, failure: str) -> None:
    def changed(phase: float) -> Row:
        row = point(phase)
        if failure == "eligible":
            row["eligible"] = ["positive"]
            row["pairs"][0]["reason"] = None
        return row

    def compare(row: Row, degree: int) -> None:
        if failure == "mismatch":
            raise ValueError("frozen anchor mismatch")

    result = proposer["search"](changed, compare, minimize=lambda *args, **kwargs: pytest.fail("search"))
    assert result["disposition"] == "invalid"
    assert result["counters"]["objective"] == dict(positive=0, negative=0)


@pytest.mark.parametrize("refusal", ["commanded-dry-floor", "effective-dry-floor",
                                    "event-order", "historically-rejected"])
def test_ordinary_pair_refusals_keep_finite_objective(proposer: Row, refusal: str) -> None:
    def refused(phase: float) -> Row:
        row = point(phase)
        if phase not in (150.0, 151.0, 152.0):
            for pair in row["pairs"]:
                pair["reason"] = refusal
        return row

    result = proposer["search"](refused, anchor, minimize=solver([150.123]))
    assert result["disposition"] == "inconclusive"
    assert all(row["objective_word"] is not None for row in result["phases"] if row["stage"] == "objective")


@pytest.mark.parametrize("reason", ["guard", "degenerate"])
def test_active_guard_aborts_only_its_search(proposer: Row, reason: str) -> None:
    def guarded(phase: float) -> Row:
        row = point(phase)
        if phase not in (150.0, 151.0, 152.0):
            row["branches"]["positive"] = dict(reason=reason)
            row["pairs"] = row["pairs"][1:]
        return row

    result = proposer["search"](guarded, anchor, minimize=solver([150.125, 151.125]))
    assert result["disposition"] == "inconclusive"
    assert result["searches"]["positive"]["status"] == "objective-unavailable"
    assert result["searches"]["positive"]["reason"] == reason
    assert result["searches"]["negative"]["status"] == "completed"
    assert result["counters"]["objective"] == dict(positive=1, negative=2)
    assert result["counters"]["root_slots"] == result["counters"]["pair_slots"] == 14


def test_other_sign_witness_precedes_active_guard_and_optimizer_success(proposer: Row) -> None:
    def admitted(phase: float) -> Row:
        row = point(phase)
        if phase not in (150.0, 151.0, 152.0):
            row["branches"]["positive"]["reason"] = "guard"
            row["pairs"] = row["pairs"][1:]
            row["pairs"][0]["reason"] = None
            row["eligible"] = ["negative"]
        return row

    result = proposer["search"](admitted, anchor, minimize=solver([150.123], success=False))
    assert result["status"] == proposer["VERIFIED"]
    assert result["witness"]["sign"] == "negative"
    assert result["counters"]["objective"] == dict(positive=1, negative=0)
    assert result["counters"]["finals"] == 0
    assert result["phases"][-1]["objective_word"] is None


@pytest.mark.parametrize("fault", ["unresolved", "missing-root", "missing-pair", "nonfinite",
                                  "independent-mass", "phase-drift"])
def test_bad_inventory_is_terminal_even_with_other_sign_eligible(proposer: Row, fault: str) -> None:
    def broken(phase: float) -> Row:
        row = point(phase)
        if phase in (150.0, 151.0, 152.0):
            return row
        row["eligible"] = ["negative"]
        row["pairs"][1]["reason"] = None
        if fault == "unresolved":
            row["unresolved"] = True
        elif fault == "missing-root":
            del row["branches"]["positive"]
        elif fault == "missing-pair":
            row["pairs"].pop(0)
        elif fault == "nonfinite":
            row["pairs"][0]["total_delta_v_m_s"] = math.inf
        elif fault == "independent-mass":
            row["pairs"][0]["reason"] = "independent-mass"
        else:
            row["phase_word"] = (phase+0.1).hex()
        return row

    result = proposer["search"](broken, anchor, minimize=solver([150.123]))
    assert result["status"] == proposer["UNKNOWN"] and result["disposition"] == "invalid"
    assert result["counters"]["phases"] == 4 and result["counters"]["root_slots"] == 8
    assert result["phases"][-1]["error"]


@pytest.mark.parametrize("phase", [True, math.nan, math.inf, 149.99, 152.01, "151.2",
                                  Fraction(1501, 10)])
def test_invalid_or_value_losing_callback_phase_is_precharged(proposer: Row, phase: object) -> None:
    def minimize(objective: Callable[[object], float], **kwargs: Any) -> None:
        objective(phase)

    result = proposer["search"](point, anchor, minimize=minimize)
    assert result["disposition"] == "invalid"
    assert result["counters"]["objective"]["positive"] == 1
    assert result["phases"][-1]["point"] is None


def test_arbitrary_ratio_keeps_exact_words_without_grid_snap(proposer: Row) -> None:
    phase = math.nextafter(151.125, 152.0)
    result = proposer["search"](point, anchor, minimize=solver([phase]))
    row = result["phases"][3]
    assert row["phase_word"] == phase.hex() and row["phase_ratio"] == list(phase.as_integer_ratio())
    assert row["phase_ratio"][1] > 64


def test_result_must_bind_recorded_callback_and_cost(proposer: Row) -> None:
    def minimize(objective: Callable[[float], float], **kwargs: Any) -> SimpleNamespace:
        result = solver([150.25])(objective, **kwargs)
        result.x = 150.5
        return result

    result = proposer["search"](point, anchor, minimize=minimize)
    assert result["disposition"] == "invalid" and result["counters"]["finals"] == 0


def test_deadline_and_point_errors_keep_charged_partial_row(proposer: Row) -> None:
    def broken(phase: float) -> Row:
        if phase == 150.25:
            raise ValueError("fabricated point failure")
        return point(phase)

    result = proposer["search"](broken, anchor, minimize=solver([150.25]))
    assert result["disposition"] == "invalid" and result["phases"][-1]["point"] is None
    assert result["counters"]["root_slots"] == 8

    def expired() -> None:
        raise TimeoutError("deadline")

    result = proposer["search"](point, anchor, minimize=solver([150.25]), check=expired)
    assert result["counters"]["phases"] == 1 and result["phases"][0]["error"]


def test_transcript_does_not_alias_adapter_memory(proposer: Row) -> None:
    shared = point(150.25)

    def reused(phase: float) -> Row:
        shared.clear()
        shared.update(point(phase))
        return shared

    result = proposer["search"](reused, anchor, minimize=solver([150.25, 151.25]))
    before = deepcopy(result)
    shared.clear()
    assert result == before


def test_actual_pinned_scipy_finds_unimodal_synthetic_witness(proposer: Row) -> None:
    def admitted(phase: float) -> Row:
        row = point(phase)
        if abs(phase-151.2) < 1e-6:
            row["pairs"][0]["reason"] = None
            row["eligible"] = ["positive"]
        return row

    result = proposer["search"](admitted, anchor)
    assert result["status"] == proposer["VERIFIED"]
    assert abs(float.fromhex(result["witness"]["phase_word"])-151.2) < 1e-6
    assert result["counters"]["objective"]["negative"] == 0


def test_actual_pinned_scipy_missed_multimodal_witness_stays_inconclusive(proposer: Row) -> None:
    def missed(phase: float) -> Row:
        row = point(phase)
        if phase not in (150.0, 151.0, 152.0):
            for pair in row["pairs"]:
                pair["total_delta_v_m_s"] = min(7000.0+(phase-151.2)**2,
                                                6000.0+1e12*(phase-150.01)**2)
            if abs(phase-150.01) < 1e-6:
                row["pairs"][0]["reason"] = None
                row["eligible"] = ["positive"]
        return row

    assert missed(150.01)["eligible"]
    result = proposer["search"](missed, anchor)
    assert result["status"] == proposer["UNKNOWN"] and result["disposition"] == "inconclusive"
    assert all(row["status"] == "completed" and row["result"]["success"] is True
               for row in result["searches"].values())
    assert result["counters"]["phases"] <= 129


@pytest.mark.parametrize("other_witness", [False, True])
def test_actual_pinned_scipy_guard_and_admitted_other_root(proposer: Row, other_witness: bool) -> None:
    def guarded(phase: float) -> Row:
        row = point(phase)
        if phase not in (150.0, 151.0, 152.0):
            row["branches"]["positive"]["reason"] = "guard"
            row["pairs"] = row["pairs"][1:]
            if other_witness:
                row["pairs"][0]["reason"] = None
                row["eligible"] = ["negative"]
        return row

    result = proposer["search"](guarded, anchor)
    if other_witness:
        assert result["status"] == proposer["VERIFIED"] and result["witness"]["sign"] == "negative"
        assert result["counters"]["objective"] == dict(positive=1, negative=0)
    else:
        assert result["disposition"] == "inconclusive"
        assert result["searches"]["positive"]["status"] == "objective-unavailable"
        assert result["searches"]["negative"]["status"] == "completed"


def test_optimizer_cannot_swallow_guard_and_continue(proposer: Row) -> None:
    def guarded(phase: float) -> Row:
        row = point(phase)
        if phase not in (150.0, 151.0, 152.0):
            row["branches"]["positive"]["reason"] = "guard"
            row["pairs"] = row["pairs"][1:]
        return row

    def minimize(objective: Callable[[float], float], **kwargs: Any) -> None:
        try:
            objective(150.25)
        except proposer["_ObjectiveUnavailable"]:
            objective(150.5)

    result = proposer["search"](guarded, anchor, minimize=minimize)
    assert result["disposition"] == "invalid"
    assert result["counters"]["objective"] == dict(positive=1, negative=0)
