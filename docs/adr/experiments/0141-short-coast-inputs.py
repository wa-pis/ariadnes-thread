"""Private R5 frozen-input/extended-runtime identity; no propagation or execution CLI."""

from __future__ import annotations

from hashlib import sha256
from importlib import import_module, util
import json
import marshal
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
INPUT_SHA = {
    "0119-m2-reference.json": "3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0",
    "0098-central-correction-study.json": "b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057",
    "0133-gravity-screen.json": "74238edd641e1b5fda42a209672c68e5bc201b20d3cffba24169e6f9b3b6a580",
    "0136-retained-boundary-audit.json": "81d78ecf6e4e80b55e9d909f929a879b2e392667387ec2569632aa99a6b41063",
}
PREPARED_SHA = {
    "0128-reference-coast.py": "027d0b4e45f9ebd941249e427963e365fd7205f9594a96365a587eb0e8cd7e81",
    "0138-short-coast-oracle.py": "d6a624f727e17de364f188f0941f2e1889741204ad035aefd9263728cf95e029",
    "0140-short-coast-native.py": "8bc888d6e1c638251d8379d6d4c896393b5cd76fb71e85c65c7faf9aab9294e2",
}


def load_common() -> ModuleType:
    path = HERE / "0128-reference-coast.py"
    if sha256(path.read_bytes()).hexdigest() != PREPARED_SHA[path.name]:
        raise ImportError("immutable R2 utilities changed")
    spec = util.spec_from_file_location("r5_immutable_r2_input_utilities", path)
    if spec is None or spec.loader is None:
        raise ImportError("R2 utilities unavailable")
    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


common = load_common()
Check = Callable[[], None]


def idle() -> None:
    pass


def check_prepared_sources(check: Check = idle) -> dict[str, str]:
    for name, digest in PREPARED_SHA.items():
        check()
        common.require(
            common.digest(HERE / name) == digest, f"prepared source identity: {name}"
        )
    check()
    return dict(PREPARED_SHA)


def validate_inputs(records: dict[str, Any]) -> dict[str, Any]:
    """Validate already-hash-bound records; no reconstruction of the initial state."""
    common.require(set(records) == set(INPUT_SHA), "R5 input records mismatch")
    reference = records["0119-m2-reference.json"]
    original = common.validate_reference(reference)
    physical = records["0098-central-correction-study.json"]["science"]
    screen = records["0133-gravity-screen.json"]
    audit = records["0136-retained-boundary-audit.json"]
    common.require(
        physical["scenario"] == reference["normalized_scenario"],
        "complete scenario mismatch",
    )
    common.require(
        physical["candidate"] == original["selected"], "complete candidate mismatch"
    )
    common.require(
        screen["status"] == audit["status"] == "passed", "prerequisite status mismatch"
    )
    common.require(
        screen["finalization_gate"] == audit["finalization_gate"] == "passed",
        "prerequisite finalization mismatch",
    )
    common.require(
        audit["input_sha256"]
        == {
            k: INPUT_SHA[k]
            for k in ("0119-m2-reference.json", "0098-central-correction-study.json")
        },
        "boundary audit input identity",
    )
    boundary = physical["runs"][0]["run"]["boundaries"][0]
    common.require(
        (boundary["label"], boundary["origin"], boundary["orientation"])
        == ("departure-ignition", "SSB", "J2000"),
        "initial event/frame mismatch",
    )
    epoch = common.number(boundary["epoch_tdb_s"])
    initial = common.vector(boundary["position_m"], 3) + common.vector(
        boundary["velocity_m_s"], 3
    )
    common.require(
        epoch == 978995455.2304223
        and epoch == original["selected"]["departure_epoch_tdb_s"],
        "initial epoch mismatch",
    )
    common.require(
        boundary["epoch_utc"] == "2031-01-09T11:09:46.046266Z",
        "initial UTC label mismatch",
    )
    common.require(
        initial
        == (
            -47124635282.7281,
            128473304107.83153,
            55670397503.89886,
            -29590.75977762049,
            -9186.174444867514,
            -2407.2479826554863,
        ),
        "initial six-state mismatch",
    )
    return {
        "scenario": physical["scenario"],
        "candidate": physical["candidate"],
        "initial": boundary,
        "state_si": initial,
        "epoch_tdb_s": epoch,
        "final_epoch_tdb_s": epoch + 300.0,
        "nodes_tdb_s": tuple(epoch + 50 * j for j in range(7)),
        "original_kernel_manifest": reference["provenance"]["manifest"]["spice"],
        "input_sha256": dict(INPUT_SHA),
        "origin": "SSB",
        "orientation": "J2000",
        "time_scale": "TDB seconds since J2000",
        "position_units": "m",
        "velocity_units": "m/s",
    }


def load_inputs(check: Check = idle) -> dict[str, Any]:
    """Read exact immutable inputs before any native import/query/propagation."""
    check_prepared_sources(check)
    records = {}
    for name, digest in INPUT_SHA.items():
        check()
        raw = (HERE / name).read_bytes()
        common.require(
            sha256(raw).hexdigest() == digest, f"frozen R5 input identity: {name}"
        )
        records[name] = json.loads(raw)
        check()
    result = validate_inputs(records)
    check()
    return result


