"""Audit retained R1.1 evidence with standard-library arithmetic, no native calls."""

from decimal import Decimal, localcontext
from hashlib import sha256
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PATH = ROOT / "docs/adr/experiments/0119-m2-reference.json"
assert sha256(PATH.read_bytes()).hexdigest() == (
    "3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0"
)
data = json.loads(PATH.read_text())
assert data["status"] == "passed" and data["elapsed_seconds"] <= 300
assert len(data["runs"]) == 2
first, second = data["runs"]
assert {k: v for k, v in first.items() if k != "number"} == {
    k: v for k, v in second.items() if k != "number"
}
for prefix in ("search", "sample"):
    assert [c["label"] for c in data["calls"] if c["label"].startswith(prefix + " ")] == [
        f"{prefix} 1", f"{prefix} 2",
    ]
assert all(c["returned"] and 0 <= c["start_s"] <= c["end_s"] <= 300
           for c in data["calls"])
for run in data["runs"]:
    assert run["provenance"] == data["provenance"]
    search = run["search"]
    assert search["evaluated_candidates"] == 1980
    assert search["solved_candidates"] + search["failed_candidates"] == 1980
    eligible = [c for c in search["pareto_front"] if c["final_mass_kg"] >= 550]
    chosen = min(eligible, key=lambda c: (
        c["total_delta_v_m_s"], c["flight_time_s"],
        c["departure_epoch_tdb_s"], c["candidate_id"],
    ))
    assert chosen == run["selected"]
    with localcontext() as context:
        context.prec = 60
        scale = Decimal("9.80665") * Decimal(450)
        final = Decimal(2000)
        for name in ("departure_delta_v_m_s", "arrival_delta_v_m_s"):
            final *= (-Decimal.from_float(chosen[name]) / scale).exp()
        assert abs(final - Decimal.from_float(chosen["final_mass_kg"])) <= Decimal("1e-9")
        assert Decimal(2000) * (1 - (-Decimal(100) / scale).exp()) < 50
    assert len(run["states"]) == 121
    for index, state in enumerate(run["states"]):
        assert (state["origin"], state["orientation"]) == ("SSB", "J2000")
        assert state["epoch_tdb_s"] == chosen["departure_epoch_tdb_s"] + (
            chosen["flight_time_s"] * index / 120
        )
        assert all(math.isfinite(v) for v in (
            state["epoch_tdb_s"], *state["position_m"], *state["velocity_m_s"],
        ))
    for name, index, excess in (
        ("departure", 0, "departure_v_infinity_m_s"),
        ("arrival", -1, "arrival_v_infinity_m_s"),
    ):
        endpoint = run["endpoints"][name]
        body, state = endpoint["body_state"], run["states"][index]
        assert state["epoch_tdb_s"] == body["epoch_tdb_s"]
        # Independent sum-of-squares arithmetic, not the runner's math.dist.
        pos = sum((a - b)**2 for a, b in zip(state["position_m"], body["position_m"]))**0.5
        vel = sum((state["velocity_m_s"][i] - body["velocity_m_s"][i]
                   - chosen[excess][i])**2 for i in range(3))**0.5
        assert pos <= 100 and vel <= .001
        assert abs(pos - endpoint["position_error_m"]) <= 1e-10
        assert abs(vel - endpoint["velocity_error_m_s"]) <= 1e-10
for relative, expected in data["identity"]["file_sha256"].items():
    assert sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
baseline = json.loads((ROOT / "tests/data/reference_kernel_baseline.json").read_text())
assert [{k: item[k] for k in ("name", "sha256")}
        for item in data["provenance"]["manifest"]["spice"]["kernels"]] == baseline["kernels"]
print("R1.1 offline audit passed: 3960 attempts, 242 states, Decimal60 mass/reserve, "
      "selection, complete payload identity, endpoints and source/kernel hashes; no native calls")
