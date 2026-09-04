from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tomllib

import pytest

import space_nav
from space_nav import cli
from space_nav.errors import EphemerisError, ScenarioValidationError, TransferSearchError
from space_nav.models import ImpulsiveTransferCandidate, TransferSearchResult


ROOT = Path(__file__).parents[1]


def _scenario(seed: int = 42) -> SimpleNamespace:
    return SimpleNamespace(limits=SimpleNamespace(random_seed=seed))


def _candidate(*, mass_feasible: bool = False) -> ImpulsiveTransferCandidate:
    return ImpulsiveTransferCandidate(
        candidate_id="d0001-t0002",
        departure_epoch_utc="2031-01-01T00:00:00Z",
        arrival_epoch_utc="2031-01-02T00:00:00Z",
        departure_epoch_tdb_s=100.0,
        arrival_epoch_tdb_s=86_500.0,
        flight_time_s=86_400.0,
        departure_v_infinity_m_s=(1.0, 2.0, 3.0),
        arrival_v_infinity_m_s=(4.0, 5.0, 6.0),
        departure_delta_v_m_s=1_000.0,
        arrival_delta_v_m_s=500.0,
        total_delta_v_m_s=1_500.0,
        propellant_mass_kg=600.0,
        final_mass_kg=1_400.0,
        mass_feasible=mass_feasible,
    )


def _result(*, mass_feasible: bool = False) -> TransferSearchResult:
    return TransferSearchResult(
        ephemeris_origin="SSB",
        transfer_central_body="Sun",
        orientation="J2000",
        time_scale="TDB seconds since J2000",
        evaluated_candidates=2,
        solved_candidates=1,
        failed_candidates=1,
        mass_feasible_candidates=int(mass_feasible),
        pareto_front=(_candidate(mass_feasible=mass_feasible),),
    )


def _stub_plan_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[str],
    *,
    mass_feasible: bool = False,
) -> None:
    scenario = _scenario(7)

    def load(path: Path) -> SimpleNamespace:
        calls.append("validate")
        return scenario

    def search(value: SimpleNamespace) -> TransferSearchResult:
        assert value is scenario
        calls.append("search")
        return _result(mass_feasible=mass_feasible)

    def manifest(path: Path, seed: int) -> dict[str, object]:
        assert seed == 7
        calls.append("manifest")
        return {"scenario_sha256": "a" * 64, "versions": {"space_nav": "0.2.0"}}

    def transfer_manifest(value: SimpleNamespace) -> dict[str, object]:
        assert value is scenario
        calls.append("transfer_manifest")
        return {"identifier": "sun-centered-zero-revolution-patched-conic-v1"}

    monkeypatch.setattr(cli, "load_scenario", load)
    monkeypatch.setattr(cli, "search_impulsive_transfers", search)
    monkeypatch.setattr(cli, "_manifest", manifest)
    monkeypatch.setattr(cli, "_transfer_model_manifest", transfer_manifest)


def test_plan_json_is_flat_complete_and_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    scenario_path = tmp_path / "mission.toml"
    scenario_path.write_text("[search]\n", encoding="utf-8")
    calls: list[str] = []
    _stub_plan_dependencies(monkeypatch, calls)

    assert cli.main(["plan", str(scenario_path), "--json"]) == 0
    first = capsys.readouterr()
    assert cli.main(["plan", str(scenario_path), "--json"]) == 0
    second = capsys.readouterr()

    assert first.err == second.err == ""
    assert first.out == second.out
    payload = json.loads(first.out)
    assert "result" not in payload
    assert payload == {
        "ok": True,
        "scenario": str(scenario_path.resolve()),
        "ephemeris_origin": "SSB",
        "transfer_central_body": "Sun",
        "orientation": "J2000",
        "time_scale": "TDB seconds since J2000",
        "evaluated_candidates": 2,
        "solved_candidates": 1,
        "failed_candidates": 1,
        "mass_feasible_candidates": 0,
        "pareto_front": [
            {
                "candidate_id": "d0001-t0002",
                "departure_epoch_utc": "2031-01-01T00:00:00Z",
                "arrival_epoch_utc": "2031-01-02T00:00:00Z",
                "departure_epoch_tdb_s": 100.0,
                "arrival_epoch_tdb_s": 86_500.0,
                "flight_time_s": 86_400.0,
                "departure_v_infinity_m_s": [1.0, 2.0, 3.0],
                "arrival_v_infinity_m_s": [4.0, 5.0, 6.0],
                "departure_delta_v_m_s": 1_000.0,
                "arrival_delta_v_m_s": 500.0,
                "total_delta_v_m_s": 1_500.0,
                "propellant_mass_kg": 600.0,
                "final_mass_kg": 1_400.0,
                "mass_feasible": False,
            }
        ],
        "manifest": {
            "scenario_sha256": "a" * 64,
            "versions": {"space_nav": "0.2.0"},
            "transfer_model": {
                "identifier": "sun-centered-zero-revolution-patched-conic-v1"
            },
        },
    }
    assert calls == [
        "validate",
        "search",
        "manifest",
        "transfer_manifest",
    ] * 2


