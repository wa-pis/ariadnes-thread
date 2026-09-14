"""Common fresh force midpoint, not native arithmetic or trajectory safety."""

from fractions import Fraction
from hashlib import sha256
from itertools import product
import json
import math
from pathlib import Path

import pytest

from space_nav import trajectory
from test_trajectory_gravity_assembly import _finite_fraction
from test_trajectory_midpoint import _midpoint_acceleration_l2_bound_m_s2


def _force_group_midpoint(
    budget: trajectory._RefinementBudget,
    groups: dict[str, tuple[tuple[float, ...], float]],
) -> tuple[tuple[float, ...], dict[str, Fraction]]:
    budget.check()
    assert set(groups) == {"gravity", "srp", "schwarzschild"}
    vectors, channels = {}, {}
    for name, (vector, error) in groups.items():
        assert len(vector) == 3
        vectors[name] = tuple(map(_finite_fraction, vector))
        channels[name] = _finite_fraction(error)
        assert channels[name] >= 0
    exact = tuple(sum((vector[axis] for vector in vectors.values()), Fraction(0)) for axis in range(3))
    midpoint, rounding = _midpoint_acceleration_l2_bound_m_s2(tuple((value, value) for value in exact), Fraction(0))
    budget.check()
    return midpoint, {**channels, "final_midpoint": rounding}


@pytest.mark.parametrize("shift", [0.0, float(2**60)])
def test_force_groups_preserve_cancellation_and_error_balls(shift: float) -> None:
    groups = {"gravity": ((shift, 0.0, 0.0), 0.5), "srp": ((1.0, 0.0, 0.0), 0.25),
              "schwarzschild": ((-shift, 0.0, 0.0), 0.125)}
    midpoint, channels = _force_group_midpoint(trajectory._RefinementBudget("force-sum", 300.0), groups)
    assert midpoint == (1.0, 0.0, 0.0)
    assert channels == {"gravity": Fraction(1, 2), "srp": Fraction(1, 4), "schwarzschild": Fraction(1, 8), "final_midpoint": Fraction(0)}
    directions = ((Fraction(1), Fraction(0), Fraction(0)), (Fraction(3, 5), Fraction(-4, 5), Fraction(0)))
    for signs, direction in product(product((-1, 1), repeat=3), directions):
        perturbation = sum((sign*Fraction(error) for sign, (_, error) in zip(signs, groups.values(), strict=True)), Fraction(0))
        assert sum((perturbation*x)**2 for x in direction) <= sum(channels.values())**2


def test_force_groups_retain_final_rounding() -> None:
    groups = {"gravity": ((1.0, 0.0, 0.0), 0.0), "srp": ((2.0**-54, 0.0, 0.0), 0.0),
              "schwarzschild": ((0.0, 0.0, 0.0), 0.0)}
    midpoint, channels = _force_group_midpoint(trajectory._RefinementBudget("force-rounding", 300.0), groups)
    assert midpoint == (1.0, 0.0, 0.0)
    assert channels["final_midpoint"] == Fraction(1, 2**54)
    assert sum(channels.values()) == channels["final_midpoint"]


@pytest.mark.parametrize("invalid", ["missing", "extra-tail", "negative", "nan", "boolean", "shape", "nonfinite-vector"])
def test_force_groups_reject_invalid_inputs(invalid: str) -> None:
    groups = {name: ((0.0,)*3, 0.0) for name in ("gravity", "srp", "schwarzschild")}
    if invalid == "missing":
        del groups["srp"]
    elif invalid == "extra-tail":
        groups["mars-tail"] = ((0.0,)*3, 1.0)
    elif invalid in {"negative", "nan", "boolean"}:
        groups["gravity"] = ((0.0,)*3, {"negative": -1.0, "nan": math.nan, "boolean": True}[invalid])
    else:
        groups["gravity"] = (() if invalid == "shape" else (math.inf, 0.0, 0.0), 0.0)
    with pytest.raises(AssertionError):
        _force_group_midpoint(trajectory._RefinementBudget("force-invalid", 300.0), groups)


@pytest.mark.parametrize("expiry_check", [1, 2])
def test_force_groups_preserve_deadline(expiry_check: int) -> None:
    clock = iter([0.0]*expiry_check+[301.0])
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _force_group_midpoint(trajectory._RefinementBudget("force-expired", 300.0, lambda: next(clock)),
                              {name: ((0.0,)*3, 0.0) for name in ("gravity", "srp", "schwarzschild")})


