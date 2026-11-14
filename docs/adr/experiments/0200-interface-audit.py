"""Bounded, stdlib-only audit of the archived lunar-to-Mars interface."""

from __future__ import annotations

from collections.abc import Callable
import gzip
from hashlib import sha256
import importlib.abc
from io import BytesIO
import math
import os
from pathlib import Path
import resource
import runpy
import subprocess
import sys
from time import monotonic
from types import ModuleType
from typing import Any

type Row = dict[str, Any]
type Check = Callable[[], None]
type Selected = list[tuple[str, Row]]

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DESIGN = HERE / "0199-design-inputs.json"
DESIGN_SHA = "5afd7e263adf7c7aa03ee902a4e7adb85360c4cadd172244a8c8b26d6d8998df"
PREP = HERE / "0200-verification.json"
WALL_S = 15
CAPS = {
    "wall_s": 15, "input_shards": 5, "raw_bytes": 80 * 2**20, "gzip_payload_bytes": 25 * 2**20,
    "bytes_per_raw_shard": 16 * 2**20, "rows": 218_972, "shard_metadata_bytes": 2**20,
    "compact_input_bytes": 2**21, "output_bytes": 2**17, "native_or_scientific_calls": 0,
    "new_states": 0, "propagation_calls": 0,
}
BLOCKED = {"tudatpy", "spiceypy", "space_nav", "numpy", "scipy"}
KERNEL_ENDINGS = {".bsp", ".bpc", ".bc", ".tf", ".tpc", ".tls", ".tm", ".ti", ".tsc"}
ERRORS = (OSError, ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError,
          EOFError, subprocess.SubprocessError)
RECEIPTS = ("parent_attempt", "attempt", "receipt", "parent_receipt")
PART_FIELDS = ("first", "rows", "raw", "gzip", "raw_sha256", "gzip_sha256")
RESULT_FILES = ("attempt.json", "report.json", "receipt.json", "late.json")


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _archive() -> Row:
    file = HERE / "0197-far-archive.py"
    raw = file.read_bytes()
    if digest(raw) != "0c316312ade239de4c08bcd4bc3404f3881dd8725269e93c961576376bdfd468":
        raise ValueError("archive primitive changed")
    module = ModuleType("_r553_archive")
    sys.modules[module.__name__] = module
    exec(compile(raw, str(file), "exec"), module.__dict__)
    return vars(module)


A = _archive()
need = A["need"]
wire = A["wire"]


def no_science() -> None:
    """Reject scientific imports, native SPICE loads and kernel file access."""
    need(not (BLOCKED & {n.partition(".")[0] for n in sys.modules}), "scientific modules already loaded")

    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> None:
            need(fullname.partition(".")[0] not in BLOCKED, "forbidden scientific import: " + fullname)
            return None

    def guard(event: str, args: tuple[Any, ...]) -> None:
        if event == "ctypes.dlopen" and args[0] is not None:
            name = os.fsdecode(args[0]).lower()
            need(not any(word in name for word in ("cspice", "spiceypy", "tudat")), "forbidden native load")
        if event == "open" and isinstance(args[0], (str, bytes)):
            need(Path(os.fsdecode(args[0])).suffix.lower() not in KERNEL_ENDINGS, "forbidden kernel access")

    sys.meta_path.insert(0, Guard())
    sys.addaudithook(guard)


def finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def regular_input(path: Path, cap: int) -> bytes:
    need(path.resolve() == path, "input path alias: " + path.name)
    return A["read"](path, cap)


def object_from(raw: bytes) -> Row:
    result = A["decode"](raw)
    need(type(result) is dict, "expected JSON object")
    return result


def hash_object(path: Path, limit: int, expected: str) -> tuple[Row, int]:
    raw = regular_input(path, limit)
    need(digest(raw) == expected, "input digest: " + path.name)
    return object_from(raw), len(raw)


