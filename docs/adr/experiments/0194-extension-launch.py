"""Launch the isolated R5.48 study or independent audit with bound receipts."""
from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ART = Path("docs/adr/experiments")
CONTRACT = "ADR0193"
LIMITS = {"study": 60.0, "audit": 10.0}
INPUTS_SHA = "83c2d3761cb4ec64ca96a6a6c8cd618a36765989de436c3858f5593a9073bb6b"
LEGACY_SHA = "e0937a7c4528febf84f5016a6d3d92148bbab1554b8f6d8c8b41ef3258bc754b"
PARENT_SHA = "5ab1bec11c821093f920953ed215ed93ce72d1956cf8fdfd5c821885fc37d958"
GIT = "/opt/homebrew/bin/git"
SCIENTIFIC = {"numpy", "scipy", "tudatpy", "spiceypy", "space_nav"}
FAILURES = (ValueError, RuntimeError, ImportError, OSError, ArithmeticError,
            TypeError, KeyError, IndexError, AttributeError, subprocess.SubprocessError)
type Row = dict[str, Any]
type Check = Callable[[], None]


def require(ok: object, message: str) -> None:
    if not ok:
        raise ValueError(message)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load(name: str, pin: str | None) -> dict[str, Any]:
    """Read and execute one private implementation in its own module scope."""
    path = HERE / name
    source = path.read_bytes()
    require(pin is None or digest(source) == pin, name + " digest")
    module = ModuleType("r548_" + path.stem.replace("-", "_"))
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module.__dict__


def input_helpers() -> dict[str, Any]:
    return load("0194-extension-inputs.py", INPUTS_SHA)


def phase_helper(role: str, pins: Row | None) -> dict[str, Any]:
    name = f"0194-extension-{role}.py"
    return load(name, None if pins is None else pins[str(ART/name)])


def clock_gate(clock: Callable[[], float], start: float, limit: float) -> None:
    require(0 <= clock() - start < limit, f"{limit:g} s phase deadline")


def same_identity(value: Row, bundle: Row, pins: Row) -> None:
    require(value["dirty"] == [] and value["kernels"] == bundle["kernel_manifest"],
            "clean pinned kernel identity")
    for key in ("versions", "imports", "native_binary", "conda_build", "resource_build",
                "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime", "kernels"):
        require(value[key] == bundle["historical_identity"][key] == bundle["b_runtime"][key],
                "frozen runtime: " + key)
    for name, pin in pins.items():
        if name.startswith(str(ART/"0194-extension-")) and name.endswith(".py"):
            require(value["source_sha256"][name] == pin, "extension runtime source identity")


def run_study(
    bundle: Row, provider: Callable[..., Any] | None, native_adapter: Any,
    *, identity_provider: Callable[[], Row] | None, started_s: float | None = None,
    clock: Callable[[], float] = monotonic, pins: Row | None = None,
) -> Row:
    """Run the fixed profiles; only tests may inject external science adapters."""
    injected = identity_provider is not None
    require((injected and provider is not None and native_adapter is not None and pins is None)
            or (not injected and provider is None and native_adapter is None and pins is not None),
            "require all synthetic adapters or verified reference mode")
    start = clock() if started_s is None else started_s
    report: Row = {
        "contract": CONTRACT, "status": "partial", "marker_status": "unavailable",
        "adapter_mode": "injected-test" if injected else "reference",
        "origin": "SSB", "orientation": "J2000", "time_scale": "TDB",
        "aberration_correction": "NONE", "position_units": "m", "velocity_units": "m/s",
        "acceleration_units": "m/s^2", "budget_s": 60.0, "duration_s": 50.0, "model": "B",
        "model_a_propagations": 0, "gm_acquisitions": 0, "optimizer_calls": 0,
        "scientific_verified": False, "mission_accuracy_verified": False,
        "continuous_safety_verified": False,
        "rhs": [], "trials": [], "node_table": [], "profiles": [], "observations": [],
        "state_requests": [], "unavailable": [], "comparisons": [], "comparison_summary": {},
        "native_profiles": [], "identities": {}, "native_metadata_returns": [],
        "counts": {}, "ledger": [],
        "inputs": bundle, "coast_mass_kg": bundle["mass_kg"],
    }
    stage = "preflight"

    def set_stage(value: str) -> None:
        nonlocal stage
        stage = value

    try:
        clock_gate(clock, start, LIMITS["study"])
        legacy = load("0180-split-study.py", LEGACY_SHA)
        core = phase_helper("study", pins)
        budget = core["new_budget"](clock, start)
        report.update(counts=budget.counts, ledger=budget.ledger)
        require(bundle["offsets_s"] == list(range(0, 51, 5)), "fixed coepoch grid")
        require(type(bundle["mass_kg"]) in (int, float)
                and 0 < bundle["mass_kg"] < float("inf"), "coast mass")
        if not injected:
            inputs = input_helpers()
            adapter = inputs["load_file"](ROOT, "0141-short-coast-inputs.py",
                                          inputs["PURE_PINS"]["0141-short-coast-inputs.py"], budget.check)
            assert pins is not None
            source_set = tuple(ROOT/name for name in pins if name.startswith(str(ART/"0194-extension-"))
                               and name.endswith(".py"))
            source_set += (ROOT/ART/"0142-short-coast-runner.py", ROOT/"tests/test_r5_short_coast_runner.py")

        def capture(when: str) -> Row:
            budget.event("identities", "attempt")
            if identity_provider is not None:
                value = identity_provider()
            else:
                from space_nav import ephemeris
                require(ephemeris._kernels_loaded == (when == "after"), "fresh/retained kernel pool")
                with legacy["native_observer"](budget, report):
                    value = adapter["runtime_identity"](budget.check, source_set)
                same_identity(value, bundle, pins)
            budget.event("identities", "return")
            report["identities"][when] = value
            budget.event("identities", "complete")
            return value

        stage = "identity-before"
        before = capture("before")
        core["run"](bundle, report, budget, provider or legacy["real_provider"],
                    native_adapter, set_stage=set_stage)
        stage = "identity-after"
        require(capture("after") == before, "before/after runtime identity")
        require(len(report["comparisons"]) == 33 and len(report["observations"]) == 36,
                "incomplete extension evidence")
        clock_gate(clock, start, LIMITS["study"])
        report["status"] = "passed"
    except FAILURES as exc:
        report.update(error={"stage": stage, "type": type(exc).__name__, "message": str(exc)})
        report["unavailable"].append("verified continuation and marker verdict")
    return report


