"""Independently validate a bounded-search transcript without calling its proposer."""

import json
import math
from typing import Any

type Row = dict[str, Any]
SIGNS = ("positive", "negative")
SETTINGS = dict(method="bounded", bounds=[150.0, 152.0],
                options=dict(xatol=1e-5, maxiter=62, disp=0))


def _need(ok: object, reason: str) -> None:
    if not ok:
        raise ValueError("bounded trace: " + reason)


def _word(raw: object, *, phase: bool = False) -> float:
    _need(type(raw) is str, "binary64 word required")
    value = float.fromhex(raw)
    _need(math.isfinite(value) and value.hex() == raw and
          (150.0 <= value <= 152.0 if phase else value >= 0), "canonical finite word")
    return value


def _ratio(raw: object, phase: float) -> None:
    _need(type(raw) is list and len(raw) == 2 and all(type(x) is int for x in raw)
          and raw == list(phase.as_integer_ratio()), "exact degree ratio")


def _point(row: Row) -> dict[str, Row]:
    point = row["point"]
    _need(type(point) is dict and point["phase_word"] == row["phase_word"]
          and point["phase_ratio"] == row["phase_ratio"]
          and point["unresolved"] is False, "point phase or unresolved classification")
    _ratio(point["phase_ratio"], float.fromhex(row["phase_word"]))
    branches, pairs, eligible = (point[name] for name in ("branches", "pairs", "eligible"))
    _need(type(branches) is dict and set(branches) == set(SIGNS), "signed root inventory")
    _need(all(branches[sign]["reason"] in (None, "guard", "degenerate") for sign in SIGNS),
          "signed root disposition")
    available = [sign for sign in SIGNS if branches[sign]["reason"] is None]
    _need(type(pairs) is list and [pair["roots"] for pair in pairs] ==
          [["positive", sign] for sign in available], "signed pair inventory")
    costs = dict(zip(available, pairs, strict=True))
    for pair in pairs:
        cost = pair["total_delta_v_m_s"]
        _need(type(cost) in (float, int) and math.isfinite(cost) and cost >= 0
              and cost == float(cost), "finite analytical cost")
        _need(pair["reason"] != "independent-mass" and
              (pair["reason"] is None or type(pair["reason"]) is str), "pair disposition")
    _need(type(eligible) is list and eligible == [sign for sign in SIGNS if sign in eligible]
          and all(sign in costs and costs[sign]["reason"] is None for sign in eligible),
          "eligible inventory")
    return costs


