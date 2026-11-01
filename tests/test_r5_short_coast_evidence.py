"""Frozen JSON and isolated file fixtures; no scientific import/query/propagation."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0145-short-coast-evidence.py"
spec = importlib.util.spec_from_file_location("r5_saved_file_checks", PATH)
assert spec is not None and spec.loader is not None
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


@pytest.mark.parametrize(
    "raw",
    [
        '{"x":1,"x":2}',
        '{"nested":{"x":1,"x":2}}',
        '{"x":NaN}',
        '{"x":Infinity}',
        '{"x":-Infinity}',
        '{"x":1e400}',
        "[]",
        "1",
        "{",
    ],
)
def test_strict_json_rejects_duplicate_nonfinite_and_nonobject(raw: str) -> None:
    with pytest.raises(ValueError):
        evidence.parse(raw)


def test_strict_json_retains_markers_flags_and_does_not_conflate_numbers() -> None:
    assert evidence.parse('{"flag":true,"bad":{"nonfinite":"NaN"}}') == {
        "flag": True,
        "bad": {"nonfinite": "NaN"},
    }
    with pytest.raises(ValueError, match="mismatch"):
        evidence.same({"x": False}, {"x": 0}, "typed input")
    with pytest.raises(ValueError, match="mismatch"):
        evidence.same({"x": 1}, {"x": 1.0}, "typed input")
    evidence.same({"b": 2, "a": 1}, {"a": 1, "b": 2}, "unordered objects")


def test_frozen_inputs_match_the_prepared_loader_without_native_imports() -> None:
    p = ROOT / "docs/adr/experiments/0141-short-coast-inputs.py"
    prior_spec = importlib.util.spec_from_file_location("r5_prior_input_comparison", p)
    assert prior_spec is not None and prior_spec.loader is not None
    prior = importlib.util.module_from_spec(prior_spec)
    prior_spec.loader.exec_module(prior)
    actual = evidence.load_inputs()
    # Only the wire format is compared; no old validator is called by new code.
    assert evidence.canonical(actual) == evidence.canonical(prior.load_inputs())
    assert actual["epoch_tdb_s"] == 978995455.2304223
    assert actual["final_epoch_tdb_s"] == 978995755.2304223
    assert len(actual["original_kernel_manifest"]["kernels"]) == 13


def test_frozen_input_byte_change_stops_before_interpretation(
    tmp_path: Path, monkeypatch: Any
) -> None:
    for name in evidence.INPUT_SHA:
        (tmp_path / name).write_bytes((evidence.HERE / name).read_bytes())
    path = tmp_path / "0119-m2-reference.json"
    path.write_bytes(path.read_bytes() + b" ")
    monkeypatch.setattr(evidence, "HERE", tmp_path)
    with pytest.raises(ValueError, match="frozen input identity"):
        evidence.load_inputs()


def test_import_and_input_loading_are_stdlib_only_in_fresh_process() -> None:
    code = f"import runpy,sys;m=runpy.run_path({str(PATH)!r});m['load_inputs']();assert not any(k.startswith(('numpy','scipy','spiceypy','tudatpy','space_nav','r5_runner')) for k in sys.modules)"
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
    assert not hasattr(evidence, "execute") and not hasattr(evidence, "audit_file")


def test_digest_checks_deadline_between_chunks_and_before_io(tmp_path: Path) -> None:
    path = tmp_path / "data"
    path.write_bytes(b"x" * (2 * 1024 * 1024 + 3))
    calls = []

    def check() -> None:
        calls.append(None)
        if len(calls) == 3:
            raise RuntimeError("deadline")

    with pytest.raises(RuntimeError, match="deadline"):
        evidence.digest(path, check)
    assert len(calls) == 3
    assert evidence.digest(path) == sha256(path.read_bytes()).hexdigest()

    def expired() -> None:
        raise RuntimeError("already expired")

    with pytest.raises(RuntimeError, match="already expired"):
        evidence.read_json(tmp_path / "does-not-exist", expired)


@pytest.fixture
def identity_fixture(
    tmp_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    checkout, prefix = tmp_path / "checkout", tmp_path / "conda"
    for name in evidence.required_sources(ROOT):
        target = checkout / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    module_dir = prefix / "lib/python3.12/site-packages"
    module_dir.mkdir(parents=True)

    def record_file(path: Path) -> dict[str, str]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("unexecuted fixture: " + str(path))
        return {"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest()}

    modules = {
        name: record_file(module_dir / name.replace(".", "/") / "__init__.py")
        for name in evidence.MODULES
    }
    tudat_init = record_file(module_dir / "tudatpy/__init__.py")
    binary = record_file(module_dir / "tudatpy/kernel.fixture.so")
    builds = {}
    for name in ("tudatpy", "tudat-resources", "numpy", "scipy", "spiceypy"):
        record = {"name": name, "version": evidence.VERSIONS[name], "build": "fixture"}
        path = prefix / "conda-meta" / f"{name}-{record['version']}-fixture.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record))
        builds[name] = {
            "metadata_path": str(path),
            "metadata_sha256": evidence.digest(path),
            "record": record,
        }
    kernels = evidence.load_inputs()["original_kernel_manifest"]
    snapshot = {
        "versions": dict(evidence.VERSIONS),
        "revision": "a" * 40,
        "dirty": [],
        "imports": {
            "space_nav": str(checkout / "src/space_nav/__init__.py"),
            "tudatpy": tudat_init["path"],
        },
        "native_binary": binary,
        "conda_build": builds["tudatpy"]["record"],
        "resource_build": builds["tudat-resources"]["record"],
        "conda_metadata_sha256": builds["tudatpy"]["metadata_sha256"],
        "resource_metadata_sha256": builds["tudat-resources"]["metadata_sha256"],
        "source_sha256": {
            p: evidence.digest(checkout / p)
            for p in evidence.required_sources(checkout)
        },
        "kernels": deepcopy(kernels),
        "r5_runtime": {
            "modules": modules,
            "builds": {
                k: v for k, v in builds.items() if k in ("numpy", "scipy", "spiceypy")
            },
            "coefficients": {
                k: {"shape": list(shape), "dtype": "float64", "sha256": "b" * 64}
                for k, shape in evidence.SHAPES.items()
            },
            "callables": {
                k: {
                    "module": module,
                    "qualname": qualified,
                    "source_path": modules[module]["path"],
                    "source_sha256": modules[module]["sha256"],
                    "code_sha256": "c" * 64,
                }
                for k, (module, qualified) in evidence.CALLABLES.items()
            },
        },
    }
    return snapshot, kernels, checkout, prefix


def verify(
    fixture: tuple[dict[str, Any], dict[str, Any], Path, Path],
) -> dict[str, Any]:
    snapshot, kernels, checkout, prefix = fixture
    return evidence.verify_snapshot(snapshot, kernels, checkout=checkout, prefix=prefix)


def test_full_file_fixture_checks_bytes_but_never_claims_historical_memory_or_reference(
    identity_fixture: tuple[dict[str, Any], dict[str, Any], Path, Path],
) -> None:
    result = verify(identity_fixture)
    assert result["current_source_files_checked"] == len(
        evidence.required_sources(ROOT)
    )
    assert result["current_module_files_checked"] == 9
    assert result["current_conda_records_checked"] == 5
    assert not result["historical_loaded_memory_verified"]
    assert not result["reference_study_verified"]
    assert "no current kernel-byte/pool read" in result["kernel_scope"]


@pytest.mark.parametrize(
    "fault",
    [
        "version",
        "missing_source",
        "extra_source",
        "source_bytes",
        "prepared_pin",
        "native_bytes",
        "outside_prefix",
        "symlink",
        "module_bytes",
        "module_inventory",
        "conda_bytes",
        "build_name",
        "metadata_path",
        "coefficient_shape",
        "coefficient_hash",
        "callable_role",
        "callable_source",
        "kernel_order",
        "kernel_count",
        "missing_field",
        "revision",
        "dirty",
        "import_path",
    ],
)
def test_identity_and_current_file_corruption_is_rejected(
    identity_fixture: tuple[dict[str, Any], dict[str, Any], Path, Path], fault: str
) -> None:
    s, kernels, checkout, prefix = identity_fixture
    runtime = s["r5_runtime"]
    if fault == "version":
        s["versions"]["scipy"] = "1.17.0"
    elif fault == "missing_source":
        s["source_sha256"].pop("environment.yml")
    elif fault == "extra_source":
        s["source_sha256"]["../outside"] = "b" * 64
    elif fault == "source_bytes":
        (checkout / "src/space_nav/__init__.py").write_text("changed")
    elif fault == "prepared_pin":
        p = checkout / "docs/adr/experiments/0142-short-coast-runner.py"
        p.write_text("changed")
        s["source_sha256"][str(p.relative_to(checkout))] = evidence.digest(p)
    elif fault == "native_bytes":
        Path(s["native_binary"]["path"]).write_text("changed")
    elif fault in ("outside_prefix", "symlink"):
        outside = prefix.parent / "outside"
        outside.write_text("unexecuted")
        p = outside
        if fault == "symlink":
            p = prefix / "alias"
            p.symlink_to(outside)
        s["native_binary"] = {"path": str(p), "sha256": evidence.digest(outside)}
    elif fault == "module_bytes":
        Path(runtime["modules"]["numpy"]["path"]).write_text("changed")
    elif fault == "module_inventory":
        runtime["modules"].pop("numpy")
    elif fault == "conda_bytes":
        Path(runtime["builds"]["numpy"]["metadata_path"]).write_text("{}")
    elif fault == "build_name":
        runtime["builds"]["numpy"]["record"]["name"] = "scipy"
    elif fault == "metadata_path":
        runtime["builds"]["numpy"]["metadata_path"] = runtime["builds"]["scipy"][
            "metadata_path"
        ]
    elif fault == "coefficient_shape":
        runtime["coefficients"]["A"]["shape"] = [15, 16]
    elif fault == "coefficient_hash":
        runtime["coefficients"]["A"]["sha256"] = "not-a-digest"
    elif fault == "callable_role":
        runtime["callables"]["DOP853_step"]["qualname"] = "DOP853._step_impl"
    elif fault == "callable_source":
        value = runtime["modules"]["numpy"]
        runtime["callables"]["rk_step"].update(
            source_path=value["path"], source_sha256=value["sha256"]
        )
    elif fault == "kernel_order":
        s["kernels"]["kernels"].reverse()
    elif fault == "kernel_count":
        s["kernels"]["loaded_kernel_count"] = 12
    elif fault == "missing_field":
        s.pop("dirty")
    elif fault == "revision":
        s["revision"] = "unknown"
    elif fault == "dirty":
        s["dirty"] = [False]
    else:
        s["imports"]["space_nav"] = str(prefix / "other.py")
    with pytest.raises(ValueError):
        verify(identity_fixture)


def test_snapshot_comparison_detects_only_in_memory_digest_drift(
    identity_fixture: tuple[dict[str, Any], dict[str, Any], Path, Path],
) -> None:
    snapshot = identity_fixture[0]
    after = deepcopy(snapshot)
    evidence.same(snapshot, after, "snapshot")
    after["r5_runtime"]["coefficients"]["A"]["sha256"] = "d" * 64
    with pytest.raises(ValueError, match="snapshot mismatch"):
        evidence.same(snapshot, after, "snapshot")
