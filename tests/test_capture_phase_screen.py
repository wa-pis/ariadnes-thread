"""Exercise the complete R5.59e grid on fabricated, offline archives."""

from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
from runpy import run_path
from shutil import copytree
from time import monotonic_ns
from typing import Any

import pytest

ART = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
INPUT_CAP = 128 * 1024
OUTPUT_CAP = 4 * 1024 * 1024
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
type Row = dict[str, Any]
type Pins = dict[str, str]
type Vector = tuple[float, float, float]


@pytest.fixture(scope="module")
def runner() -> Row:
    return run_path(str(ART / "0213-phase-runner.py"))


@pytest.fixture(scope="module")
def fixtures() -> Row:
    return run_path(str(ART / "0213-phase-fixtures.py"))


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def read(path: Path, name: str) -> Row:
    return json.loads((path / name).read_bytes())


def save(path: Path, name: str, data: Row) -> None:
    (path / name).write_bytes(
        (json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    )


def repin(path: Path) -> Pins:
    return {name: sha(path / name) for name in FILES}


def bind_report(path: Path, report: Row) -> Pins:
    """Rehash the writable chain to test checks beyond byte authentication."""
    save(path, "report.json", report)
    receipt = read(path, "receipt.json")
    receipt["report_sha256"] = sha(path / "report.json")
    save(path, "receipt.json", receipt)
    completion = read(path, "completion.json")
    completion["receipt_sha256"] = sha(path / "receipt.json")
    save(path, "completion.json", completion)
    return repin(path)


def size(path: Path) -> int:
    return sum((path / name).stat().st_size for name in FILES)


@pytest.fixture(scope="module")
def archive(tmp_path_factory: pytest.TempPathFactory, fixtures: Row) -> tuple[Path, Pins]:
    source = tmp_path_factory.mktemp("r559e-archives") / "artificial"
    pins = fixtures["build"](source)
    assert pins == repin(source)
    return source, pins


@pytest.fixture(scope="module")
def result(
    tmp_path_factory: pytest.TempPathFactory, runner: Row, archive: tuple[Path, Pins],
) -> tuple[Path, Pins, Path, Row]:
    source, _ = archive
    base = tmp_path_factory.mktemp("r559e-grid")
    padded = base / "padded-source"
    copytree(source, padded)
    source_report = read(padded, "report.json")
    bind_report(padded, source_report | dict(fixture_padding=""))
    padding = INPUT_CAP - size(padded)
    assert padding > 0
    pins = bind_report(padded, source_report | dict(fixture_padding="x" * padding))
    assert size(padded) == INPUT_CAP

    output = base / "evidence"
    assert runner["launch"](padded, pins, output) == 0
    report = runner["verify_result"](output, pins, expected_completion_sha256=sha(output / "completion.json"))
    assert repin(padded) == pins
    return padded, pins, output, report


def cross(a: Vector, b: Vector) -> Vector:
    return a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]


def invariants(relative: list[float], mu: float) -> tuple[float, Vector, Vector]:
    x, y, z, vx, vy, vz = relative
    r, v = (x, y, z), (vx, vy, vz)
    h = cross(r, v)
    rnorm = math.hypot(*r)
    a, b, c = cross(v, h)
    e = (a/mu-x/rnorm, b/mu-y/rnorm, c/mu-z/rnorm)
    return math.fsum(k*k for k in v)/2 - mu/rnorm, h, e


