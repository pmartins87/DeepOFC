# External 06R1 — Belief-correct R4 local strength × compute contract

Status: **FROZEN BEFORE 06R1 RESULTS**  
Authority: `BELIEF_CORRECT_R4_LOCAL_RESOLVING_RESEARCH_ONLY`  
Production authority: **none** (`REAL = 0/50` remains unchanged)

## Question

At a real observed R4 P0 information state, after replacing the 06R0 future-only geometry sampler with a posterior that is correct for the frozen synthetic prefix policy, which practical local-search family buys more exact local strength per terminal evaluation: suit-canonical IS-UCT or suit-canonical outcome-sampling MCCFR?

This gate is intentionally restricted to `R4_P0_A`. At R4 P0 only two decisions remain: P0 acts, P1 observes that public placement and acts, then exact terminal scoring occurs. Therefore the root action values against an exact P1 best response can be enumerated without a heuristic continuation value.

## Frozen fixture

- Fixture: `R4_P0_A` from 06R0.
- Fixture seed: `64001`.
- Prefix action rule: the already frozen payoff-blind deterministic 06R0 prefix rule.
- Rules, physical 54-card deck with two Jokers, action space, scoring, information-state firewall and global-suit automorphism are unchanged.
- No fixture, action or budget may be selected from 06R1 payoff results.

## Posterior / belief semantics

The original 06R0 sampler is **not** a strategic posterior: it keeps the original hidden past and only re-samples unseen future packets. 06R1 must instead condition only on information actually available to the R4 P0 actor plus the frozen prefix-generation policy.

The exact synthetic posterior is defined as follows:

1. Keep all public opening cards and public placement history fixed.
2. Keep P0's own private cards/discards and current incoming packet fixed, because they are part of P0's information state.
3. Do **not** read or preserve P1's original hidden discards.
4. Enumerate every sequence of P1 hidden discard cards that:
   - uses unique physical cards;
   - is compatible with all fixed known cards; and
   - when the hand is replayed under the frozen deterministic prefix action rule, reproduces the exact observed public history.
5. Under the uniform without-replacement chance model, every complete compatible hidden-discard history has equal conditional chance weight for this frozen fixture.
6. For each compatible history, P1's still-unseen R4 packet is distributed uniformly over all 3-card combinations of the remaining physical deck.
7. Every sampled/materialized belief world must reproduce P0's exact raw and suit-canonical root information state and exact legal root action set.

Using the original concrete P1 discard sequence to choose, weight or filter a candidate is prohibited except in a separately reported validation assertion that never changes the posterior.

## Exact R4 oracle

For every legal canonical P0 root action `a`:

1. Enumerate every posterior world with its exact conditional weight.
2. Apply `a`.
3. Group resulting states by P1's **raw** information-state key. P1 may condition on everything P1 legally observes, including its current packet and own private discards, but not on P0 hidden discards.
4. Inside each P1 information set, enumerate every legal P1 action and choose the action minimizing expected P0 terminal utility.
5. Aggregate the group minima over the posterior.

Because P0's realized action is public before P1 acts, mixing at the P0 root cannot conceal the realized action from P1. Therefore the exact optimal R4 root action is the pure action with maximum exact value from the procedure above.

For any candidate root policy `pi`, define:

`exact_local_policy_regret(pi) = oracle_best_value - sum_a pi(a) * exact_value(a)`.

For a candidate top action `a*`, define:

`exact_local_top_action_regret = oracle_best_value - exact_value(a*)`.

Both regrets must be non-negative within numerical tolerance.

## Search arms

### Arm U — belief-correct suit-canonical IS-UCT

- Existing 06P0 information-set UCT equations.
- Exploration constant: `2.0`.
- One terminal evaluation per iteration.
- Fresh posterior world for every trajectory.
- Root policy for regret accounting: normalized root visit counts.
- Top action: maximum root visits, with the existing deterministic tie semantics.

### Arm M — belief-correct suit-canonical outcome-sampling MCCFR

- Existing certified suit-canonical OS-MCCFR equations.
- `epsilon = 0.6`.
- CFR+ enabled.
- Alternating update players as already implemented.
- Two terminal evaluations/episodes per MCCFR iteration.
- Fresh posterior world for each update episode.
- Root policy for regret accounting: average policy at the canonical root node.
- Top action: highest average-policy probability, lexical tie break at `1e-15` numerical equality.

## Equal-compute budgets

Terminal-evaluation budgets, cumulative per solver instance:

- `256`
- `1024`
- `4096`

IS-UCT runs exactly `budget` iterations. MCCFR runs exactly `budget / 2` iterations. Budgets are even by construction.

Learner seeds:

- `20260830`
- `20260831`

Belief/chance RNG must be separate from the algorithm's action-selection RNG so that changing exploration mechanics cannot silently redefine the posterior.

## Required measurements

For each arm × seed × budget:

- terminal evaluations;
- wall-clock training seconds;
- canonical infosets materialized;
- complete normalized root policy;
- top root action;
- exact local policy regret;
- exact local top-action regret;
- oracle-best-action agreement;
- finite/probability/accounting checks.

Also report:

- number of compatible hidden-discard histories;
- number of exact R4 posterior worlds;
- posterior reconstruction invariants;
- exact value for every legal root action;
- oracle best action/value;
- cross-seed TV and top-action agreement at every budget;
- Pareto non-dominated points in `(training_seconds, exact_local_policy_regret)` per seed.

## Frozen interpretation

Tolerance: `1e-9` exact local regret.

At the final 4096-terminal budget, for each seed:

- M wins if `regret_M + tol < regret_U`;
- U wins if `regret_U + tol < regret_M`;
- otherwise tie.

Cross-seed recommendation:

- `PROMOTE_MCCFR_TO_R2_R3_LOCAL_RESOLVER_VALIDATION` if M is never worse and strictly wins at least one seed;
- `PROMOTE_ISUCT_TO_R2_R3_LOCAL_SEARCH_VALIDATION` if U is never worse and strictly wins at least one seed;
- otherwise `NO_CROSS_SEED_R4_WINNER_CONTINUE_DIAGNOSTICS`.

The recommendation is about the **research architecture only**. It does not certify production play, Fantasy continuation value, broader state coverage, or REAL routes.

## Fail-closed rules

06R1 must fail mechanically if any of the following occurs:

- posterior world changes P0's root information state;
- hidden/private opponent information leaks into P0 keys/actions;
- duplicate physical cards occur;
- compatible-history enumeration depends on the original hidden discard realization;
- exact P1 information-set action sets collide;
- action probabilities are non-finite, negative or fail to sum to one;
- exact regret is materially negative;
- terminal-evaluation accounting differs from the frozen budgets.

No production file, canonical solver authority, TM, OpenHoldem formula or REAL route may be modified by this gate.
