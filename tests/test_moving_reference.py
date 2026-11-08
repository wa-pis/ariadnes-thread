"""Synthetic exact-input tests; no retained moving study or real body forces."""

from __future__ import annotations

import ast
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any

import pytest

PATH = (
    Path(__file__).resolve().parents[1]
    / "docs/adr/experiments/0160-moving-reference.py"
)
spec = importlib.util.spec_from_file_location("moving_reference_tests", PATH)
assert spec is not None and spec.loader is not None
reference = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reference
spec.loader.exec_module(reference)


def encoded(values: Any) -> list[dict[str, str]]:
    return [
        {"numerator": str(v.numerator), "denominator": str(v.denominator)}
        for v in values
    ]


def decoded(values: Any) -> tuple[Fraction, ...]:
    return tuple(Fraction(int(v["numerator"]), int(v["denominator"])) for v in values)


def initial(
    position: Any = (0.0, 0.0, 0.0), velocity: Any = (0.0, 0.0, 0.0)
) -> dict[str, Any]:
    return {
        "position_m": list(position),
        "velocity_m_s": list(velocity),
        "epoch_tdb_s": 1000.0,
    }


def motion(values: dict[str, Any], elapsed: float = 0.0) -> dict[str, Any]:
    # Construct test operands locally; the independent oracle never imports this recipe.
    s = Fraction.from_float(elapsed)
    a = (Fraction(-1), Fraction(1, 2), Fraction(-1, 4))
    qi, wi = tuple(v * s * s / 2 for v in a), tuple(v * s for v in a)
    q, w = [float(v) for v in qi], [float(v) for v in wi]
    d = [v * elapsed for v in values["velocity_m_s"]]
    return {
        "label": "controlled-kinematic-arithmetic-probe",
        "elapsed_s": elapsed,
        "elapsed_hex": elapsed.hex(),
        "q_ideal_m": encoded(qi),
        "w_ideal_m_s": encoded(wi),
        "q_m": q,
        "q_hex": [v.hex() for v in q],
        "q_ratios": encoded(map(Fraction.from_float, q)),
        "w_m_s": w,
        "w_hex": [v.hex() for v in w],
        "w_ratios": encoded(map(Fraction.from_float, w)),
        "drift_m": d,
        "position_m": [
            math.fsum((values["position_m"][j], d[j], q[j])) for j in range(3)
        ],
        "velocity_m_s": [
            math.fsum((values["velocity_m_s"][j], w[j])) for j in range(3)
        ],
    }


def row(
    position_km: Any = (2.0, 3.0, 6.0),
    *,
    body: str = "Sun",
    elapsed: float = 0.0,
    slope_km: Any = (0.0, 0.0, 0.0),
    native_offset_m: Any = (0.0, 0.0, 0.0),
) -> dict[str, Any]:
    chains = {"Sun": ((10, 0),), "Earth": ((399, 0),), "Moon": ((301, 399), (399, 0))}
    segments, records = [], []
    for i, (target, centre) in enumerate(chains[body]):
        coeff, slope = (position_km, slope_km) if i == 0 else ((0.0,) * 3, (0.0,) * 3)
        words = [1000.0, 100.0, *[v for pair in zip(coeff, slope) for v in pair]]
        records.append(reference.ORACLE.parse_record(words))
        segments.append(
            {
                "body": target,
                "centre": centre,
                "frame": 1,
                "type": 2,
                "first_tdb_s": 900.0,
                "last_tdb_s": 1100.0,
                "words": words,
            }
        )
    state = [1000 * c + offset for c, offset in zip(position_km, native_offset_m)]
    state.extend(10 * c for c in slope_km)
    return {
        "body": body,
        "elapsed_s": elapsed,
        "hi_tdb_s": 1000.0,
        "hi_hex": (1000.0).hex(),
        "lo_s": elapsed,
        "lo_hex": elapsed.hex(),
        "state_si": state,
        "segments": segments,
        "assessment": reference.ORACLE.assess(state, records, 1000.0, elapsed),
    }


