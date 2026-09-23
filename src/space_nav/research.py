"""Research-only reports and accounting; no strict-M3 qualification."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
from typing import Any, Literal

from .models import (
    _BOUNDARY_DIFFERENCE_LABELS,
    _CANDIDATE_ID_PATTERN,
    _PHYSICAL_FORCE_MODEL_ID,
    _finite_number,
    _json_real,
    _nonempty_text,
    _normalized_utc,
    FiniteBurnRecord,
    Scenario,
    TrajectoryBoundaryDifference,
    TrajectoryBoundaryState,
)
from .trajectory import _RefinementBudget, _direction_tnw_from_angles


_COVERAGE_LIMITATION = (
    "Only the declared evaluated states/events were checked. Undetected "
    "between-check impacts, small bodies and debris are not excluded. "
    "Numerical agreement is not target closure, real-world accuracy or safety."
)


def _canonical_object(name: str, value: str) -> str:
    """Freeze finite JSON metadata as text; emit fresh objects on serialization."""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be JSON object text")
    parsed = json.loads(value)
    if not isinstance(parsed, dict) or not parsed:
        raise ValueError(f"{name} must contain a nonempty object")
    return json.dumps(parsed, sort_keys=True, allow_nan=False)


@dataclass(frozen=True, slots=True)
class ResearchProgress:
    """Immutable accounting snapshot, not a completed scientific report.

    Counts are dimensionless. A completed arc means the caller accepted its
    completion checks, not that continuous collision safety was established.
    """

    attempted_arcs: int
    completed_arcs: int
    continuous_safety_verified: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        for name in ("attempted_arcs", "completed_arcs"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
        if not 0 <= self.completed_arcs <= self.attempted_arcs <= 6:
            raise ValueError("arc counts must satisfy 0 <= completed <= attempted <= 6")


@dataclass(frozen=True, slots=True, kw_only=True)
class ResearchRun:
    """One integration profile: diagnostics, or four completed SI boundaries.

    Epochs are TDB seconds since J2000, positions/velocities SSB/J2000.
    Aborted/unavailable runs retain diagnostics, never a partial endpoint.
    Metadata strings are immutable finite JSON objects, not live mappings.
    """

    profile: Literal["nominal", "tighter"]
    outcome: Literal["completed", "aborted", "unavailable"]
    reason: str | None
    progress: ResearchProgress
    checked_state_count: int
    check_coverage: str
    integrator_settings_json: str | None = None
    boundaries: tuple[TrajectoryBoundaryState, ...] = ()
    boundary_masses_kg: tuple[float, ...] = ()
    burns: tuple[FiniteBurnRecord, ...] = ()
    target_state: TrajectoryBoundaryState | None = None
    continuous_safety_verified: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.profile not in ("nominal", "tighter"):
            raise ValueError("profile must be nominal or tighter")
        if self.outcome not in ("completed", "aborted", "unavailable"):
            raise ValueError("outcome must be completed, aborted or unavailable")
        if not isinstance(self.progress, ResearchProgress):
            raise ValueError("progress must be ResearchProgress")
        attempted, completed = (
            self.progress.attempted_arcs,
            self.progress.completed_arcs,
        )
        if attempted > 3 or attempted - completed > 1:
            raise ValueError("one run permits three ordered arcs and no retry")
        if (
            isinstance(self.checked_state_count, bool)
            or not isinstance(self.checked_state_count, int)
            or self.checked_state_count < 0
        ):
            raise ValueError("checked_state_count must be a nonnegative integer")
        _nonempty_text("check_coverage", self.check_coverage)
        if self.integrator_settings_json is not None:
            object.__setattr__(
                self,
                "integrator_settings_json",
                _canonical_object(
                    "integrator_settings_json",
                    self.integrator_settings_json,
                ),
            )
        elif attempted:
            raise ValueError("attempted arcs require integrator settings")
        for name, item_type in (
            ("boundaries", TrajectoryBoundaryState),
            ("burns", FiniteBurnRecord),
        ):
            items = getattr(self, name)
            if not isinstance(items, tuple) or not all(
                isinstance(v, item_type) for v in items
            ):
                raise ValueError(f"{name} must be a tuple of {item_type.__name__}")
        if not isinstance(self.boundary_masses_kg, tuple):
            raise ValueError("boundary_masses_kg must be a tuple")
        if self.outcome != "completed":
            _nonempty_text("reason", self.reason)
            if (
                self.boundaries
                or self.boundary_masses_kg
                or self.burns
                or self.target_state is not None
            ):
                raise ValueError("incomplete runs cannot contain trajectory values")
            if completed == 3 or (
                self.outcome == "unavailable"
                and (attempted or self.checked_state_count)
            ):
                raise ValueError("outcome conflicts with work counts")
            return
        if self.reason is not None or completed != 3 or self.checked_state_count < 4:
            raise ValueError(
                "completed runs require three arcs, checked boundaries and no failure reason"
            )
        if tuple(s.label for s in self.boundaries) != _BOUNDARY_DIFFERENCE_LABELS:
            raise ValueError("boundaries must contain four states in fixed order")
        epochs = tuple(s.epoch_tdb_s for s in self.boundaries)
        utc = tuple(
            _normalized_utc("boundary epoch", s.epoch_utc) for s in self.boundaries
        )
        if any(a >= b for a, b in zip(epochs, epochs[1:])) or any(
            a >= b for a, b in zip(utc, utc[1:])
        ):
            raise ValueError("boundary epochs must increase strictly")
        if len(self.boundary_masses_kg) != 4:
            raise ValueError("four boundary masses required")
        for mass in self.boundary_masses_kg:
            _finite_number("boundary mass kg", mass)
            if mass <= 0:
                raise ValueError("boundary mass must be positive")
        if tuple(b.burn_id for b in self.burns) != ("departure", "arrival"):
            raise ValueError("two burns required in departure/arrival order")
        departure, arrival = self.burns
        if epochs != (
            departure.start_epoch_tdb_s,
            departure.end_epoch_tdb_s,
            arrival.start_epoch_tdb_s,
            arrival.end_epoch_tdb_s,
        ):
            raise ValueError("burn epochs must match boundaries exactly")
        if self.boundary_masses_kg != (
            departure.initial_mass_kg,
            departure.final_mass_kg,
            arrival.initial_mass_kg,
            arrival.final_mass_kg,
        ):
            raise ValueError("burn masses must match boundary masses")
        if departure.final_mass_kg != arrival.initial_mass_kg:
            raise ValueError("coast mass must be unchanged")
        if not isinstance(self.target_state, TrajectoryBoundaryState):
            raise ValueError("completed run requires target_state")
        if (
            self.target_state.epoch_tdb_s != epochs[-1]
            or self.target_state.epoch_utc != self.boundaries[-1].epoch_utc
        ):
            raise ValueError("target epoch must match arrival cutoff")
        # Validate derived norms too: finite coordinates can overflow on subtraction.
        for value in self.terminal_errors:
            _finite_number("terminal residual", value, nonnegative=True)

    @property
    def terminal_errors(self) -> tuple[float, float] | None:
        """Position (m) and velocity (m/s) miss; absent for incomplete runs."""
        if self.outcome != "completed":
            return None
        assert self.target_state is not None
        terminal = self.boundaries[-1]
        return (
            math.dist(terminal.position_m, self.target_state.position_m),
            math.dist(terminal.velocity_m_s, self.target_state.velocity_m_s),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ResearchReport:
    """Separate research evidence, never a PhysicalTrajectoryResult.

    Seed controls: departure azimuth/elevation (rad), duration (s), then arrival.
    The caller supplies a loader-validated Scenario and verified provenance.
    This contract checks internal consistency, not truth of resource metadata.
    """

    candidate_id: str
    scenario: Scenario
    seed_controls: tuple[float, ...] | None
    provenance_json: str | None
    nominal: ResearchRun
    tighter: ResearchRun
    elapsed_wall_s: float
    research_only: bool = field(default=True, init=False)
    continuous_safety_verified: bool = field(default=False, init=False)
    force_model_id: str = field(default=_PHYSICAL_FORCE_MODEL_ID, init=False)
    _scenario_json: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(
            self.candidate_id, str
        ) or not _CANDIDATE_ID_PATTERN.fullmatch(self.candidate_id):
            raise ValueError("candidate_id must match dIIII-tJJJJ")
        if not isinstance(self.scenario, Scenario):
            raise ValueError("scenario must be a normalized Scenario")
        object.__setattr__(
            self,
            "_scenario_json",
            json.dumps(
                self.scenario.to_dict(),
                sort_keys=True,
                allow_nan=False,
                default=_json_real,
            ),
        )
        _finite_number("elapsed_wall_s", self.elapsed_wall_s, nonnegative=True)
        if self.provenance_json is not None:
            object.__setattr__(
                self,
                "provenance_json",
                _canonical_object("provenance_json", self.provenance_json),
            )
        for run, profile in ((self.nominal, "nominal"), (self.tighter, "tighter")):
            if not isinstance(run, ResearchRun) or run.profile != profile:
                raise ValueError(f"{profile} must contain its matching ResearchRun")
        if (
            self.nominal.outcome != "completed"
            and self.tighter.outcome != "unavailable"
        ):
            raise ValueError("tighter run requires completed nominal run")
        if self.seed_controls is not None:
            if (
                not isinstance(self.seed_controls, tuple)
                or len(self.seed_controls) != 6
            ):
                raise ValueError("seed_controls must contain six values")
            for value in self.seed_controls:
                _finite_number("seed_controls", value)
            for offset in (0, 3):
                azimuth, elevation, duration = self.seed_controls[offset : offset + 3]
                if (
                    not -math.pi <= azimuth < math.pi
                    or abs(elevation) > math.pi / 2
                    or duration <= 0
                ):
                    raise ValueError(
                        "seed_controls must be canonical angles and positive durations"
                    )
        if self.progress.attempted_arcs and (
            self.seed_controls is None or self.provenance_json is None
        ):
            raise ValueError("attempted propagation requires controls and provenance")
        for run in (self.nominal, self.tighter):
            if run.outcome == "completed":
                self._validate_completed_run(run)
        if self.tighter.outcome == "completed":
            if (
                self.nominal.boundaries[0] != self.tighter.boundaries[0]
                or self.nominal.target_state != self.tighter.target_state
                or tuple(s.epoch_tdb_s for s in self.nominal.boundaries)
                != tuple(s.epoch_tdb_s for s in self.tighter.boundaries)
                or tuple(s.epoch_utc for s in self.nominal.boundaries)
                != tuple(s.epoch_utc for s in self.tighter.boundaries)
            ):
                raise ValueError(
                    "profiles must share initial state, target and boundary epochs"
                )
            for nominal_burn, tighter_burn in zip(
                self.nominal.burns, self.tighter.burns
            ):
                if nominal_burn.direction_tnw != tighter_burn.direction_tnw:
                    raise ValueError("profiles must use identical burn directions")
        # Difference records reject overflow as well as malformed magnitudes.
        self.integration_differences

    def _validate_completed_run(self, run: ResearchRun) -> None:
        spacecraft = self.scenario.spacecraft
        if run.boundary_masses_kg[0] != spacecraft.initial_mass_kg:
            raise ValueError("initial mass must match scenario")
        if any(mass <= spacecraft.dry_mass_kg for mass in run.boundary_masses_kg):
            raise ValueError("completed boundaries must remain above dry mass")
        assert self.seed_controls is not None
        for offset, burn in zip((0, 3), run.burns):
            azimuth, elevation, duration = self.seed_controls[offset : offset + 3]
            if (
                burn.thrust_n != spacecraft.max_thrust_n
                or burn.isp_s != spacecraft.isp_s
                or math.dist(
                    burn.direction_tnw, _direction_tnw_from_angles(azimuth, elevation)
                )
                > 1e-12
                or not math.isclose(
                    burn.end_epoch_tdb_s - burn.start_epoch_tdb_s,
                    duration,
                    rel_tol=0.0,
                    abs_tol=1e-6,
                )
            ):
                raise ValueError(
                    "burns must use fixed seed commands and scenario engine"
                )

    @property
    def progress(self) -> ResearchProgress:
        return ResearchProgress(
            self.nominal.progress.attempted_arcs + self.tighter.progress.attempted_arcs,
            self.nominal.progress.completed_arcs + self.tighter.progress.completed_arcs,
        )

    @property
    def integration_differences(self) -> tuple[TrajectoryBoundaryDifference, ...]:
        if self.tighter.outcome != "completed":
            return ()
        return tuple(
            TrajectoryBoundaryDifference(
                label=left.label,  # type: ignore[arg-type] -- ResearchRun enforces fixed labels
                position_difference_m=math.dist(left.position_m, right.position_m),
                velocity_difference_m_s=math.dist(
                    left.velocity_m_s, right.velocity_m_s
                ),
                mass_difference_kg=abs(lm - rm),
            )
            for left, right, lm, rm in zip(
                self.nominal.boundaries,
                self.tighter.boundaries,
                self.nominal.boundary_masses_kg,
                self.tighter.boundary_masses_kg,
            )
        )

    @property
    def numerical_agreement(self) -> bool | None:
        differences = self.integration_differences
        if not differences:
            return None
        return all(
            d.position_difference_m <= 10.0
            and d.velocity_difference_m_s <= 0.0001
            and d.mass_difference_kg <= 0.000001
            for d in differences
        )

    @property
    def outcome(self) -> Literal["completed", "aborted", "unavailable"]:
        """Completion describes both integrations, never target closure."""
        if self.nominal.outcome == self.tighter.outcome == "completed":
            return "completed"
        if "aborted" in (self.nominal.outcome, self.tighter.outcome):
            return "aborted"
        return "unavailable"

    @property
    def comparison_reason(self) -> str | None:
        if self.numerical_agreement is None:
            return self.tighter.reason
        if not self.numerical_agreement:
            return "integration-threshold-exceeded"
        return None

    def to_dict(self) -> dict[str, Any]:
        """Detached finite JSON values; wall time separate from scientific data."""
        data = asdict(self)
        del data["elapsed_wall_s"]
        del data["_scenario_json"]
        data["scenario"] = json.loads(self._scenario_json)
        provenance = data.pop("provenance_json")
        data["provenance"] = None if provenance is None else json.loads(provenance)
        controls = data.pop("seed_controls")
        data["seed_commands"] = (
            None
            if controls is None
            else dict(
                zip(
                    (
                        "departure_azimuth_rad",
                        "departure_elevation_rad",
                        "departure_duration_s",
                        "arrival_azimuth_rad",
                        "arrival_elevation_rad",
                        "arrival_duration_s",
                    ),
                    controls,
                )
            )
        )
        data.update(
            origin="SSB",
            orientation="J2000",
            time_scale="TDB seconds since J2000",
            units="SI",
            outcome=self.outcome,
            coverage_limitation=_COVERAGE_LIMITATION,
            numerical_agreement=self.numerical_agreement,
            comparison_reason=self.comparison_reason,
            integration_differences=[asdict(d) for d in self.integration_differences],
            progress=asdict(self.progress),
        )
        for run in (self.nominal, self.tighter):
            item = data[run.profile]
            settings = item.pop("integrator_settings_json")
            item["integrator_settings"] = (
                None if settings is None else json.loads(settings)
            )
            residuals = run.terminal_errors
            item["terminal_position_error_m"] = (
                None if residuals is None else residuals[0]
            )
            item["terminal_velocity_error_m_s"] = (
                None if residuals is None else residuals[1]
            )
        return json.loads(
            json.dumps(
                {"science": data, "wall_clock": {"elapsed_s": self.elapsed_wall_s}},
                allow_nan=False,
                default=_json_real,
            )
        )


@dataclass(slots=True)
class _ResearchBudget(_RefinementBudget):
    """One seed, two ordered three-arc runs, using the existing shared clock.

    No automatic retry: an attempted arc must be explicitly accepted before
    another can launch. The cooperative deadline cannot preempt a native call;
    native execution must also check it before accepting returned output.
    """

    completed_arcs: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        _RefinementBudget.__post_init__(self)
        if self.max_arcs_per_evaluation != 3:
            self._fail(
                "research-budget", "research requires exactly three arcs per run"
            )

    def begin_control(self) -> None:
        self.check()
        if self.control_attempts:
            self._fail("research-budget", "one fixed control only; no retries")
        _RefinementBudget.begin_control(self)

    def begin_arc(self, *, first_in_evaluation: bool) -> None:
        self.check()
        if self.control_attempts != 1:
            self._fail("research-budget", "a fixed control must be registered first")
        if self.native_arc_propagations >= 6:
            self._fail("research-budget", "native-arc limit 6 reached")
        if self.completed_arcs != self.native_arc_propagations:
            self._fail("research-budget", "previous arc has not completed; no retries")
        expected_first = self.native_arc_propagations in (0, 3)
        if (
            not isinstance(first_in_evaluation, bool)
            or first_in_evaluation != expected_first
        ):
            self._fail("research-budget", "arcs must follow two ordered three-arc runs")
        _RefinementBudget.begin_arc(self, first_in_evaluation=first_in_evaluation)

    def complete_arc(self) -> None:
        """Count only after the caller's event, completion and handoff checks."""
        self.check()
        if self.native_arc_propagations != self.completed_arcs + 1:
            self._fail("research-budget", "no single pending arc to complete")
        self.completed_arcs += 1

    def snapshot(self) -> ResearchProgress:
        """Preserve accounting even after deadline/failure; never claim safety."""
        return ResearchProgress(self.native_arc_propagations, self.completed_arcs)
