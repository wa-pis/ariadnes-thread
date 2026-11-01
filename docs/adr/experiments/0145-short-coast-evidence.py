"""ADR0143 stdlib-only JSON/input/file-identity checks. No execution/audit verdict API."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
Check = Callable[[], None]
INPUT_SHA = {
    "0119-m2-reference.json": "3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0",
    "0098-central-correction-study.json": "b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057",
    "0133-gravity-screen.json": "74238edd641e1b5fda42a209672c68e5bc201b20d3cffba24169e6f9b3b6a580",
    "0136-retained-boundary-audit.json": "81d78ecf6e4e80b55e9d909f929a879b2e392667387ec2569632aa99a6b41063",
}
PREPARED_SHA = {
    "0128-reference-coast.py": "027d0b4e45f9ebd941249e427963e365fd7205f9594a96365a587eb0e8cd7e81",
    "0128-audit-reference-coast.py": "138d6c98b9f914dbcc7b26355e0e8c2019bece997f1d18b089a90b3cce095ad9",
    "0138-short-coast-oracle.py": "d6a624f727e17de364f188f0941f2e1889741204ad035aefd9263728cf95e029",
    "0140-short-coast-native.py": "8bc888d6e1c638251d8379d6d4c896393b5cd76fb71e85c65c7faf9aab9294e2",
    "0141-short-coast-inputs.py": "4457d9094afe3e8b674a46704b6789fdd724469cb8e1efe5cc054ce39d34c37c",
    "0142-short-coast-runner.py": "a1e6c74d7316d876f05c8d9527170ed633aeef86726dab91da9e2fdce96524ab",
}
VERSIONS = {
    "python": "3.12.14",
    "tudatpy": "1.0.0",
    "tudat-resources": "2.4",
    "numpy": "1.26.4",
    "scipy": "1.17.1",
    "spiceypy": "8.2.0",
}
MODULES = (
    "numpy",
    "scipy",
    "spiceypy",
    "scipy.integrate",
    "scipy.integrate._ivp.ivp",
    "scipy.integrate._ivp.rk",
    "scipy.integrate._ivp.dop853_coefficients",
    "numpy.core._multiarray_umath",
    "numpy.linalg._umath_linalg",
)
SHAPES = {"A": [16, 16], "B": [12], "C": [16], "D": [4, 16], "E3": [13], "E5": [13]}
CALLABLES = {
    "solve_ivp": ("scipy.integrate._ivp.ivp", "solve_ivp"),
    "rk_step": ("scipy.integrate._ivp.rk", "rk_step"),
    "DOP853_step": ("scipy.integrate._ivp.rk", "RungeKutta._step_impl"),
    "DOP853_error": ("scipy.integrate._ivp.rk", "DOP853._estimate_error_norm"),
    "DOP853_dense": ("scipy.integrate._ivp.rk", "DOP853._dense_output_impl"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def idle() -> None:
    pass


def reject_constant(token: str) -> None:
    raise ValueError("nonfinite JSON constant: " + token)


def finite_float(token: str) -> float:
    value = float(token)
    require(math.isfinite(value), "nonfinite JSON number")
    return value


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def parse(raw: bytes | str) -> dict[str, Any]:
    result = json.loads(
        raw,
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
        parse_float=finite_float,
    )
    require(isinstance(result, dict), "JSON root must be an object")
    return result


def canonical(value: object) -> str:
    """Preserve JSON number versus boolean distinctions in identity equality."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def same(left: object, right: object, label: str) -> None:
    require(canonical(left) == canonical(right), label + " mismatch")


def digest(path: Path, check: Check = idle) -> str:
    check()
    value = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            check()
            value.update(chunk)
    check()
    return value.hexdigest()


def read_json(path: Path, check: Check = idle) -> dict[str, Any]:
    check()
    raw = path.read_bytes()
    check()
    result = parse(raw)
    check()
    return result


