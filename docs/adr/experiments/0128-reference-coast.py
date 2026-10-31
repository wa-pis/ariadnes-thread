"""Private ADR0127 verifier. Native execution requires separately authorized --execute."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from importlib import import_module
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
from time import monotonic
from typing import Any, Callable, TypeVar, cast

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = ROOT / "docs/adr/experiments/0119-m2-reference.json"
REFERENCE_SHA = "3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0"
SOURCE_SHA = {
    "src/space_nav/explorer.py": "0e151f806a8467adc11f88aa86b9721330e20c140c89d7583fbdfbf74b3b81b1",
    "src/space_nav/ephemeris.py": "70535eb56881ffbc197903e53b675716128ea4630fb4d377bcf63b1a5d56bfea",
    "environment.yml": "c2948772bfbe09677354f803d9ba79e4c78eb44c5916c98b8d58126832c0e4b7",
}
MU = 1.327124400420322e20
FRAME = {"origin": "SSB", "orientation": "J2000"}
UNITS = {
    "time": "TDB seconds since J2000",
    "position_units": "m",
    "velocity_units": "m/s",
}
State = tuple[float, ...]
Vector = tuple[float, ...]
T = TypeVar("T")


class GateFailure(RuntimeError):
    """Stop this study without retries or changed gates."""


class Unavailable(GateFailure):
    """The required data, domain or pinned resources are unavailable."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def number(value: object) -> float:
    require(
        type(value) in (int, float) and math.isfinite(value), "finite number required"
    )
    return float(value)


def vector(value: object, size: int) -> Vector:
    require(
        isinstance(value, (tuple, list)) and len(value) == size,
        f"expected {size} components",
    )
    return tuple(number(v) for v in cast(list[object], value))


def dot(a: Vector, b: Vector) -> float:
    return math.fsum(x * y for x, y in zip(a, b, strict=True))


def cross(a: Vector, b: Vector) -> Vector:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def invariants(state: State) -> tuple[float, Vector]:
    r, v = state[:3], state[3:]
    require(math.hypot(*r) > 0, "zero radius")
    return dot(v, v) / 2 - MU / math.hypot(*r), cross(r, v)


@dataclass(frozen=True, slots=True)
class Ellipse:
    a_m: float
    eccentricity: float
    p: Vector
    q: Vector
    w: Vector
    initial_eccentric_anomaly_rad: float
    initial_mean_anomaly_rad: float
    mean_motion_rad_s: float


def derive(initial: object) -> Ellipse:
    """Recover a private elliptic Sun/J2000 SI geometry from an original seed."""
    state = vector(initial, 6)
    r, v = state[:3], state[3:]
    radius = math.hypot(*r)
    if radius == 0:
        raise Unavailable("zero radius outside oracle domain")
    energy, h = invariants(state)
    hn = math.hypot(*h)
    if not (energy < 0 and hn > 0):
        raise Unavailable("non-elliptic or degenerate seed")
    a = 1 / (2 / radius - dot(v, v) / MU)
    vh = cross(v, h)
    ev = tuple(vh[i] / MU - r[i] / radius for i in range(3))
    e = math.hypot(*ev)
    if not (1e9 <= a <= 1e13 and 1e-6 <= e <= 0.95):
        raise Unavailable("seed outside admitted a/e domain")
    p, w = tuple(x / e for x in ev), tuple(x / hn for x in h)
    q = cross(w, p)
    require(all(abs(math.hypot(*b) - 1) <= 1e-12 for b in (p, q, w)), "basis norm")
    require(
        all(abs(dot(x, y)) <= 1e-12 for x, y in ((p, q), (q, w), (w, p))),
        "basis orthogonality",
    )
    require(
        max(abs(x - y) for x, y in zip(cross(p, q), w)) <= 1e-12, "basis handedness"
    )
    e0 = math.atan2(dot(r, q) / (a * math.sqrt(1 - e * e)), dot(r, p) / a + e)
    return Ellipse(a, e, p, q, w, e0, e0 - e * math.sin(e0), math.sqrt(MU / a**3))