def arms(
    raw: dict[str, Any],
    values: dict[str, Any],
    sample: dict[str, Any],
    gm: float = 49_000_000.0,
) -> dict[str, Any]:
    c = [v * raw["lo_s"] for v in raw["state_si"][3:]]
    r, d, q = values["position_m"], sample["drift_m"], sample["q_m"]
    sums = {
        "compensated": [
            [raw["state_si"][j], -r[j], -d[j], -q[j], c[j]] for j in range(3)
        ],
        "flattened_craft": [
            [raw["state_si"][j], -sample["position_m"][j], c[j]] for j in range(3)
        ],
        "omitted_q": [[raw["state_si"][j], -r[j], -d[j], c[j]] for j in range(3)],
    }
    result = {}
    for name, terms in sums.items():
        delta = [math.fsum(v) for v in terms]
        rho = math.hypot(*delta)
        result[name] = {
            "separation_m": delta,
            "rephasing_m": list(c),
            "acceleration_m_s2": [gm * (v / rho) / (rho * rho) for v in delta],
        }
    return result


def source(
    raw: dict[str, Any],
    values: dict[str, Any] | None = None,
    sample: dict[str, Any] | None = None,
    returned: dict[str, Any] | None = None,
    gm: float = 49_000_000.0,
    radius: float = 1.0,
    event: Any = None,
    progress: Any = None,
) -> dict[str, Any]:
    values = initial() if values is None else values
    sample = motion(values, raw["elapsed_s"]) if sample is None else sample
    returned = arms(raw, values, sample, gm) if returned is None else returned
    return reference.assess_source(
        raw,
        values,
        sample,
        gm,
        radius,
        returned,
        (lambda phase: None) if event is None else event,
        progress=progress,
    )


def totals_arms(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        model: {
            arm: {
                "acceleration_m_s2": [
                    math.fsum(results[i][arm]["acceleration_m_s2"][j] for i in indices)
                    for j in range(3)
                ]
            }
            for arm in reference.ARMS
        }
        for model, indices in {"A": (0, 1), "B": (0, 1, 2)}.items()
    }


@pytest.mark.parametrize(
    "elapsed",
    [0.0, 0.25, 1.0, 0.05260015195876773, 150.00000008940697, 299.9999999701977, 300.0],
)
def test_exact_motion_targets_and_component_gates(elapsed: float) -> None:
    values = initial((float(2**50), -float(2**48), float(2**40)), (0.1, -0.3, 7.1))
    sample = motion(values, elapsed)
    result = reference.assess_motion(values, sample)
    assert result["passed"]
    expected = tuple(
        Fraction.from_float(values["position_m"][j])
        + Fraction.from_float(values["velocity_m_s"][j]) * Fraction.from_float(elapsed)
        + Fraction.from_float(sample["q_m"][j])
        for j in range(3)
    )
    assert decoded(result["exact_position_m"]) == expected
    assert all(
        v["passed"] for group in result["component_gates"].values() for v in group
    )
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    "field",
    [
        "label",
        "elapsed_hex",
        "q_ideal_m",
        "w_ideal_m_s",
        "q_hex",
        "q_ratios",
        "w_hex",
        "w_ratios",
    ],
)
def test_wire_metadata_mutations_fail(field: str) -> None:
    values = initial()
    sample = motion(values, 0.25)
    sample[field] = "incorrect"
    assert not reference.assess_motion(values, sample)["passed"]


@pytest.mark.parametrize(
    "field", ["drift_m", "position_m", "velocity_m_s", "q_m", "w_m_s"]
)
def test_numeric_motion_mutations_fail(field: str) -> None:
    values = initial((1.0, 2.0, 3.0), (1.0, 2.0, 3.0))
    sample = motion(values, 0.25)
    sample[field][0] += 0.125
    assert not reference.assess_motion(values, sample)["passed"]


