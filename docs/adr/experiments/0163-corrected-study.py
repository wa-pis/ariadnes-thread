"""Once-only ADR0162 entry point; import alone requests no real states."""

from __future__ import annotations

# ruff: noqa: E402 -- Start includes imports and setup.
from time import monotonic
PROCESS_START = monotonic()

from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Iterator, TextIO

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
HELPERS = tuple("0163-corrected-" + s + ".py" for s in ("inputs", "reference", "integrator", "study", "audit"))
FAILURES = (ValueError, RuntimeError, ImportError, OSError, ArithmeticError, TypeError, KeyError)
Check = Callable[[], None]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(root: Path, name: str, expected: str | None = None) -> ModuleType:
    path = root / "docs/adr/experiments" / name
    raw = path.read_bytes()
    if expected is not None:
        require(sha256(raw).hexdigest() == expected, "helper hash: " + name)
    spec = importlib.util.spec_from_file_location("corrected_private_" + path.stem.replace("-", "_"), path)
    require(spec is not None and spec.loader is not None, "helper loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def fingerprints(root: Path, check: Check) -> dict[str, str]:
    result = {}
    for name in HELPERS:
        check()
        result[name] = sha256((root / "docs/adr/experiments" / name).read_bytes()).hexdigest()
    check()
    return result


def finite_wire(value: Any) -> Any:
    """Invalid raw returns remain explicit evidence; never become valid operands."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        return value if math.isfinite(value) else {"invalid_numeric": repr(value)}
    if type(value) in (tuple, list):
        return [finite_wire(v) for v in value]
    if type(value) is dict:
        return {str(k): finite_wire(v) for k, v in value.items()}
    return {"invalid_type": type(value).__name__, "representation": repr(value)}


def failure(report: dict[str, Any], stage: str, error: BaseException) -> None:
    report["status"] = "failed"
    report.setdefault("error", {"stage": stage, "type": type(error).__name__, "message": str(error)})
    report["scientific_verified"] = False


@contextmanager
def native_observer(budget: Any, report: dict[str, Any]) -> Iterator[None]:
    """Count explicit setup/metadata APIs, not hidden transitive C/FFI calls."""
    import spiceypy
    from tudatpy.interface import spice
    originals = []
    def wrap(module: Any, name: str, operation: str) -> None:
        original = getattr(module, name)
        originals.append((module, name, original))
        def call(*args: Any, **kwargs: Any) -> Any:
            budget.event(operation, "attempt")
            value = original(*args, **kwargs)
            report["native_metadata_returns"].append({"api": name, "operation": operation,
                                                       "args": list(args), "value": value})
            budget.event(operation, "return")
            budget.event(operation, "complete")
            return value
        setattr(module, name, call)
    try:
        wrap(spice, "load_standard_kernels", "initializations")
        wrap(spice, "get_total_count_of_kernels_loaded", "metadata")
        wrap(spiceypy, "ktotal", "metadata")
        wrap(spiceypy, "kdata", "metadata")
        yield
    finally:
        for module, name, original in reversed(originals):
            setattr(module, name, original)


def runtime_identity(root: Path, budget: Any, report: dict[str, Any]) -> dict[str, Any]:
    # This adapter is called only by a separately authorized future real study.
    path = root / "docs/adr/experiments/0141-short-coast-inputs.py"
    expected = report["inputs"]["protected_sha256"][str(path.relative_to(root))]
    adapter = load(root, path.name, expected)
    from space_nav import ephemeris
    require(not report["identities"] or ephemeris._kernels_loaded, "kernel pool lost")
    if not report["identities"]:
        require(not ephemeris._kernels_loaded, "study must initialize fresh kernel pool")
    with native_observer(budget, report):
        return adapter.runtime_identity(budget.check,
            tuple(root / "docs/adr/experiments" / name for name in HELPERS) +
            (root / "docs/adr/experiments/0142-short-coast-runner.py",
             root / "tests/test_r5_short_coast_runner.py"))


def check_identity(actual: dict[str, Any], historical: dict[str, Any], kernels: dict[str, Any]) -> None:
    require(actual["kernels"] == kernels and kernels["loaded_kernel_count"] == 13,
            "ordered thirteen-kernel identity")
    for key in ("versions", "imports", "native_binary", "conda_build", "resource_build",
                "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime"):
        require(actual[key] == historical[key], "frozen runtime identity: " + key)


def real_provider(body: str, hi_tdb_s: float) -> list[float]:
    import spiceypy
    try:
        raw, _light_time = spiceypy.spkezr(body, hi_tdb_s, "J2000", "NONE", "SSB")
    except Exception as error:  # Untyped native boundary only.
        raise ValueError("SPICE state unavailable: " + body) from error
    return raw.tolist() if hasattr(raw, "tolist") else list(raw)


def body_rows(bundle: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return {body: {**deepcopy(bundle["source_rows_template"][body]), **deepcopy(raw),
                   "elapsed_s": row["elapsed_s"], "hi_tdb_s": row["hi_tdb_s"], "lo_s": row["lo_s"]}
            for body, raw in row["bodies"].items()}


def finish(stream: TextIO, receipt_stream: TextIO, report: dict[str, Any], budget: Any) -> dict[str, Any]:
    report["finalization_gate"] = "passed"
    try:
        budget.check()
        report["elapsed_before_flush_s"] = budget.clock()-budget.start_s
        json.dump(finite_wire(report), stream, allow_nan=False, separators=(",", ":"))
        stream.flush()
        budget.check()
        receipt = {"status": report["status"], "finalization_gate": "passed",
                   "elapsed_s": budget.clock()-budget.start_s}
        json.dump(receipt, receipt_stream, allow_nan=False)
        receipt_stream.flush()
        budget.check()
    except FAILURES as error:
        failure(report, "finalization", error)
        report["finalization_gate"] = "failed"
        stream.seek(0)
        stream.truncate()
        json.dump(finite_wire(report), stream, allow_nan=False, separators=(",", ":"))
        stream.flush()
        receipt_stream.seek(0)
        receipt_stream.truncate()
        json.dump({"status": "failed", "finalization_gate": "failed"}, receipt_stream, allow_nan=False)
        receipt_stream.flush()
    return finite_wire(report)


def execute(path: Path, *, root: Path = ROOT, clock: Callable[[], float] = monotonic,
            started_s: float | None = None, inputs_loader: Any = None, references: Any = None,
            identity_provider: Any = None, provider: Any = None, integrate: Any = None) -> dict[str, Any]:
    """Prepare a future once-only study; injected tests never qualify real science."""
    real = all(x is None for x in (inputs_loader, references, identity_provider, provider, integrate)) and clock is monotonic
    if real:
        require(started_s is not None and started_s <= PROCESS_START, "external pre-child baseline required")
        require(not any(n.split(".")[0] in {"numpy", "scipy", "spiceypy", "tudatpy", "space_nav"}
                        for n in sys.modules), "fresh process required")
    start = (PROCESS_START if clock is monotonic else clock()) if started_s is None else started_s
    def startup_check() -> None:
        elapsed = clock()-start
        require(type(elapsed) in (float, int) and math.isfinite(elapsed) and 0 <= elapsed < 60.,
                "process deadline/clock")
    budget = SimpleNamespace(clock=clock, start_s=start, counts={}, ledger=[], check=startup_check)
    marker, receipt = path.with_suffix(".attempt.json"), path.with_suffix(".receipt.json")
    require(not any(p.exists() for p in (path, marker, receipt)), "exclusive evidence already exists")
    report: dict[str, Any] = {"contract": "ADR0162", "status": "partial", "adapter_mode": "reference" if real else "injected-test",
        "origin": "SSB", "orientation": "J2000", "time_scale": "TDB", "aberration_correction": "NONE",
        "position_units": "m", "velocity_units": "m/s", "acceleration_units": "m/s^2",
        "budget_s": 60., "native_propagations": 0, "gm_acquisitions": 0, "optimizer_calls": 0,
        "historical_final_identity_complete": False, "mission_accuracy_verified": False,
        "continuous_safety_verified": False, "scientific_verified": False,
        "rhs": [], "trials": [], "node_table": [], "profiles": [], "observations": [],
        "comparisons": [], "native_guards": [], "identities": {}, "native_metadata_returns": [],
        "counts": budget.counts, "ledger": budget.ledger, "finalization_gate": "failed"}
    with marker.open("x") as stream:
        json.dump({"contract": "ADR0162", "started_s": start, "adapter_mode": report["adapter_mode"]}, stream, allow_nan=False)
        stream.flush()
    with path.open("x") as stream, receipt.open("x") as receipt_stream:
        stage = "preflight"
        try:
            budget.check()
            core_digest = None
            if real:
                prepared = json.loads((root / "docs/adr/experiments/0163-verification.json").read_text())
                require(prepared["preparation_complete"] is True, "preparation incomplete")
                core_digest = prepared["tested_source_sha256"]["docs/adr/experiments/0163-corrected-integrator.py"]
            core = load(root, "0163-corrected-integrator.py", core_digest)
            budget = core.Budget(clock, start)
            report["counts"], report["ledger"] = budget.counts, budget.ledger
            budget.check()
            hashes = fingerprints(root, budget.check)
            report["helper_sha256"] = hashes
            if real:
                manifest_path = root / "docs/adr/experiments/0163-verification.json"
                manifest = json.loads(manifest_path.read_text())
                require(manifest["preparation_complete"] is True, "preparation incomplete")
                for name, digest in hashes.items():
                    require(manifest["tested_source_sha256"]["docs/adr/experiments/"+name] == digest, "tested helper identity")
                report["preparation_manifest_sha256"] = sha256(manifest_path.read_bytes()).hexdigest()
                report["tested_source_sha256"] = manifest["tested_source_sha256"]
                for name, digest in report["tested_source_sha256"].items():
                    budget.check()
                    require(sha256((root / name).read_bytes()).hexdigest() == digest, "tested source identity: " + name)
            inputs_loader = inputs_loader or load(root, HELPERS[0], hashes[HELPERS[0]]).load_inputs
            references = references or load(root, HELPERS[1], hashes[HELPERS[1]])
            bundle = inputs_loader(root, budget.check)
            report["inputs"] = deepcopy(bundle)
            for index in range(7):
                assessment = references.compare_states(bundle["native_samples"]["normal"][index],
                    bundle["native_samples"]["tighter"][index], .01, 1e-5)
                report["comparisons"].append({"name": "native_step", "index": index, "assessment": assessment})
                require(assessment["passed"], "native step comparison")
            stage = "identity-before"
            budget.event("identities", "attempt")
            before = identity_provider() if identity_provider else runtime_identity(root, budget, report)
            report["identities"]["before"] = before
            budget.event("identities", "return")
            check_identity(before, bundle["historical_identity"], bundle["kernel_manifest"])
            budget.event("identities", "complete")
            provider = provider or real_provider
            stage = "node-table-and-native-guards"
            for index, s in enumerate(core.OFFSETS):
                row: dict[str, Any] = {}
                report["node_table"].append(row)
                core.query_bodies(s, bundle["initial"], provider, budget, row)
                for name in ("normal", "tighter"):
                    x = bundle["native_samples"][name][index][:3]
                    for body in core.BODIES:
                        budget.event("native_guards", "attempt")
                        d = math.dist(x, row["bodies"][body]["state_si"][:3])
                        guard = {"profile": name, "index": index, "body": body, "distance_m": d,
                                 "passed": math.isfinite(d) and d > bundle["radii_m"][body]}
                        report["native_guards"].append(guard)
                        budget.event("native_guards", "complete")
                        require(guard["passed"], "native node guard")
            for name in ("normal", "tighter"):
                stage = "solve-" + name
                profile = (integrate or core.solve_profile)(bundle, name, report, provider, budget)
                for output in profile["outputs"]:
                    output["motion_assessment"] = references.assess_motion(bundle["initial"], output["motion"])
                    require(output["motion_assessment"]["passed"], "output assembly bound")
            stage = "trajectory-comparisons"
            outputs = {p["name"]: p["outputs"] for p in report["profiles"]}
            for index in range(7):
                cart = {k: v[index]["motion"]["position_m"]+v[index]["motion"]["velocity_m_s"] for k, v in outputs.items()}
                for name, left, right, pl, vl in (
                    ("native_tighter", bundle["native_samples"]["tighter"][index], cart["tighter"], .01, 1e-5),
                    ("oracle_step", cart["normal"], cart["tighter"], .001, 1e-6)):
                    assessment = references.compare_states(left, right, pl, vl)
                    report["comparisons"].append({"name": name, "index": index, "assessment": assessment})
                    require(assessment["passed"], name + " comparison")
            stage = "selected-force-reference"
            for name in ("normal", "tighter"):
                selected_rhs = [r for r in report["rhs"] if r["profile"] == name and r.get("completed")][:7]
                require([r["index"] for r in selected_rhs] == list(range(7)), "first seven RHS unavailable")
                require(any(r["lo_s"] != 0 for r in selected_rhs), "selected RHS needs nonzero low epoch")
                for kind, rows in (("output", outputs[name]), ("rhs", selected_rhs)):
                    for index, row in enumerate(rows):
                        entry = {"profile": name, "kind": kind, "index": index, "progress": {}}
                        report["observations"].append(entry)
                        entry["assessment"] = references.assess_observation(bundle["initial"], row["motion"],
                            body_rows(bundle, row), row["geometry"], bundle["gm_m3_s2"], bundle["radii_m"],
                            budget.event, budget.check, progress=entry["progress"])
                        require(entry["assessment"]["passed"], "required source/force/assembly gate")
            stage = "identity-after"
            budget.event("identities", "attempt")
            after = identity_provider() if identity_provider else runtime_identity(root, budget, report)
            report["identities"]["after"] = after
            budget.event("identities", "return")
            require(after == before, "before/after runtime identity")
            check_identity(after, bundle["historical_identity"], bundle["kernel_manifest"])
            require(fingerprints(root, budget.check) == hashes, "before/after helper bytes")
            require(json.dumps(inputs_loader(root, budget.check), sort_keys=True, allow_nan=False)
                    == json.dumps(report["inputs"], sort_keys=True, allow_nan=False), "before/after input identity")
            if real:
                require(sha256(manifest_path.read_bytes()).hexdigest() == report["preparation_manifest_sha256"], "final preparation manifest")
                for name, digest in report["tested_source_sha256"].items():
                    budget.check()
                    require(sha256((root/name).read_bytes()).hexdigest() == digest, "final tested source identity: " + name)
            budget.event("identities", "complete")
            for key, expected in {"solves": 2, "states": 3*len(report["rhs"])+21, "native_guards": 42,
                                  "body_checks": 84, "source_rows": 56, "reference_fields": 448, "model_totals": 28,
                                  "binary64_fields": 2*(len(report["rhs"])+14), "dynamic_totals": len(report["rhs"])+14}.items():
                require(budget.counts[key]["attempted"] == budget.counts[key]["completed"] == expected, "completed count: " + key)
            report["status"] = "passed"
            # The separate saved-data audit is still required for scientific success.
            report["scientific_verified"] = False
        except FAILURES as error:
            failure(report, stage, error)
        return finish(stream, receipt_stream, report, budget)


if __name__ == "__main__":
    require(len(sys.argv) == 3, "usage: STUDY OUTPUT EXTERNAL_PRE_CHILD_MONOTONIC")
    result = execute(Path(sys.argv[1]), started_s=float(sys.argv[2]))
    raise SystemExit(0 if result["status"] == "passed" and result["finalization_gate"] == "passed" else 2)
