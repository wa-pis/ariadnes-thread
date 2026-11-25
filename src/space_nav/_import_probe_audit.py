"""Independent stdlib review of a bounded import-only diagnostic trace.

Trace acceptance remains conditional on the separately supervised outer cleanup
and finalization. It establishes neither a timeout cause nor physical admission.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import importlib.abc
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys
from time import monotonic
from typing import cast


class ProbeAuditError(ValueError):
    """A saved import observation is invalid, incomplete or unavailable."""


_PHASES = ("bootstrap-ready", "guards-ready", "native-import-enter",
           "native-import-return", "spice-guard-ready", "complete")
_PROFILE = {"schema", "scope", "mode", "kernel_path", "kernel_sha256", "probe_sha256"}
_OBSERVATION = {"schema", "exit_code", "producer_elapsed_s", "trace_sha256",
                "probe_sha256", "finalization", "finalized_elapsed_s"}
_MARKER = {"schema", "index", "phase", "elapsed_s", "scope"}
_FORBIDDEN = ("tudatpy", "numpy", "scipy", "spiceypy", "cspyce",
              "space_nav._import_probe", "space_nav._import_probe_run",
              "space_nav._owner_endpoint_fixture", "space_nav._owner_endpoint_run")


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ProbeAuditError(message)


def _mapping(value: object, keys: set[str], field: str) -> dict[str, object]:
    _need(type(value) is dict, field + ": object required")
    result = cast(dict[str, object], value)
    _need(set(result) == keys, field + ": unexpected or missing fields")
    return result


def _number(value: object, field: str) -> float:
    _need(type(value) in (int, float), field + ": finite nonboolean number required")
    try:
        result = float(cast(float, value))
    except (ValueError, OverflowError) as exc:
        raise ProbeAuditError(field + ": finite number required") from exc
    _need(math.isfinite(result), field + ": finite number required")
    return result


def _digest(value: object, field: str) -> str:
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", cast(str, value)) is not None,
          field + ": lowercase SHA256 required")
    return cast(str, value)


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        _need(key not in result, "duplicate JSON field: " + key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ProbeAuditError("nonfinite JSON constant: " + value)


def _decode(raw: bytes) -> object:
    try:
        return json.loads(raw, object_pairs_hook=_unique, parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ProbeAuditError("invalid finite JSON") from exc


def audit(raw: bytes, profile: object, observation: object, *, deadline_s: float,
          clock: Callable[[], float] = monotonic) -> dict[str, object]:
    """Validate six saved markers against pinned input and durable child facts.

    Times are seconds elapsed from the inherited parent start. The observation's
    pins and child status require external admission; no producer is imported.
    """
    deadline = _number(deadline_s, "audit deadline_s")
    previous_clock = _number(clock(), "audit clock")
    _need(previous_clock < deadline, "audit deadline exhausted")

    def check() -> None:
        nonlocal previous_clock
        now = _number(clock(), "audit clock")
        _need(previous_clock <= now < deadline, "audit clock reversed or deadline exhausted")
        previous_clock = now

    p = _mapping(profile, _PROFILE, "profile")
    _need(p["schema"] == "ariadna-import-input-v1" and p["scope"] == "import-only",
          "profile: fixed schema/scope required")
    _need(type(p["mode"]) is str and p["mode"] in ("injected", "native"),
          "profile.mode: injected or native required")
    _need(type(p["kernel_path"]) is str and "\0" not in cast(str, p["kernel_path"])
          and Path(cast(str, p["kernel_path"])).is_absolute(),
          "profile.kernel_path: absolute path without NUL required")
    kernel_sha = _digest(p["kernel_sha256"], "profile.kernel_sha256")
    probe_sha = _digest(p["probe_sha256"], "profile.probe_sha256")
    o = _mapping(observation, _OBSERVATION, "observation")
    _need(o["schema"] == "ariadna-import-observation-v1", "observation.schema mismatch")
    _need(type(o["exit_code"]) is int and o["exit_code"] == 0,
          "observation.exit_code: successful child required")
    _need(o["finalization"] == "checked-after-fsync", "durable child observation required")
    finished = _number(o["producer_elapsed_s"], "producer_elapsed_s")
    finalized = _number(o["finalized_elapsed_s"], "finalized_elapsed_s")
    _need(0 <= finished <= finalized < 45, "child observation outside producer45s phase")
    _need(_digest(o["probe_sha256"], "observation.probe_sha256") == probe_sha,
          "probe identity differs")
    _need(type(raw) is bytes and 0 < len(raw) <= 4096, "trace: nonempty <=4096bytes required")
    _need(_digest(o["trace_sha256"], "observation.trace_sha256") == sha256(raw).hexdigest(),
          "trace hash differs")
    _need(raw.endswith(b"\n"), "trace: truncated final marker")
    lines = raw.splitlines(keepends=True)
    _need(len(lines) == 6, "trace: six complete markers required")
    previous_elapsed = 0.0
    for index, (phase, line) in enumerate(zip(_PHASES, lines, strict=True)):
        check()
        _need(len(line) <= 512 and line.endswith(b"\n"), "marker: <=512newline-terminated bytes required")
        keys = _MARKER | ({"kernel_path", "kernel_sha256"} if index == 5 else set())
        marker = _mapping(_decode(line), keys, "marker")
        _need(marker["schema"] == "ariadna-import-marker-v1" and marker["scope"] == "import-only",
              "marker: fixed schema/scope required")
        _need(type(marker["index"]) is int and marker["index"] == index
              and marker["phase"] == phase, "marker: exact phase order required")
        elapsed = _number(marker["elapsed_s"], "marker.elapsed_s")
        _need(previous_elapsed <= elapsed <= finished, "marker: elapsed clock reversed or beyond child")
        previous_elapsed = elapsed
        if index == 5:
            _need(marker["kernel_path"] == p["kernel_path"], "loaded kernel path differs")
            _need(_digest(marker["kernel_sha256"], "marker.kernel_sha256") == kernel_sha,
                  "loaded kernel hash differs")
    check()
    return {"schema": "ariadna-import-audit-v1", "status": "passed", "scope": "import-only",
            "physical_admission": "unavailable", "mode": p["mode"], "markers_checked": 6,
            "kernel_sha256": kernel_sha, "completion_requires_outer_finalization": True}


def _install_guard() -> None:
    if any(name == prefix or name.startswith(prefix + ".")
           for name in sys.modules for prefix in _FORBIDDEN):
        raise ProbeAuditError("independent auditor already loaded producer/scientific runtime")

    class ImportGuard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname: str, path: object = None,
                      target: object = None) -> None:
            if any(fullname == prefix or fullname.startswith(prefix + ".") for prefix in _FORBIDDEN):
                raise ImportError("independent auditor forbids " + fullname)

    sys.meta_path.insert(0, ImportGuard())


def _read(path: str, limit: int) -> bytes:
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    _need(len(raw) <= limit, "saved input exceeds fixed byte cap")
    return raw


def main(argv: Sequence[str] | None = None) -> int:
    """Audit saved bytes only; never execute an import probe."""
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        _need(len(args) == 5 and args[0] == "--audit",
              "private audit requires profile/observation/trace/deadline")
        _install_guard()
        result = audit(_read(args[3], 4096), _decode(_read(args[1], 65536)),
                       _decode(_read(args[2], 65536)), deadline_s=float(args[4]))
        sys.stdout.write(json.dumps(result, allow_nan=False, sort_keys=True) + "\n")
        return 0
    except (ProbeAuditError, OSError, ValueError, TypeError) as exc:
        sys.stderr.write(f"{type(exc).__name__}: {str(exc)[:1024]}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
