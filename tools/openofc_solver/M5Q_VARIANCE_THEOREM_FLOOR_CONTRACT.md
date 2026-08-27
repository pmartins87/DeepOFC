# M5Q variance-aware theorem optimistic-floor contract

Status: `REDUCED_GAME_THEOREM_FEASIBILITY / NOT_CERTIFICATION`

## Question

The sampled-regret instrumentation/unbiasedness diagnostic passed. Before deriving a new concentration inequality, M5Q tests whether the existing variance-aware CFR theorem from Gibson, Lanctot, Burch, Szafron & Bowling can possibly be practical for DeepOFC.

The relevant bound is Theorem 2 in *Generalized Sampling and Variance in Counterfactual Regret Minimization* (AAAI 2012). For bounded unbiased counterfactual-value estimators, player `i`'s average regret is bounded with probability at least `1-p` by

`(Delta_hat_i + sqrt(Var_i)/sqrt(p)) * |I_i| * sqrt(|A_i|) / sqrt(T)`.

Here `|A_i| = max_{I in I_i} |A(I)|` and `Var_i` is the theorem's maximum variance term.

Primary paper: `https://ojs.aaai.org/index.php/AAAI/article/view/8241`

## Why test the zero-variance floor first

`Var_i >= 0`. Therefore the theorem can never be tighter than the impossible optimistic case `Var_i = 0`.

If the iteration requirement is already impractical at `Var_i = 0`, measuring or estimating the actual External Sampling variance cannot rescue this theorem as a primary certificate. We can reject the theorem family without spending training compute or introducing a variance-estimation confidence problem.

This gate intentionally computes that floor before any empirical variance result is used.

## Two-player conversion

For a two-player zero-sum HU game, if both player regret statements hold, average-profile exploitability is at most half their sum. At `Var=0`, the confidence parameter disappears from the numerical floor, so the joint-confidence allocation does not affect this optimistic lower limit on required iterations.

For each player M5Q computes directly from the exact reduced game:

- `|I_i|`: number of player infosets;
- `|A_i|`: maximum legal action count over those infosets.

The optimistic exploitability-bound coefficient is

`0.5 * Delta_hat * (|I_0| sqrt(|A_0|) + |I_1| sqrt(|A_1|))`.

The required iteration floor for target exploitability `epsilon` is the ceiling of the square of `coefficient / epsilon`.

## Delta_hat surfaces

M5Q reports:

1. `Delta_hat = 1`, a normalized estimator-value range exposing pure game-structure scaling;
2. `Delta_hat = 206`, the conservative raw pairwise OFC utility range already derived and frozen in M5P.

Because the production External Sampling estimator returns downstream utilities/convex combinations on traversed actions and zeroes an unvisited infoset's sampled update, a symmetric utility interval bounded by the project pairwise range provides a conservative estimate-difference bound. The normalized unit-range result is the decisive structural floor regardless.

## Frozen families and targets

- exact two-round `joker`;
- exact two-round `hidden-discard`;
- targets: `1.0`, `0.25`, `0.15`, `0.05`.

No training is performed.

## Decision rule

This gate records the numbers rather than inventing a favorable compute threshold after seeing them. A count in the many-billions/trillions even at `Delta_hat=1` is treated as practical rejection for the Ryzen-scale DeepOFC certification program; the theorem remains a valid theoretical backstop.

If the zero-variance floor is unexpectedly modest, only then may a separate gate compute/bound the actual estimator variance.

## Authority firewall

This analysis cannot certify a route and cannot use empirical variance as if it were the theorem's true `Var` without a separate confidence argument.

REAL route count remains `0/50`.
