"""Independently verify saved lineage using endpoint arithmetic and no scientific replay."""

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from hashlib import sha256
import json
from math import gcd
import re
from typing import Any

type Record = dict[str, Any]
type Check = Callable[[], None]
type Charge = Callable[[str, int], None]

_STAGES = ("bounds", "_ellipse", "_reverse", "_unit", "_cross", "_norm2",
           "_mass_exclusion", "_clearance", "_binary64")
_SELECTION = (
    {"row_index": 62, "lo_deg": "150", "hi_deg": "4801/32", "midpoint_deg": "9601/64"},
    {"row_index": 94, "lo_deg": "151", "hi_deg": "4833/32", "midpoint_deg": "9665/64"},
    {"row_index": 125, "lo_deg": "4863/32", "hi_deg": "152", "midpoint_deg": "9727/64"},
)
_CHECKPOINTS = {
    "_ellipse": {"anomaly": "rad", "radius": "m", "return[0][0]": "m", "return[0][1]": "m",
                 "return[0][2]": "m", "return[1][0]": "m/s", "return[1][1]": "m/s", "return[1][2]": "m/s"},
    "_mass_exclusion": {"coast": "kg", "durations[0]": "s", "durations[1]": "s", "final": "kg"},
    "_reverse": {"radius": "m", "return[0]": "m/s", "return[1]": "m/s", "return[2]": "m/s", "root": "m2/s"},
    "bounds": {"speed": "m/s"},
}
_ALIASES = [
    {"source": "_ellipse.return.return[0][i]", "targets": ["_reverse.call.r[i]", "_reverse.return.r[i]", "bounds.return.r[i]"], "units": "m"},
    {"source": "_ellipse.return.return[1][i]", "targets": ["bounds.return.orbital[i]"], "units": "m/s"},
    {"source": "_ellipse.return.return[2]", "targets": ["_reverse.call.mu", "_reverse.return.mu", "bounds.return.mu"], "units": "m3/s2"},
    {"source": "_ellipse.call.anomaly", "targets": ["_ellipse.return.anomaly", "bounds.return.anomaly"], "units": "rad"},
    {"source": "_reverse.return.return[i]", "targets": ["bounds.return.future[i]"], "units": "m/s"},
    {"source": "bounds.return.speed", "targets": ["_mass_exclusion.call.arrival", "_mass_exclusion.return.arrival"], "units": "m/s"},
]
_ROLES = [
    {"role": "impulse-squared", "parent_path": "bounds", "direct_norm2_ordinal": 0, "operand_units": "m/s", "result_units": "m2/s2"},
    {"role": "radius-squared", "parent_path": "bounds/_reverse[0]", "direct_norm2_ordinal": 1, "operand_units": "m", "result_units": "m2"},
    {"role": "angular-momentum-squared", "parent_path": "bounds/_reverse[0]", "direct_norm2_ordinal": 4, "operand_units": "m2/s", "result_units": "m4/s2"},
]
_RISKS = [
    "Common-anomaly geometry reuses phase-dependent operands.",
    "Normalization and signed-root reconstruction reuse dependent vectors.",
    "Coast/final-mass expressions share departure and arrival operands.",
]
_LIMIT = "No contribution to final width or dominant cause is established."
_LIMITATIONS = [
    "cell width minus singleton width is not dependency overestimation or a rounding-error bound",
    "one midpoint cannot determine within-cell extrema or separate phase variation, dependency loss and rounding",
    "ellipse radius and reverse radius are distinct rounded expressions; no identity/contraction without a separate proof",
    "local matched-operand response does not quantify contribution to final arrival width",
    "missing operation-level snapshots/common-phase correlation/covariance/extremizer witnesses remain missing",
]
_CONTEXT_ASSUMPTION = (
    "Decimal96 context equality follows conditionally from pinned source/provenance, not a runtime context snapshot; "
    "do not report it as observed data. If this assumption cannot be justified, reject local-effect admission."
)
_CAPS = {"endpoint_text_chars": 1024, "decimal_significand_digits": 256,
         "absolute_decimal_exponent": 512, "rational_component_bits": 4096,
         "input_event_records": 8192, "counted_event_visits_per_process": 32768,
         "descriptor_records": 1024, "alias_links": 768, "norm_pair_slots": 36}
