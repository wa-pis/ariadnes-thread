"""ADR0156 private fixed-position calculator; never imports scientific libraries."""
from __future__ import annotations

# ruff: noqa: E402 -- The cooperative clock includes the remaining imports.
from time import monotonic

PROCESS_START = monotonic()

from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable, TextIO

ROOT = Path(__file__).resolve().parents[3]
ARMS = ("compensated", "uncorrected", "wrong_sign")
MODELS = {"A": ("Sun", "Moon"), "B": ("Sun", "Moon", "Earth")}
RADII = {"Sun": 696000000.0, "Moon": 1737400.0, "Earth": 6378136.6}
CAPS = {"source_rows": 21, "reference_fields": 168, "binary64_fields": 63,
        "model_totals": 14}
HELPERS = ("0157-fixed-gravity-inputs.py", "0157-fixed-gravity-reference.py",
           "0157-fixed-gravity-study.py", "0157-fixed-gravity-audit.py",
           "0153-real-ephemeris-oracle.py", "0145-short-coast-evidence.py")
FAILURES = (ValueError, TypeError, KeyError, IndexError, AttributeError, OSError,
            ImportError, RuntimeError, ArithmeticError)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def number(value: object, label: str) -> float:
    require(type(value) in (int, float), label + ": expected finite nonboolean number")
    result = float(value)
    require(math.isfinite(result), label + ": expected finite number")
    return result


def vector(value: object, label: str) -> list[float]:
    require(isinstance(value, (list, tuple)) and len(value) == 3, label + ": three components")
    return [number(component, label) for component in value]


class Budget:
    """Bound completed work without erasing attempted or post-return failures."""

    def __init__(self, clock: Callable[[], float], start_s: float) -> None:
        self.clock = clock
        self.start = number(start_s, "start_s")
        self.counts = {name: {"attempted": 0, "completed": 0} for name in CAPS}
        self.ledger: list[dict[str, str]] = []
        self.stage = "inputs"

    def elapsed(self) -> float:
        return number(self.clock(), "clock") - self.start

    def check(self) -> None:
        require(0 <= self.elapsed() < 10.0, "deadline/clock")

    def event(self, name: str, phase: str, *, stage: str | None = None) -> None:
        require(name in CAPS and phase in ("attempt", "complete"), "work event")
        count = self.counts[name]
        if phase == "attempt":
            self.check()
            if stage is not None:
                self.stage = stage
            require(count["attempted"] < CAPS[name], "work cap: " + name)
            count["attempted"] += 1
        else:
            require(count["completed"] < count["attempted"], "unattempted completion")
            count["completed"] += 1
        self.ledger.append({"operation": name, "phase": phase})
        self.check()


