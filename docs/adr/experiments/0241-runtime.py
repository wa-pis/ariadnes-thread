"""Bound the installed scalar-solver runtime; never permit mission data or SPICE."""
from collections.abc import Callable
from hashlib import sha256
import os
from pathlib import Path
import sys
import sysconfig
from typing import Any

Row = dict[str, Any]
Check = Callable[[], None]
MAX_FILES = 2048
MAX_RUNTIME_BYTES = 256 * 1024**2


def need(value: object, reason: str) -> None:
    if not value:
        raise ValueError("bounded runtime: " + reason)


def _package(path: Path) -> bool:
    """Permit only the installed interpreter and the two pinned packages."""
    prefix = Path(sys.base_prefix).resolve()
    if not path.is_relative_to(prefix):
        return False
    relative = path.relative_to(prefix)
    parts = relative.parts
    if "site-packages" not in parts:
        stdlib = Path(sysconfig.get_path("stdlib")).resolve()
        return path.is_relative_to(stdlib) or path == Path(sys.executable).resolve()
    package = parts[parts.index("site-packages") + 1:]
    return bool(package) and (package[0] in {"numpy", "scipy"}
                              or package[0].startswith(("numpy-", "scipy-", "numpy.libs", "scipy.libs")))


class Guard:
    """Audit-visible access control and conservative whole-file read accounting."""

    def __init__(self, private: set[Path], inputs: set[Path], output: Path,
                 check: Check, profile: Row | None, *, scientific: bool) -> None:
        self.private = {str(path.resolve()) for path in private}
        self.input_dirs = {path.resolve().parent for path in inputs}
        self.os_metadata = {Path("/System/Library/CoreServices/SystemVersion.plist")} if sys.platform == "darwin" else set()
        self.inputs = {str(path.resolve()) for path in inputs}
        self.output = output.resolve()
        self.check = check
        self.profile = profile
        self.scientific = scientific
        self.sysconfig_name = sysconfig._get_sysconfigdata_name()
        self.source_bytes = 0
        self.runtime_read_bytes = 0
        self.runtime_files: set[str] = set()
        self.runtime_dirs: set[str] = set()
        self.denied_imports: set[str] = set()
        self.denied_operations: set[str] = set()
        self.inspecting_native = False
        self.global_loader_opens = 0
        self.native_files: set[str] = set(profile.get("native_files", [])) if profile else set()
        for filename in self.native_files:
            path = Path(filename)
            system = filename.startswith(("/usr/lib/", "/lib/", "/System/Library/",
                                          "/System/Volumes/Preboot/Cryptexes/OS/"))
            library = path.name.endswith(".dylib") or ".so" in path.name
            need(str(path.resolve()) == filename
                 and (path.is_relative_to(Path(sys.base_prefix).resolve()) or system)
                 and (library or path == Path(sys.executable).resolve())
                 and not any(token in filename.lower() for token in ("spice", "tudat"))
                 and filename in profile["files"], "unqualified native image root/type")
        self.expected = set(profile["files"]) if profile else set()
        if profile:
            need(profile.get("schema") == "ariadna-bounded-runtime-v1"
                 and 0 < len(self.expected) <= MAX_FILES
                 and type(profile["artifact_bytes"]) is int and 0 < profile["artifact_bytes"] <= MAX_RUNTIME_BYTES
                 and profile["runtime_read_cap_bytes"] == 4 * profile["artifact_bytes"], "runtime profile limits")
        self.read_cap = profile["runtime_read_cap_bytes"] if profile else MAX_RUNTIME_BYTES * 4
        # Conservatively account for startup modules loaded before the audit hook.
        for module in tuple(sys.modules.values()):
            filename = getattr(module, "__file__", None)
            if isinstance(filename, str):
                path = Path(filename).resolve()
                if _package(path) and path.is_file() and str(path) not in self.private:
                    self._runtime(path)

    def hook(self, event: str, args: tuple[Any, ...]) -> None:
        self.check()
        if event == "import":
            name = str(args[0]).partition(".")[0]
            need(name not in {"tudatpy", "spiceypy"}, "SPICE/native mission import forbidden")
            allowed = (name in sys.stdlib_module_names or name == self.sysconfig_name or self.scientific and
                       (name in {"numpy", "scipy", "cython_runtime"} or name.startswith("_cython_")))
            if not allowed:
                # Optional test/backport probes may fall back, never load another package.
                self.denied_imports.add(name)
                raise ModuleNotFoundError("package outside the qualified runtime: " + name)
            if len(args) > 1 and isinstance(args[1], str):
                self._runtime(Path(args[1]).resolve())
        elif event == "open" and not isinstance(args[0], int):
            path = Path(os.fsdecode(args[0])).resolve()
            name = str(path)
            reading = not int(args[2]) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            if name in self.private or name in self.inputs:
                need(reading, "input mutation")
                self.source_bytes += path.stat().st_size
                need(self.source_bytes <= 4 * 1024**2, "input/private-source byte cap")
            elif path.parent == self.output:
                need(path.name in {"attempt.json", "report.json", "receipt.json", "completion.json"},
                     "unexpected evidence path")
            elif path in {self.output, self.output.parent}:
                need(reading, "directory write")
            else:
                need(reading, "runtime mutation")
                self._runtime(path)
        elif event in {"os.listdir", "os.scandir"}:
            path = Path(os.fsdecode(args[0])).resolve()
            if path == self.output or path in self.input_dirs:
                return
            need(_package(path) or path == Path(sysconfig.get_path("purelib")).resolve(),
                 "directory outside installed runtime: " + str(path))
            if self.profile is not None:
                need(str(path) in self.profile["directories"], "unqualified import directory")
            self.runtime_dirs.add(str(path))
        elif event == "ctypes.dlopen":
            # The sole CDLL(None) is loader-image inspection, never a science API.
            self.global_loader_opens += 1
            need(args[0] is None and self.global_loader_opens <= 4,
                 "external or excess native-library load forbidden")
        elif event == "os.mkdir":
            need(Path(os.fsdecode(args[0])).resolve() == self.output, "out-of-scope directory creation")
        elif event in {"os.remove", "os.rmdir", "os.rename", "os.chmod", "os.link", "os.symlink", "os.chdir"}:
            need(False, "filesystem mutation forbidden")
        else:
            if event in {"subprocess.Popen", "os.system", "os.fork", "os.exec", "os.posix_spawn", "socket.__new__"}:
                self.denied_operations.add(event)
                raise PermissionError("out-of-scope operation: " + event)

    def _runtime(self, path: Path) -> None:
        name = str(path)
        native = name in self.native_files
        metadata = path in self.os_metadata
        need((_package(path) or native or metadata) and (native or metadata or path == Path(sys.executable).resolve()
             or path.suffix in {".py", ".pyc", ".so", ".dylib", ".json", ".txt"}),
             "out-of-scope runtime file: " + name)
        if not self.scientific:
            need("site-packages" not in path.parts, "third-party audit import")
        if self.profile is not None:
            need(name in self.expected, "unqualified runtime artifact: " + name)
        if metadata:
            self.source_bytes += path.stat().st_size
            need(self.source_bytes <= 4 * 1024**2, "OS metadata input cap")
        self.runtime_files.add(name)
        need(len(self.runtime_files) <= MAX_FILES, "runtime artifact count")
        self.runtime_read_bytes += path.stat().st_size
        need(self.runtime_read_bytes <= self.read_cap, "runtime read-volume cap")