def verify(result: Row) -> Row:
    """Return counters and whether a complete trace can receive numerical audit.

    Invalid or partial attempts remain unverified. This is structural validation;
    independent numerical verification must still check every recorded point.
    """
    _need(result["schema"] == "ariadna-bounded-witness-search-v1", "schema")
    _need(json.dumps(result["settings"], sort_keys=True, allow_nan=False) ==
          json.dumps(SETTINGS, sort_keys=True), "fixed scalar settings")
    rows, searches = result["phases"], result["searches"]
    _need(type(rows) is list and 0 <= len(rows) <= 129, "phase ceiling")
    _need(type(searches) is dict and set(searches) == set(SIGNS), "search inventory")
    _need(result["disposition"] in ("invalid", "inconclusive", "witness"), "terminal disposition")
    partial = result["disposition"] == "invalid" or len(rows) < 3
    counts = dict(anchors=0, objective=dict(positive=0, negative=0), finals=0,
                  phases=len(rows), root_slots=2*len(rows), pair_slots=2*len(rows), blocked_attempts=0)
    grouped: dict[str, list[Row]] = {sign: [] for sign in SIGNS}
    active = "positive"
    for index, row in enumerate(rows):
        stage, sign = row["stage"], row["sign"]
        _need(stage in ("anchor", "objective", "final"), "phase stage")
        if stage == "anchor":
            _need(index < 3 and sign is None, "anchor order")
            counts["anchors"] += 1
        else:
            _need(index >= 3 and sign in SIGNS, "phase sign")
            grouped[sign].append(row)
            if stage == "objective":
                counts["objective"][sign] += 1
                _need(counts["objective"][sign] <= 62, "signed callback ceiling")
            else:
                counts["finals"] += 1
                _need(counts["finals"] <= 2, "final ceiling")
        if row["phase_word"] is None:
            _need(row["phase_ratio"] is None and row["point"] is None, "partial phase")
            partial = True
        else:
            _ratio(row["phase_ratio"], _word(row["phase_word"], phase=True))
        partial |= row["point"] is None or row["error"] is not None
    blocked = result["blocked_attempt"]
    if blocked is not None:
        partial = True
        counts["blocked_attempts"] = 1
        _need(type(blocked) is dict and blocked["stage"] == "objective" and
              blocked["sign"] in SIGNS and counts["objective"][blocked["sign"]] == 62,
              "blocked callback binding")
    _need(json.dumps(result["counters"], sort_keys=True, allow_nan=False) ==
          json.dumps(counts, sort_keys=True) and all(type(searches[s]["callbacks"]) is int and
          searches[s]["callbacks"] == counts["objective"][s] for s in SIGNS), "work accounting")
    if partial:
        _need(result["status"] == "inconclusive/invalid" and result["disposition"] == "invalid"
              and result["witness"] is None, "partial attempt cannot admit a witness")
        return dict(verified=False, counters=counts)
    witness = None
    for index, row in enumerate(rows):
        _need(witness is None, "phase after witness")
        stage, sign = row["stage"], row["sign"]
        costs = _point(row)
        eligible = row["point"]["eligible"]
        if stage == "anchor":
            _need(row["phase_word"] == float(150+index).hex() and row["compared"] is True
                  and not eligible and row["objective_word"] is None, "frozen anchor parity")
            continue
        _need(row["compared"] is False, "search phase marked as anchor")
        if sign != active:
            _need(active == "positive" and sign == "negative" and grouped["positive"]
                  and searches["positive"]["status"] in ("completed", "objective-unavailable"), "signed search order")
            active = sign
        if eligible:
            witness = dict(phase_index=index, phase_word=row["phase_word"], phase_ratio=row["phase_ratio"],
                           sign=eligible[0], eligible=eligible)
        if stage == "objective" and not eligible and sign in costs:
            _word(row["objective_word"])
            _need(row["objective_word"] == float(costs[sign]["total_delta_v_m_s"]).hex(), "active objective cost")
        else:
            _need(row["objective_word"] is None, "unavailable or terminal objective")
    for sign in SIGNS:
        saved, events = searches[sign], grouped[sign]
        objectives = [row for row in events if row["stage"] == "objective"]
        finals = [row for row in events if row["stage"] == "final"]
        if not events:
            _need(saved == dict(status="not-started", callbacks=0, reason=None, result=None)
                  and witness is not None, "missing signed search")
            continue
        _need(objectives and events == objectives+finals and len(finals) <= 1, "callback/final order")
        guards = [row for row in objectives if not row["point"]["eligible"] and
                  row["point"]["branches"][sign]["reason"] in ("guard", "degenerate")]
        if saved["status"] == "completed":
            _need(not guards and len(finals) == 1 and saved["reason"] is None, "completed scalar call")
            value = saved["result"]
            x, fun = _word(value["x_word"], phase=True), _word(value["fun_word"])
            _ratio(value["x_ratio"], x)
            _need(any(row["phase_word"] == x.hex() and row["objective_word"] == fun.hex()
                      for row in objectives), "result.x/fun callback binding")
            _need(finals[0]["phase_word"] == x.hex() and finals[0]["phase_ratio"] == value["x_ratio"], "final result.x binding")
            _need(type(value["nfev"]) is int and value["nfev"] == len(objectives)
                  and type(value["nit"]) is int and value["nit"] == value["nfev"]
                  and type(value["status"]) is int and value["status"] in (0, 1)
                  and type(value["success"]) is bool and value["success"] == (value["status"] == 0)
                  and type(value["message"]) is str, "bounded result metadata")
        else:
            _need(not finals and saved["result"] is None, "aborted scalar result")
            if saved["status"] == "objective-unavailable":
                _need(guards == [objectives[-1]] and saved["reason"] ==
                      objectives[-1]["point"]["branches"][sign]["reason"], "guard abort/restart")
            else:
                _need(saved["status"] == "witness" and not guards and witness is not None
                      and objectives[-1] is rows[-1] and objectives[-1]["point"]["eligible"]
                      and saved["reason"] == "point-gates-pass", "witness scalar stop")
    _need(json.dumps(result["witness"], sort_keys=True, allow_nan=False) ==
          json.dumps(witness, sort_keys=True), "witness binding")
    _need((result["status"], result["disposition"], result["reason"]) ==
          (("verified-analytical-witness", "witness", "point-gates-pass") if witness else
           ("inconclusive/invalid", "inconclusive", "no-verified-witness")), "terminal conclusion")
    return dict(verified=True, counters=counts)
