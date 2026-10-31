from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, localcontext
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from space_nav import explorer_ui, research_export as export
from space_nav.ephemeris import CartesianState
from space_nav.models import ImpulsiveTransferCandidate, TransferSearchResult
from space_nav.scenario import load_scenario

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/adr/experiments/0119-m2-reference.json"


def state(value: dict[str, Any]) -> CartesianState:
    return CartesianState(
        **{
            **value,
            "position_m": tuple(value["position_m"]),
            "velocity_m_s": tuple(value["velocity_m_s"]),
        }
    )


def candidate(value: dict[str, Any]) -> ImpulsiveTransferCandidate:
    return ImpulsiveTransferCandidate(
        **{
            **value,
            "departure_v_infinity_m_s": tuple(value["departure_v_infinity_m_s"]),
            "arrival_v_infinity_m_s": tuple(value["arrival_v_infinity_m_s"]),
        }
    )


@pytest.fixture
def inputs() -> tuple[Any, ...]:
    record = json.loads(FIXTURE.read_bytes())
    run = record["runs"][0]
    provenance = {
        **record["provenance"]["manifest"],
        "scenario": record["normalized_scenario"],
        "transfer_model": record["provenance"]["transfer_model"],
        "source": record["identity"],
    }
    search = TransferSearchResult(
        **{
            **run["search"],
            "pareto_front": tuple(candidate(c) for c in run["search"]["pareto_front"]),
        }
    )
    return (
        load_scenario(ROOT / "examples/r1_m2_reserve_reference.toml"),
        candidate(run["selected"]),
        search,
        tuple(state(s) for s in run["states"]),
        provenance,
    )


def build(inputs: tuple[Any, ...], **kwargs: object) -> export.ExportBundle:
    record = json.loads(FIXTURE.read_bytes())
    search_call = next(call for call in record["calls"] if call["label"] == "search 1")
    endpoints = tuple(
        state(record["runs"][0]["endpoints"][key]["body_state"])
        for key in ("departure", "arrival")
    )
    return export.build_export(
        *inputs,
        creation_utc="2026-10-31T10:00:00.000000Z",
        selection_policy="minimum-delta-v-with-50kg-reserve",
        endpoints=endpoints,
        search_elapsed_s=search_call["end_s"] - search_call["start_s"],
        **kwargs,
    )


