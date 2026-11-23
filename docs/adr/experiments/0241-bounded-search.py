"""Propose an analytical witness at recorded binary64 phases; never prove refusal."""

from collections.abc import Callable, Mapping
import json
import math
from numbers import Real
from typing import Any

type Row = dict[str, Any]

SIGNS = ("positive", "negative")
SETTINGS = dict(method="bounded", bounds=[150.0, 152.0],
                options=dict(xatol=1e-5, maxiter=62, disp=0))
CAPS = dict(anchors=3, callbacks_per_sign=62, finals=2, phases=129,
            root_slots=258, pair_slots=258)
VERIFIED = "verified-analytical-witness"
UNKNOWN = "inconclusive/invalid"
_ERRORS = (ValueError, TypeError, ArithmeticError, KeyError, AttributeError,
           RuntimeError, TimeoutError, ImportError)


class _Halt(Exception):
    """Leave the entire attempt without another point evaluation."""


class _ObjectiveUnavailable(Exception):
    """Leave only the active signed scalar call."""


def _check() -> None:
    pass


def _number(raw: object) -> float:
    if isinstance(raw, bool) or not isinstance(raw, Real):
        raise ValueError("binary64 scalar required")
    value = float(raw)
    if not math.isfinite(value) or raw != value:
        raise ValueError("nonfinite or value-changing scalar conversion")
    return value


def _phase(raw: object) -> float:
    value = _number(raw)
    if not 150.0 <= value <= 152.0:
        raise ValueError("phase outside [150, 152] degrees")
    return value


def _inventory(row: Row, phase: float) -> dict[str, Row]:
    if row.get("unresolved") is not False:
        raise ValueError("unresolved point classification")
    if row.get("phase_word", phase.hex()) != phase.hex() or row.get(
        "phase_ratio", list(phase.as_integer_ratio())
    ) != list(phase.as_integer_ratio()):
        raise ValueError("point phase identity mismatch")
    branches, pairs, eligible = (row[name] for name in ("branches", "pairs", "eligible"))
    if not isinstance(branches, dict) or set(branches) != set(SIGNS):
        raise ValueError("both signed root slots required")
    available = []
    for sign in SIGNS:
        reason = branches[sign]["reason"]
        if reason not in (None, "guard", "degenerate"):
            raise ValueError("unresolved signed root classification")
        if reason is None:
            available.append(sign)
    if not isinstance(pairs, list) or [pair["roots"] for pair in pairs] != [
        ["positive", sign] for sign in available
    ]:
        raise ValueError("signed pair inventory mismatch")
    costs = {}
    for sign, pair in zip(available, pairs, strict=True):
        if _number(pair["total_delta_v_m_s"]) < 0:
            raise ValueError("negative analytical cost")
        if pair["reason"] == "independent-mass" or not (
            pair["reason"] is None or isinstance(pair["reason"], str)
        ):
            raise ValueError("independent pair disagreement")
        costs[sign] = pair
    if not isinstance(eligible, list) or eligible != [sign for sign in SIGNS if sign in eligible]:
        raise ValueError("eligible signed inventory mismatch")
    if any(sign not in costs or costs[sign]["reason"] is not None for sign in eligible):
        raise ValueError("eligible pair disposition mismatch")
    return costs


def _solver() -> Callable[..., Any]:
    # Imports occur inside the caller's startup-inclusive clock and runtime profile.
    import numpy
    import scipy
    from scipy.optimize import minimize_scalar

    if (numpy.__version__, scipy.__version__) != ("1.26.4", "1.17.1"):
        raise ValueError("pinned NumPy/SciPy versions required")
    return minimize_scalar


def _result(raw: Any, rows: list[Row], sign: str, callbacks: int) -> Row:
    def field(name: str) -> Any:
        return raw[name] if isinstance(raw, Mapping) else getattr(raw, name)

    phase, cost = _phase(field("x")), _number(field("fun"))
    matching = [row for row in rows if row["stage"] == "objective" and row["sign"] == sign
                and row["phase_word"] == phase.hex() and row["objective_word"] == cost.hex()]
    if not matching:
        raise ValueError("result.x/fun was not a recorded objective result")
    success, nfev, nit, status, message = (field(name) for name in (
        "success", "nfev", "nit", "status", "message"
    ))
    if (type(success) is not bool or type(nfev) is not int or nfev != callbacks
            or type(nit) is not int or nit < 0 or type(status) is not int
            or not isinstance(message, str)):
        raise ValueError("optimizer result metadata mismatch")
    return dict(x_word=phase.hex(), x_ratio=list(phase.as_integer_ratio()),
                fun_word=cost.hex(), success=success, nfev=nfev, nit=nit,
                status=status, message=message)


