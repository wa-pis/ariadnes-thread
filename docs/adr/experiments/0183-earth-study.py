"""Prepare a once-only B coast and keep the old A tracks as read-only evidence."""
from __future__ import annotations

# ruff: noqa: E402 -- Include module startup in the study budget.
from time import monotonic
PROCESS_START = monotonic()

from collections.abc import Callable
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = Path("docs/adr/experiments")
CONTRACT = "ADR0182"
LEGACY_STUDY_SHA = "e0937a7c4528febf84f5016a6d3d92148bbab1554b8f6d8c8b41ef3258bc754b"
FAILURES = (ValueError, RuntimeError, ImportError, OSError, ArithmeticError, TypeError, KeyError,
            IndexError, AttributeError)
type Row = dict[str, Any]
type Check = Callable[[], None]


def require(ok: bool, label: str) -> None:
    if not ok:
        raise ValueError(label)


def module_from(path: Path, raw: bytes) -> ModuleType:
    module = ModuleType("study_r537_" + path.stem.replace("-", "_"))
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def load(root: Path, name: str, expected: str | None = None) -> ModuleType:
    path = root / ARTIFACTS / name
    raw = path.read_bytes()
    require(expected is None or sha256(raw).hexdigest() == expected, "source hash: " + name)
    return module_from(path, raw)


def difference(left: list[float], right: list[float]) -> Row:
    require(len(left) == len(right) == 6, "state difference dimensions")
    require(all(type(x) in (int, float) and math.isfinite(x) for x in (*left, *right)),
            "state difference finite numeric operands")
    v = [float(b)-float(a) for a, b in zip(left, right, strict=True)]
    pos, vel = math.hypot(*v[:3]), math.hypot(*v[3:])
    require(math.isfinite(pos) and math.isfinite(vel), "state difference range")
    return {"vector": v, "position_norm_m": pos, "velocity_norm_m_s": vel}


def effect(index: int, epoch_tdb_s: float, a_native: list[float], b_native: list[float],
           a_dop: list[float], b_dop: list[float]) -> Row:
    """Compare signed state effects using the original staged binary64 expression."""
    n, d = difference(a_native, b_native), difference(a_dop, b_dop)
    x = difference(n["vector"], d["vector"])
    pl, vl = 0.02, 2e-5
    return {"index": index, "epoch_tdb_s": epoch_tdb_s, "native": n, "dop853": d, "discrepancy": x,
            "position_above_scale": min(n["position_norm_m"], d["position_norm_m"]) > pl,
            "velocity_above_scale": min(n["velocity_norm_m_s"], d["velocity_norm_m_s"]) > vl,
            "passed": (x["position_norm_m"] <= pl and x["velocity_norm_m_s"] <= vl
                       and (index != 0 or all(v == 0 for v in n["vector"] + d["vector"])))}


def compare(report: Row, reference: ModuleType, name: str, index: int,
            left: list[float], right: list[float], p: float, v: float) -> None:
    result = reference.compare_states(left, right, p, v)
    report["comparisons"].append({"name": name, "index": index, "assessment": result})
    require(result["passed"], "trajectory comparison: " + name)


def runtime_identity(root: Path, budget: Any, report: Row, legacy: ModuleType, tested: dict[str, str]) -> Row:
    # Called only by the future authorized reference phase.
    key = ARTIFACTS / "0141-short-coast-inputs.py"
    adapter = load(root, key.name, report["inputs"]["protected_sha256"][str(key)])
    from space_nav import ephemeris
    require(ephemeris._kernels_loaded == bool(report["identities"]), "fresh/retained kernel pool")
    extras = tuple(root / name for name in tested if name.startswith(str(ARTIFACTS / "0183-earth-")))
    with legacy.native_observer(budget, report):
        return adapter.runtime_identity(budget.check, extras + (
            root / ARTIFACTS / "0142-short-coast-runner.py", root / "tests/test_r5_short_coast_runner.py"))


