"""Qualify the local norm comparison exclusively on fabricated trace operands."""

from collections import Counter
from copy import deepcopy
from decimal import Decimal, Inexact, Rounded, getcontext, localcontext
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

import pytest

from matched_norm_fixtures import (
    ART, CANDIDATE, REFERENCE, ROOT, ROLES, SCOPE, contract, direct_decimal_norm,
    fabricated_archive, fabricated_vector, rechain, selected_norm_events, wire,
    write_artificial_pack,
)

type Row = dict[str, Any]
METHODS = ("square-sum", "product-sum-clipped")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _load_private(name: str) -> ModuleType:
    """Compile only the new private source; historical scientific modules stay inert."""
    path = ART / ("0235-matched-norm-" + name + ".py")
    module = ModuleType("_matched_norm_qualification_" + name)
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


@pytest.fixture(scope="module")
def core() -> ModuleType:
    return _load_private("core")


@pytest.fixture(scope="module")
def auditor() -> ModuleType:
    return _load_private("audit")


@pytest.fixture(scope="module")
def archive() -> Row:
    return fabricated_archive()


@pytest.fixture(scope="module")
def design() -> Row:
    return contract()


def _analyze(core: ModuleType, archive: Row, design: Row) -> tuple[Row, Counter[str]]:
    used: Counter[str] = Counter()

    def charge(kind: str, count: int = 1) -> None:
        used[kind] += count

    result = core.analyze(archive, design, check=lambda: None, charge=charge, scope=SCOPE)
    return result, used


def _verify(auditor: ModuleType, archive: Row, design: Row, result: Row) -> Row:
    return auditor.verify(archive, design, result, check=lambda: None,
                          charge=lambda kind, count=1: None, scope=SCOPE)


@pytest.fixture(scope="module")
def produced(core: ModuleType, archive: Row, design: Row) -> Row:
    return _analyze(core, archive, design)[0]


def _rational_interval(value: Row) -> tuple[Fraction, Fraction]:
    lo, hi = value["rational"]
    return Fraction(lo), Fraction(hi)


def _exact_box(vector: list[dict[str, str]]) -> tuple[Fraction, Fraction]:
    """Direct analytic Cartesian-box invariant, independent of rounded primitives."""
    intervals = [(Fraction(value["lo"]), Fraction(value["hi"])) for value in vector]
    lo = sum((Fraction(0) if left <= 0 <= right else min(left * left, right * right)
              for left, right in intervals), Fraction(0))
    hi = sum((max(left * left, right * right) for left, right in intervals), Fraction(0))
    return lo, hi


