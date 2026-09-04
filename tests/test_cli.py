from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from space_nav import cli
from space_nav.ephemeris import CartesianState
from space_nav.errors import ScenarioValidationError


ROOT = Path(__file__).parents[1]
REFERENCE = ROOT / "examples" / "reference_mission.toml"


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    source_path = str(ROOT / "src")
    environment["PYTHONPATH"] = os.pathsep.join(
        part for part in (source_path, environment.get("PYTHONPATH", "")) if part
    )
    return subprocess.run(
        [sys.executable, "-m", "space_nav", *arguments],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _scenario(seed: int = 42) -> SimpleNamespace:
    return SimpleNamespace(limits=SimpleNamespace(random_seed=seed))


def test_validate_human_and_exact_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    scenario_path = tmp_path / "mission.toml"
    scenario_path.write_text("[search]\n", encoding="utf-8")
    monkeypatch.setattr(cli, "load_scenario", lambda path: _scenario())

    assert cli.main(["validate", str(scenario_path)]) == 0
    captured = capsys.readouterr()
    assert str(scenario_path.resolve()) in captured.out
    assert captured.err == ""

    assert cli.main(["validate", str(scenario_path), "--json"]) == 0
    captured = capsys.readouterr()
    assert captured.out == json.dumps(
        {"ok": True, "scenario": str(scenario_path.resolve())}, sort_keys=True
    ) + "\n"
    assert captured.err == ""


def test_validate_json_error_is_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    scenario_path = tmp_path / "bad.toml"

    def fail(path: Path) -> None:
        raise ScenarioValidationError("is required", "spacecraft.max_thrust_n")

    monkeypatch.setattr(cli, "load_scenario", fail)
    assert cli.main(["validate", str(scenario_path), "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "ok": False,
        "error": {
            "type": "ScenarioValidationError",
            "message": "spacecraft.max_thrust_n: is required",
            "field": "spacecraft.max_thrust_n",
        },
    }
    assert "Traceback" not in captured.err


def test_ephemeris_validates_first_and_emits_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    scenario_path = tmp_path / "mission.toml"
    scenario_path.write_text("seed = 42\n", encoding="utf-8")
    calls: list[str] = []

    def load(path: Path) -> SimpleNamespace:
        calls.append("validate")
        return _scenario(7)

    def query(body: str, epoch: str) -> CartesianState:
        calls.append("query")
        return CartesianState(
            body=body,
            epoch_utc=epoch,
            epoch_tdb_s=123.0,
            origin="SSB",
            orientation="J2000",
            position_m=(1.0, 2.0, 3.0),
            velocity_m_s=(4.0, 5.0, 6.0),
        )

    monkeypatch.setattr(cli, "load_scenario", load)
    monkeypatch.setattr(cli, "query_body_state", query)
    monkeypatch.setattr(
        cli,
        "kernel_metadata",
        lambda: {
            "kernel_source": "tudatpy-standard",
            "loaded_kernel_count": 10,
            "kernels": [],
            "kernel_list_status": "not_exposed_by_tudatpy",
        },
    )

    assert (
        cli.main(
            [
                "ephemeris",
                str(scenario_path),
                "--body",
                "Mars",
                "--epoch",
                "2031-01-01T00:00:00Z",
                "--json",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert captured.err == ""
    assert calls == ["validate", "query"]
    assert payload["body"] == "Mars"
    assert payload["origin"] == "SSB"
    assert payload["orientation"] == "J2000"
    assert payload["position_m"] == [1.0, 2.0, 3.0]
    assert payload["velocity_m_s"] == [4.0, 5.0, 6.0]
    assert payload["manifest"]["random_seed"] == 7
    assert len(payload["manifest"]["scenario_sha256"]) == 64


def test_json_usage_error_and_help_do_not_query_spice(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli,
        "query_body_state",
        lambda *args: pytest.fail("SPICE must not be queried"),
    )
    assert cli.main(["ephemeris", "mission.toml", "--json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["error"]["type"] == "ArgumentError"

    assert cli.main(["--help"]) == 0
    captured = capsys.readouterr()
    assert "validate" in captured.out
    assert "ephemeris" in captured.out
    assert captured.err == ""


def test_human_ephemeris_labels_units_and_frame(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    scenario_path = tmp_path / "mission.toml"
    scenario_path.write_text("seed = 42\n", encoding="utf-8")
    monkeypatch.setattr(cli, "load_scenario", lambda path: _scenario())
    monkeypatch.setattr(
        cli,
        "query_body_state",
        lambda body, epoch: CartesianState(
            body=body,
            epoch_utc=epoch,
            epoch_tdb_s=123.0,
            origin="SSB",
            orientation="J2000",
            position_m=(1.0, 2.0, 3.0),
            velocity_m_s=(4.0, 5.0, 6.0),
        ),
    )
    monkeypatch.setattr(
        cli,
        "kernel_metadata",
        lambda: {
            "kernel_source": "tudatpy-standard",
            "loaded_kernel_count": 10,
            "kernels": [],
            "kernel_list_status": "not_exposed_by_tudatpy",
        },
    )
    assert (
        cli.main(
            [
                "ephemeris",
                str(scenario_path),
                "--body",
                "Mars",
                "--epoch",
                "2031-01-01T00:00:00Z",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert "Epoch UTC:" in captured.out
    assert "Epoch TDB [s since J2000]:" in captured.out
    assert "origin SSB, orientation J2000" in captured.out
    assert "Position [m]:" in captured.out
    assert "Velocity [m/s]:" in captured.out
    assert captured.err == ""


def test_validation_subprocess_exit_streams_and_invalid_utf8(tmp_path: Path) -> None:
    valid = _run_cli("validate", str(REFERENCE), "--json")
    assert valid.returncode == 0
    assert json.loads(valid.stdout) == {
        "ok": True,
        "scenario": str(REFERENCE.resolve()),
    }
    assert valid.stderr == ""

    invalid = tmp_path / "invalid-utf8.toml"
    invalid.write_bytes(b"\xff\xfe")
    rejected = _run_cli("validate", str(invalid), "--json")
    assert rejected.returncode == 2
    assert rejected.stdout == ""
    assert json.loads(rejected.stderr)["error"]["type"] == "ScenarioValidationError"
    assert "Traceback" not in rejected.stderr


def test_import_help_and_validation_leave_tudatpy_unloaded() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    script = """
import sys
assert "tudatpy" not in sys.modules
import space_nav
assert "tudatpy" not in sys.modules
from space_nav.cli import main
assert main(["--help"]) == 0
assert "tudatpy" not in sys.modules
assert main(["validate", sys.argv[1]]) == 0
assert "tudatpy" not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(REFERENCE)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stderr == ""


def test_installed_console_entry_point() -> None:
    entry_point = Path(sys.executable).with_name("space-nav")
    if not entry_point.is_file():
        pytest.skip("space-nav console entry point is not installed in this environment")
    result = subprocess.run(
        [str(entry_point), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "validate" in result.stdout
    assert "ephemeris" in result.stdout
    assert result.stderr == ""


def test_real_ephemeris_subprocess_is_reproducible() -> None:
    pytest.importorskip("tudatpy")
    arguments = (
        "ephemeris",
        str(REFERENCE),
        "--body",
        "Mars",
        "--epoch",
        "2031-01-01T00:00:00Z",
        "--json",
    )
    first = _run_cli(*arguments)
    second = _run_cli(*arguments)
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == ""

    first_payload = json.loads(first.stdout)
    second_payload = json.loads(second.stdout)
    for field in (
        "body",
        "epoch_utc",
        "epoch_tdb_s",
        "origin",
        "orientation",
        "position_m",
        "velocity_m_s",
    ):
        assert first_payload[field] == second_payload[field]

    manifest = first_payload["manifest"]
    assert manifest["random_seed"] == 42
    assert manifest["versions"]["tudatpy"] == "1.0.0"
    assert manifest["spice"]["loaded_kernel_count"] == len(
        manifest["spice"]["kernels"]
    )
    assert all(
        len(kernel["sha256"]) == 64 for kernel in manifest["spice"]["kernels"]
    )

    rejected = _run_cli(
        "ephemeris",
        str(REFERENCE),
        "--body",
        "Definitely-Not-A-SPICE-Body",
        "--epoch",
        "2031-01-01T00:00:00Z",
        "--json",
    )
    assert rejected.returncode == 2
    assert rejected.stdout == ""
    error = json.loads(rejected.stderr)["error"]
    assert error["type"] == "EphemerisError"
    assert "Definitely-Not-A-SPICE-Body" in error["message"]
    assert "2031-01-01T00:00:00Z" in error["message"]
    assert "Traceback" not in rejected.stderr
