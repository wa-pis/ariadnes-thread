"""Bounded retained-observation adapter; qualification uses artificial archives only."""

# Start the shared dispatch clock before other imports.
# ruff: noqa: E402
from time import monotonic_ns

_ENTRY_STARTED_NS = monotonic_ns()

from dataclasses import dataclass, field
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import ModuleType
from typing import Any
from uuid import uuid4

type Row = dict[str, Any]
HERE = Path(__file__).resolve()
CAP = 4 * 1024**2
AUDIT_RESERVE = 64 * 1024
SMALL = 8192
WALL_NS = 30_000_000_000
FILES = ("attempt.json", "report.json", "receipt.json", "completion.json")
ROLES = (
    "grid_attempt",
    "grid_report",
    "grid_receipt",
    "grid_audit",
    "study_attempt",
    "study_report",
    "study_receipt",
    "study_completion",
    "study_audit",
)
SIGNS = ("positive", "negative")
RETAINED_OUTPUT = HERE.with_name("0224-retained-trace-result")
RETAINED_AUDIT = HERE.with_name("0224-retained-trace-audit.json")
STATUS = "observations-verified-attribution-unresolved"
FLAGS = dict(
    commands=None,
    live_authorized=False,
    physical_launch_authorized=False,
    physical_status="physical-join-not-established",
    spice_queries=0,
    kernel_accesses=0,
    force_evaluations=0,
    integrations=0,
    r559i_attempts=0,
    old_audit_replays=0,
    new_points=0,
    point_root_constructions=0,
    r560_attempts=0,
)
CONTRACT_PIN = "118795d87f4084528a1d4096c4f1d61c0936f0afbc927ae6c040f6ec26600dea"
METHODS = {
    "io": (
        "0206-readiness-runner.py",
        "ff1cd800a74f40f3bc91f74550c4b49205713f391d436e37360e92a9740c1a1e",
    ),
    "core": (
        "0208-seed-worksheet.py",
        "4907db44f0ef53cb657cd563a6fa27df8a138442807c703a66c1343bde4788ba",
    ),
    "oracle": (
        "0208-seed-oracle.py",
        "cf4041c69e5204f79ab6786be5e393c0dbc0977317e693587eb1a85e8265e475",
    ),
    "reader": (
        "0210-retained-readback.py",
        "a6e1b9a32f0c46c9e03974c1367a8b04d2849eca86d807907a3bcefa1f0e8920",
    ),
    "orbit": (
        "0213-phase-orbit.py",
        "ba78ca47097703cb27ed7dca8d844b9be34c61b1fee9a5668fae97db039979c3",
    ),
    "screen": (
        "0213-phase-screen.py",
        "39d59baecb394f759ef6a775ce6cca548e4828dbfef94207b47c9e048d1d0f2b",
    ),
    "interval": (
        "0219-interval.py",
        "3243ec83031b8bc873dfae47076e0bbb086640893e396b1e56c2dbcf5d865329",
    ),
    "bounds": (
        "0219-phase-bounds.py",
        "b1a2673aa5516533320febed3efddeb27edece1f3f60b775323520e71324f83e",
    ),
    "points": (
        "0219-phase-points.py",
        "a9eca487527068c8114ff00353846e39fcf6eb7212009c5046b4df0cc23af223",
    ),
    "study": (
        "0219-phase-study.py",
        "9ba27b0419a24e16209b646c8f0adb4c4ad55e938fadc5816c4944a72a01fc60",
    ),
    "archive": (
        "0220-phase-archive.py",
        "43c4c3b7fe1f82324a4833ea74a22aaed9922e8c0f9ea67fa0aa76161062dcf8",
    ),
    "anchors": (
        "0220-phase-anchors.py",
        "7fadcb3fc9de4a43aa1ce80efd30d2e6499f76ee4918519cf8783d50bca2057e",
    ),
    "trace_schema": (
        "0223-bound-trace.py",
        "e50876ce72c8e80a74d7d615b4f67f6d69ab9a259a10663b041ee56d78730091",
    ),
    "containment": (
        "0223-trace-oracle.py",
        "bb9024663cb1b6642d0417ff73236ba47fa1eb9f48b3981db89d6aaf0c547973",
    ),
    "trace": (
        "0225-bound-trace.py",
        "d382d1181c8069d7d5d1b51b8261c75f726be522b95ed08252363c5a1a45c42d",
    ),
    "checks": (
        "0225-trace-checks.py",
        "30f3fbafa1898884c4d4234bdc66369f81dab64271dcd9ec9c4c2e1841ba829a",
    ),
}
ARTIFICIAL_REFS = {
    "cf20fb7d66cb6efe54b809519d1c0ca8f3031aee83c8532de4a20e2c6f0b1cec",
    "5316e28ef1c7c27035ba9ef08c2fa26ac9d600d04ba8a06af1dc69fe6c4c5467",
}


