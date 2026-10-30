"""Audit retained ADR 0122 arithmetic with stdlib only; never run native code."""

from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]


def conserved(state: list[float], mu: float) -> tuple[float, list[float]]:
    r, v = state[:3], state[3:]
    energy = math.fsum(x * x for x in v) / 2 - mu / math.hypot(*r)
    h = [r[1]*v[2]-r[2]*v[1], r[2]*v[0]-r[0]*v[2], r[0]*v[1]-r[1]*v[0]]
    return energy, h


def audit() -> None:
    evidence = ROOT / "docs/adr/experiments/0122-elliptic-coast.json"
    raw = evidence.read_bytes()
    result = json.loads(raw)
    assert result["status"] == "passed" and "error" not in result
    assert result["benchmark"] == "r1-elliptic-coast-v1"
    assert result["oracle"] == "kepler-bisection-cartesian-v1"
    assert result["reference"] == {
        "origin": "Sun", "orientation": "J2000", "position_units": "m",
        "velocity_units": "m/s", "time": "TDB seconds since J2000"}
    assert result["mass"] == {"status": "not-modelled", "error_kg": None}
    mu, a, e, t0 = 1.327124400420322e20, 149597870700.0, .2, 978995455.2304223
    p, q = [.36, .48, .8], [-.8, .6, 0.0]
    initial = [43084186761.6, 57445582348.799995, 95742637248.0,
               -29182.918856121985, 21887.189142091487, 0.0]
    n = math.sqrt(mu / a**3)
    period = 2 * math.pi / n
    assert result["inputs"] == dict(initial_state=initial, gm_m3_s2=mu, a_m=a,
                                    eccentricity=e, P=p, Q=q, t0_tdb_s=t0,
                                    period_s=period)
    assert result["attempted_adapter_calls"] == result["completed_adapter_calls"] == 17
    assert result["budget_s"] == 30 and 0 < result["elapsed_seconds"] <= 30
    expected = ["source checks", "pure oracle self-checks", "initial provenance",
                "adapter import"]
    expected += [label for i in range(17) for label in (f"oracle {i}", f"adapter {i}")]
    expected += ["final provenance"]
    assert [call["label"] for call in result["calls"]] == expected
    previous = 0.0
    for call in result["calls"]:
        assert call["returned"] is True
        assert previous <= call["start_s"] <= call["end_s"] <= result["elapsed_seconds"]
        previous = call["end_s"]
    provenance = result["provenance"]
    assert provenance == result["final_provenance"]
    assert provenance["base_revision"] == "35ae8a324ab38fa8da8bf74f5bfe775df78e338a"
    assert provenance["dirty_status"] == ["?? docs/adr/experiments/0122-elliptic-coast.json"]
    assert (provenance["python"], provenance["tudatpy"], provenance["numpy"]) == (
        "3.12.14", "1.0.0", "1.26.4")
    assert provenance["spice_requests"] == 0
    assert provenance["conda_build"]["build"] == "py312h2196d89_3"
    for name, digest in provenance["source_sha256"].items():
        assert sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    for name, digest in provenance["native_binary_sha256"].items():
        assert sha256(Path(name).read_bytes()).hexdigest() == digest, name
    assert len(result["points"]) == 17
    energy0, h0 = conserved(initial, mu)
    maximum_position, maximum_velocity, maximum_invariant = 0.0, 0.0, 0.0
    for k, point in enumerate(result["points"]):
        epoch = t0 + k * period / 16
        elapsed = epoch - t0
        assert (point["index"], point["epoch_tdb_s"], point["elapsed_s"],
                point["status"]) == (k, epoch, elapsed, "passed")
        oracle = point["oracle"]
        mean = math.remainder(n * elapsed, 2 * math.pi)
        anomaly = oracle["eccentric_anomaly_rad"]
        assert oracle["mean_anomaly_rad"] == mean
        assert abs(anomaly - e * math.sin(anomaly) - mean) == oracle["residual_rad"] <= 2e-14
        assert 0 <= oracle["bracket_width_rad"] <= 2e-14
        assert 1 <= oracle["updates"] <= 64
        # A distinct Newton solve checks the retained bisection root without importing it.
        independent = mean
        for _ in range(12):
            independent -= (independent-e*math.sin(independent)-mean)/(1-e*math.cos(independent))
        assert abs(independent - anomaly) <= 3e-14
        c, s = math.cos(anomaly), math.sin(anomaly)
        rate, root = n / (1-e*c), math.sqrt(1-e*e)
        analytic = [a*(c-e)*p[j]+a*root*s*q[j] for j in range(3)]
        analytic += [-a*s*rate*p[j]+a*root*c*rate*q[j] for j in range(3)]
        native, reference = point["native_state"], oracle["state"]
        for state in (native, reference):
            assert len(state) == 6 and all(type(x) is float and math.isfinite(x) for x in state)
        assert math.dist(analytic[:3], reference[:3]) <= 1e-4
        assert math.dist(analytic[3:], reference[3:]) <= 1e-10
        comparison = point["comparison"]
        delta = [x-y for x, y in zip(native, reference)]
        assert delta == comparison["native_minus_oracle"]
        pos, vel = math.hypot(*delta[:3]), math.hypot(*delta[3:])
        assert pos == comparison["position_error_m"] <= 1
        assert vel == comparison["velocity_error_m_s"] <= 1e-6
        maximum_position, maximum_velocity = max(maximum_position, pos), max(maximum_velocity, vel)
        for name, state in (("native", native), ("oracle", reference)):
            energy, h = conserved(state, mu)
            errors = (abs(energy-energy0)/abs(energy0), math.dist(h, h0)/math.hypot(*h0))
            saved = comparison["invariants"][name]
            for actual, key in zip(errors, ("relative_energy_error", "relative_angular_momentum_error")):
                assert actual <= 1e-12 and abs(actual-saved[key]) <= 2e-15
                maximum_invariant = max(maximum_invariant, actual, saved[key])
    assert not any(re.match(r"^(tudatpy|spiceypy)(\.|$)", name) for name in sys.modules)
    print(json.dumps(dict(status="passed", native_calls=0, evidence_sha256=sha256(raw).hexdigest(),
                          max_position_error_m=maximum_position, max_velocity_error_m_s=maximum_velocity,
                          max_relative_invariant_error=maximum_invariant)))


if __name__ == "__main__":
    audit()
