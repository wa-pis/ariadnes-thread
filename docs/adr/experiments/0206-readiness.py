"""R5.59: exercise the physical-join admission contract on invented evidence only."""

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction
from hashlib import sha256
import json
import math
from typing import Any

type Row = dict[str, Any]  # JSON boundary
MODEL = ("ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-"
         "cannonball-srp-schwarzschild-direct-spice-v2")
FIXED_WORDS = ("0x1.d2d247f9d7e7ap+29", "0x1.d2d4a9afb54adp+29", "0x1.ded341cb4c44bp+29")
LINKS = ("10:0", "1:0", "2:0", "399:0", "301:399", "499:4", "4:0", "599:5",
         "5:0", "699:6", "6:0", "J2000:IAU_Moon", "J2000:IAU_Mars")
MASS = dict(initial_kg=2000, dry_kg=500, thrust_n=1000, isp_s=450, g0_m_s2=9.80665,
            area_m2=20, reflectivity=1.3)
SOLVERS = ("RKDP87", "DOP853")
JOIN = dict(epoch_s="1e-6", position_m="0.001", velocity_m_s="1e-6", mass_kg="1e-9")
TARGET = dict(position_m="1000", velocity_m_s="0.01")
CAPS = dict(segments=12, rhs=1_000_000, provider=32_000_000, evidence_bytes=64 * 2**20)


class Unavailable(ValueError):
    """A synthetic packet cannot exercise the complete admission path."""


def require(condition: object, reason: str) -> None:
    if not condition:
        raise Unavailable(reason)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: object) -> str:
    return sha256(canonical(value)).hexdigest()


def sha_word(value: object) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def number(value: object) -> float:
    if type(value) not in (float, int):
        raise ValueError("finite binary64 number required")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("finite binary64 number required")
    return result


def word(value: object) -> float:
    if not isinstance(value, str) or len(value) > 30:
        raise ValueError("canonical binary64 word required")
    result = float.fromhex(value)
    if not math.isfinite(result) or result.hex() != value:
        raise ValueError("canonical binary64 word required")
    return result


def read_object(pairs: list[tuple[str, Any]]) -> Row:
    result: Row = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def nonfinite(value: str) -> None:
    raise ValueError(f"invalid JSON number: {value}")


def ledger(departure_s: Fraction, arrival_s: Fraction) -> tuple[Fraction, Fraction]:
    rate_kg_s = Fraction(MASS["thrust_n"] / (MASS["g0_m_s2"] * MASS["isp_s"]))
    coast_kg = Fraction(2000) - rate_kg_s * departure_s
    return coast_kg, coast_kg - rate_kg_s * arrival_s


def check_binding(binding: Row) -> tuple[float, float, Row]:
    require(binding["candidate"] == "d0001-t0035" and binding["model"] == MODEL
            and binding["coordinates"] == ["SI", "SSB", "J2000", "TDB seconds since J2000"],
            "candidate-model-frame")
    require(binding["anchors"] == list(FIXED_WORDS), "fixed-epochs")
    require(canonical(binding["mass"]) == canonical(MASS), "fixed-spacecraft")
    require(all(sha_word(binding[key]) for key in
                ("departure_state_sha256", "target_state_sha256", "settings_sha256")),
            "source-binding")
    require(binding["departure_state_sha256"] != binding["target_state_sha256"], "source-binding")
    resources = binding["ordered_resources_sha256"]
    require(isinstance(resources, list) and bool(resources) and all(map(sha_word, resources))
            and len(set(resources)) == len(resources), "resource-identity")
    cmd = binding["command"]
    require(cmd["source"] == "independent-artificial" and isinstance(cmd["rationale"], str)
            and bool(cmd["rationale"].strip()) and sha_word(cmd["source_sha256"]), "command-provenance")
    a_d, e_d, tau_d, a_a, e_a, tau_a = map(word, cmd["words"])
    require(list(cmd["words"]) == [x.hex() for x in (a_d, e_d, tau_d, a_a, e_a, tau_a)]
            and all(-math.pi <= a < math.pi for a in (a_d, a_a))
            and all(abs(e) <= math.pi / 2 for e in (e_d, e_a))
            and min(tau_d, tau_a) > 0, "command-domain")
    t0, checkpoint, tf = map(word, FIXED_WORDS)
    require(binding["native_clock"] == "artificial-absolute-binary64-tdb", "native-clock")
    native = [t0, t0 + tau_d, checkpoint, tf - tau_a, tf]
    require(all(left < right for left, right in zip(native, native[1:])), "event-order")
    require(binding["native_event_words"] == [time.hex() for time in native], "native-events")
    declared = ledger(Fraction(tau_d), Fraction(tau_a))
    effective = ledger(Fraction(native[1]) - Fraction(t0), Fraction(tf) - Fraction(native[3]))
    require(declared[1] >= 500, "commanded-dry-floor")
    require(effective[1] >= 500, "effective-dry-floor")
    return t0, tf, {
        "native_event_words": binding["native_event_words"],
        "commanded_coast_coast_final_kg_exact": [str(declared[0]), str(declared[0]), str(declared[1])],
        "effective_coast_coast_final_kg_exact": [str(effective[0]), str(effective[0]), str(effective[1])],
        "effective_minus_commanded_kg_exact": [str(e - d) for e, d in zip(effective, declared)],
    }


