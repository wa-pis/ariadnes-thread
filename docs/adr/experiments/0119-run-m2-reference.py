"""One authorized ADR 0118 study; --self-test is native-free, never a retry."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal, localcontext
from hashlib import sha256
from importlib.metadata import version
import json
import math
from pathlib import Path
import subprocess
import sys
from time import monotonic
import tomllib
from typing import Any, Callable, TypeVar

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "examples/r1_m2_reserve_reference.toml"
OUTPUT = ROOT / "docs/adr/experiments/0119-m2-reference.json"
TEMPLATE = ROOT / "examples/m3_feasible_mission.toml"
TEMPLATE_SHA256 = "2c3b2a140d6e6ea00c2173caab5c51b1c4be87a112d2dec28a40cd1e2a0a9b42"
T = TypeVar("T")


class GateFailure(RuntimeError):
    """A failed acceptance check stops this study without another launch."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


class Budget:
    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self.clock = clock
        self.start = clock()
        self.deadline = self.start + 300.0
        self.calls: list[dict[str, Any]] = []

    def call(
        self, label: str, function: Callable[[], T],
        retain: Callable[[T], None] | None = None,
    ) -> T:
        require(self.clock() < self.deadline, f"budget exhausted before {label}")
        event: dict[str, Any] = {"label": label, "start_s": self.clock() - self.start}
        self.calls.append(event)
        try:
            value = function()
        finally:
            event["end_s"] = self.clock() - self.start
            event["returned"] = sys.exc_info()[0] is None
        if retain is not None:
            retain(value)  # Keep returned science even when its native call overran.
        require(self.clock() <= self.deadline, f"budget exceeded after {label}")
        return value


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def identity() -> dict[str, Any]:
    paths = sorted((ROOT / "src/space_nav").rglob("*.py")) + [
        Path(__file__).resolve(), FIXTURE, TEMPLATE, ROOT / "moon_to_mars.py",
        ROOT / "environment.yml", ROOT / "tests/data/reference_kernel_baseline.json",
    ]
    return {
        "base_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        ).strip(),
        "dirty_status": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True,
        ).splitlines(),
        "file_sha256": {str(path.relative_to(ROOT)): digest(path) for path in paths},
    }


def select(front: tuple[Any, ...]) -> Any:
    eligible = [candidate for candidate in front if candidate.final_mass_kg >= 550.0]
    require(bool(eligible), "no Pareto candidate preserves the 50 kg reserve")
    return min(eligible, key=lambda c: (
        c.total_delta_v_m_s, c.flight_time_s, c.departure_epoch_tdb_s, c.candidate_id,
    ))


def mass_check(candidate: Any) -> dict[str, Any]:
    with localcontext() as context:
        context.prec = 50
        scale = Decimal("9.80665") * Decimal("450")
        mass = Decimal("2000")
        for delta_v in (candidate.departure_delta_v_m_s, candidate.arrival_delta_v_m_s):
            mass *= (-Decimal.from_float(delta_v) / scale).exp()
        difference = abs(mass - Decimal.from_float(candidate.final_mass_kg))
        require(candidate.final_mass_kg >= 550.0, "reserve deficit")
        require(difference <= Decimal("1e-9"), "independent mass mismatch")
        return {"precision_digits": 50, "final_mass_decimal_kg": str(mass),
                "absolute_difference_kg": str(difference),
                "mass_above_dry_kg": candidate.final_mass_kg - 500.0,
                "mass_above_dry_plus_reserve_kg": candidate.final_mass_kg - 550.0}


def endpoint_check(state: Any, body: Any, excess: tuple[float, ...]) -> dict[str, Any]:
    position_error = math.dist(state.position_m, body.position_m)
    velocity_error = math.dist(state.velocity_m_s, tuple(
        body.velocity_m_s[i] + excess[i] for i in range(3)
    ))
    require(math.isfinite(position_error) and position_error <= 100.0,
            "endpoint position exceeds 100 m")
    require(math.isfinite(velocity_error) and velocity_error <= 0.001,
            "endpoint velocity exceeds 0.001 m/s")
    require(state.epoch_tdb_s == body.epoch_tdb_s, "endpoint epoch mismatch")
    return {"body_state": asdict(body), "position_error_m": position_error,
            "velocity_error_m_s": velocity_error}