def load(root: Path, name: str, expected: str) -> ModuleType:
    path = root / "docs/adr/experiments" / name
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == expected, "helper identity: " + name)
    spec = importlib.util.spec_from_file_location("fixed_gravity_" + name.replace("-", "_"), path)
    require(spec is not None and spec.loader is not None, "private module loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def fingerprints(root: Path, check: Callable[[], None]) -> dict[str, str]:
    result = {}
    for name in HELPERS:
        check()
        result[name] = sha256((root / "docs/adr/experiments" / name).read_bytes()).hexdigest()
        check()
    return result


def calculate_arms(row: dict[str, Any], position_m: object, gm_m3_s2: object,
                   radius_m: object, event: Callable[[str], None],
                   target: dict[str, Any] | None = None) -> dict[str, Any]:
    """Binary64 fsum separation and direct SSB gravity; controls are diagnostic."""
    position = vector(position_m, "position_m")
    state = row["state_si"]
    require(isinstance(state, list) and len(state) == 6, "state_si: six components")
    body = [number(v, "state_si") for v in state]
    low = number(row["lo_s"], "lo_s")
    gm = number(gm_m3_s2, "gm_m3_s2")
    guard = number(radius_m, "radius_m")
    require(gm > 0 and guard > 0, "positive GM/radius")
    correction = [body[j + 3] * low for j in range(3)]
    require(all(math.isfinite(v) for v in correction), "finite rephasing product")
    result = {} if target is None else target
    for name in ARMS:
        event("attempt")
        applied = (correction if name == "compensated" else
                   [0.0, 0.0, 0.0] if name == "uncorrected" else [-v for v in correction])
        delta = [math.fsum((body[j], -position[j], applied[j])) for j in range(3)]
        # Fraction comparison keeps the strict exterior guard independent of hypot rounding.
        from fractions import Fraction
        require(sum(Fraction.from_float(v)**2 for v in delta)
                > Fraction.from_float(guard)**2, "exterior domain: " + row["body"])
        radius = math.hypot(*delta)
        require(math.isfinite(radius) and radius > 0, "finite positive separation norm")
        force = [gm * (v / radius) / (radius * radius) for v in delta]
        require(all(math.isfinite(v) for v in force), "finite force")
        result[name] = {"separation_m": delta, "rephasing_m": list(applied),
                        "acceleration_m_s2": force}
        event("complete")
    return result


def total_arms(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_body = {row["source_row"]["body"]: row["arms"] for row in rows}
    require(set(by_body) == set(RADII) and len(rows) == 3, "model source inventory")
    return {model: {arm: {"acceleration_m_s2": [
        math.fsum(by_body[body][arm]["acceleration_m_s2"][j] for body in bodies)
        for j in range(3)]} for arm in ARMS} for model, bodies in MODELS.items()}


def safe_wire(value: Any) -> Any:
    """Keep partial malformed operands explicit without nonfinite JSON tokens."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"invalid_number": repr(value)}
    if isinstance(value, dict):
        return {str(k): safe_wire(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_wire(v) for v in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return {"invalid_type": type(value).__name__}


def failure(result: dict[str, Any], stage: str, exc: BaseException) -> None:
    error = {"stage": stage, "type": type(exc).__name__, "message": str(exc)}
    result.setdefault("first_error", error)
    result["error"] = error
    result["status"] = "partial"


def safe_elapsed(budget: Budget) -> float | None:
    try:
        return budget.elapsed()
    except FAILURES:
        return None


def flush_result(stream: TextIO, result: dict[str, Any], budget: Budget) -> dict[str, Any]:
    result["elapsed_before_flush_s"] = safe_elapsed(budget)
    result["finalization_gate"] = "passed"
    try:
        budget.check()
        json.dump(safe_wire(result), stream, allow_nan=False, indent=2)
        stream.flush()
        budget.check()
    except FAILURES as exc:
        failure(result, "finalization", exc)
        result["finalization_gate"] = "failed"
        result["elapsed_after_failed_flush_s"] = safe_elapsed(budget)
        # A cooperative overrun must not leave a persisted passed result.
        stream.seek(0)
        stream.truncate()
        json.dump(safe_wire(result), stream, allow_nan=False, indent=2)
        stream.flush()
    return safe_wire(result)


def execute(path: Path, *, root: Path = ROOT, clock: Callable[[], float] = monotonic,
            start_s: float | None = None, inputs_loader: Callable[..., Any] | None = None,
            references: Any = None) -> dict[str, Any]:
    """One exclusive 10s offline study; injected fixtures cannot qualify real data."""
    start = (PROCESS_START if clock is monotonic else clock()) if start_s is None else start_s
    start = number(start, "start_s")
    result: dict[str, Any] = {
        "contract": "ADR0156", "study": "fixed-position-real-gravity-v1",
        "status": "partial", "adapter_mode": "reference" if inputs_loader is None
        and references is None and clock is monotonic else "injected-test", "research_only": True,
        "mission_accuracy_verified": False, "continuous_safety_verified": False,
        "origin": "SSB", "orientation": "J2000", "time_scale": "TDB",
        "aberration_correction": "NONE", "acceleration_units": "m/s^2",
        "budget_s": 10.0, "native_calls": 0, "kernel_loads": 0,
        "gm_acquisitions": 0, "spacecraft_propagations": 0, "scientific_imports": 0,
        "reference_replayed": False, "rows": [], "totals": [],
        "finalization_gate": "failed",
    }
    # Refuse an existing output before reading scientific inputs or loading helpers.
    with Path(path).open("x") as stream:
        budget = Budget(clock, start)
        result["counts"], result["ledger"] = budget.counts, budget.ledger
        try:
            budget.check()
            if result["adapter_mode"] == "reference":
                require(budget.start <= PROCESS_START, "process-start baseline cannot be reset")
                forbidden = {"numpy", "scipy", "spiceypy", "tudatpy", "space_nav"}
                require(not any(name.split(".")[0] in forbidden for name in sys.modules),
                        "reference study requires fresh stdlib-only process")
            hashes = fingerprints(root, budget.check)
            result["helper_sha256"] = hashes
            if inputs_loader is None:
                inputs_loader = load(root, "0157-fixed-gravity-inputs.py",
                                     hashes["0157-fixed-gravity-inputs.py"]).load_inputs
            if references is None:
                references = load(root, "0157-fixed-gravity-reference.py",
                                  hashes["0157-fixed-gravity-reference.py"])
            bundle = inputs_loader(root, budget.check)
            snapshot = {key: deepcopy(bundle[key]) for key in (
                "position_m", "initial", "gm_m3_s2", "input_sha256",
                "source_provenance", "identity")}
            result["inputs"] = snapshot
            require(isinstance(bundle["rows"], list) and len(bundle["rows"]) == 21,
                    "exactly21 source rows")
            for i, raw in enumerate(bundle["rows"]):
                budget.event("source_rows", "attempt", stage=f"source:{i}")
                row: dict[str, Any] = {"index": i, "source_row": deepcopy(raw), "arms": {},
                                        "reference_progress": {}}
                result["rows"].append(row)
                expected = ("Sun", "Earth", "Moon")[i % 3]
                require(raw["body"] == expected, "source row order")
                arms = calculate_arms(raw, snapshot["position_m"],
                    snapshot["gm_m3_s2"][expected], RADII[expected],
                    lambda phase: budget.event("binary64_fields", phase), row["arms"])
                row["assessment"] = references.assess_source(raw, snapshot["position_m"],
                    snapshot["gm_m3_s2"][expected], RADII[expected], arms,
                    lambda phase: budget.event("reference_fields", phase),
                    progress=row["reference_progress"])
                budget.event("source_rows", "complete")
                require(row["assessment"]["passed"] is True, "required source force/precision gate")
                if i % 3 == 2:
                    time_index = i // 3
                    group = {"index": time_index, "elapsed_s": raw["elapsed_s"],
                             "arms": total_arms(result["rows"][-3:]), "assessment": {}}
                    result["totals"].append(group)
                    def consume_model(phase: str) -> None:
                        n = budget.counts["model_totals"]["attempted"]
                        label = ("A", "B")[(n if phase == "attempt" else n-1) % 2]
                        budget.event("model_totals", phase,
                                     stage=f"totals:{time_index}:{label}" if phase == "attempt" else None)
                    group["assessment"] = references.assess_totals(
                        [r["assessment"] for r in result["rows"][-3:]], group["arms"],
                        consume_model=consume_model, progress=group["assessment"])
                    require(set(group["assessment"]) == set(MODELS)
                            and all(v["passed"] is True for v in group["assessment"].values()),
                            "required model force/precision gate")
            require(all(c["attempted"] == c["completed"] == CAPS[k]
                        for k, c in budget.counts.items()), "complete counts")
            budget.stage = "identity"
            after_bundle = inputs_loader(root, budget.check)
            after = {key: after_bundle[key] for key in snapshot}
            require(json.dumps(snapshot, sort_keys=True, allow_nan=False)
                    == json.dumps(after, sort_keys=True, allow_nan=False), "input identity changed")
            require(hashes == fingerprints(root, budget.check), "helper identity changed")
            result["identity_after"] = deepcopy(after)
            budget.check()
            result["status"] = "passed"
        except FAILURES as exc:
            failure(result, budget.stage, exc)
        return flush_result(stream, result, budget)
