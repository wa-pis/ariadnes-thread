"""Qualify selected-source admission using artificial 17-role provenance only."""

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest

import test_matched_norm_dispatch as legacy_dispatch
from matched_norm_fixtures import (
    ART, ROOT, SCOPE, contract, fabricated_archive as six_role_archive, rechain, wire,
)
from matched_norm_metadata_fixtures import (
    EXTRA_ROLES, SELECTED_ROLES, fabricated_archive, write_artificial_pack,
)

SCRIPT = ART / "0237-matched-norm.py"
HARNESS = Path(__file__).with_name("matched_norm_metadata_dispatch_harness.py")
COUNTS = dict(event_visits=1248, boxes=72, methods=144, oracles=72,
              diagonals=72, comparisons=72, descriptors=72, directed_primitives=3444)
type Row = dict[str, Any]


def load_private(part: str, *, version: str = "0237") -> ModuleType:
    """Load pure private scalar code; never import historical orbit modules."""
    path = ART / f"{version}-matched-norm-{part}.py"
    module = ModuleType(f"_metadata_qualification_{version}_{part}")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def load_dispatcher() -> ModuleType:
    module = ModuleType("_metadata_dispatch_qualification")
    module.__file__ = str(SCRIPT)
    sys.modules[module.__name__] = module
    exec(compile(SCRIPT.read_bytes(), str(SCRIPT), "exec"), module.__dict__)
    return module


def analyze(core: ModuleType, archive: Row, design: Row) -> tuple[Row, Counter[str]]:
    used: Counter[str] = Counter()

    def charge(kind: str, count: int = 1) -> None:
        used[kind] += count

    result = core.analyze(archive, design, scope=SCOPE, check=lambda: None, charge=charge)
    return result, used


def verify(auditor: ModuleType, archive: Row, design: Row, result: Row) -> Row:
    return auditor.verify(archive, design, result, scope=SCOPE, check=lambda: None,
                          charge=lambda kind, count=1: None)


@pytest.fixture(scope="module")
def core() -> ModuleType:
    return load_private("core")


@pytest.fixture(scope="module")
def auditor() -> ModuleType:
    return load_private("audit")


@pytest.fixture(scope="module")
def archive() -> Row:
    return fabricated_archive()


@pytest.fixture(scope="module")
def design() -> Row:
    return contract()


@pytest.fixture(scope="module")
def produced(core: ModuleType, archive: Row, design: Row) -> Row:
    return analyze(core, archive, design)[0]


def test_full_artificial_shape_keeps_six_bindings_and_seals_all_seventeen_roles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, core: ModuleType, auditor: ModuleType,
    design: Row,
) -> None:
    forbidden = {ROOT / item["path"] for item in design["original_input_artifacts"]
                 if item["path"].endswith(".json")}
    forbidden |= {ROOT / path for path in design["motivation"]["reference_only_evidence"]}
    read = Path.read_bytes

    def block_saved_data(path: Path) -> bytes:
        assert path not in forbidden, "qualification must never read saved numerical inputs"
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", block_saved_data)
    saved = fabricated_archive()
    selected = saved["_context"]["source_pins"]
    assert set(selected) == set(SELECTED_ROLES)
    expected_roles = set(SELECTED_ROLES) | set(EXTRA_ROLES)
    metadata = saved["report"]["method_sha256"]
    assert len(metadata) == 17 and set(metadata) == expected_roles
    assert {key: metadata[key] for key in selected} == selected
    assert saved["attempt"]["method_sha256"] == saved["receipt"]["method_sha256"] == metadata
    profile = write_artificial_pack(tmp_path / "inputs")
    for role, path in profile["inputs"].items():
        raw = Path(path).read_bytes()
        assert profile["pins"][role] == dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
    source_bytes = sum(item["bytes"] for item in profile["pins"].values())
    source_bytes += sum((ROOT / item["path"]).stat().st_size for item in design["original_input_artifacts"]
                        if item["path"].endswith(".py"))
    assert source_bytes >= design["original_input_bytes"]
    result, counts = analyze(core, saved, design)
    assert dict(counts) == result["counts"] == COUNTS
    assert verify(auditor, saved, design, result)["status"] == "verified"


