# 0039 — Bind physical evidence before interval composition

Date: 2026-09-14. Parent revision: `ab954f0`. Task 3.9 remains open.

## Observed gap

The same live probe computes the fresh cubic, endpoint residual, error
transport and conditional clearance in `tests/test_trajectory_spk.py`.
It preserves the incoming handoff and checks both native history endpoints
after the force probes. This is stronger than unrelated saved numbers, but
the retained JSON reports are not independently usable interval evidence:

- `m3_fresh_cubic_reference.json` stores the initial six-state vector,
  exact reference endpoint and native residual norms, not the actual native
  terminal vector. A residual norm cannot reconstruct that vector.
- `m3_fresh_error_transport.json` stores epoch, duration, model, incoming
  radii and outgoing bounds, but neither endpoint vector nor coast mass.
- `m3_fresh_conditional_clearance.json` stores interval/domain, incoming
  radii, mass, PCK hash and eight margins, but neither endpoint vector.
- Harmonic coefficient identities and PCK inputs are retained separately
  in `m3_fresh_harmonic_replay.json`; the Sun velocity binding has its SPK
  hash. The main SPK inventory's `spk_files` field contains names, not a
  complete hash-bound resource manifest for these three reports.

This audit does not identify a demonstrated wrong live result. It identifies
missing standalone bindings; shared model labels and passing gate flags
alone must not authorize reuse for another state or interval.

## Smallest next implementation

Extend the existing test-local probe, without a new native arc or query,
to retain the actual initial and terminal seven-state vectors (SI,
including mass) and exact start/end epochs alongside its incoming and
outgoing error radii. Verify the saved endpoint residuals directly against
the retained exact cubic endpoint, with the existing outward rounding.
Bind transport and clearance to those same values rather than reconstructing
a native endpoint from residual magnitudes. Preserve the old, slightly
tighter shifted-reference control; fresh success is not an improvement claim.

Use the existing resource identity records. Before any cross-run consumer,
resolve the complete selected SPK chain/resource identities and coverage,
plus harmonic/PCK and force inputs; filenames or model ID alone do not
suffice. Do not introduce a production certificate class in this step.

Acceptance for this next step: WHEN a retained native endpoint, epoch or
incoming radius is altered independently, THEN the same-probe consistency
check rejects it; WHEN the unchanged report is replayed, THEN its residuals
and outgoing bounds reproduce without additional native work. This is a
planned check, not a result obtained by this documentation-only audit.

Later child composition must use the actual accepted left endpoint as the
right initial state at the identical epoch and carry its error enclosure
without shrinking/resetting it. Both domains must close with compatible
force/resource coverage. Parent retries and rejected arcs remain charged to
one operation budget. These conditions are not yet physically qualified.

## Runtime and numerical applicability

The retained fresh interval is 0.0625 s, not a mission-length result.
Its transport timer (0.000141334 s) and clearance timer (0.000030791 s)
cover those local arithmetic/report blocks, excluding their prerequisites.
The prior full-suite 497.72 s and native-inventory 158.77 s are test timings,
not a measured mission evaluation under the shared 300-second deadline.

The existing uniform-tiling counterexample uses a DIFFERENT 1/64 s control:
1,611,124,364 arcs for the candidate interval, versus the operation cap of
228 (covering just 3.5625 s even if all arcs were coast). It excludes burns,
retries and targeting. This rejects that uniform strategy only; it is not
an adaptive-method lower bound, a timing forecast, or mission infeasibility.
Do not extrapolate the fresh 1/16 s control across changing geometry either.

## Verification and scope

Read-only source/artifact audit; strict OpenSpec validation and whitespace
checks pass. No runtime code, fixtures, scientific values or limits changed;
the full suite was not rerun. No new native experiment, longer coast,
production safety claim or targeting is enabled. Next implement the
same-probe endpoint binding above; full-force scalability remains open.