def run_audit(
    bundle: Row, study_report: Row, *, started_s: float | None = None,
    clock: Callable[[], float] = monotonic, pins: Row | None = None, revision: str | None = None,
) -> Row:
    """Independently check saved data; this path never loads the study module."""
    start = clock() if started_s is None else started_s
    report: Row = {
        "contract": CONTRACT, "audit_status": "partial", "marker_status": "unavailable",
        "native_calls": 0, "kernel_loads": 0, "scientific_imports": 0, "spacecraft_propagations": 0,
        "scientific_verified": False, "continuous_safety_verified": False, "budget_s": 10.0,
    }

    def check() -> None:
        clock_gate(clock, start, LIMITS["audit"])

    try:
        check()
        require(study_report["contract"] == CONTRACT, "audit study contract")
        if "inputs" in study_report:
            require(study_report["inputs"] == bundle, "audit immutable bundle")
        else:
            require(study_report["status"] == "partial" and "error" in study_report
                    and not any(study_report.get(key) for key in (
                        "identities", "counts", "rhs", "native_profiles", "state_requests")),
                    "incomplete study without frozen inputs")
            report["partial_study_error"] = study_report["error"]
            return report
        identities = study_report["identities"]
        complete = study_report["status"] == "passed"
        if complete:
            require(set(identities) == {"before", "after"} and
                    identities["before"] == identities["after"], "complete identity")
        if pins is not None:
            require(study_report["adapter_mode"] == "reference"
                    and not ({n.split(".")[0] for n in sys.modules} & SCIENTIFIC), "stdlib-only reference audit")
            inputs = input_helpers()
            snapshot = inputs["load_file"](ROOT, "0145-short-coast-evidence.py",
                                          inputs["PURE_PINS"]["0145-short-coast-evidence.py"], check)
            report["snapshot_checks"] = {}
            for stage, saved in identities.items():
                same_identity(saved, bundle, pins)
                require(saved["revision"] == revision, "saved study revision")
                base_snapshot = {**saved, "source_sha256": {
                    k: v for k, v in saved["source_sha256"].items()
                    if not k.startswith(str(ART/"0194-extension-"))
                }}
                report["snapshot_checks"][stage] = snapshot["verify_snapshot"](
                    base_snapshot, bundle["kernel_manifest"], check, checkout=ROOT)
        else:
            require(study_report["adapter_mode"] == "injected-test", "synthetic audit mode")
        phase_helper("audit", pins)["verify"](bundle, study_report, report, check)
        require(pins is None or not ({n.split(".")[0] for n in sys.modules} & SCIENTIFIC),
                "audit scientific module imported")
        check()
        if complete:
            require(report["marker_status"] in ("marker-bracketed", "marker-not-established"),
                    "no audited marker status")
            report["audit_status"] = "passed"
    except FAILURES as exc:
        report.update(marker_status="unavailable", numerical_status="unavailable",
                      error={"type": type(exc).__name__, "message": str(exc)})
    return report


