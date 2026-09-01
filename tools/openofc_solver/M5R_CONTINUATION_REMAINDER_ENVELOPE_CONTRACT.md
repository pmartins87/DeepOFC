# M5R — Continuation-aware remainder-envelope transfer contract

Status: **methodology transfer research only**. This contract grants no M5H/M5C authority and leaves `REAL = 0/50`.

## Problem closed by this gate

The reduced M5R interval bridge safely bounds omitted future play with a state-local interval over **current-hand raw points**. That is insufficient for the production Normal×Normal Bellman objective, whose terminal utility is

`current_hand_points + continuation_value[next_HU_state]`.

A raw-point-only upper bound can therefore understate the value of a missed unilateral deviation whenever a pruned subtree can reach a high-value continuation state.

## Conservative continuation set

For a fixed current `HUContinuationState`, the next button is the exact alternating button. Before a partial board is complete, the evaluator uses a safe mode superset:

- current Normal (`0`) -> next mode may be `0`, `14`, `15`, `16`, or `17`;
- current Fantasy `k in {14,15,16,17}` -> next mode may be `0` or the same `k`.

The two players' safe sets are combined by Cartesian product. This intentionally admits terminal combinations that may become impossible once more board cards are known; over-inclusion widens the interval but cannot invalidate an upper bound.

For a supplied complete finite 50-state continuation vector `V`, define

`Vmin = min V(s')` and `Vmax = max V(s')`

over that safe next-state set. If the previously audited raw-point envelope is `[Lraw, Uraw]`, the continuation-aware interval is

`[Lraw + Vmin, Uraw + Vmax]`.

This is a conservative Minkowski-sum bound. It does not assume that the raw-score extremum and continuation-value extremum are jointly attainable.

## Validation requirement

This construction is not certification-authoritative merely because the algebra is conservative. Before any approximate full-game BR evaluator can inherit authority, an independent validation gate must demonstrate against exact tractable games that:

1. every exact continuation-coupled terminal utility lies inside the corresponding continuation-aware state envelope;
2. exact BR values remain inside conservative BR intervals when the callback is continuation-aware;
3. threshold zero reproduces the exact continuation-coupled BR;
4. responding-player actions are never pruned;
5. both player perspectives are checked;
6. at least one nonzero, pre-frozen structured continuation vector is exercised in addition to the zero vector;
7. button dependence and player-exchange sign behavior are represented by the structured vector or a separate exact check;
8. one containment failure removes authority from the transfer method.

The validation continuation vectors must be frozen before the corresponding exact/interval results are observed.

## Production boundary

Passing a tractable continuation-aware validation gate proves only the correctness of this bounding construction on the configured validation scope. It does not prove that a particular production threshold is useful, does not freeze a production candidate policy, and does not certify any real route.

A later full-game M5R evaluator must still bind:

- the complete frozen candidate-policy SHA-256;
- the exact continuation-vector SHA-256 used by the policy/objective;
- an independently justified missed-deviation upper bound;
- pre-frozen approximation budgets/thresholds;
- validation evidence whose scope covers the deployed evaluator semantics.

Only then may M5H consume a certification-eligible evaluator manifest, and only M5C may create a REAL route.