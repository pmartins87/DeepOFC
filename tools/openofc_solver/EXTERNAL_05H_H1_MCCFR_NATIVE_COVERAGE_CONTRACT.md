# EXTERNAL 05H-H1 — MCCFR native coverage calibration contract

Authority: `BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

This contract is frozen **before reading the 05H-H0 exhaustive geometry result** and before any 05H strategic payoff is evaluated.

## Preconditions

H1 may execute only if H0 passes the frozen 144-world geometry gate. The support, public prefix and information-state key remain immutable.

## Learner

Only `OverlapExternalSamplingMCCFR` is calibrated in H1. Search/UCT is deliberately excluded because 05G-Q0C established a structural native-support saturation: increasing UCT iterations refined action visits but did not expand counterfactual policy support. H1 is an engineering coverage calibration, not a strategic A/B.

## Frozen seeds

- `20260829`
- `20260830`

Seeds are evaluated separately.

## Frozen budget ladder

Run cumulative MCCFR snapshots at:

1. **1,024 iterations**
2. **2,048 iterations**
3. **4,096 iterations**

The same solver instance may be advanced cumulatively to avoid redundant work, but the snapshot at each exact budget must be recorded.

## Coverage metrics

Against the exhaustive H0 support, report for every seed and budget:

- all reachable native infosets;
- non-root native infosets and fraction;
- ambiguous non-root native infosets and fraction;
- native coverage by each R3/R4 actor layer;
- terminal evaluations;
- runtime;
- profile SHA-256;
- action-set/probability/firewall validation.

No completion, EV, cross-play, best response, NashConv or exploitability is allowed in H1.

## Precommitted budget selection rule for H2/H3

Select the **smallest tested budget** for which **both seeds** satisfy simultaneously:

- non-root native coverage >= **80%**; and
- ambiguous non-root native coverage >= **95%**.

These thresholds are inherited from the 05G engineering rule. They are completion-burden thresholds only; they are not claims of convergence or strategic quality.

If no tested budget meets both thresholds, select **4,096** as the frozen downstream budget and explicitly retain completion for all remaining holes. Do not invent a larger budget after inspecting exploitability. Any later expansion beyond 4,096 requires a new precommitted engineering contract before payoff evaluation.

## Guardrails

- profile keys may contain no hidden world identifier;
- legal action sets must match exhaustive support;
- probability distributions must be finite, non-negative and normalized;
- native means actually materialized by MCCFR; no implicit uniform policy is counted as native;
- seeds remain separate;
- H1 cannot promote any strategy or alter canonical DeepOFC.