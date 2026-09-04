from __future__ import annotations

from collections.abc import Sequence
from hashlib import sha256
import math
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from space_nav import ephemeris, trajectory
from space_nav.errors import EphemerisError, TrajectoryRefinementError
from space_nav.models import ImpulsiveTransferCandidate


ROOT = Path(__file__).resolve().parents[1]


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


def test_environment_import_remains_tudatpy_and_kernel_lazy() -> None:
    code = """
import sys
from space_nav import ephemeris, trajectory

assert trajectory.PHYSICAL_MODEL_IDENTIFIER
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


def test_real_environment_uses_exact_time_limited_resources_and_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.dynamics import environment_setup

    candidate = _real_candidate(monkeypatch)
    calls: list[tuple[tuple[str, ...], float, float, str, str, float]] = []
    original = environment_setup.get_default_body_settings_time_limited

    def record_limited_settings(
        bodies: Sequence[str],
        initial_time: float,
        final_time: float,
        base_frame_origin: str = "SSB",
        base_frame_orientation: str = "ECLIPJ2000",
        time_step: float = 300.0,
    ) -> Any:
        calls.append(
            (
                tuple(bodies),
                initial_time,
                final_time,
                base_frame_origin,
                base_frame_orientation,
                time_step,
            )
        )
        return original(
            bodies,
            initial_time,
            final_time,
            base_frame_origin,
            base_frame_orientation,
            time_step,
        )

    monkeypatch.setattr(
        environment_setup,
        "get_default_body_settings_time_limited",
        record_limited_settings,
    )
    environment = trajectory._build_physical_environment(
        candidate,
        gravity_models_path=_gravity_models_path(),
    )

    assert trajectory.PHYSICAL_MODEL_IDENTIFIER == (
        "ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-"
        "cannonball-srp-schwarzschild-v1"
    )
    assert trajectory.PHYSICAL_BODY_NAMES == (
        "Sun",
        "Mercury",
        "Venus",
        "Earth",
        "Moon",
        "Mars",
        "Jupiter",
        "Saturn",
    )
    assert trajectory.EPHEMERIS_TIME_STEP_S == 300.0
    assert calls == [
        (
            trajectory.PHYSICAL_BODY_NAMES,
            candidate.departure_epoch_tdb_s,
            candidate.arrival_epoch_tdb_s,
            "SSB",
            "J2000",
            trajectory.EPHEMERIS_TIME_STEP_S,
        )
    ]

    assert environment.model_id == trajectory.PHYSICAL_MODEL_IDENTIFIER
    assert environment.initial_epoch_tdb_s == candidate.departure_epoch_tdb_s
    assert environment.final_epoch_tdb_s == candidate.arrival_epoch_tdb_s
    assert environment.origin == "SSB"
    assert environment.orientation == "J2000"
    assert environment.bodies.global_frame_origin() == "SSB"
    assert environment.bodies.global_frame_orientation() == "J2000"
    assert set(environment.bodies.list_of_bodies()) == set(
        trajectory.PHYSICAL_BODY_NAMES
    )

    for body_name in trajectory.PHYSICAL_BODY_NAMES:
        body = environment.bodies.get_body(body_name)
        assert body.ephemeris.frame_origin == "SSB"
        assert body.ephemeris.frame_orientation == "J2000"
        for epoch_tdb_s in (
            candidate.departure_epoch_tdb_s,
            candidate.arrival_epoch_tdb_s,
        ):
            state = tuple(float(value) for value in body.ephemeris.cartesian_state(
                epoch_tdb_s
            ))
            assert len(state) == 6
            assert all(math.isfinite(value) for value in state)

    fields = {field.body: field for field in environment.harmonic_fields}
    assert set(fields) == {"Moon", "Mars"}
    expected = {
        "Moon": {
            "model": "gggrx1200",
            "file_name": "gggrx_1200l_sha.tab",
            "degree": 200,
            "order": 200,
            "hash": trajectory.MOON_HARMONIC_COEFFICIENT_SHA256,
            "frame": "IAU_Moon",
            "gm": trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            "radius": trajectory.MOON_HARMONIC_NORMALIZATION_RADIUS_M,
        },
        "Mars": {
            "model": "jgmro120d",
            "file_name": "jgmro120d.txt",
            "degree": 120,
            "order": 120,
            "hash": trajectory.MARS_HARMONIC_COEFFICIENT_SHA256,
            "frame": "IAU_Mars",
            "gm": trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2,
            "radius": trajectory.MARS_HARMONIC_NORMALIZATION_RADIUS_M,
        },
    }
    for body_name, expected_field in expected.items():
        field = fields[body_name]
        body = environment.bodies.get_body(body_name)
        gravity = body.gravity_field_model
        rotation = body.rotation_model
        assert field.model == expected_field["model"]
        assert field.file_name == expected_field["file_name"]
        assert field.degree == expected_field["degree"]
        assert field.order == expected_field["order"]
        assert field.expected_sha256 == expected_field["hash"]
        assert field.actual_sha256 == expected_field["hash"]
        assert field.associated_frame == expected_field["frame"]
        assert field.rotation_base_frame == "J2000"
        assert field.rotation_target_frame == expected_field["frame"]
        assert math.isclose(
            field.gravitational_parameter_m3_s2,
            expected_field["gm"],
            rel_tol=1e-15,
            abs_tol=0.0,
        )
        assert field.normalization_radius_m == expected_field["radius"]
        assert gravity.maximum_degree == expected_field["degree"]
        assert gravity.maximum_order == expected_field["order"]
        assert math.isclose(
            gravity.gravitational_parameter,
            expected_field["gm"],
            rel_tol=1e-15,
            abs_tol=0.0,
        )
        assert gravity.reference_radius == expected_field["radius"]
        assert rotation.inertial_frame_name == "J2000"
        assert rotation.body_fixed_frame_name == expected_field["frame"]

    assert trajectory.MOON_ORBIT_SHAPE_RADIUS_M == 1_737_400.0
    assert trajectory.MARS_ORBIT_SHAPE_RADIUS_M == 3_389_500.0
    assert trajectory.MOON_HARMONIC_NORMALIZATION_RADIUS_M == 1_738_000.0
    assert trajectory.MARS_HARMONIC_NORMALIZATION_RADIUS_M == 3_396_000.0
    assert (
        trajectory.MOON_ORBIT_SHAPE_RADIUS_M
        != trajectory.MOON_HARMONIC_NORMALIZATION_RADIUS_M
    )
    assert (
        trajectory.MARS_ORBIT_SHAPE_RADIUS_M
        != trajectory.MARS_HARMONIC_NORMALIZATION_RADIUS_M
    )
    assert trajectory.MOON_HARMONIC_COEFFICIENT_SHA256 == (
        "3f4652c01db58e14a4e4c67fe8225874d10120a29cbd7699f5068469ef65b21d"
    )
    assert trajectory.MARS_HARMONIC_COEFFICIENT_SHA256 == (
        "d13b31d46862838abe62ebab3cef8209244588abe14e4e5e481c0fb64354e980"
    )


@pytest.mark.parametrize(
    ("body", "relative_path"),
    [
        ("Moon", Path("Moon") / "gggrx_1200l_sha.tab"),
        ("Mars", Path("Mars") / "jgmro120d.txt"),
    ],
)
def test_missing_harmonic_resource_is_chained_without_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    relative_path: Path,
) -> None:
    pytest.importorskip("tudatpy")
    monkeypatch.setattr(ephemeris, "_ensure_standard_kernels", lambda: object())
    other = (
        Path("Mars") / "jgmro120d.txt"
        if body == "Moon"
        else Path("Moon") / "gggrx_1200l_sha.tab"
    )
    (tmp_path / other).parent.mkdir(parents=True)
    (tmp_path / other).symlink_to(_gravity_models_path() / other)

    with pytest.raises(
        TrajectoryRefinementError,
        match=r"(?i)d0001-t0035.*resource-validation",
    ) as caught:
        trajectory._build_physical_environment(
            _candidate(),
            gravity_models_path=tmp_path,
        )

    assert caught.value.__cause__ is not None
    message = str(caught.value)
    assert "missing or unreadable" in message
    assert body in message
    assert relative_path.name in message


def test_altered_harmonic_resource_reports_expected_and_actual_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    monkeypatch.setattr(ephemeris, "_ensure_standard_kernels", lambda: object())
    moon_path = tmp_path / "Moon" / "gggrx_1200l_sha.tab"
    moon_path.parent.mkdir(parents=True)
    contents = b"altered gravity coefficients"
    moon_path.write_bytes(contents)
    actual_hash = sha256(contents).hexdigest()

    with pytest.raises(
        TrajectoryRefinementError,
        match=r"(?i)d0001-t0035.*resource-validation.*Moon.*SHA-256 mismatch",
    ) as caught:
        trajectory._build_physical_environment(
            _candidate(),
            gravity_models_path=tmp_path,
        )

    message = str(caught.value)
    assert trajectory.MOON_HARMONIC_COEFFICIENT_SHA256 in message
    assert actual_hash in message
    assert caught.value.__cause__ is not None


def test_missing_standard_kernel_is_chained_before_environment_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure = EphemerisError("missing pinned standard kernel")

    def fail_kernel_initialization() -> object:
        raise failure

    monkeypatch.setattr(
        ephemeris,
        "_ensure_standard_kernels",
        fail_kernel_initialization,
    )
    with pytest.raises(
        TrajectoryRefinementError,
        match=(
            r"d0001-t0035.*resource-validation.*"
            r"missing pinned standard kernel"
        ),
    ) as caught:
        trajectory._build_physical_environment(
            _candidate(),
            gravity_models_path=_gravity_models_path(),
        )

    assert caught.value.__cause__ is failure


def test_uncovered_spice_interval_is_chained_without_unlimited_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.dynamics import environment_setup

    failure = RuntimeError("SPICE(SPKINSUFFDATA): uncovered candidate interval")
    create_calls = 0

    def fail_creation(_settings: object) -> object:
        nonlocal create_calls
        create_calls += 1
        raise failure

    monkeypatch.setattr(environment_setup, "create_system_of_bodies", fail_creation)
    with pytest.raises(
        TrajectoryRefinementError,
        match=(
            r"(?i)d0001-t0035.*environment-construction.*"
            r"(?:SPKINSUFFDATA|coverage|uncovered)"
        ),
    ) as caught:
        trajectory._build_physical_environment(
            _candidate(),
            gravity_models_path=_gravity_models_path(),
        )

    assert create_calls == 1
    assert caught.value.__cause__ is not None
    assert caught.value.__cause__.__cause__ is failure


@pytest.mark.parametrize(
    ("drift", "expected_text"),
    [
        ("frame", "frame"),
        ("gm", "gravitational parameter"),
        ("radius", "normalization radius"),
        ("degree", "degree/order"),
        ("order", "degree/order"),
    ],
)
def test_drifted_moon_harmonic_settings_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
    expected_text: str,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.dynamics import environment_setup

    original = environment_setup.gravity_field.from_file_spherical_harmonic

    def drifted_settings(
        file: str,
        maximum_degree: int,
        maximum_order: int,
        associated_reference_frame: str = "",
        gravitational_parameter_index: int = 0,
        reference_radius_index: int = 1,
    ) -> Any:
        is_moon = Path(file).name == "gggrx_1200l_sha.tab"
        if is_moon and drift == "degree":
            maximum_degree -= 1
        if is_moon and drift == "order":
            maximum_order -= 1
        settings = original(
            file,
            maximum_degree,
            maximum_order,
            associated_reference_frame,
            gravitational_parameter_index,
            reference_radius_index,
        )
        if is_moon and drift == "frame":
            settings.associated_reference_frame = "IAU_Mars"
        if is_moon and drift == "gm":
            settings.gravitational_parameter = (
                trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2
                * (1.0 + 2e-15)
            )
        if is_moon and drift == "radius":
            settings = SimpleNamespace(
                associated_reference_frame=settings.associated_reference_frame,
                gravitational_parameter=settings.gravitational_parameter,
                reference_radius=settings.reference_radius + 1.0,
                normalized_cosine_coefficients=(
                    settings.normalized_cosine_coefficients
                ),
                normalized_sine_coefficients=settings.normalized_sine_coefficients,
            )
        return settings

    monkeypatch.setattr(
        environment_setup.gravity_field,
        "from_file_spherical_harmonic",
        drifted_settings,
    )
    with pytest.raises(
        TrajectoryRefinementError,
        match=rf"(?i)d0001-t0035.*resource-validation.*Moon.*{expected_text}",
    ) as caught:
        trajectory._build_physical_environment(
            _candidate(),
            gravity_models_path=_gravity_models_path(),
        )

    assert caught.value.__cause__ is not None
