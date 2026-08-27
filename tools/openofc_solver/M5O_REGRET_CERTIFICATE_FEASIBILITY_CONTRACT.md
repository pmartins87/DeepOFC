# M5O — regret-derived exploitability certificate feasibility

Status: `REDUCED_GAME_FEASIBILITY / NOT_PRODUCTION_CERTIFICATION`

## Motivation

M5L Q1/Q2 rejected the current learned best-response family as a reliable exploitability-bound evaluator. M5O tests a structurally different route: derive an upper bound from exact cumulative counterfactual regrets instead of trying to approximate best response.

The first target is deliberately the exact two-round reduced HU game, where both the CFR regret accounting and the true NashConv can be audited independently.

## Mathematical surface under test

For undiscounted standard CFR in a finite two-player zero-sum perfect-recall game, let `R_i^T(I,a)` be cumulative immediate counterfactual regret at player `i` information set `I`. Define the CFR decomposition bound

`B_i(T) = sum_I max(0, max_a R_i^T(I,a)) / T`.

The player's average external regret is upper-bounded by `B_i(T)`. For the standard reach-weighted average strategy in a two-player zero-sum game, the joint NashConv is therefore upper-bounded by

`B_NC(T) = B_0(T) + B_1(T)`

and exploitability by `B_NC(T) / 2`.

M5O does not take this equation on faith as an implementation claim. The exact reduced-game gate must compare the derived bound against an independently computed exact best-response NashConv for the same average profile.

## Required solver semantics

The feasibility gate is valid only for `TwoRoundFullTreeCFR(variant='cfr')`, which must have all of the following properties:

1. no regret clipping;
2. no DCFR discounting;
3. simultaneous per-iteration updates from the same pre-update strategy;
4. exact full-tree counterfactual regret deltas;
5. counterfactual regret reach excludes the acting player's own reach and includes chance plus opponent reach;
6. average strategy is the ordinary unweighted standard CFR average, with the player's own sequence reach;
7. the game is two-player, zero-sum and perfect recall.

CFR+, DCFR, outcome-sampling MCCFR, external-sampling MCCFR and any linearly/temporally weighted average are outside this first certificate surface. Their regret accounting requires separate derivation and validation.

## Fail-closed rules

A reduced-game certificate must refuse to run when:

- solver variant is not exactly `cfr`;
- no completed iteration exists;
- any regret/bound is non-finite;
- exact NashConv exceeds the derived NashConv bound beyond numerical tolerance;
- the exact independently evaluated profile is not the same standard CFR average being certified.

## Evidence required

For every checkpoint record:

- iteration count;
- number of information sets for each player;
- sum of positive maximum cumulative immediate counterfactual regret for each player;
- per-player average external-regret upper bound;
- joint NashConv upper bound;
- exploitability upper bound;
- independently exact NashConv/exploitability of the average profile;
- bound slack;
- source hashes and deterministic configuration.

## Authority boundary

Passing M5O on reduced exact games proves only that the **implementation of the deterministic standard-CFR regret accounting** matches the theorem on those audited games.

It does not certify any M4Z route and does not automatically transfer to the production External Sampling MCCFR architecture. A stochastic scalable certificate would require a separate M5O stage with mathematically justified sampling/estimation bounds, independently tested against exact games. Raw MCCFR regret tables are not a certificate.

REAL route count remains unchanged by M5O feasibility evidence.
