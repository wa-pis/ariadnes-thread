from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
import math
from pathlib import Path
import subprocess
import sys

import pytest

from space_nav import ephemeris
from space_nav.errors import EphemerisError, TransferSearchError
from space_nav.models import ImpulsiveTransferCandidate, TransferSearchResult


def _candidate(**changes: object) -> ImpulsiveTransferCandidate:
    values: dict[str, object] = {
        "candidate_id": "d0000-t0000",
        "departure_epoch_utc": "2031-01-01T00:00:00Z",
        "arrival_epoch_utc": "2031-01-02T00:00:00Z",
        "departure_epoch_tdb_s": 100.0,
        "arrival_epoch_tdb_s": 200.0,
        "flight_time_s": 100.0,
        "departure_v_infinity_m_s": (1.0, 2.0, 3.0),
        "arrival_v_infinity_m_s": (4.0, 5.0, 6.0),
        "departure_delta_v_m_s": 10.0,
        "arrival_delta_v_m_s": 20.0,
        "total_delta_v_m_s": 30.0,
        "propellant_mass_kg": 100.0,
        "final_mass_kg": 900.0,
        "mass_feasible": True,
    }
    values.update(changes)
    return ImpulsiveTransferCandidate(**values)  # type: ignore[arg-type]


def _result(
    front: tuple[ImpulsiveTransferCandidate, ...] | None = None,
    **changes: object,
) -> TransferSearchResult:
    values: dict[str, object] = {
        "ephemeris_origin": "SSB",
        "transfer_central_body": "Sun",
        "orientation": "J2000",
        "time_scale": "TDB seconds since J2000",
        "evaluated_candidates": 2,
        "solved_candidates": 1,
        "failed_candidates": 1,
        "mass_feasible_candidates": 1,
        "pareto_front": front or (_candidate(),),
    }
    values.update(changes)
    return TransferSearchResult(**values)  # type: ignore[arg-type]


