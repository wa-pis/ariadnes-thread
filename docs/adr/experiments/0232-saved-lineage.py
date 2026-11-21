"""Bounded stdlib-only archive readback; historical scientific code is text only."""

# ruff: noqa: E402 -- Start the shared clock before other imports.
from time import monotonic_ns

_ENTRY_NS = monotonic_ns()

from dataclasses import dataclass, field
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable
from types import ModuleType
from uuid import uuid4

type Row = dict[str, Any]
HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
CONTRACT = HERE.with_name("0229-saved-lineage-contract.json")
CONTRACT_SHA = "4c4e6d4c8981428b5931def910aa7d648f7860a9ce5e75d78b16952063a4b087"
OUTPUT = HERE.with_name("0229-saved-lineage-result")
AUDIT = HERE.with_name("0229-saved-lineage-audit.json")
PRIVATE = ("0232-saved-lineage.py", "0230-lineage-core.py", "0230-lineage-audit.py")
ROLES = (
    "attempt",
    "report",
    "receipt",
    "completion",
    "audit",
    "manifest",
    "selection_contract",
)
DATA_NAMES = (
    "0224-retained-trace-result/attempt.json",
    "0224-retained-trace-result/report.json",
    "0224-retained-trace-result/receipt.json",
    "0224-retained-trace-result/completion.json",
    "0224-retained-trace-audit.json",
    "0228-verification.json",
    "0224-retained-trace-contract.json",
)
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
# Source-symbol links accompany stage.event.field aliases and JSON pointers.
SOURCE_REFERENCES = [
    dict(path="docs/adr/experiments/0219-phase-bounds.py", symbol=symbol, line=line)
    for symbol, line in (
        ("_norm2", 47),
        ("_ellipse", 61),
        ("_reverse", 91),
        ("_mass_exclusion", 141),
        ("bounds", 157),
    )
] + [
    dict(
        path="docs/adr/experiments/0219-phase-bounds.py",
        symbol="bounds",
        line=line,
        statement=statement,
    )
    for line, statement in (
        (172, "r, orbital, mu = _ellipse(mars, anomaly, interval, independent)"),
        (176, "speed = _norm2(_sum(orbital, future), interval, independent).sqrt()"),
        (
            177,
            "proof = _mass_exclusion(interval.box(lunar), speed, interval, independent)",
        ),
    )
]
# Content identities of the separately fabricated full and two early-exit profiles.
# Paths are excluded so qualification can run in an isolated temporary directory.
ARTIFICIAL_PROFILES = {
    "82bee745b4838043ce59d5a3735781c857ca7b106e27081964efcbd7da1cc5ec": "full",
    "ae85824e5779e7aabb54e7520e77247ebb1806ff6bb5d6c7d034d794ce6aec59": "before-reverse",
    "4e7f06f3a845312d319dbdd9a85bac63ba655f8d72cc23a2430b66a066acfa76": "mass-exit",
}
WALL_NS = 30_000_000_000
ZERO = dict.fromkeys(
    (
        "new_bounds",
        "new_traces",
        "new_points",
        "new_point_roots",
        "new_oracle_mass",
        "new_norms",
        "new_stage_events",
        "spice_queries",
        "kernel_accesses",
        "force_evaluations",
        "integrations",
        "native_calls",
        "old_audit_replays",
        "r560_attempts",
    ),
    0,
)


def need(ok: object, message: str) -> None:
    if not ok:
        raise ValueError("R5.59r: " + message)