def test_full_grid_has_all_states_both_roots_and_independent_orbit_invariants(
    result: tuple[Path, Pins, Path, Row],
) -> None:
    source, pins, output, report = result
    assert report["schema"] == "ariadna-r559e-phase-evidence-v1"
    assert report["status"] == "artificial-phase-proposal"
    assert set(p.name for p in output.iterdir()) == set(FILES)
    assert 0 < size(output) <= OUTPUT_CAP
    assert report["source_bytes"] == INPUT_CAP
    assert sorted(report["archive_open_attempts"]) == sorted(pins)
    assert report["work"]["phase_positions"] == 360
    assert report["work"]["mars_roots"] == 720
    assert 0 < report["work"]["pairs"] == sum(len(row["pairs"]) for row in report["rows"]) <= 720
    assert [row["index"] for row in report["rows"]] == list(range(360))
    assert report["live_authorized"] is False
    assert report["physical_launch_authorized"] is False
    for name in ("r559f_attempts", "r560_attempts", "spice_queries", "kernel_accesses", "force_evaluations", "integrations"):
        assert type(report[name]) is int and report[name] == 0

    seed = read(source, "report.json")
    mars = seed["normalized"]["endpoints"][1]
    relative0 = list(map(float, mars["relative_si"]))
    mu = mars["gm_m3_s2"]
    energy0, h0, e0 = invariants(relative0, mu)
    assert math.hypot(*e0) > 0.1 and math.prod(h0) != 0
    radius0, speed0 = math.hypot(*relative0[:3]), math.hypot(*relative0[3:])
    periapsis = [x/radius0 for x in relative0[:3]]
    tangent = [x/speed0 for x in relative0[3:]]
    for k, row in enumerate(report["rows"]):
        assert set(row["branches"]) == {"positive", "negative"}
        angle = float.fromhex(row["angle_word"])
        assert math.isclose(angle, math.tau*k/360, rel_tol=0, abs_tol=1e-15)
        projs = [math.fsum(a*b for a, b in zip(row["relative_si"][:3], axis, strict=True))
                 for axis in (tangent, periapsis)]
        assert abs(math.remainder(math.atan2(*projs) - angle, math.tau)) <= 1e-10
        energy, angular_momentum, eccentricity = invariants(row["relative_si"], mu)
        assert math.dist(angular_momentum, h0) <= 2.0
        assert math.dist(eccentricity, e0) <= 5e-10
        assert math.isclose(energy, energy0, rel_tol=5e-10)
        assert all(v == rel + body for v, rel, body in zip(row["ssb_si"], row["relative_si"],
                                                           mars["body_ssb_si"], strict=True))
        independent = list(map(float, row["independent_relative_si"]))
        assert math.dist(independent[:3], row["relative_si"][:3]) <= 0.001
        assert math.dist(independent[3:], row["relative_si"][3:]) <= 1e-6
        assert all(math.isfinite(value) for value in (row["relative_si"] + row["ssb_si"]))
    zero = report["rows"][0]
    assert math.dist(zero["relative_si"][:3], relative0[:3]) <= 0.001
    assert math.dist(zero["relative_si"][3:], relative0[3:]) <= 1e-6
    assert {sign: row["reason"] for sign, row in zero["branches"].items()} == {
        sign: row["reason"] for sign, row in seed["branch_decisions"]["Mars"].items()
    }
    assert "commanded-dry-floor" in [pair["reason"] for pair in zero["pairs"]]
    assert not any(pair.get("command_words") for pair in zero["pairs"])
    assert any(branch["reason"] == "guard" for row in report["rows"] for branch in row["branches"].values())


