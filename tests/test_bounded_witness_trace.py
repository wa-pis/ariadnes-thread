"""Exercise independent trace validation with fabricated complete and partial rows."""

import ast
from copy import deepcopy
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

type Row = dict[str, Any]
ART = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
SIGNS = ("positive", "negative")


@pytest.fixture(scope="module")
def auditor() -> Row:
    return run_path(str(ART / "0241-trace-audit.py"))


def _row(stage: str, sign: str | None, phase: float) -> Row:
    point = dict(phase_word=phase.hex(), phase_ratio=list(phase.as_integer_ratio()),
                 branches={s: dict(reason=None) for s in SIGNS},
                 pairs=[dict(roots=["positive", s], reason="commanded-dry-floor",
                             total_delta_v_m_s=7000.0) for s in SIGNS], eligible=[], unresolved=False)
    return dict(stage=stage, sign=sign, phase_word=point["phase_word"], phase_ratio=point["phase_ratio"],
                point=point, objective_word=(7000.0).hex() if stage == "objective" else None,
                compared=stage == "anchor", error=None)


def _count(report: Row) -> None:
    rows = report["phases"]
    report["counters"] = dict(anchors=sum(row["stage"] == "anchor" for row in rows),
                              objective={s: sum(row["stage"] == "objective" and row["sign"] == s
                                                for row in rows) for s in SIGNS},
                              finals=sum(row["stage"] == "final" for row in rows), phases=len(rows),
                              root_slots=2*len(rows), pair_slots=2*len(rows),
                              blocked_attempts=int(report["blocked_attempt"] is not None))


def _report(callbacks: int = 1) -> Row:
    report = dict(schema="ariadna-bounded-witness-search-v1", status="inconclusive/invalid",
                  disposition="inconclusive", reason="no-verified-witness", witness=None,
                  blocked_attempt=None, settings=dict(method="bounded", bounds=[150.0, 152.0],
                  options=dict(xatol=1e-5, maxiter=62, disp=0)), searches={},
                  phases=[_row("anchor", None, float(n)) for n in (150, 151, 152)])
    for sign in SIGNS:
        report["phases"].extend(_row("objective", sign, 150.25) for _ in range(callbacks))
        report["phases"].append(_row("final", sign, 150.25))
        report["searches"][sign] = dict(status="completed", callbacks=callbacks, reason=None,
            result=dict(x_word=(150.25).hex(), x_ratio=[601, 4], fun_word=(7000.0).hex(),
                        success=True, nfev=callbacks, nit=callbacks, status=0, message="fabricated"))
    _count(report)
    return report


def test_full_129_duplicate_phases_are_counted_without_optimizer(auditor: Row) -> None:
    report = _report(62)
    report["searches"]["positive"]["result"].update(success=False, status=1)
    verdict = auditor["verify"](report)
    assert verdict == dict(verified=True, counters=dict(anchors=3, objective=dict(positive=62, negative=62),
                           finals=2, phases=129, root_slots=258, pair_slots=258, blocked_attempts=0))


@pytest.mark.parametrize("fault", ["settings", "unavailable-cost", "duplicate-positive-final",
    "result-metadata", "negative-first", "objective-after-final", "callback-count", "nfev", "nit", "status",
    "success", "new-result-x", "ratio", "nan", "missing-root", "missing-pair", "unresolved",
    "counter-bool", "objective-cost", "callback-after-guard", "false-refusal", "false-witness"])
