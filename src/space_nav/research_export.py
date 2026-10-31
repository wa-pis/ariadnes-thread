"""Traceable research result and a deliberately narrow, verified OEM exchange."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
from typing import Any

from . import _oem_audit as audit
from .ephemeris import CartesianState
from .errors import TransferSearchError
from .models import ImpulsiveTransferCandidate, Scenario, TransferSearchResult

SCHEMA = "ariadna-result-v1"
MODEL = "sun-centered-zero-revolution-patched-conic-v1"
READER_SHA256 = "a531dec0b774f29a78b02a2b65c7418bd27919bacbcf8f2893372c9b80541247"
ROOT = Path(__file__).resolve().parents[2]


class ResultExportError(TransferSearchError):
    """An invalid research result or failed exchange check; no files may publish."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ResultExportError(message)


def canonical_json(value: Any) -> bytes:
    """Encode finite normalized scientific data with stable UTF-8 key ordering."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ResultExportError(f"JSON: {exc}") from exc


def source_identity() -> dict[str, Any]:
    """Capture the actual checkout and source bytes, never a fabricated revision."""
    try:
        paths = sorted((ROOT / "src/space_nav").rglob("*.py")) + [
            ROOT / "environment.yml"
        ]
        return {
            "base_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).strip(),
            "dirty_status": subprocess.check_output(
                ["git", "status", "--short"],
                cwd=ROOT,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).splitlines(),
            "file_sha256": {
                str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest()
                for p in paths
            },
        }
    except (OSError, subprocess.SubprocessError) as exc:
        raise ResultExportError(f"Source provenance unavailable: {exc}") from exc


def format_tdb(epoch_tdb_s: float) -> str:
    """Gregorian TDB, microseconds half-even; no UTC or Unix conversion."""
    _require(
        type(epoch_tdb_s) in (float, int) and math.isfinite(epoch_tdb_s),
        "finite numeric TDB epoch",
    )
    try:
        with localcontext() as context:
            context.prec = 400
            micros = int(
                (Decimal(epoch_tdb_s) * 1000000).to_integral_value(
                    rounding=ROUND_HALF_EVEN
                )
            )
        value = datetime(2000, 1, 1, 12) + timedelta(microseconds=micros)
    except (OverflowError, ValueError) as exc:
        raise ResultExportError("TDB calendar overflow") from exc
    _require(1900 <= value.year <= 2100, "TDB calendar year outside 1900–2100")
    return value.isoformat(timespec="microseconds")


def _component(value_si: float) -> str:
    _require(
        type(value_si) in (float, int) and math.isfinite(value_si),
        "finite SI component",
    )
    with localcontext() as context:
        context.prec = 400
        context.rounding = ROUND_HALF_EVEN
        value = Decimal(value_si) / 1000
        if value == 0:
            return "0.000000000000000E+00"
        mantissa, exponent = format(value, ".15E").split("E")
        return f"{mantissa}E{int(exponent):+03d}"


def _oem_bytes(
    states: tuple[CartesianState, ...],
    result_id: str,
    qualification: str,
    creation_utc: str,
) -> bytes:
    labels = [format_tdb(s.epoch_tdb_s) for s in states]
    _require(
        all(b > a for a, b in zip(labels, labels[1:])),
        "duplicate or unordered formatted epochs",
    )
    lines = [
        "CCSDS_OEM_VERS = 3.0",
        "COMMENT PROFILE ariadna-oem-kvn-v1",
        "COMMENT RESEARCH_ONLY NOT_FOR_OPERATIONAL_NAVIGATION",
        "COMMENT ORIGINATOR_UNREGISTERED NO_FULL_CCSDS_CONFORMANCE",
        f"COMMENT QUALIFICATION {qualification}",
        f"COMMENT RESULT_ID {result_id}",
        f"CREATION_DATE = {creation_utc}",
        "ORIGINATOR = ARIADNA",
        f"MESSAGE_ID = {result_id}",
        "META_START",
        "OBJECT_NAME = UNKNOWN",
        "OBJECT_ID = UNKNOWN",
        "CENTER_NAME = SOLAR SYSTEM BARYCENTER",
        "REF_FRAME = ICRF",
        "TIME_SYSTEM = TDB",
        f"START_TIME = {labels[0]}",
        f"STOP_TIME = {labels[-1]}",
        "META_STOP",
    ]
    lines.extend(
        label + " " + " ".join(_component(v) for v in (*s.position_m, *s.velocity_m_s))
        for label, s in zip(labels, states)
    )
    try:
        return ("\n".join(lines) + "\n").encode("ascii")
    except UnicodeError as exc:
        raise ResultExportError("OEM ASCII encoding") from exc


@dataclass(frozen=True, slots=True)
class ExportBundle:
    """Verified, immutable paired files; science identity excludes export time."""

    result_id: str
    json_bytes: bytes
    oem_bytes: bytes

    def __post_init__(self) -> None:
        _require(
            type(self.result_id) is str
            and len(self.result_id) == 64
            and all(c in "0123456789abcdef" for c in self.result_id),
            "result ID",
        )
        _require(
            type(self.json_bytes) is bytes
            and bool(self.json_bytes)
            and type(self.oem_bytes) is bytes
            and bool(self.oem_bytes),
            "paired file bytes",
        )


def _admit(provenance: dict[str, Any]) -> None:
    """Admit only the ordered hash-pinned reference manifest, with no resource query."""
    reference = {
        "origin": "SSB",
        "orientation": "J2000",
        "time": "TDB seconds since J2000",
        "position_units": "m",
        "velocity_units": "m/s",
    }
    _require(provenance["reference"] == reference, "unsupported reference/time/units")
    _require(provenance["transfer_model"]["identifier"] == MODEL, "unsupported model")
    _require(
        provenance["spice"]["kernel_list_status"] == "complete",
        "incomplete kernel inventory",
    )
    actual = [(k["name"], k["sha256"]) for k in provenance["spice"]["kernels"]]
    _require(
        actual == ADMITTED_KERNELS
        and provenance["spice"]["loaded_kernel_count"] == len(actual),
        "unsupported ordered resource hashes; ICRF admission unavailable",
    )
    source = provenance["source"]
    _require(
        isinstance(source["base_revision"], str)
        and bool(source["base_revision"])
        and isinstance(source["dirty_status"], list)
        and bool(source["file_sha256"]),
        "source provenance unavailable",
    )
    _require(
        all(
            provenance["versions"].get(name) not in (None, "unknown", "")
            for name in ("python", "tudatpy", "space_nav")
        ),
        "runtime versions unavailable",
    )
    _require(
        sha256(Path(audit.__file__).read_bytes()).hexdigest() == READER_SHA256,
        "independent reader identity changed",
    )


def build_export(
    scenario: Scenario,
    candidate: ImpulsiveTransferCandidate,
    search: TransferSearchResult,
    states: tuple[CartesianState, ...],
    provenance: dict[str, Any],
    *,
    creation_utc: str,
    selection_policy: str,
    endpoints: tuple[CartesianState, CartesianState],
    search_elapsed_s: float,
) -> ExportBundle:
    """Build and independently verify SI/SSB/J2000 research JSON and OEM bytes.

    Consumes completed calculation snapshots only; never propagates or queries SPICE.
    The fixed 50 kg reserve qualifies only this ideal coast, never a full mission.
    """
    try:
        _require(
            type(search_elapsed_s) in (float, int)
            and math.isfinite(search_elapsed_s)
            and search_elapsed_s >= 0,
            "finite nonnegative search elapsed seconds",
        )
        _admit(provenance)
        _require(
            canonical_json(provenance["scenario"])
            == canonical_json(scenario.to_dict()),
            "scenario/provenance mismatch",
        )
        _require(
            provenance["random_seed"] == scenario.limits.random_seed, "seed mismatch"
        )
        _require(
            candidate in search.pareto_front, "selected candidate is not in this search"
        )
        _require(
            type(selection_policy) is str and bool(selection_policy),
            "selection policy missing",
        )
        _require(
            type(states) is tuple and 2 <= len(states) <= 1001,
            "sample count outside 2–1001",
        )
        expected_points: list[audit.Point] = []
        for index, state in enumerate(states):
            _require(
                isinstance(state, CartesianState)
                and state.body == "Spacecraft"
                and state.origin == "SSB"
                and state.orientation == "J2000",
                "noncanonical state",
            )
            _require(
                state.epoch_tdb_s
                == candidate.departure_epoch_tdb_s
                + candidate.flight_time_s * index / (len(states) - 1),
                "sampler epoch mismatch",
            )
            expected_points.append(
                audit.Point(
                    Decimal(state.epoch_tdb_s),
                    tuple(Decimal(v) for v in (*state.position_m, *state.velocity_m_s)),
                )
            )
        _require(
            all(b.epoch_tdb_s > a.epoch_tdb_s for a, b in zip(states, states[1:])),
            "sample order",
        )
        endpoint_errors: list[dict[str, float]] = []
        _require(
            type(endpoints) is tuple and len(endpoints) == 2, "endpoint checks missing"
        )
        for state, body, name, excess in zip(
            (states[0], states[-1]),
            endpoints,
            ("Moon", "Mars"),
            (candidate.departure_v_infinity_m_s, candidate.arrival_v_infinity_m_s),
        ):
            _require(
                isinstance(body, CartesianState)
                and body.body == name
                and body.epoch_tdb_s == state.epoch_tdb_s
                and body.origin == "SSB"
                and body.orientation == "J2000",
                "endpoint identity",
            )
            position = math.dist(state.position_m, body.position_m)
            velocity = math.dist(
                state.velocity_m_s,
                tuple(body.velocity_m_s[i] + excess[i] for i in range(3)),
            )
            _require(
                position <= 100 and velocity <= 0.001, "endpoint numeric check failed"
            )
            endpoint_errors.append(
                {"position_error_m": position, "velocity_error_m_s": velocity}
            )
        grid = provenance["transfer_model"]["grid"]
        _require(
            search.evaluated_candidates == grid["attempted_candidates"],
            "search completion mismatch",
        )
        with localcontext() as context:
            context.prec = 80
            mass = Decimal(scenario.spacecraft.initial_mass_kg)
            for delta_v in (
                candidate.departure_delta_v_m_s,
                candidate.arrival_delta_v_m_s,
            ):
                mass *= (
                    -Decimal(delta_v)
                    / (Decimal("9.80665") * Decimal(scenario.spacecraft.isp_s))
                ).exp()
            mass_error = abs(mass - Decimal(candidate.final_mass_kg))
            propellant_error = abs(
                Decimal(scenario.spacecraft.initial_mass_kg)
                - mass
                - Decimal(candidate.propellant_mass_kg)
            )
        _require(
            mass_error <= Decimal("1e-9") and propellant_error <= Decimal("1e-9"),
            "mass accounting mismatch",
        )
        _require(
            candidate.mass_feasible
            == (candidate.final_mass_kg >= scenario.spacecraft.dry_mass_kg),
            "mass-feasible flag mismatch",
        )
        reserve_passed = (
            candidate.final_mass_kg >= scenario.spacecraft.dry_mass_kg + 50.0
        )
        qualification = "ideal-model-feasible" if reserve_passed else "unqualified"
        scientific = {
            "schema_version": SCHEMA,
            "scenario": scenario.to_dict(),
            "input_id": sha256(canonical_json(scenario.to_dict())).hexdigest(),
            "candidate": asdict(candidate),
            "model": provenance["transfer_model"],
            "provenance": provenance,
            "search": asdict(search),
            "selection_policy": selection_policy,
            "sampling": {
                "count": len(states),
                "method": "existing-evenly-spaced-M2-coast",
                "endpoints": "coast, not parking-orbit states",
                "endpoint_checks": endpoint_errors,
                "endpoint_body_states": [asdict(body) for body in endpoints],
            },
            "states": [asdict(s) for s in states],
            "reference": provenance["reference"],
            "status": {
                "calculation": "passed",
                "reserve": "passed" if reserve_passed else "failed",
                "qualification": qualification,
            },
            "reserve": {
                "required_kg": 50.0,
                "dry_mass_kg": scenario.spacecraft.dry_mass_kg,
                "margin_kg": candidate.final_mass_kg
                - scenario.spacecraft.dry_mass_kg
                - 50.0,
                "independent_final_mass_decimal_kg": str(mass),
                "mass_error_kg": str(mass_error),
                "propellant_error_kg": str(propellant_error),
            },
            "not_modelled": {
                "status": "not-modelled",
                "covariance": None,
                "tracking": None,
                "safety": None,
            },
            "limitations": [
                "research only; not operational navigation",
                "Sun point-mass coast",
                "body-centre endpoints; scalar instantaneous maneuvers",
                "no finite burn, lunar escape, Mars capture, tracking or safety validation",
                "wire accuracy at nodes only; no interpolation guarantee",
            ],
        }
        result_id = sha256(canonical_json(scientific)).hexdigest()
        oem = _oem_bytes(states, result_id, qualification, creation_utc)
        residuals = audit.verify(
            oem,
            tuple(expected_points),
            result_id=result_id,
            qualification=qualification,
        )
        payload = {
            "result_id": result_id,
            "scientific": scientific,
            "execution": {
                "exporter_source_sha256": sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
                "search_elapsed_s": search_elapsed_s,
                "search_completion": "completed",
                "runtime_limit_s": scenario.limits.runtime_seconds,
            },
            "exchange": {
                "status": "passed",
                "profile": audit.PROFILE_ID,
                "oem_version": "3.0",
                "creation_utc": creation_utc,
                "oem_sha256": sha256(oem).hexdigest(),
                "reader": {"id": audit.READER_ID, "sha256": READER_SHA256},
                "maximum_residuals": {k: str(v) for k, v in residuals.items()},
                "originator_registration": "unregistered; no full CCSDS conformance",
            },
        }
        return ExportBundle(result_id, canonical_json(payload) + b"\n", oem)
    except ResultExportError:
        raise
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        OSError,
        OverflowError,
    ) as exc:
        raise ResultExportError(
            f"Research export validation/decoding failed: {exc}"
        ) from exc


# ADR0124 admits only the complete ordered ADR0119 resource identity.
ADMITTED_KERNELS: list[tuple[str, str]] = [
    (
        "pck00010.tpc",
        "59468328349aa730d18bf1f8d7e86efe6e40b75dfb921908f99321b3a7a701d2",
    ),
    (
        "inpop19a_TDB_m100_p100_spice.tpc",
        "55798de268f64f43f5ccf71dae84e1d1603a99301f80251c4d74cb8f26a72eee",
    ),
    (
        "NOE-4-2020.tpc",
        "0edbcf5f8a1265f2937594f55d7fe395526d610e14445c3d77448e0df1adcf21",
    ),
    (
        "NOE-5-2021.tpc",
        "069cb44cef6809e84a618bbb3b8efde2fe42224ff0636b59808034a9c806cec6",
    ),
    (
        "NOE-6-2018-MAIN-v2.tpc",
        "2f3084319850f92b2fc6adaaf7846b1362c7775b56c550c9b10615fc7fedc3cc",
    ),
    (
        "codes_300ast_20100725.bsp",
        "7bb92faaadac29ec0b62aa96041a37c92ae24b9a5460de03d3fcaa2f63fe51f0",
    ),
    (
        "codes_300ast_20100725.tf",
        "15ee3b1731817774672725ccc226b249eb9ca5aa5d0a6a7805c91e5f57497f40",
    ),
    (
        "inpop19a_TDB_m100_p100_spice.bsp",
        "01f095b148ef1e5aad6f95213c188ca5b0d8a58901d19a95b0c11082b1d3a0c6",
    ),
    (
        "NOE-4-2020.bsp",
        "bd05fc94f3f2c873b26bfc420759bc82df306593c1ed4173716b8472b115ab9b",
    ),
    (
        "NOE-5-2021.bsp",
        "85063d326f068f4a6e5bd4f56c4c4bae330c0cea210d18d190451f33cb3add24",
    ),
    (
        "NOE-6-2018-MAIN-v2.bsp",
        "ff2188d11c8cd31933e6757e81cd43e66644e218d041c72628ebf291754e7f39",
    ),
    (
        "juice_mat_crema_4_0_20220601_20330626_v01.bsp",
        "79ea4e0483909305dcf40280e16b859f0c7050420517cb35a60b1b166d8edd76",
    ),
    (
        "naif0012.tls",
        "678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b",
    ),
]
