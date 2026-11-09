# 0167 — Prepare the split-centre ephemeris probe

Date: 2026-11-09 (Europe/Samara)
Decision status: accepted implementation of [ADR0166](0166-bound-split-centre-ephemeris-probe.md).
Implementation: R5.20 complete; R5.21 awaits separate execution instruction.
Verification: synthetic and archived metadata only for the new probe.
Scope / milestone: M3 R5.20, private capture and independent saved-data analysis.
Base revision: `b53c2fe72ba779ece62d0c0f34b9b3e041ea4681`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
[design](../../openspec/changes/refine-physical-trajectory/design.md),
[tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none.

## Context and constraints

R5.19 fixed the three epochs, two source legs, direct Moon control and static
Moon force checks. R5.20 prepares the tools and tests how they handle artificial
responses. It cannot resolve the saved R5.17 force miss or measure whether the
real capture will satisfy its deadline. The 13 kernels, motion operands,
archived reference, force formula and tolerances are unchanged.

## Options considered

- Read live values inside the arithmetic program: fewer files, but would mix
  source acquisition, numerical interpretation and their failure budgets.
- Rebuild the trajectory or reevaluate the Type 2 polynomials: unnecessary for
  fixed-state attribution and excluded by ADR0166.
- Use isolated capture and analysis children with durable evidence and
  independent validation of the saved ledger: chosen. Shared code only handles
  input binding, the file format and counters.

## Decision and rationale

The [private runner](experiments/0167/ariadna_split_run.py) binds the verified
helper and test hashes before work, takes the monotonic start before spawning
each child, and independently checks deadlines and child receipts. The
[capture](experiments/0167/ariadna_split_capture.py) checks its helper/input and
runtime/kernel identity before and after the nine E/G/B state queries and six
selectors. The maximum of 46 explicit native attempts includes setup and both
inventory snapshots. A returned value is written to the ledger before
post-call checks. Exclusive paths and an attempt marker preserve negative or
incomplete evidence; watchdog bounds do not extend the 15 s and 10 s gates.
After separate execution instruction, the private parent takes the phase
and this preparation manifest's SHA-256. Both phases use the fixed
`/private/tmp/ariadna-r521` evidence directory.

The [analyzer](experiments/0167/ariadna_split_analysis.py) reads saved evidence
in a fresh Python process with no scientific dependencies. It verifies exact
source order, state parity and archived E/B bits, then records position closure
and static Moon force separately. A finite closure miss can still yield a force
verdict. A missing identity, parity failure or invalid domain cannot qualify
that force result. Exact relative assembly retains both source legs and the
saved motion, with one final separation rounding. The analyzer reuses the
saved d0 field; three binary64 and 18 Decimal evaluations are its maxima.
The [input reader](experiments/0167/ariadna_split_inputs.py) verifies the archived
source and reference bytes without evaluating polynomials or fields.

## Evidence and verification

- [Focused pytest](experiments/0167-focused-pytest.txt): 101 passed in 2.87 s.
  Artificial states exercised the full save/read path (46 capture calls and 21
  static field evaluations), independent analytic force and coordinate checks,
  closure/force disagreement, argument and identity mutations, partial returns,
  caps, deadlines, exclusive outputs and late finalization.
- [Full pytest](experiments/0167-full-pytest.txt): 6283 passed in 802.98 s.
  All 671 tracked or new source files and Git status were frozen during pytest.
  This regression suite includes pre-existing native component tests; the new
  probe tests use only artificial sources or saved metadata.
- [Verification manifest](experiments/0167-verification.json): tested helper and
  test hashes, archive/input pins, 11 pinned runtime files checked on disk
  without scientific imports, Ruff, strict OpenSpec, links and protected bytes.
  The retained R5.17 artifacts, runtime package and educational model are intact.

## Consequences and revisit conditions

R5.21 can use the verified bytes only after separate execution instruction.
This stage performed no live R5.21 capture, polynomial evaluation or trajectory
propagation. Actual native agreement, end-to-end budget feasibility and the
sampled force outcome are unmeasured. R5.17 remains failed; no R5.3, Earth
sensitivity, strict M3 or mission safety qualification. Automation stays paused.
