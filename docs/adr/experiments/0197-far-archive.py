"""Lossless, bounded JSON-lines shards for the private ADR0196 check."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from typing import Any

type Row = dict[str, Any]
type Check = Callable[[], None]
SCHEMA = "ADR0196/shards-v1"


@dataclass(frozen=True, slots=True)
class Limits:
    shard_raw: int = 16 * 2**20
    raw: int = 2 * 2**30
    zipped: int = 512 * 2**20
    metadata: int = 2**20
    free: int = 4 * 2**30


def need(ok: object, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def wire(value: object) -> bytes:
    return (json.dumps(value, allow_nan=False, ensure_ascii=True, separators=(",", ":")) + "\n").encode()


def reject_constant(word: str) -> Any:
    raise ValueError("nonfinite JSON: " + word)


def members(pairs: list[tuple[str, Any]]) -> Row:
    result: Row = {}
    for key, value in pairs:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def decode(raw: bytes) -> Any:
    return json.loads(raw, parse_constant=reject_constant, object_pairs_hook=members)


def regular(path: Path) -> None:
    need(path.is_file() and not path.is_symlink(), f"required regular file: {path.name}")


def read(path: Path, limit: int) -> bytes:
    regular(path)
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    need(len(data) <= limit, f"file size limit: {path.name}")
    return data


def metadata_bytes(parent: Path) -> int:
    total = 0
    for file in [*parent.glob("*.json"), *parent.glob("*/manifest.json")]:
        regular(file)
        total += file.stat().st_size
    return total


def put(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def put_json(path: Path, row: Row, parent: Path, limit: int) -> str:
    raw = wire(row)
    need(metadata_bytes(parent) + len(raw) <= limit, "combined metadata byte cap")
    put(path, raw)
    return sha256(raw).hexdigest()


def preflight(directory: Path, limits: Limits) -> None:
    need(directory.is_dir() and not directory.is_symlink(), "evidence parent must exist")
    need(shutil.disk_usage(directory).free >= limits.free, "evidence free space floor")


class Writer:
    """Keep only one uncompressed shard in memory; sync each committed prefix."""

    def __init__(self, path: Path, binding: Row, check: Check, limits: Limits = Limits(),
                 *, used_raw: int = 0, used_zip: int = 0) -> None:
        self.path = path
        self.binding = binding
        self.check = check
        self.limits = limits
        self.raw = used_raw
        self.zipped = used_zip
        self.start_raw = used_raw
        self.start_zip = used_zip
        self.total = 0
        self.kinds: Counter[str] = Counter()
        self.buffer = bytearray()
        self.parts: list[Row] = []
        self.in_part = 0
        self.sealed = False
        self.failed = False
        path.mkdir(mode=0o700)

    def append(self, kind: str, row: Row) -> None:
        self.check()
        need(not self.sealed and not self.failed and type(kind) is str and kind.isidentifier()
             and type(row) is dict, "archive record shape or closed writer")
        line = wire([kind, row])
        need(len(line) <= self.limits.shard_raw, "individual record size cap")
        if len(self.buffer) + len(line) > self.limits.shard_raw:
            self.flush()
        need(self.raw + len(self.buffer) + len(line) <= self.limits.raw, "combined raw byte cap")
        self.buffer.extend(line)
        self.in_part += 1
        self.total += 1
        self.kinds[kind] += 1

    def flush(self) -> None:
        if not self.buffer:
            return
        self.check()
        raw = self.buffer
        packed = gzip.compress(raw, compresslevel=1, mtime=0)
        need(self.zipped + len(packed) <= self.limits.zipped, "combined compressed byte cap")
        number = len(self.parts)
        meta = {
            "first": self.total - self.in_part, "rows": self.in_part,
            "raw": len(raw), "gzip": len(packed),
            "raw_sha256": sha256(raw).hexdigest(), "gzip_sha256": sha256(packed).hexdigest(),
        }
        # A single synced shard contains its own prefix index: recovery never
        # uses a half-written shard or needs to guess raw count/length limits.
        header = wire(meta)
        temporary = self.path / f"{number:05d}.partial"
        final = self.path / f"{number:05d}.shard"
        self.failed = True
        put(temporary, header + packed)
        need(not final.exists(), "shard already exists")
        temporary.rename(final)
        fd = os.open(self.path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        self.parts.append(meta)
        self.raw += len(raw)
        self.zipped += len(packed)
        self.buffer.clear()
        self.in_part = 0
        self.failed = False
        self.check()

    def seal(self, status: str, summary: Row) -> str:
        need(not self.sealed and status in ("passed", "partial"), "phase already sealed")
        if status == "passed":
            need(not self.failed, "cannot accept failed evidence write")
            self.flush()
        elif not self.failed:
            # Scientific failures can retain buffered complete records too.
            try:
                self.flush()
            except (OSError, ValueError, RuntimeError):
                self.failed = True
        total = sum(part["rows"] for part in self.parts)
        digest = put_json(self.path / "manifest.json", {
            "schema": SCHEMA, "binding": self.binding, "status": status,
            "summary": summary, "parts": self.parts, "rows": total,
            "kinds": dict(self.kinds) if total == self.total and not self.failed else None,
            "raw": self.raw-self.start_raw, "gzip": self.zipped-self.start_zip,
        }, self.path.parent, self.limits.metadata)
        self.sealed = True
        return digest


class Reader:
    """Check the complete ordered stream without retaining the expanded archive."""

    def __init__(self, path: Path, check: Check, limits: Limits = Limits()) -> None:
        self.path, self.check, self.limits = path, check, limits
        need(path.is_dir() and not path.is_symlink(), "invalid shard directory")
        raw = read(path/"manifest.json", limits.metadata)
        self.digest = sha256(raw).hexdigest()
        self.manifest = decode(raw)
        m = self.manifest
        need(type(m) is dict and m.get("schema") == SCHEMA and m.get("status") in ("passed", "partial"),
             "invalid shard manifest")
        parts = m.get("parts")
        need(type(parts) is list and all(type(p) is dict for p in parts), "invalid shard list")
        expected = {f"{i:05d}.shard" for i in range(len(parts))}
        need({p.name for p in path.glob("*.shard")} == expected, "shard inventory")
        need(m["status"] == "partial" or {p.name for p in path.iterdir()} == expected | {"manifest.json"},
             "unexpected file in complete evidence")

    @classmethod
    def recover_prefix(cls, path: Path, check: Check, limits: Limits = Limits()) -> Reader:
        """Reconstruct only a synced prefix if the parent killed an unsealed phase."""
        need(path.is_dir() and not path.is_symlink() and not (path/"manifest.json").exists(),
             "an unsealed shard directory is required")
        shards = sorted(path.glob("*.shard"))
        parts: list[Row] = []
        for i, file in enumerate(shards):
            check()
            need(file.name == f"{i:05d}.shard", "recovery shard inventory")
            regular(file)
            with file.open("rb") as stream:
                header = stream.readline(1025)
            need(len(header) <= 1024 and header.endswith(b"\n"), "recovery header bounds")
            meta = decode(header)
            need(type(meta) is dict and wire(meta) == header, "recovery shard header")
            parts.append(meta)
        need(sum(len(wire(part)) for part in parts) <= limits.metadata, "recovery metadata cap")
        reader = cls.__new__(cls)
        reader.path, reader.check, reader.limits = path, check, limits
        reader.digest = None
        reader.manifest = {
            "schema": SCHEMA, "status": "partial", "parts": parts, "kinds": None,
            **{key: sum(part[key] for part in parts) for key in ("rows", "raw", "gzip")},
        }
        return reader

    def records(self) -> Iterator[tuple[str, Row]]:
        m = self.manifest
        seen: Counter[str] = Counter()
        count = raw_total = compressed_total = 0
        for i, expected in enumerate(m["parts"]):
            self.check()
            need(expected["first"] == count, "shard ordinal")
            for key, high in (("raw", self.limits.shard_raw), ("gzip", self.limits.zipped),
                              ("rows", self.limits.shard_raw)):
                need(type(expected[key]) is int and 0 < expected[key] <= high, "shard size or count")
            raw_total += expected["raw"]
            compressed_total += expected["gzip"]
            need(raw_total <= self.limits.raw and compressed_total <= self.limits.zipped, "archive size cap")
            filename = self.path / f"{i:05d}.shard"
            header = wire(expected)
            data = read(filename, len(header) + expected["gzip"])
            need(data[:len(header)] == header, "shard header binding")
            packed = data[len(header):]
            need(len(packed) == expected["gzip"] and sha256(packed).hexdigest() == expected["gzip_sha256"],
                 "compressed shard digest/size")
            from io import BytesIO

            before = count
            with gzip.GzipFile(fileobj=BytesIO(packed)) as stream:
                raw = stream.read(expected["raw"] + 1)
            need(len(raw) == expected["raw"] and sha256(raw).hexdigest() == expected["raw_sha256"],
                 "raw shard digest/size")
            at = 0
            while at < len(raw):
                ending = raw.find(b"\n", at)
                need(ending >= at, "unterminated archive record")
                pair = decode(raw[at:ending])
                at = ending + 1
                need(type(pair) is list and len(pair) == 2 and type(pair[0]) is str
                     and pair[0].isidentifier() and type(pair[1]) is dict, "invalid archive record")
                kind, row = pair
                count += 1
                seen[kind] += 1
                yield kind, row
            need(count-before == expected["rows"], "shard record count")
        need((m["rows"], m["raw"], m["gzip"]) == (count, raw_total, compressed_total), "archive totals")
        need(m["kinds"] == dict(seen) or (m["status"] == "partial" and m["kinds"] is None),
             "archive record inventory")

    def verify(self) -> int:
        return sum(1 for _ in self.records())
