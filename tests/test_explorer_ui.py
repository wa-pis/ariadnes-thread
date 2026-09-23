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
    app.select_slider[0].set_value(float(app.select_slider[0].options[-1])).run()
    assert not app.exception
    assert app.session_state["result"] == before
    last_epoch = app.session_state["sampled"][0][-1].epoch_utc
    assert any(f"UTC: {last_epoch}" in item.value for item in app.markdown)
    alternate = app.selectbox(key="candidate").options[1]
    app.selectbox(key="candidate").select(alternate).run()
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
    app.select_slider[0].set_value(float(app.select_slider[0].options[10])).run()
    app.selectbox(key="candidate").select(app.selectbox(key="candidate").options[1]).run()
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


def test_preferences_filter_help_and_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    from space_nav.explorer_help import FIELD_HELP
    from space_nav.scenario import _FIELDS

    assert set().union(*_FIELDS.values()) == set(FIELD_HELP)
    assert all(FIELD_HELP.values())
    search = Mock(wraps=explorer_ui.search_impulsive_transfers)
    provenance = Mock(wraps=explorer_ui._search_provenance)
    monkeypatch.setattr(explorer_ui, "search_impulsive_transfers", search)
    monkeypatch.setattr(explorer_ui, "_search_provenance", provenance)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button[0].click().run()
    assert all(w.help for w in (*app.number_input, *app.text_input))
    assert sum(w.key == "field:limits.max_candidates" for w in app.number_input) == 1
    assert any("44 дат старта × 45" in c.value for c in app.caption)
    app.button[1].click().run()
    result = app.session_state["result"]
    snapshot = app.session_state["provenance"]
    chosen = app.selectbox(key="candidate").value
    for priority, attr in explorer_ui.PRIORITIES.items():
        app.selectbox(key="priority").select(priority).run()
        assert not app.exception
        expected = [c.candidate_id for c in sorted(result.pareto_front,
                    key=lambda c: (getattr(c, attr), c.candidate_id))]
        assert app.selectbox(key="candidate").options == expected
        assert app.selectbox(key="candidate").value == chosen
        assert any("Проверка столкновений" in w.value for w in app.warning)
    app.checkbox(key="fuel_only").check().run()
    feasible = [c for c in result.pareto_front if c.mass_feasible]
    if feasible:
        assert set(app.selectbox(key="candidate").options) == {c.candidate_id for c in feasible}
    else:
        assert not app.metric and not app.select_slider
        assert any("Нет подходящих" in i.value for i in app.info)
    assert any(e.label == "О расчёте" for e in app.expander)
    app.checkbox(key="fuel_only").uncheck().run()
    assert not app.exception
    assert app.metric and app.select_slider
    assert search.call_count == provenance.call_count == 1
    assert app.session_state["result"] == result
    assert app.session_state["provenance"] == snapshot
    for budget, grid in ((1, "1 дат старта × 1"), (100, "10 дат старта × 10")):
        app.number_input(key="field:limits.max_candidates").set_value(budget).run()
        assert "result" not in app.session_state
        assert any(grid in c.value for c in app.caption)
        app.button[1].click().run()
        assert not app.exception
        assert search.call_args.args[0].limits.max_candidates == budget


def test_elapsed_days_reset_on_candidate_change() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button[0].click().run()
    app.button[1].click().run()
    slider = app.select_slider[0]
    assert slider.label == "Дней после старта"
    assert len(slider.options) == 121
    app.select_slider[0].set_value(float(slider.options[60])).run()
    other = app.selectbox(key="candidate").options[1]
    app.selectbox(key="candidate").select(other).run()
    assert not app.exception
    assert app.select_slider[0].value == 0
    candidate = next(c for c in app.session_state["result"].pareto_front if c.candidate_id == other)
    assert float(app.select_slider[0].options[-1]) == candidate.flight_time_s / 86400


def test_manufactured_long_transfer_days() -> None:
    days = explorer_ui._elapsed_days(3000 * 86400.0, 121)
    assert len(days) == len(set(days)) == 121
    assert (days[0], days[60], days[-1]) == (0, 1500, 3000)


def test_help_semantics_and_ignored_fields() -> None:
    from space_nav.explorer_help import FIELD_HELP, CONTROL_HELP, RESULT_HELP
    from space_nav.transfer import IGNORED_SCENARIO_FIELDS
    from space_nav.scenario import _FIELDS

    for field in IGNORED_SCENARIO_FIELDS:
        section, _, name = field.partition(".")
        names = _FIELDS[section] if not name else (name,)
        for key in names:
            assert "не учитывает" in FIELD_HELP[key]
    assert set(CONTROL_HELP) == {"elapsed", "priority", "fuel_only", "candidate"}
    assert all(CONTROL_HELP.values()) and all(RESULT_HELP.values())
    assert "кг" in FIELD_HELP["dry_mass_kg"]
    assert "сухой" in FIELD_HELP["initial_mass_kg"]
    assert "UTC" in FIELD_HELP["departure_start_utc"]
    assert "1–2000" in FIELD_HELP["max_candidates"]
    assert "не текущая скорость" in RESULT_HELP["delta_v"]
    assert "неизвестные" in RESULT_HELP["scope"]