def verify_phases(archive: Path, recorded: Row, ext: Row, check: Check, synthetic: bool) -> dict[str, Row]:
    """Check the frozen chains without re-reading the unselected archive members."""
    budget = CAPS["shard_metadata_bytes"]
    manifests = {}
    study_binding = ext["finalization_sha256"]["study"]
    need(recorded["full_independent_audit_passed"] is True, "R5.51 not fully audited")
    need(Path(recorded["once_only_location"]) == archive, "R5.51 location binding")
    expected_mode = "capacity" if synthetic else "live"
    deadlines = (360, 225) if synthetic else (480, 300)
    for phase, cap in zip(("study", "audit"), deadlines, strict=True):
        phase_data = recorded["phases"][phase]
        hashes = phase_data["receipt_sha256"]
        bound = ext["finalization_sha256"][phase]
        manifest_sha = bound["manifest_sha256"]
        need(bound == phase_data["finalized"] and hashes["parent_receipt"] == bound["parent_receipt_sha256"],
             "R5.51 phase binding: " + phase)
        need(set(hashes) == set(RECEIPTS) and not (archive / f"{phase}.late.json").exists(),
             "missing or late R5.51 receipt: " + phase)
        got = {}
        for key in RECEIPTS:
            got[key], n = hash_object(archive / f"{phase}.{key}.json", budget, hashes[key])
            budget -= n
            check()
        m, n = hash_object(archive / phase / "manifest.json", budget, manifest_sha)
        budget -= n
        start, child_start, child, parent = (got[k] for k in RECEIPTS)
        identity = {"contract": "ADR0196", "phase": phase, "mode": expected_mode,
                    "revision": recorded["measured_revision"], "pin_sha256": recorded["preparation_sha256"]}
        started = start["started_s"]
        need(finite(started) and started >= 0 and all(row["identity"] == identity and row["started_s"] == started
                                                      for row in got.values()), "R5.51 receipt identity")
        need(all(row["parent_attempt_sha256"] == hashes["parent_attempt"] for row in (child_start, child, parent))
             and all(row["attempt_sha256"] == hashes["attempt"] and row["manifest_sha256"] == manifest_sha
                     for row in (child, parent)) and parent["child_receipt_sha256"] == hashes["receipt"],
             "R5.51 receipt chain")
        need(m["binding"] == identity and m["schema"] == A["SCHEMA"] and m["status"] == "passed"
             and all(row["status"] == row["gate"] == "passed" and finite(row["elapsed_s"])
                     for row in (child, parent))
             and parent["checkout_frozen"] is True and type(parent["returncode"]) is int and parent["returncode"] == 0
             and 0 <= child["elapsed_s"] <= parent["elapsed_s"] < cap, "R5.51 phase finalization")
        if phase == "audit":
            need(m["summary"]["study_binding"] == study_binding, "R5.51 audit to study binding")
        manifests[phase] = m
        check()
    return manifests


def member_plan(ext: Row) -> tuple[list[Row], dict[str, int]]:
    plan = ext["selected_members"]
    need(type(plan) is list and len(plan) == CAPS["input_shards"], "selected shard count")
    totals = dict(raw=0, gzip=0, rows=0)
    seen = set()
    for part in plan:
        index, phase = part["manifest_index"], part["phase"]
        need(type(index) is int and 0 <= index < 100000 and phase in ("study", "audit")
             and part["member"] == f"{index:05d}.shard" and (phase, index) not in seen, "selected shard identity")
        seen.add((phase, index))
        for key, cap in (("raw", "bytes_per_raw_shard"), ("gzip", "gzip_payload_bytes"), ("rows", "rows")):
            value = part[key]
            need(type(value) is int and 0 < value <= CAPS[cap], "selected shard " + key + " cap")
            totals[key] += value
        selectors = part["selectors"]
        indices = [q["row_in_member"] for q in selectors]
        need(bool(indices) and all(type(i) is int and 0 <= i < part["rows"] for i in indices)
             and indices == sorted(set(indices)), "missing, duplicate or unordered selected rows")
    for key, cap in (("raw", "raw_bytes"), ("gzip", "gzip_payload_bytes"), ("rows", "rows")):
        need(totals[key] <= CAPS[cap] and ext["selected_member_totals"][key] == totals[key],
             "combined " + key + " cap or inventory")
    return plan, totals


