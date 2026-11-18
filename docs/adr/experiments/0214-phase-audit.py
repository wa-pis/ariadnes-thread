"""Audit the saved R5.59f grid without repeating the phase scan or solving a conic."""

from collections.abc import Callable
from decimal import Decimal
from types import ModuleType
from typing import Any

type Row = dict[str, Any]

SIGNS = ("positive", "negative")
CANDIDATES = {"retained": "d0001-t0035", "artificial": "artificial-moon-mars"}
PROPOSALS = {"retained": "analytic-phase-proposal", "artificial": "artificial-phase-proposal"}


def _need(ok: object, reason: str) -> None:
    if not ok:
        raise ValueError(f"R5.59f audit: {reason}")


def _branches(branches: Row, endpoint: Row, reader: ModuleType) -> list[list[str]]:
    """Check the stored signed roots and determine the required pair inventory."""
    _need(set(branches) == set(SIGNS), "both signed roots required")
    accepted = []
    unresolved = False
    for sign in SIGNS:
        branch = branches[sign]
        if branch["reason"] == "unresolved":
            _need(isinstance(branch.get("detail"), str) and branch["detail"], "unresolved root detail")
            unresolved = True
            continue
        reason = reader._root(branch, endpoint)
        if reason is None:
            accepted.append(["positive", sign])
        unresolved |= reason not in (None, "guard", "degenerate")
    return [] if unresolved else accepted


def audit(report: Row, screen: ModuleType, reader: ModuleType, check: Callable[[], None]) -> None:
    """Check bounded evidence, state reconstruction, ledgers and independent ranking."""
    check()
    mode, status = report["mode"], report["status"]
    _need(mode in CANDIDATES and report["synthetic"] is (mode == "artificial")
          and report["live_authorized"] is False and report["physical_launch_authorized"] is False
          and report["physical_status"] == "physical-join-not-established", "scope or physical authority")

    work, rows = report["work"], report["rows"]
    _need(set(work) == {"phase_positions", "mars_roots", "pairs"}
          and all(type(x) is int and x >= 0 for x in work.values()) and isinstance(rows, list)
          and len(rows) <= work["phase_positions"] <= screen.GRID
          and 2*len(rows) <= work["mars_roots"] <= 2*work["phase_positions"]
          and work["pairs"] <= work["mars_roots"], "work caps")
    if status == screen.INVALID:
        error = report.get("error")
        _need(report["command_words"] is None and report["selected"] is None
              and isinstance(error, str) and 0 < len(error) <= 512, "invalid output")
        return

    _need(work["phase_positions"] == len(rows) == screen.GRID
          and work["mars_roots"] == 2*screen.GRID, "incomplete grid")
    ref = report["reference"]
    source = ref["normalized"]
    moon, mars = source["endpoints"]
    _need(source["scope"] == mode and source["candidate_id"] == CANDIDATES[mode]
          and source["command_words"] is None and source["live_authorized"] is False
          and (source["origin"], source["orientation"], source["units"], source["time_scale"])
          == ("SSB", "J2000", "SI", "TDB seconds since J2000"), "fixed candidate or reference frame")
    epochs = reader._vector(source["epochs_tdb_s"], 3)
    _need(epochs[0] < epochs[1] < epochs[2] and source["epoch_words"] == [t.hex() for t in epochs],
          "exact epoch order")
    for endpoint, body, label, epoch in ((moon, "Moon", "departure-ignition", epochs[0]),
                                         (mars, "Mars", "arrival-cutoff", epochs[2])):
        _need(endpoint["body"] == body and endpoint["label"] == label
              and endpoint["epoch_word"] == epoch.hex() and reader._number(endpoint["epoch_tdb_s"]) == epoch,
              "endpoint direction or epoch")
    lunar = ref["lunar"]
    _need(reader._root(lunar, moon) is None, "fixed lunar root")
    excluded = set()
    for command in source["rejected_command_words"]:
        _need(isinstance(command, list) and len(command) == 6, "historical exclusions")
        excluded.add(tuple(map(reader._word, command)))
    craft = source["spacecraft"]

    zero_branches, zero_pairs = ref["zero_branches"], ref["zero_pairs"]
    _need(isinstance(zero_pairs, list) and zero_pairs
          and [pair["roots"] for pair in zero_pairs] == _branches(zero_branches, mars, reader),
          "zero phase pair inventory")
    for pair in zero_pairs:
        _need(pair["reason"] == "commanded-dry-floor"
              and not reader._pair(pair, lunar, zero_branches[pair["roots"][1]], epochs, craft, excluded),
              "zero phase fuel refusal")

    good = []
    count = 0
    inconclusive = False
    for index, row in enumerate(rows):
        check()
        screen._read_state(row, mars, index, reader)
        branches, pairs = row["branches"], row["pairs"]
        state = mars | {"relative_si": [str(Decimal(x)) for x in row["relative_si"]]}
        _need(isinstance(pairs, list) and [p["roots"] for p in pairs] == _branches(branches, state, reader),
              "phase pair inventory")
        inconclusive |= screen._unresolved(branches)
        for pair in pairs:
            _need(type(pair["index"]) is int and pair["index"] == index, "pair phase")
            count += 1
            if reader._pair(pair, lunar, branches[pair["roots"][1]], epochs, craft, excluded):
                good.append(pair)
            inconclusive |= pair["reason"] == "independent-mass"
    screen._verify_zero(rows[0], ref)
    _need(count == work["pairs"], "pair count")

    winner = None if inconclusive else screen._select(good)
    if winner is None:
        expected = screen.INCONCLUSIVE if inconclusive or good else screen.REFUSAL
        reason = "independent-disagreement" if inconclusive else "ambiguous-rank" if good else "no-eligible-pair"
        _need(status == expected and report["reason"] == reason and report["command_words"] is None
              and report["selected"] is None, "refusal or ambiguity binding")
    else:
        _need(status == PROPOSALS[mode] and report["reason"] is None
              and report["command_words"] == winner["command_words"]
              and report["selected"] == screen._proposal(rows[winner["index"]], winner), "winning phase binding")
    check()
