"""Independent analytic fixtures for the private ADR0156 force reference.

No retained source rows, scientific packages, kernels or production force helpers
are used. The small binary64 recipe below is local test input, not an oracle.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any

import pytest


REFERENCE_PATH = Path(__file__).resolve().parents[1] / "docs/adr/experiments/0157-fixed-gravity-reference.py"


def _load_reference() -> Any:
    spec = importlib.util.spec_from_file_location("ariadna_0157_reference_test", REFERENCE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


reference = _load_reference()


def _row(
    position_km: tuple[float, float, float] = (2.0, 3.0, 6.0), *,
    body: str = "Sun", lo: float = 0.0,
    slope_km: tuple[float, float, float] = (0.0, 0.0, 0.0),
    native_offset_m: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> dict[str, Any]:
    segments: list[dict[str, Any]] = []
    records: list[Any] = []
    chains = {"Sun": ((10, 0),), "Earth": ((399, 0),), "Moon": ((301, 399), (399, 0))}
    for index, (target, centre) in enumerate(chains[body]):
        coefficients = position_km if index == 0 else (0.0, 0.0, 0.0)
        slopes = slope_km if index == 0 else (0.0, 0.0, 0.0)
        words = [1000.0, 100.0, *[value for pair in zip(coefficients, slopes) for value in pair]]
        records.append(reference.ORACLE.parse_record(words))
        segments.append({"body": target, "centre": centre, "frame": 1, "type": 2,
                         "first_tdb_s": 900.0, "last_tdb_s": 1100.0, "words": words})
    # Linear coefficient/normalization arithmetic is independent of evaluate_chain.
    state = [1000.0 * value + offset for value, offset in zip(position_km, native_offset_m)]
    state += [10.0 * value for value in slope_km]
    return {"body": body, "hi_tdb_s": 1000.0, "hi_hex": (1000.0).hex(),
            "lo_s": lo, "lo_hex": lo.hex(), "segments": segments, "state_si": state,
            "assessment": reference.ORACLE.assess(state, records, 1000.0, lo)}


def _arms(row: dict[str, Any], gm: float = 49_000_000.0,
          position: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, sign in (("compensated", 1.0), ("uncorrected", 0.0), ("wrong_sign", -1.0)):
        correction = [sign * row["state_si"][i + 3] * row["lo_s"] for i in range(3)]
        separation = [math.fsum((row["state_si"][i], -position[i], correction[i])) for i in range(3)]
        distance = math.hypot(*separation)
        acceleration = [gm * (value / distance) / (distance * distance) for value in separation]
        result[name] = {"separation_m": separation, "rephasing_m": correction,
                        "acceleration_m_s2": acceleration}
    return result


def _assess(row: dict[str, Any], *, gm: float = 49_000_000.0,
            position: tuple[float, float, float] = (0.0, 0.0, 0.0),
            arms: dict[str, Any] | None = None) -> dict[str, Any]:
    return reference.assess_source(row, position, gm, 1.0,
                                   _arms(row, gm, position) if arms is None else arms,
                                   lambda _phase: None)


def _decoded(vector: list[dict[str, str]]) -> tuple[Fraction, ...]:
    return tuple(Fraction(int(item["numerator"]), int(item["denominator"])) for item in vector)


def _total_arms(arms: list[dict[str, Any]]) -> dict[str, Any]:
    return {model: {name: {"acceleration_m_s2": [
        math.fsum(arms[i][name]["acceleration_m_s2"][axis] for i in indices)
        for axis in range(3)]} for name in reference.ARM_NAMES}
        for model, indices in {"A": (0, 1), "B": (0, 1, 2)}.items()}


def test_three_dimensional_analytic_field_and_signed_attribution() -> None:
    result = _assess(_row())
    assert result["passed"]
    for profile in ("80", "100"):
        with localcontext() as context:
            context.prec = int(profile)
            expected = [Decimal(value) / 7 for value in (2, 3, 6)]
        assert [Decimal(value) for value in result["reference"][profile]["d0"]] == expected
        assert all(Decimal(value) == 0 for name in reference.CONTRIBUTIONS[:3]
                   for value in result["contributions_m_s2"][profile][name])
        assert result["telescope"][profile]["passed"]
    assert _decoded(result["exact_geometries_m"]["d0"]) == (2000, 3000, 6000)
    json.dumps(result, allow_nan=False)


def test_central_field_has_exact_zero_components() -> None:
    result = _assess(_row((1.0, 0.0, 0.0)), gm=1.0)
    for profile in ("80", "100"):
        assert [Decimal(value) for value in result["reference"][profile]["d0"]] == [
            Decimal("1e-6"), Decimal(), Decimal()]
    assert result["passed"]


@pytest.mark.parametrize("lo", [0.25, -0.25])
def test_linear_epoch_sign_omission_and_wrong_sign_controls(lo: float) -> None:
    row = _row(lo=lo, slope_km=(100.0, -50.0, 25.0))
    result = _assess(row)
    assert result["passed"]
    assert _decoded(result["exact_position_time_m"]) == (
        Fraction(2000) + 1000 * Fraction(lo), Fraction(3000) - 500 * Fraction(lo),
        Fraction(6000) + 250 * Fraction(lo))
    for profile in ("80", "100"):
        assert not result["gates"][profile]["controls"]["uncorrected"]["passed"]
        assert not result["gates"][profile]["controls"]["wrong_sign"]["passed"]
        assert result["gates"][profile]["overall"]["passed"]


def test_zero_low_epoch_controls_can_all_pass() -> None:
    result = _assess(_row(slope_km=(100.0, -50.0, 25.0)))
    assert result["passed"]
    assert all(gate["passed"] for profile in result["gates"].values()
               for gate in profile["controls"].values())


def test_source_discrepancy_is_retained_when_field_arithmetic_passes() -> None:
    row = _row((1.0, 0.0, 0.0), native_offset_m=(0.0005, 0.0, 0.0))
    result = _assess(row, gm=1.0, position=(996.0, 0.0, 0.0))
    assert row["assessment"]["passed"]
    assert not result["passed"]
    for profile in ("80", "100"):
        assert result["gates"][profile]["returned_geometry"]["passed"]
        assert not result["gates"][profile]["overall"]["passed"]
        assert Decimal(result["contributions_m_s2"][profile]["native_source"][0]) != 0


def test_absolute_rounding_mutation_loses_a_small_correction() -> None:
    row = _row((float(2**40), 0.0, 0.0), lo=1e-6, slope_km=(100.0, 0.0, 0.0))
    position = (row["state_si"][0] - 4.0, 0.0, 0.0)
    valid = _arms(row, 1.0, position)
    assert _assess(row, gm=1.0, position=position, arms=valid)["passed"]
    mutant = deepcopy(valid)
    correction = mutant["compensated"]["rephasing_m"][0]
    separation = (row["state_si"][0] + correction) - position[0]
    mutant["compensated"]["separation_m"][0] = separation
    mutant["compensated"]["acceleration_m_s2"][0] = 1.0 / separation**2
    result = _assess(row, gm=1.0, position=position, arms=mutant)
    assert not result["passed"]
    assert result["gates"]["100"]["returned_geometry"]["passed"]
    assert not result["gates"]["100"]["overall"]["passed"]
    assert Decimal(result["contributions_m_s2"]["100"]["relative_assembly"][0]) != 0


def test_candidate_field_mutation_fails_returned_geometry_and_overall() -> None:
    row = _row()
    arms = _arms(row)
    arms["compensated"]["acceleration_m_s2"][0] += 1e-8
    result = _assess(row, arms=arms)
    assert not result["passed"]
    assert not result["gates"]["100"]["returned_geometry"]["passed"]
    assert not result["gates"]["100"]["overall"]["passed"]


def test_cancellation_uses_constituent_norm_scale_and_zero_total() -> None:
    rows = [_row(), _row((-2.0, -3.0, -6.0), body="Moon"),
            _row((3.0, 0.0, 4.0), body="Earth")]
    arms = [_arms(row) for row in rows]
    sources = [_assess(row, arms=arm) for row, arm in zip(rows, arms, strict=True)]
    totals_arms = _total_arms(arms)
    # A's true force is zero, but a tiny returned error uses the two-source scale.
    totals_arms["A"]["compensated"]["acceleration_m_s2"][0] = 1e-12
    ledger: list[str] = []
    totals = reference.assess_totals(sources, totals_arms, consume_model=ledger.append)
    assert ledger == ["attempt", "complete", "attempt", "complete"]
    assert set(totals) == {"A", "B"}
    assert totals["A"]["passed"] and totals["B"]["passed"]
    for profile in ("80", "100"):
        assert all(Decimal(value) == 0 for value in totals["A"]["reference"][profile]["d0"])
        assert Decimal(totals["A"]["reference_norms_m_s2"][profile]["d0"]) > Decimal("1.9")
        assert Decimal(totals["A"]["gates"][profile]["overall"]["envelope_m_s2"]) > Decimal("1.9e-11")


def test_omitted_source_mutation_and_totals_fail_stop_prefix() -> None:
    rows = [_row(), _row(body="Moon"), _row(body="Earth")]
    arms = [_arms(row) for row in rows]
    sources = [_assess(row, arms=arm) for row, arm in zip(rows, arms, strict=True)]
    totals_arms = _total_arms(arms)
    totals_arms["B"]["compensated"] = deepcopy(totals_arms["A"]["compensated"])
    totals = reference.assess_totals(sources, totals_arms)
    assert totals["A"]["passed"] and not totals["B"]["passed"]
    totals_arms["A"]["compensated"]["acceleration_m_s2"] = [0.0, 0.0, 0.0]
    ledger: list[str] = []
    totals = reference.assess_totals(sources, totals_arms, consume_model=ledger.append)
    assert set(totals) == {"A"}
    assert ledger == ["attempt", "complete"]


@pytest.mark.parametrize("missing", ["Sun", "Moon", "Earth"])
def test_totals_reject_missing_or_duplicate_source(missing: str) -> None:
    rows = [_row(body=body) for body in ("Sun", "Moon", "Earth")]
    sources = [_assess(row) for row in rows]
    bad = [source for source in sources if source["body"] != missing]
    with pytest.raises(ValueError, match="source set"):
        reference.assess_totals(bad, {})
    bad.append(deepcopy(bad[0]))
    with pytest.raises(ValueError, match="source set"):
        reference.assess_totals(bad, {})


def _fabricated_fields(low: Decimal, high: Decimal) -> tuple[dict[str, Any], dict[str, Any]]:
    fields = {"80": {name: (low, Decimal(), Decimal()) for name in reference.GEOMETRIES},
              "100": {name: (high, Decimal(), Decimal()) for name in reference.GEOMETRIES}}
    scales = {profile: {name: Decimal(1) for name in reference.GEOMETRIES}
              for profile in ("80", "100")}
    return fields, scales


def test_exact_gate_boundary_and_precision_classification_ambiguity() -> None:
    with localcontext() as context:
        context.prec = 100
        boundary = Decimal(1) - Decimal("1e-11")
        fields, scales = _fabricated_fields(boundary, boundary - Decimal("1e-79"))
    candidate = {name: (Fraction(1), Fraction(), Fraction()) for name in reference.ARM_NAMES}
    result = reference._assessment(fields, scales, candidate)
    assert result["precision"]["reference_fields"]["d0"]["passed"]
    assert result["gates"]["80"]["overall"]["passed"]
    assert not result["gates"]["100"]["overall"]["passed"]
    assert not result["precision"]["gate_classifications_stable"]
    assert not result["passed"]


def test_precision_disagreement_and_zero_loss_are_failures() -> None:
    candidate = {name: (Fraction(1), Fraction(), Fraction()) for name in reference.ARM_NAMES}
    with localcontext() as context:
        context.prec = 100
        fields, scales = _fabricated_fields(Decimal(1), Decimal(1) + Decimal("1e-50"))
    assert not reference._assessment(fields, scales, candidate)["precision"]["passed"]
    fields, scales = _fabricated_fields(Decimal(), Decimal("1e-90"))
    result = reference._assessment(fields, scales, candidate)
    assert not result["precision"]["reference_fields"]["d0"]["zero_preserved"]
    assert not result["precision"]["passed"]


def test_zero_coefficient_is_valid_only_for_pure_field_fixture() -> None:
    with localcontext() as context:
        context.prec = 100
        assert reference._field((Fraction(1), Fraction(2), Fraction(3)), Fraction()) == (Decimal(),) * 3
    row = _row()
    with pytest.raises(ValueError, match="positive"):
        reference.assess_source(row, [0.0] * 3, 0.0, 1.0, _arms(row), lambda _phase: None)


@pytest.mark.parametrize("geometry", ["d0", "d1", "d2", "d3", "uncorrected", "wrong_sign"])
def test_every_geometry_and_control_is_exterior_before_any_field(geometry: str) -> None:
    row = _row((1.0, 0.0, 0.0))
    arms = _arms(row, 1.0)
    position = [0.0, 0.0, 0.0]
    radius = 1000.0 if geometry in ("d0", "d1", "d2") else 1.0
    if geometry in ("d3", "uncorrected", "wrong_sign"):
        arms["compensated" if geometry == "d3" else geometry]["separation_m"] = [0.0] * 3
    ledger: list[str] = []
    with pytest.raises(ValueError, match="exterior-domain"):
        reference.assess_source(row, position, 1.0, radius, arms, ledger.append)
    assert ledger == []


def test_singular_exact_polynomial_geometry_is_rejected() -> None:
    row = _row((0.0, 0.0, 0.0))
    # Artificial finite returned arms cannot conceal the exact singularity.
    arms = {name: {"separation_m": [3.0, 0.0, 0.0], "acceleration_m_s2": [1.0, 0.0, 0.0],
                   "rephasing_m": [0.0] * 3} for name in reference.ARM_NAMES}
    with pytest.raises(ValueError, match="exterior-domain"):
        _assess(row, arms=arms)


@pytest.mark.parametrize("bad", [True, None, "1", math.inf, math.nan, 10**1000])
@pytest.mark.parametrize("field", ["gm", "radius", "position", "separation", "acceleration", "correction", "state"])
def test_scientific_numeric_boundaries_reject_bool_and_nonfinite(bad: Any, field: str) -> None:
    row = _row()
    arms = _arms(row)
    gm, radius, position = 49_000_000.0, 1.0, [0.0] * 3
    if field == "gm":
        gm = bad
    elif field == "radius":
        radius = bad
    elif field == "position":
        position[0] = bad
    elif field == "state":
        row["state_si"][0] = bad
    else:
        key = {"separation": "separation_m", "acceleration": "acceleration_m_s2",
               "correction": "rephasing_m"}[field]
        arms["compensated"][key][0] = bad
    with pytest.raises(ValueError):
        reference.assess_source(row, position, gm, radius, arms, lambda _phase: None)


@pytest.mark.parametrize("field,bad", [("body", 399), ("centre", 399), ("frame", True),
                                       ("frame", 2), ("type", 3), ("first_tdb_s", 1001.0),
                                       ("last_tdb_s", 999.0)])
def test_metadata_corruption_is_rejected(field: str, bad: Any) -> None:
    row = _row()
    row["segments"][0][field] = bad
    with pytest.raises(ValueError, match="chain|coverage"):
        _assess(row)


def test_record_coverage_covers_hi_and_exact_hi_plus_low() -> None:
    row = _row(lo=0.25)
    row["segments"][0]["words"][0] = 900.0
    with pytest.raises(ValueError, match="record coverage"):
        _assess(row)


@pytest.mark.parametrize("mutation", ["flag", "exact", "hex", "correction", "bool"])
def test_saved_assessment_is_reconstructed_instead_of_trusted(mutation: str) -> None:
    row = _row(lo=0.25, slope_km=(1.0, 0.0, 0.0))
    if mutation == "flag":
        row["assessment"]["passed"] = False
    elif mutation == "exact":
        row["assessment"]["exact"]["position_hi_m"][0]["numerator"] = "9"
    elif mutation == "hex":
        row["hi_hex"] = (1001.0).hex()
    elif mutation == "bool":
        row["assessment"]["passed"] = 1
    else:
        row["assessment"]["correction_m"][0] *= -1
    with pytest.raises(ValueError, match="mismatch"):
        _assess(row)


def test_candidate_rephasing_sign_must_match_exact_saved_operands() -> None:
    row = _row(lo=0.25, slope_km=(1.0, 0.0, 0.0))
    arms = _arms(row)
    arms["wrong_sign"]["rephasing_m"][0] *= -1
    with pytest.raises(ValueError, match="correction operands/sign"):
        _assess(row, arms=arms)


def test_reference_callbacks_count_attempts_and_completed_fields() -> None:
    row = _row()
    ledger: list[str] = []
    reference.assess_source(row, [0.0] * 3, 49_000_000.0, 1.0, _arms(row), ledger.append)
    assert ledger == ["attempt", "complete"] * 8


def test_reference_callbacks_preserve_partial_field_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _row()
    ledger: list[str] = []
    original = reference._field
    count = 0

    def failing_field(geometry: Any, gm: Fraction) -> Any:
        nonlocal count
        count += 1
        if count == 3:
            raise ValueError("injected field failure")
        return original(geometry, gm)

    monkeypatch.setattr(reference, "_field", failing_field)
    with pytest.raises(ValueError, match="injected field"):
        reference.assess_source(row, [0.0] * 3, 49_000_000.0, 1.0, _arms(row), ledger.append)
    assert ledger == ["attempt", "complete"] * 2 + ["attempt"]


def test_reference_stops_when_cooperative_budget_callback_rejects() -> None:
    row = _row()
    ledger: list[str] = []

    def limited(phase: str) -> None:
        ledger.append(phase)
        if ledger.count("attempt") == 3:
            raise ValueError("reference field cap/deadline")

    with pytest.raises(ValueError, match="cap/deadline"):
        reference.assess_source(row, [0.0] * 3, 49_000_000.0, 1.0, _arms(row), limited)
    assert ledger == ["attempt", "complete"] * 2 + ["attempt"]


def test_helper_hash_is_checked_before_import(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "modified-oracle.py"
    fake.write_text("raise AssertionError('must never import')\n")
    monkeypatch.setattr(reference, "ORACLE_PATH", fake)
    with pytest.raises(ValueError, match="SHA256"):
        reference.load_oracle()


def test_reference_imports_only_stdlib_and_the_pinned_pure_helper() -> None:
    tree = ast.parse(REFERENCE_PATH.read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    assert modules <= {"__future__", "collections", "decimal", "fractions", "hashlib",
                       "importlib", "json", "math", "pathlib", "sys", "types", "typing"}
    source = REFERENCE_PATH.read_text()
    assert '0152-' not in source and '0153-real-ephemeris-study.py' not in source
    assert 'space_nav' not in source and 'tudatpy' not in source and 'spiceypy' not in source


def test_binary64_operands_do_not_pass_through_display_decimal() -> None:
    assert reference._exact_vector([0.1, 0.2, 0.3], "fixture")[0] == Fraction.from_float(0.1)
    assert reference._exact_vector([0.1, 0.2, 0.3], "fixture")[0] != Fraction("0.1")


def test_reference_profiles_fix_rounding_independently_of_ambient_context() -> None:
    from decimal import ROUND_DOWN

    row = _row()
    expected = _assess(row)
    with localcontext() as context:
        context.prec = 7
        context.rounding = ROUND_DOWN
        assert _assess(row) == expected


@pytest.mark.parametrize("bad", [True, math.nan, math.inf, 10**1000])
def test_record_words_reject_nonbinary64_operands(bad: Any) -> None:
    row = _row()
    row["segments"][0]["words"][2] = bad
    with pytest.raises(ValueError, match="record.words"):
        _assess(row)


@pytest.mark.parametrize("completed", [1, 4, 8])
def test_each_returned_reference_survives_completion_callback_failure(completed: int) -> None:
    row = _row()
    expected = _assess(row)["reference"]
    progress: dict[str, Any] = {}
    ledger: list[str] = []

    def interrupt(phase: str) -> None:
        ledger.append(phase)
        if phase == "complete" and ledger.count("complete") == completed:
            raise ValueError("injected post-field deadline")

    with pytest.raises(ValueError, match="post-field deadline"):
        reference.assess_source(row, [0.0] * 3, 49_000_000.0, 1.0, _arms(row),
                                interrupt, progress=progress)
    assert ledger == ["attempt", "complete"] * completed
    assert sum(len(fields) for fields in progress["reference"].values()) == completed
    for profile, fields in progress["reference"].items():
        assert list(fields) == list(reference.GEOMETRIES)[:len(fields)]
        assert fields == {name: expected[profile][name] for name in fields}


@pytest.mark.parametrize("failed_phase", ["b_attempt", "a_complete", "b_complete"])
def test_returned_models_survive_later_callback_failure(failed_phase: str) -> None:
    rows = [_row(), _row(body="Moon"), _row(body="Earth")]
    arms = [_arms(row) for row in rows]
    sources = [_assess(row, arms=arm) for row, arm in zip(rows, arms, strict=True)]
    total_arms = _total_arms(arms)
    expected = reference.assess_totals(sources, total_arms)
    progress: dict[str, Any] = {}
    ledger: list[str] = []

    def interrupt(phase: str) -> None:
        ledger.append(phase)
        if ((failed_phase == "a_complete" and ledger == ["attempt", "complete"])
                or (failed_phase == "b_attempt" and ledger == ["attempt", "complete", "attempt"])
                or (failed_phase == "b_complete" and ledger == ["attempt", "complete"] * 2)):
            raise ValueError("injected model deadline")

    with pytest.raises(ValueError, match="model deadline"):
        reference.assess_totals(sources, total_arms, consume_model=interrupt, progress=progress)
    models = ["A", "B"] if failed_phase == "b_complete" else ["A"]
    assert list(progress) == models
    assert progress == {model: expected[model] for model in models}


def test_oracle_executes_checked_bytes_despite_valid_stale_bytecode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from hashlib import sha256
    import os
    import py_compile

    path = tmp_path / "oracle.py"
    poison = b'VALUE = "poison!"\n'
    checked = b'VALUE = "checked"\n'
    assert len(poison) == len(checked)
    path.write_bytes(poison)
    saved_stat = path.stat()
    py_compile.compile(str(path), doraise=True)
    path.write_bytes(checked)
    os.utime(path, ns=(saved_stat.st_atime_ns, saved_stat.st_mtime_ns))
    monkeypatch.setattr(reference, "ORACLE_PATH", path)
    monkeypatch.setattr(reference, "ORACLE_SHA256", sha256(checked).hexdigest())
    name = "ariadna_0157_polynomial_oracle"
    original = sys.modules[name]
    try:
        assert reference.load_oracle().VALUE == "checked"
    finally:
        sys.modules[name] = original
