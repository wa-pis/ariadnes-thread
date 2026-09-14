# 0040 — Retain and replay the native coast endpoints

Date: 2026-09-14. Parent revision: `be47597`. Task 3.9 remains open.

## Change and reason

Decision0039 identified that residual magnitudes did not retain the actual
native terminal vector. The existing fresh-coast probe now emits
`fresh_endpoint_binding`: both seven-component SI states including mass,
exact representable start/end epochs, incoming/outgoing error radii and
the same model/frame/time labels. Its source is the existing native history,
not an endpoint reconstructed from residuals. No new arc or SPICE query.

The test-only `_check_endpoint_binding` is used by the live probe and by
offline replay. It checks epoch/duration equality using exact Fractions,
initial-state and constant-mass agreement, and identical incoming radii
across cubic, transport and clearance reports. It reconstructs the exact
cubic endpoint with the existing helper, recomputes native endpoint L1
residuals with the original outward rounding, then replays error transport
and the single addition of the native residual. All four outgoing bounds
must reproduce, and the retained outgoing pair must match.

The old reports retain their original scientific fields unchanged. The
new JSON artifact is separate, so earlier historical evidence is preserved.
No force-model, dependency, tolerance, production limit or UI change.

## Checks and observed result

Fourteen focused controls pass in 0.06 s: an analytic nonzero-error example,
offline replay of the physical reports, eight independent state/mass/error
changes and four epoch/model/frame changes. The existing full-force native
inventory passes in 150.09 s; cubic, transport and clearance reports match
their prior artifacts exactly excluding elapsed time.

The retained interval is 978995455.2929223 to 978995455.3554223 TDB seconds
since J2000, with coast mass 2000 kg. Its outgoing bounds remain
0.00014951281615784107 m and 9.62662340905759e-7 m/s. They pass the short
control gates but do not improve on the preserved shifted-reference result.
The incoming uncertainty is not reset or reduced.

Final verification: all 3162 tests pass in 504.90 s (native inventory
165.62 s, portable inventory 68.31 s), preserving thirteen/zero arcs.
Focused and full-run endpoint reports equal the saved artifact; the three
older fresh reports match excluding elapsed time. All prior conditional
coast-domain scientific values match the Decision0038 run. The initial
comparison also included `generic_prefix_evaluation_seconds`, a timing
field without "elapsed" in its name; excluding that explicit timing field
as well resolves the comparison, with no scientific differences. Ruff,
strict OpenSpec, whitespace and unchanged legacy checksum/import isolation
checks pass. These test durations are not mission runtime measurements.

## Limits and next step

This is consistency checking, not authentication: coordinated edits to
reports, or another state with identical residual norms, are not ruled out
by residual arithmetic alone. The actual vector is now retained for exact
handoff comparison; no cross-run consumer or physical child composition is
introduced here. The live probe retains its history-immutability checks,
shared deadline checks and unchanged native counters.

Next resolve the selected SPK chain/resource identities and coverage into
the existing evidence context before cross-run reuse; retain harmonic/PCK
and force-input identities too. `ephemeris.kernel_metadata()` already
inventories the loaded pool with file hashes and checks the TudatPy/CSPICE
kernel counts; inspect/reuse that path rather than create a second generic
manifest mechanism. Pool inventory alone does not identify the selected
segment/record chain or establish its coverage. Do not add generic dispatch or extend the
coast merely because this consistency check passes. Native-stage safety,
finite burns and full-force subdivision scalability remain unqualified.
