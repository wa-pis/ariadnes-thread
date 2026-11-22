"""Exercise test selection and fail-closed offline access without real native work."""
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]
POLICY = Path(__file__).with_name("conftest.py")


def policy(pytester: pytest.Pytester, overrides: str = "") -> None:
    pytester.makeconftest(POLICY.read_text() + "\nLIVE_TESTS = set()\nARCHIVE_TESTS = set()\n" + overrides)
    pytester.makeini("[pytest]\nmarkers =\n live: native regression\n archive: exact historical check\n")


@pytest.mark.parametrize("options,passed,skipped,deselected", [
    ([], 2, 1, 0), (["--offline"], 1, 1, 1),
    (["--run-archive"], 3, 0, 0), (["--offline", "--run-archive"], 2, 0, 1),
    (["-m", "live"], 1, 0, 2),
])
def test_lane_selection(pytester: pytest.Pytester, options: list[str], passed: int,
                        skipped: int, deselected: int) -> None:
    policy(pytester, "LIVE_TESTS = {'test_lanes.py::test_live'}\n")
    pytester.makepyfile(test_lanes="""
import pytest

def test_unit(): pass

def test_live(): pass

@pytest.mark.archive
def test_archive(): pass
""")
    result = pytester.runpytest_subprocess("-q", *options)
    result.assert_outcomes(passed=passed, skipped=skipped, deselected=deselected)


@pytest.mark.parametrize("source,expected", [
    ("import tudatpy", "*offline test attempted native import: tudatpy*"),
    ('import ctypes; ctypes.CDLL("libcspice-policy-test.so")', "*offline test attempted native load:*"),
])
def test_unmarked_native_access_fails(pytester: pytest.Pytester, source: str, expected: str) -> None:
    policy(pytester)
    pytester.makepyfile("def test_unknown_native():\n    " + source)
    result = pytester.runpytest_subprocess("--offline", "-q")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines([expected])


def test_stale_classification_is_an_error(pytester: pytest.Pytester) -> None:
    policy(pytester, "LIVE_TESTS = {'test_example.py::test_missing'}\n")
    pytester.makepyfile(test_example="def test_present(): pass")
    result = pytester.runpytest_subprocess("--collect-only", "-q")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(["*stale live/archive classification: test_example.py::test_missing*"])
