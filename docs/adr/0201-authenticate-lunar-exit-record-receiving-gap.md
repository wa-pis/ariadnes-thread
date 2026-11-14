# 0201 — Authenticate the lunar exit and record the receiving-data gap

- Date: 2026-11-15 (Europe/Samara)
- Decision status: accepted evidence under [ADR0199](0199-design-retained-lunar-to-mars-interface-check.md).
- Implementation: R5.54 complete; the once-only attempt is consumed.
- Verification: one isolated offline audit and readback of its bound receipts passed.
- Scope: R5.51 model B candidate `d0001-t0035` and the pinned Mars-bound references.
- Measured revision: `c6c5226a0a1f63ea97976e693e9686a792c09887`, clean synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-check-retained-lunar-to-mars-interface-readiness), [design result](../../openspec/changes/refine-physical-trajectory/design.md#r554-retained-lunar-to-mars-interface-result-2026-11-15), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0135](0135-fixed-orbit-boundary-contract.md) remains the mission interface.

## Context and constraints

[ADR0198](0198-far-lunar-range-marker-bracketed.md) establishes the
sampled 18,374 km crossing in model B. [ADR0199](0199-design-retained-lunar-to-mars-interface-check.md)
fixes a different, already stored sample for this audit: the
terminal common point, +16,000 s after the R5.51 restart.
[ADR0200](0200-prepare-retained-lunar-to-mars-audit.md) qualified the
exact worksheet on artificial inputs. This run inspects only the
selected archive members and receiving references.

## Options considered

- Treat the sampled crossing or a matching candidate ID as the
  physical join: neither supplies the required incoming state.
- Interpolate, retime or propagate a Mars-bound state: that would
  create a receiving state outside this saved-data contract.
- Authenticate the outgoing state and independently inventory the
  stored receiving records: selected once, with no retry.

## Decision and rationale

| Check | Observed result |
| --- | --- |
| Outgoing source | `source-state-authenticated`. At 979014965.9635216 TDB s since J2000, the epoch and SI/SSB/J2000 state agree bit for bit across the raw tighter RK4 row, its common sample and both audited direction records. Constant mass metadata is 1351.7475727997967 kg. |
| Ideal receiving reference | `ideal-reference-coepoch-unavailable`. Zero exact matches among 121 R1/R2 nodes. The first two nodes, 978995455.2304223 and 979205237.0486041 TDB s, bound the entire R5.51 interval without an interior ideal sample. |
| Physical interface | `physical-join-not-established`. All 29 records from five pinned reports were ineligible. No independent incoming state and mass at the same epoch and under a compatible interface were retained. |

At the terminal sample, the independently checked lunar radius is
21,097,219.385986 m and signed radial speed is
+983.562162329 m/s in both saved coordinate paths.
This is an arithmetic check of the stored outgoing state. The
time, position, velocity and mass continuity residuals are all
`null` because no compatible pair exists to compare. The audit
did not evaluate the R4 physical join or target gates.

## Evidence and verification

- The launcher exited `0` in 0.382442 s including interpreter
  startup and finalization. The bound parent receipt records
  0.344528 s before its write; the post-finalization
  deadline check passed under 15 s. No late receipt was present.
- Five selected members passed manifest, receipt, raw and compressed
  digest checks. They contained 218,972 lines,
  83,885,015 raw bytes and 25,613,216 gzip payload
  bytes. The isolated process made zero scientific imports or
  native/SPICE calls, kernel accesses, new trajectory states or
  propagations.
- The [verification manifest](experiments/0201-verification.json)
  preserves the exact recorded outcome and the SHA256 bindings of
  the attempt, report and receipt (11,500 bytes total), with the
  design, preparation, measured revision and authorization digests.
  Original output remains in `/Users/agrudin/dev/my/ariadna-evidence/R5.54` outside the checkout.
  Readback verified the certificate without replaying the audit.
- Source pins, local links, evidence JSON, diff and strict OpenSpec
  passed. The code is unchanged from ADR0200 (30 focused tests,
  6,247 guarded passed, 494 skipped; Ruff passed), so runtime
  regression was not rerun.

## Consequences and revisit conditions

The authenticated model B state may be used as a source packet
for a later study. A physical check still needs an independently
produced Mars-bound receiving state and mass at the same event and
epoch under a separately defined, compatible force contract.
This audit establishes neither physical continuity nor Mars
arrival, capture, safety or strict M3 completion. No rerun is
authorized by this result.
