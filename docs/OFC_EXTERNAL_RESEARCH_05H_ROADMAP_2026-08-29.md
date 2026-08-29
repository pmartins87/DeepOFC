# OpenOFC external research — 05H roadmap

Date: 2026-08-29  
Authority: `BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
Canonical/production authority: **none**  
REAL routes certified: **0**

## Scientific objective

Stress-test the 05G finding — MCCFR-native + explicit local-uniform completion can form an essentially unexploitable complete reduced-game profile — on a substantially broader hidden-information fixture selected before strategic payoff is observed.

Frozen 05H support: **4×4×3×3 = 144 chance worlds** over the same exact HU R3→R4 game mechanics and public prefix.

## Gate roadmap

| Gate | Question | Authority / criterion | Status |
|---|---|---|---|
| H0 | Is the 144-world fixture physically valid and materially broader? | Geometry only; no payoff | **PASS** |
| H1 | What frozen MCCFR budget gives adequate native coverage? | 1024→2048→4096; smallest budget with both seeds >=80% nonroot and >=95% ambiguous-nonroot, else 4096 | **RUNNING** |
| H2 | Can complete M be materialized with exact source provenance? | MCCFR_NATIVE exact; completion only in holes; no payoff | **CONTRACT + RUNNER READY; NOT RUN** |
| H3 | Is complete M robust to exact bilateral best response? | exact NashConv; both seeds separate; <=1e-6 strict near-Nash | **CONTRACT + RUNNER READY; NOT RUN** |
| H4 | Does local-uniform completion match exact counterfactual posterior? | conditional on H3 strict replicated pass; TV epsilon 1e-12 | **CONTRACT + RUNNER READY; DORMANT** |

## H0 frozen result

- 144 physical worlds
- 261,076 reachable infosets
- 43,344 ambiguous non-root infosets
- 43,344 non-root infosets with >=3 compatible concrete states
- maximum compatible-state multiplicity 36
- hidden-discard collision present in both directions
- exhaustive support materialization ~103.48 s on GitHub-hosted Ubuntu CPU

H0 therefore materially increased both chance breadth and counterfactual policy-completeness burden compared with 05G.

## H1 frozen rule

Seeds: `20260829`, `20260830`.  
Snapshots: `1024`, `2048`, `4096` MCCFR iterations.

Downstream budget is selected mechanically before payoff:

1. choose the smallest tested budget for which **both seeds** reach >=80% non-root native coverage and >=95% ambiguous-nonroot native coverage;
2. if no budget satisfies both, freeze 4096 and retain explicit completion for all holes;
3. no larger post-hoc budget may be chosen after seeing exploitability.

## H2 frozen profile definition

For each seed independently:

`M = MCCFR_NATIVE at H1-selected budget + COMPLETION_UNIFORM_LOCAL_BACKWARD_V1 only where MCCFR is missing`.

There is no 05H Search/UCT hybrid. Source provenance, source-map hashes and exact native preservation are required.

## H3 frozen strategic interpretation

Exact bilateral best response is the strategic authority.

- exploitability <= `1e-6`: `NEAR_NASH_STRICT`
- `1e-6 < exploitability <= 1e-3`: `LOW_BUT_NOT_STRICT`
- exploitability > `1e-3`: `MATERIAL_EXPLOITABILITY`

Only if **both seeds** are strict is the cross-seed result `05H_NEAR_NASH_REPLICATED` and H4 becomes active. No averaging across seeds may manufacture a pass.

## H4 frozen conditional audit

If activated, H4 compares the exact unilateral-BR counterfactual posterior over compatible concrete states with the uniform distribution assumed by the completion builder. If TV remains <=1e-12 on every counterfactually relevant ambiguous completion hole across both seeds, the posterior-distortion hypothesis is rejected again at the broader fixture.

If non-uniformity appears, only then may the already-prepared counterfactual-weighted completion architecture enter a causal A/B while preserving MCCFR-native policy exactly.

## Infrastructure validation

The H2, H3 and H4 runners compile successfully. A dedicated downstream-core workflow also revalidates support/completion invariants. Additional unit tests freeze H2 source-priority behavior and H3 threshold boundaries before the expensive gates are run.

## Non-goals

05H is not production certification, not full-game OFC solution, not permission to replace canonical DeepOFC, and not a REAL-route certification. Any later promotion would require a separate explicit contract spanning representativeness, full-game approximation error, runtime integration and production safety.