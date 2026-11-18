"""Qualify R5.59h on fabricated sources only."""

from collections.abc import Callable
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from runpy import run_path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

type Row = dict[str, Any]

ART = Path(__file__).resolve().parents[1] / "docs/adr/experiments"


@pytest.fixture(scope="module")
def harness() -> tuple[Row, dict[str, ModuleType]]:
    study = run_path(str(ART / "0219-phase-study.py"))
    methods, _ = study["_methods"]()
    return study, methods


def inputs(folder: Path, case: str, methods: dict[str, ModuleType], *, size: int | None = None
           ) -> tuple[Path, str, Path]:
    source = folder / "r559h-artificial.json"
    fixture = methods["points"].fixture(case, methods)
    io = methods["io"]
    if size is not None:
        fixture["padding"] = ""
        fixture["padding"] = "x" * (size-len(io._wire(fixture)))
    raw = io._wire(fixture)
    source.write_bytes(raw)
    return source, io._sha(raw), folder / "r559h-artificial-output"


@pytest.mark.parametrize(("case", "status", "code"), [
    ("witness", "eligible-off-grid-witness", 0),
    ("refusal", "no-eligible-pair-on-local-interval", 2),
])
def test_artificial_isolated_screen_and_saved_readback(
    harness: tuple[Row, dict[str, ModuleType]], tmp_path: Path, case: str, status: str, code: int,
) -> None:
    study, methods = harness
    source, pin, output = inputs(tmp_path, case, methods, size=study["CAP"] if case == "refusal" else None)
    assert study["launch"](source, pin, output) == code
    io = methods["io"]
    completion = output / "completion.json"
    completion_pin = io._sha(completion.read_bytes())
    result = study["verify_result"](source, pin, output, completion_sha256=completion_pin)
    assert result["status"] == status and result["producer_status"] == status
    assert result["scope"] == "artificial" and result["commands"] is None
    assert result["source_bytes"] == source.stat().st_size
    for name in ("spice_queries", "kernel_accesses", "force_evaluations", "integrations", "r559i_attempts",
                 "r560_attempts"):
        assert result[name] == 0
    proof = result["independent_readback"]
    assert proof["status"] == status and proof["work"] == result["work"]
    if case == "witness":
        phase = Fraction(result["witness"]["phase_deg"])
        assert 150 < phase < 152 and phase.denominator > 1
        assert result["witness"]["signs"]
        assert any(row["point"] and row["point"]["eligible"] for row in result["rows"])
    else:
        assert result["witness"] is None
        assert proof["verified_leaves"] >= 2 and proof["unresolved"] == 0
        assert result["source_bytes"] == study["CAP"]
    assert sum(file.stat().st_size for file in output.iterdir()) <= study["CAP"]
    assert study["launch"](source, pin, output) == 3
    assert io._sha(completion.read_bytes()) == completion_pin


def test_reject_scope_and_byte_overflow(harness: tuple[Row, dict[str, ModuleType]], tmp_path: Path) -> None:
    study, methods = harness
    source, pin, dest = inputs(tmp_path, "refusal", methods, size=study["CAP"]+1)
    assert study["launch"](source, pin, dest) == 3
    assert not (dest / "completion.json").exists()
    assert not dest.exists()
    fake = {"scope": "retained", "reference": {}}
    raw = methods["io"]._wire(fake)
    source.write_bytes(raw)
    assert study["launch"](source, methods["io"]._sha(raw), dest) == 3
    assert not dest.exists()
    with pytest.raises(ValueError, match="artificial-only"):
        study["launch"](source.with_name("report.json"), pin, dest)


