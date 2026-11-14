"""Bind the fixed ADR0193 restart to the audited B archive without native work."""
from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ART = Path("docs/adr/experiments")
DESIGN = ART / "0193-design-inputs.json"
DESIGN_SHA = "c8a9f67541b25c68b6bc0f3768b622d64b5229bcefaa0087f3f95cdef84da6ea"
PREVIOUS_SHA = "202b14ba22532d8a3129c185b4fd88788e9030b0d7c981a03ee5b57d4a5a83b8"
RANGE_INPUTS = "9c48b2f887d75f31a7de256b20b70a0add4f3a877822c36188385535254ade83"
PURE_PINS = {
    "0189-post-cutoff-prepare.py": "81b49f2d980587a8379f5617cf56798acc0d11c3e8cdaa2bbf2eace719654983",
    "0189-post-cutoff-inputs.py": "2e91821f24a7a0d1170b576c8d22771ca984e65c524245031c61db92694b3a05",
    "0192-range-inputs.py": RANGE_INPUTS,
    "0141-short-coast-inputs.py": "4457d9094afe3e8b674a46704b6789fdd724469cb8e1efe5cc054ce39d34c37c",
    "0145-short-coast-evidence.py": "426fe4e0abe9b9dfcf6380d09e86e8dbf5748f66875f74b26b45dceb6ba5da14",
}
type Wire = dict[str, Any]
type Check = Callable[[], None]


def require(ok: object, message: str) -> None:
    if not ok:
        raise ValueError(message)


def read(root: Path, relative: Path | str, pin: str, check: Check) -> bytes:
    check()
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), "input outside checkout")
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == pin, "input SHA256: " + str(relative))
    check()
    return raw


def load_file(root: Path, name: str, pin: str, check: Check) -> dict[str, Any]:
    raw = read(root, ART/name, pin, check)
    module = ModuleType("r548_input_" + name.removesuffix(".py").replace("-", "_"))
    module.__file__ = str(root / ART / name)
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return module.__dict__


def words(values: list[float]) -> list[str]:
    require(all(type(x) in (float, int) and math.isfinite(x) for x in values), "nonfinite state value")
    return [float(x).hex() for x in values]


def bind(design: Wire, old: Wire, grids: Wire) -> Wire:
    restart, coast = design["restart"], design["coast"]
    epoch, state, moon = grids["native_tighter"][-1]
    mass = restart["mass_kg"]
    require(design["candidate"] == "d0001-t0035" and len(state) == len(moon) == 6,
            "restart candidate and state size")
    require(words([epoch, mass]) == [restart["epoch_binary64_hex"], restart["mass_binary64_hex"]]
            and words([epoch, mass]) == words([restart["epoch_tdb_s"], old["mass_kg"]])
            and words(state) == words(restart["state_si"]) == restart["state_binary64_hex"]
            and words(moon) == words(restart["moon_state_si"]), "restart words")
    require(epoch == old["initial"]["epoch_tdb_s"] + 600, "archived endpoint epoch")
    for name, delta in restart["archived_state_minus_restart_signed_si"].items():
        end_epoch, end_state, _ = grids[name][-1]
        require(end_epoch == epoch and words(delta) == words([a-b for a,b in zip(end_state, state, strict=True)]),
                "saved same-start deltas")
    offsets = coast["coepoch_offsets_s"]
    require(offsets == list(range(0, 51, 5)) and coast["horizon_s"] == 50
            and coast["marker_radius_m"] == 3474800
            and coast["stop_tdb_s"] == epoch + 50
            and words([epoch + 50]) == [coast["stop_binary64_hex"]]
            and coast["coepochs_tdb_s"] == [epoch + t for t in offsets]
            and all((epoch + s) - epoch == s for s in offsets), "frozen extension time grid")
    require(coast["model_id"] == old["coast"]["model_id"]
            and coast["gm_m3_s2"] == old["gm_m3_s2"] and coast["radii_m"] == old["radii_m"]
            and coast["gates"] == old["coast"]["comparisons"]
            and coast["dop853_settings"] == old["coast"]["dop853_settings"]
            and coast["native_steps_s"] == old["coast"]["native_steps_s"]
            and coast["thrust_n"] == coast["mass_flow_kg_s"] == 0, "frozen model B controls")
    return {**old,
            "initial": {"epoch_tdb_s": epoch, "position_m": state[:3], "velocity_m_s": state[3:]},
            "offsets_s": offsets, "restart_moon_state_si": moon,
            "extension": design, "origin_cutoff": old["cutoff"]}


def design_inputs(root: Path, check: Check) -> tuple[Wire, Wire]:
    """Verify the covered metadata, archived restart and preparation inputs."""
    old_module = load_file(root, "0189-post-cutoff-inputs.py", PURE_PINS["0189-post-cutoff-inputs.py"], check)
    design = old_module["parse"](read(root, DESIGN, DESIGN_SHA, check))
    require(design["stage"] == "R5.46" and design["contract"] == "ADR0193", "R5.46 design identity")
    for name, sha in design["source_sha256"].items():
        read(root, ART/name, sha, check)
    range_module = load_file(root, "0192-range-inputs.py", RANGE_INPUTS, check)
    grids, _ = range_module["load"](root, check)
    prior = old_module["load"](root, check)
    old_module["_coverage"](design["record_metadata"], prior["source_rows_template"],
                            design["coast"]["coepochs_tdb_s"])
    return design, bind(design, prior, grids)


def prepare(root: Path, expected: str, check: Check) -> Wire:
    """Require the exact synthetic verification manifest plus old research pins."""
    old = load_file(root, "0189-post-cutoff-prepare.py", PURE_PINS["0189-post-cutoff-prepare.py"], check)
    old["verify"](root, PREVIOUS_SHA, check)
    parser = load_file(root, "0189-post-cutoff-inputs.py", PURE_PINS["0189-post-cutoff-inputs.py"], check)["parse"]
    prep = parser(read(root, ART/"0194-verification.json", expected, check))
    require(prep["contract"] == "ADR0193" and prep["stage"] == "R5.47" and prep["preparation_complete"] is True
            and prep["design_sha256"] == DESIGN_SHA, "verified R5.47 preparation required")
    pins = prep["tested_source_sha256"]
    require(all(str(ART/f"0194-extension-{role}.py") in pins
                for role in ("inputs", "study", "audit", "launch")), "tested R5.47 modules")
    require(all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in pins),
            "untrusted preparation path")
    for name, pin in pins.items():
        read(root, name, pin, check)
    return pins
