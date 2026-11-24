"""Cold-start/full-volume qualification uses fabricated affine arcs only."""

from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


# This is a test subprocess, not a production launcher or mission propagator.
_FIXTURE = r'''
import builtins
import json
import os
from pathlib import Path
import sys
import time

original_import = builtins.__import__

def guarded_import(name: str, *args: object, **kwargs: object) -> object:
    if name.split('.')[0] in {'numpy', 'scipy', 'tudatpy', 'spiceypy'}:
        raise ImportError('artificial bridge forbids ' + name)
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import

def guard_files(event: str, args: tuple[object, ...]) -> None:
    if event == 'open' and args and isinstance(args[0], (str, bytes)):
        name = os.fsdecode(args[0]).replace('\\', '/')
        if ('/docs/adr/experiments/' in name or name.endswith(
                ('.bsp', '.tls', '.tpc', 'moon_to_mars.py'))):
            raise RuntimeError('artificial bridge forbids archive/kernel access')

sys.addaudithook(guard_files)
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from fractions import Fraction
from space_nav import _coupled_bridge as bridge

budget = bridge.Budget(started_s=float(sys.argv[1]))
raw = sys.stdin.buffer.read(65537)
budget.check_input_bytes(raw)
payload = json.loads(raw)
spec = bridge.BridgeSpec(
    initial_state=tuple(payload['initial_state']),
    target_state=tuple(payload['target_state']),
    t0_s=payload['t0_s'], tf_s=payload['tf_s'],
    initial_mass_kg=2000.0, dry_mass_kg=500.0,
    thrust_n=1000.0, isp_s=450.0,
    anchors=tuple(tuple(v) for v in payload['anchors']), artificial=True,
)
unknowns = tuple(payload['unknowns'])
contexts = 0
closed = 0
calls = 0
rate = Fraction(1000.0 / float(9.80665 * 450.0))

@contextmanager
def factory() -> Iterator[Callable[[bridge.ArcRequest], bridge.ArcResponse]]:
    global contexts, closed
    contexts += 1
    local_calls = 0
    def affine(request: bridge.ArcRequest) -> bridge.ArcResponse:
        global calls
        nonlocal local_calls
        local_calls += 1
        calls += 1
        dt = request.end_event.exact_s - request.start_event.exact_s
        start = request.start_state
        # Closed-form affine test flow; no force or integration is evaluated.
        state = tuple(float(Fraction(start[i]) + Fraction(start[i+3])*dt)
                      for i in range(3)) + tuple(start[3:])
        mass = Fraction(request.start_mass_kg)
        if request.burn_id is not None:
            mass -= rate * dt
        return bridge.ArcResponse(state, float(mass), request.end_event, True, True)
    try:
        yield affine
    finally:
        closed += 1
        if local_calls != 3:
            raise AssertionError('incomplete artificial context')

for _ in range(73):
    result = bridge.evaluate(spec, unknowns, mode='shooting',
                             arc_factory=factory, budget=budget)
for _ in range(3):
    result = bridge.evaluate(spec, unknowns, mode='replay', diagnostic=True,
                             arc_factory=factory, budget=budget)
producer_elapsed = time.monotonic() - float(sys.argv[1])
report = {
    'scope': 'fabricated affine interface qualification only',
    'counts': budget.snapshot(), 'counts_phase': 'producer-before-summary-write',
    'contexts': contexts, 'closed': closed,
    'arc_calls': calls, 'producer_elapsed_s': producer_elapsed,
    'max_raw_defect': max(abs(v) for v in result.raw_defects),
    'inherited_start_s': float(sys.argv[1]),
}
assert not ({name.split('.')[0] for name in sys.modules} & {'numpy', 'scipy', 'tudatpy', 'spiceypy'})
data = (json.dumps(report, sort_keys=True) + '\n').encode()
budget.check_output_bytes(data)
budget.check_finalization()
with Path(sys.argv[2]).open('xb') as stream:
    stream.write(data)
    stream.flush()
    os.fsync(stream.fileno())
budget.check_finalization()
'''


