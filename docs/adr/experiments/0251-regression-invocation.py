"""Run both unchanged Makefile test targets on one frozen checkout."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

repo = Path('/Users/agrudin/dev/my/ariadna')
prefix = Path('/private/tmp/ariadna-0251')

def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=repo, text=True)

def snapshot() -> dict[str, object]:
    names = sorted(filter(None, git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0')))
    return {
        'revision': git('rev-parse', 'HEAD').strip(),
        'git_status': git('status', '--porcelain=v1', '--untracked-files=all'),
        'sha256': {name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in names},
    }

before = snapshot()
Path(str(prefix) + '-frozen-checkout.json').write_text(json.dumps(before, indent=2) + '\n')
results = []
with Path(str(prefix) + '-regression.log').open('xb') as log:
    for lane, target in [('portable', 'test-unit'), ('live', 'test-live')]:
        env = os.environ.copy()
        env['PYTEST_ADDOPTS'] = '--junitxml=' + str(prefix) + '-' + lane + '.xml'
        command = ['make', target, 'CONDA=/opt/homebrew/bin/conda']
        started = time.monotonic()
        process = subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
        log.flush()
        after = snapshot()
        unchanged = after == before
        item = {'lane': lane, 'command': command, 'pytest_addopts': env['PYTEST_ADDOPTS'],
                'returncode': process.returncode, 'elapsed_s': time.monotonic() - started,
                'checkout_unchanged': unchanged}
        results.append(item)
        Path(str(prefix) + '-progress.json').write_text(json.dumps(results, indent=2) + '\n')
        if process.returncode != 0 or not unchanged:
            raise SystemExit(f'{lane} failed or checkout changed: {item}')
verification = {'status': 'passed', 'revision': before['revision'],
                'files_unchanged': len(before['sha256']), 'git_status_unchanged': True,
                'frozen_manifest_sha256': hashlib.sha256(Path(str(prefix) + '-frozen-checkout.json').read_bytes()).hexdigest(),
                'lanes': results}
Path(str(prefix) + '-freeze-verification.json').write_text(json.dumps(verification, indent=2) + '\n')
print(json.dumps(verification, indent=2))
