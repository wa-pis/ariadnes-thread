"""Run the ADR0191 saved-state range audit once with a finalization receipt."""

from collections.abc import Callable
from hashlib import sha256
import json
import os
from pathlib import Path
import runpy
import sys
from time import monotonic
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BUDGET_S = 10.0


class BudgetExceeded(ValueError):
    """The saved-data operation exceeded its inclusive time allowance."""


def save_json(path: Path, value: dict[str, Any], *, exclusive: bool = True) -> str:
    """Flush finite evidence to a new file and return the stored digest."""
    encoded = (json.dumps(value, allow_nan=False, indent=2) + "\n").encode()
    with path.open("xb" if exclusive else "wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return sha256(encoded).hexdigest()


def worksheet(report: dict[str, Any], check: Callable[[], None]) -> None:
    """Read pinned archives and compare both sign paths for each required grid."""
    directory = Path(__file__).resolve().parent
    source_files = [directory / f"0192-range-{role}.py"
                    for role in ("run", "inputs", "brackets")]
    report["worksheet_sha256"] = {
        path.name: sha256(path.read_bytes()).hexdigest() for path in source_files
    }
    inputs = runpy.run_path(str(source_files[1]))
    analysis = runpy.run_path(str(source_files[2]))
    grids, report["inputs_sha256"] = inputs["load"](ROOT, check)
    analysis["analyze"](grids, report, check)


def execute(directory: Path, work: Callable[[dict[str, Any], Callable[[], None]], None],
            clock: Callable[[], float] = monotonic) -> int:
    """Bind one attempt, its finalized evidence and a fail-closed receipt."""
    started_s = clock()

    def check() -> None:
        if clock() - started_s > BUDGET_S:
            raise BudgetExceeded("R5.45 exceeded the 10 s offline cap")

    targets = [directory / f"{name}.json" for name in ("attempt", "evidence", "receipt")]
    if any(path.exists() or path.is_symlink() for path in targets):
        raise FileExistsError("R5.45 output already exists; do not retry")
    attempt, evidence, receipt_path = targets
    attempt_sha = save_json(attempt, {"contract": "ADR0191", "stage": "R5.45",
                                     "started_s": started_s})
    report: dict[str, Any] = {
        "contract": "ADR0191", "stage": "R5.45", "status": "partial",
        "marker_radius_m": 3_000_000, "budget_s": BUDGET_S,
        "native_calls": 0, "kernel_loads": 0, "record_evaluations": 0,
        "scientific_imports": 0, "spacecraft_propagations": 0,
        "time_scale": "TDB seconds since J2000", "origin": "SSB",
        "orientation": "J2000", "position_units": "m", "velocity_units": "m/s",
        "continuous_safety_verified": False,
    }
    try:
        check()
        work(report, check)
        check()
        report["status"] = "passed"
    except (OSError, ValueError, KeyError, TypeError, IndexError, ArithmeticError) as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"

    report["elapsed_before_flush_s"] = clock() - started_s
    evidence_sha = save_json(evidence, report)
    elapsed_s = clock() - started_s
    receipt: dict[str, Any] = {
        "contract": "ADR0191", "stage": "R5.45", "started_s": started_s,
        "attempt_sha256": attempt_sha, "evidence_sha256": evidence_sha,
        "elapsed_s": elapsed_s, "finalization_gate": (
            "passed" if elapsed_s <= BUDGET_S else "failed"),
        "status": report["status"] if elapsed_s <= BUDGET_S else "partial",
    }
    save_json(receipt_path, receipt)
    if clock() - started_s > BUDGET_S:
        # Correct only the receipt; the raw evidence and attempt remain immutable.
        receipt.update(status="partial", finalization_gate="failed",
                       elapsed_s=clock() - started_s)
        save_json(receipt_path, receipt, exclusive=False)
    return 0 if receipt["status"] == "passed" else 2


def main() -> int:
    """Run in an isolated stdlib interpreter against one existing output directory."""
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise ValueError("use the pinned Python interpreter with -I -S -B")
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_dir():
        raise ValueError("expected one existing, unused output directory")
    return execute(Path(sys.argv[1]), worksheet)


if __name__ == "__main__":
    raise SystemExit(main())
