"""Verify the three original R5.59f records without completing or replaying the run."""

from collections import Counter
from collections.abc import Callable
from decimal import Decimal
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
from time import monotonic_ns
from types import ModuleType
from typing import Any

type Row = dict[str, Any]
type Entries = list[tuple[Row, str]]

HERE = Path(__file__).resolve()
EVIDENCE = HERE.with_name("0215-r559f")
PINS = {
    "attempt.json": "ac1d02f445ebed82ac5b4f728193ea8533890188ed2422117523db50d087bf0a",
    "report.json": "323c2c71e17168a46e9dd5280015a3fecb0865016b9b6954dcb051de4def1800",
    "receipt.json": "395d20ab4771b9a9e4743e038e5c50338d12b8d890018befc3879bf3de21a18b",
}
BINDING = HERE.with_name("0214-phase-binding.py")
BINDING_SHA256 = "e5f9e671aa4716e1a6b953569cfa86e5b06b90322b8faec480ec032b5bc1c9ab"
WALL_NS = 30_000_000_000


def _zero_state(index: int, row: Row) -> Row:
    """Canonicalize only the recorded exact zero, in a local state view."""
    words = row["independent_relative_si"]
    if index == 0 and type(row["index"]) is int and row["index"] == 0 and words[3] == "0E-569":
        return row | {"independent_relative_si": [*words[:3], "0", *words[4:]]}
    return row


def _audit_saved(entries: Entries, binding: Row, identity: Row, raw: dict[str, bytes], *,
                 check: Callable[[], None]) -> Row:
    io, screen, reader, auditor = (binding["_load"](name, raw[name])
                                   for name in ("io", "screen", "reader", "audit"))
    state_check = screen._read_state
    uses = states = 0

    def check_state(row: Row, endpoint: Row, index: int, parser: ModuleType) -> None:
        nonlocal uses, states
        view = _zero_state(index, row)
        state_check(view, endpoint, index, parser)
        uses += view is not row
        states += 1

    screen._read_state = check_state
    report, _, _, _, _ = binding["_audit"](entries, identity, io, auditor, screen, reader, check)
    binding["need"](states == 360 and (identity["mode"] != "retained" or uses == 1), "saved state audit inventory")
    binding["need"](report["status"] == screen.REFUSAL and report["command_words"] is None
                    and report["selected"] is None, "saved no-command refusal")
    rows = report["rows"]
    pairs = [pair for row in rows for pair in row["pairs"]]
    least = min(pairs, key=lambda p: p["total_delta_v_m_s"])
    independent_least = min(pairs, key=lambda p: Decimal(p["oracle_total_delta_v_m_s"]))
    craft = report["reference"]["normalized"]["spacecraft"]
    budget = 9.80665 * craft["isp_s"] * math.log(craft["initial_mass_kg"] / craft["dry_mass_kg"])
    pair_fields = ("index", "roots", "reason", "total_delta_v_m_s", "oracle_total_delta_v_m_s")
    check()
    return {
        "status": report["status"], "reason": report["reason"], "commands": None,
        "work": report["work"], "state_checks": states, "adapter_uses": uses,
        "candidate_id": report["reference"]["normalized"]["candidate_id"],
        "source_bytes": report["source_bytes"], "source_sha256": report["source_sha256"],
        "branch_decisions": {s: Counter(row["branches"][s]["reason"] or "passes" for row in rows)
                             for s in ("positive", "negative")},
        "pair_decisions": Counter(p["reason"] or "eligible" for p in pairs),
        "zero_phase_delta_v_m_s": rows[0]["pairs"][0]["total_delta_v_m_s"],
        "least_recorded_pair": {k: least[k] for k in pair_fields},
        "least_independent_pair": {k: independent_least[k] for k in pair_fields},
        "ideal_dry_mass_budget_m_s": budget,
        "least_pair_over_ideal_budget_m_s": least["total_delta_v_m_s"] - budget,
        "max_state_discrepancies": {k: max(row["discrepancies"][k] for row in rows)
                                    for k in rows[0]["discrepancies"]},
    }


def _guard(methods: set[Path]) -> None:
    allowed = methods | {EVIDENCE / name for name in PINS}
    stdlib = Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}"

    def guard(event: str, args: tuple[Any, ...]) -> None:
        if event in {"subprocess.Popen", "os.system", "os.fork", "os.exec", "os.posix_spawn",
                     "socket.__new__", "ctypes.dlopen"}:
            raise PermissionError(f"audit blocked {event}")
        if event == "import":
            root = str(args[0]).split(".", 1)[0]
            if root not in sys.stdlib_module_names or root in {"ctypes", "_ctypes"}:
                raise PermissionError(f"audit blocked import {root}")
        if event in {"os.scandir", "os.listdir"}:
            directory = Path(os.fsdecode(args[0]))
            if directory != EVIDENCE and not directory.is_relative_to(stdlib):
                raise PermissionError(f"audit blocked inventory of {directory.name}")
        if event == "open" and not isinstance(args[0], int):
            pathname = Path(os.path.abspath(os.fsdecode(args[0])))
            if (int(args[2]) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
                or (pathname not in allowed and not (pathname.is_relative_to(stdlib)
                    and pathname.suffix in {".py", ".pyc", ".so", ".dylib"}))):
                raise PermissionError(f"audit blocked open of {pathname.name}")

    sys.addaudithook(guard)


def main() -> None:
    """Read only the pinned failed invocation and its pinned audit methods."""
    started = monotonic_ns()
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise ValueError("use Python -I -S -B")
    # The binding is authenticated before loading it to obtain the exact method allowlist.
    fd = os.open(BINDING, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        source = stream.read(64 * 1024 + 1)
    if sha256(source).hexdigest() != BINDING_SHA256:
        raise ValueError("changed R5.59f binding")
    binding = {"__name__": "_r559f_original_binding", "__file__": str(BINDING)}
    exec(compile(source, str(BINDING), "exec"), binding)
    io = binding["_io"]()
    _guard({HERE.with_name(name) for name, _ in binding["METHODS"].values()})
    binding["need"](not EVIDENCE.is_symlink(), "saved evidence directory is a symlink")

    def check() -> None:
        binding["_elapsed"](started, WALL_NS)

    identity, raw = binding["_methods"](io, dict(binding["RETAINED_PINS"]), "retained")
    envelope = binding["_load"]("envelope", raw["envelope"])
    entries = envelope._files(EVIDENCE, tuple(PINS), io)
    binding["need"](dict(zip(PINS, (digest for _, digest in entries), strict=True)) == PINS,
                    "changed R5.59f evidence")
    report = entries[1][0]
    binding["need"](identity["source_sha256"]["audit"] == report["source_sha256"]["audit"], "changed auditor")
    result = _audit_saved(entries, binding, identity, raw, check=check)
    binding["need"](report["source_bytes"] == 13_363, "saved source bytes")
    result.update(
        schema="ariadna-r559f-saved-grid-audit-v1", saved_grid_verified=True,
        original_invocation_completed=False, original_new_completion_witness=False,
        source_pins=PINS, evidence_bytes=sum(len(io._wire(row)) for row, _ in entries),
        archive_reopens=0, new_r559f_attempts=0, new_phase_scans=0, new_conic_solves=0, wall_ns=WALL_NS,
        original_elapsed_before_receipt_ns=entries[2][0]["elapsed_before_receipt_ns"],
        zero_encoding=dict(phase_index=0, velocity_component_index=0, original="0E-569", audit_view="0"),
        **binding["FLAGS"],
    )
    check()
    result["elapsed_ns"] = monotonic_ns() - started
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
