# M5R deep opponent-branch best-response interval contract

Authority: `RIGOROUS_DEEP_BRANCH_BR_INTERVAL_NOT_ROUTE_CERTIFICATION`.

M5R-D proved that whole round-3 prefix subtrees can be skipped with a rigorous utility-envelope remainder bound. That pruning granularity is intentionally coarse. M5R-E moves the same fail-closed idea deeper into the exact best-response traversal so low-reach **opponent** branches can be skipped without ever pruning a responding-player action merely because the frozen candidate assigns it little probability.

## Scope

The first implementation is restricted to the exact enumerable two-round perfect-recall HU benchmark family. It is a certification-architecture feasibility gate, not a production-route certificate.

## Counterfactual reach

For the responding player, reach contains only:

- chance probability;
- frozen opponent action probabilities encountered on the branch.

The responding player's own policy probability is never multiplied into best-response reach.

## Allowed pruning points

A threshold may skip:

1. a complete post-round-3 continuation once both round-3 actions are known and its opponent/chance counterfactual reach is small;
2. when the opponent acts first on round 4, one complete opponent-action branch before the responding player's round-4 action;
3. when the responding player acts first on round 4, one low-reach opponent terminal action after each responding-player round-4 action.

Responding-player legal actions themselves are always represented in the maximizing information-set buckets. This prevents the candidate's own small action probability from hiding a profitable deviation.

## Remainder semantics

For any skipped branch with counterfactual reach `r` and responding-player terminal utility envelope `[u_min,u_max]`, the skipped contribution is replaced by:

`[r*u_min, r*u_max]`.

Intervals are aggregated over chance/opponent branches and maximized only at responding-player information sets. Therefore the result must satisfy:

`BR_lower <= exact_BR <= BR_upper`.

Given an independently supplied frozen profile value, the same interval yields a rigorous unilateral-deviation interval. Its width is a deterministic upper bound on how much best-response value can remain unresolved by the pruned traversal.

## Work evidence

The evaluator records resolved terminal utility calls and skipped terminal descendants by pruning level. The validation harness uses a fresh evaluator game and an instrumented `terminal_u0` wrapper so the observed number of terminal-evaluator invocations must equal the reported resolved-terminal count.

## Fail-closed boundaries

This gate does not establish full-game scalability, a production utility envelope, a production missed-deviation budget, or any M4Z/M5C route certificate. `REAL` remains `0/50`.

A production-facing evaluator still needs a state-local/full-game implementation, frozen candidate/continuation identity, independently validated utility/remainder envelopes, and integration with M5H/M5C uncertainty/provenance gates.