def selected_rows(archive: Path, part: Row, manifest: Row, check: Check) -> Selected:
    index = part["manifest_index"]
    meta = {k: part[k] for k in PART_FIELDS}
    need(manifest["parts"][index] == meta, "member is not authenticated by manifest")
    head = wire(meta)
    saved = regular_input(archive / part["phase"] / part["member"], len(head) + meta["gzip"])
    packed = saved[len(head):]
    need(saved.startswith(head) and len(packed) == meta["gzip"] and digest(packed) == meta["gzip_sha256"],
         "compressed shard hash, header or length")
    with gzip.GzipFile(fileobj=BytesIO(packed)) as stream:
        raw = stream.read(meta["raw"] + 1)
    need(len(raw) == meta["raw"] and digest(raw) == meta["raw_sha256"], "raw shard hash or length")
    need(raw.endswith(b"\n") and raw.count(b"\n") == meta["rows"], "shard row count")
    start = cursor = 0
    output = []
    for q in part["selectors"]:
        ordinal = q["row_in_member"]
        while cursor < ordinal:
            start = raw.index(b"\n", start) + 1
            cursor += 1
        stop = raw.index(b"\n", start)
        item = A["decode"](raw[start:stop])
        need(type(item) is list and len(item) == 2 and item[0] == q["kind"]
             and type(item[1]) is dict and all(type(item[1].get(k)) is type(v) and item[1].get(k) == v
                                               for k, v in q["keys"].items()), "selected row identity")
        output.append((item[0], item[1]))
        check()
    return output


def evaluate(pins: Row, input_dir: Path, check: Check) -> Row:
    """Audit a supplied verified input set; the launcher controls the allowed paths."""
    check()
    need(pins["stage"] == "R5.52" and pins["contract"] == "ADR0199"
         and pins["future_audit_maxima"] == CAPS, "audit contract or limits")
    ext = pins["external_r551"]
    archive = Path(ext["retention_root"])
    need(archive.is_absolute() and archive.resolve() == archive and archive.is_dir(), "archive root")
    plan, totals = member_plan(ext)
    budget = CAPS["compact_input_bytes"]
    inputs = {}
    for name, want in pins["input_sha256"].items():
        need(type(name) is str and Path(name).name == name and name.endswith(".json"), "invalid compact input name")
        inputs[name], n = hash_object(input_dir / name, budget, want)
        budget -= n
        check()
    recorded = inputs["0198-verification.json"]
    synthetic = pins.get("synthetic") is True
    need((recorded.get("synthetic") is True) == synthetic, "synthetic evidence binding")
    manifests = verify_phases(archive, recorded, ext, check, synthetic)
    selected = []
    for part in plan:
        selected.extend(selected_rows(archive, part, manifests[part["phase"]], check))
    audited = runpy.run_path(str(HERE / "0200-interface-inventory.py"))["inspect"](pins, inputs, selected, check)
    check()
    return audited | {"status": "passed", "synthetic": synthetic, "selected_members": len(plan), "archive": totals,
                      "native_or_scientific_calls": 0, "new_states": 0, "propagation_calls": 0}


def deadline(started: float, wall: float) -> None:
    need(0 <= monotonic() - started < wall, "15 s audit deadline")


def sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def put_output(directory: Path, name: str, data: Row) -> str:
    raw = wire(data)
    total = sum((directory / f).stat().st_size for f in RESULT_FILES if (directory / f).exists())
    need(total + len(raw) <= CAPS["output_bytes"], "audit output byte cap")
    A["put"](directory / name, raw)
    sync_directory(directory)
    return digest(raw)


def stage_for(mode: str) -> str:
    need(mode in ("synthetic", "retained"), "unknown audit mode")
    return "R5.53" if mode == "synthetic" else "R5.54"


