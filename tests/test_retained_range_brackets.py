"""Artificial checks for retrospective lunar range evidence."""

import math
from pathlib import Path
import runpy
from typing import Any

import pytest

source = Path(__file__).with_name("0192-range-brackets.py")
if not source.exists():
    source = Path(__file__).parents[1] / "docs/adr/experiments/0192-range-brackets.py"
mod = runpy.run_path(str(source))
MARKER = 3_000_000
EPOCH = 978_998_000.0
type Sample = tuple[float, list[float], list[float]]


def _sample(elapsed_s: float, range_m: float, speed_m_s: float = 1000.0) -> Sample:
    moon = [math.ldexp(1.0, 37), 5.0, 0.0, 300.0, 0.0, 0.0]
    spacecraft = [moon[0] + range_m, 5.0, 0.0, 300.0 + speed_m_s, 0.0, 0.0]
    return EPOCH + elapsed_s, spacecraft, moon


def _grids() -> dict[str, list[Sample]]:
    steps = (50.0, 50.0, 50.0, 50.0, 1.0, 0.5)
    names = (*mod["COEPOCHS"], *mod["MESHES"])
    return {
        name: [_sample(i * step, MARKER + (i * step - 107.125) * 1000) for i in range(int(600 / step) + 1)]
        for name, step in zip(names, steps, strict=True)
    }


def _noop() -> None:
    pass


def test_all_grids_bracket_the_known_linear_crossing() -> None:
    report: dict[str, Any] = {}
    mod["analyze"](_grids(), report, _noop)
    assert (report["coepoch_rows"], report["native_rows"]) == (52, 1802)
    assert report["common_bracket_tdb_s"] == [EPOCH + 100, EPOCH + 150]
    assert report["native_overlap_tdb_s"] == [EPOCH + 107, EPOCH + 107.5]
    left, right = report["grids"]["mesh_native_tighter"]["endpoints"]
    assert (left["radius_m"], right["radius_m"]) == (MARKER - 125, MARKER + 375)
    assert left["decimal80"]["radial_sign"] == right["decimal80"]["radial_sign"] == 1


def test_range_sign_is_not_taken_from_rounded_radius() -> None:
    spacecraft = [float(MARKER), 0.01, 0.0, 1.0, 0.0, 0.0]
    report = mod["measure"]((EPOCH, spacecraft, [0.0] * 6))
    assert report["radius_m"] == MARKER
    assert report["range_sign"] == report["decimal80"]["range_sign"] == 1


@pytest.mark.parametrize(
    ("symbols", "problem"),
    [
        ("-0+", "exact-equality"), ("+-", "inward-pair"),
        ("-+-+", "multiple-outward-pairs"), ("-+v", "nonpositive-outward-endpoint"),
    ],
)
def test_unresolved_crossings_preserve_distinct_reasons(symbols: str, problem: str) -> None:
    distances = {"-": MARKER - 100.0, "0": MARKER, "+": MARKER + 100.0}
    if symbols.endswith("v"):
        samples = [_sample(0, distances["-"]), _sample(1, distances["+"], speed_m_s=0)]
    else:
        samples = [_sample(i, distances[s]) for i, s in enumerate(symbols)]
    result = mod["_summarize"]([mod["measure"](sample) for sample in samples])
    assert result["status"] == "unresolved"
    assert problem in result["problems"]
    assert "epochs_tdb_s" not in result


@pytest.mark.parametrize(
    ("mesh_intervals", "error"),
    [(([105, 107], [107, 110]), "overlap"), (([98, 107], [105, 110]), "outside")],
)
def test_meshes_must_overlap_inside_common_bracket(mesh_intervals: tuple[list[int], ...], error: str) -> None:
    grids = {name: {"epochs_tdb_s": [100, 150]} for name in mod["COEPOCHS"]}
    grids.update({
        name: {"epochs_tdb_s": interval} for name, interval in zip(mod["MESHES"], mesh_intervals, strict=True)
    })
    with pytest.raises(ValueError, match=error):
        mod["_intervals"](grids)


def test_invalid_epoch_keeps_count_and_profile_evidence() -> None:
    grids = _grids()
    t, sc, moon = grids["native_tighter"][4]
    grids["native_tighter"][4] = (t + 1, sc, moon)
    report: dict[str, Any] = {}
    with pytest.raises(ValueError, match="native_tighter row 4: unexpected or duplicate grid epoch"):
        mod["analyze"](grids, report, _noop)
    assert report["coepoch_rows"] == 17
    assert report["grids"]["native_normal"]["status"] == "bracketed"
    assert report["grids"]["native_tighter"]["rows_checked"] == 4


def test_overlapping_epochs_require_same_spacecraft_state_words() -> None:
    grids = _grids()
    _, sc, _ = grids["mesh_native_tighter"][100]
    sc[1] = math.nextafter(sc[1], math.inf)
    with pytest.raises(ValueError, match="overlapping spacecraft words disagree"):
        mod["analyze"](grids, {}, _noop)


def test_expired_budget_is_not_a_completed_report() -> None:
    def check() -> None:
        raise TimeoutError("synthetic deadline")

    report: dict[str, Any] = {}
    with pytest.raises(TimeoutError, match="deadline"):
        mod["analyze"](_grids(), report, check)
    assert report["coepoch_rows"] == report["native_rows"] == 0
    assert "native_overlap_tdb_s" not in report
