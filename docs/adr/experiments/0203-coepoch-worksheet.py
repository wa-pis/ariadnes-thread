"""Private ADR0202 worksheet: two analytic ideal paths and no native work."""

from collections.abc import Callable
from hashlib import sha256
import math
from pathlib import Path
import resource
from runpy import run_path
import subprocess
import sys
from time import monotonic
from typing import Any

type Row = dict[str, Any]
type Check = Callable[[], None]
type State = tuple[float, ...]

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WALL_S = 15
CAPS = {
    "wall_s": 15, "input_shards": 1, "bytes_per_raw_shard": 16 * 2**20,
    "gzip_payload_bytes": 5 * 2**20, "rows": 42_862, "compact_input_bytes": 2**21,
    "shard_metadata_bytes": 2**20, "output_bytes": 2**17,
}
R1, R2, AUDIT = "0119-m2-reference.json", "0129-reference-coast.json", "0129-reference-coast-audit.json"
DESIGN, LIVE, CERT = "0199-design-inputs.json", "0198-verification.json", "0201-verification.json"
TARGET = "0098-central-correction-study.json"
PREP = HERE / "0203-verification.json"
ADMISSIBLE = {R1, R2, AUDIT, DESIGN, LIVE, CERT}
RETAINED = {
    R1: "3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0",
    R2: "e2c5d077285fe0218d1c93f3000f319048006eb55477d680f83041f6c70ce9d7",
    AUDIT: "41a8d4434db26752e3cae96e965480710f36eabbff885ed957b2766e957456c7",
    DESIGN: "5afd7e263adf7c7aa03ee902a4e7adb85360c4cadd172244a8c8b26d6d8998df",
    LIVE: "133623435622766b109ae11891f95ba4764868ebc550dbdd543f26f361336e79",
    CERT: "b4a760bd2b598d682b04969fb3b6e3f60cce5f738b3d6d655bb0a22207a25cd6",
    TARGET: "b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057",
}
R2_AUDIT_SHA = "138d6c98b9f914dbcc7b26355e0e8c2019bece997f1d18b089a90b3cce095ad9"
SELECTORS = [
    {"row_in_member": 16, "kind": "identity", "keys": {"when": "before"}},
    {"row_in_member": 337, "kind": "node", "keys": {"index": 320}},
]
FRAME = {"origin": "SSB", "orientation": "J2000"}
TIME = "TDB seconds since J2000"
CANDIDATE = "d0001-t0035"
MODEL_B = "r5-ssb-sun-moon-earth-point-v1"
IDEAL_MODEL = "sun-centered-zero-revolution-patched-conic-v1"
MU = 1.327124400420322e20
PHYSICAL = "physical-join-not-established"
NULLS = dict(epoch_s=None, position_m=None, velocity_m_s=None, mass_kg=None)
ZERO_WORK = dict(native_or_scientific_calls=0, kernel_accesses=0, force_evaluations=0,
                 propagation_calls=0, fit_attempts=0)


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def local_module(name: str, expected: str) -> Row:
    """Use only the previously qualified helper bytes."""
    file = HERE / name
    raw = file.read_bytes()
    if digest(raw) != expected:
        raise ValueError("changed helper: " + name)
    code: Row = {"__name__": "_r556_archive_helpers", "__file__": str(file)}
    exec(compile(raw, str(file), "exec"), code)
    return code


BASE = local_module("0200-interface-audit.py", "b4198de7f3e79a7dc375155dea6aa4140bd390bec51d4fc4b7d21f13f6ad1e8e")
need = BASE["need"]
wire = BASE["wire"]
read = BASE["regular_input"]
obj = BASE["object_from"]
sync = BASE["sync_directory"]
ERRORS = BASE["ERRORS"]
RESULT_FILES = BASE["RESULT_FILES"]


