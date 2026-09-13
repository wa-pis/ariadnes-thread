# Decision journal

Record consequential choices, not every command. OpenSpec remains authoritative
for requirements, milestone order and acceptance gates; these records explain why.
Use English, stable numbered filenames and links to evidence rather than copied logs.

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
introducing the record (`git log --follow -- docs/decisions/FILE.md`); a record need
not contain its own future commit hash. For a changed decision, add a new record
linking the old one and mark the old one superseded; do not erase earlier outcomes.

## Records

- [0001 — Investigate the inventory deadline before optimization](0001-inventory-runtime-investigation.md)
- [0002 — Exact harmonic input duplication is observed](0002-exact-harmonic-input-duplicate.md)
- [0003 — Reuse exact harmonic errors within one inventory](0003-local-harmonic-reuse.md)
