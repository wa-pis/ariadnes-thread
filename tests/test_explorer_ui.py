from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from space_nav import explorer_ui
from space_nav.errors import TransferSearchError


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
