"""Private D17 quadratic steering experiment; never mission qualification."""

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

from . import bounded_local_targeting as bounded, local_burn as local
from . import local_targeting as target, trajectory as physical
from .errors import EphemerisError, TrajectoryRefinementError
from .lunar_departure import _unit


_MODEL = "local-moon-point-mass-bezier-burn-v1"
_ALGORITHM = "bound-aware-bezier-trf-v1"
_BOUNDED_SHA256 = "417f4a33e6407a37e9a41caff29330557f39d7a3bbfc34e9b908cc1d5589cb89"
_SEED = (-1094.4910010491465, 5467.042096122668,
         .11712983121190776, .03964718570666498,
         -.24799059467100915, .04826945627805249,
         -.6131110205539261, .05689172684944001)
_CONTROL_SCALES = (300., 300., .1, .1, .1, .1, .1, .1)
_PROBE_STEPS = (1., 1., .001, .001, .001, .001, .001, .001)
_SETTINGS = dict(bounded._SETTINGS)


def _eight(values: target.Controls, name: str) -> target.Controls:
    if not isinstance(values, tuple) or len(values) != 8:
        raise ValueError(f"{name} requires eight immutable components")
    return tuple(physical._finite_float(name, value) for value in values)


def _linear_controls(x: target.Controls) -> target.Controls:
    x = _eight(x, "Bezier controls")
    return x[:4]+x[6:]


def _command(domain: target._TargetDomain, x: target.Controls) -> local._LocalCommand:
    x = _eight(x, "Bezier controls")
    if any(abs(value) > 1 for value in x[2:]):
        raise ValueError("Bezier command outside slope domain")
    return domain.command(_linear_controls(x))


def _bezier_direction(basis: target.Basis, x: target.Controls, relative_s: float) -> target.Vector3:
    x = _eight(x, "Bezier steering controls")
    tau = physical._positive_finite("burn duration_s", x[1])
    s = physical._finite_float("relative burn time_s", relative_s)/tau
    # Extend the SAME polynomial through RK trial stages; no clamp or midpoint event.
    p, q = ((1-s)**2*x[j]+2*s*(1-s)*x[j+2]+s*s*x[j+4] for j in (2, 3))
    return _unit(tuple(d+p*a+q*b for d, a, b in zip(*basis)))


def _bounds(domain: target._TargetDomain) -> tuple[target.Controls, target.Controls]:
    lower, upper = bounded._bounds(domain)
    return lower[:4]+(-1., -1.)+lower[4:], upper[:4]+(1., 1.)+upper[4:]


def _stencils(domain: target._TargetDomain, x: target.Controls) -> list[tuple[str, target.Controls, target.Controls]]:
    x = _eight(x, "Jacobian center")
    pairs = []
    for j, h in enumerate(_PROBE_STEPS):
        for name, offsets in (("central", (h, -h)), ("forward", (h, 2*h)), ("backward", (-h, -2*h))):
            points = [tuple(v+(offset if i == j else 0.) for i, v in enumerate(x)) for offset in offsets]
            try:
                for point in points:
                    _command(domain, point)
            except ValueError:
                continue
            pairs.append((name, points[0], points[1]))
            break
        else:
            raise bounded._DomainUnresolved("derivative-domain-unresolved", f"D17 coordinate {j}; fixed h={h}")
    return pairs