def test_retained_fresh_force_assembly() -> None:
    budget = trajectory._RefinementBudget("fresh-force-assembly", 300.0)
    data = Path(__file__).parent / "data"
    documents = []
    for name, expected in (
        ("m3_gravity_only_assembly.json", "a10cbb8627452fcb93776d6b47b0a1dad085f021c80e8923d112a443d8c1bca4"),
        ("m3_fresh_srp_vector.json", "e383d36894b6eb7597ea5bcee002c70b25e2d3a91b82b2f6de68587176bae01c"),
        ("m3_fresh_schwarzschild_vector.json", "33252c0de39b7621e5ee742f96a6929838accd225453db50c8bd332138b85c0c"),
        ("m3_fresh_light_inputs.json", "78228d371cf23325aaf7ad10559157513d95fa24f7d7a5703e5ed495cd12b7e4"),
        ("m3_fresh_harmonic_replay.json", "e401d88cbdd0110ac6c0357612b0053a34f87f8953856ac3372360e5ea3dca99"),
    ):
        raw = (data / name).read_bytes()
        assert sha256(raw).hexdigest() == expected
        documents.append(json.loads(raw))
        budget.check()
    gravity, srp, relativity = (document[key] for document, key in zip(documents[:3],
        ("gravity_only_assembly", "fresh_srp_vector", "fresh_schwarzschild_vector"), strict=True))
    light, replay = documents[3]["fresh_light_inputs"], documents[4]
    for document in (gravity, srp, relativity, light, replay):
        assert document["epoch_tdb_s"] == 978995455.2929223
        assert document["origin"] == "SSB" and document["orientation"] == "J2000"
    assert light["model_id"] == trajectory.PHYSICAL_MODEL_IDENTIFIER
    assert light["spacecraft_state_m_m_s"] == replay["spacecraft_position_m"]+replay["spacecraft_velocity_m_s"]
    assert light["spacecraft_mass_kg"] == replay["spacecraft_mass_kg"]
    assert light["pck_sha256"] == replay["pck_sha256"]
    assert gravity["source_convention"] == srp["source_convention"] == "exact position polynomials"
    assert gravity["harmonic_matrix_convention"] == "stored matrices held fixed"
    assert relativity["source_convention"] == "exact Sun type-2 position polynomials and their derivatives"
    assert srp["full_light_by_occultor"] == light["full_light_by_occultor"] == {"Moon": True, "Earth": True, "Mars": True}
    groups = {name: (tuple(document["midpoint_m_s2"]), document["acceleration_l2_allowance_m_s2"])
              for name, document in zip(("gravity", "srp", "schwarzschild"), (gravity, srp, relativity), strict=True)}
    midpoint, channels = _force_group_midpoint(budget, groups)
    # Group totals already include their tails, source bridges and rounding.
    assert all(channels[name] == Fraction(group[1]) for name, group in groups.items())
    total = sum(channels.values(), Fraction(0))
    reported = math.nextafter(float(total), math.inf)
    assert math.isfinite(reported) and Fraction(reported) >= total > 0
    budget.check()
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)
    print(json.dumps({"fresh_force_assembly": {
        "epoch_tdb_s": light["epoch_tdb_s"], "origin": "SSB", "orientation": "J2000",
        "model_id": trajectory.PHYSICAL_MODEL_IDENTIFIER,
        "spacecraft_state_m_m_s": light["spacecraft_state_m_m_s"], "spacecraft_mass_kg": light["spacecraft_mass_kg"],
        "midpoint_m_s2": midpoint, "acceleration_l2_allowance_m_s2": reported,
        "error_channels_m_s2": {key: math.nextafter(float(value), math.inf) if key == "final_midpoint" and value else float(value)
                                for key, value in channels.items()},
        "source_convention": "exact position polynomials; Sun velocity is their type-2 derivative",
        "harmonic_matrix_convention": "stored matrices held fixed",
        "additional_native_queries": 0, "additional_native_arcs": 0,
        "scope": "Gravity, fully lit SRP and PPN=1 Sun Schwarzschild at fixed nominal coast state; no PCK/native force arithmetic, state/time domain or mission certificate",
    }}, sort_keys=True, allow_nan=False))
