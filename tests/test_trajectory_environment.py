from __future__ import annotations

from collections.abc import Sequence
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from space_nav import ephemeris, trajectory
from space_nav.errors import EphemerisError, TrajectoryRefinementError
from space_nav.models import ImpulsiveTransferCandidate, SpacecraftSpec


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


def test_production_direct_ephemerides_match_candidate_and_saturn_joins() -> None:
    import numpy as np

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    start, end = evidence["epoch_tdb_s"][0], evidence["epoch_tdb_s"][-1]
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    candidate = _candidate(
        departure_epoch_tdb_s=start, arrival_epoch_tdb_s=end, flight_time_s=end - start,
        departure_epoch_utc=ephemeris.tdb_to_utc(start),
        arrival_epoch_utc=ephemeris.tdb_to_utc(end),
    )
    environment = trajectory._build_physical_environment(candidate, _spacecraft(), budget=budget)
    spice = ephemeris._ensure_standard_kernels()
    for body in trajectory.PHYSICAL_BODY_NAMES:
        epochs = list(evidence["epoch_tdb_s"])
        if body == "Saturn":
            # Directory-derived joins already independently qualified in test_trajectory_spk.
            for index in range(73):
                epoch = 979252416.0 + index * 343872.0
                epochs.extend((math.nextafter(epoch, -math.inf), epoch,
                               math.nextafter(epoch, math.inf)))
        model = environment.bodies.get(body).ephemeris
        for epoch in epochs:
            budget.check()
            expected = spice.get_body_cartesian_state_at_epoch(body, "SSB", "J2000", "NONE", epoch)
            difference = np.asarray(model.cartesian_state(epoch)).reshape(6) - expected
            assert np.all(np.isfinite(difference)), (body, epoch)
            assert np.linalg.norm(difference[:3]) <= 0.001, (body, epoch)  # m
            assert np.linalg.norm(difference[3:]) <= 0.000001, (body, epoch)  # m/s
    budget.check()
    assert budget.native_arc_propagations == 0


@pytest.mark.parametrize("case", ["valid", "gap", "missing-center", "frame", "center", "type",
                                  "descriptor", "no-files", "missing-file", "native", "expired"])
