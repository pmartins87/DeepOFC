# OpenOFC 05G — Broad hidden-information benchmark

Status: **SHADOW RESEARCH / NOT CERTIFICATION**

Authority: `BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`

## Motivation

05F successfully created real hidden-discard ambiguity and showed that exact posterior structure can differ materially from a uniform determinization prior. It also exposed a limitation: the four-world payoff surface was too narrow. MCCFR landed essentially on the exact saddle point, while reach-weighting 8,658 synthetic Search completion decisions changed no selected action and therefore changed exploitability by exactly zero.

05G broadens the information and payoff geometry before any production-architecture decision.

## Permanent firewall

05G does not alter the canonical DeepOFC solver, runtime, Bellman registry, M5C/M5H authority, or `REAL` route count. It is an isolated A/B benchmark only.

## Frozen construction rule

The benchmark must be generated deterministically from a committed seed schedule and the canonical physical deck. Candidate support selection may inspect only:

- physical card uniqueness;
- private-type diversity;
- public-history collisions;
- canonical information-state-key collisions;
- action-set legality;
- counts of compatible worlds per information state.

Support selection must **not** inspect terminal utilities, best-response values, exploitability, Search performance, MCCFR performance, or which algorithm would win. This prevents fixture cherry-picking by strategic outcome.

## Minimum support geometry

The accepted frozen support must contain:

- at least 3 distinct P0 R3 private packet types;
- at least 3 distinct P1 R3 private packet types;
- at least 2 distinct P0 R4 packet types;
- at least 2 distinct P1 R4 packet types;
- at least 18 complete physical worlds;
- no duplicate physical card inside any world;
- at least 1,000 non-root ambiguous information states in the full exact reachable support;
- at least 100 non-root information states with 3 or more compatible concrete worlds;
- ambiguity in both directions: hidden P0 information affecting a P1 infoset and hidden P1 information affecting a later P0 infoset;
- no opponent hidden discard, future packet, or hidden world identifier in the acting-player information-state key.

If the first deterministic candidate schedule cannot satisfy these information-only gates within the frozen search budget, Q0 fails closed and a new precommitted schedule must be added; the gates must not be relaxed after seeing strategic results.

## Q0 — mechanics and ambiguity

Q0 must prove:

1. reproducible support SHA under the frozen seed schedule;
2. physical uniqueness for every world;
3. acting-player private information changes its own infoset when appropriate;
4. opponent private discard identity does not leak;
5. exact same-public-history/different-hidden-world collision witnesses in both directions;
6. full exact reachable-support counts by layer and compatible-world multiplicity;
7. deterministic UCT/ISMCTS smoke keyed only by canonical information state;
8. deterministic External-Sampling MCCFR smoke on exactly the same support.

No terminal-payoff-based fixture selection is permitted in Q0.

## Q1 — frozen fixed-profile A/B

Using precommitted budgets and seeds:

- materialize Search/ISMCTS profile;
- materialize External-Sampling MCCFR profile;
- record native infoset coverage before any completion;
- complete missing off-trajectory decisions with the same declared baseline completion mechanism for both algorithms where applicable;
- compute exact self-play and cross-play EV on the finite support;
- freeze every completed profile by SHA.

Cross-play cannot rank equilibrium quality.

## Q2 — exact bilateral best response

Run exact finite-support BR0 and BR1 against each frozen completed profile. Report:

- BR0;
- BR1;
- NashConv;
- exploitability;
- exact replay agreement;
- terminal work and infoset coverage.

Q2 is the ranking authority inside the reduced 05G fixture.

## Q3 — posterior audit

For each frozen completed profile, enumerate exact acting-player counterfactual posteriors at ambiguous information states and compare them with the completion/determinization prior. Report by layer:

- number of ambiguous infosets with defined counterfactual posterior;
- mean/median/p95/max TV against uniform;
- compatible-world multiplicity;
- effective support;
- number of posterior-degenerate infosets.

## Q4 — isolated posterior-aware Search A/B

Q4 is activated only if Q3 finds material non-uniform posterior structure for Search. Preserve all native Search decisions. Change only synthetic/off-trajectory completion decisions using the frozen Q3 posterior source, then rerun exact bilateral BR.

Report both action-change count and exploitability delta. If posterior-aware completion changes its own induced posterior materially, stop at one pass and record that fixed-point work would be required; do not claim self-consistency.

## Decision rule

A component may be considered for migration only if it shows reproducible improvement under exact-BR authority on 05G and does not violate canonical OFC/Joker/HU semantics. One reduced benchmark is still insufficient for production replacement; a positive result advances the component to a broader validation ladder.

`real_routes_certified = 0`.
