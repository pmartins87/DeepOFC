# OpenOFC 05F-Q3 — Reach-weighted local completion A/B

Status: **SHADOW RESEARCH / NOT CERTIFICATION**

Authority: `HIDDEN_DISCARD_REACH_WEIGHTED_COMPLETION_SHADOW_ONLY`

## Trigger

05F-Q2 measured the hidden-state prior induced by the exact completed Q1 profiles. For Search/UCT, uniform compatible-state sampling was materially different from the acting player's counterfactual posterior:

- 1,766 ambiguous infosets with defined counterfactual posterior;
- mean uniform-vs-counterfactual TV `0.08155869849319133`;
- p95 `0.5`;
- max `0.5`.

For the MCCFR Q1 profile the same metric was exactly zero on all 550 ambiguous infosets with defined posterior. Therefore Q3 changes **only the Search completion treatment** and keeps MCCFR as the frozen control.

## Scientific interpretation

Q1's uniform-compatible-state completion is not retroactively declared invalid. Uniform determinization is itself a legitimate algorithmic choice, but Q2 proves that it ignores strategic signalling on this fixture. Q3 is an isolated A/B variant that asks whether using exact counterfactual reach as the hidden-state belief improves the resulting fixed Search policy.

## Frozen baseline

Reproduce Q1 byte-for-byte from the same:

- four physical worlds;
- UCT iterations/seed/exploration;
- MCCFR iterations/seed;
- Q1 local-completion budget and seeds;
- canonical information-state keys and terminal utility.

The reproduced Q1 completed Search profile is the immutable **reference profile** for Q3.

## Q3 one-pass resolver

For each information set missing from the original Search snapshot:

1. enumerate all concrete states in the exact finite support;
2. compute acting-player counterfactual reach under the immutable Q1 reference profile:
   - chance reach × opponent behavioral reach;
   - exclude the acting player's own reach;
   - traverse zero-own-probability branches because later counterfactual reach can remain positive;
3. choose the local root action **before** drawing a hidden concrete state;
4. draw the hidden concrete state using the normalized counterfactual-reach weights;
5. roll out all downstream decisions using the immutable Q1 reference profile;
6. materialize the local action-visit distribution.

Original UCT-covered information states remain unchanged. Newly generated Q3 decisions never bootstrap one another during this pass.

If an information set has zero total counterfactual reach under the reference profile, Q3 uses the declared uniform-compatible-state fallback and records it separately. Such a state is not silently described as reach-weighted.

## Evaluation

Compare Q1 uniform-completion Search against Q3 reach-weighted Search using:

- profile SHA and number of changed completed infosets;
- exact self-play EV;
- exact cross-play against frozen Q1 MCCFR;
- exact bilateral best responses;
- NashConv/exploitability;
- a fresh conditional-reach audit of the Q3 fixed profile.

The Q3 result is accepted as an algorithmic improvement only if exact exploitability decreases without any semantic or completeness regression. A worse or equal result preserves Q1 Search as the better reduced-game variant.

## Self-consistency firewall

Q3 is deliberately **one pass**. The priors come from the immutable Q1 reference profile. If the resulting Q3 profile materially changes its own induced counterfactual posteriors, a later fixed-point/iterative experiment is required. Q3 must not be labeled a self-consistent Bayesian equilibrium policy merely because it used reach weights once.

## Promotion firewall

Q3 cannot certify a production Bellman route and cannot replace the current DeepOFC strategic architecture. It is a reduced-game A/B experiment inspired by external solver methodology.

`real_routes_certified = 0`.
