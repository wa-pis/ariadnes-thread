"""Test saved-only lineage with manually fabricated endpoints and no scientific replay."""

from collections import Counter
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

from lineage_fixtures import (
    ART, ROOT, ROLES, SCOPE, contract, fabricated_archive, rechain, reseal,
    wire, write_artificial_pack,
)

type Row = dict[str, Any]


@pytest.fixture(scope="module")
def core() -> Row:
    return run_path(str(ART / "0230-lineage-core.py"))


@pytest.fixture(scope="module")
def verifier() -> Row:
    return run_path(str(ART / "0230-lineage-audit.py"))


@pytest.fixture(scope="module")
def archive() -> Row:
    return fabricated_archive()


@pytest.fixture(scope="module")
def design() -> Row:
    return contract()


def _analyze(core: Row, archive: Row, design: Row, *, scope: str = SCOPE) -> tuple[Row, Counter[str]]:
    used: Counter[str] = Counter()

    def charge(kind: str, count: int = 1) -> None:
        used[kind] += count

    result = core["analyze"](archive, design, scope=scope, check=lambda: None, charge=charge)
    return result, used


def _verify(verifier: Row, archive: Row, design: Row, result: Row, *, scope: str = SCOPE) -> Row:
    return verifier["verify"](archive, design, result, scope=scope,
                              check=lambda: None, charge=lambda kind, count=1: None)


@pytest.fixture(scope="module")
def produced(core: Row, archive: Row, design: Row) -> Row:
    return _analyze(core, archive, design)[0]


def _event(row: Row, stage: str, kind: str = "return") -> Row:
    return next(event for event in row["trace"]["events"] if event["stage"] == stage and event["event"] == kind)


def test_full_volume_is_numeric_descriptors_and_separately_pinned_artificial_records(tmp_path: Path) -> None:
    profile = write_artificial_pack(tmp_path / "inputs")
    design = contract()
    paths = {role: Path(path) for role, path in profile["inputs"].items()}
    data_bytes = sum(path.stat().st_size for path in paths.values())
    pinned_source_bytes = sum((ROOT / path).stat().st_size for path in design["source_bindings"].values())
    assert 3_784_677 <= data_bytes + pinned_source_bytes < 4 * 1024**2
    assert set(paths) == set(profile["pins"]) == set(ROLES)
    assert profile["scope"] == SCOPE and profile["candidate_id"] == "artificial-saved-lineage-case"
    assert profile["reference_sha256"] != design["inherited_reference_sha256"]
    assert profile["completion_sha256"] != design["completion_sha256"]
    assert profile["expected_events"] == 1248
    for role, path in paths.items():
        raw = path.read_bytes()
        assert profile["pins"][role] == dict(sha256=sha256(raw).hexdigest(), bytes=len(raw))
    saved = fabricated_archive()
    assert len(saved["report"]["saved_endpoint_descriptors"]) == 6156
    assert not any("padding" in key for key in saved["report"])
    endpoints = [endpoint for row in saved["report"]["rows"] for event in row["trace"]["events"]
                 for interval in event["fields"].values() for endpoint in interval.values()]
    assert any("E+120" in value for value in endpoints) and any("E-90" in value for value in endpoints)
    assert all(90 <= len(Decimal(value).as_tuple().digits) <= 96 for value in endpoints)


def test_complete_matrix_has_independently_verified_aliases_and_exact_counters(
    core: Row, verifier: Row, archive: Row, design: Row, produced: Row,
) -> None:
    result, counted = _analyze(core, archive, design)
    assert result == produced
    assert result["status"] == "lineage-qualified-attribution-unresolved" and result["scope"] == SCOPE
    assert len(result["checkpoints"]) == 432 and len(result["comparisons"]) == 216
    assert len(result["lineage"]) == 528 and len(result["norm_pairs"]) == 36
    assert all(link["status"] == "matched" for link in result["lineage"])
    assert result["counts"] == dict(counted) == dict(event_visits=1248, descriptors=648, aliases=528, norm_pairs=36)
    proof = _verify(verifier, archive, design, result)
    assert proof["status"] == "lineage-independently-verified"
    assert proof["produced_sha256"] == sha256(wire(result)).hexdigest()


def test_all_three_local_norm_dispositions_are_distinct_from_final_attribution(produced: Row) -> None:
    assert Counter(pair["status"] for pair in produced["norm_pairs"]) == Counter({
        "no-local-difference-observed": 12, "conditional-local-method-response": 12, "input-confounded": 12,
    })
    assert {pair["role"] for pair in produced["norm_pairs"]} == {
        "impulse-squared", "radius-squared", "angular-momentum-squared",
    }
    assert all(pair["context_assumption"] in produced["assumptions"] for pair in produced["norm_pairs"])
    assert all(pair["attribution_limit"] == "No contribution to final width or dominant cause is established."
               for pair in produced["norm_pairs"])
    assert "local matched-operand response does not quantify contribution to final arrival width" in produced["limitations"]


