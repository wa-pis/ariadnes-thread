"""Command-line diagnostics for mission scenarios and SPICE states."""

from __future__ import annotations

import argparse
from hashlib import sha256
from importlib import import_module
from importlib import metadata
import json
from pathlib import Path
import platform
import sys
from typing import Any, Sequence

from . import __version__
from .ephemeris import CartesianState, kernel_metadata, query_body_state
from .errors import EphemerisError, ScenarioValidationError, TransferSearchError
from .models import ImpulsiveTransferCandidate, Scenario, TransferSearchResult
from .scenario import load_scenario
from .transfer import _transfer_model_manifest, search_impulsive_transfers


class _UsageError(Exception):
    pass


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _UsageError(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="space-nav", description="Space navigation diagnostics")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate a mission scenario")
    validate.add_argument("scenario", help="path to a TOML mission scenario")
    validate.add_argument("--json", action="store_true", help="emit JSON")

    ephemeris = subparsers.add_parser("ephemeris", help="inspect a SPICE body state")
    ephemeris.add_argument("scenario", help="path to a TOML mission scenario")
    ephemeris.add_argument("--body", required=True, help="SPICE body name")
    ephemeris.add_argument("--epoch", required=True, help="ISO-8601 UTC epoch ending in Z")
    ephemeris.add_argument("--json", action="store_true", help="emit JSON")

    plan = subparsers.add_parser("plan", help="plan impulsive Moon-to-Mars transfers")
    plan.add_argument("scenario", help="path to a TOML mission scenario")
    plan.add_argument("--json", action="store_true", help="emit JSON")
    return parser


def _json_dump(value: dict[str, Any], stream: Any) -> None:
    print(json.dumps(value, allow_nan=False, sort_keys=True), file=stream)


def _error_payload(exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "type": "ArgumentError" if isinstance(exc, _UsageError) else type(exc).__name__,
            "message": str(exc),
            "field": getattr(exc, "field", None),
        },
    }


def _render_error(exc: Exception, json_mode: bool) -> None:
    if json_mode:
        _json_dump(_error_payload(exc), sys.stderr)
    else:
        print(f"Error: {exc}", file=sys.stderr)


def _distribution_version(distribution: str, fallback: str = "unknown") -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return fallback


def _tudatpy_version() -> str:
    """Read TudatPy's module version without importing it during CLI startup."""

    try:
        return str(import_module("tudatpy").__version__)
    except (ImportError, AttributeError):
        return "unknown"


def _manifest(scenario_path: Path, random_seed: int) -> dict[str, Any]:
    return {
        "scenario_sha256": sha256(scenario_path.read_bytes()).hexdigest(),
        "versions": {
            "python": platform.python_version(),
            "space_nav": _distribution_version("space-nav", __version__),
            "tudatpy": _tudatpy_version(),
        },
        "reference": {
            "origin": "SSB",
            "orientation": "J2000",
            "time": "TDB seconds since J2000",
            "position_units": "m",
            "velocity_units": "m/s",
        },
        "random_seed": random_seed,
        "spice": kernel_metadata(),
    }


def _state_payload(
    state: CartesianState, scenario_path: Path, random_seed: int
) -> dict[str, Any]:
    return {
        "ok": True,
        "body": state.body,
        "epoch_utc": state.epoch_utc,
        "epoch_tdb_s": state.epoch_tdb_s,
        "origin": state.origin,
        "orientation": state.orientation,
        "position_m": list(state.position_m),
        "velocity_m_s": list(state.velocity_m_s),
        "manifest": _manifest(scenario_path, random_seed),
    }


def _run_validate(scenario_text: str, json_mode: bool) -> None:
    scenario_path = Path(scenario_text).expanduser().resolve()
    load_scenario(scenario_path)
    if json_mode:
        _json_dump({"ok": True, "scenario": str(scenario_path)}, sys.stdout)
    else:
        print(f"Scenario valid: {scenario_path}")


def _run_ephemeris(
    scenario_text: str, body: str, epoch: str, json_mode: bool
) -> None:
    scenario_path = Path(scenario_text).expanduser().resolve()
    scenario = load_scenario(scenario_path)
    state = query_body_state(body, epoch)
    payload = _state_payload(state, scenario_path, scenario.limits.random_seed)
    if json_mode:
        _json_dump(payload, sys.stdout)
        return
    print(f"Body: {state.body}")
    print(f"Epoch UTC: {state.epoch_utc}")
    print(f"Epoch TDB [s since J2000]: {state.epoch_tdb_s:.9f}")
    print("Frame: origin SSB, orientation J2000")
    print("Position [m]: " + ", ".join(f"{value:.9g}" for value in state.position_m))
    print(
        "Velocity [m/s]: "
        + ", ".join(f"{value:.9g}" for value in state.velocity_m_s)
    )
    print(
        "SPICE kernels: "
        f"{payload['manifest']['spice']['loaded_kernel_count']} "
        "from tudatpy-standard"
    )


