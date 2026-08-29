# OpenOFC external research — 05G-Q3 results (2026-08-29)

Authority: `BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

## Run

- Workflow: `OpenOFC external 05G Q3 counterfactual posterior audit`
- Run: `33260994001`
- Job: `99122798664`
- Immutable run head: `f01e075641bdd4dc92e21aa0576fedc54b600e22`
- Conclusion: `success`
- Artifact: `openofc-external-05g-q3`, id `9717339439`
- Artifact ZIP SHA-256: `ab92808a09f80d02546115084ddce6e2db22e30df9c0cb8f3cededa6153d116c`
- Manifest SHA-256: `d71f5ee1d2e52ca77fd5d06533719f36cf6890e8c96da0eb1039bce7d8577bdd`

## Frozen geometry

- chance worlds: **36**
- reachable information states: **69,828**
- non-root information states: **69,825**
- ambiguous non-root information states: **15,393**
- completion policy SHA-256: `16722f9ac620786332980cc488478ad0a38df3eb30626854463c93763bb2b0d5`
- support SHA-256: `a08ed2d6604fd3c632cfcc41cc6f065f871861042450f0649962ea92ab415ed6`

## Result

Q3 audited the exact counterfactual posterior relevant to unilateral best response under the complete M profile. Counterfactual reach was defined as uniform chance prior × opponent behavior reach, while the responder's own actions were enumerated and therefore excluded from the posterior weights.

The baseline being audited was exactly the Q1B completion assumption: uniform over `ReachableSupport.concrete_states` at each information set.

### Seed 20260829

- M native MCCFR information states: **55,408**
- M completion information states: **14,420**
- counterfactually reachable ambiguous completion states: **311**
- mean TV(uniform, counterfactual posterior): **0.0**
- median TV: **0.0**
- p95 TV: **0.0**
- max TV: **0.0**
- count TV > 0.01 / 0.05 / 0.10 / 0.25: **0 / 0 / 0 / 0**
- M profile SHA-256: `f25255cdf52cd4fb789becfe411ad5a127537f675e0ca6fab3cb7b1dfa85978a`

### Seed 20260830

- M native MCCFR information states: **55,149**
- M completion information states: **14,679**
- counterfactually reachable ambiguous completion states: **350**
- mean TV(uniform, counterfactual posterior): **0.0**
- median TV: **0.0**
- p95 TV: **0.0**
- max TV: **0.0**
- count TV > 0.01 / 0.05 / 0.10 / 0.25: **0 / 0 / 0 / 0**
- M profile SHA-256: `5ac4026b5878303b81379e091295394d0e38e96ebc4e22a5fb04b5983eadf340`

All posterior diagnostics were clean on both seeds: no state outside the exhaustive row, no invalid counterfactual mass, no posterior mass failure, no invalid TV, and no hidden-world leakage.

## Scientific interpretation

**Verdict: `PASS_COUNTERFACTUAL_POSTERIOR_AUDIT`.**

For every ambiguous completion hole that matters counterfactually on this frozen 36-world fixture, the local-uniform completion assumption is not merely an approximation: it matches the exact counterfactual posterior used by the BR calculation. Therefore the hypothesized posterior-distortion failure mode is absent here.

This result strengthens the interpretation of the extremely small Q2 exploitability of M, but it remains limited to this finite reduced fixture. It does not certify production play, the full OFC game, or any REAL route.

## Q4A disposition

The precommitted Q4A counterfactual-weighted completion A/B is **not activated**, because its activation condition (non-uniform counterfactual posterior in completion holes) did not occur. The implementation and tests are retained as shadow research infrastructure for a future fixture where the condition may actually hold.

The Q4A core itself passed mechanically in workflow run `33261252986`: runner compiled and six completion invariant tests passed. No Q4A strategic A/B was run and no strategic result is inferred from those tests.

## Next gate

Per the precommitted Q3 routing rule, the next scientific move is to **broaden the external hidden-information fixture while preserving M provenance and exact bilateral BR as the strategic authority**. The next fixture must be selected from card/information geometry before observing strategic payoff.