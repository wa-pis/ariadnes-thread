# 0041 — Bind the coast report to selected SPK records

Date: 2026-09-14. Parent revision: `d8f48ac`. Task 3.9 remains open.

## Existing path reused

After the test has initialized standard kernels, reuse
`ephemeris.kernel_metadata()` to hash the actual loaded files. Check the
pool snapshot immediately afterwards and again at the existing inventory
exit; this must not register or remove kernels. Duplicate registrations
must agree, and the distinct SPK paths must have distinct basenames before
matching metadata to the existing DAF handles. Deadline checks bracket
the inventory call. Hashing/pool enumeration adds work, but no propagation
arc or native state request is introduced.

While reading the already inspected position records, retain their file
identity, segment bounds/word addresses, record index/word addresses,
midpoint/radius/guard and position-coefficient digest. Pair those records
with the existing unique guarded-core selection, not a new selector or a
nearby-epoch lookup. The fresh source context contains eleven links for
the eight body-to-SSB chains and the original covered one-second domain.
Only the Sun type-2 derivative is identified as a velocity reference;
type-3 stored velocities are not silently treated as position derivatives.

`m3_fresh_spk_context.json` retains those selected records. They come from
four of the six inspected SPK files: INPOP19a and the Mars, Jupiter and
Saturn NOE files. Unused files are not claimed as selected source inputs.
The native endpoint report references the context by SHA-256, using the
pinned Python `json.dumps(sort_keys=True, allow_nan=False)` representation.
This is a test-local encoding, not a portable interchange standard or
signature proving the publisher's authenticity.

## Checks and an observed serialization failure

The shared live/offline check requires matching epoch/frame/time labels,
all eleven unique targets, correct chain centers, J2000/SPK type, consistent
record addresses/index and coverage of the entire source domain inside
each segment and its 16-ULP guarded record core. It also verifies the
context digest against the endpoint report. This does not establish all
force inputs, astronomical uncertainty or native-stage safety.

Nine new offline controls cover retained replay, a changed kernel hash,
and seven structurally inconsistent records even after recomputing the
digest. The combined endpoint module passes 23 tests in 0.07 s. The
standalone live inventory passes in 123.75 s before the extra offline
record-address consistency assertion was added; final-suite verification
below covers the final code.

The first artifact transfer went through JavaScript JSON serialization,
which removed `.0` from integer-valued floating-point fields. Python then
read integers, changing its serialized bytes and the context digest. The
replay correctly failed (1 failed, 22 passed). Preserve the Python-emitted
JSON through `apply_patch` instead; do not replace the expected digest or
weaken its check. The corrected artifact reproduces the original digest
`b00e888032a19081c8bbfd13ca73549af21224916ed997e4714fa68af7ce8cd5`.

Final verification: all 3171 tests pass in 468.49 s (native inventory
146.50 s, portable 50.72 s), retaining thirteen/zero native arcs and the
unchanged loaded pool. Focused/full/retained source contexts and endpoint
bindings agree; portable/native source contexts also agree. Prior endpoint
values match after excluding only the newly added context digest, and all
previous coast-domain science matches after excluding explicit timing
fields. Ruff, strict OpenSpec, whitespace and legacy checksum/import
isolation pass. Runtime variation is not a measured speedup or mission-cost
claim; the shared 300-second operation deadline remains unchanged.

## Scope and next prerequisite

The original endpoint states/errors remain intact with one added context
digest. No production or UI changes, new dependencies, longer coast or
weakened limits. These are selected source-file/record bindings, not a
complete replay capsule: harmonic coefficients, PCK/pool inputs, radiation
and relativity parameters remain in their existing separate evidence.
Next connect those existing force identities to the same endpoint context
before any cross-run consumer; avoid a second inventory framework. Physical
child composition and full-force subdivision runtime remain unqualified.
