# 0211 — Record the fixed-command seed refusal

- Date: 2026-11-16 (Europe/Samara)
- Decision status: accepted negative evidence under [ADR0207](0207-design-fixed-command-seed.md).
- Verification: one retained R5.59c execution, complete saved-evidence readback passed; no command proposal.
- Scope: candidate `d0001-t0035`, fixed R4 endpoints and original signed R1 excess vectors.
- Measured revision: `4dd53e69542a2a2fb75bdcb1515964fe16901a03`, synchronized, clean `dev` before launch.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-derive-and-freeze-one-fixed-command-seed), [design result](../../openspec/changes/refine-physical-trajectory/design.md#r559c-record-the-retained-command-refusal-2026-11-16), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. The physical contract [ADR0205](0205-design-fixed-command-physical-join.md) remains in force.

## Context and constraints

[ADR0210](0210-qualify-retained-command-invocation.md) qualified the
complete offline invocation. This independently requested attempt
asks whether both fixed endpoints admit one new pair under the
local two-body impulsive surrogate and the existing 500 kg dry
floor. It does not fit the interplanetary coast or test finite burns.

## Options considered

- Accept the only pair that clears the local radius guards: rejected;
  the dry floor is mandatory.
- Adjust a phase, vector, spacecraft or command duration: outside this
  once-only fixed-input experiment.
- Preserve the authenticated refusal with null commands: selected.

## Decision and rationale

Both arithmetic paths checked both signed roots at each endpoint.
The radius is the minimum on the Moon's future conic or the Mars
reverse-time conic, using the fixed spherical guard and 0.001 m margin.

| Endpoint | Root | Minimum radius (km) | Decision |
| --- | --- | ---: | --- |
| Moon | positive | 1836.942 | passes 1,737.400 km guard |
| Moon | negative | 322.328 | violates guard |
| Mars | positive | 3689.500 | passes 3,396.190 km guard |
| Mars | negative | 80.595 | violates guard |

The sole Cartesian pair (positive/positive) requires
**11,661.307589 m/s** and fails the exact
commanded dry floor before commands are emitted. Independent
duration and mass estimates differed by
4.55e-13 s and
0 kg.
For scale, applying the ideal rocket equation directly to that
recorded total would leave about **142.4 kg**.
The 2,000 kg initial mass, 500 kg floor and 450 s Isp give an
ideal budget of **6,117.707 m/s**. These scalar diagnostics
interpret the refusal; they are not new commands or a native mass
ledger. The effective ledger was not evaluated because the
commanded ledger failed first.

## Evidence and verification

The only attempt returned code 2: a complete scientific
`command-seed-unavailable` / `no-eligible-pair`, not an execution
error. It read six pinned inputs once (357,883 bytes),
used 13,363 bytes of exclusive evidence, and reached saved
readback in 0.046988 s within the shared 15 s watchdog.
The parent accepted timely durable completion. The receipt chain
and independent saved-byte audit passed, and a subsequent readback
of the same four evidence files verified the completion hash
without opening the six input archives or solving either conic.
The checked code and protected project inputs remained unchanged.

| Evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| [attempt.json](experiments/0211-r559c/attempt.json) | 1,567 | `8df6fdaa9e1ecdb75d1e9def89d14da51dde6b34817065836d9b9bfda26570f5` |
| [report.json](experiments/0211-r559c/report.json) | 9,828 | `421fb33a5ba76750e5524cd9734e2729f4e222b8a7838bd44fc8edfd86e29781` |
| [receipt.json](experiments/0211-r559c/receipt.json) | 1,785 | `627396cd7ba4e4934fda33c8c62fa611c0b7918fed74c035f568e4a222ab4189` |
| [completion.json](experiments/0211-r559c/completion.json) | 183 | `bb0e6bf9eddcd77aebf698f2c8a55d339e2e84d91d6ce6df4166b3f2519d82b5` |

The normalized input digest is `ba1b7a3316114e5d29e2c779cf0009668f8e8ea95857291b01a37477228232af`.
SPICE queries, kernel access, force evaluations, trajectory
integrations and R5.60 attempts were all zero. Strict OpenSpec,
local links, JSON/receipt digests and diff checks passed.
The implementation was unchanged; ADR0210's 15 focused and
6,431 guarded checks (494 skipped) were not repeated.

## Consequences and revisit conditions

The only R5.59c attempt is consumed. No pair may be handed to
R5.60 from this method for the frozen inputs. This rules out the
tested local construction under the stated conditions; it does not
rule out the mission or physical trajectory solutions outside
that construction. Any changed geometry, candidate or method
needs a new scientific question and design before a new attempt.