def oracle(ellipse: Ellipse, elapsed_s: object) -> dict[str, Any]:
    """Independent bisection, SI state and radian root diagnostics."""
    elapsed = number(elapsed_s)
    require(elapsed >= 0, "negative elapsed time")
    mean = math.remainder(
        ellipse.initial_mean_anomaly_rad + ellipse.mean_motion_rad_s * elapsed,
        2 * math.pi,
    )
    low, high = -math.pi, math.pi
    for updates in range(1, 65):
        anomaly = (low + high) / 2
        residual = anomaly - ellipse.eccentricity * math.sin(anomaly) - mean
        if residual == 0:
            low = high = anomaly
        elif residual > 0:
            high = anomaly
        else:
            low = anomaly
        if high - low <= 2e-14 and abs(residual) <= 2e-14:
            break
    else:
        raise GateFailure("root failed in64 bisections")
    a, e, p, q = ellipse.a_m, ellipse.eccentricity, ellipse.p, ellipse.q
    sine, cosine = math.sin(anomaly), math.cos(anomaly)
    beta = math.sqrt(1 - e * e)
    rate = ellipse.mean_motion_rad_s / (1 - e * cosine)
    state = tuple(
        a * (cosine - e) * p[i] + a * beta * sine * q[i] for i in range(3)
    ) + tuple(
        -a * sine * rate * p[i] + a * beta * cosine * rate * q[i] for i in range(3)
    )
    vector(state, 6)
    return {
        "state": state,
        "mean_anomaly_rad": mean,
        "eccentric_anomaly_rad": anomaly,
        "bracket_width_rad": high - low,
        "residual_rad": abs(residual),
        "updates": updates,
    }


def body_state(value: dict[str, Any], body: str, epoch: float) -> State:
    require(
        value["body"] == body and all(value[k] == v for k, v in FRAME.items()),
        "body/frame mismatch",
    )
    require(number(value["epoch_tdb_s"]) == epoch, "epoch mismatch")
    require(
        isinstance(value["epoch_utc"], str) and bool(value["epoch_utc"]),
        "missing UTC label",
    )
    return vector(value["position_m"], 3) + vector(value["velocity_m_s"], 3)


def validate_reference(reference: dict[str, Any]) -> dict[str, Any]:
    require(
        reference["status"] == "passed"
        and reference["identical_scientific_payloads"] is True,
        "reference status",
    )
    run = reference["runs"][0]
    require(
        run["number"] == 1 and run["selected"]["candidate_id"] == "d0001-t0035",
        "selection identity",
    )
    require(
        run["provenance"]["normalized_scenario"] == reference["normalized_scenario"],
        "scenario identity",
    )
    require(run["provenance"] == reference["provenance"], "provenance identity")
    prov = reference["provenance"]
    require(
        number(prov["transfer_model"]["gravitational_parameters"]["values"]["Sun"])
        == MU,
        "GM mismatch",
    )
    require(
        prov["manifest"]["reference"] == FRAME | UNITS, "reference frame/time/units"
    )
    candidate = run["selected"]
    start, end, flight = (
        number(candidate[k])
        for k in ("departure_epoch_tdb_s", "arrival_epoch_tdb_s", "flight_time_s")
    )
    require(
        start < end and flight > 0 and start + flight == end, "candidate time order"
    )
    vector(candidate["departure_v_infinity_m_s"], 3)
    states = run["states"]
    require(len(states) == 121, "requires121 states")
    previous = -math.inf
    for k, state in enumerate(states):
        epoch = number(state["epoch_tdb_s"])
        require(
            epoch == start + flight * k / 120 and epoch > previous, "epoch grid/order"
        )
        body_state(state, "Spacecraft", epoch)
        previous = epoch
    body_state(run["endpoints"]["departure"]["body_state"], "Moon", start)
    body_state(run["endpoints"]["arrival"]["body_state"], "Mars", end)
    return run


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_reference() -> dict[str, Any]:
    if digest(REFERENCE) != REFERENCE_SHA or any(
        digest(ROOT / k) != v for k, v in SOURCE_SHA.items()
    ):
        raise Unavailable("frozen source/reference identity mismatch")
    reference = json.loads(REFERENCE.read_text())
    validate_reference(reference)
    return reference


def compare(
    saved: State, expected: State, initial: State, conservation_required: bool = True
) -> dict[str, Any]:
    difference = tuple(a - b for a, b in zip(saved, expected, strict=True))
    energy0, h0 = invariants(initial)
    conservation = {}
    for name, state in (
        (("saved", saved), ("oracle", expected)) if conservation_required else ()
    ):
        energy, h = invariants(state)
        conservation[name] = {
            "energy": abs(energy - energy0) / abs(energy0),
            "angular_momentum": math.dist(h, h0) / math.hypot(*h0),
        }
    return {
        "difference": difference,
        "position_error_m": math.hypot(*difference[:3]),
        "velocity_error_m_s": math.hypot(*difference[3:]),
        "invariants": conservation,
    }


