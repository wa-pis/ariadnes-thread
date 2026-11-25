"""Literal artificial trace auditing; no probe or native runtime imports."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from space_nav import _import_probe_audit as candidate


_PHASES = ("bootstrap-ready", "guards-ready", "native-import-enter",
           "native-import-return", "spice-guard-ready", "complete")


def _profile() -> dict[str, object]:
    return {"schema": "ariadna-import-input-v1", "scope": "import-only", "mode": "injected",
            "kernel_path": "/artificial/kernel.so", "kernel_sha256": "a" * 64,
            "probe_sha256": "b" * 64}


def _markers() -> list[dict[str, object]]:
    result = [{"schema": "ariadna-import-marker-v1", "index": index, "phase": phase,
               "elapsed_s": float(index), "scope": "import-only"}
              for index, phase in enumerate(_PHASES)]
    result[-1].update(kernel_path="/artificial/kernel.so", kernel_sha256="a" * 64)
    return result


def _encode(markers: list[dict[str, object]]) -> bytes:
    return b"".join((json.dumps(marker, separators=(",", ":")) + "\n").encode()
                    for marker in markers)


def _observation(raw: bytes) -> dict[str, object]:
    return {"schema": "ariadna-import-observation-v1", "exit_code": 0,
            "producer_elapsed_s": 6.0, "trace_sha256": sha256(raw).hexdigest(),
            "probe_sha256": "b" * 64, "finalization": "checked-after-fsync",
            "finalized_elapsed_s": 6.1}


def _audit(raw: bytes | None = None, *, profile: object | None = None,
           observation: object | None = None) -> dict[str, object]:
    if raw is None:
        raw = _encode(_markers())
    return candidate.audit(raw, _profile() if profile is None else profile,
                           _observation(raw) if observation is None else observation,
                           deadline_s=10.0, clock=lambda: 0.0)


@pytest.mark.parametrize("mode", ["native", "injected"])
def test_literal_success_remains_conditional_import_only(mode: str) -> None:
    profile = _profile()
    profile["mode"] = mode
    result = _audit(profile=profile)
    assert result == {"schema": "ariadna-import-audit-v1", "status": "passed",
                      "scope": "import-only", "physical_admission": "unavailable",
                      "mode": mode, "markers_checked": 6, "kernel_sha256": "a" * 64,
                      "completion_requires_outer_finalization": True}


@pytest.mark.parametrize("field,value", [
    ("schema", "wrong"), ("scope", "physical"), ("mode", []), ("mode", "physical"),
    ("kernel_path", "relative.so"), ("kernel_path", False),
    ("kernel_sha256", "A" * 64), ("kernel_sha256", "z" * 64),
    ("probe_sha256", "short"), ("probe_sha256", True),
])
def test_profile_scope_and_pins_are_strict(field: str, value: object) -> None:
    profile = _profile()
    profile[field] = value
    with pytest.raises(candidate.ProbeAuditError):
        _audit(profile=profile)


def test_matching_nul_paths_refuse_even_when_profile_and_marker_agree() -> None:
    profile, markers = _profile(), _markers()
    profile["kernel_path"] = "/artificial/kernel\0.so"
    markers[-1]["kernel_path"] = profile["kernel_path"]
    with pytest.raises(candidate.ProbeAuditError, match="without NUL"):
        _audit(_encode(markers), profile=profile)


@pytest.mark.parametrize("profile", [None, [], True, {}, {"extra": 1}])
def test_profile_requires_exact_object(profile: object) -> None:
    raw = _encode(_markers())
    with pytest.raises(candidate.ProbeAuditError):
        candidate.audit(raw, profile, _observation(raw), deadline_s=10, clock=lambda: 0)


@pytest.mark.parametrize("field,value", [
    ("schema", "wrong"), ("exit_code", True), ("exit_code", False),
    ("exit_code", 0.0), ("exit_code", 2), ("finalization", "pending-after-fsync-observation"),
    ("probe_sha256", "c" * 64), ("trace_sha256", "c" * 64),
    ("producer_elapsed_s", True), ("producer_elapsed_s", -1), ("producer_elapsed_s", 45),
    ("producer_elapsed_s", float("nan")), ("producer_elapsed_s", float("inf")),
    ("finalized_elapsed_s", 5.9), ("finalized_elapsed_s", 45),
    ("finalized_elapsed_s", float("nan")), ("finalized_elapsed_s", True),
])
def test_child_failure_identity_and_incomplete_finalization_refuse(field: str, value: object) -> None:
    raw = _encode(_markers())
    observation = _observation(raw)
    observation[field] = value
    with pytest.raises(candidate.ProbeAuditError):
        _audit(raw, observation=observation)


@pytest.mark.parametrize("record", ["profile", "observation"])
@pytest.mark.parametrize("change", ["extra", "missing"])
def test_record_keys_are_exact(record: str, change: str) -> None:
    raw = _encode(_markers())
    profile, observation = _profile(), _observation(raw)
    item = profile if record == "profile" else observation
    if change == "extra":
        item["scientific_pass"] = True
    else:
        item.pop("schema")
    with pytest.raises(candidate.ProbeAuditError):
        _audit(raw, profile=profile, observation=observation)


@pytest.mark.parametrize("index,field,value", [
    (0, "index", False), (1, "index", True), (2, "index", 2.0), (3, "index", 2),
    (0, "schema", "wrong"), (2, "scope", "physical"), (3, "phase", "native-import-enter"),
    (0, "elapsed_s", -0.1), (0, "elapsed_s", True), (1, "elapsed_s", float("nan")),
    (1, "elapsed_s", float("inf")), (3, "elapsed_s", 1.0), (5, "elapsed_s", 6.01),
    (5, "kernel_path", "/other/kernel.so"), (5, "kernel_sha256", "c" * 64),
])
def test_markers_cannot_change_order_clock_scope_or_kernel(index: int, field: str, value: object) -> None:
    markers = _markers()
    markers[index][field] = value
    with pytest.raises(candidate.ProbeAuditError):
        _audit(_encode(markers))


@pytest.mark.parametrize("index", range(6))
def test_each_missing_phase_is_unavailable(index: int) -> None:
    markers = _markers()
    markers.pop(index)
    with pytest.raises(candidate.ProbeAuditError, match="six"):
        _audit(_encode(markers))


@pytest.mark.parametrize("change", ["duplicate", "reverse", "extra-field", "missing-field"])
def test_trace_structure_is_fixed(change: str) -> None:
    markers = _markers()
    if change == "duplicate":
        markers.insert(2, deepcopy(markers[2]))
    elif change == "reverse":
        markers.reverse()
    elif change == "extra-field":
        markers[3]["cause"] = "deadlock"
    else:
        markers[5].pop("kernel_sha256")
    with pytest.raises(candidate.ProbeAuditError):
        _audit(_encode(markers))


@pytest.mark.parametrize("change", ["truncated", "duplicate-key", "invalid-utf8", "array", "empty", "nonbytes", "deep"])
def test_malformed_saved_bytes_are_unavailable(change: str) -> None:
    raw = _encode(_markers())
    if change == "truncated":
        raw = raw[:-1]
    elif change == "duplicate-key":
        raw = raw.replace(b'{"schema":', b'{"index":0,"schema":', 1)
    elif change == "invalid-utf8":
        raw = raw.replace(b"bootstrap-ready", b"\xff" * 15, 1)
    elif change == "array":
        raw = b"[]\n" + b"\n".join(raw.splitlines()[1:]) + b"\n"
    elif change == "empty":
        raw = b""
    elif change == "deep":
        raw = b"[" * 200 + b"0" + b"]" * 200 + b"\n" + b"\n".join(raw.splitlines()[1:]) + b"\n"
    if change == "nonbytes":
        with pytest.raises(candidate.ProbeAuditError):
            candidate.audit(raw.decode(), _profile(), _observation(raw), deadline_s=10, clock=lambda: 0)
    else:
        with pytest.raises(candidate.ProbeAuditError):
            _audit(raw)


def test_exact_marker_capacity_passes_but_one_extra_byte_refuses() -> None:
    lines = _encode(_markers()).splitlines(keepends=True)
    raw = b"".join(line[:-1] + b" " * (512 - len(line)) + b"\n" for line in lines)
    assert len(raw) == 6 * 512
    assert _audit(raw)["status"] == "passed"
    with pytest.raises(candidate.ProbeAuditError, match="512"):
        _audit(raw.replace(b"\n", b" \n", 1))
    with pytest.raises(candidate.ProbeAuditError, match="4096"):
        _audit(raw + b" " * (4097 - len(raw)))


@pytest.mark.parametrize("clock,deadline", [
    (lambda: False, 10), (lambda: float("nan"), 10), (lambda: float("inf"), 10),
    (lambda: 10.0, 10.0), (lambda: 0.0, False), (lambda: 0.0, float("inf")),
])
def test_audit_requires_finite_unexpired_clock(clock: object, deadline: object) -> None:
    raw = _encode(_markers())
    with pytest.raises(candidate.ProbeAuditError):
        candidate.audit(raw, _profile(), _observation(raw), deadline_s=deadline, clock=clock)


@pytest.mark.parametrize("times", [(0, 1, 0), (0, 1, 10)])
def test_audit_detects_clock_reversal_or_expiry_during_parsing(times: tuple[float, ...]) -> None:
    values = iter(times)
    raw = _encode(_markers())
    with pytest.raises(candidate.ProbeAuditError):
        candidate.audit(raw, _profile(), _observation(raw), deadline_s=10, clock=lambda: next(values))


def _cli(tmp_path: Path, *, changed_profile: bytes | None = None,
         prefix: str = "") -> subprocess.CompletedProcess[str]:
    raw = _encode(_markers())
    profile = tmp_path / "profile.json"
    observation = tmp_path / "observation.json"
    trace = tmp_path / "trace.jsonl"
    profile.write_bytes(json.dumps(_profile()).encode() if changed_profile is None else changed_profile)
    observation.write_text(json.dumps(_observation(raw)))
    trace.write_bytes(raw)
    source = str(Path(candidate.__file__).parents[1])
    args = ["--audit", str(profile), str(observation), str(trace), repr(time.monotonic() + 8)]
    script = (f"import sys; sys.path.insert(0,{source!r}); " + prefix
              + f"from space_nav._import_probe_audit import main; raise SystemExit(main({args!r}))")
    return subprocess.run([sys.executable, "-I", "-B", "-c", script], capture_output=True,
                          text=True, timeout=10)


def test_saved_artificial_cli_is_independent_and_passes(tmp_path: Path) -> None:
    result = _cli(tmp_path)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["completion_requires_outer_finalization"] is True


@pytest.mark.parametrize("profile", [b" " * 65537, b'{"schema":0,"schema":1}', b"NaN"])
def test_cli_refuses_oversize_duplicate_or_nonfinite_input(tmp_path: Path, profile: bytes) -> None:
    result = _cli(tmp_path, changed_profile=profile)
    assert result.returncode == 2 and result.stdout == ""


def test_cli_refuses_even_simulated_preloaded_scientific_runtime(tmp_path: Path) -> None:
    result = _cli(tmp_path, prefix="import types;sys.modules['numpy']=types.ModuleType('numpy');")
    assert result.returncode == 2 and "already loaded" in result.stderr


def test_guard_blocks_producer_and_scientific_imports_without_loading_them(tmp_path: Path) -> None:
    source = str(Path(candidate.__file__).parents[1])
    script = f"""
import importlib, sys
sys.path.insert(0, {source!r})
from space_nav._import_probe_audit import _install_guard
_install_guard()
for name in ('space_nav._import_probe', 'space_nav._import_probe_run',
             'space_nav._owner_endpoint_fixture', 'tudatpy', 'numpy', 'scipy', 'spiceypy'):
    try:
        importlib.import_module(name)
    except ImportError:
        pass
    else:
        raise AssertionError(name)
assert not {{'tudatpy', 'numpy', 'scipy', 'spiceypy'}} & set(sys.modules)
"""
    result = subprocess.run([sys.executable, "-I", "-B", "-c", script], capture_output=True,
                            text=True, timeout=10)
    assert result.returncode == 0, result.stderr
