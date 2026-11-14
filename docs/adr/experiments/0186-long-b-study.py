"""Private ADR0185 study; injected fixtures and the future live route are disjoint."""
from __future__ import annotations

# ruff: noqa: E402 -- Include startup in the phase budget.
from time import monotonic
PROCESS_START = monotonic()

from collections.abc import Callable
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = Path("docs/adr/experiments")
CONTRACT = "ADR0185"
LEGACY_PIN = "e0937a7c4528febf84f5016a6d3d92148bbab1554b8f6d8c8b41ef3258bc754b"
FAILURES = (ValueError, RuntimeError, ImportError, OSError, ArithmeticError, TypeError, KeyError,
            IndexError, AttributeError)
PROFILES = ("normal", "tighter")
type Row = dict[str, Any]
type Check = Callable[[], None]


def require(ok: bool, label: str) -> None:
    if not ok:
        raise ValueError(label)


def load(root: Path, name: str, expected: str | None = None) -> ModuleType:
    path = root / ARTIFACTS / name
    raw = path.read_bytes()
    require(expected is None or sha256(raw).hexdigest() == expected, "source hash: " + name)
    module = ModuleType("r539_study_" + path.stem.replace("-", "_"))
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def select_samples(profile: Row, report: Row) -> list[tuple[str, Row, int | None]]:
    """Choose completed RHS rows in callback order, including rejected trials."""
    rhs = [r for r in report["rhs"] if r["profile"] == profile["name"] and r.get("completed") is True]
    require(all(a["index"] < b["index"] for a, b in zip(rhs, rhs[1:])), "RHS records are not in ordinal order")
    first = rhs[:7]
    require([r["index"] for r in first] == list(range(7)), "first seven RHS unavailable")
    require(any(r["lo_s"] != 0 for r in first), "selected RHS needs nonzero low epoch")
    later: list[Row] = []
    for start in range(300, 600, 50):
        row = next((r for r in rhs if start < r["elapsed_s"] <= start + 50), None)
        require(row is not None, f"missing RHS extension interval ({start},{start+50}]")
        later.append(row)
    require(len({r["global_index"] for r in first + later}) == 13, "RHS samples overlap")
    selected = [("output", r, None) for r in profile["outputs"]]
    require([r["index"] for _, r, _ in selected] == list(range(13)), "thirteen output samples required")
    for r in first + later:
        owners = [trial["index"] for trial in report["trials"]
                  if trial["rhs_start"] <= r["global_index"] < trial["rhs_end"]]
        require(len(owners) <= 1, "overlapping trial membership")
        selected.append(("rhs", r, owners[0] if owners else None))
    return selected


def check_samples(profile: Row, report: Row, bundle: Row, reference: ModuleType,
                  legacy: ModuleType, budget: Any) -> None:
    for kind, row, trial_index in select_samples(profile, report):
        budget.check()
        hi, lo = row["hi_tdb_s"], row["lo_s"]
        entry = {"profile": profile["name"], "kind": kind, "index": row["index"], "trial_index": trial_index,
                 "progress": {}, "hi_tdb_s": hi, "exact_tdb_s": str(Fraction(hi)+Fraction(lo))}
        report["observations"].append(entry)
        entry["assessment"] = reference.assess_observation(
            bundle["initial"], row["motion"], legacy.body_rows(bundle, row), row["geometry"],
            bundle["gm_m3_s2"], bundle["radii_m"], budget.event, budget.check, progress=entry["progress"])
        require(entry["assessment"]["passed"], "required source/force/assembly gate")


def compare(report: Row, reference: ModuleType, name: str, index: int,
            left: list[float], right: list[float], limits: tuple[float, float]) -> None:
    assessment = reference.compare_states(left, right, *limits)
    delta = [float(b)-float(a) for a, b in zip(left, right, strict=True)]
    diff = {"vector": delta, "position_norm_m": math.hypot(*delta[:3]), "velocity_norm_m_s": math.hypot(*delta[3:])}
    require(all(math.isfinite(v) for v in (*delta, diff["position_norm_m"], diff["velocity_norm_m_s"])),
            "nonfinite signed residual")
    t0 = report["inputs"]["initial"]["epoch_tdb_s"]
    report["comparisons"].append({"name": name, "index": index, "epoch_tdb_s": t0 + 50*index,
                                  "assessment": assessment, "difference": diff})
    group = report["comparison_summary"].setdefault(name, {"prefix": None, "extension": None, "endpoint": None})
    extent = "prefix" if index < 7 else "extension"
    maxima = group[extent]
    group[extent] = {key: max(diff[key], maxima[key]) if maxima is not None else diff[key]
                     for key in ("position_norm_m", "velocity_norm_m_s")}
    if index == (6 if name.startswith("prefix_") else 12):
        group["endpoint"] = diff
    require(assessment["passed"], "trajectory comparison: " + name)


