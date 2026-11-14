"""One bounded study or independent offline audit; synthetic mode is the default."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from hashlib import sha256
import importlib.abc
import os
from pathlib import Path
import resource
import subprocess
import sys
from time import monotonic
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DESIGN_SHA = "302872faf1d5819dbc438cb7efa4cbcdcb2da37fc3a1249fa26bfd2fa346fb22"
DESIGN = HERE/"0196-design-inputs.json"
PREPARATION = HERE/"0197-verification.json"
GIT = "/opt/homebrew/bin/git"
CONTRACT = "ADR0196"
CAPS = {"study": 480.0, "audit": 300.0}
CAPACITY = {"study": 360.0, "audit": 225.0}
RSS_CAP = 2**31
PHASE_ERRORS = (ValueError, RuntimeError, OSError, ArithmeticError, KeyError, TypeError,
                ImportError, IndexError, AttributeError, subprocess.SubprocessError)
type Row = dict[str, Any]
type Check = Callable[[], None]


def load(name: str, pin: str | None = None) -> Row:
    file = HERE/name
    raw = file.read_bytes()
    if pin is not None and sha256(raw).hexdigest() != pin:
        raise ValueError(f"source digest changed: {name}")
    module = ModuleType("r550_" + file.stem.replace("-", "_"))
    module.__file__ = str(file)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(file), "exec"), module.__dict__)
    return module.__dict__


A = load("0197-far-archive.py")
need = A["need"]
LIMITS = A["Limits"]()


def restricted(phase: str, mode: str) -> None:
    blocked = {"tudatpy", "spiceypy", "space_nav"} if mode == "capacity" else set()
    if phase == "audit":
        blocked |= {"tudatpy", "spiceypy", "space_nav", "numpy", "scipy"}

    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> None:
            need(fullname.partition(".")[0] not in blocked, f"forbidden scientific import: {fullname}")
            return None

    def forbid(event: str, args: tuple[Any, ...]) -> None:
        if blocked and event == "ctypes.dlopen" and args[0] is not None:
            library = os.fsdecode(args[0]).lower()
            need(not any(x in library for x in ("cspice", "spiceypy", "tudat")), "forbidden native load")

    need(not (blocked & {n.partition(".")[0] for n in sys.modules}), "scientific modules already loaded")
    sys.meta_path.insert(0, Guard())
    sys.addaudithook(forbid)


def git(*args: str) -> bytes:
    return subprocess.check_output([GIT, *args], cwd=ROOT, timeout=15)


def snapshot() -> Row:
    tracked = git("ls-files", "-z").decode().split("\0")
    files = {n: sha256((ROOT/n).read_bytes()).hexdigest() for n in tracked if n}
    return {"revision": git("rev-parse", "HEAD").decode().strip(), "tracked": files,
            "status": git("status", "--porcelain=v1", "-z").hex()}


def preparation(mode: str, digest: str, check: Check, directory: Path) -> Row:
    raw = DESIGN.read_bytes()
    need(sha256(raw).hexdigest() == DESIGN_SHA, "ADR0196 design digest")
    check()
    if mode == "capacity":
        need(digest == DESIGN_SHA, "synthetic design binding")
        return {}
    raw = A["read"](PREPARATION, LIMITS.metadata)
    need(sha256(raw).hexdigest() == digest, "preparation digest")
    prep = A["decode"](raw)
    need(prep["preparation_complete"] is True and prep["design_sha256"] == DESIGN_SHA
         and prep["synthetic_capacity_verified"] is True, "R5.50 not ready")
    need(directory.parent == Path(prep["retention_root"]).resolve(), "unapproved retention volume")
    for name, pin in prep["tested_source_sha256"].items():
        file = ROOT/name
        need(file.resolve().is_relative_to(ROOT) and sha256(file.read_bytes()).hexdigest() == pin,
             f"tested source changed: {name}")
        check()
    return prep


def live_gate(directory: Path, revision: str, digest: str) -> None:
    need(directory.name == "R5.51", "fixed once-only R5.51 directory")
    auth = A["decode"](A["read"](directory.parent/"R5.51-authorization.json", 4096))
    need(type(auth) is dict and auth.get("authorized") is True
         and auth == {"contract": CONTRACT, "stage": "R5.51", "revision": revision,
                      "preparation_sha256": digest, "authorized": True}, "separate R5.51 authorization required")


def phase_name(directory: Path, phase: str, suffix: str) -> Path:
    return directory/f"{phase}.{suffix}.json"


def bind(directory: Path, phase: str, key: str, row: Row) -> str:
    return A["put_json"](phase_name(directory, phase, key), row, directory, LIMITS.metadata)


def read_binding(directory: Path, phase: str, key: str) -> tuple[Row, str]:
    raw = A["read"](phase_name(directory, phase, key), LIMITS.metadata)
    return A["decode"](raw), sha256(raw).hexdigest()


def deadline(started: float, limit: float) -> None:
    need(0 <= monotonic()-started < limit, f"phase elapsed limit {limit:g} s")


def rss_bytes() -> int:
    count = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return count if sys.platform == "darwin" else count*1024


def accepted(status: str, rc: int | None) -> bool:
    return (status == "passed" and rc == 0) or (status == "partial" and rc == 2)


def finalized(directory: Path, phase: str, identity: Row, *, required: bool = True) -> Row:
    parent, parent_sha = read_binding(directory, phase, "parent_receipt")
    attempt, attempt_sha = read_binding(directory, phase, "parent_attempt")
    child, child_sha = read_binding(directory, phase, "receipt")
    binding, binding_sha = read_binding(directory, phase, "attempt")
    reader = A["Reader"](directory/phase, lambda: None, LIMITS)
    limit = (CAPACITY if identity["mode"] == "capacity" else CAPS)[phase]
    need(not phase_name(directory, phase, "late").exists(), "late finalization")
    need(all(r["identity"] == identity for r in (parent, child, binding))
         and attempt == {"identity": identity, "started_s": binding["started_s"]}
         and parent["started_s"] == binding["started_s"] == child["started_s"], "phase identity binding")
    need(parent["parent_attempt_sha256"] == attempt_sha and parent["attempt_sha256"] == binding_sha
         and parent["child_receipt_sha256"] == child_sha and child["attempt_sha256"] == binding_sha
         and binding["parent_attempt_sha256"] == attempt_sha, "attempt and receipt chain")
    need(reader.manifest["binding"] == identity and reader.digest == child["manifest_sha256"]
         == parent["manifest_sha256"], "phase manifest binding")
    need(parent["checkout_frozen"] is True and parent["gate"] == child["gate"] == "passed"
         and 0 <= child["elapsed_s"] <= parent["elapsed_s"] < limit
         and parent["status"] == child["status"] == reader.manifest["status"]
         and accepted(parent["status"], parent["returncode"]), "phase finalization")
    need(not required or parent["status"] == "passed", "study evidence is partial")
    return {"manifest_sha256": reader.digest, "parent_receipt_sha256": parent_sha}


def matching_identity(value: Row, bundle: Row, prep: Row, revision: str) -> None:
    need(value["revision"] == revision and value["dirty"] == [], "clean reference revision")
    for key in ("versions", "imports", "native_binary", "conda_build", "resource_build",
                "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime", "kernels"):
        need(value[key] == bundle["historical_identity"][key] == bundle["b_runtime"][key],
             f"reference runtime changed: {key}")
    for name, pin in prep["tested_source_sha256"].items():
        if name.startswith("docs/adr/experiments/0197-far-") and name.endswith(".py"):
            need(value["source_sha256"][name] == pin, "prepared reference source identity")


class Metadata:
    def __init__(self, writer: Any) -> None:
        self.writer = writer

    def append(self, row: Row) -> None:
        self.writer.append("native_metadata", row)


def live_study(bundle: Row, writer: Any, budget: Any, prep: Row, revision: str, study: Row) -> Row:
    from space_nav import ephemeris

    legacy = load("0180-split-study.py", "e0937a7c4528febf84f5016a6d3d92148bbab1554b8f6d8c8b41ef3258bc754b")
    source = load("0141-short-coast-inputs.py", "4457d9094afe3e8b674a46704b6789fdd724469cb8e1efe5cc054ce39d34c37c")
    extra = tuple(ROOT/n for n in prep["tested_source_sha256"] if n.startswith("docs/adr/experiments/0197-far-")
                  and n.endswith(".py"))
    extra += (HERE/"0142-short-coast-runner.py", ROOT/"tests/test_r5_short_coast_runner.py")

    def capture(when: str) -> Row:
        budget.event("identities", "attempt")
        need(ephemeris._kernels_loaded == (when == "after"), "fresh then retained kernel pool")
        with legacy["native_observer"](budget, {"native_metadata_returns": Metadata(writer)}):
            value = source["runtime_identity"](budget.check, extra)
        matching_identity(value, bundle, prep, revision)
        budget.event("identities", "return")
        writer.append("identity", {"when": when, "value": value})
        budget.event("identities", "complete")
        return value

    before = capture("before")
    summary = study["run"](bundle, writer, budget, legacy["real_provider"])
    need(capture("after") == before, "before/after reference identity")
    need({k: budget.counts[k]["completed"] for k in ("identities", "initializations", "metadata")}
         == {"identities": 2, "initializations": 1, "metadata": 30}, "reference metadata/initializations")
    return summary


def verified_live_records(records: Iterator[tuple[str, Row]], bundle: Row, prep: Row, revision: str,
                          check: Check, work_counts: Row) -> Iterator[tuple[str, Row]]:
    old = load("0145-short-coast-evidence.py", "426fe4e0abe9b9dfcf6380d09e86e8dbf5748f66875f74b26b45dceb6ba5da14")

    meta: list[Row] = []
    snapshots: list[Row] = []
    science_seen = False
    for kind, row in records:
        if kind == "native_metadata":
            need(len(snapshots) < 2 and len(meta) < 31, "metadata order/cap")
            meta.append(row)
        elif kind == "identity":
            when = ("before", "after")[len(snapshots)] if len(snapshots) < 2 else "unexpected"
            need(row["when"] == when and len(meta) == (16 if when == "before" else 31)
                 and science_seen == (when == "after"), "identity order")
            value = row["value"]
            matching_identity(value, bundle, prep, revision)
            base = {**value, "source_sha256": {
                k: v for k, v in value["source_sha256"].items() if not k.startswith("docs/adr/experiments/0197-far-")
            }}
            old["verify_snapshot"](base, bundle["kernel_manifest"], check, checkout=ROOT)
            snapshots.append(value)
        else:
            need(len(snapshots) == 1 and len(meta) == 16, "science outside reference snapshots")
            science_seen = True
            if kind == "study_summary":
                closed = {
                    **row["counts"],
                    "identities": {"attempted": 2, "returned": 2, "completed": 2},
                    "metadata": {"attempted": 30, "returned": 30, "completed": 30},
                }
                need(closed == work_counts, "opening science and closing work counters")
            yield kind, row
    need(len(snapshots) == 2 and snapshots[0] == snapshots[1], "missing or different reference snapshots")
    replay = load("0183-earth-audit.py", "6cace255c1eb11e7c2c33aa05d9195325aeabadb3586d512ee272e2095c36b50")
    replay["_check_metadata"]({
        "native_metadata_returns": meta, "adapter_mode": "reference",
        "counts": {"initializations": {"returned": 1}, "metadata": {"returned": 30}},
    }, bundle, True)


def child(directory: Path, phase: str, mode: str, digest: str, revision: str,
          started: float) -> int:
    need(sys.flags.isolated and sys.dont_write_bytecode
         and bool(sys.flags.no_site) == (phase == "audit"), "child isolation flags")
    restricted(phase, mode)
    limit = (CAPACITY if mode == "capacity" else CAPS)[phase]

    def check() -> None:
        deadline(started, limit)

    identity = {"contract": CONTRACT, "phase": phase, "mode": mode, "revision": revision, "pin_sha256": digest}
    marker, marker_sha = read_binding(directory, phase, "parent_attempt")
    need(marker == {"identity": identity, "started_s": started}, "invalid parent attempt")
    prep = preparation(mode, digest, check, directory)
    if mode == "live":
        live_gate(directory, revision, digest)
    binding = {"identity": identity, "started_s": started, "parent_attempt_sha256": marker_sha}
    binding_sha = bind(directory, phase, "attempt", binding)
    context: Row = {}
    reader = None
    durability: Row = {}
    if phase == "audit":
        study_identity = {**identity, "phase": "study"}
        context = finalized(directory, "study", study_identity, required=False)
        reader = A["Reader"](directory/"study", check, LIMITS)
        durability = {"used_raw": reader.manifest["raw"], "used_zip": reader.manifest["gzip"]}
    writer = A["Writer"](directory/phase, identity, check, LIMITS, **durability)
    status, summary = "partial", {"marker_status": "unavailable"}
    budget = None
    try:
        if phase == "study":
            study = load("0197-far-study.py")
            budget = study["new_budget"](monotonic, started)
            if mode == "capacity":
                summary = load("0197-far-fixtures.py")["produce"](writer, full_cap=True, budget=budget)
            else:
                bundle = load("0197-far-inputs.py")["prepare"](ROOT, check)
                summary = live_study(bundle, writer, budget, prep, revision, study)
            status = "passed"
        else:
            assert reader is not None
            if mode == "capacity":
                bundle = load("0197-far-fixtures.py")["bundle"]()
            else:
                bundle = load("0197-far-inputs.py")["prepare"](ROOT, check)
            iterator = reader.records()
            if mode == "live" and reader.manifest["status"] == "passed":
                iterator = verified_live_records(iterator, bundle, prep, revision, check,
                                                 reader.manifest["summary"]["work_counts"])
            audit_status = "capacity" if mode == "capacity" and reader.manifest["status"] == "passed" else reader.manifest["status"]
            summary = load("0197-far-audit.py")["verify"](bundle, iterator, writer.append, check, status=audit_status)
            need(next(iterator, None) is None, "unconsumed study record")
            if reader.manifest["status"] == "passed":
                status = "passed"
        check()
    except PHASE_ERRORS as error:
        status = "partial"
        first = error
        while isinstance(first.__context__, PHASE_ERRORS) and first.__cause__ is None:
            first = first.__context__
        summary.update(error=f"{type(first).__name__}: {first}", marker_status="unavailable")
    if budget is not None:
        summary["work_counts"] = budget.counts
    summary.update(mode=mode, capacity_only=mode == "capacity", study_binding=context)
    try:
        manifest = writer.seal(status, summary)
    except PHASE_ERRORS as error:
        status = "partial"
        summary.update(error=summary.get("error", f"{type(error).__name__}: {error}"), marker_status="unavailable")
        manifest = writer.seal(status, summary)
    elapsed = monotonic()-started
    peak = rss_bytes()
    gate = 0 <= elapsed < limit and (mode != "capacity" or peak <= RSS_CAP)
    packet = {**binding, "status": status, "gate": "passed" if gate else "failed",
              "attempt_sha256": binding_sha, "manifest_sha256": manifest,
              "elapsed_s": elapsed, "peak_rss_bytes": peak}
    bind(directory, phase, "receipt", packet)
    if monotonic()-started >= limit:
        bind(directory, phase, "late", {**packet, "gate": "failed"})
        gate = False
    return 0 if gate and status == "passed" else 2


def launch(directory: Path, phase: str, mode: str, digest: str) -> bool:
    started = monotonic()
    need(phase in CAPS and mode in ("capacity", "live"), "unknown experiment mode or phase")
    limit = (CAPACITY if mode == "capacity" else CAPS)[phase]

    def check() -> None:
        deadline(started, limit)

    need(Path(sys.executable).resolve().parent.parent.name == "space-nav", "pinned Conda Python required")
    need(not directory.is_relative_to(ROOT), "evidence must be outside checkout")
    A["preflight"](directory.parent, LIMITS)
    prep = preparation(mode, digest, check, directory)
    before = snapshot()
    revision = before["revision"]
    if mode == "live":
        live_gate(directory, revision, digest)
        need(not before["status"] and git("branch", "--show-current").strip() == b"dev"
             and git("rev-parse", "origin/dev").strip() == revision.encode(), "clean synchronized dev")
        need(prep["retention_root"] == str(directory.parent), "retention path changed")
    if phase == "study":
        directory.mkdir(mode=0o700)
    else:
        A["preflight"](directory, LIMITS)
    need(directory.is_dir() and not directory.is_symlink(), "exclusive run directory")
    identity = {"contract": CONTRACT, "phase": phase, "mode": mode, "revision": revision, "pin_sha256": digest}
    if phase == "audit":
        finalized(directory, "study", {**identity, "phase": "study"}, required=False)
    need(not (directory/phase).exists() and not any(directory.glob(phase + ".*")),
         "phase already attempted; no retry")
    check()
    marker_sha = bind(directory, phase, "parent_attempt", {"identity": identity, "started_s": started})
    flags = ["-I", "-S", "-B"] if phase == "audit" else ["-I", "-B"]
    command = [sys.executable, *flags, str(Path(__file__).resolve()), "child", phase, mode,
               str(directory), digest, revision, repr(started)]
    rc: int | None = None
    error = None
    try:
        remaining = limit-(monotonic()-started)
        need(remaining > 0, "no time to start child")
        proc = subprocess.run(command, cwd=ROOT, check=False, timeout=remaining)
        rc = proc.returncode
    except PHASE_ERRORS as exc:
        error = type(exc).__name__
    gate, status = "failed", "partial"
    attempt_sha = receipt_sha = manifest_sha = None
    child_peak = None
    frozen = False
    try:
        frozen = snapshot() == before
        attempt, attempt_sha = read_binding(directory, phase, "attempt")
        child_receipt, receipt_sha = read_binding(directory, phase, "receipt")
        reader = A["Reader"](directory/phase, check, LIMITS)
        manifest_sha = reader.digest
        status = reader.manifest["status"]
        child_peak = child_receipt["peak_rss_bytes"]
        need(attempt == {"identity": identity, "started_s": started, "parent_attempt_sha256": marker_sha}
             and child_receipt["identity"] == reader.manifest["binding"] == identity
             and child_receipt["manifest_sha256"] == manifest_sha
             and child_receipt["attempt_sha256"] == attempt_sha
             and child_receipt["parent_attempt_sha256"] == marker_sha
             and child_receipt["status"] == status and child_receipt["started_s"] == started,
             "child receipt binding")
        need(frozen and accepted(status, rc) and child_receipt["gate"] == "passed"
             and not phase_name(directory, phase, "late").exists()
             and 0 <= child_receipt["elapsed_s"] <= monotonic()-started, "child deadline/checkout/exit gate")
        if mode == "capacity":
            need(type(child_peak) is int and 0 < child_peak <= RSS_CAP and rss_bytes() <= RSS_CAP, "capacity RSS gate")
        check()
        gate = "passed"
    except PHASE_ERRORS as exc:
        error = error or str(exc)
    parent = {"identity": identity, "started_s": started, "elapsed_s": monotonic()-started,
              "checkout_frozen": frozen, "returncode": rc, "status": status, "gate": gate,
              "parent_attempt_sha256": marker_sha, "attempt_sha256": attempt_sha,
              "child_receipt_sha256": receipt_sha, "manifest_sha256": manifest_sha,
              "parent_peak_rss_bytes": rss_bytes(), "child_peak_rss_bytes": child_peak, "error": error}
    bind(directory, phase, "parent_receipt", parent)
    timely = monotonic()-started < limit
    if not timely and not phase_name(directory, phase, "late").exists():
        bind(directory, phase, "late", {**parent, "gate": "failed"})
    return timely and gate == status == "passed"


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 7 and args[0] == "child":
        _, p, m, directory_arg, digest_arg, revision_arg, time_arg = args
        raise SystemExit(child(Path(directory_arg), p, m, digest_arg, revision_arg, float(time_arg)))
    if len(args) != 4:
        raise SystemExit("usage: launch PHASE (capacity|live) DIRECTORY PIN_SHA256")
    phase_arg, mode_arg, location, pin_arg = args
    raise SystemExit(0 if launch(Path(location).resolve(), phase_arg, mode_arg, pin_arg) else 2)
