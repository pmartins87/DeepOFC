# M5Q — Predictable infoset-visitation variance

Date: 2026-08-27

Status: **REDUCED-GAME PREDICTABLE VARIANCE ACCOUNTING PASS**

The previous coordinate-wise Freedman feasibility gate was dominated by an intentionally crude assumption: every regret coordinate was assigned `Delta_u^2` predictable variance on every iteration. External Sampling is much sparser than that.

This gate computed the exact pre-update probability that each traverser infoset is visited by sampled chance/opponent decisions and used the rigorous second-moment envelope

`E[X_t(I,a)^2 | F_(t-1)] <= P_t(visit I | F_(t-1)) * Delta_u^2`.

## Frozen execution

- workflow run: `33125162221`
- job: `98701420634`
- head: `0b21a34c5e2fa3480b84b2541d829037486c22e8`
- mechanics: `2 passed`
- artifact payload SHA-256: `bd0312c66eb13151a7159f1e42eafbba72544b7ab1ad272bf867cba27ce13f51`
- artifact ZIP SHA-256: `96232f4f49182ee94dc8aa87417b2af653fbd5b582819cb02d86ba2b07e64260`

All mass-conservation invariants passed for both traversers. The same total second-moment accounting was obtained under the uniform and deterministic hash-mixed profiles; the distribution across individual infosets changes, but total expected visitation mass is structural.

## Result

| Family | crude total coordinate second moment | visit-weighted total | ratio |
| --- | ---: | ---: | ---: |
| Joker | 631,296 | 1,440 | 0.0022810219 |
| hidden-discard | 49,579,776 | 37,152 | 0.0007493378 |

Equivalently, exact predictable visitation reduces the aggregate conditional second-moment envelope by roughly:

- **438.4x** for Joker;
- **1,334.5x** for hidden-discard.

The reduced-game traversal invariants are also informative:

- exactly one traverser round-3 infoset is visited per sampled traversal;
- Joker visits an expected 9 round-4 traverser infosets because own round-3 actions are enumerated;
- hidden-discard visits an expected 21 round-4 traverser infosets;
- maximum individual infoset visit probability is `0.25` on both families;
- many later infosets have much smaller predictable reach probabilities.

## Interpretation

This is the first strong positive result in the support-free concentration path. The huge Freedman-union floor was not intrinsic to support-free certification; a major part came from pretending hundreds of thousands of regret coordinates were simultaneously exposed to full variance every iteration.

The next experiment must accumulate these predictable visit probabilities along the **actual pre-update MCCFR trajectory**, bind a coordinate-specific predictable quadratic variation for every regret coordinate, and compute the resulting simultaneous Freedman regret upper bound. That experiment can be validated against exact reduced-game exploitability while remaining non-certifying until the theorem/average/full-game bridges are complete.

## Authority firewall

This PASS is an exact reduced-game variance-accounting reference. It does not yet provide a scalable full-game implementation or a final exploitability certificate. REAL remains `0/50`.