def test_seventeen_metadata_roles_preserve_all_artificial_numeric_results_and_provenance(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row, produced: Row,
) -> None:
    old = load_private("core", version="0235")
    baseline, old_counts = analyze(old, six_role_archive(), design)
    assert produced == baseline
    assert produced["counts"] == dict(old_counts) == COUNTS
    assert produced["status"] == "matched-norm-qualified-local-only"
    assert len(produced["rows"]) == 72
    assert all(row["diagonal"]["matches"] for row in produced["rows"])
    assert all(method["contains_oracle"] for row in produced["rows"] for method in row["methods"].values())
    assert len({(row["trace_row"], row["role"], row["source_origin"]) for row in produced["rows"]}) == 72
    assert verify(auditor, archive, design, produced)["counts"] == COUNTS
    with pytest.raises(ValueError, match="source/scope identity"):
        analyze(old, archive, design)


def test_legacy_six_role_shape_remains_exactly_compatible(
    core: ModuleType, auditor: ModuleType, design: Row, produced: Row,
) -> None:
    saved = six_role_archive()
    result, counts = analyze(core, saved, design)
    assert result == produced and dict(counts) == COUNTS
    assert verify(auditor, saved, design, result)["status"] == "verified"


def test_extra_provenance_hashes_are_not_claimed_as_additional_selected_source_files(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row, produced: Row,
) -> None:
    saved = deepcopy(archive)
    for record in ("attempt", "report", "receipt"):
        for role in EXTRA_ROLES:
            saved[record]["method_sha256"][role] = "f" * 64
    rechain(saved)
    # The raw-file wrapper seals metadata; local admission checks only the six sources.
    result, _ = analyze(core, saved, design)
    assert result == produced
    assert verify(auditor, saved, design, result)["status"] == "verified"


@pytest.mark.parametrize("role", SELECTED_ROLES)
@pytest.mark.parametrize("fault", ["missing", "mismatched"])
def test_every_selected_source_is_mandatory_and_hash_exact_before_arithmetic(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row, produced: Row,
    role: str, fault: str,
) -> None:
    saved = deepcopy(archive)
    if fault == "missing":
        del saved["report"]["method_sha256"][role]
    else:
        saved["report"]["method_sha256"][role] = "0" * 64
    _assert_prearithmetic_rejection(core, auditor, saved, design, produced)


@pytest.mark.parametrize("fault", [
    "extra-short", "extra-uppercase", "extra-bool", "extra-null", "extra-integer-key",
    "unknown-role", "partial-extra-shape", "metadata-list", "selected-empty",
    "selected-missing", "selected-extra", "selected-bool", "selected-uppercase",
    "report-scope", "context-scope",
])
def test_full_metadata_and_selected_context_fail_closed_before_arithmetic(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row, produced: Row,
    fault: str,
) -> None:
    saved = deepcopy(archive)
    metadata = saved["report"]["method_sha256"]
    selected = saved["_context"]["source_pins"]
    if fault == "extra-short":
        metadata["anchors"] = "a" * 63
    elif fault == "extra-uppercase":
        metadata["anchors"] = "A" * 64
    elif fault == "extra-bool":
        metadata["anchors"] = True
    elif fault == "extra-null":
        metadata["anchors"] = None
    elif fault == "extra-integer-key":
        metadata[1] = metadata.pop("anchors")
    elif fault == "unknown-role":
        metadata["unlisted"] = metadata.pop("anchors")
    elif fault == "partial-extra-shape":
        del metadata["anchors"]
    elif fault == "metadata-list":
        saved["report"]["method_sha256"] = list(metadata.items())
    elif fault == "selected-empty":
        saved["_context"]["source_pins"] = {}
    elif fault == "selected-missing":
        del selected["bounds"]
    elif fault == "selected-extra":
        selected["anchors"] = metadata["anchors"]
    elif fault == "selected-bool":
        selected["bounds"] = True
    elif fault == "selected-uppercase":
        selected["bounds"] = "A" * 64
    elif fault == "report-scope":
        saved["report"]["scope"] = "retained"
    else:
        saved["_context"]["scope"] = "retained"
    _assert_prearithmetic_rejection(core, auditor, saved, design, produced)


def _assert_prearithmetic_rejection(
    core: ModuleType, auditor: ModuleType, archive: Row, design: Row, produced: Row,
) -> None:
    for component in (core, auditor):
        charged: Counter[str] = Counter()

        def charge(kind: str, count: int = 1) -> None:
            charged[kind] += count

        with pytest.raises(ValueError):
            if component is core:
                component.analyze(archive, design, scope=SCOPE, check=lambda: None, charge=charge)
            else:
                component.verify(archive, design, produced, scope=SCOPE, check=lambda: None, charge=charge)
        assert not charged, "invalid metadata must fail before selected-trace or arithmetic work"