def test_full_artificial_pack_has_real_descriptor_volume_and_no_retained_reads(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    design = contract()
    forbidden = {ROOT / item["path"] for item in design["original_input_artifacts"][:6]}
    forbidden |= {ROOT / item for item in design["motivation"]["reference_only_evidence"]}
    read = Path.read_bytes

    def no_observations(path: Path) -> bytes:
        assert path not in forbidden, "qualification must not open retained numerical evidence"
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", no_observations)
    core, auditor = _load_private("core"), _load_private("audit")
    saved = fabricated_archive()
    profile = write_artificial_pack(tmp_path / "inputs")
    output, _ = _analyze(core, saved, design)
    assert _verify(auditor, saved, design, output)["status"] == "verified"
    assert set(profile["inputs"]) == set(profile["pins"]) == set(ROLES)
    assert profile["scope"] == SCOPE and profile["candidate_id"] == CANDIDATE
    assert profile["reference_sha256"] == REFERENCE
    assert REFERENCE != design["inherited_contract"]["sha256"]
    assert profile["expected_events"] == 1248
    assert all(saved[role].get("scope", SCOPE) == SCOPE for role in ROLES)
    assert len(saved["report"]["rows"]) == 24
    assert len(saved["report"]["saved_endpoint_descriptors"]) == 6156
    assert not any("padding" in name for name in saved["report"])
    input_bytes = 0
    for role, path_text in profile["inputs"].items():
        raw = Path(path_text).read_bytes()
        input_bytes += len(raw)
        assert profile["pins"][role] == dict(sha256=sha256(raw).hexdigest(), bytes=len(raw))
    source_bytes = sum((ROOT / item["path"]).stat().st_size for item in design["original_input_artifacts"][6:])
    assert design["original_input_bytes"] <= input_bytes + source_bytes < 4 * 1024**2
    endpoints = [endpoint for row in saved["report"]["rows"] for event in row["trace"]["events"]
                 for interval in event["fields"].values() for endpoint in interval.values()]
    assert sum(90 <= len(Decimal(value).as_tuple().digits) <= 97 for value in endpoints) > 11900
    assert any("E+120" in value for value in endpoints)
    assert any("E-90" in value for value in endpoints)


def test_complete_matrix_is_matched_unchanged_and_independently_verified(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row, produced: Row,
) -> None:
    before = wire(archive)
    result, used = _analyze(core, archive, design)
    assert wire(archive) == before
    assert result == produced and result["scope"] == SCOPE
    assert result["status"] == "matched-norm-qualified-local-only" and result["reason"] is None
    assert len(result["rows"]) == 72
    assert result["counts"] == dict(used)
    assert {key: used[key] for key in ("event_visits", "boxes", "methods", "oracles", "diagonals", "comparisons", "descriptors")} == dict(
        event_visits=1248, boxes=72, methods=144, oracles=72, diagonals=72, comparisons=72, descriptors=72,
    )
    assert 0 < used["directed_primitives"] <= design["caps"]["directed_primitive_operations_per_process"]
    assert result["progress"] == dict(methods=dict(attempted=144, charged=144, completed=144),
                                       oracles=dict(attempted=72, charged=72, completed=72))
    assert _verify(auditor, archive, design, produced)["status"] == "verified"
    expected = [(row["row_index"], row["domain"], row["sign"], role,
                 "independent" if row["independent"] else "default")
                for row in archive["report"]["rows"] for role, _, _ in selected_norm_events(row)]
    assert [(row["row_index"], row["domain"], row["sign"], row["role"], row["source_origin"])
            for row in produced["rows"]] == expected
    for record in produced["rows"]:
        source_row = archive["report"]["rows"][record["trace_row"]]
        _, call, returned = next(item for item in selected_norm_events(source_row) if item[0] == record["role"])
        strings = [call["fields"][f"v[{index}]"][endpoint] for index in range(3) for endpoint in ("lo", "hi")]
        digest = sha256(_canonical(strings)).hexdigest()
        assert record["input"] == dict(raw_endpoint_strings=strings, sha256=digest)
        assert record["source"]["call"] == call["index"]
        assert record["source"]["return"] == returned["index"]
        assert record["source"]["call_pointer"].endswith(f"/events/{call['index']}")
        assert record["source"]["return_field_pointer"].endswith(f"/events/{returned['index']}/fields/return")
        assert record["diagonal"]["matches"] is True
        assert {method["input_sha256"] for method in record["methods"].values()} == {digest}
        assert record["result_units"] in ("m2/s2", "m2", "m4/s2")


def test_every_rounded_endpoint_and_exact_real_box_has_an_independent_oracle(produced: Row) -> None:
    for record in produced["rows"]:
        vector = fabricated_vector(record["id"])
        reference = _exact_box(vector)
        assert _rational_interval(record["oracle"]) == reference
        assert Fraction(record["oracle"]["width"]) == reference[1] - reference[0]
        for name in METHODS:
            expected = direct_decimal_norm(vector, independent=name == "product-sum-clipped")
            actual = record["methods"][name]
            endpoints = _rational_interval(actual["final"])
            assert endpoints == (Fraction(expected["lo"]), Fraction(expected["hi"]))
            assert tuple(Fraction(value) for value in actual["final"]["decimal"]) == endpoints
            assert endpoints[0] <= reference[0] <= reference[1] <= endpoints[1]
            assert actual["contains_oracle"] is True
            assert Fraction(actual["metrics"]["width"]) == endpoints[1] - endpoints[0]
            assert Fraction(actual["metrics"]["lower_excess"]) == reference[0] - endpoints[0]
            assert Fraction(actual["metrics"]["upper_excess"]) == endpoints[1] - reference[1]
            assert Fraction(actual["metrics"]["excess_width"]) == endpoints[1] - endpoints[0] - (reference[1] - reference[0])


def test_zero_crossing_clipping_abs_rounding_and_exact_zero_ratios(produced: Row) -> None:
    crossing, zero, point = produced["rows"][:3]
    product = crossing["methods"]["product-sum-clipped"]
    assert _rational_interval(product["raw"])[0] == -5
    assert _rational_interval(product["final"]) == (Fraction(0), Fraction(50))
    assert _rational_interval(crossing["methods"]["square-sum"]["final"]) == (Fraction(1), Fraction(50))
    for record in (zero, point):
        assert record["metrics"]["width_ratio_product_over_square"] is None
        assert record["metrics"]["width_ratio_status"] == "both-widths-zero"
    assert _rational_interval(point["oracle"]) == (Fraction(25), Fraction(25))
    assert any(Fraction(value) < 0 for value in crossing["input"]["raw_endpoint_strings"])
    assert len(set(zero["input"]["raw_endpoint_strings"])) > 1
    assert all(Fraction(value) == 0 for value in zero["input"]["raw_endpoint_strings"])
    boundary = produced["rows"][8]
    assert len(Decimal(boundary["input"]["raw_endpoint_strings"][0]).as_tuple().digits) == 97
    squared = boundary["methods"]["square-sum"]["final"]["rational"]
    product_squared = boundary["methods"]["product-sum-clipped"]["final"]["rational"]
    assert Fraction(squared[0]) == Fraction(product_squared[0]) == 1
    assert Fraction(squared[1]) > Fraction(product_squared[1])
    assert boundary["classification"] == "product-sum-clipped-strict-subset"
    assert len({row["input"]["sha256"] for row in produced["rows"]}) < 72
    assert len({(row["trace_row"], row["role"], row["source_origin"]) for row in produced["rows"]}) == 72


def test_contexts_are_fresh_and_ignore_ambient_precision_flags_and_traps(
    core: ModuleType, archive: Row, design: Row, produced: Row,
) -> None:
    with localcontext() as ambient:
        ambient.prec = 7
        ambient.rounding = "ROUND_DOWN"
        ambient.traps[Inexact] = True
        ambient.flags[Rounded] = True
        before = getcontext().copy()
        observed, _ = _analyze(core, archive, design)
        assert str(getcontext()) == str(before)
    assert observed == produced
    for record in produced["rows"]:
        for method in record["methods"].values():
            context = method["context"]
            assert context["fingerprint"] == produced["context"]["fingerprint"]
            assert context["lower_before_flags"] == context["upper_before_flags"] == []
            assert set(context["lower_after_flags"] + context["upper_after_flags"]) <= {"Inexact", "Rounded"}
    assert any(method["context"]["upper_after_flags"] for row in produced["rows"] for method in row["methods"].values())


def test_single_diagonal_mismatch_preserves_all_evidence_and_forces_inconclusive(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row,
) -> None:
    saved = deepcopy(archive)
    _, _, returned = selected_norm_events(saved["report"]["rows"][0])[0]
    returned["fields"]["return"]["hi"] = "51"
    rechain(saved)
    result, used = _analyze(core, saved, design)
    assert result["status"] == "inconclusive" and result["reason"] == "compatibility-mismatch"
    assert sum(not row["diagonal"]["matches"] for row in result["rows"]) == 1
    assert all(row["classification"] == "inconclusive-compatibility-mismatch" for row in result["rows"])
    assert used["methods"] == 144 and used["oracles"] == used["diagonals"] == 72
    assert len(result["rows"]) == 72
    assert _verify(auditor, saved, design, result)["status"] == "verified"


@pytest.mark.parametrize("fault", ["missing-call", "missing-return", "parent", "call-order", "missing-operand", "changed-return-operand", "mode", "nan", "bool", "reversed", "huge-exponent", "significand", "effective-exponent", "declared-exponent", "source-pin", "scope"])
def test_resealed_input_shape_context_and_numeric_tampering_is_rejected(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row, produced: Row, fault: str,
) -> None:
    saved = deepcopy(archive)
    row = saved["report"]["rows"][0]
    _, call, returned = selected_norm_events(row)[0]
    if fault == "missing-call":
        row["trace"]["events"].remove(call)
    elif fault == "missing-return":
        row["trace"]["events"].remove(returned)
    elif fault == "parent":
        call["parent"] = 999
    elif fault == "call-order":
        call["call"] = 999
    elif fault == "missing-operand":
        del call["fields"]["v[0]"]
    elif fault == "changed-return-operand":
        returned["fields"]["v[0]"]["hi"] = "4"
    elif fault == "mode":
        returned["scalars"]["independent"] = True
    elif fault in ("nan", "bool", "reversed", "huge-exponent", "significand", "effective-exponent", "declared-exponent"):
        value = {"nan": "NaN", "bool": True, "reversed": "-3", "huge-exponent": "1E+513",
                 "significand": "1" * 257, "effective-exponent": "0." + "0" * 254 + "1E-258",
                 "declared-exponent": "1." + "0" * 100 + "E+600"}[fault]
        call["fields"]["v[0]"]["hi"] = value
        returned["fields"]["v[0]"]["hi"] = value
    elif fault == "source-pin":
        saved["_context"]["source_pins"] = dict(saved["_context"]["source_pins"])
        key = next(iter(saved["_context"]["source_pins"]))
        saved["_context"]["source_pins"][key] = "0" * 64
    else:
        saved["_context"]["scope"] = "retained"
    rechain(saved)
    with pytest.raises(ValueError):
        _analyze(core, saved, design)
    with pytest.raises(ValueError):
        _verify(auditor, saved, design, produced)


@pytest.mark.parametrize("fault", ["precision", "rounding", "traps", "flags", "role", "ordinal", "units"])
def test_fixed_contract_context_and_role_dimensions_cannot_be_reconfigured(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row, produced: Row, fault: str,
) -> None:
    changed = deepcopy(design)
    if fault == "precision":
        changed["context"]["prec"] = 95
    elif fault == "rounding":
        changed["context"]["directed_rounding"] = ["ROUND_DOWN", "ROUND_UP"]
    elif fault == "traps":
        changed["context"]["enabled_traps"] = []
    elif fault == "flags":
        changed["context"]["initial_flags"] = "Inexact"
    else:
        spec = changed["selection"]["norm_pair_roles"][0]
        spec[{"role": "role", "ordinal": "direct_norm2_ordinal", "units": "result_units"}[fault]] = {
            "role": "arrival-speed", "ordinal": 1, "units": "m/s",
        }[fault]
    with pytest.raises(ValueError):
        _analyze(core, archive, changed)
    with pytest.raises(ValueError):
        _verify(auditor, archive, changed, produced)


@pytest.mark.parametrize("fault", ["raw-string", "input-hash", "pointer", "unit", "context", "before-flags", "after-flags", "raw-product", "rounded-endpoint", "oracle", "width", "ratio", "classification", "diagonal", "count", "claim"])
def test_independent_auditor_rejects_report_tampering(
    auditor: ModuleType, archive: Row, design: Row, produced: Row, fault: str,
) -> None:
    changed = deepcopy(produced)
    row = changed["rows"][0]
    method = row["methods"]["square-sum"]
    if fault == "raw-string":
        row["input"]["raw_endpoint_strings"][0] = "-2.0"
    elif fault == "input-hash":
        method["input_sha256"] = "0" * 64
    elif fault == "pointer":
        row["source"]["operand_pointers"][0] += "/lo"
    elif fault == "unit":
        row["result_units"] = "m/s"
    elif fault == "context":
        changed["context"]["lower"]["prec"] = 95
    elif fault == "before-flags":
        method["context"]["lower_before_flags"] = ["Rounded"]
    elif fault == "after-flags":
        method["context"]["upper_after_flags"] = ["Underflow"]
    elif fault == "raw-product":
        row["methods"]["product-sum-clipped"]["raw"]["rational"][0] = "0"
    elif fault == "rounded-endpoint":
        method["final"]["decimal"][1] = "51"
        method["final"]["rational"][1] = "51"
    elif fault == "oracle":
        row["oracle"]["rational"][0] = "2"
    elif fault == "width":
        method["metrics"]["width"] = "50"
    elif fault == "ratio":
        row["metrics"]["width_ratio_product_over_square"] = "1"
    elif fault == "classification":
        row["classification"] = "equal-enclosures"
    elif fault == "diagonal":
        row["diagonal"]["matches"] = False
    elif fault == "count":
        changed["counts"]["methods"] = 143
    else:
        changed["physical_status"] = "strict-M3-qualified"
    with pytest.raises(ValueError):
        _verify(auditor, archive, design, changed)


def test_attempted_work_is_charged_before_arithmetic_and_caps_fail_without_retry(
    core: ModuleType, archive: Row, design: Row,
) -> None:
    ledger: Counter[str] = Counter()

    def stop_first_method(kind: str, count: int = 1) -> None:
        ledger[kind] += count
        if kind == "methods":
            raise ValueError("deliberate attempted-method budget failure")

    with pytest.raises(ValueError, match="attempted-method"):
        core.analyze(archive, design, check=lambda: None, charge=stop_first_method, scope=SCOPE)
    assert ledger["methods"] == 1 and ledger["directed_primitives"] == 0
    assert ledger["oracles"] == 1
    for name, value in (("input_vector_boxes", 71), ("method_evaluations_per_process", 143),
                        ("exact_box_range_evaluations_per_process", 71), ("rational_component_bits", 32),
                        ("directed_primitive_operations_per_process", 1), ("input_event_records", 1247)):
        changed = deepcopy(design)
        changed["caps"][name] = value
        with pytest.raises(ValueError):
            _analyze(core, archive, changed)


def _replace_selected(saved: Row, trace_row: int, role_index: int, vector: list[dict[str, str]]) -> None:
    row = saved["report"]["rows"][trace_row]
    _, call, returned = selected_norm_events(row)[role_index]
    for index, value in enumerate(vector):
        call["fields"][f"v[{index}]"] = deepcopy(value)
        returned["fields"][f"v[{index}]"] = deepcopy(value)
    returned["fields"]["return"] = direct_decimal_norm(vector, independent=row["independent"])
    rechain(saved)


def test_source_origin_does_not_change_either_method_on_identical_payloads(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row,
) -> None:
    saved = deepcopy(archive)
    _replace_selected(saved, 1, 0, fabricated_vector(0))
    result, _ = _analyze(core, saved, design)
    default, independent = result["rows"][0], result["rows"][3]
    assert default["source_origin"] == "default" and independent["source_origin"] == "independent"
    assert default["input"] == independent["input"]
    assert default["methods"] == independent["methods"]
    assert default["source"] != independent["source"]
    assert default["diagonal"]["matches"] is independent["diagonal"]["matches"] is True
    assert _verify(auditor, saved, design, result)["status"] == "verified"


def test_numeric_diagonal_equality_accepts_signed_scaled_exact_zero(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row,
) -> None:
    saved = deepcopy(archive)
    _, _, returned = selected_norm_events(saved["report"]["rows"][0])[1]
    returned["fields"]["return"] = dict(lo="-0E+96", hi="0.0000")
    rechain(saved)
    result, _ = _analyze(core, saved, design)
    assert result["status"] == "matched-norm-qualified-local-only"
    assert result["rows"][1]["saved_return"] == dict(decimal=["-0E+96", "0.0000"], rational=["0", "0"])
    assert result["rows"][1]["diagonal"]["matches"] is True
    assert _verify(auditor, saved, design, result)["status"] == "verified"


def test_rounding_and_dependency_can_produce_overlapping_incomparable_enclosures(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row,
) -> None:
    saved = deepcopy(archive)
    point = "1.23456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012"
    vector = [dict(lo=point, hi=point), dict(lo="-0.01", hi="0.01"), dict(lo="0", hi="0")]
    _replace_selected(saved, 0, 0, vector)
    result, _ = _analyze(core, saved, design)
    row = result["rows"][0]
    assert row["classification"] == "overlap-incomparable"
    a, b = (_rational_interval(row["methods"][method]["final"]) for method in METHODS)
    assert b[0] < a[0] < b[1] < a[1]
    assert _verify(auditor, saved, design, result)["status"] == "verified"


@pytest.mark.parametrize("exponent", [-256, 256])
def test_finite_source_exponent_boundary_has_exact_compatible_squared_endpoints(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row, exponent: int,
) -> None:
    saved = deepcopy(archive)
    endpoint = "1E" + str(exponent)
    vector = [dict(lo=endpoint, hi=endpoint), dict(lo="0", hi="0"), dict(lo="0", hi="0")]
    _replace_selected(saved, 0, 0, vector)
    result, _ = _analyze(core, saved, design)
    expected = Fraction("1E" + str(2 * exponent))
    assert _rational_interval(result["rows"][0]["oracle"]) == (expected, expected)
    assert result["rows"][0]["diagonal"]["matches"] is True
    assert _verify(auditor, saved, design, result)["status"] == "verified"


def test_mixed_extreme_exponents_fail_predicted_rational_growth_before_allocation(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row, produced: Row,
) -> None:
    saved = deepcopy(archive)
    _, call, returned = selected_norm_events(saved["report"]["rows"][0])[0]
    for index, endpoint in enumerate(("1E+512", "1E-512", "0")):
        value = dict(lo=endpoint, hi=endpoint)
        call["fields"][f"v[{index}]"] = deepcopy(value)
        returned["fields"][f"v[{index}]"] = deepcopy(value)
    returned["fields"]["return"] = dict(lo="0", hi="1")
    rechain(saved)
    with pytest.raises(ValueError, match="before allocation"):
        _analyze(core, saved, design)
    with pytest.raises(ValueError):
        _verify(auditor, saved, design, produced)


@pytest.mark.parametrize("fault", ["row-count", "row-order", "domain", "sign", "origin", "angle", "event-index", "trace-seal"])
def test_matrix_and_event_identity_are_fixed(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row, produced: Row, fault: str,
) -> None:
    saved = deepcopy(archive)
    rows = saved["report"]["rows"]
    if fault == "row-count":
        rows.pop()
    elif fault == "row-order":
        rows[0], rows[1] = rows[1], rows[0]
    elif fault == "domain":
        rows[0]["domain"] = "singleton"
    elif fault == "sign":
        rows[0]["sign"] = "negative"
    elif fault == "origin":
        rows[0]["independent"] = True
    elif fault == "angle":
        rows[0]["lo_deg"] = "149"
    elif fault == "event-index":
        rows[0]["trace"]["events"][0]["index"] = 1
    else:
        rows[0]["trace"]["seal"] = "0" * 64
    if fault != "trace-seal":
        rechain(saved)
    with pytest.raises(ValueError):
        _analyze(core, saved, design)
    with pytest.raises(ValueError):
        _verify(auditor, saved, design, produced)


@pytest.mark.parametrize("fault", ["second-method-charge", "first-primitive-charge"])
def test_failed_attempts_expose_completed_work_without_retries(
    core: ModuleType, archive: Row, design: Row, fault: str,
) -> None:
    ledger: Counter[str] = Counter()

    def refuse(kind: str, count: int = 1) -> None:
        ledger[kind] += count
        if (fault == "second-method-charge" and kind == "methods" and ledger[kind] == 2
                or fault == "first-primitive-charge" and kind == "directed_primitives"):
            raise ValueError("deliberate charge refusal")

    with pytest.raises(core.EvaluationError, match="deliberate charge refusal") as caught:
        core.analyze(archive, design, check=lambda: None, charge=refuse, scope=SCOPE)
    error = caught.value
    expected = (dict(attempted=2, charged=1, completed=1) if fault == "second-method-charge"
                else dict(attempted=1, charged=1, completed=0))
    assert error.progress["methods"] == expected
    assert error.progress["oracles"] == dict(attempted=1, charged=1, completed=1)
    assert error.counts["methods"] == 1 and error.partial_rows == []
    if fault == "first-primitive-charge":
        assert error.counts["directed_primitives"] == 0 and ledger["directed_primitives"] == 1


def test_nonmode_source_primitives_do_not_require_fabricated_mode_flags(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row,
) -> None:
    saved = deepcopy(archive)
    for row in saved["report"]["rows"]:
        for event in row["trace"]["events"]:
            if event["stage"] in ("_cross", "_binary64"):
                del event["scalars"]["independent"]
    rechain(saved)
    result, _ = _analyze(core, saved, design)
    assert result["status"] == "matched-norm-qualified-local-only"
    assert _verify(auditor, saved, design, result)["status"] == "verified"


def test_faulty_rounded_program_retains_invalid_containment_and_zero_ratio_evidence(
    monkeypatch: pytest.MonkeyPatch, core: ModuleType, auditor: ModuleType,
    archive: Row, design: Row,
) -> None:
    saved = deepcopy(archive)
    _, _, returned = selected_norm_events(saved["report"]["rows"][0])[0]
    returned["fields"]["return"] = dict(lo="0", hi="0")
    rechain(saved)
    evaluate = core._Kernel.evaluate
    calls = 0

    def faulty_kernel(self: Any, operands: Any, method: str) -> tuple[Any, Any, Row]:
        nonlocal calls
        raw, final, context = evaluate(self, operands, method)
        calls += 1
        if calls <= 2:
            final = (Decimal(0), Decimal(0 if method == "square-sum" else 1))
            raw = final
        return raw, final, context

    monkeypatch.setattr(core._Kernel, "evaluate", faulty_kernel)
    result, _ = _analyze(core, saved, design)
    assert result["status"] == "inconclusive" and result["reason"] == "invalid-containment"
    row = result["rows"][0]
    assert row["classification"] == "invalid-containment"
    assert row["diagonal"]["matches"] is True
    assert row["metrics"]["width_ratio_product_over_square"] is None
    assert row["metrics"]["width_ratio_status"] == "denominator-zero-numerator-nonzero"
    with pytest.raises(ValueError):
        _verify(auditor, saved, design, result)