def study() -> dict[str, Any]:
    budget = Budget()  # Includes imports, validation, resource setup and both runs.
    record: dict[str, Any] = {
        "reference_id": "r1-m2-reserve-reference", "status": "failed",
        "contract": "ADR 0118", "budget_seconds": 300.0, "reserve_kg": 50.0,
        "calls": budget.calls, "runs": [],
    }
    expected_errors: tuple[type[Exception], ...] = (
        RuntimeError, ValueError, OSError, ImportError, KeyError, TypeError,
    )
    try:
        import space_nav
        from space_nav import ephemeris
        from space_nav.cli import _manifest
        from space_nav.errors import EphemerisError, TransferSearchError
        from space_nav.explorer import sample_transfer
        from space_nav.scenario import load_scenario
        from space_nav.transfer import _search_impulsive_transfers, _transfer_model_manifest

        expected_errors += (EphemerisError, TransferSearchError)
        require(Path(space_nav.__file__).resolve() == ROOT / "src/space_nav/__init__.py",
                "imported package is not the measured checkout")
        record["import_path"] = space_nav.__file__
        record["identity"] = budget.call("initial source identity", identity)
        require(digest(TEMPLATE) == TEMPLATE_SHA256, "template bytes changed")
        require(tomllib.loads(FIXTURE.read_text()) == tomllib.loads(TEMPLATE.read_text()),
                "explicit scenario values differ from the accepted template")
        scenario = budget.call("load scenario", lambda: load_scenario(FIXTURE))
        record["normalized_scenario"] = scenario.to_dict()
        require(scenario.to_dict() == load_scenario(TEMPLATE).to_dict(),
                "normalized input mismatch")
        with localcontext() as context:
            context.prec = 50
            bound = Decimal(2000) * (1 - (-Decimal(100) / (
                Decimal("9.80665") * Decimal(450)
            )).exp())
            require(bound < Decimal(50), "contingency bound exceeds reserve")
            record["contingency_propellant_bound_decimal_kg"] = str(bound)

        def provenance() -> dict[str, Any]:
            return {"manifest": _manifest(FIXTURE, scenario.limits.random_seed),
                    "transfer_model": _transfer_model_manifest(scenario),
                    "versions": {name: version(name) for name in (
                        "numpy", "scipy", "spiceypy",
                    )}, "identity": identity(),
                    "normalized_scenario": load_scenario(FIXTURE).to_dict()}

        initial = budget.call("initial resource provenance", provenance,
                              lambda value: record.__setitem__("provenance", value))
        baseline = json.loads((ROOT / "tests/data/reference_kernel_baseline.json").read_text())
        actual = initial["manifest"]["spice"]
        require(actual["kernel_list_status"] == "complete", "incomplete kernel inventory")
        require(actual["loaded_kernel_count"] == baseline["loaded_kernel_count"],
                "kernel count mismatch")
        require([{key: kernel[key] for key in ("name", "sha256")}
                 for kernel in actual["kernels"]] == baseline["kernels"],
                "ordered kernel hashes differ from baseline")
        require(initial["manifest"]["versions"]["python"] == "3.12.14"
                and initial["manifest"]["versions"]["tudatpy"] == "1.0.0"
                and initial["transfer_model"]["tudat_resources_version"] == "2.4"
                and initial["versions"] == {
                    "numpy": "1.26.4", "scipy": "1.17.1", "spiceypy": "8.2.0",
                }, "scientific versions differ from pins")
        require(initial["transfer_model"]["identifier"]
                == "sun-centered-zero-revolution-patched-conic-v1", "model changed")
        for number in (1, 2):
            run: dict[str, Any] = {"number": number}
            record["runs"].append(run)
            result = budget.call(
                f"search {number}", lambda: _search_impulsive_transfers(
                    scenario, deadline_monotonic_s=budget.deadline,
                ), lambda value: run.__setitem__("search", asdict(value)),
            )
            require(result.evaluated_candidates == 1980
                    and result.solved_candidates + result.failed_candidates == 1980,
                    "search grid accounting mismatch")
            if number == 2:
                require(run["search"] == record["runs"][0]["search"],
                        "search payload changed; no second sampler permitted")
            chosen = select(result.pareto_front)
            run["selected"] = asdict(chosen)
            run["mass_check"] = mass_check(chosen)
            if number == 2:
                require(run["selected"] == record["runs"][0]["selected"],
                        "selected candidate changed")
            states = budget.call(
                f"sample {number}", lambda: sample_transfer(chosen, count=121),
                lambda value: run.__setitem__("states", [asdict(state) for state in value]),
            )
            require(len(states) == 121, "sample count mismatch")
            for index, state in enumerate(states):
                require(state.origin == "SSB" and state.orientation == "J2000"
                        and state.epoch_tdb_s == chosen.departure_epoch_tdb_s
                        + chosen.flight_time_s * index / 120
                        and all(math.isfinite(v) for v in (*state.position_m, *state.velocity_m_s)),
                        "nonfinite or noncanonical sample")
            moon = budget.call(f"Moon endpoint {number}", lambda: ephemeris._query_body_state_tdb(
                "Moon", chosen.departure_epoch_tdb_s,
            ))
            mars = budget.call(f"Mars endpoint {number}", lambda: ephemeris._query_body_state_tdb(
                "Mars", chosen.arrival_epoch_tdb_s,
            ))
            run["endpoints"] = {
                "departure": endpoint_check(states[0], moon, chosen.departure_v_infinity_m_s),
                "arrival": endpoint_check(states[-1], mars, chosen.arrival_v_infinity_m_s),
            }
            run["provenance"] = budget.call(f"post-run provenance {number}", provenance)
            require(run["provenance"] == initial, "input/source/resources changed")
        first, second = record["runs"]
        require({k: v for k, v in first.items() if k != "number"}
                == {k: v for k, v in second.items() if k != "number"},
                "full scientific payload differs")
        record["identical_scientific_payloads"] = True
        require(budget.clock() <= budget.deadline, "budget exceeded at final gate")
        record["status"] = "passed"
    except expected_errors as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        record["elapsed_seconds"] = budget.clock() - budget.start
    return record


