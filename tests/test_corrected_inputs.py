"""ADR0162 metadata/hash boundaries; no new states, fields or native work."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/adr/experiments"
PATH = HERE / "0163-corrected-inputs.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("corrected_inputs_test", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


inputs = load()


@pytest.fixture(scope="module")
def records() -> tuple[dict[str, Any], ...]:
    return tuple(json.loads((HERE / name).read_text()) for name in inputs.INPUT_SHA)


def validate(records: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    return inputs.validate_bundle(*records)


def test_metadata_loader_matches_frozen_contract() -> None:
    bundle = inputs.load_inputs()
    assert bundle["offsets_s"] == [0., 50., 100., 150., 200., 250., 300.]
    assert len(bundle["protected_sha256"]) == 381
    assert bundle["input_sha256"] == inputs.INPUT_SHA
    assert bundle["initial"] == {
        "epoch_tdb_s": 978995455.2304223,
        "position_m": inputs.POSITION_M, "velocity_m_s": inputs.VELOCITY_M_S}
    assert bundle["gm_m3_s2"]["Moon"] == 4902800121846.8
    assert bundle["radii_m"] == inputs.RADII_M
    assert len(bundle["native_samples"]["normal"]) == 7
    assert len(bundle["native_samples"]["tighter"]) == 7
    assert bundle["native_samples"]["normal"][0] == inputs.POSITION_M + inputs.VELOCITY_M_S
    assert bundle["historical_final_identity_available"] is False
    assert bundle["source_provenance"]["historical_loaded_memory_verified"] is False
    assert bundle["identity"]["current_kernel_pool_queried"] is False
    assert bundle["kernel_manifest"]["loaded_kernel_count"] == 13
    assert bundle["historical_identity"]["kernels"] == bundle["kernel_manifest"]
    for body, row in bundle["source_rows_template"].items():
        assert set(row) == {"body", "segments"} and row["body"] == body
        assert "assessment" not in row and "state_si" not in row
    assert bundle["retained_guard_metadata"]["normal"]["guarded_states"] == 301
    assert bundle["retained_guard_metadata"]["tighter"]["guarded_states"] == 601


def test_outputs_do_not_mutate_retained_inputs(records: tuple[dict[str, Any], ...]) -> None:
    original = deepcopy(records)
    bundle = validate(records)
    bundle["source_rows_template"]["Moon"]["segments"][0]["words"][2] = 0.
    bundle["native_samples"]["normal"][0][0] = 0.
    bundle["initial"]["position_m"][0] = 0.
    bundle["kernel_manifest"]["kernels"][0]["sha256"] = "0" * 64
    assert records == original


@pytest.mark.parametrize("record,path,value", [
    (0, ["rows", 0, "stored_endpoint", "position_m", 0], 0.),
    (0, ["rows", 0, "gm_m3_s2"], 4902800205346.301),
    (1, ["inputs", "initial", "position_m", 0], 0.),
    (1, ["inputs", "origin"], "Moon"),
    (1, ["inputs", "orientation"], "ECLIPJ2000"),
    (1, ["inputs", "time_scale"], "UTC"),
    (1, ["inputs", "position_units"], "km"),
    (1, ["inputs", "velocity_units"], "km/s"),
    (1, ["inputs", "state_si", 0], 0.),
    (1, ["inputs", "epoch_tdb_s"], 0.),
    (1, ["inputs", "final_epoch_tdb_s"], 0.),
    (1, ["inputs", "nodes_tdb_s", 1], 978995505.2304224),
    (1, ["models", "A", "model_id"], "B"),
    (1, ["models", "A", "included_sources"], ["Sun", "Moon", "Earth"]),
    (1, ["models", "A", "gm_m3_s2", "Moon"], 4902800205346.301),
    (1, ["models", "A", "gm_m3_s2", "Earth"], True),
    (1, ["identity", "versions", "scipy"], "other"),
    (1, ["identity", "native_binary"], {}),
    (1, ["models", "A", "profiles", "native-normal", "raw_returned", "integration_completed"], False),
    (1, ["models", "A", "profiles", "native-normal", "result", "retained_states"], True),
    (1, ["models", "A", "profiles", "native-normal", "result", "guarded_states"], 300),
    (1, ["models", "A", "profiles", "native-tight", "result", "step_s"], 1.),
    (1, ["models", "A", "profiles", "native-normal", "result", "step_s"], True),
    (1, ["models", "A", "profiles", "native-normal", "result", "origin"], "Sun"),
    (1, ["models", "A", "profiles", "native-normal", "result", "force_order"], ["Sun", "Moon", "total"]),
    (1, ["models", "A", "profiles", "native-normal", "result", "gravity_parameters_m3_s2", "Moon"], 4902800205346.301),
    (1, ["models", "A", "profiles", "native-tight", "result", "samples", 3, "epoch_tdb_s"], 0.),
    (1, ["models", "A", "profiles", "native-tight", "result", "samples", 3, "state", 0], 0.),
    (1, ["models", "A", "profiles", "native-tight", "result", "minimum_checked_distances_m", "Moon"], 1737400.),
    (1, ["counts", "native_guard_reads_attempted"], 2711),
    (1, ["counts", "native_guard_reads_returned"], True),
    (1, ["native_minimum_checked_distances_m", "Moon"], 2000000.),
    (2, ["status"], "failed"),
    (2, ["stage"], "other"),
    (2, ["origin"], "Sun"),
    (2, ["aberration_correction"], "LT"),
    (2, ["state_units", 0], "km"),
    (2, ["t0_hex"], "0x0.0p0"),
    (2, ["offsets_s", 3], 0.),
    (2, ["spacecraft_propagations"], True),
    (2, ["force_evaluations"], 1),
    (2, ["reference_replayed"], True),
    (2, ["rows", 0, "body"], "Earth"),
    (2, ["rows", 0, "elapsed_s"], True),
    (2, ["rows", 0, "lo_s"], 1e-8),
    (2, ["rows", 0, "state_si", 0], 0.),
    (2, ["identity_after", "kernels", "kernels", 0, "sha256"], "0" * 64),
    (2, ["rows", 0, "segments", 0, "body"], 399),
    (2, ["rows", 0, "segments", 0, "centre"], 399),
    (2, ["rows", 0, "segments", 0, "frame"], 17),
    (2, ["rows", 0, "segments", 0, "type"], 3),
    (2, ["rows", 0, "segments", 0, "first_tdb_s"], 978995456.),
    (2, ["rows", 0, "segments", 0, "begin"], 0),
    (2, ["rows", 0, "segments", 0, "descriptor", 2], 0.),
    (2, ["rows", 0, "segments", 0, "path"], "other.bsp"),
    (2, ["rows", 0, "segments", 0, "trailer", 1], 0.),
    (2, ["rows", 0, "segments", 0, "trailer", 2], 38.),
    (2, ["rows", 0, "segments", 0, "index"], True),
    (2, ["rows", 0, "segments", 0, "address"], 1),
    (2, ["rows", 0, "segments", 0, "words", 0], 0.),
    (2, ["rows", 0, "segments", 0, "words", 1], 0.),
    (2, ["rows", 3, "segments", 0, "words", 2], 1.),
])
def test_changed_metadata_fails(records: tuple[dict[str, Any], ...], record: int,
                               path: list[Any], value: Any) -> None:
    changed = deepcopy(records)
    current: Any = changed[record]
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value
    with pytest.raises(ValueError):
        validate(changed)


def test_native_history_grid_is_not_interpolated(records: tuple[dict[str, Any], ...]) -> None:
    changed = deepcopy(records)
    history = changed[1]["models"]["A"]["profiles"]["native-normal"]["raw_returned"]["state_history"]
    key = next(iter(history))
    history[str(float(key) + 0.125)] = history.pop(key)
    with pytest.raises(ValueError, match="native exact grid"):
        validate(changed)


def test_native_state_nonfinite_rejected(records: tuple[dict[str, Any], ...]) -> None:
    changed = deepcopy(records)
    history = changed[1]["models"]["A"]["profiles"]["native-tight"]["raw_returned"]["state_history"]
    history[next(iter(history))][2] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        validate(changed)


def test_exact_type2_record_interval_must_cover_entire_coast(records: tuple[dict[str, Any], ...]) -> None:
    segment = deepcopy(records[2]["rows"][0]["segments"][0])
    # Valid directory and record covering t0 but ending before tf; no evaluation.
    interval = 100.
    index = 0
    segment["begin"] = 1
    segment["end"] = 39
    segment["trailer"] = [inputs.T0 - 10, interval, 35., 1.]
    segment["index"] = index
    segment["address"] = 1
    segment["words"][0:2] = [inputs.T0 + 40, interval / 2]
    descriptor = segment["descriptor"]
    import struct
    descriptor[2:] = struct.unpack("<3d", struct.pack("<6i", 10, 0, 1, 2, 1, 39))
    with pytest.raises(ValueError, match="full record coverage"):
        inputs.validate_segment(segment, 10)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
                                 b'{"x":1e999}', b'[]'])
def test_strict_json_rejects_invalid(raw: bytes) -> None:
    with pytest.raises(ValueError):
        inputs.parse(raw)


@pytest.mark.parametrize("value", [True, False, "1", None, float("inf"), float("nan"), 10**1000])
def test_number_rejects_invalid(value: Any) -> None:
    with pytest.raises(ValueError):
        inputs.number(value, "fixture")


def test_frozen_manifest_changed_bytes_rejected(tmp_path: Path) -> None:
    path = tmp_path / inputs.MANIFEST
    path.parent.mkdir(parents=True)
    path.write_bytes((ROOT / inputs.MANIFEST).read_bytes() + b" ")
    with pytest.raises(ValueError, match="manifest hash"):
        inputs.check_protected(tmp_path)


def test_deadline_stops_before_further_reads() -> None:
    calls = 0
    def check() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise TimeoutError("fixture deadline")
    with pytest.raises(TimeoutError, match="fixture deadline"):
        inputs.load_inputs(check=check)
    assert calls == 2


def test_clean_process_imports_no_scientific_package() -> None:
    script = f'''import importlib.util,sys
p={str(PATH)!r}
s=importlib.util.spec_from_file_location("corrected_input_process",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.load_inputs()
assert not any(k.split('.')[0] in ('numpy','scipy','spiceypy','tudatpy') for k in sys.modules)
print("metadata only")
'''
    completed = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", script],
                               capture_output=True, text=True, timeout=10)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "metadata only\n"


def test_source_hashes_are_immutable() -> None:
    for name, digest in inputs.INPUT_SHA.items():
        assert sha256((HERE / name).read_bytes()).hexdigest() == digest