@dataclass(slots=True)
class _BezierBudget(target._TargetBudget):
    objective_requests: int = field(default=0, init=False)
    jacobian_batches: int = field(default=0, init=False)
    completed_jacobian_batches: int = field(default=0, init=False)
    nominal_evaluations: int = field(default=0, init=False)
    limit_reason: str | None = field(default=None, init=False)

    def limit(self, reason: str) -> NoReturn:
        self.limit_reason = reason
        raise bounded._Limit(reason)

    def _fail(self, operation: str, detail: str) -> NoReturn:
        if operation == "deadline" and detail == "shared deadline reached":
            self.limit(f"D17 deadline: {detail}")
        physical._RefinementBudget._fail(self, operation, detail)

    def ready(self) -> None:
        self.check()
        if (self.max_arcs_per_evaluation != 2 or self.tighter_evaluations
                or self.completed_arcs != self.native_arc_propagations
                or (self._active and self.native_arc_propagations != self._evaluation_start_arcs+2)):
            raise ValueError("D17 ordered complete burn/coast evaluations only; no retry")

    def begin_control(self) -> None:
        self.ready()
        self.control_attempts += 1

    def begin_objective(self) -> None:
        self.ready()
        if self.objective_requests >= 40:
            self.limit("D17 objective-request limit 40 reached")
        self.objective_requests += 1

    def begin_batch(self) -> None:
        self.ready()
        if self.jacobian_batches >= 40:
            self.limit("D17 Jacobian-batch limit 40 reached")
        if self.nominal_evaluations+16 > 681 or self.native_arc_propagations+32 > 1362:
            self.limit("D17 complete sixteen-probe batch cannot fit nominal budget")
        self.jacobian_batches += 1

    def begin_evaluation(self, tighter: bool) -> None:
        self.ready()
        if not isinstance(tighter, bool) or (tighter and self.nominal_evaluations == 0):
            raise ValueError("D17 evaluation requires nominal replay before tighter")
        if self.propagation_evaluations >= 682 or (not tighter and self.nominal_evaluations >= 681):
            self.limit("D17 evaluation ceiling reached; tighter pair remains reserved")
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
            raise ValueError("D17 native burn/coast order violated; no retry")
        if self.native_arc_propagations >= (1364 if self.tighter_evaluations else 1362):
            self.limit("D17 native-launch ceiling reached")
        self.native_arc_propagations += 1


def _evaluate_command(domain: target._TargetDomain, x: target.Controls, command: local._LocalCommand,
                      tighter: bool, budget: target._TargetBudget, evidence: dict[str, Any]) -> dict[str, Any]:
    cutoff, checks = local._native_local_arc(command, command.initial_state_si, 0.,
        command.cutoff_after_ignition_s, True, tighter, budget,
        direction_at_s=lambda at: _bezier_direction(domain.basis, x, at))
    evidence["cutoff_state_si"] = cutoff  # Preserve a completed burn on coast failure.
    if (abs(cutoff[6]-command.target_state_si[6]) > 1e-6
            or cutoff[6]*math.exp(-domain.arrival_delta_v_m_s/(
                physical.STANDARD_GRAVITY_M_S2*command.isp_s)) < command.dry_mass_kg):
        raise ValueError("D17 propagated cutoff/arrival mass disagreement")
    final, coast_checks = local._native_local_arc(command, cutoff,
        command.cutoff_after_ignition_s, command.match_after_ignition_s, False, tighter, budget)
    return {"cutoff_state_si": cutoff, "final_state_si": final,
            "checked_saved_states": checks+coast_checks}