def _candidate_payload(candidate: ImpulsiveTransferCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "departure_epoch_utc": candidate.departure_epoch_utc,
        "arrival_epoch_utc": candidate.arrival_epoch_utc,
        "departure_epoch_tdb_s": candidate.departure_epoch_tdb_s,
        "arrival_epoch_tdb_s": candidate.arrival_epoch_tdb_s,
        "flight_time_s": candidate.flight_time_s,
        "departure_v_infinity_m_s": list(candidate.departure_v_infinity_m_s),
        "arrival_v_infinity_m_s": list(candidate.arrival_v_infinity_m_s),
        "departure_delta_v_m_s": candidate.departure_delta_v_m_s,
        "arrival_delta_v_m_s": candidate.arrival_delta_v_m_s,
        "total_delta_v_m_s": candidate.total_delta_v_m_s,
        "propellant_mass_kg": candidate.propellant_mass_kg,
        "final_mass_kg": candidate.final_mass_kg,
        "mass_feasible": candidate.mass_feasible,
    }


def _plan_payload(
    result: TransferSearchResult, scenario: Scenario, scenario_path: Path
) -> dict[str, Any]:
    manifest = _manifest(scenario_path, scenario.limits.random_seed)
    manifest["transfer_model"] = _transfer_model_manifest(scenario)
    return {
        "ok": True,
        "scenario": str(scenario_path),
        "ephemeris_origin": result.ephemeris_origin,
        "transfer_central_body": result.transfer_central_body,
        "orientation": result.orientation,
        "time_scale": result.time_scale,
        "evaluated_candidates": result.evaluated_candidates,
        "solved_candidates": result.solved_candidates,
        "failed_candidates": result.failed_candidates,
        "mass_feasible_candidates": result.mass_feasible_candidates,
        "pareto_front": [_candidate_payload(item) for item in result.pareto_front],
        "manifest": manifest,
    }


def _format_vector(values: Sequence[float]) -> str:
    return ", ".join(f"{value:.9g}" for value in values)


def _render_plan_human(payload: dict[str, Any]) -> None:
    print(f"Scenario: {payload['scenario']}")
    print(
        f"Reference: {payload['ephemeris_origin']}/{payload['orientation']} "
        f"(ephemeris origin {payload['ephemeris_origin']}, "
        f"orientation {payload['orientation']})"
    )
    print(f"Transfer central body: {payload['transfer_central_body']} (Sun-centered)")
    print(f"Time scale: {payload['time_scale']}")
    print(f"Evaluated candidates: {payload['evaluated_candidates']}")
    print(f"Solved candidates: {payload['solved_candidates']}")
    print(f"Failed candidates: {payload['failed_candidates']}")
    print(f"Mass-feasible candidates: {payload['mass_feasible_candidates']}")
    if payload["mass_feasible_candidates"] == 0:
        print("Spacecraft feasibility: infeasible; no candidate respects dry mass")

    for candidate in payload["pareto_front"]:
        print(f"Pareto candidate: {candidate['candidate_id']}")
        print(f"  Departure UTC: {candidate['departure_epoch_utc']}")
        print(f"  Arrival UTC: {candidate['arrival_epoch_utc']}")
        print(
            "  Departure TDB [s since J2000]: "
            f"{candidate['departure_epoch_tdb_s']:.9f}"
        )
        print(
            "  Arrival TDB [s since J2000]: "
            f"{candidate['arrival_epoch_tdb_s']:.9f}"
        )
        print(f"  Flight time [s]: {candidate['flight_time_s']:.9f}")
        print(
            "  Departure hyperbolic-excess velocity [J2000 m/s]: "
            + _format_vector(candidate["departure_v_infinity_m_s"])
        )
        print(
            "  Arrival hyperbolic-excess velocity [J2000 m/s]: "
            + _format_vector(candidate["arrival_v_infinity_m_s"])
        )
        print(f"  Departure delta-v [m/s]: {candidate['departure_delta_v_m_s']:.9f}")
        print(f"  Arrival delta-v [m/s]: {candidate['arrival_delta_v_m_s']:.9f}")
        print(f"  Total delta-v [m/s]: {candidate['total_delta_v_m_s']:.9f}")
        print(f"  Propellant mass [kg]: {candidate['propellant_mass_kg']:.9f}")
        print(f"  Final mass [kg]: {candidate['final_mass_kg']:.9f}")
        print(f"  Mass feasible: {str(candidate['mass_feasible']).lower()}")


def _run_plan(scenario_text: str, json_mode: bool) -> None:
    scenario_path = Path(scenario_text).expanduser().resolve()
    scenario = load_scenario(scenario_path)
    result = search_impulsive_transfers(scenario)
    payload = _plan_payload(result, scenario, scenario_path)
    if json_mode:
        _json_dump(payload, sys.stdout)
    else:
        _render_plan_human(payload)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in arguments
    try:
        try:
            args = _build_parser().parse_args(arguments)
        except SystemExit as exc:
            if exc.code == 0:
                return 0
            raise
        if args.command == "validate":
            _run_validate(args.scenario, args.json)
        elif args.command == "ephemeris":
            _run_ephemeris(args.scenario, args.body, args.epoch, args.json)
        else:
            _run_plan(args.scenario, args.json)
    except (
        _UsageError,
        ScenarioValidationError,
        EphemerisError,
        TransferSearchError,
    ) as exc:
        _render_error(exc, json_mode)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