@pytest.mark.parametrize(
    "value", [True, False, math.nan, math.inf, -math.inf, "0", None, -1.0, 301.0]
)
def test_invalid_elapsed_rejected(value: Any) -> None:
    with pytest.raises(ValueError):
        reference.prescribed_corrections(value)


@pytest.mark.parametrize("field", ["position_m", "velocity_m_s"])
@pytest.mark.parametrize("bad", [[0.0, 0.0], [True, 0.0, 0.0], [math.inf, 0.0, 0.0]])
def test_initial_vector_schema_rejected(field: str, bad: Any) -> None:
    values = initial()
    sample = motion(values)
    values[field] = bad
    with pytest.raises(ValueError):
        reference.assess_motion(values, sample)


@pytest.mark.parametrize("base", [1.0, -1.0, math.ulp(0.0), -math.ulp(0.0)])
def test_half_ulp_alone_does_not_accept_wrong_midpoint_neighbor(base: float) -> None:
    neighbor = math.nextafter(base, math.inf)
    target = (Fraction.from_float(base) + Fraction.from_float(neighbor)) / 2
    expected = float(target)
    wrong = neighbor if base == expected else base
    assert reference._round_gate(expected, target, "m")["passed"]
    rejected = reference._round_gate(wrong, target, "m")
    assert (
        rejected["midpoint"]
        and not rejected["nearest_ties_even"]
        and not rejected["passed"]
    )


def test_subnormal_halfway_preserves_even_zero() -> None:
    target = Fraction.from_float(math.ulp(0.0)) / 2
    accepted = reference._round_gate(0.0, target, "m")
    rejected = reference._round_gate(math.ulp(0.0), target, "m")
    assert accepted["passed"] and accepted["midpoint"]
    assert not rejected["passed"]
    assert decoded([rejected["signed_error"]])[0] == target


def test_zero_is_checked_against_actual_sum_not_unrounded_target() -> None:
    small = Fraction(1, 2**104)
    result = reference._sum_gate(
        float(small), Fraction(), Fraction(1, 2**53), small, "m"
    )
    assert result["passed"] and not result["zero_required"]
    result = reference._sum_gate(
        float(small), Fraction(), Fraction(1, 2**53), Fraction(), "m"
    )
    assert not result["passed"] and result["zero_required"]


def test_signed_zero_is_a_numerical_zero() -> None:
    assert reference._round_gate(-0.0, Fraction(), "m")["passed"]
    assert reference._sum_gate(-0.0, Fraction(), Fraction(), Fraction(), "m")["passed"]


def test_three_dimensional_reference_and_eight_field_ledger() -> None:
    events: list[str] = []
    result = source(row(), event=events.append)
    assert result["passed"] and events == ["attempt", "complete"] * 8
    assert decoded(result["exact_geometries_m"]["d0"]) == (2000, 3000, 6000)
    for profile in ("80", "100"):
        assert result["telescope"][profile]["passed"]
        assert "rephasing_and_drift" in result["contributions_m_s2"][profile]
        assert "residual_rephasing" not in result["contributions_m_s2"][profile]
        assert list(result["gates"][profile]["controls"]) == [
            "flattened_craft",
            "omitted_q",
        ]
    assert reference.BASE.CONTRIBUTIONS[1] == "residual_rephasing"
    assert reference.BASE.ARM_NAMES == ("compensated", "uncorrected", "wrong_sign")


def test_nonzero_motion_source_increment_and_drift_identity() -> None:
    elapsed = 0.05260015195876773
    raw = row(elapsed=elapsed, slope_km=(100.0, -50.0, 25.0))
    values = initial((4.0, -3.0, 7.0), (0.1, 0.3, -0.7))
    result = source(raw, values)
    assert result["passed"] and result["geometry_error_identity"]
    d1, d2 = (decoded(result["exact_geometries_m"][name]) for name in ("d1", "d2"))
    increment = decoded(result["exact_source_increment_error_m"])
    drift = decoded(result["exact_drift_product_error_m"])
    assert any(x != 0 for x in drift)
    assert tuple(a - b for a, b in zip(d2, d1)) == tuple(
        a - b for a, b in zip(increment, drift)
    )