def check_comparison(values: dict[str, Any], invariants_required: bool = True) -> None:
    require(number(values["position_error_m"]) <= 1, "position mismatch >1m")
    require(number(values["velocity_error_m_s"]) <= 1e-6, "velocity mismatch >1e-6m/s")
    if invariants_required:
        require(
            all(
                number(v) <= 1e-12
                for path in values["invariants"].values()
                for v in path.values()
            ),
            "invariant mismatch",
        )


class Budget:
    def __init__(self, clock: Callable[[], float]) -> None:
        self.clock = clock
        self.start = number(clock())
        self.calls: list[dict[str, Any]] = []

    def check(self, stage: str) -> None:
        elapsed = number(self.clock()) - self.start
        require(0 <= elapsed < 30, f"deadline/clock at {stage}")

    def call(
        self,
        label: str,
        function: Callable[[], T],
        retain: Callable[[T], None] | None = None,
    ) -> T:
        self.check("before " + label)
        event = {
            "label": label,
            "start_s": self.clock() - self.start,
            "returned": False,
        }
        self.calls.append(event)
        try:
            result = function()
            event["returned"] = True
            if retain is not None:
                retain(result)
        finally:
            event["end_s"] = self.clock() - self.start
        self.check("after " + label)
        return result


def check_inventory(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    if (
        actual != expected
        or actual["loaded_kernel_count"] != 13
        or actual["kernel_list_status"] != "complete"
    ):
        raise Unavailable("ordered kernel manifest mismatch")


def conda_metadata(name: str) -> tuple[Path, dict[str, Any]]:
    paths = sorted((Path(sys.prefix) / "conda-meta").glob(name + "-*.json"))
    records = [(p, json.loads(p.read_text())) for p in paths]
    records = [(p, v) for p, v in records if v.get("name") == name]
    if len(records) != 1:
        raise Unavailable(f"ambiguous/missing Conda metadata for {name}")
    return records[0]


def runtime_identity() -> dict[str, Any]:
    """Lazy native identity/inventory; never used by pure preparation/tests."""
    build_path, build = conda_metadata("tudatpy")
    resources_path, resources = conda_metadata("tudat-resources")
    versions = {
        "python": platform.python_version(),
        "tudatpy": build["version"],
        "tudat-resources": resources["version"],
        **{k: version(k) for k in ("numpy", "scipy", "spiceypy")},
    }
    if versions != {
        "python": "3.12.14",
        "numpy": "1.26.4",
        "scipy": "1.17.1",
        "spiceypy": "8.2.0",
        "tudatpy": "1.0.0",
        "tudat-resources": "2.4",
    }:
        raise Unavailable("pinned runtime mismatch")
    package = import_module("space_nav")
    require(
        Path(package.__file__).resolve() == ROOT / "src/space_nav/__init__.py",
        "checkout import mismatch",
    )
    tudat = import_module("tudatpy")
    require(tudat.__version__ == versions["tudatpy"], "native module version mismatch")
    binary = Path(import_module("tudatpy.kernel").__file__).resolve()
    paths = sorted((ROOT / "src/space_nav").glob("*.py")) + [
        Path(__file__).resolve(),
        Path(__file__).with_name("0128-audit-reference-coast.py"),
        ROOT / "tests/test_r2_reference_coast.py",
        ROOT / "environment.yml",
        REFERENCE,
    ]
    return {
        "versions": versions,
        "imports": {"space_nav": package.__file__, "tudatpy": tudat.__file__},
        "native_binary": {"path": str(binary), "sha256": digest(binary)},
        "conda_build": build,
        "resource_build": resources,
        "resource_metadata_sha256": digest(resources_path),
        "conda_metadata_sha256": digest(build_path),
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "dirty": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True
        ).splitlines(),
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in paths},
        "kernels": import_module("space_nav.ephemeris").kernel_metadata(),
    }


