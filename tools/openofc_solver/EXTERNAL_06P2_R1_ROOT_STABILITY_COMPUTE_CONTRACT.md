# External OFC 06P2 — R1 Root Stability/Compute Probe

Status: FROZEN BEFORE 06P2 RESULTS

## Authority

`FULL_GAME_R1_ROOT_STABILITY_COMPUTE_DIAGNOSTIC_ONLY`

06P2 compares the practical search geometry of the two currently implemented conditioned methods at one strategically clean full-game root. It is not a strength-ranking gate.

## Why R1_P0

The frozen `R1_P0_A` fixture from 06R0 is used. Before the non-dealer acts on R1 there are no prior Pineapple discards. Therefore the root observation plus the remaining physical 54-card deck permits exact uniform future resampling without needing a posterior over earlier hidden discards.

`resample_unseen_future` must preserve the exact raw and suit-canonical root infoset and legal action set.

## Candidate methods

1. `ISUCT` — `ConditionedSuitCanonicalISUCT`, exploration `2.0`.
2. `MCCFR` — `ConditionedSuitCanonicalOutcomeSamplingMCCFR`, epsilon `0.6`, CFR+.

Both use the same exact rules, scoring, information firewall, physical chance model and exact global-suit canonicalization.

## Frozen seeds

- `20260830`
- `20260831`

## Equal terminal-evaluation budgets

Cumulative terminal-evaluation budgets:

- `512`
- `2,048`
- `8,192`

ISUCT performs one terminal evaluation per iteration.

Conditioned MCCFR performs two terminal trajectories per iteration (one update player each), so its iteration targets are `256`, `1,024`, `4,096` respectively.

This equalizes the primary expensive rollout count while wall-clock time remains separately reported.

## Metrics

At every cumulative budget and seed report:

- wall-clock seconds;
- terminal evaluations / episodes;
- stored information-state count;
- canonical root legal-action count;
- root action distribution;
- top root action and its probability;
- root distribution entropy;
- deterministic distribution hash.

For ISUCT the root distribution is normalized root visit count.

For MCCFR the root distribution is the average policy of the canonical conditioned root node.

Also report:

- total-variation distance between the two seeds for the same method/budget;
- whether both seeds choose the same top root action;
- within-seed TV change from one budget to the next;
- relative wall-clock cost at equal terminal-evaluation budget.

## Mechanical quality

PASS requires:

- exact root-information preservation under resampling;
- same canonical root action set for both methods;
- normalized finite distributions;
- exact requested terminal-evaluation accounting;
- deterministic same-seed smoke already certified by 06P0/06R0;
- all 12 method/seed/budget snapshots present.

Mechanical PASS verdict:

`PASS_06P2_R1_ROOT_STABILITY_COMPUTE_PROBE`

Mechanical failure verdict:

`FAIL_06P2_R1_ROOT_STABILITY_COMPUTE_MECHANICS`

## Interpretation

Root stability is an engineering signal, not proof that the converged action is strategically correct. 06P2 must be read together with 06P1 exact reduced-game calibration and later held-out strategic evaluation.

A cheap stable method is a promising practical candidate; an unstable method may need more compute, a better prior, pruning or a different search architecture.

## Forbidden claims

06P2 cannot claim full-game exploitability, equilibrium quality, strategic superiority, posterior correctness after hidden discards, production readiness or Fantasy continuation quality.

`REAL = 0/50`.
