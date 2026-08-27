# M5Q Appendix-C `M_i(sigma*)` variance-floor result — 2026-08-27

## Gate result

Workflow `33113411659`: **PASS**.

Artifact payload SHA-256:

`a85265d6a66f43dd96d8282edae3c7aaf2ef0481f8ee356eeb04125fcbe4c237`

Artifact ZIP digest:

`sha256:5da63d4643c1794d7b9a2652b7f6450e5489e122be40d7276017aa8bf65d365c`

Durable payload:

`evidence/strategic/m5q_appendix_c_mstar_floor_2026-08-27.json`

## What was tested

The gate instantiated the strategy-dependent `M_i(sigma_i*)` deterministic term from Gibson's long-form Appendix C, Theorem C.1, using independently exact pure best responses in the reduced two-round games.

This was deliberately an impossible-best-case feasibility floor:

- estimator variance = `0`;
- sampling probability floor `delta = 1`;
- therefore `DeltaHatPrime = Delta_u`;
- no production confidence/certificate claim.

Profiles were frozen before observation:

- Joker uniform;
- Joker standard full-tree CFR average after 8 iterations;
- hidden-discard uniform;
- hidden-discard standard full-tree CFR average after 1 iteration.

## Structural reduction

The exact best-response reach reduced the static M-value, but not by orders of magnitude:

- Joker: static `M_i = 301.4270353022821`; exact-BR `M_i(sigma*) = 219.26865167650712`; ratio `0.7274352529679909`.
- hidden-discard: static `M_i = 1188.9767044688751`; exact-BR `M_i(sigma*) = 795.4795634373298`; ratio `0.669045541807042`.

For both frozen profiles within each family, the pure BR activates the same own-sequence groups, so the M-star floor is identical inside the family even though exact exploitability differs.

## Optimistic iteration floors for exploitability 0.15

### Joker

With the artificial unit utility range `Delta_u=1`:

- coefficient `657.8059550295213`;
- bound at 1,000,000 iterations `0.6578059550295213`;
- required iterations `19,231,497`.

With the conservative project raw HU range `Delta_u=206`:

- coefficient `135,508.0267360814`;
- bound at 1,000,000 iterations `135.5080267360814`;
- required iterations `816,107,791,552`.

### Hidden-discard

With `Delta_u=1`:

- coefficient `3645.34531324199`;
- bound at 1,000,000 iterations `3.64534531324199`;
- required iterations `590,601,887`.

With `Delta_u=206`:

- coefficient `750,941.13452785`;
- bound at 1,000,000 iterations `750.94113452785`;
- required iterations `25,062,781,667,822`.

## Decision

**The Appendix-C M-star refinement is mathematically worth retaining, but the global-range zero-variance floor is still not a practical production certificate.**

The result is much tighter than the published `|I| sqrt(|A|)` deterministic term, especially on the Joker family, but it is still evaluated under assumptions that are strictly more favorable than the real External Sampling process. Actual estimator variance is nonzero. More importantly, the convenient sampled-value bound `DeltaHatPrime = Delta_u / delta` requires a strictly positive sampling-probability floor. The current regret-matching External Sampling kernel can assign zero probability to legal opponent actions after regret updates, so a global terminal-history `delta` may collapse to zero unless exploration/support is explicitly guaranteed.

Therefore the next gate is **support/range feasibility before variance estimation**:

1. derive the exact terminal utility range on the reduced games instead of relying only on the global `206` envelope;
2. audit the actual External Sampling support probability `q(z)` under frozen current profiles;
3. detect whether `min_z q(z)` is zero under the present no-explicit-exploration regret matcher;
4. only if a finite, defensible `DeltaHatPrime` survives those checks should we spend work on exact estimator variance or simultaneous concentration.

No threshold is tuned from these results. No sampled regret table is promoted. No M4Z route becomes REAL.

**REAL = 0/50.**
