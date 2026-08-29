# EXTERNAL 05H-A0 — MCCFR simple-average implementation fidelity contract

Authority: `BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

This parallel research gate is frozen before 05H-H3 exploitability is observed. It does not alter the already frozen H1/H2/H3 current-policy path.

## Motivation

Classical CFR/MCCFR equilibrium guarantees concern an accumulated average strategy, whereas the existing OpenOFC shadow comparator exposes the instantaneous regret-matching `current_profile()`. Exact BR proved that the current policy happened to be essentially Nash in 05G, but average-policy behavior should be audited before relying on MCCFR architecture at larger scale.

Primary references are recorded in `docs/OFC_MCCFR_CURRENT_VS_AVERAGE_STRATEGY_LITERATURE_AUDIT_2026-08-29.md`.

## A0 implementation target

Implement a two-player external-sampling `SIMPLE` average accumulator analogous to OpenSpiel's simple averaging mode:

- regret updates must remain exactly the existing `OverlapExternalSamplingMCCFR` updates;
- RNG call sequence must remain unchanged;
- when traversing player i and encountering the opponent's visited information set, accumulate that opponent's current behavior distribution before sampling the opponent action;
- average policy at an information set is the normalized cumulative behavior sum;
- no implicit unvisited policy is counted as average-native.

## Required fidelity tests

For identical fixture, seed and iteration count, the average-enabled solver versus the existing solver must have exactly equal:

- cumulative regret tables;
- action sets;
- terminal evaluation counts;
- iteration counts;
- `current_profile()` distributions.

The average profile must be deterministic for fixed seed, legal, finite, non-negative and normalized.

A0 contains no strategic payoff comparison and cannot promote either current or average policy.

## Routing

A0 mechanical PASS permits a later parallel current-vs-average comparator. That comparator must use identical chance support, seeds, frozen iteration budget, explicit completion rules and exact bilateral best response. Existing H1/H2/H3 results remain separately interpretable and are never overwritten.