def verify_result(result_dir: Path) -> Row:
    """Return a certificate only for a timely parent receipt bound to the report."""
    need(not (result_dir / "late.json").exists(), "late audit finalization")
    cap = CAPS["output_bytes"]
    files = {}
    hashes = {}
    for name in RESULT_FILES[:3]:
        raw = regular_input(result_dir / name, cap)
        files[name], hashes[name] = object_from(raw), digest(raw)
        cap -= len(raw)
    attempt, report, receipt = (files[name] for name in RESULT_FILES[:3])
    need(receipt["attempt_sha256"] == hashes["attempt.json"] == report["attempt_sha256"]
         and receipt["report_sha256"] == hashes["report.json"], "audit result hash binding")
    need(attempt["stage"] == report["stage"] == receipt["stage"] == stage_for(attempt["mode"])
         and all(report.get(k) == receipt.get(k) == v for k, v in attempt["inputs"].items())
         and report["synthetic"] is (attempt["mode"] == "synthetic"), "audit result identity")
    need(type(receipt["returncode"]) is int and receipt["returncode"] == 0
         and receipt["status"] == report["status"] == "passed" and finite(receipt["elapsed_s"])
         and 0 <= receipt["elapsed_s"] < attempt["wall_s"] <= CAPS["wall_s"], "audit result unavailable")
    return report


def git(*args: str) -> str:
    return subprocess.check_output(["/opt/homebrew/bin/git", *args], cwd=ROOT, timeout=3, text=True).strip()


def configured(mode: str, pins_path: Path, location: Path) -> tuple[Row, Path, Row]:
    raw = regular_input(pins_path, CAPS["shard_metadata_bytes"])
    pins, pin = object_from(raw), digest(raw)
    if mode == "synthetic":
        need(pins.get("synthetic") is True and pin != DESIGN_SHA and location.parent == pins_path.parent,
             "synthetic fixture tree required")
        need(Path(pins["external_r551"]["retention_root"]) == pins_path.parent / "archive",
             "synthetic archive must stay in fixture tree")
        return pins, pins_path.parent / "inputs", {"pins_sha256": pin}
    need(mode == "retained" and pin == DESIGN_SHA and pins_path == DESIGN, "frozen retained inputs required")
    need(Path(sys.executable).resolve().parent.parent.name == "space-nav", "pinned Conda Python required")
    base = Path(pins["external_r551"]["retention_root"]).parent
    need(location == base / "R5.54", "fixed once-only R5.54 directory")
    prep = regular_input(PREP, CAPS["shard_metadata_bytes"])
    data = object_from(prep)
    revision = git("rev-parse", "HEAD")
    auth_raw = regular_input(base / "R5.54-authorization.json", 4096)
    auth = object_from(auth_raw)
    need(auth == {"stage": "R5.54", "revision": revision, "preparation_sha256": digest(prep),
                  "design_sha256": pin, "authorized": True}, "separate R5.54 authorization required")
    need(data["preparation_complete"] is True and data["full_synthetic_verified"] is True
         and data["design_sha256"] == pin, "R5.53 preparation is not complete")
    for name, want in data["tested_source_sha256"].items():
        need(type(name) is str and (ROOT / name).is_relative_to(ROOT)
             and digest(regular_input(ROOT / name, CAPS["compact_input_bytes"])) == want,
             "prepared source changed: " + name)
    need(git("branch", "--show-current") == "dev" and git("rev-parse", "origin/dev") == revision
         and not git("status", "--porcelain=v1"), "clean synchronized dev required")
    return pins, HERE, {"pins_sha256": pin, "revision": revision,
                        "preparation_sha256": digest(prep), "authorization_sha256": digest(auth_raw)}


