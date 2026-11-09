"""Private ADR0166 capture and saved-ledger validation; native imports are lazy."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from importlib import import_module
import os
from pathlib import Path
import platform
from struct import pack, unpack
import sys
from typing import Any

from ariadna_split_common import CAPTURE_CAPS, Recorder, digest, number, require, same, wire

Sample = dict[str, Any]
StateRow = dict[str, list[float]]
KERNEL_COUNT = 13
STATES = (("E", "Earth", "SSB"), ("G", "Moon", "Earth"), ("B", "Moon", "SSB"))
BODIES = (399, 301)
SAMPLES = (
    (13, "rhs", 6, 0.25, "0x1.d2d247fbd7e7ap+29"),
    (0, "output", 0, 0.0, "0x1.d2d247f9d7e7ap+29"),
    (5, "output", 5, 250.0, "0x1.d2d24fc9d7e7ap+29"),
)


def _samples(bundle: dict[str, Any]) -> list[Sample]:
    rows = bundle["samples_in_probe_order"]
    require(type(rows) is list and len(rows) == len(SAMPLES), "fixed three samples")
    for row, expected in zip(rows, SAMPLES, strict=True):
        same([row["observation_ordinal"], row["normal_kind"], row["source_index"],
              row["elapsed_s"], row["hi_hex"]], list(expected), "fixed sample order")
        require(number(row["hi_tdb_s"], "sample hi").hex() == row["hi_hex"]
                and row["lo_hex"] == "0x0.0p+0", "sample coepoch hi/lo bits")
    return rows


def _count(raw: Any) -> None:
    require(type(raw) is int and raw == KERNEL_COUNT, "ordered thirteen-kernel count")


def _found(raw: Any, fields: int, label: str) -> list[Any]:
    require(type(raw) is list and len(raw) in (fields, fields + 1),
            f"{label} raw return shape")
    require(len(raw) == fields or raw[-1] is True, f"{label} not found")
    return raw[:fields]


def _kernel_entry(raw: Any) -> list[Any]:
    fields = _found(raw, 4, "kdata")
    path, kind, source, handle = fields
    require(type(path) is str and Path(path).is_absolute()
            and type(kind) is str and kind in ("SPK", "TEXT")
            and type(source) is str and type(handle) is int
            and (handle > 0 if kind == "SPK" else handle == 0), "kdata raw identity")
    return fields


def _kernel_row(raw: Any, current: Any, expected: Any, parent: Path) -> None:
    path, kind, source, _handle = _kernel_entry(raw)
    require(type(current) is dict and set(current) == {"path", "metadata"}
            and current["path"] == path == str(parent / expected["name"])
            and kind == expected["type"] and (source or None) == expected["source"],
            "kernel inventory path/type/source")
    same(current["metadata"], expected, "kernel inventory digest and metadata")


def _selected_handle(raw_rows: list[Any], bundle: dict[str, Any]) -> int:
    entries = [_kernel_entry(raw) for raw in raw_rows]
    handles = [item[3] for item in entries if item[1] == "SPK"]
    require(len(set(handles)) == len(handles)
            and len({item[0] for item in entries}) == KERNEL_COUNT,
            "unique inventory paths and SPK handles")
    paths = {record["path"] for record in bundle["records"]}
    require(len(paths) == 1, "both selectors use the same frozen kernel")
    selected = [(row, info) for row, info in zip(
        entries, bundle["original_ordered_pool_manifest"]["kernels"], strict=True
    ) if row[0] in paths]
    require(len(selected) == 1 and selected[0][0][1] == "SPK"
            and selected[0][1]["sha256"] == bundle["locked_selected_kernel_sha256"],
            "selector kernel path/digest from inventory")
    return selected[0][0][3]


def _state(raw: Any) -> list[float]:
    require(type(raw) is list and len(raw) == 2 and type(raw[0]) is list
            and len(raw[0]) == 6, "spkezr six components and light time")
    require(all(type(item) is float for item in [*raw[0], raw[1]]),
            "spkezr binary64 state and light time")
    number(raw[1], "spkezr light time s")
    return [number(value, "spkezr state km/km/s") for value in raw[0]]


def _selector(raw: Any, handle: int, hi_tdb_s: float, record: dict[str, Any]) -> None:
    selected_handle, descriptor, label = _found(raw, 3, "spksfs")
    require(type(selected_handle) is int and selected_handle == handle
            and type(label) is str and label == record["label"], "spksfs handle or label")
    require(type(descriptor) is list and len(descriptor) == 5
            and all(type(value) is float for value in descriptor), "spksfs descriptor shape/type")
    values = [number(value, "spksfs descriptor word") for value in descriptor]
    require([value.hex() for value in values] == record["descriptor_hex"],
            "spksfs frozen descriptor bytes")
    # Archived descriptor words are the binary64 encodings of packed DAF summaries.
    body, centre, frame, kind, begin, end = unpack("<6i", pack("<3d", *values[2:]))
    require((body, centre, frame, kind, begin, end) == (
        record["body"], record["centre"], 1, 2, record["begin"], record["end"]
    ) and (body, centre) in ((399, 0), (301, 399)) and begin > 0,
        "spksfs decoded centre/frame/type/addresses")
    first, last = values[:2]
    init, interval, size, count = record["trailer"]
    lower, upper = record["record_interval_tdb_s"]
    index = record["index"]
    require(first == record["first_tdb_s"] == init and last == record["last_tdb_s"]
            and interval > 0 and size == record["word_count"] == 41
            and index == 12192 and 0 <= index < count
            and lower == init + index * interval and upper == lower + interval
            and first <= lower <= hi_tdb_s < upper <= last
            and begin + index * size == record["address"]
            and end == begin + size * count + 3, "spksfs frozen Type 2 record coverage")


def _records(bundle: dict[str, Any]) -> dict[int, Any]:
    records = bundle["records"]
    require(type(records) is list and [row["body"] for row in records] == [301, 399],
            "two frozen segment descriptors")
    return {row["body"]: row for row in records}


def _runtime_pin(bundle: dict[str, Any]) -> dict[str, Any]:
    history = bundle["historical_identity"]
    versions = history["versions"]
    cspice = bundle["local_cspice_file_pin"]
    prefix = Path(cspice["path"]).parents[1]
    spice = history["r5_runtime"]["builds"]["spiceypy"]
    tudat = history["conda_build"]
    resources = history["resource_build"]

    def package_path(record: dict[str, Any], digest: str) -> dict[str, str]:
        name = f"{record['name']}-{record['version']}-{record['build']}.json"
        return {"path": str(prefix / "conda-meta" / name), "sha256": digest}

    def module_path(record: dict[str, Any], module: str) -> dict[str, str]:
        matches = [entry for entry in record["paths_data"]["paths"]
                   if entry["_path"].endswith("/site-packages/" + module)]
        require(len(matches) == 1, "frozen Conda module record: " + module)
        entry = matches[0]
        return {"path": str(prefix / entry["_path"]),
                "sha256": entry.get("sha256_in_prefix", entry["sha256"])}

    tudat_init = module_path(tudat, "tudatpy/__init__.py")
    spice_init = module_path(spice["record"], "spiceypy/__init__.py")
    require(tudat_init["path"] == history["imports"]["tudatpy"]
            and spice_init == history["r5_runtime"]["modules"]["spiceypy"],
            "frozen imported module locations")
    return {
        "versions": {name: versions[name] for name in
                     ("python", "tudatpy", "spiceypy", "tudat-resources")},
        "prefix": str(prefix),
        "files": {
            "tudatpy": tudat_init,
            "tudatpy_interface": module_path(tudat, "tudatpy/interface/spice/__init__.py"),
            "tudatpy_native": history["native_binary"],
            "spiceypy": spice_init,
            "spiceypy_wrapper": module_path(spice["record"], "spiceypy/spiceypy.py"),
            "spiceypy_loader": module_path(spice["record"], "spiceypy/utils/libspicehelper.py"),
            "spiceypy_conda": {"path": spice["metadata_path"], "sha256": spice["metadata_sha256"]},
            "tudatpy_conda": package_path(tudat, history["conda_metadata_sha256"]),
            "resource_conda": package_path(resources, history["resource_metadata_sha256"]),
            "cspice": {key: cspice[key] for key in ("path", "sha256")},
            "cspice_conda": {"path": cspice["conda_record"], "sha256": cspice["conda_record_sha256"]},
        },
    }


class _Native:
    """Only the six explicitly budgeted native API names are exposed."""

    def __init__(self) -> None:
        require(not any(name in sys.modules for name in ("spiceypy", "tudatpy")),
                "capture requires a fresh native process")
        require(not os.environ.get("CSPICE_SHARED_LIB"), "CSPICE library override")
        self.spiceypy = import_module("spiceypy")
        self.tudat = import_module("tudatpy")
        self.tudat_spice = import_module("tudatpy.interface.spice")
        self.tudat_native = import_module("tudatpy.kernel")
        self.wrapper = import_module("spiceypy.spiceypy")
        self.loader = import_module("spiceypy.utils.libspicehelper")

    @staticmethod
    def _call(function: Callable[..., Any], *args: Any) -> Any:
        try:
            return function(*args)
        except Exception as exc:  # Untyped native API boundary.
            raise ValueError(f"native {function.__name__} failed: {exc}") from exc

    def load_standard_kernels(self) -> Any:
        return self._call(self.tudat_spice.load_standard_kernels)

    def ktotal(self, kind: str) -> Any:
        return self._call(self.spiceypy.ktotal, kind)

    def kdata(self, index: int, kind: str) -> Any:
        return self._call(self.spiceypy.kdata, index, kind)

    def get_total_count_of_kernels_loaded(self) -> Any:
        return self._call(self.tudat_spice.get_total_count_of_kernels_loaded)

    def spkezr(self, target: str, hi_tdb_s: float, frame: str, abcorr: str, observer: str) -> Any:
        return self._call(self.spiceypy.spkezr, target, hi_tdb_s, frame, abcorr, observer)

    def spksfs(self, target: int, hi_tdb_s: float, idlen: int) -> Any:
        return self._call(self.spiceypy.spksfs, target, hi_tdb_s, idlen)

    def identity(self, bundle: dict[str, Any], check: Callable[[], None]) -> dict[str, Any]:
        expected = _runtime_pin(bundle)
        resources = bundle["historical_identity"]["resource_build"]
        paths = {
            "tudatpy": self.tudat.__file__,
            "tudatpy_interface": self.tudat_spice.__file__,
            "tudatpy_native": self.tudat_native.__file__,
            "spiceypy": self.spiceypy.__file__,
            "spiceypy_wrapper": self.wrapper.__file__,
            "spiceypy_loader": self.loader.__file__,
            "cspice": self.loader.libspice_path,
        }
        files = {}
        for key, entry in expected["files"].items():
            check()
            path = Path(paths.get(key, entry["path"])).resolve(strict=True)
            files[key] = {"path": str(path), "sha256": digest(path)}
            check()
        return {
            "versions": {"python": platform.python_version(), "tudatpy": self.tudat.__version__,
                         "spiceypy": self.spiceypy.__version__, "tudat-resources": resources["version"]},
            "prefix": str(Path(sys.prefix).resolve()),
            "files": files,
        }

    @staticmethod
    def kernel_metadata(path_text: str, kind: str, source: str,
                        check: Callable[[], None]) -> dict[str, Any]:
        check()
        path = Path(path_text).resolve(strict=True)
        result = {"path": str(path), "metadata": {
            "name": path.name, "version": path.stem, "type": kind,
            "source": source or None, "size_bytes": path.stat().st_size,
            "sha256": digest(path),
        }}
        check()
        return result


def native_adapter() -> _Native:
    """Construct the real adapter only from a future fresh authorized process."""
    return _Native()


def _native_call(recorder: Recorder, adapter: Any, operation: str, api: str,
                 args: list[Any], validate: Callable[[Any], None]) -> Any:
    return wire(recorder.call(operation, api, args, lambda: getattr(adapter, api)(*args),
                              lambda raw: validate(wire(raw))))


def _setup(raw: Any) -> None:
    require(raw is None, "standard setup return")


def _inventory(bundle: dict[str, Any], adapter: Any, recorder: Recorder,
               snapshot: dict[str, Any]) -> list[Any]:
    call = _native_call
    raw_rows = []
    parent = Path(bundle["records"][0]["path"]).parent
    call(recorder, adapter, "inventory", "ktotal", ["ALL"], _count)
    for index, expected in enumerate(bundle["original_ordered_pool_manifest"]["kernels"]):
        raw = call(recorder, adapter, "inventory", "kdata", [index, "ALL"], _kernel_entry)
        path, kind, source, _handle = _kernel_entry(raw)
        raw_rows.append(raw)
        current = adapter.kernel_metadata(path, kind, source, recorder.check)
        snapshot["kernels"].append(current)
        _kernel_row(raw, current, expected, parent)
    call(recorder, adapter, "inventory", "get_total_count_of_kernels_loaded", [], _count)
    return raw_rows


def capture(bundle: dict[str, Any], report: dict[str, Any], recorder: Recorder, *,
            adapter: Any, identity_pin: dict[str, Any]) -> None:
    """Acquire a single ordered sequence; store each raw response via the recorder."""
    report["identity_pin"] = deepcopy(identity_pin)
    report["identities"] = {}
    report["capture_phase"] = "metadata"
    rows = _samples(bundle)
    records = _records(bundle)
    expected_runtime = _runtime_pin(bundle)
    require(len(bundle["original_ordered_pool_manifest"]["kernels"]) == KERNEL_COUNT,
            "frozen kernel inventory size")

    def snapshot(phase: str) -> dict[str, Any]:
        report["capture_phase"] = phase + "_identity"
        recorder.check()
        result = {"runtime": adapter.identity(bundle, recorder.check), "kernels": []}
        report["identities"][phase] = result
        same(result["runtime"], expected_runtime, "pinned runtime/library/build identity")
        recorder.check()
        return result

    before = snapshot("before")
    report["capture_phase"] = "setup"
    _native_call(recorder, adapter, "setup", "load_standard_kernels", [], _setup)
    report["capture_phase"] = "before_inventory"
    before_rows = _inventory(bundle, adapter, recorder, before)
    handle = _selected_handle(before_rows, bundle)
    report["capture_phase"] = "states"
    for row in rows:
        for _key, target, observer in STATES:
            args = [target, row["hi_tdb_s"], "J2000", "NONE", observer]
            _native_call(recorder, adapter, "state", "spkezr", args, _state)
    report["capture_phase"] = "selectors"
    for row in rows:
        hi_tdb_s = row["hi_tdb_s"]
        for body in BODIES:
            _native_call(recorder, adapter, "selector", "spksfs", [body, hi_tdb_s, 128],
                         lambda raw: _selector(raw, handle, hi_tdb_s, records[body]))
    after = snapshot("after")
    report["capture_phase"] = "after_inventory"
    after_rows = _inventory(bundle, adapter, recorder, after)
    same(after_rows, before_rows, "before/after raw inventory")
    same(after, before, "before/after kernel and runtime identity")
    recorder.check()
    report["capture_phase"] = "complete"


def validate_capture(bundle: dict[str, Any], report: dict[str, Any],
                     identity_pin: dict[str, Any]) -> list[StateRow]:
    """Replay capture arguments, data, count and clock constraints without native imports."""
    same(report["identity_pin"], identity_pin, "tested helper/input identity")
    require(report["capture_phase"] == "complete", "capture is incomplete")
    rows = _samples(bundle)
    records = _records(bundle)
    ledger = report["ledger"]
    require(type(ledger) is list and len(ledger) == sum(CAPTURE_CAPS.values()),
            "capture completed ledger length")
    expected_counts = {op: {"attempted": cap, "returned": cap, "completed": cap}
                       for op, cap in CAPTURE_CAPS.items()}
    same(report["counts"], expected_counts, "capture exact counts")
    require(report["budget_s"] == 15.0, "capture frozen deadline")
    steps = iter(ledger)
    previous = 0.0

    def event(operation: str, api: str, args: list[Any]) -> Any:
        nonlocal previous
        entry = next(steps)
        require(type(entry) is dict and set(entry) == {
            "operation", "api", "args", "attempted_s", "returned_s", "raw", "completed_s"
        }, "capture complete ledger event")
        same([entry["operation"], entry["api"], entry["args"]], [operation, api, args],
             "capture ordered call/args")
        attempted, returned, complete = (
            number(entry[key], "capture event time") for key in
            ("attempted_s", "returned_s", "completed_s")
        )
        require(previous <= attempted <= returned <= complete <= 15.0,
                "capture ordered ledger/deadline")
        previous = complete
        return entry["raw"]

    _setup(event("setup", "load_standard_kernels", []))
    expected_kernels = bundle["original_ordered_pool_manifest"]["kernels"]
    require(len(expected_kernels) == KERNEL_COUNT, "frozen kernel inventory size")
    identities = report["identities"]
    require(type(identities) is dict and set(identities) == {"before", "after"},
            "capture identity snapshots")
    runtime = _runtime_pin(bundle)
    parent = Path(bundle["records"][0]["path"]).parent

    def inventory(phase: str) -> list[Any]:
        snapshot = identities[phase]
        require(type(snapshot) is dict and set(snapshot) == {"runtime", "kernels"}
                and len(snapshot["kernels"]) == KERNEL_COUNT, "capture kernel snapshot size")
        same(snapshot["runtime"], runtime, "capture runtime/library/build identity")
        _count(event("inventory", "ktotal", ["ALL"]))
        raw_rows = []
        for index, expected in enumerate(expected_kernels):
            raw = event("inventory", "kdata", [index, "ALL"])
            _kernel_row(raw, snapshot["kernels"][index], expected, parent)
            raw_rows.append(raw)
        _count(event("inventory", "get_total_count_of_kernels_loaded", []))
        return raw_rows

    before_rows = inventory("before")
    handle = _selected_handle(before_rows, bundle)
    states = [
        {key: _state(event("state", "spkezr", [target, row["hi_tdb_s"], "J2000", "NONE", observer]))
         for key, target, observer in STATES}
        for row in rows
    ]
    for row in rows:
        hi_tdb_s = row["hi_tdb_s"]
        for body in BODIES:
            raw = event("selector", "spksfs", [body, hi_tdb_s, 128])
            _selector(raw, handle, hi_tdb_s, records[body])
    after_rows = inventory("after")
    same(after_rows, before_rows, "capture raw inventory stability")
    same(identities["after"], identities["before"], "capture identity stability")
    require(next(steps, None) is None, "capture trailing ledger entry")
    return states