def test_cell_singleton_difference_and_zero_denominator_are_exact_and_descriptive(produced: Row) -> None:
    radii = [record for record in produced["comparisons"] if (record["stage"], record["field"]) == ("_ellipse", "radius")]
    assert len(radii) == 12
    assert all(record["cell_width"] == record["difference"] == "2" and record["singleton_width"] == "0"
               and record["ratio"] is None and record["units"] == "m" for record in radii)
    assert all(record["status"] == "matched" for record in radii)


def test_equal_numbers_from_distinct_source_origins_are_not_an_extra_alias(
    core: Row, verifier: Row, archive: Row, design: Row,
) -> None:
    saved = deepcopy(archive)
    for row in saved["report"]["rows"]:
        _event(row, "_reverse")["fields"]["radius"] = deepcopy(_event(row, "_ellipse")["fields"]["radius"])
        reseal(row["trace"])
    rechain(saved)
    result, _ = _analyze(core, saved, design)
    assert len(result["lineage"]) == 528
    assert all(".radius" not in link["source"] and ".radius" not in link["target"] for link in result["lineage"])
    assert _verify(verifier, saved, design, result)["status"] == "lineage-independently-verified"


@pytest.mark.parametrize("early", ["before-reverse", "mass-exit"])
def test_explicit_early_dispositions_do_not_invent_observations(
    core: Row, verifier: Row, design: Row, early: str,
) -> None:
    saved = fabricated_archive(early=early)
    result, used = _analyze(core, saved, design)
    assert used["event_visits"] == saved["_context"]["expected_events"]
    assert len(result["checkpoints"]) == 432 and len(result["norm_pairs"]) == 36
    if early == "before-reverse":
        assert saved["_context"]["expected_events"] == 96
        assert all(pair["status"] == "not-reached" for pair in result["norm_pairs"])
        assert all(record["status"] == "not-reached" and record["width"] is None for record in result["checkpoints"])
    else:
        assert saved["_context"]["expected_events"] == 1152
        assert all(row["trace"]["stages"]["_clearance"]["status"] == "not-reached" for row in saved["report"]["rows"])
        assert all(record["status"] == "observed" for record in result["checkpoints"])
    assert _verify(verifier, saved, design, result)["status"] == "lineage-independently-verified"


@pytest.mark.parametrize("fault", ["alias", "parent", "call-order", "missing-field", "path-flag", "result", "nan", "huge-exponent"])
def test_resealed_saved_numeric_and_tree_mutations_are_invalid(
    core: Row, verifier: Row, archive: Row, design: Row, produced: Row, fault: str,
) -> None:
    saved = deepcopy(archive)
    row = saved["report"]["rows"][0]
    if fault == "alias":
        _event(row, "bounds")["fields"]["r[0]"]["hi"] = "99999"
    elif fault == "parent":
        _event(row, "_reverse", "call")["parent"] = 999
    elif fault == "call-order":
        _event(row, "_reverse", "call")["call"] = 999
    elif fault == "missing-field":
        del _event(row, "_ellipse")["fields"]["radius"]
    elif fault == "path-flag":
        _event(row, "_reverse")["scalars"]["independent"] = True
    elif fault == "result":
        row["trace"]["result"]["reason"] = "guard"
    else:
        _event(row, "_reverse")["fields"]["root"]["hi"] = "NaN" if fault == "nan" else "1E+513"
    reseal(row["trace"])
    rechain(saved)
    with pytest.raises(ValueError):
        _analyze(core, saved, design)
    with pytest.raises(ValueError):
        _verify(verifier, saved, design, produced)


@pytest.mark.parametrize("fault", ["role", "units", "context", "scope"])
def test_contract_role_dimensions_context_and_scope_cannot_be_relabeled(
    core: Row, verifier: Row, archive: Row, design: Row, produced: Row, fault: str,
) -> None:
    saved, changed = deepcopy(archive), deepcopy(design)
    if fault == "role":
        changed["norm_pair_roles"][0]["direct_norm2_ordinal"] = 1
    elif fault == "units":
        changed["checkpoint_fields"]["_ellipse"]["radius"] = "kg"
    elif fault == "context":
        saved["_context"]["context_justified"] = False
    else:
        saved["_context"]["scope"] = "retained"
    with pytest.raises(ValueError):
        _analyze(core, saved, changed)
    with pytest.raises(ValueError):
        _verify(verifier, saved, changed, produced)


@pytest.mark.parametrize("fault", ["claim", "alias-pointer", "unit", "local-disposition"])
def test_independent_verifier_rejects_unsupported_claims_and_output_mutations(
    verifier: Row, archive: Row, design: Row, produced: Row, fault: str,
) -> None:
    changed = deepcopy(produced)
    if fault == "claim":
        changed["norm_pairs"][0]["attribution_limit"] = "This proves the dominant cause of final width."
    elif fault == "alias-pointer":
        changed["lineage"][0]["to"] = changed["lineage"][0]["from"]
    elif fault == "unit":
        changed["checkpoints"][0]["units"] = "kg"
    else:
        changed["norm_pairs"][0]["status"] = "conditional-local-method-response"
    with pytest.raises(ValueError):
        _verify(verifier, archive, design, changed)