class _Corrector:
    def __init__(self, domain: target._TargetDomain, seed: target.Controls,
                 budget: _BezierBudget, report: dict[str, Any], evaluate: target.Evaluator) -> None:
        self.domain, self.seed, self.budget = domain, _eight(seed, "seed"), budget
        self.report, self.evaluate = report, evaluate
        self.entries: list[dict[str, Any]] = []
        self.jacobians: list[dict[str, Any]] = []
        self.accepted: list[int] = []
        self.center: dict[str, Any] | None = None
        report.update(proposals=self.entries, jacobians=self.jacobians,
            accepted_iterates=self.accepted, best_objective=None, selected_objective=None,
            baseline_replay="unavailable", embedding_replay="unavailable", agreement="unavailable",
            baseline_replay_differences_si=None, embedding_replay_differences_si=None,
            agreement_differences_si=None, solver_result=None,
            outcome="failed", reason=None, mission_qualified=False)

    def controls(self, y: Any) -> target.Controls:
        values = _eight(tuple(y), "solver coordinates")
        return _eight(tuple(a+t*b for a, t, b in zip(self.seed, _CONTROL_SCALES, values)), "physical controls")

    def propose(self, x: target.Controls, role: str, parent: int | None,
                *, tighter: bool = False, reference_evaluate: target.Evaluator | None = None) -> dict[str, Any]:
        reference = role == "two-node-reference-replay"
        x = target._six(x, "reference controls") if reference else _eight(x, "Bezier controls")
        self.budget.begin_control()
        entry: dict[str, Any] = {"id": len(self.entries), "role": role, "parent": parent,
            "controls": x, "control_units": ("s", "s")+("1",)*(len(x)-2),
            "model_id": target._MODEL if reference else _MODEL,
            "profile": "tighter" if tighter else "nominal", "cache_hit": False,
            "outcome": "failed", "reason": "not completed", "command": None,
            "cutoff_state_si": None, "final_state_si": None, "residual_si": None,
            "scaled_residual": None, "closure": "unavailable", "score": None,
            "accepted_iterate": False, "match_epoch_tdb_s": self.domain.match_epoch_tdb_s,
            "cutoff_epoch_tdb_s": None, "steering_rate_upper_rad_s": None,
            "cutoff_mass_error_kg": None, "post_arrival_reserve_kg": None}
        self.entries.append(entry)
        try:
            command = self.domain.command(x) if reference else _command(self.domain, x)
            rate = (math.hypot(x[4]-x[2], x[5]-x[3]) if reference else
                    2*max(math.hypot(x[4]-x[2], x[5]-x[3]), math.hypot(x[6]-x[4], x[7]-x[5]))) / x[1]
            entry.update(command=asdict(command), steering_rate_upper_rad_s=rate,
                         cutoff_epoch_tdb_s=command.ignition_epoch_tdb_s+x[1])
            self.budget.begin_evaluation(tighter)
            evaluator = reference_evaluate if reference else self.evaluate
            if evaluator is None:
                raise ValueError("D17 old-model replay requires its separate evaluator")
            result = evaluator(self.domain, x, command, tighter, self.budget, entry)
            self.budget.check()
            if (self.budget.native_arc_propagations != self.budget._evaluation_start_arcs+2
                    or self.budget.completed_arcs != self.budget.native_arc_propagations):
                raise ValueError("D17 incomplete burn/coast evaluation")
            entry.update(result, **bounded._validate_endpoint(self.domain, command, result),
                         outcome="completed", reason=None)
        except (ValueError, TypeError, KeyError, OverflowError, TrajectoryRefinementError) as exc:
            entry["reason"] = str(exc)
            raise
        if role in ("bezier-seed-replay", "objective"):
            best = self.report["best_objective"]
            if best is None or entry["score"] < self.entries[best]["score"]:
                self.report["best_objective"] = entry["id"]
        return entry

    def objective(self, y: Any) -> target.Controls:
        self.budget.begin_objective()
        x = self.controls(y)
        if self.budget.objective_requests == 1:
            if (x != self.seed or tuple(y) != (0.,)*8 or len(self.entries) != 2
                    or self.entries[1]["role"] != "bezier-seed-replay"
                    or self.entries[1]["outcome"] != "completed"):
                raise ValueError("D17 initial solver request changed the replayed seed")
            entry = dict(self.entries[1], id=len(self.entries), role="objective", parent=1,
                         cache_hit=True, cache_source=1, accepted_iterate=False)
            self.entries.append(entry)
        else:
            entry = self.propose(x, "objective", self.accepted[-1] if self.accepted else 1)
        self.center = entry
        if entry["closure"] == "pass":
            raise bounded._Closed(entry)
        return tuple(entry["scaled_residual"])

    def jacobian(self, y: Any) -> tuple[target.Controls, ...]:
        import numpy as np

        x = self.controls(y)
        center = self.center
        if center is None or x != tuple(center["controls"]):
            raise ValueError("D17 Jacobian requires its completed objective center")
        pairs = _stencils(self.domain, x)  # Preflight all sixteen before ANY launch.
        self.budget.begin_batch()
        center["accepted_iterate"] = True
        if not self.accepted or self.accepted[-1] != center["id"]:
            self.accepted.append(center["id"])
        lower, upper = _bounds(self.domain)
        free = tuple(lo < v < hi for lo, v, hi in zip(lower, x, upper))
        record: dict[str, Any] = {"parent": center["id"], "stencils": [p[0] for p in pairs],
            "probe_ids": [], "probe_steps": _PROBE_STEPS, "control_scales": _CONTROL_SCALES,
            "matrix": None, "singular_values": None, "rank": None, "condition_number": None,
            "rcond": 1e-10, "gradient": None, "gradient_parent": center["id"],
            "face_free_mask": free, "free_singular_values": None, "free_rank": None,
            "bound_margins": {"lower": tuple(v-lo for v, lo in zip(x, lower)),
                              "upper": tuple(hi-v for v, hi in zip(x, upper))}}
        self.jacobians.append(record)
        columns = []
        for j, (kind, a, b) in enumerate(pairs):
            probes = []
            for point in (a, b):
                record["probe_ids"].append(len(self.entries))
                entry = self.propose(point, "probe", center["id"])
                probes.append(np.asarray(entry["scaled_residual"]))
            ra, rb = probes
            rc = np.asarray(center["scaled_residual"])
            numerator = (ra-rb if kind == "central" else
                         -3*rc+4*ra-rb if kind == "forward" else 3*rc-4*ra+rb)
            columns.append(numerator/(2*_PROBE_STEPS[j])*_CONTROL_SCALES[j])
        matrix = tuple(_eight(tuple(row), "Jacobian row") for row in np.asarray(columns).T)
        record["matrix"] = matrix
        try:
            singular = target._six(tuple(np.linalg.svd(matrix, compute_uv=False)), "singular values")
            free_singular = tuple(physical._finite_float("free singular value", v)
                                  for v in np.linalg.svd(np.asarray(matrix)[:, free], compute_uv=False))
        except np.linalg.LinAlgError as exc:
            raise ValueError(f"D17 SVD failed: {exc}") from exc
        condition = singular[0]/singular[-1] if singular[-1] > 0 else None
        record.update(singular_values=singular, rank=sum(s > 1e-10*singular[0] for s in singular),
            condition_number=condition if condition is not None and math.isfinite(condition) else None,
            gradient=_eight(tuple(np.asarray(matrix).T@np.asarray(center["scaled_residual"])), "measured gradient"),
            free_singular_values=free_singular,
            free_rank=sum(s > 1e-10*free_singular[0] for s in free_singular) if free_singular else 0)
        self.budget.check()
        self.budget.completed_jacobian_batches += 1
        return matrix

    def qualify(self, entry: dict[str, Any]) -> None:
        if (entry["role"] not in ("bezier-seed-replay", "objective") or entry["closure"] != "pass"
                or entry["outcome"] != "completed"):
            raise ValueError("D17 qualification requires a closed eligible Bezier objective")
        self.report["selected_objective"] = entry["id"]
        repeated = self.propose(tuple(entry["controls"]), "frozen-repeat", entry["id"], tighter=True)
        differences = target._agreement(tuple(entry["final_state_si"]), tuple(repeated["final_state_si"]))
        agrees = all(a <= b for a, b in zip(differences, (1., .001, 1e-6)))
        self.report.update(agreement_differences_si=differences, agreement="pass" if agrees else "fail",
            outcome="local-qualified" if agrees and repeated["closure"] == "pass" else "tighter-unqualified")
        self.budget.check()


