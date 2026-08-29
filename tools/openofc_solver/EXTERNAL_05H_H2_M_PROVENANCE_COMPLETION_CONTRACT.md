# EXTERNAL 05H-H2 — explicit M provenance + completion contract

Authority: `BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

This contract is frozen before any 05H strategic payoff is evaluated.

## Preconditions

- 05H-H0 geometry PASS.
- 05H-H1 coverage calibration PASS.
- H1's precommitted selection rule determines the exact MCCFR iteration budget. H2 may not choose a budget using EV, best response or exploitability.

## Frozen complete profile M

For each seed independently:

1. train `OverlapExternalSamplingMCCFR` to exactly the H1-selected budget;
2. every infoset actually materialized by MCCFR is labelled `MCCFR_NATIVE` and its behavior distribution is preserved exactly;
3. every remaining exhaustive-support hole is filled by the deterministic learner-independent `COMPLETION_UNIFORM_LOCAL_BACKWARD_V1` policy;
4. completion may **never overwrite** an MCCFR-native infoset.

There is no Search-priority hybrid in 05H-H2. 05G already established that Search native support saturation is an unsuitable counterfactual-completeness mechanism; 05H tests the current M architecture directly.

## Required provenance artifact

For each seed report:

- exhaustive support count;
- MCCFR-native count and percentage;
- completion count and percentage;
- source counts by R3/R4 actor layer;
- ambiguous non-root source counts;
- MCCFR native profile SHA-256;
- completion choice/policy SHA-256;
- complete M profile SHA-256;
- complete M source-map SHA-256;
- exact preservation check for all MCCFR-native distributions;
- completion-only-in-native-holes check;
- legal action-set and normalized-probability firewalls;
- no hidden world-id leakage.

The completion policy is built once from the frozen exhaustive support and is seed-independent. MCCFR native snapshots remain seed-specific.

## Forbidden in H2

H2 performs no fixed-profile EV, cross-play, best response, NashConv, exploitability or strategic ranking.

## Routing

Mechanical H2 PASS routes directly to 05H-H3 exact bilateral best response. No source proportion, native coverage percentage or completion percentage can itself be interpreted as strategic strength.