# EXT-06R2A — R3 practical information-safe online A/B

Status: **CONDITIONAL PROTOCOL FROZEN BEFORE EXT-06R1 RESULTS**

Authority: `PRACTICAL_R3_STRENGTH_COMPUTE_RESEARCH_ONLY`

This protocol supersedes the unexecuted `EXT-06R2` single-Hero-root empirical-oracle design. The project objective is practical strength under finite compute, not a claim of globally exact R3 equilibrium.

`REAL = 0` throughout.

## Activation

Run only after EXT-06R1 mechanically passes.

- If 06R1 promotes MCCFR, MCCFR is the candidate and IS-UCT remains the control.
- If 06R1 promotes IS-UCT, IS-UCT is the candidate and MCCFR remains the control.
- If 06R1 has no cross-seed winner, do not run the strategic A/B; diagnose R4 first.

The activation rule is frozen before seeing 06R1 results.

## Core information-safety rule

At **every actual decision**, the acting agent must rebuild its search world distribution from that actor's own legal information only.

The sampler may use:

- both public boards;
- full public placement history;
- the actor's own historical private discards;
- the actor's current incoming packet;
- exact rules/deck/card-removal constraints.

It must not use:

- opponent private discards;
- opponent current packet before it is public/owned by the acting player;
- future packets;
- the concrete hidden realization stored in the test `HUState` except for facts present in the acting player's information state.

Unknown hidden cards are sampled **uniformly without replacement** from the physically possible deck after removing all legally known cards. This deliberately ignores strategic action-likelihood signalling at this stage. That is an approximation, but it is explicit, reproducible, information-safe, and shared by both methods.

This is the frozen `UNIFORM_INFORMATION_SAFE_BELIEF_V1` baseline. A later learned/action-likelihood posterior may replace it only in a separate A/B.

## Online re-solving, not root-world strategy fusion

Search is restarted from the actual actor's infoset whenever control changes. A simulation distribution created for player 0 may not be silently reused as player 1's belief and vice versa.

This rule is the practical firewall against giving a simulated opponent information about hidden discards that only the root player knew.

## Methods

Two complete online stacks are compared:

1. `ISUCT_UNIFORM_INFO_SAFE`
2. `MCCFR_UNIFORM_INFO_SAFE`

Both use:

- exact 54-card physical deck;
- exact legality and scoring;
- exact global-suit canonicalization certified by 06S0;
- the same `UNIFORM_INFORMATION_SAFE_BELIEF_V1` sampler;
- no production priors;
- no Fantasy continuation heuristic in this gate.

The only intended strategic difference is the local search/update method.

## Frozen R3 fixtures

Use both payoff-blind public prefixes already selected before payoff inspection:

- `R3_P0_A`
- `R3_P1_A`

Both are required.

## Evaluation worlds

For each fixture, materialize 128 unique information-compatible complete worlds from independent deterministic evaluation seeds:

- `R3_P0_A`: `306301`
- `R3_P1_A`: `306311`

These worlds are never used for training or method selection. Their hashes are stored in the artifact.

The concrete test world supplies the physical terminal outcome only. Every decision search inside that world must still resample from the acting player's legal information rather than reading hidden fields directly.

## Budgets

Per-decision terminal-evaluation budgets:

- 256
- 1,024

Use the same budget definition for both methods. Runtime is recorded independently.

A final 4,096 budget may be activated only if the 1,024 result is strategically ambiguous; this escalation rule is frozen now and is not allowed merely to rescue a losing method.

## Cross-play

For every evaluation world and budget, play both seat assignments:

- stack U controls P0, stack M controls P1;
- stack M controls P0, stack U controls P1.

Start at the frozen R3 root and re-solve every subsequent decision from the acting player's information.

Use deterministic common-random-number seed derivation from:

`fixture | evaluation_world_hash | budget | decision_public_history | acting_player | method`

No RNG stream is shared across methods, but seed derivation is paired and reproducible.

## Metrics

Primary practical metric:

- paired zero-sum points/hand advantage of one stack over the other after seat swapping.

Also report:

- foul frequency by method and player;
- scoop frequency;
- royalty differential;
- mean/p50/p95 decision time;
- peak information states materialized per decision;
- root-action agreement across repeated search seeds on a 16-world diagnostic subset;
- R4 oracle-best-action agreement on any downstream R4 P0 state for which the exact cached R4 oracle is computationally available within the frozen diagnostic cap of 16 states.

The R4 oracle diagnostic cannot override the primary cross-play result; it is a blunder detector.

## Frozen practical decision rule

At budget 1,024, method A is the provisional R3 winner only if all conditions hold:

1. seat-swapped paired mean advantage is positive on **both** R3 fixtures;
2. combined paired mean advantage is at least `+0.10` points/hand;
3. method A does not have a foul rate more than `1.0` percentage point worse than method B on either fixture;
4. p95 decision time is no more than `2.0x` method B unless its combined advantage is at least `+0.50` points/hand.

If both fixtures disagree in sign or combined absolute advantage is `< 0.10`, run the pre-authorized 4,096 budget. At 4,096 apply the same sign/foul/runtime rules with no further budget escalation in this gate.

Possible recommendations:

- `PROMOTE_ISUCT_R3_PRACTICAL_STACK`
- `PROMOTE_MCCFR_R3_PRACTICAL_STACK`
- `NO_R3_PRACTICAL_WINNER_KEEP_HYBRID_OR_ADD_PRIOR`

No claim of Nash equilibrium or global exploitability is permitted.

## Next boundary

A repeatable R3 practical winner may be tested at R2 under the same information-safe online architecture. R1 remains separate because 06R0/06P2 showed much weaker reuse and poor low-budget stability there.

If no method wins R3, the next experiment should add a **shared cheap value/prior layer** or rollout pruning and rerun the same equal-budget cross-play, not spend orders of magnitude more compute on raw tabular search.