def _correct_target(domain: target._TargetDomain, seed: target.Controls, retained: local.State7,
                    budget: _BezierBudget, report: dict[str, Any],
                    *, evaluate: target.Evaluator = _evaluate_command,
                    reference_evaluate: target.Evaluator = target._evaluate_command) -> None:
    corrector = _Corrector(domain, seed, budget, report, evaluate)
    try:
        lower, upper = _bounds(domain)
        report["minimum_box_coast_s"] = domain.match_epoch_tdb_s-(domain.baseline.ignition_epoch_tdb_s+upper[0])-upper[1]
        scipy = import_module("scipy")
        if scipy.__version__ != "1.17.1":
            raise ValueError("D17 requires pinned Conda SciPy 1.17.1")
        least_squares = import_module("scipy.optimize").least_squares
        lo = tuple((v-s)/t for v, s, t in zip(lower, seed, _CONTROL_SCALES))
        hi = tuple((v-s)/t for v, s, t in zip(upper, seed, _CONTROL_SCALES))
        report.update(solver_settings=dict(_SETTINGS), solver_bounds=(lo, hi), seed_controls=seed,
                      control_scales=_CONTROL_SCALES, residual_scales=target._RESIDUAL_SCALES)
        reference = corrector.propose(_linear_controls(seed), "two-node-reference-replay", None,
                                      reference_evaluate=reference_evaluate)
        differences = target._agreement(tuple(reference["final_state_si"]), retained)
        report["baseline_replay_differences_si"] = differences
        if not all(a <= b for a, b in zip(differences, (1., .001, 1e-6))):
            report.update(outcome="baseline-replay-mismatch", baseline_replay="fail")
            return
        report["baseline_replay"] = "pass"
        replay = corrector.propose(seed, "bezier-seed-replay", 0)
        comparisons = {"fresh_reference": target._agreement(tuple(replay["final_state_si"]), tuple(reference["final_state_si"])),
                       "retained_reference": target._agreement(tuple(replay["final_state_si"]), retained)}
        report["embedding_replay_differences_si"] = comparisons
        if not all(all(a <= b for a, b in zip(d, (1., .001, 1e-6))) for d in comparisons.values()):
            report.update(outcome="embedding-replay-mismatch", embedding_replay="fail", best_objective=None)
            return
        report["embedding_replay"] = "pass"
        if replay["closure"] == "pass":
            corrector.qualify(replay)
            return
        import numpy as np

        try:
            result = least_squares(corrector.objective, (0.,)*8, jac=corrector.jacobian,
                                   bounds=(lo, hi), **_SETTINGS)
        except bounded._Closed as closed:
            report["solver_stop"] = "physical-closure-before-jacobian"
            corrector.qualify(closed.entry)
            return
        except (RuntimeError, np.linalg.LinAlgError) as exc:
            raise ValueError(f"D17 bounded solver failed: {exc}") from exc
        budget.check()
        final_x = corrector.controls(result.x)
        final = next((e for e in reversed(corrector.entries) if e["role"] == "objective"
                      and tuple(e["controls"]) == final_x and e["outcome"] == "completed"), None)
        if final is None:
            raise ValueError("D17 solver result has no completed objective")
        if final["id"] not in corrector.accepted:
            corrector.accepted.append(final["id"])
            final["accepted_iterate"] = True
        report["solver_result"] = {"status": int(result.status), "message": str(result.message),
            "nfev": int(result.nfev), "njev": int(result.njev), "final_objective": final["id"],
            "coordinates": _eight(tuple(result.x), "solver result"),
            "active_mask": _eight(tuple(result.active_mask), "active bounds"),
            "gradient": _eight(tuple(result.grad), "solver gradient"),
            "optimality": physical._finite_float("solver optimality", result.optimality)}
        if result.status == 0:
            budget.limit("D17 SciPy objective-request limit reached")
        if result.status not in (1, 2, 3, 4):
            raise ValueError(f"D17 unexpected solver status {result.status}")
        report["outcome"] = "stationary-unclosed" if result.status == 1 else "stagnated-unclosed"
    except (ImportError, AttributeError, ValueError, TypeError, KeyError, OverflowError,
            TrajectoryRefinementError) as exc:
        report.update(outcome=("budget-exhausted" if budget.limit_reason else
                              exc.outcome if isinstance(exc, bounded._DomainUnresolved) else "failed"),
                      reason=f"D17 stopped: {budget.limit_reason or exc}")


