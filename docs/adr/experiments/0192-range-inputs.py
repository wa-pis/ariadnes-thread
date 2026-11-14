"""Load the immutable R5.43 report operands without scientific dependencies."""

from __future__ import annotations

from collections.abc import Callable
import gzip
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
from typing import Any

ARCHIVES = Path("docs/adr/experiments")
MANIFEST_SHA = "6a4a04491af0f94805b7f21dc99aa1ee967fc434fc0cef091a60f8c14d9e7a61"
DESIGN_SHA = "dca18b7a555c89e27ae0a3ac4251d93f33b28a354f195334ba0e4748136a797e"
CONTRACT = "ADR0188"
ORDER = ("native_normal", "native_tighter", "dop853_normal", "dop853_tighter")
OFFSETS = tuple(range(0, 601, 50))
BODY_ORDER = ("Sun", "Moon", "Earth")
COUNTS = {"comparisons": 39, "observations": 52, "native_telemetry": 26,
          "direction_rows": 52, "net_range_signs": 4}

type Check = Callable[[], None]
type Wire = dict[str, Any]
type Row = tuple[float, list[float], list[float]]
type Histories = dict[str, list[Row]]


def _need(condition: object, field: str) -> None:
    if not condition:
        raise ValueError("R5.43 archive: " + field)


def _number(raw: object) -> float:
    if type(raw) not in (float, int):
        raise ValueError("R5.43 archive: expected finite binary64 number")
    try:
        value = float(raw)
    except OverflowError as exc:
        raise ValueError("R5.43 archive: binary64 overflow") from exc
    _need(math.isfinite(value), "nonfinite binary64 number")
    return value


def _vec(raw: object, size: int = 6) -> list[float]:
    if type(raw) is not list or len(raw) != size:
        raise ValueError(f"R5.43 archive: expected vector of length {size}")
    return [_number(v) for v in raw]


def _words(raw: object, size: int = 6) -> list[str]:
    return [v.hex() for v in _vec(raw, size)]


def _epoch(raw: object, expected: float) -> None:
    _need(_number(raw).hex() == expected.hex(), "wrong epoch")


def _verified_bytes(path: Path, digest: str, check: Check, size: int | None = None) -> bytes:
    check()
    if size is not None:
        _need(path.stat().st_size == size, path.name + " byte count")
    data = path.read_bytes()
    _need((size is None or len(data) == size) and sha256(data).hexdigest() == digest,
          path.name + " digest")
    check()
    return data


def _invalid(token: str) -> None:
    raise ValueError(f"R5.43 archive: nonfinite JSON token {token}")


def _json(data: bytes) -> Wire:
    result = json.loads(data, parse_constant=_invalid)
    if not isinstance(result, dict):
        raise ValueError("R5.43 archive: JSON root is not an object")
    return result


def _phase(folder: Path, name: str, files: Wire, manifest: Wire, check: Check) -> tuple[Wire, str]:
    report_name = name + ".json.gz"
    spec = files[report_name]
    data = _verified_bytes(folder / report_name, spec["sha256"], check, spec["bytes"])
    size = spec["original_bytes"]
    with gzip.GzipFile(fileobj=BytesIO(data)) as stream:
        raw = stream.read(size + 1)
    digest = sha256(raw).hexdigest()
    _need(len(raw) == size and digest == spec["original_sha256"], name + " original report digest")
    report = _json(raw)
    check()

    side = {}
    for kind in ("attempt", "receipt", "parent-attempt", "parent-receipt"):
        filename = f"{name}.{kind}.json"
        record = files[filename]
        side[kind] = _json(_verified_bytes(folder / filename, record["sha256"], check, record["bytes"]))
    attempt, child = side["attempt"], side["receipt"]
    parent_attempt, parent = side["parent-attempt"], side["parent-receipt"]
    expected = {"contract": CONTRACT, "phase": name, "revision": manifest["measured_revision"],
                "preparation_sha256": manifest["preparation_sha256"]}
    _need(parent_attempt == expected and all(parent[k] == v for k, v in expected.items()),
          name + " parent identity")
    _need(attempt["contract"] == report["contract"] == CONTRACT and
          attempt["adapter_mode"] == report["adapter_mode"] == "reference", name + " study mode")
    for field, kind in (("attempt_sha256", "attempt"), ("child_receipt_sha256", "receipt"),
                        ("parent_attempt_sha256", "parent-attempt")):
        _need(parent[field] == files[f"{name}.{kind}.json"]["sha256"], name + " receipt link")
    _need(child["evidence_sha256"] == parent["evidence_sha256"] == digest, name + " evidence receipt")
    _need(child["status"] == "passed" and type(parent["returncode"]) is int and
          parent["returncode"] == 0 and parent["checkout_frozen"] is True and
          report["finalization_gate"] == child["finalization_gate"] == parent["finalization_gate"] == "passed",
          name + " status/finalization")
    cap = 60 if name == "study" else 10
    _need(report["budget_s"] == cap and 0 < _number(child["elapsed_s"]) <= _number(parent["elapsed_s"]) <= cap,
          name + " budget")
    _need(_number(attempt["started_s"]) == _number(child["started_s"]) == _number(parent["started_s"]),
          name + " start receipt")
    return report, digest


