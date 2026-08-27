# M5Q Exploration-Supported External Sampling Feasibility Contract

Status: **PRECOMMITTED FEASIBILITY GATE — NOT CERTIFICATION**

Authority: `EXPLORATION_SUPPORTED_EXTERNAL_SAMPLING_FEASIBILITY_NOT_CERTIFICATION`

## Question

M5Q-D established that the current regret-matching External Sampling kernel loses strictly positive global terminal-history sampling support after its first update, so an Appendix-C bound that requires a global `delta > 0` cannot be instantiated directly.

This gate asks the narrower question that must be answered before changing the production solver:

> If every local sampling distribution were mixed with explicit uniform exploration, would the resulting guaranteed positive support make the Appendix-C `Delta_u / delta` route computationally useful?

## Frozen exploration family

For a local information set with `A(I)` legal actions and exploration mass `epsilon`, the hypothetical sampling strategy is

`q_epsilon(a|I) = (1-epsilon) q(a|I) + epsilon / |A(I)|`.

Therefore every legal sampled action has probability at least

`epsilon / |A(I)|`.

The frozen epsilon ladder is:

- `0.01`
- `0.05`
- `0.10`
- `0.20`
- `1.00`

`epsilon = 1.00` is intentionally included because it maximizes the guaranteed minimum local action probability inside this mixture family. If even that optimistic endpoint leaves the theorem impractical, smaller exploration masses cannot rescue the global-floor route.

## Structural support calculation

For each exact two-round reduced benchmark and each traverser, enumerate every terminal history. Chance is sampled uniformly exactly as in the existing External Sampling implementation. The traverser's own actions are enumerated and therefore do not enter its sampling probability. Every non-traverser decision contributes its guaranteed local lower bound `epsilon / |A(I)|`.

For each traverser compute the exact structural lower bound

`delta_i(epsilon) = min_z [ p_chance(z) * product_{opponent sampled I on z} epsilon / |A(I)| ]`.

The theorem-facing global floor is

`delta(epsilon) = min(delta_0, delta_1)`.

This is a **guarantee for the hypothetical exploration-mixed sampling contract**, not a measurement from the current production solver.

## Frozen benchmark families

- two-round Joker perfect-recall benchmark;
- two-round hidden-discard perfect-recall benchmark.

Use each family's exact terminal utility range already audited in M5Q-D.

## Theorem accounting

For each family and epsilon:

1. compute `delta(epsilon)` structurally;
2. compute the Appendix-C zero-variance `M_i(sigma*)` floor at the uniform profile using the independently exact best-response implementation;
3. set `variance = 0`;
4. use the exact reduced-game utility range;
5. report the bound coefficient and required iterations for target exploitability `0.15`.

The uniform profile is deliberately frozen here because this is a support/theorem feasibility audit, not a strategy-quality experiment. `epsilon=1` leaves the behavior uniform and gives the best guaranteed support available in this exploration family.

## Decision rule

This gate may reject the explicit-exploration/global-floor theorem route as a practical certification architecture if the `epsilon=1` endpoint is already computationally prohibitive.

It may **not** certify a production strategy, may not change production training semantics, and may not convert any M4Z route to REAL.

If explicit exploration is later adopted for training, it is a new solver contract requiring separate convergence/quality validation and cannot inherit certification from this feasibility calculation.

## Forbidden interpretations

- no claim that exploration improves strategic quality;
- no claim that the current solver already has positive support;
- no production confidence interval;
- no empirical variance substitution;
- no post-hoc epsilon selection to manufacture a PASS;
- no increase to the REAL route count.
