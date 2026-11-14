"""Exercise the private far-range archive and launcher failure boundaries."""

from hashlib import sha256
import json
from pathlib import Path
import runpy
from time import monotonic
from typing import Any

import pytest

HERE = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
A = runpy.run_path(str(HERE / "0197-far-archive.py"))
L = runpy.run_path(str(HERE / "0197-far-launch.py"))


def idle() -> None:
    pass


def test_lossless_shards_and_deterministic_digests(tmp_path: Path) -> None:
    limits = A["Limits"](shard_raw=128)
    rows = [("force", {"sources": {"Sun": [float(i), -0.0], "Moon": [1.0], "Earth": [2.0]}})
            for i in range(15)]
    hashes = []
    for name in ("original", "restore"):
        writer = A["Writer"](tmp_path/name, {"stage": "capacity"}, idle, limits)
        for kind, value in rows:
            writer.append(kind, value)
        hashes.append(writer.seal("passed", {"verified": True}))
        reader = A["Reader"](tmp_path/name, idle, limits)
        output = list(reader.records())
        assert output == rows
        assert all(list(record["sources"]) == ["Sun", "Moon", "Earth"] for _, record in output)
        assert all(record["sources"]["Sun"][1].hex() == "-0x0.0p+0" for _, record in output)
        assert reader.manifest["rows"] == 15 and len(reader.manifest["parts"]) > 1
    assert hashes[0] == hashes[1]


def test_tampering_and_truncation_fail_before_rows(tmp_path: Path) -> None:
    archive = tmp_path/"damaged"
    writer = A["Writer"](archive, {}, idle)
    writer.append("rhs", {"i": 1, "value": 0.125})
    writer.seal("passed", {})
    shard = archive/"00000.shard"
    raw = shard.read_bytes()
    for bad in (raw[:-1], raw[:-1]+bytes([raw[-1] ^ 1])):
        shard.write_bytes(bad)
        with pytest.raises(ValueError, match="digest|size"):
            next(A["Reader"](archive, idle).records())


@pytest.mark.parametrize(("limits", "message"), [
    ({"shard_raw": 5}, "individual record"),
    ({"raw": 25}, "raw byte cap"),
    ({"zipped": 1}, "compressed byte cap"),
])
def test_storage_cap_preserves_partial(tmp_path: Path, limits: dict[str, int], message: str) -> None:
    archive = tmp_path/"limited"
    cap = A["Limits"](**limits)
    writer = A["Writer"](archive, {}, idle, cap)
    with pytest.raises(ValueError, match=message):
        writer.append("a", {"data": "x"*30})
        writer.seal("passed", {})
    writer.seal("partial", {"first_failure": message})
    reader = A["Reader"](archive, idle, cap)
    assert list(reader.records()) == []
    assert reader.manifest["status"] == "partial"


def test_combined_bytes_carry_from_study_to_audit(tmp_path: Path) -> None:
    limits = A["Limits"](raw=55, zipped=1000)
    row = {"sample": 3.141592653589793}
    w = A["Writer"](tmp_path/"study", {}, idle, limits)
    w.append("source", row)
    w.seal("passed", {})
    prior = A["Reader"](tmp_path/"study", idle, limits).manifest
    w = A["Writer"](tmp_path/"audit", {}, idle, limits, used_raw=prior["raw"], used_zip=prior["gzip"])
    with pytest.raises(ValueError, match="combined raw"):
        w.append("source", row)


def test_late_or_unbound_receipt_never_accepts(tmp_path: Path) -> None:
    w = A["Writer"](tmp_path/"study", {"mode": "capacity"}, idle)
    w.append("fixture", {"x": 1})
    digest = w.seal("passed", {})
    identity = {"mode": "capacity"}
    marker = {"identity": identity, "started_s": 1.0}
    bind_sha = L["bind"](tmp_path, "study", "parent_attempt", marker)
    attempt = {**marker, "parent_attempt_sha256": bind_sha}
    attempt_sha = L["bind"](tmp_path, "study", "attempt", attempt)
    receipt = {**attempt, "gate": "passed", "status": "passed", "attempt_sha256": attempt_sha,
               "manifest_sha256": digest, "elapsed_s": 2.0}
    receipt_sha = L["bind"](tmp_path, "study", "receipt", receipt)
    path = L["phase_name"](tmp_path, "study", "parent_receipt")
    parent = {**receipt, "elapsed_s": 3.0, "checkout_frozen": True, "returncode": 0,
              "child_receipt_sha256": receipt_sha}
    L["bind"](tmp_path, "study", "parent_receipt", parent)
    assert L["finalized"](tmp_path, "study", identity)["parent_receipt_sha256"] == sha256(path.read_bytes()).hexdigest()
    for bad, error in (({"manifest_sha256": "bad"}, "manifest binding"),
                       ({"elapsed_s": 360.0}, "finalization"),
                       ({"returncode": 2}, "finalization")):
        path.write_text(json.dumps({**parent, **bad}))
        with pytest.raises(ValueError, match=error):
            L["finalized"](tmp_path, "study", identity)
    path.write_text(json.dumps(parent))
    L["bind"](tmp_path, "study", "late", {"gate": "failed"})
    with pytest.raises(ValueError, match="late"):
        L["finalized"](tmp_path, "study", identity)


def test_deadline_and_external_storage_preflight(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="elapsed limit"):
        L["deadline"](monotonic()-4, 3)
    with pytest.raises(ValueError, match="free space"):
        A["preflight"](tmp_path, A["Limits"](free=2**60))


def test_no_live_without_separate_authorization(tmp_path: Path) -> None:
    proposed = tmp_path/"R5.51"
    with pytest.raises(ValueError, match="authorization"):
        L["live_gate"](proposed, "revision", "preparation")
    (tmp_path/"R5.51-authorization.json").write_text(json.dumps({
        "contract": "ADR0196", "stage": "R5.51", "revision": "revision",
        "preparation_sha256": "preparation", "authorized": 1,
    }))
    with pytest.raises(ValueError, match="separate R5.51 authorization"):
        L["live_gate"](proposed, "revision", "preparation")


def test_duplicate_json_field_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        A["decode"](b'{"x":0,"x":1}')


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_records_rejected(tmp_path: Path, value: Any) -> None:
    w = A["Writer"](tmp_path/"bad", {}, idle)
    with pytest.raises(ValueError):
        w.append("rhs", {"value": value})


def test_interrupted_shard_never_hides_synced_prefix(tmp_path: Path) -> None:
    path = tmp_path/"interrupted"
    writer = A["Writer"](path, {}, idle)
    row = {"value": 3.141592653589793}
    writer.append("rhs", row)
    writer.flush()
    (path/"00001.partial").write_bytes(b"aborted")
    reader = A["Reader"].recover_prefix(path, idle)
    assert reader.manifest["status"] == "partial" and reader.digest is None
    assert list(reader.records()) == [("rhs", row)]
    assert not (path/"manifest.json").exists()
