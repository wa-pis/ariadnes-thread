"""Artificial oracle checks; fabricated packets do not prove optimizer recovery."""

from copy import deepcopy
import math
from time import monotonic
from typing import cast

import pytest

from space_nav import _coupled_benchmark_oracle as oracle


def _packet() -> dict[str, object]:
    """Manufacture a known-witness report to isolate independent-auditor checks."""
    reference = oracle.reference()
    rows = cast(list[list[float]], reference["states"])
    nodes = [row[:6] for row in rows[1:3]]
    m1 = 2000.0 - 1000.0 / (9.80665 * 450.0) * 1000.0
    trajectory = {"epochs_s": [0.0, 1000.0, 9000.0, 10000.0], "states": deepcopy(rows)}
    return {"schema": "ariadna-coupled-synthetic-v1", "frame": "SYNTHETIC_INERTIAL",
            "time_scale": "elapsed_seconds", "reference": reference,
            "controls": [0.0, 0.0, 1000.0, 0.0, 0.0, 1000.0], "shooting_nodes": nodes,
            "initial_defects": [1000.0] + [0.0] * 17, "defects": [0.0] * 18,
            "arc_start_states": [rows[0].copy(), nodes[0] + [m1], nodes[1] + [m1]],
            "arc_end_states": deepcopy(rows[1:]), "witness": deepcopy(trajectory),
            "recovered": deepcopy(trajectory),
            "counts": {"residual_calls": 1, "synthetic_arc_attempts": 9, "rhs_attempts": 9,
                       "native_propagations": 0, "spice_queries": 0,
                       "kernel_reads": 0, "real_archive_reads": 0},
            "solver": {"method": "trf", "jac": "2-point", "tr_solver": "exact",
                       "loss": "linear", "max_nfev": 20, "ftol": 1e-12,
                       "xtol": 1e-12, "gtol": 1e-12, "diff_step": None,
                       "verbose": 0, "workers": None, "status": 1,
                       "success": True, "message": "fabricated packet; not a solver run",
                       "nfev": 1, "njev": 1, "integration_method": "DOP853",
                       "rtol": 1e-12, "atol": [1e-6] * 3 + [1e-10] * 4,
                       "first_step_s": 1, "max_step_s": 100}, "status": "passed"}


def _run(packet: dict[str, object]) -> dict[str, object]:
    return oracle.audit(packet, deadline=monotonic() + 60.0)


def test_decimal_reference_obeys_independent_mass_and_velocity_invariants() -> None:
    reference = oracle.reference()
    states = cast(list[list[float]], reference["states"])
    epochs = cast(list[float], reference["epochs_s"])
    exhaust = 9.80665 * 450.0
    rate = 1000.0 / exhaust
    for index, (epoch, row) in enumerate(zip(epochs, states, strict=True)):
        burn_time = (0.0, 1000.0, 1000.0, 2000.0)[index]
        assert row[6] == pytest.approx(2000.0 - rate * burn_time, abs=1e-12)
        expected_speed = 1000.0 + 0.1 * epoch + exhaust * math.log(2000.0 / row[6])
        assert row[4] == pytest.approx(expected_speed, abs=1e-10)
        assert row[0] == 10000000.0 and row[2] == row[3] == row[5] == 0.0
    precision = cast(dict[str, float], reference["precision_differences"])
    assert precision["position_m"] <= 1e-9
    assert precision["velocity_m_s"] <= 1e-12
    assert precision["mass_kg"] <= 1e-15
    relevance = cast(dict[str, float], reference["relevance"])
    assert relevance["gravity_speed_m_s"] >= relevance["initial_speed_m_s"] / 2
    assert relevance["consumed_mass_kg"] >= relevance["initial_mass_kg"] / 10


def test_reference_packets_are_fresh() -> None:
    reference = oracle.reference()
    fixture = cast(dict[str, object], reference["fixture"])
    cast(list[float], fixture["r0_m"])[0] = -1.0
    cast(list[list[float]], reference["states"])[0][0] = -1.0
    fresh = oracle.reference()
    assert cast(dict[str, object], fresh["fixture"])["r0_m"] == [10000000.0, 0.0, 0.0]
    assert cast(list[list[float]], fresh["states"])[0][0] == 10000000.0


def test_full_independent_inventory_and_known_witness_parity() -> None:
    result = _run(_packet())
    counts = cast(dict[str, int], result["counts"])
    assert result["status"] == "passed"
    assert counts["rhs_attempts"] == 294912 and counts["synthetic_arc_attempts"] == 12
    assert counts["optimizer_calls"] == 0
    assert all(counts[key] == 0 for key in (
        "native_propagations", "spice_queries", "kernel_reads", "real_archive_reads"))
    maxima = cast(dict[str, dict[str, float]], result["max_errors"])
    for key in ("witness", "mesh", "candidate_rk4"):
        assert maxima[key]["position_m"] <= 0.001
        assert maxima[key]["velocity_m_s"] <= 1e-6