def load_inputs(check: Check = idle) -> dict[str, Any]:
    """Independently reconstruct the expected wire bundle from frozen JSON only."""
    records = {}
    for name, expected in INPUT_SHA.items():
        check()
        raw = (HERE / name).read_bytes()
        require(sha256(raw).hexdigest() == expected, "frozen input identity: " + name)
        records[name] = parse(raw)
        check()
    reference = records["0119-m2-reference.json"]
    physical = records["0098-central-correction-study.json"]["science"]
    selected = reference["runs"][0]["selected"]
    same(physical["scenario"], reference["normalized_scenario"], "complete scenario")
    same(physical["candidate"], selected, "complete candidate")
    initial = physical["runs"][0]["run"]["boundaries"][0]
    epoch = float(initial["epoch_tdb_s"])
    state = [float(v) for v in initial["position_m"] + initial["velocity_m_s"]]
    require(
        epoch == 978995455.2304223 and selected["departure_epoch_tdb_s"] == epoch,
        "initial epoch",
    )
    require(
        state
        == [
            -47124635282.7281,
            128473304107.83153,
            55670397503.89886,
            -29590.75977762049,
            -9186.174444867514,
            -2407.2479826554863,
        ],
        "initial six-state",
    )
    check()
    return {
        "scenario": physical["scenario"],
        "candidate": selected,
        "initial": initial,
        "state_si": state,
        "epoch_tdb_s": epoch,
        "final_epoch_tdb_s": epoch + 300,
        "nodes_tdb_s": [epoch + 50 * j for j in range(7)],
        "original_kernel_manifest": reference["provenance"]["manifest"]["spice"],
        "input_sha256": dict(INPUT_SHA),
        "origin": "SSB",
        "orientation": "J2000",
        "time_scale": "TDB seconds since J2000",
        "position_units": "m",
        "velocity_units": "m/s",
    }


def required_sources(checkout: Path = ROOT) -> set[str]:
    paths = {
        str(p.relative_to(checkout)) for p in (checkout / "src/space_nav").glob("*.py")
    }
    paths.update(
        {
            "src/space_nav/__init__.py",
            "environment.yml",
            "tests/test_r2_reference_coast.py",
            "tests/test_r5_short_coast_oracle.py",
            "tests/test_r5_short_coast_native.py",
            "tests/test_r5_short_coast_inputs.py",
            "tests/test_r5_short_coast_runner.py",
        }
    )
    paths.update("docs/adr/experiments/" + p for p in (*INPUT_SHA, *PREPARED_SHA))
    return paths


def hash_text(value: object) -> str:
    require(
        isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None,
        "SHA256 value required",
    )
    return value


def contained(raw: object, root: Path) -> Path:
    require(isinstance(raw, str), "file path must be a string")
    path = Path(raw).resolve()
    require(path.is_relative_to(root.resolve()), "identity path outside declared root")
    return path


def file_identity(record: dict[str, Any], prefix: Path, check: Check) -> Path:
    path = contained(record["path"], prefix)
    require(
        digest(path, check) == hash_text(record["sha256"]),
        "current file identity: " + str(path),
    )
    return path


def metadata_identity(
    record: dict[str, Any], expected_hash: object, prefix: Path, check: Check
) -> Path:
    name = record["name"]
    require(
        name in VERSIONS and record["version"] == VERSIONS[name], "Conda name/version"
    )
    path = prefix / "conda-meta" / f"{name}-{record['version']}-{record['build']}.json"
    path = contained(str(path), prefix / "conda-meta")
    require(digest(path, check) == hash_text(expected_hash), "Conda metadata identity")
    same(read_json(path, check), record, "Conda record")
    return path


