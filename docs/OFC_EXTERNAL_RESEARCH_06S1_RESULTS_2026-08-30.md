# OFC External Research 06S1 — Exact Suit-Canonical Tabular Reuse Diagnostic

Date: 2026-08-30

## Authority

`EXACT_SUIT_CANONICAL_TABULAR_REUSE_DIAGNOSTIC_ONLY`

This result is an engineering/representation diagnostic only. It does not authorize a production strategy or any REAL route.

- Repository: `pmartins87/DeepOFC`
- Frozen baseline: `DeepOFC@c3430819d6cb22c8ad823791a35374d56a88a32a`
- Research head used by the run: `67d83a122f8b62e656ba8b3076f912f7d28979ba`
- GitHub Actions run: `33294823234`
- Artifact id: `9727189390`
- Artifact file: `external_06s1.json`
- Seeds: `20260830`, `20260831`
- Budgets: `256`, `1024`, `4096` MCCFR iterations
- Arms: `RAW_06A_KEY`, `SUIT_ORBIT_24_EXACT`
- Suit canonicalization: exact global 24-suit orbit, lexicographic representative; no rank-changing abstraction.

## Frozen decision rule

06S1 asked one narrow question: does the exact lossless suit quotient create enough repeated downstream visits to make direct global tabular learning plausible?

The precommitted reuse-starved condition required the canonical arm to remain below the frozen repeat-update thresholds. The contract explicitly stated that a failure here must **not** be answered by simply inflating global tabular iterations; the next gate must instead change representation or move to conditioned/current-hand resolving.

## Final 4096-iteration readout

| Seed | Arm | Overall repeat-update | R1–R4 repeat-update | R1–R4 updated infosets | R1–R4 revisited infosets | Max R1–R4 visits |
|---|---|---:|---:|---:|---:|---:|
| 20260830 | RAW | 0.01849755% | 0.01233464% | 24,320 | 3 | 2 |
| 20260830 | SUIT_CANONICAL | 0.13337990% | **0.00000000%** | 22,338 | **0** | **1** |
| 20260831 | RAW | 0.01233899% | 0.01233949% | 24,309 | 3 | 2 |
| 20260831 | SUIT_CANONICAL | 0.13479516% | **0.00000000%** | 22,269 | **0** | **1** |

The exact suit quotient increases some aggregate reuse near the top of the tree, but it does not create useful downstream recurrence. In both independent seeds every updated canonical R1–R4 infoset was visited exactly once.

## Frozen verdict

`SUIT_CANONICALIZATION_EXACT_BUT_INSUFFICIENT_FOR_DIRECT_TABULAR_SCALING`

Next gate recommendation from the frozen runner:

`06R_CONDITIONED_RESOLVING_AND_GENERALIZATION_ARCHITECTURE`

## Scientific conclusion

The 24-suit canonicalization remains valuable because it is lossless and reduces equivalent representation. However, it does **not** solve the central geometry problem of the full normal-hand game: global outcome-sampling tabular learning is still starved of repeated downstream information states.

Consequently, the repository must not spend large CPU budgets merely scaling the same global tabular algorithm. The next architecture should concentrate computation around the actually observed state and/or generalize across strategically similar states.

This is a negative result with positive engineering value: it closes a tempting but structurally inefficient route before weeks or months of Ryzen 9 compute are spent on it.

## Production status

`REAL = 0/50`

No external component is promoted by this result.