def prepare(guard: Guard) -> tuple[Callable[..., Any], Row]:
    """Import the pinned proposer dependency inside the shared startup deadline."""
    purelib = sysconfig.get_path("purelib")
    if purelib not in sys.path:
        sys.path.append(purelib)
    import numpy
    import scipy
    from scipy.optimize import minimize_scalar
    need((numpy.__version__, scipy.__version__) == ("1.26.4", "1.17.1"), "pinned dependency versions")
    identity = dict(python=list(sys.version_info[:3]), prefix=str(Path(sys.base_prefix).resolve()),
                    numpy=numpy.__version__, scipy=scipy.__version__)
    return minimize_scalar, identity


def _native_images(guard: Guard) -> tuple[set[str], list[str]]:
    """Read the OS loader's finite image inventory, including linked BLAS libraries."""
    images = {str(Path(sys.executable).resolve())}
    opaque = []
    if sys.platform == "darwin":
        import ctypes
        guard.inspecting_native = True
        try:
            library = ctypes.CDLL(None)
            count = library._dyld_image_count
            count.argtypes, count.restype = [], ctypes.c_uint32
            name = library._dyld_get_image_name
            name.argtypes, name.restype = [ctypes.c_uint32], ctypes.c_char_p
            size = count()
            need(size <= MAX_FILES, "native image count")
            for index in range(size):
                value = name(index)
                need(value is not None, "missing native image")
                images.add(os.fsdecode(value))
        finally:
            guard.inspecting_native = False
    elif sys.platform.startswith("linux"):
        # Kernel-generated process metadata, not a package/directory scan.
        path = Path("/proc/self/maps")
        guard.private.add(str(path))
        with path.open("rb") as stream:
            raw = stream.read(512 * 1024 + 1)
        need(len(raw) <= 512 * 1024, "native image metadata cap")
        guard.source_bytes += len(raw)
        need(guard.source_bytes <= 4 * 1024**2, "native metadata input cap")
        for line in raw.decode().splitlines():
            fields = line.split(maxsplit=5)
            if len(fields) == 6 and fields[5].startswith("/"):
                images.add(fields[5])
    else:
        raise ValueError("unqualified loader-inventory platform")
    regular = set()
    for value in images:
        path = Path(value).resolve()
        system = str(path).startswith(("/usr/lib/", "/lib/", "/System/Library/",
                                      "/System/Volumes/Preboot/Cryptexes/OS/"))
        need(path.is_relative_to(Path(sys.base_prefix).resolve()) or system,
             "unexpected injected native image: " + str(path))
        if path.is_file():
            regular.add(str(path))
        else:
            need(system and sys.platform == "darwin", "unreadable installed native image")
            opaque.append(str(path))
    guard.native_files.update(regular)
    for name in regular - guard.runtime_files:
        guard._runtime(Path(name))
    return regular, sorted(opaque)


