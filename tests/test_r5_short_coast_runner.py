"""Injected orchestration fixtures only; no R5 scientific execution."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0142-short-coast-runner.py"
spec = importlib.util.spec_from_file_location("r5_coordinator_tests", PATH)
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


class Clock:
    value: float = 0.0

    def __call__(self) -> float:
        return self.value


class Fixtures:
    def __init__(self) -> None:
        self.clock = Clock()
        self.calls: list[tuple[str, str, bool]] = []
        self.manifest = {
            "loaded_kernel_count": 13,
            "kernel_list_status": "complete",
            "kernels": ["injected"],
        }
        self.bundle = {
            "state_si": (1e9, 0.0, 0.0, 0.0, 0.0, 0.0),
            "epoch_tdb_s": 0.0,
            "nodes_tdb_s": tuple(50.0 * j for j in range(7)),
            "original_kernel_manifest": self.manifest,
            "synthetic": True,
        }
        self.identities = 0

    def loader(self, check: Any) -> dict[str, Any]:
        check()
        return deepcopy(self.bundle)

    def identity(self, check: Any) -> dict[str, Any]:
        check()
        self.identities += 1
        return {"kernels": deepcopy(self.manifest), "test": "synthetic"}

    def body(self, body: str, epoch: float) -> dict[str, Any]:
        positions = {
            "Sun": (0.0, 0.0, 0.0),
            "Moon": (2e9, 0.0, 0.0),
            "Earth": (3e9, 0.0, 0.0),
        }
        return {
            "body": body,
            "epoch_tdb_s": epoch,
            "origin": "SSB",
            "orientation": "J2000",
            "aberration_correction": "NONE",
            "position_m": positions[body],
            "velocity_m_s": (0.0,) * 3,
        }

    def points(self, model: str) -> list[dict[str, Any]]:
        return [
            {
                "epoch_tdb_s": 50.0 * j,
                "state": (
                    1e9 + (100.0 * j / 6 if model == "B" else 0.0),
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ),
            }
            for j in range(7)
        ]

    def native(
        self, initial: object, epoch: float, model: str, tight: bool, c: Any
    ) -> dict[str, Any]:
        self.calls.append((model, "native", tight))
        c.arcs_attempted += 1
        c.arcs_returned += 1
        c.arcs_completed += 1
        c.last_returned = {
            "state_history": {"synthetic": [[1.0, 2.0, 3.0]]},
            "integration_completed": True,
        }
        return {
            "model": model,
            "origin": "SSB",
            "orientation": "J2000",
            "position_units": "m",
            "velocity_units": "m/s",
            "time_units": "TDB seconds since J2000",
            "step_s": 0.5 if tight else 1.0,
            "retained_states": 601 if tight else 301,
            "guarded_states": 601 if tight else 301,
            "gravity_parameters_m3_s2": dict(runner.oracle.GM),
            "force_order": ("total",) + runner.oracle.included(model),
            "samples": self.points(model),
        }

    def oracle(
        self,
        initial: object,
        epoch: float,
        model: str,
        tight: bool,
        c: Any,
        provider: Any,
    ) -> dict[str, Any]:
        self.calls.append((model, "oracle", tight))
        before = c.counts()
        c.rhs_attempted += 1
        c.rhs_completed += 1
        c.states_attempted += 3
        c.states_completed += 3
        return {
            "model": model,
            "tighter": tight,
            "nfev": 1,
            "counts_before": before,
            "counts_after": c.counts(),
            "samples": self.points(model),
        }

    def invoke(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        stream = kwargs.pop("stream", io.StringIO())
        options = {
            "clock": self.clock,
            "loader": self.loader,
            "identity_provider": self.identity,
            "native_solver": self.native,
            "oracle_solver": self.oracle,
            "provider": self.body,
        } | kwargs
        result = runner.run(stream, **options)
        return result, json.loads(stream.getvalue())


def test_import_is_lazy_and_cannot_launch_on_import() -> None:
    code = f"import runpy,sys;runpy.run_path({str(PATH)!r});assert not any(k.startswith(('numpy','scipy','spiceypy','tudatpy','space_nav')) for k in sys.modules)"
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)


def test_complete_order_counts_signed_differences_and_finite_evidence() -> None:
    f = Fixtures()
    r, saved = f.invoke()
    assert (
        r == saved and r["status"] == "passed" and r["adapter_mode"] == "injected-test"
    )
    assert f.calls == [
        (m, e, t)
        for m in ("A", "B")
        for e, t in [
            ("native", False),
            ("native", True),
            ("oracle", False),
            ("oracle", True),
        ]
    ]
    assert f.identities == 2
    assert len(r["body_table"]) == 7 and all(
        len(p["states"]) == 3 for p in r["body_table"]
    )
    assert r["counts"]["native_arcs_completed"] == 4
    assert r["counts"]["oracle"]["states_attempted"] == 33
    assert all(len(b["node_forces"]) == 28 for b in r["models"].values())
    assert r["signed_model_differences"][-1]["native_B_minus_A"][
        "right_minus_left_si"
    ] == [100.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    assert (
        r["signed_model_differences"][-1]["oracle_minus_native_sensitivity"][
            "position_norm_m"
        ]
        == 0.0
    )
    assert (
        r["finalization_gate"] == "passed" and r["mission_accuracy_verified"] is False
    )


@pytest.mark.parametrize(
    "gate,tag,amount",
    [
        ("native_profile", "native", 1.0),
        ("native_oracle", "oracle", 1.0),
        ("oracle_profile", "oracle", 0.002),
    ],
)
def test_first_A_numerical_failure_prevents_B(
    gate: str, tag: str, amount: float
) -> None:
    f = Fixtures()
    original = getattr(f, tag)

    def corrupt(*args: Any) -> dict[str, Any]:
        r = original(*args)
        if (
            (gate == "native_profile" and args[3])
            or (gate == "native_oracle" and args[3])
            or (gate == "oracle_profile" and not args[3])
        ):
            r["samples"][1]["state"] = tuple(
                v + amount if j == 0 else v
                for j, v in enumerate(r["samples"][1]["state"])
            )
        return r

    r, _ = f.invoke(**{tag + "_solver": corrupt})
    assert r["status"] == "failed" and set(r["models"]) == {"A"}
    assert r["models"]["A"]["numerical_comparison"][-1]["gates"][gate] is False
    assert len(f.calls) == 4 and f.identities == 1
    assert r["interpretation"].startswith("unavailable")


@pytest.mark.parametrize(
    "bad",
    [
        "epoch",
        "initial",
        "shape",
        "nonfinite",
        "model",
        "step",
        "GM",
        "coverage",
        "force_order",
        "labels",
        "boolean_step",
    ],
)
def test_malformed_native_return_stops_and_is_retained(bad: str) -> None:
    f = Fixtures()

    def corrupt(*args: Any) -> dict[str, Any]:
        r = f.native(*args)
        if bad == "epoch":
            r["samples"][1]["epoch_tdb_s"] += 1.0
        if bad == "initial":
            r["samples"][0]["state"] = (0.0,) * 6
        if bad == "shape":
            r["samples"].pop()
        if bad == "nonfinite":
            r["samples"][1]["state"] = (math.nan,) * 6
        if bad == "model":
            r["model"] = "B"
        if bad == "labels":
            r["origin"] = "Sun"
        if bad == "boolean_step":
            r["step_s"] = True
        if bad == "step":
            r["step_s"] = 0.1
        if bad == "GM":
            r["gravity_parameters_m3_s2"]["Moon"] += 1.0
        if bad == "coverage":
            r["guarded_states"] = 0
        if bad == "force_order":
            r["force_order"] = ("total", "Earth")
        return r

    r, saved = f.invoke(native_solver=corrupt)
    assert r == saved and r["status"] == "failed" and len(f.calls) == 1
    assert "result" in r["models"]["A"]["profiles"]["native-normal"]
    assert r["partial_raw"]["native"]["state_history"] == {
        "synthetic": [[1.0, 2.0, 3.0]]
    }
    if bad == "nonfinite":
        assert r["models"]["A"]["profiles"]["native-normal"]["result"]["samples"][1][
            "state"
        ][0] == {"nonfinite": "nan"}


@pytest.mark.parametrize("bad", ["profile", "nfev", "counts"])
def test_oracle_profile_and_counts_are_verified(bad: str) -> None:
    f = Fixtures()

    def corrupt(*args: Any) -> dict[str, Any]:
        r = f.oracle(*args)
        if bad == "profile":
            r["tighter"] = not r["tighter"]
        if bad == "nfev":
            r["nfev"] = 2
        if bad == "counts":
            r["counts_after"]["rhs_completed"] = 99
        return r

    r, _ = f.invoke(oracle_solver=corrupt)
    assert r["status"] == "failed" and len(f.calls) == 3 and set(r["models"]) == {"A"}


def test_provider_error_never_starts_an_arc() -> None:
    f = Fixtures()

    def fail(*args: object) -> Any:
        raise runner.oracle.OracleUnavailable("missing kernel")

    r, _ = f.invoke(provider=fail)
    assert r["status"] == "failed" and f.calls == []
    assert (
        r["counts"]["oracle"]["states_attempted"] == 1
        and r["counts"]["oracle"]["states_completed"] == 0
    )


def test_provider_after_return_deadline_preserves_raw() -> None:
    f = Fixtures()

    def late(*args: Any) -> Any:
        r = f.body(*args)
        f.clock.value = 61.0
        return r

    r, _ = f.invoke(provider=late)
    assert r["status"] == "failed" and f.calls == []
    assert r["partial_raw"]["oracle_body"]["body"] == "Sun"
    assert r["counts"]["oracle"]["states_completed"] == 1
    assert (
        r["finalization_gate"] == "failed" and r["actual_elapsed_after_flush_s"] == 61.0
    )


def test_native_exception_attempt_is_not_retried() -> None:
    f = Fixtures()

    def fail(initial: object, epoch: float, model: str, tight: bool, c: Any) -> Any:
        c.arcs_attempted += 1
        raise runner.native.NativeError("native failure")

    r, _ = f.invoke(native_solver=fail)
    assert r["status"] == "failed" and r["counts"]["native_arcs_attempted"] == 1
    assert (
        r["counts"]["native_arcs_returned"] == 0
        and r.get("oracle_solves_attempted", 0) == 0
    )


def test_returned_native_output_survives_budget_failure() -> None:
    f = Fixtures()

    def late(*args: Any) -> Any:
        r = f.native(*args)
        f.clock.value = 61.0
        return r

    r, _ = f.invoke(native_solver=late)
    assert r["status"] == "failed" and len(f.calls) == 1
    assert "result" in r["models"]["A"]["profiles"]["native-normal"]
    assert r["partial_raw"]["native"]["integration_completed"] is True


def test_original_and_final_identity_drift_stop() -> None:
    f = Fixtures()

    def drift(check: Any) -> Any:
        r = f.identity(check)
        if f.identities == 2:
            r["changed"] = True
        return r

    r, _ = f.invoke(identity_provider=drift)
    assert (
        r["status"] == "failed"
        and len(f.calls) == 8
        and "identity drift" in r["error"]["message"]
    )
    assert "final_identity" in r
    f = Fixtures()

    def wrong_manifest(check: Any) -> Any:
        r = f.identity(check)
        r["kernels"]["kernels"] = ["different"]
        return r

    r, _ = f.invoke(identity_provider=wrong_manifest)
    assert r["status"] == "failed" and f.calls == [] and r["body_table"] == []


def test_serialization_and_flush_are_inside_budget() -> None:
    f = Fixtures()

    class Stream(io.StringIO):
        def flush(self) -> None:
            f.clock.value = 61.0

    r, saved = f.invoke(stream=Stream())
    assert r == saved and r["status"] == "failed" and r["finalization_gate"] == "failed"
    assert r["error"]["stage"] == "evidence flush" and len(f.calls) == 8


def test_clock_backtracking_stops_without_science() -> None:
    f = Fixtures()

    def loader(check: Any) -> Any:
        result = f.loader(check)
        f.clock.value = -1.0
        return result

    r, _ = f.invoke(loader=loader)
    assert r["status"] == "failed" and f.calls == []


def test_signed_vector_comparison_uses_vectors_not_only_norms() -> None:
    a = runner.difference((0.0,) * 6, (1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    b = runner.difference((0.0,) * 6, (-1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    assert a["position_norm_m"] == b["position_norm_m"] == 1.0
    delta = runner.difference(a["right_minus_left_si"], b["right_minus_left_si"])
    assert delta["right_minus_left_si"][0] == -2.0
    assert not runner.within(delta, 0.02, 2e-5)
    assert runner.within(
        {"position_norm_m": 0.02, "velocity_norm_m_s": 2e-5}, 0.02, 2e-5
    )


def test_execute_requires_fresh_process_without_creating_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "sys", SimpleNamespace(modules={"numpy": object()}))
    path = tmp_path / "new.json"
    with pytest.raises(runner.common.GateFailure, match="fresh process"):
        runner.execute(path)
    assert not path.exists()


def test_exclusive_output_preserves_existing_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "sys", SimpleNamespace(modules={}))
    path = tmp_path / "existing.json"
    path.write_text("immutable")
    with pytest.raises(FileExistsError):
        runner.execute(path)
    assert path.read_text() == "immutable"


def test_execute_passes_process_start_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "sys", SimpleNamespace(modules={}))

    def fake(stream: Any, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["start_s"] == runner.PROCESS_START
        stream.write("{}")
        return {"injected": True}

    monkeypatch.setattr(runner, "run", fake)
    assert runner.execute(tmp_path / "new.json") == {"injected": True}


def test_returned_oracle_arrays_survive_adapter_validation_failure() -> None:
    f = Fixtures()
    raw = {"success": True, "corrections": [[0.0] * 6], "offsets_s": [0.0], "nfev": 1}

    def fail(*args: Any) -> Any:
        f.oracle(*args)
        raise runner.oracle.ReturnedOracleFailure("after solve deadline", raw)

    r, _ = f.invoke(oracle_solver=fail)
    assert r["status"] == "failed" and len(f.calls) == 3
    assert r["failed_solver_returned"] == raw
    assert (
        r["oracle_solves_attempted"] == 1 and r.get("oracle_solves_completed", 0) == 0
    )


def test_first_error_survives_failed_finalization() -> None:
    f = Fixtures()

    def late(*args: Any) -> Any:
        r = f.native(*args)
        f.clock.value = 61.0
        return r

    r, _ = f.invoke(native_solver=late)
    assert r["first_error"]["stage"] == "A native normal"
    assert r["error"]["stage"] == "evidence flush"


def test_reused_mutable_identity_cannot_hide_drift() -> None:
    f = Fixtures()
    shared = {"kernels": deepcopy(f.manifest), "serial": 0}

    def identity(check: Any) -> Any:
        shared["serial"] += 1
        return shared

    r, _ = f.invoke(identity_provider=identity)
    assert r["status"] == "failed" and "identity drift" in r["error"]["message"]
    assert r["identity"]["serial"] == 1 and r["final_identity"]["serial"] == 2


def test_budget_includes_pre_import_baseline() -> None:
    f = Fixtures()
    f.clock.value = 61.0
    r, _ = f.invoke(start_s=0.0)
    assert r["status"] == "failed" and f.calls == [] and "inputs" not in r


def test_prepared_adapter_hash_drift_stops_before_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    f = Fixtures()
    bad = dict(runner.SOURCE_SHA)
    bad["0140-short-coast-native.py"] = "0" * 64
    monkeypatch.setattr(runner, "SOURCE_SHA", bad)
    r, _ = f.invoke()
    assert r["status"] == "failed" and f.calls == [] and f.identities == 0


def test_lost_oracle_query_count_is_not_accepted() -> None:
    f = Fixtures()

    def corrupt(*args: Any) -> Any:
        r = f.oracle(*args)
        args[4].states_attempted -= 1
        args[4].states_completed -= 1
        r["counts_after"] = args[4].counts()
        return r

    r, _ = f.invoke(oracle_solver=corrupt)
    assert r["status"] == "failed" and r["error"]["stage"] == "final counts"


def test_write_failure_is_reported_to_caller() -> None:
    f = Fixtures()

    class Broken(io.StringIO):
        def write(self, value: str) -> int:
            raise OSError("disk unavailable")

    with pytest.raises(OSError, match="disk unavailable"):
        f.invoke(stream=Broken())