def runtime_identity(root: Path, budget: Any, report: Row, legacy: ModuleType, tested: dict[str, str]) -> Row:
    """Only called in a separately authorized future reference process."""
    key = ARTIFACTS / "0141-short-coast-inputs.py"
    adapter = load(root, key.name, report["inputs"]["protected_sha256"][str(key)])
    from space_nav import ephemeris
    require(ephemeris._kernels_loaded == bool(report["identities"]), "fresh/retained kernel pool")
    extras = tuple(root / name for name in tested if name.startswith(str(ARTIFACTS / "0186-long-b-")))
    with legacy.native_observer(budget, report):
        return adapter.runtime_identity(budget.check, extras + (
            root / ARTIFACTS / "0142-short-coast-runner.py", root / "tests/test_r5_short_coast_runner.py"))


def check_counts(report: Row, real: bool) -> None:
    nrhs = len(report["rhs"])
    expected = {"identities": 2, "native_arcs": 2, "native_guard_reads": 5412,
                "native_telemetry": 26, "native_reference_fields": 156, "solves": 2,
                "states": 4*(nrhs+13), "body_checks": 156, "moon_earth_checks": 52,
                "source_rows": 156, "reference_fields": 1248, "model_totals": 52,
                "binary64_fields": 3*(nrhs+26), "dynamic_totals": nrhs+26,
                "rhs": nrhs, "trials": len(report["trials"])}
    if real:
        expected.update(initializations=1, metadata=30)
    for key, value in expected.items():
        count = report["counts"][key]
        require(count["attempted"] == count["completed"] == value, "completed count: " + key)
    for key in ("identities", "native_arcs", "native_guard_reads", "solves", "states",
                *(("initializations", "metadata") if real else ())):
        count = report["counts"][key]
        require(count["returned"] == count["completed"], "returned count: " + key)
    exact = sum(3 if row["exact_tdb_s"] == str(Fraction(row["hi_tdb_s"])) else 6
                for row in report["observations"])
    record = report["counts"]["record_evaluations"]
    require(156 <= record["attempted"] == record["completed"] == exact <= 312, "sampled record count")


