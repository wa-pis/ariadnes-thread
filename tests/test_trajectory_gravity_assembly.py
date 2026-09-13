"""Gravity-only assembly at ideal sources and fixed stored harmonic matrices."""

from fractions import Fraction
from hashlib import sha256
from itertools import product
import json
import math
from pathlib import Path
import shutil

import pytest

from space_nav import trajectory
from test_trajectory_midpoint import _midpoint_acceleration_l2_bound_m_s2


def _gravity_midpoint(
    budget: trajectory._RefinementBudget,
    boxes: dict[str, tuple[tuple[Fraction, Fraction], ...]],
    allowances: dict[str, Fraction],
) -> tuple[tuple[float, ...], dict[str, Fraction]]:
    budget.check()
    assert set(boxes) == set(trajectory.PHYSICAL_BODY_NAMES)
    assert set(allowances) == {"mars_midpoint", "moon_source", "mars_source"}
    assert all(isinstance(value, Fraction) and value >= 0 for value in allowances.values())
    for box in boxes.values():
        assert len(box) == 3 and all(len(pair) == 2 and all(isinstance(value, Fraction) for value in pair)
                                     and pair[0] <= pair[1] for pair in box)
        budget.check()
    summed = tuple(tuple(sum((boxes[body][axis][side] for body in trajectory.PHYSICAL_BODY_NAMES), Fraction(0))
                         for side in (0, 1)) for axis in range(3))
    midpoint, box_error = _midpoint_acceleration_l2_bound_m_s2(summed, Fraction(0))
    budget.check()
    return midpoint, {"box_midpoint": box_error, **allowances}


def _finite_fraction(value: float) -> Fraction:
    assert type(value) is float and math.isfinite(value)
    return Fraction(value)


def _load_gravity_assembly(data: Path, budget: trajectory._RefinementBudget) -> tuple[dict, dict]:
    budget.check()
    ledger = json.loads((data / "m3_gravity_assembly_inputs.json").read_text())
    names = ("m3_fresh_point_gravity_intervals.json", "m3_separate_tail_midpoint_verification.json",
             "m3_fresh_harmonic_source_errors.json", "m3_fresh_harmonic_replay.json")
    assert set(ledger["input_sha256"]) == set(names)
    documents = []
    for name in names:
        raw = (data / name).read_bytes()
        assert sha256(raw).hexdigest() == ledger["input_sha256"][name], name
        documents.append(json.loads(raw))
        budget.check()
    points, mars, errors, replay = documents
    errors = errors["fresh_harmonic_source_errors"]
    assert len(errors) == 2 and {row["body"] for row in errors} == {"Moon", "Mars"}
    for document in (ledger, points, mars, replay, *errors):
        assert document["epoch_tdb_s"] == 978995455.2929223
        assert document["origin"] == "SSB" and document["orientation"] == "J2000"
    assert ledger["acceleration_unit"] == points["acceleration_unit"] == "m/s^2"
    assert ledger["target_source_convention"] == "exact position polynomials at fixed nominal spacecraft state"
    assert ledger["harmonic_matrix_convention"] == "stored binary64 matrices held fixed"
    assert ledger["moon_box_includes_tail"] is True
    assert ledger["moon_evaluated_through_degree"] == 20 and ledger["moon_maximum_degree"] == 200
    assert mars["snapshot_sha256"] == ledger["input_sha256"][names[3]]
    assert set(replay["fields"]) == {"Moon", "Mars"}
    for row in errors:
        resource = replay["fields"][row["body"]]["resource"]
        assert row["coefficient_sha256"] == resource["actual_sha256"] == resource["expected_sha256"]
        assert row["degree"] == resource["degree"] == resource["order"] == (200 if row["body"] == "Moon" else 120)
    boxes = {body: tuple(tuple(_finite_fraction(value) for value in pair) for pair in box)
             for body, box in points["body_intervals_m_s2"].items()}
    assert set(boxes) == set(trajectory.PHYSICAL_BODY_NAMES) - {"Moon", "Mars"}
    boxes["Moon"] = tuple(tuple(_finite_fraction(value) for value in pair) for pair in ledger["moon_stored_component_intervals_m_s2"])
    boxes["Mars"] = tuple((_finite_fraction(value), _finite_fraction(value)) for value in mars["midpoint_m_s2"])
    allowances = {"mars_midpoint": _finite_fraction(mars["separate_tail_l2_error_upper_m_s2"])}
    allowances.update({row["body"].lower()+"_source": _finite_fraction(row["acceleration_l2_allowance_m_s2"]) for row in errors})
    budget.check()
    return boxes, allowances


