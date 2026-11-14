"""Study-side Moon-relative diagnostics for the fixed post-cutoff coepochs."""

from __future__ import annotations

from collections.abc import Callable
import math
from typing import Any

PROFILES = ("native_normal", "native_tighter", "dop853_normal", "dop853_tighter")
NODES = 13
RAW_KEYS = {"profile", "index", "epoch_tdb_s", "spacecraft", "moon"}
type RawRow = dict[str, Any]
type Check = Callable[[], None]


def idle() -> None:
    pass


def _word(value: Any) -> float:
    if type(value) in (int, float):
        try:
            word = float(value)
        except OverflowError as exc:
            raise ValueError("direction: invalid binary64 word") from exc
        if math.isfinite(word):
            return word
    raise ValueError("direction: invalid binary64 word")


def _six(values: Any) -> list[float]:
    if not isinstance(values, (list, tuple)) or len(values) != 6:
        raise ValueError("direction: expected six raw state components")
    return [_word(x) for x in values]


def _dyadic_word(value: float) -> int:
    # Every binary64 word is an integer multiple of the least subnormal.
    num, den = value.as_integer_ratio()
    return num << (1075 - den.bit_length())


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def compute(
    rows: list[RawRow], moon_mu: float, moon_radius: float, check: Check = idle,
) -> RawRow:
    """Save per-node Moon-relative observations and exact dyadic signs."""
    check()
    mu, surface = _word(moon_mu), _word(moon_radius)
    if mu <= 0 or surface <= 0 or len(rows) != len(PROFILES) * NODES:
        raise ValueError("direction: expected 52 rows and positive Moon constants")
    out: list[RawRow] = []
    net: list[RawRow] = []
    first_radius, first_r2 = 0.0, 0
    t0 = 0.0
    moons: list[list[str]] = []

    for ordinal, src in enumerate(rows):
        check()
        bucket, j = divmod(ordinal, NODES)
        profile = PROFILES[bucket]
        if (not isinstance(src, dict) or src.keys() != RAW_KEYS
                or src["profile"] != profile or type(src["index"]) is not int or src["index"] != j):
            raise ValueError("direction: unexpected row, profile or node")
        epoch = _word(src["epoch_tdb_s"])
        if ordinal == 0:
            t0 = epoch
        coepoch = t0 if j == 0 else t0 + 50 * j
        if epoch.hex() != coepoch.hex() or (j and epoch <= out[-1]["epoch_tdb_s"]):
            raise ValueError("direction: non-coepoch state")
        sc, moon = _six(src["spacecraft"]), _six(src["moon"])
        moon_words = [x.hex() for x in moon]
        if bucket == 0:
            moons.append(moon_words)
        elif moon_words != moons[j]:
            raise ValueError("direction: profiles must share the same Moon state")
        delta = [x - y for x, y in zip(sc, moon, strict=True)]
        words = [_dyadic_word(x) - _dyadic_word(y) for x, y in zip(sc, moon, strict=True)]
        r2 = sum(x*x for x in words[:3])
        dot = sum(x*y for x, y in zip(words[:3], words[3:], strict=True))
        rho = math.hypot(*delta[:3])
        if not math.isfinite(rho) or r2 <= _dyadic_word(surface)**2:
            raise ValueError("direction: Moon exterior guard")
        try:
            vr = math.fsum(x*y for x, y in zip(delta[:3], delta[3:], strict=True)) / rho
            epsilon = math.fsum(v*v / 2 for v in delta[3:]) - mu / rho
        except (OverflowError, ValueError) as exc:
            raise ValueError("direction: invalid relative diagnostics") from exc
        if not math.isfinite(vr) or not math.isfinite(epsilon):
            raise ValueError("direction: nonfinite relative diagnostics")
        out.append({"profile": profile, "index": j, "epoch_tdb_s": epoch,
                    "spacecraft": sc, "moon": moon, "radius_m": rho,
                    "radial_speed_m_s": vr, "specific_energy_m2_s2": epsilon,
                    "radial_sign": _sign(dot)})
        if j == 0:
            first_radius, first_r2 = rho, r2
        elif j == NODES - 1:
            net.append({"profile": profile, "net_range_change_m": rho - first_radius,
                        "net_range_sign": _sign(r2 - first_r2)})
    passed = all(r["radial_sign"] > 0 for r in out) and all(r["net_range_sign"] > 0 for r in net)
    check()
    return {"rows": out, "net_ranges": net,
            "classification": "outbound-at-samples" if passed else "outbound-not-established"}
