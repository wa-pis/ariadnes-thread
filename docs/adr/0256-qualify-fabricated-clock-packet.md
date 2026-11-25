# 0256 — Qualify the fabricated realized-clock checker

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (private fabricated arithmetic only)
Implementation: complete for F10; physical producer/adapter/clock bounds remain unimplemented
Verification:94 focused,7530 portable+42 archival skips,413 live pass; CI7906pass/79skip,7985matching local/CI IDs
Scope / milestone: F10 / M3 preparation in the sole active change
Base revision: `c15efa4b741525feddcd12af5652091a62ffcad7` plus the four qualified source/test hashes
Related OpenSpec: [contract](../../openspec/changes/refine-physical-trajectory/design.md#f10-private-field-encodings-2026-11-25), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-bound-realized-clock-evidence-without-changing-commands), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; implements the artificial part of ADR0255

## Context and constraints

[ADR0255](0255-design-realized-clock-packet.md) requires separating requested
Fractions, serialized words, actual-chain observations, mass bookkeeping and
physical admission. This stage tests that contract on explicit inline artificial
operands. It does not observe native Time, acquire SPICE, execute a trajectory,
change F0 commands or supply physical error bounds. Existing required live
regressions are separately scoped; they are not a new physical campaign.

## Options considered

- Implement a native producer or physical certificate registry: deferred; neither
  has a qualified readback/force basis.
- Import the existing analytical/native conformance oracle as a general checker:
  rejected; its fixed witness and exact admission are a different scope.
- Use one private standard-library Fraction checker and reuse the existing
  bounded stdlib worker reader: selected; no dependency, public API or new solver.

## Decision and rationale

`_realized_clock_packet.check_packet` consumes at most64KiB of strict UTF-8 JSON.
It validates the fixed4event/3arc/6observation/4node schema, canonical finite
binary64 words including signed zero, reduced rationals, sources declared within
one packet, boundary/duration identities and actual-chain word links. It derives
signed clock spans/errors, commanded/effective global and actual-start local mass
ledgers with conservative interval arithmetic in both directions. Original
binary64 gate thresholds and independent dry-floor/matching decisions persist.

Unknown or unqualified bounds remain unavailable. Structural interval order,
units, mass-word containment and nonnegative norm declarations are checked
before qualification filtering. Native identity flags remain producer observations;
no native Time emulator or hash-based certificate authority is introduced.
Every output keeps scientific and physical admission unavailable, including a
fully passed fabricated consistency result. Endpoint/clock-force operands are
artificial gate inputs, never derived physical bounds.

`_realized_clock_run.run` reuses the existing bounded stdlib worker/evidence
reader with one inherited15s clock and2MiB combined input/output/log/report cap.
A caller must supervise the whole run-parent with the same absolute deadline to
bound opaque parent I/O. Qualification tests actually supply that outer watchdog,
including a stalled parent-finalization case. The exclusive durable report says
`pending-parent-check`; a separate returned/external observation records the
subsequent fsync/deadline outcome. No successful durable claim is rewritten.
First failures and safe partials are retained; failed namespaces are not reused.

## Consequences and revisit conditions

F10 qualifies artificial arithmetic and process plumbing only. F0 admissibility,
full-force seed/derivatives/guards, actual native readback and clock-to-force or
independent endpoint bounds remain open. No native adapter, executable physical
profile, old-study replay or R5.60 is admitted. F5/F7 exact semantics, fixed
boundary/command data,73/76/228/300s production limits and all physical gates
remain unchanged. Physical certificate support needs its own qualified basis;
a caller-provided scope or verification flag is insufficient.

Source-bound CI is now verified below; do not replay passed local/CI runs or
download retained artifacts again. A further ordinary preparation step
must remove a concrete remaining readback/readiness blocker, not add a generic
framework or an automatic chain of synthetic diagnostics. Pause automation for
a concrete required scientific-contract/dependency/access/user decision.

## Evidence and verification

The independent arithmetic tests cover both-direction exact ledgers, coherent
nonzero clock offsets, all eight gate thresholds and sub-ULP-over-limit values,
floor equality/straddling/deficit without matching-tolerance repair, unknown
bases/routes, physical-unqualified scope, signed-zero carry, malformed declarations
and limits. Independent review found two narrow parser issues: UTF-16/32 acceptance
and structural checks skipped after unqualified-bound filtering. Both were fixed
and eight regression cases added; the reviewer confirmed closure.

94 focused tests pass. Both required Conda regression lanes pass:7530 portable
with42 unchanged opt-in archival skips, then413 live. All1469
checkout file hashes and exact Git status remain frozen through both lanes;
Ruff and independent reviews pass. Local logs/JUnit, the synthetic outer-watchdog
property, frozen manifest and phase receipts are retained in the immutable
[validation ZIP](experiments/0256-local-validation-results.zip).
The [qualification receipt](experiments/0256-qualification.json) records source
hashes, exact commands/counts, links/protected bytes/diff and strict OpenSpec.
Source-bound CI was unobserved in the initial local receipts; the supplement
below records the subsequent result without rewriting those artifacts.
The separate [final documentation receipt](experiments/0256-doc-verification.json)
records the last planning-summary correction, unchanged code hashes and final
links/diff/strict checks; the original qualification receipt remains immutable.

The final cached whitespace check found one extra EOF newline in the new pure
test file, which an unstaged diff did not inspect. Exactly that newline was
removed: the Python AST and every production source byte are identical. All94
focused tests and Ruff pass again; the original full frozen runs remain retained
and are reused for this test-only whitespace change. The separate
[whitespace-verification receipt](experiments/0256-whitespace-verification.json)
binds final hashes, AST equivalence, matching case IDs and the final cached check.
Final-source CI was unobserved when that receipt was sealed; the earlier
receipts are not rewritten.

### Source-bound CI verification (2026-11-25)

[CI45530971440](https://github.com/wa-pis/ariadnes-thread/actions/runs/45530971440)
completed successfully on exact `a9fa9cfa1b2edb3e124e64cef97d5051f3070536`.
The original [JUnit/environment ZIP](experiments/0256-ci-validation-results.zip)
is116817bytes; its SHA-256 matches GitHub artifact14985344780's published digest.
The [CI verification receipt](experiments/0256-ci-verification.json) retains run,
job, artifact/member identities, resolved environment, per-lane counts and skips.
Portable CI has7529passes/43skips and live CI377passes/36skips:7906passes,
79skips, zero failures/errors. All7985unique case IDs match the qualified local
lanes, all94new F10 cases pass, and the previous7891IDs are preserved. The exact
42opt-in archival and37platform skip ID/reason maps match ADR0253; all37platform
cases passed locally. Python3.12.14/TudatPy1.0.0/NumPy1.26.4 remain recorded.

All four final source/test hashes match both the whitespace receipt and exact
committed Git blobs. GitHub metadata binds the results to that workflow head;
the ZIP does not independently attest every executed source byte. The intentional
test-only EOF change is accounted for by its final receipt, not compared against
the earlier pre-EOF hash as though it were an unexplained source change.

`unit.xml` embeds the raw `ariadna-f10-isolated-fixture` suite property. Its outer
supervisor completes in0.1497836s within the inherited15s limit with16455evidence
bytes. The durable report remains `pending-parent-check`; a separate returned
observation records `checked-after-fsync`. All fabricated consistency gates pass,
while scientific and physical admission remain unavailable. `live.xml` also
embeds the existing F7 producer/audit packet; its synthetic integer-event scope
does not qualify F0. Neither property creates a native readback or force bound.

This follow-up reads saved artifacts only. No tests, new SPICE/native propagation,
integration, command search or old-study replay are performed by the verifier.
Independent review and [documentary checks](experiments/0256-ci-doc-verification.json)
cover sources, IDs/skips, links/protected history, diff and strict OpenSpec.
