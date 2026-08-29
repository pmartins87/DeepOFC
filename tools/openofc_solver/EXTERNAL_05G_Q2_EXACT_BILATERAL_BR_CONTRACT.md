# OpenOFC external research — 05G-Q2 exact bilateral best-response contract

Status: **precommitted equilibrium-quality ranking authority for the reduced 05G fixture**  
Authority: `BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
REAL routes certified: **0/50**

## Purpose

Q2 is the first 05G stage allowed to rank the frozen completed S/M/H profiles by equilibrium quality. It uses exact bilateral best response on the finite 36-world game.

This authority is limited to the reduced 05G fixture. Even a positive result cannot directly replace the production solver or certify a REAL route; it only advances the winning component/profile family to the broader validation ladder.

## Frozen inputs

For each seed `20260829` and `20260830`, reproduce exactly the Q1A/Q1B completed profiles:

- Search native: 50,000 UCT iterations, exploration `1.0`;
- MCCFR native: 1,024 iterations;
- common completion: `COMPLETION_UNIFORM_LOCAL_BACKWARD_V1`;
- `S-complete`, `M-complete`, `H-complete` with the frozen source-priority semantics.

No budget, seed, support card, completion rule, profile source priority, terminal utility or information-state key may change after Q1C results are observed.

## Exact bilateral best response

For every seed and each profile `S`, `M`, `H`:

1. compute exact `BR0` against the frozen opponent profile;
2. compute exact `BR1` against the same frozen opponent profile;
3. report `NashConv = BR0_value + BR1_value` in the zero-sum convention already implemented by the 05F exact comparator;
4. report `exploitability = NashConv / 2`;
5. record BR choices at every responder R3/R4 information set, terminal work and choice-map SHA256;
6. exact-replay each BR policy against the frozen opponent profile and require replay agreement with the reported BR value.

No sampling, local rollout approximation, missing-key fallback, policy update or posterior approximation is permitted in Q2.

## Ranking rule

For each seed independently:

- lower exploitability is better;
- values within absolute tolerance `1e-9` are treated as tied;
- self-play EV and cross-play EV from Q1C are not used in the ranking.

A **cross-seed reduced-fixture winner** exists only if the same named profile (`S`, `M`, or `H`) has strictly lower exploitability than both alternatives by more than `1e-9` in **both** seeds.

If winners differ across seeds, or a lowest value is tied within tolerance in either seed, the verdict is `NO_UNIQUE_CROSS_SEED_WINNER` and no winner is declared by averaging seeds after the fact.

The mean/median exploitability across the two seeds may be reported descriptively but cannot override the cross-seed rule.

## Integrity gates

`PASS_EXACT_BILATERAL_BR` requires:

- frozen 36-world support unchanged;
- every fixed profile is complete, legal and source-consistent;
- exact BR covers every responder information set at R3 and R4;
- BR0 and BR1 are finite;
- NashConv is non-negative up to numerical tolerance;
- exact BR replay agrees with BR values within `1e-9`;
- repeated profile/BR choice hashes are deterministic for the frozen run;
- six profile/seed bilateral evaluations complete;
- seeds remain separate.

A gate pass means the ranking machinery is valid; it does **not** require a unique winner.

## Interpretation and next steps

- If one profile is the unique cross-seed reduced-fixture winner, preserve that result and advance the relevant component hypothesis to Q3 plus broader out-of-fixture validation.
- If there is no unique cross-seed winner, preserve the seed-specific ranking and continue diagnostic posterior work without manufacturing an averaged winner.
- Q3 remains an exact counterfactual-posterior audit of the uniform completion assumption.
- Q4 remains an isolated posterior-aware Search completion A/B only if Q3 finds material non-uniform posterior structure for Search.

No Q2 result by itself authorizes production migration or increases `real_routes_certified`.
