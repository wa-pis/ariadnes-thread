"""Run one observed native B profile using the frozen ADR0140 adapter."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Protocol

HERE = Path(__file__).resolve().parent
ADAPTER_SHA256 = "8bc888d6e1c638251d8379d6d4c896393b5cd76fb71e85c65c7faf9aab9294e2"
BODIES = ("Sun", "Moon", "Earth")
ORDER = ("normal", "tighter")
OFFSETS = (0., 50., 100., 150., 200., 250., 300.)
type Row = dict[str, Any]


class Budget(Protocol):
    def check(self) -> None: ...
    def event(self, operation: str, phase: str) -> None: ...


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_adapter() -> ModuleType:
    path = HERE / "0140-short-coast-native.py"
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == ADAPTER_SHA256, "ADR0140 adapter digest")
    module = ModuleType("earth_b_native_adapter")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def wire(value: object) -> Any:
    """Keep native arrays and explicit invalid values JSON-safe before checks."""
    if hasattr(value, "tolist"):
        value = value.tolist()
    if type(value) is float and not math.isfinite(value):
        return {"invalid_numeric": repr(value)}
    if value is None or type(value) in (str, bool, int, float):
        return value
    if type(value) in (tuple, list):
        return [wire(x) for x in value]
    if type(value) is dict:
        return {str(k): wire(x) for k, x in value.items()}
    return {"invalid_type": type(value).__name__}


@dataclass(slots=True)
class Arc:
    """Observe ADR0140's existing attempt and raw-return boundaries."""

    budget: Budget
    row: Row
    arcs_completed: int = 0
    arcs_returned: int = 0

    def check(self) -> None:
        self.budget.check()

    @property
    def arcs_attempted(self) -> int:
        return self.row["arc"]["attempted"]

    @arcs_attempted.setter
    def arcs_attempted(self, value: int) -> None:
        require(value == 1 and self.arcs_attempted == 0, "one native attempt per profile")
        self.budget.event("native_arcs", "attempt")
        self.row["arc"]["attempted"] = value

    @property
    def last_returned(self) -> Row | None:
        return self.row.get("raw_returned")

    @last_returned.setter
    def last_returned(self, raw: Row) -> None:
        require(self.arcs_attempted == self.arcs_returned == 1
                and "raw_returned" not in self.row, "unmatched native arc return")
        self.row["raw_returned"] = wire(raw)
        self.row["arc"]["returned"] = 1
        self.budget.event("native_arcs", "return")


def inventory(adapter: ModuleType, prepared: Any, gm_m3_s2: Row) -> Row:
    adapter.validate_inventory(prepared)
    require(prepared.included == BODIES and prepared.gravity_parameters_m3_s2 == gm_m3_s2,
            "native B sources/GM configuration")
    bodies = prepared.bodies
    return {
        "model": "B", "origin": bodies.global_frame_origin(),
        "orientation": bodies.global_frame_orientation(), "aberration": "NONE",
        "force_order": ["total", *BODIES],
        "force_counts": {body: len(prepared.accelerations["Spacecraft"][body]) for body in BODIES},
        "gm_m3_s2": {body: adapter.number(float(
            bodies.get(body).gravity_field_model.gravitational_parameter)) for body in BODIES},
    }


def solve_profile(bundle: Row, name: str, report: Row, budget: Budget, *,
                  adapter: ModuleType | None = None) -> Row:
    """Run the next B-only RK4 profile and retain existing guard returns once."""
    profiles = report.setdefault("native_profiles", [])
    require(len(profiles) < 2 and name == ORDER[len(profiles)]
            and all(p["arc"]["completed"] == 1 for p in profiles), "native B profile order/cap")
    adapter = load_adapter() if adapter is None else adapter
    require(tuple(bundle["offsets_s"]) == OFFSETS and bundle["gm_m3_s2"] == adapter.GM
            and bundle["radii_m"] == adapter.GUARDS, "native B frozen controls")
    raw_initial = bundle["initial"]
    t0 = adapter.number(raw_initial["epoch_tdb_s"])
    initial = adapter.vector(raw_initial["position_m"] + raw_initial["velocity_m_s"], 6)
    step_s = 1. if name == "normal" else 0.5
    row: Row = {"name": name, "step_s": step_s, "guards": [],
                "arc": {"attempted": 0, "returned": 0, "completed": 0}}
    profiles.append(row)
    prepared = adapter.build_model("B", budget.check)
    row["inventory"] = inventory(adapter, prepared, bundle["gm_m3_s2"])
    context = Arc(budget, row)
    radii = bundle["radii_m"]

    def guard(at: float, state: tuple[float, ...]) -> None:
        reads = row["guards"]
        group = len(reads) // len(BODIES)
        expected = t0 + max(0, group-1)*step_s
        require(len(reads) % len(BODIES) == 0 and at == expected
                and group <= int(300/step_s)+1, "native guard order/grid")
        for body in BODIES:
            budget.event("native_guard_reads", "attempt")
            entry = {"body": body, "epoch_tdb_s": at, "group": group}
            reads.append(entry)
            try:
                raw = prepared.bodies.get(body).ephemeris.cartesian_state(at)
            except Exception as exc:  # Untyped native ephemeris boundary.
                raise ValueError(f"native guard failed: {body} at {at}: {exc}") from exc
            entry["state_si"] = wire(raw.reshape(-1) if hasattr(raw, "reshape") else raw)
            budget.event("native_guard_reads", "return")
            position = adapter.vector(entry["state_si"], 6)[:3]
            distance_m = math.dist(state[:3], position)
            require(math.isfinite(distance_m), "native guard distance nonfinite")
            entry["distance_m"] = distance_m
            entry["passed"] = distance_m > radii[body]
            require(entry["passed"], f"native {body} exclusion sphere at {at}")
            budget.event("native_guard_reads", "complete")

    result = adapter.propagate(prepared, initial, t0, 300., step_s, OFFSETS, context, guard)
    require(context.arcs_completed == 1 and context.arcs_returned == 1,
            "native arc did not finalize its history")
    require(len(row["guards"]) == 3*(2+int(300/step_s)), "native guard coverage")
    row["result"] = wire(result)
    row["arc"]["completed"] = 1
    budget.event("native_arcs", "complete")
    return row
