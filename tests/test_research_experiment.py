from dataclasses import dataclass
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from space_nav import research_experiment as experiment
from space_nav.errors import EphemerisError
from space_nav.scenario import load_scenario
from test_research_report import _report


@dataclass(frozen=True)
class Candidate:
    candidate_id: str = "d0001-t0035"


@dataclass(frozen=True)
class Field:
    body: str
    gravitational_parameter_m3_s2: float


@pytest.fixture
def rig(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    scenario = load_scenario(Path("examples/m3_feasible_mission.toml"))
    calls: list[tuple[str, object]] = []
    candidate = Candidate()
    resource = Field("manufactured", 1.0)
    environment = SimpleNamespace(
        model_id="manufactured", origin="SSB", orientation="J2000",
        initial_epoch_tdb_s=100.0, final_epoch_tdb_s=200.0,
        harmonic_fields=(Field("Moon", 2.0), Field("Mars", 3.0)),
        gravity_acceleration_inventory=(resource,),
        solar_radiation_pressure=resource, relativity=resource,
        collision_resource=resource,
    )

    def search(value: object, **kwargs: object) -> object:
        assert value is scenario
        calls.append(("search", kwargs))
        return SimpleNamespace(pareto_front=(candidate,))

    def build(value: object, spacecraft: object, *, budget: object) -> object:
        assert value is candidate and spacecraft is scenario.spacecraft
        calls.append(("environment", budget))
        return environment

    def boundaries(*args: object) -> tuple[str, str]:
        assert args == (scenario, candidate, 2.0, 3.0)
        return "initial", "target"

    def compare(*args: object) -> object:
        calls.append(("compare", args))
        return _report()

    monkeypatch.setattr(experiment, "_search_impulsive_transfers", search)
    monkeypatch.setattr(experiment, "_runtime_manifest", lambda seed: {"seed": seed})
    monkeypatch.setattr(experiment.physical, "_build_physical_environment", build)
    monkeypatch.setattr(experiment.physical, "_build_boundary_states", boundaries)
    monkeypatch.setattr(experiment.physical, "_build_initial_burn_controls",
                        lambda *args: (0.0, 0.0, 10.0, 0.0, 0.0, 10.0))
    monkeypatch.setattr(experiment, "_compare_research_profiles", compare)
    return SimpleNamespace(scenario=scenario, calls=calls)


def test_reference_reuses_budget_resources_and_commands(rig: SimpleNamespace) -> None:
    experiment._run_reference(rig.scenario)
    assert [name for name, _ in rig.calls] == ["search", "environment", "compare"]
    search, budget, args = [value for _, value in rig.calls]
    assert args[0] is budget
    assert search["deadline_monotonic_s"] == budget.deadline_monotonic_s
    assert search["monotonic"] is budget.monotonic
    assert budget.runtime_seconds == 300 and budget.control_attempts == 0
    assert args[4:7] == ("initial", "target", (0.0, 0.0, 10.0, 0.0, 0.0, 10.0))
    metadata = json.loads(args[7])
    assert metadata["automatic_retries"] == 0
    assert metadata["maximum_native_arcs"] == 6
    assert metadata["environment"]["harmonic_fields"][0]["body"] == "Moon"


@pytest.mark.parametrize("failure", ["candidate", "resource", "seed", "deadline"])
def test_preparation_failure_retained_without_launch(
    rig: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    if failure == "candidate":
        monkeypatch.setattr(experiment, "_search_impulsive_transfers",
                            lambda *a, **kw: SimpleNamespace(pareto_front=()))
    elif failure == "resource":
        def missing(seed: int) -> dict:
            raise EphemerisError("missing kernel")
        monkeypatch.setattr(experiment, "_runtime_manifest", missing)
    elif failure == "seed":
        monkeypatch.setattr(experiment.physical, "_build_initial_burn_controls",
                            lambda *a: "analytic dry-mass rejection")
    else:
        original = experiment._ResearchBudget
        ticks = iter((0.0, 301.0))
        monkeypatch.setattr(experiment, "_ResearchBudget",
                            lambda *a: original(*a, monotonic=lambda: next(ticks)))
    report = experiment._run_reference(rig.scenario)
    assert report.progress.attempted_arcs == 0
    assert report.nominal.outcome == "unavailable"
    assert report.nominal.reason
    assert report.nominal.terminal_errors is None
    assert report.tighter.outcome == "unavailable"
    assert not report.continuous_safety_verified
    assert all(name != "compare" for name, _ in rig.calls)
    json.dumps(report.to_dict(), allow_nan=False)


def test_entrypoint_preserves_evidence_and_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    def run(scenario: object) -> object:
        calls.append(scenario)
        return _report()

    monkeypatch.setattr(experiment, "_run_reference", run)
    output = tmp_path / "evidence.json"
    argv = ["examples/m3_feasible_mission.toml", str(output)]
    assert experiment.main(argv) == 0
    payload = json.loads(output.read_text())
    assert payload["science"]["research_only"]
    assert "research_experiment.py" in payload["reproduction"]["source_sha256"]
    with pytest.raises(FileExistsError):
        experiment.main(argv)
    assert len(calls) == 1
