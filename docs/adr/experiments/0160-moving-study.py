"""Private ADR0159 moving-coordinate preparation; no scientific imports or solve."""
from __future__ import annotations

# ruff: noqa: E402 -- Include imports in the cooperative process budget.
from time import monotonic

PROCESS_START = monotonic()

from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable, TextIO

ROOT = Path(__file__).resolve().parents[3]
ARMS = ("compensated", "flattened_craft", "omitted_q")
MODELS = {"A": ("Sun", "Moon"), "B": ("Sun", "Moon", "Earth")}
RADII = {"Sun": 696000000.0, "Moon": 1737400.0, "Earth": 6378136.6}
CAPS = {"six_state_assemblies": 7, "source_rows": 21, "reference_fields": 168,
        "binary64_fields": 63, "model_totals": 14}
HELPERS = ("0160-moving-inputs.py", "0160-moving-reference.py", "0160-moving-study.py",
           "0160-moving-audit.py", "0157-fixed-gravity-inputs.py",
           "0157-fixed-gravity-reference.py", "0157-fixed-gravity-audit.py",
           "0153-real-ephemeris-oracle.py", "0145-short-coast-evidence.py")
SNAPSHOT = ("position_m", "initial", "gm_m3_s2", "input_sha256", "source_provenance",
            "identity", "zero_reference")
FAILURES = (ValueError, TypeError, KeyError, IndexError, AttributeError, OSError,
            ImportError, RuntimeError, ArithmeticError)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def number(value: Any, field: str) -> float:
    require(type(value) in (int, float), field + ": finite nonboolean number required")
    result = float(value)
    require(math.isfinite(result), field + ": finite number required")
    return result


def vector(value: Any, field: str) -> list[float]:
    require(isinstance(value, (list, tuple)) and len(value) == 3, field + ": three components")
    return [number(v, field) for v in value]


def ratios(values: list[Fraction]) -> list[dict[str, str]]:
    return [{"numerator": str(v.numerator), "denominator": str(v.denominator)} for v in values]


def assemble_motion(initial: dict[str, Any], elapsed_s: float,
                    target: dict[str, Any] | None = None) -> dict[str, Any]:
    """Prescribe input corrections; keep drift separate from absolute coordinates."""
    r0, v0 = vector(initial["position_m"], "position_m"), vector(initial["velocity_m_s"], "velocity_m_s")
    elapsed = number(elapsed_s, "elapsed_s")
    require(0 <= elapsed <= 300.0, "elapsed_s outside controlled interval")
    result = {} if target is None else target
    result.update(label="controlled-kinematic-arithmetic-probe", elapsed_s=elapsed,
                  elapsed_hex=elapsed.hex())
    s = Fraction.from_float(elapsed)
    a = (Fraction(-1), Fraction(1, 2), Fraction(-1, 4))
    q_ideal = [value * s * s / 2 for value in a]
    w_ideal = [value * s for value in a]
    result["q_ideal_m"], result["w_ideal_m_s"] = ratios(q_ideal), ratios(w_ideal)
    q, w = [float(v) for v in q_ideal], [float(v) for v in w_ideal]
    require(all(math.isfinite(v) for v in q + w), "finite prescribed corrections")
    result.update(q_m=q, q_hex=[v.hex() for v in q],
                  q_ratios=ratios([Fraction.from_float(v) for v in q]),
                  w_m_s=w, w_hex=[v.hex() for v in w],
                  w_ratios=ratios([Fraction.from_float(v) for v in w]))
    drift = [number(v * elapsed, "drift_m") for v in v0]
    result["drift_m"] = drift
    result["position_m"] = [number(math.fsum((r0[j], drift[j], q[j])), "assembled position_m")
                            for j in range(3)]
    result["velocity_m_s"] = [number(math.fsum((v0[j], w[j])), "assembled velocity_m_s")
                              for j in range(3)]
    return result


