# EXTERNAL 05H-H4 — counterfactual posterior audit contract

Authority: `BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

This contract is frozen before 05H-H3 exploitability is known.

## Activation condition

H4 executes **only** if H3 yields `05H_NEAR_NASH_REPLICATED` under the precommitted <=1e-6 exact exploitability threshold on both seeds.

If H3 does not meet that condition, H4 remains dormant and no posterior result is inferred.

## Target profile

For each frozen seed, audit exactly the complete 05H M profile from H2/H3:

- `MCCFR_NATIVE` at the H1-selected budget;
- `COMPLETION_UNIFORM_LOCAL_BACKWARD_V1` only in remaining native holes.

## Counterfactual posterior

At every ambiguous information set, compute the exact counterfactual mass over the exhaustive `ReachableSupport.concrete_states` using:

- uniform chance prior over the 144 frozen worlds;
- opponent behavior reach from the complete M profile;
- responder's own actions enumerated and excluded from the posterior weight.

This is the posterior relevant to unilateral best-response evaluation.

The baseline distribution is exactly the assumption made by the completion builder: uniform over the concrete states grouped into that information set.

## Required diagnostics

For each seed and layer, separately report:

- ambiguous infoset count;
- counterfactually reachable ambiguous infoset count;
- completion-source ambiguous infoset count;
- completion-source ambiguous infosets with positive counterfactual mass;
- total variation distance between uniform and exact counterfactual posterior;
- mean / median / p95 / maximum TV;
- counterfactual-mass-weighted mean TV (descriptive only);
- counts above frozen diagnostic thresholds **0.01, 0.05, 0.10, 0.25**;
- zero-counterfactual-mass infoset count;
- posterior mass/integrity firewalls.

No policy may be changed in H4. No best-response choice, EV, NashConv or exploitability may be recomputed in this gate.

## Interpretation rule

- If every counterfactually reachable ambiguous completion hole has TV <= **1e-12** on both seeds: `UNIFORM_COMPLETION_MATCHES_COUNTERFACTUAL_POSTERIOR_05H`.
- Otherwise: `NONUNIFORM_COUNTERFACTUAL_POSTERIOR_DETECTED_05H`.

If non-uniformity is detected, the already precommitted counterfactual-weighted local-backward completion architecture may be adapted to 05H in a new explicit A/B gate. Native MCCFR policy must remain untouched in that A/B.

If exact uniformity persists, the posterior-distortion hypothesis is rejected again for the broader fixture and the next research step should broaden game geometry or move toward a less reduced game, not invent a completion correction.