# M5R prefix-subtree best-response interval contract

Authority: `RIGOROUS_PREFIX_SUBTREE_BR_INTERVAL_NOT_ROUTE_CERTIFICATION`.

This gate tests whether a frozen-policy best-response evaluator can save real terminal work while retaining a mathematically valid upper bound on missed unilateral deviation.

## Scope

The first implementation is deliberately limited to the exact enumerable two-round perfect-recall HU benchmark family (`HUTwoRoundSubgame` and subclasses). It is a certification-architecture feasibility gate, not a production-route certificate.

## Counterfactual reach rule

For the responding player, counterfactual reach contains:

- chance probability;
- every opponent action probability already observed in the prefix;
- **no responding-player strategy probability**.

The pruning point is after both round-3 actions are fixed, so the responding player's round-3 infoset and exact own predecessor action are known.

## Rigorous skipped-subtree bound

Let `r` be the counterfactual reach at a round-3 prefix and let every terminal utility for the responding player lie in `[u_min, u_max]`.

If the whole remaining round-4 continuation is skipped, future opponent probabilities sum to one and the responding player may choose any legal continuation. Therefore the skipped continuation contribution is rigorously bounded by:

`r * u_min <= continuation_value <= r * u_max`.

That interval is added directly to the responding player's already-known round-3 predecessor action. Exact continuations are accumulated normally. Max operators at round-4 and round-3 infosets propagate lower and upper bounds independently.

The resulting interval must satisfy:

`BR_lower <= exact_BR <= BR_upper`.

If an independently supplied frozen profile value is `v_i`, then:

`BR_lower - v_i <= deviation_gain <= BR_upper - v_i`.

## Work-saving requirement

A pruned prefix must not call `terminal_u0` for any descendant terminal. The report records:

- resolved terminal histories;
- skipped terminal histories;
- pruned round-3 prefixes;
- zero-reach skipped histories;
- exact terminal-work fraction.

`resolved + skipped` must equal the benchmark's complete terminal-history count.

## Exact-reference separation

The evaluator itself must not call `exact_best_response` or `expected_u0`. Exact BR and exact profile value may be computed **outside** the evaluator by the validation harness only, to test containment and quantify tightness on tractable benchmarks.

## Fail-closed boundaries

This M5R gate does not establish that:

- the global utility envelope is tight enough for production;
- the same prefix structure is scalable to the full OpenOFC continuation game;
- a useful full-game missed-deviation upper bound has been achieved;
- any M4Z/M5C route is certified.

Current route authority remains `REAL = 0/50`.

The next useful refinement after this gate is state-/subtree-local utility envelopes and/or deeper reach-mass pruning that preserve the same rigorous remainder semantics while shrinking interval width for a given amount of work.