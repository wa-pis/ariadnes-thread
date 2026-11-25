"""ADR0252 fixed synthetic native conformance; never a mission propagator."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
from typing import Any

from . import _coupled_benchmark_oracle as physical_oracle

_INPUT_BYTES = 64 * 1024
_OUTPUT_BYTES = 2 * 1024 * 1024
_RATE = 1000.0 / float(9.80665 * 450.0)
_MODES = ("departure-burn", "coast", "arrival-burn")
_EPOCHS = (0, 1000, 9000, 10000)


class ConformanceError(RuntimeError):
    """The fixed fixture is failed or unavailable, with no retry permission."""

    logs: dict[str, str]


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConformanceError(f"{field}: finite nonboolean number required")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ConformanceError(f"{field}: finite number required") from exc
    if not math.isfinite(result):
        raise ConformanceError(f"{field}: finite number required")
    return result


def _state(value: object) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != 7:
        raise ConformanceError("state: seven SI components required")
    state = tuple(_number(v, "state") for v in value)
    if state[6] < 500.0:
        raise ConformanceError("state: mass below500kg")
    from .trajectory import _build_tnw_basis
    try:
        _build_tnw_basis(state[:3], state[3:6])
    except ValueError as exc:
        raise ConformanceError(f"state: degenerate TNW: {exc}") from exc
    return state


@dataclass(frozen=True, slots=True)
class NativeRequest:
    mode: str
    start_s: Fraction
    end_s: Fraction
    start_state: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.mode not in _MODES:
            raise ConformanceError("mode: explicit departure/coast/arrival required")
        if type(self.start_s) is not Fraction or type(self.end_s) is not Fraction:
            raise ConformanceError("events: exact Fraction required")
        if self.start_s == self.end_s:
            raise ConformanceError("events: positive directed span required")
        object.__setattr__(self, "start_state", _state(self.start_state))

    @property
    def direction(self) -> int:
        return 1 if self.end_s > self.start_s else -1


def admit_transport(request: NativeRequest) -> None:
    for event in (request.start_s, request.end_s):
        try:
            label = _number(float(event), "event label")
        except OverflowError as exc:
            raise ConformanceError("unavailable-transport: event overflow") from exc
        if Fraction(label) != event:
            raise ConformanceError("unavailable-transport: exact event not representable")
    if request.direction * (float(request.end_s) - float(request.start_s)) <= 0:
        raise ConformanceError("unavailable-transport: collapsed event labels")


@dataclass(slots=True)
class Budget:
    started_s: float
    clock: Callable[[], float] = time.monotonic
    native_attempts: int = 0
    provider_attempts: int = 0
    contexts_created: int = 0
    contexts_closed: int = 0
    failed: bool = False
    previous_s: float | None = None
    output_bytes: int = 0
    spice_queries: int = 0
    kernel_reads: int = 0
    real_archive_reads: int = 0

    def _time(self, limit_s: float) -> None:
        previous_failure = self.failed
        self.failed = True
        try:
            now = _number(self.clock(), "monotonic clock")
        except (ValueError, RuntimeError, TypeError, OverflowError, OSError) as exc:
            raise ConformanceError(f"monotonic clock failed: {exc}") from exc
        started = _number(self.started_s, "started_s")
        if now < started or (self.previous_s is not None and now < self.previous_s):
            self.failed = True
            raise ConformanceError("monotonic clock moved backwards")
        self.previous_s = now
        if now - started >= limit_s:
            raise ConformanceError("deadline exceeded")
        self.failed = previous_failure

    def check(self) -> None:
        if self.failed:
            raise ConformanceError("fixture already failed")
        self._time(45.0)

    def check_finalization(self) -> None:
        self._time(60.0)

    def charge_native(self) -> None:
        self.check()
        if self.native_attempts >= 6:
            self.failed = True
            raise ConformanceError("native attempt cap6")
        self.native_attempts += 1

    def charge_provider(self) -> None:
        self.check()
        if self.provider_attempts >= 100000:
            self.failed = True
            raise ConformanceError("provider entry cap100000")
        self.provider_attempts += 1

    def check_output_bytes(self, data: bytes) -> None:
        self.check_finalization()
        if self.output_bytes + len(data) > _OUTPUT_BYTES:
            self.failed = True
            raise ConformanceError("combined output byte cap2MiB")
        self.output_bytes += len(data)

    def snapshot(self) -> dict[str, object]:
        return {
            "native_attempts": self.native_attempts,
            "provider_attempts": self.provider_attempts,
            # Logical runner-scope exits do not prove C++ graph destruction.
            "contexts_created": self.contexts_created, "contexts_closed": self.contexts_closed,
            "spice_queries": self.spice_queries, "kernel_reads": self.kernel_reads,
            "real_archive_reads": self.real_archive_reads,
            "optimizer_entries": 0,
        }


def reported_functions(history: Mapping[object, object]) -> int:
    if not isinstance(history, Mapping) or not history:
        raise ConformanceError("native function telemetry missing")
    counts = []
    for epoch, count in history.items():
        _number(epoch, "telemetry epoch")
        if isinstance(count, bool) or not isinstance(count, (int, float)):
            raise ConformanceError("native function count: nonnegative integer required")
        number = _number(count, "native function count")
        if number < 0 or number != int(number):
            raise ConformanceError("native function count: nonnegative integer required")
        counts.append(int(number))
    return max(counts)


def _event_observation(
    exact_s: Fraction, native_time: Any, time_factory: Callable[[float], Any],
) -> dict[str, object]:
    label = float(exact_s)
    expected_time = time_factory(label)
    return {
        "requested": [exact_s.numerator, exact_s.denominator], "label_hex": label.hex(),
        "observed_label_s": _number(native_time.to_float(), "native label"),
        "native_equal": bool(native_time == expected_time),
        "residual_s": _number((native_time - expected_time).to_float(), "native residual"),
    }


def read_arc(
    simulator: Any, request: NativeRequest, time_factory: Callable[[float], Any],
) -> dict[str, object]:
    """Read native keys by direction; near equality never creates exact identity."""
    admit_transport(request)
    try:
        if simulator.integration_completed_successfully is not True:
            raise ConformanceError("native integration incomplete")
        history = simulator.state_history_time_object
        if not history or len(history) < 2:
            raise ConformanceError("native history missing start/end")
        ordered = sorted(history, reverse=request.direction < 0)
        for key in ordered:
            _number(key.to_float(), "native history epoch")
            values = history[key]
            flatten = getattr(values, "reshape", None)
            _state(tuple(flatten(-1) if callable(flatten) else values))
        ends = []
        for exact, key in ((request.start_s, ordered[0]), (request.end_s, ordered[-1])):
            ends.append(_event_observation(exact, key, time_factory))
        start_raw, end_raw = history[ordered[0]], history[ordered[-1]]
        def values(raw: Any) -> list[float]:
            flatten = getattr(raw, "reshape", None)
            return list(_state(tuple(flatten(-1) if callable(flatten) else raw)))
        if [v.hex() for v in values(start_raw)] != [v.hex() for v in request.start_state]:
            raise ConformanceError("native initial state/mass was reset")
        return {
            "mode": request.mode, "direction": request.direction,
            "start_event": ends[0], "end_event": ends[1],
            "start_state": values(start_raw), "end_state": values(end_raw),
            "provider_attempts": 0,
            "native_reported_function_evaluations": reported_functions(
                simulator.cumulative_number_of_function_evaluations),
            "samples_checked": len(history),
        }
    except ConformanceError:
        raise
    except Exception as exc:
        raise ConformanceError(f"native history read failed: {exc}") from exc


def native_arc(request: NativeRequest, budget: Budget) -> dict[str, object]:
    """One fresh synthetic native context, with no kernels or ephemerides acquired."""
    try:
        admit_transport(request)
        budget.check()
        import numpy as np
        import tudatpy
        from tudatpy.astro.time_representation import Time
        from tudatpy.dynamics import environment_setup, propagation_setup, simulator
        from . import trajectory
        from .models import SpacecraftSpec
        if tudatpy.__version__ != "1.0.0" or np.__version__ != "1.26.4":
            raise ConformanceError("pinned native runtime mismatch")
        settings = environment_setup.BodyListSettings("SSB", "J2000")
        settings.add_empty_settings("Spacecraft")
        settings.get("Spacecraft").constant_mass = request.start_state[6]
        for name in ("Moon", "Mars"):
            settings.add_empty_settings(name)
            settings.get(name).ephemeris_settings = environment_setup.ephemeris.constant(
                np.zeros(6), "SSB", "J2000")
        bodies = environment_setup.create_system_of_bodies(settings)
        for name in ("Moon", "Mars"):
            bodies.get(name).state_in_base_frame_from_ephemeris(Time(float(request.start_s)))
        def gravity(epoch_s: float) -> Any:
            budget.charge_provider()
            _number(epoch_s, "provider epoch")
            body = bodies.get("Spacecraft")
            _state(tuple(float(v) for v in np.asarray(body.state).reshape(-1))
                   + (float(body.mass),))
            return np.asarray((0.0, 0.1, 0.0))
        forces = [propagation_setup.acceleration.custom_acceleration(gravity)]
        burn_id = "departure" if request.mode == "departure-burn" else "arrival"
        if request.mode != "coast":
            spacecraft = SpacecraftSpec(
                initial_mass_kg=request.start_state[6], dry_mass_kg=500.0,
                max_thrust_n=1000.0, isp_s=450.0, srp_area_m2=20.0,
                reflectivity_coefficient=1.3, maneuver_magnitude_sigma_fraction=0.001,
                maneuver_pointing_sigma_rad=0.001,
            )
            engine = trajectory._install_tnw_engine(
                "synthetic-native-conformance", bodies, spacecraft, burn_id, 0.0, 0.0)
            forces.append(propagation_setup.acceleration.thrust_from_engine(engine))
        accelerations = propagation_setup.create_acceleration_models(
            bodies, {"Spacecraft": {"Spacecraft": forces}}, ["Spacecraft"], ["SSB"])
        profile = trajectory._arc_integrator_profile(
            "synthetic-native-conformance", request.mode, tighter=True)
        profile["initial_step_s"] *= request.direction
        integrator = trajectory._build_integrator_from_profile(
            "synthetic-native-conformance", request.mode, profile)
        termination = propagation_setup.propagator.time_termination(
            float(request.end_s), terminate_exactly_on_final_condition=True)
        coupled = trajectory._build_coupled_arc_settings(
            "synthetic-native-conformance", bodies, accelerations, request.start_state[:6],
            request.start_state[6], float(request.start_s), integrator, termination,
            thrust_enabled=request.mode != "coast")
        before = budget.provider_attempts
        budget.charge_native()
        result = simulator.create_dynamics_simulator(bodies, coupled)
        budget.check()
        row = read_arc(result, request, Time)
        row["provider_attempts"] = budget.provider_attempts - before
        return row
    except ConformanceError:
        budget.failed = True
        raise
    except Exception as exc:
        budget.failed = True
        raise ConformanceError(f"synthetic native arc failed: {exc}") from exc


def _runtime() -> dict[str, object]:
    versions = {}
    for name in ("tudatpy", "numpy"):
        receipts = list((Path(sys.prefix) / "conda-meta").glob(f"{name}-*.json"))
        if len(receipts) != 1:
            raise ConformanceError(f"pinned Conda receipt unavailable: {name}")
        receipt = json.loads(receipts[0].read_text())
        versions[name] = receipt["version"]
    paths = ("_native_arc_conformance.py", "_native_arc_oracle.py", "trajectory.py")
    return {
        "python": sys.version.split()[0],
        "tudatpy": versions["tudatpy"], "numpy": versions["numpy"],
        "source_sha256": {"src/space_nav/" + p: hashlib.sha256(
            Path(__file__).with_name(p).read_bytes()).hexdigest() for p in paths},
    }


def produce(
    reference: Mapping[str, object], budget: Budget,
    arc_runner: Callable[[NativeRequest, Budget], dict[str, object]] | None = None,
) -> dict[str, object]:
    """Retain the first failed/unavailable path; never optimize or reset a node."""
    budget.check()
    if encode_packet(dict(reference), _INPUT_BYTES) != encode_packet(
            physical_oracle.reference(), _INPUT_BYTES):
        raise ConformanceError("reference differs from frozen exact-decimal fixture")
    from ._native_arc_oracle import reference as word_reference
    word_nodes = word_reference()
    states = reference["states"]
    assert isinstance(states, list)
    runner = native_arc if arc_runner is None else arc_runner
    packet: dict[str, Any] = {
        "schema": "ariadna-native-conformance-v1", "frame": "SYNTHETIC_INERTIAL",
        "time_scale": "elapsed_seconds", "controls": [0.0, 0.0, 1000.0, 0.0, 0.0, 1000.0],
        "words": {"thrust_n": (1000.0).hex(), "g0_m_s2": (9.80665).hex(),
                  "isp_s": (450.0).hex(), "gravity_y_m_s2": (0.1).hex(),
                  "rate_kg_s": _RATE.hex()},
        "reference": dict(reference), "paths": {"forward": [], "reverse": []},
        "counts": {}, "status": "passed", "failure": None, "runtime": _runtime(),
    }
    try:
        for name, order in (("forward", (0, 1, 2, 3)), ("reverse", (3, 2, 1, 0))):
            state = _state(states[order[0]])
            initial_mass = Fraction(state[6])
            burned_s = Fraction(0)
            for index, (start, end) in enumerate(zip(order, order[1:])):
                request = NativeRequest(_MODES[min(start, end)], Fraction(_EPOCHS[start]),
                                        Fraction(_EPOCHS[end]), state)
                admit_transport(request)
                budget.check()
                budget.contexts_created += 1
                try:
                    row = runner(request, budget)
                finally:
                    budget.contexts_closed += 1
                packet["paths"][name].append(row)
                for key in ("start_event", "end_event"):
                    event = row[key]
                    if event["native_equal"] is not True:
                        raise ConformanceError("unavailable-transport: native event identity differs")
                    if (abs(_number(event["residual_s"], "native residual")) > 1e-6
                            or abs(_number(event["observed_label_s"], "native label")
                                   - float(request.start_s if key == "start_event"
                                           else request.end_s)) > 1e-6):
                        raise ConformanceError("native event residual exceeds1us")
                if tuple(row["start_state"]) != state:
                    raise ConformanceError("native initial state/mass was reset")
                state = _state(row["end_state"])
                if request.mode != "coast":
                    burned_s += request.end_s-request.start_s
                ledger = initial_mass-Fraction(_RATE)*burned_s
                if abs(Fraction(state[6])-ledger) > Fraction(1, 1000000000):
                    raise ConformanceError("native event mass ledger exceeds1e-9kg")
                expected_word = word_nodes[name + "_states"][index+1]
                for expected in (states[end], expected_word):
                    if (math.hypot(*(state[i]-expected[i] for i in range(3))) > 0.001
                            or math.hypot(*(state[i]-expected[i] for i in range(3, 6))) > 1e-6
                            or abs(state[6]-expected[6]) > 1e-9):
                        raise ConformanceError("native analytic event gate failed")
    except ConformanceError as exc:
        budget.failed = True
        packet["status"] = ("unavailable-transport" if "unavailable-transport" in str(exc)
                            else "failed")
        packet["failure"] = str(exc)
    packet["counts"] = budget.snapshot()
    packet["counts"]["native_reported_function_evaluations"] = [
        row["native_reported_function_evaluations"]
        for name in ("forward", "reverse") for row in packet["paths"][name]]
    return packet


def encode_packet(packet: object, maxbytes: int = _OUTPUT_BYTES) -> bytes:
    try:
        data = (json.dumps(packet, sort_keys=True, allow_nan=False) + "\n").encode()
    except (TypeError, ValueError) as exc:
        raise ConformanceError("packet: finite JSON required") from exc
    if len(data) > maxbytes:
        raise ConformanceError("output byte cap")
    return data


def decode_input(raw: bytes) -> dict[str, object]:
    if len(raw) > _INPUT_BYTES:
        raise ConformanceError("input byte cap64KiB")
    try:
        packet = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ConformanceError("input: invalid JSON") from exc
    if not isinstance(packet, dict):
        raise ConformanceError("input: object required")
    encode_packet(packet, _INPUT_BYTES)
    return packet


def write_packet(
    path: Path, packet: object, budget: Budget, final: bool = False,
    *, maxbytes: int = _OUTPUT_BYTES,
) -> None:
    data = encode_packet(packet, maxbytes)
    budget.check_finalization() if final else budget.check()
    budget.check_output_bytes(data)
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        budget.failed = True
        raise ConformanceError(f"exclusive durable output failed: {exc}") from exc
    budget.check_finalization()


def _child(command: list[str], deadline_s: float, log_cap: int) -> dict[str, object]:
    """Bound opaque work and captured pipes; never use unbounded communicate()."""
    logs = {"stdout": bytearray(), "stderr": bytearray()}
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        assert process.stdout is not None and process.stderr is not None
        try:
            with selectors.DefaultSelector() as selector:
                for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, name)
                while selector.get_map():
                    remaining = deadline_s - time.monotonic()
                    if remaining <= 0:
                        raise ConformanceError("external watchdog deadline")
                    for key, _ in selector.select(min(remaining, 0.1)):
                        chunk = os.read(key.fd, 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                        elif sum(map(len, logs.values())) + len(chunk) > log_cap:
                            raise ConformanceError("captured log byte cap")
                        else:
                            logs[key.data].extend(chunk)
            remaining = deadline_s - time.monotonic()
            if remaining <= 0:
                raise ConformanceError("external watchdog deadline")
            try:
                code = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired as exc:
                raise ConformanceError("external watchdog deadline") from exc
        except ConformanceError as exc:
            exc.logs = {k: bytes(v).decode(errors="replace") for k, v in logs.items()}
            raise
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    return {"returncode": code, **{k: bytes(v).decode(errors="replace") for k, v in logs.items()}}


def run_isolated(directory: Path, reference: Mapping[str, object] | None = None) -> dict[str, object]:
    """One cold synthetic producer and independent audit under the fixed60s clock."""
    started = time.monotonic()
    reference = physical_oracle.reference() if reference is None else reference
    raw = encode_packet(dict(reference), _INPUT_BYTES)
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise ConformanceError("fixture directory must be empty; evidence never overwritten")
    source, producer_path, audit_path = (directory / p for p in
                                         ("input.json", "producer.json", "audit.json"))
    with source.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    summary: dict[str, Any] = {"status": "failed", "producer": None, "audit": None,
                               "failure": None, "children": []}
    try:
        producer = _child([sys.executable, "-m", __name__, "produce", str(source),
                           str(producer_path), repr(started)], started + 45.0, 128 * 1024)
        summary["children"].append(producer)
        if not producer_path.exists():
            raise ConformanceError(f"producer produced no evidence: {producer}")
        if producer_path.stat().st_size > 1024 * 1024:
            raise ConformanceError("producer byte partition exceeded")
        summary["producer"] = json.loads(producer_path.read_bytes())
        if producer["returncode"] != 0 or summary["producer"]["status"] != "passed":
            raise ConformanceError("native producer failed/unavailable; no audit or retry")
        audit = _child([sys.executable, "-m", __name__, "audit", str(producer_path),
                        str(audit_path), repr(started)], min(time.monotonic()+10.0,
                                                           started+55.0), 128 * 1024)
        summary["children"].append(audit)
        if audit_path.stat().st_size > 512 * 1024:
            raise ConformanceError("audit byte partition exceeded")
        summary["audit"] = json.loads(audit_path.read_bytes())
        if audit["returncode"] != 0 or summary["audit"]["status"] != "passed":
            raise ConformanceError("independent audit failed")
        summary["status"] = "passed"
    except (ConformanceError, OSError, ValueError) as exc:
        summary["failure"] = str(exc)
        if isinstance(exc, ConformanceError) and hasattr(exc, "logs"):
            summary["children"].append({"returncode": None, **exc.logs})
    summary["external_elapsed_s"] = time.monotonic()-started
    # Worker<=1MiB, audit<=512KiB, both logs<=256KiB, receipt<=256KiB total<=2MiB.
    final_budget = Budget(started)
    final_budget.output_bytes = sum(p.stat().st_size for p in (producer_path, audit_path)
                                    if p.exists())
    write_packet(directory / "receipt.json", summary, final_budget, final=True,
                 maxbytes=256 * 1024)
    if time.monotonic()-started >= 60.0:
        raise ConformanceError("finalization exceeded external60s deadline")
    return summary


def _source_guard(budget: Budget, event: str, args: tuple[object, ...]) -> None:
    if event != "open" or not args or not isinstance(args[0], (str, bytes)):
        return
    name = os.fsdecode(args[0]).replace("\\", "/")
    if "/docs/adr/experiments/" in name:
        budget.real_archive_reads += 1
    elif name.lower().endswith((".bsp", ".tls", ".tpc", ".bpc", ".bc", ".tf", ".ti", ".tm", ".tsc")):
        budget.kernel_reads += 1
    else:
        return
    budget.failed = True
    raise ConformanceError("synthetic fixture forbids archive/kernel access")


def _guard_spice(budget: Budget, spice_module: Any) -> None:
    def blocked(*args: object, **kwargs: object) -> object:
        budget.spice_queries += 1
        budget.failed = True
        raise ConformanceError("synthetic fixture forbids SPICE calls")
    for name in dir(spice_module):
        if not name.startswith("_") and callable(getattr(spice_module, name)):
            setattr(spice_module, name, blocked)


def _main() -> int:
    if len(sys.argv) != 5 or sys.argv[1] not in {"produce", "audit"}:
        raise ConformanceError("private fixed fixture worker arguments")
    stage, input_name, output_name, started = sys.argv[1:]
    began = _number(float(started), "inherited start")
    budget = Budget(began)
    sys.addaudithook(lambda event, args: _source_guard(budget, event, args))
    if stage == "produce":
        from tudatpy.interface import spice
        _guard_spice(budget, spice)
        with Path(input_name).open("rb") as stream:
            reference = decode_input(stream.read(_INPUT_BYTES+1))
        packet = produce(reference, budget)
        partition = 1024 * 1024
    else:
        from ._native_arc_oracle import audit
        with Path(input_name).open("rb") as stream:
            data_in = stream.read(1024 * 1024+1)
        if len(data_in) > 1024 * 1024:
            raise ConformanceError("audit producer input byte partition")
        packet = audit(json.loads(data_in), deadline=min(time.monotonic()+10.0, began+55.0))
        if {name.split(".")[0] for name in sys.modules} & {"tudatpy", "numpy", "scipy", "spiceypy"}:
            raise ConformanceError("independent audit imported a scientific library")
        partition = 512 * 1024
    write_packet(Path(output_name), packet, budget, final=True, maxbytes=partition)
    return 0 if packet["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(_main())