def test_transfer_contracts_are_immutable_and_search_error_is_public() -> None:
    candidate = _candidate()
    result = _result()

    with pytest.raises(FrozenInstanceError):
        candidate.flight_time_s = 1.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.evaluated_candidates = 1  # type: ignore[misc]
    assert not hasattr(candidate, "__dict__")
    assert not hasattr(result, "__dict__")
    assert str(TransferSearchError("search failed")) == "search failed"


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"candidate_id": "candidate-1"}, "candidate_id"),
        ({"departure_epoch_utc": "2031-01-01T00:00:00.000Z"}, "normalized"),
        ({"arrival_epoch_utc": "2030-01-01T00:00:00Z"}, "after"),
        ({"departure_epoch_tdb_s": math.nan}, "finite"),
        ({"flight_time_s": 0.0, "arrival_epoch_tdb_s": 100.0}, "positive"),
        ({"arrival_epoch_tdb_s": 201.0}, "consistent"),
        ({"departure_v_infinity_m_s": (1.0, 2.0)}, "three finite"),
        ({"arrival_v_infinity_m_s": (1.0, math.inf, 3.0)}, "three finite"),
        ({"departure_delta_v_m_s": -1.0}, "nonnegative"),
        ({"total_delta_v_m_s": 31.0}, "must equal"),
        ({"propellant_mass_kg": -1.0}, "nonnegative"),
        ({"final_mass_kg": math.inf}, "finite"),
        ({"mass_feasible": 1}, "Boolean"),
    ],
)
def test_candidate_rejects_invalid_values(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _candidate(**changes)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"ephemeris_origin": "Earth"}, "SSB"),
        ({"transfer_central_body": "Mars"}, "Sun"),
        ({"orientation": "ECLIPJ2000"}, "J2000"),
        ({"time_scale": "UTC"}, "TDB seconds"),
        ({"evaluated_candidates": True}, "nonnegative integer"),
        ({"evaluated_candidates": 2001, "solved_candidates": 2000}, "2000"),
        ({"failed_candidates": 0}, "must equal"),
        ({"mass_feasible_candidates": 2}, "must not exceed"),
        ({"pareto_front": [_candidate()]}, "tuple"),
        (
            {
                "evaluated_candidates": 1,
                "solved_candidates": 0,
                "failed_candidates": 1,
                "mass_feasible_candidates": 0,
                "pareto_front": (),
            },
            "solved Pareto",
        ),
    ],
)
def test_result_rejects_invalid_conventions_and_counts(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _result(**changes)


def test_result_requires_unique_stably_ordered_front_and_feasible_count() -> None:
    first = _candidate(candidate_id="d0000-t0001")
    second = _candidate(
        candidate_id="d0001-t0000",
        arrival_epoch_tdb_s=300.0,
        flight_time_s=200.0,
        arrival_delta_v_m_s=21.0,
        total_delta_v_m_s=31.0,
        propellant_mass_kg=90.0,
        mass_feasible=False,
    )
    result = _result(
        (first, second),
        solved_candidates=2,
        failed_candidates=0,
        mass_feasible_candidates=1,
    )
    assert result.pareto_front == (first, second)

    with pytest.raises(ValueError, match="stable order"):
        _result(
            (second, first),
            solved_candidates=2,
            failed_candidates=0,
            mass_feasible_candidates=1,
        )
    with pytest.raises(ValueError, match="unique"):
        _result(
            (first, first),
            solved_candidates=2,
            failed_candidates=0,
            mass_feasible_candidates=2,
        )
    with pytest.raises(ValueError, match="more feasible"):
        _result(mass_feasible_candidates=0)


def test_package_import_does_not_import_tudatpy_or_load_spice() -> None:
    project_root = Path(__file__).resolve().parents[1]
    code = (
        "import sys; import space_nav; "
        "assert not any(name == 'tudatpy' or name.startswith('tudatpy.') "
        "for name in sys.modules)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


class _FakeSpice:
    def __init__(self) -> None:
        self.loads = 0
        self.queries: list[dict[str, object]] = []
        self.gm_queries: list[str] = []

    def load_standard_kernels(self) -> None:
        self.loads += 1

    def get_approximate_utc_from_tdb(self, value: float) -> float:
        return value

    def get_body_cartesian_state_at_epoch(self, **kwargs: object) -> tuple[float, ...]:
        self.queries.append(kwargs)
        if kwargs["target_body_name"] == "Unknown":
            raise RuntimeError("SPICE(IDCODENOTFOUND)")
        return (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)

    def get_body_gravitational_parameter(self, body: str) -> float:
        self.gm_queries.append(body)
        if body == "Unknown":
            raise RuntimeError("SPICE(KERNELVARNOTFOUND)")
        if body == "Invalid":
            return math.nan
        return 4.282837e13


@pytest.fixture
def transfer_spice(monkeypatch: pytest.MonkeyPatch) -> _FakeSpice:
    fake = _FakeSpice()
    monkeypatch.setattr(ephemeris, "_spice", None)
    monkeypatch.setattr(ephemeris, "_kernels_loaded", False)
    monkeypatch.setattr(ephemeris, "_import_spice", lambda: fake)
    return fake


def test_exact_tdb_state_and_gm_reuse_the_lazy_kernel_pool(
    transfer_spice: _FakeSpice,
) -> None:
    assert transfer_spice.loads == 0
    first = ephemeris._query_body_state_tdb("Mars", 100.25)
    second = ephemeris._query_body_state_tdb("Mars", 100.25)
    gm = ephemeris._get_body_gravitational_parameter("Mars")

    assert first == second
    assert first.epoch_tdb_s == 100.25
    assert first.epoch_utc == "2000-01-01T12:01:40.25Z"
    assert first.position_m == (1.0, 2.0, 3.0)
    assert first.velocity_m_s == (4.0, 5.0, 6.0)
    assert transfer_spice.loads == 1
    assert transfer_spice.queries[0] == {
        "target_body_name": "Mars",
        "observer_body_name": "SSB",
        "reference_frame_name": "J2000",
        "aberration_corrections": "NONE",
        "ephemeris_time": 100.25,
    }
    assert transfer_spice.gm_queries == ["Mars"]
    assert gm == 4.282837e13


def test_exact_tdb_and_gm_failures_are_contextual_and_chained(
    transfer_spice: _FakeSpice,
) -> None:
    with pytest.raises(EphemerisError, match="Mars.*finite") as invalid_epoch:
        ephemeris._query_body_state_tdb("Mars", math.nan)
    assert invalid_epoch.value.__cause__ is not None
    assert transfer_spice.loads == 0

    with pytest.raises(EphemerisError, match="Unknown.*100") as state_failure:
        ephemeris._query_body_state_tdb("Unknown", 100.0)
    assert state_failure.value.__cause__ is not None

    with pytest.raises(EphemerisError, match="Unknown") as gm_failure:
        ephemeris._get_body_gravitational_parameter("Unknown")
    assert gm_failure.value.__cause__ is not None

    with pytest.raises(EphemerisError, match="invalid gravitational.*Invalid"):
        ephemeris._get_body_gravitational_parameter("Invalid")


def test_real_exact_tdb_state_and_gm_match_direct_tudatpy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.interface import spice

    monkeypatch.setattr(ephemeris, "_spice", None)
    monkeypatch.setattr(ephemeris, "_kernels_loaded", False)
    epoch_tdb_s = ephemeris.utc_to_tdb("2030-01-01T00:00:00Z")
    state = ephemeris._query_body_state_tdb("Moon", epoch_tdb_s)
    direct = spice.get_body_cartesian_state_at_epoch(
        target_body_name="Moon",
        observer_body_name="SSB",
        reference_frame_name="J2000",
        aberration_corrections="NONE",
        ephemeris_time=epoch_tdb_s,
    )
    position_error = math.sqrt(
        sum((state.position_m[index] - float(direct[index])) ** 2 for index in range(3))
    )
    velocity_error = math.sqrt(
        sum(
            (state.velocity_m_s[index] - float(direct[index + 3])) ** 2
            for index in range(3)
        )
    )
    assert position_error <= 0.001
    assert velocity_error <= 0.000001
    assert state.epoch_tdb_s == epoch_tdb_s

    flight_time_s = 86_400.0
    arrival_state = ephemeris._query_body_state_tdb(
        "Mars", epoch_tdb_s + flight_time_s
    )
    candidate = _candidate(
        departure_epoch_utc=state.epoch_utc,
        arrival_epoch_utc=arrival_state.epoch_utc,
        departure_epoch_tdb_s=state.epoch_tdb_s,
        arrival_epoch_tdb_s=arrival_state.epoch_tdb_s,
        flight_time_s=flight_time_s,
    )
    for utc_label, tdb_value in (
        (candidate.departure_epoch_utc, candidate.departure_epoch_tdb_s),
        (candidate.arrival_epoch_utc, candidate.arrival_epoch_tdb_s),
    ):
        assert abs(ephemeris.utc_to_tdb(utc_label) - tdb_value) <= 0.001

    gm = ephemeris._get_body_gravitational_parameter("Moon")
    assert gm == pytest.approx(spice.get_body_gravitational_parameter("Moon"))
    utc = datetime.fromisoformat(state.epoch_utc.replace("Z", "+00:00"))
    expected = datetime(2030, 1, 1, tzinfo=UTC)
    assert abs((utc - expected).total_seconds()) <= 0.001