_METHOD_PINS = {
    "bounds": "b1a2673aa5516533320febed3efddeb27edece1f3f60b775323520e71324f83e",
    "interval": "3243ec83031b8bc873dfae47076e0bbb086640893e396b1e56c2dbcf5d865329",
    "trace_schema": "e50876ce72c8e80a74d7d615b4f67f6d69ab9a259a10663b041ee56d78730091",
    "trace": "d382d1181c8069d7d5d1b51b8261c75f726be522b95ed08252363c5a1a45c42d",
    "checks": "30f3fbafa1898884c4d4234bdc66369f81dab64271dcd9ec9c4c2e1841ba829a",
    "runner": "395d711620fb0e6e4ea092001adb52a769052af8d527300902653df4b6a4d6d7",
}
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:E[+-]?[0-9]+)?\Z")
_INDEPENDENT_ARGUMENT = frozenset({"bounds", "_ellipse", "_reverse", "_unit", "_norm2", "_mass_exclusion", "_clearance"})
_COMPONENT_LIMIT = (1 << 4096) - 1


def _require(value: object, message: str) -> None:
    if not value:
        raise ValueError("saved lineage verifier: " + message)


def _record(value: Any, label: str) -> Record:
    _require(type(value) is dict and all(type(key) is str for key in value), label + " record")
    return value


def _list(value: Any, label: str) -> list[Any]:
    _require(type(value) is list, label + " list")
    return value


def _json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _pointer(row: int, event: int, name: str) -> str:
    return f"/report/rows/{row}/trace/events/{event}/fields/" + name.replace("~", "~0").replace("/", "~1")


def _mandatory(stage: str) -> set[str]:
    scalars = {
        "bounds": "anomaly mu speed",
        "_ellipse": "anomaly mu peri e sin_i cos_i sin_o cos_o sin_u cos_u sin_nu cos_nu a p h radius u t return[2]",
        "_reverse": "mu radius linear constant discriminant_sq disc root",
        "_mass_exclusion": "departure arrival init coast final rate durations[0] durations[1] observed_duration_binary64[0] observed_duration_binary64[1]",
        "_clearance": "mu surface radius radial minimum return[0] return[1] return[2]",
        "_norm2": "return", "_cross": "", "_unit": "", "_binary64": "",
    }
    vectors = {
        "bounds": "r orbital future", "_ellipse": "node normal onto_plane radial_hat transverse_hat return[0] return[1]",
        "_reverse": "r given v_inf r_hat direction normal signed_h e_inf return",
        "_mass_exclusion": "", "_clearance": "r v r_hat", "_norm2": "v", "_unit": "v return",
        "_cross": "a b return", "_binary64": "",
    }
    return set(scalars[stage].split()) | {f"{name}[{component}]" for name in vectors[stage].split() for component in range(3)}


@dataclass(frozen=True, slots=True)
class _Endpoint:
    text: tuple[str, str]
    lower: Fraction
    upper: Fraction


@dataclass(slots=True)
class _Frame:
    number: int
    stage: str
    path: str
    entry_index: int
    entry: dict[str, _Endpoint]
    entry_scalars: Record
    exit_index: int = -1
    exit_kind: str = ""
    exit: dict[str, _Endpoint] = field(default_factory=dict)
    exit_scalars: Record = field(default_factory=dict)
    children: list["_Frame"] = field(default_factory=list)


@dataclass(slots=True)
class _Tree:
    frames: dict[str, _Frame]
    early: bool