def verify_snapshot(
    snapshot: dict[str, Any],
    original_kernels: dict[str, Any],
    check: Check = idle,
    *,
    checkout: Path = ROOT,
    prefix: Path = Path(sys.prefix),
) -> dict[str, Any]:
    """Check saved assertions and current bytes, without imports or kernel reads.

    checkout/prefix parameters are for isolated file fixtures only. They do not
    authorize a reference verdict; the future file auditor must use real defaults.
    """
    check()
    require(
        set(snapshot)
        == {
            "versions",
            "imports",
            "native_binary",
            "conda_build",
            "resource_build",
            "resource_metadata_sha256",
            "conda_metadata_sha256",
            "revision",
            "dirty",
            "source_sha256",
            "kernels",
            "r5_runtime",
        },
        "snapshot field inventory",
    )
    require(
        isinstance(snapshot["revision"], str)
        and re.fullmatch("[0-9a-f]{40}", snapshot["revision"]) is not None,
        "saved Git revision",
    )
    require(
        isinstance(snapshot["dirty"], list)
        and all(isinstance(v, str) for v in snapshot["dirty"]),
        "saved Git status",
    )
    require(
        set(snapshot["imports"]) == {"space_nav", "tudatpy"}, "saved import inventory"
    )
    same(snapshot["versions"], VERSIONS, "pinned versions")
    same(snapshot["kernels"], original_kernels, "original ordered kernels")
    require(
        type(original_kernels["loaded_kernel_count"]) is int
        and original_kernels["loaded_kernel_count"] == 13
        and original_kernels["kernel_list_status"] == "complete"
        and len(original_kernels["kernels"]) == 13,
        "complete kernel manifest",
    )
    for kernel in original_kernels["kernels"]:
        hash_text(kernel["sha256"])
    sources = snapshot["source_sha256"]
    require(set(sources) == required_sources(checkout), "source inventory")
    for relative, expected in sources.items():
        path = contained(str(checkout / relative), checkout)
        require(
            digest(path, check) == hash_text(expected),
            "source file identity: " + relative,
        )
        if relative.startswith("docs/adr/experiments/"):
            name = Path(relative).name
            require(
                expected == (INPUT_SHA | PREPARED_SHA)[name],
                "frozen/prepared source pin",
            )
    require(
        Path(snapshot["imports"]["space_nav"]).resolve()
        == (checkout / "src/space_nav/__init__.py").resolve(),
        "checkout import path",
    )
    expected_tudat = prefix / "lib/python3.12/site-packages/tudatpy/__init__.py"
    require(
        contained(snapshot["imports"]["tudatpy"], prefix) == expected_tudat.resolve(),
        "Tudat import path",
    )
    require(expected_tudat.is_file(), "Tudat import file unavailable")
    file_identity(snapshot["native_binary"], prefix, check)
    for record_name, hash_name in (
        ("conda_build", "conda_metadata_sha256"),
        ("resource_build", "resource_metadata_sha256"),
    ):
        expected_name = "tudatpy" if record_name == "conda_build" else "tudat-resources"
        require(snapshot[record_name]["name"] == expected_name, "Conda package role")
        metadata_identity(snapshot[record_name], snapshot[hash_name], prefix, check)
    runtime = snapshot["r5_runtime"]
    require(set(runtime["modules"]) == set(MODULES), "runtime module inventory")
    for record in runtime["modules"].values():
        file_identity(record, prefix, check)
    require(
        set(runtime["builds"]) == {"numpy", "scipy", "spiceypy"},
        "runtime build inventory",
    )
    for name, value in runtime["builds"].items():
        require(value["record"]["name"] == name, "runtime build name")
        path = metadata_identity(
            value["record"], value["metadata_sha256"], prefix, check
        )
        require(
            contained(value["metadata_path"], prefix) == path, "metadata path binding"
        )
    require(set(runtime["coefficients"]) == set(SHAPES), "coefficient inventory")
    for name, shape in SHAPES.items():
        record = runtime["coefficients"][name]
        same(record["shape"], shape, "coefficient shape")
        require(record["dtype"] == "float64", "coefficient dtype")
        hash_text(record["sha256"])
    require(set(runtime["callables"]) == set(CALLABLES), "callable inventory")
    for name, (module, qualified) in CALLABLES.items():
        record = runtime["callables"][name]
        require(
            record["module"] == module and record["qualname"] == qualified,
            "callable role",
        )
        path = file_identity(
            {"path": record["source_path"], "sha256": record["source_sha256"]},
            prefix,
            check,
        )
        require(
            path == Path(runtime["modules"][module]["path"]).resolve(),
            "callable module path",
        )
        hash_text(record["code_sha256"])
    check()
    return {
        "current_source_files_checked": len(sources),
        "current_native_binary_checked": True,
        "current_module_files_checked": len(MODULES),
        "current_conda_records_checked": 5,
        "kernel_scope": "saved ordered manifest equal to R1; no current kernel-byte/pool read",
        "coefficient_callable_scope": "saved shapes/roles/digest syntax only; compare snapshots separately",
        "historical_loaded_memory_verified": False,
        "reference_study_verified": False,
    }
