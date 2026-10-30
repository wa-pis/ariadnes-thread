"""ADR 0120 evidence preparation; native study requires explicit --execute."""

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
OUTPUT = ROOT / "docs/adr/experiments/0122-elliptic-coast.json"
REFERENCE = ROOT / "docs/adr/experiments/0119-m2-reference.json"
REFERENCE_SHA = "3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0"
ADAPTER_SHA = "0e151f806a8467adc11f88aa86b9721330e20c140c89d7583fbdfbf74b3b81b1"
GM_M3_S2 = 1.327124400420322e20
A_M, ECC = 149597870700.0, 0.2
P, Q = (0.36, 0.48, 0.8), (-0.8, 0.6, 0.0)
T0_TDB_S = 978995455.2304223
INITIAL = (43084186761.6, 57445582348.799995, 95742637248.0,
           -29182.918856121985, 21887.189142091487, 0.0)
MEAN_MOTION_RAD_S = math.sqrt(GM_M3_S2 / A_M**3)
PERIOD_S = 2 * math.pi / MEAN_MOTION_RAD_S
MAX_BISECTIONS = 64
State = tuple[float, float, float, float, float, float]
Adapter = Callable[[State, float, float], State]
T = TypeVar("T")


class GateFailure(RuntimeError):
    """Stop without retry or changed parameters."""