def _moon(raw: Wire, epoch: float) -> list[float]:
    _need((raw["body"], raw["observer"], raw["frame"], raw["aberration"]) ==
          ("Moon", "SSB", "J2000", "NONE"), "Moon frame/body identity")
    _epoch(raw["epoch_tdb_s"], epoch)
    state = _vec(raw["state_si"])
    _need(_words(state) == [float(x * 1000).hex() for x in _vec(raw["state_km_km_s"])],
          "Moon SI unit image")
    return state


def _mesh(profile: Wire, t0: float, count: int, step: float, check: Check) -> list[Row]:
    raw = profile["raw_returned"]
    outcome = profile["result"]
    _need(raw["integration_completed"] is True and profile["step_s"] == outcome["step_s"] == step and
          outcome["retained_states"] == outcome["guarded_states"] == count and
          (outcome["origin"], outcome["orientation"], outcome["position_units"], outcome["velocity_units"],
           outcome["time_units"]) == ("SSB", "J2000", "m", "m/s", "TDB seconds since J2000"),
          "native mesh metadata")
    history = raw["state_history"]
    _need(isinstance(history, dict) and len(history) == count, "native mesh count")
    states = {}
    for key, values in history.items():
        check()
        epoch = _number(float(key))
        _need(epoch not in states, "duplicate native mesh epoch")
        states[epoch] = _vec(values)
    guards = profile["guards"]
    _need(len(guards) == 3 * (count + 1), "native guard count")
    rows = []
    for group in range(count + 1):
        check()
        epoch = t0 + max(0, group - 1) * step
        _need(epoch in states, "missing native mesh epoch")
        for i, body in enumerate(BODY_ORDER):
            guard = guards[group*3+i]
            _need(type(guard["group"]) is int and guard["group"] == group and guard["body"] == body and
                  guard["passed"] is True, "native guard order/status")
            _epoch(guard["epoch_tdb_s"], epoch)
        if group:
            rows.append((epoch, states[epoch], _vec(guards[group*3+1]["state_si"])))
    return rows


def _native(study: Wire, moons: list[list[float]], t0: float, mass: float,
            check: Check) -> tuple[Histories, Histories]:
    common: Histories = {}
    meshes: Histories = {}
    for profile, name, step, count in zip(study["native_profiles"], ORDER[:2], (1., .5),
                                          (601, 1201), strict=True):
        _need("native_" + profile["name"] == name and _number(profile["coast_mass_kg"]) == mass,
              "native profile identity/mass")
        inventory = profile["inventory"]
        _need((inventory["model"], inventory["origin"], inventory["orientation"], inventory["aberration"],
               inventory["force_order"], inventory["gm_m3_s2"]) ==
              ("B", "SSB", "J2000", "NONE", ["total", *BODY_ORDER], study["inputs"]["coast"]["gm_m3_s2"]),
              "native inventory")
        mesh = _mesh(profile, t0, count, step, check)
        grid = []
        for offset, moon, sample in zip(OFFSETS, moons, profile["result"]["samples"], strict=True):
            check()
            epoch = t0 + offset
            _epoch(sample["epoch_tdb_s"], epoch)
            sc = _vec(sample["state"])
            _need(_words(sc) == _words(mesh[int(offset / step)][1]), "native coepoch state words")
            grid.append((epoch, sc, moon))
        common[name], meshes["mesh_" + name] = grid, mesh
    return common, meshes


