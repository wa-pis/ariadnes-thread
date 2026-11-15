"""Manufactured conic states and resource/refusal checks for R5.59b."""

from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
from runpy import run_path
import shutil
from time import monotonic
from types import ModuleType
from typing import Any

import pytest


ART = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
CODE = ART / "0208-seed-worksheet.py"
ORACLE = ART / "0208-seed-oracle.py"
RUNNER = ART / "0208-seed-runner.py"
IO = ART / "0206-readiness-runner.py"
CAP = 512*1024
type Row = dict[str, Any]


def sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


@pytest.fixture(scope="module")
def work() -> Row:
    return run_path(str(CODE))


@pytest.fixture(scope="module")
def oracle() -> ModuleType:
    module = ModuleType("seed_test_oracle")
    module.__dict__.update(run_path(str(ORACLE)))
    return module


@pytest.fixture(scope="module")
def fixture() -> Row:
    return run_path(str(ART / "0208-seed-fixtures.py"))


@pytest.fixture(scope="module")
def runner() -> Row:
    return run_path(str(RUNNER))


def evaluate(work: Row, oracle: ModuleType, fixture: Row, bundle: Row | None = None) -> Row:
    raw = fixture["wire"](fixture["build"]() if bundle is None else fixture["rebind"](bundle))
    return work["evaluate"](raw, sha(raw), oracle)


def no_live(report: Row) -> None:
    assert report["synthetic"] is True and report["live_authorized"] is False
    assert report["physical_status"] == "physical-join-not-established"
    assert report.get("physical_residuals", {}) == dict.fromkeys(report.get("physical_residuals", {}))


def test_known_tilted_conics_and_full_sequential_burns(work: Row, oracle: ModuleType, fixture: Row) -> None:
    report = evaluate(work, oracle, fixture)
    no_live(report)
    geometry = fixture["known_geometry"]()
    assert report["status"] == "synthetic-command-proposal"
    assert report["selected_roots"] == ["negative", "positive"]
    assert report["branch_decisions"]["Mars"]["negative"]["reason"] == "guard"
    selected, = [pair for pair in report["pairs"] if pair["roots"] == report["selected_roots"]]
    for j, state in enumerate(geometry):
        leg = report["branch_decisions"][state.body][state.root]
        assert math.dist(leg["hyperbolic_velocity_m_s"], state.hyperbolic_m_s) < 1e-6
        assert math.dist(leg["reconstructed_excess_m_s"], state.excess_m_s) < 1e-6
        assert abs(leg["minimum_radius_m"]-state.future_minimum_radius_m) < .001
        expected = tuple((a-b)*(-1 if j else 1) for a, b in
                         zip(state.hyperbolic_m_s, state.orbital_m_s, strict=True))
        assert math.dist(expected, leg["impulse_m_s"]) < 1e-6
        # Verify the physical inbound sign at Mars, not just a speed norm.
        assert math.fsum(r*v for r, v in zip(state.r_m, leg["hyperbolic_velocity_m_s"], strict=True)) < 0
    a, e, td, b, f, ta = map(float.fromhex, report["command_words"])
    assert all(-math.pi <= angle < math.pi for angle in (a, b))
    assert all(abs(angle) <= math.pi/2 for angle in (e, f))
    assert td > 0 and ta > 0
    rate = Fraction(1000 / (9.80665*450))
    assert Fraction(selected["ledgers"]["mass_kg_exact"]["commanded"][-1]) == 2000-rate*(Fraction(td)+Fraction(ta))
    expected_ideal_kg = 2000*math.exp(-selected["total_delta_v_m_s"]/(9.80665*450))
    assert math.isclose(selected["ideal_end_masses_kg"][-1], expected_ideal_kg, abs_tol=1e-8, rel_tol=0)


@pytest.mark.parametrize("arrival", [False, True])
def test_exact_angular_momentum_roots_and_reversal(work: Row, oracle: ModuleType, arrival: bool) -> None:
    sign = -1 if arrival else 1
    oracle_result = oracle.branches(("2","0","0"), ("0","2","0"), ("0",str(sign),"0"),
                                   "4", "0.1", arrival=arrival)
    actual = work["float_branches"]((2.,0.,0.), (0.,2.,0.), (0.,float(sign),0.), 4., .1, arrival=arrival)
    for label, velocity in (("positive", (1.,2.,0.)), ("negative", (-2.,-1.,0.))):
        expected = tuple(sign*v for v in velocity)
        assert math.dist(actual[label].velocity, expected) < 1e-12
        assert math.dist(oracle_result[label]["velocity"], expected) < 1e-12
        assert math.dist(actual[label].reconstructed_excess, (0.,sign,0.)) < 1e-12