def search(point: Callable[[float], Row], compare_anchor: Callable[[Row, int], None], *,
           minimize: Callable[..., Any] | None = None, check: Callable[[], None] = _check) -> Row:
    """Search positive then negative once, retaining every charged point and disposition.

    ``point`` performs both binary64 and independent point checks. The frozen
    comparator authenticates each anchor. This function has no scientific inputs,
    file access, durable readback, or authority to select executable commands.
    """
    counts = dict(anchors=0, objective={sign: 0 for sign in SIGNS}, finals=0,
                  phases=0, root_slots=0, pair_slots=0, blocked_attempts=0)
    report: Row = dict(schema="ariadna-bounded-witness-search-v1", status=UNKNOWN,
                       disposition="inconclusive", reason="no-verified-witness",
                       settings=json.loads(json.dumps(SETTINGS)), counters=counts,
                       phases=[], searches={sign: dict(status="not-started", callbacks=0,
                                                      reason=None, result=None) for sign in SIGNS},
                       witness=None, blocked_attempt=None)

    def fail(reason: str) -> None:
        report.update(status=UNKNOWN, disposition="invalid", reason=reason, witness=None)
        raise _Halt

    def evaluate(raw: object, stage: str, sign: str | None) -> tuple[Row, dict[str, Row]]:
        if (counts["phases"] >= CAPS["phases"] or stage == "final" and counts["finals"] >= 2
                or stage == "objective" and counts["objective"][sign] >= 62):
            counts["blocked_attempts"] += 1
            report["blocked_attempt"] = dict(stage=stage, sign=sign)
            fail("phase or signed callback ceiling")
        counts["phases"] += 1
        counts["root_slots"] += 2
        counts["pair_slots"] += 2
        if stage == "objective":
            counts["objective"][sign] += 1
            report["searches"][sign]["callbacks"] += 1
        else:
            counts["anchors" if stage == "anchor" else "finals"] += 1
        row: Row = dict(stage=stage, sign=sign, phase_word=None, phase_ratio=None,
                       point=None, objective_word=None, compared=False, error=None)
        report["phases"].append(row)
        try:
            check()
            phase = _phase(raw)
            row.update(phase_word=phase.hex(), phase_ratio=list(phase.as_integer_ratio()))
            row["point"] = json.loads(json.dumps(point(phase), allow_nan=False))
            check()
            costs = _inventory(row["point"], phase)
            return row, costs
        except _ERRORS as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            fail(row["error"])
        raise AssertionError("unreachable")

    def witness(row: Row) -> None:
        eligible = row["point"]["eligible"]
        if eligible:
            report.update(status=VERIFIED, disposition="witness", reason="point-gates-pass",
                          witness=dict(phase_index=len(report["phases"])-1,
                                       phase_word=row["phase_word"], phase_ratio=row["phase_ratio"],
                                       sign=eligible[0], eligible=eligible))
            raise _Halt

    try:
        for degree in (150, 151, 152):
            row, _ = evaluate(float(degree), "anchor", None)
            compare_anchor(row["point"], degree)
            if row["point"]["eligible"]:
                fail("eligible anchor violates frozen refusal parity")
            row["compared"] = True
            check()
        solver = _solver() if minimize is None else minimize
        for sign in SIGNS:
            current = report["searches"][sign]
            current["status"] = "running"
            unavailable = False

            def objective(raw: object) -> float:
                nonlocal unavailable
                if unavailable:
                    fail("optimizer continued after objective-unavailable")
                row, costs = evaluate(raw, "objective", sign)
                witness(row)
                if sign not in costs:
                    unavailable = True
                    current.update(status="objective-unavailable", reason=row["point"]["branches"][sign]["reason"])
                    raise _ObjectiveUnavailable
                cost = _number(costs[sign]["total_delta_v_m_s"])
                row["objective_word"] = cost.hex()
                return cost

            try:
                check()
                result = solver(objective, method="bounded", bounds=(150.0, 152.0),
                                options=dict(xatol=1e-5, maxiter=62, disp=0))
                check()
                if unavailable:
                    fail("optimizer swallowed objective-unavailable")
                current["result"] = _result(result, report["phases"], sign, current["callbacks"])
                current["status"] = "completed"
            except _ObjectiveUnavailable:
                continue
            row, _ = evaluate(float.fromhex(current["result"]["x_word"]), "final", sign)
            witness(row)
        check()
    except _Halt:
        pass
    except _ERRORS as exc:
        report.update(status=UNKNOWN, disposition="invalid", reason=f"{type(exc).__name__}: {exc}", witness=None)
    for current in report["searches"].values():
        if current["status"] == "running":
            current["status"] = "witness" if report["status"] == VERIFIED else "invalid"
            current["reason"] = report["reason"]
    return report