def execute(path: Path, *, root: Path = ROOT, clock: Callable[[], float] = monotonic,
            started_s: float | None = None, manifest_sha256: str | None = None,
            inputs_loader: Callable[[Path, Check], Row] | None = None,
            identity_provider: Callable[[], Row] | None = None, provider: Callable[..., Any] | None = None,
            native_adapter: ModuleType | None = None) -> Row:
    """Synthetic injection and the future live path are disjoint."""
    real = all(x is None for x in (inputs_loader, identity_provider, provider, native_adapter)) and clock is monotonic
    if real:
        require(manifest_sha256 is not None and started_s is not None and started_s <= PROCESS_START,
                "external launcher and preparation digest required")
        require(not any(n.split(".")[0] in {"numpy", "scipy", "spiceypy", "tudatpy", "space_nav"}
                        for n in sys.modules), "fresh process required")
    else:
        require(inputs_loader is not None and identity_provider is not None and provider is not None
                and native_adapter is not None, "injected mode requires all non-live adapters")
    start = (PROCESS_START if real else clock()) if started_s is None else started_s

    def startup_check() -> None:
        elapsed = clock() - start
        require(math.isfinite(elapsed) and 0 <= elapsed < 60., "study deadline")

    legacy = load(root, "0180-split-study.py", LEGACY_STUDY_SHA)
    budget = SimpleNamespace(clock=clock, start_s=start, counts={}, ledger=[], check=startup_check)
    marker, receipt = path.with_suffix(".attempt.json"), path.with_suffix(".receipt.json")
    require(not any(p.exists() for p in (path, marker, receipt)), "exclusive evidence already exists")
    report: Row = {"contract": CONTRACT, "status": "partial", "adapter_mode": "reference" if real else "injected-test",
                   "origin": "SSB", "orientation": "J2000", "time_scale": "TDB", "aberration_correction": "NONE",
                   "position_units": "m", "velocity_units": "m/s", "acceleration_units": "m/s^2",
                   "budget_s": 60., "gm_acquisitions": 0, "optimizer_calls": 0, "model": "B",
                   "historical_final_identity_complete": False, "mission_accuracy_verified": False,
                   "continuous_safety_verified": False, "scientific_verified": False,
                   "rhs": [], "trials": [], "node_table": [], "profiles": [], "observations": [],
                   "state_requests": [], "unavailable": [], "comparisons": [], "effects": [], "native_profiles": [],
                   "identities": {}, "native_metadata_returns": [], "counts": budget.counts,
                   "ledger": budget.ledger, "finalization_gate": "failed"}
    with marker.open("x", encoding="utf-8") as stream:
        json.dump({"contract": CONTRACT, "started_s": start, "adapter_mode": report["adapter_mode"]}, stream)
        stream.flush()
    with path.open("x", encoding="utf-8") as stream, receipt.open("x", encoding="utf-8") as receipt_stream:
        stage = "preflight"
        try:
            budget.check()
            tested: dict[str, str] = {}
            manifest_path = root / ARTIFACTS / "0183-verification.json"
            if real:
                report["preparation_manifest_sha256"] = manifest_sha256
                raw = manifest_path.read_bytes()
                require(sha256(raw).hexdigest() == manifest_sha256, "external preparation digest")
                tested = json.loads(raw)["tested_source_sha256"]
                report["tested_source_sha256"] = tested

            def helper(name: str) -> ModuleType:
                expected = tested[str(ARTIFACTS / name)] if real else None
                budget.check()
                return load(root, name, expected)

            assets = helper("0183-earth-inputs.py")
            if real:
                require(assets.preparation(root, budget.check) == (manifest_sha256, tested), "verified preparation")
            core = helper("0183-earth-integrator.py")
            budget = core.Budget(clock, start)
            report["counts"], report["ledger"] = budget.counts, budget.ledger
            reference = helper("0183-earth-reference.py")
            native = helper("0183-earth-native.py")
            native_replay = helper("0183-earth-native-replay.py")
            loader = inputs_loader if inputs_loader is not None else assets.load_inputs
            bundle = loader(root, budget.check)
            report["inputs"] = deepcopy(bundle)

            def capture_identity(when: str) -> Row:
                budget.event("identities", "attempt")
                captured = (identity_provider() if identity_provider is not None
                            else runtime_identity(root, budget, report, legacy, tested))
                report["identities"][when] = captured
                budget.event("identities", "return")
                legacy.check_identity(captured, bundle["historical_identity"], bundle["kernel_manifest"])
                if real:
                    require(all(captured[k] == bundle["a_runtime"][k] for k in assets.RUNTIME_KEYS),
                            "A/B common scientific runtime")
                return captured

            stage = "identity-before"
            before = capture_identity("before")
            budget.event("identities", "complete")
            state_provider = provider if provider is not None else legacy.real_provider
            native_nodes: dict[str, list[list[float]]] = {}
            for name in ("normal", "tighter"):
                stage = "native-" + name
                p = native.solve_profile(bundle, name, report, budget, adapter=native_adapter)
                verified = native_replay.replay_profile(p, bundle, check=budget.check, event=budget.event)
                require(verified is not None, "incomplete native B profile")
                native_nodes[name] = [node["state"] for node in verified]
            stage = "native-step-comparison"
            for j, (left, right) in enumerate(zip(native_nodes["normal"], native_nodes["tighter"], strict=True)):
                compare(report, reference, "native_step", j, left, right, .01, 1e-5)
            stage = "node-table"
            core.fill_node_table(bundle, report, state_provider, budget)
            archive = legacy.saved_epochs(root)
            for name in ("normal", "tighter"):
                stage = "solve-" + name
                profile = core.solve_profile(bundle, name, report, state_provider, budget)
                for output in profile["outputs"]:
                    output["motion_assessment"] = reference.assess_motion(bundle["initial"], output["motion"])
                    require(output["motion_assessment"]["passed"], "output assembly bound")
                stage = "sampled-reference-" + name
                legacy.check_samples(profile, report, bundle, reference, budget, archive)
            stage = "trajectory-comparisons"
            outputs = {p["name"]: p["outputs"] for p in report["profiles"]}
            tight_states = []
            for j in range(7):
                states = {name: rows[j]["motion"]["position_m"] + rows[j]["motion"]["velocity_m_s"]
                          for name, rows in outputs.items()}
                tight_states.append(states["tighter"])
                compare(report, reference, "native_tighter", j, native_nodes["tighter"][j], states["tighter"], .01, 1e-5)
                compare(report, reference, "oracle_step", j, states["normal"], states["tighter"], .001, 1e-6)
            stage = "signed-effects"
            for j, t in enumerate(bundle["offsets_s"]):
                budget.check()
                row = effect(j, bundle["initial"]["epoch_tdb_s"] + t, bundle["a_samples"]["native"][j],
                             native_nodes["tighter"][j], bundle["a_samples"]["dop853"][j], tight_states[j])
                report["effects"].append(row)
                require(row["passed"], "signed B-minus-A discrepancy")
            stage = "identity-after"
            require(capture_identity("after") == before, "before/after runtime identity")
            require(json.dumps(loader(root, budget.check), sort_keys=True, allow_nan=False)
                    == json.dumps(report["inputs"], sort_keys=True, allow_nan=False), "before/after input identity")
            if real:
                require(assets.preparation(root, budget.check) == (manifest_sha256, tested), "final tested hashes")
            budget.event("identities", "complete")

            stage = "counts"
            nrhs = len(report["rhs"])
            for key, expected in {"identities": 2, "native_arcs": 2, "native_guard_reads": 2712,
                                  "native_telemetry": 14, "native_reference_fields": 84, "solves": 2,
                                  "states": 4*(nrhs+7), "body_checks": 84, "moon_earth_checks": 28,
                                  "source_rows": 84, "reference_fields": 672, "model_totals": 28,
                                  "binary64_fields": 3*(nrhs+14), "dynamic_totals": nrhs+14,
                                  "rhs": nrhs, "trials": len(report["trials"])}.items():
                counts = budget.counts[key]
                require(counts["attempted"] == counts["completed"] == expected, "completed count: " + key)
            for key in ("identities", "native_arcs", "native_guard_reads", "solves", "states"):
                counts = budget.counts[key]
                require(counts["returned"] == counts["completed"], "returned count: " + key)
            record = budget.counts["record_evaluations"]
            require(84 <= record["attempted"] == record["completed"] <= 168, "record evaluation count")
            if real:
                require(budget.counts["initializations"] == {"attempted": 1, "returned": 1, "completed": 1}
                        and budget.counts["metadata"] == {"attempted": 30, "returned": 30, "completed": 30},
                        "kernel setup and two inventories")
            report["status"] = "passed"
        except FAILURES as error:
            legacy.failure(report, stage, error)
            for name, ready in (("remaining native profiles", len(report["native_profiles"]) == 2),
                                ("remaining B profiles or outputs", len(report["profiles"]) == 2),
                                ("remaining sampled observations or gates", len(report["observations"]) == 28),
                                ("remaining trajectory comparisons or gates", len(report["comparisons"]) == 21),
                                ("remaining signed effects or gates", len(report["effects"]) == 7),
                                ("final identity", len(report["identities"]) == 2)):
                if not ready:
                    report["unavailable"].append(name)
            report["unavailable"].append("full B-only qualification")
        return legacy.finish(stream, receipt_stream, report, budget)
