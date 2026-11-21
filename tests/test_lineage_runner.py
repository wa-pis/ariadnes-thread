"""Scope, byte/work/time and durable evidence tests on fabricated archives only."""

from __future__ import annotations

import copy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs/adr/experiments/0230-saved-lineage.py"


def runner() -> Any:
    spec = importlib.util.spec_from_file_location("_lineage_runner_tests", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "raw",
    [
        b'{"x":1,"x":2}\n',
        b'{"x":{"a":1,"a":2}}\n',
        b'{"x":NaN}\n',
        b'{"x":Infinity}\n',
        b'{"x":1e999}\n',
        b"[]\n",
        b'{"x": 1}\n',
        b"{}",
    ],
)
def test_strict_decoder(raw: bytes) -> None:
    with pytest.raises(ValueError):
        runner().decode(raw)


@pytest.mark.parametrize(
    "key,limit",
    [
        ("event_visits", 32768),
        ("descriptors", 1024),
        ("aliases", 768),
        ("norm_pairs", 36),
    ],
)
def test_exact_work_caps(key: str, limit: int) -> None:
    b = runner().Budget()
    b.charge(key, limit)
    with pytest.raises(ValueError, match="cap exhausted"):
        b.charge(key)


def test_clock_and_counter_validation() -> None:
    m = runner()
    b = m.Budget(started_ns=10, clock=lambda: 30_000_000_010)
    with pytest.raises(ValueError, match="deadline"):
        b.check()
    b = m.Budget()
    for key, count in [("norm_pairs", True), ("missing", 1), ("norm_pairs", -1)]:
        with pytest.raises(ValueError):
            b.charge(key, count)


def test_inventory_cap_and_duplicate_read(tmp_path: Path) -> None:
    m = runner()
    p = tmp_path / "data"
    p.write_bytes(b"x" * 4194304)
    b = m.Budget()
    assert len(b.read(p)) == 4194304
    b.read(p)
    assert b.source_bytes == 4194304
    other = tmp_path / "more"
    other.write_bytes(b"x")
    with pytest.raises(ValueError, match="inventory cap"):
        b.read(other)
    p.write_bytes(b"x" * 4194305)
    with pytest.raises(ValueError, match="file byte cap"):
        m.Budget().read(p)


def test_fixed_retained_profile_rejects_override_without_input_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    m = runner()

    def saved_metadata() -> tuple[bool, dict[str, str | None]]:
        paths = {m.AUDIT, *m.OUTPUT.glob("*")}
        return m.OUTPUT.exists(), {
            str(path): sha256(path.read_bytes()).hexdigest() if path.exists() else None
            for path in paths
        }

    before = saved_metadata()
    read = m.Budget.read
    forbidden = {m.HERE.parent / name for name in m.DATA_NAMES}

    def metadata_only(self: Any, path: Path, **kwargs: Any) -> bytes:
        assert path not in forbidden, "profile rejection must not read retained inputs"
        return read(self, path, **kwargs)

    monkeypatch.setattr(m.Budget, "read", metadata_only)
    profile = m.retained_profile()
    profile["pins"]["report"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="fixed retained profile"):
        m.profile_check(profile, m.OUTPUT)
    profile = m.retained_profile()
    with pytest.raises(ValueError, match="fixed retained profile"):
        m.profile_check(profile, tmp_path / "out")
    # ADR0233 legitimately created these files; rejection must preserve any state.
    assert saved_metadata() == before


def pack(tmp_path: Path) -> tuple[Any, dict[str, Any], Path]:
    from lineage_fixtures import write_artificial_pack

    profile = write_artificial_pack(tmp_path / "inputs")
    return runner(), profile, tmp_path / "out"


