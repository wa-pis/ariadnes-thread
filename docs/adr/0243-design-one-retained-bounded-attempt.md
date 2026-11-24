# 0243 — Design one retained bounded witness attempt

Date: 2026-11-24 (Europe/Samara)
Decision status: accepted
Implementation: design only; retained binding/dispatcher not implemented
Verification: static source, raw-file identity and documentation checks only; no new scientific result
Scope / milestone: one future local analytical P3 attempt within the active M3 change
Base revision: `c0e7abc3559922e42e122a224237988da49ce7c3`, clean `dev`
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-use-bounded-scalar-search-only-to-propose-an-analytical-witness), [design](../../openspec/changes/refine-physical-trajectory/design.md#p4-one-retained-bounded-attempt-2026-11-24), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [roadmap](../../openspec/ROADMAP.md)
Supersedes / Superseded by: none; binds ADR0240's method after ADR0242 qualification, without changing either scientific gates or historical evidence

## Context and constraints

[ADR0242](0242-finish-p3-regression-qualification.md) completes P3 preparation:
all 128 P3 cases pass in CI on `1812360`, with both required regression lanes.
It does not authorize a saved run. The user now requests its design only, with
no execution, SPICE or integration. Existing real-data evidence remains
inconclusive; no claim is made that the approximately 40.085 m/s gap is recoverable.

The qualified [0241 invocation](experiments/0241-bounded-invocation.py) rejects
repository/retained paths and emits artificial scope. Relabelling a profile or
passing real archives through that command would bypass the qualified boundary.
The [point adapter](experiments/0241-phase-points.py) also requires artificial
scope/candidate in `_reference`, in both `point` and `audit_point`. Reusing it
unchanged would reject real inputs. Minimal versioned dispatcher and point-identity
bindings must therefore qualify before a separate execution instruction. This
record specifies one attempt, not a new method or optimizer.

## Options considered

- Feed real paths to the artificial command, remove its checks or monkeypatch its
  scope: rejected; this would erase the artificial/retained boundary.
- Replay an old grid/interval study or widen the search: rejected; consumed
  attempts and the [ADR0239 stop policy](0239-stop-diagnostics-at-a-feasibility-decision.md)
  remain binding.
- Add a versioned private retained dispatcher and point adapter, changing only
  the point adapter's scope/candidate admission, around the unchanged search,
  trace, runtime and archive/anchor helpers: selected. Preserve all numerical
  arithmetic and oracle/command checks; qualify the new identity binding,
  output lifecycle and actual command forms. No public API, framework,
  dependency or environment change is needed.

## Decision and rationale

### Fixed scientific inputs

Only these four original raw files are scientific inputs. The values below
match the unchanged `PINS` in [0220](experiments/0220-phase-invocation.py).
Do not regenerate, canonicalize, repair, substitute or select other evidence.

| Role | Repository path under `docs/adr/experiments/` | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Saved attempt | `0215-r559f/attempt.json` | 1508 | `ac1d02f445ebed82ac5b4f728193ea8533890188ed2422117523db50d087bf0a` |
| Saved report | `0215-r559f/report.json` | 1059325 | `323c2c71e17168a46e9dd5280015a3fecb0865016b9b6954dcb051de4def1800` |
| Saved receipt | `0215-r559f/receipt.json` | 1727 | `395d20ab4771b9a9e4743e038e5c50338d12b8d890018befc3879bf3de21a18b` |
| Independent saved-grid audit | `0217-saved-grid-audit.json` | 3398 | `bdc9eb8225a4af912327d0c8cd62231bf4f625991f6d4233ea58a5e9481172d5` |

Authenticate raw bytes before parsing; preserve role-specific historical encoding,
including the grid audit's exact-zero view, without rewriting any source bytes.
Use the [0220 archive binder](experiments/0220-phase-archive.py) with
`retained=True`: require the exact evidence/lineage inventory, upstream pins,
reference digest `6b845f74881f658d2eeea28bfdde43c9190a283da5bb166644bb845c4f847c5b`
and its existing binding and epoch-word checks. Embedded upstream hashes are
sealed metadata; this does not authorize opening/replaying upstream archives.
The old 360 rows are read/validated structurally; only three anchors are newly
evaluated. No 360-point replay, new endpoint extraction study or old audit dispatch.

Preserve candidate `d0001-t0035`, positive lunar branch, signed excess vectors,
body translations, orbital plane/apsides/GMs/guards, historical exclusions and
all three original TDB epoch words exactly as bound by the reference digest.
Keep SI, SSB origin and J2000 orientation; the archived full-model identifier is
provenance, not a claim that those forces are evaluated by this impulsive study.
Spacecraft remains 2000 kg initial / 500 kg dry, 1000 N thrust, 450 s Isp,
20 m² area and Cr=1.3. Only Mars true anomaly at the original arrival epoch may
vary over the closed [150°, 152°] domain. No hidden dates or physical defaults.

### Unchanged method and versioned identity admission

Preserve [ADR0240](0240-choose-bounded-scalar-witness-search.md). Create a new
version of the [0241 point adapter](experiments/0241-phase-points.py) changing
only `_reference` scope/candidate admission to the fixed retained identity or
its disjoint fabricated qualification identity; never relabel retained operands
as artificial. All other validation, binary64/oracle arithmetic and literal-command
checks remain unchanged. P5 must check this restricted source/AST difference and
qualify both `point` and `audit_point`, including scope/candidate cross-pair rejection.
Reuse the [bounded proposer](experiments/0241-bounded-search.py),
[trace checker](experiments/0241-trace-audit.py), runtime and frozen scientific
helpers byte-for-byte. First compare
refusing anchors 150°, 151°, 152°; then bounded Brent once for positive and once
for negative Mars sign, in that order, stopping at the first admitted point.
Settings remain `bounds=(150.0,152.0)`, `xatol=1e-5` degrees, `maxiter=62`, `disp=0`.
Both sign slots are checked at every phase. Mass-rejected finite costs remain
searchable; definitive guard/degenerate active objectives end only that sign,
without penalties/restarts. Missing/unresolved data or disagreement ends invalid.

Retain exact binary64 phase hex/ratio and all six original TNW command words.
Require every original state/asymptote/impulse/guard/reversal/event/exclusion gate:
0.001 m and 1e-6 m/s state agreement, minimum-radius agreement 0.001 m and strict
clearance more than 0.001 m above the guard, duration agreement 1e-6 s and mass
agreement 1e-8 kg, unrounded ideal budget and both exact commanded/effective
500 kg ledgers. Oracle-rounded substitute commands, snapped phases, a relaxed
floor or a new Mars target adopted for the physical mission are forbidden.

### Source/runtime readiness before one-shot dispatch

Keep completed 0241 sources/commands and all 0241/0242 evidence immutable. Add
only a small versioned private retained dispatcher and the scope-gated point
adapter; preserve the latter's numerical implementation and reuse the stdlib
independent recorded-point audit, without a new scientific stack. Freeze the new
dispatcher and point adapter's exact source/role map, bootstrap, configuration and
selected solver source hashes after artificial qualification. The
[0242 repaired bindings](experiments/0242-linux-profile-repair.json) authenticate
the existing helper family; their artificial-bootstrap role cannot be silently
relabelled or loaded as a retained fixture. New dispatcher bindings are pending,
not a runnable profile supplied by this design.

Use the existing pinned Conda Python 3.12.14 / NumPy 1.26.4 / SciPy 1.17.1.
The local producer/auditor runtime tables are the `runtime` subobjects in
[0242 producer](experiments/0242-producer-runtime.json) and
[0242 audit](experiments/0242-audit-runtime.json), canonically bound by the repaired
binding record. Preserve exact paths, build/digest maps and the explicit OS
shared-cache opacity caveat. Producer: 1000 artifacts / 85,086,011 artifact bytes,
340,344,044 read-byte cap; auditor: 105 / 17,929,804 / 71,719,216 respectively.
No directory-wide allowlist, automatic profile regeneration, machine migration,
new artifact or cap increase. New wrapper imports must fit these exact tables;
otherwise readiness fails. NumPy/SciPy native imports are permitted and counted;
TudatPy/SPICE, kernels, network, force/integration APIs and old studies are not.

### One fixed attempt and finite budgets

Plan the future command as `retained`, with no caller-supplied input, phase, sign,
profile or output path. It owns the fixed exclusive namespace
`docs/adr/experiments/0243-p3-retained/`, initially absent. Reserve it atomically
before worker dispatch and write a bounded invocation identity. One parent may
launch at most one isolated cold producer and, only for its complete auditable
result, one separately implemented stdlib auditor process. Both workers use
`-I -S -B`, fresh identities and distinct `producer/` and `audit/` directories.
Existence of the namespace or any dispatched failure consumes the whole attempt,
even before scientific work/output; no overwrite, retry, resume or audit-only rerun.
Design/preparation creates no such namespace and consumes no saved attempt.

| Resource | Fixed ceiling |
| --- | --- |
| New retained producer / independent auditor | At most 1 / 1; no other study/optimizer replay |
| Direct phase work per producer arithmetic path and per auditor | 3 anchors + 62 callbacks/sign + 2 already-recorded final checks = 129 phases |
| Mars signed-root / pair slots per path | 258 / 258, precharged including duplicate/rejected/error attempts |
| Interval cells / bounds | 0 / 0 |
| Producer wall time | 30 s from a parent clock started before reservation/manifest/bootstrap, including worker startup/imports, authentication and durable finalization/readback |
| Separate auditor wall time | 30 s including its startup/imports, input/result reads, arithmetic and durable finalization/readback |
| Source/configuration/scientific input bytes per reader | 4 MiB, including all rereads and auditor reads of producer evidence |
| Combined new evidence | 4 MiB including the launcher record and both four-record process chains |
| Launcher record / producer chain / auditor chain | 4096 B / at most (4 MiB - 4096 B - 64 KiB) / at most 64 KiB |

Both workers keep canonical finite `attempt.json`, `report.json`, `receipt.json`
and `completion.json` chains with input/source/runtime/run identity. Parent
checks and producer readback are structural/hash-only, never repeated phase work.
Input/source charging includes bootstrap/config/profile and selected solver source;
installed-runtime reads have the separate frozen caps above, with no omitted
loading/authentication time or warm-up outside the clock. A parent kills a worker
at its deadline and cannot accept a late completion as successful. Preserve late
or partial bytes and bounded failure metadata; missing/late completion means
invalid/unverified, with no deletion to hide the failure.

The 64 KiB audit reserve is an internal allocation inside the inherited 4 MiB,
not a raised cap: the earlier artificial maximum-volume audit used 47,371 B.
That observation motivates headroom, but does not qualify the new schema/dispatcher.
Preparation must measure the full new 129-phase producer/auditor volume, every
read and finalization cost; failure leaves execution unavailable, without tuning
scientific gates or rerunning saved data to size the buffers.

### Independent audit and terminal result

For a complete producer result with exit 0 (provisional witness) or 2 (complete
inconclusive), bind the external raw `completion.json` SHA-256 and the entire
producer chain. Reauthenticate the same four archives, reference and qualified
source/runtime identities. Do not dispatch a numerical audit for an absent,
partial, inconsistent or unauthenticated chain; preserve it as failed/consumed.

The separate auditor uses the original 96-digit independent conic/orbit and
literal-command/mass path, not producer point construction or its optimizer.
Check every recorded phase and both signed slots, anchor refusals, exact words,
objective/result/final bindings, sign/stopping order and independent precharged
counters. Zero optimizer calls and zero new/unrecorded phases in audit. Reusing
common scoped input parsing/identity helpers does not make the numerical paths
independent; the separate point oracle and literal-word checks are required.

Only an agreed, durably completed producer/auditor witness may conclude
`verified-analytical-witness`. An audited complete no-witness transcript remains
`inconclusive/invalid`; audit success is not feasibility success. A timeout, drift,
missing evidence, disagreement or cap failure is invalid/unverified. Brent cannot
certify continuous refusal or global optimality. Report actual source/runtime,
work/read/output/time counters and zero SPICE/kernel/force/integration/old-study/
R5.60 work; do not report zero numerical work or zero native-library loads.
Stop after every terminal outcome. No automatic diagnostic successor is planned.

## Consequences and revisit conditions

The design supplies fixed inputs, bounds and one-shot failure semantics without
claiming readiness. P5 must separately implement/qualify the minimal dispatcher
and point-identity binding on fabricated archive files, actual command shapes,
restricted point-adapter source/AST changes, full volume, path/scope/hash/
encoding/chain drift, cap/deadline/partial-output failures and independent auditing
of witness and no-witness outcomes. Project checks remain required; no new SPICE
or integration is authorized by this planning instruction. Any required live/CI
verification for changed code must have explicit applicable authority.
Only completed preparation and another explicit instruction permit P6 dispatch.

An analytical witness still changes the Mars target and needs separate boundary
and immutable-command selection review; it does not admit an executable pair or
original R5.60. M3/physical closure/reserve/safety remain unproved and automation
stays PAUSED. Inconclusive or failed preparation/execution needs a separate
reviewed decision, not new inputs, a deeper search or relaxed caps by default.

## Evidence and verification

Read source/AST and existing metadata only. Hash/size checks confirm all four
raw input identities above and the qualified helper/runtime references; no saved
numerical operands were extracted/evaluated and no scientific module was imported.
All 526 local links/anchors, strict OpenSpec, whitespace and Markdown-only scope
checks pass; 1043 protected non-Markdown files remain byte-identical. Independent
review identified the artificial-only point identity gate before implementation;
the corrected design versions that gate and has no remaining blocking findings.
Runtime, tests, dependencies and historical evidence are unchanged. Reuse ADR0242
regression evidence on unchanged code, without rerunning pytest, Ruff, live tests
or CI for prose. Design only: no retained dispatcher, profile,
output namespace, search, point/conic calculation, SPICE or integration was run.