class Unavailable(GateFailure):
    """Required source or native environment is unavailable/mismatched."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def finite_state(value: object) -> State:
    require(isinstance(value, (tuple, list)) and len(value) == 6,
            "state must contain six SI components")
    values = cast(tuple[object, ...], value)
    require(all(not isinstance(v, bool) and isinstance(v, (float, int))
                and math.isfinite(v) for v in values), "nonfinite/nonnumeric state")
    return cast(State, tuple(float(v) for v in values))


@dataclass(frozen=True, slots=True)
class OracleResult:
    state: State
    mean_anomaly_rad: float
    eccentric_anomaly_rad: float
    updates: int
    bracket_width_rad: float
    residual_rad: float


def oracle(elapsed_s: float) -> OracleResult:
    """Independent synthetic Sun-relative/J2000 SI ellipse, no native imports."""
    require(not isinstance(elapsed_s, bool) and isinstance(elapsed_s, (int, float))
            and math.isfinite(elapsed_s) and elapsed_s >= 0, "invalid elapsed seconds")
    mean = math.remainder(MEAN_MOTION_RAD_S * elapsed_s, 2 * math.pi)
    low, high = -math.pi, math.pi
    for updates in range(1, MAX_BISECTIONS + 1):
        anomaly = (low + high) / 2
        residual = anomaly - ECC * math.sin(anomaly) - mean
        if residual == 0:
            low = high = anomaly
        elif residual > 0:
            high = anomaly
        else:
            low = anomaly
        if high - low <= 2e-14 and abs(residual) <= 2e-14:
            break
    else:
        raise GateFailure("oracle root/bracket did not converge in 64 updates")
    sine, cosine = math.sin(anomaly), math.cos(anomaly)
    root = math.sqrt(1 - ECC * ECC)
    rate = MEAN_MOTION_RAD_S / (1 - ECC * cosine)
    x, y = A_M * (cosine - ECC), A_M * root * sine
    vx, vy = -A_M * sine * rate, A_M * root * cosine * rate
    state = finite_state(tuple(x * P[i] + y * Q[i] for i in range(3))
                         + tuple(vx * P[i] + vy * Q[i] for i in range(3)))
    return OracleResult(state, mean, anomaly, updates, high - low, abs(residual))


def invariants(state: State) -> tuple[float, tuple[float, float, float]]:
    r, v = state[:3], state[3:]
    radius = math.hypot(*r)
    require(radius > 0, "zero central-body radius")
    energy = sum(x * x for x in v) / 2 - GM_M3_S2 / radius
    h = (r[1] * v[2] - r[2] * v[1], r[2] * v[0] - r[0] * v[2],
         r[0] * v[1] - r[1] * v[0])
    return energy, h


def comparison(native: State, reference: State) -> dict[str, Any]:
    difference = tuple(a - b for a, b in zip(native, reference))
    energy0, h0 = invariants(INITIAL)
    conservation = {}
    for name, state in (("native", native), ("oracle", reference)):
        energy, h = invariants(state)
        conservation[name] = {
            "relative_energy_error": abs(energy - energy0) / abs(energy0),
            "relative_angular_momentum_error": math.dist(h, h0) / math.hypot(*h0),
        }
    return {"native_minus_oracle": difference,
            "position_error_m": math.hypot(*difference[:3]),
            "velocity_error_m_s": math.hypot(*difference[3:]),
            "invariants": conservation}


def check_comparison(values: dict[str, Any]) -> None:
    require(values["position_error_m"] <= 1.0, "position mismatch exceeds 1 m")
    require(values["velocity_error_m_s"] <= 1e-6, "velocity mismatch exceeds 1e-6 m/s")
    for path in values["invariants"].values():
        require(all(math.isfinite(v) and v <= 1e-12 for v in path.values()),
                "energy/angular-momentum invariant mismatch")


def self_check() -> None:
    """Closed-form periapsis/apoapsis/recurrence, zero native work."""
    require(abs(sum(a * b for a, b in zip(P, Q))) <= 1e-15, "basis orthogonality")
    require(all(abs(math.hypot(*basis) - 1) <= 1e-15 for basis in (P, Q)), "basis norm")
    for elapsed, sign, distance, speed in (
        (0.0, 1, A_M * (1 - ECC), math.sqrt(GM_M3_S2 * (1 + ECC) / (A_M * (1 - ECC)))),
        (PERIOD_S / 2, -1, A_M * (1 + ECC), math.sqrt(GM_M3_S2 * (1 - ECC) / (A_M * (1 + ECC)))),
        (PERIOD_S, 1, A_M * (1 - ECC), math.sqrt(GM_M3_S2 * (1 + ECC) / (A_M * (1 - ECC)))),
    ):
        expected = tuple(sign * distance * x for x in P) + tuple(sign * speed * x for x in Q)
        actual = oracle(elapsed).state
        require(math.dist(actual[:3], expected[:3]) <= .01, "oracle position self-check")
        require(math.dist(actual[3:], expected[3:]) <= 1e-8, "oracle velocity self-check")


class Budget:
    def __init__(self, clock: Callable[[], float]) -> None:
        self.clock = clock
        self.start = clock()
        self.calls: list[dict[str, Any]] = []

    def call(
        self, label: str, function: Callable[[], T],
        retain: Callable[[T], None] | None = None,
    ) -> T:
        require(self.clock() - self.start < 30.0, f"deadline before {label}")
        event: dict[str, Any] = {"label": label, "start_s": self.clock() - self.start}
        self.calls.append(event)
        try:
            result = function()
        finally:
            event["end_s"] = self.clock() - self.start
            event["returned"] = sys.exc_info()[0] is None
        if retain is not None:
            retain(result)
        require(self.clock() - self.start <= 30.0, f"deadline after {label}")
        return result


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_check() -> None:
    if digest(REFERENCE) != REFERENCE_SHA or digest(ROOT / "src/space_nav/explorer.py") != ADAPTER_SHA:
        raise Unavailable("frozen reference/adapter hash mismatch")
    reference = json.loads(REFERENCE.read_text())
    require(reference["provenance"]["transfer_model"]["gravitational_parameters"]
            ["values"]["Sun"] == GM_M3_S2, "frozen SPICE GM mismatch")
    expected = reference["identity"]["file_sha256"]["environment.yml"]
    if digest(ROOT / "environment.yml") != expected:
        raise Unavailable("pinned environment file changed")


def provenance() -> dict[str, Any]:
    """Native imports/identity only; never load/query SPICE kernels."""
    space_nav = import_module("space_nav")
    tudatpy = import_module("tudatpy")

    if (platform.python_version() != "3.12.14" or tudatpy.__version__ != "1.0.0"
            or version("numpy") != "1.26.4"):
        raise Unavailable("scientific runtime differs from pinned versions")
    require(Path(space_nav.__file__).resolve() == ROOT / "src/space_nav/__init__.py",
            "import path is not measured checkout")
    binary_files = {}
    for name in ("tudatpy.kernel.astro.element_conversion", "tudatpy.kernel.astro.two_body_dynamics"):
        module = import_module(name)
        # Pybind submodules may share the parent extension instead of __file__.
        filename = getattr(module, "__file__", None)
        if filename is None:
            filename = getattr(import_module("tudatpy.kernel"), "__file__", None)
        if not isinstance(filename, str):
            raise Unavailable(f"native binary location unavailable for {name}")
        binary = Path(filename).resolve()
        binary_files[str(binary)] = digest(binary)
    conda = sorted((Path(sys.prefix) / "conda-meta").glob("tudatpy-*.json"))
    if len(conda) != 1:
        raise Unavailable("TudatPy Conda build metadata unavailable/ambiguous")
    package = json.loads(conda[0].read_text())
    require(package["version"] == "1.0.0", "Conda build version mismatch")
    paths = sorted((ROOT / "src/space_nav").rglob("*.py")) + [
        Path(__file__).resolve(), ROOT / "environment.yml", REFERENCE,
    ]
    return {
        "base_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).splitlines(),
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in paths},
        "native_binary_sha256": binary_files,
        "python": platform.python_version(), "python_executable": sys.executable,
        "tudatpy": str(tudatpy.__version__), "numpy": version("numpy"),
        "space_nav_import": str(space_nav.__file__), "tudatpy_import": str(tudatpy.__file__),
        "conda_build": {k: package.get(k) for k in ("name", "version", "build", "channel")},
        "conda_metadata_sha256": digest(conda[0]), "spice_requests": 0,
    }


def load_adapter() -> Adapter:
    from space_nav.errors import TransferSearchError
    from space_nav.explorer import propagate_two_body

    def invoke(initial: State, elapsed_s: float, gm_m3_s2: float) -> State:
        try:
            return propagate_two_body(initial, elapsed_s, gm_m3_s2)
        except TransferSearchError as exc:
            raise GateFailure(f"native coast adapter failed: {exc}") from exc

    return invoke


def safe_json(value: Any) -> Any:
    """Preserve malformed native outputs explicitly, never emit JSON NaN."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": repr(value)}
    if isinstance(value, (tuple, list)):
        return [safe_json(v) for v in value]
    if isinstance(value, dict):
        return {str(k): safe_json(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return {"unsupported_type": type(value).__name__, "representation": repr(value)}


def run(clock: Callable[[], float] = monotonic) -> dict[str, Any]:
    budget = Budget(clock)
    report: dict[str, Any] = {
        "benchmark": "r1-elliptic-coast-v1", "oracle": "kepler-bisection-cartesian-v1",
        "status": "failed", "reference": {"origin": "Sun", "orientation": "J2000",
            "position_units": "m", "velocity_units": "m/s", "time": "TDB seconds since J2000"},
        "inputs": {"initial_state": INITIAL, "gm_m3_s2": GM_M3_S2, "a_m": A_M,
                   "eccentricity": ECC, "P": P, "Q": Q, "t0_tdb_s": T0_TDB_S, "period_s": PERIOD_S},
        "mass": {"status": "not-modelled", "error_kg": None},
        "budget_s": 30.0, "attempted_adapter_calls": 0, "completed_adapter_calls": 0,
        "calls": budget.calls, "points": [],
    }
    try:
        budget.call("source checks", source_check)
        budget.call("pure oracle self-checks", self_check)
        before = budget.call("initial provenance", provenance,
                             lambda v: report.__setitem__("provenance", v))
        adapter = budget.call("adapter import", load_adapter)
        for index in range(17):
            epoch = T0_TDB_S + index * PERIOD_S / 16
            elapsed = epoch - T0_TDB_S
            point: dict[str, Any] = {"index": index, "epoch_tdb_s": epoch,
                                     "elapsed_s": elapsed, "status": "failed"}
            report["points"].append(point)
            reference = budget.call(f"oracle {index}", lambda: oracle(elapsed),
                                    lambda v: point.__setitem__("oracle", asdict(v)))

            def launch() -> State:
                require(report["attempted_adapter_calls"] < 17, "adapter call limit")
                report["attempted_adapter_calls"] += 1
                state = adapter(INITIAL, elapsed, GM_M3_S2)
                report["completed_adapter_calls"] += 1
                return state

            state = budget.call(f"adapter {index}", launch,
                                lambda v: point.__setitem__("native_state", safe_json(v)))
            values = comparison(finite_state(state), reference.state)
            point["comparison"] = values
            check_comparison(values)
            point["status"] = "passed"
        after = budget.call("final provenance", provenance,
                            lambda v: report.__setitem__("final_provenance", v))
        require(before == after, "source/build/input provenance changed")
        require(clock() - budget.start <= 30.0, "deadline at final gate")
        report["status"] = "passed"
    except (GateFailure, OSError, ImportError, ValueError, TypeError, KeyError,
            subprocess.SubprocessError) as exc:
        report["status"] = "unavailable" if isinstance(exc, (Unavailable, ImportError)) else "failed"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        report["elapsed_seconds"] = clock() - budget.start
        if report["status"] == "passed" and report["elapsed_seconds"] > 30.0:
            report["status"] = "failed"
            report["error"] = {"type": "GateFailure", "message": "deadline at final timing capture"}
    return safe_json(report)


def write_exclusive(path: Path, compute: Callable[[], dict[str, Any]] = run) -> dict[str, Any]:
    with path.open("x", encoding="utf-8") as stream:
        report = compute()
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return report


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_check()
        print("Pure periapsis/apoapsis/period checks passed; zero native calls")
    elif sys.argv[1:] == ["--execute"]:
        result = write_exclusive(OUTPUT)
        print(json.dumps({k: result.get(k) for k in (
            "status", "error", "attempted_adapter_calls", "completed_adapter_calls", "elapsed_seconds",
        )}))
        sys.exit(0 if result["status"] == "passed" else 1)
    else:
        raise SystemExit("Use --self-test; --execute requires separate user authorization")