def test_known_nonzero_winner_uses_physical_arrival_and_exact_ledgers(
    result: tuple[Path, Pins, Path, Row], fixtures: Row,
) -> None:
    source, _, _, report = result
    selected = report["selected"]
    assert selected["index"] != 0
    index, sign, total, gap, final_kg = fixtures["independent_winner"]()
    assert selected["index"] == index == fixtures["EXPECTED_INDEX"]
    assert selected["roots"] == ["positive", sign]
    assert selected["total_delta_v_m_s"] == pytest.approx(total, rel=0, abs=1e-6)
    eligible = sorted(pair["total_delta_v_m_s"] for row in report["rows"] for pair in row["pairs"]
                      if pair["reason"] is None)
    assert eligible[1] - eligible[0] == pytest.approx(gap, rel=0, abs=1e-6)
    assert selected["ideal_end_masses_kg"][-1] == pytest.approx(final_kg, rel=0, abs=1e-8)
    row = report["rows"][selected["index"]]
    winner, = [pair for pair in row["pairs"] if pair["roots"] == selected["roots"]]
    assert winner["reason"] is None
    assert selected["command_words"] == report["command_words"] == winner["command_words"]
    assert selected["ledgers"] == winner["ledgers"]
    for key in ("angle_word", "relative_si", "ssb_si"):
        assert selected[key] == row[key]
    seed = read(source, "report.json")
    mars = seed["normalized"]["endpoints"][1]
    branch = row["branches"][selected["roots"][1]]
    assert math.dist(branch["reconstructed_excess_m_s"], mars["v_infinity_m_s"]) <= 1e-6
    incoming = branch["hyperbolic_velocity_m_s"]
    assert math.dist(branch["impulse_m_s"],
                     [after - before for after, before in zip(row["relative_si"][3:], incoming, strict=True)]) <= 1e-6
    assert branch["minimum_radius_m"] > mars["guard_m"] + 0.001

    _, _, td, _, _, ta = map(float.fromhex, selected["command_words"])
    t0, t1, checkpoint, t2, tf = map(float.fromhex, selected["ledgers"]["epoch_words"])
    assert t0 < t1 == t0 + td < checkpoint < t2 == tf - ta < tf
    assert [t0.hex(), checkpoint.hex(), tf.hex()] == seed["normalized"]["epoch_words"]
    rate = Fraction(1000 / (9.80665 * 450))
    ledgers = selected["ledgers"]["mass_kg_exact"]
    for kind, elapsed in (("commanded", (Fraction(td), Fraction(ta))),
                          ("effective", (Fraction(t1)-Fraction(t0), Fraction(tf)-Fraction(t2)))):
        m1 = 2000 - rate * elapsed[0]
        m2 = m1 - rate * elapsed[1]
        assert tuple(map(Fraction, ledgers[kind])) == (m1, m1, m2)
        assert m2 >= 500