def test_retained_gravity_assembly() -> None:
    budget = trajectory._RefinementBudget("gravity-assembly", 300.0)
    boxes, allowances = _load_gravity_assembly(Path(__file__).parent / "data", budget)
    midpoint, channels = _gravity_midpoint(budget, boxes, allowances)
    total = sum(channels.values(), Fraction(0))
    reported = math.nextafter(float(total), math.inf)
    assert math.isfinite(reported) and Fraction(reported) >= total > 0
    assert {key: value for key, value in channels.items() if key != "box_midpoint"} == allowances
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)
    print(json.dumps({"gravity_only_assembly": {
        "epoch_tdb_s": 978995455.2929223, "origin": "SSB", "orientation": "J2000",
        "midpoint_m_s2": midpoint, "acceleration_l2_allowance_m_s2": reported,
        "error_channels_m_s2": {key: math.nextafter(float(value), math.inf) if value else 0.0 for key, value in channels.items()},
        "source_convention": "exact position polynomials", "harmonic_matrix_convention": "stored matrices held fixed",
        "scope": "Gravity only at nominal state; no PCK, native arithmetic, other forces or interval certificate",
        "additional_native_queries": 0, "additional_native_arcs": 0,
    }}, sort_keys=True, allow_nan=False))


@pytest.mark.parametrize("shift", [Fraction(0), Fraction(1, 3), Fraction(2**60)])
def test_gravity_sum_encloses_independent_corners_and_balls(shift: Fraction) -> None:
    zero = ((Fraction(0), Fraction(0)),)*3
    boxes = {body: zero for body in trajectory.PHYSICAL_BODY_NAMES}
    boxes["Sun"] = ((shift-1, shift+1), (Fraction(-2), Fraction(2)), (Fraction(0), Fraction(0)))
    boxes["Earth"] = ((1-shift, 1-shift), (Fraction(3), Fraction(3)), (Fraction(0), Fraction(0)))
    allowances = {"mars_midpoint": Fraction(1, 2), "moon_source": Fraction(1, 4), "mars_source": Fraction(1, 8)}
    midpoint, channels = _gravity_midpoint(trajectory._RefinementBudget("sum-control", 300.0), boxes, allowances)
    assert midpoint == (1.0, 3.0, 0.0)
    radius = sum(channels.values(), Fraction(0))
    directions = ((Fraction(1), Fraction(0), Fraction(0)), (Fraction(3, 5), Fraction(4, 5), Fraction(0)))
    for x, y, direction in product((Fraction(0), Fraction(2)), (Fraction(1), Fraction(5)), directions):
        truth = tuple(a+Fraction(7, 8)*b for a, b in zip((x, y, Fraction(0)), direction, strict=True))
        assert sum((a-Fraction(b))**2 for a, b in zip(truth, midpoint, strict=True)) <= radius**2