def test_complete_artificial_dispatch_and_separate_audit(tmp_path: Path) -> None:
    m, profile, out = pack(tmp_path)
    profile_path = tmp_path / "profile.json"
    profile_path.write_bytes(m.wire(profile))
    cmd = [sys.executable, "-I", "-S", "-B", str(SCRIPT)]
    first = subprocess.run(
        [*cmd, "artificial", str(profile_path), str(out)],
        capture_output=True,
        text=True,
        timeout=35,
    )
    assert first.returncode == 0, first.stderr
    p = sha256((out / "completion.json").read_bytes()).hexdigest()
    target = tmp_path / "audit.json"
    second = subprocess.run(
        [*cmd, "audit-artificial", str(profile_path), str(out), p, str(target)],
        capture_output=True,
        text=True,
        timeout=35,
    )
    assert second.returncode == 0, second.stderr
    report = json.loads((out / "report.json").read_bytes())
    result = json.loads(target.read_bytes())
    assert report["status"] == "lineage-qualified-attribution-unresolved"
    assert result["status"] == "lineage-independently-verified"
    assert report["source_inventory_bytes"] >= 3784677
    assert (
        sum(p.stat().st_size for p in out.iterdir()) + target.stat().st_size <= 1048576
    )
    for key in m.ZERO:
        assert report[key] == result[key] == 0
    again = subprocess.run(
        [*cmd, "artificial", str(profile_path), str(out)],
        capture_output=True,
        text=True,
        timeout=35,
    )
    assert again.returncode == 3 and "existing" in again.stderr


def test_raw_pin_precedes_decode(tmp_path: Path) -> None:
    m, profile, out = pack(tmp_path)
    Path(profile["inputs"]["report"]).write_bytes(b"not JSON")
    with pytest.raises(ValueError, match="report raw pin"):
        m.run(out, profile)
    assert not out.exists()


def test_mixed_scope_and_path_rejected(tmp_path: Path) -> None:
    m, profile, out = pack(tmp_path)
    for field, value in [
        ("scope", "retained"),
        ("reference_sha256", m.retained_profile()["reference_sha256"]),
        ("candidate_id", "d0001-t0035"),
    ]:
        bad = copy.deepcopy(profile)
        bad[field] = value
        with pytest.raises(ValueError):
            m.run(out, bad)
    bad = copy.deepcopy(profile)
    bad["inputs"]["report"] = str(
        m.HERE.with_name("0224-retained-trace-result") / "report.json"
    )
    with pytest.raises(ValueError, match="path isolation"):
        m.run(out, bad)


def test_late_producer_failure_removes_own_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    m, profile, out = pack(tmp_path)
    b = m.Budget()
    read = b.read

    def late(path: Path, *, source: bool = True, cap: int = 4194304) -> bytes:
        value = read(path, source=source, cap=cap)
        if path == out / "completion.json":
            raise ValueError("late finalization failure")
        return value

    monkeypatch.setattr(b, "read", late)
    with pytest.raises(ValueError, match="late finalization"):
        m.run(out, profile, budget=b)
    assert (out / "attempt.json").exists() and not (out / "completion.json").exists()


def test_saved_analysis_tampering_fails_separate_verifier(tmp_path: Path) -> None:
    m, profile, out = pack(tmp_path)
    m.run(out, profile)
    report = m.decode((out / "report.json").read_bytes())
    report["analysis"]["status"] = "dominant-cause-proved"
    raw = m.wire(report)
    (out / "report.json").write_bytes(raw)
    receipt = m.decode((out / "receipt.json").read_bytes())
    receipt["report_sha256"] = sha256(raw).hexdigest()
    raw = m.wire(receipt)
    (out / "receipt.json").write_bytes(raw)
    completion = m.decode((out / "completion.json").read_bytes())
    completion["receipt_sha256"] = sha256(raw).hexdigest()
    completion["analysis_sha256"] = m.digest(report["analysis"])
    raw = m.wire(completion)
    (out / "completion.json").write_bytes(raw)
    with pytest.raises(ValueError):
        m.audit(
            out, profile, sha256(raw).hexdigest(), audit_path=tmp_path / "audit.json"
        )
    assert not (tmp_path / "audit.json").exists()


