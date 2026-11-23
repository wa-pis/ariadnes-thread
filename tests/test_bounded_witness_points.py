"""Qualify arbitrary binary64 points on fabricated operands without archive reads."""

from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import importlib.util
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

import pytest

type Row = dict[str, Any]
type Methods = dict[str, ModuleType]

ART = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
PINS = {
    "core": ("0208-seed-worksheet.py", "4907db44f0ef53cb657cd563a6fa27df8a138442807c703a66c1343bde4788ba"),
    "oracle": ("0208-seed-oracle.py", "cf4041c69e5204f79ab6786be5e393c0dbc0977317e693587eb1a85e8265e475"),
    "reader": ("0210-retained-readback.py", "a6e1b9a32f0c46c9e03974c1367a8b04d2849eca86d807907a3bcefa1f0e8920"),
    "orbit": ("0213-phase-orbit.py", "ba78ca47097703cb27ed7dca8d844b9be34c61b1fee9a5668fae97db039979c3"),
    "screen": ("0213-phase-screen.py", "39d59baecb394f759ef6a775ce6cca548e4828dbfef94207b47c9e048d1d0f2b"),
    "old_points": ("0219-phase-points.py", "a9eca487527068c8114ff00353846e39fcf6eb7212009c5046b4df0cc23af223"),
    "anchors": ("0220-phase-anchors.py", "7fadcb3fc9de4a43aa1ce80efd30d2e6499f76ee4918519cf8783d50bca2057e"),
}