def test_offline_reference_roundtrip_and_identities(
    inputs: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Serialization must consume retained states, without another native calculation.
    from space_nav import ephemeris

    monkeypatch.setattr(
        ephemeris,
        "_ensure_standard_kernels",
        Mock(side_effect=AssertionError("native query")),
    )
    bundle = build(inputs)
    assert bundle == build(inputs)
    payload = json.loads(bundle.json_bytes)
    assert (
        sha256(export.canonical_json(payload["scientific"])).hexdigest()
        == bundle.result_id
    )
    assert payload["scientific"]["status"] == {
        "calculation": "passed",
        "reserve": "passed",
        "qualification": "ideal-model-feasible",
    }
    assert payload["scientific"]["reserve"]["required_kg"] == 50
    assert len(payload["scientific"]["states"]) == 121
    assert payload["exchange"]["oem_sha256"] == sha256(bundle.oem_bytes).hexdigest()
    decoded = export.audit.read_bytes(bundle.oem_bytes)
    assert decoded.result_id == bundle.result_id
    assert len(decoded.points) == 121
    assert decoded.qualification == "ideal-model-feasible"
    maximum = payload["exchange"]["maximum_residuals"]
    assert Decimal(maximum["epoch_error_s"]) <= Decimal("1e-6")
    assert Decimal(maximum["position_error_m"]) <= Decimal("0.001")
    assert Decimal(maximum["velocity_error_m_s"]) <= Decimal("1e-9")
    assert (
        sha256(FIXTURE.read_bytes()).hexdigest()
        == "3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0"
    )
    assert (
        Path(export.audit.__file__).read_bytes()
        == (ROOT / "docs/adr/experiments/0124-oem-reader.py").read_bytes()
    )


def test_creation_time_is_only_exchange_envelope(inputs: tuple[Any, ...]) -> None:
    original = build(inputs)
    record = json.loads(FIXTURE.read_bytes())
    endpoints = tuple(
        state(record["runs"][0]["endpoints"][key]["body_state"])
        for key in ("departure", "arrival")
    )
    other = export.build_export(
        *inputs,
        creation_utc="2026-11-01T00:00:00.000000Z",
        selection_policy="minimum-delta-v-with-50kg-reserve",
        endpoints=endpoints,
        search_elapsed_s=0.2,
    )
    assert original.result_id == other.result_id
    assert original.oem_bytes != other.oem_bytes


@pytest.mark.parametrize("change", ["states", "source", "ignored-input"])
def test_scientific_identity_binds_actual_payload(
    inputs: tuple[Any, ...], change: str
) -> None:
    original = build(inputs)
    values = list(deepcopy(inputs))
    if change == "states":
        states = list(values[3])
        s = states[60]
        states[60] = replace(s, position_m=(s.position_m[0] + 1, *s.position_m[1:]))
        values[3] = tuple(states)
    elif change == "source":
        values[4]["source"]["base_revision"] = "f" * 40
    else:
        scenario = replace(
            values[0], spacecraft=replace(values[0].spacecraft, max_thrust_n=1.0)
        )
        values[0] = scenario
        values[4]["scenario"] = scenario.to_dict()
    assert build(tuple(values)).result_id != original.result_id


@pytest.mark.parametrize(
    "bad",
    [
        "frame",
        "kernel",
        "order",
        "version",
        "source",
        "scenario",
        "model",
        "count",
        "epoch",
        "mass",
        "endpoint",
    ],
)
def test_bad_snapshot_cannot_publish(inputs: tuple[Any, ...], bad: str) -> None:
    values = list(deepcopy(inputs))
    if bad == "frame":
        values[4]["reference"]["orientation"] = "EME2000"
    elif bad == "kernel":
        values[4]["spice"]["kernels"][0]["sha256"] = "0" * 64
    elif bad == "order":
        values[4]["spice"]["kernels"].reverse()
    elif bad == "version":
        values[4]["versions"]["tudatpy"] = "unknown"
    elif bad == "source":
        values[4]["source"].clear()
    elif bad == "scenario":
        values[4]["scenario"]["spacecraft"]["isp_s"] = 1
    elif bad == "model":
        values[4]["transfer_model"]["identifier"] = "new-model"
    elif bad == "count":
        values[3] = values[3][:1]
    elif bad == "epoch":
        values[3] = (replace(values[3][0], epoch_tdb_s=0), *values[3][1:])
    elif bad == "mass":
        c = replace(values[1], final_mass_kg=values[1].final_mass_kg + 1)
        values[1] = c
        values[2] = replace(
            values[2],
            pareto_front=tuple(
                c if x.candidate_id == c.candidate_id else x
                for x in values[2].pareto_front
            ),
        )
    else:
        values[3] = (replace(values[3][0], position_m=(0.0, 0.0, 0.0)), *values[3][1:])
    with pytest.raises(export.ResultExportError):
        build(tuple(values))


def test_failed_independent_decode_blocks_bundle(
    inputs: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        export.audit, "verify", Mock(side_effect=ValueError("independent mismatch"))
    )
    with pytest.raises(export.ResultExportError, match="independent mismatch"):
        build(inputs)


@pytest.mark.parametrize(
    ("epoch", "text"),
    [
        (0.0, "2000-01-01T12:00:00.000000"),
        (-0.000001, "2000-01-01T11:59:59.999999"),
        (86400.0, "2000-01-02T12:00:00.000000"),
        (0.0078125, "2000-01-01T12:00:00.007812"),
        (0.0234375, "2000-01-01T12:00:00.023438"),
        (5140799.9999999, "2000-03-01T00:00:00.000000"),
    ],
)
def test_tdb_rounding_anchors(epoch: float, text: str) -> None:
    with localcontext() as context:
        context.prec = 6
        assert export.format_tdb(epoch) == text


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), 1e300, -1e300])
def test_bad_epoch(bad: float) -> None:
    with pytest.raises(export.ResultExportError):
        export.format_tdb(bad)


def test_component_units_precision_and_gate() -> None:
    assert export._component(1234.5) == "1.234500000000000E+00"
    assert export._component(-0.0) == "0.000000000000000E+00"
    assert export._component(1e-300).endswith("E-303")
    with pytest.raises(export.ResultExportError):
        export._component(True)
    with pytest.raises(export.ResultExportError):
        export.canonical_json({"x": float("nan")})
    # Rounding must not collapse epochs into a publishable segment.
    s = CartesianState(
        "Spacecraft",
        "2000-01-01T12:00:00Z",
        0.0,
        "SSB",
        "J2000",
        (1.0, 2.0, 3.0),
        (4.0, 5.0, 6.0),
    )
    with pytest.raises(export.ResultExportError, match="formatted epochs"):
        export._oem_bytes(
            (s, replace(s, epoch_tdb_s=0.0000001)),
            "a" * 64,
            "unqualified",
            "2026-10-31T00:00:00.000000Z",
        )


def app() -> AppTest:
    return AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=45).run()


