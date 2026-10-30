"""Native-free preparation tests; mock equality is NOT physical validation."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "docs/adr/experiments/0121-elliptic-coast.py"
spec = importlib.util.spec_from_file_location("r1_elliptic_benchmark", SCRIPT)
assert spec is not None and spec.loader is not None
bench = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bench
spec.loader.exec_module(bench)


@pytest.fixture(autouse=True)
def no_native(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent even accidental scientific imports in this test module."""
    import builtins

    original = builtins.__import__

    def guarded(name: str, *args: Any, **kwargs: Any) -> Any:
        assert not name.startswith(("tudatpy", "spiceypy")), name
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)


@pytest.fixture
def prepared(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []

    def fake(initial: tuple[float, ...], elapsed: float, gm: float) -> tuple[float, ...]:
        calls.append((initial, elapsed, gm))
        return bench.oracle(elapsed).state

    monkeypatch.setattr(bench, "provenance", lambda: {"mode": "test-only mock"})
    monkeypatch.setattr(bench, "load_adapter", lambda: fake)
    return calls


def test_frozen_source_and_closed_forms() -> None:
    bench.source_check()
    bench.self_check()
    assert math.dist(bench.oracle(0).state, bench.INITIAL) < .001
    # Independent quarter-ellipse Cartesian point: E=pi/2, not M=pi/2.
    elapsed = (math.pi / 2 - bench.ECC) / bench.MEAN_MOTION_RAD_S
    state = bench.oracle(elapsed).state
    x, y = -bench.A_M * bench.ECC, bench.A_M * math.sqrt(1 - bench.ECC**2)
    expected_r = tuple(x * p + y * q for p, q in zip(bench.P, bench.Q))
    expected_v = tuple(-bench.A_M * bench.MEAN_MOTION_RAD_S * p for p in bench.P)
    assert math.dist(state[:3], expected_r) <= .01
    assert math.dist(state[3:], expected_v) <= 1e-8


@pytest.mark.parametrize("fraction", [i / 16 for i in range(17)])
def test_root_and_independent_invariants(fraction: float) -> None:
    result = bench.oracle(bench.PERIOD_S * fraction)
    assert result.updates <= 64
    assert result.bracket_width_rad <= 2e-14
    assert result.residual_rad <= 2e-14
    r, v = result.state[:3], result.state[3:]
    # Vis-viva and fixed orbital plane do not use comparison/invariants helpers.
    assert abs(sum(x*x for x in v) - bench.GM_M3_S2*(2/math.hypot(*r)-1/bench.A_M)) < .01
    normal = (-.48, -.64, .6)
    assert abs(sum(x*y for x, y in zip(r, normal))) < .001


@pytest.mark.parametrize("elapsed", [True, -1, math.nan, math.inf, "seconds"])
def test_oracle_rejects_bad_time(elapsed: Any) -> None:
    with pytest.raises(bench.GateFailure):
        bench.oracle(elapsed)


def test_root_failure_and_wrong_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bench, "MAX_BISECTIONS", 0)
    with pytest.raises(bench.GateFailure, match="root"):
        bench.oracle(100.)
    monkeypatch.setattr(bench, "MAX_BISECTIONS", 64)
    monkeypatch.setattr(bench, "Q", bench.P)
    with pytest.raises(bench.GateFailure, match="basis"):
        bench.self_check()


@pytest.mark.parametrize("value", [(), (1,)*5, (1,)*7, None, [True]*6,
                                  [math.nan]*6, [math.inf]*6, ["1"]*6])
def test_state_boundary(value: Any) -> None:
    with pytest.raises(bench.GateFailure):
        bench.finite_state(value)


def test_mock_schedule_and_exact_elapsed(prepared: list[tuple[Any, ...]]) -> None:
    report = bench.run(lambda: 0.0)
    assert report["status"] == "passed"
    assert len(prepared) == report["attempted_adapter_calls"] == report["completed_adapter_calls"] == 17
    for index, (initial, elapsed, gm) in enumerate(prepared):
        assert initial == bench.INITIAL and gm == bench.GM_M3_S2
        assert elapsed == (bench.T0_TDB_S + index * bench.PERIOD_S / 16) - bench.T0_TDB_S
        assert report["points"][index]["elapsed_s"] == elapsed
    assert any(elapsed != i * bench.PERIOD_S / 16
               for i, (_, elapsed, _) in enumerate(prepared))
    assert report["mass"] == {"status": "not-modelled", "error_kg": None}


