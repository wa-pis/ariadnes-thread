# 0263 — Authorize one isolated native binding build

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (user authorized preparation and one bounded build)
Implementation: one isolated kernel build passed; native fixture qualification incomplete
Scope / milestone: F17 / M3 native-adapter preparation
Base revision: `e98329e282b99290964d533cd64f8218787ccea0`
Related OpenSpec: [F17 design](../../openspec/changes/refine-physical-trajectory/design.md#f17-isolated-native-build-2026-11-25), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [readback requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-keep-split-time-enclosures-conditional-on-the-conversion-basis)
Supersedes / Superseded by: none; records authorization missing at ADR0262

## Context and constraints

The user explicitly answered “разрешаю” to [ADR0262](0262-recommend-original-key-build-route.md)'s
proposal for preparation and one isolated in-tree TudatPy build, with pinned build
dependencies and operational space-nav preserved. This resolves that approval;
do not ask for it again. Scientific experiments and package adoption remain separate.

## Options considered

- Invoke the whole upstream build: unnecessary Tudat-core compilation, global
  CMake registry writes and recipe network fetches; rejected for this unit.
- Build the existing monolithic kernel binding with the additional in-tree method,
  linking isolated copies of pinned core archives: selected, subject to preflight.
  This is the same kernel/type registration, not a separately loaded extension.

## Decision and rationale

First establish resource and prefix isolation; then acquire/identify complete
sources and an explicit Conda build manifest, implement the minimal original-row
visitor and permit at most one native build. Do not execute the upstream recipe.
Use a distinct private build prefix/cache/HOME/TMP/config, copies rather than edits
of operational files, no CMake package registry/system fallback or build network.
Record exact source/patch/toolchain/flags/link identities before compilation.
Reject operational-prefix include/link/runtime fallback and missing prerequisites.
A source/metadata label is not effective compiled FP or ABI evidence.

The one preparation/build episode has a3600s inclusive deadline, at most two
compiler workers,8GiB aggregate scratch,2GiB aggregate acquisition and16MiB logs.
A capacity-limited temporary volume is the preferred disk enforcement; size polling
or per-file limits cannot establish the aggregate cap. Streaming acquisition/log
accounting and a process-group watchdog must be qualified before use. Do not
launch if enforcement/pins/source completeness is missing. Configuration/ABI probes are compiler activity and are recorded separately.
A setup correction before compiling the kernel target stays within the same
episode/deadline; it does not authorize a second kernel-target attempt or a
scientific conclusion. Preserve every failed configure/cache and its correction.

Only after an authorized successful build, a separate finite fixture packet may
use at most12 visitor calls/60s/64KiB input/2MiB evidence and zero trajectory
launches. Validate pre-copy/hash/narrow admission, native finite/range predicate,
explicit7value Cartesian/mass schema, same-row direction/state/mass, owner/mutation
and signed-word/neighbor semantics. Do not expose borrowed native references or
claim cross-context carry, lawful prior arithmetic or physical F0 qualification.
Required checks for actual project code changes remain the frozen portable/live
lanes, focused tests, Ruff, independent review and strict OpenSpec. An external
build/preflight without project runtime changes is documented as such; do not
rerun successful unchanged project tests merely for a prose/packaging result.

## Consequences and revisit conditions

The operational package and historical qualification remain intact. New artifacts
are distinctly identified and cannot inherit official-package CI qualification.
No mission integration, scientific evaluation, altered force/time/target/tolerance,
old replay, optimizer or physical gate closure is authorized here. Pause only for
an actual user/access/contract decision, not ordinary reversible preparation.

## Evidence and verification

[Result](experiments/0263-build-result.json) and [immutable evidence ZIP](experiments/0263-build-evidence.zip)
retain99 members, per-member hashes, controls, source/manifests, setup failures,
all logs, private source text and the proposed next packet. No binary, environment,
cache or adopted Ariadna runtime implementation is committed.

- Resource controls were checked before use: capacity-limited APFS volume,
  isolated HOME/cache/TMP, denied build network and operational-prefix reads,
  streaming quota/log accounting and process-group watchdog. Self-tests cover
  denied writes/network/proxy bypass, exact relay quota, log overflow, child
  termination, safe environment and persistent quota reservation.
- Pinned upstream2300d7fe3d7db4db9a78dd4a9a4a713f614da22d,
  Python3.12.14/TudatPy1.0.0, Clang18.1.8, CMake4.1.2, Make4.4.1,
  pybind11 3.0.1 and Eigen3.4.0; all310 isolated Conda records retained.
  The isolated dependency solve also updated OpenSSL/certifi/CA certificates;
  scientific packages and the operational environment were preserved.
- Two configure failures preceded kernel compilation: explicit flat Tudat_DIR
  was missing, then the legacy CSpice::cspice target spelling differed from
  installed CSPICE::cspice. Cache/log/profile history is retained. An alias to
  that exact installed target corrected configuration without replacing archives.
  Identification/ABI/pthread probes did compile; these are not zero compiler
  activity. Three configure invocations led to exactly one kernel-target build.
- All81 binding translation units and47 explicit link libraries were independently
  checked for isolated paths; final commands use O1/no-fast-math/FP-contract-off/
  no-LTO/C++14. The kernel built in422.086s. Its SHA256 is
  `04f7af4c8429c09aec9a21f50888e7e4a979e69184e8abc530e17e88e4cb4941`.
  Thirty-four linker warnings concern weak Boost.Math symbol visibility. System
  C++ runtime dependencies/dynamic lookup and pinned precompiled-core arithmetic
  remain qualification caveats. Build success is not blanket ABI/FP proof.
- The private source selects one original const-map row, validates native finite
  remainder before copying/hashing/narrowing, requires seven finite state values,
  and captures all scalar values before Python allocation. A source review and
  27 pure fake-callable runner checks pass; neither proves live-owner behavior.
- The first finite packet aborted during native import after3.863s, returncode-6:
  isolated HOME lacked quadrature/gaussianNodes.txt. Zero fixture calls occurred;
  no fixture result JSON/native-context observation was produced. This is an
  environment-preparation failure, not a failed physical trajectory or a pass.
  The pinned resource Conda package contains a post-link downloader; offline
  installation success did not establish the resource payload. This prerequisite
  should have been checked before importing the kernel.
- Two existing local quadrature dependencies, nodes36021B and weights37106B,
  are now copied read-only into isolated HOME with source/destination SHA256
  checks. Exact local bytes are pinned, not authenticated v2.4 release contents.
  Their73127B are runtime dependencies, separate from the64KiB fixture-parameter
  packet, and are precharged to acquisition with a lower persistent proxy cap.
  There was no subsequent native import, dependency install, HTTP or rebuild.
- Preparation/result closure measured2578.954s against3600s. Aggregate acquisition
  is496986960B; captured logs169675B. Volume capacity8380178432B and measured
  allocated root storage excluding the mounted tree5699117056B remain below8GiB.
  These byte observations do not claim kernel wire-byte accounting.
- All71459 operational paths and1646916124 regular bytes match the original
  full SHA256/symlink manifest exactly. Historical project non-Markdown blobs,
  legacy model, links/anchors/diff and strict validation are checked separately
  in the [documentary receipt](experiments/0263-doc-verification.json).
  Project runtime tests/CI were not rerun: Ariadna runtime/test code is unchanged.

### Stopping rule and concrete next proposal

The first packet's inclusive wall window has passed. One review proposed summing
active process durations and reusing the remainder; the stricter independent
control review correctly distinguished that from the original inclusive window.
We retain the failed packet and do not substitute a new clock interpretation.
Automation ariadna-m3 is PAUSED, confirmed by the app, for a new packet decision.
F17 remains unchecked; build success does not complete its qualification duties.

The archived next-fixture-proposal.json is reviewable but not authorized/launched:
one new11-call/60s inclusive/64KiB parameter/2MiB evidence packet on the exact
already-built kernel and unchanged runner, using the two pinned local math files.
No compiler, dependency install, HTTP, SPICE, integration, simulator construction,
mission run, package adoption or retry of the build is proposed. The earlier
build episode and failed packet remain closed, with their original limits/results;
any future packet requires explicit authority and its own fixed preflight/clock.
Even a successful manufactured packet would leave owner lifecycle/concurrency,
prior Time arithmetic, cross-context carry, frame/body semantics and physical F0
unqualified. No admissible command pair,99% success or M3 completion is claimed.