def test_direct_coverage_rejects_invalid_chains(
    case: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import spiceypy as spice

    centers = {10: 0, 1: 0, 2: 0, 399: 0, 301: 399,
               499: 4, 4: 0, 599: 5, 5: 0, 699: 6, 6: 0}
    records = [(target, center, 1, 2, 100.0, 200.0, 1, 100) for target, center in centers.items()]
    if case == "gap":
        records = [record for record in records if record[0] != 699]
        records += [(699, 6, 1, 3, 100.0, 149.0, 1, 100),
                    (699, 6, 1, 3, 151.0, 200.0, 101, 200)]
    if case == "missing-center":
        records = [record for record in records if record[0] != 4]
    if case in {"frame", "center", "type", "descriptor"}:
        changed = list(records[0])
        changed[{"frame": 2, "center": 1, "type": 3, "descriptor": 4}[case]] = (
            float("nan") if case == "descriptor" else 99
        )
        records[0] = tuple(changed)
    now_s = [0.0]
    budget = trajectory._RefinementBudget("coverage-control", 300.0, lambda: now_s[0])
    cursor = [-1]
    failure = RuntimeError("unreadable SPK directory")

    def next_segment() -> bool:
        if case == "native":
            raise failure
        cursor[0] += 1
        if case == "expired":
            now_s[0] = 300.0
        return cursor[0] < len(records)

    monkeypatch.setattr(spice, "ktotal", lambda kind: 0 if case == "no-files" else 1)
    path = ROOT / ("missing-coverage-kernel.bsp" if case == "missing-file" else "README.md")
    monkeypatch.setattr(spice, "kdata", lambda index, kind: (str(path), "SPK", "", 1))
    monkeypatch.setattr(spice, "dafbfs", lambda handle: None)
    monkeypatch.setattr(spice, "daffna", next_segment)
    monkeypatch.setattr(spice, "dafgs", lambda: [0.0] * 5)
    monkeypatch.setattr(spice, "spkuds", lambda descriptor: records[cursor[0]])
    if case == "valid":
        trajectory._validate_direct_spice_coverage("coverage-control", 100.0, 200.0, budget)
    else:
        with pytest.raises(TrajectoryRefinementError, match="coverage-control") as caught:
            trajectory._validate_direct_spice_coverage("coverage-control", 100.0, 200.0, budget)
        assert caught.value.__cause__ is not None
        if case == "native":
            assert caught.value.__cause__ is failure
        if case in {"gap", "missing-center"}:
            assert "missing or gapped coverage" in str(caught.value)
        if case == "expired":
            assert "deadline" in str(caught.value)
    assert budget.native_arc_propagations == 0


@pytest.mark.parametrize("start,end", [(True, 200.0), (float("nan"), 200.0),
                                       (100.0, float("inf")), (200.0, 100.0)])
def test_direct_coverage_invalid_epochs_precede_native_inspection(
    start: float, end: float, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import spiceypy as spice

    native = Mock(side_effect=AssertionError("invalid epochs reached SPICE"))
    monkeypatch.setattr(spice, "ktotal", native)
    with pytest.raises(TrajectoryRefinementError, match="ephemeris-coverage"):
        trajectory._validate_direct_spice_coverage("coverage-control", start, end)
    native.assert_not_called()


@pytest.mark.parametrize("case", ["table", "frame", "light", "stellar", "converge", "global"])
def test_direct_settings_reject_wrong_model_frame_or_aberration(
    case: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tudatpy.dynamics import environment_setup

    ephemeris._ensure_standard_kernels()
    settings = trajectory._create_direct_body_settings(environment_setup)
    target = settings.get("Moon").ephemeris_settings
    if case == "table":
        settings.get("Moon").ephemeris_settings = environment_setup.ephemeris.constant(
            [0.0] * 6, "SSB", "J2000",
        )
    elif case == "global":
        settings = SimpleNamespace(frame_origin="Earth", frame_orientation="J2000")
    elif case == "frame":
        target.frame_orientation = "ECLIPJ2000"
    else:
        # Native aberration flags are read-only in the pinned binding.
        attribute = {"light": "correct_for_light_time_aberration",
                     "stellar": "correct_for_stellar_aberration",
                     "converge": "converge_light_time_aberration"}[case]
        monkeypatch.setattr(type(target), attribute, property(lambda self: True))
    with pytest.raises(ValueError, match="frame|direct SPICE|geometric"):
        trajectory._validate_direct_body_settings(environment_setup, settings)


def test_expired_environment_budget_starts_no_native_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now_s = [0.0]
    budget = trajectory._RefinementBudget("d0001-t0035", 300.0, lambda: now_s[0])
    native_import = Mock()
    monkeypatch.setattr(trajectory, "_import_tudat_environment_setup", native_import)
    now_s[0] = 300.0
    with pytest.raises(TrajectoryRefinementError, match="deadline.*runtime limit 300 s"):
        trajectory._build_physical_environment(_candidate(), _spacecraft(), budget=budget)
    native_import.assert_not_called()


def test_coverage_failure_precedes_body_system_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    failure = TrajectoryRefinementError("coverage-control: missing center 4")
    monkeypatch.setattr(trajectory, "_validate_direct_spice_coverage", Mock(side_effect=failure))
    native = Mock(side_effect=AssertionError("coverage failure reached body creation"))
    monkeypatch.setattr(trajectory, "_create_system_of_bodies", native)
    with pytest.raises(TrajectoryRefinementError) as caught:
        trajectory._build_physical_environment(_real_candidate(monkeypatch), _spacecraft())
    assert caught.value is failure
    native.assert_not_called()


@pytest.mark.parametrize("stage", ["defaults", "ephemeris"])
def test_direct_factory_failure_retains_native_cause(stage: str) -> None:
    native = Mock()
    failure = RuntimeError("direct factory failed")
    target = native.get_default_body_settings if stage == "defaults" else native.ephemeris.direct_spice
    target.side_effect = failure
    with pytest.raises(RuntimeError, match="direct SSB/J2000") as caught:
        trajectory._create_direct_body_settings(native)
    assert caught.value.__cause__ is failure


@pytest.mark.parametrize(
    ("stage", "next_stage"),
    [
        ("_verified_coefficient_files", "_build_collision_resource"),
        ("_validate_direct_spice_coverage", "_create_direct_body_settings"),
        ("_create_direct_body_settings", "_validate_direct_body_settings"),
        ("_load_harmonic_field_settings", "_validate_harmonic_field_settings"),
        ("_create_system_of_bodies", "_validate_created_environment"),
        ("_build_relativistic_acceleration_settings", "_PhysicalEnvironment"),
    ],
)
def test_environment_stage_expiry_discards_result_without_resetting_budget(
    monkeypatch: pytest.MonkeyPatch, stage: str, next_stage: str,
) -> None:
    candidate = _real_candidate(monkeypatch)
    now_s = [10.0]
    budget = trajectory._RefinementBudget(candidate.candidate_id, 300.0, lambda: now_s[0])
    original = getattr(trajectory, stage)

    def delayed_stage(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        now_s[0] = 310.0
        return result

    following = Mock()
    monkeypatch.setattr(trajectory, stage, delayed_stage)
    monkeypatch.setattr(trajectory, next_stage, following)
    now_s[0] = 200.0  # Earlier handoff work has already consumed part of the budget.
    with pytest.raises(TrajectoryRefinementError, match="deadline") as caught:
        trajectory._build_physical_environment(candidate, _spacecraft(), budget=budget)
    following.assert_not_called()
    assert budget.deadline_monotonic_s == 310.0
    for expected in ("runtime limit 300 s", "control_attempts=0",
                     "propagation_evaluations=0", "native_arc_propagations=0",
                     "no partial result"):
        assert expected in str(caught.value)
    assert isinstance(caught.value.__cause__, RuntimeError)


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


def test_real_environment_uses_exact_direct_resources_and_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.dynamics import environment_setup

    candidate = _real_candidate(monkeypatch)
    calls: list[tuple[tuple[str, ...], str, str]] = []
    original = environment_setup.get_default_body_settings

    def record_direct_settings(
        bodies: Sequence[str],
        base_frame_origin: str = "SSB",
        base_frame_orientation: str = "ECLIPJ2000",
    ) -> Any:
        calls.append((tuple(bodies), base_frame_origin, base_frame_orientation))
        return original(bodies, base_frame_origin, base_frame_orientation)

    monkeypatch.setattr(
        environment_setup,
        "get_default_body_settings",
        record_direct_settings,
    )
    table_factory = Mock(side_effect=AssertionError("production requested a table"))
    monkeypatch.setattr(environment_setup, "get_default_body_settings_time_limited", table_factory)
    monkeypatch.setattr(environment_setup, "get_safe_interpolation_interval", table_factory)
    budget = trajectory._RefinementBudget(candidate.candidate_id, 300.0, lambda: 100.0)
    environment = trajectory._build_physical_environment(
        candidate,
        _spacecraft(),
        gravity_models_path=_gravity_models_path(),
        budget=budget,
    )
    assert budget.deadline_monotonic_s == 400.0
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations) == (0, 0, 0)

    assert trajectory.PHYSICAL_MODEL_IDENTIFIER == (
        "ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-"
        "cannonball-srp-schwarzschild-direct-spice-v2"
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
    assert calls == [(trajectory.PHYSICAL_BODY_NAMES, "SSB", "J2000")]
    table_factory.assert_not_called()

    assert environment.model_id == trajectory.PHYSICAL_MODEL_IDENTIFIER
    assert environment.initial_epoch_tdb_s == candidate.departure_epoch_tdb_s
    assert environment.final_epoch_tdb_s == candidate.arrival_epoch_tdb_s
    assert environment.origin == "SSB"
    assert environment.orientation == "J2000"
    assert environment.bodies.global_frame_origin() == "SSB"
    assert environment.bodies.global_frame_orientation() == "J2000"
    assert set(environment.bodies.list_of_bodies()) == (
        set(trajectory.PHYSICAL_BODY_NAMES) | {trajectory.SPACECRAFT_BODY_NAME}
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
            _spacecraft(),
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
            _spacecraft(),
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
            _spacecraft(),
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
            _spacecraft(),
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
            _spacecraft(),
            gravity_models_path=_gravity_models_path(),
        )

    assert caught.value.__cause__ is not None