def number(value: object, name: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("invalid finite " + name)
    return float(value)


def word(value: object, name: str) -> str:
    return number(value, name).hex()


def vector(value: object, size: int, name: str) -> State:
    if type(value) is not list or len(value) != size:
        raise ValueError(f"{name}: expected {size} components")
    return tuple(number(x, name) for x in value)


def state(row: Row, body: str, epoch: float) -> State:
    need(row["body"] == body and all(row[k] == v for k, v in FRAME.items())
         and word(row["epoch_tdb_s"], body + " epoch") == epoch.hex(), body + " frame or epoch")
    return vector(row["position_m"], 3, body) + vector(row["velocity_m_s"], 3, body)


def lookup_sources(inputs: Row, hashes: Row) -> tuple[float, float, State, State, Row]:
    r1, r2, audit = (inputs[k] for k in (R1, R2, AUDIT))
    run = r1["runs"][0]
    points = r2["points"]
    saved = run["states"]
    chosen = run["selected"]
    need(run["number"] == 1 and chosen["candidate_id"] == CANDIDATE and r2["original"] == run,
         "original R1 run or candidate")
    need(r1["status"] == r2["status"] == "passed" and r2["reference_sha256"] == hashes[R1]
         and audit["evidence_sha256"] == hashes[R2] and audit["audit_source_sha256"] == R2_AUDIT_SHA
         and audit["native_calls"] == 0
         and audit["result"] == dict(audit="passed", study_status="passed", arithmetic_nodes_checked=121,
                                      reference_coast_verified=True), "R2 audit binding")
    need(len(points) == len(saved) == r2["attempted_sun_calls"] == r2["completed_sun_calls"] == 121
         and r2["native_spacecraft_propagations"] == 0 and r2["frame"] == FRAME
         and r2["units"] == dict(time=TIME, position_units="m", velocity_units="m/s"), "R2 inventory or frame")
    model = run["provenance"]["transfer_model"]
    gm = model["gravitational_parameters"]
    need(model["identifier"] == IDEAL_MODEL and gm["units"] == "m^3/s^2"
         and word(gm["values"]["Sun"], "ideal solar GM") == MU.hex(), "ideal force model or GM")
    start = number(chosen["departure_epoch_tdb_s"], "departure epoch")
    stop = number(chosen["arrival_epoch_tdb_s"], "arrival epoch")
    for i, epoch in ((0, start), (120, stop)):
        p = points[i]
        need(type(p["index"]) is int and p["index"] == i and p["status"] == "passed"
             and word(p["epoch_tdb_s"], "R2 seed epoch") == epoch.hex(), "R2 seed point identity")
    sun0 = state(points[0]["sun"], "Sun", start)
    moon = state(run["endpoints"]["departure"]["body_state"], "Moon", start)
    excess = vector(chosen["departure_v_infinity_m_s"], 3, "departure excess speed")
    operands = r2["seed_operands"]
    for key, values in (("moon", moon), ("sun0", sun0), ("excess_m_s", excess)):
        need(tuple(x.hex() for x in vector(operands[key], len(values), key)) == tuple(x.hex() for x in values),
             "R2 departure seed operands")
    reconstructed = tuple(moon[i] - sun0[i] for i in range(3)) + tuple(
        (moon[i+3] - sun0[i+3]) + excess[i] for i in range(3)
    )
    initial = vector(r2["initial_state"], 6, "R2 departure state")
    need(tuple(x.hex() for x in reconstructed) == tuple(x.hex() for x in initial), "R2 departure seed arithmetic")
    last = state(saved[120], "Spacecraft", stop)
    mars = state(run["endpoints"]["arrival"]["body_state"], "Mars", stop)
    excess_arrival = vector(chosen["arrival_v_infinity_m_s"], 3, "arrival excess speed")
    err_m_s = math.hypot(*(last[i+3] - mars[i+3] - excess_arrival[i] for i in range(3)))
    need(err_m_s <= 0.001, "R1 pre-impulse spacecraft velocity is inconsistent with arrival excess speed")
    sun_last = state(points[120]["sun"], "Sun", stop)
    terminal = tuple(x-y for x,y in zip(last, sun_last, strict=True))
    return start, stop, initial, terminal, r2["identity"]["kernels"]


def outgoing_packet(inputs: Row, hashes: Row, checkpoint: float) -> tuple[State, str]:
    cert = inputs[CERT]
    need(cert["stage"] == "R5.54" and cert["contract"] == "ADR0199"
         and cert["design_sha256"] == hashes[DESIGN], "R5.54 certificate identity")
    names = RESULT_FILES[:3]
    raw = {n: wire(cert["original_records"][n]) for n in names}
    h = {n: digest(raw[n]) for n in names}
    need(cert["retained_file_checks"] == {n: {"bytes": len(raw[n]), "sha256": h[n]} for n in names},
         "R5.54 original report/receipt digests")
    attempt, report, receipt = (cert["original_records"][n] for n in names)
    need(attempt["stage"] == report["stage"] == receipt["stage"] == "R5.54"
         and attempt["mode"] == "retained" and report["synthetic"] is False
         and attempt["inputs"]["pins_sha256"] == hashes[DESIGN]
         and all(report.get(k) == receipt.get(k) == v for k, v in attempt["inputs"].items())
         and receipt["attempt_sha256"] == report["attempt_sha256"] == h["attempt.json"]
         and receipt["report_sha256"] == h["report.json"], "R5.54 receipt binding")
    need(type(receipt["returncode"]) is int and receipt["returncode"] == 0
         and 0 <= number(receipt["elapsed_s"], "R5.54 duration") < attempt["wall_s"] == 15
         and report["status"] == receipt["status"] == "passed"
         and report["source_status"] == "source-state-authenticated"
         and report["physical_status"] == PHYSICAL and report["continuity_residuals"] == NULLS,
         "R5.54 incomplete or late")
    source, export = report["outgoing"], inputs[DESIGN]["export_selector"]
    need(all(source.get(k) == v for k,v in export.items()) and all(source[k] == v for k,v in FRAME.items())
         and source["candidate_id"] == CANDIDATE and source["model"] == "B"
         and source["force_model_id"] == MODEL_B and source["time_scale"] == TIME
         and source["units"] == ["m", "m/s", "kg"]
         and word(source["epoch_tdb_s"], "model B coepoch") == source["epoch_binary64_hex"] == checkpoint.hex(),
         "R5.54 outgoing provenance or epoch")
    sc = vector(source["state_si"], 6, "model B state")
    need([x.hex() for x in sc] == source["state_binary64_hex"], "R5.54 outgoing binary64 words")
    return sc, h["report.json"]


def sun_packet(inputs: Row, hashes: Row, archive: Path, kernels: Row, checkpoint: float,
               check: Check, synthetic: bool) -> tuple[State, Row, Row]:
    design = inputs[DESIGN]
    ext = design["external_r551"]
    need(Path(ext["retention_root"]) == archive and archive.is_dir() and archive.resolve() == archive,
         "one-shard archive root")
    need(design["input_sha256"][LIVE] == hashes[LIVE], "R5.51 compact verification digest")
    candidates = ext["selected_members"]
    need(type(candidates) is list and bool(candidates) and sum(
        m["phase"] == "study" and m["manifest_index"] == 0 for m in candidates
    ) == CAPS["input_shards"] == 1, "selected shard count")
    part = candidates[0]
    need((part["phase"], part["manifest_index"], part["member"], part["first"]) == ("study", 0, "00000.shard", 0)
         and type(part["manifest_index"]) is int
         and part["selectors"] in (SELECTORS, SELECTORS[1:]), "selected shard identity or locators")
    for field, key in (("rows", "rows"), ("raw", "bytes_per_raw_shard"), ("gzip", "gzip_payload_bytes")):
        need(type(part[field]) is int and 0 < part[field] <= CAPS[key], f"selected shard {field} cap")
    need(part["rows"] > 337, "selected shard row count")
    meta_paths = [archive / phase / "manifest.json" for phase in ("study", "audit")]
    meta_paths.extend(archive / f"{phase}.{role}.json"
                      for phase in ("study", "audit") for role in BASE["RECEIPTS"])
    need(sum(path.stat().st_size for path in meta_paths) <= CAPS["shard_metadata_bytes"], "archive metadata cap")
    live = inputs[LIVE]
    need(live["stage"] == "R5.51" and live["contract"] == "ADR0196" and live["model"] == "B"
         and (live.get("synthetic") is True) is synthetic
         and word(live["stop_tdb_s"], "R5.51 terminal epoch") == checkpoint.hex(), "R5.51 study identity")
    manifests = BASE["verify_phases"](archive, live, ext, check, synthetic)
    identity, node = BASE["selected_rows"](archive, part | {"selectors": SELECTORS}, manifests["study"], check)
    need(identity[1]["value"]["kernels"] == kernels, "archived ordered kernel identity")
    record = node[1]
    requests = [r for r in record["requests"] if r["body"] == "Sun"]
    need(len(requests) == 1 and word(record["hi_tdb_s"], "node epoch") == checkpoint.hex(), "Sun node epoch or request")
    response = record["bodies"]["Sun"]
    for item in (requests[0], response):
        need(all(item[k] == v for k,v in dict(body="Sun", observer="SSB", frame="J2000", aberration="NONE").items())
             and word(item["epoch_tdb_s"], "Sun state epoch") == checkpoint.hex(), "Sun frame, epoch or aberration")
    return vector(response["state_si"], 6, "Sun SI state"), {k: part[k] for k in ("raw", "gzip", "rows")}, {
        "study_manifest_sha256": ext["finalization_sha256"]["study"]["manifest_sha256"],
        "study_parent_receipt_sha256": ext["finalization_sha256"]["study"]["parent_receipt_sha256"],
        "member_raw_sha256": part["raw_sha256"], "member_gzip_sha256": part["gzip_sha256"],
        "selectors": SELECTORS, "ordered_kernel_inventory_matches_r2": True,
        "metadata_bytes": sum(p.stat().st_size for p in meta_paths),
    }


def synthetic_pins(pins_path: Path) -> tuple[Row, int, str]:
    raw = read(pins_path, CAPS["compact_input_bytes"])
    pins = obj(raw)
    need(pins_path.name == "pins.json" and pins.get("synthetic") is True and pins.get("stage") == "R5.56"
         and set(pins["input_sha256"]) == ADMISSIBLE, "artificial fixture pins required")
    return pins["input_sha256"], len(raw), digest(raw)


def collect(directory: Path, archive: Path, hashes: Row, pin_size: int, synthetic: bool, check: Check) -> Row:
    budget = CAPS["compact_input_bytes"] - pin_size
    inputs = {}
    for name, h in hashes.items():
        inputs[name], count = BASE["hash_object"](directory / name, budget, h)
        budget -= count
        check()
    design = inputs[DESIGN]
    need(design["stage"] == "R5.52" and design["contract"] == "ADR0199"
         and (design.get("synthetic") is True) is synthetic
         and design["candidate_id"] == CANDIDATE, "archive design identity")
    export = design["export_selector"]
    checkpoint = number(export["epoch_tdb_s"], "checkpoint epoch")
    need(checkpoint.hex() == export["epoch_binary64_hex"]
         and (synthetic or checkpoint.hex() == "0x1.d2d4a9afb54adp+29"), "fixed checkpoint word")
    start, stop, initial, terminal, kernels = lookup_sources(inputs, hashes)
    saved_sun, sizes, bindings = sun_packet(inputs, hashes, archive, kernels, checkpoint, check, synthetic)
    existing, report_digest = outgoing_packet(inputs, hashes, checkpoint)
    check()
    core = run_path(str(HERE / "0203-coepoch-arithmetic.py"))["evaluate"]
    result = core(checkpoint, start, stop, initial, terminal, saved_sun, existing, check)
    check()
    return result | ZERO_WORK | {"status": "passed", "synthetic": synthetic, "archive": sizes,
                                "compact_input_bytes": CAPS["compact_input_bytes"] - budget,
                                "archive_bindings": bindings | {"r554_report_sha256": report_digest},
                                "source_sha256": hashes, "outgoing_model_b_ssb_si": existing}


def evaluate(pins_path: Path, check: Check) -> Row:
    """Evaluate only an artificial fixture in this entry point."""
    check()
    hashes, size, _ = synthetic_pins(pins_path)
    return collect(pins_path.parent / "inputs", pins_path.parent / "archive", hashes, size, True, check)


def git(*args: str) -> str:
    return subprocess.check_output(["/opt/homebrew/bin/git", *args], cwd=ROOT, timeout=3, text=True).strip()


def configure(mode: str, pins: Path, output: Path) -> tuple[Row, int, Path, Path, Row]:
    if mode == "synthetic":
        hashes, size, sha = synthetic_pins(pins)
        need(output.parent == pins.parent, "artificial fixture output must stay in fixture tree")
        return hashes, size, pins.parent / "inputs", pins.parent / "archive", {"pins_sha256": sha}
    need(mode == "retained" and pins == HERE / DESIGN and Path(sys.executable).resolve().parent.parent.name == "space-nav",
         "frozen retained pins and pinned Conda Python required")
    base = Path("/Users/agrudin/dev/my/ariadna-evidence")
    need(output == base / "R5.57", "fixed once-only R5.57 destination")
    prep_raw = read(PREP, CAPS["shard_metadata_bytes"])
    prep = obj(prep_raw)
    revision = git("rev-parse", "HEAD")
    auth_raw = read(base / "R5.57-authorization.json", 4096)
    identity = {"revision": revision, "design_sha256": RETAINED[DESIGN], "preparation_sha256": digest(prep_raw)}
    need(obj(auth_raw) == (identity | {"stage": "R5.57", "authorized": True}), "separate R5.57 authorization required")
    expected_sources = {
        "docs/adr/experiments/0203-coepoch-worksheet.py", "docs/adr/experiments/0203-coepoch-arithmetic.py",
        "docs/adr/experiments/0203-coepoch-fixtures.py", "tests/test_coepoch_mars_worksheet.py",
        "tests/test_coepoch_mars_arithmetic.py",
    }
    tested = prep["tested_source_sha256"]
    need(prep["stage"] == "R5.56" and prep["preparation_complete"] is True
         and prep["full_synthetic_verified"] is True and prep["design_sha256"] == RETAINED[DESIGN]
         and set(tested) == expected_sources, "incomplete R5.56 preparation")
    for name, want in tested.items():
        need(digest(read(ROOT / name, CAPS["compact_input_bytes"])) == want, "prepared source changed: " + name)
    need(git("branch", "--show-current") == "dev" and git("rev-parse", "origin/dev") == revision
         and not git("status", "--porcelain=v1"), "clean synchronized dev required")
    return RETAINED, 0, HERE, base / "R5.51", identity | {"authorization_sha256": digest(auth_raw)}


def deadline(started: float, wall: float) -> None:
    need(0 <= monotonic() - started < wall, "coepoch worksheet deadline")


def put(directory: Path, name: str, value: Row) -> str:
    raw = wire(value)
    size = sum(p.stat().st_size for n in RESULT_FILES if (p := directory / n).exists())
    need(size + len(raw) <= CAPS["output_bytes"], "coepoch output byte cap")
    BASE["A"]["put"](directory / name, raw)
    sync(directory)
    return digest(raw)


def stage_for(mode: str) -> str:
    need(mode in ("synthetic", "retained"), "worksheet mode")
    return "R5.56" if mode == "synthetic" else "R5.57"


def verify_result(result_dir: Path) -> Row:
    """Authenticate timely result readback without re-evaluating either path."""
    need(not (result_dir / "late.json").exists(), "late coepoch finalization")
    data, h = {}, {}
    budget = CAPS["output_bytes"]
    for name in RESULT_FILES[:3]:
        raw = read(result_dir / name, budget)
        data[name], h[name] = obj(raw), digest(raw)
        budget -= len(raw)
    attempt, report, receipt = (data[n] for n in RESULT_FILES[:3])
    need(receipt["attempt_sha256"] == report["attempt_sha256"] == h["attempt.json"]
         and receipt["report_sha256"] == h["report.json"], "coepoch result hash binding")
    need(attempt["stage"] == report["stage"] == receipt["stage"] == stage_for(attempt["mode"])
         and all(report.get(k) == receipt.get(k) == v for k,v in attempt["inputs"].items())
         and report["synthetic"] is (attempt["mode"] == "synthetic"), "coepoch result identity")
    need(type(receipt["returncode"]) is int and receipt["returncode"] == 0
         and receipt["status"] == report["status"] == "passed"
         and 0 <= number(receipt["elapsed_s"], "receipt time") < attempt["wall_s"] <= CAPS["wall_s"],
         "coepoch result unavailable")
    need(report["ideal_status"] == "ideal-reference-coepoch-computed"
         and type(report["analytic_evaluations"]) is int and report["analytic_evaluations"] == 2
         and type(report["root_updates"]) is int and 2 <= report["root_updates"] <= 128
         and report["physical_status"] == PHYSICAL and report["continuity_residuals"] == NULLS
         and report["ideal_mass_kg"] is None and all(type(report[k]) is int and report[k] == v for k,v in ZERO_WORK.items()),
         "uncertified physical result or work count")
    return report


def child(mode: str, pins: Path, output: Path, started: float, wall: float) -> int:
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "worksheet child isolation")
    BASE["no_science"]()

    def check() -> None:
        deadline(started, wall)

    raw = read(output / "attempt.json", 4096)
    attempt = obj(raw)
    need(attempt["mode"] == mode and attempt["started_s"] == started and attempt["wall_s"] == wall,
         "coepoch attempt identity")
    envelope = {"stage": stage_for(mode), **attempt["inputs"], "attempt_sha256": digest(raw),
                "synthetic": mode == "synthetic"}
    try:
        hashes, size, directory, archive, identity = configure(mode, pins, output)
        need(identity == attempt["inputs"], "worksheet inputs changed between parent and child")
        report = collect(directory, archive, hashes, size, mode == "synthetic", check)
        need(len(wire(report | envelope)) + len(raw) + 4096 <= CAPS["output_bytes"], "coepoch output byte cap")
        check()
    except ERRORS as error:
        report = {"status": "invalid-evidence", "error": f"{type(error).__name__}: {error}"[:1024]}
    put(output, "report.json", report | envelope)
    return 0 if report["status"] == "passed" else 2


