"""Hash-bound ADR0162 metadata; no polynomial, state or force evaluations."""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
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

ROOT = Path(__file__).resolve().parents[3]
Check = Callable[[], None]
MANIFEST = "docs/adr/experiments/0161-verification.json"
MANIFEST_SHA = "d8397b00362e4a3464ec9895351a10d34e96a18132dfa6fd9d08e86834cfce99"
BASE_NAME = "0157-fixed-gravity-inputs.py"
BASE_SHA = "5592d0295da35351a37795865f5ccaab0bcc64961b2dc0173245bbfe81e20f97"
INPUT_SHA = {
    "0136-retained-boundary-audit.json":
        "81d78ecf6e4e80b55e9d909f929a879b2e392667387ec2569632aa99a6b41063",
    "0148-short-coast-study.json":
        "8bbe6f5f7d08f4e220ee3cff450488531da0776b8a69cb4c37e1c9af9872b096",
    "0155-real-source.json":
        "278b094cff6dd417ac15c04d3b4e4da137acede17de7147babd72fe9e3812102",
}
T0 = 978995455.2304223
POSITION_M = [-47124635282.7281, 128473304107.83153, 55670397503.89886]
VELOCITY_M_S = [-29590.75977762049, -9186.174444867514, -2407.2479826554863]
OFFSETS = (0.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0)
BODIES = ("Sun", "Moon", "Earth")
GM_M3_S2 = {"Sun": 1.327124400420322e20, "Moon": 4902800121846.8,
            "Earth": 398600435468295.9}
RADII_M = {"Sun": 696000000.0, "Moon": 1737400.0, "Earth": 6378136.6}
CHAINS = {"Sun": (10,), "Moon": (301, 399), "Earth": (399,)}
CENTRES = {10: 0, 399: 0, 301: 399}


def idle() -> None:
    pass


def require(condition: bool, field: str) -> None:
    if not condition:
        raise ValueError("corrected inputs: " + field)


def number(value: Any, field: str) -> float:
    require(type(value) in (int, float), field + " finite nonboolean number")
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError("corrected inputs: " + field + " binary64 overflow") from error
    require(math.isfinite(result), field + " finite number")
    return result


def vector(value: Any, size: int, field: str) -> list[float]:
    require(isinstance(value, (list, tuple)) and len(value) == size, field + " dimensions")
    return [number(x, field) for x in value]


def integer(value: Any, field: str) -> int:
    require(type(value) is int, field + " integer")
    return value


def same(actual: Any, expected: Any, field: str) -> None:
    require(json.dumps(actual, sort_keys=True, allow_nan=False)
            == json.dumps(expected, sort_keys=True, allow_nan=False), field + " mismatch")