def test_native_source_floor_is_included_in_overall_gate() -> None:
    raw = row((1.0, 0.0, 0.0), native_offset_m=(0.0005, 0.0, 0.0))
    result = source(raw, initial((996.0, 0.0, 0.0)), gm=1.0)
    assert not result["passed"]
    for p in ("80", "100"):
        assert result["gates"][p]["returned_geometry"]["passed"]
        assert not result["gates"][p]["overall"]["passed"]
        assert Decimal(result["contributions_m_s2"][p]["native_source"][0]) != 0


def test_flattened_craft_and_omitted_q_fail_without_stopping_valid_candidate() -> None:
    raw = row((float(2**40), 0.0, 0.0), elapsed=0.25)
    values = initial((raw["state_si"][0] - 4.0, 0.0, 0.0))
    sample = motion(values, 0.25)
    returned = arms(raw, values, sample, 1.0)
    result = source(raw, values, sample, returned, gm=1.0)
    assert result["passed"]
    assert all(not v["passed"] for v in result["gates"]["100"]["controls"].values())
    returned["compensated"] = deepcopy(returned["flattened_craft"])
    progress: dict[str, Any] = {}
    events: list[str] = []
    with pytest.raises(ValueError, match="relative assembly"):
        source(
            raw,
            values,
            sample,
            returned,
            gm=1.0,
            event=events.append,
            progress=progress,
        )
    assert (
        not events and not progress["assembly"]["relative_sum_components"][0]["passed"]
    )


@pytest.mark.parametrize(
    "change",
    ["frame", "type", "body", "coverage", "boolean", "assessment", "elapsed", "epoch"],
)
def test_source_metadata_mutations_fail_before_fields(change: str) -> None:
    raw = row(elapsed=0.25)
    values = initial()
    sample = motion(values, 0.25)
    returned = arms(raw, values, sample)
    if change == "frame":
        raw["segments"][0]["frame"] = 2
    elif change == "type":
        raw["segments"][0]["type"] = 3
    elif change == "body":
        raw["body"] = "Jupiter"
    elif change == "coverage":
        raw["segments"][0]["last_tdb_s"] = 999.0
    elif change == "boolean":
        raw["state_si"][0] = True
    elif change == "assessment":
        raw["assessment"]["passed"] = False
    elif change == "elapsed":
        raw["elapsed_s"] = 0.5
    else:
        values["epoch_tdb_s"] += 1.0
    events: list[str] = []
    with pytest.raises(ValueError):
        source(raw, values, sample, returned, event=events.append)
    assert not events


@pytest.mark.parametrize("bad", [True, math.inf, 0.0, -1.0])
@pytest.mark.parametrize("field", ["gm", "radius"])
def test_invalid_gm_or_radius_rejected(bad: Any, field: str) -> None:
    with pytest.raises(ValueError):
        source(row(), **{field: bad})


def test_domain_failure_retains_guards_without_evaluating_fields() -> None:
    progress: dict[str, Any] = {}
    events: list[str] = []
    with pytest.raises(ValueError, match="exterior-domain"):
        source(row(), radius=7000.0, event=events.append, progress=progress)
    assert not events
    assert not all(progress["assembly"]["domain_guards"].values())
    assert progress["reference"] == {"80": {}, "100": {}}


def test_rephasing_operand_mutation_rejected_before_fields() -> None:
    raw = row(elapsed=0.25, slope_km=(1.0, 0.0, 0.0))
    values = initial()
    sample = motion(values, 0.25)
    returned = arms(raw, values, sample)
    returned["compensated"]["rephasing_m"][0] += 1.0
    events: list[str] = []
    progress: dict[str, Any] = {}
    with pytest.raises(ValueError, match="RN-product"):
        source(raw, values, sample, returned, event=events.append, progress=progress)
    assert not events and not progress["assembly"]["correction_operands_match"]


