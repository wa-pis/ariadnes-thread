"""Qualify retained point identity using fabricated operands, never real archives."""

import ast
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

import pytest

from bounded_witness_fixtures import load_methods, synthetic_reference

type Row = dict[str, Any]
type Methods = dict[str, ModuleType]

ART = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
OLD_PIN = "6f908729ae72c1f37f763f8e8683cc7a0b2fc9c82d70c826be5116a11510bd07"


@pytest.fixture(scope="module")
def methods() -> Methods:
    loaded = load_methods()
    path = ART / "0244-phase-points.py"
    module = ModuleType("_retained_bounded_point_fixture")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(path.read_bytes(), str(path), "exec"), vars(module))
    return loaded | {"retained_points": module}


@pytest.fixture(scope="module")
def witness(methods: Methods) -> tuple[Row, Row]:
    reference = synthetic_reference(methods, "witness")
    row = methods["points"].point(reference, 151.5, methods)
    assert row["eligible"] and not row["unresolved"]
    return reference, row


def test_only_identity_gate_and_descriptions_change() -> None:
    original = (ART / "0241-phase-points.py").read_bytes()
    assert sha256(original).hexdigest() == OLD_PIN
    old, new = ast.parse(original), ast.parse((ART / "0244-phase-points.py").read_bytes())
    # Compare every operation after removing only the identity predicate/descriptions.
    old.body[0] = new.body[0]
    old_ref = next(node for node in old.body if isinstance(node, ast.FunctionDef) and node.name == "_reference")
    new_ref = next(node for node in new.body if isinstance(node, ast.FunctionDef) and node.name == "_reference")
    old_gate, new_gate = old_ref.body[2].value, new_ref.body[2].value
    assert isinstance(old_gate, ast.Call) and isinstance(new_gate, ast.Call)
    old_conditions, new_conditions = old_gate.args[0], new_gate.args[0]
    assert isinstance(old_conditions, ast.BoolOp) and isinstance(new_conditions, ast.BoolOp)
    assert len(old_conditions.values) == 5 and len(new_conditions.values) == 4
    old_conditions.values = old_conditions.values[2:]
    new_conditions.values = new_conditions.values[1:]
    old_gate.args[1] = new_gate.args[1]
    assert ast.dump(old) == ast.dump(new)


@pytest.mark.parametrize("case", ["witness", "refusal"])
@pytest.mark.parametrize("phase", [150., 151.23456789012345, 152.])
def test_both_fixed_identities_preserve_point_and_independent_audit(
    methods: Methods, case: str, phase: float,
) -> None:
    fabricated = synthetic_reference(methods, case)
    expected = methods["points"].point(fabricated, phase, methods)
    expected_audit = methods["points"].audit_point(fabricated, expected, methods)
    for scope, candidate in (("artificial", "artificial-moon-mars"), ("retained", "d0001-t0035")):
        reference = deepcopy(fabricated)
        # Only a fabricated unit fixture carries retained identity; no saved data are read.
        reference["normalized"].update(scope=scope, candidate_id=candidate)
        actual = methods["retained_points"].point(reference, phase, methods)
        assert actual == expected
        assert methods["retained_points"].audit_point(reference, actual, methods) == expected_audit


@pytest.mark.parametrize("operation", ["point", "audit_point"])
@pytest.mark.parametrize(("scope", "candidate"), [
    ("artificial", "d0001-t0035"), ("retained", "artificial-moon-mars"),
    ("retained", "other"), ("other", "d0001-t0035"),
    ("artificial", "other"), ("", ""),
])
def test_mixed_or_unknown_identity_is_rejected_in_both_paths(
    methods: Methods, witness: tuple[Row, Row], operation: str, scope: str, candidate: str,
) -> None:
    reference, row = deepcopy(witness)
    reference["normalized"].update(scope=scope, candidate_id=candidate)
    args = (reference, 151.5, methods) if operation == "point" else (reference, row, methods)
    with pytest.raises(ValueError, match="fixed scope/candidate"):
        getattr(methods["retained_points"], operation)(*args)


@pytest.mark.parametrize("operation", ["point", "audit_point"])
@pytest.mark.parametrize(("field", "reason"), [
    ("spacecraft", "fixed scope/candidate"), ("commands", "fixed scope/candidate"),
    ("authority", "fixed scope/candidate"), ("origin", "scientific frame"),
    ("time_scale", "scientific frame"), ("epoch", "epoch binding"),
    ("body", "endpoint binding"),
])
def test_retained_identity_does_not_bypass_existing_reference_checks(
    methods: Methods, witness: tuple[Row, Row], operation: str, field: str, reason: str,
) -> None:
    reference, row = deepcopy(witness)
    source = reference["normalized"]
    source.update(scope="retained", candidate_id="d0001-t0035")
    if field == "spacecraft":
        source["spacecraft"]["dry_mass_kg"] = 499.
    elif field == "commands":
        source["command_words"] = ["0x0.0p+0"] * 6
    elif field == "authority":
        source["live_authorized"] = True
    elif field in ("origin", "time_scale"):
        source[field] = "incorrect"
    elif field == "epoch":
        source["epoch_words"][0] = "0x0.0p+0"
    else:
        source["endpoints"][0]["body"] = "Venus"
    args = (reference, 151.5, methods) if operation == "point" else (reference, row, methods)
    with pytest.raises(ValueError, match=reason):
        getattr(methods["retained_points"], operation)(*args)
