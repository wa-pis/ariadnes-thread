from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from space_nav import targeting_experiment as experiment
from space_nav.errors import TrajectoryRefinementError
from space_nav.models import FiniteBurnRecord
from space_nav.research import ResearchProgress, ResearchRun
from space_nav.scenario import load_scenario
from test_targeting_experiment import (
    REFERENCE,
    SCENARIO,
    _state,
    pipeline as d7_pipeline,
)
from test_damping_experiment import DAMPING
from test_research_propagation import _rig


RESPONSE = Path("docs/adr/experiments/0092-local-response-study.json")


def test_budget_order_caps_no_restart_and_deadline() -> None:
    clock = [0.0]
    budget = experiment._ColumnBudget("fixture", 300, lambda: clock[0])
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_arc(first_in_evaluation=True)
    for _ in range(13):
        budget.begin_control()
        with pytest.raises(TrajectoryRefinementError):
            budget.begin_control()
        for arc in range(3):
            budget.begin_arc(first_in_evaluation=arc == 0)
            with pytest.raises(TrajectoryRefinementError):
                budget.begin_arc(first_in_evaluation=False)
            budget.complete_arc()
    assert (
        budget.control_attempts,
        budget.propagation_evaluations,
        budget.completed_arcs,
    ) == (13, 13, 39)
    for action in (
        budget.begin_control,
        lambda: budget.begin_arc(first_in_evaluation=True),
    ):
        with pytest.raises(TrajectoryRefinementError):
            action()
    clock[0] = 300
    with pytest.raises(TrajectoryRefinementError):
        budget.check()