def closed_coverage(coverage: Row, t0: float, tf: float) -> None:
    require(set(coverage) == set(LINKS), "coverage-inventory")
    for link in LINKS:
        end = t0
        for lo_word, hi_word in coverage[link]:
            lo, hi = word(lo_word), word(hi_word)
            require(lo <= hi and lo <= end, f"coverage-gap:{link}")
            end = max(hi, end)
        require(end >= tf, f"coverage-end:{link}")


def check_qualification(qualification: Row, pin: str, t0: float, tf: float) -> None:
    require(qualification["binding_sha256"] == pin, "qualification-binding")
    closed_coverage(qualification["coverage"], t0, tf)
    require(set(qualification["solvers"]) == set(SOLVERS), "solver-inventory")
    solver_sources = set()
    for name in SOLVERS:
        record = qualification["solvers"][name]
        require(record["reverse"] == "decreasing-time-unchanged-physical-rhs"
                and record["adapter"] == "artificial-qualification"
                and isinstance(record["version"], str) and bool(record["version"].strip()),
                f"reverse-qualification:{name}")
        for key in ("source_sha256", "settings_sha256", "clock_policy_sha256",
                    "endpoint_certificate_sha256", "force_parity_sha256"):
            require(sha_word(record[key]), f"missing-{key}:{name}")
        require(set(record["force_controls"]) == {"near-Moon", "cruise", "near-Mars"},
                f"force-controls:{name}")
        solver_sources.add(record["source_sha256"])
    require(len(solver_sources) == 2, "reference-not-independent")
    require(sha_word(qualification["timing_sha256"]), "timing-proof")


def check_budget(budget: Row, pin: str) -> Row:
    require(budget["binding_sha256"] == pin and sha_word(budget["accounting_sha256"])
            and budget["accounting"] in ("instrumented", "charged-upper-bound"), "budget-proof")
    require(all(type(budget[key]) is int and budget[key] == expected for key, expected in
                (("attempts", 1), ("pairs", 1), ("searches", 0), ("retries", 0), ("audits", 1))), "one-attempt")
    require(0 <= number(budget["work_stopped_s"]) <= 285
            and number(budget["work_stopped_s"]) <= number(budget["finalized_s"]) <= 300, "study-deadline")
    require(0 <= number(budget["audit_finalized_s"]) <= 30, "audit-deadline")
    audit_in, audit_out = budget["audit_input_bytes"], budget["audit_output_bytes"]
    require(type(audit_in) is int and 0 < audit_in <= CAPS["evidence_bytes"]
            and type(audit_out) is int and 0 < audit_out <= 128 * 2**10, "audit-bytes")
    charges = {name: dict.fromkeys(CAPS, 0) for name in SOLVERS}
    totals = dict.fromkeys(CAPS, 0)
    completed_segments = dict.fromkeys(SOLVERS, 0)
    failed = False
    for name, counter, count, outcome in budget["charges"]:
        require(name in SOLVERS and counter in CAPS and type(count) is int and count > 0,
                "unknown-charge")
        require(outcome in ("used", "rejected", "failed", "reserved"), "unknown-outcome")
        require(outcome != "reserved" or budget["accounting"] == "charged-upper-bound",
                "opaque-unaccounted")
        require(not failed, "work-after-failure")
        totals[counter] += count
        charges[name][counter] += count
        require(totals[counter] <= CAPS[counter], f"attempt-cap:{counter}")
        require(charges[name]["segments"] <= 6, f"segment-cap:{name}")
        if counter == "segments" and outcome == "used":
            completed_segments[name] += count
        failed = outcome == "failed"
    require(not failed, "failed-work-counted")
    require(all(completed_segments[name] == 6 and charges[name]["rhs"] > 0
                and charges[name]["provider"] > 0 for name in SOLVERS)
            and totals["evidence_bytes"] > 0, "incomplete-accounting")
    require(audit_in == totals["evidence_bytes"], "audit-evidence-binding")
    return {"attempt_totals": totals, "by_solver": charges, "completed_segments": completed_segments}