def test_at_most_four_pairs_with_both_legs_outside(work: Row, oracle: ModuleType, fixture: Row) -> None:
    bundle = fixture["build"]()
    bundle["sections"]["audit"]["endpoints"][1]["guard_m"] = 1.
    report = evaluate(work, oracle, fixture, bundle)
    assert report["status"] == "synthetic-command-proposal"
    assert len(report["pairs"]) == 4
    assert len({tuple(row["roots"]) for row in report["pairs"]}) == 4


def test_submitted_rejected_seed_excluded_and_no_fallback(work: Row, oracle: ModuleType, fixture: Row) -> None:
    first = evaluate(work, oracle, fixture)
    bundle = fixture["build"]()
    bundle["sections"]["baseline"]["failures"] = [
        list(map(float.fromhex, row["command_words"])) for row in first["pairs"] if row["reason"] is None
    ]
    report = evaluate(work, oracle, fixture, bundle)
    no_live(report)
    assert report["reason"] == "no-eligible-pair" and report["command_words"] is None
    assert {pair["reason"] for pair in report["pairs"]} == {"historically-rejected"}


def test_equal_speed_with_both_transverse_roots_refuses(work: Row, oracle: ModuleType, fixture: Row) -> None:
    packet = fixture["build"]()
    r4 = packet["sections"]["r4"]["endpoints"][0]
    audit = packet["sections"]["audit"]["endpoints"][0]
    # A normal-to-plane parking velocity makes both same-energy solutions equidistant.
    scalar = math.sqrt(audit["gm_m3_s2"]/math.hypot(*map(float, audit["relative_si"][:3])))
    orbital = (0., -.8*scalar, .6*scalar)
    values = [v+b for v, b in zip(orbital, audit["body_ssb_si"][3:], strict=True)]
    for row in (r4, audit):
        row["endpoint_ssb_si"][3:] = values
    with localcontext(prec=96):
        audit["relative_si"][3:] = [str(Decimal(v)-Decimal(b))
                                    for v, b in zip(values, audit["body_ssb_si"][3:], strict=True)]
    audit["orbit_relative_si"][3:] = list(map(str, map(Decimal, orbital)))
    report = evaluate(work, oracle, fixture, packet)
    assert report["reason"] == "ambiguous-rank" and report["command_words"] is None
    assert len(report["pairs"]) == 2


