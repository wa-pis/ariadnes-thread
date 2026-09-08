from __future__ import annotations

import json
from fractions import Fraction
from importlib.metadata import version
import math
from pathlib import Path
import platform

import numpy as np
import pytest

from space_nav import ephemeris, trajectory
from space_nav.scenario import load_scenario
from space_nav.transfer import search_impulsive_transfers


ROOT = Path(__file__).resolve().parents[1]


def _rational_lagrange_state(
    epochs_tdb_s: list[float], states_si: np.ndarray, epoch_tdb_s: float,
) -> np.ndarray:
    """Exact polynomial of supplied binary SI states; not a SPICE error bound."""
    nodes = [Fraction(epoch) for epoch in epochs_tdb_s]
    target = Fraction(epoch_tdb_s)
    weights = [
        math.prod((target - other) / (node - other)
                  for index, other in enumerate(nodes) if index != selected)
        for selected, node in enumerate(nodes)
    ]
    return np.asarray([
        float(sum((weight * Fraction(float(value)) for weight, value in zip(weights, column)),
                  Fraction(0)))
        for column in states_si.T
    ])


@pytest.mark.parametrize("degree", range(6))
def test_rational_ephemeris_oracle_reproduces_polynomials(degree: int) -> None:
    origin_tdb_s = 978995455.2304223
    offsets_s = [-2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
    nodes_tdb_s = [origin_tdb_s + offset for offset in offsets_s]
    states_si = np.asarray([
        [(component + 1) * offset ** degree for component in range(6)]
        for offset in offsets_s
    ])
    # Include knots and off-grid evaluations; each SI component is independent.
    for offset_s in (0.0, 0.125, 0.5, 0.875, 1.0):
        actual = _rational_lagrange_state(nodes_tdb_s, states_si, origin_tdb_s + offset_s)
        expected = np.asarray([(component + 1) * offset_s ** degree for component in range(6)])
        np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-12)


@pytest.mark.parametrize("phase", ["departure", "cruise", "arrival"])
@pytest.mark.parametrize("duration_s", [30.0, 300.0, 86400.0])
def test_moving_body_chord_deviation_is_not_interpolation_error(
    phase: str, duration_s: float,
) -> None:
    """Measure required motion allowances; sampled maxima are not upper bounds."""
    from tudatpy.dynamics import environment_setup

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    departure_s, arrival_s = evidence["epoch_tdb_s"][0], evidence["epoch_tdb_s"][-1]
    fraction = {"departure": 0.0, "cruise": 0.5, "arrival": 1.0}[phase]
    start_s = departure_s + fraction * (arrival_s - departure_s - duration_s)
    end_s = start_s + duration_s
    spice = ephemeris._ensure_standard_kernels()
    settings = trajectory._create_time_limited_body_settings(
        environment_setup, start_s, end_s,
    )
    trajectory._validate_time_limited_body_settings(settings, start_s, end_s)
    # Include the midpoint and off-grid samples even for a whole-day interval.
    fractions = np.unique(np.append(np.linspace(0.0, 1.0, 34), 0.5))
    epochs_s = start_s + fractions * duration_s
    measurements: dict[str, dict[str, float]] = {}
    for body in trajectory.PHYSICAL_BODY_NAMES:
        table = environment_setup.create_body_ephemeris(
            settings.get(body).ephemeris_settings, body,
        )
        safe_start_s, safe_end_s = environment_setup.get_safe_interpolation_interval(table)
        assert safe_start_s <= start_s < end_s <= safe_end_s
        assert table.frame_origin == "SSB" and table.frame_orientation == "J2000"
        direct = np.asarray([
            spice.get_body_cartesian_state_at_epoch(body, "SSB", "J2000", "NONE", epoch)
            for epoch in epochs_s
        ]).reshape(-1, 6)
        native = np.asarray([table.cartesian_state(epoch) for epoch in epochs_s]).reshape(-1, 6)
        assert np.all(np.isfinite(direct)) and np.all(np.isfinite(native))
        errors = native - direct
        position_error_m = float(np.max(np.linalg.norm(errors[:, :3], axis=1)))
        velocity_error_m_s = float(np.max(np.linalg.norm(errors[:, 3:], axis=1)))
        assert position_error_m <= 0.025, (phase, duration_s, body, position_error_m)
        assert velocity_error_m_s <= 2.5e-6, (phase, duration_s, body, velocity_error_m_s)
        # Subtract the first position before forming the chord to reduce SSB cancellation.
        direct_offsets = direct[:, :3] - direct[0, :3]
        native_offsets = native[:, :3] - native[0, :3]
        direct_defect = direct_offsets - fractions[:, None] * direct_offsets[-1]
        native_defect = native_offsets - fractions[:, None] * native_offsets[-1]
        # Each chord is a convex combination of its two endpoints. The difference
        # in the two defects is therefore <= twice the input position allowance.
        assert np.max(np.linalg.norm(native_defect - direct_defect, axis=1)) <= 2 * 0.025
        direct_deviation_m = float(np.max(np.linalg.norm(direct_defect, axis=1)))
        if body in {"Earth", "Moon", "Mars"} and duration_s >= 300.0:
            assert direct_deviation_m > 1.0
        measurements[body] = {
            "sampled_direct_chord_deviation_m": direct_deviation_m,
            "sampled_native_chord_deviation_m": float(np.max(
                np.linalg.norm(native_defect, axis=1),
            )),
            "sampled_position_error_m": position_error_m,
            "sampled_velocity_error_m_s": velocity_error_m_s,
        }
    print(json.dumps({
        "candidate_id": evidence["candidate_id"], "phase": phase,
        "start_tdb_s": start_s, "duration_s": duration_s, "sample_count": len(fractions),
        "origin": "SSB", "orientation": "J2000", "time_scale": "TDB seconds since J2000",
        "scope": "Sampled lower bounds on required body-motion allowance; not safety upper bounds",
        "measurements": measurements,
    }, sort_keys=True, allow_nan=False))


