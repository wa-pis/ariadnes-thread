"""Private model B restart from an archived departure cutoff."""
from __future__ import annotations

# ruff: noqa: E402 -- Include startup in the phase deadline.
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
CONTRACT = "ADR0188"
FAILURES = (ValueError, RuntimeError, ImportError, OSError, ArithmeticError, TypeError,
            KeyError, IndexError, AttributeError)
PROFILES = ("normal", "tighter")
PRIOR = {
    "study": "85f54a68afdd9745801088478700cd6e5420f9d060831affffef44b4ffb8669c",
    "integrator": "e0bb9a459b0aa81f281225e00b5db0766f81d3a8e2dff61547756b7c68a77dc6",
    "native": "c9f2908927bcd1bf68678f5ca6db2c43fcf83ee3c399b549d79f2a0fd9cd359d",
    "native-replay": "6306c4626d555429e091341190de0d092f8f6f1d419e305d188fa0ed6eef3833",
    "reference": "4fb366b232c1515e4d6f96d2bc14b77249ed09bed909bbe3d79ac9a29b59e7c5",
}
NATIVE_LIMITS, ADAPTIVE_LIMITS = (.01, 1e-5), (.001, 1e-6)
type Row = dict[str, Any]
type Check = Callable[[], None]


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def load(root: Path, name: str, pin: str | None) -> ModuleType:
    path = root / ARTIFACTS / name
    raw = path.read_bytes()
    require(pin is None or sha256(raw).hexdigest() == pin, "source hash: " + name)
    module = ModuleType("r542_study_" + path.stem.replace("-", "_"))
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def check_start(initial: Row, state: list[float], epoch: float) -> None:
    """The reported solver start must preserve the supplied epoch and six binary64 words."""
    def words(values: list[float]) -> list[str]:
        require(len(values) == 7 and all(type(x) in (int, float) and math.isfinite(x) for x in values),
                "finite initial six-state and epoch")
        return [float(x).hex() for x in values]

    require(words([epoch, *state]) == words([initial["epoch_tdb_s"], *initial["position_m"],
                                            *initial["velocity_m_s"]]), "exact cutoff start")


def runtime_identity(root: Path, budget: Any, report: Row, legacy: ModuleType, tested: dict[str, str]) -> Row:
    key = ARTIFACTS / "0141-short-coast-inputs.py"
    adapter = load(root, key.name, report["inputs"]["protected_sha256"][str(key)])
    from space_nav import ephemeris
    require(ephemeris._kernels_loaded == bool(report["identities"]), "fresh/retained kernel pool")
    prefixes = (str(ARTIFACTS / "0186-long-b-"), str(ARTIFACTS / "0189-post-cutoff-"))
    extras = tuple(root / name for name in tested if name.startswith(prefixes) and name.endswith(".py"))
    with legacy.native_observer(budget, report):
        return adapter.runtime_identity(budget.check, extras + (
            root / ARTIFACTS / "0142-short-coast-runner.py", root / "tests/test_r5_short_coast_runner.py"))


