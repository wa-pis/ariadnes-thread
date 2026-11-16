"""Fabricate a tilted Mars ellipse and a four-record, source-bound phase-study input."""

from decimal import Decimal, localcontext
from hashlib import sha256
import json
import math
from pathlib import Path
from runpy import run_path
from tempfile import TemporaryDirectory
from typing import Any

type Vector = tuple[float, float, float]
type Row = dict[str, Any]

HERE = Path(__file__).resolve().parent
P: Vector = (0.6, 0.8, 0.)
Q: Vector = (-48/65, 36/65, 5/13)
RP_M = 3_689_500.
ECC = 0.53
GM_MARS = 42_828_375_815_756.1
GUARD_MARS = 3_396_190.
MARS_SHAPE_M = 3_389_500.
T0 = 2**30 + 128.
TF = 2**30 + 50_128.
EXPECTED_INDEX = 95
EXPECTED_ROOT = "positive"


def _linear(a: float, p: Vector, b: float, q: Vector) -> Vector:
    return (a*p[0]+b*q[0], a*p[1]+b*q[1], a*p[2]+b*q[2])


def _cross(p: Vector, q: Vector) -> Vector:
    return (p[1]*q[2]-p[2]*q[1], p[2]*q[0]-p[0]*q[2], p[0]*q[1]-p[1]*q[0])


def _dot(p: Vector, q: Vector) -> float:
    return math.fsum(x*y for x, y in zip(p, q, strict=True))


def _unit(p: Vector) -> Vector:
    length = math.hypot(*p)
    return (p[0]/length, p[1]/length, p[2]/length)


def _moon() -> tuple[Vector, Vector, Vector, Vector]:
    seed = run_path(str(HERE / "0208-seed-fixtures.py"))
    moon = seed["_endpoint"]("Moon", T0, 4_902_800_121_846.8, 1_737_400., 1_800_000., 3.4, .85,
                             (1., 0., 0.), (0., .6, .8), arrival=False)
    return moon.r_m, moon.orbital_m_s, moon.hyperbolic_m_s, moon.excess_m_s


def _mars_state(k: int) -> tuple[Vector, Vector]:
    turn = math.radians(k)
    c, s = math.cos(turn), math.sin(turn)
    radius_m = RP_M * (1+ECC) / (1+ECC*c)
    orbital_scale_m_s = math.sqrt(GM_MARS / (RP_M * (1+ECC)))
    return (_linear(radius_m*c, P, radius_m*s, Q),
            _linear(-orbital_scale_m_s*s, P, orbital_scale_m_s*(ECC+c), Q))


def _excess(*, impossible: bool) -> Vector:
    tilt, heading = map(math.radians, (4, 120))
    in_plane = _linear(math.cos(heading), P, math.sin(heading), Q)
    speed = 12_000. if impossible else 2500.
    return _linear(speed*math.cos(tilt), in_plane, speed*math.sin(tilt), _cross(P, Q))