def test_full_candidate_interpolation_against_direct_spice() -> None:
    """Qualify SI/SSB/J2000 states, not propagated trajectory accuracy."""
    import tudatpy
    from tudatpy.dynamics import environment_setup

    scenario = load_scenario(ROOT / "examples/m3_feasible_mission.toml")
    candidate = next(
        item
        for item in search_impulsive_transfers(scenario).pareto_front
        if item.candidate_id == "d0001-t0035"
    )
    start = candidate.departure_epoch_tdb_s
    end = candidate.arrival_epoch_tdb_s
    # Offset interior samples from both 300 s and 150 s grids; include arc edges.
    epochs = sorted(
        {start, start + 0.125, start + 75.25, end - 75.25, end - 0.125, end}
        | {
            start + ((end - start) * index / 33 // 300) * 300 + 37.125
            for index in range(1, 33)
        }
    )
    settings = trajectory._create_time_limited_body_settings(
        environment_setup, start, end
    )
    trajectory._validate_time_limited_body_settings(settings, start, end)
    with pytest.raises(ValueError, match="do not cover"):
        trajectory._validate_time_limited_body_settings(settings, start - 86400.0, end)
    with pytest.raises(ValueError, match="do not cover"):
        trajectory._validate_time_limited_body_settings(settings, start, end + 86400.0)
    dense_settings = environment_setup.get_default_body_settings_time_limited(
        trajectory.PHYSICAL_BODY_NAMES,
        start,
        end,
        "SSB",
        "J2000",
        150.0,
    )
    spice = ephemeris._ensure_standard_kernels()
    errors: dict[str, dict[str, list[float]]] = {}
    for body in trajectory.PHYSICAL_BODY_NAMES:
        nominal = environment_setup.create_body_ephemeris(
            settings.get(body).ephemeris_settings, body
        )
        dense = environment_setup.create_body_ephemeris(
            dense_settings.get(body).ephemeris_settings, body
        )
        for table in (nominal, dense):
            safe_start, safe_end = environment_setup.get_safe_interpolation_interval(
                table
            )
            assert safe_start <= start < end <= safe_end
            assert table.frame_origin == "SSB" and table.frame_orientation == "J2000"
        differences: dict[str, list[list[float]]] = {
            "300s_direct": [],
            "150s_direct": [],
            "300s_150s": [],
            "300s_rational_polynomial": [],
        }
        body_settings = settings.get(body).ephemeris_settings
        grid_start_s = body_settings.initial_time
        step_s = body_settings.time_step
        for epoch in epochs:
            direct = np.asarray(
                spice.get_body_cartesian_state_at_epoch(
                    body, "SSB", "J2000", "NONE", epoch
                )
            ).reshape(6)
            coarse = np.asarray(nominal.cartesian_state(epoch)).reshape(6)
            fine = np.asarray(dense.cartesian_state(epoch)).reshape(6)
            lower_index = math.floor((epoch - grid_start_s) / step_s)
            # Native six-stage interior window: two knots before the lower knot,
            # that knot, and three after it. Never reconstruct a boundary spline.
            nodes_tdb_s = [grid_start_s + index * step_s
                           for index in range(lower_index - 2, lower_index + 4)]
            assert grid_start_s < nodes_tdb_s[0] < nodes_tdb_s[-1] < body_settings.final_time
            node_states_si = np.asarray([
                spice.get_body_cartesian_state_at_epoch(body, "SSB", "J2000", "NONE", node)
                for node in nodes_tdb_s
            ]).reshape(6, 6)
            rational_state_si = _rational_lagrange_state(nodes_tdb_s, node_states_si, epoch)
            for label, difference in (
                ("300s_direct", coarse - direct),
                ("150s_direct", fine - direct),
                ("300s_150s", coarse - fine),
                ("300s_rational_polynomial", coarse - rational_state_si),
            ):
                assert np.all(np.isfinite(difference))
                differences[label].append(
                    [
                        float(np.linalg.norm(difference[:3])),
                        float(np.linalg.norm(difference[3:])),
                    ]
                )
        errors[body] = {
            label: np.max(values, axis=0).tolist()
            for label, values in differences.items()
        }
        for position_m, velocity_m_s in errors[body].values():
            assert position_m <= 0.025, (body, errors[body])
            assert velocity_m_s <= 2.5e-6, (body, errors[body])
        del nominal, dense
    print(
        json.dumps(
            {
                "candidate_id": candidate.candidate_id,
                "epoch_tdb_s": epochs,
                "error_units": ["m", "m/s"],
                "origin": "SSB",
                "orientation": "J2000",
                "time_scale": "TDB seconds since J2000",
                "interpolation": "Tudat default six-point Lagrange",
                "steps_s": [300.0, 150.0],
                "state_error_limits": {"position_m": 0.025, "velocity_m_s": 2.5e-6},
                "scope": "Sampled input-state qualification, not a bound on propagated trajectory error",
                "python": platform.python_version(),
                "platform": platform.platform(),
                "tudatpy": tudatpy.__version__,
                "numpy": version("numpy"),
                "kernels": ephemeris.kernel_metadata(),
                "max_errors": errors,
            },
            sort_keys=True,
            allow_nan=False,
        )
    )
