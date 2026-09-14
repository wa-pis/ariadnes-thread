"""Pure text-PCK angle controls; no kernel or native orientation queries."""

from fractions import Fraction
import math

import pytest

from space_nav import trajectory
from test_trajectory_spk import _pck_angle_intervals_deg


def _inputs() -> dict[str, list[float]]:
    result = {f"BODY{body}_{key}": values.copy() for body in (301, 499)
              for key, values in (("POLE_RA", [10.0, 2.0, -1.0]), ("POLE_DEC", [-20.0, -3.0, 2.0]), ("PM", [30.0, 360.0, -1.0]))}
    result.update({f"BODY301_NUT_PREC_{key}": [0.0]*13 for key in ("RA", "DEC", "PM")})
    result["BODY3_NUT_PREC_ANGLES"] = [0.0]*26
    return result


@pytest.mark.parametrize("epoch", [-86400.0, 0.0, 86400.0])
@pytest.mark.parametrize("body", ["Moon", "Mars"])
def test_pck_angle_polynomials_use_centuries_and_days(epoch: float, body: str) -> None:
    intervals = _pck_angle_intervals_deg(trajectory._RefinementBudget("pck-polynomial", 300.0), _inputs(), epoch)[body]
    t, d = Fraction(epoch)/(36525*86400), Fraction(epoch)/86400
    expected = (10+2*t-t*t, -20-3*t+2*t*t, (30+360*d-d*d) % 360)
    assert intervals == tuple((value, value) for value in expected)


@pytest.mark.parametrize("amplitude", [-2.0, 2.0])
@pytest.mark.parametrize("angle,sine,cosine", [(0, 0, 1), (90, 1, 0), (180, 0, -1), (270, -1, 0)])
def test_pck_periodic_phase_and_sine_cosine_selection(amplitude: float, angle: int, sine: int, cosine: int) -> None:
    inputs = _inputs()
    for key in ("POLE_RA", "POLE_DEC", "PM"):
        inputs[f"BODY301_{key}"][1:] = [0.0, 0.0]
    for key in ("RA", "DEC", "PM"):
        inputs[f"BODY301_NUT_PREC_{key}"][0] = amplitude
    inputs["BODY3_NUT_PREC_ANGLES"][:2] = [float(angle-90), 90.0]
    result = _pck_angle_intervals_deg(trajectory._RefinementBudget("pck-periodic", 300.0), inputs, float(36525*86400))["Moon"]
    expected = (10+Fraction(amplitude)*sine, -20+Fraction(amplitude)*cosine, 30+Fraction(amplitude)*sine)
    assert all(lo <= exact <= hi and hi-lo < Fraction(1, 10**25)
               for (lo, hi), exact in zip(result, expected, strict=True))


def test_pck_fresh_epoch_is_not_reused_anchor() -> None:
    inputs = _inputs()
    for body in (301, 499):
        inputs[f"BODY{body}_PM"][2] = 0.0
    budget = trajectory._RefinementBudget("pck-reanchor", 300.0)
    old = _pck_angle_intervals_deg(budget, inputs, 978995455.2304223)
    fresh = _pck_angle_intervals_deg(budget, inputs, 978995455.2929223)
    for body in ("Moon", "Mars"):
        assert fresh[body][2][0]-old[body][2][0] == Fraction(360, 16*86400)


@pytest.mark.parametrize("invalid", ["missing", "extra", "polynomial-size", "phase-size", "nonfinite", "boolean", "epoch"])
def test_pck_angles_reject_invalid_inputs(invalid: str) -> None:
    inputs = _inputs()
    if invalid == "missing":
        del inputs["BODY301_PM"]
    elif invalid == "extra":
        inputs["BODY499_NUT_PREC_PM"] = [0.0]*13
    elif invalid in {"polynomial-size", "phase-size"}:
        inputs["BODY301_PM" if invalid == "polynomial-size" else "BODY3_NUT_PREC_ANGLES"].pop()
    elif invalid in {"nonfinite", "boolean"}:
        inputs["BODY301_PM"][0] = math.nan if invalid == "nonfinite" else True
    with pytest.raises(AssertionError):
        _pck_angle_intervals_deg(trajectory._RefinementBudget("pck-invalid", 300.0), inputs, math.nan if invalid == "epoch" else 0.0)


def test_pck_angles_reject_prime_meridian_wrap_enclosure() -> None:
    inputs = _inputs()
    inputs["BODY301_PM"] = [0.0]*3
    inputs["BODY301_NUT_PREC_PM"][0] = 1.0
    inputs["BODY3_NUT_PREC_ANGLES"][0] = 180.0
    with pytest.raises(AssertionError, match="crosses a wrap"):
        _pck_angle_intervals_deg(trajectory._RefinementBudget("pck-wrap", 300.0), inputs, 0.0)


@pytest.mark.parametrize("expiry_check", [1, 4])
def test_pck_angles_preserve_deadline(expiry_check: int) -> None:
    clock = iter([0.0]*expiry_check+[301.0])
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _pck_angle_intervals_deg(trajectory._RefinementBudget("pck-expired", 300.0, lambda: next(clock)), _inputs(), 0.0)
