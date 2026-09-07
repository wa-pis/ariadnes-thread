from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

from space_nav import ephemeris, trajectory
from space_nav.errors import TrajectoryRefinementError
from space_nav.models import ImpulsiveTransferCandidate, SpacecraftSpec


ROOT = Path(__file__).resolve().parents[1]
_PCK_SHA256 = "59468328349aa730d18bf1f8d7e86efe6e40b75dfb921908f99321b3a7a701d2"
_EXPECTED_RADII_M = (
    ("Sun", (696_000_000.0, 696_000_000.0, 696_000_000.0)),
    ("Mercury", (2_439_700.0, 2_439_700.0, 2_439_700.0)),
    ("Venus", (6_051_800.0, 6_051_800.0, 6_051_800.0)),
    ("Earth", (6_378_136.6, 6_378_136.6, 6_356_751.9)),
    ("Moon", (1_737_400.0, 1_737_400.0, 1_737_400.0)),
    ("Mars", (3_396_190.0, 3_396_190.0, 3_376_200.0)),
    ("Jupiter", (71_492_000.0, 71_492_000.0, 66_854_000.0)),
    ("Saturn", (60_268_000.0, 60_268_000.0, 54_364_000.0)),
)


class _FakeSpice:
    def __init__(
        self,
        overrides: dict[str, object] | None = None,
        missing_bodies: set[str] | None = None,
    ) -> None:
        self.overrides = overrides or {}
        self.missing_bodies = missing_bodies or set()
        self.calls: list[tuple[str, str, int]] = []

    def check_body_property_in_kernel_pool(
        self,
        body: str,
        property_name: str,
    ) -> bool:
        assert property_name == "RADII"
        return body not in self.missing_bodies

    def get_body_properties(
        self,
        body: str,
        property_name: str,
        maximum_number_of_values: int,
    ) -> object:
        self.calls.append((body, property_name, maximum_number_of_values))
        value = self.overrides.get(body)
        if isinstance(value, Exception):
            raise value
        if value is not None:
            return value
        expected_m = dict(_EXPECTED_RADII_M)[body]
        return [component_m / 1_000.0 for component_m in expected_m]


def _candidate(**changes: object) -> ImpulsiveTransferCandidate:
    values: dict[str, object] = {
        "candidate_id": "d0001-t0035",
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
        "final_mass_kg": 1_400.0,
        "mass_feasible": True,
    }
    values.update(changes)
    return ImpulsiveTransferCandidate(**values)  # type: ignore[arg-type]


def _spacecraft() -> SpacecraftSpec:
    return SpacecraftSpec(
        initial_mass_kg=2_000.0,
        dry_mass_kg=1_000.0,
        max_thrust_n=1_000.0,
        isp_s=450.0,
        srp_area_m2=20.0,
        reflectivity_coefficient=1.3,
        maneuver_magnitude_sigma_fraction=0.001,
        maneuver_pointing_sigma_rad=math.radians(0.05),
    )


def _real_candidate(monkeypatch: pytest.MonkeyPatch) -> ImpulsiveTransferCandidate:
    monkeypatch.setattr(ephemeris, "_spice", None)
    monkeypatch.setattr(ephemeris, "_kernels_loaded", False)
    departure_epoch_utc = "2031-01-01T00:00:00Z"
    arrival_epoch_utc = "2031-01-02T00:00:00Z"
    departure_epoch_tdb_s = ephemeris.utc_to_tdb(departure_epoch_utc)
    arrival_epoch_tdb_s = ephemeris.utc_to_tdb(arrival_epoch_utc)
    return _candidate(
        departure_epoch_utc=departure_epoch_utc,
        arrival_epoch_utc=arrival_epoch_utc,
        departure_epoch_tdb_s=departure_epoch_tdb_s,
        arrival_epoch_tdb_s=arrival_epoch_tdb_s,
        flight_time_s=arrival_epoch_tdb_s - departure_epoch_tdb_s,
    )


def _gravity_models_path() -> Path:
    pytest.importorskip("tudatpy")
    from tudatpy import data

    return Path(data.get_gravity_models_path())


def _kernel_metadata(*hashes: str) -> dict[str, object]:
    kernels = [
        {
            "name": "pck00010.tpc",
            "version": "pck00010",
            "type": "TEXT",
            "source": None,
            "size_bytes": 1,
            "sha256": digest,
        }
        for digest in hashes
    ]
    return {
        "kernel_source": "tudatpy-standard",
        "loaded_kernel_count": len(kernels),
        "spiceypy_version": "test",
        "kernels": kernels,
        "kernel_list_status": "complete",
    }


