# 0081 — The failed numerical qualification is reproducible

Date: 2026-09-27. Measured revision: `1c8fd9e`, clean before the experiment.
Status: accepted D4 repeatability evidence, not numerical or mission acceptance.

## Procedure and observations

One user-authorized replay, no automatic retry, unchanged scenario and code:

```sh
conda run --no-capture-output -n space-nav python -m space_nav.research_experiment examples/m3_feasible_mission.toml docs/decisions/experiments/0081-research-replay.json
```

Compare the [first report](experiments/0079-research-reference.json) with the
[replay](experiments/0081-research-replay.json). Parsed `science` objects match
exactly, including both profiles, commands, boundaries, residuals, resources,
settings, counters and classification. Parsed `reproduction` objects also match
exactly, including scenario/source hashes. Only elapsed wall time differs:
20.101860458 s initially, 22.114353167 s on replay. Both are below the shared
300-second budget; each launched and completed six arcs, with no retry.

Both reports say numerical_agreement=false with integration-threshold-exceeded.
The replay intentionally exits 1 for that failed qualification. Completion of
the integrations does not qualify the trajectory. Arrival profile difference
remains 1751.286621 m; nominal target miss remains 197851062193.609 m.
Continuous safety remains unverified.

Reproduce the comparison without native computation from the repository root:

```python
import json
from pathlib import Path

root = Path("docs/decisions/experiments")
a = json.loads((root / "0079-research-reference.json").read_text())
b = json.loads((root / "0081-research-replay.json").read_text())
assert a["science"] == b["science"]
assert a["reproduction"] == b["reproduction"]
assert b["science"]["progress"]["attempted_arcs"] == 6
assert b["science"]["numerical_agreement"] is False
assert b["wall_clock"]["elapsed_s"] < 300
```

## Verification and decision

130 focused research/native/budget checks passed in 1.77 s. Ruff, strict OpenSpec,
whitespace checks and unchanged legacy SHA-256 pass. Full-suite evidence is
reused from `0138db9`: 3,604 passed in 607.53 s. It was not rerun for this
evidence-only change; Git comparison confirms no differences in `src`, `tests`,
`environment.yml` or `pyproject.toml` since that tested revision.

D4.5 is complete by combining those unchanged-code checks with this missing
repeatability evidence. Research D4 is complete as an experiment, not a usable
mission. Strict M3 and task 3.9 remain open; no change is archived. Do not infer
accuracy from determinism. No optimizer, force changes or relaxed tolerances.

Next proposed work remains the separately bounded identical-start coast study
from [Decision 0080](0080-seed-and-integration-diagnosis.md). It has not run and
needs its own agreed budget before changing the experimental protocol.
