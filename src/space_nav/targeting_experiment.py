"""Private bounded D7–D11 orchestration; no production targeting or safety claim."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from . import research_correction as correction
from . import research_columns as columns
from . import research_response as response
from . import trajectory as physical
from .cli import _runtime_manifest
from .coast_diagnostic import _difference, _environment_manifest, _load_reference, _REFERENCE_SHA256
from .errors import EphemerisError, TrajectoryRefinementError
from .explorer import SCIENCE_LOCK
from .models import ImpulsiveTransferCandidate, Scenario
from .research import ResearchRun, _ResearchBudget
from .research_propagation import _ARCS, _COVERAGE, _compose_research_run
from .scenario import load_scenario


_DAMPING_SHA256 = "c370c31f4a3dcd1f3ef324d0f2331bb46d707af0eae6d256ee935471a6c9233d"
_COLUMN_REFERENCE_SHA256 = "164760a35451b3e8cf43bf2213e8466a331dbcb85004249e134e9daefa1a7374"
_CENTRAL_REFERENCE_SHA256 = "8be4356f4c339eaad9ca30ce2f49786d7e65498ae731fc468d8810836a97fb55"
_CONTROL_NAMES = ("departure_azimuth_rad", "departure_elevation_rad", "departure_duration_s",
                  "arrival_azimuth_rad", "arrival_elevation_rad", "arrival_duration_s")


@dataclass(slots=True)
class _TargetingBudget(_ResearchBudget):
    stopped: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _ResearchBudget.__post_init__(self)
        if self.runtime_seconds != 300:
            self._fail("D7-budget", "D7 requires 300 seconds")

    def begin_control(self) -> None:
        self.check()
        if (self.stopped or self.control_attempts >= 8
                or self.control_attempts != self.propagation_evaluations
                or self.completed_arcs != 3 * self.propagation_evaluations
                or self.completed_arcs != self.native_arc_propagations):
            self._fail("D7-budget", "eight ordered controls only; no retries")
        physical._RefinementBudget.begin_control(self)

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check()
        first = self.native_arc_propagations % 3 == 0
        expected_controls = min(self.propagation_evaluations + int(first), 8)
        if (self.stopped or self.native_arc_propagations >= 27
                or self.completed_arcs != self.native_arc_propagations
                or not isinstance(first_in_evaluation, bool) or first_in_evaluation != first
                or self.control_attempts != expected_controls):
            self._fail("D7-budget", "nine three-arc evaluations only; no retries")
        physical._RefinementBudget.begin_arc(self, first_in_evaluation=first_in_evaluation)


@dataclass(slots=True)
class _DampingBudget(_TargetingBudget):
    tighter_started: bool = field(default=False, init=False)

    def begin_control(self) -> None:
        if self.tighter_started or self.control_attempts >= 3:
            self._fail("D8-budget", "three controls only; no controls after selection")
        _TargetingBudget.begin_control(self)

    def begin_tighter(self) -> None:
        self.check()
        if (self.stopped or self.tighter_started or self.control_attempts not in (2, 3)
                or self.propagation_evaluations != self.control_attempts
                or self.completed_arcs != self.native_arc_propagations
                or self.completed_arcs != 3 * self.control_attempts):
            self._fail("D8-budget", "one frozen run after completed trial only")
        self.tighter_started = True

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check()
        first = self.native_arc_propagations % 3 == 0
        expected_controls = self.propagation_evaluations + int(first) - int(self.tighter_started)
        if (self.stopped or self.native_arc_propagations >= 12
                or self.completed_arcs != self.native_arc_propagations
                or not isinstance(first_in_evaluation, bool) or first_in_evaluation != first
                or self.control_attempts != expected_controls):
            self._fail("D8-budget", "four ordered three-arc evaluations only; no retries")
        physical._RefinementBudget.begin_arc(self, first_in_evaluation=first_in_evaluation)


@dataclass(slots=True)
class _ResponseBudget(_TargetingBudget):
    def begin_control(self) -> None:
        self.check()
        if (self.stopped or self.control_attempts >= 5
                or self.propagation_evaluations != 2*self.control_attempts
                or self.completed_arcs != 3*self.propagation_evaluations
                or self.completed_arcs != self.native_arc_propagations):
            self._fail("D9-budget", "five ordered paired commands only; no retries")
        physical._RefinementBudget.begin_control(self)

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check()
        first = self.native_arc_propagations % 3 == 0
        expected_controls = (self.propagation_evaluations + int(first) + 1)//2
        if (self.stopped or self.native_arc_propagations >= 30
                or self.completed_arcs != self.native_arc_propagations
                or not isinstance(first_in_evaluation, bool) or first_in_evaluation != first
                or self.control_attempts != expected_controls):
            self._fail("D9-budget", "ten ordered three-arc evaluations only; no retries")
        physical._RefinementBudget.begin_arc(self, first_in_evaluation=first_in_evaluation)


@dataclass(slots=True)
class _ColumnBudget(_TargetingBudget):
    def begin_control(self) -> None:
        self.check()
        if (self.stopped or self.control_attempts >= 13
                or self.control_attempts != self.propagation_evaluations
                or self.completed_arcs != 3*self.propagation_evaluations
                or self.completed_arcs != self.native_arc_propagations):
            self._fail("D10-budget", "thirteen ordered nominal controls only; no retries")
        physical._RefinementBudget.begin_control(self)

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check()
        first = self.native_arc_propagations % 3 == 0
        if (self.stopped or self.native_arc_propagations >= 39
                or self.completed_arcs != self.native_arc_propagations
                or not isinstance(first_in_evaluation, bool) or first_in_evaluation != first
                or self.control_attempts != self.propagation_evaluations+int(first)):
            self._fail("D10-budget", "thirteen three-arc evaluations only; no retries")
        physical._RefinementBudget.begin_arc(self, first_in_evaluation=first_in_evaluation)


@dataclass(slots=True)
class _CentralBudget(_DampingBudget):
    def begin_control(self) -> None:
        if self.control_attempts >= 2:
            self._fail("D11-budget", "baseline and one trial only")
        _DampingBudget.begin_control(self)

    def begin_tighter(self) -> None:
        if self.control_attempts != 2:
            self._fail("D11-budget", "tighter requires completed sole trial")
        _DampingBudget.begin_tighter(self)

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        if self.native_arc_propagations >= 9:
            self._fail("D11-budget", "three evaluations / nine arcs only")
        _DampingBudget.begin_arc(self, first_in_evaluation=first_in_evaluation)


def _load_central_reference(path: Path, stored: dict[str, Any]) -> dict[str, Any]:
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != _CENTRAL_REFERENCE_SHA256:
        raise ValueError("central reference digest differs from ADR 0095")
    payload = json.loads(raw)
    _validate_central_reference(payload, stored)
    return payload


def _validate_central_reference(payload: dict[str, Any], stored: dict[str, Any]) -> None:
    """Bind completed D10 evidence and reconstruct every imported central column."""
    json.dumps(payload, allow_nan=False)
    data = payload["science"]
    for key, expected in (("scenario", stored["scenario"]), ("candidate", stored["provenance"]["candidate"]),
                          ("runtime", stored["provenance"]["runtime"]),
                          ("environment", stored["provenance"]["environment"]),
                          ("seed_controls", [stored["seed_commands"][n] for n in _CONTROL_NAMES]),
                          ("reference_sha256", _REFERENCE_SHA256), ("response_reference_sha256", _DAMPING_SHA256),
                          ("column_reference_sha256", _COLUMN_REFERENCE_SHA256), ("outcome", "completed")):
        if data[key] != expected:
            raise ValueError(f"central reference {key} mismatch")
    checks = data["column_diagnostics"]["checks"]
    if (len(data["runs"]) != 13 or len(data["column_pairs"]) != 6
            or data["column_diagnostics"]["consistent"] is not True or len(checks) != 2):
        raise ValueError("completed consistent central study required")
    for alpha, check in zip((2**-14, 2**-15), checks):
        ratio = physical._finite_float("retained central discrepancy", check["norm_ratio"])
        if (check["alpha"] != alpha or check["threshold"] != .10 or check["within_threshold"] is not True
                or not 0 <= ratio <= .10):
            raise ValueError("central reference consistency check mismatch")
    residuals = []
    for j, entry in enumerate(data["runs"]):
        run = entry["run"]
        expected = list(data["seed_controls"])
        if j:
            i, sign = (j-1)//2, 1 if j % 2 else -1
            h = correction._PROBE_STEPS[i]
            expected[i] += sign*h
            if (entry["column"], entry["sign"], entry["probe_step"]) != (i, sign, h):
                raise ValueError("central reference column/sign mismatch")
        if (entry["controls"] != expected or run["profile"] != "nominal" or run["outcome"] != "completed"
                or run["integrator_settings"] != stored["nominal"]["integrator_settings"]
                or run["target_state"] != stored["nominal"]["target_state"] or len(run["boundaries"]) != 4):
            raise ValueError("central reference run identity mismatch")
        end, target = run["boundaries"][-1], run["target_state"]
        for key in ("epoch_tdb_s", "epoch_utc", "origin", "orientation"):
            if end[key] != target[key]:
                raise ValueError("central reference terminal frame/epoch mismatch")
        raw = tuple(a-b for a, b in zip((*end["position_m"], *end["velocity_m_s"]),
                                       (*target["position_m"], *target["velocity_m_s"])))
        residual = correction._residual(raw)
        if json.loads(json.dumps(asdict(residual))) != entry["residual"]:
            raise ValueError("central reference raw residual mismatch")
        residuals.append(residual.scaled)
    for i, pair in enumerate(data["column_pairs"]):
        historical = tuple(row[i] for row in data["retained_jacobian"])
        rebuilt = columns._column_pair(residuals[0], residuals[1+2*i], residuals[2+2*i], i,
                                       historical, tuple(data["retained_control_step"]))
        if json.loads(json.dumps(rebuilt)) != pair:
            raise ValueError("central reference reconstructed column mismatch")
    if not all(d["within_thresholds"] for d in _compare_boundaries(data["runs"][0]["run"], stored["nominal"])):
        raise ValueError("central reference baseline identity mismatch")


def _load_column_reference(path: Path, retained: dict[str, Any], stored: dict[str, Any]) -> dict[str, Any]:
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != _COLUMN_REFERENCE_SHA256:
        raise ValueError("column reference digest differs from ADR 0092")
    payload = json.loads(raw)
    _validate_column_reference(payload, retained, stored)
    return payload


def _validate_column_reference(
    payload: dict[str, Any], retained: dict[str, Any], stored: dict[str, Any],
) -> None:
    """Validate D9 identity and the six historical positive-probe identities."""
    json.dumps(payload, allow_nan=False)
    data, d7 = payload["science"], retained["science"]
    for key in ("scenario", "candidate", "runtime", "environment", "seed_controls"):
        if data[key] != d7[key]:
            raise ValueError(f"column reference {key} mismatch")
    if (data["outcome"] != "completed" or data["reference_sha256"] != _REFERENCE_SHA256
            or data["response_reference_sha256"] != _DAMPING_SHA256
            or data["retained_control_step"] != d7["correction"]["control_step"]
            or data["retained_jacobian"] != d7["correction"]["jacobian"]
            or data["response_diagnostics"] is None or len(data["runs"]) != 10):
        raise ValueError("column reference incomplete or direction mismatch")
    seed = data["seed_controls"]
    for i, alpha in enumerate(response._ALPHAS):
        for k, profile in enumerate(("nominal", "tighter")):
            entry = data["runs"][2*i+k]
            run = entry["run"]
            expected = [v+alpha*d for v, d in zip(seed, data["retained_control_step"])]
            if (entry["alpha"] != alpha or entry["controls"] != expected
                    or run["outcome"] != "completed" or run["profile"] != profile
                    or run["target_state"] != stored[profile]["target_state"]
                    or run["integrator_settings"] != stored[profile]["integrator_settings"]):
                raise ValueError("column reference paired run identity mismatch")
    for i, h in enumerate(correction._PROBE_STEPS):
        entry = d7["runs"][i+1]
        run = entry["run"]
        expected = [v+(h if j == i else 0) for j, v in enumerate(seed)]
        if (entry["role"] != f"probe-{i}" or entry["controls"] != expected
                or run["outcome"] != "completed" or run["profile"] != "nominal"
                or run["target_state"] != stored["nominal"]["target_state"]
                or run["integrator_settings"] != stored["nominal"]["integrator_settings"]):
            raise ValueError("historical positive probe identity mismatch")
    slopes = data["response_diagnostics"]["profiles"]["nominal"]["slopes"]
    if len(slopes) != 2:
        raise ValueError("column reference requires two nominal slopes")
    for slope in slopes:
        physical._finite_cartesian_values(slope, "retained nominal slope")


def _load_damping_reference(path: Path, stored: dict[str, Any]) -> dict[str, Any]:
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != _DAMPING_SHA256:
        raise ValueError("damping reference digest differs from Decision 0086")
    payload = json.loads(raw)
    _validate_damping_reference(payload, stored)
    return payload


def _validate_damping_reference(payload: dict[str, Any], stored: dict[str, Any]) -> None:
    """Validate imported scientific identity even after its artifact digest passes."""
    json.dumps(payload, allow_nan=False)
    data = payload["science"]
    for key, expected in (("reference_sha256", _REFERENCE_SHA256), ("outcome", "not-improving"),
                          ("scenario", stored["scenario"]), ("candidate", stored["provenance"]["candidate"]),
                          ("runtime", stored["provenance"]["runtime"]),
                          ("environment", stored["provenance"]["environment"]),
                          ("seed_controls", [stored["seed_commands"][n] for n in _CONTROL_NAMES])):
        if data[key] != expected:
            raise ValueError(f"damping reference {key} mismatch")
    if data["correction"]["rank"] != 6 or data["correction"]["reason"] is not None:
        raise ValueError("damping requires a rank-six completed correction")
    step = physical._finite_cartesian_values(data["correction"]["control_step"], "retained direction")
    if any(abs(v) > bound for v, bound in zip(step, correction._TRUST_SCALES)):
        raise ValueError("retained direction exceeds trust scales")
    baseline = data["runs"][0]
    run = baseline["run"]
    if (baseline["role"] != "baseline" or baseline["controls"] != data["seed_controls"]
            or run["outcome"] != "completed" or run["profile"] != "nominal"
            or run["integrator_settings"] != stored["nominal"]["integrator_settings"]
            or run["target_state"] != stored["nominal"]["target_state"]
            or run["boundaries"][0] != stored["nominal"]["boundaries"][0]
            or not all(d["within_thresholds"] for d in _compare_boundaries(run, stored["nominal"]))):
        raise ValueError("damping reference baseline identity mismatch")


def _run_data(run: ResearchRun) -> dict[str, Any]:
    data = asdict(run)
    settings = data.pop("integrator_settings_json")
    data["integrator_settings"] = None if settings is None else json.loads(settings)
    return json.loads(json.dumps(data, allow_nan=False))


def _compare_boundaries(left: dict[str, Any], right: dict[str, Any]) -> list[dict[str, Any]]:
    if len(left["boundaries"]) != 4 or len(right["boundaries"]) != 4:
        raise ValueError("comparison requires four completed boundaries")
    differences = []
    for i, (a, b) in enumerate(zip(left["boundaries"], right["boundaries"])):
        for key in ("label", "epoch_tdb_s", "epoch_utc", "origin", "orientation"):
            if a[key] != b[key]:
                raise ValueError(f"boundary {i} {key} mismatch")
        differences.append(_difference(
            (*a["position_m"], *a["velocity_m_s"], left["boundary_masses_kg"][i]),
            (*b["position_m"], *b["velocity_m_s"], right["boundary_masses_kg"][i]),
        ))
    return differences


def _terminal_residual(run: ResearchRun) -> tuple[float, ...]:
    if run.outcome != "completed" or run.target_state is None:
        raise ValueError("completed run required for residual")
    end, target = run.boundaries[-1], run.target_state
    return correction._residual(tuple(a-b for a, b in zip(
        (*end.position_m, *end.velocity_m_s), (*target.position_m, *target.velocity_m_s),
    ))).values


def _run_targeting(
    scenario: Scenario, reference: Path, *, damping_reference: Path | None = None,
    response_reference: Path | None = None,
    column_references: tuple[Path, Path] | None = None,
    central_reference: Path | None = None,
) -> dict[str, Any]:
    """One update at most; preserve diagnostics after failure, never retry."""
    damping = damping_reference is not None
    local_response = response_reference is not None
    local_columns = column_references is not None
    central = central_reference is not None
    if sum((damping, local_response, local_columns, central)) > 1:
        raise ValueError("damping, response and column modes are mutually exclusive")
    budget_type = (_CentralBudget if central else _ColumnBudget if local_columns else _ResponseBudget if local_response
                   else _DampingBudget if damping else _TargetingBudget)
    budget = budget_type("d0001-t0035", 300.0)
    science: dict[str, Any] = {
        "research_only": True, "continuous_safety_verified": False,
        "origin": "SSB", "orientation": "J2000", "units": "SI",
        "time_scale": "TDB seconds since J2000", "scenario": scenario.to_dict(),
        "runtime_limit_s": 300, "maximum_controls": 8, "maximum_evaluations": 9,
        "maximum_native_arcs": 27, "automatic_retries": 0, "check_coverage": _COVERAGE,
        "outcome": "aborted", "reason": None, "runs": [], "baseline_comparison": None,
        "correction": None, "improvement": None, "tighter_comparison": None,
        "numerical_agreement": None, "expected_reference_sha256": _REFERENCE_SHA256,
        "rejection_counts": {},
        "control_units": ["rad", "rad", "s", "rad", "rad", "s"],
        "interpretation": "One empirical correction; improvement, closure and numerical "
        "agreement are separate. No accuracy, continuous safety or strict M3 qualification.",
    }
    if damping:
        science.update(maximum_controls=3, maximum_evaluations=4, maximum_native_arcs=12,
                       expected_damping_reference_sha256=_DAMPING_SHA256,
                       damping_baseline_comparison=None, selected_alpha=None,
                       fractions=[{"alpha": a, "status": "not-started", "reason": None} for a in (0.5, 0.25)])
    if local_response:
        science.update(maximum_controls=5, maximum_evaluations=10, maximum_native_arcs=30,
                       expected_response_reference_sha256=_DAMPING_SHA256,
                       response_reference_sha256=None, response_diagnostics=None,
                       response_unavailable_reason="study-not-completed", selected_alpha=None,
                       response_baseline_comparison=None, tighter_baseline_comparison=None,
                       baseline_profile_comparison=None, diagnostic_threshold=response._THRESHOLD,
                       interpretation="Local directional response only; no command selection, derivative "
                       "error bound, accuracy, continuous safety or strict M3 qualification.")
    if local_columns:
        science.update(maximum_controls=13, maximum_evaluations=13, maximum_native_arcs=39,
                       expected_response_reference_sha256=_DAMPING_SHA256,
                       expected_column_reference_sha256=_COLUMN_REFERENCE_SHA256,
                       column_reference_sha256=None, response_baseline_comparison=None,
                       column_baseline_comparison=None, positive_probe_comparisons=[],
                       column_pairs=[], column_diagnostics=None,
                       column_unavailable_reason="study-not-completed", selected_alpha=None,
                       interpretation="Nominal central-column diagnosis only; no solve or selection, "
                       "column/cross-profile accuracy, continuous safety or strict M3 qualification.")
    if central:
        science.update(maximum_controls=2, maximum_evaluations=3, maximum_native_arcs=9,
                       expected_central_reference_sha256=_CENTRAL_REFERENCE_SHA256,
                       central_reference_sha256=None, central_baseline_comparison=None, selected_alpha=None,
                       tighter_status="not-started",
                       interpretation="One research correction from retained central columns; improvement, "
                       "closure and numerical agreement are distinct; no safety or strict M3 qualification.")
    stage = "reference-verification"
    previous: list[physical._PhysicalEnvironment] = []
    with SCIENCE_LOCK:
        try:
            budget.check()
            stored = _load_reference(reference, scenario)
            science["reference_sha256"] = _REFERENCE_SHA256
            budget.check()
            if central:
                stage = "central-reference-verification"
                central_data = _load_central_reference(central_reference, stored)
                science.update(central_reference_sha256=_CENTRAL_REFERENCE_SHA256,
                               imported_source_sha256=central_data["source_sha256"],
                               retained_jacobian=tuple(zip(*(p["central"] for p in central_data["science"]["column_pairs"]))))
                budget.check()
            if damping or local_response or local_columns:
                stage = "damping-reference-verification"
                direction_path = (column_references[0] if local_columns else
                                  response_reference if local_response else damping_reference)
                retained = _load_damping_reference(direction_path, stored)
                science.update(**{("response_reference_sha256" if local_response or local_columns else "damping_reference_sha256"):
                                  _DAMPING_SHA256},
                               imported_source_sha256=retained["source_sha256"],
                               retained_control_step=retained["science"]["correction"]["control_step"])
                if local_response or local_columns:
                    stage = "direction-verification"
                    science["retained_jacobian"] = retained["science"]["correction"]["jacobian"]
                    direction = response._direction(science["retained_jacobian"], science["retained_control_step"])
                    science["predicted_direction"] = direction
                if local_columns:
                    stage = "column-reference-verification"
                    column_reference = _load_column_reference(column_references[1], retained, stored)
                    science.update(column_reference_sha256=_COLUMN_REFERENCE_SHA256,
                                   imported_column_source_sha256=column_reference["source_sha256"],
                                   baseline_profile_comparison=column_reference["science"]["baseline_profile_comparison"])
                budget.check()
            stage = "candidate-verification"
            values = dict(stored["provenance"]["candidate"])
            for key in ("departure_v_infinity_m_s", "arrival_v_infinity_m_s"):
                values[key] = tuple(values[key])
            candidate = physical._verify_candidate_handoff(
                scenario, ImpulsiveTransferCandidate(**values),
                deadline_monotonic_s=budget.deadline_monotonic_s, monotonic=budget.monotonic,
            )
            science["candidate"] = asdict(candidate)
            budget.check()
            runtime = _runtime_manifest(scenario.limits.random_seed)
            if runtime != stored["provenance"]["runtime"]:
                raise ValueError("runtime/kernel identity mismatch")
            science["runtime"] = runtime

            def fresh_environment() -> physical._PhysicalEnvironment:
                budget.check()
                env = physical._build_physical_environment(candidate, scenario.spacecraft, budget=budget)
                budget.check()
                manifest = _environment_manifest(env)
                if manifest != stored["provenance"]["environment"]:
                    raise ValueError("environment/resource identity mismatch")
                if any(env is old or env.bodies is old.bodies for old in previous):
                    raise ValueError("fresh native environment required for every run")
                previous.append(env)
                science["environment"] = manifest
                return env

            stage = "boundary-and-seed-preparation"
            environment = fresh_environment()
            gm = {v.body: v.gravitational_parameter_m3_s2 for v in environment.harmonic_fields}
            initial, target = physical._build_boundary_states(scenario, candidate, gm["Moon"], gm["Mars"])
            budget.begin_control()  # Count the seed before its analytic validation.
            seed = physical._build_initial_burn_controls(scenario, candidate, gm["Moon"], gm["Mars"])
            if isinstance(seed, str):
                science["rejection_counts"][seed] = 1
                raise ValueError(seed)
            if seed != tuple(stored["seed_commands"][n] for n in _CONTROL_NAMES):
                raise ValueError("prescribed seed mismatch")
            for state, expected in ((initial, stored["nominal"]["boundaries"][0]),
                                    (target, stored["nominal"]["target_state"])):
                if json.loads(json.dumps(asdict(state))) != expected:
                    raise ValueError("rebuilt boundary/target mismatch")
            science["seed_controls"] = seed

            def evaluate(role: str, controls: tuple[float, ...], *, tighter: bool = False,
                         alpha: float | None = None, column: int | None = None,
                         sign: int | None = None) -> ResearchRun:
                nonlocal stage
                stage = role
                budget.check()
                if not tighter and role != "baseline":
                    budget.begin_control()
                if (damping or central) and tighter:
                    budget.begin_tighter()
                entry: dict[str, Any] = {"role": role, "controls": controls, "run": None, "reason": None}
                if column is not None:
                    entry.update(column=column, sign=sign, probe_step=correction._PROBE_STEPS[column])
                if damping or local_response or central:
                    entry["alpha"] = alpha
                science["runs"].append(entry)
                prepared = physical._prepare_burn_controls(
                    candidate.candidate_id, scenario.spacecraft, initial.epoch_tdb_s,
                    target.epoch_tdb_s, controls,
                )
                if isinstance(prepared, str):
                    entry["reason"] = prepared
                    science["rejection_counts"][prepared] = 1
                    raise ValueError(prepared)
                entry["controls"] = prepared
                env = environment if role == "baseline" else fresh_environment()
                expected_settings = stored["tighter" if tighter else "nominal"]["integrator_settings"]
                settings = {arc: physical._arc_integrator_profile(candidate.candidate_id, arc, tighter=tighter)
                            for arc in _ARCS}
                if json.loads(json.dumps(settings)) != expected_settings:
                    raise ValueError("integrator settings mismatch")
                run = _compose_research_run(budget, scenario, env, initial, target, prepared,
                                            tighter=tighter, register_control=False)
                entry["run"] = _run_data(run)
                if run.outcome != "completed":
                    entry["reason"] = run.reason
                    science["rejection_counts"][str(run.reason)] = 1
                    raise ValueError(run.reason)
                entry["residual"] = asdict(correction._residual(_terminal_residual(run)))
                budget.check()
                return run

            baseline = evaluate("baseline", seed, alpha=0.0 if local_response else None)
            science["baseline_comparison"] = _compare_boundaries(_run_data(baseline), stored["nominal"])
            if not all(d["within_thresholds"] for d in science["baseline_comparison"]):
                raise ValueError("baseline drift; probes not started")
            if damping or local_response or local_columns:
                comparison_key = "response_baseline_comparison" if local_response or local_columns else "damping_baseline_comparison"
                science[comparison_key] = _compare_boundaries(
                    _run_data(baseline), retained["science"]["runs"][0]["run"],
                )
                if not all(d["within_thresholds"] for d in science[comparison_key]):
                    raise ValueError("D7 baseline drift; damping not started")
            base_residual = _terminal_residual(baseline)
            if central:
                stage = "central-baseline-replay"
                science["central_baseline_comparison"] = _compare_boundaries(
                    _run_data(baseline), central_data["science"]["runs"][0]["run"])
                if not all(d["within_thresholds"] for d in science["central_baseline_comparison"]):
                    raise ValueError("D10 baseline drift; solve not started")
                if correction._residual(base_residual).closes:
                    science["outcome"] = "baseline-closed"
                else:
                    stage = "central-correction-solve"
                    update = correction._central_correction(tuple(tuple(row) for row in science["retained_jacobian"]), base_residual)
                    science["correction"] = update
                    if update["reason"] is not None:
                        raise ValueError(update["reason"])
                    trial_controls = tuple(v+d for v, d in zip(seed, update["control_step"]))
                    trial = evaluate("central-trial", trial_controls, alpha=1.0)
                    trial_residual = _terminal_residual(trial)
                    improving, ratio, reason = correction._improvement(base_residual, trial_residual)
                    actual = correction._residual(trial_residual).scaled
                    base_scaled = correction._residual(base_residual).scaled
                    science["improvement"] = dict(improving=improving, score_ratio=ratio,
                        ratio_unavailable_reason=reason, score_threshold=correction._residual(base_residual).score*(1-1e-4),
                        actual_change=physical._finite_cartesian_values(tuple(a-b for a, b in zip(actual, base_scaled)), "actual change"),
                        model_error=physical._finite_cartesian_values(tuple(a-p for a, p in zip(actual, update["predicted_residual"])), "model error"))
                    science["outcome"] = "not-improving"
                    if improving:
                        science["selected_alpha"] = 1.0
                        science["tighter_status"] = "attempted"
                        frozen = tuple(science["runs"][-1]["controls"])
                        tighter = evaluate("central-tighter", frozen, tighter=True, alpha=1.0)
                        science["tighter_comparison"] = _compare_boundaries(_run_data(trial), _run_data(tighter))
                        science["numerical_agreement"] = all(d["within_thresholds"] for d in science["tighter_comparison"])
                        science["tighter_status"] = "completed"
                        science["outcome"] = "improving"
            elif local_columns:
                stage = "column-baseline-replay"
                science["column_baseline_comparison"] = _compare_boundaries(
                    _run_data(baseline), column_reference["science"]["runs"][0]["run"])
                if not all(d["within_thresholds"] for d in science["column_baseline_comparison"]):
                    raise ValueError("D9 baseline drift; columns not started")
                base_scaled = correction._residual(base_residual).scaled
                for i, h in enumerate(correction._PROBE_STEPS):
                    pair_values = []
                    for sign in (1, -1):
                        controls = tuple(v+(sign*h if j == i else 0) for j, v in enumerate(seed))
                        trial = evaluate(f"column-{i}-{sign:+d}", controls, column=i, sign=sign)
                        if sign == 1:
                            stage = f"positive-probe-{i}-replay"
                            differences = _compare_boundaries(_run_data(trial), retained["science"]["runs"][i+1]["run"])
                            science["positive_probe_comparisons"].append(dict(column=i, differences=differences))
                            if not all(d["within_thresholds"] for d in differences):
                                raise ValueError("positive probe drift; negative probe not started")
                        pair_values.append(correction._residual(_terminal_residual(trial)).scaled)
                    stage = f"column-{i}-arithmetic"
                    historical = tuple(row[i] for row in science["retained_jacobian"])
                    science["column_pairs"].append(columns._column_pair(base_scaled, *pair_values, i,
                        historical, tuple(science["retained_control_step"])))
                    budget.check()
                stage = "column-arithmetic"
                slopes = column_reference["science"]["response_diagnostics"]["profiles"]["nominal"]["slopes"]
                science["column_diagnostics"] = columns._column_diagnostics(
                    science["column_pairs"], direction, tuple(tuple(v) for v in slopes))
                science["column_unavailable_reason"] = None
                science["outcome"] = "completed"
            elif local_response:
                tighter_baseline = evaluate("baseline-tighter", seed, tighter=True, alpha=0.0)
                science["tighter_baseline_comparison"] = _compare_boundaries(
                    _run_data(tighter_baseline), stored["tighter"],
                )
                if not all(d["within_thresholds"] for d in science["tighter_baseline_comparison"]):
                    raise ValueError("tighter baseline drift; perturbations not started")
                science["baseline_profile_comparison"] = _compare_boundaries(
                    _run_data(baseline), _run_data(tighter_baseline),
                )
                nominal_values = [correction._residual(base_residual).scaled]
                tighter_values = [correction._residual(_terminal_residual(tighter_baseline)).scaled]
                for alpha in response._ALPHAS[1:]:
                    controls = tuple(v+alpha*d for v, d in zip(seed, science["retained_control_step"]))
                    trial = evaluate(f"response-{alpha:g}", controls, alpha=alpha)
                    frozen = tuple(science["runs"][-1]["controls"])
                    tighter = evaluate(f"response-{alpha:g}-tighter", frozen, tighter=True, alpha=alpha)
                    nominal_values.append(correction._residual(_terminal_residual(trial)).scaled)
                    tighter_values.append(correction._residual(_terminal_residual(tighter)).scaled)
                stage = "response-arithmetic"
                science["response_diagnostics"] = response._response_diagnostics(
                    direction, tuple(nominal_values), tuple(tighter_values),
                )
                science["response_unavailable_reason"] = None
                science["outcome"] = "completed"
            elif correction._residual(base_residual).closes:
                science["outcome"] = "baseline-closed"
            elif damping:
                science["outcome"] = "not-improving"
                for fraction in science["fractions"]:
                    alpha = fraction["alpha"]
                    fraction.update(status="attempted",
                                    score_threshold=correction._residual(base_residual).score * (1-1e-4*alpha))
                    controls = tuple(v + alpha*d for v, d in zip(seed, science["retained_control_step"]))
                    trial = evaluate(f"fraction-{alpha:g}", controls, alpha=alpha)
                    improving, ratio, reason = correction._improvement(
                        base_residual, _terminal_residual(trial), alpha=alpha,
                    )
                    fraction.update(status="completed", improving=improving, score_ratio=ratio,
                                    ratio_unavailable_reason=reason)
                    if not improving:
                        continue
                    science["selected_alpha"] = alpha
                    science["improvement"] = dict(fraction)
                    frozen = tuple(science["runs"][-1]["controls"])
                    tighter = evaluate("tighter", frozen, tighter=True, alpha=alpha)
                    differences = _compare_boundaries(_run_data(trial), _run_data(tighter))
                    science["tighter_comparison"] = differences
                    science["numerical_agreement"] = all(d["within_thresholds"] for d in differences)
                    science["outcome"] = "improving"
                    break
            else:
                probes = []
                for i, h in enumerate(correction._PROBE_STEPS):
                    controls = tuple(v + (h if j == i else 0) for j, v in enumerate(seed))
                    probes.append(_terminal_residual(evaluate(f"probe-{i}", controls)))
                stage = "correction-solve"
                update = correction._correction(base_residual, tuple(probes))
                science["correction"] = asdict(update)
                if update.control_step is None:
                    raise ValueError(update.reason)
                trial_controls = tuple(a+b for a, b in zip(seed, update.control_step))
                trial = evaluate("trial", trial_controls)
                improving, ratio, reason = correction._improvement(base_residual, _terminal_residual(trial))
                science["improvement"] = {"improving": improving, "score_ratio": ratio,
                                          "ratio_unavailable_reason": reason}
                science["outcome"] = "not-improving"
                if improving:
                    frozen = tuple(science["runs"][-1]["controls"])
                    tighter = evaluate("tighter", frozen, tighter=True)
                    differences = _compare_boundaries(_run_data(trial), _run_data(tighter))
                    science["tighter_comparison"] = differences
                    science["numerical_agreement"] = all(d["within_thresholds"] for d in differences)
                    science["outcome"] = "improving"
            budget.check()
        except (ValueError, OSError, EphemerisError, TrajectoryRefinementError) as exc:
            science["outcome"] = "aborted"
            science["reason"] = f"{stage}: {exc}"
        finally:
            budget.stopped = True
            if local_response and science["response_diagnostics"] is None:
                science["response_unavailable_reason"] = science["reason"]
            if local_columns and science["column_diagnostics"] is None:
                science["column_unavailable_reason"] = science["reason"]
            if central and science["tighter_status"] != "completed":
                attempted = science["tighter_status"] == "attempted"
                science["tighter_status"] = "failed" if attempted else "skipped"
                science["tighter_reason"] = science["reason"] if science["reason"] else science["outcome"]
            if damping:
                for fraction in science["fractions"]:
                    if fraction["status"] == "not-started":
                        fraction.update(status="skipped", reason="earlier-selection" if science["selected_alpha"]
                                        is not None else science["outcome"])
                    elif fraction["status"] == "attempted":
                        fraction.update(status="failed", reason=science["reason"])
    science.update(control_attempts=budget.control_attempts,
                   propagation_evaluations=budget.propagation_evaluations,
                   attempted_arcs=budget.native_arc_propagations, completed_arcs=budget.completed_arcs)
    source = Path(__file__).parent
    return json.loads(json.dumps({"science": science,
        "source_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(source.glob("*.py"))},
        "wall_clock": {"elapsed_s": budget._last_monotonic_s - (budget.deadline_monotonic_s - 300)},
    }, allow_nan=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("output", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--damping-reference", type=Path, help="Opt into D8 with retained Decision 0086 JSON")
    modes.add_argument("--response-reference", type=Path, help="Opt into D9 with retained Decision 0086 JSON")
    modes.add_argument("--column-references", type=Path, nargs=2, metavar=("D7", "D9"),
                       help="Opt into D10 with retained 0086 and 0092 JSON")
    modes.add_argument("--central-reference", type=Path, help="Opt into D11 with retained 0095 JSON")
    args = parser.parse_args(argv)
    scenario = load_scenario(args.scenario)
    with args.output.open("x", encoding="utf-8") as stream:
        options = ({"central_reference": args.central_reference} if args.central_reference is not None else
                   {"column_references": tuple(args.column_references)} if args.column_references is not None else
                   {"response_reference": args.response_reference} if args.response_reference is not None else
                   {"damping_reference": args.damping_reference} if args.damping_reference is not None else {})
        result = _run_targeting(scenario, args.reference, **options)
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return 1 if result["science"]["outcome"] == "aborted" else 0


if __name__ == "__main__":
    raise SystemExit(main())
