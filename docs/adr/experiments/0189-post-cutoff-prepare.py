"""Bind R5.42 tested sources to the frozen R5.41 design and archives."""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
import json
from pathlib import Path

ARTIFACTS = Path("docs/adr/experiments")
DESIGN = ARTIFACTS / "0188-design-inputs.json"
PREPARATION = ARTIFACTS / "0189-verification.json"
R539 = ARTIFACTS / "0186-verification.json"
R539_SHA256 = "3f0c4cd0cc41671f247420f8c632999f00cad2ecfd2c5e788e25c2ea6fed0e9b"
SCRIPTS = tuple(ARTIFACTS / f"0189-post-cutoff-{role}.py" for role in (
    "study", "audit", "inputs", "direction", "direction-audit", "launch", "prepare",
))
TESTS = tuple(Path("tests") / f"test_post_cutoff{suffix}.py" for suffix in (
    "", "_direction", "_inputs",
))
GUARD = ARTIFACTS / "0189" / "pytest-offline-guard.py.txt"


def require(ok: bool, label: str) -> None:
    if not ok:
        raise ValueError(label)


def verify(root: Path, expected_sha256: str, check: Callable[[], None]) -> dict[str, str]:
    """Check the preparation digest, its required entries and every pinned file."""
    def read(name: str | Path, digest: str) -> bytes:
        path = Path(name)
        require(not path.is_absolute() and ".." not in path.parts, "unsafe preparation path")
        check()
        data = (root / path).read_bytes()
        require(sha256(data).hexdigest() == digest, "preparation file digest: " + str(path))
        check()
        return data

    manifest = json.loads(read(PREPARATION, expected_sha256))
    require(manifest["stage"] == "R5.42" and manifest["contract"] == "ADR0188"
            and manifest["preparation_complete"] is True, "verified R5.42 preparation required")
    pins = manifest["design_input_sha256"]
    design = json.loads(read(DESIGN, pins[str(DESIGN)]))
    require(design["stage"] == "R5.41" and design["contract"] == "ADR0188", "R5.41 design identity")
    old = json.loads(read(R539, R539_SHA256))
    needed = design["immutable_input_sha256"] | old["design_input_sha256"] | {str(DESIGN): pins[str(DESIGN)]}
    tested = manifest["tested_source_sha256"]
    old_sources = old["tested_source_sha256"]
    require(pins == needed and set(tested) == set(old_sources) | {str(p) for p in (*SCRIPTS, *TESTS, GUARD)}
            and all(tested[k] == v for k, v in old_sources.items()), "incomplete preparation bindings")
    for name, digest in (pins | tested).items():
        read(name, digest)
    return tested
