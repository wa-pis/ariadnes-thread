"""ADR0172 source capture and independent replay of its completed call sequence."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from ariadna_split_capture import (
    KERNEL_COUNT,
    _count,
    _inventory,
    _kernel_row,
    _native_call,
    _records,
    _runtime_pin,
    _selected_handle,
    _selector,
    _setup,
    _state,
)
from ariadna_split_common import BUDGETS, Recorder, number, require, same

EPOCH_COUNT = 16
CAPTURE_CAPS = {"setup": 1, "inventory": 30, "selector": EPOCH_COUNT, "state": EPOCH_COUNT}


def _epochs(bundle: dict[str, Any], moon: dict[str, Any]) -> list[float]:
    rows = bundle["epochs"]
    require(type(rows) is list and len(rows) == EPOCH_COUNT, "fixed 16 holdout epochs")
    lower, upper = moon["record_interval_tdb_s"]
    epochs = []
    for row in rows:
        raw = row["hi_tdb_s"]
        require(type(raw) is float, "holdout epoch must be a binary64 hi")
        hi = number(raw, "holdout hi TDB s")
        require(lower <= hi < upper, "holdout epoch outside Moon record coverage")
        epochs.append(hi)
    require(len(set(epochs)) == EPOCH_COUNT, "duplicate holdout hi epoch")
    return epochs


def capture(bundle: dict[str, Any], report: dict[str, Any], recorder: Recorder, *,
            adapter: Any, identity_pin: dict[str, Any]) -> None:
    """Read one Moon/Earth state after its selector; journal raw data before validation."""
    unavailable = list(range(EPOCH_COUNT))
    report.update(identity_pin=deepcopy(identity_pin), identities={}, capture_phase="metadata",
                  unavailable=unavailable)
    moon = _records(bundle)[301]
    epochs = _epochs(bundle, moon)
    expected_runtime = _runtime_pin(bundle)
    require(len(bundle["original_ordered_pool_manifest"]["kernels"]) == KERNEL_COUNT,
            "frozen kernel inventory size")

    def snapshot(phase: str) -> dict[str, Any]:
        report["capture_phase"] = phase + "_identity"
        recorder.check()
        current = {"runtime": adapter.identity(bundle, recorder.check), "kernels": []}
        report["identities"][phase] = current
        same(current["runtime"], expected_runtime, "pinned runtime/library/build identity")
        recorder.check()
        return current

    before = snapshot("before")
    report["capture_phase"] = "setup"
    _native_call(recorder, adapter, "setup", "load_standard_kernels", [], _setup)
    report["capture_phase"] = "before_inventory"
    before_rows = _inventory(bundle, adapter, recorder, before)
    handle = _selected_handle(before_rows, bundle)
    for hi in epochs:
        report["capture_phase"] = "selector"
        _native_call(recorder, adapter, "selector", "spksfs", [301, hi, 128],
                     lambda raw: _selector(raw, handle, hi, moon))
        report["capture_phase"] = "state"
        _native_call(recorder, adapter, "state", "spkezr", ["Moon", hi, "J2000", "NONE", "Earth"], _state)
        del unavailable[0]

    after = snapshot("after")
    report["capture_phase"] = "after_inventory"
    after_rows = _inventory(bundle, adapter, recorder, after)
    same(after_rows, before_rows, "before/after raw inventory")
    same(after, before, "before/after kernel and runtime identity")
    recorder.check()
    report["capture_phase"] = "complete"


def validate_capture(bundle: dict[str, Any], report: dict[str, Any],
                     identity_pin: dict[str, Any]) -> list[list[float]]:
    """Verify the complete capture ledger without consulting the adapter or SPICE."""
    same(report["identity_pin"], identity_pin, "capture tested helper/input identity")
    require(report["capture_phase"] == "complete" and report["unavailable"] == [], "capture incomplete")
    moon = _records(bundle)[301]
    epochs = _epochs(bundle, moon)
    budget = BUDGETS["capture"]
    require(report["budget_s"] == budget, "capture frozen deadline")
    same(report["counts"], {name: dict.fromkeys(("attempted", "returned", "completed"), cap)
                           for name, cap in CAPTURE_CAPS.items()}, "capture exact counts")
    ledger = report["ledger"]
    require(type(ledger) is list and len(ledger) == sum(CAPTURE_CAPS.values()),
            "capture completed ledger length")
    steps = iter(ledger)
    previous_s = 0.0

    def event(operation: str, api: str, args: list[Any]) -> Any:
        nonlocal previous_s
        entry = next(steps)
        require(type(entry) is dict and set(entry) == {
            "operation", "api", "args", "attempted_s", "returned_s", "raw", "completed_s",
        }, "capture complete ledger event")
        same([entry["operation"], entry["api"], entry["args"]], [operation, api, args],
             "capture ordered call/args")
        attempted, returned, complete = (number(entry[key], "capture event time") for key in
                                          ("attempted_s", "returned_s", "completed_s"))
        require(previous_s <= attempted <= returned <= complete <= budget, "capture ordered ledger/deadline")
        previous_s = complete
        return entry["raw"]

    _setup(event("setup", "load_standard_kernels", []))
    identities = report["identities"]
    require(type(identities) is dict and set(identities) == {"before", "after"}, "capture identity snapshots")
    runtime = _runtime_pin(bundle)
    kernels = bundle["original_ordered_pool_manifest"]["kernels"]
    require(len(kernels) == KERNEL_COUNT, "frozen kernel inventory size")
    parent = Path(moon["path"]).parent

    def inventory(phase: str) -> list[Any]:
        snapshot = identities[phase]
        require(type(snapshot) is dict and set(snapshot) == {"runtime", "kernels"}
                and len(snapshot["kernels"]) == KERNEL_COUNT, "capture kernel snapshot size")
        same(snapshot["runtime"], runtime, "capture runtime/library/build identity")
        _count(event("inventory", "ktotal", ["ALL"]))
        raw_rows = []
        for index, expected in enumerate(kernels):
            raw = event("inventory", "kdata", [index, "ALL"])
            _kernel_row(raw, snapshot["kernels"][index], expected, parent)
            raw_rows.append(raw)
        _count(event("inventory", "get_total_count_of_kernels_loaded", []))
        return raw_rows

    before_rows = inventory("before")
    handle = _selected_handle(before_rows, bundle)
    states = []
    for hi in epochs:
        _selector(event("selector", "spksfs", [301, hi, 128]), handle, hi, moon)
        states.append(_state(event("state", "spkezr", ["Moon", hi, "J2000", "NONE", "Earth"])))
    same(inventory("after"), before_rows, "capture raw inventory stability")
    same(identities["after"], identities["before"], "capture identity stability")
    require(next(steps, None) is None, "capture trailing ledger entry")
    return states
