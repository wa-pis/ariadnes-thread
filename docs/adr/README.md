# Architecture Decision Records (ADRs)

Record consequential choices, not every command. OpenSpec remains authoritative
for requirements, milestone order and acceptance gates; these records explain why.
Use English, stable numbered filenames and links to evidence rather than copied logs.

## ADR workflow

This is the canonical ADR directory, migrated from `docs/decisions` on 2026-09-28.
Keep one shared numbering sequence; do not create a parallel decision journal.
An ADR explains a consequential architectural choice: module boundaries,
interfaces, dependencies, data contracts or scientific architecture. Experiments
remain evidence records, not automatically architectural decisions. Routine fixes,
status updates and every individual run do not require an ADR.

1. Search the journal for the affected topic and read relevant decisions before
   changing code. Follow supersession links; do not assume the newest numbered
   experiment supersedes an architectural choice.
2. Copy [the ADR template](ADR_TEMPLATE.md) to the next unused `NNNN-short-title.md`
   in the shared sequence. Record context, actual alternatives and reasons before
   or alongside implementation. Do not reconstruct unknown historical motives.
3. Use decision status `proposed`, `accepted`, `rejected` or `superseded`.
   Track implementation and verification separately. Acceptance does not mean
   the code exists, a hypothesis is proven or a mission is qualified.
4. Link the relevant OpenSpec requirement/change and evidence. OpenSpec defines
   what must hold; ADRs explain why a design was selected. A conflicting ADR must
   not silently relax an acceptance gate or enable deferred work.
5. Commit the record with the relevant change and add an entry below. When a
   choice changes, create a new record with `Supersedes`, then mark the earlier
   one `superseded` with `Superseded by`. Preserve its original rationale/results.

Historical records 0001–0086 retain their original structures and status wording:
they include scientific experiments, not just architectural choices. Paths in
Markdown now reference this directory; retained JSON and experiment scripts are
unchanged. Paths embedded in immutable evidence describe the original run.
Record 0087 and new ADRs use the template's explicit sections. Do not fabricate
missing alternatives or retroactively mark historical experiments accepted.
The list below is a curated entry point,
not a complete catalogue. Find all records with `rg --files docs/adr` and
search topics with `rg -n 'TOPIC' docs/adr --glob '*.md'`.

## Record structure

- Date, milestone, status (proposed, accepted, rejected or superseded), and scope.
- Question and constraints.
- Evidence: measured revision and dirty-state caveats, environment/resource
  identifiers, procedure, results with units, and links to artifacts. State missing
  provenance instead of inventing it. Preserve failures alongside successes.
- Interpretation: distinguish empirical observations, hypotheses and mathematical
  claims with their assumptions. State what the evidence does not establish.
- Decision and alternatives, with reasons.
- Next checks and measurable acceptance criteria; implementation status is separate
  from acceptance of a decision.

Commit a record with its evidence as a small `docs:` commit when appropriate.
Check facts, relative links, JSON syntax and the staged scope. A failed experiment
is legitimate evidence, not a passing implementation gate. Do not bundle unfinished
code merely to save the record. Code completion still requires the project checks.

Link the measured base revision in each record. Git history identifies the commit
introducing the record (`git log --follow -- docs/adr/FILE.md`); a record need
not contain its own future commit hash. For a changed decision, add a new record
linking the old one and mark the old one superseded; do not erase earlier outcomes.

## Records

- [0097 — Central correction implementation](0097-central-correction-implementation.md) — D11.2 verified: 236 focused / 3,896 full tests; one bounded native study pending.
- [0096 — One central-matrix correction contract](0096-single-central-correction-contract.md) — D11 specified: baseline, one capped solve/trial, conditional tighter repeat, 2/3/9 budget.
- [0095 — Central columns match local response](0095-central-columns-match-local-response.md) — D10.3 complete: 39 arcs / 27.93 s; discrepancies 0.00573/0.01358 pass <=0.10, no solve/selection or mission qualification.
- [0094 — Central-column implementation](0094-central-column-implementation.md) — D10.2 verified: 246 focused / 3,856 full tests; no live D10 study yet.
- [0093 — Central-column study contract](0093-central-column-study-proposal.md) — approved 2026-10-04; thirteen nominal evaluations / 39 arcs, no solve or selection; implementation verified separately.
- [0092 — Local response disagreement](0092-local-response-disagrees-with-jacobian.md) — D9.3 complete: 30 arcs / 95.75 s; eight of twelve checks pass, all four model checks fail; no selection or M3 qualification.
- [0091 — Local response implementation](0091-local-response-implementation.md) — D9.2 verified; one D9.3 live study remains.
- [0090 — Local response study contract](0090-local-response-study-contract.md) — D9 specified; implementation and experiment pending.
- [0089 — Local response diagnosis](0089-local-response-diagnosis.md) — linear prediction disagrees with retained propagation; bounded derivative study recommended.
- [0088 — Damping does not improve](0088-damping-does-not-improve.md) — completed D8 study; neither fraction selected.
- [0087 — Retained-step damping](0087-retained-direction-damping.md) — current ADR; implementation verified, live study pending.

### Historical decision and evidence records

- [0001 — Investigate the inventory deadline before optimization](0001-inventory-runtime-investigation.md)
- [0002 — Exact harmonic input duplication is observed](0002-exact-harmonic-input-duplicate.md)
- [0003 — Reuse exact harmonic errors within one inventory](0003-local-harmonic-reuse.md)
- [0004 — Count the harmonic tail once in the midpoint norm](0004-separate-harmonic-tail.md)
- [0005 — Fresh-handoff full-force evidence ledger](0005-fresh-full-force-ledger.md)
- [0006 — Expose signed point-gravity intervals](0006-point-gravity-intervals.md)
- [0007 — Bind six point forces to the fresh handoff](0007-fresh-point-gravity-binding.md)
- [0008 — Audit source-position allowance coverage](0008-source-allowance-coverage.md)
