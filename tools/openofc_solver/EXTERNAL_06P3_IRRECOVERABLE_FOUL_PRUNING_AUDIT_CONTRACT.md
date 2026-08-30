# External OFC 06P3 — Irrecoverable-Foul Pruning Audit

Status: FROZEN BEFORE 06P3 RESULTS

## Authority

`REDUCED_GAME_PRUNING_SAFETY_AUDIT_ONLY`

06P3 evaluates one deliberately simple action-pruning approximation motivated by practical OFC solvers that filter obviously bad placements before spending Monte Carlo/search budget. The external heuristic weights are **not** imported. DeepOFC uses only its own exact row/Joker evaluator to define the candidate.

## Candidate pruning rule

For an acting player's legal action, apply the action to that player's board. The action is labelled `IRRECOVERABLE_ORDERING_FOUL` only if an adjacent pair of rows is already complete after the action and there exists **no legal row-local Joker resolution** satisfying the OFC ordering requirement for that completed pair:

- complete Top + complete Middle, but no `Middle >= Top` resolution; or
- complete Middle + complete Bottom, but no `Bottom >= Middle` resolution.

If the whole board is complete, this is equivalent to the exact `resolve_board(board) is None` foul test.

Incomplete adjacent rows are never pruned by 06P3. No draw odds, royalties, Fantasy value, hand-strength heuristic or opponent model enters this rule.

The rule is observable-state based and must classify the same action identically in every concrete hidden world belonging to one information set. Any classification disagreement is mechanical failure.

## Why this is an approximation, not a theorem of strategic dominance

Committing to a fouled board is terminally weak for the player's own board, but public placements can also signal information and alter opponent responses. 06P3 therefore does not assume that such actions may be deleted from an imperfect-information game without measurement.

Instead, the already-certified 05G exact best-response machinery is used to measure the strategic effect directly.

## Frozen reference strategy

Use the same two frozen 05G seeds:

- `20260829`
- `20260830`

For each seed reconstruct profile `M` exactly as in 05G-Q2: MCCFR native policy at 1,024 iterations plus the frozen uniform backward completion only in native holes.

The original M profile is not retrained or altered before the pruning audit.

## Frozen candidate profile

For every information state:

1. set probability of every `IRRECOVERABLE_ORDERING_FOUL` action to zero;
2. renormalize remaining original M probabilities;
3. if the remaining probability mass is zero, retain the original M row unchanged and mark `ZERO_SURVIVOR_FALLBACK`.

This creates `M_PRUNED` while changing nothing else.

No policy learning, re-solving, post-hoc tuning or heuristic replacement is allowed in 06P3.

## Required measurements

For each seed report:

- total reachable information states and legal actions;
- prunable action count/fraction;
- information states with at least one prunable action;
- counts by `R3_P0`, `R3_P1`, `R4_P0`, `R4_P1`;
- original M probability mass assigned to prunable actions overall and by layer;
- number of rows where pruning changes the distribution;
- number of `ZERO_SURVIVOR_FALLBACK` rows;
- original M and `M_PRUNED` profile hashes;
- exact exploitability and NashConv of both profiles;
- exploitability delta `M_PRUNED - M`;
- exact BR replay/coverage checks inherited from Q2.

Also report the theoretical action-count reduction available to a search implementation that applies this filter before node expansion.

## Frozen interpretation bands

Numerical tolerance: `1e-9`.

If mechanical checks pass and, for both seeds:

- zero-survivor fallback count is zero;
- original M prunable probability mass <= `1e-12`;
- `M_PRUNED` exploitability is not worse than M by more than `1e-9`;

interpretation:

`HIGH_CONFIDENCE_IRRECOVERABLE_FOUL_PRUNING_CANDIDATE`

Otherwise, if mechanical checks pass and for both seeds exploitability increase is <= `1e-4` with no zero-survivor fallback:

`EMPIRICALLY_LOW_COST_FOUL_PRUNING_CANDIDATE_NEEDS_BROADER_AB`

Otherwise:

`DO_NOT_PROMOTE_FOUL_PRUNING_YET`

These labels are reduced-game engineering recommendations only.

## Mechanical verdict

PASS requires unchanged 05G geometry, classification invariance across concrete states, complete/legal normalized M and M_PRUNED profiles, exact BR replay success, finite values, and no REAL route.

- PASS: `PASS_06P3_IRRECOVERABLE_FOUL_PRUNING_AUDIT`
- FAIL: `FAIL_06P3_PRUNING_AUDIT_MECHANICS`

## Forbidden claims

06P3 cannot establish full-game equilibrium preservation, production readiness, correct hidden-discard posterior, Fantasy continuation value or universal dominance of fouling actions.

`REAL = 0/50`.