def calculate_arms(row: dict[str, Any], initial: dict[str, Any], motion: dict[str, Any],
                   gm_m3_s2: float, radius_m: float, event: Callable[[str], None],
                   target: dict[str, Any] | None = None, *,
                   preflight: Callable[[dict[str, Any]], Any] | None = None) -> dict[str, Any]:
    """Direct SSB point forces from split operands; controls remain diagnostic."""
    r0 = vector(initial["position_m"], "r0")
    drift, q = vector(motion["drift_m"], "drift_m"), vector(motion["q_m"], "q_m")
    craft = vector(motion["position_m"], "assembled position_m")
    state = row["state_si"]
    require(type(state) is list and len(state) == 6, "source state_si: six components")
    state = [number(v, "state_si") for v in state]
    low = number(row["lo_s"], "lo_s")
    gm, radius = number(gm_m3_s2, "gm_m3_s2"), number(radius_m, "radius_m")
    require(gm > 0 and radius > 0, "positive GM/radius required")
    correction = [number(v * low, "rephasing_m") for v in state[3:]]
    prepared: dict[str, Any] = {}
    norms: dict[str, tuple[float, float]] = {}
    for arm in ARMS:
        if arm == "flattened_craft":
            delta = [math.fsum((state[j], -craft[j], correction[j])) for j in range(3)]
        else:
            delta = [math.fsum((state[j], -r0[j], -drift[j],
                               -q[j] if arm == "compensated" else 0.0, correction[j]))
                     for j in range(3)]
        delta = vector(delta, "separation_m")
        require(sum((Fraction.from_float(v)**2 for v in delta), Fraction())
                > Fraction.from_float(radius)**2, "exterior domain: " + str(row["body"]))
        rho = number(math.hypot(*delta), "separation norm")
        squared = number(rho * rho, "squared separation norm")
        require(rho > 0 and squared > 0, "positive separation norms required")
        prepared[arm] = {"separation_m": delta, "rephasing_m": list(correction)}
        norms[arm] = (rho, squared)
    if preflight is not None:
        preflight(prepared)
    result = {} if target is None else target
    for arm in ARMS:
        event("attempt")
        rho, squared = norms[arm]
        force = [number(gm * (v / rho) / squared, "acceleration_m_s2")
                 for v in prepared[arm]["separation_m"]]
        result[arm] = {**prepared[arm], "acceleration_m_s2": force}
        event("complete")
    return result


def total_arms(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_body = {r["source_row"]["body"]: r["arms"] for r in rows}
    require(set(by_body) == {"Sun", "Earth", "Moon"}, "model source inventory")
    return {model: {arm: {"acceleration_m_s2": [number(math.fsum(
        by_body[body][arm]["acceleration_m_s2"][j] for body in bodies), "model acceleration")
        for j in range(3)]} for arm in ARMS} for model, bodies in MODELS.items()}


class Budget:
    def __init__(self, clock: Callable[[], float], start_s: float) -> None:
        self.clock, self.start = clock, start_s
        self.stage = "inputs"
        self.counts = {name: {"attempted": 0, "completed": 0} for name in CAPS}
        self.ledger: list[dict[str, str]] = []

    def elapsed(self) -> float:
        return number(number(self.clock(), "clock") - self.start, "elapsed_s")

    def check(self) -> None:
        require(0 <= self.elapsed() < 10.0, "deadline/clock")

    def event(self, operation: str, phase: str, stage: str | None = None) -> None:
        require(operation in CAPS and phase in ("attempt", "complete"), "work event")
        count = self.counts[operation]
        if phase == "attempt":
            self.check()
            if stage is not None:
                self.stage = stage
            require(count["attempted"] < CAPS[operation], "work cap: " + operation)
            count["attempted"] += 1
        else:
            require(count["completed"] < count["attempted"], "unattempted completion")
            count["completed"] += 1
        self.ledger.append({"operation": operation, "phase": phase})
        self.check()


def load(root: Path, name: str, expected: str) -> ModuleType:
    path = root / "docs/adr/experiments" / name
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == expected, "helper identity: " + name)
    spec = importlib.util.spec_from_file_location("moving_" + name.replace("-", "_"), path)
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


