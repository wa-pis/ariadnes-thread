"""Frozen ADR0156 SI operands and saved provenance; no force or native calls."""
from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
Check = Callable[[], None]
INPUT_SHA = {
    "0136-retained-boundary-audit.json":
        "81d78ecf6e4e80b55e9d909f929a879b2e392667387ec2569632aa99a6b41063",
    "0148-short-coast-study.json":
        "8bbe6f5f7d08f4e220ee3cff450488531da0776b8a69cb4c37e1c9af9872b096",
    "0155-real-source.json":
        "278b094cff6dd417ac15c04d3b4e4da137acede17de7147babd72fe9e3812102",
}
ORACLE_SHA = "23915fee1feacca37f4a4c0f794feec177aac777407b9c87cc0f8176b0b4a6c8"
STRICT_SHA = "426fe4e0abe9b9dfcf6380d09e86e8dbf5748f66875f74b26b45dceb6ba5da14"
PYTHON_METADATA_SHA = "1ac066bc02e3b470f5e7fa74b0f91f9cfe21a8c87d76417f2a8c7531f38e5201"
PYTHON_EXECUTABLE_SHA = "795d8316b7dabff1c64e56d5f5787caf0fe1b1e18580d34fc3a4956d501475c2"
T0 = 978995455.2304223
U = math.ulp(T0)
OFFSETS = (0.0, U / 4, U / 2, 3 * U / 4, 0.05260015195876773,
           150 + 3 * U / 4, 300 - U / 4)
POSITION_M = [-47124635282.7281, 128473304107.83153, 55670397503.89886]
VELOCITY_M_S = [-29590.75977762049, -9186.174444867514, -2407.2479826554863]
GM_M3_S2 = {"Sun": 1.327124400420322e20, "Moon": 4902800121846.8,
            "Earth": 398600435468295.9}
CHAINS = {"Sun": (10,), "Earth": (399,), "Moon": (301, 399)}
CENTRES = {10: 0, 399: 0, 301: 399}
KERNEL_NAME = "inpop19a_TDB_m100_p100_spice.bsp"
KERNEL_SHA = "01f095b148ef1e5aad6f95213c188ca5b0d8a58901d19a95b0c11082b1d3a0c6"


def idle() -> None:
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _module(path: Path, expected: str, check: Check) -> ModuleType:
    check()
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == expected, "helper identity: " + path.name)
    check()
    name = "fixed_gravity_input_" + path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "private helper loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    # Execute checked bytes rather than reading the file again at import time.
    exec(compile(raw, str(path), "exec"), module.__dict__)
    check()
    return module


def strict_json(check: Check = idle) -> ModuleType:
    """Reuse immutable ADR0145's strict duplicate/nonfinite JSON parser."""
    return _module(HERE / "0145-short-coast-evidence.py", STRICT_SHA, check)


def load_oracle(root: Path = ROOT, check: Check = idle) -> ModuleType:
    """Load only the hash-pinned pure Type2 polynomial oracle."""
    return _module(root / "docs/adr/experiments/0153-real-ephemeris-oracle.py",
                   ORACLE_SHA, check)


def number(value: Any, label: str) -> float:
    require(type(value) in (int, float), label + ": finite nonboolean number required")
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(label + ": finite binary64 number required") from error
    require(math.isfinite(result), label + ": finite nonboolean number required")
    return result


def integer(value: Any, label: str) -> int:
    require(type(value) is int, label + ": integer required")
    return value


def vector(value: Any, size: int, label: str) -> list[float]:
    require(isinstance(value, list) and len(value) == size, label + ": vector size")
    return [number(item, label) for item in value]


def _same(left: object, right: object, label: str) -> None:
    require(json.dumps(left, sort_keys=True, allow_nan=False)
            == json.dumps(right, sort_keys=True, allow_nan=False), label + " mismatch")