def prepare_dispatch_case(folder: Path) -> Row:
    """Expose a fabricated-only bootstrap case to the qualification driver."""
    folder.mkdir()
    module = load_dispatcher()
    profile = write_artificial_pack(folder / "inputs")
    bootstrap = folder / "bootstrap.py"
    shutil.copyfile(HARNESS, bootstrap)
    config_path = bootstrap.with_suffix(".json")
    output, audit = folder / "result", folder / "audit.json"
    config = dict(script=str(SCRIPT), profile=profile, output=str(output), audit=str(audit),
                  forbidden_real_inputs=[str(ART / name) for name in module.DATA_NAMES],
                  forbid_archive_reads=False, fail_worker_after_success=[])
    config_path.write_bytes(wire(config))
    return dict(profile=profile, bootstrap=bootstrap, config=config_path, output=output, audit=audit)


def invoke(case: Row, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-I", "-S", "-B", str(case["bootstrap"]), *args],
                          capture_output=True, text=True, timeout=35, check=False)


def telemetry(result: subprocess.CompletedProcess[str]) -> list[Row]:
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def digest_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def inventory_bytes(case: Row) -> int:
    module = load_dispatcher()
    inherited = json.loads(module.CONTRACT.read_bytes())
    paths = {case["bootstrap"], case["config"], module.CONTRACT, module.DESIGN}
    paths.update(Path(path) for path in case["profile"]["inputs"].values())
    paths.update(ART / name for name in module.PRIVATE)
    paths.update(ROOT / path for path in inherited["source_bindings"].values())
    return sum(path.stat().st_size for path in paths)


def assert_dispatch(case: Row, result: subprocess.CompletedProcess[str], command: list[str]) -> None:
    rows = telemetry(result)
    dispatched = next(row for row in rows if row.get("harness_dispatch"))
    worker = next(row for row in rows if row.get("harness_entry") and row["role"] == "worker")
    parent_budget = next(row for row in rows if row.get("harness_budget") and row["role"] == "parent")
    worker_budget = next(row for row in rows if row.get("harness_budget") and row["role"] == "worker")
    expected = ["worker", str(parent_budget["started_ns"]), parent_budget["invocation_id"], *command]
    assert dispatched["argv"] == worker["argv"] == expected
    assert len(expected) == (4 if command == ["retained"] else 5)
    assert dispatched["script"] == worker["script"] == str(SCRIPT)
    assert parent_budget["started_ns"] == parent_budget["bootstrap_entry_ns"]
    assert worker_budget["started_ns"] == parent_budget["started_ns"]
    assert worker_budget["invocation_id"] == parent_budget["invocation_id"]
    for row in rows:
        if row.get("harness_complete"):
            assert row["real_input_reads"] == 0
            assert row["artificial_input_reads"] == (7 if row["role"] == "worker" else 0)
        if row.get("harness_budget"):
            assert row["charged_bytes"] == case["bootstrap"].stat().st_size + case["config"].stat().st_size
            assert row["bootstrap_sha256"] == digest_file(case["bootstrap"])
            assert row["config_sha256"] == digest_file(case["config"])
    work = next(row for row in rows if "scientific_work" in row)
    assert work["work"] == COUNTS
    assert all(type(value) is int and value == 0 for value in work["scientific_work"].values())


def _failure_snapshot() -> dict[str, str]:
    folder = ART / "0234-matched-norm-result"
    return {path.name: digest_file(path) for path in folder.iterdir()}


def test_exact_parent_worker_commands_qualify_seventeen_roles_and_keep_consumed_failure(
    tmp_path: Path,
) -> None:
    before = _failure_snapshot()
    case = prepare_dispatch_case(tmp_path / "case")
    first = invoke(case, "retained")
    assert first.returncode == 0, first.stderr
    assert_dispatch(case, first, ["retained"])
    completion_pin = digest_file(case["output"] / "completion.json")
    second = invoke(case, "audit", completion_pin)
    assert second.returncode == 0, second.stderr
    assert_dispatch(case, second, ["audit", completion_pin])
    report = json.loads((case["output"] / "report.json").read_bytes())
    audit = json.loads(case["audit"].read_bytes())
    assert report["stage"] == "R5.59y" and report["scope"] == SCOPE
    assert report["status"] == "matched-norm-qualified-local-only"
    assert audit["status"] == "matched-norm-independently-verified"
    assert audit["completion_sha256"] == completion_pin
    assert report["work"] == audit["work"] == audit["proof"]["counts"] == COUNTS
    assert report["source_inventory_bytes"] == inventory_bytes(case) <= 4 * 1024**2
    assert sum(path.stat().st_size for path in case["output"].iterdir()) + case["audit"].stat().st_size <= 1048576
    assert case["audit"].stat().st_size <= 65536
    assert _failure_snapshot() == before
    assert not (ART / "0234-matched-norm-audit.json").exists()