def test_complete_trace_tampering_is_rejected(auditor: Row, fault: str) -> None:
    report = _report()
    positive = report["searches"]["positive"]
    if fault == "settings":
        report["settings"] = dict(method="brent", bounds=[149.0, 153.0], options=dict(maxiter=1000))
    elif fault == "unavailable-cost":
        report["phases"][3]["objective_word"] = None
        positive.update(status="objective-unavailable", reason="guard")
    elif fault == "duplicate-positive-final":
        report["phases"][-1]["sign"] = "positive"
    elif fault == "result-metadata":
        positive["result"].update(nfev=1000, fun_word=(0.0).hex())
    elif fault == "negative-first":
        for row in report["phases"][3:]:
            row["sign"] = "negative" if row["sign"] == "positive" else "positive"
    elif fault == "objective-after-final":
        report["phases"][3:5] = reversed(report["phases"][3:5])
    elif fault == "callback-count":
        positive["callbacks"] = 2
    elif fault in ("nfev", "nit", "status", "success"):
        positive["result"][fault] = dict(nfev=1000, nit=9, status=7, success=False)[fault]
    elif fault == "new-result-x":
        positive["result"]["x_word"] = (150.5).hex()
    elif fault == "ratio":
        report["phases"][3]["phase_ratio"] = [15025, 100]
    elif fault == "nan":
        report["phases"][3]["objective_word"] = "nan"
    elif fault == "missing-root":
        del report["phases"][3]["point"]["branches"]["negative"]
    elif fault == "missing-pair":
        report["phases"][3]["point"]["pairs"].pop()
    elif fault == "unresolved":
        report["phases"][3]["point"]["unresolved"] = True
    elif fault == "counter-bool":
        report["counters"]["objective"]["positive"] = True
    elif fault == "objective-cost":
        report["phases"][3]["objective_word"] = (1.0).hex()
    elif fault == "callback-after-guard":
        row = report["phases"][3]
        row["point"]["branches"]["positive"]["reason"] = "guard"
        row["point"]["pairs"].pop(0)
        row["objective_word"] = None
    elif fault == "false-refusal":
        report["status"] = "continuous-refusal"
    else:
        report.update(status="verified-analytical-witness", disposition="witness")
    with pytest.raises((ValueError, KeyError, TypeError)):
        auditor["verify"](report)


def test_guard_aborts_positive_and_negative_search_still_completes(auditor: Row) -> None:
    report = _report()
    row = report["phases"][3]
    row["point"]["branches"]["positive"]["reason"] = "guard"
    row["point"]["pairs"].pop(0)
    row["objective_word"] = None
    report["phases"].pop(4)
    report["searches"]["positive"].update(status="objective-unavailable", reason="guard", result=None)
    _count(report)
    assert auditor["verify"](report)["verified"] is True


def test_other_root_witness_stops_before_active_guard_or_optimizer_result(auditor: Row) -> None:
    report = _report()
    row = report["phases"][3]
    row["point"]["branches"]["positive"]["reason"] = "guard"
    row["point"]["pairs"].pop(0)
    row["point"]["pairs"][0]["reason"] = None
    row["point"]["eligible"] = ["negative"]
    row["objective_word"] = None
    report["phases"] = report["phases"][:4]
    report.update(status="verified-analytical-witness", disposition="witness", reason="point-gates-pass",
                  witness=dict(phase_index=3, phase_word=row["phase_word"], phase_ratio=row["phase_ratio"],
                               sign="negative", eligible=["negative"]))
    report["searches"]["positive"].update(status="witness", reason="point-gates-pass", result=None)
    report["searches"]["negative"].update(status="not-started", reason=None, result=None, callbacks=0)
    _count(report)
    assert auditor["verify"](report)["verified"] is True
    changed = deepcopy(report)
    changed["phases"].append(_row("objective", "negative", 151.25))
    changed["searches"]["negative"]["callbacks"] = 1
    _count(changed)
    with pytest.raises(ValueError, match="phase after witness"):
        auditor["verify"](changed)


@pytest.mark.parametrize("blocked", [False, True])
def test_partial_or_blocked_attempt_never_receives_complete_verification(auditor: Row, blocked: bool) -> None:
    report = _report(62 if blocked else 1)
    report.update(disposition="invalid", reason="fabricated failure")
    report["phases"] = report["phases"][:65 if blocked else 1]
    if blocked:
        report["blocked_attempt"] = dict(stage="objective", sign="positive")
        report["searches"]["positive"].update(status="invalid", reason="cap", result=None)
    else:
        report["phases"][0].update(point=None, error="ValueError: point failure", compared=False)
        report["searches"]["positive"]["callbacks"] = 0
    report["searches"]["negative"]["callbacks"] = 0
    _count(report)
    assert auditor["verify"](report) == dict(verified=False, counters=report["counters"])


def test_trace_auditor_has_only_stdlib_imports_and_no_proposer_dispatch() -> None:
    tree = ast.parse((ART / "0241-trace-audit.py").read_text())
    imported = {node.module if isinstance(node, ast.ImportFrom) else alias.name
                for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names}
    assert imported == {"json", "math", "typing"}


def test_callback_63_is_rejected_even_below_the_total_phase_ceiling(auditor: Row) -> None:
    report = _report(62)
    report["phases"] = report["phases"][:65] + [_row("objective", "positive", 150.25)]
    report["searches"]["positive"]["callbacks"] = 63
    report["searches"]["negative"]["callbacks"] = 0
    _count(report)
    with pytest.raises(ValueError, match="signed callback ceiling"):
        auditor["verify"](report)
