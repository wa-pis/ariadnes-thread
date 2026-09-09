"""Read-only SPK provenance controls, not a between-epoch error certificate."""

from __future__ import annotations

import ctypes
from fractions import Fraction
import json
from itertools import permutations
import math
from pathlib import Path
import platform
from statistics import median
import sys
from time import perf_counter

import numpy as np
import pytest

from space_nav import ephemeris, trajectory


ROOT = Path(__file__).resolve().parents[1]


def _read_native_spk_record(
    native: ctypes.CDLL, data_type: int, handle: int, descriptor: np.ndarray,
    epoch_tdb_s: float, record_size: int,
) -> np.ndarray:
    """Read raw TDB-s/km/type-3-km/s words using the pinned, test-only f2c ABI."""
    assert data_type in (2, 3) and record_size > 2
    native_handle = ctypes.c_int(handle)
    native_epoch = ctypes.c_double(epoch_tdb_s)
    native_descriptor = (ctypes.c_double * 5)(*descriptor)
    raw_record = (ctypes.c_double * (record_size + 2))()
    raw_record[-1] = 1234567.0  # Guard after length and directory-sized data.
    reader = native.spkr02_ if data_type == 2 else native.spkr03_
    reader(ctypes.byref(native_handle), native_descriptor, ctypes.byref(native_epoch), raw_record)
    assert native.failed_c() == 0
    assert raw_record[0] == record_size and raw_record[-1] == 1234567.0
    return np.asarray(raw_record)[1:-1].copy()


@pytest.mark.parametrize("degree", [0, 1, 2, 19])
def test_spk_rate_bound_matches_single_mode_endpoint_oracle(degree: int) -> None:
    budget = trajectory._RefinementBudget("chebyshev-rate-control", 300.0)
    row = tuple(1.0 if index == degree else 0.0 for index in range(degree + 1))
    bound_m_s = trajectory._spk_position_rate_bound(budget, (row, (0.0,) * len(row),
                                                               (0.0,) * len(row)), 17.0)
    exact_m_s = Fraction(1000 * degree ** 2, 17)
    assert Fraction(bound_m_s) >= exact_m_s
    assert bound_m_s == (math.nextafter(float(exact_m_s), math.inf) if degree else 0.0)
    derivative_m_s = np.polynomial.chebyshev.chebval(
        1.0, np.polynomial.chebyshev.chebder(row),
    ) * 1000 / 17
    assert abs(derivative_m_s - float(exact_m_s)) <= 1e-12  # m/s