def _bind_references(reference: dict[str, Any], study: dict[str, Any], steering: dict[str, Any],
                     bounded_report: dict[str, Any], window: tuple[float, float]) -> tuple[target._TargetDomain, local.State7]:
    domain, _ = bounded._bind_steering(reference, study, steering, window)
    def normalized(value: Any) -> Any:
        return json.loads(json.dumps(value, allow_nan=False))
    expected_hashes = [local._REFERENCE_SHA256, target._STUDY_SHA256, bounded._STEERING_SHA256]
    if (bounded_report["binding"] != normalized(asdict(domain))
            or any(bounded_report[key] != steering[key] for key in
                   ("candidate_id", "origin", "orientation", "units", "time_scale", "profiles",
                    "retained_lunar_resource", "kernels"))
            or bounded_report["runtime_versions"] != {**steering["runtime_versions"], "scipy": "1.17.1"}
            or bounded_report["reference_sha256"] != expected_hashes
            or bounded_report["model_id"] != target._MODEL
            or bounded_report["algorithm_id"] != "bound-aware-local-trf-v1"
            or bounded_report["solver_settings"] != _SETTINGS
            or bounded_report["baseline_replay"] != "pass"
            or bounded_report["mission_qualified"] is not False
            or bounded_report["outcome"] != "budget-exhausted"
            or bounded_report["agreement"] != "unavailable"
            or bounded_report["tighter_evaluations"] != 0
            or bounded_report["solver_result"] is not None
            or bounded_report["best_objective"] != 262
            or len(bounded_report["proposals"]) != 263
            or bounded_report["nominal_evaluations"] != 262
            or bounded_report["propagation_evaluations"] != 262
            or bounded_report["native_arc_propagations"] != 524
            or bounded_report["completed_arcs"] != 524):
        raise ValueError("D17 retained bounded/model/resource binding mismatch")
    for i, entry in enumerate(bounded_report["proposals"]):
        x = target._six(tuple(entry["controls"]), "retained controls")
        command = domain.command(x)
        checked = bounded._validate_endpoint(domain, command, entry)
        if (entry["id"] != i or entry["profile"] != "nominal" or entry["outcome"] != "completed"
                or entry["command"] != normalized(asdict(command))
                or entry["match_epoch_tdb_s"] != domain.match_epoch_tdb_s
                or entry["cutoff_epoch_tdb_s"] != command.ignition_epoch_tdb_s+x[1]
                or any(entry[key] != normalized(value) for key, value in checked.items())):
            raise ValueError(f"D17 retained proposal {i} command/residual/mass mismatch")
    seed = bounded_report["proposals"][158]
    if (tuple(seed["controls"]) != _linear_controls(_SEED) or seed["accepted_iterate"] is not True
            or seed["role"] != "objective" or seed["cache_hit"] is not False
            or 158 not in bounded_report["accepted_iterates"]
            or _SEED[4:6] != tuple((a+b)/2 for a, b in zip(_SEED[2:4], _SEED[6:8]))):
        raise ValueError("D17 explicit accepted ID 158/embedded seed mismatch")
    _bounds(domain)
    _command(domain, _SEED)
    return domain, tuple(seed["final_state_si"])