def self_test() -> None:
    """Native-free guards; no SPICE, planner, sampler, imports or file writes."""
    from types import SimpleNamespace

    candidate = SimpleNamespace(
        final_mass_kg=2000.0, departure_delta_v_m_s=0.0, arrival_delta_v_m_s=0.0,
        total_delta_v_m_s=0.0, flight_time_s=1.0, departure_epoch_tdb_s=0.0,
        candidate_id="a",
    )
    require(mass_check(candidate)["absolute_difference_kg"] == "0", "zero-dv mass")
    require(select((candidate,)) is candidate, "positive selection")
    checks = 2
    for value in (549.999999999, 500.0):
        candidate.final_mass_kg = value
        try:
            select((candidate,))
        except GateFailure:
            checks += 1
        else:
            raise AssertionError("reserve deficit admitted")
    candidate.final_mass_kg = 550.0
    require(select((candidate,)) is candidate, "exact reserve boundary")
    checks += 1
    other = SimpleNamespace(**vars(candidate))
    other.candidate_id = "b"
    require(select((other, candidate)) is candidate, "deterministic tie order")
    checks += 1
    for mass, dep, arr in ((550.0, 0.0, 0.0), (2000.0, 1.0, 0.0)):
        candidate.final_mass_kg = mass
        candidate.departure_delta_v_m_s = dep
        candidate.arrival_delta_v_m_s = arr
        try:
            mass_check(candidate)
        except GateFailure:
            checks += 1
        else:
            raise AssertionError("mass mismatch admitted")
    state = SimpleNamespace(position_m=(0.0, 0.0, 0.0),
                            velocity_m_s=(0.0, 0.0, 0.0), epoch_tdb_s=0.0)
    # A dataclass is required only for retaining an accepted body's raw state.
    from dataclasses import make_dataclass

    body_type = make_dataclass("Body", ["position_m", "velocity_m_s", "epoch_tdb_s"])
    body = body_type((100.0, 0.0, 0.0), (0.001, 0.0, 0.0), 0.0)
    require(endpoint_check(state, body, (0.0, 0.0, 0.0))["position_error_m"] == 100.0,
            "endpoint boundary rejected")
    checks += 1
    for position, velocity, epoch in (
        ((100.001, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0),
        ((0.0, 0.0, 0.0), (0.001001, 0.0, 0.0), 0.0),
        ((float("nan"), 0.0, 0.0), (0.0, 0.0, 0.0), 0.0),
        ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0),
    ):
        try:
            endpoint_check(state, body_type(position, velocity, epoch), (0.0, 0.0, 0.0))
        except GateFailure:
            checks += 1
        else:
            raise AssertionError("endpoint mismatch admitted")
    now = [0.0]
    budget = Budget(lambda: now[0])
    require(budget.call("ok", lambda: 7) == 7, "budget return")
    now[0] = 300.0
    try:
        budget.call("forbidden", lambda: (_ for _ in ()).throw(AssertionError("launched")))
    except GateFailure:
        checks += 1
    budget = Budget(lambda: now[0])
    retained: list[None] = []
    try:
        budget.call("overrun", lambda: now.__setitem__(0, 601.0), retained.append)
    except GateFailure:
        checks += 1
    else:
        raise AssertionError("overrun admitted")
    require(retained == [None], "overrun lost returned science")
    checks += 1
    budget = Budget(lambda: now[0])
    try:
        budget.call("native failure", lambda: (_ for _ in ()).throw(ValueError("test")))
    except ValueError:
        require(not budget.calls[-1]["returned"], "failure labelled returned")
        checks += 1
    else:
        raise AssertionError("failure swallowed")
    print(f"Native-free self-checks passed: {checks + 1}; no scientific calls")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    else:
        require(not sys.argv[1:], "only --self-test or one authorized invocation")
        require(not OUTPUT.exists(), "retained evidence exists; do not rerun")
        evidence = study()
        # Generated scientific output, exclusive creation; never overwrite evidence.
        with OUTPUT.open("x", encoding="utf-8") as stream:
            json.dump(evidence, stream, indent=2, allow_nan=False)
            stream.write("\n")
        print(json.dumps({key: evidence[key] for key in (
            "status", "elapsed_seconds",
        )} | {"error": evidence.get("error"), "output": str(OUTPUT)}))
        sys.exit(0 if evidence["status"] == "passed" else 1)
