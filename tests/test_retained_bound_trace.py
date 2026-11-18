"""Qualify the archive-bound trace on fabricated evidence, never retained inputs."""

from collections import Counter, deque
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
from runpy import run_path
import sys
from types import CodeType, ModuleType
from typing import Any

import pytest

ART = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
ROLES = (
    "grid_attempt", "grid_report", "grid_receipt", "grid_audit",
    "study_attempt", "study_report", "study_receipt", "study_completion", "study_audit",
)
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
CELLS = (
    (62, Fraction(150), Fraction(4801, 32)),
    (94, Fraction(151), Fraction(4833, 32)),
    (125, Fraction(4863, 32), Fraction(152)),
)
CAP = 4 * 1024**2
RESERVE = 65_536
MIN_SOURCE_BYTES = 2_280_855
type Row = dict[str, Any]
type Methods = dict[str, ModuleType]


def wire(row: Any) -> bytes:
    return (json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def row_digest(row: Any) -> str:
    return sha256(wire(row)).hexdigest()


def _put(path: Path, row: Row) -> str:
    path.write_bytes(wire(row))
    return digest(path)


def build_profile(root: Path, methods: Methods, *, case: str = "witness") -> Row:
    """Fabricate archival shapes; evaluate only six fake bounds and three fake points.

    Other grid/study rows and the old audits are format fixtures, not independently
    evaluated scientific evidence. Padding exercises the complete input byte volume.
    """
    root.mkdir()
    design = json.loads((ART / "0224-retained-trace-contract.json").read_bytes())
    old_methods = design["historical_method_identity"]
    fixture = methods["points"].fixture(case, methods)
    ref = fixture["reference"]
    anchors = fixture["anchors"]
    saved: dict[int, Row] = {}
    for index, lo, hi in CELLS:
        saved[index] = dict(
            lo_deg=str(lo), hi_deg=str(hi), depth=5, action="unresolved",
            point=methods["points"].point(ref, (lo + hi) / 2, methods),
            bounds={sign: methods["bounds"].bounds(ref, lo, hi, sign, methods["interval"])
                    for sign in ("positive", "negative")},
        )

    inputs = {role: root / (role + ".json") for role in ROLES}
    pins: dict[str, str] = {}
    upstream = {name: sha256(("fabricated-upstream-" + name).encode()).hexdigest() for name in FILES}
    flags = dict(
        spice_queries=0, kernel_accesses=0, force_evaluations=0, integrations=0,
        r560_attempts=0, live_authorized=False, physical_launch_authorized=False,
        physical_status="physical-join-not-established",
    )
    grid_head = flags | dict(
        schema="ariadna-r559f-phase-evidence-v1", stage="R5.59f", mode="artificial",
        synthetic=True, r559f_attempts=0, source_pins=upstream,
        source_sha256=old_methods, run_id="a" * 32,
    )
    attempt = grid_head | dict(wall_ns=30_000_000_000)
    pins["grid_attempt"] = _put(inputs["grid_attempt"], attempt)
    grid_rows: list[Row] = []
    for index in range(360):
        anchor = deepcopy(anchors[index % len(anchors)])
        anchor.update(index=index, angle_word=(math.tau * index / 360).hex())
        anchor["pairs"] = [pair | dict(index=index, command_words=None) for pair in anchor["pairs"]]
        grid_rows.append(anchor)
    grid_work = dict(phase_positions=360, mars_roots=720,
                     pairs=sum(len(row["pairs"]) for row in grid_rows))
    report = grid_head | dict(
        status="no-eligible-pair-on-grid", reason="no-eligible-pair", command_words=None,
        selected=None, reference=ref, rows=grid_rows, work=grid_work,
        source_bytes=13_363, archive_open_attempts=list(FILES),
        attempt_sha256=pins["grid_attempt"],
        artificial_fixture="Fabricated lineage and unselected rows; no original study or old audit executed.",
        artificial_padding="x" * RESERVE,
    )
    pins["grid_report"] = _put(inputs["grid_report"], report)
    receipt = grid_head | dict(
        status=report["status"], attempt_sha256=pins["grid_attempt"],
        report_sha256=pins["grid_report"], elapsed_before_receipt_ns=1_000_000,
    )
    pins["grid_receipt"] = _put(inputs["grid_receipt"], receipt)
    grid_source_pins = {name: pins["grid_" + name.removesuffix(".json")]
                        for name in FILES[:3]}
    pairs = [pair for row in grid_rows for pair in row["pairs"]]
    pair_fields = ("index", "roots", "reason", "total_delta_v_m_s", "oracle_total_delta_v_m_s")
    least = min(pairs, key=lambda row: row["total_delta_v_m_s"])
    grid_audit = flags | dict(
        schema="ariadna-r559f-saved-grid-audit-v1", saved_grid_verified=True,
        original_invocation_completed=False, original_new_completion_witness=False,
        source_pins=grid_source_pins, source_sha256=old_methods,
        evidence_bytes=sum(inputs[role].stat().st_size for role in ROLES[:3]),
        archive_reopens=0, new_r559f_attempts=0, new_phase_scans=0, new_conic_solves=0,
        wall_ns=30_000_000_000, elapsed_ns=1_000_000,
        original_elapsed_before_receipt_ns=receipt["elapsed_before_receipt_ns"],
        candidate_id="artificial-moon-mars", work=grid_work, source_bytes=13_363,
        status=report["status"], reason="no-eligible-pair", commands=None,
        state_checks=360, adapter_uses=0,
        branch_decisions={sign: dict(Counter(row["branches"][sign]["reason"] or "passes"
                                             for row in grid_rows))
                          for sign in ("positive", "negative")},
        pair_decisions={"commanded-dry-floor": len(pairs)},
        least_recorded_pair={key: least[key] for key in pair_fields},
        least_independent_pair={key: least[key] for key in pair_fields},
        zero_phase_delta_v_m_s=grid_rows[0]["pairs"][0]["total_delta_v_m_s"],
        artificial_fixture="Format fixture only; no old scientific audit replay.",
    )
    pins["grid_audit"] = _put(inputs["grid_audit"], grid_audit)

    source_pins = grid_source_pins | {"audit.json": pins["grid_audit"]}
    old_work = dict(cells=126, bounds=252, points=129, point_roots=258, point_pairs=258)
    study_head = flags | dict(
        schema="ariadna-r559i-phase-evidence-v1", stage="R5.59i-preparation", scope="artificial",
        r559i_attempts=0, commands=None, r559f_replays=0,
        source_pins=source_pins, methods_sha256=old_methods, run_id="b" * 32,
        source_bytes=sum(inputs[role].stat().st_size for role in ROLES[:4]),
    )
    study_attempt = study_head | dict(wall_ns=30_000_000_000)
    pins["study_attempt"] = _put(inputs["study_attempt"], study_attempt)
    queue = deque([(Fraction(150), Fraction(151), 0), (Fraction(151), Fraction(152), 0)])
    rows: list[Row] = []
    while queue:
        lo, hi, depth = queue.popleft()
        index = len(rows)
        if index in saved:
            row = saved[index]
            assert (row["lo_deg"], row["hi_deg"]) == (str(lo), str(hi))
        else:
            point = deepcopy(anchors[0])
            point["phase_deg"] = str((lo + hi) / 2)
            row = dict(lo_deg=str(lo), hi_deg=str(hi), depth=depth, point=point,
                       bounds=deepcopy(saved[62]["bounds"]),
                       action="split" if depth < 5 else "unresolved")
        rows.append(row)
        if depth < 5:
            mid = (lo + hi) / 2
            queue.extend(((lo, mid, depth + 1), (mid, hi, depth + 1)))
    assert len(rows) == 126
    study_report = study_head | dict(
        status="inconclusive", witness=None, work=old_work, rows=rows,
        attempt_sha256=pins["study_attempt"],
        artificial_fixture="Only selected rows have evaluated fabricated points and bounds.",
    )
    pins["study_report"] = _put(inputs["study_report"], study_report)
    study_receipt = study_head | dict(
        attempt_sha256=pins["study_attempt"], report_sha256=pins["study_report"], elapsed_ns=2_000_000,
    )
    pins["study_receipt"] = _put(inputs["study_receipt"], study_receipt)
    proof = dict(status="inconclusive", work=old_work, unresolved=64, verified_leaves=0)
    completion = dict(receipt_sha256=pins["study_receipt"], proof=proof,
                      run_id=study_head["run_id"], exit_code=2, elapsed_ns=3_000_000)
    pins["study_completion"] = _put(inputs["study_completion"], completion)
    study_audit = study_report | dict(
        producer_status="inconclusive", independent_readback=proof,
        artificial_fixture="Echoed format fixture; no old scientific audit was evaluated.",
    )
    pins["study_audit"] = _put(inputs["study_audit"], study_audit)
    selected = []
    for index, lo, hi in CELLS:
        row = saved[index]
        selected.append(dict(
            row_index=index, lo_deg=str(lo), hi_deg=str(hi), midpoint_deg=str((lo + hi) / 2),
            action="unresolved", depth=5, row_sha256=row_digest(row),
            point_sha256=row_digest(row["point"]),
            saved_default_bounds_sha256={sign: row_digest(row["bounds"][sign])
                                         for sign in ("positive", "negative")},
        ))
    assert MIN_SOURCE_BYTES <= sum(path.stat().st_size for path in inputs.values()) <= CAP
    return dict(scope="artificial", inputs=inputs, pins=pins,
                reference_sha256=row_digest(ref), selected_rows=selected)


@pytest.fixture(scope="module")
def runner() -> Row:
    return run_path(str(ART / "0225-retained-trace.py"))


@pytest.fixture(scope="module")
def methods(runner: Row) -> Methods:
    return runner["_methods"]()


@pytest.fixture(scope="module")
def profile(methods: Methods, tmp_path_factory: pytest.TempPathFactory) -> Row:
    return build_profile(tmp_path_factory.mktemp("r559m-artificial") / "source", methods)


@pytest.fixture(scope="module")
def outcome(runner: Row, profile: Row) -> tuple[Path, Row]:
    output = profile["inputs"]["grid_attempt"].parent.with_name("r559m-artificial-result")
    return output, runner["run"](output, profile)


def test_full_volume_profile_is_fabricated_and_pinned(profile: Row) -> None:
    assert set(profile["inputs"]) == set(profile["pins"]) == set(ROLES)
    assert all(digest(path) == profile["pins"][role] for role, path in profile["inputs"].items())
    assert MIN_SOURCE_BYTES <= sum(path.stat().st_size for path in profile["inputs"].values()) <= CAP
    assert [row["row_index"] for row in profile["selected_rows"]] == [62, 94, 125]
    reference = json.loads(profile["inputs"]["grid_report"].read_bytes())["reference"]
    assert reference["normalized"]["scope"] == "artificial"
    assert reference["normalized"]["candidate_id"] == "artificial-moon-mars"


def test_full_matrix_matches_controls_saved_bounds_and_readback(
    runner: Row, methods: Methods, profile: Row, outcome: tuple[Path, Row],
) -> None:
    output, report = outcome
    assert report["scope"] == "artificial" and report["commands"] is None
    assert report["work"]["bounds"] == 48 and report["work"]["points"] == 0
    assert report["work"]["oracle_mass"] == 12
    assert 0 < report["work"]["events"] <= 8192
    expected = [(index, domain, str(a), str(b), sign, ind)
                for index, lo, hi in CELLS
                for domain, a, b in (("cell", lo, hi), ("singleton", (lo + hi) / 2, (lo + hi) / 2))
                for sign in ("positive", "negative") for ind in (False, True)]
    assert len(report["rows"]) == 24
    assert [(row["row_index"], row["domain"], row["lo_deg"], row["hi_deg"], row["sign"], row["independent"])
            for row in report["rows"]] == expected
    saved = json.loads(profile["inputs"]["study_report"].read_bytes())["rows"]
    historical = 0
    for row in report["rows"]:
        assert wire(row["trace"]["result"]) == wire(row["control"])
        methods["trace_schema"].verify_trace(row["trace"], row["control"])
        checks = row["containment"]
        assert checks["status"] == "verified" and checks["containment_checks"] == 16
        if row["domain"] == "cell" and row["independent"] is False:
            assert wire(row["control"]) == wire(saved[row["row_index"]]["bounds"][row["sign"]])
            historical += 1
    assert historical == 6
    assert any(row["containment"]["clearance_status"] == "not-reached" for row in report["rows"])
    assert {path.name for path in output.iterdir()} == set(FILES)
    assert sum(path.stat().st_size for path in output.iterdir()) + RESERVE <= CAP
    assert runner["audit"](output, profile, digest(output / "completion.json")) == report
    proof = report["independent_readback"]
    assert proof["new_bounds"] == proof["new_points"] == 0
    assert proof["oracle_mass_calls"] == 6
    assert all(report[key] == 0 for key in ("spice_queries", "kernel_accesses", "force_evaluations",
                                           "integrations", "r559i_attempts", "r560_attempts"))


def test_artificial_refusal_preserves_mass_before_clearance_disposition(
    runner: Row, methods: Methods, tmp_path: Path,
) -> None:
    profile = build_profile(tmp_path / "source", methods, case="refusal")
    report = runner["run"](tmp_path / "r559m-artificial-refusal", profile)
    assert len(report["rows"]) == 24
    assert all(row["control"]["reason"] == "mass" for row in report["rows"])
    assert all(row["containment"]["clearance_status"] == "not-reached" for row in report["rows"])
    assert report["work"]["bounds"] == 48 and report["work"]["oracle_mass"] == 12


def test_existing_output_and_wrong_completion_pin_preserve_evidence(
    runner: Row, profile: Row, outcome: tuple[Path, Row],
) -> None:
    output, _ = outcome
    before = {path.name: digest(path) for path in output.iterdir()}
    with pytest.raises(ValueError):
        runner["run"](output, profile)
    with pytest.raises(ValueError):
        runner["audit"](output, profile, "0" * 64)
    assert {path.name: digest(path) for path in output.iterdir()} == before


@pytest.mark.parametrize("fault", ["control", "phase", "summary", "work"])
def test_resealed_saved_output_tampering_fails_independent_readback(
    runner: Row, profile: Row, outcome: tuple[Path, Row], tmp_path: Path, fault: str,
) -> None:
    original, _ = outcome
    output = tmp_path / ("r559m-artificial-resealed-" + fault)
    output.mkdir()
    for path in original.iterdir():
        (output / path.name).write_bytes(path.read_bytes())
    report = json.loads((output / "report.json").read_bytes())
    if fault == "control":
        report["rows"][0]["control"]["reason"] = "mass"
    elif fault == "phase":
        report["rows"][0]["lo_deg"] = "151"
    elif fault == "summary":
        report["summary"] = {}
    else:
        report["work"]["points"] = 1
    report_pin = _put(output / "report.json", report)
    receipt = json.loads((output / "receipt.json").read_bytes())
    receipt["report_sha256"] = report_pin
    receipt_pin = _put(output / "receipt.json", receipt)
    completion = json.loads((output / "completion.json").read_bytes())
    completion["receipt_sha256"] = receipt_pin
    complete_pin = _put(output / "completion.json", completion)
    with pytest.raises(ValueError):
        runner["audit"](output, profile, complete_pin)


def _rebind_profile(profile: Row, root: Path) -> Row:
    root.mkdir()
    copied = deepcopy(profile)
    copied["inputs"] = {role: root / path.name for role, path in profile["inputs"].items()}
    for role, path in copied["inputs"].items():
        path.write_bytes(profile["inputs"][role].read_bytes())
    return copied


@pytest.mark.parametrize("fault", ["pin", "scope", "reference", "row-order", "phase", "bound", "grid-chain", "study-chain"])
def test_source_scope_phase_control_and_lineage_tampering_fail_closed(
    runner: Row, profile: Row, tmp_path: Path, fault: str,
) -> None:
    copied = _rebind_profile(profile, tmp_path / "source")
    if fault == "scope":
        copied["scope"] = "retained"
    elif fault == "reference":
        copied["reference_sha256"] = "0" * 64
    elif fault == "row-order":
        copied["selected_rows"].reverse()
    elif fault == "phase":
        copied["selected_rows"][0]["midpoint_deg"] = "150"
    elif fault == "bound":
        copied["selected_rows"][0]["saved_default_bounds_sha256"]["positive"] = "0" * 64
    else:
        role = "grid_report" if fault == "pin" else "grid_receipt" if fault == "grid-chain" else "study_completion"
        row = json.loads(copied["inputs"][role].read_bytes())
        row["artificial_padding"] = "tampered" if fault == "pin" else row.get("artificial_padding", "")
        if fault == "grid-chain":
            row["report_sha256"] = "0" * 64
        elif fault == "study-chain":
            row["receipt_sha256"] = "0" * 64
        _put(copied["inputs"][role], row)
        if fault != "pin":
            copied["pins"][role] = digest(copied["inputs"][role])
    output = tmp_path / ("r559m-artificial-fault-" + fault)
    with pytest.raises(ValueError):
        runner["run"](output, copied)
    assert not (output / "completion.json").exists()


def test_full_source_inventory_byte_cap_prevents_completion(
    runner: Row, profile: Row, tmp_path: Path,
) -> None:
    copied = _rebind_profile(profile, tmp_path / "source")
    source = copied["inputs"]["grid_report"]
    row = json.loads(source.read_bytes())
    row["artificial_padding"] = "x" * CAP
    copied["pins"]["grid_report"] = _put(source, row)
    output = tmp_path / "r559m-artificial-oversize-source"
    with pytest.raises(ValueError, match="cap"):
        runner["run"](output, copied)
    assert not (output / "completion.json").exists()


def test_rechained_grid_method_metadata_tampering_is_rejected_by_binder(
    runner: Row, profile: Row, tmp_path: Path,
) -> None:
    copied = _rebind_profile(profile, tmp_path / "source")
    records = {role: json.loads(path.read_bytes()) for role, path in copied["inputs"].items()}
    records["grid_report"]["source_sha256"]["bounds"] = "0" * 64
    copied["pins"]["grid_report"] = _put(copied["inputs"]["grid_report"], records["grid_report"])
    records["grid_receipt"]["report_sha256"] = copied["pins"]["grid_report"]
    copied["pins"]["grid_receipt"] = _put(copied["inputs"]["grid_receipt"], records["grid_receipt"])
    grid_pins = {name: copied["pins"]["grid_" + name.removesuffix(".json")]
                 for name in FILES[:3]}
    records["grid_audit"]["source_pins"] = grid_pins
    copied["pins"]["grid_audit"] = _put(copied["inputs"]["grid_audit"], records["grid_audit"])
    source_pins = grid_pins | {"audit.json": copied["pins"]["grid_audit"]}
    for role in ("study_attempt", "study_report", "study_receipt", "study_audit"):
        records[role]["source_pins"] = source_pins
    copied["pins"]["study_attempt"] = _put(copied["inputs"]["study_attempt"], records["study_attempt"])
    for role in ("study_report", "study_receipt", "study_audit"):
        records[role]["attempt_sha256"] = copied["pins"]["study_attempt"]
    copied["pins"]["study_report"] = _put(copied["inputs"]["study_report"], records["study_report"])
    records["study_receipt"]["report_sha256"] = copied["pins"]["study_report"]
    copied["pins"]["study_receipt"] = _put(copied["inputs"]["study_receipt"], records["study_receipt"])
    records["study_completion"]["receipt_sha256"] = copied["pins"]["study_receipt"]
    copied["pins"]["study_completion"] = _put(copied["inputs"]["study_completion"], records["study_completion"])
    copied["pins"]["study_audit"] = _put(copied["inputs"]["study_audit"], records["study_audit"])
    assert all(digest(path) == copied["pins"][role] for role, path in copied["inputs"].items())
    with pytest.raises(ValueError, match="grid.*(method|source|lineage)"):
        runner["_inputs"](copied, runner["Budget"]())


def test_producer_budget_preserves_space_for_separate_audit(
    runner: Row, profile: Row, outcome: tuple[Path, Row], tmp_path: Path,
) -> None:
    original, _ = outcome
    producer_size = sum(path.stat().st_size for path in original.iterdir())
    output = tmp_path / "r559m-artificial-audit-reserve"
    with pytest.raises(ValueError, match="cap"):
        runner["run"](output, profile, budget=runner["Budget"](byte_cap=producer_size))
    assert not (output / "completion.json").exists()


@pytest.mark.parametrize(("field", "cap"), [
    ("wall_ns", 0), ("bound_cap", 47), ("event_cap", 1), ("byte_cap", 32_768),
    ("mass_cap", 11),
])
def test_caps_prevent_completion_and_restore_observer_state(
    runner: Row, methods: Methods, profile: Row, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch, field: str, cap: int,
) -> None:
    functions = {name: getattr(methods["bounds"], name)
                 for name in ("bounds", "_ellipse", "_reverse", "_norm2", "_mass_exclusion")}
    conversion, profiler = methods["interval"].binary64_lower, sys.getprofile()
    monkeypatch.setitem(runner["run"].__globals__, "_methods", lambda: methods)
    output = tmp_path / ("r559m-artificial-cap-" + field)
    with pytest.raises(ValueError, match="cap"):
        runner["run"](output, profile, budget=runner["Budget"](**{field: cap}))
    assert not (output / "completion.json").exists()
    assert sys.getprofile() is profiler
    assert methods["interval"].binary64_lower is conversion
    assert all(getattr(methods["bounds"], name) is function for name, function in functions.items())


@pytest.mark.parametrize(("field", "cap"), [
    ("wall_ns", 30_000_000_001), ("bound_cap", 49), ("event_cap", 8193),
    ("byte_cap", CAP + 1), ("mass_cap", 13), ("bound_cap", True),
])
def test_resource_ceilings_cannot_be_raised(runner: Row, field: str, cap: int) -> None:
    with pytest.raises(ValueError, match="cap"):
        runner["Budget"](**{field: cap})


def test_changed_mathematical_source_pin_prevents_loading(runner: Row, monkeypatch: pytest.MonkeyPatch) -> None:
    namespace = runner["_methods"].__globals__
    pins = dict(namespace["METHODS"])
    filename, _ = pins["bounds"]
    pins["bounds"] = filename, "0" * 64
    monkeypatch.setitem(namespace, "METHODS", pins)
    with pytest.raises(ValueError, match="bounds.*pin"):
        runner["_methods"]()


def test_observer_rejects_an_arbitrary_reference_relabelled_artificial_before_bounds(
    methods: Methods, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = dict(normalized=dict(scope="artificial", candidate_id="artificial-moon-mars",
                               live_authorized=False, command_words=None),
               fabricated_operands="Arbitrary caller input with a matching SHA-256 is insufficient.")
    pin = row_digest(ref)
    assert pin not in methods["trace"].ARTIFICIAL_REFERENCE_SHA256

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("an unapproved reference reached bound evaluation")

    monkeypatch.setattr(methods["bounds"], "bounds", forbidden)
    with pytest.raises(ValueError, match="artificial trace scope"):
        methods["trace"].trace_bound(
            ref, Fraction(150), Fraction(4801, 32), "positive", methods,
            independent=False, reference_sha256=pin, retained=False,
            check=lambda: None, emit=lambda event: pytest.fail("an unapproved reference emitted an event"),
        )


def test_saved_only_run_and_audit_construct_zero_points_and_cache_mass_arithmetic(
    runner: Row, methods: Methods, profile: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = Counter()
    original_mass = methods["oracle"].mass
    original_bound = methods["bounds"].bounds

    def mass(*args: Any, **kwargs: Any) -> Any:
        calls["mass"] += 1
        return original_mass(*args, **kwargs)

    class CountedBound:
        # Observe the original bound frame, including its unchanged local operands.
        __code__: CodeType = original_bound.__code__

        def __call__(self, *args: Any, **kwargs: Any) -> Row:
            calls["bounds"] += 1
            return original_bound(*args, **kwargs)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("saved-only trace attempted a point, orbit, signed conic solve, or old audit")

    for module, names in (
        ("points", ("point", "fixture", "_state")),
        ("orbit", ("state", "_local_state", "_oracle_state")),
        ("core", ("audited_roots", "float_branches", "evaluate")),
        ("oracle", ("branches",)),
        ("study", ("_scan", "_saved", "_audit")),
        ("screen", ("scan", "audit")),
        ("anchors", ("verify_anchor",)),
        ("reader", ("validate_science",)),
    ):
        for name in names:
            if hasattr(methods[module], name):
                monkeypatch.setattr(methods[module], name, forbidden)
    monkeypatch.setattr(methods["oracle"], "mass", mass)
    monkeypatch.setattr(methods["bounds"], "bounds", CountedBound())
    monkeypatch.setitem(runner["run"].__globals__, "_methods", lambda: methods)
    output = tmp_path / "r559m-artificial-spies"
    result = runner["run"](output, profile)
    assert calls == Counter(bounds=48, mass=12)
    assert result["work"]["points"] == 0
    calls.clear()
    monkeypatch.setattr(methods["trace"], "trace_bound", forbidden)
    monkeypatch.setattr(methods["bounds"], "bounds", forbidden)
    saved = runner["audit"](output, profile, digest(output / "completion.json"))
    assert saved == result and calls == Counter(mass=6)


def test_late_readback_failure_removes_completion_and_keeps_partial_evidence(
    runner: Row, profile: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "r559m-artificial-late"
    durable: dict[str, str] = {}

    def late_readback(*args: Any, **kwargs: Any) -> Row:
        assert (output / "completion.json").is_file()
        durable.update({name: digest(output / name) for name in FILES[:3]})
        raise ValueError("wall cap")

    monkeypatch.setitem(runner["run"].__globals__, "_saved", late_readback)
    with pytest.raises(ValueError, match="wall cap"):
        runner["run"](output, profile)
    assert durable and {path.name for path in output.iterdir()} == set(FILES[:3])
    assert {path.name: digest(path) for path in output.iterdir()} == durable
    with pytest.raises(ValueError):
        runner["run"](output, profile)
    assert {path.name: digest(path) for path in output.iterdir()} == durable


def test_post_write_completion_failure_removes_only_owned_completion(
    runner: Row, methods: Methods, profile: Row, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "r559m-artificial-completion-flush"
    original_put = methods["io"]._put
    durable: dict[str, str] = {}

    def fail_after_completion(path: Path, row: Row, cap: int) -> str:
        pin = original_put(path, row, cap)
        if path.name == "completion.json":
            durable.update({name: digest(output / name) for name in FILES[:3]})
            raise OSError("completion post-write fsync")
        return pin

    monkeypatch.setattr(methods["io"], "_put", fail_after_completion)
    monkeypatch.setitem(runner["run"].__globals__, "_methods", lambda: methods)
    with pytest.raises(OSError, match="completion post-write fsync"):
        runner["run"](output, profile)
    assert durable and {path.name for path in output.iterdir()} == set(FILES[:3])
    assert {path.name: digest(path) for path in output.iterdir()} == durable


def test_post_write_audit_failure_removes_owned_audit_and_preserves_producer(
    runner: Row, methods: Methods, profile: Row, outcome: tuple[Path, Row],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, _ = outcome
    target = output.with_name("r559m-artificial-audit-flush.json")
    before = {path.name: digest(path) for path in output.iterdir()}
    original_put, original_mass = methods["io"]._put, methods["oracle"].mass
    calls = Counter()
    budget = runner["Budget"](mass_cap=6)

    def fail_after_audit(path: Path, row: Row, cap: int) -> str:
        pin = original_put(path, row, cap)
        if path == target:
            assert path.is_file()
            assert row["invocation_id"] == budget.invocation_id
            raise OSError("audit post-write fsync")
        return pin

    def mass(*args: Any, **kwargs: Any) -> Any:
        calls["mass"] += 1
        return original_mass(*args, **kwargs)

    monkeypatch.setattr(methods["io"], "_put", fail_after_audit)
    monkeypatch.setattr(methods["oracle"], "mass", mass)
    monkeypatch.setitem(runner["audit"].__globals__, "_methods", lambda: methods)
    with pytest.raises(OSError, match="audit post-write fsync"):
        runner["audit"](output, profile, digest(output / "completion.json"),
                        audit_path=target, budget=budget)
    assert not target.exists()
    assert calls == Counter(mass=6)
    assert budget.used == dict(bounds=0, points=0, events=0, oracle_mass=6)
    assert {path.name: digest(path) for path in output.iterdir()} == before


def test_audit_exclusive_write_race_preserves_foreign_invocation(
    runner: Row, methods: Methods, profile: Row, outcome: tuple[Path, Row],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, _ = outcome
    target = output.with_name("r559m-artificial-audit-foreign.json")
    before = {path.name: digest(path) for path in output.iterdir()}
    foreign = wire(dict(invocation_id="f" * 32, artificial_fixture="Another invocation owns this audit."))
    original_put = methods["io"]._put

    def race_after_exclusive_check(path: Path, row: Row, cap: int) -> str:
        if path == target:
            path.write_bytes(foreign)
            raise FileExistsError("another invocation created the audit")
        return original_put(path, row, cap)

    monkeypatch.setattr(methods["io"], "_put", race_after_exclusive_check)
    monkeypatch.setitem(runner["audit"].__globals__, "_methods", lambda: methods)
    with pytest.raises(FileExistsError, match="another invocation"):
        runner["audit"](output, profile, digest(output / "completion.json"), audit_path=target)
    assert target.read_bytes() == foreign
    assert {path.name: digest(path) for path in output.iterdir()} == before


def test_audit_rejects_a_larger_mass_budget_before_fresh_arithmetic(
    runner: Row, methods: Methods, profile: Row, outcome: tuple[Path, Row],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, _ = outcome

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("an enlarged audit mass budget reached fresh arithmetic")

    monkeypatch.setattr(methods["oracle"], "mass", forbidden)
    monkeypatch.setitem(runner["audit"].__globals__, "_methods", lambda: methods)
    with pytest.raises(ValueError, match="(audit|mass).*cap"):
        runner["audit"](output, profile, digest(output / "completion.json"),
                        budget=runner["Budget"](mass_cap=7))