def test_reference_vector_is_stored_before_completion_callback_failure() -> None:
    progress: dict[str, Any] = {}

    def consume(phase: str) -> None:
        if phase == "complete":
            raise RuntimeError("after return")

    with pytest.raises(RuntimeError, match="after return"):
        source(row(), event=consume, progress=progress)
    assert list(progress["reference"]["80"]) == ["d0"]
    assert progress["assembly"]["geometry_error_identity"]


def test_candidate_field_mutation_fails_required_force_gate() -> None:
    raw, values = row(), initial()
    sample = motion(values)
    returned = arms(raw, values, sample)
    returned["compensated"]["acceleration_m_s2"][0] += 1e-6
    result = source(raw, values, sample, returned)
    assert (
        not result["passed"]
        and not result["gates"]["100"]["returned_geometry"]["passed"]
    )


def model_inputs() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raws = [
        row(),
        row((-2.0, -3.0, -6.0), body="Moon"),
        row((3.0, 0.0, 4.0), body="Earth"),
    ]
    values = initial()
    sample = motion(values)
    returned = [arms(raw, values, sample) for raw in raws]
    assessed = [source(raw, values, sample, arm) for raw, arm in zip(raws, returned)]
    return assessed, totals_arms(returned)


def test_cancellation_preserves_sum_of_source_norm_scale() -> None:
    sources, returned = model_inputs()
    returned["A"]["compensated"]["acceleration_m_s2"][0] = 1e-12
    events: list[str] = []
    result = reference.assess_totals(sources, returned, consume_model=events.append)
    assert events == ["attempt", "complete"] * 2
    assert result["A"]["passed"] and result["B"]["passed"]
    assert all(Decimal(x) == 0 for x in result["A"]["reference"]["100"]["d0"])
    assert Decimal(result["A"]["reference_norms_m_s2"]["100"]["d0"]) > Decimal("1.9")


def test_model_failure_stops_before_later_model_and_preserves_converted_prefix() -> (
    None
):
    sources, returned = model_inputs()
    returned["A"]["compensated"]["acceleration_m_s2"] = [1.0, 0.0, 0.0]
    progress: dict[str, Any] = {}
    events: list[str] = []
    result = reference.assess_totals(
        sources, returned, consume_model=events.append, progress=progress
    )
    assert result is progress and list(result) == ["A"]
    assert not result["A"]["passed"] and events == ["attempt", "complete"]
    assert "rephasing_and_drift" in result["A"]["contributions_m_s2"]["100"]


def test_model_complete_callback_failure_retains_converted_upstream_result() -> None:
    sources, returned = model_inputs()
    progress: dict[str, Any] = {}

    def consume(phase: str) -> None:
        if phase == "complete":
            raise RuntimeError("after model")

    with pytest.raises(RuntimeError, match="after model"):
        reference.assess_totals(
            sources, returned, consume_model=consume, progress=progress
        )
    assert list(progress) == ["A"]
    assert list(progress["A"]["gates"]["100"]["controls"]) == [
        "flattened_craft",
        "omitted_q",
    ]


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "wrong_body", "wrong_model"]
)
def test_model_inventory_corruption_rejected(change: str) -> None:
    sources, returned = model_inputs()
    if change == "missing":
        sources.pop()
    elif change == "duplicate":
        sources[1] = sources[0]
    elif change == "wrong_body":
        sources[1]["body"] = "Mars"
    else:
        returned["C"] = returned.pop("B")
    with pytest.raises(ValueError):
        reference.assess_totals(sources, returned)


