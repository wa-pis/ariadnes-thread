from __future__ import annotations

from datetime import UTC, datetime
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from space_nav import ephemeris
from space_nav.ephemeris import CartesianState
from space_nav.errors import EphemerisError


class _FakeSpice:
    def __init__(self) -> None:
        self.loads = 0
        self.queries: list[dict[str, object]] = []

    def load_standard_kernels(self) -> None:
        self.loads += 1

    def convert_date_string_to_ephemeris_time(self, value: str) -> float:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
        return (parsed - datetime(2000, 1, 1, 12, tzinfo=UTC)).total_seconds()

    def get_approximate_utc_from_tdb(self, value: float) -> float:
        return value

    def get_body_cartesian_state_at_epoch(self, **kwargs: object) -> tuple[float, ...]:
        self.queries.append(kwargs)
        if kwargs["target_body_name"] == "Unknown":
            raise RuntimeError("SPICE(IDCODENOTFOUND)")
        return (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)

    def get_total_count_of_kernels_loaded(self) -> int:
        return 11


@pytest.fixture
def fake_spice(monkeypatch: pytest.MonkeyPatch) -> _FakeSpice:
    fake = _FakeSpice()
    monkeypatch.setattr(ephemeris, "_spice", None)
    monkeypatch.setattr(ephemeris, "_kernels_loaded", False)
    monkeypatch.setattr(ephemeris, "_import_spice", lambda: fake)
    return fake


def test_cartesian_state_requires_canonical_finite_vectors() -> None:
    state = CartesianState(
        body="Mars",
        epoch_utc="2031-01-01T00:00:00Z",
        epoch_tdb_s=1.0,
        origin="SSB",
        orientation="J2000",
        position_m=(1.0, 2.0, 3.0),
        velocity_m_s=(4.0, 5.0, 6.0),
    )
    assert state.position_m == (1.0, 2.0, 3.0)
    with pytest.raises(ValueError, match="SSB/J2000"):
        CartesianState(
            body="Mars",
            epoch_utc=state.epoch_utc,
            epoch_tdb_s=1.0,
            origin="Earth",  # type: ignore[arg-type]
            orientation="J2000",
            position_m=state.position_m,
            velocity_m_s=state.velocity_m_s,
        )
    with pytest.raises(ValueError, match="finite"):
        CartesianState(
            body="Mars",
            epoch_utc=state.epoch_utc,
            epoch_tdb_s=math.nan,
            origin="SSB",
            orientation="J2000",
            position_m=state.position_m,
            velocity_m_s=state.velocity_m_s,
        )


def test_query_is_lazy_deterministic_and_uses_canonical_arguments(
    fake_spice: _FakeSpice,
) -> None:
    assert fake_spice.loads == 0
    first = ephemeris.query_body_state("Mars", "2031-01-01T00:00:00Z")
    second = ephemeris.query_body_state("Mars", "2031-01-01T00:00:00Z")

    assert first == second
    assert fake_spice.loads == 1
    assert fake_spice.queries[0] == {
        "target_body_name": "Mars",
        "observer_body_name": "SSB",
        "reference_frame_name": "J2000",
        "aberration_corrections": "NONE",
        "ephemeris_time": first.epoch_tdb_s,
    }
    assert first.position_m == (1.0, 2.0, 3.0)
    assert first.velocity_m_s == (4.0, 5.0, 6.0)


def test_time_conversion_round_trips_with_spice(fake_spice: _FakeSpice) -> None:
    epoch = "2031-01-02T03:04:05.123Z"
    assert ephemeris.tdb_to_utc(ephemeris.utc_to_tdb(epoch)) == epoch
    assert fake_spice.loads == 1


def test_query_wraps_body_and_epoch_failure(fake_spice: _FakeSpice) -> None:
    with pytest.raises(EphemerisError) as caught:
        ephemeris.query_body_state("Unknown", "2031-01-01T00:00:00Z")
    message = str(caught.value)
    assert "Unknown" in message
    assert "2031-01-01T00:00:00Z" in message
    assert "coverage" in message
    assert caught.value.__cause__ is not None


