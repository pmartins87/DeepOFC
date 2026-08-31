# M5R Three-Round Conservative BR Interval Bridge Contract

Status: FROZEN VALIDATION CONTRACT  
Authority: M5R methodology validation only; not route certification and not a production-policy change.

## Purpose

Validate the scalable M5R branch-truncation idea against the exact three-round best-response ladder before any approximate best-response evaluator can acquire certification authority.

The bridge must answer one narrow question: when low counterfactual-reach opponent branches are not expanded, does the evaluator still return a mathematically conservative interval containing the exact best-response value?

## Frozen benchmark

Use exactly the two games already frozen by `M5R_EXACT_BR_VALIDATION_LADDER_CONTRACT.md`:

- `three-round-v1` / `HUThreeRoundSequentialSubgame`;
- `three-round-v2` / `HUThreeRoundSequentialSubgameV2`;
- responding players `0` and `1`;
- empty strategy profile, whose game-defined fallback is uniform over every legal opponent action.

The exact reference for every cell is `deepofc.hu_three_round_br.exact_best_response`.

## Required interval semantics

1. Chance probability and opponent behavioral probability are counterfactual reach.
2. The responding player's own behavioral probability is never multiplied into reach and can never trigger pruning.
3. Every responding-player legal action encountered on an expanded path is expanded.
4. A branch may be truncated only immediately after selecting an opponent action and only after the responding player has at least one own-action predecessor to which the skipped contribution can be attached.
5. The skipped contribution must use the canonical state-local raw-point envelope from `m5r_full_game_remainder_envelope.p0_raw_point_interval` on the child state at the cut.
6. For player 1, the P0 interval `[L,U]` is transformed to `[-U,-L]`.
7. Interval propagation through a responding-player information set is `max(lower[action])` and `max(upper[action])`. This preserves the common-action information-set constraint while bounding any omitted contribution.
8. At threshold `0`, the bridge must traverse the exact tree, evaluate the frozen exact number of terminal histories, and agree with exact BR to absolute tolerance `1e-10`.
9. Every positive-threshold cell must contain the exact BR value: `lower - 1e-10 <= exact <= upper + 1e-10`.
10. The validation must exercise at least one positive threshold that strictly reduces terminal utility evaluations and actually invokes state-local envelopes.

## Frozen thresholds

Evaluate every family/player cell at:

- `0.0` (exactness anchor),
- `0.01`,
- `0.05`.

These thresholds are validation stimuli, not production certification thresholds.

## Required evidence

For each interval result record at least:

- lower/upper BR value and width;
- exact-reference BR value;
- terminal utility evaluations;
- pruned opponent branches;
- state-local envelope calls;
- minimum/maximum observed local envelope width;
- responding-player information sets represented;
- explicit own-action-pruning count (must be zero);
- containment status.

The aggregate passes only if all four family/player cells satisfy zero-threshold exactness, all positive-threshold intervals contain exact BR, and each cell demonstrates positive-threshold work reduction with nonzero state-local envelope use.

## Authority firewall

A PASS validates the *interval methodology on the reduced exact ladder only*. It does not prove the full-game M5B policy, does not make M5H evidence certification-grade by itself, does not alter M5C thresholds, does not promote a policy, and certifies `0/50` REAL routes.

The next required step after PASS is a full-game scalable evaluator whose missed-deviation contribution is bounded by the same validated conservative semantics and whose candidate/reference identities are frozen.