def paths(directory: Path, phase: str) -> dict[str, Path]:
    names = ("attempt", "receipt", "parent-attempt", "parent-receipt")
    return {"evidence": directory/f"{phase}.json", **{name: directory/f"{phase}.{name}.json" for name in names}}


def read_json(path: Path) -> tuple[Row, str]:
    raw = path.read_bytes()
    value = json.loads(raw)
    require(type(value) is dict, "evidence JSON object")
    return value, digest(raw)


def save(path: Path, value: Row) -> str:
    raw = (json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return digest(raw)


def receipt_gate(receipt: Row, phase: str, started: float, elapsed: float,
                 attempt_sha: str, evidence_sha: str, status: str) -> bool:
    child_s = receipt.get("elapsed_s")
    return (receipt.get("finalization_gate") == "passed" and receipt.get("status") == status
            and receipt.get("contract") == CONTRACT and receipt.get("phase") == phase
            and receipt.get("started_s") == started and receipt.get("attempt_sha256") == attempt_sha
            and receipt.get("evidence_sha256") == evidence_sha
            and type(child_s) in (float, int) and 0 <= child_s <= elapsed < LIMITS[phase])


def read_study(directory: Path, revision: str, preparation: str) -> tuple[Row, Row]:
    require(not (directory/"study.late.json").exists(), "study flush exceeded its deadline")
    links = paths(directory, "study")
    values = {key: read_json(path) for key, path in links.items()}
    study, evidence_sha = values["evidence"]
    parent, _ = values["parent-receipt"]
    attempt, attempt_sha = values["attempt"]
    child, child_sha = values["receipt"]
    parent_attempt, parent_attempt_sha = values["parent-attempt"]
    identity = {"contract": CONTRACT, "phase": "study", "revision": revision,
                "preparation_sha256": preparation}
    require(parent_attempt == identity and all(parent[name] == value for name, value in identity.items())
            and all(attempt[name] == value for name, value in identity.items())
            and parent["checkout_frozen"] is True and parent["finalization_gate"] == "passed",
            "study parent binding")
    require(parent["parent_attempt_sha256"] == parent_attempt_sha and parent["attempt_sha256"] == attempt_sha
            and parent["child_receipt_sha256"] == child_sha and parent["evidence_sha256"] == evidence_sha
            and study["preparation_sha256"] == preparation and study["contract"] == CONTRACT
            and study["adapter_mode"] == "reference" and parent["started_s"] == attempt["started_s"],
            "study receipt digests")
    status = study["status"]
    require(status in ("passed", "partial") and parent["returncode"] == (0 if status == "passed" else 2)
            and receipt_gate(child, "study", attempt["started_s"], parent["elapsed_s"],
                             attempt_sha, evidence_sha, status), "study receipt finalization")
    return study, {k + "_sha256": value for k, (_, value) in values.items()}


def child(phase: str, directory: Path, preparation: str, revision: str, started: float) -> int:
    require(sys.flags.isolated and sys.dont_write_bytecode
            and bool(sys.flags.no_site) == (phase == "audit"), "isolated phase interpreter")
    limit = LIMITS[phase]

    def check() -> None:
        clock_gate(monotonic, started, limit)

    linked = paths(directory, phase)
    parent_attempt, _ = read_json(linked["parent-attempt"])
    require(parent_attempt == {"contract": CONTRACT, "phase": phase, "revision": revision,
                               "preparation_sha256": preparation}, "parent invocation binding")
    pins = input_helpers()["prepare"](ROOT, preparation, check)
    attempt_sha = save(linked["attempt"], {**parent_attempt, "started_s": started})
    try:
        _, bundle = input_helpers()["design_inputs"](ROOT, check)
        if phase == "study":
            result = run_study(bundle, None, None, identity_provider=None, started_s=started, pins=pins)
            status = result["status"]
        else:
            previous, bound = read_study(directory, revision, preparation)
            result = run_audit(bundle, previous, started_s=started, pins=pins, revision=revision)
            result["study_sha256s"] = bound
            status = result["audit_status"]
        require(input_helpers()["prepare"](ROOT, preparation, check) == pins, "post-phase input hashes")
        check()
    except FAILURES as exc:
        status = "partial"
        result = {"contract": CONTRACT, "status" if phase == "study" else "audit_status": status,
                  "marker_status": "unavailable", "error": str(exc)}
    result["preparation_sha256"] = preparation
    result["adapter_mode"] = "reference"
    evidence_sha = save(linked["evidence"], result)
    elapsed = monotonic() - started
    timely = 0 <= elapsed < limit
    receipt = {"contract": CONTRACT, "phase": phase, "started_s": started,
               "elapsed_s": elapsed, "evidence_sha256": evidence_sha,
               "attempt_sha256": attempt_sha, "status": status if timely else "partial",
               "finalization_gate": "passed" if timely else "failed"}
    save(linked["receipt"], receipt)
    if monotonic()-started >= limit and timely:
        save(directory/f"{phase}.late.json", {**receipt, "finalization_gate": "failed"})
        return 2
    return 0 if status == "passed" and timely else 2


def git(*args: str) -> bytes:
    return subprocess.check_output([GIT, *args], cwd=ROOT)


def snapshot() -> dict[str, str]:
    return {name: digest((ROOT/name).read_bytes()) for name in git("ls-files", "-z").decode().split("\0") if name}


def launch(phase: str, directory: Path, preparation: str) -> Row:
    started = monotonic()
    limit = LIMITS[phase]
    require(directory.is_dir() and not directory.resolve().is_relative_to(ROOT), "external evidence directory")
    require(Path(sys.executable).resolve().parent.parent.name == "space-nav", "pinned space-nav Python")
    require(not any(p.exists() or p.is_symlink()
                    for p in (*paths(directory, phase).values(), directory/f"{phase}.late.json")),
            "phase already attempted; do not retry")
    revision = git("rev-parse", "HEAD").decode().strip()
    require(git("branch", "--show-current").strip() == b"dev" and
            git("rev-parse", "origin/dev").strip() == revision.encode() and
            not git("status", "--porcelain"), "clean synchronized dev")
    pins = input_helpers()["prepare"](ROOT, preparation, lambda: clock_gate(monotonic, started, limit))
    name = Path(__file__).relative_to(ROOT)
    require(digest(Path(__file__).read_bytes()) == pins[str(name)], "launcher source hash")
    if phase == "audit":
        read_study(directory, revision, preparation)
    before = snapshot()
    linked = paths(directory, phase)
    marker = {"contract": CONTRACT, "phase": phase, "revision": revision, "preparation_sha256": preparation}
    parent_attempt_sha = save(linked["parent-attempt"], marker)
    flags = ["-I", "-B"] if phase == "study" else ["-I", "-S", "-B"]
    command = [sys.executable, *flags, str(ROOT/name), "child", phase, str(directory),
               preparation, revision, repr(started)]
    remaining = limit - (monotonic() - started)
    if remaining > 0:
        invoke = load("0189-post-cutoff-launch.py", PARENT_SHA)["run_child"]
        result = invoke(command, remaining)
    else:
        result = {"returncode": None, "stderr": "phase deadline before child"}
    status = "passed" if result["returncode"] == 0 else "partial"
    try:
        frozen = bool(snapshot() == before and git("rev-parse", "HEAD").strip() == revision.encode()
                      and not git("status", "--porcelain"))
    except (OSError, subprocess.SubprocessError) as exc:
        result["checkout_error"] = str(exc)
        frozen = False
    receipt, child_sha, evidence_sha, attempt_sha = {}, None, None, None
    try:
        receipt, child_sha = read_json(linked["receipt"])
        _, attempt_sha = read_json(linked["attempt"])
        evidence_sha = digest(linked["evidence"].read_bytes())
    except (ValueError, OSError) as exc:
        result["readback_error"] = str(exc)
    elapsed = monotonic()-started
    passed = (frozen and result["returncode"] in (0, 2) and attempt_sha is not None
              and evidence_sha is not None and receipt_gate(
                  receipt, phase, started, elapsed, attempt_sha, evidence_sha, status))
    result.update(**marker, parent_attempt_sha256=parent_attempt_sha, started_s=started,
                  elapsed_s=elapsed, checkout_frozen=frozen, attempt_sha256=attempt_sha,
                  evidence_sha256=evidence_sha, child_receipt_sha256=child_sha,
                  finalization_gate="passed" if passed else "failed")
    save(linked["parent-receipt"], result)
    if monotonic()-started >= limit:
        result.update(finalization_gate="failed", elapsed_s=monotonic()-started)
        # Keep the initial receipt and require a second failure record if its flush was late.
        late = directory/f"{phase}.late.json"
        if not late.exists():
            save(late, result)
    return result


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 6 and args[0] == "child":
        raise SystemExit(child(args[1], Path(args[2]).resolve(), args[3], args[4], float(args[5])))
    if len(args) != 3:
        raise SystemExit("usage: launch PHASE EVIDENCE_DIRECTORY PREPARATION_SHA256")
    result = launch(args[0], Path(args[1]).resolve(), args[2])
    raise SystemExit(0 if result["returncode"] == 0 and result["finalization_gate"] == "passed" else 2)
