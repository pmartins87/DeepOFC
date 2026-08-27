# M5L Q2 held-out benchmark plan — frozen before activation

Status: `PRECOMMITTED / DORMANT_PENDING_Q1 / NOT_CERTIFICATION`

## Why this is frozen now

Q2 must test benchmark families that were not used to tune the approximate reference evaluator.  Defining the games, profiles, budgets and output schema before seeing Q2 results prevents result-driven benchmark selection.

The Q2 driver is `tools/openofc_solver/run_m5l_two_round_q2.py`.  No Q2 workflow is activated yet.  The activation precondition is explicit: **M5L Q1 must complete and its evidence must be durably recorded first.**

## Held-out game families

Q0/Q0B/Q1 use the exact three-round benchmark family.  Q2 crosses into independently implemented two-round perfect-recall benchmarks:

1. `HUTwoRoundHiddenDiscardSubgame`
   - two real later Pineapple rounds;
   - ambiguous hidden round-3 discard support;
   - exact best response from `deepofc/hu_two_round_br.py`.
2. `HUTwoRoundJokerSubgame`
   - persistent physical Joker identities;
   - hidden-discard ambiguity;
   - exact best response through the same generic exact two-round BR interface, with separate Joker game construction/scoring support.

These families were not part of M5L Q0/Q0B/Q1 response tuning.

## Frozen profile stressors

Each held-out family is evaluated against:

- `uniform`;
- `hash-biased-mixed`, a deterministic SHA-derived public-infoset/action profile.

Both persistent players are tested independently.

## Frozen approximate-response budget

- outcome-sampled response training: **16,384 terminal episodes**;
- epsilon: **0.6**;
- two deterministic response-seed identities per family/profile/player.

The budget is deliberately frozen before Q2.  Q0B already demonstrated that the exact-key response method can retain multi-point underestimation even at 65,536 episodes.  Q2 is therefore a transfer/stability diagnostic, not a search for a budget that produces a preferred residual.

## Required evidence per row

Q2 records:

- family/profile/player/seed identity;
- exact BR value;
- independent exact replay of the exact pure BR;
- approximate pure-response value;
- `exact_br - approximate_response` residual;
- responding-infoset learned/fallback counts and coverage;
- response-training work and seed;
- implementation source manifest.

The approximate response may never exceed exact BR by more than numerical tolerance.

## Authority boundary

Q2 remains `HELDOUT_BENCHMARK_FAMILY_CALIBRATION_NOT_CERTIFICATION`.

A favorable Q2 residual envelope would still only permit advancement toward Q3.  It would not itself create a `LOW_EXPLOITABILITY_CERTIFICATION_ELIGIBLE` manifest.  An unstable or large held-out residual envelope ends the qualification attempt for this evaluator design unless the evaluator itself is materially redesigned and the calibration program restarted without reusing Q2 as tuning data.