@pytest.mark.parametrize("component,delta", [(0, 1.1), (3, 1.1e-6)])
def test_first_mismatch_stops_and_retains(
    prepared: list[tuple[Any, ...]], monkeypatch: pytest.MonkeyPatch,
    component: int, delta: float,
) -> None:
    def wrong(initial: Any, elapsed: float, gm: float) -> tuple[float, ...]:
        state = list(bench.oracle(elapsed).state)
        state[component] += delta
        return tuple(state)

    monkeypatch.setattr(bench, "load_adapter", lambda: wrong)
    report = bench.run(lambda: 0.)
    assert report["status"] == "failed"
    assert report["attempted_adapter_calls"] == report["completed_adapter_calls"] == 1
    assert "comparison" in report["points"][0]
    assert report["points"][0]["status"] == "failed"


@pytest.mark.parametrize("value", [(0.,)*5, (math.nan,)*6, (True,)*6])
def test_malformed_output_is_finite_json(
    prepared: list[tuple[Any, ...]], monkeypatch: pytest.MonkeyPatch, value: Any,
) -> None:
    monkeypatch.setattr(bench, "load_adapter", lambda: lambda *args: value)
    report = bench.run(lambda: 0.)
    assert report["status"] == "failed" and report["completed_adapter_calls"] == 1
    assert "native_state" in report["points"][0]
    json.dumps(report, allow_nan=False)


def test_invariant_gate_independent_of_pair_agreement() -> None:
    wrong = bench.INITIAL[:3] + tuple(v * 1.01 for v in bench.INITIAL[3:])
    values = bench.comparison(wrong, wrong)
    assert values["position_error_m"] == values["velocity_error_m_s"] == 0
    with pytest.raises(bench.GateFailure, match="invariant"):
        bench.check_comparison(values)


def test_native_failure_counts_attempt_not_completion(
    prepared: list[tuple[Any, ...]], monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: Any) -> None:
        raise bench.GateFailure("fake native failure")

    monkeypatch.setattr(bench, "load_adapter", lambda: fail)
    report = bench.run(lambda: 0.)
    assert report["status"] == "failed"
    assert (report["attempted_adapter_calls"], report["completed_adapter_calls"]) == (1, 0)
    assert report["calls"][-1]["returned"] is False


def test_expired_preflight_and_overrun_retains_state(
    prepared: list[tuple[Any, ...]], monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.]
    budget = bench.Budget(lambda: now[0])
    now[0] = 30.
    with pytest.raises(bench.GateFailure, match="before"):
        budget.call("forbidden", lambda: pytest.fail("launched"))
    assert budget.calls == []
    now[0] = 0.

    def slow(initial: Any, elapsed: float, gm: float) -> tuple[float, ...]:
        now[0] = 30.001
        return bench.oracle(elapsed).state

    monkeypatch.setattr(bench, "load_adapter", lambda: slow)
    report = bench.run(lambda: now[0])
    assert report["status"] == "failed" and report["completed_adapter_calls"] == 1
    assert "native_state" in report["points"][0]
    assert report["elapsed_seconds"] == 30.001


