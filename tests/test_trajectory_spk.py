"""Read-only SPK provenance controls, not a between-epoch error certificate."""

from __future__ import annotations

import ctypes
from fractions import Fraction
import json
from itertools import permutations
import math
from pathlib import Path
import platform
import sys

import numpy as np
import pytest

from space_nav import ephemeris, trajectory


ROOT = Path(__file__).resolve().parents[1]


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
    assert overlapping_record_count == 74 and len(record_boundaries_tdb_s) == 73
    assert 986817600.0 in record_boundaries_tdb_s
    assert set(record_endpoints_si) == record_boundaries_tdb_s
    coefficient_jumps_si: list[tuple[float, float, float]] = []
    incompatible_position_joins = incompatible_velocity_joins = 0
    for epoch_s, endpoints in sorted(record_endpoints_si.items()):
        assert len(endpoints) == 2
        difference_si = tuple(a - b for a, b in zip(*endpoints))
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
