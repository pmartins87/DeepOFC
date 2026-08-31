# M5R exact BR ladder and conservative interval bridge — authoritative result

Date: 2026-08-31

Scope: research/certification methodology only. This document does not promote a policy, does not modify any live/canonical solver, and certifies zero REAL routes.

## Gate A — exact BR validation ladder

Authoritative GitHub Actions run: `33426520598` (`OpenOFC M5R exact BR validation ladder`).

Aggregate artifact:

- schema: `openofc-m5r-exact-br-validation-ladder-v2`
- aggregate file SHA-256: `948139daa538ba5af8faa31b5dee3eada4efc01289f66d98dfefae135beddb9d`
- internal canonical manifest SHA-256: `13ff5cac67d466c1a1660a5a19ea5b7bf1d2321b63ae36b1d282637d84ff38f6`
- `decision.exact_reference_ladder_validated = true`
- `decision.full_game_scalable_evaluator_validated = false`
- `production_certification_eligible = false`
- `real_routes_certified = 0`

All four exact-reference cases passed the independent pure-response replay and exact coverage checks:

| Family | Player | Exact BR value | Responding infosets | Exact terminal histories | Independent replay | Abs. error |
|---|---:|---:|---:|---:|---:|---:|
| three-round-v1 | 0 | 10.418788580246916 | 204962 | 1312200 | 10.418788580246913 | 3.552713678800501e-15 |
| three-round-v1 | 1 | 10.418788580246916 | 204962 | 1312200 | 10.418788580246913 | 3.552713678800501e-15 |
| three-round-v2 | 0 | 6.843106995884774 | 96022 | 839808 | 6.8431069958847734 | 8.881784197001252e-16 |
| three-round-v2 | 1 | 6.8431069958847734 | 96022 | 839808 | 6.8431069958847734 | 0.0 |

The exact BR implementation excludes the responding player's behavioral probabilities from counterfactual reach, includes chance and opponent probabilities, maximizes consistently at each perfect-recall infoset, and independently replays the resulting pure response through the fully audited transition path.

## Gate B — conservative BR interval bridge

Authoritative GitHub Actions run: `33427294227` (`OpenOFC M5R three-round interval bridge`).

Aggregate artifact:

- schema: `openofc-m5r-three-round-interval-bridge-aggregate-v1`
- verdict: `PASS_M5R_THREE_ROUND_INTERVAL_BRIDGE`
- aggregate file SHA-256: `b44c01e1c17c8ada4e477dc008fc66975b36dca1d7e1405f66ec251a9f37e985`
- internal canonical manifest SHA-256: `8c633e92999d127888bff2cf6a8e409498e47532614f2b82c857913b5a8d550d`
- all eight positive-threshold intervals contain the exact BR
- max positive interval width: `123.11111111111114`
- minimum positive terminal-work fraction: `0.0`
- `production_certification_eligible = false`
- `real_routes_certified = 0`

The bridge has the required authority firewall: it never prunes a responding-player action and never multiplies the responding player's own policy probability into counterfactual reach. Only opponent children may be replaced by a conservative state-local utility envelope. Threshold zero reproduces the exact BR value and exact terminal-history count in all four cells.

### Positive-threshold result

The method is mathematically valid on the exact ladder, but the initially frozen positive thresholds are too coarse to be useful as certification bounds.

For V1, threshold `0.01` yields interval width `101.97222222222223` and threshold `0.05` yields `106.15277777777779`; both reduce terminal utility evaluations to zero. For V2, both thresholds yield width `123.11111111111114` and also reduce terminal utility evaluations to zero. Therefore the experiment proves conservative containment and work reduction, but it does **not** yet prove a practically tight missed-deviation upper bound.

This supersedes any informal earlier transcription of smaller positive-threshold widths. The authoritative values are those in run `33427294227` and the aggregate/hash above.

## Frozen interpretation

1. The exact three-round BR reference is validated for the two reduced benchmark families.
2. The conservative interval construction is validated against that exact reference.
3. The initial positive thresholds are not useful for certification because they collapse the terminal work to zero and leave extremely wide intervals.
4. The next scientific gate is opponent-counterfactual-reach geometry, followed by a pre-frozen calibrated threshold frontier.
5. A reduced-game PASS cannot itself grant authority to a full-game evaluator. Final transfer must preserve the same counterfactual-reach semantics and must conservatively bound the continuation/Bellman-coupled value used by the frozen full-game route evaluator, not merely terminal raw points.
6. M5H and M5C must not be advanced as certification evidence until a useful full-game conservative upper bound and a concrete frozen candidate identity are both established.

REAL remains `0/50`.