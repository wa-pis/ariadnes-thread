"""Check the narrowly scoped phase-zero adapter and saved readback on artificial evidence."""

from copy import deepcopy
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

ARTIFACTS = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
type Row = dict[str, Any]
type Evidence = list[tuple[Row, str]]


@pytest.fixture(scope="module")
def readback() -> Row:
    return run_path(str(ARTIFACTS / "0216-saved-phase-readback.py"))


@pytest.mark.parametrize(
    ("index", "row_index", "component", "word", "changes"),
    [
        (0, 0, 3, "0E-569", True),
        (1, 0, 3, "0E-569", False),
        (0, 1, 3, "0E-569", False),
        (0, 0, 2, "0E-569", False),
        (0, 0, 4, "0E-569", False),
        (0, 0, 3, "1E-569", False),
        (0, 0, 3, "-0E-569", False),
        (0, 0, 3, "0E-568", False),
        (0, 0, 3, "0", False),
    ],
)
def test_zero_adapter_is_exact_and_does_not_mutate_evidence(
    readback: Row, index: int, row_index: int, component: int, word: str, changes: bool,
) -> None:
    row = {
        "index": row_index,
        "angle_word": (0.).hex(),
        "independent_relative_si": ["10", "20", "30", "40", "50", "60"],
        "relative_si": [1., 2., 3., 4., 5., 6.],
        "ssb_si": [7., 8., 9., 10., 11., 12.],
        "discrepancies": {"saved": 0.},
    }
    row["independent_relative_si"][component] = word
    original = deepcopy(row)
    expected = deepcopy(row)
    if changes:
        expected["independent_relative_si"][component] = "0"

    assert readback["_zero_state"](index, row) == expected
    assert row == original


@pytest.fixture(scope="module")
def saved_grid(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Evidence, Row, Row, dict[str, bytes]]:
    root = tmp_path_factory.mktemp("r559f-saved-artificial")
    source, output = root / "source", root / "output"
    binding = run_path(str(ARTIFACTS / "0214-phase-binding.py"))
    fixtures = run_path(str(ARTIFACTS / "0213-phase-fixtures.py"))
    pins = fixtures["build"](source, impossible=True)
    assert binding["launch"](output, artificial=(source, pins)) == 2

    io = binding["_io"]()
    identity, methods = binding["_methods"](io, pins, "artificial")
    # Read only the three records present in the original retained invocation.
    evidence = []
    for name in binding["FILES"][:3]:
        raw = (output / name).read_bytes()
        evidence.append((io._row(raw), io._sha(raw)))
    return evidence, binding, identity, methods


def test_saved_grid_checks_every_row_without_a_completion(
    readback: Row, saved_grid: tuple[Evidence, Row, Row, dict[str, bytes]],
) -> None:
    evidence, binding, identity, methods = saved_grid
    result = readback["_audit_saved"](evidence, binding, identity, methods, check=lambda: None)
    report = evidence[1][0]
    assert result["status"] == report["status"] == "no-eligible-pair-on-grid"
    assert result["work"] == report["work"]
    assert result["state_checks"] == report["work"]["phase_positions"] == 360
    assert result["work"]["mars_roots"] == 720
    assert result["adapter_uses"] == 0


def test_saved_grid_rejects_the_same_zero_literal_on_the_last_row(
    readback: Row, saved_grid: tuple[Evidence, Row, Row, dict[str, bytes]],
) -> None:
    original, binding, identity, methods = saved_grid
    evidence = deepcopy(original)
    report = evidence[1][0]
    report["rows"][359]["independent_relative_si"][3] = "0E-569"
    io = binding["_io"]()
    evidence[1] = report, io._sha(io._wire(report))
    # Rebind the artificial receipt so the failure comes from the row, not its digest.
    receipt = evidence[2][0]
    receipt["report_sha256"] = evidence[1][1]
    evidence[2] = receipt, io._sha(io._wire(receipt))

    with pytest.raises(ValueError, match="unbounded decimal field"):
        readback["_audit_saved"](evidence, binding, identity, methods, check=lambda: None)