def test_ui_positive_export_stale_inputs_candidate_and_sort() -> None:
    ui = app()
    ui.selectbox(key="example_choice").select("С резервом 50 кг").run()
    ui.button[0].click().run()
    ui.button[1].click().run()
    assert not ui.exception
    assert "export" in ui.session_state, [item.value for item in ui.error]
    bundle = ui.session_state["export"]
    payload = json.loads(bundle.json_bytes)
    assert payload["scientific"]["status"]["qualification"] == "ideal-model-feasible"
    assert len(ui.get("download_button")) == 2
    ui.select_slider[0].set_value(float(ui.select_slider[0].options[60])).run()
    assert "export" in ui.session_state, [item.value for item in ui.error]
    assert ui.session_state["export"] == bundle
    ui.selectbox(key="priority").select("Быстрее долететь").run()
    assert "export" in ui.session_state, [item.value for item in ui.error]
    assert ui.session_state["export"] == bundle
    other = ui.selectbox(key="candidate").options[1]
    ui.selectbox(key="candidate").select(other).run()
    assert not ui.exception
    assert "export" in ui.session_state, [item.value for item in ui.error]
    assert ui.session_state["export"].result_id != bundle.result_id
    assert (
        json.loads(ui.session_state["export"].json_bytes)["scientific"]["candidate"][
            "candidate_id"
        ]
        == other
    )
    ui.number_input(key="field:spacecraft.isp_s").set_value(451.0).run()
    assert not ui.get("download_button")
    assert "export" not in ui.session_state


def test_ui_exchange_failure_retains_diagnostics_without_download(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        explorer_ui,
        "build_export",
        Mock(side_effect=export.ResultExportError("decode mismatch")),
    )
    ui = app()
    ui.button[0].click().run()
    ui.button[1].click().run()
    assert not ui.exception and ui.metric
    assert not ui.get("download_button")
    assert ui.session_state["export_error"]["stage"] == "exchange"
    assert ui.session_state["export_error"]["provenance"]


def test_ui_resource_change_invalidates_downloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ui = app()
    ui.button[0].click().run()
    ui.button[1].click().run()
    assert "export" in ui.session_state, [item.value for item in ui.error]
    assert ui.session_state["export"]
    changed = deepcopy(ui.session_state["provenance"]["spice"])
    changed["kernels"][0]["sha256"] = "0" * 64
    monkeypatch.setattr(explorer_ui.ephemeris, "kernel_metadata", lambda: changed)
    ui.run()
    assert not ui.exception
    assert "result" not in ui.session_state
    assert "export" not in ui.session_state
    assert not ui.get("download_button")


@pytest.mark.parametrize("stage", ["search", "sample", "export"])
def test_late_result_is_not_published(
    monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    name = {
        "search": "search_impulsive_transfers",
        "sample": "sample_transfer",
        "export": "build_export",
    }[stage]
    original = getattr(explorer_ui, name)

    def late(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        explorer_ui._invalidate()
        return result

    monkeypatch.setattr(explorer_ui, name, late)
    ui = app()
    ui.button[0].click().run()
    ui.button[1].click().run()
    assert not ui.exception
    assert "export" not in ui.session_state
    assert not ui.get("download_button")
    assert ui.error


def test_unqualified_coast_is_never_promoted() -> None:
    ui = app()
    ui.button[0].click().run()
    ui.button[1].click().run()
    assert not ui.exception
    assert "export" in ui.session_state, [item.value for item in ui.error]
    payload = json.loads(ui.session_state["export"].json_bytes)
    assert payload["scientific"]["status"]["qualification"] == "unqualified"
    assert payload["scientific"]["status"]["reserve"] == "failed"
    assert b"COMMENT QUALIFICATION unqualified" in ui.session_state["export"].oem_bytes
    ui.checkbox(key="fuel_only").check().run()
    assert not ui.get("download_button")
    assert "export" not in ui.session_state


@pytest.mark.parametrize("change", ["source", "model"])
def test_other_stale_identity_invalidates_downloads(
    monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    ui = app()
    ui.button[0].click().run()
    ui.button[1].click().run()
    assert "export" in ui.session_state, [item.value for item in ui.error]
    assert ui.session_state["export"]
    if change == "source":
        changed = deepcopy(ui.session_state["provenance"]["source"])
        changed["base_revision"] = "0" * 40
        monkeypatch.setattr(explorer_ui, "source_identity", lambda: changed)
    else:
        # A model code change is part of the source identity, not a new physical run.
        changed = deepcopy(ui.session_state["provenance"]["source"])
        changed["file_sha256"]["src/space_nav/transfer.py"] = "0" * 64
        monkeypatch.setattr(explorer_ui, "source_identity", lambda: changed)
    ui.run()
    assert not ui.exception
    assert "export" not in ui.session_state
    assert not ui.get("download_button")
    assert ui.session_state["calculation_error"]["stage"] == "stale-result"


def test_search_error_retains_available_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        explorer_ui,
        "search_impulsive_transfers",
        Mock(side_effect=export.ResultExportError("search failed")),
    )
    ui = app()
    ui.button[0].click().run()
    ui.button[1].click().run()
    assert not ui.exception
    diagnostic = ui.session_state["calculation_error"]
    assert diagnostic["stage"] == "search"
    assert diagnostic["message"] == "search failed"
    assert diagnostic["provenance"]["source"]
    assert diagnostic["provenance"]["spice"]
    assert not ui.get("download_button")
    ui.run()
    assert any("search failed" in item.value for item in ui.error)
