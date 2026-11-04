"""Private ADR0153 acquisition; importing this file requests no scientific state."""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
from time import monotonic
from types import ModuleType
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
T0 = 978995455.2304223
U = math.ulp(T0)
OFFSETS = (0.0, U / 4, U / 2, 3 * U / 4, 0.05260015195876773,
           150 + 3 * U / 4, 300 - U / 4)
CHAINS = {"Sun": (10,), "Earth": (399,), "Moon": (301, 399)}
CENTRES = {10: 0, 399: 0, 301: 399}
KERNEL_PATH = Path.home() / ".tudat/resource/spice_kernels/inpop19a_TDB_m100_p100_spice.bsp"
KERNEL_SHA = "01f095b148ef1e5aad6f95213c188ca5b0d8a58901d19a95b0c11082b1d3a0c6"
COMPENSATED_SHA = "b462ebbae0243366493d66363a5f9343f65d85e40352a538017a2304705bf77f"


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def load(name: str, expected: str | None = None) -> ModuleType:
    path = HERE / name
    require(expected is None or sha256(path.read_bytes()).hexdigest() == expected,
            "private source identity: " + name)
    spec = importlib.util.spec_from_file_location("real_boundary_" + name[:4] + name[5:9], path)
    require(spec is not None and spec.loader is not None, "private module loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(slots=True)
class Budget:
    clock: Callable[[], float] = monotonic
    start: float = field(init=False)
    counts: dict[str, int] = field(default_factory=dict)
    completed: list[dict[str, Any]] = field(default_factory=list)
    limits: dict[str, int] = field(default_factory=lambda: {
        "states": 21, "selections": 28, "descriptors": 28,
        "paths": 3, "arrays": 6,
    })

    def __post_init__(self) -> None:
        self.start = self.clock()
        self.check()

    def check(self) -> None:
        elapsed = self.clock() - self.start
        require(math.isfinite(elapsed) and 0 <= elapsed < 60.0, "deadline/clock")

    def call(self, name: str, function: Callable[..., Any], *args: Any) -> Any:
        self.check()
        require(self.counts.get(name, 0) < self.limits[name], "call cap: " + name)
        self.counts[name] = self.counts.get(name, 0) + 1
        try:
            result = function(*args)
        except Exception as exc:  # Untyped native SPICE call boundary.
            raise RuntimeError(f"native {name}: {exc}") from exc
        self.counts[name + "_returned"] = self.counts.get(name + "_returned", 0) + 1
        self.completed.append({"call": name, "returned": result})
        self.check()
        return result


def finite(values: Any) -> list[float]:
    raw = values.tolist() if hasattr(values, "tolist") else list(values)
    require(all(type(v) in (int, float) and math.isfinite(v) for v in raw),
            "finite nonboolean array")
    return [float(v) for v in raw]


def chain_records(spice: Any, oracle: ModuleType, targets: tuple[int, ...],
                  hi: float, lo: float, budget: Budget,
                  cache: dict[tuple[int, int, int], dict[str, Any]],
                  paths: dict[int, str]) -> tuple[list[Any], list[dict[str, Any]]]:
    records, metadata = [], []
    exact = Fraction.from_float(hi) + Fraction.from_float(lo)
    for target in targets:
        handle, descriptor, label = budget.call("selections", spice.spksfs, target, hi, 128)
        unpacked = budget.call("descriptors", spice.spkuds, descriptor)
        body, centre, frame, kind, first, last, begin, end = unpacked
        require((body, centre, frame, kind) == (target, CENTRES[target], 1, 2),
                "unsupported body/centre/frame/type")
        require(math.isfinite(first) and math.isfinite(last)
                and Fraction.from_float(first) <= min(exact, Fraction.from_float(hi))
                and max(exact, Fraction.from_float(hi)) <= Fraction.from_float(last),
                "segment coverage")
        require(type(begin) is int and type(end) is int and 0 < begin < end, "DAF addresses")
        if handle not in paths:
            kind_name, _source, loaded_handle = budget.call("paths", spice.kinfo, str(KERNEL_PATH))
            require(kind_name == "SPK" and loaded_handle == handle, "selected kernel handle")
            path = KERNEL_PATH.resolve()
            require(path.name == "inpop19a_TDB_m100_p100_spice.bsp"
                    and sha256(path.read_bytes()).hexdigest() == KERNEL_SHA,
                    "selected kernel identity")
            paths[handle] = str(path)
        key = (handle, begin, end)
        if key not in cache:
            trailer = finite(budget.call("arrays", spice.dafgda, handle, end - 3, end))
            require(len(trailer) == 4, "Type2 trailer length")
            init, interval, size, count = trailer
            require(interval > 0 and size.is_integer() and count.is_integer()
                    and 5 <= size <= 128 and (int(size) - 2) % 3 == 0 and count > 0,
                    "Type2 trailer layout")
            require(int(size) * int(count) + 4 == end - begin + 1, "Type2 segment size")
            index = math.floor((Fraction.from_float(hi) - Fraction.from_float(init))
                               / Fraction.from_float(interval))
            require(0 <= index < int(count), "Type2 record index")
            address = begin + int(size) * index
            words = finite(budget.call("arrays", spice.dafgda, handle, address,
                                      address + int(size) - 1))
            require(len(words) == int(size), "Type2 record length")
            record = oracle.parse_record(words)
            require(Fraction.from_float(words[1]) * 2 == Fraction.from_float(interval)
                    and Fraction.from_float(words[0]) == Fraction.from_float(init)
                    + Fraction.from_float(interval) * Fraction(2 * index + 1, 2),
                    "Type2 record/directory alignment")
            cache[key] = {"record": record, "words": words, "trailer": trailer,
                          "address": address, "index": index}
        saved = cache[key]
        # Coverage is checked afresh even when the polynomial is cached.
        oracle.evaluate_chain([saved["record"]], Fraction.from_float(hi))
        oracle.evaluate_chain([saved["record"]], exact)
        records.append(saved["record"])
        metadata.append({"body": body, "centre": centre, "frame": frame, "type": kind,
                         "first_tdb_s": first, "last_tdb_s": last, "begin": begin,
                         "end": end, "label": label, "path": paths[handle],
                         "descriptor": finite(descriptor),
                         **{k: v for k, v in saved.items() if k != "record"}})
    return records, metadata


def collect(spice: Any, oracle: ModuleType, split: Callable[..., tuple[float, float]],
            budget: Budget, result: dict[str, Any]) -> None:
    cache: dict[tuple[int, int, int], dict[str, Any]] = {}
    paths: dict[int, str] = {}
    for s in OFFSETS:
        hi, lo = split(T0, s)
        require(Fraction.from_float(hi) + Fraction.from_float(lo)
                == Fraction.from_float(T0) + Fraction.from_float(s), "exact epoch split")
        for body, targets in CHAINS.items():
            records, metadata = chain_records(spice, oracle, targets, hi, lo, budget, cache, paths)
            row = {"body": body, "elapsed_s": s, "elapsed_hex": s.hex(),
                   "hi_tdb_s": hi, "hi_hex": hi.hex(), "lo_s": lo, "lo_hex": lo.hex(),
                   "segments": metadata}
            result["rows"].append(row)
            raw, _light_time = budget.call("states", spice.spkezr, body, hi, "J2000", "NONE", "SSB")
            raw_km = finite(raw)
            require(len(raw_km) == 6, "native state size")
            state_si = [v * 1000 for v in raw_km]
            row.update(state_km_km_s=raw_km, state_si=state_si)
            row["assessment"] = oracle.assess(state_si, records, hi, lo)
            budget.check()
            require(row["assessment"]["passed"], "scientific boundary gate: " + body)
    require(budget.counts["states"] == 21 and budget.counts["selections"] == 28
            and budget.counts["arrays"] == 6, "completed acquisition counts")
    require(any(r["lo_s"] > 0 for r in result["rows"])
            and any(r["lo_s"] < 0 for r in result["rows"]), "both correction signs")
    require(any(not r["assessment"]["wrong_sign_passed"] for r in result["rows"]),
            "wrong-sign mutation must fail")


def wire(value: Any) -> Any:
    """Preserve partial native values as finite JSON with explicit invalid markers."""
    if hasattr(value, "tolist"):
        return wire(value.tolist())
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": repr(value)}
    if isinstance(value, dict):
        return {str(k): wire(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [wire(v) for v in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return {"unsupported_type": type(value).__name__}


def execute(path: Path, *, clock: Callable[[], float] = monotonic) -> dict[str, Any]:
    budget = Budget(clock)
    result: dict[str, Any] = {"stage": "R5.8 real ephemeris time boundary", "status": "partial",
        "budget_s": 60.0, "origin": "SSB", "orientation": "J2000", "time_scale": "TDB",
        "aberration_correction": "NONE", "state_units": ["m"] * 3 + ["m/s"] * 3,
        "t0_tdb_s": T0, "t0_hex": T0.hex(), "offsets_s": list(OFFSETS),
        "rows": [], "spacecraft_propagations": 0, "force_evaluations": 0,
        "reference_replayed": False, "counts": budget.counts, "native_returns": budget.completed}
    # Exclusivity is established before any scientific imports or kernel queries.
    with path.open("x") as stream:
        try:
            oracle = load("0153-real-ephemeris-oracle.py")
            compensated = load("0152-compensated-time-diagnostic.py", COMPENSATED_SHA)
            runner = load("0142-short-coast-runner.py")
            bundle = runner.inputs.load_inputs(budget.check)
            sources = (Path(__file__), HERE / "0153-real-ephemeris-oracle.py",
                       HERE / "0152-compensated-time-diagnostic.py")
            before = runner.inputs.runtime_identity(budget.check, extra_sources=sources)
            result["identity_before"] = before
            require(before["kernels"] == bundle["original_kernel_manifest"], "original kernel manifest")
            import spiceypy
            collect(spiceypy, oracle, compensated.split_epoch, budget, result)
            after = runner.inputs.runtime_identity(budget.check, extra_sources=sources)
            result["identity_after"] = after
            require(before == after, "before/after identity changed")
            budget.check()
            result["status"] = "passed"
        except (ValueError, TypeError, KeyError, AttributeError, OSError, ImportError, RuntimeError, ArithmeticError) as exc:
            result["status"] = "partial"
            result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        result["elapsed_before_flush_s"] = clock() - budget.start
        json.dump(wire(result), stream, indent=2, allow_nan=False)
        stream.flush()
        try:
            budget.check()
        except ValueError as exc:
            result["status"] = "partial"
            result["error"] = {"type": type(exc).__name__, "message": str(exc)}
            result["elapsed_after_failed_flush_s"] = clock() - budget.start
            stream.seek(0)
            stream.truncate()
            json.dump(wire(result), stream, indent=2, allow_nan=False)
            stream.flush()
    return wire(result)


def audit_saved(path: Path) -> dict[str, Any]:
    """Recheck serialized source rows with no native imports or state queries."""
    result = json.loads(path.read_text())
    require(result["status"] == "passed", "saved acquisition incomplete")
    require(result["identity_before"] == result["identity_after"], "saved identity mismatch")
    require(result["t0_tdb_s"] == T0 and result["t0_hex"] == T0.hex()
            and result["offsets_s"] == list(OFFSETS), "saved time contract")
    require(0 <= result["elapsed_before_flush_s"] < 60
            and result["spacecraft_propagations"] == result["force_evaluations"] == 0
            and result["reference_replayed"] is False, "saved scope/budget")
    require((result["origin"], result["orientation"], result["time_scale"],
             result["aberration_correction"]) == ("SSB", "J2000", "TDB", "NONE")
            and result["state_units"] == ["m"] * 3 + ["m/s"] * 3, "saved conventions")
    for name, expected in (("states", 21), ("selections", 28), ("descriptors", 28), ("arrays", 6)):
        require(result["counts"][name] == result["counts"][name + "_returned"] == expected,
                "saved call counts: " + name)
    require(1 <= result["counts"]["paths"] <= 3
            and result["counts"]["paths"] == result["counts"]["paths_returned"], "saved handle counts")
    oracle = load("0153-real-ephemeris-oracle.py")
    compensated = load("0152-compensated-time-diagnostic.py", COMPENSATED_SHA)
    require(len(result["rows"]) == 21, "saved row count")
    for row, (s, body) in zip(result["rows"],
            ((s, body) for s in OFFSETS for body in CHAINS), strict=True):
        hi, lo = compensated.split_epoch(T0, s)
        require((row["body"], row["elapsed_s"], row["elapsed_hex"], row["hi_tdb_s"],
                 row["hi_hex"], row["lo_s"], row["lo_hex"])
                == (body, s, s.hex(), hi, hi.hex(), lo, lo.hex()), "saved row/time order")
        require(row["state_si"] == [v * 1000 for v in finite(row["state_km_km_s"])],
                "saved unit conversion")
        require(len(row["segments"]) == len(CHAINS[body]), "saved centre chain length")
        records = []
        for segment, target in zip(row["segments"], CHAINS[body], strict=True):
            require((segment["body"], segment["centre"], segment["frame"], segment["type"])
                    == (target, CENTRES[target], 1, 2), "saved centre/frame/type")
            records.append(oracle.parse_record(segment["words"]))
        assessment = oracle.assess(row["state_si"], records, hi, lo)
        require(assessment == row["assessment"] and assessment["passed"], "saved exact assessment")
    require(any(not row["assessment"]["wrong_sign_passed"] for row in result["rows"]),
            "saved wrong-sign mutation")
    return {"status": "passed", "rows": 21, "native_calls": 0,
            "input_sha256": sha256(path.read_bytes()).hexdigest()}