def test_reject_input_and_evidence_tampering(harness: tuple[Row, dict[str, ModuleType]], tmp_path: Path) -> None:
    study, methods = harness
    source, pin, dest = inputs(tmp_path, "refusal", methods)
    assert study["launch"](source, "0"*64, dest) == 3
    assert study["launch"](source, pin, dest) == 2
    io = methods["io"]
    witness = dest / "completion.json"
    completion_pin = io._sha(witness.read_bytes())
    report = dest / "report.json"
    raw = report.read_bytes()
    row = io._row(raw)
    row["commands"] = ["unauthorized"]
    report.write_bytes(io._wire(row))
    with pytest.raises(ValueError, match="authority binding"):
        study["verify_result"](source, pin, dest, completion_sha256=completion_pin)
    report.write_bytes(raw)
    with pytest.raises(ValueError, match="completion binding"):
        study["verify_result"](source, pin, dest, completion_sha256="1"*64)
    source.write_bytes(source.read_bytes()+b" ")
    with pytest.raises(ValueError, match="input hash"):
        study["verify_result"](source, pin, dest, completion_sha256=completion_pin)


def _fixed_fixture(methods: dict[str, ModuleType],
                   reason: Callable[[Fraction, Fraction, str, bool], str | None]
                   ) -> tuple[Row, Row]:
    # Abstract proof fixtures exercise all scheduler work independently of the geometry workload.
    def point(ref: Row, phase: Fraction, calls: Row) -> Row:
        return {"phase_deg": str(phase), "eligible": []}

    def bounds(ref: Row, lo: Fraction, hi: Fraction, sign: str, interval: ModuleType, *,
               independent: bool) -> Row:
        return {"reason": reason(lo, hi, sign, independent)}

    sa = {"reference": {}, "anchors": [point({}, Fraction(n), {}) for n in (150, 151, 152)]}
    return sa, methods | {"points": SimpleNamespace(point=point), "bounds": SimpleNamespace(bounds=bounds, validate_claim=lambda row: None)}


def test_exhaust_both_full_work_inventories_with_a_transition(
    harness: tuple[Row, dict[str, ModuleType]],
) -> None:
    study, methods = harness
    source, mock = _fixed_fixture(methods, lambda lo, hi, sign, independent: "guard" if sign == "negative" else None)
    report = study["_scan"](source, mock, lambda: None)
    proof = study["_audit"](source, report, mock, lambda: None)
    assert proof["status"] == report["status"] == study["UNKNOWN"]
    assert proof["unresolved"] == 64
    assert report["work"] == proof["work"] == study["CAPS"]
    assert len({row["point"]["phase_deg"] for row in report["rows"]}) == 126
    assert all(row["depth"] <= study["DEPTH"] for row in report["rows"])
    for key, count in study["CAPS"].items():
        counter = {key: count}
        with pytest.raises(ValueError, match="cap"):
            study["_charge"](counter, key, lambda: None)
        assert counter[key] == count


def test_gaps_and_disagreement_cannot_certify_refusal(harness: tuple[Row, dict[str, ModuleType]]) -> None:
    study, methods = harness
    source, mock = _fixed_fixture(methods, lambda lo, hi, sign, independent: "mass")
    report = study["_scan"](source, mock, lambda: None)
    hole = deepcopy(report)
    hole["rows"].pop()
    with pytest.raises(ValueError, match="coverage"):
        study["_audit"](source, hole, mock, lambda: None)
    missing_sign = deepcopy(report)
    del missing_sign["rows"][0]["bounds"]["negative"]
    with pytest.raises(ValueError, match="two signed"):
        study["_audit"](source, missing_sign, mock, lambda: None)
    _, disagree = _fixed_fixture(methods, lambda lo, hi, sign, ind: None if ind and sign == "negative" else "mass")
    assert study["_audit"](source, report, disagree, lambda: None)["status"] == study["UNKNOWN"]


def test_wall_cap_and_invalid_anchors(harness: tuple[Row, dict[str, ModuleType]], tmp_path: Path) -> None:
    study, methods = harness
    source, pin, dest = inputs(tmp_path, "refusal", methods)
    namespace = study["launch"].__globals__
    old = namespace["WALL_NS"]
    try:
        namespace["WALL_NS"] = 1
        assert study["launch"](source, pin, dest) == 3
    finally:
        namespace["WALL_NS"] = old
    assert not (dest / "completion.json").exists()
    io = methods["io"]
    record = io._row(source.read_bytes())
    record["anchors"][1]["phase_deg"] = "149"
    raw = io._wire(record)
    source.write_bytes(raw)
    assert study["launch"](source, io._sha(raw), dest) == 3
    assert (dest / "attempt.json").is_file()
    assert not (dest / "completion.json").exists()
    assert study["launch"](source, io._sha(raw), dest) == 3


