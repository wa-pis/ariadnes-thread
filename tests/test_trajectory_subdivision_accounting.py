"""Analytic subdivision cost controls; not qualified native subarcs."""

from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path

import pytest

from test_trajectory_error_transport import _coast_error_envelope


@pytest.mark.parametrize("count", [1, 2, 4, 8, 16, 32])
@pytest.mark.parametrize("channels", [(0, 0, 0, 0), (0, 2, 0, 0), (1, 0, 0, 0),
                                     (1, 2, F(1, 100), F(1, 1000)), (0, 0, 0, F(1, 1000))])
@pytest.mark.parametrize("sign", [-1, 1])
def test_subdivision_preserves_defect_and_repeated_residual_costs(count: int, channels: tuple, sign: int) -> None:
    """Smooth truth, piecewise reference and exact endpoint perturbations attain the ledger."""
    horizon = F(1, 8)
    step = horizon/count
    assert F(float(step)) == step
    d, j, rp, rv = map(F, channels)
    p0, v0 = F(1, 10000), F(1, 10**7)
    p, v = p0, v0
    reference_p, reference_v = -sign*p0, -sign*v0
    for i in range(1, count+1):
        start = (i-1)*step
        # Truth acceleration is sign*(D+J*t), smooth across all joins.
        # Reference acceleration sign*J*start yields local defect D+J*tau.
        acceleration = sign*j*start
        reference_p += reference_v*step+acceleration*step**2/2-sign*rp
        reference_v += acceleration*step-sign*rv
        p, v = _coast_error_envelope(float(step), p, v, F(0), F(0), d, acceleration_defect_rate_m_s3=j)
        p, v = p+rp, v+rv  # Charge every endpoint once; never reset incoming error.
        time = i*step
        truth_p = sign*(d*time**2/2+j*time**3/6)
        truth_v = sign*(d*time+j*time**2/2)
        assert abs(truth_p-reference_p) == p
        assert abs(truth_v-reference_v) == v
        assert v == v0+d*time+j*i*step**2/2+i*rv
        assert p == p0+time*v0+d*time**2/2+j*step**3*i*(3*i-1)/12+i*rp+rv*step*i*(i-1)/2


def test_fourth_endpoint_hypothetical_subdivision_allowances() -> None:
    """Sensitivity screen only: the benchmark rate is NOT uniform over new references."""
    root = Path(__file__).parent / "data"
    hashes = {}

    def read(name: str, key: str) -> dict:
        raw = (root/name).read_bytes()
        hashes[name] = sha256(raw).hexdigest()
        return json.loads(raw)[key]

    endpoint = read("m3_fresh_endpoint_binding.json", "fresh_endpoint_binding")
    benchmark = read("m3_fourth_conditional_local_translation.json", "fourth_conditional_local_translation")
    source = read("m3_fourth_endpoint_source_anchor.json", "fourth_endpoint_source_anchor")
    assert source["epoch_tdb_s"] == endpoint["end_epoch_tdb_s"]
    horizon = F(source["end_epoch_tdb_s"])-F(source["epoch_tdb_s"])
    assert horizon == F(benchmark["duration_s"]) == F(1, 8)
    p0, v0 = map(F, endpoint["outgoing_error_m_m_s"])
    j = F(benchmark["translation_rate_upper_m_s3"])
    rows = []
    for count in (1, 2, 4, 8, 16, 32):
        # Deliberately optimistic: shared constant J assumed, Lx=Lv=D=0,
        # with zero new residuals until the conditional allowances below.
        p = p0+horizon*v0+j*horizon**3*(3*count-1)/(12*count**2)
        v = v0+j*horizon**2/(2*count)
        velocity_room = F("0.000001")-v
        position_room = F("0.001")-p
        # Exact recurrence independently checks closed-form arithmetic.
        pr, vr = p0, v0
        for _ in range(count):
            pr, vr = _coast_error_envelope(float(horizon/count), pr, vr, F(0), F(0), F(0), acceleration_defect_rate_m_s3=j)
        assert (pr, vr) == (p, v)
        rows.append({"reference_piece_count": count, "step_s": float(horizon/count),
                     "optimistic_position_m_approx": float(p), "optimistic_velocity_m_s_approx": float(v),
                     "fits_both_without_other_costs": p <= F("0.001") and v <= F("0.000001"),
                     "velocity_room_m_s_approx": float(velocity_room),
                     "constant_D_cap_from_velocity_m_s2_approx": float(velocity_room/horizon),
                     "per_piece_velocity_residual_cap_from_velocity_m_s_approx": float(velocity_room/count),
                     "per_piece_position_residual_cap_from_position_m_approx": float(position_room/count)})
    print(json.dumps({"fourth_hypothetical_subdivision_allowances": {
        "input_sha256": hashes, "horizon_s": float(horizon), "incoming_error_m_m_s": [float(p0), float(v0)],
        "hypothetical_common_J_m_s3": float(j), "rows": rows,
        "additional_ephemeris_queries": 0, "additional_native_arcs": 0,
        "scope": "Optimistic algebraic sensitivity only, assuming the benchmark J on every future piece without qualification; signed caps are approximate, separate intercepts not simultaneous allocations; not new arc counts, full-force composition, native residual bounds or a selected partition",
    }}, sort_keys=True, allow_nan=False))
