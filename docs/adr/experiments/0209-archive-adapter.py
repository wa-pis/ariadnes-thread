"""Authenticate and normalize ADR0207 inputs; no seed or live execution entry point."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any, Callable, Mapping

type Row = dict[str, Any]  # JSON input and evidence boundary
type Six = tuple[float, float, float, float, float, float]

R1 = "0119-m2-reference.json"
R4 = "0098-central-correction-study.json"
AUDIT = "0136-retained-boundary-audit.json"
SEED = "0079-research-reference.json"
FRACTIONS = "0101-central-damping-study.json"
CONTRACT = "0205-design-fixed-command-physical-join.md"
RETAINED_PINS = {
    R1: "3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0",
    R4: "b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057",
    AUDIT: "81d78ecf6e4e80b55e9d909f929a879b2e392667387ec2569632aa99a6b41063",
    SEED: "17f03d9557be6e439af5f1c388e1eb092f55236b3c2afc3de65006d5f639c235",
    FRACTIONS: "70bd01122433fea421d27b44edd9bc1f5324e834aa80f8979af4e2d3b6af9c07",
    CONTRACT: "4ced4dab487bfe5a06ef70e9dd56341d78a35e8aa1ec759b0cd40a1ac2126b6d",
}
INPUT_LIMIT = 512 * 1024
TDB = "TDB seconds since J2000"
MODEL = ("ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-"
         "cannonball-srp-schwarzschild-direct-spice-v2")
SPACECRAFT = dict(initial_mass_kg=2000., dry_mass_kg=500., max_thrust_n=1000.,
                  isp_s=450., srp_area_m2=20., reflectivity_coefficient=1.3)
COMMAND_KEYS = tuple(f"{leg}_{param}" for leg in ("departure", "arrival")
                     for param in ("azimuth_rad", "elevation_rad", "duration_s"))
BOUNDARIES = (
    ("departure", "Moon", "departure-ignition", "departure_orbit", 4902800121846.8, 1737400., 1737400.),
    ("arrival", "Mars", "arrival-cutoff", "target_orbit", 42828375815756.1, 3389500., 3396190.),
)


class ArchiveInputError(ValueError):
    """A pinned archive cannot supply normalized command inputs."""


@dataclass(frozen=True, slots=True)
class ArchiveProfile:
    """Expected candidate and exact epoch words for an archive, including artificial mirrors."""

    candidate_id: str
    epoch_words: tuple[str, str, str]


RETAINED_PROFILE = ArchiveProfile("d0001-t0035", (
    "0x1.d2d247f9d7e7ap+29", "0x1.d2d4a9afb54adp+29", "0x1.ded341cb4c44bp+29",
))


def need(ok: object, reason: str) -> None:
    if not ok:
        raise ArchiveInputError(reason)


def load(path: Path, room: int) -> bytes:
    need(room >= 0, "aggregate byte cap")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        entry = os.fstat(stream.fileno())
        need(stat.S_ISREG(entry.st_mode) and 0 < entry.st_size <= room, f"{path.name}: byte cap or file type")
        raw = stream.read(room + 1)
    need(len(raw) <= room and len(raw) == entry.st_size, f"{path.name}: size changed")
    return raw


def pairs(rows: list[tuple[str, Any]]) -> Row:
    out: Row = {}
    for key, value in rows:
        need(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def invalid_constant(word: str) -> None:
    raise ArchiveInputError(f"nonfinite JSON token: {word}")


def object_record(raw: bytes) -> Row:
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
    need(isinstance(value, dict), "archive object required")
    return value


def same(a: object, b: object) -> bool:
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def number(value: object) -> float:
    need(type(value) in (int, float), "finite numeric field required")
    result = float(value)
    need(math.isfinite(result), "nonfinite input")
    return result


def vector(values: Any, count: int) -> tuple[float, ...]:
    need(isinstance(values, list) and len(values) == count, "archive vector shape")
    return tuple(number(value) for value in values)


def exact(text: object) -> Fraction:
    need(isinstance(text, str) and 1 <= len(text) <= 384, "decimal coordinate required")
    value = Decimal(text)
    need(value.is_finite() and abs(value.adjusted()) <= 400, "nonfinite or unbounded decimal coordinate")
    return Fraction(value)


def state(record: Row, epoch: float, utc: str, key: str, label: str) -> tuple[float, ...]:
    need(record["origin"] == "SSB" and record["orientation"] == "J2000"
         and record[key] == label and record["epoch_utc"] == utc
         and number(record["epoch_tdb_s"]).hex() == epoch.hex(), f"{label}: frame, label or epoch")
    return vector(record["position_m"], 3) + vector(record["velocity_m_s"], 3)


def within(a: tuple[Fraction, ...], b: tuple[Fraction, ...], pos: str, vel: str) -> bool:
    limits = (Fraction(pos), Fraction(vel))
    return all(sum((x-y)**2 for x, y in zip(a[i:i+3], b[i:i+3], strict=True)) <= limit**2
               for i, limit in zip((0, 3), limits, strict=True))


def audit_vector(row: Row, field: str) -> tuple[Fraction, ...]:
    value = row[field]
    need(isinstance(value, list) and len(value) == 6, f"{field}: six components")
    return tuple(exact(x) for x in value)


def pick_epochs(raw: bytes, profile: ArchiveProfile, pins: Mapping[str, str]) -> tuple[float, float, float]:
    text = raw.decode("utf-8")
    need(f"`{MODEL}`" in text, "force model in contract")
    for name in (R1, R4, AUDIT):
        line = f"| [{name}](experiments/{name}) | `{pins[name]}` |"
        need(text.splitlines().count(line) == 1, f"{name}: contract lineage")
    times: list[float] = []
    for event, expected in zip(("t0", "t*", "tf"), profile.epoch_words, strict=True):
        pattern = r"^\| " + re.escape(event) + r" = ([0-9.]+) \(`([^`]+)`\) \|"
        matches = re.findall(pattern, text, flags=re.M)
        need(len(matches) == 1, f"{event}: exact event row")
        label, word = matches[0]
        epoch = number(float.fromhex(word))
        need(epoch.hex() == word == expected and float(label).hex() == word, f"{event}: exact event word")
        times.append(epoch)
    need(times[0] < times[1] < times[2], "fixed event order")
    return times[0], times[1], times[2]


def history_words(values: Any) -> Six:
    az_d, el_d, td, az_a, el_a, ta = vector(values, 6)
    need(all(-math.pi <= a < math.pi for a in (az_d, az_a))
         and all(abs(e) <= math.pi/2 for e in (el_d, el_a))
         and min(td, ta) > 0, "noncanonical rejected command")
    return az_d, el_d, td, az_a, el_a, ta


def rejected_controls(seed: Row, central: Row, fractions: Row, pins: Mapping[str, str]) -> list[list[str]]:
    for record in (seed, central, fractions):
        need(record["origin"] == "SSB" and record["orientation"] == "J2000" and record["units"] == "SI"
             and record["time_scale"] == TDB and record["research_only"] is True, "rejected command provenance")
    need(seed["force_model_id"] == MODEL and seed["outcome"] == "completed"
         and seed["numerical_agreement"] is False, "baseline outcome")
    named = seed["seed_commands"]
    need(set(named) == set(COMMAND_KEYS), "named rejected command shape")
    original = history_words([named[k] for k in COMMAND_KEYS])
    rejected = [original]
    for record, roles in ((central, ["baseline", "central-trial"]),
                          (fractions, ["baseline", "fraction-0.5", "fraction-0.25"])):
        need(record["reference_sha256"] == record["expected_reference_sha256"] == pins[SEED]
             and record["outcome"] == "not-improving" and record["selected_alpha"] is None
             and record["numerical_agreement"] is None and record["control_units"] == ["rad", "rad", "s"]*2,
             "correction history linkage or status")
        runs = record["runs"]
        need([row["role"] for row in runs] == roles and history_words(runs[0]["controls"]) == original,
             "correction roles or baseline")
        rejected.extend(history_words(row["controls"]) for row in runs[1:])
    need(fractions["central_step_sha256"] == fractions["expected_central_step_sha256"] == pins[R4],
         "fractions central source")
    # Collapse semantic signed zero for comparison with later proposed command words.
    return [[(0.0 if value == 0 else value).hex() for value in cmd] for cmd in dict.fromkeys(rejected)]


def normalize_boundaries(first: Row, central: Row, audit: Row, scenario: Row,
                         selected: Row, times: tuple[float, float, float],
                         pins: Mapping[str, str]) -> list[Row]:
    need(audit["record"] == "ADR0136" and audit["contract"] == "ADR0135" and audit["status"] == "passed"
         and audit["finalization_gate"] == "passed" and audit["input_equality"] is True
         and all(type(audit[k]) is int and audit[k] == 0 for k in ("native_imports_or_calls", "spacecraft_propagations"))
         and audit["input_sha256"] == {key: pins[key] for key in (R1, R4)}
         and audit["units"] == dict(position="m", velocity="m/s", gm="m^3/s^2", epoch=TDB)
         and audit["frames"] == dict(relative="body-relative J2000", absolute="SSB/J2000"), "R4 audit status or lineage")
    run = central["runs"][0]["run"]
    endpoints = (run["boundaries"][0], run["target_state"])
    result = []
    for spec, row, endpoint, epoch in zip(BOUNDARIES, audit["rows"], endpoints, times[::2], strict=True):
        leg, body, label, orbit, gm, shape, guard = spec
        source = first["endpoints"][leg]["body_state"]
        utc = selected[f"{leg}_epoch_utc"]
        need(isinstance(utc, str) and utc.endswith("Z")
             and number(selected[f"{leg}_epoch_tdb_s"]).hex() == epoch.hex(), f"{leg}: candidate epoch")
        endpoint_si = state(endpoint, epoch, utc, "label", label)
        body_si = state(source, epoch, utc, "body", body)
        need(row["body"] == body and same(row["stored_body"], source) and same(row["stored_endpoint"], endpoint)
             and same(row["orbit"], scenario[orbit]) and number(row["gm_m3_s2"]) == gm
             and number(row["shape_radius_m"]) == shape, f"{leg}: audit operand, phase or constants")
        delta = tuple(Fraction(a)-Fraction(b) for a, b in zip(endpoint_si, body_si, strict=True))
        relative = audit_vector(row, "retained_relative_exact")
        algebraic = tuple(map(Fraction, vector(row["binary64_relative"], 6)))
        high = audit_vector(row, "decimal80_relative")
        refine = audit_vector(row, "decimal100_relative")
        need(delta != (0,)*6 and delta == relative and within(high, refine, "1e-12", "1e-15")
             and all(within(relative, v, "0.001", "1e-6") for v in (algebraic, high, refine)),
             f"{leg}: relative reconstruction")
        excess = vector(selected[f"{leg}_v_infinity_m_s"], 3)
        need(excess != (0,)*3, f"{leg}: zero excess")
        result.append(dict(body=body, epoch_word=epoch.hex(), epoch_tdb_s=epoch, epoch_utc=utc, label=label,
                           body_ssb_si=body_si, endpoint_ssb_si=endpoint_si, relative_si=row["retained_relative_exact"],
                           orbit_relative_si=row["decimal80_relative"], v_infinity_m_s=excess, gm_m3_s2=gm,
                           shape_radius_m=shape, guard_m=guard, orbit=scenario[orbit]))
    return result


def prepare(paths: Mapping[str, Path], pins: Mapping[str, str], profile: ArchiveProfile,
            *, check_deadline: Callable[[], None]) -> Row:
    """Read six externally pinned files and normalize selectors without running any solver."""
    check_deadline()
    need(set(paths) == set(RETAINED_PINS) == set(pins), "exact six named archive sources required")
    if profile.candidate_id == RETAINED_PROFILE.candidate_id:
        need(profile == RETAINED_PROFILE and pins == RETAINED_PINS, "fixed retained trust pins and epochs")
    else:
        need(not (set(pins.values()) & set(RETAINED_PINS.values())), "mixed retained and artificial source pins")
    raw: dict[str, bytes] = {}
    total = 0
    try:
        for name in RETAINED_PINS:
            check_deadline()
            path, pin = paths[name], pins[name]
            need(path.name == name and isinstance(pin, str) and re.fullmatch("[a-f0-9]{64}", pin),
                 f"{name}: expected path or pin")
            data = load(path, INPUT_LIMIT - total)
            need(sha256(data).hexdigest() == pin, f"{name}: source digest mismatch")
            total += len(data)
            raw[name] = data
        check_deadline()
        times = pick_epochs(raw[CONTRACT], profile, pins)
        r1 = object_record(raw[R1])
        central, seed, fractions = (object_record(raw[name])["science"] for name in (R4, SEED, FRACTIONS))
        a, b = r1["runs"]
        scenario, selected = r1["normalized_scenario"], a["selected"]
        need(r1["status"] == "passed" and r1["reference_id"] == "r1-m2-reserve-reference"
             and r1["identical_scientific_payloads"] is True and same(b["selected"], selected)
             and same(a["endpoints"], b["endpoints"]), "R1 archived repeatability")
        need(selected["candidate_id"] == profile.candidate_id == seed["candidate_id"]
             and all(same(x["candidate"], selected) for x in (central, fractions))
             and all(same(x["scenario"], scenario) for x in (central, seed, fractions)), "source candidate or scenario")
        craft = scenario["spacecraft"]
        need(all(number(craft[key]) == expected for key, expected in SPACECRAFT.items()), "fixed spacecraft")
        history = rejected_controls(seed, central, fractions, pins)
        endpoints = normalize_boundaries(a, central, object_record(raw[AUDIT]), scenario, selected, times, pins)
        check_deadline()
        return dict(schema="ariadna-r559c-normalized-input-v1", status="archive-inputs-validated",
                    scope="retained" if profile == RETAINED_PROFILE else "artificial",
                    candidate_id=profile.candidate_id, source_pins=dict(pins), source_bytes=total,
                    epochs_tdb_s=times, epoch_words=profile.epoch_words, model_id=MODEL,
                    origin="SSB", orientation="J2000", time_scale=TDB, units="SI",
                    spacecraft=dict(SPACECRAFT), endpoints=endpoints, rejected_command_words=history,
                    command_words=None, live_authorized=False)
    except ArchiveInputError:
        raise
    except (KeyError, TypeError, IndexError, ValueError, OSError, OverflowError, InvalidOperation, RecursionError) as exc:
        raise ArchiveInputError(f"invalid archive input: {exc}") from exc