@pytest.mark.parametrize(("d", "a", "reason"), [
    (6000., float.fromhex("0x1.35be8f5c28f52p+9"), "commanded-dry-floor"),
    (float.fromhex("0x1.77000000101b3p+12"), float.fromhex("0x1.35be8f5ba81b8p+9"), "effective-dry-floor"),
    (1e-11, 500., "exact-event-order"),
])
def test_mass_before_rounding_and_native_epoch_collapse(work: Row, d: float, a: float, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        work["ledgers"]((978995455.2304223, 979014965.9635216, 1004169273.4122404), (d,a))


@pytest.mark.parametrize("case", ["zero", "parallel", "anti-parallel", "below-collinearity-limit"])
def test_degenerate_asymptote_returns_no_commands(work: Row, oracle: ModuleType, fixture: Row, case: str) -> None:
    bundle = fixture["build"]()
    local = bundle["sections"]["audit"]["endpoints"][0]
    r = [float(x) for x in local["relative_si"][:3]]
    v = dict(zero=[0.,0.,0.], parallel=r, **{"anti-parallel":[-x for x in r],
             "below-collinearity-limit": [r[0],r[1],r[2]+1e-3]})[case]
    bundle["sections"]["r1"]["excess_m_s"][0] = v
    report = evaluate(work, oracle, fixture, bundle)
    assert report["command_words"] is None and report["reason"] == "no-eligible-pair"
    assert all(row["reason"] == "degenerate" for row in report["branch_decisions"]["Moon"].values())


@pytest.mark.parametrize("case", ["rehashed-input", "section-pin", "epoch", "scenario", "model",
                                  "relative", "independent-orbit", "native-schema", "bool-excess"])
def test_malformed_or_substituted_synthetic_inputs(work: Row, oracle: ModuleType, fixture: Row, case: str) -> None:
    bundle = fixture["build"]()
    pin = sha(fixture["wire"](bundle))
    sections = bundle["sections"]
    if case in ("rehashed-input", "section-pin"):
        sections["baseline"]["failures"] = [[0.,0.,1.,0.,0.,1.]]
    elif case == "epoch":
        sections["contract"]["epochs_tdb_s"][0] += .002
    elif case == "scenario":
        sections["r1"]["scenario"]["units"] = "km"
    elif case == "model":
        sections["contract"]["model"] = "live"
    elif case == "relative":
        sections["audit"]["endpoints"][0]["relative_si"][0] = "0.1"
    elif case == "independent-orbit":
        sections["audit"]["endpoints"][0]["orbit_relative_si"][0] = "0.1"
    elif case == "native-schema":
        bundle["schema"] = "ariadna-retained-command-v1"
    elif case == "bool-excess":
        sections["r1"]["excess_m_s"][0][0] = True
    raw = fixture["wire"](bundle if case == "section-pin" else fixture["rebind"](bundle))
    with pytest.raises(ValueError, match="invalid synthetic seed evidence"):
        work["evaluate"](raw, pin if case == "rehashed-input" else sha(raw), oracle)


def artifact(root: Path, fixture: Row, *, extra: int = 0) -> tuple[Path, str]:
    raw = fixture["wire"](fixture["build"]()).ljust(CAP+extra, b" ")
    source = root / "fixture.json"
    source.write_bytes(raw)
    return source, sha(raw)


def test_full_size_runner_and_independent_pinned_readback(runner: Row, fixture: Row, tmp_path: Path) -> None:
    path, pin = artifact(tmp_path, fixture)
    out = tmp_path / "result"
    assert runner["launch"](path, pin, out)
    contents = {p.name: p.read_bytes() for p in out.iterdir()}
    assert sum(map(len, contents.values())) <= 128*1024
    completion = sha(contents["completion.json"])
    report = runner["verify_result"](out, pin, expected_completion_sha256=completion)
    no_live(report)
    assert report["status"] == "synthetic-command-proposal" and report["fixture_bytes"] == CAP
    assert not runner["launch"](path, pin, out)
    assert contents == {p.name: p.read_bytes() for p in out.iterdir()}
    with pytest.raises(ValueError):
        runner["verify_result"](out, pin, expected_completion_sha256="a"*64)
    (out/"report.json").write_bytes(contents["report.json"]+b" ")
    with pytest.raises(ValueError):
        runner["verify_result"](out, pin)


@pytest.mark.parametrize("case", ["oversize", "link", "wrong-pin"])
def test_runner_rejects_input_cap_link_and_pin(runner: Row, fixture: Row, tmp_path: Path, case: str) -> None:
    path, pin = artifact(tmp_path, fixture, extra=(case == "oversize"))
    if case == "link":
        alias = tmp_path/"alias.json"
        alias.symlink_to(path)
        path = alias
    out = tmp_path/"invalid"
    pin = "0"*64 if case == "wrong-pin" else pin
    assert not runner["launch"](path, pin, out)
    result = runner["verify_result"](out, pin)
    assert result["status"] == "invalid-evidence" and result["command_words"] is None
    no_live(result)


def copy_runner(root: Path) -> Row:
    for source in (CODE, ORACLE, RUNNER, IO):
        shutil.copyfile(source, root/source.name)
    return run_path(str(root/RUNNER.name))


def test_oversize_generated_report_is_rejected(fixture: Row, tmp_path: Path) -> None:
    path, pin = artifact(tmp_path, fixture)
    runner = copy_runner(tmp_path)
    with (tmp_path/CODE.name).open("a") as stream:
        stream.write("\noriginal = evaluate\ndef evaluate(raw, pin, oracle):\n"
                     "    return original(raw,pin,oracle) | {'large': 'x' * (128*1024)}\n")
    out = tmp_path/"large"
    assert not runner["launch"](path, pin, out)
    assert runner["verify_result"](out, pin)["status"] == "invalid-evidence"
    assert sum(p.stat().st_size for p in out.iterdir()) <= 128*1024


def test_watchdog_leaves_first_evidence_if_readback_stalls(fixture: Row, tmp_path: Path) -> None:
    path, pin = artifact(tmp_path, fixture)
    runner = copy_runner(tmp_path)
    path_copy = tmp_path/RUNNER.name
    original = path_copy.read_text()
    needle = "    audited, checked_sha, checked_id, checked_wall, _ = _audit"
    assert original.count(needle) == 1
    path_copy.write_text(original.replace(needle, "    import time\n    time.sleep(4)\n"+needle))
    launch = runner["launch"]
    launch.__globals__["WALL_S"] = 0.8
    started = monotonic()
    out = tmp_path/"late"
    assert not launch(path, pin, out)
    assert monotonic()-started < 4
    assert (out/"report.json").is_file() and (out/"receipt.json").is_file()
    assert not (out/"completion.json").exists()
    with pytest.raises((ValueError,OSError)):
        runner["verify_result"](out, pin)


def test_full_negative_evidence_preserves_physical_refusal(runner: Row, fixture: Row, tmp_path: Path) -> None:
    data = fixture["build"]()
    data["sections"]["r1"]["excess_m_s"][0] = [0.,0.,0.]
    raw = fixture["wire"](fixture["rebind"](data))
    source = tmp_path/"refusal.json"
    source.write_bytes(raw)
    out = tmp_path/"negative"
    assert not runner["launch"](source, sha(raw), out)
    report = runner["verify_result"](out,sha(raw))
    assert report["status"] == "command-seed-unavailable" and report["reason"] == "no-eligible-pair"
    assert report["command_words"] is None
    assert json.loads((out/"receipt.json").read_bytes())["status"] == "command-seed-unavailable"
    no_live(report)
