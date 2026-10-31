"""Independent stdlib-only arithmetic audit of ADR0127 evidence; no native imports."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from typing import Any

REFERENCE_SHA = "3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0"
MU = 1.327124400420322e20


def demand(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def finite(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            finite(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            finite(item)
    elif isinstance(value, float):
        demand(math.isfinite(value), "nonfinite JSON")


def state(record: dict[str, Any]) -> tuple[float, ...]:
    values = tuple(record["position_m"]) + tuple(record["velocity_m_s"])
    demand(
        len(values) == 6
        and all(type(v) in (int, float) and math.isfinite(v) for v in values),
        "state shape/numbers",
    )
    return values


def angular(r: tuple[float, ...], v: tuple[float, ...]) -> tuple[float, ...]:
    return (
        r[1] * v[2] - r[2] * v[1],
        r[2] * v[0] - r[0] * v[2],
        r[0] * v[1] - r[1] * v[0],
    )


def energy(x: tuple[float, ...]) -> float:
    return math.fsum(v * v for v in x[3:]) / 2 - MU / math.hypot(*x[:3])


def audit(report: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    """Recalculate retained arithmetic; partial evidence never certifies R2."""
    finite(report)
    demand(
        report["comparison"] == "r2-reference-coast-v1"
        and report["oracle"] == "cartesian-ellipse-bisection-v1",
        "contract IDs",
    )
    demand(
        report["contract"] == "ADR0127" and report["reference_sha256"] == REFERENCE_SHA,
        "reference digest/contract",
    )
    demand(
        report["units"]
        == {
            "time": "TDB seconds since J2000",
            "position_units": "m",
            "velocity_units": "m/s",
        },
        "units",
    )
    demand(report["frame"] == {"origin": "SSB", "orientation": "J2000"}, "frame")
    demand(
        report["native_spacecraft_propagations"] == 0 and report["budget_s"] == 30.0,
        "execution contract",
    )
    original = json.loads(json.dumps(reference["runs"][0]))
    demand(report.get("original", original) == original, "original data changed")
    points = report["points"]
    attempted, completed = report["attempted_sun_calls"], report["completed_sun_calls"]
    demand(
        type(attempted) is int
        and type(completed) is int
        and 0 <= completed <= attempted <= 121,
        "call counts",
    )
    sun_calls = [c for c in report["calls"] if c["label"].startswith("Sun ")]
    demand(len(sun_calls) == attempted, "attempted ledger")
    demand(
        sum(c["returned"] is True for c in sun_calls) == completed, "completed ledger"
    )
    demand(
        [c["label"] for c in sun_calls] == [f"Sun {k}" for k in range(attempted)],
        "call order",
    )
    demand(sum("sun" in p for p in points) == completed, "returned data count")
    demand(len(points) <= 121, "point cap")
    for call in report["calls"]:
        demand(0 <= call["start_s"] <= call["end_s"], "call timing")
    checked = 0
    if "initial_state" in report:
        seed = tuple(report["initial_state"])
        operands = report["seed_operands"]
        moon = state(original["endpoints"]["departure"]["body_state"])
        sun0 = state(points[0]["sun"])
        excess = tuple(original["selected"]["departure_v_infinity_m_s"])
        demand(
            tuple(operands["moon"]) == moon
            and tuple(operands["sun0"]) == sun0
            and tuple(operands["excess_m_s"]) == excess,
            "seed operands",
        )
        expected_seed = tuple(moon[i] - sun0[i] for i in range(3)) + tuple(
            (moon[i + 3] - sun0[i + 3]) + excess[i] for i in range(3)
        )
        demand(seed == expected_seed, "seed arithmetic")
        if "ellipse" not in report:
            demand(
                report["status"] in ("failed", "unavailable") and "error" in report,
                "missing geometry failure",
            )
            return {
                "audit": "passed",
                "study_status": report["status"],
                "arithmetic_nodes_checked": 0,
                "reference_coast_verified": False,
            }
        r, v = seed[:3], seed[3:]
        h = angular(r, v)
        radius = math.hypot(*r)
        a = 1 / (2 / radius - math.fsum(t * t for t in v) / MU)
        vh = angular(v, h)
        ev = tuple(vh[i] / MU - r[i] / radius for i in range(3))
        e = math.hypot(*ev)
        demand(1e9 <= a <= 1e13 and 1e-6 <= e <= 0.95, "admitted domain")
        p = tuple(t / e for t in ev)
        w = tuple(t / math.hypot(*h) for t in h)
        q = angular(w, p)
        dotrq = math.fsum(r[i] * q[i] for i in range(3))
        dotrp = math.fsum(r[i] * p[i] for i in range(3))
        e0 = math.atan2(dotrq / (a * math.sqrt(1 - e * e)), dotrp / a + e)
        m0, n = e0 - e * math.sin(e0), math.sqrt(MU / a**3)
        geometry = report["ellipse"]
        demand(
            geometry
            == {
                "a_m": a,
                "eccentricity": e,
                "p": list(p),
                "q": list(q),
                "w": list(w),
                "initial_eccentric_anomaly_rad": e0,
                "initial_mean_anomaly_rad": m0,
                "mean_motion_rad_s": n,
            },
            "ellipse identity/arithmetic",
        )
        for k, point in enumerate(points):
            demand(point["index"] == k, "node order")
            epoch = original["states"][k]["epoch_tdb_s"]
            dt = epoch - original["states"][0]["epoch_tdb_s"]
            demand(
                point["epoch_tdb_s"] == epoch and point["elapsed_s"] == dt,
                "epoch/dt identity",
            )
            if "relative" not in point:
                demand(point["status"] != "passed", "missing completed comparison")
                continue
            sun_record = point["sun"]
            demand(
                sun_record["body"] == "Sun"
                and sun_record["origin"] == "SSB"
                and sun_record["orientation"] == "J2000"
                and sun_record["epoch_tdb_s"] == epoch,
                "Sun identity",
            )
            sun = state(sun_record)
            saved = state(original["states"][k])
            solved = point["oracle"]
            anomaly = solved["eccentric_anomaly_rad"]
            mean = math.remainder(m0 + n * dt, 2 * math.pi)
            residual = abs(anomaly - e * math.sin(anomaly) - mean)
            demand(
                mean == solved["mean_anomaly_rad"]
                and residual == solved["residual_rad"],
                "root arithmetic",
            )
            demand(
                0 <= solved["bracket_width_rad"] <= 2e-14
                and residual <= 2e-14
                and type(solved["updates"]) is int
                and 1 <= solved["updates"] <= 64,
                "root gate",
            )
            sine, cosine = math.sin(anomaly), math.cos(anomaly)
            beta, rate = math.sqrt(1 - e * e), n / (1 - e * cosine)
            expected = tuple(
                a * (cosine - e) * p[i] + a * beta * sine * q[i] for i in range(3)
            ) + tuple(
                -a * sine * rate * p[i] + a * beta * cosine * rate * q[i]
                for i in range(3)
            )
            demand(tuple(solved["state"]) == expected, "oracle state arithmetic")
            relative = tuple(x - y for x, y in zip(saved, sun, strict=True))
            ssb = tuple(x + y for x, y in zip(expected, sun, strict=True))
            demand(
                tuple(point["saved_relative"]) == relative
                and tuple(point["oracle_ssb"]) == ssb,
                "translation arithmetic",
            )
            passed = True
            for name, left, right in (
                ("relative", relative, expected),
                ("ssb", saved, ssb),
            ):
                difference = tuple(x - y for x, y in zip(left, right, strict=True))
                position, velocity = (
                    math.hypot(*difference[:3]),
                    math.hypot(*difference[3:]),
                )
                comparison = point[name]
                demand(
                    tuple(comparison["difference"]) == difference
                    and comparison["position_error_m"] == position
                    and comparison["velocity_error_m_s"] == velocity,
                    "difference arithmetic",
                )
                passed &= position <= 1 and velocity <= 1e-6
            for name, x in (("saved", relative), ("oracle", expected)):
                de = abs(energy(x) - energy(seed)) / abs(energy(seed))
                dh = math.dist(angular(x[:3], x[3:]), h) / math.hypot(*h)
                demand(
                    point["relative"]["invariants"][name]
                    == {"energy": de, "angular_momentum": dh},
                    "invariant arithmetic",
                )
                passed &= de <= 1e-12 and dh <= 1e-12
            if point["status"] == "passed":
                demand(passed, "node verdict")
            else:
                demand(
                    point["status"] == "failed"
                    and report["status"] != "passed"
                    and k == len(points) - 1
                    and "error" in report,
                    "partial node verdict",
                )
            checked += 1
    if report["status"] == "passed":
        demand(
            checked == completed == attempted == len(points) == 121,
            "success requires121 checked nodes",
        )
        demand(all(p["status"] == "passed" for p in points), "failed nodes")
        demand(report["identity"] == report["final_identity"], "identity drift")
        demand(
            report["identity"]["kernels"]
            == reference["provenance"]["manifest"]["spice"],
            "kernel identity",
        )
        demand(
            0 <= report["elapsed_seconds"] < 30
            and all(c["end_s"] < 30 for c in report["calls"]),
            "deadline",
        )
    else:
        demand(
            report["status"] in ("failed", "unavailable") and "error" in report,
            "failure context",
        )
    return {
        "audit": "passed",
        "study_status": report["status"],
        "arithmetic_nodes_checked": checked,
        "reference_coast_verified": report["status"] == "passed",
    }


def audit_file(path: Path) -> dict[str, Any]:
    reference_path = Path(__file__).resolve().with_name("0119-m2-reference.json")
    demand(
        sha256(reference_path.read_bytes()).hexdigest() == REFERENCE_SHA,
        "frozen reference changed",
    )
    report = json.loads(path.read_text())
    if "identity" in report:
        identity = report["identity"]
        root = reference_path.parents[3]
        for name, digest in identity["source_sha256"].items():
            source = (root / name).resolve()
            demand(
                source.is_relative_to(root.resolve()), "source path outside checkout"
            )
            demand(
                sha256(source.read_bytes()).hexdigest() == digest, "source hash drift"
            )
        binary = identity["native_binary"]
        demand(
            sha256(Path(binary["path"]).read_bytes()).hexdigest() == binary["sha256"],
            "native binary drift",
        )
        demand(
            identity["versions"]
            == {
                "python": "3.12.14",
                "numpy": "1.26.4",
                "scipy": "1.17.1",
                "spiceypy": "8.2.0",
                "tudatpy": "1.0.0",
                "tudat-resources": "2.4",
            },
            "runtime versions",
        )
    return audit(report, json.loads(reference_path.read_text()))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: 0128-audit-reference-coast.py EVIDENCE.json")
    print(json.dumps(audit_file(Path(sys.argv[1]))))
