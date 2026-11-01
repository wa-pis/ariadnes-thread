"""Native-free R3 preparation; synthetic body snapshots are not physical evidence."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0132-gravity-screen.py"
spec = importlib.util.spec_from_file_location("r3_gravity_screen_tests", PATH)
assert spec and spec.loader
r3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r3)


@pytest.fixture(autouse=True)
def no_native(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    original = builtins.__import__

    def guard(name: str, *args: Any, **kwargs: Any) -> Any:
        assert not name.startswith(("tudatpy", "spiceypy", "numpy", "scipy")), name
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)


def identity() -> dict[str, Any]:
    return {"kernels": deepcopy(r3.load_inputs()["kernels"]), "test_only": True}


def provider(body: str, epoch: float) -> dict[str, Any]:
    inputs = r3.load_inputs()
    row = next(r for r in inputs["rows"] if r["epoch_tdb_s"] == epoch)
    shift = {"Earth": 1e9, "Moon": 2e9, "Mars": 3e9}[body]
    return {
        "body": body,
        "epoch_tdb_s": epoch,
        "epoch_utc": "2031-01-01T00:00:00Z",
        "origin": "SSB",
        "orientation": "J2000",
        "position_m": [v + shift for v in row["spacecraft"]["position_m"]],
        "velocity_m_s": [0.0, 0.0, 0.0],
    }


def invoke(**kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    stream = kwargs.pop("stream", io.StringIO())
    result = r3.run(
        stream,
        identity=kwargs.pop("identity", identity),
        provider=kwargs.pop("provider", provider),
        gm_provider=kwargs.pop("gm_provider", lambda: 3.986004354e14),
        **kwargs,
    )
    return result, json.loads(stream.getvalue())


def test_real_frozen_inputs_and_synthetic_self_checks() -> None:
    inputs = r3.load_inputs()
    r3.validate_inputs(inputs)
    assert [v["index"] for v in inputs["rows"]] == [0, 60, 120]
    r3.self_check()


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("sign", [-1, 1])
def test_closed_form_rotation_and_sign(axis: int, sign: int) -> None:
    x = [0.0, 0.0, 0.0]
    b = [0.0, 0.0, 0.0]
    x[axis] = float(sign)
    b[axis] = 3.0 * sign
    term = r3.force(x, b, 8.0, 0.0)
    expected = [0.0, 0.0, 0.0]
    expected[axis] = sign * 10 / 9
    assert math.dist(term["differential_m_s2"], expected) < 1e-14
    r3.independent.check_term(term)
    assert abs(
        Decimal(term["decimal"]["differential"][axis])
        - Decimal(sign) * Decimal(10) / Decimal(9)
    ) < Decimal("1e-26")


def test_tilted_rotation_and_translated_ssb_inputs() -> None:
    q = (0.36, 0.48, 0.8)
    expected = tuple(10 / 9 * v for v in q)
    shift = (1e9, -2e9, 3e9)
    x = tuple((q[i] + shift[i]) - shift[i] for i in range(3))
    b = tuple((3 * q[i] + shift[i]) - shift[i] for i in range(3))
    result = r3.force(x, b, 8.0, 0.0)
    r3.independent.check_term(result)
    assert math.dist(result["differential_m_s2"], expected) < 2e-6
    exact = r3.force(q, tuple(3 * v for v in q), 8.0, 0.0)
    assert math.dist(exact["differential_m_s2"], expected) < 1e-14


@pytest.mark.parametrize("distance", [1e4, 1e8, 1e12])
def test_small_differential_cancellation(distance: float) -> None:
    result = r3.force((1.0, 2.0, 3.0), (distance, 2 * distance, -distance), 8.0, 0.0)
    r3.independent.check_term(result)


@pytest.mark.parametrize("guard", [2.0, 3.0, 4.0])
def test_guard_boundary(guard: float) -> None:
    term = r3.force((1.0, 0.0, 0.0), (3.0, 0.0, 0.0), 8.0, guard)
    assert term["status"] == "inadmissible"
    assert "differential_m_s2" not in term and "norm_m_s2" not in term
    r3.independent.check_term(term)


@pytest.mark.parametrize(
    "bad", [True, None, "1", float("nan"), float("inf"), -1.0, 0.0]
)
def test_bad_gm(bad: object) -> None:
    with pytest.raises((r3.common.GateFailure, ValueError)):
        r3.force((1.0, 0.0, 0.0), (3.0, 0.0, 0.0), bad, 0.0)


@pytest.mark.parametrize(
    "bad", [(), (1.0, 2.0), (True, 0.0, 0.0), (float("nan"), 0.0, 0.0)]
)
def test_bad_positions(bad: object) -> None:
    with pytest.raises(r3.common.GateFailure):
        r3.force(bad, (3.0, 0.0, 0.0), 8.0, 0.0)


@pytest.mark.parametrize(
    "corruption",
    ["indirect_sign", "differential", "direct", "decimal", "distance", "domain"],
)
def test_independent_oracle_rejects_corruption(corruption: str) -> None:
    term = r3.common.safe_json(r3.force((1.0, 0.0, 0.0), (3.0, 0.0, 0.0), 8.0, 0.0))
    if corruption == "indirect_sign":
        term["indirect_m_s2"][0] *= -1
    elif corruption == "differential":
        term["differential_m_s2"][0] = 0.0
    elif corruption == "direct":
        term["direct_m_s2"][0] = 0.0
    elif corruption == "decimal":
        term["decimal"]["differential"][0] = "0"
    elif corruption == "distance":
        term["distance_m"] = 1.0
    else:
        term["status"] = "inadmissible"
    with pytest.raises(ValueError):
        r3.independent.check_term(term)


def test_mock_success_all_terms_counts_order_and_audit() -> None:
    report, written = invoke()
    assert report == written
    assert report["status"] == "passed", report.get("error")
    assert report["counts"] == {
        "states_attempted": 7,
        "states_completed": 7,
        "earth_gm_attempted": 1,
        "earth_gm_completed": 1,
    }
    assert report["rows"][0]["terms"]["Moon"]["status"] == "inadmissible"
    assert report["rows"][-1]["terms"]["Mars"]["status"] == "inadmissible"
    assert (
        report["rows"][0]["summary"] is None and report["rows"][-1]["summary"] is None
    )
    result = r3.independent.audit(written)
    assert result == {
        "audit": "passed",
        "screening_status": "passed",
        "terms_checked": 9,
        "screening_verified": True,
    }


@pytest.mark.parametrize(
    "body,epoch_index",
    [
        ("Earth", 0),
        ("Mars", 0),
        ("Earth", 60),
        ("Moon", 60),
        ("Mars", 60),
        ("Earth", 120),
        ("Moon", 120),
    ],
)
def test_first_provider_failure_stops(body: str, epoch_index: int) -> None:
    epoch = next(
        r["epoch_tdb_s"] for r in r3.load_inputs()["rows"] if r["index"] == epoch_index
    )

    def fail(name: str, time: float) -> dict[str, Any]:
        if name == body and time == epoch:
            raise r3.common.Unavailable("synthetic coverage failure")
        return provider(name, time)

    report, written = invoke(provider=fail)
    position = r3.ORDER.index((body, epoch_index))
    assert report["status"] == "unavailable"
    assert report["counts"]["states_attempted"] == position + 1
    assert report["counts"]["states_completed"] == position
    assert r3.independent.audit(written)["screening_verified"] is False


@pytest.mark.parametrize(
    "key,value",
    [
        ("body", "Venus"),
        ("origin", "Sun"),
        ("orientation", "bad"),
        ("epoch_tdb_s", 0.0),
        ("position_m", [True, 0.0, 0.0]),
        ("position_m", [float("nan"), 0.0, 0.0]),
        ("velocity_m_s", []),
    ],
)
def test_returned_state_validation(key: str, value: object) -> None:
    def wrong(body: str, epoch: float) -> dict[str, Any]:
        return provider(body, epoch) | {key: value}

    report, _ = invoke(provider=wrong)
    assert report["status"] == "failed"
    assert (
        report["counts"]["states_attempted"]
        == report["counts"]["states_completed"]
        == 1
    )
    assert len(report["rows"]) == 1


@pytest.mark.parametrize("bad", [True, 0.0, -1.0, float("nan"), float("inf"), "GM"])
def test_gm_boundary_retains_raw_before_failure(bad: object) -> None:
    report, _ = invoke(gm_provider=lambda: bad)
    assert report["status"] == "failed" and report["counts"]["states_attempted"] == 0
    assert report["counts"]["earth_gm_completed"] == 1 and "raw_earth_gm" in report


def test_middle_domain_is_unavailable_not_zero_force() -> None:
    def interior(body: str, epoch: float) -> dict[str, Any]:
        value = provider(body, epoch)
        row = next(r for r in r3.load_inputs()["rows"] if r["epoch_tdb_s"] == epoch)
        if row["index"] == 60:
            value["position_m"] = row["spacecraft"]["position_m"]
        return value

    report, written = invoke(provider=interior)
    assert report["status"] == "unavailable"
    assert report["counts"]["states_attempted"] == 5
    assert report["rows"][-1]["terms"]["Earth"]["status"] == "inadmissible"
    assert not r3.independent.audit(written)["screening_verified"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x["rows"].reverse(),
        lambda x: x["rows"][0].update(epoch_tdb_s=0.0),
        lambda x: x["rows"][0]["spacecraft"].update(origin="Sun"),
        lambda x: x["gm_m3_s2"].update(Moon=1.0),
        lambda x: x["rows"][1]["spacecraft"]["position_m"].__setitem__(0, 1.0),
    ],
)
def test_input_corruption_before_queries(mutation: Any) -> None:
    inputs = r3.load_inputs()
    mutation(inputs)
    report, _ = invoke(loader=lambda: inputs)
    assert report["status"] == "failed"
    assert sum(report["counts"].values()) == 0


@pytest.mark.parametrize("which", ["initial", "final"])
def test_inventory_identity_failure(which: str) -> None:
    n = 0

    def snapshot() -> dict[str, Any]:
        nonlocal n
        n += 1
        value = identity()
        if which == "initial" or n == 2:
            value["kernels"]["kernels"].reverse()
        return value

    report, _ = invoke(identity=snapshot)
    assert report["status"] == "unavailable"
    assert report["counts"]["states_attempted"] == (0 if which == "initial" else 7)


@pytest.mark.parametrize("stage", ["inputs", "gm", "state", "identity", "flush"])
def test_cooperative_deadline(stage: str) -> None:
    now = [0.0]
    identity_count = 0

    class Stream(io.StringIO):
        def flush(self) -> None:
            if stage == "flush":
                now[0] = 31.0

    def inputs() -> dict[str, Any]:
        if stage == "inputs":
            now[0] = 31.0
        return r3.load_inputs()

    def gm() -> float:
        if stage == "gm":
            now[0] = 31.0
        return 3.986e14

    def states(body: str, epoch: float) -> dict[str, Any]:
        if stage == "state":
            now[0] = 31.0
        return provider(body, epoch)

    def snapshot() -> dict[str, Any]:
        nonlocal identity_count
        identity_count += 1
        if stage == "identity" and identity_count == 2:
            now[0] = 31.0
        return identity()

    result, written = invoke(
        clock=lambda: now[0],
        stream=Stream(),
        loader=inputs,
        provider=states,
        gm_provider=gm,
        identity=snapshot,
    )
    assert result["status"] == written["status"] == "failed"
    if stage == "state":
        assert result["counts"]["states_completed"] == 1
        assert "Earth" in result["rows"][0]["bodies"]
    if stage == "gm":
        assert "raw_earth_gm" in result


@pytest.mark.parametrize(
    "corruption",
    [
        lambda r: r["counts"].update(states_completed=6),
        lambda r: r.update(origin="SSB"),
        lambda r: r["guards_m"].update(Mars=1.0),
        lambda r: r["rows"][1]["summary"].update(sum_solar_ratio=0.0),
        lambda r: r["rows"][1]["terms"]["Earth"].update(solar_ratio=0.0),
        lambda r: r["rows"][0]["terms"]["Moon"].update(
            differential_m_s2=[0.0, 0.0, 0.0]
        ),
        lambda r: r["rows"][1]["bodies"]["Earth"].update(body="Venus"),
        lambda r: r["rows"][1]["terms"]["Earth"]["decimal"]["differential"].__setitem__(
            0, "0"
        ),
        lambda r: r["rows"].pop(),
    ],
)
def test_offline_audit_rejects_report_corruption(corruption: Any) -> None:
    _, written = invoke()
    corruption(written)
    with pytest.raises((ValueError, KeyError)):
        r3.independent.audit(written)


def test_exclusive_output_and_fresh_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "result.json"
    p.write_text("preserve")
    with pytest.raises(FileExistsError):
        r3.execute(p)
    assert p.read_text() == "preserve"
    monkeypatch.setitem(sys.modules, "space_nav.injected", object())
    with pytest.raises(r3.common.GateFailure, match="fresh"):
        r3.execute(tmp_path / "new.json")


def test_no_scientific_imports_in_subprocess() -> None:
    code = f"import runpy,sys;m=runpy.run_path({str(PATH)!r});m['self_check']();assert not any(k.startswith(('space_nav','tudatpy','spiceypy','numpy','scipy')) for k in sys.modules)"
    subprocess.run(
        [sys.executable, "-I", "-c", code], check=True, capture_output=True, text=True
    )


def test_numerical_failure_retains_term_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = r3.force

    def wrong(*args: Any, **kwargs: Any) -> dict[str, Any]:
        term = original(*args, **kwargs)
        if term["status"] == "admissible":
            term["differential_m_s2"] = (0.0, 0.0, 0.0)
        return term

    monkeypatch.setattr(r3, "force", wrong)
    # Pure self-check is tested separately; inject an evaluated-force failure.
    monkeypatch.setattr(r3, "self_check", lambda: None)
    report, written = invoke()
    assert report["status"] == "failed" and report["counts"]["states_attempted"] == 2
    assert "Earth" in written["rows"][0]["terms"]
    with pytest.raises(ValueError):
        r3.independent.audit(written)


def test_earth_gm_provider_exception_is_not_completion() -> None:
    def bad() -> float:
        raise r3.common.Unavailable("synthetic GM missing")

    report, written = invoke(gm_provider=bad)
    assert report["status"] == "unavailable"
    assert report["counts"] == {
        "states_attempted": 0,
        "states_completed": 0,
        "earth_gm_attempted": 1,
        "earth_gm_completed": 0,
    }
    assert not r3.independent.audit(written)["screening_verified"]


def test_extra_node_and_wrong_order_rejected_before_data_requests() -> None:
    inputs = r3.load_inputs()
    inputs["rows"].append(deepcopy(inputs["rows"][-1]))
    report, _ = invoke(loader=lambda: inputs)
    assert report["status"] == "failed" and sum(report["counts"].values()) == 0


def test_numeric_and_source_identity_drift() -> None:
    count = 0

    def snapshot() -> dict[str, Any]:
        nonlocal count
        count += 1
        return identity() | {"revision": str(count)}

    report, written = invoke(identity=snapshot)
    assert report["status"] == "failed" and report["counts"]["states_completed"] == 7
    assert not r3.independent.audit(written)["screening_verified"]


def test_float_distance_overflow_rejected() -> None:
    with pytest.raises(r3.common.GateFailure):
        r3.force((-1e308, 0.0, 0.0), (1e308, 0.0, 0.0), 8.0, 0.0)


def test_file_audit_and_authentic_input_rejection(tmp_path: Path) -> None:
    _, written = invoke()
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(written))
    # Synthetic identity is intentionally not native provenance; audit_file may
    # audit a pre-identity partial failure without manufacturing native evidence.
    written["status"] = "failed"
    written["error"] = {"stage": "test-only"}
    written.pop("identity")
    written.pop("final_identity")
    path.write_text(json.dumps(written))
    assert not r3.independent.audit_file(path)["screening_verified"]
    written["inputs"]["rows"][0]["sun"]["position_m"][0] += 1.0
    path.write_text(json.dumps(written))
    with pytest.raises(ValueError, match="identity"):
        r3.independent.audit_file(path)


def test_native_boundaries_translate_domain_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from space_nav import ephemeris
    from space_nav.errors import EphemerisError

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise EphemerisError("synthetic native boundary failure")

    monkeypatch.setattr(ephemeris, "_query_body_state_tdb", broken)
    monkeypatch.setattr(ephemeris, "_get_body_gravitational_parameter", broken)
    monkeypatch.setattr(r3.common, "runtime_identity", broken)
    for fn in (
        lambda: r3.body_provider("Earth", 1.0),
        r3.earth_gm_provider,
        r3.runtime_identity,
    ):
        with pytest.raises(r3.common.Unavailable):
            fn()


def test_body_gm_wrappers_preserve_exact_tdb_and_si(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from space_nav import ephemeris

    called = []

    def fake(body: str, epoch: float) -> ephemeris.CartesianState:
        called.append((body, epoch))
        return ephemeris.CartesianState(
            body=body,
            epoch_utc="2031-01-01T00:00:00Z",
            epoch_tdb_s=epoch,
            origin="SSB",
            orientation="J2000",
            position_m=(1.0, 2.0, 3.0),
            velocity_m_s=(4.0, 5.0, 6.0),
        )

    monkeypatch.setattr(ephemeris, "_query_body_state_tdb", fake)
    monkeypatch.setattr(
        ephemeris,
        "_get_body_gravitational_parameter",
        lambda body: 123.0 if body == "Earth" else None,
    )
    assert r3.body_provider("Earth", 978995455.2304223)["position_m"] == (1.0, 2.0, 3.0)
    assert called == [("Earth", 978995455.2304223)]
    assert r3.earth_gm_provider() == 123.0
