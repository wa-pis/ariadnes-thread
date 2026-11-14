"""Reject altered phase evidence and malformed archive joins without real data."""

from __future__ import annotations

import gzip
from hashlib import sha256
import json
from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[1]
NAME = "0192-range-inputs.py"
MODULE = Path(__file__).resolve().with_name(NAME)
A = runpy.run_path(str(MODULE if MODULE.is_file() else ROOT / "docs" / "adr" / "experiments" / NAME))


def check() -> None:
    pass


def record(path: Path, payload: object) -> dict[str, int | str]:
    raw = json.dumps(payload, allow_nan=False).encode()
    data = gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw
    path.write_bytes(data)
    result = {"bytes": len(data), "sha256": sha256(data).hexdigest()}
    if path.suffix == ".gz":
        result |= {"original_bytes": len(raw), "original_sha256": sha256(raw).hexdigest()}
    return result


def test_pinned_design_rejects_stale_bytes(tmp_path: Path) -> None:
    archive = tmp_path / "docs" / "adr" / "experiments"
    archive.mkdir(parents=True)
    (archive / "0188-design-inputs.json").write_text("{}")
    with pytest.raises(ValueError, match="0188-design-inputs.json digest"):
        A["load"](tmp_path, check)


@pytest.mark.parametrize("mutate", ["none", "bytes", "child-link", "late"])
def test_phase_verifies_bound_sidecars(tmp_path: Path, mutate: str) -> None:
    common = {"contract": "ADR0188", "adapter_mode": "reference"}
    parent_common = {"contract": "ADR0188", "phase": "audit", "revision": "a" * 40, "preparation_sha256": "b" * 64}
    manifest = {"measured_revision": parent_common["revision"],
                "preparation_sha256": parent_common["preparation_sha256"]}
    original = {
        "audit.json.gz": {"budget_s": 10, "finalization_gate": "passed", **common},
        "audit.attempt.json": {"started_s": 4.0, **common},
        "audit.parent-attempt.json": parent_common,
    }
    files = {name: record(tmp_path / name, body) for name, body in original.items()}
    digest = files["audit.json.gz"]["original_sha256"]
    child = {"status": "passed", "finalization_gate": "passed", "elapsed_s": 7.0,
             "started_s": 4.0, "evidence_sha256": digest}
    files["audit.receipt.json"] = record(tmp_path / "audit.receipt.json", child)
    parent = {
        **parent_common, "returncode": 0, "checkout_frozen": True, "started_s": 4.0,
        "elapsed_s": 10.1 if mutate == "late" else 8.0, "finalization_gate": "passed",
        "attempt_sha256": files["audit.attempt.json"]["sha256"],
        "parent_attempt_sha256": files["audit.parent-attempt.json"]["sha256"],
        "child_receipt_sha256": "c"*64 if mutate == "child-link" else files["audit.receipt.json"]["sha256"],
        "evidence_sha256": digest,
    }
    files["audit.parent-receipt.json"] = record(tmp_path / "audit.parent-receipt.json", parent)
    if mutate == "bytes":
        p = tmp_path / "audit.receipt.json"
        p.write_bytes(p.read_bytes().replace(b"7.0", b"6.0"))
    if mutate == "none":
        report, reported_sha = A["_phase"](tmp_path, "audit", files, manifest, check)
        assert report == original["audit.json.gz"] and reported_sha == digest
    else:
        error = {"bytes": "audit.receipt.json digest", "child-link": "receipt link", "late": "budget"}[mutate]
        with pytest.raises(ValueError, match=error):
            A["_phase"](tmp_path, "audit", files, manifest, check)


@pytest.mark.parametrize("mutate", ["none", "epoch-alias", "guard-group", "nonfinite", "bool"])
def test_native_mesh_uses_guard_six_state_at_exact_epoch(mutate: str) -> None:
    t0 = 1000.0
    sc, moon = [1.0]*6, [2.0]*6
    guards = [
        {"body": body, "epoch_tdb_s": epoch, "group": group, "state_si": moon[:], "passed": True}
        for group, epoch in enumerate((t0, t0, t0+0.5))
        for body in ("Sun", "Moon", "Earth")
    ]
    second_key = str(t0+0.5)
    if mutate == "guard-group":
        guards[-2]["group"] = 1
    if mutate == "epoch-alias":
        second_key = "1e3"
    if mutate in {"nonfinite", "bool"}:
        guards[-2]["state_si"][0] = float("inf") if mutate == "nonfinite" else False
    profile = {
        "step_s": 0.5,
        "raw_returned": {"integration_completed": True, "state_history": {str(t0): sc, second_key: sc}},
        "guards": guards,
        "result": {"step_s": 0.5, "retained_states": 2, "guarded_states": 2, "origin": "SSB",
                   "orientation": "J2000", "position_units": "m", "velocity_units": "m/s",
                   "time_units": "TDB seconds since J2000"},
    }
    if mutate == "none":
        assert A["_mesh"](profile, t0, 2, 0.5, check) == [(t0, sc, moon), (t0+0.5, sc, moon)]
    else:
        error = {"epoch-alias": "duplicate native mesh epoch", "guard-group": "native guard order",
                 "nonfinite": "nonfinite", "bool": "expected finite"}[mutate]
        with pytest.raises(ValueError, match=error):
            A["_mesh"](profile, t0, 2, 0.5, check)
