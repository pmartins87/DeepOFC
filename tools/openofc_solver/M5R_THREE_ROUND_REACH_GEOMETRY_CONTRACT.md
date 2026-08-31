# M5R three-round opponent-reach geometry contract

Status: **FROZEN RESEARCH/CERTIFICATION-METHODOLOGY CONTRACT**

This gate exists only to calibrate the prune-reach frontier of the already validated conservative three-round BR interval bridge. It cannot certify a production route, cannot promote a policy, and cannot modify the frozen solver.

## Question

For the exact V1/V2 three-round BR ladder under the same empty/uniform profile used by the exact reference and interval bridge, what positive opponent-counterfactual-reach values actually occur at children where the bridge is legally allowed to cut?

The answer determines the discrete threshold breakpoints. The prior positive thresholds `0.01` and `0.05` were deliberately coarse validation stimuli; after the authoritative bridge run they are known to be too large for a useful interval frontier.

## Frozen semantics

For each family in `{three-round-v1, three-round-v2}` and responding player in `{0,1}`:

1. Start every chance outcome with `game.chance_probability`.
2. When the responding player acts:
   - traverse every legal action;
   - do **not** multiply reach by the responding player's behavior probability;
   - increment the responding-player perfect-recall action depth.
3. When the opponent acts:
   - use the exact `game.distribution(profile, info)` probability;
   - child counterfactual reach is `parent_reach * opponent_action_probability`;
   - only after at least one responding-player action has occurred is that child a legal bridge-cut candidate;
   - record the child reach before traversing the child.
4. Traverse the complete tree. No reach threshold is applied in this geometry gate.
5. Terminal utility/scoring is not needed; terminal visits are counted solely as a complete-tree coverage invariant.

These semantics intentionally mirror the cut-site reach calculation in `m5r_three_round_interval_bridge.py`.

## Required outputs per cell

The artifact must contain:

- family and responding player;
- exact terminal-history coverage and frozen expected count;
- total legal cut-candidate opponent children;
- zero-reach candidate count;
- every distinct positive reach level represented by `float.hex()` plus its decimal value and multiplicity;
- the same level counts broken down by opponent decision round;
- minimum and maximum positive cut-candidate reach;
- number of distinct positive reach levels;
- SHA-256 over canonical unsigned JSON.

No reach level may be rounded before identity/grouping. `float.hex()` is the canonical level key.

## Frozen expected terminal coverage

- `three-round-v1`: `1,312,200` terminal histories per responding player.
- `three-round-v2`: `839,808` terminal histories per responding player.

Any mismatch is a gate failure.

## PASS criteria

A cell passes iff:

- terminal-history coverage equals the frozen expected count;
- at least one legal cut-candidate opponent child exists;
- at least one positive reach level exists;
- every recorded positive level is finite and strictly positive;
- responding-player probabilities were never used in reach;
- no bridge pruning was executed.

The four-cell aggregate passes only if all four cells pass.

## Authority firewall

Every artifact must state:

- `authority = M5R_REDUCED_EXACT_REACH_GEOMETRY_ONLY`
- `production_certification_eligible = false`
- `real_routes_certified = 0`

A PASS authorizes only the next experiment: pre-freezing a calibrated reduced-game interval frontier around the observed discrete reach breakpoints. It does **not** authorize M5H, M5C, or any REAL route.