def execute(path: Path, *, root: Path = ROOT, clock: Callable[[], float] = monotonic,
            started_s: float | None = None, manifest_sha256: str | None = None,
            inputs_loader: Callable[[Path, Check], Row] | None = None,
            identity_provider: Callable[[], Row] | None = None, provider: Callable[..., Any] | None = None,
            native_adapter: ModuleType | None = None) -> Row:
    """Prepare evidence from two independent B propagation paths."""
    injected = (inputs_loader, identity_provider, provider, native_adapter)
    real = all(x is None for x in injected) and clock is monotonic
    if real:
        require(manifest_sha256 is not None and started_s is not None and started_s <= PROCESS_START,
                "external launcher and preparation digest required")
        require(not any(n.split(".")[0] in {"numpy", "scipy", "spiceypy", "tudatpy", "space_nav"}
                        for n in sys.modules), "fresh process required")
    else:
        require(all(x is not None for x in injected), "injected mode requires all non-live adapters")
    start = clock() if started_s is None else started_s

    def startup_check() -> None:
        elapsed = clock()-start
        require(math.isfinite(elapsed) and 0 <= elapsed < 60., "study deadline")

    legacy = load(root, "0180-split-study.py", LEGACY_PIN)
    budget = SimpleNamespace(clock=clock, start_s=start, counts={}, ledger=[], check=startup_check)
    marker, receipt = path.with_suffix(".attempt.json"), path.with_suffix(".receipt.json")
    require(not any(p.exists() for p in (path, marker, receipt)), "exclusive evidence already exists")
    report: Row = {
        "contract": CONTRACT, "status": "partial", "adapter_mode": "reference" if real else "injected-test",
        "origin": "SSB", "orientation": "J2000", "time_scale": "TDB", "aberration_correction": "NONE",
        "position_units": "m", "velocity_units": "m/s", "acceleration_units": "m/s^2",
        "budget_s": 60., "duration_s": 600., "model": "B", "model_a_propagations": 0,
        "gm_acquisitions": 0, "optimizer_calls": 0, "scientific_verified": False,
        "mission_accuracy_verified": False, "continuous_safety_verified": False,
        "rhs": [], "trials": [], "node_table": [], "profiles": [], "observations": [],
        "state_requests": [], "unavailable": [], "comparisons": [], "comparison_summary": {}, "native_profiles": [],
        "identities": {}, "native_metadata_returns": [], "counts": budget.counts,
        "ledger": budget.ledger, "finalization_gate": "failed",
    }
    with marker.open("x", encoding="utf-8") as stream:
        json.dump({"contract": CONTRACT, "started_s": start, "adapter_mode": report["adapter_mode"]}, stream)
        stream.flush()
    with path.open("x", encoding="utf-8") as stream, receipt.open("x", encoding="utf-8") as receipt_stream:
        stage = "preflight"
        try:
            budget.check()
            tested: dict[str, str] = {}
            if real:
                report["preparation_manifest_sha256"] = manifest_sha256
                raw = (root / ARTIFACTS / "0186-verification.json").read_bytes()
                require(sha256(raw).hexdigest() == manifest_sha256, "external preparation digest")
                tested = json.loads(raw)["tested_source_sha256"]
                report["tested_source_sha256"] = tested

            def helper(role: str) -> ModuleType:
                name = f"0186-long-b-{role}.py"
                budget.check()
                return load(root, name, tested[str(ARTIFACTS / name)] if real else None)

            assets = helper("inputs")
            if real:
                require(assets.preparation(root, budget.check) == (manifest_sha256, tested), "verified preparation")
            core, reference, native, native_replay = (helper(role) for role in
                                                        ("integrator", "reference", "native", "native-replay"))
            budget = core.Budget(clock, start)
            report["counts"], report["ledger"] = budget.counts, budget.ledger
            loader = inputs_loader if inputs_loader is not None else assets.load_inputs
            bundle = loader(root, budget.check)
            require(bundle["offsets_s"] == list(core.OFFSETS), "frozen 600 s coepochs")
            report["inputs"] = deepcopy(bundle)

            def capture_identity(when: str) -> Row:
                budget.event("identities", "attempt")
                captured = deepcopy(identity_provider() if identity_provider is not None else
                                    runtime_identity(root, budget, report, legacy, tested))
                report["identities"][when] = captured
                budget.event("identities", "return")
                legacy.check_identity(captured, bundle["historical_identity"], bundle["kernel_manifest"])
                require(all(captured[k] == bundle["b_runtime"][k] for k in assets.RUNTIME_KEYS),
                        "archived B common scientific runtime")
                return captured

            def prefix(family: str, name: str, new: list[list[float]], limits: tuple[float, float]) -> None:
                past = bundle["b_prefix"][family][name]
                require(len(past) == 7 and len(new) == 13, "prefix and new coepochs")
                require(all(float(a).hex() == float(b).hex() for a, b in zip(past[0], new[0], strict=True)),
                        "bitwise common starting state")
                for index, (left, right) in enumerate(zip(past, new[:7], strict=True)):
                    budget.check()
                    compare(report, reference, f"prefix_{family}_{name}", index, left, right, limits)

            stage = "identity-before"
            before = capture_identity("before")
            budget.event("identities", "complete")
            native_limits, oracle_limits = (.01, 1e-5), (.001, 1e-6)
            native_nodes = {}
            for name in PROFILES:
                stage = "native-" + name
                row = native.solve_profile(bundle, name, report, budget, adapter=native_adapter)
                nodes = native_replay.replay_profile(row, bundle, check=budget.check, event=budget.event)
                require(nodes is not None, "incomplete native B profile")
                native_nodes[name] = [node["state"] for node in nodes]
                stage = "native-prefix-" + name
                prefix("native", name, native_nodes[name], native_limits)
            stage = "native-step-comparison"
            for j, (left, right) in enumerate(zip(native_nodes["normal"], native_nodes["tighter"], strict=True)):
                budget.check()
                compare(report, reference, "native_step", j, left, right, native_limits)
            stage = "node-table"
            state_provider = provider if provider is not None else legacy.real_provider
            core.fill_node_table(bundle, report, state_provider, budget)
            outputs = {}
            for name in PROFILES:
                stage = "solve-" + name
                profile = core.solve_profile(bundle, name, report, state_provider, budget)
                states = outputs[name] = []
                for output in profile["outputs"]:
                    output["motion_assessment"] = reference.assess_motion(bundle["initial"], output["motion"])
                    require(output["motion_assessment"]["passed"], "output assembly bound")
                    motion = output["motion"]
                    states.append(motion["position_m"] + motion["velocity_m_s"])
                stage = "sampled-reference-" + name
                check_samples(profile, report, bundle, reference, legacy, budget)
                stage = "dop853-prefix-" + name
                prefix("dop853", name, states, oracle_limits)
            stage = "trajectory-comparisons"
            for j, (a, b, c) in enumerate(zip(native_nodes["tighter"], outputs["normal"], outputs["tighter"], strict=True)):
                budget.check()
                compare(report, reference, "native_tighter", j, a, c, native_limits)
                compare(report, reference, "oracle_step", j, b, c, oracle_limits)
            stage = "identity-after"
            require(capture_identity("after") == before, "before/after runtime identity")
            require(loader(root, budget.check) == report["inputs"], "before/after input identity")
            if real:
                require(assets.preparation(root, budget.check) == (manifest_sha256, tested), "final tested hashes")
            budget.event("identities", "complete")
            stage = "counts"
            check_counts(report, real)
            require(len(report["comparisons"]) == 67 and len(report["observations"]) == 52, "complete B comparisons and samples")
            report["status"] = "passed"
        except FAILURES as error:
            legacy.failure(report, stage, error)
            for name, ready in (("remaining native profiles", len(report["native_profiles"]) == 2),
                                ("remaining adaptive profiles", len(report["profiles"]) == 2),
                                ("remaining sampled force gates", len(report["observations"]) == 52),
                                ("remaining trajectory gates", len(report["comparisons"]) == 67),
                                ("final identity", len(report["identities"]) == 2)):
                if not ready:
                    report["unavailable"].append(name)
            report["unavailable"].append("full B-only qualification")
        return legacy.finish(stream, receipt_stream, report, budget)