class _Audit:
    def __init__(self, contract: Record, check: Check, charge: Charge) -> None:
        self.contract: Record = contract
        self.check: Check = check
        self.charge: Charge = charge
        self.used: dict[str, int] = {"event_visits": 0, "descriptors": 0, "aliases": 0, "norm_pairs": 0}
        self.numbers: dict[str, Fraction] = {}

    def tick(self, kind: str) -> None:
        self.check()
        limit = {"event_visits": 32768, "descriptors": 1024, "aliases": 768, "norm_pairs": 36}[kind]
        _require(self.used[kind] < limit, kind + " exhausted")
        self.charge(kind, 1)
        self.used[kind] += 1

    def bounded(self, value: Fraction) -> Fraction:
        self.check()
        _require(value.numerator.bit_length() <= 4096 and value.denominator.bit_length() <= 4096,
                 "rational component bit cap")
        return value

    def product(self, left: int, right: int) -> int:
        self.check()
        _require(right == 0 or abs(left) <= _COMPONENT_LIMIT // abs(right),
                 "rational product bit cap before arithmetic")
        return left * right

    def subtract(self, left: Fraction, right: Fraction) -> Fraction:
        self.bounded(left)
        self.bounded(right)
        if left == right:
            return Fraction(0)
        common = gcd(left.denominator, right.denominator)
        multiplier = right.denominator // common
        denominator = self.product(left.denominator, multiplier)
        first = self.product(left.numerator, multiplier)
        second = self.product(right.numerator, left.denominator // common)
        if (first < 0) != (second < 0):
            _require(abs(first) <= _COMPONENT_LIMIT - abs(second),
                     "rational subtraction bit cap before arithmetic")
        return self.bounded(Fraction(first - second, denominator))

    def divide(self, left: Fraction, right: Fraction) -> Fraction:
        self.bounded(left)
        self.bounded(right)
        _require(right != 0, "undefined rational ratio")
        first = gcd(left.numerator, right.numerator)
        second = gcd(left.denominator, right.denominator)
        numerator = self.product(left.numerator // first, right.denominator // second)
        denominator = self.product(left.denominator // second, right.numerator // first)
        return self.bounded(Fraction(numerator, denominator))

    def number(self, value: Any) -> Fraction:
        self.check()
        _require(type(value) is str and 0 < len(value) <= 1024 and _DECIMAL.fullmatch(value) is not None,
                 "finite canonical decimal text")
        if value in self.numbers:
            return self.numbers[value]
        mantissa, _, exponent = value.partition("E")
        _require(len(mantissa.replace("-", "").replace(".", "")) <= 256, "decimal significand cap")
        _require(not exponent or len(exponent.lstrip("+-")) <= 4, "decimal exponent cap")
        _require(not exponent or abs(int(exponent)) <= 512, "decimal exponent cap")
        try:
            parsed = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("saved lineage verifier: invalid decimal") from error
        _require(parsed.is_finite() and str(parsed) == value and abs(parsed.as_tuple().exponent) <= 512,
                 "finite canonical decimal or exponent")
        result = self.bounded(Fraction(parsed))
        self.numbers[value] = result
        return result

    def ranges(self, raw: Any) -> dict[str, _Endpoint]:
        result: dict[str, _Endpoint] = {}
        for name, value in _record(raw, "event fields").items():
            self.check()
            _require(0 < len(name) <= 256, "field name")
            sides = _record(value, "interval endpoints")
            _require(set(sides) == {"lo", "hi"}, "endpoint inventory")
            lower, upper = self.number(sides["lo"]), self.number(sides["hi"])
            _require(lower <= upper, "endpoint order")
            result[name] = _Endpoint((sides["lo"], sides["hi"]), lower, upper)
        return result

    def scalars(self, raw: Any) -> Record:
        values = _record(raw, "event scalars")
        for key, value in values.items():
            _require(0 < len(key) <= 256 and (value is None or type(value) in (str, bool, int)), "scalar type")
            if type(value) is str:
                _require(len(value) <= 4096, "scalar text cap")
            if type(value) is int:
                _require(value.bit_length() <= 4096, "scalar integer cap")
        return values

    def tree(self, trace: Record, control: Record) -> _Tree:
        content = {key: value for key, value in trace.items() if key != "seal"}
        _require(trace.get("seal") == sha256(_json(content)[:-1]).hexdigest(), "trace seal")
        result = _record(trace.get("result"), "trace result")
        _require(_json(result) == _json(control), "traced/control equality")
        events = _list(trace.get("events"), "trace events")
        _require(0 < len(events) <= 8192 and self.used["event_visits"] + len(events) <= 8192, "input event cap")
        early = "detail" in result
        _require(trace.get("status") == ("early-failure" if early else "complete"), "trace completion label")
        if early:
            _require(type(result["detail"]) is str and 0 < len(result["detail"]) <= 4096, "early exit reason")
        frames: dict[str, _Frame] = {}
        by_number: dict[int, _Frame] = {}
        active: list[_Frame] = []
        counts = {stage: {"calls": 0, "returns": 0, "errors": 0} for stage in _STAGES}
        for ordinal, raw in enumerate(events):
            self.tick("event_visits")
            event = _record(raw, "event")
            _require(set(event) == {"index", "call", "parent", "stage", "event", "fields", "scalars"}, "event inventory")
            stage, kind = event["stage"], event["event"]
            _require(type(event["index"]) is int and event["index"] == ordinal
                     and type(event["call"]) is int and event["call"] >= 0
                     and stage in _STAGES and kind in ("call", "return", "error"), "event labels")
            parent = event["parent"]
            _require(parent is None or type(parent) is int and parent >= 0, "event parent type")
            fields, scalars = self.ranges(event["fields"]), self.scalars(event["scalars"])
            if stage in _INDEPENDENT_ARGUMENT:
                _require(type(scalars.get("independent")) is bool
                         and scalars["independent"] is trace["independent"], "local arithmetic path argument")
            if stage == "_reverse":
                _require(scalars.get("sign") == trace["sign"], "local signed-root argument")
            if kind == "call":
                _require(event["call"] == len(by_number), "call numbering")
                if active:
                    caller = active[-1]
                    _require(parent == caller.number, "call parent")
                    occurrence = sum(child.stage == stage for child in caller.children)
                    path = caller.path + f"/{stage}[{occurrence}]"
                else:
                    _require(not by_number and parent is None and stage == "bounds", "unique root call")
                    path = "bounds"
                frame = _Frame(event["call"], stage, path, ordinal, fields, scalars)
                if active:
                    active[-1].children.append(frame)
                frames[path] = by_number[frame.number] = frame
                active.append(frame)
                counts[stage]["calls"] += 1
            else:
                _require(bool(active), "orphan return")
                frame = active.pop()
                _require(frame.number == event["call"] and frame.stage == stage
                         and parent == (active[-1].number if active else None), "unpaired return")
                frame.exit_index, frame.exit_kind = ordinal, kind
                frame.exit, frame.exit_scalars = fields, scalars
                _require(all(name in fields and fields[name].text == value.text
                             for name, value in frame.entry.items()), "changed saved argument")
                counts[stage]["returns" if kind == "return" else "errors"] += 1
        _require(not active and all(frame.exit_index >= 0 for frame in frames.values()), "incomplete call tree")
        _require(len(frames) > 0 and frames["bounds"].exit_kind == "return", "bound result not returned")
        _require(any(frame.exit_kind == "error" for frame in frames.values()) is early, "unjustified early exit")
        expected_inventory = {stage: values | {"status": "error" if values["errors"] else
                              "complete" if values["returns"] else "not-reached"} for stage, values in counts.items()}
        _require(_json(trace.get("stages")) == _json(expected_inventory), "stage inventory")
        for frame in frames.values():
            self.check()
            self.children(frame, result, early)
            if frame.exit_kind == "return" and not (early and frame.stage == "bounds"):
                _require(_mandatory(frame.stage) <= frame.exit.keys(), "missing completed source field " + frame.path)
        root = frames["bounds"]
        _require(all(type(root.entry_scalars.get(key)) is type(trace.get(key))
                     and root.entry_scalars.get(key) == trace.get(key)
                     for key in ("lo", "hi", "sign", "independent")), "trace input links")
        flattened: Record = {}
        self.flatten(result, "return", flattened)
        _require(_json({key: value for key, value in root.exit_scalars.items() if key.startswith("return.")})
                 == _json(flattened), "returned result links")
        return _Tree(frames, early)

    def flatten(self, value: Any, path: str, output: Record) -> None:
        self.check()
        if type(value) is dict:
            for name, part in value.items():
                _require(type(name) is str and len(name) <= 256, "result field name")
                self.flatten(part, path + "." + name, output)
        elif type(value) is list:
            for index, part in enumerate(value):
                self.flatten(part, f"{path}[{index}]", output)
        else:
            _require(value is None or type(value) in (str, int, bool), "result scalar type")
            output[path] = value

    def children(self, frame: _Frame, result: Record, early: bool) -> None:
        expected: dict[str, list[str]] = {
            "_ellipse": ["_cross", "_cross"], "_unit": ["_norm2"],
            "_norm2": [], "_cross": [], "_binary64": [],
            "_reverse": ["_unit", "_unit", "_cross", "_norm2", "_norm2", "_cross",
                         "_norm2", "_norm2", "_unit", "_cross", "_cross", "_norm2"],
            "_mass_exclusion": ["_binary64", "_binary64"],
            "bounds": ["_ellipse", "_reverse", "_norm2", "_mass_exclusion"],
            "_clearance": ["_norm2", "_unit"],
        }
        sequence = expected[frame.stage]
        if frame.stage == "bounds" and result.get("reason") != "mass":
            sequence += ["_clearance"]
        if frame.stage == "_clearance":
            radial = frame.exit.get("radial")
            if radial is not None and radial.lower < 0:
                sequence += ["_cross", "_cross", "_norm2", "_norm2"]
        observed = [child.stage for child in frame.children]
        truncated = frame.exit_kind == "error" or frame.stage == "bounds" and early
        _require(observed == sequence or truncated and observed == sequence[:len(observed)],
                 "incompatible source call role " + frame.path)

    def field(self, tree: _Tree, stage: str, event: str, name: str) -> tuple[int, _Endpoint] | None:
        path = "bounds" if stage == "bounds" else f"bounds/{stage}[0]"
        frame = tree.frames.get(path)
        if frame is None:
            _require(tree.early, "missing completed source stage " + stage)
            return None
        if event == "return" and (frame.exit_kind != "return" or stage == "bounds" and tree.early):
            return None
        values = frame.entry if event == "call" else frame.exit
        _require(name in values, "missing required reached field " + stage + "." + name)
        return (frame.entry_index if event == "call" else frame.exit_index), values[name]

    def descriptor(self, tree: _Tree, text: str) -> tuple[int, _Endpoint] | None:
        stage, event, name = text.split(".", 2)
        return self.field(tree, stage, event, name)


def _validate_contract(contract: Record, context: Record, scope: str) -> None:
    _require(scope in ("retained", "artificial-saved-lineage") and context.get("scope") == scope, "scope")
    _require(_json(contract.get("checkpoint_fields")) == _json(_CHECKPOINTS)
             and _json(contract.get("alias_groups")) == _json(_ALIASES)
             and _json(contract.get("norm_pair_roles")) == _json(_ROLES),
             "fixed observables, aliases, roles or units")
    caps = _record(contract.get("future_caps"), "contract caps")
    _require(all(type(caps.get(key)) is int and caps[key] == value for key, value in _CAPS.items()), "fixed numeric or work caps")
    expected = _record(contract.get("expected_retained"), "contract matrix")
    _require(_json(expected.get("selection")) == _json(list(_SELECTION))
             and type(expected.get("rows")) is int and expected["rows"] == 24
             and type(expected.get("norm_pair_slots")) is int and expected["norm_pair_slots"] == 36,
             "fixed selection matrix")
    _require(context.get("source_pins") == _METHOD_PINS and context.get("context_justified") is True
             and context.get("context_assumption") == contract.get("context_provenance")
             and contract.get("context_provenance") == _CONTEXT_ASSUMPTION,
             "conditional source/context justification")
    _require(type(context.get("expected_events")) is int and 0 < context["expected_events"] <= 8192
             and (scope != "retained" or context["expected_events"] == 1248), "declared event inventory")
    _require(contract.get("interpretation_limits") == _LIMITATIONS, "interpretation limits")


def verify(archive: Record, contract: Record, produced: Record, *, scope: str,
           check: Check, charge: Charge) -> Record:
    """Independently read saved SI endpoints; context equality remains a provenance assumption."""
    check()
    archive, contract, produced = (_record(value, label) for value, label in (
        (archive, "archive"), (contract, "contract"), (produced, "produced report")))
    context = _record(archive.get("_context"), "authenticated context")
    _validate_contract(contract, context, scope)
    audit = _Audit(contract, check, charge)
    report = _record(archive.get("report"), "saved report")
    rows = _list(report.get("rows"), "saved rows")
    _require(len(rows) == 24, "24 saved trace rows")
    identities = [(selected["row_index"], domain, selected["lo_deg"] if domain == "cell" else selected["midpoint_deg"],
                   selected["hi_deg"] if domain == "cell" else selected["midpoint_deg"], sign, independent)
                  for selected in _SELECTION for domain in ("cell", "singleton")
                  for sign in ("positive", "negative") for independent in (False, True)]
    trees: list[_Tree] = []
    indices: dict[tuple[int, str, str, bool], int] = {}
    for index, (raw, identity) in enumerate(zip(rows, identities, strict=True)):
        row = _record(raw, "saved trace row")
        _require(type(row.get("row_index")) is int and type(row.get("independent")) is bool
                 and tuple(row.get(key) for key in ("row_index", "domain", "lo_deg", "hi_deg", "sign", "independent")) == identity,
                 "saved matrix order or identity")
        trace = _record(row.get("trace"), "saved trace")
        _require(type(trace.get("independent")) is bool
                 and tuple(trace.get(key) for key in ("lo", "hi", "sign", "independent")) == identity[2:], "trace identity")
        trees.append(audit.tree(trace, _record(row.get("control"), "saved control")))
        indices[identity[0], identity[1], identity[4], identity[5]] = index
    _require(audit.used["event_visits"] == context["expected_events"], "declared events mismatch")
    lineage: list[Record] = []
    checkpoints: list[Record] = []
    widths: dict[tuple[int, str, str], Fraction | None] = {}
    for index, tree in enumerate(trees):
        for group in contract["alias_groups"]:
            for component in range(3) if "[i]" in group["source"] else range(1):
                source = group["source"].replace("[i]", f"[{component}]")
                start = audit.descriptor(tree, source)
                for target_text in group["targets"]:
                    audit.tick("aliases")
                    target = target_text.replace("[i]", f"[{component}]")
                    end = audit.descriptor(tree, target)
                    if start is not None and end is not None:
                        _require(start[1].text == end[1].text, "broken exact source alias")
                    lineage.append(dict(row=index, source=source, target=target, units=group["units"],
                        status="matched" if start is not None and end is not None else "not-reached",
                        **{"from": _pointer(index, start[0], source.split(".", 2)[2]) if start is not None else None},
                        to=_pointer(index, end[0], target.split(".", 2)[2]) if end is not None else None))
        for stage, fields in contract["checkpoint_fields"].items():
            for name, units in fields.items():
                audit.tick("descriptors")
                value = audit.field(tree, stage, "return", name)
                width = audit.subtract(value[1].upper, value[1].lower) if value is not None else None
                widths[index, stage, name] = width
                checkpoints.append(dict(row=index, stage=stage, field=name, units=units,
                    status="observed" if value is not None else "not-reached",
                    pointer=_pointer(index, value[0], name) if value is not None else None,
                    lo=value[1].text[0] if value is not None else None,
                    hi=value[1].text[1] if value is not None else None, width=str(width) if width is not None else None))
    comparisons: list[Record] = []
    for selected in _SELECTION:
        row_index = selected["row_index"]
        for sign in ("positive", "negative"):
            for independent in (False, True):
                cell = indices[row_index, "cell", sign, independent]
                singleton = indices[row_index, "singleton", sign, independent]
                for stage, fields in contract["checkpoint_fields"].items():
                    for name, units in fields.items():
                        audit.tick("descriptors")
                        left, right = widths[cell, stage, name], widths[singleton, stage, name]
                        both = left is not None and right is not None
                        difference = audit.subtract(left, right) if both else None
                        ratio = audit.divide(left, right) if both and right != 0 else None
                        status = "matched" if both else "both-not-reached" if left is None and right is None else \
                                 "cell-not-reached" if left is None else "singleton-not-reached"
                        comparisons.append(dict(row_index=row_index, sign=sign, independent=independent,
                            stage=stage, field=name, units=units, cell=cell, singleton=singleton, status=status,
                            cell_width=str(left) if left is not None else None,
                            singleton_width=str(right) if right is not None else None,
                            difference=str(difference) if difference is not None else None,
                            ratio=str(ratio) if ratio is not None else None))
    pairs: list[Record] = []
    for selected in _SELECTION:
        for domain in ("cell", "singleton"):
            for sign in ("positive", "negative"):
                default = indices[selected["row_index"], domain, sign, False]
                independent = indices[selected["row_index"], domain, sign, True]
                for role in contract["norm_pair_roles"]:
                    audit.tick("norm_pairs")
                    path = role["parent_path"] + f"/_norm2[{role['direct_norm2_ordinal']}]"
                    nodes = [trees[number].frames.get(path) for number in (default, independent)]
                    operands: list[list[str] | None] = []
                    results: list[str | None] = []
                    boxes: list[tuple[_Endpoint, ...] | None] = []
                    for number, node in zip((default, independent), nodes, strict=True):
                        if node is None or node.exit_kind != "return":
                            _require(trees[number].early, "missing reached norm role")
                            operands.append(None)
                            results.append(None)
                            boxes.append(None)
                            continue
                        _require(all(f"v[{component}]" in node.entry for component in range(3))
                                 and "return" in node.exit, "missing norm operands/result")
                        operands.append([_pointer(number, node.entry_index, f"v[{component}]") for component in range(3)])
                        results.append(_pointer(number, node.exit_index, "return"))
                        boxes.append(tuple(node.entry[f"v[{component}]"] for component in range(3)) + (node.exit["return"],))
                    if boxes[0] is None or boxes[1] is None:
                        disposition = "not-reached"
                    elif any(boxes[0][component].text != boxes[1][component].text for component in range(3)):
                        disposition = "input-confounded"
                    elif boxes[0][3].text == boxes[1][3].text:
                        disposition = "no-local-difference-observed"
                    else:
                        disposition = "conditional-local-method-response"
                    pairs.append(dict(row_index=selected["row_index"], domain=domain, sign=sign,
                        **role, default=default, independent=independent, status=disposition,
                        default_operands=operands[0], independent_operands=operands[1],
                        default_result=results[0], independent_result=results[1],
                        context_assumption=contract["context_provenance"], source_pins=context["source_pins"],
                        attribution_limit=_LIMIT))
    expected = dict(schema="ariadna-saved-lineage-v1", status="lineage-qualified-attribution-unresolved",
                    scope=scope, lineage=lineage, checkpoints=checkpoints, comparisons=comparisons, norm_pairs=pairs,
                    risks=list(_RISKS), assumptions=[contract["context_provenance"]],
                    limitations=contract["interpretation_limits"], counts=dict(audit.used))
    check()
    _require(_json(produced) == _json(expected), "produced descriptors, dispositions or claim limits differ")
    proof = dict(status="lineage-independently-verified", counts=dict(audit.used),
                 produced_sha256=sha256(_json(produced)).hexdigest())
    check()
    return proof