def parse(raw: bytes) -> dict[str, Any]:
    """Reject duplicate keys, booleans-as-numbers later, and all nonfinite JSON."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key " + key)
            result[key] = value
        return result

    def invalid(value: str) -> None:
        raise ValueError("corrected inputs: nonfinite JSON " + value)

    def finite(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                finite(item)
        elif isinstance(value, list):
            for item in value:
                finite(item)
        elif type(value) is float:
            require(math.isfinite(value), "nonfinite JSON number")

    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    require(isinstance(result, dict), "JSON object required")
    finite(result)
    return result


def load_base(root: Path = ROOT, check: Check = idle) -> ModuleType:
    """Reuse only immutable metadata/interpreter checks, not its polynomial path."""
    check()
    path = root / "docs/adr/experiments" / BASE_NAME
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == BASE_SHA, "metadata helper hash")
    name = "corrected_input_metadata_base"
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "metadata helper loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    check()
    return module


def check_protected(root: Path = ROOT, check: Check = idle) -> dict[str, str]:
    """Verify all381 historical source/evidence bindings without loading them."""
    check()
    raw = (root / MANIFEST).read_bytes()
    require(sha256(raw).hexdigest() == MANIFEST_SHA, "0161 manifest hash")
    manifest = parse(raw)
    require(manifest["protected_count"] == 370
            and manifest["all_protected_bytes_unchanged"] is True, "0161 manifest scope")
    protected = dict(manifest["protected_sha256"])
    require(len(protected) == 370, "0161 protected inventory")
    for name, digest in manifest["artifact_sha256"].items():
        require(name not in protected or protected[name] == digest, "conflicting protection")
        protected[name] = digest
    protected[MANIFEST] = MANIFEST_SHA
    require(len(protected) == 381, "complete historical protection inventory")
    for name, expected in protected.items():
        check()
        path = root / name
        require(path.resolve().is_relative_to(root.resolve()), "protected path outside root")
        require(sha256(path.read_bytes()).hexdigest() == expected,
                "protected hash: " + name)
        check()
    return protected


def validate_segment(segment: dict[str, Any], target: int) -> None:
    """Check exact Type2 descriptor/directory/interval metadata, never evaluate it."""
    require(isinstance(segment, dict), "segment object")
    actual = tuple(integer(segment[k], "segment " + k)
                   for k in ("body", "centre", "frame", "type"))
    require(actual == (target, CENTRES[target], 1, 2), "body/centre/frame/Type2")
    first, last = (number(segment[k], k) for k in ("first_tdb_s", "last_tdb_s"))
    require(Fraction(first) <= Fraction(T0) <= Fraction(T0) + 300 <= Fraction(last),
            "full segment coverage")
    begin, end = (integer(segment[k], k) for k in ("begin", "end"))
    require(0 < begin < end, "segment addresses")
    descriptor = vector(segment["descriptor"], 5, "descriptor")
    require(descriptor[:2] == [first, last], "descriptor epochs")
    packed = struct.unpack("<6i", struct.pack("<3d", *descriptor[2:]))
    require(packed == (*actual, begin, end), "descriptor integers")
    require(isinstance(segment["label"], str) and bool(segment["label"]), "segment label")
    require(isinstance(segment["path"], str)
            and Path(segment["path"]).name == "inpop19a_TDB_m100_p100_spice.bsp",
            "segment kernel path")
    init, interval, size, count = vector(segment["trailer"], 4, "trailer")
    require(interval > 0 and size.is_integer() and count.is_integer()
            and size in (35, 41) and count > 0, "Type2 trailer layout")
    require(int(size) * int(count) + 4 == end - begin + 1, "segment size")
    index = integer(segment["index"], "record index")
    expected = (Fraction(T0) - Fraction(init)) // Fraction(interval)
    require(index == expected and 0 <= index < int(count), "record index")
    require(integer(segment["address"], "record address") == begin + int(size) * index,
            "record address")
    words = vector(segment["words"], int(size), "record words")
    midpoint, radius = map(Fraction, words[:2])
    require(radius > 0 and radius * 2 == Fraction(interval)
            and midpoint == Fraction(init) + Fraction(interval) * Fraction(2 * index + 1, 2),
            "record directory alignment")
    require(midpoint - radius <= Fraction(T0) <= Fraction(T0) + 300 <= midpoint + radius,
            "full record coverage")


def validate_bundle(boundary: dict[str, Any], study: dict[str, Any],
                    source: dict[str, Any], *, base: ModuleType | None = None,
                    check: Check = idle) -> dict[str, Any]:
    """Validate parsed saved metadata; no state, polynomial or gravity evaluation."""
    check()
    metadata = load_base(check=check) if base is None else base
    initial = study["inputs"]["initial"]
    require(isinstance(initial, dict), "initial object")
    same(boundary["rows"][0]["stored_endpoint"], initial, "0136/0148 endpoint")
    require(number(initial["epoch_tdb_s"], "t0") == T0
            and initial["origin"] == "SSB" and initial["orientation"] == "J2000",
            "initial epoch/origin/orientation")
    require(vector(initial["position_m"], 3, "r0") == POSITION_M
            and vector(initial["velocity_m_s"], 3, "v0") == VELOCITY_M_S,
            "initial six-state")
    saved = study["inputs"]
    require((saved["origin"], saved["orientation"], saved["time_scale"],
             saved["position_units"], saved["velocity_units"])
            == ("SSB", "J2000", "TDB seconds since J2000", "m", "m/s"), "SI conventions")
    same(saved["state_si"], POSITION_M + VELOCITY_M_S, "initial SI six-state")
    require(number(saved["epoch_tdb_s"], "saved t0") == T0
            and number(saved["final_epoch_tdb_s"], "saved tf") == T0 + 300, "interval")
    nodes = [Fraction(T0) + Fraction(s) for s in OFFSETS]
    require([Fraction(x) for x in vector(saved["nodes_tdb_s"], 7, "native nodes")] == nodes,
            "seven exact native coepochs")
    model = study["models"]["A"]
    require(model["model_id"] == "r5-ssb-sun-moon-point-v1"
            and model["included_sources"] == ["Sun", "Moon"], "model A")
    require(set(model["gm_m3_s2"]) == set(BODIES), "GM inventory")
    for body in BODIES:
        require(number(model["gm_m3_s2"][body], body + " GM") == GM_M3_S2[body],
                "frozen GM " + body)
    require(number(boundary["rows"][0]["gm_m3_s2"], "0136 lunar GM") == GM_M3_S2["Moon"],
            "0136 harmonic lunar GM")
    provenance = metadata._saved_identity(study, source)
    same(study["identity"]["kernels"], saved["original_kernel_manifest"], "0148 initial kernels")
    for key in ("versions", "native_binary", "conda_build", "resource_build",
                "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime"):
        same(study["identity"][key], source["identity_before"][key], "historical " + key)
    require(source["status"] == "passed"
            and source["stage"] == "R5.8 real ephemeris time boundary", "source status/stage")
    require((source["origin"], source["orientation"], source["time_scale"],
             source["aberration_correction"]) == ("SSB", "J2000", "TDB", "NONE")
            and source["state_units"] == ["m"] * 3 + ["m/s"] * 3, "source conventions")
    require(number(source["t0_tdb_s"], "source t0") == T0
            and source["t0_hex"] == T0.hex(), "source epoch")
    require(type(source["spacecraft_propagations"]) is int
            and source["spacecraft_propagations"] == 0
            and type(source["force_evaluations"]) is int and source["force_evaluations"] == 0
            and source["reference_replayed"] is False, "retained source scope")
    rows = source["rows"]
    require(isinstance(rows, list) and len(rows) == 21, "source rows")
    saved_offsets = vector(source["offsets_s"], 7, "retained source offsets")
    unit = math.ulp(T0)
    same(saved_offsets, [0.0, unit / 4, unit / 2, 3 * unit / 4,
                        0.05260015195876773, 150 + 3 * unit / 4, 300 - unit / 4],
         "retained source offsets")
    templates: dict[str, Any] = {}
    unique: set[str] = set()
    for row, (elapsed, body) in zip(rows, ((s, b) for s in saved_offsets
                                         for b in ("Sun", "Earth", "Moon")), strict=True):
        check()
        require(row["body"] == body and number(row["elapsed_s"], "source s") == elapsed
                and row["elapsed_hex"] == elapsed.hex(), "source row order")
        hi, lo = number(row["hi_tdb_s"], "hi"), number(row["lo_s"], "lo")
        exact = Fraction(T0) + Fraction(elapsed)
        require(Fraction(hi) + Fraction(lo) == exact and hi == float(exact)
                and row["hi_hex"] == hi.hex() and row["lo_hex"] == lo.hex(), "source time split")
        raw = vector(row["state_km_km_s"], 6, "raw source state")
        require(vector(row["state_si"], 6, "source SI") == [x * 1000 for x in raw],
                "source SI conversion")
        segments = row["segments"]
        require(isinstance(segments, list) and len(segments) == len(CHAINS[body]), "centre chain")
        for segment, target in zip(segments, CHAINS[body], strict=True):
            validate_segment(segment, target)
            unique.add(json.dumps(segment, sort_keys=True, allow_nan=False))
        template = {"body": body, "segments": segments}
        if body in templates:
            same(template, templates[body], "repeated retained record")
        else:
            templates[body] = deepcopy(template)
    require(len(unique) == 3, "three unique retained Type2 records")
    samples: dict[str, list[list[float]]] = {}
    guards: dict[str, Any] = {}
    for label, key, step, count in (("normal", "native-normal", 1.0, 301),
                                    ("tighter", "native-tight", 0.5, 601)):
        check()
        profile = model["profiles"][key]
        raw, result = profile["raw_returned"], profile["result"]
        require(raw["integration_completed"] is True
                and number(result["step_s"], "native step_s") == step,
                "native completion/profile")
        require(integer(result["retained_states"], "native retained states") == count
                and integer(result["guarded_states"], "native guarded states") == count,
                "native retained/guarded counts")
        require((result["origin"], result["orientation"], result["position_units"],
                 result["velocity_units"], result["time_units"], result["model"])
                == ("SSB", "J2000", "m", "m/s", "TDB seconds since J2000", "A"),
                "native result conventions")
        same(result["force_order"], ["total", "Sun", "Moon"], "native force order")
        same(result["gravity_parameters_m3_s2"], GM_M3_S2, "native assigned GMs")
        history = raw["state_history"]
        require(isinstance(history, dict) and len(history) == count, "native history length")
        grid = {Fraction(number(float(epoch), "native epoch")): vector(state, 6, "native state")
                for epoch, state in history.items()}
        require(sorted(grid) == [Fraction(T0) + i * Fraction(step) for i in range(count)],
                "native exact grid")
        require(grid[Fraction(T0)] == POSITION_M + VELOCITY_M_S, "native initial state")
        require(len(result["samples"]) == 7, "native seven samples")
        samples[label] = []
        for epoch, sample in zip(nodes, result["samples"], strict=True):
            require(Fraction(number(sample["epoch_tdb_s"], "native sample epoch")) == epoch
                    and vector(sample["state"], 6, "native sample state") == grid[epoch],
                    "native exact coepoch sample")
            samples[label].append(list(grid[epoch]))
        for body, radius in RADII_M.items():
            require(number(result["minimum_checked_distances_m"][body], body + " minimum")
                    > radius, "historical guard minimum " + body)
        guards[label] = {"retained_states": count, "guarded_states": count,
                         "minimum_checked_distances_m": deepcopy(result["minimum_checked_distances_m"])}
    for key in ("native_guard_reads_attempted", "native_guard_reads_returned"):
        require(integer(study["counts"][key], key) == 2712, "historical native guard count")
    for body in BODIES:
        require(number(study["native_minimum_checked_distances_m"][body], "total guard minimum")
                == min(guards[p]["minimum_checked_distances_m"][body] for p in guards),
                "historical cumulative minimum " + body)
    return {"initial": {"epoch_tdb_s": T0, "position_m": list(POSITION_M),
                        "velocity_m_s": list(VELOCITY_M_S)},
            "offsets_s": list(OFFSETS), "gm_m3_s2": dict(GM_M3_S2),
            "radii_m": dict(RADII_M), "source_rows_template": {body: templates[body] for body in BODIES},
            "native_samples": samples, "historical_identity": deepcopy(study["identity"]),
            "kernel_manifest": deepcopy(saved["original_kernel_manifest"]),
            "source_provenance": provenance, "retained_guard_metadata": guards,
            "historical_final_identity_available": False,
            "retained_native_guard_reads": {"attempted": 2712, "returned": 2712},
            "input_sha256": {}}


def load_inputs(root: Path = ROOT, check: Check = idle) -> dict[str, Any]:
    """Load immutable anchors and record metadata without scientific acquisition."""
    protected = check_protected(root, check)
    records: dict[str, dict[str, Any]] = {}
    for name, expected in INPUT_SHA.items():
        check()
        raw = (root / "docs/adr/experiments" / name).read_bytes()
        require(sha256(raw).hexdigest() == expected, "frozen input hash: " + name)
        records[name] = parse(raw)
        check()
    base = load_base(root, check)
    result = validate_bundle(records["0136-retained-boundary-audit.json"],
                             records["0148-short-coast-study.json"],
                             records["0155-real-source.json"], base=base, check=check)
    result["input_sha256"] = dict(INPUT_SHA)
    result["protected_sha256"] = protected
    result["identity"] = base.interpreter_identity(check)
    check()
    return result