def module_identity(name: str, version: str | None = None) -> dict[str, Any]:
    """Record actual imported file under the active Conda prefix, not metadata alone."""
    module = import_module(name)
    path = Path(module.__file__).resolve()
    common.require(
        path.is_relative_to(Path(sys.prefix).resolve()),
        f"runtime import outside prefix: {name}",
    )
    if version is not None:
        common.require(
            module.__version__ == version, f"actual runtime version mismatch: {name}"
        )
    return {"path": str(path), "sha256": common.digest(path)}


def callable_identity(function: Any) -> dict[str, str]:
    code = function.__code__
    path = Path(code.co_filename).resolve()
    common.require(
        path.is_relative_to(Path(sys.prefix).resolve()), "solver code outside prefix"
    )
    return {
        "module": function.__module__,
        "qualname": function.__qualname__,
        "source_path": str(path),
        "source_sha256": common.digest(path),
        "code_sha256": sha256(marshal.dumps(code)).hexdigest(),
    }


def runtime_identity(
    check: Check = idle, extra_sources: tuple[Path, ...] = ()
) -> dict[str, Any]:
    """Extend immutable R2 identity; no body states or trajectories are requested.

    This is a reproducibility snapshot, not a proof that every transitive native
    library or initially loaded Python object matches a trusted distribution.
    """
    check_prepared_sources(check)
    check()
    identity = common.runtime_identity()
    check()
    modules = {
        name: module_identity(name, identity["versions"].get(name))
        for name in (
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
    }
    integrate = import_module("scipy.integrate")
    ivp = import_module("scipy.integrate._ivp.ivp")
    rk = import_module("scipy.integrate._ivp.rk")
    coefficient = import_module("scipy.integrate._ivp.dop853_coefficients")
    np = import_module("numpy")
    common.require(integrate.solve_ivp is ivp.solve_ivp, "solve_ivp alias mismatch")
    common.require(ivp.METHODS["DOP853"] is rk.DOP853, "DOP853 registry mismatch")
    common.require(
        rk.DOP853.__module__ == rk.__name__, "DOP853 defining module mismatch"
    )
    arrays = {}
    shapes = {
        "A": (16, 16),
        "B": (12,),
        "C": (16,),
        "D": (4, 16),
        "E3": (13,),
        "E5": (13,),
    }
    for name in ("A", "B", "C", "D", "E3", "E5"):
        check()
        array = getattr(coefficient, name)
        common.require(
            isinstance(array, np.ndarray)
            and array.shape == shapes[name]
            and array.dtype == np.dtype("float64")
            and bool(np.isfinite(array).all()),
            f"DOP853 coefficient shape/type/domain: {name}",
        )
        arrays[name] = {
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "sha256": sha256(array.tobytes(order="C")).hexdigest(),
        }
    common.require(
        np.array_equal(
            rk.DOP853.A, coefficient.A[: rk.DOP853.n_stages, : rk.DOP853.n_stages]
        )
        and all(
            np.array_equal(getattr(rk.DOP853, name), getattr(coefficient, name))
            for name in ("B", "D", "E3", "E5")
        )
        and np.array_equal(rk.DOP853.C, coefficient.C[: rk.DOP853.n_stages])
        and np.array_equal(rk.DOP853.A_EXTRA, coefficient.A[rk.DOP853.n_stages + 1 :])
        and np.array_equal(rk.DOP853.C_EXTRA, coefficient.C[rk.DOP853.n_stages + 1 :])
        and rk.DOP853.n_stages == coefficient.N_STAGES == 12
        and rk.DOP853.order == 8
        and rk.DOP853.error_estimator_order == 7
        and coefficient.N_STAGES_EXTENDED == 16
        and coefficient.INTERPOLATOR_POWER == 7,
        "DOP853 class coefficients differ",
    )
    builds = {}
    for name in ("numpy", "scipy", "spiceypy"):
        check()
        path, record = common.conda_metadata(name)
        common.require(
            record["version"] == identity["versions"][name],
            f"Conda/runtime mismatch: {name}",
        )
        builds[name] = {
            "metadata_path": str(path),
            "metadata_sha256": common.digest(path),
            "record": record,
        }
    paths = [
        Path(__file__),
        HERE / "0138-short-coast-oracle.py",
        HERE / "0140-short-coast-native.py",
        ROOT / "tests/test_r5_short_coast_oracle.py",
        ROOT / "tests/test_r5_short_coast_native.py",
        ROOT / "tests/test_r5_short_coast_inputs.py",
        *(HERE / name for name in INPUT_SHA),
        *extra_sources,
    ]
    for path in paths:
        check()
        path = path.resolve()
        common.require(path.is_relative_to(ROOT), "extra source outside checkout")
        identity["source_sha256"][str(path.relative_to(ROOT))] = common.digest(path)
    identity["r5_runtime"] = {
        "modules": modules,
        "builds": builds,
        "coefficients": arrays,
        "callables": {
            name: callable_identity(function)
            for name, function in (
                ("solve_ivp", ivp.solve_ivp),
                ("rk_step", rk.rk_step),
                ("DOP853_step", rk.DOP853._step_impl),
                ("DOP853_error", rk.DOP853._estimate_error_norm),
                ("DOP853_dense", rk.DOP853._dense_output_impl),
            )
        },
    }
    check()
    return identity
