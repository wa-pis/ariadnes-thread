"""Fabricated 17-role metadata over the existing artificial 72-box archive."""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

from matched_norm_fixtures import (
    CANDIDATE, REFERENCE, ROLES, SCOPE, fabricated_archive as six_role_archive,
    rechain, wire,
)

SELECTED_ROLES = ("bounds", "checks", "interval", "runner", "trace", "trace_schema")
EXTRA_ROLES = (
    "anchors", "archive", "containment", "core", "io", "oracle", "orbit",
    "points", "reader", "screen", "study",
)
type Row = dict[str, Any]


def fabricated_archive() -> Row:
    """Add invented provenance hashes; selected source bindings stay unchanged."""
    archive = six_role_archive()
    selected = deepcopy(archive["_context"]["source_pins"])
    assert set(selected) == set(SELECTED_ROLES)
    metadata = selected | {
        role: sha256(("fabricated metadata provenance: " + role).encode()).hexdigest()
        for role in EXTRA_ROLES
    }
    for role in ("attempt", "report", "receipt"):
        archive[role]["method_sha256"] = deepcopy(metadata)
    archive["_context"]["source_pins"] = selected
    rechain(archive)
    return archive


def write_artificial_pack(folder: Path, *, archive: Row | None = None) -> Row:
    """Write only seven fabricated records with a fixed content-pinned profile."""
    archive = fabricated_archive() if archive is None else archive
    folder.mkdir()
    inputs, pins = {}, {}
    for role in ROLES:
        path = folder / (role + ".json")
        raw = wire(archive[role])
        with path.open("xb") as stream:
            stream.write(raw)
        inputs[role] = str(path.absolute())
        pins[role] = dict(sha256=sha256(raw).hexdigest(), bytes=len(raw))
    return dict(scope=SCOPE, inputs=inputs, pins=pins, expected_events=1248,
                reference_sha256=REFERENCE, candidate_id=CANDIDATE,
                completion_sha256=pins["completion"]["sha256"])