@pytest.fixture
def pipeline(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    original_targeting = experiment._TargetingBudget
    rig = d7_pipeline.__wrapped__(monkeypatch)
    monkeypatch.setattr(experiment, "_TargetingBudget", original_targeting)
    rig.d7 = experiment._load_damping_reference(DAMPING, rig.stored)
    rig.d9 = experiment._load_column_reference(RESPONSE, rig.d7, rig.stored)
    original_budget = experiment._ColumnBudget

    def budget(*args: Any) -> Any:
        value = original_budget(*args, monotonic=lambda: rig.clock[0])
        rig.budgets.append(value)
        return value

    monkeypatch.setattr(experiment, "_ColumnBudget", budget)

    def compose(
        budget: Any,
        scenario: Any,
        env: Any,
        start: Any,
        end: Any,
        controls: tuple[float, ...],
        *,
        tighter: bool,
        register_control: bool,
    ) -> ResearchRun:
        index = len(rig.calls)
        assert not tighter and not register_control
        assert budget.control_attempts == index + 1
        assert end == _state(rig.stored["nominal"]["target_state"])
        rig.calls.append((controls, tighter, env))
        raw = (
            rig.stored["nominal"]
            if index == 0
            else rig.d7["science"]["runs"][(index + 1) // 2]["run"]
        )
        if rig.failure == f"run-{index}":
            budget.begin_arc(first_in_evaluation=True)
            return ResearchRun(
                profile="nominal",
                outcome="aborted",
                reason="manufactured native failure",
                progress=ResearchProgress(1, 0),
                checked_state_count=1,
                check_coverage="manufactured",
                integrator_settings_json=json.dumps(raw["integrator_settings"]),
            )
        for arc in range(3):
            budget.begin_arc(first_in_evaluation=arc == 0)
            budget.complete_arc()
        states = [_state(v) for v in raw["boundaries"]]
        epochs = (
            start.epoch_tdb_s,
            start.epoch_tdb_s + controls[2],
            end.epoch_tdb_s - controls[5],
            end.epoch_tdb_s,
        )
        states = [replace(s, epoch_tdb_s=t) for s, t in zip(states, epochs)]
        if index > 0 and index % 2 == 0:
            original = rig.stored["nominal"]["boundaries"][-1]
            states[-1] = replace(
                states[-1],
                position_m=tuple(
                    2 * b - a
                    for a, b in zip(states[-1].position_m, original["position_m"])
                ),
                velocity_m_s=tuple(
                    2 * b - a
                    for a, b in zip(states[-1].velocity_m_s, original["velocity_m_s"])
                ),
            )
        if (
            index == 0 and rig.failure == "baseline"
        ) or rig.failure == f"positive-{index}":
            states[1] = replace(
                states[1],
                position_m=(states[1].position_m[0] + 20, *states[1].position_m[1:]),
            )
        if index == 0 or index % 2 == 1:
            masses = tuple(raw["boundary_masses_kg"])
        else:
            rate = scenario.spacecraft.max_thrust_n / (
                9.80665 * scenario.spacecraft.isp_s
            )
            m0 = scenario.spacecraft.initial_mass_kg
            m1 = m0 - (epochs[1] - epochs[0]) * rate
            masses = (m0, m1, m1, m1 - (epochs[3] - epochs[2]) * rate)
        burns = tuple(
            replace(
                FiniteBurnRecord(**{**b, "direction_tnw": tuple(b["direction_tnw"])}),
                start_epoch_tdb_s=epochs[i],
                end_epoch_tdb_s=epochs[i + 1],
                initial_mass_kg=masses[i],
                final_mass_kg=masses[i + 1],
                propellant_mass_kg=masses[i] - masses[i + 1],
                ideal_equivalent_delta_v_m_s=9.80665
                * scenario.spacecraft.isp_s
                * math.log(masses[i] / masses[i + 1]),
            )
            for b, i in zip(raw["burns"], (0, 2))
        )
        if rig.failure == "deadline" and index == 0:
            rig.clock[0] = 300
        return ResearchRun(
            profile="nominal",
            outcome="completed",
            reason=None,
            progress=ResearchProgress(3, 3),
            checked_state_count=10,
            check_coverage="manufactured",
            integrator_settings_json=json.dumps(raw["integrator_settings"]),
            boundaries=tuple(states),
            boundary_masses_kg=masses,
            burns=burns,
            target_state=end,
        )

    monkeypatch.setattr(experiment, "_compose_research_run", compose)
    monkeypatch.setattr(
        experiment.correction,
        "_correction",
        lambda *a: pytest.fail("D10 must not solve"),
    )
    return rig


def run(pipeline: SimpleNamespace) -> dict[str, Any]:
    return experiment._run_targeting(
        pipeline.scenario, REFERENCE, column_references=(DAMPING, RESPONSE)
    )["science"]


def test_schedule_replays_fresh_environments_and_no_selection(
    pipeline: SimpleNamespace,
) -> None:
    s = run(pipeline)
    assert s["outcome"] == "completed", s["reason"]
    assert (
        s["control_attempts"],
        s["propagation_evaluations"],
        s["attempted_arcs"],
        s["completed_arcs"],
    ) == (13, 13, 39, 39)
    assert len({id(env.bodies) for env in pipeline.envs}) == 13
    assert len(pipeline.budgets) == 1 and pipeline.budgets[0].stopped
    for i, h in enumerate((1e-5, 1e-5, 1.0, 1e-5, 1e-5, 1.0)):
        for k, sign in enumerate((1, -1)):
            entry = s["runs"][1 + 2 * i + k]
            assert (entry["column"], entry["sign"], entry["probe_step"]) == (i, sign, h)
            assert entry["controls"] == [
                v + (sign * h if j == i else 0) for j, v in enumerate(pipeline.seed)
            ]
            assert entry["run"]["profile"] == "nominal"
    assert len(s["positive_probe_comparisons"]) == len(s["column_pairs"]) == 6
    assert len(s["column_diagnostics"]["checks"]) == 2
    assert s["selected_alpha"] is s["correction"] is s["improvement"] is None
    assert (
        not s["continuous_safety_verified"] and s["column_unavailable_reason"] is None
    )
    assert s["imported_column_source_sha256"] == pipeline.d9["source_sha256"]
    json.dumps(s, allow_nan=False)


@pytest.mark.parametrize(
    "failure,count",
    [
        ("baseline", 1),
        ("reuse", 1),
        ("deadline", 1),
        *[(f"run-{i}", i + 1) for i in range(13)],
        *[(f"positive-{i}", i + 1) for i in range(1, 13, 2)],
    ],
)
def test_failures_stop_with_only_completed_pairs(
    pipeline: SimpleNamespace, failure: str, count: int
) -> None:
    pipeline.failure = failure
    s = run(pipeline)
    assert s["outcome"] == "aborted" and len(pipeline.calls) == count
    assert (
        s["column_diagnostics"] is None
        and s["column_unavailable_reason"] == s["reason"]
    )
    assert s["automatic_retries"] == 0 and s["selected_alpha"] is None
    assert len(s["column_pairs"]) <= max(0, (count - 2) // 2)
    if failure.startswith("run-"):
        assert not s["runs"][-1]["run"]["boundaries"]
    if failure.startswith("positive-"):
        assert s["runs"][-1]["sign"] == 1
    json.dumps(s, allow_nan=False)


@pytest.mark.parametrize("attempt", [2, 3, 12, 13])
def test_analytic_rejection_counted_before_launch(
    pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, attempt: int
) -> None:
    original = experiment.physical._prepare_burn_controls
    calls = []

    def reject(*args: Any) -> Any:
        calls.append(args)
        return "rejected-control-bounds" if len(calls) == attempt else original(*args)

    monkeypatch.setattr(experiment.physical, "_prepare_burn_controls", reject)
    s = run(pipeline)
    assert s["outcome"] == "aborted" and len(pipeline.calls) == attempt - 1
    assert s["control_attempts"] == attempt and s["runs"][-1]["run"] is None
    assert s["runs"][-1]["column"] == (attempt - 2) // 2


@pytest.mark.parametrize(
    "fault", ["event", "dry", "native", "deadline", "reset", "history-impact"]
)
def test_native_composer_guards_remain(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    rig = _rig(monkeypatch, fault)
    budget = experiment._ColumnBudget(
        rig.report.candidate_id, 300, lambda: rig.clock[0]
    )
    budget.begin_control()
    result = experiment._compose_research_run(
        budget,
        rig.report.scenario,
        rig.environment,
        rig.initial,
        rig.target,
        rig.report.seed_controls,
        tighter=False,
        register_control=False,
    )
    assert result.outcome == "aborted" and not result.boundaries
    with pytest.raises(TrajectoryRefinementError):
        budget.begin_control()


@pytest.mark.parametrize(
    "fault",
    [
        "scenario",
        "candidate",
        "runtime",
        "environment",
        "seed_controls",
        "outcome",
        "direction",
        "jacobian",
        "profile",
        "settings",
        "target",
        "positive-controls",
        "positive-role",
    ],
)
def test_reference_identity_failures(pipeline: SimpleNamespace, fault: str) -> None:
    d9 = deepcopy(pipeline.d9)
    d7 = deepcopy(pipeline.d7)
    s = d9["science"]
    if fault in (
        "scenario",
        "candidate",
        "runtime",
        "environment",
        "seed_controls",
        "outcome",
    ):
        s[fault] = None
    elif fault == "direction":
        s["retained_control_step"][0] += 0.001
    elif fault == "jacobian":
        s["retained_jacobian"][0][0] += 1
    elif fault in ("profile", "settings", "target"):
        key = {
            "profile": "profile",
            "settings": "integrator_settings",
            "target": "target_state",
        }[fault]
        s["runs"][0]["run"][key] = None
    elif fault == "positive-controls":
        d7["science"]["runs"][1]["controls"][0] += 0.001
    else:
        d7["science"]["runs"][1]["role"] = "other"
    with pytest.raises(ValueError):
        experiment._validate_column_reference(d9, d7, pipeline.stored)


@pytest.mark.parametrize("fault", ["runtime", "resource", "seed", "target", "settings"])
def test_preparation_mismatch_before_native(
    pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    if fault == "runtime":
        monkeypatch.setattr(experiment, "_runtime_manifest", lambda *a: {})
    elif fault == "resource":
        monkeypatch.setattr(experiment, "_environment_manifest", lambda *a: {})
    elif fault == "seed":
        monkeypatch.setattr(
            experiment.physical, "_build_initial_burn_controls", lambda *a: (1.0,) * 6
        )
    elif fault == "target":
        original = experiment.physical._build_boundary_states

        def changed(*args: Any) -> Any:
            start, end = original(*args)
            return start, replace(end, position_m=(0.0, 0.0, 0.0))

        monkeypatch.setattr(experiment.physical, "_build_boundary_states", changed)
    else:
        monkeypatch.setattr(
            experiment.physical, "_arc_integrator_profile", lambda *a, **kw: {}
        )
    s = run(pipeline)
    assert s["outcome"] == "aborted" and s["attempted_arcs"] == 0 and not pipeline.calls


def test_closed_seed_does_not_skip_columns(
    pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = experiment.correction._residual
    monkeypatch.setattr(
        experiment.correction, "_residual", lambda v: replace(original(v), closes=True)
    )
    s = run(pipeline)
    assert (
        s["outcome"] == "completed"
        and len(pipeline.calls) == 13
        and s["selected_alpha"] is None
    )


def test_shared_deadline_covers_import(
    pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = experiment._load_column_reference

    def expired(*args: Any) -> Any:
        value = original(*args)
        pipeline.clock[0] = 300
        return value

    monkeypatch.setattr(experiment, "_load_column_reference", expired)
    s = run(pipeline)
    assert s["outcome"] == "aborted" and not pipeline.envs and s["attempted_arcs"] == 0


def test_arithmetic_failure_retains_complete_pairs(
    pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failed(*args: Any) -> Any:
        raise ValueError("nonfinite manufactured arithmetic")

    monkeypatch.setattr(experiment.columns, "_column_diagnostics", failed)
    s = run(pipeline)
    assert (
        s["outcome"] == "aborted"
        and s["completed_arcs"] == 39
        and len(s["column_pairs"]) == 6
    )
    assert s["column_diagnostics"] is None and "column-arithmetic" in s["reason"]


def test_digest_modes_exclusive_finite_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    result = experiment._run_targeting(
        load_scenario(SCENARIO), REFERENCE, column_references=(DAMPING, bad)
    )
    assert (
        result["science"]["attempted_arcs"] == 0
        and "digest" in result["science"]["reason"]
    )
    calls = []
    monkeypatch.setattr(
        experiment, "_run_targeting", lambda *a, **kw: calls.append(kw) or result
    )
    output = tmp_path / "evidence.json"
    argv = [
        str(SCENARIO),
        str(REFERENCE),
        str(output),
        "--column-references",
        str(DAMPING),
        str(bad),
    ]
    assert experiment.main(argv) == 1
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        experiment.main(argv)
    assert (
        calls == [{"column_references": (DAMPING, bad)}]
        and output.read_bytes() == before
    )
    with pytest.raises(SystemExit) as exc:
        experiment.main([*argv, "--response-reference", str(DAMPING)])
    assert exc.value.code == 2


def test_d9_baseline_drift_stops_before_columns(
    pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = experiment._load_column_reference

    def changed(*args: Any) -> Any:
        value = deepcopy(original(*args))
        value["science"]["runs"][0]["run"]["boundaries"][1]["position_m"][0] += 20
        return value

    monkeypatch.setattr(experiment, "_load_column_reference", changed)
    s = run(pipeline)
    assert s["outcome"] == "aborted" and len(pipeline.calls) == 1
    assert "D9 baseline drift" in s["reason"] and not s["column_pairs"]


def test_pair_arithmetic_failure_keeps_only_earlier_pair(
    pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = experiment.columns._column_pair

    def failed(*args: Any) -> Any:
        if args[3] == 1:
            raise ValueError("nonfinite pair")
        return original(*args)

    monkeypatch.setattr(experiment.columns, "_column_pair", failed)
    s = run(pipeline)
    assert s["outcome"] == "aborted" and s["completed_arcs"] == 15
    assert len(s["column_pairs"]) == 1 and s["column_diagnostics"] is None


def test_zero_retained_prediction_stops_before_environment(
    pipeline: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = experiment._load_damping_reference

    def zero(*args: Any) -> Any:
        value = deepcopy(original(*args))
        value["science"]["correction"]["jacobian"] = [[0.0] * 6] * 6
        return value

    monkeypatch.setattr(experiment, "_load_damping_reference", zero)
    s = run(pipeline)
    assert s["outcome"] == "aborted" and "zero-predicted" in s["reason"]
    assert not pipeline.envs and s["attempted_arcs"] == 0