def child(mode: str, pins_path: Path, location: Path, started: float, wall: float) -> int:
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "audit child isolation")
    no_science()

    def check() -> None:
        deadline(started, wall)

    attempt_raw = regular_input(location / "attempt.json", 4096)
    attempt = object_from(attempt_raw)
    need(attempt["mode"] == mode and attempt["wall_s"] == wall and attempt["started_s"] == started,
         "audit attempt identity")
    envelope = {"stage": stage_for(mode), **attempt["inputs"], "attempt_sha256": digest(attempt_raw),
                "synthetic": mode == "synthetic"}
    try:
        pins, input_dir, identity = configured(mode, pins_path, location)
        need(identity == attempt["inputs"], "audit inputs changed between parent and child")
        report = evaluate(pins, input_dir, check)
        check()
        # Keep room for the parent and late receipts, even if this write stalls.
        need(len(wire(report | envelope)) + len(attempt_raw) + 4096 <= CAPS["output_bytes"], "audit output byte cap")
    except ERRORS as error:
        report = {"status": "invalid-evidence", "error": f"{type(error).__name__}: {error}"[:1024]}
    put_output(location, "report.json", report | envelope)
    return 0 if report["status"] == "passed" else 2


def launch(mode: str, pins_path: Path, location: Path) -> bool:
    started, wall = monotonic(), WALL_S
    need(0 < wall <= CAPS["wall_s"], "invalid audit deadline")
    need(location.parent.is_dir() and location.parent.resolve() == location.parent, "unsafe output directory")
    _, _, identity = configured(mode, pins_path, location)
    location.mkdir(mode=0o700)
    sync_directory(location.parent)
    attempt = {"stage": stage_for(mode), "mode": mode, "inputs": identity, "started_s": started, "wall_s": wall}
    attempt_sha = put_output(location, "attempt.json", attempt)
    receipt = {"stage": stage_for(mode), "status": "invalid-evidence", **identity, "attempt_sha256": attempt_sha,
               "report_sha256": None, "returncode": None, "error": None}
    try:
        deadline(started, wall)
        proc = subprocess.run([sys.executable, "-I", "-S", "-B", str(Path(__file__).resolve()),
                               "child", mode, str(pins_path), str(location), repr(started), repr(wall)],
                              check=False, timeout=max(0., wall - (monotonic() - started)))
        receipt["returncode"] = proc.returncode
        raw = regular_input(location / "report.json", CAPS["output_bytes"])
        report = object_from(raw)
        need(all(report.get(k) == v for k, v in identity.items()) and report["attempt_sha256"] == attempt_sha
             and report["stage"] == stage_for(mode) and report["synthetic"] is (mode == "synthetic"), "audit report binding")
        receipt["report_sha256"] = digest(raw)
        need(proc.returncode == 0 and report["status"] == "passed", report.get("error", "audit child failed"))
        if mode == "retained":
            need(git("rev-parse", "HEAD") == identity["revision"] and not git("status", "--porcelain=v1"),
                 "checkout changed while auditing")
        deadline(started, wall)
        receipt["status"] = "passed"
    except ERRORS as error:
        receipt["error"] = f"{type(error).__name__}: {error}"[:1024]
    receipt["elapsed_s"] = monotonic() - started
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    receipt["child_peak_rss_bytes"] = rss if sys.platform == "darwin" else rss * 1024
    put_output(location, "receipt.json", receipt)
    if monotonic() - started >= wall:
        put_output(location, "late.json", {"status": "invalid-evidence", "error": "15 s audit deadline",
                                            "attempt_sha256": attempt_sha})
        return False
    if receipt["status"] == "passed":
        verify_result(location)
        if monotonic() - started >= wall:
            put_output(location, "late.json", {"status": "invalid-evidence", "error": "15 s audit deadline",
                                                "attempt_sha256": attempt_sha})
            return False
        return True
    return False


def run_synthetic(pins_path: Path, result_dir: Path) -> bool:
    """Use only a marked artificial input tree."""
    return launch("synthetic", Path(os.path.abspath(pins_path)), Path(os.path.abspath(result_dir)))


def main(args: list[str]) -> int:
    if len(args) == 6 and args[0] == "child":
        _, mode, pins, result, started, wall = args
        return child(mode, Path(pins), Path(result), float(started), float(wall))
    if len(args) == 3 and args[0] in ("synthetic", "retained"):
        mode, pins, result = args
        return 0 if launch(mode, Path(os.path.abspath(pins)), Path(os.path.abspath(result))) else 2
    raise ValueError("usage: audit (synthetic|retained) DESIGN_JSON RESULT_DIRECTORY")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except ERRORS as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(2) from None