@pytest.mark.parametrize(("field", "value", "message"), [
    ("schema", "other", "schema"), ("frame", "SSB", "frame"),
    ("status", "targeting-failed", "status"),
    ("controls", [True, 0.0, 1000.0, 0.0, 0.0, 1000.0], "finite number"),
    ("controls", [0.0, 0.0, 499.0, 0.0, 0.0, 1000.0], "domain"),
    ("controls", [0.0, float("nan"), 1000.0, 0.0, 0.0, 1000.0], "finite number"),
    ("initial_defects", [0.0] * 18, "initial defects"),
    ("defects", [1.0] + [0.0] * 17, "raw defect"),
])
def test_packet_failure_precedes_replay(field: str, value: object, message: str) -> None:
    packet = _packet()
    packet[field] = value
    with pytest.raises(oracle.OracleError, match=message):
        _run(packet)


@pytest.mark.parametrize(("field", "value"), [
    ("residual_calls", True), ("residual_calls", -1), ("residual_calls", 401),
    ("synthetic_arc_attempts", 1207), ("synthetic_arc_attempts", 10),
    ("rhs_attempts", 1000001), ("rhs_attempts", 8),
    ("spice_queries", 1), ("kernel_reads", 1), ("native_propagations", 1),
    ("real_archive_reads", 1),
])
def test_producer_counter_type_cap_and_coherence(field: str, value: object) -> None:
    packet = _packet()
    cast(dict[str, object], packet["counts"])[field] = value
    with pytest.raises(oracle.OracleError, match="count"):
        _run(packet)


@pytest.mark.parametrize("section", ["report", "reference", "counts", "solver", "witness"])
def test_unknown_fields_are_not_admitted(section: str) -> None:
    packet = _packet()
    target = packet if section == "report" else cast(dict[str, object], packet[section])
    target["unknown"] = 1
    with pytest.raises(oracle.OracleError, match="fields"):
        _run(packet)


def test_changed_reference_and_solver_profiles_are_rejected() -> None:
    packet = _packet()
    reference = cast(dict[str, object], packet["reference"])
    cast(dict[str, object], reference["fixture"])["thrust_n"] = 999.0
    with pytest.raises(oracle.OracleError, match="identity"):
        _run(packet)
    packet = _packet()
    cast(dict[str, object], packet["solver"])["integration_method"] = "RK45"
    with pytest.raises(oracle.OracleError, match="identity"):
        _run(packet)


def test_nodes_cannot_supply_an_independent_mass_or_epoch() -> None:
    packet = _packet()
    cast(list[list[float]], packet["arc_start_states"])[1][6] += 1.0
    with pytest.raises(oracle.OracleError, match="arc start"):
        _run(packet)
    packet = _packet()
    recovered = cast(dict[str, object], packet["recovered"])
    cast(list[float], recovered["epochs_s"])[1] += 0.001
    with pytest.raises(oracle.OracleError, match="epoch"):
        _run(packet)


def test_changed_recovered_command_is_checked_beyond_a_valid_witness() -> None:
    packet = _packet()
    # The copied paths look perfect, but this actual command leaves the target.
    cast(list[float], packet["controls"])[0] = 0.01
    with pytest.raises(oracle.OracleError, match="recovered candidate/RK4|independent unreset"):
        _run(packet)


def test_tnw_uses_current_velocity_and_coast_has_gravity_without_thrust() -> None:
    work = oracle._Work(monotonic() + 5.0)
    state = [10000000.0, 1000.0, 20.0, 10.0, 1000.0, 5.0]
    burn = oracle._rhs(state, 2000.0, True, 0.0, 0.0, work)
    tangent = [value / math.hypot(*state[3:6]) for value in state[3:6]]
    assert burn[:3] == state[3:6]
    assert burn[3:] == pytest.approx([0.5 * tangent[0], 0.1 + 0.5 * tangent[1], 0.5 * tangent[2]])
    assert oracle._rhs(state, 2000.0, False, 0.0, 0.0, work)[3:] == [0.0, 0.1, 0.0]
    with pytest.raises(oracle.OracleError, match="TNW"):
        oracle._rhs([1.0, 0.0, 0.0, 1.0, 0.0, 0.0], 2000.0, True, 0.0, 0.0, work)


def test_deadline_and_exact_work_limits_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(oracle.OracleError, match="deadline") as failed:
        oracle.audit(_packet(), deadline=monotonic() - 1.0)
    assert failed.value.counts["rhs_attempts"] == 0
    assert failed.value.counts["synthetic_arc_attempts"] == 0
    work = oracle._Work(monotonic() + 5.0, rhs_attempts=299999, synthetic_arc_attempts=11)
    work.rhs()
    work.arc()
    with pytest.raises(oracle.OracleError, match="RHS cap"):
        work.rhs()
    with pytest.raises(oracle.OracleError, match="arc cap"):
        work.arc()
    monkeypatch.setattr(oracle, "monotonic", lambda: work.deadline)
    with pytest.raises(oracle.OracleError, match="deadline"):
        work.check()


def test_public_audit_cannot_extend_its_sixty_second_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = iter((100.0, 160.0))
    monkeypatch.setattr(oracle, "monotonic", lambda: next(ticks))
    with pytest.raises(oracle.OracleError, match="deadline") as failed:
        oracle.audit(_packet(), deadline=10000.0)
    assert failed.value.counts["rhs_attempts"] == 0


def test_no_candidate_or_scientific_library_imports() -> None:
    import ast
    from pathlib import Path

    source = Path(oracle.__file__).read_text()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert node.module is not None and node.module.split(".")[0] in {
                "collections", "dataclasses", "decimal", "time", "typing"}
        elif isinstance(node, ast.Import):
            assert all(alias.name == "math" for alias in node.names)
