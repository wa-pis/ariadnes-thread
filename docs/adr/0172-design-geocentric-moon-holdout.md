# 0172 — Design the geocentric Moon holdout

Date: 2026-11-10 (Europe/Samara)
Decision status: accepted design; no live execution authorized.
Implementation: R5.26 pending; R5.27 not run.
Verification: R5.25 retained metadata and document checks only.
Scope / milestone: M3 R5.25; Moon relative to Earth at 16 saved rounded epochs.
Base revision: `89c9664e5075674c1f37d395c867bdb7eeae35dc`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md),
[tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none. [ADR0171](0171-frozen-coast-moon-screen-passes.md) remains a conditional screen.

## Context and constraints

R5.24 used a rounded exact-record Moon/Earth position at 16 epochs with
no direct geocentric return. It passed both lunar force gates on all 21
rows using that proxy. The unanswered question is whether the same pinned
provider actually returns those position bits. This is a check of the
source used by the existing calculation. The reference and the provider
use the same INPOP19a data; the comparison cannot establish astronomical
accuracy independently.

## Options considered

- Use the existing parity tolerance alone: sufficient for a same-model
  agreement check, but too loose to infer bit-for-bit substitution.
- Capture only the missing geocentric states and check parity and exact
  position equivalence separately: chosen.
- Recapture Earth/SSB, Moon/SSB and the three measured epochs, or
  recalculate the frozen fields or trajectory: unnecessary for this
  source question.

## Decision and rationale

### Fixed input and capture

The [inventory](experiments/0172-inputs.json) pins the finalized R5.24
report, journal and receipts, the R5.23 preparation and the earlier
R5.21 capture provenance. It lists 16 distinct binary64 `hi` words in
first proxy-row occurrence order and the 21 mapped ordinals. Five epochs
each cover two rows. Ten mapped rows have nonzero low words (six positive,
four negative); only `hi` is queried, in TDB seconds from J2000. The three
measured epochs are excluded. Read the exact geocentric six-vector
`reference_states_si.hi.G`, the rounded `geocentric_position_km` and
the archived `E` and `B` vectors from the corresponding R5.24 rows.
Duplicates must agree on these operands. Retain the old force/trajectory
inputs unchanged.

After verified preparation and separate authorization, start one fresh
capture using the same pinned Conda Python, TudatPy, SpiceyPy and resolved
CSPICE library as ADR0166/0168. Perform standard setup once and verify the
actual ordered 13-kernel inventory, resource/build/file hashes, test
sources and frozen inputs before the first selector and after the final
state. At each frozen `hi`, in order:

1. Call `spksfs(301, hi, 128)`. Check the current INPOP19a handle against
   the ordered inventory and the label and exact descriptor against the
   saved Moon 301→Earth 399 J2000 Type 2 segment. Derive record index
   12192 and coverage `[978739200, 979084800)` from the saved trailer;
   no new explicit DAF or record read. This checks which segment applies,
   without tracing the native call's internal evaluation.
2. Call `spkezr("Moon", hi, "J2000", "NONE", "Earth")` once. Preserve six
   finite raw binary64 components (km, km/s) and finite light time (s)
   before validating the response. `NONE` does not imply zero light time.

No Earth/SSB or Moon/SSB state query, Earth segment selector, repeated
measured control, other time, alternate pool, or fallback. Call order is
part of the holdout; no inference about other orders.

### Offline verdicts

In a separate fresh stdlib-only analyzer, require a finalized, bound
capture and hash-verified retained reference. At each valid epoch report:

1. **Same-model parity:** compare the exact SI values of the returned
   binary64 words (`1000 * F(raw)`) to the saved exact geocentric state.
   Test squared Euclidean norms against `(0.001 m)^2` for position and
   `(1e-6 m/s)^2` for velocity. Keep signed SI residuals. `F` interprets
   a binary64 value as an exact rational.
2. **Proxy position equivalence:** compare the three raw km position
   components to the archived proxy bits, including signed zero. Retain
   both hex words and signed SI differences. There is no nearest-rounded
   velocity bit gate: R5.24 used the saved direct Moon/SSB velocity for
   time rephasing.
3. **Archived direct closure:** using the saved Earth/SSB `E` and
   Moon/SSB `B`, test whether `RN(F(E)+F(G_new))` reproduces the
   three raw position bits of `B`. `RN` is binary64 round-to-nearest,
   ties-to-even. Keep signed residuals and report closure separately.
   These two archive operands are not contemporaneous returns from
   this capture.

A complete confirmation needs valid finalization, all 16 state parity
checks, all 48 position-bit comparisons, and all 48 archived closure
comparisons. Bit identity means the position operand in R5.24 would be
the same at the 21 linked observations, with everything else held
fixed. A bit miss does not turn a passing parity check into a provider
failure. At the [previously observed 250 s control](experiments/0168/analysis.json),
one geocentric position component differed from the nearest reference by
one binary64 step, while parity, archived direct closure and both static
Moon gates passed. A miss at a new epoch would rule out bitwise equivalence
there. Assessing its effect on the force would require a separate design.

### Budget and failure handling

Future limits: one 15 s capture (20 s watchdog) and one 10 s offline
analysis (15 s watchdog), inclusive of imports, file checks, final flush
and receipts. Count attempts before calls: one setup, 30 inventory
calls (two snapshots of `ktotal`, 13 `kdata`, and Tudat kernel count),
16 selectors and 16 states, at most 63 explicit capture calls. This does
not count transitive operations inside the native state routine. The
analyzer checks at most 16 epochs with zero native calls. The diagnostic
does not acquire new explicit Type 2 records, evaluate record polynomials
or forces, propagate, or optimize.

Keep exclusive attempt, raw report, ordered attempted/returned/completed
journal, input hashes, timings, earliest failure and child/parent receipts
for both phases. Preserve finite raw late returns before the deadline
check. Continue with scheduled rows after a finite numerical miss if
their prerequisites remain valid. Invalid identity, data, selector,
coverage or budget stops work and leaves the valid prefix and
unavailable rows explicit. An unfinalized capture cannot qualify the
holdout. No retry or sample change.

## Consequences and revisit conditions

R5.26 may prepare and verify private code using synthetic states and
saved metadata. R5.27 needs a separate execution instruction. Even full
confirmation would support source operand equivalence only at these
fixed epochs. It would not supersede the failed R5.17 result, qualify
the coast between the sample points, resolve Earth-force sensitivity,
close strict M3 or verify mission safety. Automation stays paused.

## Evidence and verification

The [input inventory](experiments/0172-inputs.json) preserves the exact
epoch words, row mapping, archived operand digests and segment
provenance. The [verification manifest](experiments/0172-verification.json)
binds the finalized R5.24 hashes, duplicate and coverage checks and
unchanged files. Only archived bytes and metadata were checked. No
SPICE query, new polynomial/force evaluation or propagation occurred.
Strict OpenSpec, local links, digests and diff were checked. The
implementation is unchanged; runtime tests were not rerun.
