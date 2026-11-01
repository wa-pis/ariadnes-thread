"""Independent80-digit arithmetic and offline evidence audit for ADR0131."""

from __future__ import annotations

from decimal import Decimal, localcontext
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
INDICES = (0, 60, 120)
BODIES = ("Earth", "Moon", "Mars")
GUARDS = {"Sun": 696000000.0, "Earth": 6378136.6, "Moon": 1737400.0, "Mars": 3396190.0}
SHA = {
    "0119-m2-reference.json": "3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0",
    "0129-reference-coast.json": "e2c5d077285fe0218d1c93f3000f319048006eb55477d680f83041f6c70ce9d7",
}


def demand(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def decimal_force(
    x: tuple[float, ...], b: tuple[float, ...], mu: float
) -> dict[str, Any]:
    """Unit-vector/squared-distance oracle; no binary inverse-cube helpers."""
    with localcontext() as ctx:
        ctx.prec = 80
        position = [Decimal.from_float(v) for v in x]
        body = [Decimal.from_float(v) for v in b]
        delta = [v - u for u, v in zip(position, body, strict=True)]
        ds = sum(v * v for v in delta)
        bs = sum(v * v for v in body)
        demand(ds > 0 and bs > 0, "zero oracle distance")
        dn, bn = ds.sqrt(), bs.sqrt()
        gm = Decimal.from_float(mu)
        direct = [(v / dn) * (gm / ds) for v in delta]
        indirect = [(v / bn) * (gm / bs) for v in body]
        difference = [u - v for u, v in zip(direct, indirect, strict=True)]
        norm = sum(v * v for v in difference).sqrt()
        return {
            "direct": [str(v) for v in direct],
            "indirect": [str(v) for v in indirect],
            "differential": [str(v) for v in difference],
            "norm": str(norm),
        }


def check_term(term: dict[str, Any]) -> None:
    """Recalculate the independent Decimal result and the numeric gate."""
    x, b, mu = tuple(term["x_m"]), tuple(term["b_m"]), term["gm_m3_s2"]
    demand(
        len(x) == len(b) == 3
        and type(mu) in (int, float)
        and math.isfinite(mu)
        and mu > 0,
        "term input",
    )
    demand(
        all(type(v) in (int, float) and math.isfinite(v) for v in x + b),
        "term position",
    )
    delta = tuple(v - u for u, v in zip(x, b, strict=True))
    distance, body_radius = math.hypot(*delta), math.hypot(*b)
    demand(
        term["distance_m"] == distance and term["body_sun_distance_m"] == body_radius,
        "term distances",
    )
    outside = distance > term["guard_m"] and body_radius > term["guard_m"]
    demand(
        term["status"] == ("admissible" if outside else "inadmissible"),
        "domain classification",
    )
    if not outside:
        demand(
            not any(
                k in term
                for k in (
                    "differential_m_s2",
                    "direct_m_s2",
                    "indirect_m_s2",
                    "decimal",
                    "solar_ratio",
                )
            ),
            "fabricated inadmissible force",
        )
        return
    expected = decimal_force(x, b, float(mu))
    demand(term["decimal"] == expected, "Decimal oracle identity")
    with localcontext() as ctx:
        ctx.prec = 80
        threshold = max(Decimal("1e-15"), Decimal("1e-11") * Decimal(expected["norm"]))
        for name in ("direct", "indirect", "differential"):
            values = term[name + "_m_s2"]
            demand(
                len(values) == 3
                and all(type(v) in (int, float) and math.isfinite(v) for v in values),
                "finite force components",
            )
            errors = [
                abs(Decimal.from_float(float(v)) - Decimal(ref))
                for v, ref in zip(values, expected[name], strict=True)
            ]
            # Individual direct/indirect fields use their own magnitude scale.
            scale = sum(Decimal(v) ** 2 for v in expected[name]).sqrt()
            limit = (
                threshold
                if name == "differential"
                else max(Decimal("1e-15"), Decimal("1e-11") * scale)
            )
            demand(max(errors) <= limit, "force arithmetic gate " + name)
        difference = tuple(
            a - b
            for a, b in zip(term["direct_m_s2"], term["indirect_m_s2"], strict=True)
        )
        demand(
            tuple(term["differential_m_s2"]) == difference,
            "direct-minus-indirect arithmetic",
        )
        demand(term["norm_m_s2"] == math.hypot(*difference), "term norm")


def audit(report: dict[str, Any]) -> dict[str, Any]:
    """Audit full or partial saved evidence without native reads."""
    demand(
        report["contract"] == "ADR0131"
        and report["screening"] == "r3-three-epoch-gravity-v1",
        "contract",
    )
    demand(report["reference_sha256"] == SHA, "reference identities")
    demand(
        report["units"]
        == {
            "position": "m",
            "acceleration": "m/s^2",
            "gm": "m^3/s^2",
            "epoch": "TDB seconds since J2000",
        },
        "units/time",
    )
    demand(
        report["origin"] == "Sun"
        and report["orientation"] == "J2000"
        and report["aberration_correction"] == "NONE",
        "frame",
    )
    demand(
        report["guards_m"] == GUARDS
        and report["budget_s"] == 30.0
        and report["native_spacecraft_propagations"] == 0,
        "contract gates",
    )
    counts = report["counts"]
    for name, cap in (("states", 7), ("earth_gm", 1)):
        a, c = counts[name + "_attempted"], counts[name + "_completed"]
        demand(
            type(a) is int and type(c) is int and 0 <= c <= a <= cap, "request counts"
        )
    data_calls = [
        c for c in report["calls"] if c["label"].startswith(("state ", "Earth GM"))
    ]
    labels = [
        "Earth GM",
        "state Earth0",
        "state Mars0",
        "state Earth60",
        "state Moon60",
        "state Mars60",
        "state Earth120",
        "state Moon120",
    ]
    demand(
        [c["label"] for c in data_calls] == labels[: len(data_calls)], "request order"
    )
    demand(
        len(data_calls) == counts["states_attempted"] + counts["earth_gm_attempted"],
        "attempt ledger",
    )
    demand(
        sum(c["returned"] is True for c in data_calls)
        == counts["states_completed"] + counts["earth_gm_completed"],
        "completion ledger",
    )
    checked = 0
    inputs = report.get("inputs")
    if inputs is not None:
        demand(
            len(inputs["rows"]) == 3
            and [r["index"] for r in inputs["rows"]] == list(INDICES),
            "fixed nodes",
        )
        require_gm = {
            "Sun": 1.327124400420322e20,
            "Moon": 4902800205346.301,
            "Mars": 42828375010399.99,
        }
        demand(inputs["gm_m3_s2"] == require_gm, "retained GM")
        if "gm_m3_s2" in report:
            demand(
                all(report["gm_m3_s2"][k] == v for k, v in require_gm.items()),
                "GM drift",
            )
            if "Earth" in report["gm_m3_s2"]:
                demand(
                    type(report["gm_m3_s2"]["Earth"]) in (float, int)
                    and math.isfinite(report["gm_m3_s2"]["Earth"])
                    and report["gm_m3_s2"]["Earth"] > 0,
                    "Earth GM",
                )
            else:
                demand(
                    report["status"] != "passed" and not report["rows"],
                    "missing Earth GM before rows",
                )
        for point, original in zip(report["rows"], inputs["rows"]):
            k, epoch = point["index"], original["epoch_tdb_s"]
            demand(
                k == original["index"] and point["epoch_tdb_s"] == epoch, "node/epoch"
            )
            x = tuple(
                a - b
                for a, b in zip(
                    original["spacecraft"]["position_m"],
                    original["sun"]["position_m"],
                    strict=True,
                )
            )
            demand(
                tuple(point["x_m"]) == x and math.hypot(*x) > GUARDS["Sun"],
                "Sun-relative position/domain",
            )
            solar = tuple(-require_gm["Sun"] * v / math.hypot(*x) ** 3 for v in x)
            demand(
                tuple(point["solar_m_s2"]) == solar
                and point["solar_norm_m_s2"] == math.hypot(*solar),
                "solar arithmetic",
            )
            for name, term in point["terms"].items():
                demand(name in BODIES and term["guard_m"] == GUARDS[name], "body/guard")
                raw = point["bodies"][name]
                demand(
                    raw["body"] == name
                    and raw["epoch_tdb_s"] == epoch
                    and raw["origin"] == "SSB"
                    and raw["orientation"] == "J2000",
                    "body identity",
                )
                b = tuple(
                    a - b
                    for a, b in zip(
                        raw["position_m"], original["sun"]["position_m"], strict=True
                    )
                )
                demand(
                    tuple(term["x_m"]) == x
                    and tuple(term["b_m"]) == b
                    and term["gm_m3_s2"] == report["gm_m3_s2"][name],
                    "term operands",
                )
                check_term(term)
                if term["status"] == "admissible":
                    demand(
                        term["solar_ratio"]
                        == term["norm_m_s2"] / point["solar_norm_m_s2"],
                        "individual ratio",
                    )
                checked += 1
            if point.get("status") == "passed":
                demand(list(point["terms"]) == list(BODIES), "complete body terms")
                if k == 60:
                    demand(
                        all(
                            t["status"] == "admissible" for t in point["terms"].values()
                        ),
                        "middle domain",
                    )
                    vectors = [point["terms"][b]["differential_m_s2"] for b in BODIES]
                    total = tuple(math.fsum(v[i] for v in vectors) for i in range(3))
                    norm = math.hypot(*total)
                    norms = math.fsum(point["terms"][b]["norm_m_s2"] for b in BODIES)
                    demand(
                        point["summary"]
                        == {
                            "vector_sum_m_s2": list(total),
                            "norm_of_sum_m_s2": norm,
                            "sum_of_norms_m_s2": norms,
                            "sum_solar_ratio": norm / point["solar_norm_m_s2"],
                            "norms_solar_ratio": norms / point["solar_norm_m_s2"],
                        },
                        "middle sum/ratios",
                    )
                else:
                    expected_invalid = "Moon" if k == 0 else "Mars"
                    demand(
                        point["terms"][expected_invalid]["status"] == "inadmissible"
                        and point["summary"] is None,
                        "endpoint coverage",
                    )
    if report["status"] == "passed":
        demand(
            counts
            == {
                "states_attempted": 7,
                "states_completed": 7,
                "earth_gm_attempted": 1,
                "earth_gm_completed": 1,
            },
            "full counts",
        )
        demand(
            checked == 9
            and len(report["rows"]) == 3
            and all(r["status"] == "passed" for r in report["rows"]),
            "complete screening",
        )
        demand(report["identity"] == report["final_identity"], "identity drift")
        demand(report["identity"]["kernels"] == inputs["kernels"], "kernel identity")
        demand(
            report["elapsed_sample_before_flush_s"] < 30
            and report["finalization_gate"] == "passed",
            "time gate",
        )
        demand(
            all(
                0 <= c["start_s"] <= c["end_s"] < 30 and c["returned"]
                for c in report["calls"]
            ),
            "call timing",
        )
    else:
        demand(
            report["status"] in ("failed", "unavailable") and "error" in report,
            "partial failure",
        )
    return {
        "audit": "passed",
        "screening_status": report["status"],
        "terms_checked": checked,
        "screening_verified": report["status"] == "passed",
    }


def audit_file(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text())
    for name, digest in SHA.items():
        demand(
            sha256((ROOT / "docs/adr/experiments" / name).read_bytes()).hexdigest()
            == digest,
            "frozen file drift",
        )
    if "inputs" in report:
        reference = json.loads(
            (ROOT / "docs/adr/experiments/0119-m2-reference.json").read_text()
        )
        r2 = json.loads(
            (ROOT / "docs/adr/experiments/0129-reference-coast.json").read_text()
        )
        original = reference["runs"][0]
        expected = []
        for k in INDICES:
            bodies = {}
            if k == 0:
                bodies["Moon"] = original["endpoints"]["departure"]["body_state"]
            if k == 120:
                bodies["Mars"] = original["endpoints"]["arrival"]["body_state"]
            expected.append(
                {
                    "index": k,
                    "epoch_tdb_s": original["states"][k]["epoch_tdb_s"],
                    "spacecraft": original["states"][k],
                    "sun": r2["points"][k]["sun"],
                    "retained_bodies": bodies,
                }
            )
        demand(
            report["inputs"]["rows"] == expected, "original state/Sun/epoch identity"
        )
        demand(
            report["inputs"]["kernels"] == reference["provenance"]["manifest"]["spice"],
            "original manifest",
        )
    if "identity" in report:
        for name, digest in report["identity"]["source_sha256"].items():
            source = (ROOT / name).resolve()
            demand(
                source.is_relative_to(ROOT)
                and sha256(source.read_bytes()).hexdigest() == digest,
                "source drift",
            )
        binary = report["identity"]["native_binary"]
        demand(
            sha256(Path(binary["path"]).read_bytes()).hexdigest() == binary["sha256"],
            "binary drift",
        )
    return audit(report)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: 0132-gravity-audit.py EVIDENCE.json")
    print(json.dumps(audit_file(Path(sys.argv[1]))))