def test_invalid_epoch_fails_before_kernel_loading(fake_spice: _FakeSpice) -> None:
    with pytest.raises(EphemerisError, match="Mars"):
        ephemeris.query_body_state("Mars", "not-a-date")
    assert fake_spice.loads == 0


def test_kernel_initialization_failure_is_actionable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenSpice:
        def load_standard_kernels(self) -> None:
            raise RuntimeError("missing resource")

    monkeypatch.setattr(ephemeris, "_spice", None)
    monkeypatch.setattr(ephemeris, "_kernels_loaded", False)
    monkeypatch.setattr(ephemeris, "_import_spice", lambda: BrokenSpice())
    with pytest.raises(EphemerisError, match="initialization failed") as caught:
        ephemeris.utc_to_tdb("2031-01-01T00:00:00Z")
    assert caught.value.__cause__ is not None


def test_kernel_manifest_lists_versions_and_hashes(
    tmp_path: Path, fake_spice: _FakeSpice, monkeypatch: pytest.MonkeyPatch
) -> None:
    kernel_root = tmp_path / "kernels"
    kernel_root.mkdir()
    names = ("pck00010.tpc", "naif0012.tls")
    for name in names:
        (kernel_root / name).write_bytes(name.encode())

    paths = [str(kernel_root / name) for name in names]
    fake_pool = SimpleNamespace(
        __version__="8.2.0",
        ktotal=lambda kind: len(paths),
        kdata=lambda index, kind: (paths[index], "TEXT", "", index, True),
    )
    monkeypatch.setitem(sys.modules, "spiceypy", fake_pool)
    monkeypatch.setattr(fake_spice, "get_total_count_of_kernels_loaded", lambda: 2)

    manifest = ephemeris.kernel_metadata()

    assert manifest["loaded_kernel_count"] == 2
    assert manifest["spiceypy_version"] == "8.2.0"
    assert manifest["kernel_list_status"] == "complete"
    assert [item["name"] for item in manifest["kernels"]] == list(names)
    assert all(len(item["sha256"]) == 64 for item in manifest["kernels"])
    assert all(item["version"] for item in manifest["kernels"])


def test_real_tudatpy_parity_and_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.interface import spice

    monkeypatch.setattr(ephemeris, "_spice", None)
    monkeypatch.setattr(ephemeris, "_kernels_loaded", False)
    epoch_utc = "2030-01-01T00:00:00Z"
    state = ephemeris.query_body_state("Moon", epoch_utc)
    direct = spice.get_body_cartesian_state_at_epoch(
        target_body_name="Moon",
        observer_body_name="SSB",
        reference_frame_name="J2000",
        aberration_corrections="NONE",
        ephemeris_time=state.epoch_tdb_s,
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

    round_trip = ephemeris.tdb_to_utc(ephemeris.utc_to_tdb(epoch_utc))
    original_dt = datetime.fromisoformat(epoch_utc.replace("Z", "+00:00"))
    round_trip_dt = datetime.fromisoformat(round_trip.replace("Z", "+00:00"))
    assert abs((round_trip_dt - original_dt).total_seconds()) <= 0.001

    manifest = ephemeris.kernel_metadata()
    assert manifest["kernel_list_status"] == "complete"
    assert manifest["loaded_kernel_count"] == len(manifest["kernels"])
    assert len(manifest["kernels"]) > 0
    assert all(len(item["sha256"]) == 64 for item in manifest["kernels"])

    with pytest.raises(EphemerisError) as outside_coverage:
        ephemeris.query_body_state("Mars", "2500-01-01T00:00:00Z")
    assert "Mars" in str(outside_coverage.value)
    assert "2500-01-01T00:00:00Z" in str(outside_coverage.value)
    assert "coverage" in str(outside_coverage.value)