def test_gravity_sum_retains_cancellation_below_binary64_precision() -> None:
    boxes = {body: ((Fraction(0), Fraction(0)),)*3 for body in trajectory.PHYSICAL_BODY_NAMES}
    for body, value in (("Sun", 2**60), ("Mercury", 1), ("Venus", -2**60)):
        boxes[body] = ((Fraction(value), Fraction(value)), (Fraction(0), Fraction(0)), (Fraction(0), Fraction(0)))
    midpoint, channels = _gravity_midpoint(trajectory._RefinementBudget("sum-cancellation", 300.0), boxes,
                                         {key: Fraction(0) for key in ("mars_midpoint", "moon_source", "mars_source")})
    assert midpoint == (1.0, 0.0, 0.0) and sum(channels.values()) == 0


@pytest.mark.parametrize("invalid", ["body", "extra-tail", "negative", "inexact", "shape", "reversed"])
def test_gravity_sum_rejects_invalid_channels(invalid: str) -> None:
    boxes = {body: ((Fraction(0), Fraction(0)),)*3 for body in trajectory.PHYSICAL_BODY_NAMES}
    allowances = {key: Fraction(0) for key in ("mars_midpoint", "moon_source", "mars_source")}
    if invalid == "body":
        del boxes["Sun"]
    elif invalid == "extra-tail":
        allowances["mars_tail"] = Fraction(1)
    elif invalid in {"negative", "inexact"}:
        allowances["moon_source"] = Fraction(-1) if invalid == "negative" else 0.0
    else:
        boxes["Sun"] = () if invalid == "shape" else ((Fraction(1), Fraction(0)),)*3
    with pytest.raises(AssertionError):
        _gravity_midpoint(trajectory._RefinementBudget("sum-invalid", 300.0), boxes, allowances)


@pytest.mark.parametrize("invalid", ["hash", "epoch", "frame", "origin", "body-set", "midpoint-shape", "coefficient", "replay", "nan", "negative", "interval"])
def test_gravity_input_rejection(tmp_path: Path, invalid: str) -> None:
    data = Path(__file__).parent / "data"
    ledger = json.loads((data / "m3_gravity_assembly_inputs.json").read_text())
    for name in ledger["input_sha256"]:
        shutil.copyfile(data / name, tmp_path / name)
    name = "m3_fresh_harmonic_source_errors.json" if invalid in {"coefficient", "nan", "negative"} else "m3_separate_tail_midpoint_verification.json"
    if invalid == "body-set":
        name = "m3_fresh_point_gravity_intervals.json"
    document = json.loads((tmp_path / name).read_text())
    if invalid == "hash":
        ledger["input_sha256"][name] = "0"*64
    elif invalid == "epoch":
        document["epoch_tdb_s"] += 1
    elif invalid == "frame":
        document["orientation"] = "ECLIPJ2000"
    elif invalid == "origin":
        document["origin"] = "Earth"
    elif invalid == "body-set":
        del document["body_intervals_m_s2"]["Sun"]
    elif invalid == "midpoint-shape":
        document["midpoint_m_s2"] = []
    elif invalid == "replay":
        document["snapshot_sha256"] = "0"*64
    elif invalid == "interval":
        ledger["moon_stored_component_intervals_m_s2"][0] = [1.0, -1.0]
    elif invalid == "coefficient":
        document["fresh_harmonic_source_errors"][0]["coefficient_sha256"] = "0"*64
    else:
        document["fresh_harmonic_source_errors"][0]["acceleration_l2_allowance_m_s2"] = math.nan if invalid == "nan" else -1.0
    raw = json.dumps(document).encode()
    (tmp_path / name).write_bytes(raw)
    if invalid != "hash":
        ledger["input_sha256"][name] = sha256(raw).hexdigest()
    (tmp_path / "m3_gravity_assembly_inputs.json").write_text(json.dumps(ledger))
    budget = trajectory._RefinementBudget("load-invalid", 300.0)
    with pytest.raises(AssertionError):
        _gravity_midpoint(budget, *_load_gravity_assembly(tmp_path, budget))


def test_gravity_sum_rejects_expired_budget() -> None:
    clock = iter([0.0, 301.0])
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _gravity_midpoint(trajectory._RefinementBudget("sum-expired", 300.0, lambda: next(clock)), {}, {})