def _load(name: str, filename: str, expected: str | None = None) -> ModuleType:
    path = ART / filename
    raw = path.read_bytes()
    if expected is not None:
        assert sha256(raw).hexdigest() == expected
    spec = importlib.util.spec_from_file_location("bounded_points_"+name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


@pytest.fixture(scope="module")
def methods() -> Methods:
    loaded = {name: _load(name, filename, pin) for name, (filename, pin) in PINS.items()}
    return loaded | {"points": _load("new_points", "0241-phase-points.py")}


@pytest.fixture(scope="module")
def witness(methods: Methods) -> Row:
    return methods["old_points"].fixture("witness", methods)["reference"]


@pytest.mark.parametrize("phase", [150., 152., math.nextafter(151., 152.), 151.23456789012345])
def test_exact_binary64_phase_and_independent_readback(methods: Methods, witness: Row, phase: float) -> None:
    points = methods["points"]
    row = points.point(witness, phase, methods)
    assert row["phase_word"] == phase.hex()
    assert row["phase_ratio"] == list(phase.as_integer_ratio())
    assert row["phase_deg"] == str(Fraction(phase))
    assert row["angle_word"] == (math.tau*phase/360).hex()
    assert set(row["branches"]) == {"positive", "negative"}
    checked = points.audit_point(witness, row, methods)
    assert checked["eligible"] == row["eligible"]
    assert checked["unresolved"] is False
    if not phase.is_integer():
        assert row["phase_ratio"][1] > 64


@pytest.mark.parametrize("phase", [True, 150, Fraction(151), float("nan"), float("inf"),
                                  math.nextafter(150., -math.inf), math.nextafter(152., math.inf)])
def test_reject_non_binary64_and_out_of_domain(methods: Methods, witness: Row, phase: Any) -> None:
    with pytest.raises(ValueError, match="plain binary64"):
        methods["points"].point(witness, phase, methods)


def test_plain_float_subclass_is_rejected(methods: Methods, witness: Row) -> None:
    class Phase(float):
        pass

    with pytest.raises(ValueError, match="plain binary64"):
        methods["points"].point(witness, Phase(151), methods)


def test_frozen_anchor_refusals_and_costs_are_preserved(methods: Methods) -> None:
    source = methods["old_points"].fixture("refusal", methods)
    for degree, previous in zip((150, 151, 152), source["anchors"], strict=True):
        current = methods["points"].point(source["reference"], float(degree), methods)
        saved = deepcopy(previous)
        saved["index"] = degree
        for pair in saved["pairs"]:
            pair["index"] = degree
        methods["anchors"].verify_anchor(saved, current, degree, methods["reader"])
        assert current["eligible"] == [] and current["unresolved"] is False
        assert len(current["pairs"]) == sum(branch["reason"] is None for branch in current["branches"].values())
        assert all(pair["reason"] == "commanded-dry-floor"
                   and math.isfinite(pair["total_delta_v_m_s"]) for pair in current["pairs"])
        assert methods["points"].audit_point(source["reference"], current, methods)["eligible"] == []


def test_off_grid_witness_keeps_literal_commands(methods: Methods, witness: Row) -> None:
    row = methods["points"].point(witness, 151.5, methods)
    assert row["eligible"]
    for sign in row["eligible"]:
        pair = next(pair for pair in row["pairs"] if pair["roots"][1] == sign)
        assert len(pair["command_words"]) == 6
        assert set(pair["ledgers"]["mass_kg_exact"]) == {"commanded", "effective"}
    assert methods["points"].audit_point(witness, row, methods)["eligible"] == row["eligible"]


def test_endpoint_witness_only_in_isolated_point_verifier(methods: Methods, witness: Row) -> None:
    ref = deepcopy(witness)
    ref["normalized"]["endpoints"][1]["v_infinity_m_s"] = [
        value*.99 for value in ref["normalized"]["endpoints"][1]["v_infinity_m_s"]]
    for phase in (150., 152.):
        row = methods["points"].point(ref, phase, methods)
        assert row["eligible"]
        assert methods["points"].audit_point(ref, row, methods)["eligible"] == row["eligible"]


def test_guard_and_degenerate_keep_two_explicit_slots(methods: Methods) -> None:
    ref = methods["old_points"].fixture("transition", methods)["reference"]
    row = methods["points"].point(ref, 150.125, methods)
    assert row["branch_dispositions"]["positive"] == "guard"
    assert all(pair["roots"][1] != "positive" for pair in row["pairs"])
    assert methods["points"].audit_point(ref, row, methods)["branch_dispositions"]["positive"] == "guard"
    ref["normalized"]["endpoints"][1]["v_infinity_m_s"] = [0., 0., 0.]
    row = methods["points"].point(ref, 150.125, methods)
    assert row["branch_dispositions"] == {"positive": "degenerate", "negative": "degenerate"}
    assert row["pairs"] == [] and row["eligible"] == [] and row["unresolved"] is False
    assert methods["points"].audit_point(ref, row, methods)["eligible"] == []


def test_audit_never_replays_primary_or_optimizer(methods: Methods, witness: Row, monkeypatch: pytest.MonkeyPatch) -> None:
    points = methods["points"]
    row = points.point(witness, 151.5, methods)

    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("independent audit called a producer evaluator")

    monkeypatch.setattr(points, "point", forbidden)
    monkeypatch.setattr(points, "_state", forbidden)
    monkeypatch.setattr(methods["core"], "audited_roots", forbidden)
    monkeypatch.setattr(methods["core"], "float_branches", forbidden)
    monkeypatch.setattr(methods["core"], "sequence", forbidden)
    monkeypatch.setattr(methods["orbit"], "_local_state", forbidden)
    monkeypatch.setattr(methods["screen"], "_pair", forbidden)
    assert points.audit_point(witness, row, methods)["eligible"] == row["eligible"]


@pytest.mark.parametrize("field", ["phase_word", "phase_ratio", "angle_word", "relative_si", "ssb_si",
                                   "independent_relative_si", "eligible", "branch-slot", "branch-sign",
                                   "command", "ledger", "tnw", "speed"])
def test_independent_audit_rejects_record_tampering(methods: Methods, witness: Row, field: str) -> None:
    row = methods["points"].point(witness, 151.5, methods)
    assert row["eligible"]
    sign = row["eligible"][0]
    pair = next(pair for pair in row["pairs"] if pair["roots"][1] == sign)
    if field == "phase_word":
        row[field] = math.nextafter(151.5, 152.).hex()
    elif field == "phase_ratio":
        row[field][0] += 1
    elif field == "angle_word":
        row[field] = math.nextafter(float.fromhex(row[field]), math.inf).hex()
    elif field in ("relative_si", "ssb_si"):
        row[field][0] += .01
    elif field == "independent_relative_si":
        row[field][0] = "0"
    elif field == "eligible":
        row[field] = []
    elif field == "branch-slot":
        del row["branches"]["negative"]
    elif field == "branch-sign":
        row["branches"]["positive"], row["branches"]["negative"] = row["branches"]["negative"], row["branches"]["positive"]
    elif field == "command":
        pair["command_words"][0] = math.nextafter(float.fromhex(pair["command_words"][0]), math.inf).hex()
    elif field == "ledger":
        pair["ledgers"]["mass_kg_exact"]["effective"][-1] = "500"
    elif field == "tnw":
        angle = math.nextafter(row["branches"][sign]["angles_rad"][0], math.inf)
        row["branches"][sign]["angles_rad"][0] = angle
        pair["command_words"][3] = angle.hex()
    elif field == "speed":
        row["branches"][sign]["independent_speed_m_s"] = "1"
    with pytest.raises(ValueError):
        methods["points"].audit_point(witness, row, methods)


def test_historical_and_event_refusals_retain_objective(methods: Methods, witness: Row) -> None:
    ref = deepcopy(witness)
    row = methods["points"].point(ref, 151.5, methods)
    pair = next(pair for pair in row["pairs"] if pair["roots"][1] in row["eligible"])
    ref["normalized"]["rejected_command_words"] = [pair["command_words"]]
    rejected = methods["points"].point(ref, 151.5, methods)
    historical = next(p for p in rejected["pairs"] if p["roots"] == pair["roots"])
    assert historical["reason"] == "historically-rejected"
    assert historical["total_delta_v_m_s"] == pair["total_delta_v_m_s"]
    assert methods["points"].audit_point(ref, rejected, methods)["eligible"] == rejected["eligible"]
    ref["normalized"]["epochs_tdb_s"][1] = ref["normalized"]["epochs_tdb_s"][0]+1.
    ref["normalized"]["epoch_words"] = [x.hex() for x in ref["normalized"]["epochs_tdb_s"]]
    event = methods["points"].point(ref, 151.5, methods)
    assert all(p["reason"] == "exact-event-order" and math.isfinite(p["total_delta_v_m_s"]) for p in event["pairs"])
    assert methods["points"].audit_point(ref, event, methods)["eligible"] == []


def test_reject_retained_scope_and_fixed_lunar_drift(methods: Methods, witness: Row) -> None:
    ref = deepcopy(witness)
    ref["normalized"]["scope"] = "retained"
    with pytest.raises(ValueError, match="artificial"):
        methods["points"].point(ref, 151.5, methods)
    ref = deepcopy(witness)
    ref["lunar"]["angles_rad"][0] = math.nextafter(ref["lunar"]["angles_rad"][0], math.inf)
    row = methods["points"].point(ref, 151.5, methods)
    with pytest.raises(ValueError, match="TNW"):
        methods["points"].audit_point(ref, row, methods)


def test_newly_rounded_oracle_commands_cannot_replace_literals(methods: Methods, witness: Row) -> None:
    row = methods["points"].point(witness, 151.5, methods)
    sign = row["eligible"][0]
    pair = next(pair for pair in row["pairs"] if pair["roots"][1] == sign)
    source = witness["normalized"]
    moon, mars = source["endpoints"]
    from decimal import Decimal

    precise = row["independent_relative_si"]
    oracle = methods["oracle"]
    departure = oracle.branches(tuple(moon["relative_si"][:3]), tuple(moon["relative_si"][3:]),
        tuple(str(Decimal(x)) for x in moon["v_infinity_m_s"]),
        str(Decimal(moon["gm_m3_s2"])), str(Decimal(moon["guard_m"])), arrival=False)["positive"]
    arrival = oracle.branches(tuple(precise[:3]), tuple(precise[3:]),
        tuple(str(Decimal(x)) for x in mars["v_infinity_m_s"]),
        str(Decimal(mars["gm_m3_s2"])), str(Decimal(mars["guard_m"])), arrival=True)[sign]
    durations, _ = oracle.mass(departure["speed"], arrival["speed"])
    angles = [methods["core"].angles_of(tuple(float(x) for x in root["tnw"])) for root in (departure, arrival)]
    substitute = [value.hex() for value in (*angles[0], float(durations[0]), *angles[1], float(durations[1]))]
    assert substitute != pair["command_words"]
    pair["command_words"] = substitute
    with pytest.raises(ValueError, match="controls"):
        methods["points"].audit_point(witness, row, methods)


def test_unresolved_second_root_prevents_any_admission(methods: Methods, witness: Row,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    original = methods["core"].audited_roots

    def unresolved(*args: Any, **kwargs: Any) -> tuple[Row, Row]:
        roots, branches = original(*args, **kwargs)
        branches["negative"] = {"reason": "independent-classification", "primary": None, "oracle": "guard"}
        roots.pop("negative", None)
        return roots, branches

    monkeypatch.setattr(methods["core"], "audited_roots", unresolved)
    row = methods["points"].point(witness, 151.5, methods)
    assert row["unresolved"] is True and row["eligible"] == [] and row["pairs"] == []
    assert row["branch_dispositions"]["negative"] == "unresolved"
    assert methods["points"].audit_point(witness, row, methods)["unresolved"] is True
