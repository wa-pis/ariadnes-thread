"""ADR0172 offline comparisons using a finalized capture and retained operands."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from ariadna_split_analysis import _round_exact, _squares
from ariadna_split_common import FAILURES, Recorder, number, require

ANALYSIS_CAPS = {"epoch": 16}
_POSITION_LIMIT_M = Fraction(1, 1000)
_VELOCITY_LIMIT_M_S = Fraction(1, 1_000_000)


def _words(raw: object, size: int, field: str) -> tuple[float, ...]:
    require(type(raw) in (list, tuple) and len(raw) == size, field + " dimensions")
    require(all(type(x) is float for x in raw), field + " must be binary64")
    return tuple(number(x, field) for x in raw)


def _reference(raw: object) -> tuple[Fraction, ...]:
    require(type(raw) in (list, tuple) and len(raw) == 6
            and all(type(word) is str for word in raw), "retained reference SI fraction vector")
    result = tuple(Fraction(word) for word in raw)
    require(all(str(x) == word for x, word in zip(result, raw, strict=True)),
            "retained reference SI fractions are not canonical")
    return result


def _compare_epoch(
    index: int, hi_tdb_s: float, epoch: dict[str, Any], raw: list[float],
) -> dict[str, Any]:
    ordinals = epoch["observation_ordinals"]
    require(type(ordinals) is list and ordinals
            and all(type(i) is int and i >= 0 for i in ordinals)
            and ordinals == sorted(set(ordinals)), "mapped observation ordinals")
    state = _words(raw, 6, "captured Moon/Earth state")
    reference = _reference(epoch["reference_si"])
    proxy = _words(epoch["proxy_position_km"], 3, "retained proxy position")
    earth = _words(epoch["earth_ssb_km_km_s"], 6, "archived Earth/SSB state")[:3]
    moon = _words(epoch["moon_ssb_km_km_s"], 6, "archived Moon/SSB state")[:3]

    position = state[:3]
    errors = tuple(1000 * Fraction(x) - y for x, y in zip(state, reference, strict=True))
    position_sq, velocity_sq = _squares(errors[:3]), _squares(errors[3:])
    position_passed = position_sq <= _POSITION_LIMIT_M**2
    velocity_passed = velocity_sq <= _VELOCITY_LIMIT_M_S**2

    live_hex = [x.hex() for x in position]
    proxy_hex = [x.hex() for x in proxy]
    proxy_matches = [x == y for x, y in zip(live_hex, proxy_hex, strict=True)]
    proxy_error_m = tuple(1000 * (Fraction(x) - Fraction(y)) for x, y in zip(position, proxy, strict=True))

    exact_sum_km = tuple(Fraction(e) + Fraction(g) for e, g in zip(earth, position, strict=True))
    sum_hex = [_round_exact(x).hex() for x in exact_sum_km]
    moon_hex = [x.hex() for x in moon]
    closure_matches = [x == y for x, y in zip(sum_hex, moon_hex, strict=True)]
    closure_error_m = tuple(1000 * (Fraction(b) - x) for b, x in zip(moon, exact_sum_km, strict=True))

    return {
        "epoch_index": index,
        "hi_tdb_s": hi_tdb_s,
        "observation_ordinals": ordinals,
        "raw_state_km_km_s": state,
        "parity": {
            "signed_position_error_m": errors[:3],
            "signed_velocity_error_m_s": errors[3:],
            "position_error_squared_m2": position_sq,
            "velocity_error_squared_m2_s2": velocity_sq,
            "position_limit_m": _POSITION_LIMIT_M,
            "velocity_limit_m_s": _VELOCITY_LIMIT_M_S,
            "position_passed": position_passed,
            "velocity_passed": velocity_passed,
            "passed": position_passed and velocity_passed,
        },
        "proxy_position": {
            "captured_km_hex": live_hex,
            "archived_proxy_km_hex": proxy_hex,
            "signed_captured_minus_proxy_m": proxy_error_m,
            "bit_matches": proxy_matches,
            "passed": all(proxy_matches),
        },
        "archived_closure": {
            "archived_earth_ssb_km_hex": [x.hex() for x in earth],
            "archived_moon_ssb_km_hex": moon_hex,
            "rounded_earth_plus_captured_moon_km_hex": sum_hex,
            "signed_archived_moon_minus_exact_legs_m": closure_error_m,
            "bit_matches": closure_matches,
            "passed": all(closure_matches),
        },
    }


def analyze(
    bundle: dict[str, Any], states: list[list[float]], report: dict[str, Any], recorder: Recorder,
) -> None:
    """Check all valid frozen epochs; stop on malformed operands or deadline."""
    total = ANALYSIS_CAPS["epoch"]
    rows: list[dict[str, Any]] = []
    checks = {
        name: {"checked": 0, "passed": 0, "expected": count}
        for name, count in {
            "position_parity": total, "velocity_parity": total, "state_parity": total,
            "proxy_position_bits": 3 * total, "archived_closure_bits": 3 * total,
        }.items()
    }
    report.update(
        status="pending", analysis_phase="epochs", rows=rows, checks=checks,
        source={"target": "Moon", "observer": "Earth", "orientation": "J2000",
                "aberration_correction": "NONE", "epoch_scale": "TDB seconds from J2000"},
        native_calls=0, force_evaluations=0, trajectory_propagations=0,
    )
    index: int | None = None
    try:
        epochs = bundle["epochs"]
        require(type(epochs) is list and type(states) is list
                and len(epochs) == len(states) == total, "expected 16 frozen epochs and captured states")
        seen = set()
        for index, (epoch, state) in enumerate(zip(epochs, states, strict=True)):
            hi_tdb_s = epoch["hi_tdb_s"]
            require(type(hi_tdb_s) is float, "epoch must be binary64 TDB seconds")
            number(hi_tdb_s, "epoch hi_tdb_s")
            require(hi_tdb_s not in seen, "duplicate holdout epoch")
            seen.add(hi_tdb_s)
            row = recorder.call("epoch", "compare_geocentric_state", [index, hi_tdb_s],
                                lambda: _compare_epoch(index, hi_tdb_s, epoch, state))
            rows.append(row)

            for name, values in (
                ("position_parity", [row["parity"]["position_passed"]]),
                ("velocity_parity", [row["parity"]["velocity_passed"]]),
                ("state_parity", [row["parity"]["passed"]]),
                ("proxy_position_bits", row["proxy_position"]["bit_matches"]),
                ("archived_closure_bits", row["archived_closure"]["bit_matches"]),
            ):
                checks[name]["checked"] += len(values)
                checks[name]["passed"] += sum(values)
            failed = [name for name in ("parity", "proxy_position", "archived_closure") if not row[name]["passed"]]
            if failed:
                report.setdefault("error", {
                    "stage": "analysis", "type": "NumericalCheck",
                    "message": "failed " + ", ".join(failed), "epoch_index": index, "hi_tdb_s": hi_tdb_s,
                })
        report["analysis_phase"] = "complete"
    except FAILURES as exc:
        stopped = {"stage": "analysis", "type": type(exc).__name__, "message": str(exc), "epoch_index": index}
        report.setdefault("error", stopped)
        report["stopped"] = stopped
        report["analysis_phase"] = "incomplete"
    report["unavailable"] = list(range(len(rows), total))
    report["verdicts"] = {
        name: False if counts["passed"] < counts["checked"]
        else True if counts["checked"] == counts["expected"]
        else None
        for name, counts in checks.items()
    }
    report["status"] = "failed" if "error" in report else "passed"
