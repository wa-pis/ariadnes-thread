"""R5 native preparation on analytic fixtures, never the frozen reference state."""

from __future__ import annotations

from decimal import Decimal, localcontext
import importlib.util
import math
from pathlib import Path
import subprocess
import sys
from time import monotonic
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

PATH = (
    Path(__file__).resolve().parents[1]
    / "docs/adr/experiments/0140-short-coast-native.py"
)
spec = importlib.util.spec_from_file_location("r5_native_test_adapter", PATH)
assert spec is not None and spec.loader is not None
native = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = native
spec.loader.exec_module(native)


def idle() -> None:
    pass


def no_guard(at: float, state: tuple[float, ...]) -> None:
    pass


def constant(position: tuple[float, ...]) -> Any:
    from tudatpy.dynamics import environment_setup

    return environment_setup.ephemeris.constant(
        np.array(position + (0.0,) * 3), "SSB", "J2000"
    )


def zero() -> Any:
    return native.build_sources((), (), idle)


def context() -> Any:
    end = monotonic() + 15.0

    def check() -> None:
        if monotonic() > end:
            raise RuntimeError("synthetic component deadline15s")

    return native.Context(check)


def raw_history() -> dict[str, Any]:
    return {
        "state_history": {
            0.0: np.array([0.0, 0.0, 0.0, 2.0, 3.0, 4.0]),
            1.0: np.array([2.0, 3.0, 4.0, 2.0, 3.0, 4.0]),
        },
        "dependent_variable_history": {0.0: np.zeros(3), 1.0: np.zeros(3)},
        "integration_completed": True,
    }


def validate(
    raw: dict[str, Any], check: Any = idle, guard: Any = no_guard
) -> dict[str, Any]:
    return native.validate_history(
        raw, (0.0, 0.0, 0.0, 2.0, 3.0, 4.0), 0.0, 1.0, 1.0, (0.0, 1.0), (), check, guard
    )


def test_lightweight_import() -> None:
    script = f"import runpy,sys;runpy.run_path({str(PATH)!r});assert not any(k.startswith(('tudatpy','numpy','scipy','spiceypy','space_nav')) for k in sys.modules)"
    subprocess.run([sys.executable, "-c", script], check=True, capture_output=True)


@pytest.mark.parametrize("value", [True, None, "1", math.nan, math.inf, 10**1000])
def test_finite_numbers(value: object) -> None:
    with pytest.raises(native.NativeError):
        native.number(value)


@pytest.mark.parametrize("value", [(), (1.0,) * 5, (1.0,) * 5 + (True,)])
def test_cartesian_shape_and_values(value: object) -> None:
    with pytest.raises(native.NativeError):
        native.vector(value, 6)


def test_synthetic_zero_force_exact_line() -> None:
    c = context()
    # Multiples of3 keep all RK4 weighted increments exactly representable.
    result = native.propagate(
        zero(), (0.0, 0.0, 0.0, 3.0, 6.0, 12.0), 0.0, 1.0, 1.0, (0.0, 1.0), c, no_guard
    )
    assert result["samples"][-1]["state"] == (3.0, 6.0, 12.0, 3.0, 6.0, 12.0)
    assert result["samples"][0]["acceleration_m_s2"] == (0.0, 0.0, 0.0)
    assert result["retained_states"] == result["guarded_states"] == 2
    assert (c.arcs_attempted, c.arcs_returned, c.arcs_completed) == (1, 1, 1)