def _adaptive(study: Wire, moons: list[list[float]], initial: list[float], t0: float,
              mass: float, check: Check) -> Histories:
    common = {}
    settings = study["inputs"]["coast"]["dop853_settings"]
    for profile, name, cfg in zip(study["profiles"], ORDER[2:], settings, strict=True):
        _need("dop853_" + profile["name"] == name and profile["settings"] == cfg and
              _number(profile["coast_mass_kg"]) == mass, "DOP853 profile identity/mass")
        raw = profile["raw_returned"]
        _need(raw["success"] is True and type(raw["status"]) is int and raw["status"] == 0 and
              _vec(raw["t"], 13) == list(OFFSETS) and len(raw["y"]) == 6, "DOP853 raw output grid")
        components = [_vec(component, 13) for component in raw["y"]]
        grid = []
        for j, (offset, moon, out, corr) in enumerate(zip(OFFSETS, moons, profile["outputs"],
                                                        zip(*components, strict=True), strict=True)):
            check()
            epoch = t0 + offset
            _epoch(out["hi_tdb_s"], epoch)
            _need(type(out["index"]) is int and out["index"] == j and
                  out["profile"] == profile["name"] and _number(out["elapsed_s"]) == offset and
                  _number(out["lo_s"]) == 0 and _words(out["correction"]) == _words(list(corr)),
                  "DOP853 output membership")
            motion = out["motion"]
            sc = _vec(motion["position_m"], 3) + _vec(motion["velocity_m_s"], 3)
            expected = [math.fsum((initial[k], initial[k+3]*offset, corr[k])) for k in range(3)]
            expected += [math.fsum((initial[k], corr[k])) for k in range(3, 6)]
            _need(_words(sc) == _words(expected), "DOP853 raw correction and state words")
            _need(_words(_moon(out["bodies"]["Moon"], epoch)) == _words(moon), "DOP853 common Moon words")
            grid.append((epoch, sc, moon))
        common[name] = grid
    return common


def _comparisons(study: Wire, audit: Wire, common: Histories, check: Check) -> None:
    expected = [("native_step", j, ORDER[0], ORDER[1], .01, 1e-5) for j in range(13)]
    for j in range(13):
        expected.extend((("native_tighter", j, ORDER[1], ORDER[3], .01, 1e-5),
                         ("oracle_step", j, ORDER[2], ORDER[3], .001, 1e-6)))
    _need(audit["checks"]["comparison_summary"] == study["comparison_summary"],
          "audit comparison summary")
    for (family, j, left, right, pos, vel), saved in zip(expected, study["comparisons"], strict=True):
        check()
        epoch, a, _ = common[left][j]
        _, b, _ = common[right][j]
        _epoch(saved["epoch_tdb_s"], epoch)
        _need(saved["name"] == family and type(saved["index"]) is int and saved["index"] == j,
              "comparison membership")
        gate = saved["assessment"]
        _need((gate["position_limit_m"], gate["velocity_limit_m_s"]) == (pos, vel) and
              all(gate[field] is True for field in ("passed", "position_passed", "velocity_passed")) and
              math.dist(a[:3], b[:3]) <= pos and math.dist(a[3:], b[3:]) <= vel, family + " gate")


def _audited_operands(study: Wire, audit: Wire, common: Histories, initial: list[float], check: Check) -> None:
    for saved in (study["direction"]["rows"], audit["checks"]["direction"]["rows"]):
        _need(len(saved) == 52, "audited direction row count")
        for index, (name, grid) in enumerate(common.items()):
            _need(_words(grid[0][1]) == _words(initial), "initial state words")
            for j, (epoch, sc, moon) in enumerate(grid):
                check()
                row = saved[index*13+j]
                _epoch(row["epoch_tdb_s"], epoch)
                _need(row["profile"] == name and type(row["index"]) is int and row["index"] == j and
                      _words(row["spacecraft"]) == _words(sc) and _words(row["moon"]) == _words(moon),
                      "audited coepoch operand words")