def directed(value: Fraction, rounding: str) -> Decimal:
    with localcontext(prec=40, rounding=rounding):
        return Decimal(value.numerator) / Decimal(value.denominator)


def interval(sample: Row, limit_text: str, count: int) -> Row:
    d = number(sample["difference"])
    require(d >= 0, "negative-magnitude")
    errors = sample.get("error_bounds")
    if errors is None:
        return {"status": "inconclusive", "observed": d, "interval": None}
    require(isinstance(errors, list) and len(errors) == count, "error-allowances")
    terms = [number(error) for error in errors]
    require(all(term >= 0 for term in terms), "negative-allowance")
    error = sum(map(Fraction, terms), Fraction(0))
    lower = directed(max(Fraction(0), Fraction(d) - error), ROUND_FLOOR)
    upper = directed(Fraction(d) + error, ROUND_CEILING)
    limit = Decimal(limit_text)
    status = "pass" if upper <= limit else "fail" if lower > limit else "inconclusive"
    return {"status": status, "observed": d, "interval": [str(lower), str(upper)]}


def compare(samples: Row) -> Row:
    result: Row = {}
    require(set(samples) == set(SOLVERS), "comparison-solvers")
    for group, metrics, error_count in (("join", JOIN, 3), ("target", TARGET, 2)):
        per_solver = {solver: {} for solver in SOLVERS}
        for solver in SOLVERS:
            event_word = FIXED_WORDS[1 if group == "join" else 2]
            require(samples[solver][group + "_event_words"] == [event_word, event_word], "sample-coepoch")
            if group == "join":
                require(number(samples[solver][group]["epoch_s"]["difference"]) == 0, "sample-clock")
            require(set(samples[solver][group]) == set(metrics), "comparison-quantities")
            for key, limit in metrics.items():
                per_solver[solver][key] = interval(samples[solver][group][key], limit, error_count)
        consensus = {}
        for key in metrics:
            statuses = {per_solver[solver][key]["status"] for solver in SOLVERS}
            consensus[key] = next(iter(statuses)) if len(statuses) == 1 else "inconclusive"
        statuses = set(consensus.values())
        status = "fail" if "fail" in statuses else "inconclusive" if "inconclusive" in statuses else "pass"
        result[group] = {"status": status, "quantities": consensus, "solvers": per_solver}
    return result


def evaluate(raw: bytes, expected_sha256: str) -> Row:
    """Verify external fixture identity, then evaluate the artificial packet and counters."""
    if len(raw) > 2 * 2**20 or not sha_word(expected_sha256) or sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("fixture size or identity")
    packet = json.loads(raw, object_pairs_hook=read_object, parse_constant=nonfinite)
    if not isinstance(packet, dict) or packet.get("schema") != "ariadna-r559-artificial-v1":
        raise ValueError("artificial fixture schema required")
    result: Row = {
        "stage": "R5.59", "synthetic": True, "live_authorized": False,
        "physical_status": "physical-join-not-established", "physical_residuals": dict.fromkeys(JOIN),
    }
    try:
        binding = packet["binding"]
        binding_sha256 = digest(binding)
        require(packet["binding_sha256"] == binding_sha256, "packet-binding")
        t0, tf, mass = check_binding(binding)
        check_qualification(packet["qualification"], binding_sha256, t0, tf)
        budget = check_budget(packet["budget"], binding_sha256)
        require(packet["sample_binding_sha256"] == binding_sha256, "sample-binding")
        verdicts = compare(packet["samples"])
        result.update(status="synthetic-ready", binding_sha256=binding_sha256,
                      synthetic_mass=mass, synthetic_budget=budget, synthetic_verdicts=verdicts)
    except Unavailable as exc:
        result.update(status="unavailable", reason=str(exc))
    except (KeyError, TypeError, IndexError, ValueError, OverflowError) as exc:
        raise ValueError("invalid or missing artificial evidence field") from exc
    return result