@pytest.mark.parametrize("degree", [0, 1, 2, 3, 19])
def test_spk_extended_rate_bound_matches_closed_polynomial_oracle(degree: int) -> None:
    budget = trajectory._RefinementBudget("extended-chebyshev-control", 300.0)
    row = (0.0,) * degree + (1.0,)
    rows = (row, (0.0,) * len(row), (0.0,) * len(row))
    q = Fraction(5, 4)
    # Independent finite power formula for U_n, not the implementation recurrence.
    n = degree - 1
    exact_m_s = 1000 * degree * sum(((-1) ** j * math.comb(n - j, j) * (2 * q) ** (n - 2 * j)
                                    for j in range((n // 2) + 1)), Fraction(0)) / 4
    bound_m_s = trajectory._spk_position_rate_bound(budget, rows, 4.0, extension_s=1.0)
    assert Fraction(bound_m_s) >= exact_m_s
    assert bound_m_s == (math.nextafter(float(exact_m_s), math.inf) if degree else 0.0)
    for x in (-float(q), float(q)):
        derivative_m_s = abs(np.polynomial.chebyshev.chebval(x, np.polynomial.chebyshev.chebder(row))) * 250
        assert derivative_m_s == pytest.approx(float(exact_m_s), rel=1e-12, abs=1e-12)  # m/s
    assert trajectory._spk_position_rate_bound(budget, rows, 4.0, extension_s=0.0) == (
        trajectory._spk_position_rate_bound(budget, rows, 4.0)
    )


def test_spk_extended_rate_keeps_sub_ulp_normalized_extension() -> None:
    budget = trajectory._RefinementBudget("extended-chebyshev-control", 300.0)
    rows = ((0.0, 0.0, 1.0), (0.0,) * 3, (0.0,) * 3)
    extension_s = 2.0 ** -53
    assert 1.0 + extension_s == 1.0
    bound_m_s = trajectory._spk_position_rate_bound(budget, rows, 1.0, extension_s=extension_s)
    assert Fraction(bound_m_s) >= 4000 * (1 + Fraction(extension_s))
    assert bound_m_s > trajectory._spk_position_rate_bound(budget, rows, 1.0)


@pytest.mark.parametrize("extension_s", [-1.0, True, float("nan"), float("inf"), 1e308])
def test_spk_extended_rate_rejects_invalid_or_overflowing_extension(extension_s: float) -> None:
    budget = trajectory._RefinementBudget("extended-chebyshev-control", 300.0)
    with pytest.raises(trajectory.TrajectoryRefinementError, match="spk-position-rate-bound") as caught:
        trajectory._spk_position_rate_bound(
            budget, ((0.0, 0.0, 1.0), (0.0,) * 3, (0.0,) * 3), 1e-308, extension_s=extension_s,
        )
    assert caught.value.__cause__ is not None


@pytest.mark.parametrize("extension_s", [0.0, 0.1])
def test_spk_rate_bound_rounds_mixed_axes_outward(extension_s: float) -> None:
    rows = ((1e200, 0.1, -0.3), (-1e200, 0.2, 0.0), (0.0, -0.4, 0.5))
    weights = (Fraction(0), Fraction(1), 4 * (1 + Fraction(extension_s) / Fraction(0.3)))
    exact_m_s = 1000 * sum((abs(Fraction(value)) * weights[degree]
                            for row in rows for degree, value in enumerate(row)), Fraction(0)) / Fraction(0.3)
    budget = trajectory._RefinementBudget("chebyshev-rate-control", 300.0)
    bound_m_s = trajectory._spk_position_rate_bound(budget, rows, 0.3, extension_s=extension_s)
    assert Fraction(bound_m_s) >= exact_m_s
    assert bound_m_s == math.nextafter(float(exact_m_s), math.inf)


def test_spk_rate_bound_preserves_positive_subnormal_bound() -> None:
    smallest = math.nextafter(0.0, math.inf)
    budget = trajectory._RefinementBudget("chebyshev-rate-control", 300.0)
    bound_m_s = trajectory._spk_position_rate_bound(
        budget, ((0.0, smallest), (0.0, 0.0), (0.0, 0.0)), 1e308,
    )
    assert Fraction(bound_m_s) >= 1000 * Fraction(smallest) / Fraction(1e308) > 0


@pytest.mark.parametrize("rows,radius_s", [
    ((), 1.0), (((), (), ()), 1.0), (((1.0,), (1.0, 2.0), (1.0,)), 1.0),
    (((True,), (0.0,), (0.0,)), 1.0), (((float("nan"),), (0.0,), (0.0,)), 1.0),
    (((0.0,), (0.0,), (0.0,)), 0.0), (((0.0,), (0.0,), (0.0,)), True),
    (((0.0,), (0.0,), (0.0,)), float("inf")),
    (((0.0, 1e308), (0.0, 0.0), (0.0, 0.0)), 1e-308),
])
def test_spk_rate_bound_rejects_invalid_coefficients_or_radius(
    rows: tuple[tuple[float, ...], ...], radius_s: float,
) -> None:
    budget = trajectory._RefinementBudget("chebyshev-rate-control", 300.0)
    with pytest.raises(trajectory.TrajectoryRefinementError, match="spk-position-rate-bound") as caught:
        trajectory._spk_position_rate_bound(budget, rows, radius_s)
    assert caught.value.__cause__ is not None


def test_spk_rate_bound_honors_expired_budget() -> None:
    now_s = [0.0]
    budget = trajectory._RefinementBudget("chebyshev-rate-control", 300.0, lambda: now_s[0])
    now_s[0] = 300.0
    with pytest.raises(trajectory.TrajectoryRefinementError, match="deadline"):
        trajectory._spk_position_rate_bound(budget, ((0.0,),) * 3, 1.0)


@pytest.mark.parametrize("native_record_readback", [False, True], ids=["portable", "native-readback"])
def test_loaded_spk_chain_coverage_contains_candidate_interval(
    native_record_readback: bool, request: pytest.FixtureRequest,
) -> None:
    """Qualify coverage and exact record motion, not native error or safety."""
    import spiceypy as spice
    from spiceypy.utils.support_types import SPICEDOUBLE_CELL

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    start_tdb_s, end_tdb_s = evidence["epoch_tdb_s"][0], evidence["epoch_tdb_s"][-1]
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    native: ctypes.CDLL | None = None
    if native_record_readback:
        native = request.getfixturevalue("cspice")
        assert isinstance(native, ctypes.CDLL)
        budget.check()
    ephemeris._ensure_standard_kernels()
    kernels_before = [spice.kdata(i, "ALL") for i in range(spice.ktotal("ALL"))]
    registrations = [spice.kdata(i, "SPK") for i in range(spice.ktotal("SPK"))]
    # Repeated kernel initialization registers the same physical file again.
    files = list({str(Path(entry[0]).resolve()): entry for entry in registrations}.values())
    assert files
    # Effective targets already qualified against named Tudat states.
    expected_centers = {10: 0, 1: 0, 2: 0, 399: 0, 301: 399,
                        499: 4, 4: 0, 599: 5, 5: 0, 699: 6, 6: 0}
    segment_counts = dict.fromkeys(expected_centers, 0)
    segments: list[tuple[int, int, int, float, float, int, int, np.ndarray]] = []
    total_segments = 0
    # Complete DAF scans before calling other routines that start DAF searches.
    for path, kind, _, handle in files:
        assert kind == "SPK"
        spice.dafbfs(handle)
        while spice.daffna():
            budget.check()
            total_segments += 1
            descriptor = spice.dafgs()[:5]
            target, center, frame, data_type, first, last, begin, end = spice.spkuds(descriptor)
            assert math.isfinite(first) and math.isfinite(last) and first <= last
            assert 0 < begin <= end
            if target in expected_centers and first <= end_tdb_s and last >= start_tdb_s:
                assert center == expected_centers[target], (path, target, center)
                assert frame == 1 and data_type in (2, 3), (path, target, frame, data_type)
                segment_counts[target] += 1
                segments.append((handle, target, data_type, first, last, begin, end, descriptor.copy()))
    assert len(files) == 6 and total_segments == 2028
    assert segment_counts == {target: 2 if target == 699 else 1 for target in expected_centers}

    rates_m_s: dict[int, list[float]] = {target: [] for target in expected_centers}
    joins: dict[tuple[int, Fraction], dict[int, tuple[
        tuple[Fraction, ...], tuple[Fraction, ...], float, np.ndarray,
    ]]] = {}
    max_position_difference_m = max_type2_velocity_difference_m_s = 0.0
    max_join_position_difference_m = 0.0
    native_join_failures: list[tuple[int, float, int, float]] = []
    all_record_checks = dict.fromkeys(expected_centers, 0)
    early_record_choices = dict.fromkeys(expected_centers, 0)
    switching_records: dict[int, list[tuple[int, np.ndarray, float, float, int, np.ndarray]]] = {
        499: [], 599: [],
    }
    for handle, target, data_type, first, last, begin, end, descriptor in segments:
        budget.check()
        init_s, interval_s, raw_size, raw_count = spice.dafgda(handle, end - 3, end)
        assert all(math.isfinite(value) for value in (init_s, interval_s, raw_size, raw_count))
        assert interval_s > 0 and raw_size == int(raw_size) and raw_count == int(raw_count)
        size, count = int(raw_size), int(raw_count)
        components = 3 if data_type == 2 else 6
        assert size > 2 and count > 0 and (size - 2) % components == 0
        coefficient_count = (size - 2) // components
        assert end - begin + 1 == size * count + 4
        assert Fraction(init_s) == Fraction(first)
        assert Fraction(init_s) + count * Fraction(interval_s) == Fraction(last)
        # Include both touching records at exact endpoints without rounded index division.
        first_index = max(0, math.ceil((Fraction(start_tdb_s) - Fraction(init_s)) / Fraction(interval_s)) - 1)
        last_index = min(count - 1, math.floor((Fraction(end_tdb_s) - Fraction(init_s)) / Fraction(interval_s)))
        assert 0 <= first_index <= last_index < count
        for index in range(first_index, last_index + 1):
            budget.check()
            address = begin + index * size
            record = spice.dafgda(handle, address, address + size - 1)
            assert np.all(np.isfinite(record))
            record_start_s = Fraction(init_s) + index * Fraction(interval_s)
            assert Fraction(record[0]) == record_start_s + Fraction(interval_s) / 2
            assert Fraction(record[1]) == Fraction(interval_s) / 2
            if native is not None:
                probes_s = [float(record[0])]
                for boundary_s, direction in ((record_start_s, 1), (record_start_s + Fraction(interval_s), -1)):
                    if start_tdb_s < boundary_s < end_tdb_s:
                        probes_s.append(float(boundary_s) + direction * math.ulp(float(boundary_s)))
                for probe_s in probes_s:
                    budget.check()
                    selected_index = math.floor((probe_s - init_s) / interval_s)
                    assert 0 <= selected_index < count
                    assert selected_index in (index, index + 1)
                    selected_address = begin + selected_index * size
                    expected_record = spice.dafgda(handle, selected_address, selected_address + size - 1)
                    actual_record = _read_native_spk_record(native, data_type, handle, descriptor, probe_s, size)
                    assert actual_record.tobytes() == expected_record.tobytes(), (target, probe_s)
                    all_record_checks[target] += 1
                    early_record_choices[target] += selected_index != index
            if target in switching_records:
                switching_records[target].append((handle, descriptor, init_s, interval_s, index, record))
            coefficients_km = record[2:].reshape(components, coefficient_count)[:3]
            bound_m_s = trajectory._spk_position_rate_bound(
                budget, tuple(tuple(float(value) for value in row) for row in coefficients_km),
                float(record[1]),
            )
            rates_m_s[target].append(bound_m_s)
            extension_s = 16 * math.ulp(float(record[0]))
            extended_bound_m_s = trajectory._spk_position_rate_bound(
                budget, tuple(tuple(float(value) for value in row) for row in coefficients_km),
                float(record[1]), extension_s=extension_s,
            )
            assert extended_bound_m_s >= bound_m_s
            exact_q = 1 + Fraction(extension_s) / Fraction(record[1])
            extended_q = float(exact_q)
            if Fraction(extended_q) > exact_q:
                extended_q = math.nextafter(extended_q, 1.0)
            for x in (-extended_q, extended_q):
                derivative_m_s = np.polynomial.chebyshev.chebval(
                    x, np.polynomial.chebyshev.chebder(coefficients_km.T, axis=0),
                ) * (1000 / record[1])
                assert np.linalg.norm(derivative_m_s) <= extended_bound_m_s
            for sign in (-1, 1):
                epoch_s = Fraction(record[0]) + sign * Fraction(record[1])
                if not start_tdb_s < epoch_s < end_tdb_s:
                    continue
                # Store each side explicitly; segment file order need not be chronological.
                sides = joins.setdefault((target, epoch_s), {})
                assert sign not in sides, (target, epoch_s)
                endpoint_m = tuple(1000 * sum((Fraction(value) * sign ** degree
                                              for degree, value in enumerate(row)), Fraction(0))
                                   for row in coefficients_km)
                offset_s = Fraction(math.ulp(float(epoch_s)))
                assert Fraction(float(epoch_s)) == epoch_s and 0 < offset_s < Fraction(record[1])
                normalized_time = sign * (1 - offset_s / Fraction(record[1]))
                basis = [Fraction(1), normalized_time]
                for degree in range(2, coefficient_count):
                    basis.append(2 * normalized_time * basis[-1] - basis[-2])
                near_m = tuple(1000 * sum((Fraction(value) * basis[degree]
                                          for degree, value in enumerate(row)), Fraction(0))
                               for row in coefficients_km)
                query_s = float(epoch_s) - sign * float(offset_s)
                assert Fraction(query_s) == epoch_s - sign * offset_s
                join_frame, join_state_km, join_center = spice.spkpvn(handle, descriptor, query_s)
                assert (join_frame, join_center) == (1, expected_centers[target])
                assert np.all(np.isfinite(join_state_km))
                join_difference_m = float(np.linalg.norm(
                    np.asarray([float(value) for value in near_m]) - join_state_km[:3] * 1000,
                ))
                if join_difference_m > 0.001:
                    native_join_failures.append((target, float(epoch_s), sign, join_difference_m))
                max_join_position_difference_m = max(max_join_position_difference_m, join_difference_m)
                sides[sign] = (endpoint_m, near_m, bound_m_s, join_state_km[:3] * 1000)
            derivative_coefficients = np.polynomial.chebyshev.chebder(coefficients_km.T, axis=0)
            for normalized_time in (-1.0, -0.5, 0.0, 0.5, 1.0):
                derivative_m_s = np.polynomial.chebyshev.chebval(
                    normalized_time, derivative_coefficients,
                ) * (1000 / record[1])
                assert np.all(np.isfinite(derivative_m_s))
                assert np.linalg.norm(derivative_m_s) <= bound_m_s, (target, index)
            frame, state_km, center = spice.spkpvn(handle, descriptor, float(record[0]))
            assert (frame, center) == (1, expected_centers[target])
            assert np.all(np.isfinite(state_km))
            position_difference_m = float(np.linalg.norm(
                (np.polynomial.chebyshev.chebval(0.0, coefficients_km.T) - state_km[:3]) * 1000,
            ))
            assert position_difference_m <= 0.001, (target, index)
            max_position_difference_m = max(max_position_difference_m, position_difference_m)
            if data_type == 2:
                velocity_difference_m_s = float(np.linalg.norm(
                    (np.polynomial.chebyshev.chebval(0.0, derivative_coefficients) / record[1]
                     - state_km[3:]) * 1000,
                ))
                assert velocity_difference_m_s <= 0.000001, (target, index)
                max_type2_velocity_difference_m_s = max(max_type2_velocity_difference_m_s,
                                                       velocity_difference_m_s)

    jump_observations: dict[int, list[tuple[float, float, bool]]] = {target: [] for target in expected_centers}
    for (target, epoch_s), sides in sorted(joins.items()):
        budget.check()
        assert set(sides) == {-1, 1}, (target, epoch_s)
        left, right = sides[1], sides[-1]
        jump_m = sum((abs(a - b) for a, b in zip(left[0], right[0])), Fraction(0))
        motion_m = sum((abs(a - b) for a, b in zip(left[1], right[1])), Fraction(0))
        local_bound_m = Fraction(math.ulp(float(epoch_s))) * (Fraction(left[2]) + Fraction(right[2]))
        assert motion_m <= local_bound_m + jump_m, (target, epoch_s)
        if target in (499, 599):
            # Counterexample: just before the mathematical join, native values
            # agree with the other side instead. This is not a native-error bound.
            assert np.linalg.norm(left[3] - np.asarray([float(value) for value in right[1]])) <= 0.001
        jump_observations[target].append((float(epoch_s), float(jump_m), motion_m > local_bound_m))
    assert all(len(jump_observations[target]) == len(rates_m_s[target]) - 1 for target in expected_centers)
    assert len(joins) == 539
    assert len(native_join_failures) == 221
    assert {(target, epoch_s) for target, epoch_s, _, _ in native_join_failures} == {
        (target, float(epoch_s)) for target, epoch_s in joins if target in (499, 599)
    }
    assert all(sign == 1 for _, _, sign, _ in native_join_failures)

    switching_probes: list[tuple[int, float, int, float]] = []
    ambiguity_bounds: list[tuple[int, float, float]] = []
    exact_ambiguity_checks = 0
    native_record_checks = 0
    for target, records in switching_records.items():
        for left, right in zip(records, records[1:]):
            handle, descriptor, init_s, interval_s, index, left_record = left
            assert right[4] == index + 1
            right_record = right[5]
            if native is not None:
                # Both directories were checked before calling the raw record reader.
                assert len(left_record) == len(right_record) == 122
                assert spice.spkuds(descriptor)[3] == 3
            epoch_s = float(left_record[0] + left_record[1])
            assert epoch_s == right_record[0] - right_record[1]
            extension_s = 16 * math.ulp(epoch_s)
            rate_sum_m_s = sum((Fraction(trajectory._spk_position_rate_bound(
                budget, tuple(tuple(float(value) for value in row)
                              for row in record[2:].reshape(6, -1)[:3]),
                float(record[1]), extension_s=extension_s,
            )) for record in (left_record, right_record)), Fraction(0))
            endpoints = joins[(target, Fraction(epoch_s))]
            jump_m = sum((abs(a - b) for a, b in zip(endpoints[1][0], endpoints[-1][0])), Fraction(0))
            uniform_bound_m = jump_m + rate_sum_m_s * Fraction(extension_s)
            reported_bound_m = math.nextafter(float(uniform_bound_m), math.inf)
            assert math.isfinite(reported_bound_m) and Fraction(reported_bound_m) >= uniform_bound_m
            ambiguity_bounds.append((target, epoch_s, reported_bound_m))
            selected_offsets: list[int] = []
            max_error_m = 0.0
            for offset in range(-16, 17):
                budget.check()
                query_s = epoch_s + offset * math.ulp(epoch_s)
                if offset in (-16, -5, -4, -1, 0, 1, 16):
                    exact_positions_m: list[tuple[Fraction, ...]] = []
                    for record in (left_record, right_record):
                        rows = record[2:].reshape(6, -1)[:3]
                        x_exact = (Fraction(query_s) - Fraction(record[0])) / Fraction(record[1])
                        assert abs(x_exact) <= 1 + Fraction(extension_s) / Fraction(record[1])
                        basis = [Fraction(1), x_exact]
                        for degree in range(2, rows.shape[1]):
                            basis.append(2 * x_exact * basis[-1] - basis[-2])
                        exact_positions_m.append(tuple(
                            1000 * sum((Fraction(value) * basis[degree]
                                        for degree, value in enumerate(row)), Fraction(0)) for row in rows
                        ))
                    difference_m = sum((abs(a - b) for a, b in zip(*exact_positions_m)), Fraction(0))
                    motion_only_m = rate_sum_m_s * abs(Fraction(query_s) - Fraction(epoch_s))
                    assert difference_m <= jump_m + motion_only_m <= uniform_bound_m
                    assert difference_m > motion_only_m  # Omitting the source jump is unsafe.
                    exact_ambiguity_checks += 1
                if -4 <= offset < 0:
                    assert Fraction(query_s) - Fraction(init_s) < Fraction(epoch_s) - Fraction(init_s)
                    assert query_s - init_s == epoch_s - init_s
                # Candidate arithmetic replay, qualified against native values below.
                selected_index = math.floor((query_s - init_s) / interval_s)
                assert selected_index in (index, index + 1)
                selected_record = left_record if selected_index == index else right_record
                if native is not None:
                    actual_record = _read_native_spk_record(native, 3, handle, descriptor, query_s, 122)
                    assert actual_record.tobytes() == selected_record.tobytes()
                    native_record_checks += 1
                x = (query_s - selected_record[0]) / selected_record[1]
                predicted_m = np.polynomial.chebyshev.chebval(
                    x, selected_record[2:].reshape(6, -1)[:3].T,
                ) * 1000
                frame, state_km, center = spice.spkpvn(handle, descriptor, query_s)
                assert (frame, center) == (1, expected_centers[target])
                assert np.all(np.isfinite(state_km)) and np.all(np.isfinite(predicted_m))
                error_m = float(np.linalg.norm(predicted_m - state_km[:3] * 1000))
                assert error_m <= 0.001, (target, epoch_s, offset)
                other_record = right_record if selected_index == index else left_record
                other_m = np.polynomial.chebyshev.chebval(
                    (query_s - other_record[0]) / other_record[1],
                    other_record[2:].reshape(6, -1)[:3].T,
                ) * 1000
                assert np.linalg.norm(other_m - state_km[:3] * 1000) > 0.001
                max_error_m = max(max_error_m, error_m)
                if selected_index == index + 1:
                    selected_offsets.append(offset)
            assert selected_offsets == list(range(selected_offsets[0], 17))
            assert selected_offsets[0] == -4
            switching_probes.append((target, epoch_s, selected_offsets[0], max_error_m))
    assert len(switching_probes) == 221
    assert exact_ambiguity_checks == 1547
    assert native_record_checks == (7293 if native_record_readback else 0)
    assert sum(all_record_checks.values()) == (1628 if native_record_readback else 0)
    assert early_record_choices == {
        target: len(rates_m_s[target]) - 1 if native_record_readback and target != 699 else 0
        for target in expected_centers
    }

    common = SPICEDOUBLE_CELL(2)
    spice.wninsd(start_tdb_s, end_tdb_s, common)
    observations: dict[int, list[tuple[float, float]]] = {}
    for target in expected_centers:
        # spkcov merges into its supplied window across all loaded files.
        coverage = SPICEDOUBLE_CELL(10000)
        for path, _, _, _ in files:
            budget.check()
            spice.spkcov(path, target, coverage)
        intervals = [spice.wnfetd(coverage, i) for i in range(spice.wncard(coverage))]
        assert intervals and all(math.isfinite(value) for pair in intervals for value in pair)
        assert spice.wnincd(start_tdb_s, end_tdb_s, coverage), (target, intervals)
        common = spice.wnintd(common, coverage)
        observations[target] = intervals
    assert spice.wncard(common) == 1
    assert spice.wnfetd(common, 0) == (start_tdb_s, end_tdb_s)

    # Endpoint membership alone must not accept an interior gap.
    gap = SPICEDOUBLE_CELL(4)
    midpoint_tdb_s = (start_tdb_s + end_tdb_s) / 2
    spice.wninsd(start_tdb_s, midpoint_tdb_s - 1.0, gap)
    spice.wninsd(midpoint_tdb_s + 1.0, end_tdb_s, gap)
    assert spice.wnincd(start_tdb_s, start_tdb_s, gap)
    assert spice.wnincd(end_tdb_s, end_tdb_s, gap)
    assert not spice.wnincd(start_tdb_s, end_tdb_s, gap)
    missing = SPICEDOUBLE_CELL(10000)
    for path, _, _, _ in files:
        spice.spkcov(path, -2147483647, missing)
    assert spice.wncard(missing) == 0
    assert not spice.wnincd(start_tdb_s, end_tdb_s, missing)
    assert not spice.failed()
    assert kernels_before == [spice.kdata(i, "ALL") for i in range(spice.ktotal("ALL"))]
    budget.check()
    assert budget.native_arc_propagations == 0
    print(json.dumps({
        "candidate_id": evidence["candidate_id"], "time": "TDB seconds since J2000",
        "candidate_interval_tdb_s": [start_tdb_s, end_tdb_s],
        "spk_files": [Path(entry[0]).name for entry in files],
        "spk_registration_count": len(registrations),
        "total_segments": total_segments, "overlapping_chain_segments": segment_counts,
        "coverage_intervals_tdb_s": observations, "chain_centers": expected_centers,
        "position_rate_bounds_by_target": {
            target: {"record_count": len(values), "min_m_s": min(values), "max_m_s": max(values)}
            for target, values in rates_m_s.items()
        },
        "record_midpoint_max_position_difference_m": max_position_difference_m,
        "record_join_fields": ["epoch_tdb_s", "exact_position_jump_l1_m", "jump_omission_fails"],
        "record_joins_by_target": jump_observations,
        "record_join_max_position_difference_m": max_join_position_difference_m,
        "native_join_parity_failure_fields": ["target", "epoch_tdb_s", "record_endpoint_sign", "error_m"],
        "native_join_parity_failures": native_join_failures,
        "native_join_parity_tolerance_m": 0.001,
        "record_switch_fields": ["target", "boundary_tdb_s", "first_right_record_offset_ulp", "max_replay_error_m"],
        "record_switch_probes": switching_probes,
        "exact_branch_ambiguity_fields": ["target", "boundary_tdb_s", "position_l1_bound_m"],
        "exact_branch_ambiguity_bounds": ambiguity_bounds,
        "exact_branch_ambiguity_checks": exact_ambiguity_checks,
        "native_selected_record_bitwise_checks": native_record_checks,
        "all_chain_native_record_checks": all_record_checks,
        "all_chain_early_record_choices": early_record_choices,
        "type2_midpoint_max_velocity_difference_m_s": max_type2_velocity_difference_m_s,
        "frame": "J2000, each target relative to its listed center; chains end at SSB",
        "scope": "Coverage and exact per-record position-rate bounds, not composed motion or safety",
    }, sort_keys=True, allow_nan=False))


def test_direct_and_tabulated_ephemeris_lookup_cost() -> None:
    """Measure warm Python-boundary lookup cost, not full-force propagation."""
    from tudatpy.dynamics import environment_setup

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    epochs_tdb_s = evidence["epoch_tdb_s"]
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    spice = ephemeris._ensure_standard_kernels()
    started_s = perf_counter()
    settings = trajectory._create_time_limited_body_settings(
        environment_setup, epochs_tdb_s[0], epochs_tdb_s[-1],
    )
    settings_elapsed_s = perf_counter() - started_s
    repeats, batches = 100, 6
    observations: list[dict[str, object]] = []
    for body in trajectory.PHYSICAL_BODY_NAMES:
        budget.check()
        started_s = perf_counter()
        table = environment_setup.create_body_ephemeris(
            settings.get(body).ephemeris_settings, body,
        )
        table_setup_s = perf_counter() - started_s
        started_s = perf_counter()
        direct = environment_setup.create_body_ephemeris(
            environment_setup.ephemeris.direct_spice("SSB", "J2000", body), body,
        )
        direct_setup_s = perf_counter() - started_s
        # Validate and warm both paths outside the timed loops.
        for model in (table, direct):
            assert (model.frame_origin, model.frame_orientation) == ("SSB", "J2000")
            for epoch_tdb_s in epochs_tdb_s:
                state_si = model.cartesian_state(epoch_tdb_s)
                reference_si = spice.get_body_cartesian_state_at_epoch(
                    body, "SSB", "J2000", "NONE", epoch_tdb_s,
                )
                assert np.all(np.isfinite(state_si))
                difference_si = state_si - reference_si
                position_limit_m = 0.001 if model is direct else 0.025
                velocity_limit_m_s = 0.000001 if model is direct else 0.0000025
                assert np.linalg.norm(difference_si[:3]) <= position_limit_m
                assert np.linalg.norm(difference_si[3:]) <= velocity_limit_m_s
        elapsed_s: dict[str, list[float]] = {"table": [], "direct": []}
        paths = (("table", table), ("direct", direct))
        for batch in range(batches):
            for name, model in paths if batch % 2 == 0 else paths[::-1]:
                budget.check()
                query = model.cartesian_state
                started_s = perf_counter()
                for _ in range(repeats):
                    for epoch_tdb_s in epochs_tdb_s:
                        query(epoch_tdb_s)
                duration_s = perf_counter() - started_s
                assert math.isfinite(duration_s) and duration_s > 0
                elapsed_s[name].append(duration_s)
                budget.check()
        observations.append({
            "body": body, "table_setup_s": table_setup_s,
            "direct_setup_s": direct_setup_s, "batch_elapsed_s": elapsed_s,
            "median_query_s": {
                name: median(values) / (repeats * len(epochs_tdb_s))
                for name, values in elapsed_s.items()
            },
        })
    budget.check()
    assert budget.native_arc_propagations == 0
    print(json.dumps({
        "candidate_id": evidence["candidate_id"], "platform": platform.platform(),
        "python": platform.python_version(), "settings_elapsed_s": settings_elapsed_s,
        "epoch_count": len(epochs_tdb_s), "batches_per_path": batches,
        "queries_per_batch": repeats * len(epochs_tdb_s),
        "time": "TDB seconds since J2000", "frame": "SSB/J2000",
        "state_units": ["m", "m/s"], "observations": observations,
        "scope": "Warm Python-boundary lookup timings; no speed gate or mission estimate",
    }, sort_keys=True, allow_nan=False))


@pytest.fixture
def cspice() -> ctypes.CDLL:
    """Use the installed Darwin ABI and Tudat-loaded pool without changing it."""
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        pytest.skip("Only the installed Darwin/arm64 CSPICE ABI was inspected")
    ephemeris._ensure_standard_kernels()
    native = ctypes.CDLL(str(Path(sys.prefix) / "lib/libcspice.dylib"))
    integer, double, pointer = ctypes.c_int, ctypes.c_double, ctypes.POINTER
    assert ctypes.sizeof(integer) == 4 and ctypes.sizeof(double) == 8
    native.spksfs_c.argtypes = [
        integer, double, integer, pointer(integer), pointer(double),
        pointer(ctypes.c_char), pointer(integer),
    ]
    native.spksfs_c.restype = None
    native.spkuds_c.argtypes = [
        pointer(double), *([pointer(integer)] * 4),
        pointer(double), pointer(double), pointer(integer), pointer(integer),
    ]
    native.spkuds_c.restype = None
    native.spkssb_c.argtypes = [integer, double, ctypes.c_char_p, pointer(double)]
    native.spkssb_c.restype = None
    native.spkpvn_c.argtypes = [
        integer, pointer(double), double, pointer(integer), pointer(double), pointer(integer),
    ]
    native.spkpvn_c.restype = None
    # Pinned f2c ABI: by-reference handle/descriptor/epoch and caller-owned record.
    for reader in (native.spkr02_, native.spkr03_):
        reader.argtypes = [pointer(integer), pointer(double), pointer(double), pointer(double)]
        reader.restype = None
    native.dafbfs_c.argtypes = [integer]
    native.dafbfs_c.restype = None
    native.daffna_c.argtypes = [pointer(integer)]
    native.daffna_c.restype = None
    native.dafgs_c.argtypes = [pointer(double)]
    native.dafgs_c.restype = None
    native.dafgda_c.argtypes = [integer, integer, integer, pointer(double)]
    native.dafgda_c.restype = None
    native.failed_c.argtypes = []
    native.failed_c.restype = integer
    assert native.failed_c() == 0
    return native


@pytest.mark.parametrize("body,target_id,expected_chain", [
    ("Sun", 10, [(10, 0, 2)]),
    ("Mercury", 1, [(1, 0, 2)]),
    ("Venus", 2, [(2, 0, 2)]),
    ("Earth", 399, [(399, 0, 2)]),
    ("Moon", 301, [(301, 399, 2), (399, 0, 2)]),
    ("Mars", 499, [(499, 4, 3), (4, 0, 2)]),
    ("Jupiter", 599, [(599, 5, 3), (5, 0, 2)]),
    ("Saturn", 699, [(699, 6, 3), (6, 0, 2)]),
])
def test_sampled_spk_chains_match_tudat_states(
    cspice: ctypes.CDLL, body: str, target_id: int,
    expected_chain: list[tuple[int, int, int]],
) -> None:
    """Qualify IDs and segment types at the existing 38 TDB epochs in SSB/J2000."""
    from tudatpy.dynamics import environment_setup

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    spice = ephemeris._ensure_standard_kernels()
    direct_native = environment_setup.create_body_ephemeris(
        environment_setup.ephemeris.direct_spice("SSB", "J2000", body), body,
    )
    assert (direct_native.frame_origin, direct_native.frame_orientation) == ("SSB", "J2000")
    direct_errors_si: list[tuple[float, float]] = []
    observations: set[tuple[int, int, int, float, float, str]] = set()
    for epoch_tdb_s in evidence["epoch_tdb_s"]:
        budget.check()
        current_id = target_id
        for expected_body, expected_center, expected_type in expected_chain:
            assert current_id == expected_body
            handle, found = ctypes.c_int(), ctypes.c_int()
            descriptor = (ctypes.c_double * 5)()
            identifier = ctypes.create_string_buffer(41)
            cspice.spksfs_c(current_id, epoch_tdb_s, 41, ctypes.byref(handle),
                            descriptor, identifier, ctypes.byref(found))
            assert cspice.failed_c() == 0 and found.value == 1, (body, epoch_tdb_s)
            integers = [ctypes.c_int() for _ in range(6)]
            first, last = ctypes.c_double(), ctypes.c_double()
            cspice.spkuds_c(
                descriptor, *[ctypes.byref(value) for value in integers[:4]],
                ctypes.byref(first), ctypes.byref(last),
                *[ctypes.byref(value) for value in integers[4:]],
            )
            assert cspice.failed_c() == 0
            segment_body, center, frame, kind, begin, end = [value.value for value in integers]
            assert (segment_body, center, frame, kind) == (
                expected_body, expected_center, 1, expected_type,
            )
            assert first.value <= epoch_tdb_s <= last.value and 0 < begin <= end
            observations.add((segment_body, center, kind, first.value, last.value,
                              identifier.value.decode("ascii")))
            current_id = center
        assert current_id == 0
        raw_state_km = (ctypes.c_double * 6)()
        cspice.spkssb_c(target_id, epoch_tdb_s, b"J2000", raw_state_km)
        assert cspice.failed_c() == 0
        native_state_si = np.asarray(raw_state_km) * 1000.0
        tudat_state_si = spice.get_body_cartesian_state_at_epoch(
            body, "SSB", "J2000", "NONE", epoch_tdb_s,
        )
        difference_si = native_state_si - tudat_state_si
        assert np.all(np.isfinite(difference_si))
        assert np.linalg.norm(difference_si[:3]) <= 0.001  # m
        assert np.linalg.norm(difference_si[3:]) <= 0.000001  # m/s
        difference_si = direct_native.cartesian_state(epoch_tdb_s) - native_state_si
        assert np.all(np.isfinite(difference_si))
        error_m = float(np.linalg.norm(difference_si[:3]))
        error_m_s = float(np.linalg.norm(difference_si[3:]))
        assert error_m <= 0.001 and error_m_s <= 0.000001
        direct_errors_si.append((error_m, error_m_s))
        budget.check()
    assert budget.native_arc_propagations == 0
    print(json.dumps({
        "body": body, "effective_spk_target_id": target_id,
        "epoch_count": len(evidence["epoch_tdb_s"]),
        "time": "TDB seconds since J2000", "frame": "SSB/J2000",
        "segments": sorted(observations),
        "experimental_direct_native_max_position_error_m": max(value[0] for value in direct_errors_si),
        "experimental_direct_native_max_velocity_error_m_s": max(value[1] for value in direct_errors_si),
        "scope": "Sampled chain metadata and state parity, not full interval coverage",
    }, sort_keys=True, allow_nan=False))


@pytest.mark.parametrize("step_s", [300.0, 150.0, 75.0])
def test_saturn_spk_segment_junction(cspice: ctypes.CDLL, step_s: float) -> None:
    """Reproduce a failed allocation, not a passing interpolation qualification."""
    from tudatpy.dynamics import environment_setup

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    spice = ephemeris._ensure_standard_kernels()
    junction_tdb_s = 986817600.0
    epochs_tdb_s = [math.nextafter(junction_tdb_s, -math.inf), junction_tdb_s,
                    math.nextafter(junction_tdb_s, math.inf)]
    junction_states_si: list[np.ndarray] = []
    descriptors: list[bytes] = []
    for epoch_tdb_s in epochs_tdb_s:
        budget.check()
        handle, found = ctypes.c_int(), ctypes.c_int()
        descriptor = (ctypes.c_double * 5)()
        identifier = ctypes.create_string_buffer(41)
        cspice.spksfs_c(699, epoch_tdb_s, 41, ctypes.byref(handle), descriptor,
                        identifier, ctypes.byref(found))
        assert cspice.failed_c() == 0 and found.value == 1
        descriptors.append(bytes(descriptor))
        # The first two descriptor doubles are coverage endpoints (SPK ND=2).
        assert descriptor[0] <= junction_tdb_s <= descriptor[1]
        frame, center = ctypes.c_int(), ctypes.c_int()
        state_km = (ctypes.c_double * 6)()
        cspice.spkpvn_c(handle, descriptor, junction_tdb_s, ctypes.byref(frame),
                        state_km, ctypes.byref(center))
        assert cspice.failed_c() == 0 and (frame.value, center.value) == (1, 6)
        state_si = np.asarray(state_km).copy() * 1000.0
        assert np.all(np.isfinite(state_si))
        junction_states_si.append(state_si)
    assert descriptors[0] != descriptors[2]
    assert descriptors[1] in (descriptors[0], descriptors[2])
    difference_si = junction_states_si[2] - junction_states_si[0]
    jump_m = float(np.linalg.norm(difference_si[:3]))
    jump_m_s = float(np.linalg.norm(difference_si[3:]))
    # Counterexample: one value cannot be within 0.025 m of both segment values.
    assert jump_m > 2 * 0.025

    start_s, end_s = evidence["epoch_tdb_s"][0], evidence["epoch_tdb_s"][-1]
    if step_s == 300.0:
        settings = trajectory._create_time_limited_body_settings(environment_setup, start_s, end_s)
    else:
        settings = environment_setup.get_default_body_settings_time_limited(
            trajectory.PHYSICAL_BODY_NAMES, start_s, end_s, "SSB", "J2000", step_s,
        )
    assert settings.get("Saturn").ephemeris_settings.time_step == step_s
    budget.check()
    native = environment_setup.create_body_ephemeris(settings.get("Saturn").ephemeris_settings,
                                                    "Saturn")
    safe_start_s, safe_end_s = environment_setup.get_safe_interpolation_interval(native)
    assert safe_start_s <= start_s < end_s <= safe_end_s
    assert (native.frame_origin, native.frame_orientation) == ("SSB", "J2000")
    budget.check()
    errors_si: list[tuple[float, float]] = []
    for epoch_tdb_s in epochs_tdb_s:
        direct_si = spice.get_body_cartesian_state_at_epoch(
            "Saturn", "SSB", "J2000", "NONE", epoch_tdb_s,
        )
        difference_si = native.cartesian_state(epoch_tdb_s) - direct_si
        assert np.all(np.isfinite(difference_si))
        error_m = float(np.linalg.norm(difference_si[:3]))
        error_m_s = float(np.linalg.norm(difference_si[3:]))
        errors_si.append((error_m, error_m_s))
        budget.check()
    assert max(value[0] for value in errors_si) > 0.025
    assert max(value[1] for value in errors_si) > 2.5e-6
    assert budget.native_arc_propagations == 0
    print(json.dumps({
        "junction_tdb_s": junction_tdb_s, "time": "TDB seconds since J2000",
        "table_step_s": step_s,
        "segment_state_frame": "Saturn barycenter/J2000", "units": ["m", "m/s"],
        "same_epoch_segment_difference": [jump_m, jump_m_s],
        "junction_selection_after_left_query": "left" if descriptors[1] == descriptors[0] else "right",
        "query_epochs_tdb_s": epochs_tdb_s, "interpolation_state_frame": "SSB/J2000",
        "interpolation_errors": errors_si,
        "qualification_status": "failed-existing-interpolation-allocation",
        "scope": "Regression of a counterexample, not a passing safety qualification",
    }, sort_keys=True, allow_nan=False))


def test_saturn_junction_query_order_is_repeatable(cspice: ctypes.CDLL) -> None:
    """Qualify all six local query orders without resetting the loaded kernel pool."""
    spice = ephemeris._ensure_standard_kernels()
    budget = trajectory._RefinementBudget("d0001-t0035", 300.0)
    junction_tdb_s = 986817600.0
    epochs_tdb_s = (math.nextafter(junction_tdb_s, -math.inf), junction_tdb_s,
                    math.nextafter(junction_tdb_s, math.inf))
    reference_bits: dict[float, np.ndarray] = {}
    selection_coverage: set[tuple[float, float]] = set()
    for order in permutations(epochs_tdb_s):
        for epoch_tdb_s in order:
            budget.check()
            for _ in range(2):
                state_si = spice.get_body_cartesian_state_at_epoch(
                    "Saturn", "SSB", "J2000", "NONE", epoch_tdb_s,
                )
                assert np.all(np.isfinite(state_si))
                bits = state_si.view(np.uint64)
                if epoch_tdb_s not in reference_bits:
                    reference_bits[epoch_tdb_s] = bits.copy()
                np.testing.assert_array_equal(bits, reference_bits[epoch_tdb_s])
            raw_state_km = (ctypes.c_double * 6)()
            cspice.spkssb_c(699, epoch_tdb_s, b"J2000", raw_state_km)
            assert cspice.failed_c() == 0
            raw_state_si = np.asarray(raw_state_km) * 1000.0
            np.testing.assert_array_equal(raw_state_si.view(np.uint64),
                                          reference_bits[epoch_tdb_s])
            if epoch_tdb_s == junction_tdb_s:
                handle, found = ctypes.c_int(), ctypes.c_int()
                descriptor = (ctypes.c_double * 5)()
                identifier = ctypes.create_string_buffer(41)
                cspice.spksfs_c(699, epoch_tdb_s, 41, ctypes.byref(handle), descriptor,
                                identifier, ctypes.byref(found))
                assert cspice.failed_c() == 0 and found.value == 1
                selection_coverage.add((descriptor[0], descriptor[1]))
            budget.check()
    assert selection_coverage == {(952430400.0, junction_tdb_s)}
    assert len(reference_bits) == 3 and budget.native_arc_propagations == 0
    print(json.dumps({
        "junction_tdb_s": junction_tdb_s, "time": "TDB seconds since J2000",
        "state_frame": "SSB/J2000", "state_units": ["m", "m/s"],
        "orders": 6, "named_queries": 36, "raw_cspice_queries": 18,
        "comparison": "Exact binary64 component bit patterns",
        "exact_junction_selected_coverage_tdb_s": sorted(selection_coverage),
        "scope": "Local query-order repeatability, not continuity or interpolation accuracy",
    }, sort_keys=True, allow_nan=False))


def test_saturn_source_file_segment_inventory(cspice: ctypes.CDLL) -> None:
    """Exhaust one file and its two relevant Saturn record directories, not all sources."""
    from tudatpy.dynamics import environment_setup

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    start_s, end_s = evidence["epoch_tdb_s"][0], evidence["epoch_tdb_s"][-1]
    handle, found = ctypes.c_int(), ctypes.c_int()
    # DAF's maximum packed-summary size; SPK consumes its first five doubles.
    summary = (ctypes.c_double * 125)()
    identifier = ctypes.create_string_buffer(41)
    cspice.spksfs_c(699, start_s, 41, ctypes.byref(handle), summary,
                    identifier, ctypes.byref(found))
    assert cspice.failed_c() == 0 and found.value == 1
    cspice.dafbfs_c(handle)
    assert cspice.failed_c() == 0
    count = saturn_count = 0
    overlaps: list[tuple[float, float, int, int]] = []
    while True:
        budget.check()
        cspice.daffna_c(ctypes.byref(found))
        assert cspice.failed_c() == 0 and found.value in (0, 1)
        if not found.value:
            break
        count += 1
        cspice.dafgs_c(summary)
        assert cspice.failed_c() == 0
        integers = [ctypes.c_int() for _ in range(6)]
        first, last = ctypes.c_double(), ctypes.c_double()
        cspice.spkuds_c(summary, *[ctypes.byref(value) for value in integers[:4]],
                        ctypes.byref(first), ctypes.byref(last),
                        *[ctypes.byref(value) for value in integers[4:]])
        assert cspice.failed_c() == 0
        body, center, frame, kind, begin, end = [value.value for value in integers]
        if body == 699:
            saturn_count += 1
            assert (center, frame, kind) == (6, 1, 3)
            assert math.isfinite(first.value) and math.isfinite(last.value)
            assert first.value < last.value and 0 < begin <= end
            if first.value <= end_s and last.value >= start_s:
                overlaps.append((first.value, last.value, begin, end))
    # Keep file order: the left interval is stored after the right interval.
    assert (count, saturn_count) == (1223, 171)
    assert overlaps == [
        (986817600.0, 1021204800.0, 25956465, 25968668),
        (952430400.0, 986817600.0, 25969025, 25981228),
    ]
    assert overlaps[1][0] <= start_s < overlaps[1][1] == overlaps[0][0] < end_s <= overlaps[0][1]
    record_boundaries_tdb_s: set[float] = set()
    record_endpoints_si: dict[float, list[tuple[Fraction, ...]]] = {}
    near_endpoints_m: dict[float, list[tuple[tuple[Fraction, ...], float]]] = {}
    record_rate_bounds_m_s: list[float] = []
    join_offset_s = Fraction(1, 8388608)  # One binary64 epoch ULP in this interval.
    overlapping_record_count = 0
    for segment_start_s, segment_end_s, begin, end in overlaps:
        directory = (ctypes.c_double * 4)()
        cspice.dafgda_c(handle, end - 3, end, directory)
        assert cspice.failed_c() == 0
        # Type 3: INIT, INTLEN, RSIZE, N; six polynomial coefficient sets.
        assert list(directory) == [segment_start_s, 343872.0, 122.0, 100.0]
        assert (122 - 2) // 6 - 1 == 19
        assert end - begin + 1 == 100 * 122 + 4
        assert segment_start_s + 100 * 343872 == segment_end_s
        for index in range(100):
            budget.check()
            address = begin + index * 122
            record = (ctypes.c_double * 122)()
            cspice.dafgda_c(handle, address, address + 121, record)
            assert cspice.failed_c() == 0
            record_start_s = segment_start_s + index * 343872
            record_end_s = record_start_s + 343872
            assert list(record[:2]) == [record_start_s + 171936, 171936.0]
            assert all(math.isfinite(value) for value in record)
            if record_start_s <= end_s and record_end_s >= start_s:
                overlapping_record_count += 1
                coefficients_km = tuple(tuple(record[2 + axis * 20 + degree]
                                              for degree in range(20)) for axis in range(3))
                rate_bound_m_s = trajectory._spk_position_rate_bound(budget, coefficients_km, record[1])
                record_rate_bounds_m_s.append(rate_bound_m_s)
                derivative_coefficients = np.polynomial.chebyshev.chebder(
                    np.asarray(coefficients_km).T, axis=0,
                ) * (1000 / record[1])
                for normalized_time in (-1.0, -0.5, 0.0, 0.5, 1.0):
                    derivative_m_s = np.polynomial.chebyshev.chebval(
                        normalized_time, derivative_coefficients,
                    )
                    assert np.linalg.norm(derivative_m_s) <= rate_bound_m_s
                record_boundaries_tdb_s.update(
                    epoch_s for epoch_s in (record_start_s, record_end_s)
                    if start_s < epoch_s < end_s
                )
                for epoch_s, sign in ((record_start_s, -1), (record_end_s, 1)):
                    if start_s < epoch_s < end_s:
                        # T_k(+1)=1 and T_k(-1)=(-1)^k, evaluated exactly.
                        endpoint_si = tuple(
                            1000 * sum((Fraction(record[2 + component * 20 + degree]) * sign ** degree
                                        for degree in range(20)), Fraction(0))
                            for component in range(6)
                        )
                        coefficients = np.asarray(record)[2:].reshape(6, 20)
                        clenshaw_si = np.polynomial.chebyshev.chebval(sign, coefficients.T) * 1000
                        oracle_difference_si = clenshaw_si - np.asarray([float(value) for value in endpoint_si])
                        assert np.linalg.norm(oracle_difference_si[:3]) <= 1e-8  # m
                        assert np.linalg.norm(oracle_difference_si[3:]) <= 1e-12  # m/s
                        record_endpoints_si.setdefault(epoch_s, []).append(endpoint_si)
                        # Exact recurrence at one epoch ULP inside this record.
                        normalized_time = sign * (1 - join_offset_s / Fraction(record[1]))
                        basis = [Fraction(1), normalized_time]
                        for degree in range(2, 20):
                            basis.append(2 * normalized_time * basis[-1] - basis[-2])
                        near_m = tuple(1000 * sum((Fraction(row[degree]) * basis[degree]
                                                 for degree in range(20)), Fraction(0))
                                       for row in coefficients_km)
                        near_endpoints_m.setdefault(epoch_s, []).append((near_m, rate_bound_m_s))
    assert overlapping_record_count == 74 and len(record_boundaries_tdb_s) == 73
    assert 986817600.0 in record_boundaries_tdb_s
    assert set(record_endpoints_si) == record_boundaries_tdb_s
    coefficient_jumps_si: list[tuple[float, float, float]] = []
    incompatible_position_joins = incompatible_velocity_joins = 0
    for epoch_s, endpoints in sorted(record_endpoints_si.items()):
        assert len(endpoints) == 2
        difference_si = tuple(a - b for a, b in zip(*endpoints))
        near_left, near_right = near_endpoints_m[epoch_s]
        motion_m = sum((abs(a - b) for a, b in zip(near_left[0], near_right[0])), Fraction(0))
        within_records_m = join_offset_s * (Fraction(near_left[1]) + Fraction(near_right[1]))
        jump_m = sum((abs(value) for value in difference_si[:3]), Fraction(0))
        assert motion_m <= within_records_m + jump_m
        assert motion_m > within_records_m  # Omitting the source jump is invalid.
        # Exact squared SI norms decide allocation exceedance; floats are reporting only.
        position_squared_m2 = sum((value * value for value in difference_si[:3]), Fraction(0))
        velocity_squared_m2_s2 = sum((value * value for value in difference_si[3:]), Fraction(0))
        assert position_squared_m2 > 0 and velocity_squared_m2_s2 > 0
        incompatible_position_joins += position_squared_m2 > (2 * Fraction("0.025")) ** 2
        incompatible_velocity_joins += velocity_squared_m2_s2 > (2 * Fraction("0.0000025")) ** 2
        coefficient_jumps_si.append((epoch_s, math.sqrt(float(position_squared_m2)),
                                     math.sqrt(float(velocity_squared_m2_s2))))
    assert (incompatible_position_joins, incompatible_velocity_joins) == (70, 68)
    settings = trajectory._create_time_limited_body_settings(environment_setup, start_s, end_s)
    budget.check()
    native = environment_setup.create_body_ephemeris(settings.get("Saturn").ephemeris_settings,
                                                    "Saturn")
    budget.check()
    spice = ephemeris._ensure_standard_kernels()
    boundary_errors_si: list[tuple[float, float, float]] = []
    direct_settings = environment_setup.ephemeris.direct_spice("SSB", "J2000", "Saturn")
    direct_native = environment_setup.create_body_ephemeris(direct_settings, "Saturn")
    assert (direct_native.frame_origin, direct_native.frame_orientation) == ("SSB", "J2000")
    budget.check()
    direct_native_errors_si: list[tuple[float, float]] = []
    for boundary_s in sorted(record_boundaries_tdb_s):
        errors_si: list[tuple[float, float]] = []
        for epoch_s in (math.nextafter(boundary_s, -math.inf), boundary_s,
                        math.nextafter(boundary_s, math.inf)):
            budget.check()
            direct_si = spice.get_body_cartesian_state_at_epoch("Saturn", "SSB", "J2000", "NONE",
                                                               epoch_s)
            native_difference_si = direct_native.cartesian_state(epoch_s) - direct_si
            assert np.all(np.isfinite(native_difference_si))
            native_error_m = float(np.linalg.norm(native_difference_si[:3]))
            native_error_m_s = float(np.linalg.norm(native_difference_si[3:]))
            assert native_error_m <= 0.001 and native_error_m_s <= 0.000001
            direct_native_errors_si.append((native_error_m, native_error_m_s))
            difference_si = native.cartesian_state(epoch_s) - direct_si
            assert np.all(np.isfinite(difference_si))
            errors_si.append((float(np.linalg.norm(difference_si[:3])),
                              float(np.linalg.norm(difference_si[3:]))))
        boundary_errors_si.append((boundary_s, max(value[0] for value in errors_si),
                                   max(value[1] for value in errors_si)))
    position_failures = sum(value[1] > 0.025 for value in boundary_errors_si)
    velocity_failures = sum(value[2] > 2.5e-6 for value in boundary_errors_si)
    # Preserve the observed failure population, not a relaxed acceptance limit.
    assert (position_failures, velocity_failures) == (73, 71)
    budget.check()
    assert budget.native_arc_propagations == 0
    print(json.dumps({
        "candidate_id": evidence["candidate_id"], "file_segment_count": count,
        "saturn_segment_count": saturn_count, "overlaps_in_file_order": overlaps,
        "overlap_fields": ["start_tdb_s", "end_tdb_s", "first_daf_word", "last_daf_word"],
        "record_duration_s": 343872, "polynomial_degree": 19,
        "record_headers_checked": 200, "candidate_overlapping_records": overlapping_record_count,
        "candidate_interior_record_boundaries_tdb_s": sorted(record_boundaries_tdb_s),
        "boundary_error_fields": ["boundary_tdb_s", "max_position_error_m", "max_velocity_error_m_s"],
        "boundary_errors": boundary_errors_si,
        "coefficient_jump_fields": ["boundary_tdb_s", "position_jump_m", "velocity_jump_m_s"],
        "coefficient_jumps": coefficient_jumps_si,
        "joins_exceeding_twice_position_allocation": incompatible_position_joins,
        "joins_exceeding_twice_velocity_allocation": incompatible_velocity_joins,
        "coefficient_frame": "Saturn barycenter/J2000",
        "record_position_rate_bound_min_m_s": min(record_rate_bounds_m_s),
        "record_position_rate_bound_max_m_s": max(record_rate_bounds_m_s),
        "exact_jump_inclusive_motion_controls": len(near_endpoints_m),
        "position_failed_boundaries": position_failures, "velocity_failed_boundaries": velocity_failures,
        "position_worst_boundary": max(boundary_errors_si, key=lambda row: row[1]),
        "velocity_worst_boundary": max(boundary_errors_si, key=lambda row: row[2]),
        "comparison_frame": "SSB/J2000", "comparison_query_count": 219,
        "experimental_direct_native_query_count": len(direct_native_errors_si),
        "experimental_direct_native_max_position_error_m": max(value[0] for value in direct_native_errors_si),
        "experimental_direct_native_max_velocity_error_m_s": max(value[1] for value in direct_native_errors_si),
        "qualification_status": "failed-existing-interpolation-allocation",
        "time": "TDB seconds since J2000", "target": 699, "center": 6, "frame": "J2000",
        "scope": "One file and two Saturn record directories; not all sources or coefficient error bounds",
    }, sort_keys=True, allow_nan=False))


@pytest.mark.parametrize("body,epoch_tdb_s,error_code", [
    ("ARIADNA_UNKNOWN_BODY", 986817600.0, r"SPICE\(IDCODENOTFOUND\)"),
    ("Saturn", -1e12, r"SPICE\(SPKINSUFFDATA\)"),
    ("Saturn", 1e12, r"SPICE\(SPKINSUFFDATA\)"),
])
def test_direct_spice_errors_do_not_poison_valid_queries(
    body: str, epoch_tdb_s: float, error_code: str,
) -> None:
    """Native errors must raise and leave valid direct queries repeatable without reset."""
    import spiceypy
    from tudatpy.dynamics import environment_setup

    budget = trajectory._RefinementBudget("d0001-t0035", 300.0)
    spice = ephemeris._ensure_standard_kernels()
    kernel_count = spice.get_total_count_of_kernels_loaded()
    valid = environment_setup.create_body_ephemeris(
        environment_setup.ephemeris.direct_spice("SSB", "J2000", "Saturn"), "Saturn",
    )
    baseline_si = valid.cartesian_state(986817600.0)
    assert np.all(np.isfinite(baseline_si))
    budget.check()
    with pytest.raises(RuntimeError, match=error_code) as error:
        invalid = environment_setup.create_body_ephemeris(
            environment_setup.ephemeris.direct_spice("SSB", "J2000", body), body,
        )
        invalid.cartesian_state(epoch_tdb_s)
    assert body.upper() in str(error.value).upper()
    assert not spiceypy.failed()
    recovered_si = valid.cartesian_state(986817600.0)
    np.testing.assert_array_equal(recovered_si.view(np.uint64), baseline_si.view(np.uint64))
    assert spice.get_total_count_of_kernels_loaded() == kernel_count
    budget.check()
    assert budget.native_arc_propagations == 0


def test_unknown_spk_body_has_no_descriptor(cspice: ctypes.CDLL) -> None:
    """An unknown ID must not produce a fabricated usable segment."""
    handle, found = ctypes.c_int(), ctypes.c_int()
    descriptor = (ctypes.c_double * 5)()
    identifier = ctypes.create_string_buffer(41)
    cspice.spksfs_c(-2147483647, 978995455.2304223, 41, ctypes.byref(handle),
                    descriptor, identifier, ctypes.byref(found))
    assert cspice.failed_c() == 0 and found.value == 0
