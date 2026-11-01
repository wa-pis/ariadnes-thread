"""R5 input/identity preparation: no spacecraft propagation or body-state queries."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0141-short-coast-inputs.py"
spec = importlib.util.spec_from_file_location("r5_input_test_adapter", PATH)
assert spec is not None and spec.loader is not None
inputs = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = inputs
spec.loader.exec_module(inputs)


def records() -> dict[str, Any]:
    return {
        name: json.loads((inputs.HERE / name).read_text()) for name in inputs.INPUT_SHA
    }


def lightweight_identity() -> dict[str, Any]:
    return {
        "versions": {"numpy": "1.26.4", "scipy": "1.17.1", "spiceypy": "8.2.0"},
        "source_sha256": {},
    }


def test_load_exact_inputs_without_scientific_imports() -> None:
    code = f"import runpy,sys; m=runpy.run_path({str(PATH)!r}); r=m['load_inputs'](); assert r['candidate']['candidate_id']=='d0001-t0035'; assert not any(k.startswith(('numpy','scipy','spiceypy','tudatpy','space_nav')) for k in sys.modules)"
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
    result = inputs.load_inputs()
    expected = records()["0098-central-correction-study.json"]["science"]["runs"][0][
        "run"
    ]["boundaries"][0]
    assert result["initial"] == expected
    assert result["state_si"] == tuple(
        expected["position_m"] + expected["velocity_m_s"]
    )
    assert result["nodes_tdb_s"] == tuple(978995455.2304223 + 50 * j for j in range(7))
    assert result["final_epoch_tdb_s"] == 978995755.2304223
    assert result["original_kernel_manifest"]["loaded_kernel_count"] == 13


@pytest.mark.parametrize(
    "corruption",
    [
        "records",
        "scenario",
        "candidate",
        "status",
        "finalization",
        "audit_sha",
        "label",
        "origin",
        "orientation",
        "epoch",
        "utc",
        "position",
        "velocity",
        "boolean",
    ],
)
def test_input_contract_rejects_drift(corruption: str) -> None:
    data = records()
    physical = data["0098-central-correction-study.json"]["science"]
    initial = physical["runs"][0]["run"]["boundaries"][0]
    if corruption == "records":
        data.pop("0133-gravity-screen.json")
    if corruption == "scenario":
        physical["scenario"]["limits"]["seed"] = 43
    if corruption == "candidate":
        physical["candidate"]["candidate_id"] = "changed"
    if corruption == "status":
        data["0133-gravity-screen.json"]["status"] = "failed"
    if corruption == "finalization":
        data["0136-retained-boundary-audit.json"]["finalization_gate"] = "failed"
    if corruption == "audit_sha":
        data["0136-retained-boundary-audit.json"]["input_sha256"] = {}
    if corruption in ("label", "origin", "orientation"):
        initial[corruption] = "wrong"
    if corruption == "epoch":
        initial["epoch_tdb_s"] += 1.0
    if corruption == "utc":
        initial["epoch_utc"] = "wrong"
    if corruption == "position":
        initial["position_m"][0] += 1.0
    if corruption == "velocity":
        initial["velocity_m_s"][0] += 1.0
    if corruption == "boolean":
        initial["position_m"][0] = True
    with pytest.raises(inputs.common.GateFailure):
        inputs.validate_inputs(data)


@pytest.mark.parametrize("name", tuple(inputs.INPUT_SHA))
def test_hash_binding_precedes_record_parsing(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = dict(inputs.INPUT_SHA)
    bad[name] = "0" * 64
    monkeypatch.setattr(inputs, "INPUT_SHA", bad)
    with pytest.raises(inputs.common.GateFailure, match="frozen R5 input identity"):
        inputs.load_inputs()


@pytest.mark.parametrize("name", tuple(inputs.PREPARED_SHA))
def test_prepared_source_drift_before_native_import(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = dict(inputs.PREPARED_SHA)
    bad[name] = "0" * 64
    monkeypatch.setattr(inputs, "PREPARED_SHA", bad)
    with pytest.raises(inputs.common.GateFailure, match="prepared source identity"):
        inputs.load_inputs()


def test_input_deadline_checked_before_reads() -> None:
    def fail() -> None:
        raise RuntimeError("deadline")

    with pytest.raises(RuntimeError, match="deadline"):
        inputs.load_inputs(fail)


def test_actual_runtime_identity_is_stable_and_extended() -> None:
    before = inputs.runtime_identity()
    after = inputs.runtime_identity()
    assert before == after
    inputs.common.check_inventory(
        before["kernels"], inputs.load_inputs()["original_kernel_manifest"]
    )
    assert before["kernels"]["loaded_kernel_count"] == 13
    assert before["versions"]["scipy"] == "1.17.1"
    extension = before["r5_runtime"]
    assert extension["modules"]["numpy.core._multiarray_umath"]["path"].endswith(".so")
    assert extension["modules"]["scipy.integrate._ivp.dop853_coefficients"][
        "path"
    ].endswith(".py")
    assert extension["coefficients"]["A"]["shape"] == [16, 16]
    assert extension["coefficients"]["C"]["shape"] == [16]
    assert set(extension["builds"]) == {"numpy", "scipy", "spiceypy"}
    assert len(extension["callables"]["solve_ivp"]["code_sha256"]) == 64
    for name in [
        "docs/adr/experiments/0141-short-coast-inputs.py",
        "docs/adr/experiments/0140-short-coast-native.py",
        "docs/adr/experiments/0138-short-coast-oracle.py",
        "tests/test_r5_short_coast_inputs.py",
    ]:
        assert before["source_sha256"][name] == inputs.common.digest(ROOT / name)


@pytest.mark.parametrize("name", ["numpy", "scipy", "spiceypy"])
def test_actual_module_version_mismatch(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = inputs.import_module(name)
    monkeypatch.setattr(module, "__version__", "wrong")
    with pytest.raises(inputs.common.GateFailure, match="actual runtime version"):
        inputs.module_identity(name, "expected")


def test_shadow_import_location_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(
        inputs, "import_module", lambda _: SimpleNamespace(__file__=str(PATH))
    )
    with pytest.raises(inputs.common.GateFailure, match="outside prefix"):
        inputs.module_identity("numpy")


@pytest.mark.parametrize(
    "corruption",
    [
        "alias",
        "registry",
        "class_A",
        "class_C",
        "extra_A",
        "extra_C",
        "n_stages",
        "order",
        "coefficient_shape",
        "coeff_nonfinite",
        "coeff_dtype",
        "build_version",
    ],
)
def test_solver_or_build_drift_rejected(
    corruption: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import numpy as np
    from scipy import integrate
    from scipy.integrate._ivp import ivp, rk, dop853_coefficients as coeff

    monkeypatch.setattr(inputs.common, "runtime_identity", lightweight_identity)
    if corruption == "alias":
        monkeypatch.setattr(integrate, "solve_ivp", lambda *args: None)
    if corruption == "registry":
        monkeypatch.setitem(ivp.METHODS, "DOP853", object())
    if corruption == "class_A":
        monkeypatch.setattr(rk.DOP853, "A", np.zeros_like(rk.DOP853.A))
    if corruption == "class_C":
        monkeypatch.setattr(rk.DOP853, "C", np.zeros_like(rk.DOP853.C))
    if corruption == "extra_A":
        monkeypatch.setattr(rk.DOP853, "A_EXTRA", np.zeros_like(rk.DOP853.A_EXTRA))
    if corruption == "extra_C":
        monkeypatch.setattr(rk.DOP853, "C_EXTRA", np.zeros_like(rk.DOP853.C_EXTRA))
    if corruption == "order":
        monkeypatch.setattr(rk.DOP853, "order", 7)
    if corruption == "coefficient_shape":
        monkeypatch.setattr(coeff, "A", np.zeros((9, 9)))
    if corruption == "n_stages":
        monkeypatch.setattr(rk.DOP853, "n_stages", 11)
    if corruption == "coeff_nonfinite":
        monkeypatch.setattr(coeff, "D", np.full_like(coeff.D, np.nan))
    if corruption == "coeff_dtype":
        monkeypatch.setattr(coeff, "D", coeff.D.astype("float32"))
    if corruption == "build_version":
        old = inputs.common.conda_metadata

        def mismatch(name: str) -> Any:
            path, record = old(name)
            return path, dict(record, version="wrong")

        monkeypatch.setattr(inputs.common, "conda_metadata", mismatch)
    with pytest.raises(inputs.common.GateFailure):
        inputs.runtime_identity()


def test_live_coefficient_change_changes_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scipy.integrate._ivp import rk, dop853_coefficients as coeff

    monkeypatch.setattr(inputs.common, "runtime_identity", lightweight_identity)
    before = inputs.runtime_identity()
    changed = coeff.D.copy()
    changed[0, 0] += 1e-8
    monkeypatch.setattr(coeff, "D", changed)
    monkeypatch.setattr(rk.DOP853, "D", changed)
    after = inputs.runtime_identity()
    assert (
        before["r5_runtime"]["coefficients"]["D"]
        != after["r5_runtime"]["coefficients"]["D"]
    )


def test_callable_code_is_recorded_and_outside_prefix_rejected() -> None:
    from scipy.integrate import solve_ivp

    identity = inputs.callable_identity(solve_ivp)
    assert identity["qualname"] == "solve_ivp"
    with pytest.raises(inputs.common.GateFailure, match="code outside prefix"):
        inputs.callable_identity(lightweight_identity)


def test_extra_source_and_outside_checkout_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(inputs.common, "runtime_identity", lightweight_identity)
    identity = inputs.runtime_identity(extra_sources=(ROOT / "AGENTS.md",))
    assert identity["source_sha256"]["AGENTS.md"] == inputs.common.digest(
        ROOT / "AGENTS.md"
    )
    with pytest.raises(inputs.common.GateFailure, match="outside checkout"):
        inputs.runtime_identity(extra_sources=(Path(sys.executable),))


def test_identity_deadline_stops_before_native_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden() -> Any:
        pytest.fail("native identity should not run after deadline")

    monkeypatch.setattr(inputs.common, "runtime_identity", forbidden)

    def fail() -> None:
        raise RuntimeError("deadline")

    with pytest.raises(RuntimeError, match="deadline"):
        inputs.runtime_identity(fail)