@pytest.mark.parametrize("step", [1.0, 0.5])
def test_native_circular_orbit_against_closed_form(step: float) -> None:
    c = context()
    mu = 1e12
    radius = 1e7
    omega = math.sqrt(mu / radius**3)
    prepared = native.build_sources(
        (("C", mu, constant((0.0, 0.0, 0.0))),), ("C",), c.check
    )
    result = native.propagate(
        prepared,
        (radius, 0.0, 0.0, 0.0, radius * omega, 0.0),
        0.0,
        300.0,
        step,
        native.OFFSETS,
        c,
        no_guard,
    )
    assert result["retained_states"] == int(300 / step) + 1
    for point in result["samples"]:
        angle = omega * point["epoch_tdb_s"]
        state = point["state"]
        expected = (
            radius * math.cos(angle),
            radius * math.sin(angle),
            0.0,
            -radius * omega * math.sin(angle),
            radius * omega * math.cos(angle),
            0.0,
        )
        assert math.dist(state[:3], expected[:3]) <= 1e-6
        assert math.dist(state[3:], expected[3:]) <= 1e-8
        expected_a = tuple(-mu * x / radius**3 for x in expected[:3])
        assert math.dist(point["acceleration_m_s2"][:3], expected_a) <= 1e-12
        assert math.dist(point["acceleration_m_s2"][3:], expected_a) <= 1e-12


def test_native_direct_ssb_sources_against_decimal80() -> None:
    c = context()
    prepared = native.build_sources(
        (
            ("Sun", 8.0, constant((3.0, 0.0, 0.0))),
            ("Moon", 9.0, constant((1.0, 3.0, 0.0))),
            ("Earth", 16.0, constant((1.0, 0.0, 4.0))),
        ),
        native.BODIES,
        c.check,
    )
    result = native.propagate(
        prepared, (1.0, 0.0, 0.0, 0.0, 0.0, 0.0), 0.0, 1.0, 0.5, (0.0, 1.0), c, no_guard
    )
    first = result["samples"][0]["acceleration_m_s2"]
    with localcontext() as ctx:
        ctx.prec = 80
        exact = (
            Decimal(8) / Decimal(2) ** 2,
            Decimal(9) / Decimal(3) ** 2,
            Decimal(16) / Decimal(4) ** 2,
        )
        assert max(
            abs(Decimal.from_float(v) - x)
            for v, x in zip(first[:3], exact, strict=True)
        ) <= Decimal("1e-14")
    assert first[3:] == pytest.approx(
        (2.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0), abs=1e-14, rel=0
    )
    assert first[0] != pytest.approx(
        2.0 - 8.0 / 9.0, abs=1e-14, rel=0
    )  # Reject indirect Sun-origin forcing.
    assert result["force_order"] == ("total", "Sun", "Moon", "Earth")


@pytest.mark.parametrize(
    "mutation,message",
    [
        ("incomplete", "incomplete"),
        ("missing", "count/profile"),
        ("reordered", "time order"),
        ("epoch", "fixed-step"),
        ("initial", "initial-state"),
        ("nan", "finite"),
        ("dependent_epoch", "force-history"),
        ("force_shape", "shape"),
        ("force_nan", "finite"),
    ],
)
def test_history_gates(mutation: str, message: str) -> None:
    raw = raw_history()
    if mutation == "incomplete":
        raw["integration_completed"] = False
    if mutation == "missing":
        raw["state_history"].pop(1.0)
    if mutation == "reordered":
        raw["state_history"] = dict(reversed(list(raw["state_history"].items())))
    if mutation == "epoch":
        raw["state_history"][1.0 + 5e-7] = raw["state_history"].pop(1.0)
        raw["dependent_variable_history"][1.0 + 5e-7] = raw[
            "dependent_variable_history"
        ].pop(1.0)
    if mutation == "initial":
        raw["state_history"][0.0][0] = 1.0
    if mutation == "nan":
        raw["state_history"][1.0][0] = math.nan
    if mutation == "dependent_epoch":
        raw["dependent_variable_history"].pop(1.0)
    if mutation == "force_shape":
        raw["dependent_variable_history"][1.0] = np.zeros(4)
    if mutation == "force_nan":
        raw["dependent_variable_history"][1.0][0] = math.nan
    with pytest.raises(native.NativeError, match=message):
        validate(raw)


def test_actual_force_total_requires_sum() -> None:
    raw = raw_history()
    raw["dependent_variable_history"] = {
        at: np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0]) for at in (0.0, 1.0)
    }
    with pytest.raises(native.NativeError, match="total/source"):
        native.validate_history(
            raw,
            (0.0, 0.0, 0.0, 2.0, 3.0, 4.0),
            0.0,
            1.0,
            1.0,
            (0.0, 1.0),
            ("C",),
            idle,
            no_guard,
        )