def sun_provider(epoch: float) -> dict[str, Any]:
    """Authoritative geometric SSB/J2000 state, existing exact-TDB provider."""
    module = import_module("space_nav.ephemeris")
    try:
        return asdict(module._query_body_state_tdb("Sun", epoch))
    except Exception as exc:
        raise Unavailable(f"Sun provider failed at TDB {epoch}: {exc}") from exc


def safe_json(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": repr(value)}
    if isinstance(value, (tuple, list)):
        return [safe_json(v) for v in value]
    if isinstance(value, dict):
        return {str(k): safe_json(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return {"unsupported_type": type(value).__name__}


def run(
    stream: Any,
    *,
    clock: Callable[[], float] = monotonic,
    reference_loader: Callable[[], dict[str, Any]] = load_reference,
    identity: Callable[[], dict[str, Any]] = runtime_identity,
    provider: Callable[[float], dict[str, Any]] = sun_provider,
) -> dict[str, Any]:
    """Reserved output stream, cooperative30s cap; injected providers support pure tests."""
    budget = Budget(clock)
    report: dict[str, Any] = {
        "comparison": "r2-reference-coast-v1",
        "oracle": "cartesian-ellipse-bisection-v1",
        "reference_sha256": REFERENCE_SHA,
        "contract": "ADR0127",
        "units": UNITS,
        "frame": FRAME,
        "status": "failed",
        "attempted_sun_calls": 0,
        "completed_sun_calls": 0,
        "native_spacecraft_propagations": 0,
        "budget_s": 30.0,
        "calls": budget.calls,
        "points": [],
    }
    stage = "setup"
    try:
        reference = budget.call("reference", reference_loader)
        original = budget.call(
            "reference validation", lambda: validate_reference(reference)
        )
        report["original"] = original
        report["original_manifest"] = reference["provenance"]["manifest"]
        budget.call("pure checks", self_check)
        before = budget.call(
            "initial identity", identity, lambda v: report.__setitem__("identity", v)
        )
        check_inventory(before["kernels"], reference["provenance"]["manifest"]["spice"])
        initial: State = ()
        ellipse: Ellipse | None = None
        start = original["states"][0]["epoch_tdb_s"]
        for k, saved_record in enumerate(original["states"]):
            stage = f"node {k}"
            epoch = saved_record["epoch_tdb_s"]
            point: dict[str, Any] = {
                "index": k,
                "epoch_tdb_s": epoch,
                "elapsed_s": epoch - start,
                "status": "failed",
                "sun_request": FRAME
                | {
                    "body": "Sun",
                    "aberration_correction": "NONE",
                    "epoch_tdb_s": epoch,
                },
            }
            report["points"].append(point)

            def read() -> dict[str, Any]:
                require(report["attempted_sun_calls"] < 121, "Sun call cap")
                report["attempted_sun_calls"] += 1
                state = provider(epoch)
                report["completed_sun_calls"] += 1
                return state

            raw = budget.call(
                f"Sun {k}", read, lambda v: point.__setitem__("sun", safe_json(v))
            )
            sun = body_state(raw, "Sun", epoch)
            if k == 0:
                moon = body_state(
                    original["endpoints"]["departure"]["body_state"], "Moon", start
                )
                excess = vector(original["selected"]["departure_v_infinity_m_s"], 3)
                initial = tuple(moon[i] - sun[i] for i in range(3)) + tuple(
                    (moon[i + 3] - sun[i + 3]) + excess[i] for i in range(3)
                )
                report["seed_operands"] = {
                    "moon": moon,
                    "sun0": sun,
                    "excess_m_s": excess,
                }
                report["initial_state"] = initial
                ellipse = derive(initial)
                report["ellipse"] = asdict(ellipse)
            require(ellipse is not None, "missing ellipse")
            solved = budget.call(
                f"oracle {k}",
                lambda: oracle(cast(Ellipse, ellipse), epoch - start),
                lambda v: point.__setitem__("oracle", v),
            )
            saved = body_state(saved_record, "Spacecraft", epoch)
            relative = tuple(x - y for x, y in zip(saved, sun, strict=True))
            expected = vector(solved["state"], 6)
            expected_ssb = tuple(x + y for x, y in zip(expected, sun, strict=True))
            point.update(
                saved_relative=relative,
                oracle_ssb=expected_ssb,
                relative=compare(relative, expected, initial),
                ssb=compare(saved, expected_ssb, initial, False),
            )
            check_comparison(point["relative"])
            check_comparison(point["ssb"], False)
            budget.check(stage)
            point["status"] = "passed"
        stage = "final identity"
        after = budget.call(
            stage, identity, lambda v: report.__setitem__("final_identity", v)
        )
        check_inventory(after["kernels"], before["kernels"])
        require(before == after, "source/runtime identity drift")
        report["status"] = "passed"
    except (
        GateFailure,
        OSError,
        ImportError,
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        subprocess.SubprocessError,
    ) as exc:
        report["status"] = (
            "unavailable"
            if isinstance(exc, (Unavailable, ImportError, OSError))
            else "failed"
        )
        report["error"] = {
            "stage": stage,
            "type": type(exc).__name__,
            "message": str(exc),
        }
    # Serialize within the budget; rewrite failure if finalization itself overruns.
    report["elapsed_seconds"] = clock() - budget.start
    json.dump(safe_json(report), stream, indent=2, allow_nan=False)
    stream.flush()
    try:
        budget.check("evidence finalization")
    except GateFailure as exc:
        report["status"] = "failed"
        report["error"] = {
            "stage": "evidence finalization",
            "type": "GateFailure",
            "message": str(exc),
        }
        report["elapsed_seconds"] = clock() - budget.start
        stream.seek(0)
        stream.truncate()
        json.dump(safe_json(report), stream, indent=2, allow_nan=False)
        stream.flush()
    return safe_json(report)


def execute(path: Path) -> dict[str, Any]:
    with path.open("x", encoding="utf-8") as stream:
        require(
            not any(
                k.startswith(("space_nav", "tudatpy", "spiceypy")) for k in sys.modules
            ),
            "native execution requires a fresh process before scientific imports",
        )
        return run(stream)


def self_check() -> None:
    """Eight literal-quadrant initial fixtures, plus half/full-period checks."""
    a, e = 149597870700.0, 0.2
    p = (0.36, 0.48, 0.8)
    beta, n = math.sqrt(1 - e * e), math.sqrt(MU / a**3)
    for direction in (-1, 1):
        q = tuple(direction * x for x in (-0.8, 0.6, 0.0))
        for phase, sine, cosine in (
            (0.0, 0.0, 1.0),
            (math.pi / 2, 1.0, 0.0),
            (math.pi, 0.0, -1.0),
            (-math.pi / 2, -1.0, 0.0),
        ):
            seed = tuple(
                a * (cosine - e) * p[i] + a * beta * sine * q[i] for i in range(3)
            ) + tuple(
                -a * sine * n / (1 - e * cosine) * p[i]
                + a * beta * cosine * n / (1 - e * cosine) * q[i]
                for i in range(3)
            )
            ell = derive(seed)
            require(
                abs(ell.a_m - a) / a <= 1e-12 and abs(ell.eccentricity - e) <= 1e-12,
                "initial geometry fixture",
            )
            require(
                abs(
                    math.remainder(
                        ell.initial_eccentric_anomaly_rad - phase, 2 * math.pi
                    )
                )
                <= 2e-14,
                "initial phase fixture",
            )
            for dt in (0.0, 2 * math.pi / n):
                actual = oracle(ell, dt)["state"]
                require(
                    math.dist(actual[:3], seed[:3]) <= 0.01
                    and math.dist(actual[3:], seed[3:]) <= 1e-8,
                    "initial/period fixture",
                )
            if sine == 0:
                expected = tuple(a * (-cosine - e) * p[i] for i in range(3)) + tuple(
                    -a * beta * cosine * n / (1 + e * cosine) * q[i] for i in range(3)
                )
                actual = oracle(ell, math.pi / n)["state"]
                require(
                    math.dist(actual[:3], expected[:3]) <= 0.01
                    and math.dist(actual[3:], expected[3:]) <= 1e-8,
                    "half-period fixture",
                )


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_check()
        print("Pure reference-coast checks passed; zero native imports/queries")
    elif len(sys.argv) == 3 and sys.argv[1] == "--execute":
        result = execute(Path(sys.argv[2]))
        print(
            json.dumps(
                {
                    k: result.get(k)
                    for k in (
                        "status",
                        "error",
                        "attempted_sun_calls",
                        "completed_sun_calls",
                    )
                }
            )
        )
        sys.exit(0 if result["status"] == "passed" else 1)
    else:
        raise SystemExit(
            "Use --self-test; --execute NEW_OUTPUT requires separate authorization"
        )
