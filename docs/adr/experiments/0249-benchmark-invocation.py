"""Recorded artificial F3 invocation; zero mission/SPICE/native work."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main() -> int:
    output = Path('/private/tmp/ariadna-0249-coupled-benchmark')
    log = Path('/private/tmp/ariadna-0249-coupled-benchmark-cli.log')
    receipt = Path('/private/tmp/ariadna-0249-coupled-launch.json')
    started = time.monotonic()
    command = [sys.executable, '-m', 'space_nav._coupled_benchmark_run',
               str(output), '--parent-start', repr(started)]
    with log.open('xb') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                timeout=300.0, check=False)
    elapsed = time.monotonic() - started
    packet = {'command': command, 'exit_code': result.returncode,
              'external_elapsed_s': elapsed, 'external_limit_s': 300.0,
              'scope': 'artificial benchmark only; no mission data/SPICE/native work'}
    with receipt.open('x') as stream:
        json.dump(packet, stream, allow_nan=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    if time.monotonic() - started >= 300.0:
        raise RuntimeError('external startup-through-receipt deadline exceeded')
    print(json.dumps(packet, allow_nan=False))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