def test_every_retained_state_guarded_and_deadline_checked() -> None:
    checked = []
    result = validate(
        raw_history(), guard=lambda at, state: checked.append((at, state))
    )
    assert [at for at, _ in checked] == [0.0, 1.0]
    assert result["guarded_states"] == 2
    with pytest.raises(RuntimeError, match="deadline"):
        validate(
            raw_history(), check=lambda: (_ for _ in ()).throw(RuntimeError("deadline"))
        )


def fake_engine(raw: dict[str, Any]) -> Any:
    return SimpleNamespace(
        state_history=raw["state_history"],
        dependent_variable_history=raw["dependent_variable_history"],
        integration_completed_successfully=raw["integration_completed"],
    )


def test_returned_history_survives_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    from tudatpy.dynamics import simulator

    raw = raw_history()
    returned = False

    def create(*args: object) -> Any:
        nonlocal returned
        returned = True
        return fake_engine(raw)

    def check() -> None:
        if returned:
            raise RuntimeError("deadline")

    monkeypatch.setattr(simulator, "create_dynamics_simulator", create)
    c = native.Context(check)
    with pytest.raises(native.ReturnedNativeFailure, match="deadline") as caught:
        native.propagate(
            zero(),
            (0.0, 0.0, 0.0, 2.0, 3.0, 4.0),
            0.0,
            1.0,
            1.0,
            (0.0, 1.0),
            c,
            no_guard,
        )
    assert caught.value.returned is c.last_returned
    assert c.last_returned["state_history"] is raw["state_history"]
    assert (c.arcs_attempted, c.arcs_returned, c.arcs_completed) == (1, 1, 0)


def test_native_error_counts_attempt_without_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tudatpy.dynamics import simulator

    def fail(*args: object) -> Any:
        raise RuntimeError("native fixture failure")

    monkeypatch.setattr(simulator, "create_dynamics_simulator", fail)
    c = native.Context(idle)
    with pytest.raises(native.NativeError, match="native fixture failure"):
        native.propagate(
            zero(),
            (0.0, 0.0, 0.0, 2.0, 3.0, 4.0),
            0.0,
            1.0,
            1.0,
            (0.0, 1.0),
            c,
            no_guard,
        )
    assert (c.arcs_attempted, c.arcs_returned, c.arcs_completed) == (1, 0, 0)


def test_fifth_attempt_stops_before_native_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tudatpy.dynamics import simulator

    def forbidden(*args: object) -> Any:
        pytest.fail("fifth native call")

    monkeypatch.setattr(simulator, "create_dynamics_simulator", forbidden)
    c = native.Context(idle, arcs_attempted=4)
    with pytest.raises(native.NativeError, match="cap4"):
        native.propagate(
            zero(),
            (0.0, 0.0, 0.0, 2.0, 3.0, 4.0),
            0.0,
            1.0,
            1.0,
            (0.0, 1.0),
            c,
            no_guard,
        )


@pytest.mark.parametrize(
    "duration,step,offsets",
    [
        (1.0, 2.0, (0.0, 1.0)),
        (-1.0, 1.0, (0.0, 1.0)),
        (1.0, True, (0.0, 1.0)),
        (1.0, 1.0, (0.0, 0.0)),
        (1.0, 1.0, (0.0, 0.5)),
        (1.0, 1.0, (0.0, True)),
    ],
)
def test_profile_and_sample_rejection(
    duration: object, step: object, offsets: tuple
) -> None:
    with pytest.raises(native.NativeError):
        native.propagate(
            zero(),
            (0.0,) * 6,
            0.0,
            duration,
            step,
            offsets,
            native.Context(idle),
            no_guard,
        )


@pytest.mark.parametrize("bad", [None, 0, 1, "tight"])
def test_frozen_wrapper_profile_rejection(bad: object) -> None:
    with pytest.raises(native.NativeError):
        native.solve_model((0.0,) * 6, 0.0, "A", bad, native.Context(idle))


