# OpenOFC external research — round-adaptive practical solver architecture

Date: 2026-08-30  
Branch: `research/external-ofc-solver-audit-20260827`  
Authority: research/shadow only  
Production/REAL certification: **0/50**

## Decision

The current evidence rejects a one-algorithm-for-all-rounds architecture.

The research line should instead pursue a **round-adaptive hybrid**:

- **R1:** practical information-set sampling/search remains the leading family; do not spend additional budget trying to force local MCCFR where reuse is still starved.
- **R2-R3:** local MCCFR/resolving becomes a credible candidate because conditioned state reuse passes in both actors/seeds. It must still beat the search baseline on strength × compute under a strategically correct belief before promotion.
- **R4:** prioritize exact or near-exact local resolving/calibration wherever tractable. This round has by far the strongest measured local reuse and is the first target of the belief-correct 06R1 exact-strength gate.
- **All rounds:** preserve exact engine/scoring, the certified information firewall, physical 54-card chance model and exact global-suit automorphism. Approximation belongs in search allocation/generalization, not in rules or terminal scoring.

This is a research architecture decision, not production migration.

## Evidence

### 06R0 — conditioned suffix reuse geometry

Run: `33296463404`  
Verdict: `PASS_06R0_CONDITIONED_REUSE_GEOMETRY`

At 8,192 iterations with future-resampled conditioned roots, both learner seeds produced useful local reuse for every frozen R2+ fixture, while R1 failed the frozen gate.

| Fixture | Round/actor | Repeat-update fraction (seed A / B) | Max visits (A / B) | Both seeds useful |
|---|---:|---:|---:|---:|
| R1_P0_A | R1 P0 | 0.00853 / 0.00715 | 3 / 4 | No |
| R2_P0_A | R2 P0 | 0.01311 / 0.01211 | 4 / 4 | Yes |
| R2_P1_A | R2 P1 | 0.02579 / 0.02493 | 4 / 5 | Yes |
| R3_P0_A | R3 P0 | 0.11633 / 0.11064 | 7 / 7 | Yes |
| R3_P1_A | R3 P1 | 0.10754 / 0.10321 | 5 / 5 | Yes |
| R4_P0_A | R4 P0 | 0.28992 / 0.31189 | 6 / 6 | Yes |

Interpretation: conditioning alone does not create enough regret-table reuse at R1, but reuse rises sharply as the remaining horizon contracts.

### 06P1 — exact strength × compute in the 05G oracle game

Run: `33297851490`  
Verdict: `PASS_06P1_EXACT_STRENGTH_COMPUTE_FRONTIER`

The exact reduced-game oracle shows what happens when the regret method receives enough reusable structure:

- seed 20260829: Search budget 1,000 -> exploitability `0.6919921435` in ~1.053 s; MCCFR budget 64 -> `1.60e-14` in ~2.495 s.
- seed 20260830: Search budget 1,000 -> exploitability `0.6875845585` in ~1.032 s; MCCFR budget 64 -> `1.24e-14` in ~2.478 s.

Both families remain Pareto-nondominated because Search is faster at the cheapest point, but MCCFR buys dramatically greater exact equilibrium quality once information-set reuse is available.

### 06P2 — equal-terminal-budget R1 full-game probe

Run: `33297932559`  
Verdict: `PASS_06P2_R1_ROOT_STABILITY_COMPUTE_PROBE`

At equal terminal-evaluation budgets, runtime was almost identical between IS-UCT and MCCFR. Therefore the distinction is not explained by a gross implementation-speed advantage.

Cross-seed root behavior:

| Method | Terminal budget | Root TV | Same top action? |
|---|---:|---:|---:|
| IS-UCT | 512 | 0.66016 | No |
| IS-UCT | 2,048 | 0.52344 | No |
| IS-UCT | 8,192 | 0.21094 | **Yes** |
| MCCFR | 512 | 0.38784 | No |
| MCCFR | 2,048 | 0.28950 | No |
| MCCFR | 8,192 | 0.23940 | **No** |

Interpretation: R1 remains a poor place to force local MCCFR. IS-UCT is also noisy, but it reached cross-seed top-action agreement by the largest tested budget whereas MCCFR did not.

### 06P3 — irrecoverable-foul pruning audit

Run: `33298168449`  
Verdict: `PASS_06P3_IRRECOVERABLE_FOUL_PRUNING_AUDIT`  
Interpretation frozen by the runner: `DO_NOT_PROMOTE_FOUL_PRUNING_YET`

The simple structural classifier was far too broad:

- 69,828 information states;
- 361,494 legal actions;
- 352,562 classified prunable (`97.529%`);
- 69,384 infosets affected (`99.364%`);
- every legal R4_P1 action was classified prunable in every R4_P1 infoset.

Although the transformed completed profiles happened to retain zero exact exploitability in the tiny audit game, 67,032 rows required fallback. That is not sufficient evidence to promote this pruning rule. It remains research-only and disabled.

## Belief correction required before strategic local resolving

06R0 measured geometry only. Its sampler deliberately preserved the concrete hidden historical opponent discards and re-sampled only future packets. That is not a Bayesian/counterfactual belief suitable for a strategic strength claim.

06R1 therefore reconstructs hidden histories compatible with the actor's actual information and the frozen payoff-blind prefix policy, without consulting the original opponent hidden discard realization. R4_P0 is chosen first because the remaining game can be evaluated against an exact P1 best response, producing exact local policy regret instead of a proxy.

## Current gate

`EXT-06R1-BELIEF-CORRECT-R4-STRENGTH-COMPUTE`

Frozen comparison:

- fixture: R4_P0_A;
- terminal budgets: 256, 1,024, 4,096;
- seeds: 20260830 and 20260831;
- IS-UCT exploration: 2.0;
- MCCFR epsilon: 0.6, CFR+;
- metric: exact local policy regret against an enumerated R4 best-response oracle;
- final recommendation is determined before results by the frozen cross-seed rule.

No result from this line changes the canonical solver, TM/OpenHoldem integration or REAL certification without later broader validation.
