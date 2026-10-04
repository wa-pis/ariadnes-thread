from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from space_nav import targeting_experiment as experiment
from space_nav.scenario import load_scenario
from test_damping_experiment import pipeline as damping_pipeline
from test_targeting_experiment import REFERENCE, SCENARIO


CENTRAL_STEP = Path("docs/adr/experiments/0098-central-correction-study.json")


@pytest.fixture
def pipeline(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    rig = damping_pipeline.__wrapped__(monkeypatch)
    def no_solve(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("D12 must not solve or re-probe")
    monkeypatch.setattr(experiment.correction, "_central_correction", no_solve)
    monkeypatch.setattr(experiment.correction, "_solve_matrix", no_solve)
    return rig


@pytest.mark.parametrize("selection,count", [(0.5, 3), (0.25, 4), (None, 3)])
def test_independent_fractions_first_selection_and_frozen_check(
    pipeline: SimpleNamespace, selection: float | None, count: int,
) -> None:
    pipeline.selection = selection
    science = experiment._run_targeting(pipeline.scenario, REFERENCE,
                                       central_damping_reference=CENTRAL_STEP)["science"]
    assert science["outcome"] == ("improving" if selection else "not-improving"), science["reason"]
    assert science["selected_alpha"] == selection and len(pipeline.calls) == count
    assert science["attempted_arcs"] == science["completed_arcs"] == count*3
    assert science["control_attempts"] == (2 if selection == 0.5 else 3)
    for index, alpha in enumerate((0.5,) if selection == 0.5 else (0.5, 0.25), 1):
        assert science["runs"][index]["controls"] == [v+alpha*d for v, d in zip(
            pipeline.seed, science["retained_control_step"])]
        assert science["fractions"][index-1]["score_threshold"] == science["runs"][0]["residual"]["score"]*(1-1e-4*alpha)
    if selection:
        assert science["runs"][-1]["controls"] == science["runs"][-2]["controls"]
        assert science["tighter_status"] == "completed" and science["numerical_agreement"] is True
    else:
        assert science["tighter_status"] == "skipped" and science["numerical_agreement"] is None
    if selection == 0.5:
        assert science["fractions"][1]["status"] == "skipped"
    assert len({id(env.bodies) for env in pipeline.envs}) == count
    assert not science["continuous_safety_verified"]
    json.dumps(science, allow_nan=False)


@pytest.mark.parametrize("selection", [0.5, 0.25])
@pytest.mark.parametrize("failure", ["baseline", "reuse", "deadline", "run-0", "run-1",
                                    "run-2", "disagreement"])
def test_failures_never_resume_schedule(pipeline: SimpleNamespace,
                                      selection: float, failure: str) -> None:
    pipeline.selection, pipeline.failure = selection, failure
    science = experiment._run_targeting(pipeline.scenario, REFERENCE,
                                       central_damping_reference=CENTRAL_STEP)["science"]
    assert science["outcome"] == ("improving" if failure == "disagreement" else "aborted")
    expected = (3 if selection == 0.5 else 4) if failure == "disagreement" else (
        1 if failure in ("baseline", "reuse", "deadline", "run-0") else 2 if failure == "run-1" else 3)
    assert len(pipeline.calls) == expected
    assert science["attempted_arcs"] <= 12
    if failure == "disagreement" or (failure == "run-2" and selection == 0.5):
        assert science["improvement"]["improving"]
        assert science["selected_alpha"] == selection
        assert science["numerical_agreement"] is (False if failure == "disagreement" else None)
    if failure == "run-2" and selection == 0.5:
        assert science["tighter_status"] == "failed"
        assert science["runs"][-1]["run"]["boundaries"] == []


@pytest.mark.parametrize("field", ["scenario", "candidate", "runtime", "environment", "seed_controls"])
def test_imported_identity_rejected(field: str) -> None:
    stored = experiment._load_reference(REFERENCE, load_scenario(SCENARIO))
    payload = deepcopy(experiment._load_central_step(CENTRAL_STEP, stored))
    payload["science"][field] = None
    with pytest.raises(ValueError):
        experiment._validate_central_step(payload, stored)


@pytest.mark.parametrize("fault", ["matrix", "rank", "uncapped", "capped", "divisor", "step",
    "prediction", "score", "raw", "settings", "commands", "epoch", "selection", "count", "ratio"])
def test_retained_algebra_or_evidence_mismatch_rejected(fault: str) -> None:
    stored = experiment._load_reference(REFERENCE, load_scenario(SCENARIO))
    payload = deepcopy(experiment._load_central_step(CENTRAL_STEP, stored))
    data = payload["science"]
    update = data["correction"]
    if fault == "matrix":
        update["jacobian"][0][0] += 1
    elif fault == "rank":
        update["rank"] = 5
    elif fault in ("uncapped", "capped"):
        update[fault][0] += 1
    elif fault == "divisor":
        update["divisor"] += 1
    elif fault == "step":
        update["control_step"][0] += 0.01
    elif fault == "prediction":
        update["predicted_change"][0] += 1
    elif fault == "score":
        update["predicted_score"] += 1
    elif fault == "raw":
        data["runs"][1]["run"]["boundaries"][-1]["position_m"][0] += 1
    elif fault == "settings":
        data["runs"][1]["run"]["integrator_settings"] = {}
    elif fault == "commands":
        data["runs"][1]["controls"][0] += 1
    elif fault == "epoch":
        data["runs"][1]["run"]["boundaries"][-1]["epoch_tdb_s"] += 1
    elif fault == "selection":
        data["selected_alpha"] = 1
    elif fault == "count":
        data["attempted_arcs"] = 9
    else:
        data["improvement"]["score_ratio"] += 1
    with pytest.raises(ValueError):
        experiment._validate_central_step(payload, stored)


@pytest.mark.parametrize("fault", ["runtime", "resource", "seed", "settings"])
def test_preparation_mismatch_stops_before_native(pipeline: SimpleNamespace,
                                                monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    if fault == "runtime":
        monkeypatch.setattr(experiment, "_runtime_manifest", lambda *args: {})
    elif fault == "resource":
        monkeypatch.setattr(experiment, "_environment_manifest", lambda *args: {})
    elif fault == "seed":
        monkeypatch.setattr(experiment.physical, "_build_initial_burn_controls", lambda *args: "rejected-dry-mass")
    else:
        monkeypatch.setattr(experiment.physical, "_arc_integrator_profile", lambda *args, **kwargs: {})
    science = experiment._run_targeting(pipeline.scenario, REFERENCE,
                                       central_damping_reference=CENTRAL_STEP)["science"]
    assert science["outcome"] == "aborted" and not pipeline.calls and science["attempted_arcs"] == 0


def test_closed_baseline_skips_both(pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    loader = experiment._load_central_step
    residual = experiment.correction._residual
    def load(*args: Any) -> Any:
        data = loader(*args)
        monkeypatch.setattr(experiment.correction, "_residual", lambda values: replace(residual(values), closes=True))
        return data
    monkeypatch.setattr(experiment, "_load_central_step", load)
    science = experiment._run_targeting(pipeline.scenario, REFERENCE,
                                       central_damping_reference=CENTRAL_STEP)["science"]
    assert science["outcome"] == "baseline-closed" and len(pipeline.calls) == 1
    assert all(f["status"] == "skipped" for f in science["fractions"])


@pytest.mark.parametrize("attempt", [2, 3])
def test_analytic_rejection_counts_before_launch(pipeline: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch, attempt: int) -> None:
    pipeline.selection = None
    original = experiment.physical._prepare_burn_controls
    calls = []
    def prepare(*args: Any) -> Any:
        calls.append(args)
        return "rejected-control-bounds" if len(calls) == attempt else original(*args)
    monkeypatch.setattr(experiment.physical, "_prepare_burn_controls", prepare)
    science = experiment._run_targeting(pipeline.scenario, REFERENCE,
                                       central_damping_reference=CENTRAL_STEP)["science"]
    assert science["outcome"] == "aborted" and science["control_attempts"] == attempt
    assert science["propagation_evaluations"] == attempt-1
    assert science["runs"][-1]["run"] is None


def test_digest_exclusive_cli_and_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    result = experiment._run_targeting(load_scenario(SCENARIO), REFERENCE, central_damping_reference=bad)
    assert result["science"]["attempted_arcs"] == 0
    assert "central step digest" in result["science"]["reason"]
    output = tmp_path / "output.json"
    calls = []
    monkeypatch.setattr(experiment, "_run_targeting", lambda *args, **kwargs: calls.append(kwargs) or result)
    argv = [str(SCENARIO), str(REFERENCE), str(output), "--central-damping-reference", str(bad)]
    assert experiment.main(argv) == 1
    assert calls == [{"central_damping_reference": bad}]
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        experiment.main(argv)
    assert output.read_bytes() == before and len(calls) == 1
    with pytest.raises(SystemExit) as error:
        experiment.main(argv+["--central-reference", str(bad)])
    assert error.value.code == 2


def test_quarter_tighter_failure_preserves_selection(pipeline: SimpleNamespace) -> None:
    pipeline.selection, pipeline.failure = 0.25, "run-3"
    science = experiment._run_targeting(pipeline.scenario, REFERENCE,
                                       central_damping_reference=CENTRAL_STEP)["science"]
    assert science["outcome"] == "aborted" and len(pipeline.calls) == 4
    assert science["selected_alpha"] == 0.25 and science["improvement"]["improving"]
    assert science["numerical_agreement"] is None and science["tighter_status"] == "failed"


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf")])
def test_nonfinite_matrix_or_step_rejected(bad: float) -> None:
    stored = experiment._load_reference(REFERENCE, load_scenario(SCENARIO))
    payload = deepcopy(experiment._load_central_step(CENTRAL_STEP, stored))
    payload["science"]["correction"]["capped"][0] = bad
    with pytest.raises(ValueError):
        experiment._validate_central_step(payload, stored)


def test_no_solver_even_during_import(monkeypatch: pytest.MonkeyPatch) -> None:
    import numpy as np
    def no_solve(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("retained algebra check must not solve")
    monkeypatch.setattr(np.linalg, "lstsq", no_solve)
    monkeypatch.setattr(np.linalg, "solve", no_solve)
    stored = experiment._load_reference(REFERENCE, load_scenario(SCENARIO))
    experiment._load_central_step(CENTRAL_STEP, stored)


def test_deadline_covers_reference_loading(pipeline: SimpleNamespace,
                                         monkeypatch: pytest.MonkeyPatch) -> None:
    original = experiment._load_central_step
    def load(*args: Any) -> Any:
        result = original(*args)
        pipeline.clock[0] = 301
        return result
    monkeypatch.setattr(experiment, "_load_central_step", load)
    science = experiment._run_targeting(pipeline.scenario, REFERENCE,
                                       central_damping_reference=CENTRAL_STEP)["science"]
    assert science["outcome"] == "aborted" and not pipeline.calls
    assert science["attempted_arcs"] == 0 and not pipeline.envs