def records_for_row(row: dict[str, Any], oracle: ModuleType,
                    check: Check = idle) -> list[Any]:
    """Validate Type2 chain, directory, descriptor and hi/exact-time coverage."""
    check()
    body = row["body"]
    require(body in CHAINS, "source body")
    hi = number(row["hi_tdb_s"], "hi_tdb_s")
    lo = number(row["lo_s"], "lo_s")
    epochs = (Fraction(hi), Fraction(hi) + Fraction(lo))
    segments = row["segments"]
    require(isinstance(segments, list) and len(segments) == len(CHAINS[body]),
            "selected centre chain length")
    records = []
    for segment, target in zip(segments, CHAINS[body], strict=True):
        check()
        require(isinstance(segment, dict) and set(segment) == {
            "body", "centre", "frame", "type", "first_tdb_s", "last_tdb_s",
            "begin", "end", "label", "path", "descriptor", "words", "trailer",
            "address", "index"}, "selected segment schema")
        actual = tuple(integer(segment[k], k) for k in ("body", "centre", "frame", "type"))
        require(actual == (target, CENTRES[target], 1, 2), "selected body/centre/frame/Type2")
        first = number(segment["first_tdb_s"], "segment first")
        last = number(segment["last_tdb_s"], "segment last")
        require(Fraction(first) <= min(epochs) <= max(epochs) <= Fraction(last),
                "selected segment coverage")
        begin = integer(segment["begin"], "segment begin")
        end = integer(segment["end"], "segment end")
        require(0 < begin < end, "selected DAF addresses")
        descriptor = vector(segment["descriptor"], 5, "descriptor")
        require(descriptor[:2] == [first, last], "descriptor epoch consistency")
        packed = struct.unpack("<6i", struct.pack("<3d", *descriptor[2:]))
        require(packed == (*actual, begin, end), "descriptor integer consistency")
        require(isinstance(segment["label"], str) and segment["label"], "segment label")
        require(isinstance(segment["path"], str)
                and Path(segment["path"]).name == KERNEL_NAME, "selected kernel path")
        init, interval, size, count = vector(segment["trailer"], 4, "Type2 trailer")
        require(interval > 0 and size.is_integer() and count.is_integer()
                and 5 <= size <= 128 and (int(size) - 2) % 3 == 0 and count > 0,
                "Type2 trailer layout")
        require(int(size) * int(count) + 4 == end - begin + 1, "Type2 segment size")
        index = integer(segment["index"], "Type2 index")
        expected_index = math.floor((Fraction(hi) - Fraction(init)) / Fraction(interval))
        require(index == expected_index and 0 <= index < int(count), "Type2 record index")
        require(integer(segment["address"], "Type2 address") == begin + int(size) * index,
                "Type2 record address")
        words = vector(segment["words"], int(size), "Type2 words")
        require(Fraction(words[1]) * 2 == Fraction(interval)
                and Fraction(words[0]) == Fraction(init) + Fraction(interval)
                * Fraction(2 * index + 1, 2), "Type2 record/directory alignment")
        record = oracle.parse_record(words)
        for epoch in epochs:
            oracle.evaluate_chain([record], epoch)
            check()
        records.append(record)
    return records


