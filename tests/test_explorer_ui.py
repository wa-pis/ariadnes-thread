from __future__ import annotations

from pathlib import Path
import json
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from space_nav import explorer_ui
from space_nav.cli import _manifest
from space_nav.errors import EphemerisError, TransferSearchError
from space_nav.scenario import load_scenario
from space_nav.transfer import _transfer_model_manifest


APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def test_example_search_slider_edit_and_invalid_rerun() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert not app.number_input
    app.button[0].click().run()
    app.button[1].click().run()
    assert not app.exception
    assert len(app.metric) == 3
    assert app.error  # Reference dry mass fails the ideal budget.
    before = app.session_state["result"]
    app.slider[0].set_value(120).run()
    assert not app.exception
    assert app.session_state["result"] == before
    last_epoch = app.session_state["sampled"][0][-1].epoch_utc
    assert any(f"UTC: {last_epoch}" in item.value for item in app.markdown)
    alternate = app.selectbox[0].options[1]
    app.selectbox[0].select(alternate).run()
    assert not app.exception
    assert app.session_state["sampled_id"] == alternate
    app.number_input(key="field:spacecraft.dry_mass_kg").set_value(500.0).run()
    assert not app.metric
    app.button[1].click().run()
    assert not app.exception
    assert len(app.metric) == 3
    app.text_input(key="field:search.departure_end_utc").set_value("bad-date").run()
    assert not app.metric
    app.button[1].click().run()
    assert not app.exception
    assert any("departure_end_utc" in e.value for e in app.error)
    assert not app.metric and not app.slider


def test_search_failure_clears_previous_result(monkeypatch: pytest.MonkeyPatch) -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button[0].click().run()
    app.button[1].click().run()
    assert app.metric

    def fail(scenario: object) -> None:
        raise TransferSearchError("SPICE unavailable")

    monkeypatch.setattr(explorer_ui, "search_impulsive_transfers", fail)
    app.button[1].click().run()
    assert not app.exception
    assert any("SPICE unavailable" in e.value for e in app.error)
    assert not app.metric and not app.slider


def test_sampling_failure_removes_result(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(candidate: object) -> None:
        raise TransferSearchError("sampling resource unavailable")

    monkeypatch.setattr(explorer_ui, "sample_transfer", fail)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button[0].click().run()
    app.button[1].click().run()
    assert not app.exception
    assert any("sampling resource unavailable" in e.value for e in app.error)
    assert not app.metric and not app.slider
    assert "provenance" not in app.session_state


def test_provenance_matches_cli_and_detaches_inputs() -> None:
    path = APP.parent / "examples/reference_mission.toml"
    scenario = load_scenario(path)
    with explorer_ui.SCIENCE_LOCK:
        snapshot = explorer_ui._search_provenance(scenario)
        cli = _manifest(path, scenario.limits.random_seed)
        model = _transfer_model_manifest(scenario)
    for field in ("versions", "reference", "random_seed", "spice"):
        assert snapshot[field] == cli[field]
    assert snapshot["transfer_model"] == model
    assert snapshot["scenario"] == scenario.to_dict()
    assert "scenario_sha256" not in snapshot
    json.dumps(snapshot, allow_nan=False)
    snapshot["scenario"]["spacecraft"]["dry_mass_kg"] = 500
    assert scenario.spacecraft.dry_mass_kg != 500


def test_provenance_lifecycle_and_no_repeated_work(monkeypatch: pytest.MonkeyPatch) -> None:
    search = Mock(wraps=explorer_ui.search_impulsive_transfers)
    provenance = Mock(wraps=explorer_ui._search_provenance)
    monkeypatch.setattr(explorer_ui, "search_impulsive_transfers", search)
    monkeypatch.setattr(explorer_ui, "_search_provenance", provenance)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button[0].click().run()
    app.button[1].click().run()
    assert not app.exception
    assert any(e.label == "О расчёте" for e in app.expander)
    snapshot = app.session_state["provenance"]
    assert snapshot["scenario"] == search.call_args.args[0].to_dict()
    panel = next(e for e in app.expander if e.label == "О расчёте")
    assert json.loads(panel.json[0].value)["transfer_model"] == snapshot["transfer_model"]
    app.slider[0].set_value(10).run()
    app.selectbox[0].select(app.selectbox[0].options[1]).run()
    assert not app.exception
    assert search.call_count == provenance.call_count == 1
    assert app.session_state["provenance"] == snapshot
    app.number_input(key="field:spacecraft.dry_mass_kg").set_value(500.0).run()
    assert "provenance" not in app.session_state
    app.button[1].click().run()
    assert not app.exception
    assert app.session_state["provenance"]["scenario"]["spacecraft"]["dry_mass_kg"] == 500
    assert snapshot["scenario"]["spacecraft"]["dry_mass_kg"] != 500
    assert search.call_count == provenance.call_count == 2
    app.button[0].click().run()
    assert "provenance" not in app.session_state
    assert not app.metric and not app.slider


@pytest.mark.parametrize("stage", ["search", "provenance", "sampling", "validation"])
def test_failure_clears_successful_provenance(
    monkeypatch: pytest.MonkeyPatch, stage: str,
) -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button[0].click().run()
    app.button[1].click().run()
    assert "provenance" in app.session_state
    if stage == "validation":
        app.text_input(key="field:search.departure_end_utc").set_value("bad-date").run()
    else:
        target = {"search": "search_impulsive_transfers", "provenance": "_search_provenance",
                  "sampling": "sample_transfer"}[stage]
        monkeypatch.setattr(explorer_ui, target, Mock(side_effect=EphemerisError("resource unavailable")))
    app.button[1].click().run()
    assert not app.exception
    assert app.error
    assert "provenance" not in app.session_state
    assert "result" not in app.session_state
    assert not app.metric and not app.slider
    assert not any(e.label == "О расчёте" for e in app.expander)
