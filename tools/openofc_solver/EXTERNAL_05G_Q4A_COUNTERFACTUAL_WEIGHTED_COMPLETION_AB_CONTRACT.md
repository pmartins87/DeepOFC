# OpenOFC External 05G-Q4A — Counterfactual-weighted completion A/B contract

Status: **CONDITIONAL PROTOCOL FROZEN BEFORE Q3 RESULTS**

Authority: `BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`

## Activation condition

Q4A runs only if 05G-Q3 mechanically passes and its frozen interpretation is
`NONUNIFORM_COUNTERFACTUAL_POSTERIOR_PRESENT` on at least one frozen seed, or is
seed-dependent because one seed contains non-uniform completion-hole posterior.

If Q3 instead reports that completion holes are counterfactually irrelevant or
that the uniform completion prior matches the counterfactual posterior, Q4A is
not run and the external program proceeds to broader-fixture validation.

This activation rule is frozen before Q3 values are observed.

## Scientific question

Q1B's `COMPLETION_UNIFORM_LOCAL_BACKWARD_V1` chooses a pure action at every
completion row by averaging action value uniformly over the row's exhaustive
`ReachableSupport.concrete_states`.

Q4A asks one deliberately narrow question:

> If the *only* change to that completion algorithm is replacing the uniform
> state weights with exact counterfactual state weights induced by the frozen
> original profile M, does the resulting completed M profile have lower exact
> bilateral exploitability on the same finite 36-world game?

This is an A/B of a completion heuristic. It is not a new global solver and is
not a production-migration test.

## Frozen inputs

Per seed (`20260829`, `20260830`) Q4A reconstructs exactly the Q2/Q3 inputs:

- Search: 50,000 iterations, exploration 1.0 (provenance reproduction only);
- MCCFR: 1,024 iterations;
- original `M`: `MCCFR_NATIVE` wherever materialized, otherwise
  `COMPLETION_UNIFORM_LOCAL_BACKWARD_V1`;
- deterministic 36-world 05G support;
- exact terminal utility and exact bilateral BR implementation already used by
  Q2.

The original M profile and source-map hashes must be reproduced before any Q4A
candidate is built.

## Frozen counterfactual weights

For each player-i completion infoset I, Q4A computes the same counterfactual
state masses frozen by Q3 using the **original frozen M** as opponent behavior:

`mu_i(s,I) = P(chance world) * pi^M_{-i}(opponent actions leading to s)`.

Own actions remain enumerated rather than multiplied by own strategy.

The weight map is a one-shot frozen diagnostic derived from original M. It is
**not recomputed after candidate completion actions change**. This prevents an
implicit iterative solver from being introduced into Q4A and makes the A/B
causal: the changed variable is the completion state's weighting rule.

## Candidate completion algorithm

Candidate source label:
`COMPLETION_COUNTERFACTUAL_WEIGHTED_LOCAL_BACKWARD_V1`.

Q4A must preserve the Q1B algorithm except for the state weights:

1. same backward layer order: P1-R4, P0-R4, P1-R3, P0-R3;
2. same exhaustive support rows and legal actions;
3. same exact terminal utility;
4. same downstream local-completion rollout semantics;
5. same maximize-P0 / minimize-P1 decision rule;
6. same lexicographic tie break and `1e-12` tie tolerance;
7. for a row with positive counterfactual mass, replace uniform `1/k` state
   weights with normalized Q3 counterfactual weights over the exact concrete
   states in that row;
8. for a completion row with **zero counterfactual mass**, retain the original
   Q1B uniform-completion action exactly. Q4A may not invent a posterior for an
   unreachable row.

This intentionally isolates the belief-weighting change. Q4A may not also change
continuation semantics, MCCFR training, native-policy ownership, utility, support,
or action abstraction.

## Candidate assembled profile

For each seed, construct `M_cf` as:

- if the infoset is `MCCFR_NATIVE`, copy original M distribution byte-for-byte;
- otherwise use the pure
  `COMPLETION_COUNTERFACTUAL_WEIGHTED_LOCAL_BACKWARD_V1` action.

No MCCFR-native row may be overwritten. Source provenance must remain explicit.

## Required causal accounting

Per seed Q4A must report:

- original M profile/source-map SHA256;
- candidate completion choice SHA256;
- candidate `M_cf` profile/source-map SHA256;
- number of completion rows whose selected action changed;
- changed-action counts by round/actor, ambiguity, positive/zero
  counterfactual mass, and TV bins frozen from Q3;
- confirmation that every MCCFR-native distribution is exactly preserved;
- exact bilateral BR values, NashConv, and exploitability for both original M
  and `M_cf` recomputed in the same run;
- exact BR replay checks for both profiles;
- profile legality/completeness/firewall checks.

Cross-play may be recorded only as descriptive diagnostics and cannot decide the
winner.

## Frozen ranking rule

Use the same numerical tolerance as Q2:

`RANK_TOLERANCE = 1e-9`.

Each seed is judged separately:

- `M_cf` improves if `exploitability(M_cf) + tolerance < exploitability(M)`;
- original M improves if `exploitability(M) + tolerance < exploitability(M_cf)`;
- otherwise the seed is a tie within tolerance.

Cross-seed recommendation:

- `PROMOTE_CF_COMPLETION_TO_BROADER_EXTERNAL_VALIDATION` only if `M_cf` is never
  worse and is strictly better on at least one seed;
- `RETAIN_UNIFORM_COMPLETION_FOR_CURRENT_EXTERNAL_LINE` if original M is strictly
  better on at least one seed and `M_cf` is never strictly better;
- otherwise `NO_CROSS_SEED_COMPLETION_WINNER_CONTINUE_DIAGNOSTICS`.

Means/medians cannot manufacture a winner and cannot override a seed.

Because Q2's original M exploitability is already near numerical zero, a tie is
expected to be possible and is scientifically meaningful: it would show that the
reduced fixture does not distinguish the completion beliefs by exploitability.

## Mechanical PASS vs strategic outcome

Q4A mechanically passes if the frozen support/profile hashes reproduce, both
profiles are complete/legal, native rows are preserved, exact BR replay checks
pass, and all finite-game evaluations are finite/non-negative within existing
Q2 tolerances.

The A/B may favor M, M_cf, or neither without becoming a mechanical failure.

## Prohibited interpretation

Q4A cannot:

- invalidate a correctly computed Q2 exact NashConv merely because Q3 found
  posterior distortion;
- claim that counterfactual weighting is globally optimal;
- iterate the weight map to a fixed point;
- alter native MCCFR rows;
- select a production solver;
- certify a REAL route.

Any iterative posterior/policy fixed-point experiment, continuation-consistent
hole optimization, broader support, or production comparison requires a new
precommitted gate.

## Authority firewall

Q4A is external reduced-game research only. `real_routes_certified = 0` remains
mandatory and the canonical DeepOFC strategy remains untouched.
