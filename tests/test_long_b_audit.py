"""Read-only audit checks on artificial operands and adversarial saved rows."""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from runpy import run_path
from types import SimpleNamespace
from typing import Any

import pytest

from test_long_b_adaptive import LONGER, evaluate

ARTIFACTS = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
AUDIT = run_path(str(ARTIFACTS / "0186-long-b-audit.py"))
type Row = dict[str, Any]


def test_extension_rhs_rebuild_does_not_trust_saved_earth_field() -> None:
    radii = dict.fromkeys(LONGER["BODIES"], 1.)
    row = evaluate(LONGER, 512.123, radii)
    bundle = {
        "initial": {"position_m": [-4.7e10, 1.29e11, 5.57e10],
                    "velocity_m_s": [-3e4, -9e3, -2.4e3],
                    "epoch_tdb_s": 978995455.2304223},
        "radii_m": radii,
        "gm_m3_s2": dict.fromkeys(LONGER["BODIES"], 1e12),
    }
    assert AUDIT["reconstruct_row"](row, bundle)["derivative"] == row["derivative"]
    bad = deepcopy(row)
    bad["geometry"]["Earth"]["acceleration_m_s2"][0] *= -1
    with pytest.raises(ValueError, match="Earth field"):
        AUDIT["reconstruct_row"](bad, bundle)
    bad = deepcopy(row)
    bad["bodies"]["Earth"]["epoch_tdb_s"] += 1.
    with pytest.raises(ValueError, match="state request/source provenance"):
        AUDIT["reconstruct_row"](bad, bundle)


def test_extension_sampling_follows_attempt_order_and_saved_trial_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    t0 = 2.**30
    early = [0., .125, .25, .375, .5, .625, .75]
    # A rejected trial visited 349.75 before the next attempt visited 301.
    # Both callbacks belong to the first new window; only index 8 is selected.
    times = early + [300., 349.75, 301., 350., 350.01, 401., 451., 501., 551., 600.]
    outputs = [{"elapsed_s": i*50., "index": i, "derivative": []} for i in range(13)]
    rhs = [{"elapsed_s": t, "index": i, "global_index": i, "completed": True}
           for i, t in enumerate(times)]
    selected_rhs = [0, 1, 2, 3, 4, 5, 6, 8, 11, 12, 13, 14, 15]
    trial_map = {8: 31, 9: 32}
    for row in (*outputs, *rhs):
        exact = Fraction(t0) + Fraction(row["elapsed_s"])
        hi = float(exact)
        row.update(hi_tdb_s=hi, lo_s=float(exact-Fraction(hi)))

    def observation(kind: str, row: Row) -> Row:
        return {"profile":"normal", "kind":kind,"index":row["index"],
                "trial_index":trial_map.get(row["global_index"]) if kind == "rhs" else None,
                "hi_tdb_s":row["hi_tdb_s"],
                "exact_tdb_s":str(Fraction(row["hi_tdb_s"])+Fraction(row["lo_s"])),
                "assessment":{"passed":True}, "progress":{}}

    report = {"status":"partial", "profiles":[{"name":"normal", "outputs":outputs}],
              "observations":[observation("output",row) for row in outputs]
              + [observation("rhs",rhs[i]) for i in selected_rhs]}
    cache = {id(row): {"motion":{}, "geometry":{}} for row in (*outputs,*rhs)}
    bundle = {"initial":{"epoch_tdb_s":t0}, "gm_m3_s2":{}, "radii_m":{}}

    def stub_reference(*args: Any, **kwargs: Any) -> Row:
        return {"passed":True}

    def run(saved: Row) -> int:
        return AUDIT["replay_observations"](saved, bundle, SimpleNamespace(assess_observation=stub_reference),
                                            cache, {"normal":rhs}, trial_map, lambda:None,
                                            lambda _operation,_phase:None)

    # The source-row builder and field math are tested separately; here the
    # callback selection must stand on its own before that boundary.
    with monkeypatch.context() as substitute:
        substitute.setattr(AUDIT["split"], "source_rows", lambda *_: {})
        assert run(report) == 26
        replacement = dict(report, observations=deepcopy(report["observations"]))
        replacement["observations"][20] = observation("rhs",rhs[9])
        with pytest.raises(ValueError, match="fixed observation"):
            run(replacement)
        wrong_trial = dict(report, observations=deepcopy(report["observations"]))
        wrong_trial["observations"][20]["trial_index"] = 32
        with pytest.raises(ValueError, match="fixed observation"):
            run(wrong_trial)
        rhs[15]["completed"] = rhs[16]["completed"] = False
        with pytest.raises(ValueError, match="observation cap"):
            run(report)


def test_audit_clock_and_counter_boundaries() -> None:
    now = [10.]
    budget = AUDIT["Budget"](lambda: now[0], 0.)
    for _ in range(26):
        budget.event("native_telemetry","attempt")
        budget.event("native_telemetry","complete")
    with pytest.raises(ValueError, match="audit cap"):
        budget.event("native_telemetry","attempt")
    now[0] = 10.000001
    with pytest.raises(ValueError, match="audit deadline"):
        budget.event("rhs","attempt")