def _wire(row: Row) -> bytes:
    return (json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _archives(builder: Row, *, impossible: bool) -> dict[str, bytes]:
    sources = builder["build"]()
    r1_key, r4_key, audit_key, seed_key, fractions_key = (
        builder[name] for name in ("R1", "R4", "AUDIT", "BASELINE", "FRACTIONS"))
    r1, r4, audit, seed, fractions = map(json.loads, (sources[key] for key in
                                                    (r1_key, r4_key, audit_key, seed_key, fractions_key)))
    scenario = r1["normalized_scenario"]
    candidate = r1["runs"][0]["selected"]
    moon_r_m, moon_v_m_s, _, moon_excess = _moon()
    target_r_m, target_v_m_s = _mars_state(0)
    for index, (leg, orbit_key, exact) in enumerate((
        ("departure", "departure_orbit", moon_r_m + moon_v_m_s),
        ("arrival", "target_orbit", target_r_m + target_v_m_s),
    )):
        row = audit["rows"][index]
        stored, body = row["stored_endpoint"], row["stored_body"]
        body_si = [*body["position_m"], *body["velocity_m_s"]]
        ssb_si = [x + y for x, y in zip(body_si, exact, strict=True)]
        stored.update(position_m=ssb_si[:3], velocity_m_s=ssb_si[3:])
        if index == 0:
            shape = row["shape_radius_m"]
            orbit = builder["_orbit"]("Moon", shape, list(map(str, exact)))
            excess = moon_excess
        else:
            orbit = dict(central_body="Mars", periapsis_altitude_m=RP_M - MARS_SHAPE_M,
                         apoapsis_altitude_m=RP_M * (1+ECC)/(1-ECC) - MARS_SHAPE_M,
                         eccentricity=ECC, inclination_rad=math.acos(12/13),
                         raan_rad=math.atan2(P[1], P[0]), argument_of_periapsis_rad=0., true_anomaly_rad=0.)
            excess = _excess(impossible=impossible)
        with localcontext(prec=90):
            relative = [str(Decimal(x)-Decimal(y)) for x, y in zip(ssb_si, body_si, strict=True)]
        oracle = [str(Decimal(x)) for x in exact]
        row.update(orbit=orbit, retained_relative_exact=relative, binary64_relative=list(exact),
                   decimal80_relative=oracle, decimal100_relative=oracle)
        scenario[orbit_key] = orbit
        candidate[f"{leg}_v_infinity_m_s"] = excess
        for rec in r4, fractions:
            for trial in rec["science"]["runs"]:
                if index == 0:
                    trial["run"]["boundaries"][0] = stored
                else:
                    trial["run"]["target_state"] = stored
    for run in r1["runs"]:
        run["selected"] = candidate
    for rec in r4, seed, fractions:
        rec["science"]["scenario"] = scenario
    for rec in r4, fractions:
        rec["science"]["candidate"] = candidate
    sources.update({r1_key: _wire(r1), r4_key: _wire(r4), audit_key: _wire(audit),
                    seed_key: _wire(seed), fractions_key: _wire(fractions)})
    return builder["relink"](sources)


def build(root: Path, *, impossible: bool = False) -> dict[str, str]:
    """Write and pin a fresh artificial refusal with the actual R5.59c evidence schema."""
    builder = run_path(str(HERE / "0209-archive-fixtures.py"))
    runner = run_path(str(HERE / "0210-retained-runner.py"))
    with TemporaryDirectory(prefix="r559e-artificial-sources-", dir=root.parent) as tmp:
        source_dir = Path(tmp)
        sources = _archives(builder, impossible=impossible)
        builder["write"](source_dir, sources)
        profile = (source_dir, builder["pins"](sources), builder["profile_words"]())
        if runner["launch"](root, artificial=profile) != 2:
            raise ValueError("fabricated zero-phase refusal was not finalized")
        report = runner["verify_result"](root, artificial=profile)
    if (report["reason"] != "no-eligible-pair" or len(report["pairs"]) != 1
            or report["pairs"][0]["roots"] != ["positive", "positive"]
            or report["pairs"][0]["reason"] != "commanded-dry-floor"
            or any(group["negative"]["reason"] != "guard" for group in report["branch_decisions"].values())):
        raise ValueError("unexpected fabricated zero-phase refusal")
    return {name: sha256((root / name).read_bytes()).hexdigest() for name in runner["FILES"]}


def _fixture_incoming(k: int, sign: int) -> tuple[float, float]:
    """Find the conic via eccentricity and polar elements, with a bracketed scalar root."""
    r, orbital_v = _mars_state(k)
    radius = math.hypot(*r)
    original_excess = _excess(impossible=False)
    w = math.hypot(*original_excess)
    n = _unit(r)
    future_dir = _linear(-1., _unit(original_excess), 0., P)
    cos_delta = _dot(n, future_dir)
    sin_delta = sign * math.hypot(*_cross(n, future_dir))
    t = _unit(_linear(1., future_dir, -cos_delta, n))
    kappa = radius * w*w / GM_MARS
    lo, hi = 0., kappa + math.sqrt(2*kappa) + 1.
    for _ in range(55):
        eta = (lo+hi)/2
        if eta*eta < kappa * (1 - cos_delta + eta*sin_delta):
            lo = eta
        else:
            hi = eta
    eta = (lo+hi)/2
    e = math.hypot(1., eta)
    p = (GM_MARS / (w*w)) * eta*eta
    sin_nu_scaled = eta*cos_delta + sin_delta
    cos_nu_scaled = eta*sin_delta - cos_delta
    radial = math.sqrt(GM_MARS/p) * sin_nu_scaled
    transverse = math.sqrt(GM_MARS/p) * (1 + cos_nu_scaled)
    # Reversed velocity disappears in the physical capture impulse v_target - v_in.
    reversed_v = _linear(radial, n, sign*transverse, t)
    return math.hypot(*_linear(1., orbital_v, 1., reversed_v)), (p/(1+e) if radial < 0 else radius)


def independent_winner() -> tuple[int, str, float, float, float]:
    """Return best index/root, total delta-v, next-pair gap and ideal final mass."""
    _, orbital_m_s, hyperbolic_m_s, _ = _moon()
    departure = math.dist(hyperbolic_m_s, orbital_m_s)
    exhaust = 9.80665 * 450
    candidates = []
    for k in range(360):
        for sign in (1, -1):
            arrival, minimum = _fixture_incoming(k, sign)
            total = departure + arrival
            final = 2000 * math.exp(-total/exhaust)
            if minimum - GUARD_MARS > .001 and final >= 500:
                candidates.append((total, k, sign, final))
    candidates.sort()
    total, index, sign, final = candidates[0]
    gap = candidates[1][0] - total
    return index, "positive" if sign == 1 else "negative", total, gap, final
