"""Private research-run accounting; no trajectory or safety qualification."""

from __future__ import annotations

from dataclasses import dataclass, field

from .trajectory import _RefinementBudget


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
            self._fail("research-budget", "research requires exactly three arcs per run")

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
        if not isinstance(first_in_evaluation, bool) or first_in_evaluation != expected_first:
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
