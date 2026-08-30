# OpenOFC external research — 05H H4 counterfactual-posterior audit

Date: 2026-08-30  
Branch: `research/external-ofc-solver-audit-20260827`  
Workflow run: `33293956518`  
Head SHA: `18266c7dae1c8c00be6ac60505e7190cd2777447`  
Artifact: `openofc-external-05h-h4` (`9726992340`)  
Artifact ZIP digest: `sha256:ae805e41b55d980bb68d4627bbca157ff6721e187da8142157fdedb3e9d94780`  
Result manifest SHA-256: `06e8f09ee7ef0a0b5c182067ccefd9339820f0da942cb442c9c6a3253618b350`

## Verdict

`PASS_05H_H4_COUNTERFACTUAL_POSTERIOR_AUDIT`

Cross-seed interpretation:

`UNIFORM_COMPLETION_MATCHES_COUNTERFACTUAL_POSTERIOR_05H`

Next gate recommendation:

`BROADEN_GAME_GEOMETRY_OR_MOVE_TOWARD_LESS_REDUCED_GAME`

This result is diagnostic only and does not alter the H3 exact-BR ranking or production authority.

## Frozen support and policy reproduction

- 144 chance worlds;
- 261,076 exhaustive reachable information states;
- 43,344 ambiguous non-root information states, plus four ambiguous roots reported by the layer summary;
- frozen MCCFR budget: 4,096 iterations;
- both H1 native-profile SHA-256 fingerprints were reproduced exactly;
- completion policy SHA-256: `fa8efdc3406c584b9ea6d6684febe62472be7470a7d3799574874f92726bfc80`;
- zero action-set mismatches, illegal keys, invalid distributions, hidden-world-token leaks or posterior-mass failures.

## Seed 20260829

- native MCCFR information states: 203,731;
- counterfactually reachable information states: 20,345;
- zero-counterfactual-mass information states: 240,731;
- completion information states with positive counterfactual reach: **222**.

All 222 reachable completion states occurred at `R4_P0`. Their posterior TV versus the completion's uniform compatible-state belief was exactly:

- mean: `0.0`;
- median: `0.0`;
- p95: `0.0`;
- max: `0.0`;
- count above TV 0.01/0.05/0.10/0.25: `0/0/0/0`.

`R4_P1` contained 57,063 completion-source information states, but **zero** of them had positive acting-player counterfactual reach under M.

The native `R4_P0` portion did contain genuine signalling/posterior distortion: among 15,801 reachable ambiguous states, 126 exceeded TV 0.01, 90 exceeded 0.10 and max TV was 0.25. This is important because the audit is capable of detecting non-uniform posteriors; the zero-TV completion result is therefore not a trivially zero diagnostic.

## Seed 20260830

- native MCCFR information states: 204,215;
- counterfactually reachable information states: 20,351;
- zero-counterfactual-mass information states: 240,725;
- completion information states with positive counterfactual reach: **225**.

Again, all 225 reachable completion states occurred at `R4_P0`, and every one matched the uniform compatible-state belief exactly:

- mean/median/p95/max TV: `0.0`;
- count above TV 0.01/0.05/0.10/0.25: `0/0/0/0`.

`R4_P1` contained 56,575 completion-source information states but **zero** with positive counterfactual reach.

The native `R4_P0` portion again contained detectable non-uniform posteriors: 105 reachable ambiguous states exceeded TV 0.01, 87 exceeded 0.05, three exceeded 0.10, and max TV was 0.25.

## Scientific interpretation

H3 had already found exploitability `0.0` and NashConv `0.0` for the selected 05H policy in both independent seeds. H4 was designed to test the strongest remaining alternative explanation: that this exact reduced-game equilibrium might rely materially on uniform beliefs inserted by the completion policy at unvisited information states.

The evidence does not support that explanation. Across both seeds, every completion-source information state that actually carries positive acting-player counterfactual reach has a counterfactual posterior exactly equal to the uniform compatible-state belief used by completion. Large completion-source regions at the final P1 layer are counterfactually unreachable under the audited M policy.

At the same time, the audit detects non-uniform posteriors in native R4_P0 states, showing that the method is not mechanically forcing uniformity everywhere.

Therefore the combination `H3 exact bilateral BR + H4 exact counterfactual posterior audit` is strong evidence that the 05H equilibrium is genuine **within the frozen reduced game**, rather than an artifact of strategically wrong completion beliefs.

It still does not prove a Nash equilibrium for full OpenOFC, and Fantasy continuation remains outside this result.

`real_routes_certified = 0`.