def test_analytic_geometry_runs_at_full_work_cap(harness: tuple[Row, dict[str, ModuleType]]) -> None:
    study, methods = harness
    source = methods["points"].fixture("refusal", methods)
    actual = methods["bounds"].bounds

    def without_pruning(ref: Row, lo: Fraction, hi: Fraction, sign: str, interval: ModuleType, *,
                        independent: bool) -> Row:
        # Run the real interval formulas, but decline their proof to exercise worst-case work.
        return actual(ref, lo, hi, sign, interval, independent=independent) | {"reason": None}

    from time import monotonic_ns
    started = monotonic_ns()
    full = methods | {"bounds": SimpleNamespace(bounds=without_pruning,
                                                 validate_claim=methods["bounds"].validate_claim)}

    def check() -> None:
        study["_clock"](started, study["WALL_NS"])

    report = study["_scan"](source, full, check)
    proof = study["_audit"](source, report, full, check)
    assert proof["status"] == study["UNKNOWN"] and proof["unresolved"] == 64
    assert report["work"] == proof["work"] == study["CAPS"]
    check()


def test_exact_mass_equality_cannot_exclude(harness: tuple[Row, dict[str, ModuleType]]) -> None:
    import math
    _, methods = harness
    q = Fraction(1000 / (9.80665 * 450))
    e = Fraction(math.nextafter(1e-6, math.inf))
    arrival_s = Fraction(1500) / q + e
    exclude = methods["bounds"].dry_floor_exclusion
    for independent in (False, True):
        assert exclude(Fraction(0), arrival_s, independent=independent) == (False, Fraction(1500))
        assert exclude(Fraction(0), arrival_s + Fraction(1, 10**12), independent=independent)[0]
        assert not exclude(Fraction(0), arrival_s - Fraction(1, 10**12), independent=independent)[0]


def test_signed_bounds_across_real_artificial_guard_transition(
    harness: tuple[Row, dict[str, ModuleType]],
) -> None:
    from decimal import Decimal

    _, methods = harness
    source = methods["points"].fixture("transition", methods)
    ref = source["reference"]
    assert [row["branches"]["positive"]["reason"] for row in source["anchors"]] == ["guard", "guard", None]
    for independent in (False, True):
        for sign in ("positive", "negative"):
            enclosure = methods["bounds"].bounds(
                ref, Fraction(151), Fraction(152), sign, methods["interval"], independent=independent)
            if sign == "positive":
                assert enclosure["reason"] != "guard"
            low, high = map(Decimal, enclosure["arrival_speed_bounds_m_s"])
            for phase in map(Fraction, ("151", "605/4", "303/2", "607/4", "152")):
                branch = methods["points"].point(ref, phase, methods)["branches"][sign]
                assert low <= Decimal(branch["independent_speed_m_s"]) <= high


def test_refuse_unverified_output_and_mass_explanation(
    harness: tuple[Row, dict[str, ModuleType]], tmp_path: Path,
) -> None:
    study, methods = harness
    cap = study["CAP"] - 3 * study["SMALL"]
    io = methods["io"]
    with pytest.raises(ValueError, match="output byte cap"):
        io._put(tmp_path / "report.json", {"payload": "x" * cap}, cap)
    assert not (tmp_path / "report.json").exists()

    fixture = methods["points"].fixture("refusal", methods)
    report = study["_scan"](fixture, methods, lambda: None)
    proof = next(bound for row in report["rows"] for bound in row["bounds"].values()
                 if bound["reason"] == "mass")
    proof["consumed_mass_lower_kg"] = "1500"
    with pytest.raises(ValueError, match="saved mass proof"):
        study["_audit"](fixture, report, methods, lambda: None)
