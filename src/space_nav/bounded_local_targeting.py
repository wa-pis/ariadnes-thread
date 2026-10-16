"""Private D16 bound-aware local targeting; never a mission qualification."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
import hashlib
from importlib import import_module
import json
import math
from pathlib import Path
import time
from typing import Any, NoReturn

from . import local_burn as local, local_targeting as target, trajectory as physical
from .errors import EphemerisError, TrajectoryRefinementError


_STEERING_SHA256 = "678287cc7aee2b3d83e89c9fbff1113a96d24c5b8960f047aeadb82d049c4274"
_SEED = (-1200., 5349.046145563809, -.23058763173986188, .11687483834729254,
         -.18303318185548473, -.0660432629910532)
_SETTINGS = {"method": "trf", "tr_solver": "exact", "loss": "linear", "x_scale": 1.,
             "ftol": 1e-10, "xtol": 1e-10, "gtol": 1e-10, "max_nfev": 40,
             "verbose": 0, "workers": None}


class _Limit(ValueError):
    """An independently counted D16 work/deadline limit, not a bad residual."""


class _DomainUnresolved(ValueError):
    def __init__(self, outcome: str, detail: str) -> None:
        self.outcome = outcome
        super().__init__(f"D16 {outcome}: {detail}")


class _Closed(Exception):
    """Unwind SciPy immediately after a closed objective, before its next Jacobian."""

    def __init__(self, entry: dict[str, Any]) -> None:
        self.entry = entry
        super().__init__("physical objective closure")


@dataclass(slots=True)
class _BoundBudget(target._TargetBudget):
    objective_requests: int = field(default=0, init=False)
    jacobian_batches: int = field(default=0, init=False)
    completed_jacobian_batches: int = field(default=0, init=False)
    nominal_evaluations: int = field(default=0, init=False)
    limit_reason: str | None = field(default=None, init=False)

    def limit(self, reason: str) -> NoReturn:
        self.limit_reason = reason
        raise _Limit(reason)

    def _fail(self, operation: str, detail: str) -> NoReturn:
        # Native callbacks wrap exceptions; retain deadline classification here.
        if operation == "deadline" and detail == "shared deadline reached":
            self.limit(f"D16 deadline: {detail}")
        physical._RefinementBudget._fail(self, operation, detail)

    def ready(self) -> None:
        self.check()
        if (self.max_arcs_per_evaluation != 2 or self.tighter_evaluations
                or self.completed_arcs != self.native_arc_propagations
                or (self._active and self.native_arc_propagations != self._evaluation_start_arcs+2)):
            raise ValueError("D16 ordered complete burn/coast evaluations only; no retry")

    def begin_control(self) -> None:
        self.ready()
        self.control_attempts += 1

    def begin_objective(self) -> None:
        self.ready()
        if self.objective_requests >= 40:
            self.limit("D16 objective-request limit 40 reached")
        self.objective_requests += 1

    def begin_batch(self) -> None:
        self.ready()
        if self.jacobian_batches >= 20:
            self.limit("D16 Jacobian-batch limit 20 reached")
        if self.nominal_evaluations+12 > 280 or self.native_arc_propagations+24 > 560:
            self.limit("D16 complete twelve-probe batch cannot fit nominal budget")
        self.jacobian_batches += 1

    def begin_evaluation(self, tighter: bool) -> None:
        self.ready()
        if not isinstance(tighter, bool) or (tighter and self.nominal_evaluations == 0):
            raise ValueError("D16 evaluation requires nominal replay before tighter")
        if self.propagation_evaluations >= 281 or (not tighter and self.nominal_evaluations >= 280):
            self.limit("D16 evaluation ceiling reached; tighter pair remains reserved")
        self.propagation_evaluations += 1
        self.nominal_evaluations += int(not tighter)
        self.tighter_evaluations += int(tighter)
        self._evaluation_start_arcs = self.native_arc_propagations
        self._active = True

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check()
        index = self.native_arc_propagations-self._evaluation_start_arcs
        if (not self._active or not isinstance(first_in_evaluation, bool) or index not in (0, 1)
                or first_in_evaluation != (index == 0)
                or self.completed_arcs != self.native_arc_propagations):
            raise ValueError("D16 native burn/coast order violated; no retry")
        if self.native_arc_propagations >= (562 if self.tighter_evaluations else 560):
            self.limit("D16 native-launch ceiling reached")
        self.native_arc_propagations += 1


def _bounds(domain: target._TargetDomain) -> tuple[target.Controls, target.Controls]:
    lower = (domain.delta_bounds_s[0], domain.duration_bounds_s[0], -1., -1., -1., -1.)
    upper = (domain.delta_bounds_s[1], domain.duration_bounds_s[1], 1., 1., 1., 1.)
    # Certify the full timing box, including representable absolute-time checks.
    coast = domain.match_epoch_tdb_s-(domain.baseline.ignition_epoch_tdb_s+upper[0])-upper[1]
    if coast < 1 or any(a >= b for a, b in zip(lower, upper)):
        raise _DomainUnresolved("domain-unresolved", "unsupported coupled timing box")
    try:
        for delta in domain.delta_bounds_s:
            for duration in domain.duration_bounds_s:
                domain.command((delta, duration, 0., 0., 0., 0.))
    except ValueError as exc:
        raise _DomainUnresolved("domain-unresolved", f"timing-box corner: {exc}") from exc
    return lower, upper


def _stencils(domain: target._TargetDomain, x: target.Controls) -> list[tuple[str, target.Controls, target.Controls]]:
    pairs = []
    for j, h in enumerate(target._PROBE_STEPS):
        for name, offsets in (("central", (h, -h)), ("forward", (h, 2*h)), ("backward", (-h, -2*h))):
            points = [tuple(v+(offset if i == j else 0.) for i, v in enumerate(x)) for offset in offsets]
            try:
                for point in points:
                    domain.command(point)
            except ValueError:
                continue
            pairs.append((name, points[0], points[1]))
            break
        else:
            raise _DomainUnresolved("derivative-domain-unresolved", f"coordinate {j}; fixed h={h}")
    return pairs


def _validate_endpoint(domain: target._TargetDomain, command: local._LocalCommand,
                       result: dict[str, Any]) -> dict[str, Any]:
    cutoff, final = (tuple(result[key]) for key in ("cutoff_state_si", "final_state_si"))
    local._check_local_state(command, cutoff)
    local._check_local_state(command, final)
    error = abs(cutoff[6]-command.target_state_si[6])
    reserve = cutoff[6]*math.exp(-domain.arrival_delta_v_m_s/(
        physical.STANDARD_GRAVITY_M_S2*command.isp_s))
    if error > 1e-6 or final[6] != cutoff[6] or reserve < command.dry_mass_kg:
        raise ValueError("D16 analytic cutoff/coast mass or arrival reserve disagreement")
    closure = local._closure(command, final)
    residual = target._six(tuple(a/b for a, b in zip(closure["residual_si"], target._RESIDUAL_SCALES)),
                           "scaled residual")
    return {**closure, "cutoff_state_si": cutoff, "final_state_si": final,
            "scaled_residual": residual,
            "score": physical._finite_float("residual norm", math.hypot(*residual)),
            "cutoff_mass_error_kg": error, "post_arrival_reserve_kg": reserve}


class _Corrector:
    def __init__(self, domain: target._TargetDomain, seed: target.Controls,
                 budget: _BoundBudget, report: dict[str, Any], evaluate: target.Evaluator) -> None:
        self.domain, self.seed, self.budget = domain, target._six(seed, "seed"), budget
        self.report, self.evaluate = report, evaluate
        self.entries: list[dict[str, Any]] = []
        self.jacobians: list[dict[str, Any]] = []
        self.accepted: list[int] = []
        self.center: dict[str, Any] | None = None
        report.update(proposals=self.entries, jacobians=self.jacobians,
                      accepted_iterates=self.accepted, best_objective=None,
                      selected_objective=None, baseline_replay="unavailable", agreement="unavailable",
                      baseline_replay_differences_si=None, agreement_differences_si=None,
                      solver_result=None, outcome="failed", reason=None, mission_qualified=False)

    def controls(self, y: Any) -> target.Controls:
        values = target._six(tuple(y), "solver coordinates")
        return target._six(tuple(a+t*b for a, t, b in zip(self.seed, target._CONTROL_SCALES, values)),
                           "physical controls")

    def propose(self, x: target.Controls, role: str, parent: int | None,
                *, tighter: bool = False) -> dict[str, Any]:
        self.budget.begin_control()
        entry: dict[str, Any] = {"id": len(self.entries), "role": role, "parent": parent,
            "controls": x, "control_units": ("s", "s", "1", "1", "1", "1"),
            "profile": "tighter" if tighter else "nominal", "cache_hit": False,
            "outcome": "failed", "reason": "not completed", "command": None,
            "cutoff_state_si": None, "final_state_si": None, "residual_si": None,
            "scaled_residual": None, "closure": "unavailable", "score": None,
            "accepted_iterate": False, "match_epoch_tdb_s": self.domain.match_epoch_tdb_s}
        entry.update(cutoff_epoch_tdb_s=None, steering_rate_upper_rad_s=None,
                     cutoff_mass_error_kg=None, post_arrival_reserve_kg=None)
        self.entries.append(entry)
        try:
            command = self.domain.command(x)
            entry.update(command=asdict(command),
                         cutoff_epoch_tdb_s=command.ignition_epoch_tdb_s+command.cutoff_after_ignition_s,
                         steering_rate_upper_rad_s=math.hypot(x[4]-x[2], x[5]-x[3])/x[1])
            self.budget.begin_evaluation(tighter)
            result = self.evaluate(self.domain, x, command, tighter, self.budget, entry)
            self.budget.check()
            if (self.budget.native_arc_propagations != self.budget._evaluation_start_arcs+2
                    or self.budget.completed_arcs != self.budget.native_arc_propagations):
                raise ValueError("D16 incomplete burn/coast evaluation")
            entry.update(result, **_validate_endpoint(self.domain, command, result),
                         outcome="completed", reason=None)
        except (ValueError, TypeError, KeyError, OverflowError, TrajectoryRefinementError) as exc:
            entry["reason"] = str(exc)
            raise
        if role in ("seed-replay", "objective"):
            best = self.report["best_objective"]
            if best is None or entry["score"] < self.entries[best]["score"]:
                self.report["best_objective"] = entry["id"]
        return entry

    def objective(self, y: Any) -> target.Controls:
        self.budget.begin_objective()
        x = self.controls(y)
        if self.budget.objective_requests == 1:
            if x != self.seed or tuple(y) != (0.,)*6:
                raise ValueError("D16 initial solver request changed the replayed seed")
            entry = dict(self.entries[0], id=len(self.entries), role="objective", parent=0,
                         cache_hit=True, cache_source=0, accepted_iterate=False)
            self.entries.append(entry)
        else:
            entry = self.propose(x, "objective", self.accepted[-1] if self.accepted else 0)
        self.center = entry
        if entry["closure"] == "pass":
            raise _Closed(entry)
        return tuple(entry["scaled_residual"])

    def jacobian(self, y: Any) -> tuple[target.Controls, ...]:
        import numpy as np

        x = self.controls(y)
        center = self.center
        if center is None or x != tuple(center["controls"]):
            raise ValueError("D16 Jacobian requires its completed objective center")
        pairs = _stencils(self.domain, x)  # All twelve commands before any launch.
        self.budget.begin_batch()
        center["accepted_iterate"] = True
        if not self.accepted or self.accepted[-1] != center["id"]:
            self.accepted.append(center["id"])
        record: dict[str, Any] = {"parent": center["id"], "stencils": [p[0] for p in pairs],
            "probe_ids": [], "probe_steps": target._PROBE_STEPS,
            "control_scales": target._CONTROL_SCALES, "matrix": None,
            "singular_values": None, "rank": None, "condition_number": None, "rcond": 1e-10}
        self.jacobians.append(record)
        columns = []
        for j, (kind, a, b) in enumerate(pairs):
            probes = []
            for point in (a, b):
                entry = self.propose(point, "probe", center["id"])
                record["probe_ids"].append(entry["id"])
                probes.append(np.asarray(entry["scaled_residual"]))
            ra, rb = probes
            rc = np.asarray(center["scaled_residual"])
            numerator = (ra-rb if kind == "central" else
                         -3*rc+4*ra-rb if kind == "forward" else 3*rc-4*ra+rb)
            columns.append(numerator/(2*target._PROBE_STEPS[j])*target._CONTROL_SCALES[j])
        matrix = tuple(target._six(tuple(row), "Jacobian row") for row in np.asarray(columns).T)
        record["matrix"] = matrix
        try:
            singular = np.linalg.svd(matrix, compute_uv=False)
        except np.linalg.LinAlgError as exc:
            raise ValueError(f"D16 SVD failed: {exc}") from exc
        values = target._six(tuple(singular), "singular values")
        condition = values[0]/values[-1] if values[-1] > 0 else None
        record.update(singular_values=values, rank=sum(s > 1e-10*values[0] for s in values),
                      condition_number=condition if condition is not None and math.isfinite(condition) else None)
        self.budget.check()
        self.budget.completed_jacobian_batches += 1
        return matrix

    def qualify(self, entry: dict[str, Any]) -> None:
        self.report["selected_objective"] = entry["id"]
        repeated = self.propose(tuple(entry["controls"]), "frozen-repeat", entry["id"], tighter=True)
        differences = target._agreement(tuple(entry["final_state_si"]), tuple(repeated["final_state_si"]))
        agrees = all(a <= b for a, b in zip(differences, (1., .001, 1e-6)))
        self.report.update(agreement_differences_si=differences, agreement="pass" if agrees else "fail",
                           outcome="local-qualified" if agrees and repeated["closure"] == "pass" else "tighter-unqualified")
        self.budget.check()


def _correct_target(domain: target._TargetDomain, seed: target.Controls, retained: local.State7,
                    budget: _BoundBudget, report: dict[str, Any],
                    *, evaluate: target.Evaluator = target._evaluate_command) -> None:
    corrector = _Corrector(domain, seed, budget, report, evaluate)
    try:
        lower, upper = _bounds(domain)
        report["minimum_box_coast_s"] = domain.match_epoch_tdb_s-(domain.baseline.ignition_epoch_tdb_s+upper[0])-upper[1]
        scipy = import_module("scipy")
        if scipy.__version__ != "1.17.1":
            raise ValueError("D16 requires pinned Conda SciPy 1.17.1")
        least_squares = import_module("scipy.optimize").least_squares
        lo = tuple((v-s)/t for v, s, t in zip(lower, seed, target._CONTROL_SCALES))
        hi = tuple((v-s)/t for v, s, t in zip(upper, seed, target._CONTROL_SCALES))
        report.update(solver_settings=dict(_SETTINGS), solver_bounds=(lo, hi), seed_controls=seed,
                      control_scales=target._CONTROL_SCALES, residual_scales=target._RESIDUAL_SCALES)
        replay = corrector.propose(seed, "seed-replay", None)
        differences = target._agreement(tuple(replay["final_state_si"]), retained)
        report["baseline_replay_differences_si"] = differences
        if not all(a <= b for a, b in zip(differences, (1., .001, 1e-6))):
            report.update(outcome="baseline-replay-mismatch", baseline_replay="fail")
            return
        report["baseline_replay"] = "pass"
        if replay["closure"] == "pass":
            corrector.qualify(replay)
            return
        import numpy as np

        try:
            result = least_squares(corrector.objective, (0.,)*6, jac=corrector.jacobian,
                                   bounds=(lo, hi), **_SETTINGS)
        except _Closed as closed:
            report["solver_stop"] = "physical-closure-before-jacobian"
            corrector.qualify(closed.entry)
            return
        except (RuntimeError, np.linalg.LinAlgError) as exc:
            raise ValueError(f"D16 bounded solver failed: {exc}") from exc
        budget.check()
        final_x = corrector.controls(result.x)
        final = next((e for e in reversed(corrector.entries) if e["role"] == "objective"
                      and tuple(e["controls"]) == final_x), None)
        if final is None:
            raise ValueError("D16 solver result has no completed objective")
        if final["id"] not in corrector.accepted:
            corrector.accepted.append(final["id"])
            final["accepted_iterate"] = True
        report["solver_result"] = {"status": int(result.status), "message": str(result.message),
            "nfev": int(result.nfev), "njev": int(result.njev), "final_objective": final["id"],
            "coordinates": target._six(tuple(result.x), "solver result"),
            "active_mask": target._six(tuple(result.active_mask), "active bounds"),
            "gradient": target._six(tuple(result.grad), "solver gradient"),
            "optimality": physical._finite_float("solver optimality", result.optimality)}
        if result.status == 0:
            budget.limit("D16 SciPy objective-request limit reached")
        if result.status not in (1, 2, 3, 4):
            raise ValueError(f"D16 unexpected solver status {result.status}")
        report["outcome"] = "stationary-unclosed" if result.status == 1 else "stagnated-unclosed"
    except (ImportError, AttributeError, ValueError, TypeError, KeyError, OverflowError,
            TrajectoryRefinementError) as exc:
        report.update(outcome=("budget-exhausted" if budget.limit_reason else
                              exc.outcome if isinstance(exc, _DomainUnresolved) else "failed"),
                      reason=f"D16 stopped: {budget.limit_reason or exc}")


def _bind_steering(reference: dict[str, Any], study: dict[str, Any], steering: dict[str, Any],
                   window: tuple[float, float]) -> tuple[target._TargetDomain, local.State7]:
    domain = target._bind_references(reference, study, window)
    def normalized(value: Any) -> Any:
        return json.loads(json.dumps(value, allow_nan=False))
    if (steering["binding"] != normalized(asdict(domain))
            or any(steering[key] != study[key] for key in
                   ("candidate_id", "origin", "orientation", "units", "time_scale", "profiles",
                    "reference_sha256", "retained_lunar_resource", "kernels", "runtime_versions"))
            or steering["study_sha256"] != target._STUDY_SHA256
            or steering["model_id"] != target._MODEL or steering["best_accepted_proposal"] != 52
            or steering["baseline_replay"] != "pass" or steering["outcome"] != "not-converged"
            or steering["mission_qualified"] is not False or steering["agreement"] != "unavailable"
            or steering["tighter_evaluations"] != 0 or len(steering["proposals"]) != 53
            or steering["nominal_proposals"] != 53 or steering["propagation_evaluations"] != 53
            or steering["native_arc_propagations"] != 106 or steering["completed_arcs"] != 106):
        raise ValueError("D16 retained steering/model/resource binding mismatch")
    for i, entry in enumerate(steering["proposals"]):
        x = target._six(tuple(entry["controls"]), "retained controls")
        command = domain.command(x)
        checked = _validate_endpoint(domain, command, entry)
        if (entry["id"] != i or entry["profile"] != "nominal" or entry["outcome"] != "completed"
                or entry["command"] != normalized(asdict(command))
                or entry["match_epoch_tdb_s"] != domain.match_epoch_tdb_s
                or entry["cutoff_epoch_tdb_s"] != command.ignition_epoch_tdb_s+x[1]
                or any(entry[key] != normalized(value) for key, value in checked.items())):
            raise ValueError(f"D16 retained proposal {i} command/residual/mass mismatch")
    seed = steering["proposals"][52]
    if (tuple(seed["controls"]) != _SEED or seed["accepted"] is not True or seed["role"] != "trial"
            or steering["proposals"][0]["controls"] != list(domain.initial_controls)
            or steering["proposals"][0]["final_state_si"] != study["runs"][0]["final_state_si"]):
        raise ValueError("D16 explicit accepted warm-start mismatch")
    _bounds(domain)
    return domain, tuple(seed["final_state_si"])


def _run_bounded_local_targeting(reference_path: Path, study_path: Path, steering_path: Path,
                                 *, monotonic: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """Return finite evidence; caller saves a new file only in authorized D16.3."""
    budget = _BoundBudget("d0001-t0035", 300., monotonic, max_arcs_per_evaluation=2)
    report: dict[str, Any] = {"candidate_id": "d0001-t0035", "model_id": target._MODEL,
        "algorithm_id": "bound-aware-local-trf-v1", "origin": "Moon", "orientation": "J2000",
        "units": "SI", "time_scale": "TDB seconds since J2000", "mission_qualified": False,
        "outcome": "failed", "reason": None, "agreement": "unavailable", "binding": None,
        "source_sha256": None, "runtime_versions": None, "kernels": None,
        "baseline_replay": "unavailable", "proposals": [], "jacobians": [],
        "selected_objective": None, "best_objective": None, "solver_result": None,
        "solver_settings": dict(_SETTINGS), "solver_bounds": None,
        "baseline_replay_differences_si": None, "agreement_differences_si": None,
        "profiles": {"nominal": local._local_profile(False), "tighter": local._local_profile(True)},
        "omissions": "Earth/Sun, harmonics, SRP, relativity, Mars; no continuous safety or hardware qualification"}
    try:
        budget.check()
        paths = (reference_path, study_path, steering_path)
        expected = (local._REFERENCE_SHA256, target._STUDY_SHA256, _STEERING_SHA256)
        raw = [path.read_bytes() for path in paths]
        hashes = tuple(hashlib.sha256(data).hexdigest() for data in raw)
        report.update(reference_paths=tuple(str(p) for p in paths), reference_sha256=hashes)
        if hashes != expected:
            raise ValueError("D16 pinned 0104/0107/0110 SHA256 mismatch")
        reference, study, steering = (json.loads(data) for data in raw)
        search = reference["scenario"]["search"]
        window = tuple(local.ephemeris.utc_to_tdb(search[key]) for key in
                       ("departure_start_utc", "departure_end_utc"))
        budget.check()
        domain, retained = _bind_steering(reference, study, steering, window)
        root = Path(__file__).resolve().parents[2]
        names = ("bounded_local_targeting.py", "local_targeting.py", "local_burn.py",
                 "lunar_departure.py", "models.py", "trajectory.py", "ephemeris.py")
        report.update(binding=asdict(domain), seed_reference={"proposal": 52, "sha256": _STEERING_SHA256},
                      historical_source_sha256={"0107": study["source_sha256"], "0110": steering["source_sha256"]},
                      source_sha256={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                     for name in names},
                      environment_yml_sha256=hashlib.sha256((root/"environment.yml").read_bytes()).hexdigest(),
                      retained_lunar_resource=reference["lunar_field_provenance"],
                      kernels=local.ephemeris.kernel_metadata(),
                      runtime_versions={name: str(import_module(name).__version__)
                                        for name in ("numpy", "scipy", "tudatpy")})
        _correct_target(domain, _SEED, retained, budget, report)
        budget.check()
    except (ImportError, AttributeError, ValueError, TypeError, KeyError, OSError, OverflowError,
            EphemerisError, TrajectoryRefinementError) as exc:
        report.update(outcome=("budget-exhausted" if budget.limit_reason else
                              exc.outcome if isinstance(exc, _DomainUnresolved) else "failed"),
                      reason=f"D16 stopped: {budget.limit_reason or exc}")
    report.update(objective_requests=budget.objective_requests, jacobian_batches=budget.jacobian_batches,
        completed_jacobian_batches=budget.completed_jacobian_batches,
        control_attempts=budget.control_attempts, nominal_evaluations=budget.nominal_evaluations,
        propagation_evaluations=budget.propagation_evaluations, tighter_evaluations=budget.tighter_evaluations,
        native_arc_propagations=budget.native_arc_propagations, completed_arcs=budget.completed_arcs,
        elapsed_wall_s=budget._last_monotonic_s-(budget.deadline_monotonic_s-300.))
    json.dumps(report, allow_nan=False)
    return report