def need(ok: object, message: str) -> None:
    if not ok:
        raise ValueError("R5.59m: " + message)


def _wire(row: Any) -> bytes:
    return (
        json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def _read(path: Path, cap: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        need(
            stat.S_ISREG(info.st_mode) and 0 <= info.st_size <= cap,
            "input type or byte cap",
        )
        raw = stream.read(cap + 1)
    need(len(raw) == info.st_size, "changed or oversized input")
    return raw


def _contract() -> Row:
    raw = _read(HERE.with_name("0224-retained-trace-contract.json"), 64 * 1024)
    need(sha256(raw).hexdigest() == CONTRACT_PIN, "contract pin")
    return json.loads(raw)


def _methods() -> dict[str, ModuleType]:
    result = {}
    for key, (name, pin) in METHODS.items():
        raw = _read(HERE.with_name(name), 64 * 1024)
        need(sha256(raw).hexdigest() == pin, key + " method pin")
        module = ModuleType("_r559m_" + key)
        module.__file__ = str(HERE.with_name(name))
        sys.modules[module.__name__] = module
        exec(compile(raw, module.__file__, "exec"), vars(module))
        result[key] = module
    return result


@dataclass(slots=True)
class Budget:
    wall_ns: int = WALL_NS
    bound_cap: int = 48
    event_cap: int = 8192
    byte_cap: int = CAP
    mass_cap: int = 12
    started_ns: int = field(default_factory=monotonic_ns)
    used: dict[str, int] = field(
        default_factory=lambda: dict(bounds=0, points=0, events=0, oracle_mass=0)
    )
    event_bytes: int = 0
    invocation_id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        for key, limit in (
            ("wall_ns", WALL_NS),
            ("bound_cap", 48),
            ("event_cap", 8192),
            ("byte_cap", CAP),
            ("mass_cap", 12),
        ):
            value = getattr(self, key)
            need(type(value) is int and 0 <= value <= limit, key + " cap")
        need(
            type(self.invocation_id) is str
            and len(self.invocation_id) == 32
            and all(c in "0123456789abcdef" for c in self.invocation_id),
            "invocation identity",
        )
        need(
            self.used == dict(bounds=0, points=0, events=0, oracle_mass=0)
            and all(type(v) is int for v in self.used.values()),
            "fresh counters",
        )

    def check(self) -> None:
        need(0 <= monotonic_ns() - self.started_ns < self.wall_ns, "shared wall cap")

    def charge(self, name: str) -> None:
        self.check()
        ceiling = dict(
            bounds=self.bound_cap, events=self.event_cap, oracle_mass=self.mass_cap
        )
        need(name in ceiling and self.used[name] < ceiling[name], name + " cap")
        self.used[name] += 1

    def emit(self, event: Row) -> None:
        self.charge("events")
        self.event_bytes += len(_wire(event))
        need(self.event_bytes < self.byte_cap - AUDIT_RESERVE, "event byte cap")


def retained_profile() -> Row:
    c = _contract()
    return dict(
        scope="retained",
        inputs={
            role: HERE.parents[3] / item["path"]
            for role, item in zip(ROLES, c["input_artifacts"], strict=True)
        },
        pins={
            role: item["sha256"]
            for role, item in zip(ROLES, c["input_artifacts"], strict=True)
        },
        reference_sha256=c["reference_sha256"],
        selected_rows=c["selected_rows"],
    )


def _profile(profile: Row, output: Path, budget: Budget) -> Row:
    budget.check()
    c = _contract()
    need(
        set(profile)
        == {"scope", "inputs", "pins", "reference_sha256", "selected_rows"},
        "profile inventory",
    )
    retained = profile["scope"] == "retained"
    need(profile["scope"] in ("retained", "artificial"), "profile scope")
    need(
        set(profile["inputs"]) == set(profile["pins"]) == set(ROLES), "nine input roles"
    )
    paths = {role: Path(profile["inputs"][role]) for role in ROLES}
    need(
        len(set(paths.values())) == 9
        and all(p.is_absolute() and not p.is_symlink() for p in paths.values()),
        "input path identity",
    )
    real = retained_profile()
    if retained:
        need(
            paths == real["inputs"]
            and profile["pins"] == real["pins"]
            and profile["reference_sha256"] == real["reference_sha256"]
            and _wire(profile["selected_rows"]) == _wire(real["selected_rows"])
            and output == RETAINED_OUTPUT,
            "frozen retained profile",
        )
    else:
        real_paths = set(real["inputs"].values())
        roots = {p.parent for p in real_paths} | {RETAINED_OUTPUT}
        need(
            output.name.startswith("r559m-artificial-")
            and profile["reference_sha256"] in ARTIFICIAL_REFS
            and not set(profile["pins"].values()) & set(real["pins"].values())
            and all(
                not any(p == q or p.is_relative_to(q) for q in roots)
                for p in (*paths.values(), output)
            ),
            "mixed artificial/retained scope",
        )
    need(not output.is_symlink(), "output symlink")
    need(len(profile["selected_rows"]) == 3, "selected row inventory")
    for proposed, expected in zip(
        profile["selected_rows"], c["selected_rows"], strict=True
    ):
        need(
            set(proposed) == set(expected)
            and all(
                type(proposed[k]) is type(expected[k]) and proposed[k] == expected[k]
                for k in (
                    "row_index",
                    "lo_deg",
                    "hi_deg",
                    "depth",
                    "action",
                    "midpoint_deg",
                )
            ),
            "fixed row/cell metadata",
        )
    return profile | dict(inputs=paths)


def _inputs(profile: Row, budget: Budget) -> tuple[Row, Row]:
    records = {}
    bytes_read = len(_read(HERE, 64 * 1024))
    bytes_read += len(
        _read(HERE.with_name("0224-retained-trace-contract.json"), 64 * 1024)
    )
    bytes_read += sum(
        len(_read(HERE.with_name(name), 64 * 1024)) for name, _ in METHODS.values()
    )
    for role in ROLES:
        budget.check()
        raw = _read(profile["inputs"][role], max(0, budget.byte_cap - bytes_read))
        need(sha256(raw).hexdigest() == profile["pins"][role], role + " source pin")
        row = json.loads(raw)
        canonical = (
            json.dumps(row, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode()
        need(raw in (_wire(row), canonical), role + " canonical record")
        records[role] = row
        bytes_read += len(raw)
    need(bytes_read <= budget.byte_cap, "source inventory byte cap")
    pins = profile["pins"]
    ga, gr, gc, gu = (records[k] for k in ROLES[:4])
    sa, sr, sc, se, su = (records[k] for k in ROLES[4:])
    mode = profile["scope"]
    need(
        all(
            row["mode"] == mode and row["run_id"] == ga["run_id"]
            for row in (ga, gr, gc)
        ),
        "grid lineage",
    )
    need(
        gr["attempt_sha256"] == gc["attempt_sha256"] == pins["grid_attempt"]
        and gc["report_sha256"] == pins["grid_report"],
        "grid receipt chain",
    )
    grid_pins = {
        name: pins["grid_" + name.split(".")[0]]
        for name in ("attempt.json", "report.json", "receipt.json")
    }
    need(
        gu["source_pins"] == grid_pins
        and gu["original_invocation_completed"] is False
        and gu["saved_grid_verified"] is True
        and gu["candidate_id"]
        == ("d0001-t0035" if mode == "retained" else "artificial-moon-mars"),
        "grid audit identity",
    )
    need(
        all(row["source_pins"] == ga["source_pins"] for row in (gr, gc))
        and all(row["source_sha256"] == ga["source_sha256"] for row in (gr, gc, gu)),
        "grid source/method identity",
    )
    ref = gr["reference"]
    need(
        sha256(_wire(ref)).hexdigest() == profile["reference_sha256"]
        and ref["normalized"]["scope"] == mode
        and ref["normalized"]["candidate_id"] == gu["candidate_id"],
        "reference identity",
    )
    source_pins = grid_pins | {"audit.json": pins["grid_audit"]}
    for row in (sa, sr, sc, su):
        need(
            row["scope"] == mode
            and row["run_id"] == sa["run_id"]
            and row["source_pins"] == source_pins
            and row["methods_sha256"] == _contract()["historical_method_identity"],
            "study source/method identity",
        )
    need(
        sr["attempt_sha256"] == sc["attempt_sha256"] == pins["study_attempt"]
        and sc["report_sha256"] == pins["study_report"]
        and se["receipt_sha256"] == pins["study_receipt"]
        and se["run_id"] == sa["run_id"],
        "study receipt chain",
    )
    need(
        sr["status"] == su["status"] == se["proof"]["status"] == "inconclusive"
        and sr["witness"] is None
        and sr["commands"] is None
        and len(sr["rows"]) == len(su["rows"]) == 126
        and _wire(sr["rows"]) == _wire(su["rows"]),
        "saved study identity",
    )
    need(se["proof"] == su["independent_readback"], "old audit binding")
    selected = []
    for spec in profile["selected_rows"]:
        budget.check()
        row = sr["rows"][spec["row_index"]]
        need(sha256(_wire(row)).hexdigest() == spec["row_sha256"], "selected row pin")
        need(
            all(row[k] == spec[k] for k in ("lo_deg", "hi_deg", "depth", "action"))
            and row["point"]["phase_deg"] == spec["midpoint_deg"],
            "selected row operands",
        )
        need(
            sha256(_wire(row["point"])).hexdigest() == spec["point_sha256"],
            "saved point pin",
        )
        need(
            set(row["bounds"]) == set(SIGNS)
            and all(
                sha256(_wire(row["bounds"][s])).hexdigest()
                == spec["saved_default_bounds_sha256"][s]
                for s in SIGNS
            ),
            "saved historical bound pin",
        )
        selected.append(row)
    return dict(reference=ref, selected=selected), dict(
        source_bytes=bytes_read, source_pins=dict(pins)
    )


def _head(profile: Row, inventory: Row) -> Row:
    pins = {key: pin for key, (_, pin) in METHODS.items()}
    pins["runner"] = sha256(_read(HERE, 64 * 1024)).hexdigest()
    return FLAGS | dict(
        scope=profile["scope"],
        stage="R5.59m" if profile["scope"] == "artificial" else "R5.59n",
        contract_sha256=CONTRACT_PIN,
        method_sha256=pins,
        reference_sha256=profile["reference_sha256"],
        selected_rows=profile["selected_rows"],
        **inventory,
    )


def _validate(
    report: Row,
    data: Row,
    profile: Row,
    methods: dict[str, ModuleType],
    budget: Budget,
    cache: Row | None = None,
) -> Row:
    budget.check()
    cache = (
        cache
        if cache is not None
        else methods["checks"].prepare_points(
            data["reference"],
            [r["point"] for r in data["selected"]],
            methods,
            reference_sha256=profile["reference_sha256"],
            retained=profile["scope"] == "retained",
            charge_mass=lambda: budget.charge("oracle_mass"),
        )
    )
    expected = [
        (spec, kind, sign, ind)
        for spec in profile["selected_rows"]
        for kind in ("cell", "singleton")
        for sign in SIGNS
        for ind in (False, True)
    ]
    need(len(report["rows"]) == 24, "trace matrix inventory")
    events = 0
    samples = 0
    for row, (spec, kind, sign, ind) in zip(report["rows"], expected, strict=True):
        budget.check()
        lo, hi = (
            (spec["lo_deg"], spec["hi_deg"])
            if kind == "cell"
            else (spec["midpoint_deg"],) * 2
        )
        need(
            (
                row["row_index"],
                row["domain"],
                row["lo_deg"],
                row["hi_deg"],
                row["sign"],
                row["independent"],
            )
            == (spec["row_index"], kind, lo, hi, sign, ind)
            and type(row["independent"]) is bool,
            "matrix metadata",
        )
        trace = row["trace"]
        need(
            tuple(trace[k] for k in ("lo", "hi", "sign", "independent"))
            == (lo, hi, sign, ind),
            "trace metadata",
        )
        need(_wire(trace["result"]) == _wire(row["control"]), "traced/control parity")
        methods["trace_schema"].verify_trace(trace, row["control"])
        saved = data["selected"][profile["selected_rows"].index(spec)]
        if kind == "cell" and not ind:
            need(
                _wire(row["control"]) == _wire(saved["bounds"][sign]),
                "historical bound parity",
            )
        check = methods["checks"].verify_containment(
            data["reference"], saved["point"], trace, sign, methods, cache
        )
        need(
            _wire(check) == _wire(row["containment"])
            and check["containment_checks"] == 16,
            "containment readback",
        )
        events += len(trace["events"])
        samples += 1
    summary = methods["checks"].summarize(report["rows"])
    need(_wire(summary) == _wire(report["summary"]), "width summary readback")
    need(
        report["status"] == STATUS
        and report["work"] == dict(bounds=48, points=0, events=events, oracle_mass=12)
        and 0 < events <= 8192
        and samples == 24,
        "work counters",
    )
    return dict(
        status=STATUS,
        rows=24,
        sampled_containments=24,
        historical_parity=6,
        event_count=events,
        new_bounds=0,
        new_points=0,
        oracle_mass_calls=6,
        summary_sha256=sha256(_wire(summary)).hexdigest(),
    )


def _saved(
    output: Path,
    data: Row,
    profile: Row,
    head: Row,
    methods: dict[str, ModuleType],
    budget: Budget,
    pin: str,
    cache: Row | None = None,
) -> Row:
    need({p.name for p in output.iterdir()} == set(FILES), "evidence inventory")
    rows = []
    pins = []
    total = 0
    for name in FILES:
        budget.check()
        raw = _read(output / name, max(0, budget.byte_cap - AUDIT_RESERVE - total))
        value = json.loads(raw)
        need(_wire(value) == raw, "noncanonical new evidence")
        rows.append(value)
        pins.append(sha256(raw).hexdigest())
        total += len(raw)
    need(total <= budget.byte_cap - AUDIT_RESERVE, "combined evidence byte cap")
    a, r, c, e = rows
    run_id = a.get("invocation_id")
    need(
        type(run_id) is str
        and len(run_id) == 32
        and all(ch in "0123456789abcdef" for ch in run_id)
        and all(row.get("invocation_id") == run_id for row in (r, c, e)),
        "saved invocation identity",
    )
    need(
        all(_wire({key: row[key] for key in head}) == _wire(head) for row in (a, r, c)),
        "source identity readback",
    )
    need(
        pins[3] == pin
        and r["attempt_sha256"] == c["attempt_sha256"] == pins[0]
        and c["report_sha256"] == pins[1]
        and e["receipt_sha256"] == pins[2],
        "new receipt chain",
    )
    need(
        type(e["elapsed_ns"]) is int
        and type(c["elapsed_ns"]) is int
        and 0 <= c["elapsed_ns"] <= e["elapsed_ns"] < a["wall_ns"] <= WALL_NS,
        "saved clock",
    )
    proof = _validate(r, data, profile, methods, budget, cache)
    need(_wire(e["proof"]) == _wire(proof), "saved proof")
    budget.check()
    return r | dict(independent_readback=proof)


def run(output: Path, profile: Row, *, budget: Budget | None = None) -> Row:
    """Execute only the fixed observation matrix; callers supply an authenticated scope profile."""
    b = budget or Budget()
    b.check()
    dest = Path(output).absolute()
    p = _profile(profile, dest, b)
    need(not os.path.lexists(dest), "existing output")
    need(b.byte_cap > AUDIT_RESERVE + 3 * SMALL, "output byte cap")
    methods = _methods()
    io = methods["io"]
    data, inventory = _inputs(p, b)
    head = _head(p, inventory) | dict(invocation_id=b.invocation_id)
    dest.mkdir(mode=0o700)
    io._sync(dest.parent)
    a_pin = io._put(dest / FILES[0], head | dict(wall_ns=b.wall_ns), SMALL)
    cache = methods["checks"].prepare_points(
        data["reference"],
        [row["point"] for row in data["selected"]],
        methods,
        reference_sha256=p["reference_sha256"],
        retained=p["scope"] == "retained",
        charge_mass=lambda: b.charge("oracle_mass"),
    )
    rows = []
    for spec, saved in zip(p["selected_rows"], data["selected"], strict=True):
        for kind in ("cell", "singleton"):
            lo, hi = map(
                Fraction,
                (spec["lo_deg"], spec["hi_deg"])
                if kind == "cell"
                else (spec["midpoint_deg"],) * 2,
            )
            for sign in SIGNS:
                for ind in (False, True):
                    b.charge("bounds")
                    control = methods["bounds"].bounds(
                        data["reference"],
                        lo,
                        hi,
                        sign,
                        methods["interval"],
                        independent=ind,
                    )
                    b.charge("bounds")
                    trace = methods["trace"].trace_bound(
                        data["reference"],
                        lo,
                        hi,
                        sign,
                        methods,
                        independent=ind,
                        check=b.check,
                        emit=b.emit,
                        reference_sha256=p["reference_sha256"],
                        retained=p["scope"] == "retained",
                    )
                    need(
                        _wire(trace["result"]) == _wire(control),
                        "traced/control parity",
                    )
                    if kind == "cell" and not ind:
                        need(
                            _wire(control) == _wire(saved["bounds"][sign]),
                            "historical bound parity",
                        )
                    containment = methods["checks"].verify_containment(
                        data["reference"], saved["point"], trace, sign, methods, cache
                    )
                    need(
                        containment["containment_checks"] == 16,
                        "incomplete point containment",
                    )
                    rows.append(
                        dict(
                            row_index=spec["row_index"],
                            domain=kind,
                            lo_deg=str(lo),
                            hi_deg=str(hi),
                            sign=sign,
                            independent=ind,
                            trace=trace,
                            control=control,
                            containment=containment,
                        )
                    )
    # Prepare fresh readback arithmetic before recording observed counters.
    readback_cache = methods["checks"].prepare_points(
        data["reference"],
        [row["point"] for row in data["selected"]],
        methods,
        reference_sha256=p["reference_sha256"],
        retained=p["scope"] == "retained",
        charge_mass=lambda: b.charge("oracle_mass"),
    )
    report = head | dict(
        status=STATUS,
        rows=rows,
        summary=methods["checks"].summarize(rows),
        work=dict(b.used),
        attempt_sha256=a_pin,
    )
    r_pin = io._put(dest / FILES[1], report, b.byte_cap - AUDIT_RESERVE - 3 * SMALL)
    c_pin = io._put(
        dest / FILES[2],
        head
        | dict(
            attempt_sha256=a_pin,
            report_sha256=r_pin,
            elapsed_ns=monotonic_ns() - b.started_ns,
        ),
        SMALL,
    )
    proof = dict(
        status=STATUS,
        rows=24,
        sampled_containments=24,
        historical_parity=6,
        event_count=b.used["events"],
        new_bounds=0,
        new_points=0,
        oracle_mass_calls=6,
        summary_sha256=sha256(_wire(report["summary"])).hexdigest(),
    )
    certified = False
    try:
        pin = io._put(
            dest / FILES[3],
            dict(
                receipt_sha256=c_pin,
                proof=proof,
                invocation_id=b.invocation_id,
                elapsed_ns=monotonic_ns() - b.started_ns,
            ),
            SMALL,
        )
        result = _saved(dest, data, p, head, methods, b, pin, readback_cache)
        need(b.used == report["work"], "final work counters")
        b.check()
        certified = True
        return result
    finally:
        if not certified and os.path.lexists(dest / FILES[3]):
            (dest / FILES[3]).unlink()
            io._sync(dest)


def audit(
    output: Path,
    profile: Row,
    completion_sha256: str,
    *,
    audit_path: Path | None = None,
    budget: Budget | None = None,
) -> Row:
    """Verify saved observations with no new bounds, traces, point or conic constructors."""
    b = budget or Budget(mass_cap=6)
    need(b.mass_cap <= 6, "audit mass cap")
    dest = Path(output).absolute()
    p = _profile(profile, dest, b)
    methods = _methods()
    data, inventory = _inputs(p, b)
    result = _saved(dest, data, p, _head(p, inventory), methods, b, completion_sha256)
    need(
        b.used["bounds"] == b.used["points"] == b.used["events"] == 0
        and b.used["oracle_mass"] == 6,
        "audit work counters",
    )
    if audit_path is not None:
        target = Path(audit_path).absolute()
        need(p["scope"] != "retained" or target == RETAINED_AUDIT, "fixed audit output")
        need(
            not target.is_symlink()
            and not target.exists()
            and target.parent == dest.parent,
            "audit output scope",
        )
        certified = False
        try:
            methods["io"]._put(
                target,
                dict(
                    completion_sha256=completion_sha256,
                    invocation_id=b.invocation_id,
                    proof=result["independent_readback"],
                    work=b.used,
                    elapsed_ns=monotonic_ns() - b.started_ns,
                ),
                AUDIT_RESERVE,
            )
            need(
                sum((dest / name).stat().st_size for name in FILES)
                + target.stat().st_size
                <= b.byte_cap,
                "combined byte cap",
            )
            b.check()
            certified = True
        finally:
            if not certified and os.path.lexists(target):
                try:
                    owner = json.loads(_read(target, AUDIT_RESERVE))
                    if owner.get("invocation_id") == b.invocation_id:
                        target.unlink()
                        methods["io"]._sync(target.parent)
                except (OSError, ValueError, TypeError):
                    pass
    b.check()
    return result


def _guard(
    profile: Row, output: Path, audit_path: Path | None, *, read_only: bool
) -> None:
    scripts = {str(HERE), str(HERE.with_name("0224-retained-trace-contract.json"))}
    scripts |= {str(HERE.with_name(name)) for name, _ in METHODS.values()}
    inputs = {str(path) for path in profile["inputs"].values()}
    outputs = {str(output / name) for name in FILES}
    audits = {str(audit_path)} if audit_path is not None else set()
    dirs = {str(output), str(output.parent), *(str(Path(p).parent) for p in inputs)}
    stdlib = (
        str(
            Path(sys.base_prefix)
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
        )
        + os.sep
    )

    def scope(event: str, args: tuple[Any, ...]) -> None:
        if event == "open" and not isinstance(args[0], int):
            path = os.path.normpath(os.fsdecode(args[0]))
            write = int(args[2]) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            need(
                path in outputs
                and (not write or not read_only)
                or path in audits
                or not write
                and (
                    path in scripts | inputs | dirs
                    or path.startswith(stdlib)
                    and path.endswith((".py", ".pyc", ".so", ".dylib"))
                ),
                "file outside diagnostic scope",
            )
        if event in {"os.scandir", "os.listdir"}:
            path = os.path.normpath(os.fsdecode(args[0]))
            need(
                path in dirs or path.startswith(stdlib),
                "inventory outside diagnostic scope",
            )
        if event == "import":
            root = str(args[0]).partition(".")[0]
            need(
                root in sys.stdlib_module_names and root not in {"ctypes", "_ctypes"},
                "scientific import",
            )
        need(
            event
            not in {
                "subprocess.Popen",
                "os.system",
                "os.fork",
                "os.exec",
                "os.posix_spawn",
                "socket.__new__",
                "ctypes.dlopen",
            },
            "native or external access",
        )

    sys.addaudithook(scope)


def _cli_profile(args: list[str]) -> tuple[Row, Path, str | None, Path | None]:
    need(bool(args), "missing command")
    if args[0] == "retained" and len(args) == 1:
        return retained_profile(), RETAINED_OUTPUT, None, None
    if args[0] == "audit" and len(args) == 2:
        return retained_profile(), RETAINED_OUTPUT, args[1], RETAINED_AUDIT
    need(
        args[0] in ("artificial", "audit-artificial") and len(args) in (3, 5),
        "usage: artificial PROFILE OUTPUT | audit-artificial PROFILE OUTPUT PIN AUDIT_OUTPUT",
    )
    raw = _read(Path(args[1]).absolute(), 64 * 1024)
    profile = json.loads(raw)
    need(profile["scope"] == "artificial", "artificial profile required")
    profile["inputs"] = {k: Path(v) for k, v in profile["inputs"].items()}
    if args[0] == "artificial" and len(args) == 3:
        return profile, Path(args[2]).absolute(), None, None
    need(args[0] == "audit-artificial" and len(args) == 5, "artificial command arity")
    return profile, Path(args[2]).absolute(), args[3], Path(args[4]).absolute()


def _worker(args: list[str], started: int, run_id: str) -> int:
    need(
        sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
        "use -I -S -B",
    )
    budget = Budget(
        started_ns=started,
        invocation_id=run_id,
        mass_cap=6 if args[0] in ("audit", "audit-artificial") else 12,
    )
    profile, output, pin, audit_path = _cli_profile(args)
    profile = _profile(profile, output, budget)
    _guard(profile, output, audit_path, read_only=pin is not None)
    result = (
        run(output, profile, budget=budget)
        if pin is None
        else audit(output, profile, pin, audit_path=audit_path, budget=budget)
    )
    budget.check()
    print(
        json.dumps(
            dict(
                status=result["status"],
                work=budget.used,
                proof=result["independent_readback"],
            ),
            sort_keys=True,
        )
    )
    return 0


def main(args: list[str]) -> int:
    if args and args[0] == "worker":
        need(len(args) >= 4, "worker arguments")
        return _worker(args[3:], int(args[1]), args[2])
    need(
        sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
        "use -I -S -B",
    )
    started = _ENTRY_STARTED_NS
    profile, output, pin, audit_path = _cli_profile(args)
    _profile(profile, output, Budget(started_ns=started))
    target = audit_path if pin is not None else output
    need(
        target is not None and not os.path.lexists(target), "existing invocation output"
    )
    code = 3
    run_id = uuid4().hex
    try:
        elapsed = monotonic_ns() - started
        need(0 <= elapsed < WALL_NS, "dispatcher deadline")
        child = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                str(HERE),
                "worker",
                str(started),
                run_id,
                *args,
            ],
            stdin=subprocess.DEVNULL,
            timeout=(WALL_NS - elapsed) / 1e9,
            check=False,
        )
        if child.returncode == 0 and monotonic_ns() - started < WALL_NS:
            code = 0
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    if code != 0:
        marker = audit_path if pin is not None else output / "completion.json"
        if marker is not None and os.path.lexists(marker):
            owner = marker if pin is not None else output / "attempt.json"
            try:
                identity = json.loads(_read(owner, SMALL))
                if identity.get("invocation_id") == run_id:
                    marker.unlink()
                    _methods()["io"]._sync(marker.parent)
            except (OSError, ValueError, TypeError):
                pass
    print(
        json.dumps(
            dict(dispatcher_elapsed_ns=monotonic_ns() - started, exit_code=code),
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
