"""Bound the two R5.37 phases; never launch a study from preparation/tests."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from time import monotonic
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "0183-verification.json"
GIT = "/opt/homebrew/bin/git"
CHILD = """
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import monotonic
from types import ModuleType

phase, name, digest, start, output, saved, manifest_path, manifest_sha = sys.argv[1:]
started = float(start)
assert 0 <= monotonic()-started < (60 if phase == 'study' else 10)
raw = Path(manifest_path).read_bytes()
assert sha256(raw).hexdigest() == manifest_sha
assert json.loads(raw)['preparation_complete'] is True
source = Path(name).read_bytes()
assert sha256(source).hexdigest() == digest
module = ModuleType('r537_' + phase)
module.__file__ = name
sys.modules[module.__name__] = module
exec(compile(source, name, 'exec'), module.__dict__)
if phase == 'study':
    report = module.execute(Path(output), started_s=started, manifest_sha256=manifest_sha)
    status = report['status']
else:
    report = module.audit(Path(saved), Path(output), started_s=started, manifest_sha256=manifest_sha)
    status = report['audit_status']
raise SystemExit(0 if status == 'passed' and report['finalization_gate'] == 'passed' else 2)
"""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def git(*args: str) -> bytes:
    return subprocess.check_output([GIT, *args], cwd=ROOT)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def existing_digest(path: Path) -> str | None:
    return digest(path) if path.is_file() else None


def write_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()


def snapshot() -> dict[str, str]:
    return {name: digest(ROOT/name) for name in git("ls-files", "-z").decode().split("\0") if name}


def run_child(command: list[str], watchdog_s: float) -> dict[str, Any]:
    try:
        child = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=watchdog_s,
                               check=False)
        return {"returncode": child.returncode, "stderr": child.stderr}
    except subprocess.TimeoutExpired:
        return {"returncode": None, "stderr": f"parent watchdog ({watchdog_s:g} s)"}
    except OSError as error:
        return {"returncode": None, "stderr": f"child start: {error}"}


def launch(phase: str, directory: Path, expected_manifest_sha256: str) -> dict[str, Any]:
    require(phase in ("study", "audit"), "unknown phase")
    require(directory.is_dir() and not directory.resolve().is_relative_to(ROOT), "evidence directory outside checkout")
    require(Path(sys.executable).resolve().parent.parent.name == "space-nav", "pinned space-nav Python required")
    manifest_raw = MANIFEST.read_bytes()
    require(sha256(manifest_raw).hexdigest() == expected_manifest_sha256, "preparation manifest digest")
    manifest = json.loads(manifest_raw)
    require(manifest["preparation_complete"] is True, "verified preparation required")
    for group in ("tested_source_sha256", "design_input_sha256"):
        for name, expected in manifest[group].items():
            require(digest(ROOT/name) == expected, "preparation file digest: " + name)
    revision = git("rev-parse", "HEAD").decode().strip()
    require(git("branch", "--show-current").strip() == b"dev" and git("rev-parse", "origin/dev").strip() == revision.encode()
            and not git("status", "--porcelain"), "clean synchronized dev required")
    before = snapshot()
    saved = directory / "study.json"
    output = directory / (phase + ".json")
    child_marker, child_receipt = (output.with_suffix(s) for s in (".attempt.json", ".receipt.json"))
    parent_marker, parent_receipt = (output.with_suffix(s) for s in (".parent-attempt.json", ".parent-receipt.json"))
    require(not any(p.exists() for p in (output, child_marker, child_receipt, parent_marker, parent_receipt)),
            "once-only evidence already exists")
    if phase == "audit":
        require(saved.is_file() and saved.with_suffix(".parent-attempt.json").is_file()
                and saved.with_suffix(".parent-receipt.json").is_file(), "saved study and parent evidence required")

    helper = HERE / f"0183-earth-{phase}.py"
    pinned = manifest["tested_source_sha256"][str(helper.relative_to(ROOT))]
    duration = 60. if phase == "study" else 10.
    flags = ["-I", "-B"] if phase == "study" else ["-I", "-S", "-B"]
    write_json(parent_marker, {"contract": "ADR0182", "phase": phase, "revision": revision,
                               "preparation_sha256": expected_manifest_sha256})
    started = monotonic()
    result = run_child([sys.executable, *flags, "-c", CHILD, phase, str(helper), pinned, repr(started),
                        str(output), str(saved), str(MANIFEST), expected_manifest_sha256], duration + 5.)
    try:
        frozen = (snapshot() == before and git("rev-parse", "HEAD").strip() == revision.encode()
                  and not git("status", "--porcelain"))
    except (OSError, subprocess.SubprocessError) as error:
        result["checkout_error"] = str(error)
        frozen = False
    result.update(contract="ADR0182", phase=phase, revision=revision, started_s=started,
                  parent_attempt_sha256=digest(parent_marker), attempt_sha256=existing_digest(child_marker),
                  evidence_sha256=existing_digest(output), child_receipt_sha256=existing_digest(child_receipt),
                  preparation_sha256=expected_manifest_sha256,
                  checkout_frozen=frozen)
    try:
        receipt = json.loads(child_receipt.read_bytes()) if child_receipt.is_file() else {}
        require(type(receipt) is dict, "child receipt object")
    except (ValueError, OSError) as error:
        result["receipt_error"] = str(error)
        receipt = {}
    child_elapsed = receipt.get("elapsed_s")
    elapsed = monotonic()-started
    finalized = (result["checkout_frozen"] and result["returncode"] in (0, 2)
                 and receipt.get("finalization_gate") == "passed" and receipt.get("started_s") == started
                 and receipt.get("status") in (("passed",) if result["returncode"] == 0
                                               else ("failed", "partial", "rejected"))
                 and receipt.get("evidence_sha256") == result["evidence_sha256"]
                 and result["attempt_sha256"] is not None and result["evidence_sha256"] is not None
                 and type(child_elapsed) in (int, float) and 0 <= child_elapsed <= elapsed < duration)
    result.update(elapsed_s=elapsed, finalization_gate="passed" if finalized else "failed")
    write_json(parent_receipt, result)
    if finalized and not monotonic()-started < duration:
        result.update(elapsed_s=monotonic()-started, finalization_gate="failed")
        parent_receipt.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: launch PHASE EVIDENCE_DIRECTORY PREPARATION_MANIFEST_SHA256")
    receipt = launch(sys.argv[1], Path(sys.argv[2]).resolve(), sys.argv[3])
    raise SystemExit(0 if receipt["returncode"] == 0 and receipt["finalization_gate"] == "passed" else 2)
