"""ADR0131 private screening preparation; native study is a separate stage."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import importlib.util
import json
import math
import subprocess
from pathlib import Path
import sys
from time import monotonic
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"module unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


COMMON_PATH = HERE / "0128-reference-coast.py"
if (
    sha256(COMMON_PATH.read_bytes()).hexdigest()
    != "027d0b4e45f9ebd941249e427963e365fd7205f9594a96365a587eb0e8cd7e81"
):
    raise ImportError("immutable R2 utilities changed")
common = load_module("r3_immutable_r2_utilities", COMMON_PATH)
independent = load_module(
    "r3_independent_gravity_audit", HERE / "0132-gravity-audit.py"
)
BODIES = ("Earth", "Moon", "Mars")
GUARDS = {"Sun": 696000000.0, "Earth": 6378136.6, "Moon": 1737400.0, "Mars": 3396190.0}
ORDER = (
    ("Earth", 0),
    ("Mars", 0),
    ("Earth", 60),
    ("Moon", 60),
    ("Mars", 60),
    ("Earth", 120),
    ("Moon", 120),
)


def force(
    x_value: object, b_value: object, mu_value: object, guard_value: object
) -> dict[str, Any]:
    """Sun-relative differential point-mass acceleration in SI/J2000."""
    x, b = common.vector(x_value, 3), common.vector(b_value, 3)
    mu, guard = common.number(mu_value), common.number(guard_value)
    common.require(mu > 0 and guard >= 0, "positive GM/nonnegative guard required")
    d = tuple(v - u for u, v in zip(x, b, strict=True))
    dn, bn = math.hypot(*d), math.hypot(*b)
    common.require(math.isfinite(dn) and math.isfinite(bn), "finite distances required")
    result = {
        "x_m": x,
        "b_m": b,
        "gm_m3_s2": mu,
        "guard_m": guard,
        "distance_m": dn,
        "body_sun_distance_m": bn,
        "status": "inadmissible",
    }
    if dn <= guard or bn <= guard:
        result["reason"] = "spacecraft/body or Sun/body inside/on exclusion sphere"
        return result
    direct = tuple(mu * v / dn**3 for v in d)
    indirect = tuple(mu * v / bn**3 for v in b)
    differential = tuple(a - b for a, b in zip(direct, indirect, strict=True))
    common.vector(differential, 3)
    result.update(
        status="admissible",
        direct_m_s2=direct,
        indirect_m_s2=indirect,
        differential_m_s2=differential,
        norm_m_s2=math.hypot(*differential),
        decimal=independent.decimal_force(x, b, mu),
    )
    return result


def load_inputs() -> dict[str, Any]:
    reference = common.load_reference()
    path = HERE / "0129-reference-coast.json"
    common.require(
        common.digest(path) == independent.SHA[path.name], "R2 evidence identity"
    )
    r2 = json.loads(path.read_text())
    common.require(
        r2["status"] == "passed" and r2["reference_sha256"] == common.REFERENCE_SHA,
        "R2 evidence status",
    )
    original = reference["runs"][0]
    rows = []
    for k in (0, 60, 120):
        spacecraft = original["states"][k]
        epoch = spacecraft["epoch_tdb_s"]
        sun = r2["points"][k]["sun"]
        common.body_state(sun, "Sun", epoch)
        common.body_state(spacecraft, "Spacecraft", epoch)
        common.require(r2["points"][k]["epoch_tdb_s"] == epoch, "saved Sun epoch drift")
        bodies = {}
        if k == 0:
            bodies["Moon"] = original["endpoints"]["departure"]["body_state"]
        if k == 120:
            bodies["Mars"] = original["endpoints"]["arrival"]["body_state"]
        rows.append(
            {
                "index": k,
                "epoch_tdb_s": epoch,
                "spacecraft": spacecraft,
                "sun": sun,
                "retained_bodies": bodies,
            }
        )
    return {
        "rows": rows,
        "gm_m3_s2": reference["provenance"]["transfer_model"][
            "gravitational_parameters"
        ]["values"],
        "kernels": reference["provenance"]["manifest"]["spice"],
    }


def validate_inputs(inputs: dict[str, Any]) -> None:
    common.require(
        inputs["gm_m3_s2"]
        == {
            "Sun": 1.327124400420322e20,
            "Moon": 4902800205346.301,
            "Mars": 42828375010399.99,
        },
        "original GM identity",
    )
    common.require(
        [r["index"] for r in inputs["rows"]] == [0, 60, 120], "three fixed nodes"
    )
    original = common.load_reference()["runs"][0]
    for row in inputs["rows"]:
        epoch = row["epoch_tdb_s"]
        common.require(
            common.number(epoch) == original["states"][row["index"]]["epoch_tdb_s"],
            "original epoch identity",
        )
        common.body_state(row["spacecraft"], "Spacecraft", epoch)
        common.body_state(row["sun"], "Sun", epoch)
        common.require(
            row["spacecraft"] == original["states"][row["index"]],
            "stored spacecraft identity",
        )
        for body, record in row["retained_bodies"].items():
            common.body_state(record, body, epoch)


def runtime_identity() -> dict[str, Any]:
    from space_nav.errors import EphemerisError

    try:
        identity = common.runtime_identity()
    except (EphemerisError, AttributeError, subprocess.SubprocessError) as exc:
        raise common.Unavailable(f"native identity unavailable: {exc}") from exc
    for p in (
        Path(__file__),
        HERE / "0132-gravity-audit.py",
        ROOT / "tests/test_r3_gravity_screen.py",
        HERE / "0129-reference-coast.json",
    ):
        identity["source_sha256"][str(p.relative_to(ROOT))] = common.digest(p)
    return identity


def body_provider(body: str, epoch: float) -> dict[str, Any]:
    from space_nav.ephemeris import _query_body_state_tdb

    try:
        return asdict(_query_body_state_tdb(body, epoch))
    except Exception as exc:
        raise common.Unavailable(f"{body} at {epoch}: {exc}") from exc


def earth_gm_provider() -> float:
    from space_nav.ephemeris import _get_body_gravitational_parameter

    try:
        return _get_body_gravitational_parameter("Earth")
    except Exception as exc:
        raise common.Unavailable(f"Earth GM: {exc}") from exc


def validate_row(point: dict[str, Any]) -> None:
    if point["index"] == 60:
        if not all(t["status"] == "admissible" for t in point["terms"].values()):
            raise common.Unavailable("middle-node exterior domain unavailable")
        vectors = [point["terms"][b]["differential_m_s2"] for b in BODIES]
        total = tuple(math.fsum(v[i] for v in vectors) for i in range(3))
        norm = math.hypot(*total)
        norms = math.fsum(point["terms"][b]["norm_m_s2"] for b in BODIES)
        point["summary"] = {
            "vector_sum_m_s2": total,
            "norm_of_sum_m_s2": norm,
            "sum_of_norms_m_s2": norms,
            "sum_solar_ratio": norm / point["solar_norm_m_s2"],
            "norms_solar_ratio": norms / point["solar_norm_m_s2"],
        }
    else:
        name = "Moon" if point["index"] == 0 else "Mars"
        common.require(
            point["terms"][name]["status"] == "inadmissible",
            "expected endpoint domain changed",
        )
        point["summary"] = None
    point["status"] = "passed"


def self_check() -> None:
    for x, b, expected in (
        ((1.0, 0.0, 0.0), (3.0, 0.0, 0.0), (10 / 9, 0.0, 0.0)),
        ((0.0, 1.0, 0.0), (0.0, 3.0, 0.0), (0.0, 10 / 9, 0.0)),
        ((-1.0, 0.0, 0.0), (-3.0, 0.0, 0.0), (-10 / 9, 0.0, 0.0)),
    ):
        result = force(x, b, 8.0, 0.0)
        independent.check_term(result)
        common.require(
            math.dist(result["differential_m_s2"], expected) < 1e-14,
            "closed-form force fixture",
        )
    common.require(
        force((1.0, 0.0, 0.0), (3.0, 0.0, 0.0), 8.0, 2.0)["status"] == "inadmissible",
        "exact guard fixture",
    )


def run(
    stream: Any,
    *,
    clock: Callable[[], float] = monotonic,
    loader: Callable[[], dict[str, Any]] = load_inputs,
    identity: Callable[[], dict[str, Any]] = runtime_identity,
    provider: Callable[[str, float], dict[str, Any]] = body_provider,
    gm_provider: Callable[[], float] = earth_gm_provider,
) -> dict[str, Any]:
    budget = common.Budget(clock)
    counts = {
        "states_attempted": 0,
        "states_completed": 0,
        "earth_gm_attempted": 0,
        "earth_gm_completed": 0,
    }
    report = {
        "contract": "ADR0131",
        "screening": "r3-three-epoch-gravity-v1",
        "reference_sha256": independent.SHA,
        "origin": "Sun",
        "orientation": "J2000",
        "aberration_correction": "NONE",
        "guards_m": GUARDS,
        "units": {
            "position": "m",
            "acceleration": "m/s^2",
            "gm": "m^3/s^2",
            "epoch": "TDB seconds since J2000",
        },
        "budget_s": 30.0,
        "counts": counts,
        "native_spacecraft_propagations": 0,
        "status": "failed",
        "rows": [],
        "calls": budget.calls,
    }
    stage = "setup"
    try:
        inputs = budget.call(
            "frozen inputs", loader, lambda v: report.__setitem__("inputs", v)
        )
        budget.call("validate frozen inputs", lambda: validate_inputs(inputs))
        budget.call("pure self checks", self_check)
        before = budget.call(
            "initial identity", identity, lambda v: report.__setitem__("identity", v)
        )
        common.check_inventory(before["kernels"], inputs["kernels"])
        report["gm_m3_s2"] = dict(inputs["gm_m3_s2"])

        def gm_read() -> float:
            common.require(counts["earth_gm_attempted"] < 1, "Earth GM call cap")
            counts["earth_gm_attempted"] += 1
            value = gm_provider()
            counts["earth_gm_completed"] += 1
            return value

        raw_gm = budget.call(
            "Earth GM",
            gm_read,
            lambda v: report.__setitem__("raw_earth_gm", common.safe_json(v)),
        )
        gm = common.number(raw_gm)
        common.require(gm > 0, "Earth GM must be positive")
        report["gm_m3_s2"]["Earth"] = gm
        for row in inputs["rows"]:
            k, epoch = row["index"], row["epoch_tdb_s"]
            stage = f"node{k}"
            x = tuple(
                a - b
                for a, b in zip(
                    row["spacecraft"]["position_m"],
                    row["sun"]["position_m"],
                    strict=True,
                )
            )
            common.require(
                math.hypot(*x) > GUARDS["Sun"], "spacecraft inside Sun guard"
            )
            solar = tuple(
                -inputs["gm_m3_s2"]["Sun"] * v / math.hypot(*x) ** 3 for v in x
            )
            point = {
                "index": k,
                "epoch_tdb_s": epoch,
                "x_m": x,
                "solar_m_s2": solar,
                "solar_norm_m_s2": math.hypot(*solar),
                "bodies": dict(row["retained_bodies"]),
                "terms": {},
                "status": "failed",
            }
            report["rows"].append(point)
            for body in BODIES:
                if (body, k) not in ORDER:
                    continue

                def read() -> dict[str, Any]:
                    position = counts["states_attempted"]
                    common.require(
                        position < 7 and ORDER[position] == (body, k),
                        "state call cap/order",
                    )
                    counts["states_attempted"] += 1
                    value = provider(body, epoch)
                    counts["states_completed"] += 1
                    return value

                raw = budget.call(
                    f"state {body}{k}",
                    read,
                    lambda v: point["bodies"].__setitem__(body, common.safe_json(v)),
                )
                common.body_state(raw, body, epoch)
            for body in BODIES:
                raw = point["bodies"][body]
                common.body_state(raw, body, epoch)
                b = tuple(
                    a - b
                    for a, b in zip(
                        raw["position_m"], row["sun"]["position_m"], strict=True
                    )
                )
                term = budget.call(
                    f"force {body}{k}",
                    lambda: force(x, b, report["gm_m3_s2"][body], GUARDS[body]),
                    lambda v: point["terms"].__setitem__(body, v),
                )
                budget.call(
                    f"force check {body}{k}", lambda: independent.check_term(term)
                )
                if term["status"] == "admissible":
                    term["solar_ratio"] = term["norm_m_s2"] / point["solar_norm_m_s2"]
            budget.call(f"row gates{k}", lambda: validate_row(point))
        stage = "final identity"
        after = budget.call(
            stage, identity, lambda v: report.__setitem__("final_identity", v)
        )
        common.check_inventory(after["kernels"], before["kernels"])
        common.require(after == before, "source/runtime identity drift")
        report["status"] = "passed"
        report["finalization_gate"] = "passed"
    except (
        common.GateFailure,
        OSError,
        ImportError,
        ValueError,
        TypeError,
        KeyError,
        ArithmeticError,
        subprocess.SubprocessError,
    ) as exc:
        report["status"] = (
            "unavailable"
            if isinstance(exc, (common.Unavailable, ImportError, OSError))
            else "failed"
        )
        report["error"] = {
            "stage": stage,
            "type": type(exc).__name__,
            "message": str(exc),
        }
    report["elapsed_sample_before_flush_s"] = clock() - budget.start
    json.dump(common.safe_json(report), stream, indent=2, allow_nan=False)
    stream.flush()
    try:
        budget.check("evidence flush")
    except common.GateFailure as exc:
        report["status"] = "failed"
        report["finalization_gate"] = "failed"
        report["error"] = {
            "stage": "evidence flush",
            "type": "GateFailure",
            "message": str(exc),
        }
        report["elapsed_sample_before_flush_s"] = clock() - budget.start
        stream.seek(0)
        stream.truncate()
        json.dump(common.safe_json(report), stream, indent=2, allow_nan=False)
        stream.flush()
    return common.safe_json(report)


def execute(path: Path) -> dict[str, Any]:
    with path.open("x", encoding="utf-8") as stream:
        common.require(
            not any(
                k.startswith(("space_nav", "tudatpy", "spiceypy")) for k in sys.modules
            ),
            "fresh process required",
        )
        return run(stream)


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_check()
        print("Synthetic gravity checks passed; zero native imports/queries")
    elif len(sys.argv) == 3 and sys.argv[1] == "--execute":
        result = execute(Path(sys.argv[2]))
        print(json.dumps({k: result.get(k) for k in ("status", "error", "counts")}))
        sys.exit(0 if result["status"] == "passed" else 1)
    else:
        raise SystemExit(
            "Use --self-test; native --execute NEW_OUTPUT requires verified preparation"
        )
