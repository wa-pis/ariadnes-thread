"""Read-only tail/budget audit; run from the repository root in space-nav.

No harmonic vector, native propagation or mission certificate is produced.
Reported velocity/intercept decimals are approximations; comparisons are exact.
"""

from fractions import Fraction as F
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))

from space_nav import trajectory as t  # noqa: E402
from test_trajectory_error_transport import _coast_error_envelope  # noqa: E402
from test_trajectory_spk import (  # noqa: E402
    _dyadic_sqrt_bounds, _harmonic_remainder_anchor_error_bound_m_s2,
)


def main() -> None:
    budget = t._RefinementBudget("fourth-harmonic-tail-audit", 300.0)
    started = perf_counter()
    hashes = {}

    def read(name, key):
        data = (ROOT / "tests/data" / name).read_bytes()
        hashes[name] = sha256(data).hexdigest()
        return json.loads(data)[key]

    sensitivity = read("m3_quarter_second_force_sensitivities.json", "quarter_second_force_sensitivities")
    domain = read("m3_quarter_second_initial_domain.json", "quarter_second_initial_domain")
    endpoint = read("m3_fresh_endpoint_binding.json", "fresh_endpoint_binding")
    sources = read("m3_fourth_endpoint_source_anchor.json", "fourth_endpoint_source_anchor")
    assert sources["epoch_tdb_s"] == endpoint["end_epoch_tdb_s"]
    assert sources["end_epoch_tdb_s"] == domain["end_epoch_tdb_s"] == sensitivity["end_epoch_tdb_s"]
    for data in (sensitivity, domain, endpoint, sources):
        assert (data["origin"], data["orientation"], data["time_scale"]) == ("SSB", "J2000", "TDB seconds since J2000")
    assert sensitivity["model_id"] == domain["model_id"] == endpoint["model_id"] == t.PHYSICAL_MODEL_IDENTIFIER
    p0, v0 = map(F, endpoint["outgoing_error_m_m_s"])
    h = F(sources["end_epoch_tdb_s"]) - F(sources["epoch_tdb_s"])
    assert h == F(1, 8)
    lx, lv = F(sensitivity["position_upper_s_inv2"]), F(sensitivity["velocity_upper_s_inv"])
    light = 2 * (F(domain["srp_upper_m_s2"]) + F(domain["schwarzschild_upper_m_s2"]))
    feedback = lx*h*h/2 + lv*h
    _, base = _coast_error_envelope(float(h), p0, v0, lx, lv, light)
    cap = (F("0.000001") - base)*(1-feedback)/h
    assert cap > 0
    fields = {}
    for body, cutoffs in (("Moon", [2]), ("Mars", range(100, 121))):
        spec = next(item for item in t._HARMONIC_FIELD_SPECS if item.body == body)
        path = t._default_gravity_models_path()/body/spec.file_name
        assert t._coefficient_sha256(path) == spec.expected_sha256
        field = t._load_harmonic_field_settings(t._import_tudat_environment_setup(), spec, path)
        assert field.gravitational_parameter == spec.gravitational_parameter_m3_s2
        assert field.reference_radius == spec.normalization_radius_m
        source = [F(int(n, 16), int(d, 16)) for n, d in sources["bodies"][body]["state_exact_m_m_s"][:3]]
        relative = [F(a)-b for a, b in zip(endpoint["terminal_state_m_m_s_kg"][:3], source, strict=True)]
        lower = _dyadic_sqrt_bounds(sum(x*x for x in relative))[0]
        anchor_floor = math.nextafter(float(lower), -math.inf)
        domain_floor = sensitivity["distance_floors_m"][body]
        assert domain_floor == domain["distance_floors_m"][body]
        assert 0 < F(domain_floor) <= F(anchor_floor) <= lower
        cases = {}
        for name, floor in (("whole_domain", domain_floor), ("nominal_anchor", anchor_floor)):
            rows = []
            for cutoff in cutoffs:
                tail = _harmonic_remainder_anchor_error_bound_m_s2(
                    budget, field.gravitational_parameter, field.reference_radius, floor,
                    field.normalized_cosine_coefficients, field.normalized_sine_coefficients,
                    (F(0),)*3, excluded_through_degree=cutoff,
                )
                _, velocity = _coast_error_envelope(float(h), p0, v0, lx, lv, light+tail)
                assert (tail <= cap) == (velocity <= F("0.000001"))
                rows.append({"cutoff": cutoff, "tail_norm_upper_m_s2": float(tail),
                             "fits_optimistic_anchor_intercept": tail <= cap,
                             "optimistic_velocity_formula_m_s_approx": float(velocity)})
            assert all(a["tail_norm_upper_m_s2"] >= b["tail_norm_upper_m_s2"]
                       for a, b in zip(rows, rows[1:]))
            cases[name] = {"distance_floor_m": floor, "rows": rows}
        fields[body] = {"resource_sha256": spec.expected_sha256, "cases": cases}
    for name, expected in (("whole_domain", 120), ("nominal_anchor", 115)):
        assert next(row["cutoff"] for row in fields["Mars"]["cases"][name]["rows"]
                    if row["fits_optimistic_anchor_intercept"]) == expected
    budget.check()
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)
    print(json.dumps({"input_sha256": hashes, "fields": fields, "anchor_intercept_m_s2_approx": float(cap),
                      "elapsed_s": perf_counter()-started,
                      "scope": "Ideal orthogonal-frame tail bounds and optimistic scalar budget only; no stored-matrix/native errors, full-force reference, J, residual or mission qualification"},
                     sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