def safe_wire(value: Any) -> Any:
    if type(value) is float and not math.isfinite(value):
        return {"invalid_nonfinite": repr(value)}
    if isinstance(value, dict):
        return {k: safe_wire(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_wire(v) for v in value]
    if value is None or type(value) in (str, int, float, bool):
        return value
    return {"invalid_unserializable": repr(value)}


def finite_tree(value: Any) -> None:
    if type(value) is float:
        require(math.isfinite(value), "nonfinite result")
    elif isinstance(value, dict):
        require(all(type(k) is str for k in value), "JSON object keys")
        for item in value.values():
            finite_tree(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            finite_tree(item)
    else:
        require(value is None or type(value) in (str, int, bool), "non-JSON result")


def failure(result: dict[str, Any], stage: str, error: BaseException) -> None:
    result["status"] = "partial"
    result["error"] = {"stage": stage, "type": type(error).__name__, "message": str(error)}
    result.setdefault("first_error", dict(result["error"]))


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
    except FAILURES as error:
        failure(result, "finalization", error)
        result["finalization_gate"] = "failed"
        result["elapsed_after_failed_flush_s"] = safe_elapsed(budget)
        stream.seek(0)
        stream.truncate()
        json.dump(safe_wire(result), stream, allow_nan=False, indent=2)
        stream.flush()
    return safe_wire(result)


def execute(path: Path, *, root: Path = ROOT, clock: Callable[[], float] = monotonic,
            start_s: float | None = None, inputs_loader: Callable[..., Any] | None = None,
            references: Any = None) -> dict[str, Any]:
    """One future bounded moving probe; tests with injections never qualify science."""
    start = (PROCESS_START if clock is monotonic else clock()) if start_s is None else start_s
    start = number(start, "start_s")
    require(number(clock(), "clock") >= start, "invalid future process baseline")
    real = inputs_loader is None and references is None and clock is monotonic
    require(not real or start <= PROCESS_START, "process-start baseline cannot be reset")
    result: dict[str, Any] = {
        "contract": "ADR0159", "study": "controlled-moving-assembly-v1", "status": "partial",
        "adapter_mode": "reference" if real else "injected-test", "research_only": True,
        "mission_accuracy_verified": False, "continuous_safety_verified": False,
        "origin": "SSB", "orientation": "J2000", "time_scale": "TDB", "aberration_correction": "NONE",
        "position_units": "m", "velocity_units": "m/s", "acceleration_units": "m/s^2",
        "budget_s": 10.0, "native_calls": 0, "scientific_imports": 0, "kernel_loads": 0,
        "gm_acquisitions": 0, "spacecraft_propagations": 0, "optimizer_calls": 0,
        "reference_replayed": False, "motions": [], "rows": [], "totals": [], "finalization_gate": "failed",
    }
    with path.open("x", encoding="utf-8") as stream:
        budget = Budget(clock, start)
        result["counts"], result["ledger"] = budget.counts, budget.ledger
        try:
            budget.check()
            if real:
                forbidden = {"numpy", "scipy", "spiceypy", "tudatpy", "space_nav"}
                require(not any(n.split(".")[0] in forbidden for n in sys.modules),
                        "reference study requires fresh stdlib-only process")
            hashes = fingerprints(root, budget.check)
            result["helper_sha256"] = hashes
            if inputs_loader is None:
                inputs_loader = load(root, HELPERS[0], hashes[HELPERS[0]]).load_inputs
            if references is None:
                references = load(root, HELPERS[1], hashes[HELPERS[1]])
            bundle = inputs_loader(root, budget.check)
            snapshot = {k: deepcopy(bundle[k]) for k in SNAPSHOT}
            result["inputs"] = snapshot
            require(type(bundle["rows"]) is list and len(bundle["rows"]) == 21, "exactly21 source rows")
            for time_index in range(7):
                elapsed = bundle["rows"][3 * time_index]["elapsed_s"]
                budget.event("six_state_assemblies", "attempt", f"motion:{time_index}")
                block: dict[str, Any] = {"index": time_index, "motion": {}}
                result["motions"].append(block)
                motion = assemble_motion(snapshot["initial"], elapsed, block["motion"])
                block["assessment"] = references.assess_motion(snapshot["initial"], motion)
                finite_tree(block["assessment"])
                budget.event("six_state_assemblies", "complete")
                require(block["assessment"]["passed"] is True, "required motion assembly gate")
                if time_index == 0:
                    require(motion["position_m"] == snapshot["initial"]["position_m"]
                            and motion["velocity_m_s"] == snapshot["initial"]["velocity_m_s"],
                            "elapsed-zero initial state parity")
                for raw_index in range(3 * time_index, 3 * time_index + 3):
                    raw = bundle["rows"][raw_index]
                    budget.event("source_rows", "attempt", f"source:{raw_index}")
                    row: dict[str, Any] = {"index": raw_index, "source_row": deepcopy(raw),
                                          "arms": {}, "reference_progress": {}}
                    result["rows"].append(row)
                    body = ("Sun", "Earth", "Moon")[raw_index % 3]
                    require(raw["body"] == body and raw["elapsed_s"] == elapsed, "source order/elapsed")
                    arms = calculate_arms(raw, snapshot["initial"], motion, snapshot["gm_m3_s2"][body],
                                          RADII[body], lambda phase: budget.event("binary64_fields", phase),
                                          row["arms"], preflight=lambda draft: references.preflight_source(
                                              raw, snapshot["initial"], motion, snapshot["gm_m3_s2"][body],
                                              RADII[body], draft, progress=row["reference_progress"]))
                    if time_index == 0:
                        require(arms["compensated"] == snapshot["zero_reference"]["sources"][body],
                                "elapsed-zero source parity: " + body)
                    row["assessment"] = references.assess_source(raw, snapshot["initial"], motion,
                        snapshot["gm_m3_s2"][body], RADII[body], arms,
                        lambda phase: budget.event("reference_fields", phase), progress=row["reference_progress"])
                    finite_tree(row["assessment"])
                    budget.event("source_rows", "complete")
                    require(row["assessment"]["passed"] is True, "required source force/assembly/precision gate")
                group: dict[str, Any] = {"index": time_index, "elapsed_s": elapsed,
                                         "arms": total_arms(result["rows"][-3:]), "assessment": {}}
                result["totals"].append(group)
                def consume_model(phase: str) -> None:
                    n = budget.counts["model_totals"]["attempted"]
                    model = ("A", "B")[(n if phase == "attempt" else n-1) % 2]
                    budget.event("model_totals", phase,
                                 f"totals:{time_index}:{model}" if phase == "attempt" else None)
                    if phase == "attempt" and time_index == 0:
                        require(group["arms"][model]["compensated"]
                                == snapshot["zero_reference"]["totals"][model],
                                "elapsed-zero model parity: " + model)
                references.assess_totals([r["assessment"] for r in result["rows"][-3:]],
                                        group["arms"], consume_model=consume_model, progress=group["assessment"])
                finite_tree(group["assessment"])
                require(list(group["assessment"]) == list(MODELS)
                        and all(v["passed"] is True for v in group["assessment"].values()),
                        "required model force/precision gate")
            require(all(c["attempted"] == c["completed"] == CAPS[k] for k, c in budget.counts.items()),
                    "complete operation counts")
            budget.stage = "identity"
            after_bundle = inputs_loader(root, budget.check)
            after = {k: after_bundle[k] for k in SNAPSHOT}
            require(json.dumps(snapshot, sort_keys=True, allow_nan=False)
                    == json.dumps(after, sort_keys=True, allow_nan=False), "input identity changed")
            require(hashes == fingerprints(root, budget.check), "helper identity changed")
            result["identity_after"] = deepcopy(after)
            budget.check()
            result["status"] = "passed"
        except FAILURES as error:
            failure(result, budget.stage, error)
        return flush_result(stream, result, budget)
