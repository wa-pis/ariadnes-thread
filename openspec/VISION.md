# Ariadna — Open Space Navigation Platform

## Purpose and status

Ariadna is being developed as an open, extensible ground-based space-navigation
platform with three deliverables: an open specification, a reference
implementation, and interoperability tests. Moon-to-Mars is the first reference
mission. The current software is an engineering prototype; the broader platform
is a product direction, not a statement that every capability already exists.

An open project specification is not an adopted industry standard. Flight
qualification, onboard operation, regulatory conformity, and compatibility with
an operator's system are not claimed. Public release and licensing must be
settled explicitly before promising third-party reuse rights.

## Contract direction

The specification should describe scientific meaning independently of a
particular numerical engine. Extend contracts only when an accepted milestone
needs them; do not build a generic plugin framework now.

| Contract | Intended content |
|---|---|
| State | Position, velocity, epoch, units, origin, orientation; uncertainty when available, never a fabricated zero covariance. |
| Observation | Observable, participants, epoch, units, uncertainty model, and provenance. |
| Mission problem | Initial conditions, objectives, constraints, spacecraft parameters, and declared physical models. |
| Result | Trajectory, maneuvers, physical/convergence status, numerical checks, and resource provenance. |

SI, TDB seconds since J2000, SSB origin, and J2000 orientation remain the internal
contract. Interchange adapters must explicitly convert units, time scales, and
frames required by their declared profiles; a matching field name is not proof
of matching scientific meaning. Unknown or unsupported semantics must fail
clearly. Schema versions and migration behavior need explicit acceptance before
a public contract is revised.

Python and TudatPy/SPICE remain the reference implementation stack. Existing
Python package and CLI names remain unchanged. Additional engines, measurement
providers, and force models are extension directions, not current support claims.

## Interoperability direction

Reuse existing exchange standards rather than invent competing orbit or tracking
formats. CCSDS Orbit Data Messages (ODM), including Orbit Ephemeris Messages
(OEM), are the initial trajectory-exchange target. Tracking Data Messages (TDM)
are a future observation-exchange target. These formats do not prescribe the
entire mission planner, force model, estimator, or maneuver optimizer.

The proposed first slice is a declared trajectory contract, a TudatPy calculation,
an OEM export, and verification by an independent reader. Before scheduling it,
an accepted change must define the exact standard edition and corrections,
encoding, supported metadata/frames/time scales, numerical tolerances, and
positive and rejection fixtures. Compare decoded epochs and physical states,
not just successful parsing. Unsupported optional fields and extension handling
must be specified. No exporter, reader dependency, or backend abstraction is
introduced by this vision update.

Claim compatibility only for a named profile and tested version. Retain evidence
identifying the independent implementation and the tested fixtures. Passing
format tests does not validate the trajectory's physics or flight suitability.

## Russian and international applicability

CCSDS is an international standards effort, not a US-only navigation system.
The CCSDS April 2023 ODM publication ballot records ROSCOSMOS among approving
agencies. That is evidence of participation, not proof that every Russian
mission or ground system implements ODM/OEM.

Russia also has national space-data standards; for example, GOST R 56096-2014
addresses packet telemetry. Packet telemetry and orbit-message exchange are
different layers: the former must not be presented as a replacement for OEM.
This review has not established a directly equivalent Russian adoption of the
selected ODM/TDM editions or any specific Russian operator's interface profile.
No blanket Russian compliance claim follows from CCSDS support.

For a real integration, obtain the receiving system's interface specification,
exact document editions, reference-frame/time conventions, required fields, and
test fixtures. Add a narrowly scoped adapter and conformance tests only when
that integration is in an accepted change.

Sources checked on 2026-09-06:

- [CCSDS ODM catalog: 502.0-B-3](https://ccsds.org/publications/allpubs/entry/3073/).
- [CCSDS ODM publication ballot, April 2023](https://mailman.ccsds.org/pipermail/moims-nav-exec/2023-April/001374.html).
- [Rosstandart: GOST R 56096-2014, packet telemetry](https://protect.gost.ru/document.aspx?control=7&id=238492).

## Execution boundary

Follow the existing linear roadmap and keep one active change. M3 remains
physical trajectory refinement; this document neither completes it nor adds new
implementation tasks. Assign the interoperability slice through explicit
OpenSpec acceptance before implementing it. Preserve existing APIs, numerical
gates, dependency pins, and the educational `moon_to_mars.py` file.
