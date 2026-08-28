# OpenOFC 05D-Q2 — Conditional Reach-Weight Audit Contract

Status: **SHADOW RESEARCH / NOT CERTIFICATION**

Authority: `FINITE_SUPPORT_CONDITIONAL_REACH_AUDIT_ONLY`

## Motivation

05D-Q1 removes the Q0 uniform *policy* fallback by creating an explicit policy at every reachable information set. Its local missing-state resolver still samples compatible concrete states uniformly. That is a search prior, not necessarily the conditional distribution induced by strategic play.

Q2 measures that remaining approximation instead of silently treating it as correct.

## Frozen inputs

Q2 uses the same frozen R3->R4 finite-support game, canonical transitions, terminal utility, and information-state keys as 05C/05D. It consumes a fully explicit fixed behavior profile. No hidden card is added to a policy key.

## Exact reach enumeration

For each frozen physical world, enumerate **every legal action branch**, including branches assigned zero probability by the fixed profile, while carrying:

- chance reach: uniform probability of the physical world;
- P0 behavioral reach;
- P1 behavioral reach.

Traversing zero-probability own-action branches is mandatory. A player whose fixed strategy assigns probability zero to an earlier action can still have positive **counterfactual** reach at a later information set, because that player's own reach is deliberately excluded from the counterfactual weight.

At each information state, aggregate weights for each compatible concrete state in two ways:

1. **full reach** = chance × P0 reach × P1 reach;
2. **counterfactual reach for the acting player** = chance × opponent reach, excluding the acting player's own reach.

Each positive-mass set is normalized within the information state. If full reach has zero total mass, the full conditional belief is explicitly **undefined**; it must not be coerced into uniform or any other distribution. Likewise, if chance/opponent reach is zero, the acting-player counterfactual belief is explicitly undefined.

Defined conditional distributions are compared against the Q1 resolver's uniform-compatible-state prior and, where both exist, against each other.

## Required metrics per information state

- actor and round;
- number of compatible concrete states;
- whether full reach is defined;
- whether acting-player counterfactual reach is defined;
- normalized full-reach weights when defined;
- normalized counterfactual-reach weights when defined;
- total variation: uniform vs full reach when defined;
- total variation: uniform vs counterfactual reach when defined;
- total variation: full vs counterfactual reach when both are defined;
- maximum normalized weight;
- effective support size (`1 / sum(p^2)`).

The experiment summary must include defined-counts, maxima, and distributional summaries by decision layer and by base algorithm.

## Interpretation

A large uniform-vs-counterfactual TV means Q1's local completion may materially misweight hidden compatible states even though it no longer has an unseen-policy fallback. A small TV supports, but does not prove, the adequacy of the uniform finite-support prior for this reduced fixture.

Full-reach and counterfactual-reach differences are diagnostic. They must not be silently forced equal. A difference can arise from the acting player's own earlier strategy and therefore is not automatically a perfect-recall violation. The audit records the difference so later resolver work can use the weighting appropriate to its objective.

Zero full reach does not invalidate a counterfactual belief. Such states are especially important for best-response analysis because they can become relevant after an acting-player deviation.

## Promotion firewall

Q2 cannot produce a real Bellman route, exploitability certificate, Nash-equilibrium claim, or M5C/M5H/M5L evidence. It is a diagnostic of the reduced-game resolver prior only.

`real_routes_certified` remains `0`.
