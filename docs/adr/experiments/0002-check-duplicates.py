"""Stop one inventory at its first exact repeated harmonic-error input."""
from fractions import Fraction
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
import pytest

sys.path.insert(0, str(Path.cwd() / "tests"))
import test_trajectory_spk as inventory  # noqa: E402 -- repository test helpers after path setup.

original = inventory._generic_harmonic_term_errors_m_s2
seen: dict[tuple[object, ...], int] = {}
observations: list[dict[str, object]] = []
budget_identity: list[int] = []


def observe(
    budget: inventory.trajectory._RefinementBudget,
    gm_m3_s2: float, reference_radius_m: float,
    cosine: np.ndarray, sine: np.ndarray,
    body_position_m: np.ndarray, spacecraft_position_m: np.ndarray,
    inertial_to_fixed: np.ndarray, observed_terms_m_s2: np.ndarray,
) -> dict[tuple[int, int], Fraction]:
    budget.check()
    assert type(gm_m3_s2) is float and type(reference_radius_m) is float
    arrays = (cosine, sine, body_position_m, spacecraft_position_m,
              inertial_to_fixed, observed_terms_m_s2)
    assert all(isinstance(array, np.ndarray) for array in arrays)
    if not budget_identity:
        budget_identity.append(id(budget))
    assert id(budget) == budget_identity[0]
    key = (gm_m3_s2.hex(), reference_radius_m.hex(),
           *((array.shape, array.dtype.str, array.tobytes(order="C")) for array in arrays))
    call = len(observations) + 1
    entry: dict[str, object] = {
        "call": call, "prefix_degree": len(cosine) - 1,
        "gm_m3_s2": gm_m3_s2, "reference_radius_m": reference_radius_m,
        "native_arc_propagations": budget.native_arc_propagations,
        "duplicate_of": seen.get(key),
    }
    observations.append(entry)
    if key in seen:
        raise RuntimeError("DIAGNOSTIC_STOP: exact duplicate found; no cached result returned")
    seen[key] = call
    started = perf_counter()
    result = original(budget, gm_m3_s2, reference_radius_m, *arrays)
    entry["uncached_elapsed_s"] = perf_counter() - started
    return result


inventory._generic_harmonic_term_errors_m_s2 = observe
status = pytest.main([
    "tests/test_trajectory_spk.py::test_loaded_spk_chain_coverage_contains_candidate_interval[native-readback]",
    "-q", "--tb=short", "--show-capture=no", "-p", "no:cacheprovider",
])
print(json.dumps({"pytest_exit_code": int(status), "observations": observations,
                  "qualification": "Diagnostic early stop, not a test pass or speedup measurement"}, indent=2))
raise SystemExit(status)
