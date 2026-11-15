"""Manufacture R5.59b fixture states from tilted hyperbolic polar elements."""

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, localcontext
from hashlib import sha256
import json
import math
from typing import Any

type Vector = tuple[float, float, float]
type Bundle = dict[str, Any]  # JSON boundary


@dataclass(frozen=True, slots=True)
class KnownEndpoint:
    """Analytic truth before synthetic SSB binary64 rounding."""

    body: str
    epoch_tdb_s: float
    gm_m3_s2: float
    guard_m: float
    r_m: Vector
    orbital_m_s: Vector
    hyperbolic_m_s: Vector
    excess_m_s: Vector
    root: str
    future_minimum_radius_m: float


def linear(a: float, p: Vector, b: float, q: Vector) -> Vector:
    return (a * p[0] + b * q[0], a * p[1] + b * q[1], a * p[2] + b * q[2])


def _endpoint(body: str, epoch_tdb_s: float, gm_m3_s2: float, guard_m: float,
              rp_m: float, eccentricity: float, anomaly_rad: float,
              p_hat: Vector, q_hat: Vector, *, arrival: bool) -> KnownEndpoint:
    # Manufacture truth from orbital elements rather than the inverse inequality or roots.
    semilatus_m = rp_m * (1 + eccentricity)
    c, s = math.cos(anomaly_rad), math.sin(anomaly_rad)
    radius_m = semilatus_m / (1 + eccentricity * c)
    r_m = linear(radius_m * c, p_hat, radius_m * s, q_hat)
    direction = -1.0 if arrival else 1.0
    speed_m_s = math.sqrt(gm_m3_s2 / semilatus_m)
    hyperbolic_m_s = linear(-direction * speed_m_s * s, p_hat,
                            direction * speed_m_s * (eccentricity + c), q_hat)
    circular_m_s = direction * math.sqrt(gm_m3_s2 / radius_m)
    orbital_m_s = linear(-circular_m_s * s, p_hat, circular_m_s * c, q_hat)
    far_c = -1 / eccentricity
    far_s = math.sqrt(1 - far_c**2)
    excess_speed_m_s = direction * math.sqrt(gm_m3_s2 * (eccentricity - 1) / rp_m)
    excess_m_s = linear(excess_speed_m_s * far_c, p_hat, excess_speed_m_s * far_s, q_hat)
    # Relative to the transverse unit direction induced by the future asymptote.
    root = "positive" if c * far_s - s * far_c > 0 else "negative"
    return KnownEndpoint(body, epoch_tdb_s, gm_m3_s2, guard_m, r_m, orbital_m_s,
                         hyperbolic_m_s, excess_m_s, root, radius_m if s >= 0 else rp_m)


def known_geometry() -> tuple[KnownEndpoint, KnownEndpoint]:
    """Includes an initially inward Moon branch and physical incoming Mars branch."""
    return (
        _endpoint("Moon", 2**30 + 128.0, 4_902_800_121_846.8, 1_737_400.0, 1_800_000.0,
                  1.15, -0.85, (1.0, 0.0, 0.0), (0.0, 0.6, 0.8), arrival=False),
        _endpoint("Mars", 2**30 + 50_128.0, 42_828_375_815_756.1, 3_396_190.0, 3_700_000.0,
                  1.12, 0.35, (0.6, 0.8, 0.0), (-48/65, 36/65, 5/13), arrival=True),
    )


def wire(value: object) -> bytes:
    """Canonical artificial-section serialization; bundle padding is external."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def rebind(bundle: Bundle) -> Bundle:
    """Repin synthetic sections after a deliberate fixture mutation."""
    bundle["pins"] = {key: sha256(wire(section)).hexdigest() for key, section in bundle["sections"].items()}
    return bundle


def build() -> Bundle:
    """Create a new six-section artificial bundle; no files or real sources are read."""
    geometry = known_geometry()
    translations = ([2**37, -2**36, 2**35, 12000., -28000., 4000.],
                    [-2**37, 2**37, -2**36, -25000., -10000., 1000.])
    endpoints, audits = [], []
    with localcontext(prec=80):
        for endpoint, translation in zip(geometry, translations, strict=True):
            state = endpoint.r_m + endpoint.orbital_m_s
            ssb = [body + relative for body, relative in zip(translation, state, strict=True)]
            decimal_relative = [str(Decimal.from_float(x) - Decimal.from_float(y))
                                for x, y in zip(ssb, translation, strict=True)]
            row = dict(body=endpoint.body, epoch_tdb_s=endpoint.epoch_tdb_s,
                       body_ssb_si=list(map(float, translation)), endpoint_ssb_si=ssb)
            endpoints.append(row)
            audits.append(dict(**deepcopy(row), relative_si=decimal_relative,
                               orbit_relative_si=[str(Decimal.from_float(x)) for x in state],
                               gm_m3_s2=endpoint.gm_m3_s2, guard_m=endpoint.guard_m))

    scenario = dict(synthetic=True, frame="SSB/J2000", units="SI", time_scale="TDB seconds since J2000")
    candidate = "artificial-moon-mars"
    t0, tf = (endpoint.epoch_tdb_s for endpoint in geometry)
    return rebind({
        "schema": "ariadna-r559b-artificial-v1",
        "sections": {
            "r1": dict(scenario=scenario, candidate=candidate,
                       excess_m_s=[list(endpoint.excess_m_s) for endpoint in geometry]),
            "r4": dict(scenario=deepcopy(scenario), candidate=candidate, endpoints=endpoints, failures=[]),
            "audit": dict(endpoints=audits),
            "baseline": dict(failures=[]),
            "fractions": dict(failures=[]),
            "contract": dict(epochs_tdb_s=[t0, (t0 + tf)/2, tf], model="artificial-two-body"),
        },
    })
