## ADDED Requirements

### Requirement: Candidate-bound orbit-state semantics
For M3 refinement, `departure_orbit` and `target_orbit` SHALL describe central-body-relative osculating Keplerian elements expressed on `J2000` axes. Departure elements SHALL apply at the selected candidate's departure-burn ignition epoch and target elements SHALL apply at its arrival-burn cutoff epoch. Cartesian conversion SHALL use the relevant M3 harmonic gravity field's gravitational parameter. Orbit altitudes SHALL continue to use the established Moon `1737400 m` and Mars `3389500 m` shape radii and SHALL NOT silently use a gravity model's normalization or default SPICE shape radius.

#### Scenario: Match direct element conversion
- **WHEN** either normalized orbit is independently converted with the same body gravitational parameter and added to the body's SSB/J2000 SPICE state at its defined epoch
- **THEN** the resulting public position and velocity differ from the scenario-to-state conversion by no more than `0.001 m` and `0.000001 m/s`

#### Scenario: Preserve circular-orbit equivalence
- **WHEN** the circular lunar orbit's argument of periapsis is increased by an angle `delta` and its true anomaly is decreased by the same angle after normalization
- **THEN** its converted Cartesian position and velocity remain equal within `0.001 m` and `0.000001 m/s` because only argument of latitude is observable

#### Scenario: Keep radii distinct
- **WHEN** the normalized orbit and force-model manifests are inspected
- **THEN** the Moon and Mars orbit-altitude shape radii remain `1737400 m` and `3389500 m`, while any different harmonic normalization radii are separately named and never substitute for them