def test_frozen_wrapper_binds_inputs_without_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handle = SimpleNamespace(gravity_parameters_m3_s2=dict(native.GM))
    seen = []
    monkeypatch.setattr(native, "build_model", lambda model, check: handle)

    def fake(*args: Any) -> dict[str, Any]:
        seen.append(args)
        return {}

    monkeypatch.setattr(native, "propagate", fake)
    for tight, step in [(False, 1.0), (True, 0.5)]:
        r = native.solve_model((0.0,) * 6, 0.0, "B", tight, native.Context(idle))
        assert seen[-1][3:6] == (300.0, step, native.OFFSETS)
        assert r["model"] == "B"


def test_inventory_ignores_map_order_but_rejects_extras_and_gm_drift() -> None:
    p = native.build_sources(
        (
            ("Sun", 8.0, constant((3.0, 0.0, 0.0))),
            ("Moon", 9.0, constant((0.0, 3.0, 0.0))),
        ),
        ("Sun", "Moon"),
        idle,
    )
    p.accelerations["Spacecraft"] = {
        k: p.accelerations["Spacecraft"][k]
        for k in reversed(tuple(p.accelerations["Spacecraft"]))
    }
    native.validate_inventory(p)
    p.bodies.get("Sun").gravity_field_model.gravitational_parameter = 8.1
    with pytest.raises(native.NativeError, match="GM mismatch"):
        native.validate_inventory(p)
    p.bodies.get("Sun").gravity_field_model.gravitational_parameter = 8.0
    p.accelerations["Spacecraft"]["Extra"] = p.accelerations["Spacecraft"]["Sun"]
    with pytest.raises(native.NativeError, match="sources mismatch"):
        native.validate_inventory(p)


@pytest.mark.parametrize("mu", [0.0, -1.0, True, math.inf])
def test_invalid_source_gm(mu: object) -> None:
    with pytest.raises(native.NativeError):
        native.build_sources((("C", mu, constant((0.0, 0.0, 0.0))),), ("C",), idle)


def test_actual_spice_environment_at_time_zero() -> None:
    from space_nav import ephemeris
    from tudatpy.interface import spice

    ephemeris.kernel_metadata()
    for model, expected_sources in [("A", ("Sun", "Moon")), ("B", native.BODIES)]:
        prepared = native.build_model(model, idle)
        assert set(prepared.accelerations["Spacecraft"]) == set(expected_sources)
        for body in native.BODIES:
            state = (
                prepared.bodies.get(body)
                .ephemeris.cartesian_state(0.0)
                .reshape(-1)
                .tolist()
            )
            expected = spice.get_body_cartesian_state_at_epoch(
                body, "SSB", "J2000", "NONE", 0.0
            )
            assert math.dist(state[:3], expected[:3]) <= 0.001
            assert math.dist(state[3:], expected[3:]) <= 1e-6
            assert (
                prepared.bodies.get(body).gravity_field_model.gravitational_parameter
                == native.GM[body]
            )


