# OpenOFC external research — 05G-Q0B Search + MCCFR smoke contract

Status: **precommitted technical smoke**
Authority: `BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`
Strategic authority promoted by this experiment: **none**
REAL routes certified: **0/50**

## Purpose

05G-Q0A passed the geometry gate before any Search/MCCFR result was observed. Q0B now asks a narrower engineering question: can both candidate imperfect-information learners execute on exactly that frozen 36-world broad hidden-information support without leaking hidden state, inventing action sets, or silently turning missing policy into a strategic comparison?

This is **not** a strength contest between UCT/Search and MCCFR. No EV winner, exploitability winner, or production migration may be inferred from Q0B.

## Frozen game

Q0B uses, without payoff-driven fixture selection:

- `external_05g_broad_support.py`;
- the same 36 physical worlds accepted by Q0A;
- the same public pre-R3 state;
- the same legal action generator and exact terminal evaluator;
- the same acting-player information-state key;
- one physical world per sampled episode;
- owner-private discards and no opponent-discard leakage.

The exhaustive reachable support is materialized independently by `build_reachable_support` and is used only as a technical oracle for key/action-set validation and coverage accounting.

## Algorithms under smoke

### Search

`run_overlap_infoset_uct` on the frozen 05G support.

Search policy is the empirical action-visit distribution of materialized information-set nodes. Unvisited information sets remain **missing** for coverage purposes; they are never converted to uniform policy and then scored as if Search had produced that policy.

### MCCFR

`OverlapExternalSamplingMCCFR` on the same frozen support.

Q0B records the materialized current regret-matching profile. Information sets never materialized by MCCFR remain **missing** for coverage purposes.

## Precommitted schedules

Paired seeds:

- `20260829`
- `20260830`

Budget pairs:

1. Search `2,000` iterations; MCCFR `64` iterations.
2. Search `5,000` iterations; MCCFR `128` iterations.

Thus Q0B executes four paired trials. Changing these budgets after seeing results requires a new experiment ID; failing this gate must not be repaired by retroactively moving Q0B thresholds.

## Measurements

For each paired trial Q0B records:

- Search information sets materialized;
- MCCFR information sets materialized;
- exhaustive reachable information sets;
- Search/MCCFR total and non-root coverage;
- Search/MCCFR ambiguous non-root coverage where applicable;
- exact root-information-set presence;
- normalized root distributions;
- total-variation distance between Search and MCCFR at roots observed by both;
- top root action/probability as a diagnostic only;
- terminal evaluations reported by MCCFR;
- runtime per learner;
- illegal key count;
- action-set mismatch count;
- hidden-world-token leakage count.

## Technical PASS gate

`PASS_SMOKE` requires all of the following:

1. the 36-world physical support validates unchanged;
2. exhaustive reachable support is non-empty and contains exactly three P0-R3 root information sets;
3. every Search/MCCFR materialized key belongs to the exhaustive legal support;
4. every materialized distribution uses exactly the legal action set for that information set;
5. every materialized distribution is finite, non-negative, and normalized;
6. no information-state key contains a 05G physical `world_id` token;
7. every paired run materializes all three root information sets for both learners;
8. every paired run materializes at least one non-root information set for both learners;
9. CI completes inside the workflow timeout.

Coverage ratios and Search-vs-MCCFR root TV are **measurements, not pass thresholds** in Q0B. Their purpose is to design Q0C without cherry-picking.

## Forbidden interpretations

Q0B may not claim:

- Search beats MCCFR;
- MCCFR beats Search;
- either profile is strategically complete;
- uniform fallback represents either learner;
- low root TV implies low exploitability;
- high root TV identifies the better policy;
- 05G validates production/runtime behavior;
- any REAL route is certified.

## Next gate

If Q0B passes technically, proceed to **05G-Q0C paired policy-completeness/router experiment**. Q0C must explicitly distinguish learned coverage from any completion/fallback mechanism before exact policy evaluation or best-response analysis is allowed.