def wire(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def digest(value: Any) -> str:
    return sha256(wire(value)).hexdigest()


def decode(raw: bytes) -> Row:
    def unique(pairs: list[tuple[str, Any]]) -> Row:
        result: Row = {}
        for key, val in pairs:
            need(key not in result, "duplicate key")
            result[key] = val
        return result

    def number(text: str) -> float:
        value = float(text)
        need(math.isfinite(value), "nonfinite number")
        return value

    def invalid(text: str) -> Any:
        raise ValueError("R5.59r: nonfinite " + text)

    row = json.loads(
        raw, object_pairs_hook=unique, parse_float=number, parse_constant=invalid
    )
    need(type(row) is dict, "object record required")
    need(
        raw
        in (
            wire(row),
            (
                json.dumps(row, indent=2, sort_keys=True, allow_nan=False) + "\n"
            ).encode(),
        ),
        "canonical JSON required",
    )
    return row


@dataclass
class Budget:
    started_ns: int = field(default_factory=monotonic_ns)
    clock: Callable[[], int] = monotonic_ns
    invocation_id: str = field(default_factory=lambda: uuid4().hex)
    used: dict[str, int] = field(
        default_factory=lambda: dict(
            event_visits=0, descriptors=0, aliases=0, norm_pairs=0
        )
    )
    source_bytes: int = 0
    seen: set[Path] = field(default_factory=set)

    def check(self) -> None:
        elapsed = self.clock() - self.started_ns
        need(0 <= elapsed < WALL_NS, "deadline exhausted")

    def charge(self, key: str, count: int = 1) -> None:
        self.check()
        limits = dict(event_visits=32768, descriptors=1024, aliases=768, norm_pairs=36)
        need(
            key in limits and type(count) is int and count >= 0, "invalid work counter"
        )
        self.used[key] += count
        need(self.used[key] <= limits[key], key + " cap exhausted")

    def read(self, path: Path, *, source: bool = True, cap: int = 4194304) -> bytes:
        self.check()
        need(path.is_file() and not path.is_symlink(), "missing or symlink file")
        with path.open("rb") as stream:
            raw = stream.read(cap + 1)
        need(len(raw) <= cap, "file byte cap")
        if source and path not in self.seen:
            self.source_bytes += len(raw)
            self.seen.add(path)
            need(self.source_bytes <= 4194304, "source inventory cap")
        self.check()
        return raw


def contract(budget: Budget) -> Row:
    raw = budget.read(CONTRACT)
    need(sha256(raw).hexdigest() == CONTRACT_SHA, "design contract pin")
    return decode(raw)


def retained_profile() -> Row:
    c = contract(Budget())
    table = {item["path"]: item for item in c["input_artifacts"]}
    inputs = {
        role: str(HERE.parent / name)
        for role, name in zip(ROLES, DATA_NAMES, strict=True)
    }
    return dict(
        scope="retained",
        inputs=inputs,
        pins={
            role: {
                key: table[str(Path(path).relative_to(REPO))][key]
                for key in ("sha256", "bytes")
            }
            for role, path in inputs.items()
        },
        expected_events=1248,
        reference_sha256=c["inherited_reference_sha256"],
        candidate_id="d0001-t0035",
        completion_sha256=c["completion_sha256"],
    )


def profile_check(profile: Row, output: Path, audit_path: Path | None = None) -> None:
    need(
        set(profile)
        == {
            "scope",
            "inputs",
            "pins",
            "expected_events",
            "reference_sha256",
            "candidate_id",
            "completion_sha256",
        },
        "profile inventory",
    )
    need(set(profile["inputs"]) == set(ROLES) == set(profile["pins"]), "input roles")
    for key in ("reference_sha256", "completion_sha256"):
        need(
            type(profile[key]) is str
            and len(profile[key]) == 64
            and all(ch in "0123456789abcdef" for ch in profile[key]),
            "profile digest",
        )
    need(
        type(profile["expected_events"]) is int
        and 0 < profile["expected_events"] <= 8192,
        "event count",
    )
    if profile["scope"] == "retained":
        need(
            profile == retained_profile()
            and output == OUTPUT
            and audit_path in (None, AUDIT),
            "fixed retained profile",
        )
    else:
        need(
            profile["scope"] == "artificial-saved-lineage"
            and profile["candidate_id"] == "artificial-saved-lineage-case",
            "artificial identity",
        )
        need(
            profile["reference_sha256"]
            != "6b845f74881f658d2eeea28bfdde43c9190a283da5bb166644bb845c4f847c5b",
            "retained reference",
        )
        need(
            digest({key: value for key, value in profile.items() if key != "inputs"})
            in ARTIFICIAL_PROFILES,
            "unlisted fabricated profile",
        )
        paths = [output, *(Path(p) for p in profile["inputs"].values())]
        if audit_path is not None:
            paths.append(audit_path)
        need(
            all(
                p.is_absolute() and not p.resolve().is_relative_to(REPO) for p in paths
            ),
            "artificial path isolation",
        )
    need(output.is_absolute(), "absolute output required")
    need(
        not any(
            output.resolve() == Path(p).resolve()
            or output.resolve() in Path(p).resolve().parents
            for p in profile["inputs"].values()
        ),
        "output overlaps inputs",
    )
    if audit_path is not None:
        need(
            audit_path.parent == output.parent
            and audit_path != output
            and audit_path not in output.parents,
            "audit sibling required",
        )


def authenticate(profile: Row, budget: Budget, c: Row) -> Row:
    records: Row = {}
    for role in ROLES:
        raw = budget.read(Path(profile["inputs"][role]))
        expected = profile["pins"][role]
        need(
            set(expected) == {"bytes", "sha256"}
            and type(expected["bytes"]) is int
            and len(raw) == expected["bytes"]
            and sha256(raw).hexdigest() == expected["sha256"],
            role + " raw pin",
        )
        records[role] = decode(raw)
    for name in PRIVATE:
        budget.read(HERE.with_name(name))
    pins = {item["path"]: item for item in c["input_artifacts"]}
    source_pins: Row = {}
    for role, path in c["source_bindings"].items():
        raw = budget.read(REPO / path)
        need(
            len(raw) == pins[path]["bytes"]
            and sha256(raw).hexdigest() == pins[path]["sha256"],
            role + " source pin",
        )
        source_pins[role] = pins[path]["sha256"]
    head = records["attempt"]
    need(
        type(head.get("invocation_id")) is str
        and len(head["invocation_id"]) == 32
        and all(ch in "0123456789abcdef" for ch in head["invocation_id"]),
        "source invocation identity",
    )
    need(
        head.get("scope") == profile["scope"]
        and head.get("reference_sha256") == profile["reference_sha256"],
        "archive scope/reference",
    )
    if profile["scope"] != "retained":
        need(
            head.get("candidate_id") == profile["candidate_id"], "artificial candidate"
        )
    for role in ("report", "receipt"):
        row = records[role]
        for key in (
            "scope",
            "reference_sha256",
            "invocation_id",
            "contract_sha256",
            "method_sha256",
        ):
            need(row.get(key) == head.get(key), role + " shared " + key)
    need(
        all(
            head.get("method_sha256", {}).get(role) == pin
            for role, pin in source_pins.items()
        ),
        "method binding",
    )
    rawpins = profile["pins"]
    need(
        records["report"]["attempt_sha256"]
        == records["receipt"]["attempt_sha256"]
        == rawpins["attempt"]["sha256"],
        "attempt chain",
    )
    need(
        records["receipt"]["report_sha256"] == rawpins["report"]["sha256"],
        "report chain",
    )
    need(
        records["completion"]["receipt_sha256"] == rawpins["receipt"]["sha256"],
        "receipt chain",
    )
    need(
        records["audit"]["completion_sha256"]
        == rawpins["completion"]["sha256"]
        == profile["completion_sha256"],
        "completion chain",
    )
    need(
        records["completion"]["proof"] == records["audit"]["proof"],
        "historical proof link",
    )
    need(
        records["report"]["status"] == "observations-verified-attribution-unresolved",
        "prior result status",
    )
    need(
        records["report"]["work"]["events"] == profile["expected_events"],
        "declared event count",
    )
    need(
        head.get("contract_sha256") == c["inherited_contract_sha256"],
        "inherited contract",
    )
    for role in ("attempt", "report", "receipt", "completion", "audit"):
        key = (
            str(Path(profile["inputs"][role]).relative_to(REPO))
            if profile["scope"] == "retained"
            else role
        )
        need(
            records["manifest"]["artifact_sha256"][key] == rawpins[role],
            "manifest " + role,
        )
    if profile["scope"] == "retained":
        need(
            records["manifest"]["stage"] == "R5.59p" and head["stage"] == "R5.59n",
            "retained provenance",
        )
    else:
        need(
            records["manifest"].get("scope") == profile["scope"]
            and records["selection_contract"].get("scope") == profile["scope"]
            and records["selection_contract"].get("reference_sha256")
            == profile["reference_sha256"],
            "mixed artificial metadata",
        )
    records["_context"] = dict(
        scope=profile["scope"],
        source_pins=source_pins,
        expected_events=profile["expected_events"],
        context_justified=True,
        context_assumption=c["context_provenance"],
    )
    budget.check()
    return records


def load_private(part: str) -> Any:
    need(part in ("core", "audit"), "private module selection")
    path = HERE.with_name("0230-lineage-" + part + ".py")
    # Load authenticated private source directly; never consult an adjacent bytecode cache.
    module = ModuleType("_lineage_" + part)
    sys.modules[module.__name__] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def sync_dir(path: Path) -> None:
    handle = os.open(path, os.O_RDONLY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)


def save(path: Path, value: Row, budget: Budget, *, cap: int) -> bytes:
    budget.check()
    raw = wire(value)
    need(len(raw) <= cap, "evidence byte cap")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    sync_dir(path.parent)
    budget.check()
    return raw


def owned_cleanup(path: Path, owner: Path, invocation: str) -> None:
    if path.exists() and owner.exists():
        if decode(owner.read_bytes()).get("invocation_id") == invocation:
            path.unlink()
            sync_dir(path.parent)


def run(output: Path, profile: Row, *, budget: Budget | None = None) -> Row:
    b = budget or Budget()
    c = contract(b)
    profile_check(profile, output)
    need(not os.path.lexists(output), "existing output")
    archive = authenticate(profile, b, c)
    output.mkdir()
    sync_dir(output.parent)
    head = dict(
        stage="R5.59r" if profile["scope"] != "retained" else "R5.59s",
        scope=profile["scope"],
        invocation_id=b.invocation_id,
        contract_sha256=CONTRACT_SHA,
        source_profile_sha256=digest(profile),
        source_pins=profile["pins"],
        source_references=SOURCE_REFERENCES,
        source_inventory_bytes=b.source_bytes,
        physical_status="physical-join-not-established",
        commands=None,
        **ZERO,
    )
    attempt_raw = save(output / "attempt.json", head, b, cap=65536)
    try:
        analysis = load_private("core").analyze(
            archive, c, scope=profile["scope"], check=b.check, charge=b.charge
        )
        report = head | dict(
            attempt_sha256=sha256(attempt_raw).hexdigest(),
            status=analysis["status"],
            analysis=analysis,
            work=dict(b.used),
        )
        report_raw = save(
            output / "report.json",
            report,
            b,
            cap=1048576 - 65536 - len(attempt_raw) - 8192,
        )
        receipt_raw = save(
            output / "receipt.json",
            head
            | dict(
                attempt_sha256=sha256(attempt_raw).hexdigest(),
                report_sha256=sha256(report_raw).hexdigest(),
                elapsed_ns=b.clock() - b.started_ns,
            ),
            b,
            cap=65536,
        )
        completion = dict(
            invocation_id=b.invocation_id,
            receipt_sha256=sha256(receipt_raw).hexdigest(),
            analysis_sha256=digest(analysis),
            elapsed_ns=b.clock() - b.started_ns,
        )
        completion_raw = save(output / "completion.json", completion, b, cap=8192)
        need(
            sum(map(len, (attempt_raw, report_raw, receipt_raw, completion_raw)))
            <= 1048576 - 65536,
            "combined producer byte cap",
        )
        for name, raw in zip(
            FILES, (attempt_raw, report_raw, receipt_raw, completion_raw), strict=True
        ):
            need(
                b.read(output / name, source=False, cap=1048576) == raw,
                "durable byte readback",
            )
        b.check()
        return report
    except (OSError, ValueError, TypeError, KeyError, IndexError, ArithmeticError):
        owned_cleanup(
            output / "completion.json", output / "attempt.json", b.invocation_id
        )
        raise


def audit(
    output: Path,
    profile: Row,
    completion_pin: str,
    *,
    audit_path: Path,
    budget: Budget | None = None,
) -> Row:
    b = budget or Budget()
    c = contract(b)
    profile_check(profile, output, audit_path)
    need(not os.path.lexists(audit_path), "existing audit")
    archive = authenticate(profile, b, c)
    raw = {name: b.read(output / name, source=False, cap=1048576) for name in FILES}
    need(
        sha256(raw["completion.json"]).hexdigest() == completion_pin,
        "new completion pin",
    )
    attempt, report, receipt, completion = (decode(raw[name]) for name in FILES)
    need(
        report["attempt_sha256"]
        == receipt["attempt_sha256"]
        == sha256(raw["attempt.json"]).hexdigest(),
        "new attempt chain",
    )
    need(
        receipt["report_sha256"] == sha256(raw["report.json"]).hexdigest()
        and completion["receipt_sha256"] == sha256(raw["receipt.json"]).hexdigest(),
        "new report/receipt chain",
    )
    need(
        completion["analysis_sha256"] == digest(report["analysis"]),
        "new analysis chain",
    )
    need(
        attempt["source_profile_sha256"] == digest(profile)
        and report["source_pins"] == profile["pins"],
        "new profile identity",
    )
    need(
        all(
            row["invocation_id"] == attempt["invocation_id"]
            for row in (report, receipt, completion)
        ),
        "new invocation identity",
    )
    expected_head = dict(
        stage="R5.59r" if profile["scope"] != "retained" else "R5.59s",
        scope=profile["scope"],
        invocation_id=attempt["invocation_id"],
        contract_sha256=CONTRACT_SHA,
        source_profile_sha256=digest(profile),
        source_pins=profile["pins"],
        source_references=SOURCE_REFERENCES,
        source_inventory_bytes=b.source_bytes,
        physical_status="physical-join-not-established",
        commands=None,
        **ZERO,
    )
    need(wire(attempt) == wire(expected_head), "new attempt identity/work/inventory")
    for row, extra in (
        (report, {"attempt_sha256", "status", "analysis", "work"}),
        (receipt, {"attempt_sha256", "report_sha256", "elapsed_ns"}),
    ):
        need(set(row) == set(expected_head) | extra, "new output inventory")
        need(
            wire({key: row[key] for key in expected_head}) == wire(expected_head),
            "new output identity/work/inventory",
        )
    need(
        set(completion)
        == {"invocation_id", "receipt_sha256", "analysis_sha256", "elapsed_ns"}
        and report["status"] == "lineage-qualified-attribution-unresolved",
        "new completion/status inventory",
    )
    for row in (receipt, completion):
        need(
            type(row["elapsed_ns"]) is int and 0 <= row["elapsed_ns"] < WALL_NS,
            "new elapsed limit",
        )
    need(
        sum(map(len, raw.values())) <= 1048576 - 65536,
        "combined producer byte cap",
    )
    proof = load_private("audit").verify(
        archive,
        c,
        report["analysis"],
        scope=profile["scope"],
        check=b.check,
        charge=b.charge,
    )
    need(
        wire(report["work"]) == wire(proof["counts"]) == wire(b.used),
        "independent work counts differ",
    )
    result = dict(
        invocation_id=b.invocation_id,
        completion_sha256=completion_pin,
        proof=proof,
        status="lineage-independently-verified",
        work=dict(b.used),
        **ZERO,
        elapsed_ns=b.clock() - b.started_ns,
    )
    encoded = wire(result)
    need(
        len(encoded) <= 65536 and sum(map(len, raw.values())) + len(encoded) <= 1048576,
        "combined audit byte cap",
    )
    try:
        saved = save(audit_path, result, b, cap=65536)
        need(
            b.read(audit_path, source=False, cap=65536) == saved,
            "audit durable readback",
        )
        b.check()
    except (OSError, ValueError, TypeError, KeyError, IndexError, ArithmeticError):
        owned_cleanup(audit_path, audit_path, b.invocation_id)
        raise
    return result


def guard(
    profile: Row, output: Path, audit_path: Path | None, *, read_only: bool
) -> None:
    scripts = {str(HERE.with_name(name)) for name in PRIVATE} | {str(CONTRACT)}
    source_paths = {
        str(REPO / path) for path in contract(Budget())["source_bindings"].values()
    }
    inputs = set(profile["inputs"].values())
    outputs = {str(output / name) for name in FILES}
    audits = {str(audit_path)} if audit_path else set()
    dirs = {str(output), str(output.parent), *(str(Path(p).parent) for p in inputs)}
    stdlib = (
        str(
            Path(sys.base_prefix)
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
        )
        + os.sep
    )

    def hook(event: str, args: tuple[Any, ...]) -> None:
        if event == "open" and not isinstance(args[0], int):
            path = os.path.normpath(os.fsdecode(args[0]))
            write = int(args[2]) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            need(
                (path in outputs and (not write or not read_only))
                or path in audits
                or (
                    not write
                    and (
                        path in scripts | source_paths | inputs | dirs
                        or path.startswith(stdlib)
                        and path.endswith((".py", ".pyc", ".so", ".dylib"))
                    )
                ),
                "file outside scope: " + path,
            )
        if event in ("os.listdir", "os.scandir"):
            path = os.path.normpath(os.fsdecode(args[0]))
            need(path in dirs or path.startswith(stdlib), "inventory outside scope")
        if event == "os.mkdir":
            need(
                os.path.normpath(os.fsdecode(args[0])) == str(output),
                "mkdir outside output",
            )
        if event == "os.remove":
            need(
                os.path.normpath(os.fsdecode(args[0]))
                in ({str(output / "completion.json")} | audits),
                "remove outside completion",
            )
        if event in ("os.rmdir", "os.rename"):
            raise ValueError("R5.59r: destructive operation outside scope")
        if event == "import":
            need(
                str(args[0]).partition(".")[0] in sys.stdlib_module_names
                and str(args[0]).partition(".")[0] not in ("ctypes", "_ctypes"),
                "nonstdlib import",
            )
        if event == "exec":
            need(
                os.path.normpath(args[0].co_filename) not in source_paths,
                "historical source execution",
            )
        need(
            event
            not in (
                "subprocess.Popen",
                "os.system",
                "os.fork",
                "os.exec",
                "os.posix_spawn",
                "socket.__new__",
                "ctypes.dlopen",
            ),
            "native/external access",
        )

    sys.addaudithook(hook)


def cli(args: list[str], b: Budget) -> tuple[Row, Path, str | None, Path | None]:
    need(bool(args), "missing command")
    if args == ["retained"]:
        return retained_profile(), OUTPUT, None, None
    if args[0] == "audit" and len(args) == 2:
        return retained_profile(), OUTPUT, args[1], AUDIT
    need(
        args[0] in ("artificial", "audit-artificial") and len(args) in (3, 5),
        "command arity",
    )
    profile = decode(b.read(Path(args[1]).absolute(), cap=65536))
    need(profile["scope"] == "artificial-saved-lineage", "artificial command required")
    if args[0] == "artificial" and len(args) == 3:
        return profile, Path(args[2]).absolute(), None, None
    need(args[0] == "audit-artificial" and len(args) == 5, "audit command arity")
    return profile, Path(args[2]).absolute(), args[3], Path(args[4]).absolute()


def main(args: list[str]) -> int:
    need(
        sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
        "use -I -S -B",
    )
    if args and args[0] == "worker":
        need(len(args) >= 4, "worker arguments")
        b = Budget(started_ns=int(args[1]), invocation_id=args[2])
        profile, output, pin, target = cli(args[3:], b)
        profile_check(profile, output, target)
        guard(profile, output, target, read_only=pin is not None)
        result = (
            run(output, profile, budget=b)
            if pin is None
            else audit(output, profile, pin, audit_path=target, budget=b)
        )
        b.check()
        print(
            json.dumps(
                dict(status=result["status"], work=b.used, scientific_work=ZERO),
                sort_keys=True,
            )
        )
        return 0
    b = Budget(started_ns=_ENTRY_NS)
    profile, output, pin, target = cli(args, b)
    profile_check(profile, output, target)
    need(not os.path.lexists(target if pin else output), "existing invocation output")
    code = 3
    try:
        b.check()
        child = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                str(HERE),
                "worker",
                str(b.started_ns),
                b.invocation_id,
                *args,
            ],
            stdin=subprocess.DEVNULL,
            timeout=(WALL_NS - (b.clock() - b.started_ns)) / 1e9,
            check=False,
        )
        if child.returncode == 0:
            b.check()
            code = 0
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    if code:
        marker = target if pin else output / "completion.json"
        if marker is not None:
            owned_cleanup(
                marker, marker if pin else output / "attempt.json", b.invocation_id
            )
    print(
        json.dumps(
            dict(dispatcher_elapsed_ns=b.clock() - b.started_ns, exit_code=code),
            sort_keys=True,
        )
    )
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        ArithmeticError,
    ) as error:
        print(error, file=sys.stderr)
        raise SystemExit(3) from None
