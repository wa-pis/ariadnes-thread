"""Offline reconstruction of the post-cutoff Moon-relative outward observations."""

from __future__ import annotations

from collections.abc import Callable
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
import math
from typing import Any

ORDER = ("native_normal", "native_tighter", "dop853_normal", "dop853_tighter")
OFFSETS_S = range(0, 601, 50)
OBSERVABLE_GATES = {"radius_m": 1e-6, "radial_speed_m_s": 1e-9, "specific_energy_m2_s2": 1e-6}
NET_GATE_M = 1e-6
type Row = dict[str, Any]
type Check = Callable[[], None]
type Exact = tuple[Fraction, Fraction, Fraction]
type Precise = dict[str, Decimal]


def _noop() -> None:
    pass


def _require(ok: bool, what: str) -> None:
    if not ok:
        raise ValueError("direction audit: " + what)


def _finite(value: Any) -> float:
    _require(type(value) in (float, int), "bad binary64 type")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError("direction audit: binary64 overflow") from exc
    _require(math.isfinite(value), "nonfinite binary64")
    return value


def _state(raw: Any) -> list[float]:
    _require(isinstance(raw, (list, tuple)) and len(raw) == 6, "not a six-state")
    return [_finite(value) for value in raw]


def _exact(sc: list[float], moon: list[float]) -> Exact:
    qx, qy, qz, ux, uy, uz = [Fraction(x) - Fraction(y) for x, y in zip(sc, moon, strict=True)]
    return (qx**2 + qy**2 + qz**2, qx*ux + qy*uy + qz*uz, ux**2 + uy**2 + uz**2)


def _d(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


def _measure(operand: Exact, mu: Fraction, digits: int) -> Precise:
    with localcontext() as context:
        context.prec = digits
        context.rounding = ROUND_HALF_EVEN
        radius = _d(operand[0]).sqrt()
        return {"radius_m": radius, "radial_speed_m_s": _d(operand[1]) / radius,
                "specific_energy_m2_s2": _d(operand[2]) / 2 - _d(mu) / radius}


def _range_delta(end: Precise, first: Precise, digits: int) -> float:
    with localcontext() as context:
        context.prec = digits
        context.rounding = ROUND_HALF_EVEN
        return float(end["radius_m"] - first["radius_m"])


def _same_word(a: float, raw_b: Any) -> bool:
    return a.hex() == _finite(raw_b).hex()


def _within(raw: Any, reference: float, limit: float, key: str) -> None:
    err = abs(Fraction(_finite(raw)) - Fraction(_finite(reference)))
    _require(err <= Fraction(limit), key + " outside arithmetic gate")


def _sign(x: Fraction) -> int:
    return (x > 0) - (x < 0)


def verify(
    rows: list[Row], moon_mu: float, moon_radius: float, claimed_payload: Row, check: Check = _noop,
) -> Row:
    """Validate raw evidence and reconstruct both precisions without study code."""
    check()
    _require(isinstance(claimed_payload, dict) and
             claimed_payload.keys() == {"rows", "net_ranges", "classification"}, "payload keys")
    claimed_rows, claimed_net = claimed_payload["rows"], claimed_payload["net_ranges"]
    _require(len(rows) == 52 and isinstance(claimed_rows, list) and len(claimed_rows) == 52,
             "wrong number of observations")
    _require(isinstance(claimed_net, list) and len(claimed_net) == 4, "wrong number of net ranges")
    mu, surface = Fraction(_finite(moon_mu)), Fraction(_finite(moon_radius))
    _require(mu > 0 and surface > 0, "nonpositive lunar constants")
    _require(isinstance(rows[0], dict) and "epoch_tdb_s" in rows[0], "initial coepoch missing")
    t0 = _finite(rows[0]["epoch_tdb_s"])
    epochs = [t0, *(t0 + offset for offset in OFFSETS_S[1:])]
    _require(all(a < b and math.isfinite(b) for a, b in zip(epochs, epochs[1:])), "nonincreasing coepochs")
    names = ("profile", "index", "epoch_tdb_s", "spacecraft", "moon")
    moons: list[list[str]] = []
    audited_rows: list[Row] = []
    audited_net: list[Row] = []

    for p, profile in enumerate(ORDER):
        start_r2 = Fraction()
        first: dict[int, Precise] = {}
        for j, epoch in enumerate(epochs):
            check()
            raw = rows[p*13 + j]
            claimed = claimed_rows[p*13 + j]
            _require(isinstance(raw, dict) and raw.keys() == set(names), "raw row keys")
            _require(isinstance(claimed, dict) and
                     claimed.keys() == set(names) | OBSERVABLE_GATES.keys() | {"radial_sign"}, "saved row keys")
            _require(raw["profile"] == claimed["profile"] == profile and
                     type(raw["index"]) is int and type(claimed["index"]) is int and
                     raw["index"] == claimed["index"] == j, "wrong profile or node")
            _require(_same_word(epoch, raw["epoch_tdb_s"]) and _same_word(epoch, claimed["epoch_tdb_s"]),
                     "wrong coepoch")
            sc, moon = _state(raw["spacecraft"]), _state(raw["moon"])
            for words, saved in ((sc, claimed["spacecraft"]), (moon, claimed["moon"])):
                _require(all(_same_word(x, y) for x, y in zip(words, _state(saved), strict=True)),
                         "raw state identity mismatch")
            moon_words = [x.hex() for x in moon]
            if p == 0:
                moons.append(moon_words)
            else:
                _require(moon_words == moons[j], "noncommon Moon coepoch state")

            exact = _exact(sc, moon)
            _require(exact[0] > surface ** 2, "Moon exterior guard")
            radial_sign = _sign(exact[1])
            _require(type(claimed["radial_sign"]) is int and claimed["radial_sign"] == radial_sign,
                     "radial sign mismatch")
            at = {digits: _measure(exact, mu, digits) for digits in (80, 100)}
            for field, gate in OBSERVABLE_GATES.items():
                for measures in at.values():
                    _within(claimed[field], float(measures[field]), gate, field)
            audited_rows.append({k: raw[k] for k in names} |
                                {key: float(value) for key, value in at[100].items()} |
                                {"radial_sign": radial_sign})
            if j == 0:
                start_r2, first = exact[0], at
            if j == len(epochs) - 1:
                net = claimed_net[p]
                delta_sign = _sign(exact[0] - start_r2)
                _require(isinstance(net, dict) and
                         net.keys() == {"profile", "net_range_change_m", "net_range_sign"} and
                         net["profile"] == profile and type(net["net_range_sign"]) is int and
                         net["net_range_sign"] == delta_sign, "net range sign or profile mismatch")
                for digits in (80, 100):
                    _within(net["net_range_change_m"], _range_delta(at[digits], first[digits], digits),
                            NET_GATE_M, "net range change")
                audited_net.append({"profile": profile, "net_range_sign": delta_sign,
                                    "net_range_change_m": _range_delta(at[100], first[100], 100)})
    outward = min(r["radial_sign"] for r in audited_rows) > 0 and min(r["net_range_sign"] for r in audited_net) > 0
    label = "outbound-at-samples" if outward else "outbound-not-established"
    _require(claimed_payload["classification"] == label, "classification mismatch")
    check()
    return {"rows": audited_rows, "net_ranges": audited_net, "classification": label}