def test_unavailable_before_launch_and_changed_provenance(
    prepared: list[tuple[Any, ...]], monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable() -> None:
        raise bench.Unavailable("no build metadata")

    monkeypatch.setattr(bench, "provenance", unavailable)
    report = bench.run(lambda: 0.)
    assert report["status"] == "unavailable" and report["attempted_adapter_calls"] == 0
    snapshots = iter([{"build": 1}, {"build": 2}])
    monkeypatch.setattr(bench, "provenance", lambda: next(snapshots))
    report = bench.run(lambda: 0.)
    assert report["status"] == "failed" and report["completed_adapter_calls"] == 17
    assert "provenance changed" in report["error"]["message"]


def test_exclusive_creation_never_recomputes(tmp_path: Path) -> None:
    target = tmp_path / "test-only.json"
    bench.write_exclusive(target, lambda: {"status": "test-only"})
    with pytest.raises(FileExistsError):
        bench.write_exclusive(target, lambda: pytest.fail("recomputed"))
    assert json.loads(target.read_text()) == {"status": "test-only"}


def test_inclusive_thresholds_and_vector_momentum() -> None:
    bench.check_comparison({"position_error_m": 1., "velocity_error_m_s": 1e-6,
                            "invariants": {"test": {"energy": 1e-12, "h": 1e-12}}})
    reversed_v = bench.INITIAL[:3] + tuple(-v for v in bench.INITIAL[3:])
    values = bench.comparison(reversed_v, reversed_v)
    assert values["invariants"]["native"]["relative_energy_error"] == 0
    assert values["invariants"]["native"]["relative_angular_momentum_error"] == 2
    with pytest.raises(bench.GateFailure, match="invariant"):
        bench.check_comparison(values)


def test_partial_failure_retains_prior_points(
    prepared: list[tuple[Any, ...]], monkeypatch: pytest.MonkeyPatch,
) -> None:
    count = [0]

    def partly_wrong(initial: Any, elapsed: float, gm: float) -> tuple[float, ...]:
        count[0] += 1
        state = list(bench.oracle(elapsed).state)
        if count[0] == 9:
            state[0] += 2.
        return tuple(state)

    monkeypatch.setattr(bench, "load_adapter", lambda: partly_wrong)
    report = bench.run(lambda: 0.)
    assert report["status"] == "failed" and count[0] == 9
    assert all(p["status"] == "passed" for p in report["points"][:8])
    assert report["points"][-1]["status"] == "failed"


def test_source_mismatch_stops_without_import(
    prepared: list[tuple[Any, ...]], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bench, "digest", lambda path: "wrong")
    report = bench.run(lambda: 0.)
    assert report["status"] == "unavailable" and not prepared
    assert report["attempted_adapter_calls"] == 0


def test_adapter_wrapper_translates_domain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from space_nav import explorer
    from space_nav.errors import TransferSearchError

    def unavailable(*args: Any) -> None:
        raise TransferSearchError("test-only resource failure")

    monkeypatch.setattr(explorer, "propagate_two_body", unavailable)
    with pytest.raises(bench.GateFailure, match="native coast adapter") as caught:
        bench.load_adapter()(bench.INITIAL, 0., bench.GM_M3_S2)
    assert isinstance(caught.value.__cause__, TransferSearchError)


def test_provenance_with_fake_modules_and_missing_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from types import SimpleNamespace

    binary = tmp_path / "fake-kernel.so"
    binary.write_bytes(b"test-only binary placeholder")
    modules = {
        "space_nav": SimpleNamespace(__file__=str(bench.ROOT / "src/space_nav/__init__.py")),
        "tudatpy": SimpleNamespace(__version__="1.0.0", __file__="fake-tudatpy.py"),
        "tudatpy.kernel": SimpleNamespace(__file__=str(binary)),
        "tudatpy.kernel.astro.element_conversion": SimpleNamespace(),
        "tudatpy.kernel.astro.two_body_dynamics": SimpleNamespace(),
    }
    monkeypatch.setattr(bench, "import_module", modules.__getitem__)
    monkeypatch.setattr(bench, "version", lambda name: "1.26.4")
    result = bench.provenance()
    assert result["native_binary_sha256"] == {str(binary): bench.digest(binary)}
    assert result["spice_requests"] == 0
    modules["tudatpy.kernel"] = SimpleNamespace()
    with pytest.raises(bench.Unavailable, match="binary location"):
        bench.provenance()


@pytest.mark.parametrize("version", ["unknown", "1.1.0"])
def test_wrong_versions_fail_without_native_modules(
    monkeypatch: pytest.MonkeyPatch, version: str,
) -> None:
    from types import SimpleNamespace

    modules = {"space_nav": SimpleNamespace(), "tudatpy": SimpleNamespace(__version__=version)}
    monkeypatch.setattr(bench, "import_module", modules.__getitem__)
    with pytest.raises(bench.Unavailable, match="pinned"):
        bench.provenance()


def test_final_timing_capture_cannot_claim_overrun_success(prepared: list[tuple[Any, ...]]) -> None:
    readings = [0]

    def count_clock() -> float:
        readings[0] += 1
        return 0.

    assert bench.run(count_clock)["status"] == "passed"
    final_read = readings[0]
    readings[0] = 0

    def late_final_clock() -> float:
        readings[0] += 1
        return 30.001 if readings[0] == final_read else 0.

    report = bench.run(late_final_clock)
    assert report["status"] == "failed" and report["elapsed_seconds"] == 30.001
    assert "final timing" in report["error"]["message"]
