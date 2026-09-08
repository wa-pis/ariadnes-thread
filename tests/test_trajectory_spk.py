"""Read-only SPK provenance controls, not a between-epoch error certificate."""

from __future__ import annotations

import ctypes
import json
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
    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    spice = ephemeris._ensure_standard_kernels()
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
        budget.check()
    assert budget.native_arc_propagations == 0
    print(json.dumps({
        "body": body, "effective_spk_target_id": target_id,
        "epoch_count": len(evidence["epoch_tdb_s"]),
        "time": "TDB seconds since J2000", "frame": "SSB/J2000",
        "segments": sorted(observations),
        "scope": "Sampled chain metadata and state parity, not full interval coverage",
    }, sort_keys=True, allow_nan=False))


def test_unknown_spk_body_has_no_descriptor(cspice: ctypes.CDLL) -> None:
    """An unknown ID must not produce a fabricated usable segment."""
    handle, found = ctypes.c_int(), ctypes.c_int()
    descriptor = (ctypes.c_double * 5)()
    identifier = ctypes.create_string_buffer(41)
    cspice.spksfs_c(-2147483647, 978995455.2304223, 41, ctypes.byref(handle),
                    descriptor, identifier, ctypes.byref(found))
    assert cspice.failed_c() == 0 and found.value == 0
