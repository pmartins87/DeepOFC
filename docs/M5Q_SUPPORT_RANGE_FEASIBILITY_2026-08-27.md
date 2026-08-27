# M5Q External Sampling support/range feasibility — 2026-08-27

## Gate result

Workflow `33114239605`: **PASS**.

Source artifact payload SHA-256:

`bfd0167572f741c6260851efcf92bf47752e18ba17c9d49798bbdbeefea1b139`

Artifact ZIP digest:

`sha256:c800caee89f8d4d83737eb0bb7b1d0d470c0d6905c0af1b6df59ca7b35c57f94`

Durable summary:

`evidence/strategic/m5q_support_range_feasibility_2026-08-27.json`

## Exact reduced-game utility ranges

The global project envelope of `206` is extremely conservative for these exact two-round benchmarks.

- Joker: terminal P0 utility runs exactly from `-2` to `+2`, so `Delta_u = 4`, over `41,472` terminal histories.
- hidden-discard: terminal P0 utility runs exactly from `-6` to `+6`, so `Delta_u = 12`, over `373,248` terminal histories.

Using those exact reduced-game ranges in the Appendix-C M-star **impossible-best-case** floor (`Var=0`, `delta=1`) improves the count substantially relative to the project-wide `206` envelope, but still yields:

- Joker target exploitability `0.15`: `307,703,947` iterations;
- hidden-discard target exploitability `0.15`: `85,046,671,698` iterations.

These are still feasibility numbers only because real External Sampling has non-zero estimator variance and does not have `delta=1`.

## Actual support under the current External Sampling regret matcher

The support audit exhaustively evaluated every Joker terminal history for each traverser under the current regret-matching profile.

### Iteration 0

The initial uniform profile has full support:

- P0 traverser zero-probability histories: `0 / 41,472`;
- P1 traverser zero-probability histories: `0 / 41,472`;
- minimum sampling probability for both: `0.0005787037037037037`.

### Iteration 1

The global support floor already collapses to zero:

- P0 traverser: `5,184` zero-probability terminal histories;
- P1 traverser: `112` zero-probability terminal histories.

### Iteration 4

- P0 traverser: `9,456` zero-probability histories;
- P1 traverser: `886` zero-probability histories;
- smallest positive P0 sampling probability: `1.1564823173178708e-18`.

### Iteration 16

- P0 traverser: `14,715` zero-probability histories;
- P1 traverser: `11,817` zero-probability histories;
- smallest positive probabilities are already around `10^-19`.

## Decision

The convenient Appendix-C substitution `DeltaHatPrime = Delta_u / delta` is **not usable as a global production bound for the current no-explicit-exploration External Sampling kernel**: after the first update, `min_z q_i(z) = 0` for both traversers.

This does not invalidate External Sampling MCCFR. It closes only this particular certificate route under the current sampling policy.

The exact reduced-game utility-range result is still valuable and should be retained. It shows that route/game-local ranges can be dramatically smaller than the global `206` envelope and should eventually be derived exactly wherever a theorem needs them.

## Next architectural decision

Do not spend time estimating variance for the current `Delta/delta` Appendix-C certificate: with `delta=0`, the prerequisite is already broken.

The next certification research branch should compare two explicit alternatives before changing the production trainer:

1. **exploration-supported External Sampling** — introduce a frozen minimum exploration probability, then quantify the trade-off between guaranteed `delta>0`, theorem constants, convergence, and strategic quality;
2. **a support-free data-dependent concentration route** — derive or adopt a martingale/confidence-sequence argument that bounds sampled counterfactual-regret error without dividing by a global minimum terminal-history probability.

Any exploration change is a new solver/sampling contract and cannot inherit certification from the current kernel.

No route is promoted. **REAL = 0/50.**