def launch(mode: str, pins: Path, output: Path) -> bool:
    started, wall = monotonic(), WALL_S
    need(0 < wall <= CAPS["wall_s"] and output.parent.resolve() == output.parent, "invalid deadline or output path")
    _, _, _, _, identity = configure(mode, pins, output)
    output.mkdir(mode=0o700)
    sync(output.parent)
    stage = stage_for(mode)
    attempt = {"stage": stage, "mode": mode, "inputs": identity, "started_s": started, "wall_s": wall}
    attempt_sha = put(output, "attempt.json", attempt)
    receipt = {"stage": stage, **identity, "attempt_sha256": attempt_sha, "status": "invalid-evidence",
               "returncode": None, "error": None, "report_sha256": None}
    try:
        deadline(started, wall)
        proc = subprocess.run([sys.executable, "-I", "-S", "-B", __file__, "child", mode,
                               str(pins), str(output), repr(started), repr(wall)],
                              check=False, timeout=max(0., wall - (monotonic() - started)))
        receipt["returncode"] = proc.returncode
        raw = read(output / "report.json", CAPS["output_bytes"])
        receipt["report_sha256"] = digest(raw)
        report = obj(raw)
        need(report["stage"] == stage and report["attempt_sha256"] == attempt_sha
             and all(report.get(k) == v for k,v in identity.items()), "coepoch report identity")
        need(proc.returncode == 0 and report["status"] == "passed", report.get("error", "worksheet child failed"))
        if mode == "retained":
            need(git("rev-parse", "HEAD") == identity["revision"] and not git("status", "--porcelain=v1"),
                 "checkout changed during worksheet")
        deadline(started, wall)
        receipt["status"] = "passed"
    except ERRORS as error:
        receipt["error"] = f"{type(error).__name__}: {error}"[:1024]
    receipt["elapsed_s"] = monotonic() - started
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    receipt["child_peak_rss_bytes"] = rss if sys.platform == "darwin" else rss * 1024
    put(output, "receipt.json", receipt)
    if receipt["status"] == "passed" and monotonic() - started < wall:
        verify_result(output)
    if monotonic() - started >= wall:
        put(output, "late.json", dict(status="invalid-evidence", error="coepoch worksheet deadline",
                                      attempt_sha256=attempt_sha))
        return False
    return receipt["status"] == "passed"


def run_synthetic(pins_path: Path, result_dir: Path) -> bool:
    """Launch one isolated artificial worksheet with exclusive output."""
    return launch("synthetic", pins_path.absolute(), result_dir.absolute())


def main(args: list[str]) -> int:
    if len(args) == 6 and args[0] == "child":
        _, mode, pins, output, started, wall = args
        return child(mode, Path(pins), Path(output), float(started), float(wall))
    if len(args) == 3 and args[0] in ("synthetic", "retained"):
        return 0 if launch(args[0], Path(args[1]).absolute(), Path(args[2]).absolute()) else 2
    raise ValueError("usage: worksheet (synthetic|retained) PINS_JSON OUTPUT_DIRECTORY")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except ERRORS as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(2) from None