def test_reference_imports_no_candidate_or_scientific_library() -> None:
    parsed = ast.parse(PATH.read_text())
    names = []
    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            names.extend(x.name for x in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    assert not any(
        x.split(".")[0] in {"numpy", "scipy", "tudatpy", "spiceypy", "space_nav"}
        for x in names
    )
    assert "0160-moving-study" not in PATH.read_text()


def test_moving_three_four_five_geometry_has_independent_analytic_field() -> None:
    values = initial((496.5, 243.75, -128.875), (1.0, 2.0, 4.0))
    sample = motion(values, 1.0)
    assert reference.assess_motion(values, sample)["passed"]
    result = source(row((0.5, 0.25, -0.125), elapsed=1.0), values, sample, gm=25.0)
    assert result["passed"]
    assert decoded(result["exact_geometries_m"]["d0"]) == (3, 4, 0)
    for profile in ("80", "100"):
        assert [Decimal(x) for x in result["reference"][profile]["d0"]] == [
            Decimal("0.6"),
            Decimal("0.8"),
            Decimal(0),
        ]


def test_motion_numerical_signed_zero_keeps_consistent_metadata() -> None:
    values = initial()
    sample = motion(values)
    sample["q_m"][0] = -0.0
    sample["q_hex"][0] = (-0.0).hex()
    sample["w_m_s"][1] = -0.0
    sample["w_hex"][1] = (-0.0).hex()
    assert reference.assess_motion(values, sample)["passed"]


def test_preflight_accepts_geometry_without_acceleration_and_evaluates_no_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw, values = row(), initial()
    sample = motion(values)
    geometry = {
        name: {"separation_m": [2000.0, 3000.0, 6000.0], "rephasing_m": [0.0] * 3}
        for name in reference.ARMS
    }

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("no force evaluation allowed in preflight")

    monkeypatch.setattr(reference.BASE, "_field", forbidden)
    progress: dict[str, Any] = {}
    prepared = reference.preflight_source(
        raw, values, sample, 49_000_000.0, 1.0, geometry, progress=progress
    )
    assert prepared["geometries_m"]["d0"] == (2000, 3000, 6000)
    assert all(prepared["assembly"]["domain_guards"].values())
    assert progress["reference"] == {"80": {}, "100": {}}
    json.dumps(progress, allow_nan=False)


def test_invalid_last_control_is_rejected_before_any_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw, values = row(), initial()
    sample = motion(values)
    geometry = {
        name: {"separation_m": [2000.0, 3000.0, 6000.0], "rephasing_m": [0.0] * 3}
        for name in reference.ARMS
    }
    geometry["omitted_q"]["separation_m"] = [1.0, 0.0, 0.0]

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("no force evaluation allowed in preflight")

    monkeypatch.setattr(reference.BASE, "_field", forbidden)
    progress: dict[str, Any] = {}
    with pytest.raises(ValueError, match="exterior-domain"):
        reference.preflight_source(
            raw, values, sample, 1.0, 1.0, geometry, progress=progress
        )
    assert progress["assembly"]["domain_guards"]["compensated"]
    assert not progress["assembly"]["domain_guards"]["omitted_q"]
    assert progress["reference"] == {"80": {}, "100": {}}


def test_exact_domain_failure_precedes_all_fields_even_when_binary_arms_are_exterior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = row((1.0, 0.0, 0.0), native_offset_m=(0.0005, 0.0, 0.0))
    values = initial((999.0, 0.0, 0.0))
    sample = motion(values)
    delta = math.fsum((raw["state_si"][0], -values["position_m"][0]))
    geometry = {
        name: {"separation_m": [delta, 0.0, 0.0], "rephasing_m": [0.0] * 3}
        for name in reference.ARMS
    }

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("no force evaluation allowed in preflight")

    monkeypatch.setattr(reference.BASE, "_field", forbidden)
    progress: dict[str, Any] = {}
    with pytest.raises(ValueError, match="exterior-domain"):
        reference.preflight_source(
            raw, values, sample, 1.0, 1.0, geometry, progress=progress
        )
    guards = progress["assembly"]["domain_guards"]
    assert not guards["d0"] and all(guards[name] for name in reference.ARMS)
    assert progress["reference"] == {"80": {}, "100": {}}
