"""Fixed-state archive replay and an analytic injected A-only study."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import gzip
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/adr/experiments"


def load_study() -> ModuleType:
    path = EVIDENCE / "0180-split-study.py"
    spec = importlib.util.spec_from_file_location("split_coast_study_tests", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


study = load_study()
core = study.load(ROOT, "0180-split-integrator.py")


def checked_json(name: str, hashes: dict[str, str]) -> Any:
    path = EVIDENCE / name
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == hashes[str(path.relative_to(ROOT))]
    return json.loads(gzip.decompress(raw) if name.endswith(".gz") else raw)


@pytest.fixture(scope="module")
def archived() -> tuple[Any, ...]:
    manifest = json.loads((EVIDENCE/"0179-design-inputs.json").read_bytes())
    hashes = manifest["input_sha256"]
    return tuple(checked_json(name, hashes) for name in (
        "0178-verification.json", "0164-corrected-study.json.gz", "0171/screen.json.gz",
        "0168/capture.json", "0174/capture.json", "0177/pair.json.gz",
    ))


@pytest.mark.parametrize("ordinal", range(28))
def test_split_path_replays_archived_bits(archived: Any, ordinal: int) -> None:
    coverage, original, screen, capture21, capture27, paired = archived
    link = coverage["rows_in_r524_order"][ordinal]
    saved = screen["rows"][ordinal]
    profile, kind, index = (link[k] for k in ("profile", "kind", "index"))
    assert [saved[k] for k in ("profile", "kind", "index")] == [profile, kind, index]
    assert link["observation_ordinal"] == saved["observation_ordinal"] == ordinal
    hi = float.fromhex(link["hi_tdb_s_hex"])
    if kind == "rhs":
        row = next(v for v in original["rhs"] if (v["profile"], v["index"]) == (profile, index))
    else:
        row = next(v for v in original["profiles"] if v["name"] == profile)["outputs"][index]
    assert row["hi_tdb_s"].hex() == saved["hi_tdb_s"].hex() == hi.hex()
    raw_states = {body: raw["state_km_km_s"] for body, raw in row["bodies"].items()}
    capture = {"R5.21": capture21, "R5.27": capture27}[link["capture"]]
    returned = capture["ledger"][link["moon_earth_capture_ledger_index"]]
    assert returned["args"] == ["Moon", hi, "J2000", "NONE", "Earth"]
    calls = []
    def provider(body: str, epoch: float, frame: str, abcorr: str, observer: str) -> list[float]:
        assert (epoch.hex(), frame, abcorr) == (hi.hex(), "J2000", "NONE")
        calls.append((body, observer))
        return returned["raw"][0] if observer == "Earth" else raw_states[body]
    bundle = original["inputs"]
    fresh: dict[str, Any] = {}
    budget = core.Budget(lambda: 0., 0.)
    requests: list[dict[str, Any]] = []
    bodies = core.query_bodies(row["elapsed_s"], bundle["initial"], provider, budget, fresh, requests)
    core.build_row(bundle["initial"], row["elapsed_s"], row["correction"], bodies,
                   bundle["gm_m3_s2"], bundle["radii_m"], budget, fresh, moon_earth=fresh["moon_earth"])
    moon = fresh["geometry"]["Moon"]
    assert calls == list(core.REQUESTS) and len(requests) == 4
    assert fresh["lo_s"].hex() == row["lo_s"].hex()
    assert [x.hex() for x in moon["rephasing_m"]] == [x.hex() for x in saved["motion"]["rephasing_m"]]
    if link["evidence_route"] == "r530_confirmed":
        result = paired["rows"][link["r530_row_index"]]
        assert result["observation_ordinal"] == ordinal and result["outcome"] == "confirmed"
        exact = result["exact_separations_m"]["measured_d2"]
        d3 = result["rounded_separation_hex"]["measured"]
        force = result["acceleration_hex"]["measured"]
    else:
        result = saved["static_force"]
        exact = result["exact_separations_m"]["d2"]
        d3 = [x.hex() for x in result["rounded_separation_m"]]
        force = [x.hex() for x in result["binary64_m_s2"]]
    assert moon["pre_round_separation_m"] == exact
    assert [x.hex() for x in moon["separation_m"]] == d3
    assert [x.hex() for x in moon["acceleration_m_s2"]] == force
    for body in ("Sun", "Earth"):
        assert fresh["geometry"][body] == row["geometry"][body]


def test_single_round_after_cancellation() -> None:
    e, g, r = [2.**48, 0., 0.], [.001, 0., 0.], [1000*2.**48, 0., 0.]
    z = [0.]*3
    exact, rounded = core.split_separation(e, g, r, z, z, z)
    assert exact == [1000*Fraction(.001), 0, 0]
    assert [v.hex() for v in rounded] == [1.0.hex(), 0.0.hex(), 0.0.hex()]
    assert 1000*(e[0]+g[0])-r[0] == 0.0


@pytest.mark.parametrize("tie", [1., math.nextafter(1., math.inf)])
def test_final_round_is_nearest_even(tie: float) -> None:
    zeros = [0.]*3
    exact, rounded = core.split_separation(zeros, zeros, [-tie, 0., -0.], zeros, zeros, [2.**-53, 0., -0.])
    assert exact[0] == Fraction(tie)+Fraction(2.**-53)
    assert rounded[0] == (1. if tie == 1. else math.nextafter(tie, math.inf))
    assert rounded[2].hex() == 0.0.hex()


def artificial_bundle() -> dict[str, Any]:
    t0 = 978995455.2304223
    omega = math.sqrt(2e12/1e18)
    samples = [[1e6*math.cos(omega*s), 1e6*math.sin(omega*s), 0.,
                -1e6*omega*math.sin(omega*s), 1e6*omega*math.cos(omega*s), 0.] for s in core.OFFSETS]
    templates = {}
    for body, chain in (("Sun", ((10, 0, 0.),)),
                        ("Moon", ((301, 399, -1e6), (399, 0, 1e6))),
                        ("Earth", ((399, 0, 1e6),))):
        templates[body] = {"body": body, "segments": [{"body": b, "centre": c, "frame": 1, "type": 2,
            "first_tdb_s": t0-512., "last_tdb_s": t0+512., "words": [t0, 512., 0., 0., z]} for b, c, z in chain]}
    kernel = {"loaded_kernel_count": 13, "fixture": "synthetic-no-kernel-load"}
    identity = dict.fromkeys(("versions", "imports", "native_binary", "conda_build", "resource_build",
        "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime"), {})
    identity["kernels"] = kernel
    return {"initial": {"epoch_tdb_s": t0, "position_m": [1e6, 0., 0.],
            "velocity_m_s": [0., 1e6*omega, 0.]}, "offsets_s": list(core.OFFSETS),
            "gm_m3_s2": {"Sun": 1e12, "Moon": 1e12, "Earth": 1.},
            "radii_m": dict.fromkeys(core.BODIES, 1.), "source_rows_template": templates,
            "native_samples": {"normal": deepcopy(samples), "tighter": deepcopy(samples)},
            "input_sha256": {}, "protected_sha256": {}, "historical_identity": identity,
            "kernel_manifest": kernel, "retained_guard_metadata": {}}


def artificial_state(body: str, epoch: float, frame: str, abcorr: str, observer: str) -> list[float]:
    assert (body, observer) in core.REQUESTS and (frame, abcorr) == ("J2000", "NONE")
    z = -1e6 if observer == "Earth" else (1e6 if body == "Earth" else 0.)
    return [0., 0., z, 0., 0., 0.]


def test_injected_full_study_and_independent_audit(tmp_path: Path) -> None:
    ref = study.load(ROOT, "0180-split-reference.py")
    audit = study.load(ROOT, "0180-split-audit.py")
    bundle = artificial_bundle()
    path = tmp_path/"study.json"
    loader = lambda root, check: deepcopy(bundle)  # noqa: E731
    report = study.execute(path, inputs_loader=loader, references=ref,
        provider=artificial_state, identity_provider=lambda: bundle["historical_identity"])
    assert report["status"] == "passed", report.get("error")
    assert report["finalization_gate"] == "passed" and report["scientific_verified"] is False
    assert len(report["observations"]) == 28 and len(report["comparisons"]) == 21
    assert [v["profile"] for v in report["observations"]] == ["normal"]*14+["tighter"]*14
    assert report["counts"]["states"]["completed"] == 4*(len(report["rhs"])+7)
    assert report["counts"]["moon_earth_checks"]["completed"] == 28
    assert report["counts"]["reference_fields"]["completed"] == 448
    assert 84 <= report["counts"]["record_evaluations"]["completed"] <= 168
    checked = audit.audit(path, tmp_path/"audit.json", inputs_loader=loader, references=ref)
    assert checked["audit_status"] == "passed", checked.get("error")
    assert checked["scientific_verified"] is False
    ledger = report["ledger"]
    tighter = max(i for i, event in enumerate(ledger) if event == {"operation": "solves", "phase": "attempt"})
    ledger.insert(1, ledger.pop(tighter))
    with pytest.raises(ValueError, match="normal sampled gates"):
        audit.check_ledger(report, lambda: None)


@pytest.mark.parametrize("profile", ["normal", "tighter"])
def test_exact_observer_parity_with_integrated_corrections(profile: str) -> None:
    bundle = artificial_bundle()
    results = []
    for observed in (False, True):
        budget = core.Budget(lambda: 0., 0.)
        report: dict[str, Any] = {k: [] for k in ("rhs", "trials", "profiles", "node_table", "state_requests")}
        for s in core.OFFSETS:
            row: dict[str, Any] = {}
            core.query_bodies(s, bundle["initial"], artificial_state, budget, row, report["state_requests"])
            report["node_table"].append(row)
        result = core.solve_profile(bundle, profile, report, artificial_state, budget, observed=observed)
        results.append(result["raw_returned"])
        assert any(abs(x) > 1 for x in result["raw_returned"]["y"][0][1:])
        assert any(r["lo_s"] for r in report["rhs"][:7])
        assert budget.counts["states"]["completed"] == 4*(len(report["rhs"])+7)
    assert results[0] == results[1]


def test_normal_sample_failure_prevents_tighter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ref = study.load(ROOT, "0180-split-reference.py")
    bundle = artificial_bundle()
    def fail(*args: Any, **kwargs: Any) -> Any:
        kwargs["progress"]["negative_control"] = "sample error"
        raise ValueError("force gate negative control")
    monkeypatch.setattr(ref, "assess_observation", fail)
    path = tmp_path/"study.json"
    report = study.execute(path, inputs_loader=lambda root, check: bundle, references=ref,
        provider=artificial_state, identity_provider=lambda: bundle["historical_identity"])
    assert [p["name"] for p in report["profiles"]] == ["normal"]
    assert report["status"] == "failed" and report["error"]["stage"] == "selected-force-reference-normal"
    assert report["observations"][0]["progress"]["negative_control"] == "sample error"
    assert "remaining A profiles or outputs" in report["unavailable"]
    receipt = json.loads(path.with_suffix(".receipt.json").read_bytes())
    assert receipt["evidence_sha256"] == sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="exclusive"):
        study.execute(path, inputs_loader=lambda root, check: bundle)


@pytest.mark.parametrize("mutate", ["observer", "frame", "body", "aberration", "epoch_tdb_s", "state_si"])
def test_wrong_state_refused_before_fields(mutate: str) -> None:
    bundle = artificial_bundle()
    row: dict[str, Any] = {}
    budget = core.Budget(lambda: 0., 0.)
    bodies = core.query_bodies(0., bundle["initial"], artificial_state, budget, row, [])
    if mutate == "state_si":
        bodies["Earth"][mutate] = [1.]*6
    else:
        row["moon_earth"][mutate] = "wrong" if mutate != "epoch_tdb_s" else 0.
    with pytest.raises(ValueError, match="mismatch"):
        core.build_row(bundle["initial"], 0., [0.]*6, bodies, bundle["gm_m3_s2"], bundle["radii_m"], budget,
                       row, moon_earth=row["moon_earth"])
    assert "binary64_fields" not in budget.counts


def test_exact_guard_cannot_be_replaced_by_rounded_guard() -> None:
    bundle = artificial_bundle()
    row: dict[str, Any] = {}
    budget = core.Budget(lambda: 0., 0.)
    bodies = core.query_bodies(0., bundle["initial"], artificial_state, budget, row, [])
    bundle["radii_m"]["Moon"] = 1e6
    with pytest.raises(ValueError, match="exact exterior guard"):
        core.build_row(bundle["initial"], 0., [0.]*6, bodies, bundle["gm_m3_s2"], bundle["radii_m"], budget,
                       row, moon_earth=row["moon_earth"])
    assert "binary64_fields" not in budget.counts


def test_state_attempt_cap_and_late_return() -> None:
    bundle = artificial_bundle()
    now = [0.]
    budget = core.Budget(lambda: now[0], 0.)
    requests: list[dict[str, Any]] = []
    row: dict[str, Any] = {}
    def late(body: str, t: float, frame: str, abcorr: str, observer: str) -> list[float]:
        if observer == "Earth":
            now[0] = 60.
        return artificial_state(body, t, frame, abcorr, observer)
    with pytest.raises(ValueError, match="deadline"):
        core.query_bodies(0., bundle["initial"], late, budget, row, requests)
    assert row["moon_earth"]["state_km_km_s"][2] == -1e6
    assert budget.counts["states"] == {"attempted": 4, "returned": 4, "completed": 3}
    assert len(requests) == 4
    now[0] = 0.
    budget.counts["states"]["attempted"] = core.LIMITS["states"]
    with pytest.raises(ValueError, match="attempt cap"):
        core.query_bodies(0., bundle["initial"], late, budget, {}, requests)
    assert len(requests) == 4


@pytest.mark.parametrize(("mode", "expected"), [("ok", "passed"), ("wrong-hash", "failed"), ("late", "failed")])
def test_parent_receipt_without_a_real_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, expected: str,
) -> None:
    launch = study.load(ROOT, "0180-split-launch.py")
    manifest = tmp_path/"prep.json"
    helper = EVIDENCE/"0180-split-study.py"
    manifest.write_text(json.dumps({"preparation_complete": True, "design_input_sha256": {},
        "tested_source_sha256": {str(helper.relative_to(ROOT)): sha256(helper.read_bytes()).hexdigest()}}))
    monkeypatch.setattr(launch, "MANIFEST", manifest)
    monkeypatch.setattr(launch, "snapshot", lambda: {"stub": "frozen"})
    revision = b"a"*40
    def fake_git(*args: str) -> bytes:
        if args == ("branch", "--show-current"):
            return b"dev\n"
        if args == ("status", "--porcelain"):
            return b""
        assert args[0] == "rev-parse"
        return revision+b"\n"
    monkeypatch.setattr(launch, "git", fake_git)
    now = [1.]
    monkeypatch.setattr(launch, "monotonic", lambda: now[0])
    def fake_child(command: list[str], deadline: float) -> dict[str, Any]:
        assert deadline == 65.
        started, name = command[-5:-3]
        output = Path(name)
        output.write_text("{}")
        launch.write_json(output.with_suffix(".attempt.json"), {"started_s": float(started)})
        launch.write_json(output.with_suffix(".receipt.json"), {
            "started_s": float(started), "status": "passed", "elapsed_s": .2,
            "finalization_gate": "passed",
            "evidence_sha256": "corrupt" if mode == "wrong-hash" else sha256(output.read_bytes()).hexdigest(),
        })
        now[0] += 61. if mode == "late" else .5
        return {"returncode": 0, "stderr": ""}
    monkeypatch.setattr(launch, "run_child", fake_child)
    result = launch.launch("study", tmp_path, sha256(manifest.read_bytes()).hexdigest())
    assert result["finalization_gate"] == expected
    assert json.loads((tmp_path/"study.parent-receipt.json").read_bytes()) == result
    with pytest.raises(ValueError, match="once-only"):
        launch.launch("study", tmp_path, sha256(manifest.read_bytes()).hexdigest())



def test_injected_mode_cannot_fall_back_to_native(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ref = study.load(ROOT, "0180-split-reference.py")
    bundle = artificial_bundle()
    def forbidden(*args: Any) -> None:
        pytest.fail("attempted to reach the native boundary")
    monkeypatch.setattr(study, "runtime_identity", forbidden)
    monkeypatch.setattr(study, "real_provider", forbidden)
    report = study.execute(tmp_path/"study.json", inputs_loader=lambda root, check: bundle, references=ref)
    assert report["status"] == "failed"
    assert report["error"]["message"] == "injected identity and state providers required"
    assert not report["state_requests"] and not report["identities"]
