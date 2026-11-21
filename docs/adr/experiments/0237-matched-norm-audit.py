"""Independently audit the artificial matched-input Decimal96 norm experiment.

This module neither imports evaluator helpers nor executes historical sources.
Directed arithmetic is reproduced with bounded integers and exact Fractions.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from fractions import Fraction
from hashlib import sha256
import json
from math import gcd
import re
from typing import Any


type Row = dict[str, Any]
type Bounds = tuple[Fraction, Fraction]
type Check = Callable[[], None]
type Charge = Callable[[str, int], None]

_CATEGORIES = ("event_visits", "boxes", "methods", "oracles", "diagonals",
               "comparisons", "descriptors", "directed_primitives")
_METHODS = ("square-sum", "product-sum-clipped")
_NUMBER = re.compile(r"([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?\Z", re.ASCII)
_HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_SOURCE_BINDINGS = ("bounds", "checks", "interval", "runner", "trace", "trace_schema")
_METHOD_METADATA = frozenset((*_SOURCE_BINDINGS, "anchors", "archive", "containment", "core",
                              "io", "oracle", "orbit", "points", "reader", "screen", "study"))
_CAPS = dict(endpoint_text_chars=1024, decimal_significand_digits=256,
             absolute_decimal_exponent=512, rational_component_bits=4096,
             input_event_records=8192, event_visits_per_process=32768,
             input_vector_boxes=72, method_evaluations_per_process=144,
             exact_box_range_evaluations_per_process=72, diagonal_checks=72,
             paired_method_comparisons=72, descriptor_records=1024,
             directed_primitive_operations_per_process=8192)
_CHARGE_CAPS = dict(zip(_CATEGORIES, ("event_visits_per_process", "input_vector_boxes",
                                    "method_evaluations_per_process",
                                    "exact_box_range_evaluations_per_process",
                                    "diagonal_checks", "paired_method_comparisons",
                                    "descriptor_records",
                                    "directed_primitive_operations_per_process"), strict=True))
_CELLS = ((62, "150", "4801/32", "9601/64"),
          (94, "151", "4833/32", "9665/64"),
          (125, "4863/32", "152", "9727/64"))
_ROLES = (
    ("impulse-squared", "bounds", 0, "m/s", "m2/s2"),
    ("radius-squared", "bounds/_reverse[0]", 1, "m", "m2"),
    ("angular-momentum-squared", "bounds/_reverse[0]", 4, "m2/s", "m4/s2"),
)


def _wire(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _same(actual: Any, expected: Any, field: str) -> None:
    """Compare records without treating bools as integer provenance."""
    if type(actual) is not type(expected):
        raise ValueError(f"audit {field}: wrong type")
    if isinstance(expected, dict):
        if actual.keys() != expected.keys():
            raise ValueError(f"audit {field}: wrong fields")
        for key, item in expected.items():
            _same(actual[key], item, f"{field}.{key}")
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            raise ValueError(f"audit {field}: wrong length")
        for index, item in enumerate(expected):
            _same(actual[index], item, f"{field}[{index}]")
    elif actual != expected:
        raise ValueError(f"audit {field}: inconsistent value")


def _mapping(value: Any, field: str) -> Row:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise ValueError(f"audit {field}: expected object")
    return value


def _integer(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"audit {field}: expected nonnegative integer")
    return value


class _Replay:
    def __init__(self, check: Check, charge: Charge, caps: Row) -> None:
        self.check = check
        self.charge = charge
        self.caps = caps
        self.bits = caps["rational_component_bits"]
        self.partial_rows: list[Row] = []
        self.counts = dict.fromkeys(_CATEGORIES, 0)
        self.progress = {kind: dict(attempted=0, charged=0, completed=0)
                         for kind in ("methods", "oracles")}

    def tick(self, category: str, amount: int = 1) -> None:
        self.check()
        self.charge(category, amount)
        self.counts[category] += amount
        if self.counts[category] > self.caps[_CHARGE_CAPS[category]]:
            raise ValueError("audit " + category + " cap")

    def guard(self, value: Fraction) -> Fraction:
        self.check()
        if (value.numerator.bit_length() > self.bits
                or value.denominator.bit_length() > self.bits):
            raise ValueError("audit rational component bit cap")
        return value

    def product_size(self, left: int, right: int) -> None:
        self.check()
        if left and right and abs(left).bit_length() + abs(right).bit_length() > self.bits:
            raise ValueError("audit predicted integer product bit cap")

    def ten(self, exponent: int) -> int:
        self.check()
        if exponent < 0 or (exponent * 3322 + 999) // 1000 + 1 > self.bits:
            raise ValueError("audit predicted decimal scaling bit cap")
        return 10 ** exponent

    def parse(self, value: Any, *, source: bool = True) -> Fraction:
        self.check()
        if type(value) is not str or not 1 <= len(value) <= self.caps["endpoint_text_chars"]:
            raise ValueError("audit endpoint text cap or type")
        match = _NUMBER.fullmatch(value)
        if match is None:
            raise ValueError("audit nonfinite or malformed decimal endpoint")
        sign, integral, trailing, only_fraction, exponent_text = match.groups()
        fractional = only_fraction if integral is None else trailing or ""
        digits = (integral or "") + fractional
        if len(digits) > self.caps["decimal_significand_digits"]:
            raise ValueError("audit decimal significand digit cap")
        # Bound exponent text before int() or a decimal power can allocate.
        exponent_text = exponent_text or "0"
        magnitude = exponent_text.lstrip("+-")
        if len(magnitude) > 4:
            raise ValueError("audit decimal exponent text cap")
        explicit_exponent = int(exponent_text)
        if source and abs(explicit_exponent) > self.caps["absolute_decimal_exponent"]:
            raise ValueError("audit explicit source decimal exponent cap")
        exponent = explicit_exponent - len(fractional)
        if source and abs(exponent) > self.caps["absolute_decimal_exponent"]:
            raise ValueError("audit source decimal exponent cap")
        if abs(exponent) > 1233:
            raise ValueError("audit predicted decimal exponent bit cap")
        coefficient = int(digits)
        if sign == "-":
            coefficient = -coefficient
        if not coefficient:
            return Fraction(0)
        scale = self.ten(abs(exponent))
        if exponent >= 0:
            self.product_size(coefficient, scale)
            return self.guard(Fraction(coefficient * scale))
        return self.guard(Fraction(coefficient, scale))

    def mul(self, left: Fraction, right: Fraction) -> Fraction:
        self.check()
        if not left or not right:
            return Fraction(0)
        a, b, c, d = left.numerator, left.denominator, right.numerator, right.denominator
        first, second = gcd(abs(a), d), gcd(abs(c), b)
        a, d, c, b = a // first, d // first, c // second, b // second
        self.product_size(a, c)
        self.product_size(b, d)
        return self.guard(Fraction(a * c, b * d))

    def add(self, left: Fraction, right: Fraction) -> Fraction:
        self.check()
        shared = gcd(left.denominator, right.denominator)
        a, b = right.denominator // shared, left.denominator // shared
        self.product_size(left.numerator, a)
        self.product_size(right.numerator, b)
        self.product_size(left.denominator, a)
        predicted = max(left.numerator.bit_length() + a.bit_length(),
                        right.numerator.bit_length() + b.bit_length()) + 1
        if predicted > self.bits:
            raise ValueError("audit predicted rational addition bit cap")
        return self.guard(Fraction(left.numerator * a + right.numerator * b,
                                   left.denominator * a))

    def sub(self, left: Fraction, right: Fraction) -> Fraction:
        return self.add(left, -right)

    def ratio(self, left: Fraction, right: Fraction) -> Fraction:
        if not right:
            raise ValueError("audit zero rational divisor")
        return self.mul(left, self.guard(Fraction(right.denominator, right.numerator)))

    def le(self, left: Fraction, right: Fraction) -> bool:
        self.check()
        common = gcd(left.denominator, right.denominator)
        a, b = right.denominator // common, left.denominator // common
        self.product_size(left.numerator, a)
        self.product_size(right.numerator, b)
        return left.numerator * a <= right.numerator * b

    def lesser(self, left: Fraction, right: Fraction) -> Fraction:
        return left if self.le(left, right) else right

    def greater(self, left: Fraction, right: Fraction) -> Fraction:
        return right if self.le(left, right) else left

    def extreme(self, values: list[Fraction], upward: bool) -> Fraction:
        result = values[0]
        for value in values[1:]:
            result = self.greater(result, value) if upward else self.lesser(result, value)
        return result

    def interval(self, value: Any, *, source: bool = True) -> Bounds:
        record = _mapping(value, "interval")
        if record.keys() != {"lo", "hi"}:
            raise ValueError("audit interval fields")
        lo, hi = self.parse(record["lo"], source=source), self.parse(record["hi"], source=source)
        if not self.le(lo, hi):
            raise ValueError("audit reversed interval")
        return lo, hi

    def round96(self, value: Fraction, upward: bool) -> Fraction:
        """Round a rational directly onto the precision96 decimal lattice."""
        self.guard(value)
        if not value:
            return Fraction(0)
        magnitude = abs(value)
        numerator, denominator = magnitude.numerator, magnitude.denominator
        adjusted = len(str(numerator)) - len(str(denominator))
        if adjusted >= 0:
            scale = self.ten(adjusted)
            self.product_size(denominator, scale)
            if numerator < denominator * scale:
                adjusted -= 1
        else:
            scale = self.ten(-adjusted)
            self.product_size(numerator, scale)
            if numerator * scale < denominator:
                adjusted -= 1
        exponent = adjusted - 95
        scale = self.ten(abs(exponent))
        if exponent >= 0:
            self.product_size(value.denominator, scale)
            dividend, divisor = value.numerator, value.denominator * scale
        else:
            self.product_size(value.numerator, scale)
            dividend, divisor = value.numerator * scale, value.denominator
        coefficient = -((-dividend) // divisor) if upward else dividend // divisor
        if exponent >= 0:
            self.product_size(coefficient, scale)
            return self.guard(Fraction(coefficient * scale))
        return self.guard(Fraction(coefficient, scale))

    def directed_abs(self, value: Fraction, upward: bool) -> Fraction:
        self.tick("directed_primitives")
        return self.round96(abs(value), upward)

    def directed_mul(self, left: Fraction, right: Fraction, upward: bool) -> Fraction:
        self.tick("directed_primitives")
        return self.round96(self.mul(left, right), upward)

    def directed_add(self, left: Fraction, right: Fraction, upward: bool) -> Fraction:
        self.tick("directed_primitives")
        return self.round96(self.add(left, right), upward)

    def square(self, value: Bounds) -> Bounds:
        lo, hi = value
        upper = self.greater(self.directed_abs(lo, True), self.directed_abs(hi, True))
        lower = (Fraction(0) if self.le(lo, Fraction(0)) and self.le(Fraction(0), hi)
                 else self.lesser(self.directed_abs(lo, False), self.directed_abs(hi, False)))
        return (self.directed_mul(lower, lower, False),
                self.directed_mul(upper, upper, True))

    def self_product(self, value: Bounds) -> Bounds:
        corners = ((value[0], value[0]), (value[0], value[1]),
                   (value[1], value[0]), (value[1], value[1]))
        lower = self.extreme([self.directed_mul(a, b, False) for a, b in corners], False)
        upper = self.extreme([self.directed_mul(a, b, True) for a, b in corners], True)
        return lower, upper

    def method(self, vector: tuple[Bounds, Bounds, Bounds], name: str) -> tuple[Bounds, Bounds]:
        progress = self.progress["methods"]
        progress["attempted"] += 1
        self.tick("methods")
        progress["charged"] += 1
        operation = self.square if name == "square-sum" else self.self_product
        left, right = operation(vector[0]), operation(vector[1])
        raw = (self.directed_add(left[0], right[0], False),
               self.directed_add(left[1], right[1], True))
        third = operation(vector[2])
        raw = (self.directed_add(raw[0], third[0], False),
               self.directed_add(raw[1], third[1], True))
        if name == "product-sum-clipped":
            self.tick("directed_primitives")
            final = self.greater(Fraction(0), raw[0]), raw[1]
        else:
            final = raw
        progress["completed"] += 1
        return raw, final

    def oracle(self, vector: tuple[Bounds, Bounds, Bounds]) -> Bounds:
        progress = self.progress["oracles"]
        progress["attempted"] += 1
        self.tick("oracles")
        progress["charged"] += 1
        lower, upper = Fraction(0), Fraction(0)
        for lo, hi in vector:
            left, right = self.mul(lo, lo), self.mul(hi, hi)
            minimum = (Fraction(0) if self.le(lo, Fraction(0)) and self.le(Fraction(0), hi)
                       else self.lesser(left, right))
            lower, upper = self.add(lower, minimum), self.add(upper, self.greater(left, right))
        progress["completed"] += 1
        return lower, upper

    def interval_record(self, actual: Any, expected: Bounds, field: str,
                        *, saved: list[str] | None = None) -> None:
        record = _mapping(actual, field)
        if record.keys() != {"decimal", "rational"}:
            raise ValueError(f"audit {field}: interval record fields")
        decimal = record["decimal"]
        if type(decimal) is not list or len(decimal) != 2:
            raise ValueError(f"audit {field}: decimal endpoints")
        parsed = tuple(self.parse(item, source=saved is not None) for item in decimal)
        if parsed != expected:
            raise ValueError(f"audit {field}: independent endpoint mismatch")
        _same(record["rational"], [str(item) for item in expected], field + ".rational")
        if saved is not None:
            _same(decimal, saved, field + ".decimal")


def _context() -> Row:
    common = dict(prec=96, Emin=-999999, Emax=999999, capitals=1, clamp=0,
                  enabled_traps=["DivisionByZero", "InvalidOperation", "Overflow"])
    pair = dict(lower=common | dict(rounding="ROUND_FLOOR"),
                upper=common | dict(rounding="ROUND_CEILING"))
    return dict(fingerprint=sha256(_wire(pair)).hexdigest(), **pair)


def _method_context(actual: Any, fingerprint: str, field: str) -> None:
    record = _mapping(actual, field)
    if record.keys() != {"fingerprint", "lower_before_flags", "upper_before_flags",
                         "lower_after_flags", "upper_after_flags"}:
        raise ValueError(f"audit {field}: context fields")
    _same(record["fingerprint"], fingerprint, field + ".fingerprint")
    for side in ("lower", "upper"):
        _same(record[side + "_before_flags"], [], field + ".initial flags")
        flags = record[side + "_after_flags"]
        if (type(flags) is not list or any(type(flag) is not str for flag in flags)
                or flags != sorted(set(flags)) or not set(flags) <= {"Inexact", "Rounded"}):
            raise ValueError(f"audit {field}: disallowed final flags")


def _escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _flatten_result(value: Any, prefix: str = "return", depth: int = 0) -> Row:
    if depth > 8:
        raise ValueError("audit result nesting cap")
    if type(value) is dict:
        result: Row = {}
        for name, item in _mapping(value, "trace.result").items():
            result.update(_flatten_result(item, prefix + "." + name, depth + 1))
        return result
    if type(value) is list:
        if len(value) > 64:
            raise ValueError("audit result list cap")
        result = {}
        for index, item in enumerate(value):
            result.update(_flatten_result(item, prefix + f"[{index}]", depth + 1))
        return result
    if value is not None and type(value) not in (str, bool, int):
        raise ValueError("audit malformed result scalar")
    return {prefix: value}


def _select(archive: Row, contract: Row, scope: str, replay: _Replay) -> list[Row]:
    """Select from authenticated raw trees, independently of producer descriptors."""
    report = _mapping(archive.get("report"), "archive.report")
    context = _mapping(archive.get("_context"), "archive._context")
    _same(context.get("scope"), scope, "archive.scope")
    _same(report.get("scope"), scope, "report.scope")
    pins = _mapping(context.get("source_pins"), "source pins")
    if set(pins) != set(_SOURCE_BINDINGS) or any(
        type(value) is not str or _HEX.fullmatch(value) is None for value in pins.values()
    ):
        raise ValueError("audit source pins malformed")
    metadata = _mapping(report.get("method_sha256"), "method metadata")
    if set(metadata) not in (set(_SOURCE_BINDINGS), _METHOD_METADATA) or any(
        type(value) is not str or _HEX.fullmatch(value) is None for value in metadata.values()
    ):
        raise ValueError("audit method metadata malformed")
    # Only the selected bindings name source files authenticated by the caller.
    _same({role: metadata[role] for role in _SOURCE_BINDINGS}, pins, "report.method_sha256")
    roles = [dict(role=role, parent_path=parent, direct_norm2_ordinal=ordinal,
                  operand_units=operand, result_units=result)
             for role, parent, ordinal, operand, result in _ROLES]
    selection = _mapping(contract.get("selection"), "contract.selection")
    _same(selection.get("norm_pair_roles"), roles, "contract.roles")
    _same(selection.get("expected_trace_rows"), 24, "contract.rows")
    _same(selection.get("vector_boxes"), 72, "contract.boxes")
    rows = report.get("rows")
    if type(rows) is not list or len(rows) != 24:
        raise ValueError("audit expected 24 raw traces")
    expected = [(index, domain, sign, independent, lo if domain == "cell" else middle,
                 hi if domain == "cell" else middle)
                for index, lo, hi, middle in _CELLS
                for domain in ("cell", "singleton")
                for sign in ("positive", "negative") for independent in (False, True)]
    selected: list[Row] = []
    event_total = 0
    for trace_row, (raw_row, identity) in enumerate(zip(rows, expected, strict=True)):
        row = _mapping(raw_row, "trace row")
        index, domain, sign, independent, lo_deg, hi_deg = identity
        for key, item in dict(row_index=index, domain=domain, sign=sign, independent=independent,
                              lo_deg=lo_deg, hi_deg=hi_deg).items():
            _same(row.get(key), item, f"trace row {trace_row}.{key}")
        trace = _mapping(row.get("trace"), "trace")
        for key, item in dict(lo=lo_deg, hi=hi_deg, sign=sign, independent=independent).items():
            _same(trace.get(key), item, "trace." + key)
        _same(trace.get("status"), "complete", "trace.status")
        seal = sha256(_wire({key: value for key, value in trace.items() if key != "seal"})).hexdigest()
        _same(trace.get("seal"), seal, "trace.seal")
        _same(row.get("control"), trace.get("result"), "trace.control")
        events = trace.get("events")
        if type(events) is not list or len(events) > replay.caps["input_event_records"]:
            raise ValueError("audit malformed trace events")
        event_total += len(events)
        if event_total > replay.caps["input_event_records"]:
            raise ValueError("audit input event cap")
        stack: list[int] = []
        calls: dict[int, Row] = {}
        returns: dict[int, Row] = {}
        paths: dict[int, str] = {}
        siblings: dict[int, Counter[str]] = {}
        children: dict[int, list[str]] = {}
        totals: dict[str, Counter[str]] = {}
        for event_index, raw_event in enumerate(events):
            replay.tick("event_visits")
            event = _mapping(raw_event, "event")
            if event.keys() != {"index", "call", "parent", "stage", "event", "fields", "scalars"}:
                raise ValueError("audit event inventory")
            _same(event.get("index"), event_index, "event.index")
            call = _integer(event.get("call"), "event.call")
            stage, kind = event.get("stage"), event.get("event")
            if type(stage) is not str or kind not in ("call", "return"):
                raise ValueError("audit stage or incomplete event")
            fields = _mapping(event.get("fields"), "event.fields")
            for value in fields.values():
                replay.interval(value)
            scalars = _mapping(event.get("scalars"), "event.scalars")
            for value in scalars.values():
                if (value is not None and type(value) not in (bool, int, str)
                        or type(value) is str and len(value) > 4096
                        or type(value) is int and value.bit_length() > 4096):
                    raise ValueError("audit scalar inventory cap/type")
            if stage not in ("_cross", "_binary64"):
                _same(scalars.get("independent"), independent, "event.independent")
            totals.setdefault(stage, Counter())[kind] += 1
            if kind == "call":
                if call in calls or call != len(calls):
                    raise ValueError("audit duplicate/nonsequential call")
                parent = stack[-1] if stack else None
                _same(event.get("parent"), parent, "event.parent")
                if parent is None:
                    if calls or stage != "bounds":
                        raise ValueError("audit incorrect root")
                    path = "bounds"
                else:
                    ordinal = siblings[parent][stage]
                    siblings[parent][stage] += 1
                    children[parent].append(stage)
                    path = paths[parent] + f"/{stage}[{ordinal}]"
                calls[call] = event
                paths[call] = path
                siblings[call] = Counter()
                children[call] = []
                stack.append(call)
            else:
                if not stack or stack.pop() != call or call not in calls or call in returns:
                    raise ValueError("audit unmatched return")
                original = calls[call]
                _same(stage, original["stage"], "return.stage")
                _same(event.get("parent"), original.get("parent"), "return.parent")
                for name, value in original["fields"].items():
                    _same(fields.get(name), value, "return unchanged argument." + name)
                returns[call] = event
        if stack or calls.keys() != returns.keys():
            raise ValueError("audit incomplete call tree")
        stages = _mapping(trace.get("stages"), "trace.stages")
        for stage, summary in stages.items():
            counts = totals.get(stage, Counter())
            _same(summary, dict(calls=counts["call"], returns=counts["return"], errors=0,
                                status="complete" if counts["return"] else "not-reached"),
                  "trace.stages." + stage)
        if not set(totals) <= set(stages):
            raise ValueError("audit missing stage counters")
        expected_stages = {"bounds", "_ellipse", "_reverse", "_unit", "_cross",
                           "_norm2", "_mass_exclusion", "_clearance", "_binary64"}
        if set(stages) != expected_stages:
            raise ValueError("audit stage inventory")
        fixed_children = {
            "_ellipse": ["_cross", "_cross"], "_unit": ["_norm2"],
            "_mass_exclusion": ["_binary64", "_binary64"],
            "_reverse": ["_unit", "_unit", "_cross", "_norm2", "_norm2", "_cross",
                         "_norm2", "_norm2", "_unit", "_cross", "_cross", "_norm2"],
            "_cross": [], "_norm2": [], "_binary64": [],
        }
        for call_id, call_record in calls.items():
            stage = call_record["stage"]
            if stage == "bounds":
                result = _mapping(trace.get("result"), "trace.result")
                required_children = ["_ellipse", "_reverse", "_norm2", "_mass_exclusion"]
                if result.get("reason") != "mass":
                    required_children.append("_clearance")
                observed_result = {key: value for key, value in returns[call_id]["scalars"].items()
                                   if key.startswith("return.")}
                _same(observed_result, _flatten_result(result), "bounds result scalars")
                for key, item in dict(lo=lo_deg, hi=hi_deg, sign=sign).items():
                    _same(call_record["scalars"].get(key), item, "bounds entry." + key)
                    _same(returns[call_id]["scalars"].get(key), item, "bounds exit." + key)
            elif stage == "_clearance":
                required_children = ["_norm2", "_unit"]
                radial = returns[call_id]["fields"].get("radial")
                if radial is None:
                    raise ValueError("audit clearance radial binding")
                if replay.parse(radial["lo"]) < 0:
                    required_children.extend(["_cross", "_cross", "_norm2", "_norm2"])
            else:
                if stage not in fixed_children:
                    raise ValueError("audit unexpected child stage")
                required_children = fixed_children[stage]
            _same(children[call_id], required_children, "call source child order")
            if stage == "_reverse":
                _same(call_record["scalars"].get("sign"), sign, "reverse entry.sign")
                _same(returns[call_id]["scalars"].get("sign"), sign, "reverse exit.sign")
        for role, parent_path, ordinal, operand_units, result_units in _ROLES:
            path = parent_path + f"/_norm2[{ordinal}]"
            matches = [call for call, value in paths.items() if value == path]
            if len(matches) != 1:
                raise ValueError("audit missing/duplicate structural norm role")
            call = calls[matches[0]]
            returned = returns[matches[0]]
            input_fields, output_fields = call["fields"], returned["fields"]
            if set(input_fields) != {"v[0]", "v[1]", "v[2]"}:
                raise ValueError("audit norm operand inventory")
            raw_strings: list[str] = []
            vector: list[Bounds] = []
            for coordinate in range(3):
                field = f"v[{coordinate}]"
                if field not in input_fields or field not in output_fields:
                    raise ValueError("audit absent norm operand")
                _same(output_fields[field], input_fields[field], "norm unchanged operand")
                vector.append(replay.interval(input_fields[field]))
                raw_strings.extend((input_fields[field]["lo"], input_fields[field]["hi"]))
            if "return" not in output_fields:
                raise ValueError("audit absent saved norm return")
            saved = replay.interval(output_fields["return"])
            call_pointer = f"/report/rows/{trace_row}/trace/events/{call['index']}"
            return_pointer = f"/report/rows/{trace_row}/trace/events/{returned['index']}"
            metadata = dict(id=len(selected), trace_row=trace_row, row_index=index,
                            domain=domain, sign=sign,
                            source_origin="independent" if independent else "default",
                            lo_deg=lo_deg, hi_deg=hi_deg, role=role, parent_path=parent_path,
                            direct_norm2_ordinal=ordinal, operand_units=operand_units,
                            result_units=result_units)
            source = dict(path=path, call=call["index"], **{"return": returned["index"]},
                          call_pointer=call_pointer, return_pointer=return_pointer,
                          operand_pointers=[call_pointer + "/fields/" + _escape(f"v[{i}]")
                                            for i in range(3)],
                          return_field_pointer=return_pointer + "/fields/return")
            selected.append(dict(metadata=metadata, source=source, vector=tuple(vector),
                                 raw=raw_strings, saved=saved,
                                 saved_raw=[output_fields["return"][side] for side in ("lo", "hi")]))
    _same(context.get("expected_events"), event_total, "archive.expected_events")
    _same(selection.get("expected_trace_events"), event_total, "contract.expected_events")
    _same(report.get("work", {}).get("events"), event_total, "report.work.events")
    return selected


def _metrics(replay: _Replay, interval: Bounds, oracle: Bounds) -> Row:
    width = replay.sub(interval[1], interval[0])
    oracle_width = replay.sub(oracle[1], oracle[0])
    return dict(width=str(width), lower_excess=str(replay.sub(oracle[0], interval[0])),
                upper_excess=str(replay.sub(interval[1], oracle[1])),
                excess_width=str(replay.sub(width, oracle_width)))


def _validate_contract(contract: Row) -> Row:
    caps = _mapping(contract.get("caps"), "contract.caps")
    for name, maximum in _CAPS.items():
        value = caps.get(name)
        if type(value) is not int or not 0 < value <= maximum:
            raise ValueError("audit fixed design cap: " + name)
    context = _mapping(contract.get("context"), "contract.context")
    expected_context = dict(prec=96, Emin=-999999, Emax=999999, capitals=1, clamp=0,
                            enabled_traps=["InvalidOperation", "DivisionByZero", "Overflow"],
                            all_other_traps=False, initial_flags="all cleared",
                            directed_rounding=["ROUND_FLOOR", "ROUND_CEILING"],
                            allowed_final_flags=["Inexact", "Rounded"])
    for name, value in expected_context.items():
        if name == "enabled_traps":
            traps = context.get(name)
            if type(traps) is not list or any(type(item) is not str for item in traps):
                raise ValueError("audit contract.context enabled traps")
            _same(sorted(traps), sorted(value), "contract.context." + name)
        else:
            _same(context.get(name), value, "contract.context." + name)
    selection = _mapping(contract.get("selection"), "contract.selection")
    expected_selection = dict(
        selected_cells=[dict(row_index=index, lo_deg=lo, hi_deg=hi, midpoint_deg=middle)
                        for index, lo, hi, middle in _CELLS],
        selected_row_indices=[62, 94, 125], domains=["cell", "singleton"],
        signs=["positive", "negative"], source_origins=["default", "independent"],
        structural_slots=36, vector_boxes=72, expected_trace_rows=24,
        expected_trace_events=1248)
    for name, value in expected_selection.items():
        _same(selection.get(name), value, "contract.selection." + name)
    return caps


def _verify(archive: Row, contract: Row, produced: Row, *, check: Check,
            replay: _Replay, scope: str | None = None) -> Row:
    """Reconstruct all72 artificial boxes and independently verify144 methods.

    Caller authenticates raw archive/source bytes and enforces artificial scope;
    this audit verifies structural provenance, arithmetic and bounded work.
    """
    archive = _mapping(archive, "archive")
    contract = _mapping(contract, "contract")
    produced = _mapping(produced, "produced")
    if scope is None:
        scope = _mapping(archive.get("_context"), "archive context").get("scope")
    if type(scope) is not str or not scope:
        raise ValueError("audit nonempty scope required")
    selected = _select(archive, contract, scope, replay)
    if len(selected) != 72:
        raise ValueError("audit incomplete72-box matrix")
    required = {"schema", "scope", "status", "reason", "context", "rows", "counts", "progress"}
    if produced.keys() != required:
        raise ValueError("audit produced result fields")
    _same(produced["schema"], "ariadna-matched-norm-v1", "schema")
    _same(produced["scope"], scope, "scope")
    contexts = _context()
    _same(produced["context"], contexts, "context")
    rows = produced["rows"]
    if type(rows) is not list or len(rows) != 72:
        raise ValueError("audit produced rows")
    classifications: list[str] = []
    compatibility = True
    all_contained = True
    for selection, raw_record in zip(selected, rows, strict=True):
        replay.tick("boxes")
        replay.tick("descriptors")
        record = _mapping(raw_record, "produced row")
        metadata = selection["metadata"]
        row_fields = set(metadata) | {"source", "input", "saved_return", "methods", "oracle",
                                     "diagonal", "metrics", "classification"}
        if record.keys() != row_fields:
            raise ValueError("audit produced row fields")
        for key, value in metadata.items():
            _same(record[key], value, "row." + key)
        _same(record["source"], selection["source"], "row.source")
        vector_hash = sha256(_wire(selection["raw"])).hexdigest()
        _same(record["input"], dict(raw_endpoint_strings=selection["raw"], sha256=vector_hash),
              "row.input")
        replay.interval_record(record["saved_return"], selection["saved"], "saved_return",
                               saved=selection["saved_raw"])
        vector = selection["vector"]
        outputs = {name: replay.method(vector, name) for name in _METHODS}
        oracle = replay.oracle(vector)
        _same(record["oracle"], dict(rational=[str(item) for item in oracle],
                                     width=str(replay.sub(oracle[1], oracle[0]))), "row.oracle")
        methods = _mapping(record["methods"], "row.methods")
        if methods.keys() != set(_METHODS):
            raise ValueError("audit method matrix")
        containment: list[bool] = []
        for name in _METHODS:
            method = _mapping(methods[name], "method")
            if method.keys() != {"input_sha256", "raw", "final", "context", "metrics", "contains_oracle"}:
                raise ValueError("audit method fields")
            raw, final = outputs[name]
            _same(method["input_sha256"], vector_hash, "method.input_sha256")
            replay.interval_record(method["raw"], raw, name + ".raw")
            replay.interval_record(method["final"], final, name + ".final")
            _method_context(method["context"], contexts["fingerprint"], name + ".context")
            contained = replay.le(final[0], oracle[0]) and replay.le(oracle[1], final[1])
            containment.append(contained)
            _same(method["contains_oracle"], contained, name + ".contains_oracle")
            _same(method["metrics"], _metrics(replay, final, oracle), name + ".metrics")
        replay.tick("diagonals")
        own = _METHODS[metadata["source_origin"] == "independent"]
        matches = outputs[own][1] == selection["saved"]
        compatibility = compatibility and matches
        _same(record["diagonal"], dict(method=own, matches=matches), "row.diagonal")
        replay.tick("comparisons")
        square, product = outputs[_METHODS[0]][1], outputs[_METHODS[1]][1]
        square_width = replay.sub(square[1], square[0])
        product_width = replay.sub(product[1], product[0])
        ratio = str(replay.ratio(product_width, square_width)) if square_width else None
        ratio_status = ("finite" if square_width else "denominator-zero-numerator-nonzero"
                        if product_width else "both-widths-zero")
        _same(record["metrics"], dict(width_square_sum=str(square_width),
                                     width_product_sum_clipped=str(product_width),
                                     width_difference_product_minus_square=str(replay.sub(product_width, square_width)),
                                     width_ratio_product_over_square=ratio,
                                     width_ratio_status=ratio_status), "row.metrics")
        contained = all(containment)
        all_contained = all_contained and contained
        if not contained:
            classification = "invalid-containment"
        elif square == product:
            classification = "equal-enclosures"
        elif replay.le(product[0], square[0]) and replay.le(square[1], product[1]):
            classification = "square-sum-strict-subset"
        elif replay.le(square[0], product[0]) and replay.le(product[1], square[1]):
            classification = "product-sum-clipped-strict-subset"
        else:
            classification = "overlap-incomparable"
        classifications.append(classification)
        replay.partial_rows.append({key: value for key, value in record.items()
                                    if key != "classification"})
    if not compatibility:
        status, reason = "inconclusive", "compatibility-mismatch"
        classifications = ["inconclusive-compatibility-mismatch"] * 72
    elif not all_contained:
        status, reason = "inconclusive", "invalid-containment"
    else:
        status, reason = "matched-norm-qualified-local-only", None
    for record, classification in zip(rows, classifications, strict=True):
        _same(record["classification"], classification, "row.classification")
    _same(produced["status"], status, "status")
    _same(produced["reason"], reason, "reason")
    _same(produced["counts"], replay.counts, "counts")
    _same(produced["progress"], replay.progress, "progress")
    check()
    return dict(status="verified", scope=scope, result_status=status, reason=reason,
                counts=replay.counts, progress=replay.progress)


class VerificationError(ValueError):
    """A failed audit retaining attempted work and verified arithmetic row evidence."""

    progress: Row
    counts: dict[str, int]
    partial_rows: list[Row]

    def __init__(self, message: str, replay: _Replay) -> None:
        super().__init__(message)
        self.progress = {kind: dict(values) for kind, values in replay.progress.items()}
        self.counts = dict(replay.counts)
        self.partial_rows = list(replay.partial_rows)


def verify(archive: Row, contract: Row, produced: Row, *, check: Check,
           charge: Charge, scope: str | None = None) -> Row:
    """Verify independent local norm arithmetic and provenance, with bounded work."""
    check()
    contract = _mapping(contract, "contract")
    replay = _Replay(check, charge, _validate_contract(contract))
    try:
        return _verify(archive, contract, produced, check=check, replay=replay, scope=scope)
    except (ValueError, ArithmeticError) as error:
        raise VerificationError(str(error), replay) from error
