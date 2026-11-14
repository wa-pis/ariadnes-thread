"""Check ADR0196 on artificial sources and saved, independently replayed operands."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from runpy import run_path
import subprocess
import sys
from typing import Any

import pytest

ART = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
type Row = dict[str, Any]


@pytest.fixture(scope="module")
def modules() -> tuple[Row, Row]:
    return tuple(run_path(str(ART / f"0197-far-{role}.py")) for role in ("fixtures", "audit"))


def idle() -> None:
    pass


def ignore(_kind: str, _row: Row) -> None:
    pass


class Rows:
    def __init__(self) -> None:
        self.records: list[tuple[str, Row]] = []

    def append(self, kind: str, row: Row) -> None:
        self.records.append((kind, row))


def test_synthetic_full_cap_callback_schedule(modules: tuple[Row, Row]) -> None:
    fixture, _ = modules
    solve = fixture["_solve"](True)
    nfev = []
    for first_step, max_step in ((1., 5.), (.5, 2.5)):
        called, offsets = 0, set()

        def rhs(at_tdb_s: float, y: Any) -> list[float]:
            nonlocal called
            called += 1
            offsets.add(at_tdb_s)
            return y.tolist()

        result = solve(rhs, (0., 16_000.), [0.]*6, method=fixture["_ScriptedController"],
                       t_eval=fixture["OFFSETS"], rtol=1e-12, atol=[1e-10]*6, max_step=max_step,
                       first_step=first_step)
        assert result.success and result.nfev == called
        assert len(offsets) > called * .8
        assert result.t.tolist() == list(range(0, 16_001, 50))
        assert result.y.tolist()[0][0] == 0. < result.y.tolist()[0][-1]
        nfev.append(called)
    assert nfev == [52_876, 105_052]
    assert (sum(nfev) - 2 - 2*321*3) // 12 == 13_000
    assert 160_000 - sum(nfev) == 2_072


@pytest.fixture(scope="module")
def rhs_sample(modules: tuple[Row, Row]) -> tuple[Row, Row, Row]:
    fixture, _ = modules
    study = fixture["_load_study"]()
    inputs = fixture["bundle"]()
    budget = study.new_budget(lambda: 0., 0.)
    row = {"profile": "normal", "index": 206, "global_index": 206, "usage": "trial"}
    s = 14_023.12123153423
    study.build_rhs(inputs, fixture["provider"], budget, row, s, fixture["_correction"](s))
    assert row["completed"] and row["lo_s"] != 0
    return inputs, row, study


def test_rhs_and_selected_source_replay(
    modules: tuple[Row, Row], rhs_sample: tuple[Row, Row, Row],
) -> None:
    _, audit = modules
    inputs, row, study = rhs_sample
    assessed, counts = Rows(), study.new_budget(lambda: 0., 0.)
    study._observation(inputs, assessed, counts, "normal", "rhs", row, 17, 274)
    assert counts.counts["record_evaluations"]["completed"] == 6
    replay = audit["RhsReplay"](inputs, idle, counts.event).rhs(row)
    oracle = audit["assess_observation"](inputs["initial"], replay["motion"],
        audit["OLD"].split.source_rows(row, inputs), replay["geometry"],
        inputs["gm_m3_s2"], inputs["radii_m"], counts.event, idle)
    assert oracle["passed"] and oracle == assessed.records[0][1]["assessment"]
    assert counts.counts["record_evaluations"]["completed"] == 12


@pytest.mark.parametrize(("key", "reason"), [
    ("force", "Moon field"),
    ("low_epoch", "signed epoch lo"),
    ("observer", "source requests"),
])
def test_rhs_replay_rejects_tampered_operands(
    modules: tuple[Row, Row], rhs_sample: tuple[Row, Row, Row], key: str, reason: str,
) -> None:
    _, audit = modules
    inputs, saved, _ = rhs_sample
    row = deepcopy(saved)
    if key == "force":
        row["geometry"]["Moon"]["acceleration_m_s2"][0] *= 1.1
    elif key == "low_epoch":
        row["lo_s"] = 0.
    else:
        row["requests"][3]["observer"] = "SSB"
    with pytest.raises(ValueError, match=reason):
        audit["RhsReplay"](inputs, idle, ignore).rhs(row)


def test_native_preflight_guard_keeps_safe_prefix_and_blocks_marker(modules: tuple[Row, Row]) -> None:
    fixture, audit = modules
    rows = Rows()
    with pytest.raises(ValueError, match="Moon exclusion sphere"):
        fixture["produce"](rows, outcome="guard-failure")
    assert [kind for kind, _ in rows.records] == ["node"]*321 + ["native_start", "native_guard", "native_guard"]
    last = rows.records[-1][1]
    assert last["body"] == "Moon" and last["group"] == 0 and not last["passed"]
    result = audit["verify"](fixture["bundle"](outcome="guard-failure"), rows.records, ignore, idle, status="partial")
    assert result["audit_status"] == "partial" and result["marker_status"] == "unavailable"
    assert result["partial_record_counts"] == {"node": 321, "native_start": 1, "native_guard": 2}


def test_rhs_cap_stops_before_artificial_provider(
    rhs_sample: tuple[Row, Row, Row],
) -> None:
    inputs, _, study = rhs_sample
    counts = study.new_budget(lambda: 0., 0.)
    counts.counts["rhs"] = {"attempted": 160_000, "returned": 0, "completed": 160_000}

    def fail_provider(*_args: Any) -> None:
        pytest.fail("state read over cap")

    with pytest.raises(ValueError, match="rhs attempt cap"):
        study.build_rhs(inputs, fail_provider, counts, {}, 999., [0.]*6)
    assert counts.counts["rhs"]["attempted"] == 160_000


@pytest.mark.parametrize(("rows", "reasons"), [
    ((-1, 1), ()),
    ((-1, -1), ("no-outward-pair",)),
    ((-1, 0, 1), ("exact-equality", "no-outward-pair")),
    ((1, -1), ("inward-pair", "no-outward-pair")),
    ((-1, 1, -1, 1), ("inward-pair", "multiple-outward-pairs")),
    ((-1, 1, 1), ("nonpositive-radial-endpoint",)),
])
def test_independent_direction_edge_classes(
    modules: tuple[Row, Row], rows: tuple[int, ...], reasons: tuple[str, ...],
) -> None:
    _, audit = modules
    fixture = Rows()
    direction = audit["Directions"]("test", fixture.append)
    for j, sign in enumerate(rows):
        velocity = 0. if "nonpositive-radial-endpoint" in reasons else 1.
        direction.add(audit["_direction"]((float(j), (18_374_000.+sign, 0., 0., velocity, 0., 0.), (0.,)*6)))
    assert direction.summary()["reasons"] == list(reasons)
    assert len(fixture.records) == len(rows)
    assert [item["range_sign"] for _, item in fixture.records] == list(rows)


def test_marker_requires_agreement_between_all_six_grids(modules: tuple[Row, Row]) -> None:
    _, audit = modules
    grids = {
        f"{origin}_{name}": {"rows": 321, "reasons": [], "first_outward_tdb_s": [100., 150.]}
        for origin in ("rk4", "dop853") for name in ("normal", "tighter")
    }
    grids["mesh_normal"] = {"rows": 16_001, "reasons": [], "first_outward_tdb_s": [125., 126.]}
    grids["mesh_tighter"] = {"rows": 32_001, "reasons": [], "first_outward_tdb_s": [125.5, 126.]}
    qualified = audit["_marker"](grids)
    assert qualified["marker_status"] == "marker-bracketed"
    assert qualified["common_bracket_tdb_s"] == [100., 150.]
    assert qualified["native_overlap_tdb_s"] == [125.5, 126.]
    for label, invalid, reason in (
        ("dop853_tighter", [150., 200.], "common-brackets-disagree"),
        ("mesh_tighter", [98., 98.5], "mesh-bracket-outside-common"),
        ("mesh_tighter", [126., 126.5], "mesh-brackets-do-not-overlap"),
    ):
        altered = deepcopy(grids)
        altered[label]["first_outward_tdb_s"] = invalid
        failed = audit["_marker"](altered)
        assert failed["marker_status"] == "marker-not-established"
        assert failed["marker_reason"] == reason
        assert failed["native_overlap_tdb_s"] is None


def test_independent_audit_and_bundle_import_under_isolated_stdlib() -> None:
    script = """
