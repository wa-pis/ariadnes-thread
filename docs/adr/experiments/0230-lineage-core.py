"""Describe authenticated saved trace lineage without evaluating its formulas."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
import json
from math import gcd
import re
from typing import Any

type Row = dict[str, Any]
type Charge = Callable[[str, int], None]

_STAGES = (
    "bounds",
    "_ellipse",
    "_reverse",
    "_unit",
    "_cross",
    "_norm2",
    "_mass_exclusion",
    "_clearance",
    "_binary64",
)
_CHILDREN = {
    "_ellipse": ["_cross", "_cross"],
    "_unit": ["_norm2"],
    "_cross": [],
    "_norm2": [],
    "_binary64": [],
    "_reverse": [
        "_unit",
        "_unit",
        "_cross",
        "_norm2",
        "_norm2",
        "_cross",
        "_norm2",
        "_norm2",
        "_unit",
        "_cross",
        "_cross",
        "_norm2",
    ],
    "_mass_exclusion": ["_binary64", "_binary64"],
}
_CHECKPOINTS = {
    "_ellipse": {
        "anomaly": "rad",
        "radius": "m",
        "return[0][0]": "m",
        "return[0][1]": "m",
        "return[0][2]": "m",
        "return[1][0]": "m/s",
        "return[1][1]": "m/s",
        "return[1][2]": "m/s",
    },
    "_mass_exclusion": {
        "coast": "kg",
        "durations[0]": "s",
        "durations[1]": "s",
        "final": "kg",
    },
    "_reverse": {
        "radius": "m",
        "return[0]": "m/s",
        "return[1]": "m/s",
        "return[2]": "m/s",
        "root": "m2/s",
    },
    "bounds": {"speed": "m/s"},
}
_ALIASES = [
    dict(
        source="_ellipse.return.return[0][i]",
        targets=["_reverse.call.r[i]", "_reverse.return.r[i]", "bounds.return.r[i]"],
        units="m",
    ),
    dict(
        source="_ellipse.return.return[1][i]",
        targets=["bounds.return.orbital[i]"],
        units="m/s",
    ),
    dict(
        source="_ellipse.return.return[2]",
        targets=["_reverse.call.mu", "_reverse.return.mu", "bounds.return.mu"],
        units="m3/s2",
    ),
    dict(
        source="_ellipse.call.anomaly",
        targets=["_ellipse.return.anomaly", "bounds.return.anomaly"],
        units="rad",
    ),
    dict(
        source="_reverse.return.return[i]",
        targets=["bounds.return.future[i]"],
        units="m/s",
    ),
    dict(
        source="bounds.return.speed",
        targets=["_mass_exclusion.call.arrival", "_mass_exclusion.return.arrival"],
        units="m/s",
    ),
]
_ROLES = [
    dict(
        direct_norm2_ordinal=0,
        operand_units="m/s",
        parent_path="bounds",
        result_units="m2/s2",
        role="impulse-squared",
    ),
    dict(
        direct_norm2_ordinal=1,
        operand_units="m",
        parent_path="bounds/_reverse[0]",
        result_units="m2",
        role="radius-squared",
    ),
    dict(
        direct_norm2_ordinal=4,
        operand_units="m2/s",
        parent_path="bounds/_reverse[0]",
        result_units="m4/s2",
        role="angular-momentum-squared",
    ),
]
_SELECTION = [
    (62, "150", "4801/32", "9601/64"),
    (94, "151", "4833/32", "9665/64"),
    (125, "4863/32", "152", "9727/64"),
]
_RISKS = [
    "Common-anomaly geometry reuses phase-dependent operands.",
    "Normalization and signed-root reconstruction reuse dependent vectors.",
    "Coast/final-mass expressions share departure and arrival operands.",
]
_LIMIT = "No contribution to final width or dominant cause is established."
_DECIMAL = re.compile(r"-?(?:\d+(?:\.\d*)?|\.\d+)(?:E[+-]?\d+)?\Z", re.ASCII)


def _need(condition: object, message: str) -> None:
    if not condition:
        raise ValueError("saved lineage: " + message)


def _same(left: Any, right: Any) -> bool:
    return json.dumps(
        left, sort_keys=True, separators=(",", ":"), allow_nan=False
    ) == json.dumps(right, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _row(value: Any, name: str) -> Row:
    _need(type(value) is dict and all(type(k) is str for k in value), name + " object")
    return value


def _required(stage: str) -> set[str]:
    scalars = {
        "_ellipse": "anomaly mu peri e sin_i cos_i sin_o cos_o sin_u cos_u sin_nu cos_nu a p h radius u t return[2]",
        "_reverse": "mu radius linear constant discriminant_sq disc root",
        "_norm2": "return",
        "_mass_exclusion": "departure arrival init coast final rate durations[0] durations[1] observed_duration_binary64[0] observed_duration_binary64[1]",
        "_clearance": "mu surface radius radial minimum return[0] return[1] return[2]",
        "bounds": "anomaly mu speed",
        "_cross": "",
        "_unit": "",
        "_binary64": "",
    }
    vectors = {
        "_ellipse": "node normal onto_plane radial_hat transverse_hat return[0] return[1]",
        "_reverse": "r given v_inf r_hat direction normal signed_h e_inf return",
        "_norm2": "v",
        "_unit": "v return",
        "_cross": "a b return",
        "_clearance": "r v r_hat",
        "bounds": "r orbital future",
        "_mass_exclusion": "",
        "_binary64": "",
    }
    return set(scalars[stage].split()) | {
        f"{name}[{i}]" for name in vectors[stage].split() for i in range(3)
    }


@dataclass(frozen=True, slots=True)
class _Numbers:
    caps: Row
    check: Callable[[], None]

    def bounded(self, value: Fraction) -> Fraction:
        self.check()
        bits = self.caps["rational_component_bits"]
        _need(
            value.numerator.bit_length() <= bits
            and value.denominator.bit_length() <= bits,
            "rational component cap",
        )
        return value

    def endpoint(self, value: Any) -> Fraction:
        self.check()
        _need(
            type(value) is str and 0 < len(value) <= self.caps["endpoint_text_chars"],
            "endpoint text cap",
        )
        _need(_DECIMAL.fullmatch(value), "canonical finite endpoint")
        mantissa, _, exponent = value.partition("E")
        _need(
            sum(c.isdigit() for c in mantissa)
            <= self.caps["decimal_significand_digits"],
            "decimal significand cap",
        )
        _need(not exponent or len(exponent.lstrip("+-")) <= 4, "decimal exponent cap")
        _need(
            not exponent
            or abs(int(exponent)) <= self.caps["absolute_decimal_exponent"],
            "decimal exponent cap",
        )
        decimal = Decimal(value)
        _need(
            decimal.is_finite() and str(decimal) == value, "canonical finite endpoint"
        )
        digits = len(decimal.as_tuple().digits)
        power = decimal.as_tuple().exponent
        _need(
            type(power) is int and abs(power) <= self.caps["absolute_decimal_exponent"],
            "decimal exponent cap",
        )
        _need(
            4 * (digits + max(0, power)) <= self.caps["rational_component_bits"]
            and 4 * max(0, -power) + 1 <= self.caps["rational_component_bits"],
            "rational component cap before conversion",
        )
        return self.bounded(Fraction(decimal))

    def subtract(self, a: Fraction, b: Fraction) -> Fraction:
        self.check()
        common = gcd(a.denominator, b.denominator)
        left, right = b.denominator // common, a.denominator // common
        bits = self.caps["rational_component_bits"]
        _need(
            a.denominator.bit_length() + left.bit_length() <= bits
            and max(
                a.numerator.bit_length() + left.bit_length(),
                b.numerator.bit_length() + right.bit_length(),
            )
            + 1
            <= bits,
            "rational subtraction cap before arithmetic",
        )
        return self.bounded(a - b)

    def divide(self, a: Fraction, b: Fraction) -> Fraction:
        self.check()
        _need(b != 0, "zero ratio denominator")
        first, second = gcd(a.numerator, b.numerator), gcd(a.denominator, b.denominator)
        bits = self.caps["rational_component_bits"]
        _need(
            (a.numerator // first).bit_length() + (b.denominator // second).bit_length()
            <= bits
            and (a.denominator // second).bit_length()
            + (b.numerator // first).bit_length()
            <= bits,
            "rational ratio cap before arithmetic",
        )
        return self.bounded(a / b)

    def pair(self, value: Any) -> Row:
        endpoint = _row(value, "endpoint")
        _need(set(endpoint) == {"lo", "hi"}, "endpoint inventory")
        _need(
            self.endpoint(endpoint["lo"]) <= self.endpoint(endpoint["hi"]),
            "endpoint order",
        )
        return endpoint


@dataclass(frozen=True, slots=True)
class _Trace:
    row: int
    starts: dict[str, Row]
    ends: dict[str, Row]
    early: bool

    def field(self, path: str, event: str, field: str) -> tuple[Row, str] | None:
        item = (self.starts if event == "call" else self.ends).get(path)
        if (
            item is None
            or item["event"] == "error"
            or path == "bounds"
            and event == "return"
            and self.early
        ):
            return None
        _need(field in item["fields"], "missing reached field " + path + "." + field)
        escaped = field.replace("~", "~0").replace("/", "~1")
        pointer = (
            f"/report/rows/{self.row}/trace/events/{item['index']}/fields/{escaped}"
        )
        return item["fields"][field], pointer

    def alias(self, descriptor: str) -> tuple[Row, str] | None:
        stage, event, field = descriptor.split(".", 2)
        return self.field(
            "bounds" if stage == "bounds" else f"bounds/{stage}[0]", event, field
        )


def _result_scalars(value: Any, path: str = "return", depth: int = 0) -> Row:
    _need(depth <= 8, "result nesting cap")
    if type(value) is dict:
        result: Row = {}
        for key, item in _row(value, "result").items():
            result.update(_result_scalars(item, path + "." + key, depth + 1))
        return result
    if type(value) is list:
        _need(len(value) <= 64, "result list cap")
        result = {}
        for i, item in enumerate(value):
            result.update(_result_scalars(item, f"{path}[{i}]", depth + 1))
        return result
    _need(value is None or type(value) in (bool, int, str), "result scalar")
    return {path: value}


def _trace(row: Row, index: int, numbers: _Numbers, charge: Charge) -> _Trace:
    numbers.check()
    trace = _row(row.get("trace"), "trace")
    content = {k: v for k, v in trace.items() if k != "seal"}
    seal = sha256(
        json.dumps(
            content, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()
    _need(type(trace.get("seal")) is str and trace["seal"] == seal, "trace seal")
    result = _row(trace.get("result"), "trace result")
    _need(result == row.get("control"), "trace/control identity")
    _need(
        all(
            type(trace.get(k)) is type(row[k]) and trace[k] == row[k]
            for k in ("sign", "independent")
        ),
        "trace input identity",
    )
    _need(
        trace.get("lo") == row["lo_deg"] and trace.get("hi") == row["hi_deg"],
        "trace domain",
    )
    events = trace.get("events")
    _need(
        type(events) is list and 0 < len(events) <= numbers.caps["input_event_records"],
        "event cap",
    )
    starts: dict[str, Row] = {}
    ends: dict[str, Row] = {}
    paths: dict[int, str] = {}
    children: dict[str, list[str]] = {}
    stack: list[int] = []
    inventory = {
        stage: dict(calls=0, returns=0, errors=0, status="not-reached")
        for stage in _STAGES
    }
    for event_index, raw in enumerate(events):
        numbers.check()
        charge("event_visits", 1)
        item = _row(raw, "event")
        _need(
            set(item)
            == {"index", "call", "parent", "stage", "event", "fields", "scalars"},
            "event inventory",
        )
        _need(
            type(item["index"]) is int
            and item["index"] == event_index
            and type(item["call"]) is int
            and (item["parent"] is None or type(item["parent"]) is int)
            and item["stage"] in _STAGES
            and item["event"] in ("call", "return", "error"),
            "event identity",
        )
        stage, call, kind = item["stage"], item["call"], item["event"]
        fields, scalars = (
            _row(item["fields"], "fields"),
            _row(item["scalars"], "scalars"),
        )
        for endpoint in fields.values():
            numbers.pair(endpoint)
        _need(
            all(
                value is None or type(value) in (bool, int, str)
                for value in scalars.values()
            )
            and all(
                (type(value) is not str or len(value) <= 4096)
                and (type(value) is not int or value.bit_length() <= 4096)
                for value in scalars.values()
            ),
            "scalar inventory",
        )
        if stage not in ("_cross", "_binary64"):
            _need(
                type(scalars.get("independent")) is bool
                and scalars["independent"] is trace["independent"],
                "local arithmetic path flag",
            )
        if stage == "_reverse":
            _need(scalars.get("sign") == trace["sign"], "local signed branch")
        if kind == "call":
            parent = stack[-1] if stack else None
            _need(
                call == len(paths)
                and (
                    item["parent"] is None
                    if parent is None
                    else type(item["parent"]) is int and item["parent"] == parent
                ),
                "call hierarchy",
            )
            if parent is None:
                _need(not paths and stage == "bounds", "root stage")
                path = "bounds"
            else:
                parent_path = paths[parent]
                ordinal = children[parent_path].count(stage)
                path = f"{parent_path}/{stage}[{ordinal}]"
                children[parent_path].append(stage)
            paths[call], starts[path], children[path] = path, item, []
            stack.append(call)
            inventory[stage]["calls"] += 1
        else:
            _need(
                bool(stack) and stack[-1] == call and call in paths, "return hierarchy"
            )
            stack.pop()
            path = paths[call]
            _need(
                path not in ends
                and item["parent"] == starts[path]["parent"]
                and stage == starts[path]["stage"],
                "return pairing",
            )
            _need(
                all(fields.get(k) == v for k, v in starts[path]["fields"].items()),
                "changed observed argument",
            )
            ends[path] = item
            inventory[stage]["errors" if kind == "error" else "returns"] += 1
    _need(not stack and starts.keys() == ends.keys(), "incomplete trace")
    for count in inventory.values():
        count["status"] = (
            "error"
            if count["errors"]
            else "complete"
            if count["returns"]
            else "not-reached"
        )
    _need(_same(trace.get("stages"), inventory), "stage inventory")
    early = "detail" in result
    _need(
        trace.get("status") == ("early-failure" if early else "complete")
        and (any(e["event"] == "error" for e in ends.values()) is early),
        "early failure disposition",
    )
    _need(ends["bounds"]["event"] == "return", "root return")
    _need(
        {k: v for k, v in ends["bounds"]["scalars"].items() if k.startswith("return.")}
        == _result_scalars(result),
        "observed result link",
    )
    _need(
        all(
            type(starts["bounds"]["scalars"].get(k)) is type(trace[k])
            and starts["bounds"]["scalars"][k] == trace[k]
            for k in ("lo", "hi", "sign", "independent")
        ),
        "observed input link",
    )
    for path, start in starts.items():
        numbers.check()
        end, stage = ends[path], start["stage"]
        if stage == "bounds":
            expected = ["_ellipse", "_reverse", "_norm2", "_mass_exclusion"]
            if result.get("reason") != "mass":
                expected += ["_clearance"]
        elif stage == "_clearance":
            expected = ["_norm2", "_unit"]
            radial = end["fields"].get("radial")
            if radial is not None and numbers.endpoint(radial["lo"]) < 0:
                expected += ["_cross", "_cross", "_norm2", "_norm2"]
        else:
            expected = _CHILDREN[stage]
        _need(
            children[path] == expected
            or (
                (end["event"] == "error" or early and stage == "bounds")
                and children[path] == expected[: len(children[path])]
            ),
            "source child role order",
        )
        if end["event"] == "return" and not (early and stage == "bounds"):
            _need(
                _required(stage) <= end["fields"].keys(),
                "missing required reached fields",
            )
    if not early:
        _need(result.get("reason") in (None, "mass", "guard"), "bound branch label")
        speed = ends["bounds"]["fields"]["speed"]
        _need(
            result.get("arrival_speed_bounds_m_s") == [speed["lo"], speed["hi"]],
            "speed result link",
        )
    return _Trace(index, starts, ends, early)


def analyze(
    archive: Row,
    contract: Row,
    *,
    scope: str,
    check: Callable[[], None],
    charge: Charge,
) -> Row:
    """Read fixed saved endpoints; caller authenticates bytes, source and context provenance."""
    check()
    _need(scope in ("retained", "artificial-saved-lineage"), "scope")
    archive, contract = _row(archive, "archive"), _row(contract, "contract")
    _need(
        set(archive)
        == {
            "attempt",
            "report",
            "receipt",
            "completion",
            "audit",
            "manifest",
            "selection_contract",
            "_context",
        },
        "archive inventory",
    )
    _need(
        _same(contract.get("checkpoint_fields"), _CHECKPOINTS)
        and _same(contract.get("alias_groups"), _ALIASES)
        and _same(contract.get("norm_pair_roles"), _ROLES),
        "source role/unit contract",
    )
    caps = _row(contract.get("future_caps"), "caps")
    numeric_limits = dict(
        endpoint_text_chars=1024,
        decimal_significand_digits=256,
        absolute_decimal_exponent=512,
        rational_component_bits=4096,
        input_event_records=8192,
    )
    _need(
        all(
            type(caps.get(k)) is int and 0 < caps[k] <= limit
            for k, limit in numeric_limits.items()
        ),
        "numeric caps",
    )
    context = _row(archive["_context"], "authenticated context")
    pins = _row(context.get("source_pins"), "source pins")
    _need(
        context.get("scope") == scope
        and context.get("context_justified") is True
        and context.get("context_assumption") == contract.get("context_provenance")
        and type(context.get("context_assumption")) is str,
        "conditional context provenance",
    )
    _need(
        set(pins) == set(contract["source_bindings"])
        and all(
            type(v) is str and re.fullmatch(r"[0-9a-f]{64}", v) for v in pins.values()
        ),
        "source identity",
    )
    report = _row(archive["report"], "report")
    _need(
        report.get("scope") == scope
        and all(report.get("method_sha256", {}).get(k) == v for k, v in pins.items()),
        "report source/scope identity",
    )
    expected_events = context.get("expected_events")
    _need(
        type(expected_events) is int
        and 0 < expected_events <= caps["input_event_records"]
        and _row(report.get("work"), "historical work").get("events")
        == expected_events,
        "historical event inventory",
    )
    if scope == "retained":
        _need(
            expected_events == contract["expected_retained"]["stage_events"],
            "retained event inventory",
        )
    selection = contract["expected_retained"]["selection"]
    _need(
        type(selection) is list
        and len(selection) == 3
        and [
            (
                s.get("row_index"),
                s.get("lo_deg"),
                s.get("hi_deg"),
                s.get("midpoint_deg"),
            )
            for s in selection
        ]
        == _SELECTION,
        "fixed selection",
    )
    rows = report.get("rows")
    _need(type(rows) is list and len(rows) == 24, "fixed trace matrix")
    numbers = _Numbers(caps, check)
    counts = dict(event_visits=0, descriptors=0, aliases=0, norm_pairs=0)

    def charged(kind: str, amount: int = 1) -> None:
        check()
        charge(kind, amount)
        counts[kind] += amount

    traces: list[_Trace] = []
    identities: dict[tuple[int, str, str, bool], int] = {}
    for spec in selection:
        for domain in ("cell", "singleton"):
            lo, hi = (
                (spec["lo_deg"], spec["hi_deg"])
                if domain == "cell"
                else (spec["midpoint_deg"],) * 2
            )
            for sign in ("positive", "negative"):
                for independent in (False, True):
                    index = len(traces)
                    row = _row(rows[index], "trace row")
                    expected = dict(
                        row_index=spec["row_index"],
                        domain=domain,
                        lo_deg=lo,
                        hi_deg=hi,
                        sign=sign,
                        independent=independent,
                    )
                    _need(
                        all(
                            type(row.get(k)) is type(v) and row[k] == v
                            for k, v in expected.items()
                        ),
                        "matrix identity/order",
                    )
                    traces.append(_trace(row, index, numbers, charged))
                    identities[spec["row_index"], domain, sign, independent] = index
    _need(counts["event_visits"] == expected_events, "total saved event count")
    lineage: list[Row] = []
    checkpoints: list[Row] = []
    values: dict[tuple[int, str, str], Fraction | None] = {}
    for index, trace in enumerate(traces):
        for group in contract["alias_groups"]:
            for i in range(3) if "[i]" in group["source"] else (None,):
                source = group["source"].replace("[i]", f"[{i}]")
                origin = trace.alias(source)
                for descriptor in group["targets"]:
                    target = descriptor.replace("[i]", f"[{i}]")
                    destination = trace.alias(target)
                    charged("aliases")
                    _need(
                        origin is None
                        or destination is None
                        or origin[0] == destination[0],
                        "source alias mismatch",
                    )
                    lineage.append(
                        dict(
                            row=index,
                            source=source,
                            target=target,
                            units=group["units"],
                            status="matched"
                            if origin is not None and destination is not None
                            else "not-reached",
                            **{
                                "from": origin[1] if origin else None,
                                "to": destination[1] if destination else None,
                            },
                        )
                    )
        for stage, fields in contract["checkpoint_fields"].items():
            for field, units in fields.items():
                path = "bounds" if stage == "bounds" else f"bounds/{stage}[0]"
                found = trace.field(path, "return", field)
                charged("descriptors")
                endpoint, pointer = found if found else (None, None)
                width = (
                    numbers.subtract(
                        numbers.endpoint(endpoint["hi"]),
                        numbers.endpoint(endpoint["lo"]),
                    )
                    if endpoint
                    else None
                )
                values[index, stage, field] = width
                checkpoints.append(
                    dict(
                        row=index,
                        stage=stage,
                        field=field,
                        units=units,
                        status="observed" if found else "not-reached",
                        pointer=pointer,
                        lo=endpoint["lo"] if endpoint else None,
                        hi=endpoint["hi"] if endpoint else None,
                        width=str(width) if width is not None else None,
                    )
                )
    comparisons: list[Row] = []
    for spec in selection:
        for sign in ("positive", "negative"):
            for independent in (False, True):
                cell, singleton = (
                    identities[spec["row_index"], domain, sign, independent]
                    for domain in ("cell", "singleton")
                )
                for stage, fields in contract["checkpoint_fields"].items():
                    for field, units in fields.items():
                        charged("descriptors")
                        a, b = (
                            values[cell, stage, field],
                            values[singleton, stage, field],
                        )
                        match = a is not None and b is not None
                        status = (
                            "matched"
                            if match
                            else "both-not-reached"
                            if a is None and b is None
                            else "cell-not-reached"
                            if a is None
                            else "singleton-not-reached"
                        )
                        comparisons.append(
                            dict(
                                row_index=spec["row_index"],
                                sign=sign,
                                independent=independent,
                                stage=stage,
                                field=field,
                                units=units,
                                cell=cell,
                                singleton=singleton,
                                status=status,
                                cell_width=str(a) if a is not None else None,
                                singleton_width=str(b) if b is not None else None,
                                difference=str(numbers.subtract(a, b))
                                if match
                                else None,
                                ratio=str(numbers.divide(a, b))
                                if match and b
                                else None,
                            )
                        )
    norm_pairs: list[Row] = []
    for spec in selection:
        for domain in ("cell", "singleton"):
            for sign in ("positive", "negative"):
                default, independent = (
                    identities[spec["row_index"], domain, sign, path]
                    for path in (False, True)
                )
                for role in contract["norm_pair_roles"]:
                    charged("norm_pairs")
                    path = (
                        f"{role['parent_path']}/_norm2[{role['direct_norm2_ordinal']}]"
                    )
                    sides = []
                    for trace_index in (default, independent):
                        trace = traces[trace_index]
                        result = trace.field(path, "return", "return")
                        operands = (
                            [trace.field(path, "call", f"v[{i}]") for i in range(3)]
                            if result
                            else []
                        )
                        sides.append((operands, result))
                    (a, ar), (b, br) = sides
                    status = "not-reached"
                    if ar is not None and br is not None:
                        _need(all(x is not None for x in a + b), "missing norm operand")
                        status = (
                            "input-confounded"
                            if [x[0] for x in a] != [x[0] for x in b]
                            else (
                                "no-local-difference-observed"
                                if ar[0] == br[0]
                                else "conditional-local-method-response"
                            )
                        )
                    norm_pairs.append(
                        dict(
                            row_index=spec["row_index"],
                            domain=domain,
                            sign=sign,
                            **role,
                            default=default,
                            independent=independent,
                            status=status,
                            default_operands=[x[1] for x in a] if ar else None,
                            independent_operands=[x[1] for x in b] if br else None,
                            default_result=ar[1] if ar else None,
                            independent_result=br[1] if br else None,
                            context_assumption=context["context_assumption"],
                            source_pins=dict(pins),
                            attribution_limit=_LIMIT,
                        )
                    )
    check()
    return dict(
        schema="ariadna-saved-lineage-v1",
        status="lineage-qualified-attribution-unresolved",
        scope=scope,
        lineage=lineage,
        checkpoints=checkpoints,
        comparisons=comparisons,
        norm_pairs=norm_pairs,
        risks=list(_RISKS),
        assumptions=[context["context_assumption"]],
        limitations=contract["interpretation_limits"],
        counts=counts,
    )