def _run_bezier_local_targeting(reference_path: Path, study_path: Path, steering_path: Path,
                                bounded_path: Path, *, monotonic: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """Return finite evidence; retained native invocation belongs to authorized D17.3."""
    budget = _BezierBudget("d0001-t0035", 300., monotonic, max_arcs_per_evaluation=2)
    report: dict[str, Any] = {"candidate_id": "d0001-t0035", "model_id": _MODEL,
        "algorithm_id": _ALGORITHM, "reference_model_id": target._MODEL,
        "origin": "Moon", "orientation": "J2000", "units": "SI",
        "time_scale": "TDB seconds since J2000", "mission_qualified": False,
        "outcome": "failed", "reason": None, "agreement": "unavailable", "binding": None,
        "source_sha256": None, "runtime_versions": None, "kernels": None,
        "baseline_replay": "unavailable", "embedding_replay": "unavailable",
        "proposals": [], "jacobians": [], "accepted_iterates": [],
        "selected_objective": None, "best_objective": None, "solver_result": None,
        "solver_settings": dict(_SETTINGS), "solver_bounds": None,
        "baseline_replay_differences_si": None, "embedding_replay_differences_si": None,
        "agreement_differences_si": None,
        "profiles": {"nominal": local._local_profile(False), "tighter": local._local_profile(True)},
        "omissions": "Earth/Sun, harmonics, SRP, relativity, Mars; no continuous safety or hardware qualification"}
    try:
        budget.check()
        paths = (reference_path, study_path, steering_path, bounded_path)
        expected = (local._REFERENCE_SHA256, target._STUDY_SHA256, bounded._STEERING_SHA256, _BOUNDED_SHA256)
        raw = [path.read_bytes() for path in paths]
        hashes = tuple(hashlib.sha256(data).hexdigest() for data in raw)
        report.update(reference_paths=tuple(str(p) for p in paths), reference_sha256=hashes)
        if hashes != expected:
            raise ValueError("D17 pinned 0104/0107/0110/0113 SHA256 mismatch")
        reference, study, steering, bounded_report = (json.loads(data) for data in raw)
        search = reference["scenario"]["search"]
        window = tuple(local.ephemeris.utc_to_tdb(search[key]) for key in
                       ("departure_start_utc", "departure_end_utc"))
        budget.check()
        domain, retained = _bind_references(reference, study, steering, bounded_report, window)
        root = Path(__file__).resolve().parents[2]
        names = ("bezier_local_targeting.py", "bounded_local_targeting.py", "local_targeting.py",
                 "local_burn.py", "lunar_departure.py", "models.py", "trajectory.py", "ephemeris.py")
        report.update(binding=asdict(domain), seed_reference={"proposal": 158, "sha256": _BOUNDED_SHA256},
            historical_source_sha256={"0107": study["source_sha256"], "0110": steering["source_sha256"],
                                      "0113": bounded_report["source_sha256"]},
            source_sha256={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in names},
            environment_yml_sha256=hashlib.sha256((root/"environment.yml").read_bytes()).hexdigest(),
            retained_lunar_resource=reference["lunar_field_provenance"],
            kernels=local.ephemeris.kernel_metadata(),
            runtime_versions={name: str(import_module(name).__version__) for name in ("numpy", "scipy", "tudatpy")})
        _correct_target(domain, _SEED, retained, budget, report)
        budget.check()
    except (ImportError, AttributeError, ValueError, TypeError, KeyError, OSError, OverflowError,
            EphemerisError, TrajectoryRefinementError) as exc:
        report.update(outcome=("budget-exhausted" if budget.limit_reason else
                              exc.outcome if isinstance(exc, bounded._DomainUnresolved) else "failed"),
                      reason=f"D17 stopped: {budget.limit_reason or exc}")
    report.update(objective_requests=budget.objective_requests, jacobian_batches=budget.jacobian_batches,
        completed_jacobian_batches=budget.completed_jacobian_batches,
        control_attempts=budget.control_attempts, nominal_evaluations=budget.nominal_evaluations,
        propagation_evaluations=budget.propagation_evaluations, tighter_evaluations=budget.tighter_evaluations,
        native_arc_propagations=budget.native_arc_propagations, completed_arcs=budget.completed_arcs,
        elapsed_wall_s=budget._last_monotonic_s-(budget.deadline_monotonic_s-300.))
    json.dumps(report, allow_nan=False)
    return report
