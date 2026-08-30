# External OFC 06P1 — Exact Strength/Compute Frontier Contract

Status: FROZEN BEFORE 06P1 RESULTS

## Authority

`REDUCED_GAME_EXACT_STRENGTH_COMPUTE_CALIBRATION_ONLY`

06P1 implements the project policy in `docs/OFC_PRACTICAL_STRENGTH_COMPUTE_POLICY_2026-08-30.md`: strategy methods are compared by measured strength per available compute, while exact rules/information boundaries remain non-negotiable.

This gate is a calibration on the already-certified 05G finite reduced game. It does not authorize production migration.

## Frozen game/evaluation

- Same deterministic 36-world 05G broad hidden-information support.
- Same exhaustive reachable support and same uniform local backward completion from 05G-Q1B.
- Same exact bilateral best-response / NashConv / exploitability evaluator from 05G-Q2.
- Learner-native rows are preserved exactly; completion fills only native holes.
- Exact evaluation time is reported separately and is **not** counted as candidate training cost.

## Candidate families

### SEARCH

Information-set UCT from `run_overlap_infoset_uct`.

- exploration: `1.0`
- budgets: `1,000`, `5,000`, `20,000`, `50,000` trajectories

### MCCFR

External-sampling MCCFR from `OverlapExternalSamplingMCCFR`.

- budgets: `64`, `256`, `1,024` iterations

No budget is increased after seeing payoff results in this gate.

## Frozen seeds

- `20260829`
- `20260830`

Seeds are evaluated separately. Aggregate means may be reported descriptively but cannot manufacture a winner that is absent seed-by-seed.

## Metrics per point

Every `(family, budget, seed)` point reports at least:

- native training wall-clock seconds;
- native information-state count;
- completion information-state count;
- complete profile hash;
- legal/normalization/information-firewall validation;
- exact exploitability;
- exact NashConv;
- exact BR0 and BR1 values;
- exact-evaluation wall-clock seconds;
- exploitability reduction relative to the completion-only profile on the same support.

The common completion build cost is reported once and not charged to either family.

## Strength/compute frontier

For each seed, point A **dominates** point B iff:

- A training time <= B training time;
- A exploitability <= B exploitability;
- and at least one inequality is strict beyond numerical tolerance `1e-9`.

The nondominated points form the empirical Pareto frontier for that seed.

Wall-clock measurements from GitHub-hosted runners are engineering calibration only. They are useful for same-run relative comparisons but are not assumed to equal Ryzen 9 throughput.

## Frozen quality rules

Mechanical PASS requires:

- unchanged 36-world support;
- unchanged exhaustive support geometry;
- complete/valid common completion profile;
- every completed candidate profile covers 100% of exhaustive infosets;
- no illegal action, probability defect or hidden-world-token leakage;
- every exact BR replay passes the existing Q2 checks;
- all exploitability/NashConv values finite and non-negative within tolerance;
- all 14 frozen candidate points are present (`2 seeds x (4 SEARCH + 3 MCCFR)`).

Mechanical success verdict:

`PASS_06P1_EXACT_STRENGTH_COMPUTE_FRONTIER`

Mechanical failure verdict:

`FAIL_06P1_STRENGTH_COMPUTE_MECHANICS`

## Interpretation

06P1 may establish that one family is more cost-efficient **on this reduced fixture**. It may also show a mixed frontier. Neither result implies that the same family should be used globally in the full game.

The intended architectural use is round/mode specialization:

- exact/reduced evidence can justify MCCFR or exact methods where suffixes are tractable;
- full-game geometry and latency evidence can justify UCT, value priors or other approximations where tabular regret learning does not reuse enough state;
- a hybrid is preferred whenever it lies on a better practical frontier than a single universal method.

## Forbidden claims

06P1 cannot claim:

- full-game exploitability;
- production readiness;
- correct posterior reconstruction for hidden past discards;
- Fantasy continuation optimality;
- that the cheapest reduced-game method must be used on every street.

`REAL = 0/50` throughout this gate.