def _install_fake_collision_resources(
    monkeypatch: pytest.MonkeyPatch,
    spice: _FakeSpice,
    *hashes: str,
) -> None:
    monkeypatch.setattr(
        ephemeris,
        "kernel_metadata",
        lambda: _kernel_metadata(*hashes),
    )
    monkeypatch.setattr(ephemeris, "_ensure_standard_kernels", lambda: spice)


def test_collision_import_remains_tudatpy_and_kernel_lazy() -> None:
    code = """
import sys
from space_nav import ephemeris, trajectory

assert trajectory._COLLISION_PCK_KERNEL_NAME == "pck00010.tpc"
assert trajectory._COLLISION_RADIUS_TOLERANCE_M == 0.001
assert trajectory._build_collision_resource
assert trajectory._crosses_collision_surface
assert not any(
    name == "tudatpy" or name.startswith("tudatpy.") for name in sys.modules
)
assert not ephemeris._kernels_loaded
assert "moon_to_mars" not in sys.modules
"""
    environment = os.environ | {"PYTHONPATH": str(ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_real_environment_uses_exact_pinned_collision_surfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    spice = ephemeris._ensure_standard_kernels()
    original_get_properties = spice.get_body_properties
    calls: list[tuple[str, str, int]] = []

    def record_properties(body: str, property_name: str, count: int) -> object:
        calls.append((body, property_name, count))
        return original_get_properties(body, property_name, count)

    monkeypatch.setattr(spice, "get_body_properties", record_properties)
    environment = trajectory._build_physical_environment(
        _real_candidate(monkeypatch),
        _spacecraft(),
        gravity_models_path=_gravity_models_path(),
    )
    resource = environment.collision_resource

    assert trajectory._COLLISION_PCK_EXPECTED_SHA256 == _PCK_SHA256
    assert trajectory._PINNED_COLLISION_RADII_M == _EXPECTED_RADII_M
    assert calls == [(body, "RADII", 3) for body in trajectory.PHYSICAL_BODY_NAMES]
    assert resource.kernel_name == "pck00010.tpc"
    assert resource.expected_sha256 == resource.actual_sha256 == _PCK_SHA256
    assert resource.radius_tolerance_m == 0.001
    assert tuple(surface.body for surface in resource.surfaces) == (
        trajectory.PHYSICAL_BODY_NAMES
    )
    for surface, (body, expected_m) in zip(
        resource.surfaces,
        _EXPECTED_RADII_M,
        strict=True,
    ):
        assert surface.body == body
        assert surface.expected_radius_vector_m == expected_m
        assert max(
            abs(actual - expected)
            for actual, expected in zip(
                surface.actual_radius_vector_m,
                expected_m,
                strict=True,
            )
        ) <= 0.001
        assert surface.guard_radius_m == max(surface.actual_radius_vector_m)
        with pytest.raises(FrozenInstanceError):
            surface.guard_radius_m = 1.0  # type: ignore[misc]

    fields = {field.body: field for field in environment.harmonic_fields}
    surfaces = {surface.body: surface for surface in resource.surfaces}
    assert (
        fields["Moon"].orbit_shape_radius_m,
        fields["Moon"].normalization_radius_m,
        surfaces["Moon"].guard_radius_m,
    ) == (1_737_400.0, 1_738_000.0, 1_737_400.0)
    assert (
        fields["Mars"].orbit_shape_radius_m,
        fields["Mars"].normalization_radius_m,
        surfaces["Mars"].guard_radius_m,
    ) == (3_389_500.0, 3_396_000.0, 3_396_190.0)


def test_collision_manifest_records_exact_kernel_vectors_and_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_spice = _FakeSpice()
    _install_fake_collision_resources(monkeypatch, fake_spice, _PCK_SHA256)
    resource = trajectory._build_collision_resource("d0001-t0035")

    assert trajectory._collision_resource_manifest(resource) == {
        "pck_kernel": {
            "name": "pck00010.tpc",
            "expected_sha256": _PCK_SHA256,
            "actual_sha256": _PCK_SHA256,
        },
        "radius_tolerance_m": 0.001,
        "radii_unit": "m",
        "impact_condition": "distance_m <= guard_radius_m",
        "surfaces": [
            {
                "body": body,
                "expected_radius_vector_m": list(radii_m),
                "actual_radius_vector_m": list(radii_m),
                "guard_radius_m": max(radii_m),
            }
            for body, radii_m in _EXPECTED_RADII_M
        ],
    }


@pytest.mark.parametrize(
    ("hashes", "expected_detail"),
    [
        ((), "missing"),
        (("0" * 64,), "SHA-256"),
        ((_PCK_SHA256, "0" * 64), "SHA-256"),
    ],
)
def test_missing_drifted_or_duplicate_pck_fails_before_radius_queries(
    monkeypatch: pytest.MonkeyPatch,
    hashes: tuple[str, ...],
    expected_detail: str,
) -> None:
    fake_spice = _FakeSpice()
    _install_fake_collision_resources(monkeypatch, fake_spice, *hashes)

    with pytest.raises(
        TrajectoryRefinementError,
        match=r"d0001-t0035.*resource-validation.*pck00010\.tpc",
    ) as caught:
        trajectory._build_collision_resource("d0001-t0035")

    assert expected_detail in str(caught.value)
    assert caught.value.__cause__ is not None
    assert fake_spice.calls == []


@pytest.mark.parametrize(
    "invalid_value",
    [
        RuntimeError("SPICE radius unavailable"),
        [3_396.19, 3_396.19],
        [True, 3_396.19, 3_376.2],
        ["not-a-number", 3_396.19, 3_376.2],
        [math.nan, 3_396.19, 3_376.2],
        [math.inf, 3_396.19, 3_376.2],
        [0.0, 3_396.19, 3_376.2],
        [-1.0, 3_396.19, 3_376.2],
        [3_396.190_002, 3_396.19, 3_376.2],
    ],
    ids=(
        "missing",
        "wrong-length",
        "boolean",
        "nonnumeric",
        "nan",
        "infinity",
        "zero",
        "negative",
        "drift-over-one-millimeter",
    ),
)
def test_invalid_or_drifted_radius_vector_fails_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
    invalid_value: object,
) -> None:
    fake_spice = _FakeSpice({"Mars": invalid_value})
    _install_fake_collision_resources(monkeypatch, fake_spice, _PCK_SHA256)

    with pytest.raises(
        TrajectoryRefinementError,
        match=r"d0001-t0035.*resource-validation.*Mars.*RADII",
    ) as caught:
        trajectory._build_collision_resource("d0001-t0035")

    assert caught.value.__cause__ is not None
    if isinstance(invalid_value, Exception):
        assert caught.value.__cause__ is invalid_value
    assert fake_spice.calls[-1] == ("Mars", "RADII", 3)
    assert all(call[0] != "Jupiter" for call in fake_spice.calls)


def test_radius_availability_check_failure_is_chained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_spice = _FakeSpice()
    failure = RuntimeError("SPICE pool check failed")
    original_check = fake_spice.check_body_property_in_kernel_pool

    def fail_mars_check(body: str, property_name: str) -> bool:
        if body == "Mars":
            raise failure
        return original_check(body, property_name)

    monkeypatch.setattr(
        fake_spice,
        "check_body_property_in_kernel_pool",
        fail_mars_check,
    )
    _install_fake_collision_resources(monkeypatch, fake_spice, _PCK_SHA256)

    with pytest.raises(
        TrajectoryRefinementError,
        match=r"d0001-t0035.*resource-validation",
    ) as caught:
        trajectory._build_collision_resource("d0001-t0035")

    assert "Mars" in str(caught.value)
    assert "RADII" in str(caught.value)
    assert caught.value.__cause__ is failure
    assert all(call[0] != "Mars" for call in fake_spice.calls)


def test_missing_radius_property_fails_without_query_or_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_spice = _FakeSpice(missing_bodies={"Mars"})
    _install_fake_collision_resources(monkeypatch, fake_spice, _PCK_SHA256)

    with pytest.raises(
        TrajectoryRefinementError,
        match=r"d0001-t0035.*resource-validation",
    ) as caught:
        trajectory._build_collision_resource("d0001-t0035")

    assert caught.value.__cause__ is not None
    assert "Mars" in str(caught.value)
    assert "RADII" in str(caught.value)
    assert "missing" in str(caught.value)
    assert all(call[0] != "Mars" for call in fake_spice.calls)


def test_identical_duplicate_pck_entries_are_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_spice = _FakeSpice()
    _install_fake_collision_resources(
        monkeypatch,
        fake_spice,
        _PCK_SHA256,
        _PCK_SHA256,
    )

    resource = trajectory._build_collision_resource("d0001-t0035")

    assert resource.actual_sha256 == _PCK_SHA256
    assert len(resource.surfaces) == len(_EXPECTED_RADII_M)


def test_radius_drift_within_one_millimeter_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_m = dict(_EXPECTED_RADII_M)["Mars"]
    within_tolerance_km = [
        (expected_m[0] + 0.0005) / 1_000.0,
        expected_m[1] / 1_000.0,
        expected_m[2] / 1_000.0,
    ]
    fake_spice = _FakeSpice({"Mars": within_tolerance_km})
    _install_fake_collision_resources(monkeypatch, fake_spice, _PCK_SHA256)

    resource = trajectory._build_collision_resource("d0001-t0035")
    mars = next(surface for surface in resource.surfaces if surface.body == "Mars")

    assert abs(mars.actual_radius_vector_m[0] - expected_m[0]) <= 0.001
    assert mars.guard_radius_m == max(mars.actual_radius_vector_m)


@pytest.mark.parametrize(
    ("offset_m", "expected"),
    [
        (8_388_607.0, True),
        (8_388_608.0, True),
        (8_388_609.0, False),
    ],
)
def test_collision_uses_inclusive_distance_inequality(
    offset_m: float,
    expected: bool,
) -> None:
    body_position_m = (400_000_000.0, -300_000_000.0, 200_000_000.0)
    spacecraft_position_m = (
        body_position_m[0] + offset_m,
        body_position_m[1],
        body_position_m[2],
    )

    assert trajectory._crosses_collision_surface(
        spacecraft_position_m,
        body_position_m,
        8_388_608.0,
    ) is expected


@pytest.mark.parametrize(
    (
        "spacecraft_position_m",
        "body_position_m",
        "guard_radius_m",
        "field",
    ),
    [
        ((math.nan, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0, "spacecraft_position_m"),
        ((0.0, 0.0, 0.0), (0.0, 0.0), 1.0, "body_position_m"),
        ((0.0, 0.0, 0.0), (math.inf, 0.0, 0.0), 1.0, "body_position_m"),
        ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), True, "guard_radius_m"),
        ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0, "guard_radius_m"),
    ],
    ids=(
        "nan-spacecraft-position",
        "short-body-position",
        "infinite-body-position",
        "boolean-guard",
        "zero-guard",
    ),
)
def test_collision_rejects_invalid_inputs_with_field_context(
    spacecraft_position_m: object,
    body_position_m: object,
    guard_radius_m: object,
    field: str,
) -> None:
    with pytest.raises(ValueError, match=field):
        trajectory._crosses_collision_surface(
            spacecraft_position_m,
            body_position_m,
            guard_radius_m,
        )


