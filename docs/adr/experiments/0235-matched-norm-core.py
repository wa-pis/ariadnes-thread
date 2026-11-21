"""Isolated, bounded matched-input norm arithmetic; no historical code execution."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
)
from fractions import Fraction
from hashlib import sha256
import json
from math import gcd
import re
from typing import Any

type Row = dict[str, Any]
type Charge = Callable[[str, int], None]
type Pair = tuple[Decimal, Decimal]
type ExactPair = tuple[Fraction, Fraction]

_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?\Z")
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_METHODS = ("square-sum", "product-sum-clipped")
_SELECTION = (
    (62, "150", "4801/32", "9601/64"),
    (94, "151", "4833/32", "9665/64"),
    (125, "4863/32", "152", "9727/64"),
)
_ROLES = [
    dict(role="impulse-squared", parent_path="bounds", direct_norm2_ordinal=0,
         operand_units="m/s", result_units="m2/s2"),
    dict(role="radius-squared", parent_path="bounds/_reverse[0]", direct_norm2_ordinal=1,
         operand_units="m", result_units="m2"),
    dict(role="angular-momentum-squared", parent_path="bounds/_reverse[0]",
         direct_norm2_ordinal=4, operand_units="m2/s", result_units="m4/s2"),
]
_CHILDREN = {
    "_ellipse": ["_cross", "_cross"],
    "_unit": ["_norm2"],
    "_cross": [],
    "_norm2": [],
    "_binary64": [],
    "_reverse": ["_unit", "_unit", "_cross", "_norm2", "_norm2", "_cross",
                 "_norm2", "_norm2", "_unit", "_cross", "_cross", "_norm2"],
    "_mass_exclusion": ["_binary64", "_binary64"],
}
_STAGES = ("bounds", "_ellipse", "_reverse", "_unit", "_cross", "_norm2",
           "_mass_exclusion", "_clearance", "_binary64")
_CAPS = {
    "endpoint_text_chars": 1024,
    "decimal_significand_digits": 256,
    "absolute_decimal_exponent": 512,
    "rational_component_bits": 4096,
    "input_event_records": 8192,
    "event_visits_per_process": 32768,
    "input_vector_boxes": 72,
    "method_evaluations_per_process": 144,
    "exact_box_range_evaluations_per_process": 72,
    "diagonal_checks": 72,
    "paired_method_comparisons": 72,
    "descriptor_records": 1024,
    "directed_primitive_operations_per_process": 8192,
}
_CHARGE_CAPS = {
    "event_visits": "event_visits_per_process",
    "boxes": "input_vector_boxes",
    "methods": "method_evaluations_per_process",
    "oracles": "exact_box_range_evaluations_per_process",
    "diagonals": "diagonal_checks",
    "comparisons": "paired_method_comparisons",
    "descriptors": "descriptor_records",
    "directed_primitives": "directed_primitive_operations_per_process",
}
_CONTEXT = dict(
    prec=96, Emin=-999999, Emax=999999, capitals=1, clamp=0,
    enabled_traps=["DivisionByZero", "InvalidOperation", "Overflow"],
)


def _need(condition: object, message: str) -> None:
    if not condition:
        raise ValueError("matched norm: " + message)


def _row(value: Any, name: str) -> Row:
    _need(type(value) is dict and all(type(k) is str for k in value), name + " object")
    return value


def _wire(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _fingerprint() -> Row:
    specs = dict(
        lower=dict(_CONTEXT, enabled_traps=list(_CONTEXT["enabled_traps"]), rounding=ROUND_FLOOR),
        upper=dict(_CONTEXT, enabled_traps=list(_CONTEXT["enabled_traps"]), rounding=ROUND_CEILING),
    )
    return dict(fingerprint=sha256(_wire(specs)).hexdigest(), **specs)


@dataclass(frozen=True, slots=True)
class _Numbers:
    caps: Row
    check: Callable[[], None]

    def bounded(self, value: Fraction) -> Fraction:
        self.check()
        bits = self.caps["rational_component_bits"]
        _need(value.numerator.bit_length() <= bits and value.denominator.bit_length() <= bits,
              "rational component cap")
        return value

    def integer_product(self, left: int, right: int) -> None:
        self.check()
        if left and right:
            _need(left.bit_length() + right.bit_length() <= self.caps["rational_component_bits"],
                  "rational product cap before allocation")

    def decimal(self, value: Decimal) -> Fraction:
        self.check()
        _need(value.is_finite(), "finite Decimal endpoint")
        parts = value.as_tuple()
        exponent = parts.exponent
        _need(type(exponent) is int, "finite Decimal exponent")
        digits = len(parts.digits)
        bits = self.caps["rational_component_bits"]
        # 3.322 is a rational upper bound on log2(10), before any power allocation.
        _need(((digits + max(0, exponent)) * 3322 + 999) // 1000 + 1 <= bits
              and (max(0, -exponent) * 3322 + 999) // 1000 + 1 <= bits,
              "decimal scaling cap before allocation")
        return self.bounded(Fraction(value))

    def text(self, value: Any) -> tuple[Decimal, Fraction]:
        self.check()
        _need(type(value) is str and 0 < len(value) <= self.caps["endpoint_text_chars"],
              "endpoint text cap")
        _need(_DECIMAL.fullmatch(value), "finite endpoint encoding")
        mantissa, *powers = re.split("[Ee]", value)
        _need(sum(c.isdigit() for c in mantissa) <= self.caps["decimal_significand_digits"],
              "decimal significand cap")
        if powers:
            power = powers[0]
            _need(len(power.lstrip("+-")) <= 4
                  and abs(int(power)) <= self.caps["absolute_decimal_exponent"],
                  "decimal exponent cap")
        value_decimal = Decimal(value)
        exponent = value_decimal.as_tuple().exponent
        _need(type(exponent) is int and abs(exponent) <= self.caps["absolute_decimal_exponent"],
              "decimal exponent cap")
        return value_decimal, self.decimal(value_decimal)

    def pair(self, value: Any) -> tuple[Pair, ExactPair]:
        value = _row(value, "interval")
        _need(set(value) == {"lo", "hi"}, "interval inventory")
        lo, low_exact = self.text(value["lo"])
        hi, high_exact = self.text(value["hi"])
        _need(lo <= hi, "interval order")
        return (lo, hi), (low_exact, high_exact)

    def guard_multiply(self, left: Fraction, right: Fraction) -> None:
        a = gcd(left.numerator, right.denominator)
        b = gcd(right.numerator, left.denominator)
        self.integer_product(left.numerator // a, right.numerator // b)
        self.integer_product(left.denominator // b, right.denominator // a)

    def multiply(self, left: Fraction, right: Fraction) -> Fraction:
        self.guard_multiply(left, right)
        return self.bounded(left * right)

    def guard_add(self, left: Fraction, right: Fraction) -> None:
        common = gcd(left.denominator, right.denominator)
        a, b = right.denominator // common, left.denominator // common
        self.integer_product(left.numerator, a)
        self.integer_product(right.numerator, b)
        self.integer_product(left.denominator, a)
        _need(max(left.numerator.bit_length() + a.bit_length(),
                  right.numerator.bit_length() + b.bit_length()) + 1
              <= self.caps["rational_component_bits"], "rational addition cap before allocation")

    def add(self, left: Fraction, right: Fraction) -> Fraction:
        self.guard_add(left, right)
        return self.bounded(left + right)

    def subtract(self, left: Fraction, right: Fraction) -> Fraction:
        return self.add(left, -right)

    def divide(self, left: Fraction, right: Fraction) -> Fraction:
        _need(right != 0, "zero ratio denominator")
        inverse = Fraction(right.denominator, right.numerator)
        self.guard_multiply(left, inverse)
        return self.bounded(left / right)

    def le(self, left: Fraction, right: Fraction) -> bool:
        self.integer_product(left.numerator, right.denominator)
        self.integer_product(right.numerator, left.denominator)
        return left <= right

    def interval_record(self, value: Pair) -> Row:
        strings = [str(part) for part in value]
        _need(all(len(part) <= self.caps["endpoint_text_chars"] for part in strings),
              "output endpoint text cap")
        _need(all(len(part.as_tuple().digits) <= self.caps["decimal_significand_digits"]
                  for part in value), "output significand cap")
        return dict(decimal=strings, rational=[str(self.decimal(part)) for part in value])


class _Kernel:
    """Only the pinned scalar abs/product/add/square expressions and final clip."""

    def __init__(self, numbers: _Numbers, charge: Charge) -> None:
        self.numbers = numbers
        self.charge = charge
        self.lower = Context(prec=96, rounding=ROUND_FLOOR, Emin=-999999,
                             Emax=999999, capitals=1, clamp=0)
        self.upper = Context(prec=96, rounding=ROUND_CEILING, Emin=-999999,
                             Emax=999999, capitals=1, clamp=0)
        for context in (self.lower, self.upper):
            for signal in context.traps:
                context.traps[signal] = signal in (InvalidOperation, DivisionByZero, Overflow)
            context.clear_flags()
        self.validate_contexts()
        self.initial = (self.flags(self.lower), self.flags(self.upper))

    def validate_contexts(self) -> None:
        for context, rounding in ((self.lower, ROUND_FLOOR), (self.upper, ROUND_CEILING)):
            _need(all(getattr(context, name) == expected for name, expected in _CONTEXT.items()
                      if name != "enabled_traps")
                  and context.rounding == rounding
                  and sorted(signal.__name__ for signal, enabled in context.traps.items() if enabled)
                  == _CONTEXT["enabled_traps"], "context property drift")

    @staticmethod
    def interval(lo: Decimal, hi: Decimal) -> Pair:
        _need(lo.is_finite() and hi.is_finite() and lo <= hi, "computed interval invariant")
        return lo, hi

    @staticmethod
    def flags(context: Context) -> list[str]:
        return sorted(signal.__name__ for signal, active in context.flags.items() if active)

    def scalar(self, context: Context, operation: str, left: Decimal,
               right: Decimal | None = None) -> Decimal:
        self.charge("directed_primitives", 1)
        a = self.numbers.decimal(left)
        if operation == "abs":
            return context.abs(left)
        _need(right is not None, "binary primitive operand")
        b = self.numbers.decimal(right)
        if operation == "multiply":
            self.numbers.guard_multiply(a, b)
            return context.multiply(left, right)
        _need(operation == "add", "directed primitive")
        self.numbers.guard_add(a, b)
        return context.add(left, right)

    def add(self, left: Pair, right: Pair) -> Pair:
        return self.interval(self.scalar(self.lower, "add", left[0], right[0]),
                             self.scalar(self.upper, "add", left[1], right[1]))

    def square(self, value: Pair) -> Pair:
        lo, hi = value
        upper = max(self.scalar(self.upper, "abs", lo), self.scalar(self.upper, "abs", hi))
        lower = (Decimal(0) if lo <= 0 <= hi else
                 min(self.scalar(self.lower, "abs", lo), self.scalar(self.lower, "abs", hi)))
        return self.interval(self.scalar(self.lower, "multiply", lower, lower),
                             self.scalar(self.upper, "multiply", upper, upper))

    def product(self, value: Pair) -> Pair:
        corners = tuple((left, right) for left in value for right in value)
        return self.interval(
            min(self.scalar(self.lower, "multiply", left, right) for left, right in corners),
            max(self.scalar(self.upper, "multiply", left, right) for left, right in corners))

    def evaluate(self, operands: tuple[Pair, Pair, Pair], method: str) -> tuple[Pair, Pair, Row]:
        self.validate_contexts()
        operation = self.square if method == "square-sum" else self.product
        x, y, z = operands
        # Python's left-to-right evaluation matches the pinned left-associated expressions.
        raw = self.add(self.add(operation(x), operation(y)), operation(z))
        final = raw
        if method == "product-sum-clipped":
            self.charge("directed_primitives", 1)
            final = self.interval(max(Decimal(0), raw[0]), raw[1])
        self.validate_contexts()
        lower_flags, upper_flags = self.flags(self.lower), self.flags(self.upper)
        _need(set(lower_flags + upper_flags) <= {"Inexact", "Rounded"}, "unexpected context flags")
        return raw, final, dict(
            fingerprint=_fingerprint()["fingerprint"],
            lower_before_flags=self.initial[0], upper_before_flags=self.initial[1],
            lower_after_flags=lower_flags, upper_after_flags=upper_flags,
        )


@dataclass(frozen=True, slots=True)
class _Trace:
    row: int
    starts: dict[str, Row]
    ends: dict[str, Row]


def _flatten(value: Any, prefix: str = "return", depth: int = 0) -> Row:
    _need(depth <= 8, "result nesting cap")
    if type(value) is dict:
        return {key: item for name, part in _row(value, "result").items()
                for key, item in _flatten(part, prefix + "." + name, depth + 1).items()}
    if type(value) is list:
        _need(len(value) <= 64, "result list cap")
        return {key: item for index, part in enumerate(value)
                for key, item in _flatten(part, prefix + f"[{index}]", depth + 1).items()}
    _need(value is None or type(value) in (bool, int, str), "result scalar")
    return {prefix: value}


def _trace(row: Row, index: int, numbers: _Numbers, charge: Charge) -> _Trace:
    trace = _row(row.get("trace"), "trace")
    _need(type(trace.get("seal")) is str and _HEX.fullmatch(trace["seal"])
          and trace["seal"] == sha256(_wire({k: v for k, v in trace.items() if k != "seal"})).hexdigest(),
          "trace seal")
    _need(trace.get("status") == "complete", "complete norm trace required")
    result = _row(trace.get("result"), "trace result")
    _need(_wire(row.get("control")) == _wire(result), "trace control link")
    for field, expected in (("lo", row["lo_deg"]), ("hi", row["hi_deg"]),
                            ("sign", row["sign"]), ("independent", row["independent"])):
        _need(type(trace.get(field)) is type(expected) and trace[field] == expected, "trace identity")
    events = trace.get("events")
    _need(type(events) is list and len(events) <= numbers.caps["input_event_records"], "event inventory cap")
    starts: dict[str, Row] = {}
    ends: dict[str, Row] = {}
    paths: dict[int, str] = {}
    children: dict[str, list[str]] = {}
    stack: list[int] = []
    inventory = {stage: dict(calls=0, returns=0, errors=0, status="not-reached") for stage in _STAGES}
    for event_index, value in enumerate(events):
        charge("event_visits", 1)
        item = _row(value, "event")
        _need(set(item) == {"index", "call", "parent", "stage", "event", "fields", "scalars"}
              and type(item["index"]) is int and item["index"] == event_index
              and type(item["call"]) is int and item["stage"] in _STAGES
              and (item["parent"] is None or type(item["parent"]) is int)
              and item["event"] in ("call", "return"), "event identity")
        fields, scalars = _row(item["fields"], "fields"), _row(item["scalars"], "scalars")
        for endpoint in fields.values():
            numbers.pair(endpoint)
        _need(all(value is None or type(value) in (bool, int, str) for value in scalars.values())
              and all((type(value) is not str or len(value) <= 4096)
                      and (type(value) is not int or value.bit_length() <= 4096)
                      for value in scalars.values()), "scalar inventory")
        stage, call, kind = item["stage"], item["call"], item["event"]
        if stage not in ("_cross", "_binary64"):
            _need(type(scalars.get("independent")) is bool
                  and scalars["independent"] is trace["independent"], "local arithmetic path flag")
        if stage == "_reverse":
            _need(scalars.get("sign") == trace["sign"], "local sign")
        if kind == "call":
            parent = stack[-1] if stack else None
            _need(call == len(paths) and item["parent"] == parent, "call hierarchy")
            if parent is None:
                _need(not paths and stage == "bounds", "root stage")
                path = "bounds"
            else:
                parent_path = paths[parent]
                path = f"{parent_path}/{stage}[{children[parent_path].count(stage)}]"
                children[parent_path].append(stage)
            paths[call], starts[path], children[path] = path, item, []
            stack.append(call)
            inventory[stage]["calls"] += 1
        else:
            _need(bool(stack) and stack[-1] == call and call in paths, "return hierarchy")
            stack.pop()
            path = paths[call]
            start = starts[path]
            _need(path not in ends and item["parent"] == start["parent"]
                  and stage == start["stage"], "return pairing")
            _need(all(fields.get(name) == endpoint for name, endpoint in start["fields"].items()),
                  "changed observed argument")
            ends[path] = item
            inventory[stage]["returns"] += 1
    _need(not stack and starts.keys() == ends.keys(), "incomplete trace")
    for entry in inventory.values():
        if entry["returns"]:
            entry["status"] = "complete"
    _need(_wire(trace.get("stages")) == _wire(inventory), "stage inventory")
    for path, start in starts.items():
        numbers.check()
        stage, end = start["stage"], ends[path]
        if stage == "bounds":
            expected = ["_ellipse", "_reverse", "_norm2", "_mass_exclusion"]
            if result.get("reason") != "mass":
                expected += ["_clearance"]
        elif stage == "_clearance":
            expected = ["_norm2", "_unit"]
            radial = end["fields"].get("radial")
            _need(radial is not None, "clearance radial field")
            if numbers.pair(radial)[0][0] < 0:
                expected += ["_cross", "_cross", "_norm2", "_norm2"]
        else:
            expected = _CHILDREN[stage]
        _need(children[path] == expected, "source child role order")
    for root in (starts["bounds"], ends["bounds"]):
        _need(all(type(root["scalars"].get(k)) is type(trace[k]) and root["scalars"][k] == trace[k]
                  for k in ("lo", "hi", "sign", "independent")), "observed input link")
    _need({k: v for k, v in ends["bounds"]["scalars"].items() if k.startswith("return.")}
          == _flatten(result), "observed result link")
    return _Trace(index, starts, ends)


def _oracle(operands: tuple[ExactPair, ExactPair, ExactPair], numbers: _Numbers) -> ExactPair:
    lower, upper = Fraction(0), Fraction(0)
    for lo, hi in operands:
        a, b = numbers.multiply(lo, lo), numbers.multiply(hi, hi)
        small, large = (a, b) if numbers.le(a, b) else (b, a)
        minimum = Fraction(0) if lo <= 0 <= hi else small
        lower, upper = numbers.add(lower, minimum), numbers.add(upper, large)
    return lower, upper


def _metrics(value: ExactPair, oracle: ExactPair, numbers: _Numbers) -> Row:
    width = numbers.subtract(value[1], value[0])
    oracle_width = numbers.subtract(oracle[1], oracle[0])
    return dict(width=str(width), lower_excess=str(numbers.subtract(oracle[0], value[0])),
                upper_excess=str(numbers.subtract(value[1], oracle[1])),
                excess_width=str(numbers.subtract(width, oracle_width)))


def _classification(a: ExactPair, b: ExactPair, contained: bool, numbers: _Numbers) -> str:
    if not contained:
        return "invalid-containment"
    if a == b:
        return "equal-enclosures"
    if numbers.le(b[0], a[0]) and numbers.le(a[1], b[1]):
        return "square-sum-strict-subset"
    if numbers.le(a[0], b[0]) and numbers.le(b[1], a[1]):
        return "product-sum-clipped-strict-subset"
    return "overlap-incomparable"


def _validate_contract(contract: Row) -> Row:
    caps = _row(contract.get("caps"), "caps")
    _need(all(type(caps.get(name)) is int and 0 < caps[name] <= maximum
              for name, maximum in _CAPS.items()), "caps exceed fixed design")
    context = _row(contract.get("context"), "context")
    _need(all(type(context.get(k)) is type(v) and context[k] == v
              for k, v in _CONTEXT.items() if k != "enabled_traps")
          and type(context.get("enabled_traps")) is list
          and all(type(item) is str for item in context["enabled_traps"])
          and sorted(context["enabled_traps"]) == _CONTEXT["enabled_traps"]
          and context.get("all_other_traps") is False
          and context.get("initial_flags") == "all cleared"
          and context.get("directed_rounding") == [ROUND_FLOOR, ROUND_CEILING]
          and context.get("allowed_final_flags") == ["Inexact", "Rounded"], "fixed Decimal context")
    selection = _row(contract.get("selection"), "selection")
    _need(_wire(selection.get("norm_pair_roles")) == _wire(_ROLES)
          and _wire(selection.get("selected_cells")) == _wire([dict(
              row_index=row, lo_deg=lo, hi_deg=hi, midpoint_deg=mid
          ) for row, lo, hi, mid in _SELECTION])
          and selection.get("selected_row_indices") == [62, 94, 125]
          and selection.get("domains") == ["cell", "singleton"]
          and selection.get("signs") == ["positive", "negative"]
          and selection.get("source_origins") == ["default", "independent"]
          and selection.get("vector_boxes") == 72
          and selection.get("structural_slots") == 36
          and selection.get("expected_trace_rows") == 24
          and selection.get("expected_trace_events") == 1248, "fixed matrix/role/unit contract")
    return caps


def _analyze(
    archive: Row,
    contract: Row,
    *,
    check: Callable[[], None],
    charge: Charge,
    scope: str | None = None,
    state: Row,
) -> Row:
    """Evaluate only local Cartesian norm boxes; caller authenticates source/archive bytes."""
    check()
    archive, contract = _row(archive, "archive"), _row(contract, "contract")
    caps = _validate_contract(contract)
    context = _row(archive.get("_context"), "authenticated context")
    scope = context.get("scope") if scope is None else scope
    _need(type(scope) is str and bool(scope) and context.get("scope") == scope, "scope")
    report = _row(archive.get("report"), "report")
    pins = _row(context.get("source_pins"), "source pins")
    _need(pins and all(type(v) is str and _HEX.fullmatch(v) for v in pins.values())
          and report.get("method_sha256") == pins and report.get("scope") == scope,
          "source/scope identity")
    expected_events = context.get("expected_events")
    _need(type(expected_events) is int and 0 < expected_events <= caps["input_event_records"]
          and _row(report.get("work"), "historical work").get("events") == expected_events,
          "historical event inventory")
    rows = report.get("rows")
    _need(type(rows) is list and len(rows) == 24, "fixed trace matrix")
    input_events = 0
    for value in rows:
        events = _row(_row(value, "trace row").get("trace"), "trace").get("events")
        _need(type(events) is list, "event list")
        input_events += len(events)
        _need(input_events <= caps["input_event_records"], "input event cap")
    numbers = _Numbers(caps, check)
    counts, progress = state["counts"], state["progress"]

    def charged(kind: str, amount: int = 1) -> None:
        check()
        charge(kind, amount)
        next_count = counts[kind] + amount
        _need(next_count <= caps[_CHARGE_CAPS[kind]], kind + " cap")
        counts[kind] = next_count

    traces: list[_Trace] = []
    for row_index, lo_cell, hi_cell, midpoint in _SELECTION:
        for domain in ("cell", "singleton"):
            lo, hi = (lo_cell, hi_cell) if domain == "cell" else (midpoint, midpoint)
            for sign in ("positive", "negative"):
                for independent in (False, True):
                    index = len(traces)
                    row = _row(rows[index], "trace row")
                    identity = dict(row_index=row_index, domain=domain, lo_deg=lo, hi_deg=hi,
                                    sign=sign, independent=independent)
                    _need(all(type(row.get(k)) is type(v) and row[k] == v for k, v in identity.items()),
                          "matrix identity/order")
                    traces.append(_trace(row, index, numbers, charged))
    _need(counts["event_visits"] == expected_events, "total saved event count")
    output: list[Row] = state["rows"]
    compatible, valid_containment = True, True
    for trace in traces:
        row = rows[trace.row]
        for role in _ROLES:
            charged("boxes")
            charged("descriptors")
            path = f"{role['parent_path']}/_norm2[{role['direct_norm2_ordinal']}]"
            _need(path in trace.starts and path in trace.ends, "missing selected norm")
            start, end = trace.starts[path], trace.ends[path]
            _need(set(start["fields"]) == {"v[0]", "v[1]", "v[2]"}
                  and "return" in end["fields"], "norm field inventory")
            raw_strings = [start["fields"][f"v[{i}]"][side] for i in range(3) for side in ("lo", "hi")]
            parsed = tuple(numbers.pair(start["fields"][f"v[{i}]"]) for i in range(3))
            operands = (parsed[0][0], parsed[1][0], parsed[2][0])
            exact = (parsed[0][1], parsed[1][1], parsed[2][1])
            _, saved = numbers.pair(end["fields"]["return"])
            input_sha256 = sha256(_wire(raw_strings)).hexdigest()
            methods: Row = {}
            final_intervals: dict[str, ExactPair] = {}
            progress["oracles"]["attempted"] += 1
            charged("oracles")
            progress["oracles"]["charged"] += 1
            oracle = _oracle(exact, numbers)
            progress["oracles"]["completed"] += 1
            oracle_width = numbers.subtract(oracle[1], oracle[0])
            for method in _METHODS:
                progress["methods"]["attempted"] += 1
                charged("methods")
                progress["methods"]["charged"] += 1
                kernel = _Kernel(numbers, charged)
                raw, final, method_context = kernel.evaluate(operands, method)
                final_exact = numbers.decimal(final[0]), numbers.decimal(final[1])
                contains = numbers.le(final_exact[0], oracle[0]) and numbers.le(oracle[1], final_exact[1])
                methods[method] = dict(input_sha256=input_sha256, raw=numbers.interval_record(raw),
                                       final=numbers.interval_record(final), context=method_context,
                                       metrics=_metrics(final_exact, oracle, numbers), contains_oracle=contains)
                final_intervals[method] = final_exact
                progress["methods"]["completed"] += 1
            charged("diagonals")
            own_method = _METHODS[1 if row["independent"] else 0]
            matched = final_intervals[own_method] == saved
            compatible = compatible and matched
            charged("comparisons")
            a, b = final_intervals[_METHODS[0]], final_intervals[_METHODS[1]]
            wa, wb = numbers.subtract(a[1], a[0]), numbers.subtract(b[1], b[0])
            ratio = str(numbers.divide(wb, wa)) if wa else None
            ratio_status = "finite" if wa else "both-widths-zero" if not wb else "denominator-zero-numerator-nonzero"
            contained = all(methods[method]["contains_oracle"] for method in _METHODS)
            valid_containment = valid_containment and contained
            classification = _classification(a, b, contained, numbers)
            call_pointer = f"/report/rows/{trace.row}/trace/events/{start['index']}"
            return_pointer = f"/report/rows/{trace.row}/trace/events/{end['index']}"
            output.append(dict(
                id=len(output), trace_row=trace.row, row_index=row["row_index"], domain=row["domain"],
                sign=row["sign"], source_origin="independent" if row["independent"] else "default",
                lo_deg=row["lo_deg"], hi_deg=row["hi_deg"], **role,
                source=dict(path=path, call=start["index"], **{"return": end["index"]},
                            call_pointer=call_pointer, return_pointer=return_pointer,
                            operand_pointers=[call_pointer + f"/fields/v[{i}]" for i in range(3)],
                            return_field_pointer=return_pointer + "/fields/return"),
                input=dict(raw_endpoint_strings=raw_strings, sha256=input_sha256),
                saved_return=dict(decimal=[end["fields"]["return"][side] for side in ("lo", "hi")],
                                  rational=[str(part) for part in saved]),
                methods=methods, oracle=dict(rational=[str(part) for part in oracle], width=str(oracle_width)),
                diagonal=dict(method=own_method, matches=matched),
                metrics=dict(width_square_sum=str(wa), width_product_sum_clipped=str(wb),
                             width_difference_product_minus_square=str(numbers.subtract(wb, wa)),
                             width_ratio_product_over_square=ratio, width_ratio_status=ratio_status),
                classification=classification,
            ))
    if not compatible:
        for row in output:
            row["classification"] = "inconclusive-compatibility-mismatch"
    check()
    return dict(schema="ariadna-matched-norm-v1", scope=scope,
                status="matched-norm-qualified-local-only" if compatible and valid_containment else "inconclusive",
                reason="compatibility-mismatch" if not compatible else None if valid_containment else "invalid-containment",
                context=_fingerprint(), rows=output, counts=counts, progress=progress)


class EvaluationError(ValueError):
    """Bounded failure evidence, including work attempted before a rejected charge."""

    progress: Row
    counts: Row
    partial_rows: list[Row]

    def __init__(self, message: str, state: Row) -> None:
        super().__init__(message)
        self.progress = {name: dict(value) for name, value in state["progress"].items()}
        self.counts = dict(state["counts"])
        self.partial_rows = list(state["rows"])


def analyze(
    archive: Row,
    contract: Row,
    *,
    check: Callable[[], None],
    charge: Charge,
    scope: str | None = None,
) -> Row:
    """Evaluate bounded local norm boxes; expose charged/attempted work on failure."""
    state: Row = dict(
        counts=dict.fromkeys(_CHARGE_CAPS, 0),
        progress={name: dict(attempted=0, charged=0, completed=0)
                  for name in ("methods", "oracles")},
        rows=[],
    )
    try:
        return _analyze(archive, contract, check=check, charge=charge, scope=scope, state=state)
    except (ValueError, ArithmeticError) as error:
        raise EvaluationError(str(error), state) from error
