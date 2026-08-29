# EXTERNAL 05H-H3 — exact bilateral best-response contract

Authority: `BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

This contract and its interpretation thresholds are frozen before any 05H payoff, best response, NashConv or exploitability is observed.

## Preconditions

- H0 geometry PASS;
- H1 coverage calibration PASS;
- H2 complete M provenance PASS;
- M for each seed is exactly the H2 profile: `MCCFR_NATIVE` at the precommitted H1-selected budget plus `COMPLETION_UNIFORM_LOCAL_BACKWARD_V1` only in native holes.

## Strategic authority

For each frozen seed separately, compute exact pure best response for player 0 and player 1 against the complete M profile over all 144 chance worlds. Derive zero-sum:

- BR0 value;
- BR1 value;
- NashConv = BR0 + BR1;
- exploitability = NashConv / 2.

Exact bilateral BR is the ranking/quality authority. Self-play EV or cross-play, if later reported, cannot override it.

## Exactness firewalls

- responder choice must cover every exhaustive infoset belonging to that responder;
- every selected BR action must be legal;
- BR0 and BR1 values must be replayed through an independent exact asymmetric profile evaluator;
- absolute replay error must be <= **1e-9**;
- NashConv must be finite and non-negative up to numerical tolerance;
- all 144 chance roots are included;
- no implicit uniform fallback is allowed in the opponent M profile;
- seeds are never averaged to manufacture a winner or PASS.

## Precommitted strategic interpretation bands

Interpret each seed's exact exploitability independently:

- `NEAR_NASH_STRICT`: exploitability <= **1e-6**;
- `LOW_BUT_NOT_STRICT`: `1e-6 < exploitability <= 1e-3`;
- `MATERIAL_EXPLOITABILITY`: exploitability > **1e-3**.

Cross-seed interpretation:

- **05H_NEAR_NASH_REPLICATED** only if **both seeds** are `NEAR_NASH_STRICT`;
- **05H_LOW_NOT_STRICT_REPLICATED** only if both seeds are at most `LOW_BUT_NOT_STRICT` but the strict condition fails;
- otherwise **05H_NOT_REPLICATED_AT_LOW_EXPLOITABILITY**.

The 1e-6 strict band is intentionally much looser than the ~1e-12 exploitability observed in 05G, but still requires the broadened profile to remain effectively unexploitable on the exact reduced fixture.

## Routing frozen before results

- If `05H_NEAR_NASH_REPLICATED`: proceed to H4 counterfactual-posterior audit on ambiguous completion holes, then decide whether further fixture broadening is warranted.
- If `05H_LOW_NOT_STRICT_REPLICATED`: do not promote; create a new precommitted MCCFR budget-expansion contract before any retraining or reevaluation.
- If `05H_NOT_REPLICATED_AT_LOW_EXPLOITABILITY`: stop strategic expansion and diagnose the exact BR / completion / training failure mode before changing budgets or support.

No H3 outcome authorizes canonical DeepOFC replacement or production play.