@pytest.mark.parametrize("body", tuple(body for body, _ in _EXPECTED_RADII_M))
@pytest.mark.parametrize("offset_m", [-1.0, 0.0, 1.0])
def test_trial_safety_checks_each_inclusive_surface(
    body: str, offset_m: float, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_collision_resources(monkeypatch, _FakeSpice(), _PCK_SHA256)
    resource = trajectory._build_collision_resource("safety-control")
    positions: dict[str, object] = {
        name: (1e12, 0.0, 0.0) for name, _ in _EXPECTED_RADII_M
    }
    positions[body] = (max(dict(_EXPECTED_RADII_M)[body]) + offset_m, 0.0, 0.0)
    original = dict(positions)
    reason = trajectory._classify_trial_state(
        "safety-control", (0.0,) * 6, 1000.0, 1000.0, positions, resource,
    )
    assert reason == (f"rejected-impact:{body}" if offset_m <= 0.0 else None)
    assert positions == original


@pytest.mark.parametrize(
    "case", ["dry", "equal", "above", "negative", "both", "impacts", "nan",
             "velocity", "body", "missing", "surfaces", "boolean", "dry-zero"],
)
def test_trial_safety_mass_precedence_and_fatal_data(
    case: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_collision_resources(monkeypatch, _FakeSpice(), _PCK_SHA256)
    resource = trajectory._build_collision_resource("safety-control")
    positions: dict[str, object] = {
        name: (1e12, 0.0, 0.0) for name, _ in _EXPECTED_RADII_M
    }
    state = (0.0,) * 6
    mass_kg = {"equal": 1000.0, "above": 1001.0, "impacts": 1001.0,
               "negative": -1.0, "nan": math.nan, "boolean": True}.get(case, 999.0)
    if case in {"both", "impacts"}:
        positions["Mars"] = positions["Moon"] = (0.0, 0.0, 0.0)
    elif case == "velocity":
        state = (0.0,) * 5 + (math.inf,)
    elif case == "body":
        positions["Saturn"] = (math.nan, 0.0, 0.0)
    elif case == "missing":
        del positions["Mars"]
    elif case == "surfaces":
        resource = replace(resource, surfaces=resource.surfaces[:-1])
    if case in {"nan", "velocity", "body", "missing", "surfaces", "boolean", "dry-zero"}:
        with pytest.raises(TrajectoryRefinementError, match="safety-control") as caught:
            trajectory._classify_trial_state(
                "safety-control", state, mass_kg,
                0.0 if case == "dry-zero" else 1000.0, positions, resource,
            )
        assert isinstance(caught.value.__cause__, ValueError)
    else:
        expected = (
            None if case in {"equal", "above"} else
            "rejected-impact:Moon" if case == "impacts" else "rejected-dry-mass"
        )
        assert trajectory._classify_trial_state(
            "safety-control", state, mass_kg, 1000.0, positions, resource,
        ) == expected
