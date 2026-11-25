# 0262 — Recommend an original-key build route

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (recommendation only; no build adoption)
Implementation: not started; no native build, dependency or runtime change
Verification: 172.099s source review and independent review; documentary checks below
Scope / milestone: F16 / M3 preparation in the sole active change
Base revision: `21eaccbda8b8faa968fb662b1a065f71f9ce9d66`
Related OpenSpec: [F16 design](../../openspec/changes/refine-physical-trajectory/design.md#f16-native-build-route-selection-2026-11-25), [readback requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-keep-split-time-enclosures-conditional-on-the-conversion-basis), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves ADR0261's original-row obligations

## Context and constraints

The user resumed recurring solution research after [ADR0261](0261-design-original-key-pre-export-admission.md).
The completed F15 review already identifies the missing original-row native seam.
Do not repeat it. The open decision is how to prepare that seam without silently
changing the authoritative pinned package or relying on unqualified cross-module ABI.

## Options considered

- Add the small visitor to the existing TudatPy simulator binding and rebuild an
  isolated, explicitly versioned package: source/build impact must be identified.
- Build a separate compatible extension: ownership/type registration, headers,
  linked libraries and ABI compatibility must be established, not assumed.

## Decision and rationale

The pre-read contract permitted only the retained F15 findings, installed
simulator binding and native accessor already named there; the pinned package's
Conda metadata; retained0258 recipe/build script/paths inventory; retained0259
root CMake; and project environment/package declarations. Enumerate only related
installed include/lib/CMake locations as needed, without executing their tools.
No broad API survey, HTTP/download, imports, compiler/build/install, runtime test,
scientific/oracle/command evaluation or integration. Fix the question and paths
before reading. Source reasoning, including independent review, is limited to600s
from the recorded first source read; documentary checks follow separately.

Recommend one additional method inside the existing simulator binding, compiled
as a distinctly identified TudatPy variant in a separate Conda build environment.
Keep operational `space-nav` and the official pinned package untouched. This is a
recommendation for user approval, not adoption or evidence that a build succeeds.
The method stays in the same module/type registration as the native owner, avoiding
an additional cross-module C++/pybind boundary. No native accessor/core Time change
is required by the proposed design; compilability remains unverified.

A separate extension is plausible: headers, static archives and imported CMake
targets exist. It is not preferred because accepting the existing Python simulator
requires separate type/holder/pybind-internals/C++ ABI and ownership qualification;
static linking also adds duplication/ODR questions. These are unresolved obligations,
not proof that an extension is impossible. No compiler/profile, dependency or
scientific run is adopted by this review.

## Consequences and revisit conditions

Prefer the smallest route that keeps the original row inside its native owner;
source convenience alone does not establish a buildable or qualified adapter.
Retain F15's pre-copy/hash/narrowing admission and same-row state/mass/lifetime
obligations. The review cannot validate prior native arithmetic or endpoint bounds.
All F0 inputs/forces/tolerances and73/76/228/300s gates remain unchanged. Pause the
automation with the concrete proposal if a user build/dependency choice remains.

## Evidence and verification

The source/reasoning review ran 2026-11-25T04:10:45.883976+00:00 to
2026-11-25T04:13:37.984295+00:00: 172.099s<=600s, including an independent
source/scope review. [Source evidence](experiments/0262-source-route-review.json)
retains19 distinct source/metadata hashes, selected lines, packaging observations
and explicit qualification gaps. No runtime tests were rerun on unchanged code.

| Observation | Source / implication |
| --- | --- |
| Existing native owner | Installed expose_simulator.cpp51–53 registers the simulator with shared_ptr; scalarTypes.h18–20 declares double state and Time. A held owner is available in the proposed in-tree method, but mutation exclusion/GIL/threading is not yet implemented. |
| Original row | ADR0261's accessor returns the original const map. Its vector is dynamically sized, not automatically a seven-state. Validate exactly seven values and the explicit Cartesian/mass schema before any association claim. |
| Build declarations | Retained0258 build.sh12–24 specifies CMake/C++14/make;32–36 installs and fetches Git PyTrk234. Recipe declares Clang18.1.8/pybind11 3.0.1. Do not execute the script wholesale or silently allow its unpinned network fetch. |
| Current package records | The named Conda metadata search finds Python3.12.14/libcxx23.1.0/Boost1.84; no exact records for the listed compiler/CMake/make/ninja/pybind/Eigen packages. This does not claim those tools are absent from the machine or prove runtime incompatibility. |
| Installed exports | tudat-config23–34/43 declares paths/definitions/targets; export174 declares a static propagator target. Release182/332 names operational-prefix archives. An isolated build must reject fallback/linkage into that prefix and regenerate or independently qualify relocated exports. |
| Source identity limits | Binding cpp/header, scalarTypes and config match0258's exact-package inventory. The two installed export files have different raw hashes; inventory declares text prefix replacement, consistent with relocation but not an independently verified byte transformation here. Preserve both hashes/statuses. Declared definitions are not effective compiler/FP attestation. |

### Expected changes and qualification before adoption

Expected future changes are the upstream simulator binding implementation (plus a
minimal helper only if needed), focused native fixtures, and an isolated Conda
recipe/build manifest with a distinct build identity and patch digest. No patch,
recipe, consumer change, dependency installation or operational package replacement
has been made. Complete source/submodule availability and an exact compatible
toolchain/dependency manifest remain unverified; the retained sources are not a
claim of a complete reproducible build tree.

Before any launch, a separately accepted profile must pin sources/patches/compiler/
C++ and FP settings, Python/pybind and linked dependencies; reject operational-prefix
fallback, uncontrolled recipe network access and missing resource enforcement.
Proposed operator ceilings: one build attempt,3600s inclusive of finalization,
maximum two compiler workers,8GiB scratch,2GiB aggregate acquisition and16MiB logs.
These bound workstation cost; they are not measured build feasibility or the
physical300s limit. A missing pin/enforcement prerequisite means no build launch;
a consumed failure is reported, not automatically retried or granted a larger cap.

After a successful authorized build, a proposed native-fixture stage is bounded
by12 visitor calls,60s inclusive,64KiB input/2MiB evidence and ZERO trajectory
launches. Fixtures cover guard-before-copy/hash/narrow instrumentation; scalar
nonfinite/range rejection before unsafe Time construction; original same-row seven-
state/mass and direction binding; held owner/mutation/expiry/context rejection;
signed-zero/rounded3600/finite-neighbour export. Such fixtures do not establish
prior propagation arithmetic, actual cross-context event carry, force/endpoint
bounds or F0 feasibility. Keep the separate lifetime-safe carrier obligation.
Any later Ariadna adoption must also pass both required regression lanes against
the distinctly identified variant; historical official-package CI cannot qualify it.

### Concrete user choice and scheduler

Authorize preparation and one bounded isolated in-tree TudatPy build, including
explicitly pinned build dependencies, while preserving operational `space-nav`?
This changes the native build/dependency surface and therefore needs the user's
choice under ADR0261 and the linked F16 contract. `ariadna-m3` is PAUSED; no
automatic build, scientific run or diagnostic successor is scheduled.

[Documentary verification](experiments/0262-doc-verification.json) checks local
links/anchors, protected history/CURRENT,
source/evidence hashes, diff and strict OpenSpec. Runtime tests and CI are not
rerun for this documentary stage. The original admissible command pair and all
physical gates remain open.