def run_profiles(bundle: Row, report: Row, budget: Any, modules: dict[str, ModuleType],
                 provider: Callable[..., Any], native_adapter: ModuleType | None,
                 set_stage: Callable[[str], None]) -> None:
    old, core, native, replay, reference = (modules[k] for k in PRIOR)
    states: dict[str, list[list[float]]] = {}
    for name in PROFILES:
        set_stage("native-" + name)
        row = native.solve_profile(bundle, name, report, budget, adapter=native_adapter)
        row["coast_mass_kg"] = bundle["mass_kg"]
        nodes = replay.replay_profile(row, bundle, check=budget.check, event=budget.event)
        require(nodes is not None, "incomplete native B profile")
        check_start(bundle["initial"], nodes[0]["state"], nodes[0]["epoch_tdb_s"])
        states[f"native_{name}"] = [node["state"] for node in nodes]

    def compare(name: str, left: str, right: str, limits: tuple[float, float]) -> None:
        for j, (a, b) in enumerate(zip(states[left], states[right], strict=True)):
            budget.check()
            old.compare(report, reference, name, j, a, b, limits)

    set_stage("native-step-comparison")
    compare("native_step", "native_normal", "native_tighter", NATIVE_LIMITS)
    set_stage("node-table")
    core.fill_node_table(bundle, report, provider, budget)
    for name in PROFILES:
        set_stage("solve-" + name)
        profile = core.solve_profile(bundle, name, report, provider, budget)
        profile["coast_mass_kg"] = bundle["mass_kg"]
        rows = states[f"dop853_{name}"] = []
        for output in profile["outputs"]:
            motion = output["motion"]
            output["motion_assessment"] = reference.assess_motion(bundle["initial"], motion)
            require(output["motion_assessment"]["passed"], "output assembly bound")
            rows.append(motion["position_m"] + motion["velocity_m_s"])
        check_start(bundle["initial"], rows[0], profile["outputs"][0]["hi_tdb_s"])
        set_stage("sampled-reference-" + name)
        old.check_samples(profile, report, bundle, reference, modules["legacy"], budget)

    set_stage("trajectory-comparisons")
    # Maintain the archived comparison ordering: native step block, then interleaved pairs.
    for j, (n, a, b) in enumerate(zip(states["native_tighter"], states["dop853_normal"],
                                    states["dop853_tighter"], strict=True)):
        budget.check()
        old.compare(report, reference, "native_tighter", j, n, b, NATIVE_LIMITS)
        old.compare(report, reference, "oracle_step", j, a, b, ADAPTIVE_LIMITS)
    set_stage("direction")
    operands = [
        {"profile": label, "index": j, "epoch_tdb_s": node["hi_tdb_s"],
         "spacecraft": state, "moon": node["bodies"]["Moon"]["state_si"]}
        for label, path in states.items()
        for j, (state, node) in enumerate(zip(path, report["node_table"], strict=True))
    ]
    report["direction"] = modules["direction"].compute(
        operands, bundle["gm_m3_s2"]["Moon"], bundle["radii_m"]["Moon"], budget.check)