def test_completion_pin_failure_does_not_write_audit(tmp_path: Path) -> None:
    m, profile, out = pack(tmp_path)
    m.run(out, profile)
    with pytest.raises(ValueError, match="new completion pin"):
        m.audit(out, profile, "0" * 64, audit_path=tmp_path / "audit.json")
    assert not (tmp_path / "audit.json").exists()


@pytest.mark.parametrize("early", [None, "before-reverse", "mass-exit"])
def test_only_explicit_fabricated_content_identities_are_admitted(
    tmp_path: Path, early: str | None
) -> None:
    from lineage_fixtures import write_artificial_pack

    m = runner()
    profile = write_artificial_pack(tmp_path / "inputs", early=early)
    m.profile_check(profile, tmp_path / "out")
    profile["pins"]["report"]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="unlisted fabricated profile"):
        m.profile_check(profile, tmp_path / "out")


def test_symlink_ancestor_cannot_hide_a_retained_input_or_output(
    tmp_path: Path,
) -> None:
    m, profile, out = pack(tmp_path)
    link = tmp_path / "aliased-repository"
    link.symlink_to(ROOT, target_is_directory=True)
    profile["inputs"]["report"] = str(
        link / "docs/adr/experiments/0224-retained-trace-result/report.json"
    )
    with pytest.raises(ValueError, match="path isolation"):
        m.profile_check(profile, out)
    from lineage_fixtures import write_artificial_pack

    clean = write_artificial_pack(tmp_path / "clean-inputs")
    with pytest.raises(ValueError, match="path isolation"):
        m.profile_check(
            clean, link / "docs/adr/experiments/forbidden-artificial-output"
        )


def test_file_native_and_historical_execution_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    m, profile, out = pack(tmp_path)
    hooks = []
    monkeypatch.setattr(m.sys, "addaudithook", hooks.append)
    m.guard(profile, out, None, read_only=False)
    hook = hooks[0]
    for event, args in [
        ("open", (str(m.CONTRACT), "wb", os.O_WRONLY | os.O_TRUNC)),
        ("open", (str(tmp_path / "unlisted"), "rb", os.O_RDONLY)),
        ("import", ("tudatpy",)),
        ("import", ("ctypes",)),
        (
            "exec",
            (compile("pass", str(m.HERE.with_name("0219-phase-bounds.py")), "exec"),),
        ),
        ("subprocess.Popen", ()),
        ("socket.__new__", ()),
        ("ctypes.dlopen", ()),
        ("os.mkdir", (str(tmp_path / "unlisted"),)),
        ("os.remove", (str(out / "report.json"),)),
        ("os.rmdir", (str(out),)),
    ]:
        with pytest.raises(ValueError):
            hook(event, args)
    hook("open", (str(m.CONTRACT), "rb", os.O_RDONLY))
    hook("open", (profile["inputs"]["report"], "rb", os.O_RDONLY))
    hooks.clear()
    m.guard(profile, out, tmp_path / "audit.json", read_only=True)
    with pytest.raises(ValueError):
        hooks[0]("open", (str(out / "report.json"), "wb", os.O_WRONLY))


def test_evidence_byte_cap_and_exclusive_first_write(tmp_path: Path) -> None:
    m = runner()
    target = tmp_path / "evidence.json"
    with pytest.raises(ValueError, match="evidence byte cap"):
        m.save(target, {"data": "x" * 1024}, m.Budget(), cap=1024)
    assert not target.exists()
    original = m.save(target, {"first": True}, m.Budget(), cap=1024)
    with pytest.raises(FileExistsError):
        m.save(target, {"first": False}, m.Budget(), cap=1024)
    assert target.read_bytes() == original


