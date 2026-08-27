# M5Q — Coordinate-wise Freedman union feasibility

Date: 2026-08-27

Status: **ACCOUNTING PASS / COARSE UNION+WORST-CASE-PQV ROUTE REJECTED AS PRIMARY PRACTICAL CERTIFICATE**

This gate tested the simplest support-free martingale architecture after the reach-weighted-average semantic blocker was closed on the reduced games. The result is certification-architecture evidence only.

## Frozen execution

- workflow run: `33124925558`
- job: `98700629091`
- head: `97e137fc48eb9ea0a98cd79eb95308f586ef0753`
- mechanics: `4 passed`
- artifact payload SHA-256: `2a38e5415cd68ae8fa5bbf213b3944273c7291e635a622612ab642e17eb7c01e`
- artifact ZIP SHA-256: `41577d69d4f64ccd1444cf38092ab838c4247fbbff55669f56aecf0d7d479cc4`
- familywise failure probability: `0.05`
- target exploitability: `0.15`
- probe budget: `1,000,000` iterations

## Frozen structure

| Family | infosets P0+P1 | regret action coordinates | exact Delta_u |
| --- | ---: | ---: | ---: |
| Joker | 9,784 | 39,456 | 4 |
| hidden-discard | 66,504 | 344,304 | 12 |

The construction uses one scalar Freedman bound per regret coordinate, a union bound over all coordinates, martingale-difference envelope `2*Delta_u`, and worst-case predictable variance increment `Delta_u^2`.

## Result

Even after setting the **sampled positive regret contribution to exactly zero**, so that only the unavoidable concentration penalty of this architecture remains:

| Family | concentration-only exploitability at 1M | iterations for concentration-only <= 0.15 |
| --- | ---: | ---: |
| Joker | 102.1514467164 | 462,168,059,358 |
| hidden-discard | 2243.354372870 | 222,837,682,425,538 |

Therefore this exact combination — coordinate-wise scalar Freedman, worst-case `Delta_u^2` predictable variance, global coordinate union, and a separate additive radius at every infoset — is far too conservative to be the primary practical certificate for DeepOFC.

This is a much narrower negative result than the earlier global-`delta` rejection. It does **not** reject support-free martingale certification. The dominant looseness is now identifiable: the calculation pretends every coordinate can incur full `Delta_u^2` variance on every iteration, although External Sampling updates a coordinate only when its infoset is reached.

## Next gate

The next gate therefore replaces the crude per-coordinate/per-iteration variance envelope with exact predictable infoset visitation probabilities on the reduced games:

`E[X_t(I,a)^2 | F_(t-1)] <= P_t(visit I | F_(t-1)) * Delta_u^2`.

That work has already been started on the same branch. It is structurally preferable because the reach event is known from the pre-update strategy and does not rely on post-hoc empirical variance.

## Authority firewall

No route is certified by this result. No full-game solver semantics are changed. REAL remains `0/50`.