import importlib.abc
import json
from runpy import run_path
import sys
blocked = {"space_nav", "tudatpy", "spiceypy", "scipy", "numpy", "ariadna_far_study"}
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in blocked:
            raise RuntimeError("unexpected scientific or study import " + fullname)
g = Guard()
sys.meta_path.insert(0, g)
fixture = run_path(sys.argv[1])
audit = run_path(sys.argv[2])
report = audit["verify"](fixture["bundle"](), (), lambda *args: None, lambda: None, status="partial")
assert all(k.split(".")[0] not in blocked for k in sys.modules)
print(json.dumps(report))
"""
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", script,
                             str(ART / "0197-far-fixtures.py"), str(ART / "0197-far-audit.py")],
                            check=True, capture_output=True, text=True, timeout=5)
    report = json.loads(result.stdout)
    assert report["marker_status"] == "unavailable"
    assert all(report[key] == 0 for key in ("scientific_imports", "kernel_loads", "spacecraft_propagations"))


@pytest.mark.parametrize(("outcome", "expected"), [
    ("no-crossing", ["no-outward-pair"]),
    ("inward", ["inward-pair", "no-outward-pair"]),
    ("equality", ["exact-equality", "no-outward-pair"]),
])
def test_complete_negative_direction_grids(
    modules: tuple[Row, Row], outcome: str, expected: list[str],
) -> None:
    fixture, audit = modules
    inputs = fixture["bundle"](outcome=outcome)["initial"]
    initial = inputs["position_m"] + inputs["velocity_m_s"]
    start = inputs["epoch_tdb_s"]
    # Use the generated trajectory and lunar record, with independent
    # Fraction/Decimal signs and arithmetic at every frozen sampling epoch.
    grids = {}
    for name, step in (("common", 50.), ("mesh_normal", 1.), ("mesh_tighter", .5)):
        history = audit["Directions"](name, ignore)
        for j in range(1 + int(16_000/step)):
            elapsed = j * step
            at = start + elapsed
            state = tuple(fixture["_state"](initial, elapsed))
            moon = tuple(fixture["_body_si"]("Moon", at))
            history.add(audit["_direction"]((at, state, moon)))
        grids[name] = history.summary()
    common = grids.pop("common")
    for origin in ("rk4", "dop853"):
        for profile in ("normal", "tighter"):
            grids[f"{origin}_{profile}"] = common
    verdict = audit["_marker"](grids)
    assert verdict["marker_status"] == "marker-not-established"
    assert verdict["marker_reason"] == dict.fromkeys(grids, expected)
    assert verdict["common_bracket_tdb_s"] is None and verdict["native_overlap_tdb_s"] is None