def test_separate_audit_late_failure_removes_own_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    m, profile, out = pack(tmp_path)
    m.run(out, profile)
    target = tmp_path / "audit.json"
    b = m.Budget()
    read = b.read

    def late(path: Path, *, source: bool = True, cap: int = 4194304) -> bytes:
        value = read(path, source=source, cap=cap)
        if path == target:
            raise ValueError("late audit finalization failure")
        return value

    monkeypatch.setattr(b, "read", late)
    with pytest.raises(ValueError, match="late audit finalization"):
        m.audit(
            out,
            profile,
            sha256((out / "completion.json").read_bytes()).hexdigest(),
            audit_path=target,
            budget=b,
        )
    assert not target.exists()
    assert (out / "completion.json").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("scope", "retained"),
        ("new_bounds", False),
        ("source_inventory_bytes", 0),
        ("contract_sha256", "0" * 64),
    ],
)
def test_rechained_new_head_cannot_change_identity_or_zero_types(
    tmp_path: Path, field: str, value: Any
) -> None:
    m, profile, out = pack(tmp_path)
    m.run(out, profile)
    report = m.decode((out / "report.json").read_bytes())
    report[field] = value
    (out / "report.json").write_bytes(m.wire(report))
    receipt = m.decode((out / "receipt.json").read_bytes())
    receipt["report_sha256"] = sha256((out / "report.json").read_bytes()).hexdigest()
    (out / "receipt.json").write_bytes(m.wire(receipt))
    completion = m.decode((out / "completion.json").read_bytes())
    completion["receipt_sha256"] = sha256(
        (out / "receipt.json").read_bytes()
    ).hexdigest()
    (out / "completion.json").write_bytes(m.wire(completion))
    with pytest.raises(ValueError, match="new output identity"):
        m.audit(
            out,
            profile,
            sha256((out / "completion.json").read_bytes()).hexdigest(),
            audit_path=tmp_path / "audit.json",
        )


def test_dispatcher_deadline_covers_successful_child_and_removes_late_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    m, profile, out = pack(tmp_path)
    profile_path = tmp_path / "profile.json"
    profile_path.write_bytes(m.wire(profile))
    now = [0]
    b = m.Budget(started_ns=0, clock=lambda: now[0])
    monkeypatch.setattr(m, "Budget", lambda **kwargs: b)
    monkeypatch.setattr(
        m,
        "sys",
        SimpleNamespace(
            flags=SimpleNamespace(isolated=True, no_site=True),
            dont_write_bytecode=True,
            executable=sys.executable,
        ),
    )

    def late_child(*args: Any, **kwargs: Any) -> Any:
        out.mkdir()
        (out / "attempt.json").write_bytes(m.wire({"invocation_id": b.invocation_id}))
        (out / "completion.json").write_bytes(
            m.wire({"invocation_id": b.invocation_id})
        )
        now[0] = m.WALL_NS
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(m.subprocess, "run", late_child)
    assert m.main(["artificial", str(profile_path), str(out)]) == 3
    assert (out / "attempt.json").exists() and not (out / "completion.json").exists()


def test_owned_cleanup_preserves_foreign_completion(tmp_path: Path) -> None:
    m = runner()
    owner, marker = tmp_path / "attempt.json", tmp_path / "completion.json"
    owner.write_bytes(m.wire({"invocation_id": "foreign"}))
    marker.write_bytes(b"foreign evidence\n")
    m.owned_cleanup(marker, owner, "ours")
    assert marker.read_bytes() == b"foreign evidence\n"


@pytest.mark.parametrize(
    "value",
    [
        "0." + "0" * 1023 + "1",
        "1." + "2" * 256,
        "1E+513",
        "1E-513",
        "1e+2",
        "NaN",
        "Infinity",
    ],
)
def test_both_numeric_readers_reject_oversized_or_noncanonical_endpoints(
    value: str,
) -> None:
    m = runner()
    c = m.contract(m.Budget())
    first = m.load_private("core")._Numbers(c["future_caps"], lambda: None)
    second = m.load_private("audit")._Audit(c, lambda: None, lambda *args: None)
    for parse in (first.endpoint, second.number):
        with pytest.raises(ValueError):
            parse(value)


