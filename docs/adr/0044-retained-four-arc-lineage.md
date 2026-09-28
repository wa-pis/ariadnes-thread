# 0044 — Retain all four nominal state/error handoffs

Date: 2026-09-14. Parent revision: `18f4bcb`. Task 3.9 remains open.

## Same native histories, explicit lineage

Append a row when the existing first nominal Mars endpoint is selected and
after each of its three nominal continuations. Each row contains the actual
initial/final seven-state, exact start/end, incoming/outgoing error radii
and the operation's native-call ordinal. Tighter diagnostic endpoints are
not selected. No new arc, force evaluation or SPICE request is introduced.

The shared live/offline check verifies durations 1/64, 1/64, 1/32, 1/16 s,
three exact epoch/state joins, constant mass, and three identical exact
error handoffs without reset. The first synthetic state's initial error
is zero, not an assumed measurement accuracy. All reported old-reference
endpoint bounds retain their gates. The last row's actual state/epoch and
outward-rounded incoming error match the existing fresh endpoint artifact;
its old shifted-reference outgoing bound remains tighter than the separate
fresh-reference result for that same native endpoint.

Accepted call ordinals are 3, 6, 9 and 12; the complete successful inventory
still charges thirteen calls. The lineage has four accepted rows, not four
total evaluations. Portable mode retains no native lineage and zero arcs.

## Serialization failure and exact recovery

The first native verification failed after 102.92 s when decimal Fraction
serialization exceeded Python's 4300-digit integer conversion limit. This
was an added diagnostic serialization failure, not a failed physical gate.
That failed verification is additional work; its elapsed time is not erased
by the successful rerun.

Store each exact radius as a hexadecimal numerator/denominator pair using
standard `hex`, `int(..., 16)` and `Fraction`. Do not disable Python's global
digit protection, truncate a value or loosen numerical bounds. A dedicated
large-rational round-trip control reproduces values beyond the decimal
limit. The retained artifact is 599541 bytes; the largest integer has
114979 bits. This intentionally verbose test evidence is not a proposed
public interchange format or production arithmetic requirement.

The corrected standalone inventory passes in 124.43 s. Eighteen new tests
cover retained replay, nine changed predecessor state components, six
changed predecessor epochs/errors, accepted-versus-charged count confusion,
and large-rational serialization. Together with existing endpoint checks,
all 53 focused tests pass in 0.68 s.

Final verification: all 3201 tests pass in 468.88 s (native inventory
146.37 s, portable 50.52 s). The exact lineage matches focused/full/saved
outputs; portable mode produces none. All previous endpoint, force/SPK,
cubic, error-transport, clearance and coast-domain scientific values
match excluding explicit timings. Ruff, strict OpenSpec, whitespace and
legacy checksum/import isolation pass. Successful inventory counts remain
thirteen/zero; test timings are not mission-scale cost measurements.

## Scope and next priority

The complete retained nominal lineage now exposes its states and exact
errors, but does not independently prove each physical enclosure or native
internal-stage safety. It does not extend the 0.125 s cumulative domain,
qualify finite burns or establish mission-scale cost. Preserve the old
controls, incoming uncertainty, production limits and shared 300-second
operation deadline. Next assess the remaining domain/defect and runtime
limits to larger qualified steps; a passed lineage check alone cannot
justify another propagation or a larger coast. Task 3.9 remains open.