def _load_histories(study: Wire, audit: Wire, design: Wire, manifest: Wire, check: Check) -> Histories:
    inputs, scope = study["inputs"], manifest["scope"]
    _need(tuple(study[k] for k in ("model", "origin", "orientation", "time_scale", "aberration_correction",
                                    "position_units", "velocity_units", "duration_s")) ==
          ("B", "SSB", "J2000", "TDB", "NONE", "m", "m/s", 600), "coast identity/units")
    _need(design["candidate"] == scope["candidate"] == "d0001-t0035" and
          inputs["cutoff"] == scope["cutoff"] == design["boundary_state"] and
          inputs["initial"] == scope["initial_state"], "archived cutoff/candidate")
    mass = _number(scope["mass_kg"])
    cutoff = inputs["cutoff"]
    t0 = _number(cutoff["epoch_tdb_s"])
    initial = _vec(cutoff["position_m"], 3) + _vec(cutoff["velocity_m_s"], 3)
    frozen = design["cutoff_binary64_hex"]
    _need(t0.hex() == frozen["epoch_tdb_s"] and mass.hex() == frozen["mass_kg"] and
          _words(initial) == frozen["position_m"] + frozen["velocity_m_s"], "cutoff binary64 words")
    _epoch(inputs["initial"]["epoch_tdb_s"], t0)
    _need(_words(inputs["initial"]["position_m"], 3) + _words(inputs["initial"]["velocity_m_s"], 3) ==
          _words(initial), "initial cutoff state words")
    coast = inputs["coast"]
    _need(coast == scope["coast"] == design["coast"] and
          tuple(coast["sources"]) == BODY_ORDER and tuple(coast["offsets_s"]) == OFFSETS and
          coast["coepochs_tdb_s"] == [t0 + d for d in OFFSETS] and coast["thrust_n"] == coast["mass_flow_kg_s"] == 0,
          "frozen source and coast grid")
    _need(all(_number(x) == mass for x in (design["boundary_mass_kg"], inputs["mass_kg"],
                                          study["coast_mass_kg"], coast["constant_mass_metadata_kg"])),
          "constant cutoff mass")
    kept = study["identities"]["before"]
    kernels = kept["kernels"]
    _need(kept == study["identities"]["after"] and kept["revision"] == manifest["measured_revision"] and
          kernels == inputs["kernel_manifest"] and kernels["loaded_kernel_count"] == len(kernels["kernels"]) == 13,
          "saved kernel and runtime identity")
    audit_snapshots = audit["snapshot_checks"]
    _need(audit_snapshots["before"] == audit_snapshots["after"], "saved audit identity")
    moons = []
    for offset, row in zip(OFFSETS, study["node_table"], strict=True):
        check()
        _epoch(row["hi_tdb_s"], t0 + offset)
        _need(_number(row["elapsed_s"]) == offset and _number(row["lo_s"]) == 0,
              "common node epoch")
        moons.append(_moon(row["bodies"]["Moon"], t0 + offset))
    native, meshes = _native(study, moons, t0, mass, check)
    common = native | _adaptive(study, moons, initial, t0, mass, check)
    _audited_operands(study, audit, common, initial, check)
    _comparisons(study, audit, common, check)
    return common | meshes


def load(root: Path, check: Check) -> tuple[Histories, dict[str, str]]:
    """Bind R5.43 through its receipts and return the six saved grids."""
    archive = root / ARCHIVES
    folder = archive / "0190"
    design = _json(_verified_bytes(archive / "0188-design-inputs.json", DESIGN_SHA, check))
    manifest = _json(_verified_bytes(folder / "manifest.json", MANIFEST_SHA, check))
    _need(manifest["contract"] == design["contract"] == CONTRACT and
          manifest["stage"] == "R5.43" and design["stage"] == "R5.41" and
          manifest["numerical_status"] == "passed" and manifest["verified_counts"] == COUNTS, "manifest scope")
    files = manifest["files"]
    study, study_sha = _phase(folder, "study", files, manifest, check)
    audit, audit_sha = _phase(folder, "audit", files, manifest, check)
    _need(study["status"] == audit["audit_status"] == "passed" and audit["checks"]["passed"] is True and
          study["preparation_manifest_sha256"] == manifest["preparation_sha256"], "saved audit result/preparation")
    _need(audit["study_sha256"] == study_sha and
          audit["study_receipts"] == {
              f"{kind}_sha256": files[f"study.{kind}.json"]["sha256"]
              for kind in ("attempt", "receipt", "parent-attempt", "parent-receipt")
          }, "audit study linkage")
    _need(all(audit["checks"][key] == value for key, value in COUNTS.items()) and
          all(type(audit[k]) is int and audit[k] == 0 for k in
              ("native_calls", "scientific_imports", "kernel_loads", "spacecraft_propagations")),
          "saved audit counts and offline scope")
    result = _load_histories(study, audit, design, manifest, check)
    pins = {"manifest_sha256": MANIFEST_SHA, "design_sha256": DESIGN_SHA,
            "study_sha256": study_sha, "audit_sha256": audit_sha,
            "study_gzip_sha256": files["study.json.gz"]["sha256"], "audit_gzip_sha256": files["audit.json.gz"]["sha256"]}
    return result, pins
