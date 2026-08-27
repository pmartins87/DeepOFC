# M5Q External Sampling sampled-regret instrumentation and unbiasedness contract

Status: `INSTRUMENTATION_DIAGNOSTIC_ONLY / NOT_CERTIFICATION`

## Why M5Q exists

M5O established a correct regret-derived exploitability upper bound for deterministic full-tree standard CFR. M5P established that the classical worst-case high-probability External Sampling theorem is far too loose to be the primary practical DeepOFC certificate.

M5Q therefore starts the data-dependent route. Its first gate is intentionally narrower than a final martingale certificate: **verify that the exact External Sampling implementation exposes the sampled counterfactual-regret estimator we think it exposes, and that its sample mean agrees with the exact full-tree CFR regret increment at frozen strategy profiles.**

This is an implementation/estimator audit, not a strategic certificate.

## Frozen objects

The audited implementation is `deepofc.hu_two_round_mccfr.TwoRoundExternalSamplingMCCFR` on the exact two-round perfect-recall benchmark family.

M5Q instrumentation must:

- call the existing `_sampled_traversal` code path directly;
- return one P0+P1 sampled regret-delta table without applying it;
- advance only the RNG state;
- leave `iteration`, cumulative regrets, local strategy sums and local averaging clocks unchanged;
- preserve the production trainer's chance sampling, opponent-action sampling, traverser-action enumeration and pre-update strategy semantics.

The diagnostic uses a subclass in `m5q_external_sampling_unbiasedness.py`; production training code is not rewritten merely to make the audit convenient.

## Exact expectation reference

For each frozen profile, M5Q constructs the same regret-matching tables in:

1. standard undiscounted full-tree CFR (`variant='cfr'`), and
2. the instrumented External Sampling MCCFR solver.

One full-tree CFR step is taken from the frozen table. Because standard CFR has no regret discounting or clipping, `post_step_regret - pre_step_regret` is the exact expected counterfactual-regret increment for that profile.

The MCCFR solver remains frozen at the same regret table while independent sampled delta probes are drawn by advancing its RNG only.

## Profile stressors

Before any diagnostic result is observed, two profile rules are frozen:

- `uniform`: all cumulative regrets zero;
- `hash-mixed`: deterministic SHA-derived signed regret values, producing broad non-uniform regret-matching behavior without fitting to results.

## Projection audit

Comparing every sparse infoset/action coordinate directly would create severe multiple-testing and rare-visit problems. M5Q therefore freezes deterministic dense linear projections over the complete regret-delta coordinate surface.

For each projection:

- every infoset/action coordinate receives a deterministic SHA-derived sign `+1/-1`;
- signs are normalized by `sqrt(number_of_coordinates)`;
- the exact full-tree delta and every sampled delta are projected through the identical fixed linear map.

Linearity preserves unbiasedness: if the sampled coordinate estimator is unbiased, every frozen linear projection is unbiased.

Frozen diagnostic design:

- game family: Joker exact two-round benchmark;
- profile rules: `uniform`, `hash-mixed`;
- projections: 8;
- probes per profile: 4,096;
- RNG seeds: `2026090101` and `2026090137` respectively;
- acceptance diagnostic: every projection sample mean must be within `6.0` empirical standard errors of the exact expectation;
- zero empirical variance is accepted only when sample mean equals exact expectation within `1e-12`.

The 6-SE rule is a generous implementation-diagnostic gate, not a future certification confidence level. Passing it does not justify using a normal approximation for production certification.

## Required invariants

Tests must also verify:

- a sampled probe does not mutate training state except RNG;
- two fresh probes with the same seed and same frozen regret table are byte-for-byte/equality deterministic;
- standard full-tree CFR and MCCFR expose the same local regret-matching profile from the same regret table;
- all reported values are finite.

## What PASS means

A PASS supports this narrow statement:

> On the frozen exact reduced game and profile stressors, the instrumented External Sampling sampled-regret estimator behaves consistently with the exact full-tree CFR expected regret increment.

It does **not** prove the final concentration theorem, does not certify sampled cumulative regrets, and does not certify an M4Z route.

## What follows only after PASS

The next M5Q subgate may derive a high-probability data-dependent bound. That derivation must explicitly address:

1. martingale-difference construction relative to the filtration;
2. bounded increment or predictable range assumptions;
3. predictable quadratic variation / empirical variance if a Freedman/Bernstein-style term is used;
4. simultaneous confidence allocation over every regret coordinate needed by the external-regret decomposition and both players;
5. optional-stopping/time-uniform issues if a confidence sequence is claimed;
6. exact-BR coverage on precommitted reduced-game seeds/checkpoints.

No bootstrap interval, ordinary Monte Carlo standard error, learned-response residual, or raw sampled regret total may be relabeled as a production upper bound.

REAL route count remains `0/50`.
