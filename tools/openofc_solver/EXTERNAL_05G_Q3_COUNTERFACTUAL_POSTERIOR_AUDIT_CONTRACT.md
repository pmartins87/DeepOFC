# OpenOFC External 05G-Q3 — Counterfactual posterior audit contract

Status: **FROZEN BEFORE Q3 RESULTS**

Authority: `BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`

## Purpose

05G-Q2 found profile `M` (MCCFR-native where materialized, otherwise the frozen
`COMPLETION_UNIFORM_LOCAL_BACKWARD_V1`) to have near-zero exact bilateral
exploitability on both frozen seeds in the 36-world reduced game.

Q3 does **not** re-rank S/M/H and does **not** modify any strategy. Its purpose is
to audit the hidden-state belief implicit in the completion rows of `M` against
the exact counterfactual reach weighting used by unilateral best response.

The key distinction is important: the Q1B completion builder chose each local
action by averaging **uniformly over `ReachableSupport.concrete_states`**. Q3
therefore compares that exact baseline to the posterior over those same concrete
states induced by chance plus the *opponent* part of profile M. It does not
silently substitute a uniform-over-worlds baseline.

## Frozen support and profiles

- Support: the existing 05G deterministic 36-world support.
- Seeds remain separate: `20260829`, `20260830`.
- Search snapshot: unchanged, 50,000 UCT iterations, exploration 1.0.
- MCCFR snapshot: unchanged, 1,024 iterations.
- `M` profile provenance remains:
  1. `MCCFR_NATIVE` when that infoset was materialized by MCCFR;
  2. `COMPLETION_UNIFORM_LOCAL_BACKWARD_V1` only at MCCFR holes.
- Q3 must reproduce the same M-profile/source-map hashes generated from the
  frozen Q1 pipeline; Q3 may not overwrite native rows.

## Counterfactual posterior definition

For an infoset `I` belonging to player `i`, Q3 walks every physical world with
uniform chance prior. At player `i` decisions it enumerates **all legal actions**
without multiplying by player `i`'s own strategy. At opponent decisions it
branches according to the frozen M behavior probabilities.

For each concrete state `s in I`, the accumulated mass is therefore

`mu_i(s, I) = P(chance world) * pi_{-i}(opponent actions leading to s)`.

If the total mass of `I` is positive, the exact counterfactual posterior is

`P_cf(s | I) = mu_i(s,I) / sum_{s' in I} mu_i(s',I)`.

This is the same reach concept relevant to a unilateral best response and keeps
own deviations available even when M itself would assign them zero probability.

## Uniform baseline under audit

The Q1B completion baseline for a support row with `k` concrete states is

`P_uniform(s | I) = 1/k`.

Q3 measures total-variation distance

`TV(I) = 0.5 * sum_s |P_cf(s|I) - 1/k|`.

No alternative baseline may be introduced after observing results.

## Required accounting

For each seed, Q3 must report at minimum:

- all reachable support infosets by layer and source;
- counterfactually reachable vs zero-opponent-reach infosets;
- the same counts restricted to completion-sourced rows;
- the same counts restricted to ambiguous rows (`len(concrete_states) > 1`);
- TV distribution for counterfactually reachable ambiguous rows;
- TV distribution specifically for completion-sourced, counterfactually
  reachable ambiguous rows;
- diagnostic counts above frozen TV thresholds `0.01`, `0.05`, `0.10`, `0.25`;
- layer/source summaries;
- top distorted completion rows using hashes of information-state keys plus
  round, actor, state count, counterfactual mass and TV;
- exact source/profile hashes and support hash.

Seeds must never be averaged to create a strategic winner. Aggregate summaries
may be descriptive only.

## Mechanical firewalls

Q3 passes mechanically only if all of the following hold:

1. the frozen support remains 36 worlds and the expected exhaustive infoset
   geometry is unchanged;
2. each M profile is complete, legal, finite, normalized, and contains no hidden
   world token in an information-state key;
3. each M source map covers the exhaustive support exactly;
4. every concrete state reached by the counterfactual traversal belongs to the
   matching exhaustive support row;
5. every positive-mass posterior is finite, non-negative, sums to one within
   `1e-12`, and has TV in `[0,1]` within tolerance;
6. both seeds are audited independently;
7. Q3 performs no policy update, EV ranking, best-response choice update,
   NashConv recomputation, production migration, or REAL-route certification.

A mechanically valid Q3 is `PASS_COUNTERFACTUAL_POSTERIOR_AUDIT` regardless of
whether the posterior is uniform or non-uniform. Posterior distortion is a
scientific result, not a test failure.

## Frozen interpretation rule

Let `EPS = 1e-12`.

- If no completion-sourced ambiguous infoset is counterfactually reachable,
  report `COMPLETION_COUNTERFACTUALLY_IRRELEVANT_UNDER_M`.
- Else if the maximum TV among completion-sourced, counterfactually reachable,
  ambiguous infosets is `<= EPS`, report
  `UNIFORM_COMPLETION_MATCHES_COUNTERFACTUAL_POSTERIOR`.
- Else report `NONUNIFORM_COUNTERFACTUAL_POSTERIOR_PRESENT` and continue to a
  separately frozen Q4 that replaces **only completion holes** with a
  counterfactual-posterior-aware completion for controlled exact-BR comparison.

This rule cannot invalidate the mathematical meaning of the already-computed Q2
exact NashConv. If Q2's exact-BR implementation is correct, near-zero NashConv is
a property of the complete reduced-game profile regardless of how its missing
rows were originally generated. Q3 instead diagnoses whether the completion
heuristic itself is belief-principled and whether it should be reused when the
fixture is broadened.

## Authority firewall

Q3 remains reduced-game external research only. It authorizes **zero** REAL
routes and cannot modify or replace the canonical DeepOFC strategic authority.