def _input_bytes() -> bytes:
    initial = (float(2**37 + 10_000_000), float(-(2**37)), float(2**36),
               float(2**14), 1000.0, float(-(2**13)))

    def point(elapsed_s: int) -> list[float]:
        return [initial[i] + initial[i + 3] * elapsed_s for i in range(3)] + list(initial[3:])

    packet = {
        "initial_state": initial,
        "target_state": point(10_000),
        "t0_s": 1_000_000_000.0,
        "tf_s": 1_000_010_000.0,
        "anchors": [point(1000), point(9000)],
        "unknowns": [0.0, 0.0, 1000.0, 0.0, 0.0, 1000.0] + [0.0] * 12,
    }
    return json.dumps(packet, allow_nan=False).encode()


def _run_fixture(
    tmp_path: Path, raw: bytes, *, prior_elapsed_s: float = 0.0,
) -> tuple[subprocess.CompletedProcess[bytes], float, Path]:
    started_s = time.monotonic() - prior_elapsed_s
    target = tmp_path / "summary.json"
    remaining_s = started_s + 15.0 - time.monotonic()
    result = subprocess.run(
        [sys.executable, "-c", _FIXTURE, repr(started_s), str(target)],
        input=raw, capture_output=True, check=False, timeout=max(remaining_s, 0.01),
    )
    return result, started_s, target


def test_full_volume_from_cold_start_and_durable_summary(
    tmp_path: Path, record_testsuite_property: Callable[[str, object], None],
) -> None:
    # Exact input byte boundary, without changing the fabricated mathematical data.
    raw = _input_bytes().ljust(64 * 1024, b" ")
    process, started_s, target = _run_fixture(tmp_path, raw)
    assert process.returncode == 0, process.stderr.decode(errors="replace")
    assert process.stdout == b"" and process.stderr == b""
    report = json.loads(target.read_bytes())
    counts = report["counts"]
    assert counts["control_attempts"] == 73
    assert counts["propagation_evaluations"] == 76
    assert counts["simulated_arc_slots"] == 228
    assert report["contexts"] == report["closed"] == 76
    assert report["arc_calls"] == 228
    assert report["max_raw_defect"] == 0.0
    assert report["inherited_start_s"] == started_s
    assert report["producer_elapsed_s"] < 10.0
    assert counts["native_propagations"] == 0
    assert counts["spice_queries"] == 0
    assert counts["kernel_reads"] == 0
    assert counts["real_archive_reads"] == 0
    assert counts["integrations"] == 0
    assert counts["optimizer_calls"] == 0
    receipt = tmp_path / "outer-receipt.json"
    with receipt.open("xb") as stream:
        stream.write(json.dumps({"started_s": started_s, "child_returncode": 0,
                                 "durable_child_summary_bytes": target.stat().st_size}).encode())
        stream.flush()
        os.fsync(stream.fileno())
    assert sum(p.stat().st_size for p in tmp_path.iterdir()) <= 128 * 1024
    elapsed_s = time.monotonic() - started_s
    assert elapsed_s < 15.0
    record_testsuite_property("ariadna_f5_full_volume", json.dumps({
        "producer_report": report, "input_bytes": len(raw),
        "durable_output_bytes": sum(p.stat().st_size for p in tmp_path.iterdir()),
        "external_after_receipt_elapsed_s": elapsed_s,
    }, sort_keys=True))


def test_worker_rejects_excess_input_before_decoding(tmp_path: Path) -> None:
    process, _, target = _run_fixture(tmp_path, b" " * (64 * 1024 + 1))
    assert process.returncode != 0
    assert b"input" in process.stderr.lower()
    assert not target.exists()


def test_worker_cannot_reset_an_expired_producer_clock(tmp_path: Path) -> None:
    process, _, target = _run_fixture(tmp_path, _input_bytes(), prior_elapsed_s=10.01)
    assert process.returncode != 0
    assert b"deadline" in process.stderr.lower() or b"producer" in process.stderr.lower()
    assert not target.exists()


def test_external_watchdog_stops_a_stalled_fixture() -> None:
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run([sys.executable, "-c", "import time; time.sleep(30)"],
                       capture_output=True, check=False, timeout=0.1)
