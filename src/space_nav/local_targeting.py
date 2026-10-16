"""Private D15 bounded local targeting; no public optimizer or mission claim."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
import hashlib
from importlib import import_module
import json
import math
from pathlib import Path
import time
from typing import Any

from . import local_burn as local
from . import trajectory as physical
from .errors import EphemerisError, TrajectoryRefinementError
from .lunar_departure import _unit


Controls = tuple[float, ...]
Vector3 = tuple[float, float, float]
Basis = tuple[Vector3, Vector3, Vector3]
_STUDY_SHA256 = "01b653b72fb9a25b00f53d17cd7d88da9e9c8102fbec0f908b27da3cae9a34dc"
_MODEL = "local-moon-point-mass-steered-burn-v1"
_PROBE_STEPS = (1., 1., .001, .001, .001, .001)
_CONTROL_SCALES = (300., 300., .1, .1, .1, .1)
_RESIDUAL_SCALES = (10.,)*3+(.01,)*3
_FRACTIONS = (1., .5, .25, .125)


def _six(values: Controls, name: str) -> Controls:
    if not isinstance(values, tuple) or len(values) != 6:
        raise ValueError(f"{name} requires six immutable components")
    return tuple(physical._finite_float(name, value) for value in values)


def _steering_basis(direction: Vector3) -> Basis:
    d = physical._finite_vector3_values(direction, "steering reference")
    if abs(math.hypot(*d)-1) > 1e-12:
        raise ValueError("steering reference must be unit length")
    i = min(range(3), key=lambda j: abs(d[j]))  # Stable X/Y/Z tie order.
    axis = tuple(float(j == i) for j in range(3))
    e1 = _unit(tuple(a-d[i]*b for a, b in zip(axis, d)))
    return d, e1, physical._cross_product(d, e1)


def _steering_direction(basis: Basis, controls: Controls, relative_s: float) -> Vector3:
    x = _six(controls, "steering controls")
    tau = physical._positive_finite("burn duration_s", x[1])
    s = physical._finite_float("relative burn time_s", relative_s)/tau
    # Native RK trial stages can extend beyond exact termination. Extend the
    # same smooth chart there; do not clamp the command or create another burn.
    p, q = (1-s)*x[2]+s*x[4], (1-s)*x[3]+s*x[5]
    return _unit(tuple(d+p*a+q*b for d, a, b in zip(*basis)))


@dataclass(frozen=True, slots=True)
class _TargetDomain:
    baseline: local._LocalCommand
    virtual_parking_state_si: tuple[float, ...]
    launch_window_tdb_s: tuple[float, float]
    arrival_delta_v_m_s: float
    basis: Basis = field(init=False)
    delta_bounds_s: tuple[float, float] = field(init=False)
    duration_bounds_s: tuple[float, float] = field(init=False)
    match_epoch_tdb_s: float = field(init=False)

    def __post_init__(self) -> None:
        c = self.baseline
        parking = _six(self.virtual_parking_state_si, "virtual parking state SI")
        if not isinstance(self.launch_window_tdb_s, tuple) or len(self.launch_window_tdb_s) != 2:
            raise ValueError("launch window requires two bounds")
        lo, hi = (physical._finite_float("launch bound", v) for v in self.launch_window_tdb_s)
        dv = physical._positive_finite("arrival reserve m/s", self.arrival_delta_v_m_s)
        rp = math.hypot(*parking[:3])
        n = math.sqrt(c.mu_m3_s2/rp**3)
        if (lo >= hi or rp <= c.shape_radius_m
                or abs(math.hypot(*parking[3:])-n*rp) > 1e-6
                or abs(physical._dot_product(parking[:3], parking[3:])) > 1e-6*rp):
            raise ValueError("invalid circular parking state or launch window")
        exhaust = physical.STANDARD_GRAVITY_M_S2*c.isp_s
        rate = c.thrust_n/exhaust
        low_tau = .5*c.cutoff_after_ignition_s
        high_tau = min(1.5*c.cutoff_after_ignition_s,
                       (c.initial_state_si[6]-c.dry_mass_kg*math.exp(dv/exhaust))/rate)
        quarter_period = math.pi/(2*n)
        lower = max(-quarter_period, lo-c.ignition_epoch_tdb_s)
        upper = min(quarter_period, hi-c.ignition_epoch_tdb_s,
                    c.match_after_ignition_s-1-low_tau)
        if (lower > upper or low_tau > high_tau
                or c.initial_state_si[6]-rate*low_tau <= c.dry_mass_kg
                or (c.initial_state_si[6]-rate*low_tau)*math.exp(-dv/exhaust) < c.dry_mass_kg):
            raise ValueError("empty local targeting domain")
        object.__setattr__(self, "basis", _steering_basis(c.direction_j2000))
        object.__setattr__(self, "delta_bounds_s", (lower, upper))
        object.__setattr__(self, "duration_bounds_s", (low_tau, high_tau))
        object.__setattr__(self, "match_epoch_tdb_s", c.ignition_epoch_tdb_s+c.match_after_ignition_s)

    @property
    def initial_controls(self) -> Controls:
        return (0., self.baseline.cutoff_after_ignition_s, 0., 0., 0., 0.)

    def command(self, controls: Controls) -> local._LocalCommand:
        x = _six(controls, "targeting controls")
        delta, tau = x[:2]
        if (not self.delta_bounds_s[0] <= delta <= self.delta_bounds_s[1]
                or not self.duration_bounds_s[0] <= tau <= self.duration_bounds_s[1]
                or any(abs(slope) > 1 for slope in x[2:])):
            raise ValueError("command outside ignition/duration/slope domain")
        c = self.baseline
        ti = c.ignition_epoch_tdb_s+delta
        # New commands end at the representable frozen absolute epoch. Preserve
        # the historical relative-time arithmetic for the exact baseline replay.
        match_offset = (c.match_after_ignition_s if delta == 0
                        else self.match_epoch_tdb_s-ti)
        if (not self.launch_window_tdb_s[0] <= ti <= self.launch_window_tdb_s[1]
                or tau > match_offset-1 or ti+tau > self.match_epoch_tdb_s-1):
            raise ValueError("command outside absolute ignition/cutoff domain")
        mf = c.initial_state_si[6]-c.thrust_n*tau/(physical.STANDARD_GRAVITY_M_S2*c.isp_s)
        reserve = mf*math.exp(-self.arrival_delta_v_m_s/(physical.STANDARD_GRAVITY_M_S2*c.isp_s))
        if mf <= c.dry_mass_kg or reserve < c.dry_mass_kg:
            raise ValueError("command violates cutoff/arrival mass reserve")
        parking = self.virtual_parking_state_si
        rp = math.hypot(*parking[:3])
        n = math.sqrt(c.mu_m3_s2/rp**3)
        actual_delta = ti-c.ignition_epoch_tdb_s
        angle = -n*c.cutoff_after_ignition_s/2+n*actual_delta
        u, tangent = _unit(parking[:3]), _unit(parking[3:])
        r = tuple(rp*(a*math.cos(angle)+b*math.sin(angle)) for a, b in zip(u, tangent))
        v = tuple(n*rp*(-a*math.sin(angle)+b*math.cos(angle)) for a, b in zip(u, tangent))
        # Preserve the pinned baseline's bitwise initial-state arithmetic.
        initial = c.initial_state_si if actual_delta == 0 else r+v+(c.initial_state_si[6],)
        return replace(c, ignition_epoch_tdb_s=ti, cutoff_after_ignition_s=tau,
                       match_after_ignition_s=match_offset, initial_state_si=initial,
                       target_state_si=c.target_state_si[:6]+(mf,))


@dataclass(slots=True)
class _TargetBudget(physical._RefinementBudget):
    completed_arcs: int = field(default=0, init=False)
    tighter_evaluations: int = field(default=0, init=False)
    _evaluation_start_arcs: int = field(default=0, init=False)
    _active: bool = field(default=False, init=False)

    def begin_control(self) -> None:
        self.check()
        if self.control_attempts >= 65 or self.tighter_evaluations:
            self._fail("D15 proposals", "65 nominal proposals only; no work after tighter")
        if self.completed_arcs != self.native_arc_propagations:
            self._fail("D15 proposals", "no retry after incomplete arc")
        self.control_attempts += 1

    def begin_evaluation(self, tighter: bool) -> None:
        self.check()
        if (not isinstance(tighter, bool) or self.max_arcs_per_evaluation != 2
                or self.propagation_evaluations >= 66 or self.tighter_evaluations
                or (tighter and self.propagation_evaluations == 0)
                or self.completed_arcs != self.native_arc_propagations
                or (self._active and self.native_arc_propagations != self._evaluation_start_arcs+2)
                or (not tighter and self.propagation_evaluations >= self.control_attempts)):
            self._fail("D15 evaluation", "66 ordered burn/coast evaluations; no retry")
        self.propagation_evaluations += 1
        self.tighter_evaluations += int(tighter)
        self._evaluation_start_arcs = self.native_arc_propagations
        self._active = True

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check()
        index = self.native_arc_propagations-self._evaluation_start_arcs
        if (not self._active or not isinstance(first_in_evaluation, bool)
                or self.native_arc_propagations >= 132 or index not in (0, 1)
                or first_in_evaluation != (index == 0)
                or self.completed_arcs != self.native_arc_propagations):
            self._fail("D15 arc", "132 ordered native launches only; no retry")
        self.native_arc_propagations += 1


def _evaluate_command(
    domain: _TargetDomain, controls: Controls, command: local._LocalCommand,
    tighter: bool, budget: _TargetBudget, evidence: dict[str, Any],
) -> dict[str, Any]:
    cutoff, checks = local._native_local_arc(command, command.initial_state_si, 0.,
        command.cutoff_after_ignition_s, True, tighter, budget,
        direction_at_s=lambda at: _steering_direction(domain.basis, controls, at))
    evidence["cutoff_state_si"] = cutoff
    if (abs(cutoff[6]-command.target_state_si[6]) > 1e-6
            or cutoff[6]*math.exp(-domain.arrival_delta_v_m_s/(
                physical.STANDARD_GRAVITY_M_S2*command.isp_s)) < command.dry_mass_kg):
        raise ValueError("D15 propagated cutoff/arrival mass disagreement")
    final, coast_checks = local._native_local_arc(command, cutoff,
        command.cutoff_after_ignition_s, command.match_after_ignition_s, False, tighter, budget)
    return {"cutoff_state_si": cutoff, "final_state_si": final,
            "checked_saved_states": checks+coast_checks}


Evaluator = Callable[[_TargetDomain, Controls, local._LocalCommand, bool, _TargetBudget, dict[str, Any]], dict[str, Any]]


def _agreement(a: local.State7, b: local.State7) -> tuple[float, float, float]:
    differences = (math.dist(a[:3], b[:3]), math.dist(a[3:6], b[3:6]), abs(a[6]-b[6]))
    return tuple(physical._finite_float("endpoint agreement", value) for value in differences)


def _solve_step(residual: Controls, matrix: tuple[Controls, ...]) -> dict[str, Any]:
    import numpy as np

    r = np.asarray(_six(residual, "scaled residual"))
    if len(matrix) != 6:
        raise ValueError("Jacobian requires six rows")
    j = np.asarray(tuple(_six(row, "Jacobian row") for row in matrix))
    try:
        z, _, rank, singular = np.linalg.lstsq(j, -r, rcond=1e-10)
    except np.linalg.LinAlgError as exc:
        raise ValueError(f"D15 least-squares failed: {exc}") from exc
    for values in (z, singular):
        for value in values:
            physical._finite_float("least-squares output", float(value))
    condition = float(singular[0]/singular[-1]) if singular[-1] > 0 else None
    evidence: dict[str, Any] = {"rank": int(rank), "singular_values": singular.tolist(),
        "condition_number": condition, "rcond": 1e-10, "raw_z": z.tolist(),
        "capped_z": None, "step_controls": None, "predicted_residual": None,
        "predicted_score": None, "outcome": "rank-condition-unresolved"}
    if rank != 6 or condition is None or not math.isfinite(condition) or condition > 1e10:
        # None, rather than Inf, is the explicit unavailable condition diagnostic.
        if condition is not None and not math.isfinite(condition):
            evidence["condition_number"] = None
        return evidence
    capped = z/max(1., float(np.max(np.abs(z))))
    step = capped*np.asarray(_CONTROL_SCALES)
    with np.errstate(over="ignore", invalid="ignore"):
        predicted = r+j@capped
    for value in (*step, *predicted):
        physical._finite_float("step/predicted residual", float(value))
    score = math.hypot(*predicted)
    physical._finite_float("predicted score", score)
    evidence.update(capped_z=capped.tolist(), step_controls=step.tolist(),
        predicted_residual=predicted.tolist(), predicted_score=score,
        outcome="ready" if np.any(step != 0) and score < math.hypot(*r) else "no-predicted-decrease")
    return evidence


def _correct_target(
    domain: _TargetDomain, retained_nominal: local.State7, budget: _TargetBudget,
    report: dict[str, Any], *, evaluate: Evaluator = _evaluate_command,
) -> None:
    """Bounded state machine; injected evaluator is only for deterministic tests."""
    proposals: list[dict[str, Any]] = []
    iterations: list[dict[str, Any]] = []
    report.update(proposals=proposals, iterations=iterations, best_accepted_proposal=None,
                  baseline_replay="unavailable", agreement="unavailable", outcome="failed")

    def propose(x: Controls, role: str, parent: int | None, *, tighter: bool = False,
                fraction: float | None = None) -> dict[str, Any]:
        budget.check()
        if not tighter:
            budget.begin_control()
        entry: dict[str, Any] = {"id": len(proposals), "role": role, "parent": parent,
            "controls": x, "control_units": ("s", "s", "1", "1", "1", "1"),
            "profile": "tighter" if tighter else "nominal", "fraction": fraction,
            "feasible": None, "outcome": "failed", "reason": "not completed",
            "command": None, "cutoff_epoch_tdb_s": None, "match_epoch_tdb_s": domain.match_epoch_tdb_s,
            "steering_rate_upper_rad_s": None, "cutoff_state_si": None, "final_state_si": None,
            "residual_si": None, "scaled_residual": None, "score": None,
            "closure": "unavailable", "accepted": False, "acceptance_limit": None}
        proposals.append(entry)
        try:
            command = domain.command(x)
        except ValueError as exc:
            # Only finite, analytically infeasible controls are eligible to skip.
            _six(x, "proposed controls")
            entry.update(feasible=False, outcome="skipped", reason=str(exc))
            return entry
        entry.update(feasible=True, command=asdict(command), reason="evaluation did not complete",
                     cutoff_epoch_tdb_s=command.ignition_epoch_tdb_s+command.cutoff_after_ignition_s,
                     steering_rate_upper_rad_s=math.hypot(x[4]-x[2], x[5]-x[3])/x[1])
        budget.begin_evaluation(tighter)
        try:
            result = evaluate(domain, x, command, tighter, budget, entry)
            budget.check()  # Reject even a synthetically supplied late endpoint.
            if (budget.native_arc_propagations != budget._evaluation_start_arcs+2
                    or budget.completed_arcs != budget.native_arc_propagations):
                raise ValueError("D15 incomplete burn/coast evaluation")
            cutoff, final = (tuple(result[key]) for key in ("cutoff_state_si", "final_state_si"))
            local._check_local_state(command, cutoff)
            local._check_local_state(command, final)
            mass_error = abs(cutoff[6]-command.target_state_si[6])
            if mass_error > 1e-6 or final[6] != cutoff[6]:
                raise ValueError("D15 analytic cutoff/coast mass disagreement")
            reserve = cutoff[6]*math.exp(-domain.arrival_delta_v_m_s/(
                physical.STANDARD_GRAVITY_M_S2*command.isp_s))
            if reserve < command.dry_mass_kg:
                raise ValueError("D15 propagated arrival mass reserve violated")
            closure = local._closure(command, final)
            residual = tuple(a/b for a, b in zip(closure["residual_si"], _RESIDUAL_SCALES))
            score = physical._finite_float("scaled residual norm", math.hypot(*residual))
            entry.update(result, **closure, cutoff_state_si=cutoff, final_state_si=final,
                         scaled_residual=residual, score=score, cutoff_mass_error_kg=mass_error,
                         post_arrival_reserve_kg=reserve, outcome="completed", reason=None)
        except (ValueError, TypeError, KeyError, OverflowError, TrajectoryRefinementError) as exc:
            entry["reason"] = str(exc)
            raise
        return entry

    current = propose(domain.initial_controls, "baseline", None)
    if current["outcome"] != "completed":
        raise ValueError("D15 baseline command inadmissible")
    differences = _agreement(tuple(current["final_state_si"]), retained_nominal)
    report["baseline_replay_differences_si"] = differences
    if not all(x <= y for x, y in zip(differences, (1., .001, 1e-6))):
        report.update(outcome="baseline-replay-mismatch", baseline_replay="fail")
        return
    report["baseline_replay"] = "pass"
    current["accepted"] = True
    report["best_accepted_proposal"] = current["id"]
    for iteration in range(4):
        if current["closure"] == "pass":
            break
        x = tuple(current["controls"])
        record: dict[str, Any] = {"iteration": iteration, "parent": current["id"],
            "probe_ids": [], "trial_ids": [], "jacobian": None, "solve": None,
            "probe_steps": _PROBE_STEPS, "control_scales": _CONTROL_SCALES}
        iterations.append(record)
        probes = []
        # Preflight the complete central stencil; never launch half a stencil.
        commands = [tuple(v+(sign*h if j == i else 0) for j, v in enumerate(x))
                    for i, h in enumerate(_PROBE_STEPS) for sign in (1, -1)]
        invalid = False
        for control in commands:
            try:
                domain.command(control)
            except ValueError:
                invalid = True
        if invalid:
            for control in commands:
                budget.begin_control()
                entry = {"id": len(proposals), "role": "probe", "parent": current["id"],
                    "controls": control, "control_units": ("s", "s", "1", "1", "1", "1"),
                    "profile": "nominal", "outcome": "skipped", "feasible": True,
                    "reason": "central stencil unavailable; no native probes", "command": None,
                    "cutoff_epoch_tdb_s": None, "match_epoch_tdb_s": domain.match_epoch_tdb_s,
                    "steering_rate_upper_rad_s": None, "cutoff_state_si": None, "final_state_si": None,
                    "residual_si": None, "scaled_residual": None, "score": None,
                    "closure": "unavailable", "accepted": False}
                try:
                    entry["command"] = asdict(domain.command(control))
                except ValueError as exc:
                    entry.update(feasible=False, reason=str(exc))
                proposals.append(entry)
                record["probe_ids"].append(entry["id"])
            report["outcome"] = "derivative-domain-unresolved"
            return
        for control in commands:
            record["probe_ids"].append(len(proposals))
            probe = propose(control, "probe", current["id"])
            probes.append(probe)
        matrix = tuple(tuple((probes[2*i]["scaled_residual"][row]-probes[2*i+1]["scaled_residual"][row])
                              /(2*h/scale) for i, (h, scale) in enumerate(zip(_PROBE_STEPS, _CONTROL_SCALES)))
                       for row in range(6))
        matrix = tuple(_six(row, "central Jacobian row") for row in matrix)
        record["jacobian"] = matrix
        solution = _solve_step(tuple(current["scaled_residual"]), matrix)
        record["solve"] = solution
        if solution["outcome"] != "ready":
            report["outcome"] = solution["outcome"]
            return
        step = solution["step_controls"]
        new_x = tuple(v+d for v, d in zip(x, step))
        _six(new_x, "full proposed update")
        ti = domain.baseline.ignition_epoch_tdb_s
        if ti+new_x[0] == ti+x[0] and new_x[1:] == x[1:]:
            report["outcome"] = "unrepresentable-update"
            return
        accepted = None
        for alpha in _FRACTIONS:
            trial_x = tuple(v+alpha*d for v, d in zip(x, step))
            _six(trial_x, "trial controls")  # Nonfinite arithmetic stops, never skips.
            record["trial_ids"].append(len(proposals))
            trial = propose(trial_x, "trial", current["id"], fraction=alpha)
            if trial["outcome"] == "skipped":
                continue
            limit = (1-1e-4*alpha)*current["score"]
            trial["acceptance_limit"] = limit
            if trial["closure"] == "pass" or trial["score"] <= limit:
                trial["accepted"] = True
                accepted = trial
                break
        if accepted is None:
            report["outcome"] = "no-acceptable-step"
            return
        current = accepted
        report["best_accepted_proposal"] = current["id"]
    if current["closure"] != "pass":
        report["outcome"] = "not-converged"
        return
    repeated = propose(tuple(current["controls"]), "frozen-repeat", current["id"], tighter=True)
    differences = _agreement(tuple(current["final_state_si"]), tuple(repeated["final_state_si"]))
    report["agreement_differences_si"] = differences
    agrees = all(x <= y for x, y in zip(differences, (1., .001, 1e-6)))
    report["agreement"] = "pass" if agrees else "fail"
    budget.check()
    report["outcome"] = ("local-qualified" if repeated["closure"] == "pass" and agrees
                         else "tighter-unqualified")


def _bind_references(
    reference: dict[str, Any], study: dict[str, Any], window: tuple[float, float],
) -> _TargetDomain:
    command = local._make_local_command(reference, window)
    if (json.loads(json.dumps(asdict(command))) != study["command"]
            or study["candidate_id"] != reference["candidate"]["candidate_id"]
            or study["branch_phase_rad"] != reference["results"]["free"]["branches"][0]["phase_rad"]
            or study["model_id"] != local._MODEL or study["outcome"] != "completed"
            or study["reference_sha256"] != local._REFERENCE_SHA256
            or tuple(study["launch_window_tdb_s"]) != window
            or study["retained_lunar_resource"] != reference["lunar_field_provenance"]
            or (study["origin"], study["orientation"], study["units"], study["time_scale"])
               != ("Moon", "J2000", "SI", "TDB seconds since J2000")
            or study["native_arc_propagations"] != 4 or study["completed_arcs"] != 4
            or len(study["runs"]) != 2):
        raise ValueError("D15 retained command/model/resource binding mismatch")
    for tighter, run in zip((False, True), study["runs"]):
        name = "tighter" if tighter else "nominal"
        if (study["profiles"][name] != json.loads(json.dumps(local._local_profile(tighter)))
                or run["profile"] != name or run["outcome"] != "completed"):
            raise ValueError("D15 retained profiles/runs mismatch")
        cutoff, final = (tuple(run[key]) for key in ("cutoff_state_si", "final_state_si"))
        local._check_local_state(command, cutoff)
        local._check_local_state(command, final)
        if (any(run[key] != json.loads(json.dumps(value)) for key, value in local._closure(command, final).items())
                or abs(cutoff[6]-command.target_state_si[6]) > 1e-6 or final[6] != cutoff[6]
                or run["cutoff_mass_error_kg"] != abs(cutoff[6]-command.target_state_si[6])):
            raise ValueError("D15 retained endpoint/mass/residual mismatch")
    differences = _agreement(*(tuple(run["final_state_si"]) for run in study["runs"]))
    if list(differences) != study["agreement_differences_si"] or study["agreement"] != "pass":
        raise ValueError("D15 retained agreement mismatch")
    branch = reference["results"]["free"]["branches"][0]
    return _TargetDomain(command, tuple(branch["position_m"]+branch["parking_velocity_m_s"]),
                         window, reference["candidate"]["arrival_delta_v_m_s"])


def _run_local_targeting(
    reference_path: Path, study_path: Path, *, monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Prepare one bounded study, returning evidence even on an expected failure.

    D15.2 tests this with injected adapters only; D15.3 separately authorizes the
    live retained-reference study. Never writes or overwrites an evidence file.
    """
    budget = _TargetBudget("d0001-t0035", 300., monotonic, max_arcs_per_evaluation=2)
    report: dict[str, Any] = {"candidate_id": "d0001-t0035", "model_id": _MODEL,
        "origin": "Moon", "orientation": "J2000", "units": "SI",
        "time_scale": "TDB seconds since J2000", "mission_qualified": False,
        "outcome": "failed", "reason": None, "agreement": "unavailable",
        "proposals": [], "iterations": [], "best_accepted_proposal": None,
        "baseline_replay": "unavailable", "reference_sha256": local._REFERENCE_SHA256,
        "study_sha256": _STUDY_SHA256, "binding": None, "source_sha256": None,
        "profiles": {"nominal": local._local_profile(False), "tighter": local._local_profile(True)},
        "omissions": "Earth/Sun, harmonics, SRP, relativity, Mars; no continuous safety or hardware qualification"}
    try:
        budget.check()
        raw, old_raw = reference_path.read_bytes(), study_path.read_bytes()
        if (hashlib.sha256(raw).hexdigest() != local._REFERENCE_SHA256
                or hashlib.sha256(old_raw).hexdigest() != _STUDY_SHA256):
            raise ValueError("D15 pinned reference/study SHA256 mismatch")
        reference, study = json.loads(raw), json.loads(old_raw)
        search = reference["scenario"]["search"]
        window = tuple(local.ephemeris.utc_to_tdb(search[key]) for key in
                       ("departure_start_utc", "departure_end_utc"))
        budget.check()
        domain = _bind_references(reference, study, window)
        report["binding"] = asdict(domain)
        report["historical_source_sha256"] = study["source_sha256"]
        report["retained_lunar_resource"] = reference["lunar_field_provenance"]
        report["kernels"] = local.ephemeris.kernel_metadata()
        report["reference_paths"] = (str(reference_path), str(study_path))
        report["source_sha256"] = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ("local_targeting.py", "local_burn.py", "lunar_departure.py", "models.py", "trajectory.py", "ephemeris.py")}
        try:
            report["runtime_versions"] = {name: str(import_module(name).__version__)
                                          for name in ("numpy", "tudatpy")}
        except (ImportError, AttributeError) as exc:
            raise TrajectoryRefinementError(f"D15 runtime provenance unavailable: {exc}") from exc
        _correct_target(domain, tuple(study["runs"][0]["final_state_si"]), budget, report)
        budget.check()
    except (ValueError, TypeError, KeyError, OSError, OverflowError, EphemerisError,
            TrajectoryRefinementError) as exc:
        report.update(outcome="failed", reason=f"D15 stopped: {exc}", agreement="unavailable")
    report.update(nominal_proposals=budget.control_attempts,
        propagation_evaluations=budget.propagation_evaluations,
        tighter_evaluations=budget.tighter_evaluations,
        native_arc_propagations=budget.native_arc_propagations, completed_arcs=budget.completed_arcs,
        elapsed_wall_s=budget._last_monotonic_s-(budget.deadline_monotonic_s-300.))
    return report