def execute(path: Path, *, root: Path = ROOT, clock: Callable[[], float] = monotonic,
            started_s: float | None = None, manifest_sha256: str | None = None,
            inputs_loader: Callable[[Path, Check], Row] | None = None,
            identity_provider: Callable[[], Row] | None = None, provider: Callable[..., Any] | None = None,
            native_adapter: ModuleType | None = None) -> Row:
    """Execute once; an injected path requires every synthetic adapter."""
    injected = (inputs_loader, identity_provider, provider, native_adapter)
    real = all(x is None for x in injected) and clock is monotonic
    if real:
        require(manifest_sha256 is not None and started_s is not None and started_s <= PROCESS_START,
                "external launcher and preparation digest required")
        require(not any(n.split(".")[0] in {"numpy", "scipy", "spiceypy", "tudatpy", "space_nav"}
                        for n in sys.modules), "fresh process required")
    else:
        require(all(x is not None for x in injected), "all synthetic adapters required")
    start = clock() if started_s is None else started_s

    def startup_check() -> None:
        elapsed = clock() - start
        require(math.isfinite(elapsed) and 0 <= elapsed < 60., "study deadline")

    legacy = load(root, "0180-split-study.py", "e0937a7c4528febf84f5016a6d3d92148bbab1554b8f6d8c8b41ef3258bc754b")
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
        "identities": {}, "native_metadata_returns": [], "counts": budget.counts, "ledger": budget.ledger,
        "outward_status": "unavailable", "finalization_gate": "failed",
    }
    with marker.open("x", encoding="utf-8") as stream:
        json.dump({"contract": CONTRACT, "started_s": start, "adapter_mode": report["adapter_mode"]},
                  stream, allow_nan=False)
        stream.flush()
    with path.open("x", encoding="utf-8") as stream, receipt.open("x", encoding="utf-8") as receipt_stream:
        stage = "preflight"
        try:
            budget.check()
            tested: dict[str, str] = {}
            verify = None
            if real:
                raw = (root / ARTIFACTS / "0189-verification.json").read_bytes()
                require(sha256(raw).hexdigest() == manifest_sha256, "external preparation digest")
                report["preparation_manifest_sha256"] = manifest_sha256
                pin = json.loads(raw)["tested_source_sha256"][str(ARTIFACTS / "0189-post-cutoff-prepare.py")]
                verify = load(root, "0189-post-cutoff-prepare.py", pin).verify
                tested = verify(root, manifest_sha256, budget.check)
                report["tested_source_sha256"] = tested

            def new_helper(role: str) -> ModuleType:
                name = f"0189-post-cutoff-{role}.py"
                budget.check()
                return load(root, name, tested[str(ARTIFACTS / name)] if real else None)

            modules = {role: load(root, f"0186-long-b-{role}.py", pin) for role, pin in PRIOR.items()}
            modules.update(direction=new_helper("direction"), legacy=legacy)
            assets = new_helper("inputs")
            budget = modules["integrator"].Budget(clock, start)
            report["counts"], report["ledger"] = budget.counts, budget.ledger
            loader = inputs_loader if inputs_loader is not None else assets.load
            bundle = loader(root, budget.check)
            require(bundle["offsets_s"] == list(modules["integrator"].OFFSETS), "frozen 600 s coepochs")
            mass, dry = bundle["mass_kg"], bundle["mass_arithmetic"]["dry_mass_kg"]
            require(type(mass) in (int, float) and type(dry) in (int, float)
                    and math.isfinite(mass) and 0 < dry < mass, "cutoff mass and dry-mass guard")
            check_start(bundle["initial"], bundle["cutoff"]["position_m"] + bundle["cutoff"]["velocity_m_s"],
                        bundle["cutoff"]["epoch_tdb_s"])
            require(bundle["cutoff"]["label"] == "departure-cutoff"
                    and bundle["cutoff"]["origin"] == "SSB" and bundle["cutoff"]["orientation"] == "J2000"
                    and bundle["coast"]["constant_mass_metadata_kg"] == mass
                    and bundle["coast"]["thrust_n"] == bundle["coast"]["mass_flow_kg_s"] == 0,
                    "cutoff handoff and unpowered mass metadata")
            report["inputs"] = deepcopy(bundle)
            report["coast_mass_kg"] = mass

            def capture(when: str) -> Row:
                budget.event("identities", "attempt")
                value = deepcopy(identity_provider() if identity_provider is not None else
                                 runtime_identity(root, budget, report, legacy, tested))
                report["identities"][when] = value
                budget.event("identities", "return")
                legacy.check_identity(value, bundle["historical_identity"], bundle["kernel_manifest"])
                require(all(value[k] == bundle["b_runtime"][k] for k in assets.RUNTIME_KEYS),
                        "archived B common scientific runtime")
                return value

            stage = "identity-before"
            before = capture("before")
            budget.event("identities", "complete")
            def set_stage(value: str) -> None:
                nonlocal stage
                stage = value

            run_profiles(bundle, report, budget, modules, provider if provider is not None else legacy.real_provider,
                         native_adapter, set_stage)
            stage = "identity-after"
            require(capture("after") == before, "before/after runtime identity")
            require(loader(root, budget.check) == report["inputs"], "before/after input identity")
            if verify is not None:
                require(verify(root, manifest_sha256, budget.check) == tested, "final tested hashes")
            budget.event("identities", "complete")
            stage = "counts"
            modules["study"].check_counts(report, real)
            require(len(report["comparisons"]) == 39 and len(report["observations"]) == 52
                    and len(report["direction"]["rows"]) == 52 and len(report["direction"]["net_ranges"]) == 4,
                    "complete post-cutoff comparisons and samples")
            report["status"] = "passed"
        except FAILURES as error:
            legacy.failure(report, stage, error)
            if len(report["comparisons"]) != 39:
                report["unavailable"].append("remaining profile comparisons")
            if len(report["observations"]) != 52:
                report["unavailable"].append("remaining source/force samples")
            if len(report["identities"]) != 2:
                report["unavailable"].append("final identity")
            report["unavailable"].append("post-cutoff numerical and direction verdicts")
        return legacy.finish(stream, receipt_stream, report, budget)