@pytest.mark.parametrize("body", native.BODIES)
def test_frozen_guard_rejects_surface_including_omitted_earth(
    body: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    radius = native.GUARDS[body]

    class Bodies:
        def get(self, name: str) -> Any:
            def state(at: float) -> Any:
                position = (0.0, 0.0, 0.0) if name == body else (2e12, 0.0, 0.0)
                return np.array(position + (0.0,) * 3)

            return SimpleNamespace(ephemeris=SimpleNamespace(cartesian_state=state))

    prepared = SimpleNamespace(
        bodies=Bodies(), gravity_parameters_m3_s2=dict(native.GM)
    )
    monkeypatch.setattr(native, "build_model", lambda *_: prepared)

    def fake(*args: Any) -> dict[str, Any]:
        args[-1](0.0, (radius, 0.0, 0.0, 0.0, 0.0, 0.0))
        return {}

    monkeypatch.setattr(native, "propagate", fake)
    c = native.Context(idle)
    with pytest.raises(native.NativeError, match=body + " exclusion sphere"):
        native.solve_model((radius, 0.0, 0.0, 0.0, 0.0, 0.0), 0.0, "A", False, c)
    assert c.guard_reads_attempted == c.guard_reads_returned
    assert c.minimum_checked_distances_m[body] == radius


def test_guard_keeps_returned_raw_before_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    returned = False
    state = np.array([1e12, 0.0, 0.0, 0.0, 0.0, 0.0])

    class Bodies:
        def get(self, name: str) -> Any:
            def query(at: float) -> Any:
                nonlocal returned
                returned = True
                return state

            return SimpleNamespace(ephemeris=SimpleNamespace(cartesian_state=query))

    p = SimpleNamespace(bodies=Bodies(), gravity_parameters_m3_s2=dict(native.GM))
    monkeypatch.setattr(native, "build_model", lambda *_: p)

    def fake(*args: Any) -> dict[str, Any]:
        args[-1](0.0, (0.0,) * 6)
        return {}

    monkeypatch.setattr(native, "propagate", fake)

    def check() -> None:
        if returned:
            raise RuntimeError("after guard query deadline")

    c = native.Context(check)
    with pytest.raises(RuntimeError, match="after guard query"):
        native.solve_model((0.0,) * 6, 0.0, "A", False, c)
    assert c.last_guard_state is state
    assert c.guard_reads_attempted == c.guard_reads_returned == 1


@pytest.mark.parametrize(
    "problem", ["duplicate", "reserved", "missing", "frame", "count"]
)
def test_source_construction_and_inventory_errors(problem: str) -> None:
    sources = (("C", 8.0, constant((3.0, 0.0, 0.0))),)
    included = ("C",)
    if problem == "duplicate":
        sources = sources + sources
    if problem == "reserved":
        sources = (("Spacecraft", 8.0, constant((3.0, 0.0, 0.0))),)
    if problem == "missing":
        included = ("Unknown",)
    if problem == "frame":
        from tudatpy.dynamics import environment_setup

        sources = (
            (
                "C",
                8.0,
                environment_setup.ephemeris.constant(np.zeros(6), "Sun", "J2000"),
            ),
        )
    if problem == "count":
        p = native.build_sources(sources, included, idle)
        p.accelerations["Spacecraft"]["C"].append(p.accelerations["Spacecraft"]["C"][0])
        with pytest.raises(native.NativeError, match="counts"):
            native.validate_inventory(p)
        return
    with pytest.raises(native.NativeError):
        native.build_sources(sources, included, idle)


@pytest.mark.parametrize(
    "problem", ["raw_mapping", "force_mapping", "raw_array", "force_array"]
)
def test_malformed_native_output(problem: str) -> None:
    raw = raw_history()
    if problem == "raw_mapping":
        raw["state_history"] = None
    if problem == "force_mapping":
        raw["dependent_variable_history"] = None
    if problem == "raw_array":
        raw["state_history"][1.0] = None
    if problem == "force_array":
        raw["dependent_variable_history"][1.0] = None
    with pytest.raises(native.NativeError):
        validate(raw)


def test_exact_sampling_node_cannot_be_interpolated() -> None:
    raw = raw_history()
    with pytest.raises(native.NativeError, match="exact sample epoch missing"):
        native.validate_history(
            raw,
            (0.0, 0.0, 0.0, 2.0, 3.0, 4.0),
            0.0,
            1.0,
            1.0,
            (0.0, 0.5, 1.0),
            (),
            idle,
            no_guard,
        )


def test_no_shared_oracle_or_production_force_implementation() -> None:
    source = PATH.read_text()
    assert not any(
        term in source
        for term in ["space_nav", "0138-short-coast-oracle", "scipy", "spiceypy"]
    )


def test_coarse_epoch_rejected_before_propagation() -> None:
    with pytest.raises(native.NativeError, match="time resolution"):
        native.propagate(
            zero(),
            (0.0,) * 6,
            1e18,
            300.0,
            0.5,
            (0.0, 300.0),
            native.Context(idle),
            no_guard,
        )
