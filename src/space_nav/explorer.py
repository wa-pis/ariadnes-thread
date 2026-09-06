"""Sample the existing M2 approximation; no high-fidelity refinement."""

from __future__ import annotations

import math
from threading import RLock
from typing import cast

from . import ephemeris
from .ephemeris import CartesianState
from .errors import EphemerisError, TransferSearchError
from .models import ImpulsiveTransferCandidate


SCIENCE_LOCK = RLock()
Vector3 = tuple[float, float, float]
Cartesian6 = tuple[float, float, float, float, float, float]


def propagate_two_body(
    initial_state: Cartesian6, elapsed_s: float, gm_m3_s2: float,
) -> Cartesian6:
    """Propagate a central-body-relative J2000 state in m and m/s with Tudat."""
    values = (*initial_state, elapsed_s, gm_m3_s2)
    if len(initial_state) != 6 or any(
        isinstance(v, bool) or not isinstance(v, (int, float))
        or not math.isfinite(v) for v in values
    ) or elapsed_s < 0 or gm_m3_s2 <= 0:
        raise TransferSearchError("Two-body sampling requires finite SI inputs")
    try:
        from tudatpy.astro import element_conversion, two_body_dynamics

        elements = element_conversion.cartesian_to_keplerian(
            initial_state, gm_m3_s2,
        )
        propagated = two_body_dynamics.propagate_kepler_orbit(
            elements, elapsed_s, gm_m3_s2,
        )
        result = tuple(float(v) for v in element_conversion.keplerian_to_cartesian(
            propagated, gm_m3_s2,
        ))
    except Exception as exc:
        raise TransferSearchError(f"Tudat two-body sampling failed: {exc}") from exc
    if len(result) != 6 or not all(math.isfinite(v) for v in result):
        raise TransferSearchError("Tudat returned a non-finite sampled state")
    return cast(Cartesian6, result)


def sample_transfer(
    candidate: ImpulsiveTransferCandidate, count: int = 121,
) -> tuple[CartesianState, ...]:
    """Return immutable SI/SSB/J2000 states at TDB epochs for an M2 candidate."""
    if isinstance(count, bool) or not isinstance(count, int) or not 2 <= count <= 1001:
        raise TransferSearchError("sample count must be an integer in [2, 1001]")
    with SCIENCE_LOCK:
        try:
            start = candidate.departure_epoch_tdb_s
            moon = ephemeris._query_body_state_tdb("Moon", start)
            sun = ephemeris._query_body_state_tdb("Sun", start)
            initial = cast(Cartesian6, tuple(
                moon.position_m[i] - sun.position_m[i] for i in range(3)
            ) + tuple(
                moon.velocity_m_s[i] - sun.velocity_m_s[i]
                + candidate.departure_v_infinity_m_s[i] for i in range(3)
            ))
            gm = ephemeris._get_body_gravitational_parameter("Sun")
            states = []
            for index in range(count):
                epoch = start + candidate.flight_time_s * index / (count - 1)
                relative = propagate_two_body(initial, epoch - start, gm)
                sun = ephemeris._query_body_state_tdb("Sun", epoch)
                states.append(CartesianState(
                    body="Spacecraft", epoch_utc=sun.epoch_utc,
                    epoch_tdb_s=epoch, origin="SSB", orientation="J2000",
                    position_m=cast(Vector3, tuple(
                        relative[i] + sun.position_m[i] for i in range(3)
                    )),
                    velocity_m_s=cast(Vector3, tuple(
                        relative[i + 3] + sun.velocity_m_s[i] for i in range(3)
                    )),
                ))
            mars = ephemeris._query_body_state_tdb("Mars", candidate.arrival_epoch_tdb_s)
            expected_velocity = tuple(
                mars.velocity_m_s[i] + candidate.arrival_v_infinity_m_s[i]
                for i in range(3)
            )
            if (math.dist(states[-1].position_m, mars.position_m) > 100.0
                    or math.dist(states[-1].velocity_m_s, expected_velocity) > 0.001):
                raise TransferSearchError("Sampled arc does not match M2 arrival")
            return tuple(states)
        except EphemerisError as exc:
            raise TransferSearchError(
                f"Candidate {candidate.candidate_id}: sampling resource error: {exc}"
            ) from exc