def test_exclusive_first_output_and_readback_without_source(
    runner: Row, result: tuple[Path, Pins, Path, Row], tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, pins, output, report = result
    hashes = repin(output)
    without_source = tmp_path / "source"
    copytree(source, without_source)

    def no_spawn(*_: Any, **__: Any) -> None:
        pytest.fail("an existing output started another process")

    monkeypatch.setattr(runner["launch"].__globals__["subprocess"], "run", no_spawn)
    assert runner["launch"](without_source, pins, output) == 3
    assert repin(output) == hashes
    disappeared = source.with_name("hidden-during-readback")
    source.rename(disappeared)
    try:
        assert runner["verify_result"](output, pins, expected_completion_sha256=hashes["completion.json"]) == report
    finally:
        disappeared.rename(source)


@pytest.mark.parametrize("fault", ["wrong-pin", "symbolic-link", "one-byte-over", "retained-mode"])
def test_archive_refusals_never_yield_a_proposal(
    runner: Row, result: tuple[Path, Pins, Path, Row], tmp_path: Path, fault: str,
) -> None:
    source = tmp_path / "archives"
    copytree(result[0], source)
    pins = repin(source)
    if fault == "wrong-pin":
        pins["report.json"] = "a" * 64
    elif fault == "symbolic-link":
        moved = (source / "report.json").rename(tmp_path / "otherwise-authentic.json")
        (source / "report.json").symlink_to(moved)
    elif fault == "one-byte-over":
        report = read(source, "report.json")
        report["fixture_padding"] += "x"
        pins = bind_report(source, report)
        assert size(source) == INPUT_CAP + 1
    else:
        report = read(source, "report.json")
        report["mode"] = "retained"
        report["fixture_padding"] = ""
        pins = bind_report(source, report)
    output = tmp_path / "refused"
    assert runner["launch"](source, pins, output) == 3
    if (output / "completion.json").is_file():
        error = runner["verify_result"](output, pins)
        assert error["status"] == "invalid-evidence" and error["command_words"] is None
    else:
        with pytest.raises((OSError, ValueError)):
            runner["verify_result"](output, pins)


@pytest.mark.parametrize(
    "fault", ["missing-phase", "missing-sign", "phase-angle", "state-errors", "selected-ledger", "wrong-rank", "authority", "overcap"],
)
def test_readback_detects_rebound_science_tampering(
    runner: Row, result: tuple[Path, Pins, Path, Row], tmp_path: Path, fault: str,
) -> None:
    _, pins, output, _ = result
    forged = tmp_path / "forged"
    copytree(output, forged)
    report = read(forged, "report.json")
    if fault == "missing-phase":
        report["rows"].pop(171)
    elif fault == "missing-sign":
        del report["rows"][171]["branches"]["negative"]
    elif fault == "phase-angle":
        report["rows"][27]["angle_word"] = report["rows"][26]["angle_word"]
    elif fault == "state-errors":
        report["rows"][27]["discrepancies"]["relative_position_m"] = 0.0001
    elif fault == "selected-ledger":
        report["selected"]["ledgers"]["mass_kg_exact"]["effective"][-1] = "500"
    elif fault == "wrong-rank":
        selected = report["selected"]
        worse = next((row, pair) for row in report["rows"] for pair in row["pairs"]
                     if pair["reason"] is None and (row["index"], pair["roots"]) !=
                     (selected["index"], selected["roots"]))
        row, pair = worse
        for key in ("index", "angle_word", "relative_si", "ssb_si"):
            selected[key] = row[key]
        for key in ("roots", "command_words", "ledgers"):
            selected[key] = pair[key]
        report["command_words"] = pair["command_words"]
    elif fault == "authority":
        report["physical_launch_authorized"] = True
    else:
        report["padding"] = ""
        bind_report(forged, report)
        padding = OUTPUT_CAP + 1 - size(forged)
        assert padding > 0
        report["padding"] = "x"*padding
    expected = bind_report(forged, report)["completion.json"]
    if fault == "overcap":
        assert size(forged) == OUTPUT_CAP + 1
    with pytest.raises(ValueError):
        runner["verify_result"](forged, pins, expected_completion_sha256=expected)


def test_late_parent_invalidates_completion_but_preserves_exclusive_evidence(
    runner: Row, archive: tuple[Path, Pins], tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, pins = archive
    namespace = runner["launch"].__globals__
    run = namespace["subprocess"].run
    late = False

    def finish_late(*args: Any, **kwargs: Any) -> object:
        nonlocal late
        result = run(*args, **kwargs)
        assert result.returncode == 0
        late = True
        return result

    def clock() -> int:
        return monotonic_ns() + (31_000_000_000 if late else 0)

    monkeypatch.setattr(namespace["subprocess"], "run", finish_late)
    monkeypatch.setitem(namespace, "monotonic_ns", clock)
    output = tmp_path / "late"
    assert runner["launch"](source, pins, output) == 3
    first = {path.name: sha(path) for path in output.iterdir()}
    assert set(first) == set(FILES[:3])
    with pytest.raises((OSError, ValueError)):
        runner["verify_result"](output, pins)
    assert runner["launch"](source, pins, output) == 3
    assert {path.name: sha(path) for path in output.iterdir()} == first


def test_verified_empty_grid_reports_bounded_refusal(
    runner: Row, fixtures: Row, tmp_path: Path,
) -> None:
    source = tmp_path / "high-excess"
    pins = fixtures["build"](source, impossible=True)
    output = tmp_path / "empty"
    assert runner["launch"](source, pins, output) == 2
    report = runner["verify_result"](output, pins)
    assert report["status"] == "no-eligible-pair-on-grid"
    assert report["command_words"] is report["selected"] is None
    assert len(report["rows"]) == 360 and report["work"]["mars_roots"] == 720
    assert all(pair["reason"] is not None for row in report["rows"] for pair in row["pairs"])
    assert any(pair["reason"] == "commanded-dry-floor" for row in report["rows"] for pair in row["pairs"])
    assert read(output, "completion.json")["exit_code"] == 2


@pytest.mark.parametrize(("local", "precise"), [
    (1000.0, "1000"),
    (1000.000004, "1000.000004"),
    (1000.001, "999.999"),
])
def test_phase_audit_cannot_choose_between_ties_or_disagreeing_paths(local: float, precise: str) -> None:
    screen = run_path(str(ART / "0213-phase-screen.py"))
    a = dict(index=31, total_delta_v_m_s=1000.0, oracle_total_delta_v_m_s="1000")
    b = dict(index=211, total_delta_v_m_s=local, oracle_total_delta_v_m_s=precise)
    assert screen["_select"]([a, b]) is None
    assert screen["_select"]([a, b | dict(total_delta_v_m_s=1000.001, oracle_total_delta_v_m_s="1000.001")]) == a