def test_plan_human_labels_units_and_mass_infeasibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    scenario_path = tmp_path / "mission.toml"
    scenario_path.write_text("[search]\n", encoding="utf-8")
    _stub_plan_dependencies(monkeypatch, [])

    assert cli.main(["plan", str(scenario_path)]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    for label in (
        "Reference: SSB/J2000",
        "origin SSB, orientation J2000",
        "Sun (Sun-centered)",
        "TDB seconds since J2000",
        "Evaluated candidates: 2",
        "Solved candidates: 1",
        "Failed candidates: 1",
        "Mass-feasible candidates: 0",
        "infeasible; no candidate respects dry mass",
        "Departure UTC:",
        "Arrival UTC:",
        "Departure TDB [s since J2000]:",
        "Arrival TDB [s since J2000]:",
        "Flight time [s]:",
        "Departure hyperbolic-excess velocity [J2000 m/s]:",
        "Arrival hyperbolic-excess velocity [J2000 m/s]:",
        "Departure delta-v [m/s]:",
        "Arrival delta-v [m/s]:",
        "Total delta-v [m/s]:",
        "Propellant mass [kg]:",
        "Final mass [kg]:",
        "Mass feasible: false",
    ):
        assert label in captured.out


def test_plan_validates_before_search_or_spice(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def invalid(path: Path) -> None:
        raise ScenarioValidationError("is required", "search.departure_start_utc")

    monkeypatch.setattr(cli, "load_scenario", invalid)
    monkeypatch.setattr(
        cli,
        "search_impulsive_transfers",
        lambda scenario: pytest.fail("search must not start"),
    )
    monkeypatch.setattr(
        cli, "_manifest", lambda *args: pytest.fail("SPICE must not be queried")
    )
    monkeypatch.setattr(
        cli,
        "_transfer_model_manifest",
        lambda *args: pytest.fail("SPICE must not be queried"),
    )

    assert cli.main(["plan", "bad.toml", "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "ok": False,
        "error": {
            "type": "ScenarioValidationError",
            "message": "search.departure_start_utc: is required",
            "field": "search.departure_start_utc",
        },
    }
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "error",
    [TransferSearchError("deadline reached"), EphemerisError("no kernel")],
)
def test_plan_failure_uses_existing_error_envelope(
    error: Exception,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "load_scenario", lambda path: _scenario())

    def fail(scenario: SimpleNamespace) -> None:
        raise error

    monkeypatch.setattr(cli, "search_impulsive_transfers", fail)
    assert cli.main(["plan", "mission.toml", "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "ok": False,
        "error": {
            "type": type(error).__name__,
            "message": str(error),
            "field": None,
        },
    }
    assert "Traceback" not in captured.err


def test_version_fallback_exports_and_environment_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario_path = tmp_path / "mission.toml"
    scenario_path.write_bytes(b"mission")

    def missing(distribution: str) -> str:
        raise cli.metadata.PackageNotFoundError(distribution)

    monkeypatch.setattr(cli.metadata, "version", missing)
    monkeypatch.setattr(cli, "_tudatpy_version", lambda: "1.0.0")
    monkeypatch.setattr(cli, "kernel_metadata", lambda: {"kernels": []})
    manifest = cli._manifest(scenario_path, 42)

    assert manifest["versions"]["space_nav"] == space_nav.__version__ == "0.2.0"
    assert space_nav.ImpulsiveTransferCandidate is ImpulsiveTransferCandidate
    assert space_nav.TransferSearchResult is TransferSearchResult
    assert space_nav.TransferSearchError is TransferSearchError
    assert callable(space_nav.search_impulsive_transfers)
    assert tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
        "version"
    ] == "0.2.0"
    assert "  - tudat-resources=2.4\n" in (ROOT / "environment.yml").read_text()
