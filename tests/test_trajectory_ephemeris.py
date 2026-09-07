from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path
import platform

import numpy as np
import pytest

from space_nav import ephemeris, trajectory
from space_nav.scenario import load_scenario
from space_nav.transfer import search_impulsive_transfers


ROOT = Path(__file__).resolve().parents[1]


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
        }
        for epoch in epochs:
            direct = np.asarray(
                spice.get_body_cartesian_state_at_epoch(
                    body, "SSB", "J2000", "NONE", epoch
                )
            ).reshape(6)
            coarse = np.asarray(nominal.cartesian_state(epoch)).reshape(6)
            fine = np.asarray(dense.cartesian_state(epoch)).reshape(6)
            for label, difference in (
                ("300s_direct", coarse - direct),
                ("150s_direct", fine - direct),
                ("300s_150s", coarse - fine),
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
