"""Isolated TEST-ONLY bootstrap for real dispatcher argv over fabricated inputs.

Copy this file to a temporary directory and place its configuration beside it as
the same basename with a .json suffix. Never use this bootstrap with retained data.
"""

# ruff: noqa: E402 -- Start the shared clock before bootstrap imports.
from time import monotonic_ns

_BOOTSTRAP_ENTRY_NS = monotonic_ns()

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any

type Row = dict[str, Any]


def _emit(row: Row) -> None:
    print(json.dumps(row, sort_keys=True), flush=True)


def main() -> int:
    bootstrap = Path(__file__).resolve()
    config_path = bootstrap.with_suffix(".json")
    config_raw = config_path.read_bytes()
    config = json.loads(config_raw)
    assert type(config) is dict and config["profile"]["scope"] == "artificial-matched-norm"
    script = Path(config["script"])
    assert script.name == "0235-matched-norm.py" and script.is_absolute()
    profile = config["profile"]
    real_inputs = set(config["forbidden_real_inputs"])
    fake_inputs = set(profile["inputs"].values())
    opened = dict(real=0, artificial=0)
    role = "worker" if sys.argv[1:2] == ["worker"] else "parent"

    def read_trap(event: str, args: tuple[Any, ...]) -> None:
        if event != "open" or isinstance(args[0], int):
            return
        path = os.path.normpath(os.path.abspath(os.fsdecode(args[0])))
        write = int(args[2]) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        if not write and path in real_inputs:
            opened["real"] += 1
            raise ValueError("test harness blocked a real retained input read")
        if not write and path in fake_inputs:
            opened["artificial"] += 1
            if config.get("forbid_archive_reads", False):
                raise ValueError("test harness blocked an unexpected artificial archive read")

    sys.addaudithook(read_trap)
    module = ModuleType("_matched_norm_dispatch_under_test")
    module.__file__ = str(script)
    sys.modules[module.__name__] = module
    exec(compile(script.read_bytes(), str(script), "exec"), module.__dict__)
    # Include bootstrap/configuration work in the parent's shared deadline.
    module._ENTRY_NS = _BOOTSTRAP_ENTRY_NS
    module.OUTPUT = Path(config["output"])
    module.AUDIT = Path(config["audit"])
    module.retained_profile = lambda: deepcopy(profile)
    original_budget = module.Budget

    def charged_budget(*args: Any, **kwargs: Any) -> Any:
        budget = original_budget(*args, **kwargs)
        bootstrap_raw = budget.read(bootstrap)
        configuration_raw = budget.read(config_path)
        assert configuration_raw == config_raw
        _emit(dict(harness_budget=True, role=role, started_ns=budget.started_ns,
                   invocation_id=budget.invocation_id, bootstrap_entry_ns=_BOOTSTRAP_ENTRY_NS,
                   charged_bytes=budget.source_bytes,
                   bootstrap_sha256=sha256(bootstrap_raw).hexdigest(),
                   config_sha256=sha256(configuration_raw).hexdigest()))
        return budget

    module.Budget = charged_budget
    original_run = subprocess.run

    def redirect(command: list[str], *args: Any, **kwargs: Any) -> Any:
        assert command[:4] == [sys.executable, "-I", "-S", "-B"]
        assert command[4] == str(script)
        _emit(dict(harness_dispatch=True, argv=command[5:], script=command[4]))
        redirected = list(command)
        redirected[4] = str(bootstrap)
        return original_run(redirected, *args, **kwargs)

    module.subprocess.run = redirect
    arguments = sys.argv[1:]
    _emit(dict(harness_entry=True, role=role, argv=arguments, script=str(module.HERE)))
    code = 3
    try:
        code = module.main(arguments)
        command = arguments[3] if role == "worker" and len(arguments) >= 4 else None
        if code == 0 and command in config.get("fail_worker_after_success", []):
            code = 3
    except (OSError, ValueError, TypeError, KeyError, IndexError, ArithmeticError) as error:
        print(error, file=sys.stderr)
    finally:
        _emit(dict(harness_complete=True, role=role, argv=arguments,
                   real_input_reads=opened["real"], artificial_input_reads=opened["artificial"],
                   exit_code=code))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