def test_new_fixed_paths_and_original_profiles_cannot_reuse_the_consumed_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    module = load_dispatcher()
    forbidden = {ART / name for name in module.DATA_NAMES}
    read = Path.read_bytes

    def no_observations(path: Path) -> bytes:
        assert path not in forbidden, "profile inspection must not read saved observations"
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", no_observations)
    profile = module.retained_profile()
    assert module.OUTPUT == ART / "0237-matched-norm-result"
    assert module.AUDIT == ART / "0237-matched-norm-audit.json"
    assert all(name.startswith("0237-") for name in module.PRIVATE)
    module.profile_check(profile, module.OUTPUT, module.AUDIT)
    with pytest.raises(ValueError, match="fixed retained profile"):
        module.profile_check(profile, ART / "0234-matched-norm-result")

    output, audit = tmp_path / "result", tmp_path / "audit.json"
    monkeypatch.setattr(module, "OUTPUT", output)
    monkeypatch.setattr(module, "AUDIT", audit)
    module.profile_check(profile, output, audit)
    output.mkdir()
    previous = output / "attempt.json"
    previous.write_bytes(b"previous attempt\n")
    with pytest.raises(ValueError, match="existing output"):
        module.run(output, profile)
    assert list(output.iterdir()) == [previous]
    assert previous.read_bytes() == b"previous attempt\n" and not audit.exists()


def test_changed_artificial_raw_metadata_is_rejected_before_output(tmp_path: Path) -> None:
    case = prepare_dispatch_case(tmp_path / "case")
    path = Path(case["profile"]["inputs"]["report"])
    path.write_bytes(path.read_bytes() + b" ")
    result = invoke(case, "retained")
    assert result.returncode == 3
    assert not case["output"].exists() and not case["audit"].exists()
    assert all(row["real_input_reads"] == 0 for row in telemetry(result) if row.get("harness_complete"))


@pytest.mark.parametrize("check", [
    "test_all_work_source_time_and_output_caps_precharge_or_fail_closed",
    "test_rechained_outer_status_cannot_disagree_with_independent_analysis",
    "test_late_arithmetic_failure_preserves_first_complete_box_and_progress",
])
def test_versioned_dispatcher_keeps_existing_cap_status_and_partial_evidence_guards(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, check: str,
) -> None:
    monkeypatch.setattr(legacy_dispatch, "SCRIPT", SCRIPT)
    monkeypatch.setattr(legacy_dispatch, "HARNESS", HARNESS)
    monkeypatch.setattr(legacy_dispatch, "write_artificial_pack", write_artificial_pack)
    getattr(legacy_dispatch, check)(tmp_path)


def test_fully_resealed_artificial_bad_extra_metadata_still_fails_before_arithmetic(
    tmp_path: Path,
) -> None:
    module = load_dispatcher()
    saved = fabricated_archive()
    for record in ("attempt", "report", "receipt"):
        saved[record]["method_sha256"]["anchors"] = True
    rechain(saved)
    profile = write_artificial_pack(tmp_path / "invalid-inputs", archive=saved)
    # Test-only explicit fabricated registration; no fixed retained profile is changed.
    profile_pin = sha256(wire({key: value for key, value in profile.items() if key != "inputs"})).hexdigest()
    module.ARTIFICIAL_PROFILES[profile_pin] = "deliberately-invalid-artificial-metadata"
    output = tmp_path / "invalid-result"
    with pytest.raises(ValueError, match="source/scope identity"):
        module.run(output, profile)
    failure = json.loads((output / "failure.json").read_bytes())
    assert failure["completed_rows"] == 0 and failure["partial_rows"] == []
    assert all(value == 0 for value in failure["attempted_work"].values())
    assert not (output / "completion.json").exists() and not (output / "report.json").exists()