def authenticate(guard: Guard) -> None:
    """Authenticate every qualified runtime artifact before importing the solver."""
    need(guard.profile is not None, "qualified runtime profile required")
    for name, expected in guard.profile["files"].items():
        guard.check()
        path = Path(name)
        raw = path.read_bytes()
        need(len(raw) == expected["bytes"] and sha256(raw).hexdigest() == expected["sha256"],
             "runtime artifact drift: " + name)


def fingerprint(guard: Guard, identity: Row) -> Row:
    """Hash an explicit observed artifact list; never scan a package tree."""
    native, opaque = _native_images(guard)
    files = set(guard.runtime_files) | native
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if isinstance(filename, str):
            path = Path(filename).resolve()
            if _package(path) and path.is_file():
                files.add(str(path))
    need(len(files) <= MAX_FILES, "runtime artifact count")
    result = {}
    total = 0
    # The fixed list also authenticates import cache files actually observed by the hook.
    for name in sorted(files):
        guard.check()
        path = Path(name)
        total += path.stat().st_size
        need(total <= MAX_RUNTIME_BYTES, "runtime artifact-volume cap")
        raw = path.read_bytes()
        result[name] = dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
    manifest = dict(schema="ariadna-bounded-runtime-v1", identity=identity, files=result,
                    directories=sorted(guard.runtime_dirs), artifact_bytes=total,
                    runtime_read_cap_bytes=4 * total, native_files=sorted(native),
                    os_loader_shared_cache_images=opaque, host=list(os.uname()),
                    global_loader_opens=guard.global_loader_opens,
                    denied_optional_imports=sorted(guard.denied_imports),
                    denied_optional_operations=sorted(guard.denied_operations))
    if guard.profile is not None:
        need(manifest == guard.profile, "runtime identity or artifact inventory drift")
    return manifest