def _saved_identity(study: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    manifest = study["inputs"]["original_kernel_manifest"]
    require(isinstance(manifest, dict) and set(manifest) == {
        "kernel_source", "loaded_kernel_count", "spiceypy_version", "kernels",
        "kernel_list_status"}, "original kernel manifest schema")
    require(integer(manifest["loaded_kernel_count"], "loaded kernels") == 13
            and manifest["kernel_list_status"] == "complete"
            and manifest["kernel_source"] == "tudatpy-standard"
            and manifest["spiceypy_version"] == "8.2.0"
            and isinstance(manifest["kernels"], list) and len(manifest["kernels"]) == 13,
            "original ordered 13-kernel manifest")
    names = []
    for kernel in manifest["kernels"]:
        require(isinstance(kernel, dict) and set(kernel) == {
            "name", "version", "type", "source", "size_bytes", "sha256"}, "saved kernel schema")
        require(isinstance(kernel["name"], str) and kernel["name"] not in names,
                "saved kernel names")
        names.append(kernel["name"])
        require(integer(kernel["size_bytes"], "saved kernel bytes") > 0, "saved kernel bytes")
        digest = kernel["sha256"]
        require(isinstance(digest, str) and len(digest) == 64
                and all(c in "0123456789abcdef" for c in digest), "saved kernel SHA256")
    selected = [k for k in manifest["kernels"] if k["name"] == KERNEL_NAME]
    require(len(selected) == 1 and selected[0]["sha256"] == KERNEL_SHA
            and selected[0]["type"] == "SPK", "saved selected kernel identity")
    before, after = source["identity_before"], source["identity_after"]
    require(isinstance(before, dict) and isinstance(after, dict), "saved source identity schema")
    _same(before, after, "saved before/after identity")
    _same(before["kernels"], manifest, "saved original ordered kernels")
    require(before["versions"] == {"python": "3.12.14", "tudatpy": "1.0.0",
            "tudat-resources": "2.4", "numpy": "1.26.4", "scipy": "1.17.1",
            "spiceypy": "8.2.0"}, "saved pinned versions")
    require(before["dirty"] == [], "saved source checkout status")
    require(before["source_sha256"]["docs/adr/experiments/0153-real-ephemeris-oracle.py"]
            == ORACLE_SHA, "saved polynomial helper identity")
    return {"original_kernel_manifest": manifest, "identity_before": before,
            "identity_after": after,
            "kernel_scope": "saved ordered manifest only; no current kernel bytes or pool queried",
            "adr0148_final_identity_available": False,
            "historical_loaded_memory_verified": False}


def _returns(source: dict[str, Any], check: Check) -> None:
    ledger = source["native_returns"]
    require(isinstance(ledger, list), "saved raw-return ledger")
    cursor = 0
    counts: dict[str, int] = {}

    def take(kind: str) -> Any:
        nonlocal cursor
        check()
        require(cursor < len(ledger), "saved raw-return ledger missing return")
        entry = ledger[cursor]
        require(isinstance(entry, dict) and set(entry) == {"call", "returned"}
                and entry["call"] == kind, "saved raw-return order/schema")
        cursor += 1
        counts[kind] = counts.get(kind, 0) + 1
        return entry["returned"]

    handles: dict[int, str] = {}
    cache: dict[tuple[int, int, int], dict[str, Any]] = {}
    for row in source["rows"]:
        for segment in row["segments"]:
            selection = take("selections")
            require(isinstance(selection, list) and len(selection) == 3, "saved selection return schema")
            handle = integer(selection[0], "saved selection handle")
            require(handle > 0, "saved selection handle")
            _same(selection[1:], [segment["descriptor"], segment["label"]],
                  "saved raw selected descriptor/label")
            _same(take("descriptors"), [segment[k] for k in (
                "body", "centre", "frame", "type", "first_tdb_s", "last_tdb_s", "begin", "end")],
                "saved raw unpacked descriptor")
            if handle not in handles:
                path_return = take("paths")
                require(isinstance(path_return, list) and len(path_return) == 3
                        and path_return[0] == "SPK" and isinstance(path_return[1], str)
                        and integer(path_return[2], "saved loaded handle") == handle,
                        "saved kernel path return")
                handles[handle] = segment["path"]
            require(handles[handle] == segment["path"], "saved handle/path consistency")
            key = (handle, segment["begin"], segment["end"])
            if key not in cache:
                _same(take("arrays"), segment["trailer"], "saved raw trailer")
                _same(take("arrays"), segment["words"], "saved raw record")
                cache[key] = segment
            else:
                _same(cache[key], segment, "saved cached segment")
        state_return = take("states")
        require(isinstance(state_return, list) and len(state_return) == 2, "saved raw state return schema")
        _same(state_return[0], row["state_km_km_s"], "saved raw state")
        require(number(state_return[1], "saved light time") >= 0, "saved light time")
    require(cursor == len(ledger), "saved raw-return ledger extra return")
    expected = {"selections": 28, "descriptors": 28, "paths": 1, "arrays": 6, "states": 21}
    require(counts == expected and len(ledger) == 84, "saved raw-return counts")
    expected_counts = {k: v for name, count in expected.items()
                       for k, v in ((name, count), (name + "_returned", count))}
    for count in source["counts"].values():
        integer(count, "saved count")
    require(source["counts"] == expected_counts, "saved attempted/returned counts")


def validate_bundle(boundary: dict[str, Any], study: dict[str, Any],
                    source: dict[str, Any], oracle: ModuleType,
                    check: Check = idle) -> dict[str, Any]:
    """Validate parsed frozen data or synthetic fixtures without evaluating gravity.

    File digests and current interpreter identity are added only by load_inputs.
    Synthetic fixtures need no retained-file hashes and cannot certify real data.
    """
    check()
    initial = study["inputs"]["initial"]
    _same(boundary["rows"][0]["stored_endpoint"], initial, "0136/0148 exact endpoint")
    require(isinstance(initial, dict) and set(initial) == {
        "epoch_tdb_s", "epoch_utc", "label", "orientation", "origin", "position_m",
        "velocity_m_s"}, "initial endpoint schema")
    require(number(initial["epoch_tdb_s"], "initial epoch") == T0
            and initial["orientation"] == "J2000" and initial["origin"] == "SSB",
            "initial endpoint epoch/frame/origin")
    require(vector(initial["position_m"], 3, "initial position_m") == POSITION_M
            and vector(initial["velocity_m_s"], 3, "initial velocity_m_s") == VELOCITY_M_S,
            "frozen initial six-state")
    inputs = study["inputs"]
    require((inputs["origin"], inputs["orientation"], inputs["time_scale"],
             inputs["position_units"], inputs["velocity_units"])
            == ("SSB", "J2000", "TDB seconds since J2000", "m", "m/s"), "input conventions")
    _same(inputs["state_si"], initial["position_m"] + initial["velocity_m_s"], "initial SI state")
    model = study["models"]["A"]
    require(model["model_id"] == "r5-ssb-sun-moon-point-v1"
            and model["included_sources"] == ["Sun", "Moon"], "saved model A source contract")
    gm = model["gm_m3_s2"]
    require(set(gm) == set(GM_M3_S2), "GM source inventory")
    for body, expected in GM_M3_S2.items():
        require(number(gm[body], body + " GM") == expected and gm[body] > 0, "frozen GM: " + body)
    require(boundary["rows"][0]["body"] == "Moon"
            and number(boundary["rows"][0]["gm_m3_s2"], "0136 lunar GM") == gm["Moon"],
            "0136 harmonic lunar GM")
    require(source["status"] == "passed" and source["stage"] == "R5.8 real ephemeris time boundary",
            "saved source status/stage")
    require((source["origin"], source["orientation"], source["time_scale"],
             source["aberration_correction"]) == ("SSB", "J2000", "TDB", "NONE")
            and source["state_units"] == ["m"] * 3 + ["m/s"] * 3, "source conventions")
    require(number(source["t0_tdb_s"], "source t0") == T0 and source["t0_hex"] == T0.hex(),
            "saved t0 numeric/hex")
    _same(vector(source["offsets_s"], 7, "source offsets_s"), list(OFFSETS), "saved offsets")
    require(integer(source["spacecraft_propagations"], "saved propagations") == 0
            and integer(source["force_evaluations"], "saved force evaluations") == 0
            and source["reference_replayed"] is False, "saved source scope")
    require(number(source["budget_s"], "saved budget") == 60
            and 0 <= number(source["elapsed_before_flush_s"], "saved elapsed") < 60,
            "saved acquisition budget")
    provenance = _saved_identity(study, source)
    rows = source["rows"]
    require(isinstance(rows, list) and len(rows) == 21, "saved source row count")
    for row, (elapsed, body) in zip(rows, ((s, b) for s in OFFSETS for b in CHAINS), strict=True):
        check()
        require(isinstance(row, dict) and set(row) == {
            "body", "elapsed_s", "elapsed_hex", "hi_tdb_s", "hi_hex", "lo_s", "lo_hex",
            "segments", "state_km_km_s", "state_si", "assessment"}, "source row schema")
        require(row["body"] == body and number(row["elapsed_s"], "elapsed_s") == elapsed
                and row["elapsed_hex"] == elapsed.hex(), "saved source body/offset order")
        hi = number(row["hi_tdb_s"], "hi_tdb_s")
        lo = number(row["lo_s"], "lo_s")
        exact_epoch = Fraction(T0) + Fraction(elapsed)
        require(hi == float(exact_epoch) and lo == float(exact_epoch - Fraction(hi))
                and Fraction(hi) + Fraction(lo) == exact_epoch
                and row["hi_hex"] == hi.hex() and row["lo_hex"] == lo.hex(),
                "saved exact epoch numeric/hex split")
        raw = vector(row["state_km_km_s"], 6, "returned km state")
        state = vector(row["state_si"], 6, "returned SI state")
        _same(state, [v * 1000 for v in raw], "saved binary64 km-to-SI conversion")
        records = records_for_row(row, oracle, check)
        assessment = oracle.assess(state, records, hi, lo)
        _same(assessment, row["assessment"], "reconstructed saved assessment")
        require(assessment["passed"] is True, "reconstructed source boundary gate")
        check()
    _returns(source, check)
    return {"position_m": list(initial["position_m"]), "initial": initial,
            "gm_m3_s2": dict(gm), "rows": rows, "t0_tdb_s": T0,
            "offsets_s": list(OFFSETS), "input_sha256": {},
            "source_provenance": provenance, "identity": {},
            "origin": "SSB", "orientation": "J2000", "time_scale": "TDB",
            "aberration_correction": "NONE", "position_units": "m",
            "velocity_units": "m/s", "gm_units": "m^3/s^2"}


def interpreter_identity(check: Check = idle) -> dict[str, Any]:
    """Bind current pinned Conda Python without importing scientific packages."""
    check()
    require(sys.version_info[:3] == (3, 12, 14), "current Python must be pinned 3.12.14")
    prefix = Path(sys.prefix).resolve()
    executable = Path(sys.executable).resolve()
    require(prefix.name == "space-nav" and executable.is_relative_to(prefix),
            "current interpreter must be the space-nav Conda interpreter")
    metadata = list((prefix / "conda-meta").glob("python-3.12.14-*.json"))
    require(len(metadata) == 1, "current pinned Conda Python metadata")
    raw = metadata[0].read_bytes()
    require(sha256(raw).hexdigest() == PYTHON_METADATA_SHA, "current Conda Python metadata identity")
    parser = strict_json(check)
    record = parser.parse(raw)
    require(record["name"] == "python" and record["version"] == "3.12.14"
            and record["build"] == "hd05a0c4_3_cpython", "current pinned Conda Python build")
    digest = parser.digest(executable, check)
    require(digest == PYTHON_EXECUTABLE_SHA, "current Conda Python executable identity")
    check()
    return {"python_version": ".".join(map(str, sys.version_info[:3])),
            "prefix": str(prefix), "executable": str(executable),
            "executable_sha256": digest, "conda_metadata_path": str(metadata[0]),
            "conda_metadata_sha256": sha256(raw).hexdigest(), "conda_build": record["build"],
            "scientific_packages_imported": False, "current_kernel_pool_queried": False}


def load_inputs(root: Path = ROOT, check: Check = idle) -> dict[str, Any]:
    """Read hash-bound ADR0136/0148/0155 operands; never evaluate a force."""
    parser = strict_json(check)
    records: dict[str, dict[str, Any]] = {}
    for name, expected in INPUT_SHA.items():
        check()
        raw = (root / "docs/adr/experiments" / name).read_bytes()
        require(sha256(raw).hexdigest() == expected, "frozen input identity: " + name)
        check()
        records[name] = parser.parse(raw)
        check()
    oracle = load_oracle(root, check)
    result = validate_bundle(records["0136-retained-boundary-audit.json"],
                             records["0148-short-coast-study.json"],
                             records["0155-real-source.json"], oracle, check)
    result["input_sha256"] = dict(INPUT_SHA)
    result["helper_sha256"] = {"0153-real-ephemeris-oracle.py": ORACLE_SHA,
                               "0145-short-coast-evidence.py": STRICT_SHA}
    result["identity"] = interpreter_identity(check)
    check()
    return result