def test_both_exact_readers_bound_rational_components_before_operations() -> None:
    from fractions import Fraction

    m = runner()
    c = m.contract(m.Budget())
    first = m.load_private("core")._Numbers(c["future_caps"], lambda: None)
    second = m.load_private("audit")._Audit(c, lambda: None, lambda *args: None)
    for numbers in (first, second):
        for value in (Fraction(1 << 4096), Fraction(1, 1 << 4096)):
            with pytest.raises(ValueError, match="component.*cap"):
                numbers.bounded(value)
        with pytest.raises(ValueError, match="cap.*before arithmetic"):
            numbers.subtract(Fraction(1 << 4095), Fraction(-(1 << 4095)))
        with pytest.raises(ValueError, match="cap.*before arithmetic"):
            numbers.divide(Fraction(1 << 4095), Fraction(1, 3))
        with pytest.raises(ValueError):
            numbers.divide(Fraction(0), Fraction(0))
        assert numbers.subtract(Fraction(5, 7), Fraction(2, 3)) == Fraction(1, 21)
        assert numbers.divide(Fraction(0), Fraction(5, 7)) == 0
        assert numbers.divide(Fraction(5, 7), Fraction(5, 7)) == 1


def test_event_count_cap_is_checked_before_malformed_tree_traversal() -> None:
    from lineage_fixtures import fabricated_archive, reseal

    m = runner()
    c = m.contract(m.Budget())
    archive = fabricated_archive()
    trace = archive["report"]["rows"][0]["trace"]
    trace["events"] = [trace["events"][0]] * 8193
    reseal(trace)
    core = m.load_private("core")
    with pytest.raises(ValueError, match="event cap"):
        core.analyze(
            archive,
            c,
            scope=profile_scope(),
            check=lambda: None,
            charge=lambda *args: None,
        )
    verifier = m.load_private("audit")
    with pytest.raises(ValueError, match="event cap"):
        verifier.verify(
            archive,
            c,
            {},
            scope=profile_scope(),
            check=lambda: None,
            charge=lambda *args: None,
        )


def profile_scope() -> str:
    return "artificial-saved-lineage"


def test_source_symbol_statement_links_match_only_pinned_text() -> None:
    m = runner()
    for reference in m.SOURCE_REFERENCES:
        line = (
            (ROOT / reference["path"])
            .read_text()
            .splitlines()[reference["line"] - 1]
            .strip()
        )
        assert (
            line == reference["statement"]
            if "statement" in reference
            else line.startswith("def " + reference["symbol"] + "(")
        )


def test_oversized_analysis_cannot_publish_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    m, profile, out = pack(tmp_path)
    monkeypatch.setattr(
        m,
        "load_private",
        lambda part: SimpleNamespace(
            analyze=lambda *args, **kwargs: {
                "status": "lineage-qualified-attribution-unresolved",
                "payload": "x" * 1048576,
            }
        ),
    )
    with pytest.raises(ValueError, match="evidence byte cap"):
        m.run(out, profile)
    assert (out / "attempt.json").exists() and not (out / "completion.json").exists()


def test_auditor_reserve_exhaustion_cannot_publish_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    m, profile, out = pack(tmp_path)
    report = m.run(out, profile)

    def oversized(*args: Any, **kwargs: Any) -> dict[str, Any]:
        for key, count in report["work"].items():
            kwargs["charge"](key, count)
        return {"counts": report["work"], "payload": "x" * 65536}

    monkeypatch.setattr(
        m, "load_private", lambda part: SimpleNamespace(verify=oversized)
    )
    target = tmp_path / "audit.json"
    with pytest.raises(ValueError, match="combined audit byte cap"):
        m.audit(
            out,
            profile,
            sha256((out / "completion.json").read_bytes()).hexdigest(),
            audit_path=target,
        )
    assert not target.exists()


def test_deadline_at_completion_fsync_removes_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    m, profile, out = pack(tmp_path)
    now = [0]
    b = m.Budget(started_ns=0, clock=lambda: now[0])
    sync = m.sync_dir

    def late_sync(path: Path) -> None:
        sync(path)
        if (out / "completion.json").exists():
            now[0] = m.WALL_NS

    monkeypatch.setattr(m, "sync_dir", late_sync)
    with pytest.raises(ValueError, match="deadline exhausted"):
        m.run(out, profile, budget=b)
    assert not (out / "completion.json").exists()
