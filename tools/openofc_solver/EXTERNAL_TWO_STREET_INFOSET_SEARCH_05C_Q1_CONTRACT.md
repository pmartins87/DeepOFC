# External two-street information-set search — 05C-Q1 contract

Status: **REPRODUCIBILITY DIAGNOSTIC / SHADOW ONLY**.

Authority: `FINITE_SUPPORT_R3_R4_INFOSET_TREE_SHADOW_ONLY`.

Q0 passed the four-layer mechanical firewall in run `33141837728`. Q1 asks a narrower empirical question: under the same six-world reduced game, how sensitive are root action selection and tree coverage to search budget and RNG seed?

## Frozen matrix

Budgets:

- 1,000 iterations
- 5,000 iterations
- 20,000 iterations

Search seeds:

- 2026082841
- 2026082843
- 2026082847
- 2026082849

The physical support remains the exact six-world Q0 fixture. Exploration remains `1.0` at every player node. No parameter is tuned between cells.

## Per-cell measurements

Each of the 12 cells records:

- selected root action;
- selected-root visit share;
- selected-root on-search mean;
- total information-set count;
- fully action-covered information-set count/fraction;
- terminal mean/min/max P0 utility;
- information-set and visit counts per decision layer.

## Per-budget summaries

For each budget Q1 reports:

- count/frequency of selected root actions across the four seeds;
- number of unique selected root actions;
- dominant selected action and frequency;
- mean selected-root visit share;
- mean and population standard deviation of terminal trajectory utility;
- min/mean/max information-set count;
- mean fully-covered information-set fraction.

## Mechanical gates

Every cell must preserve:

- authority `FINITE_SUPPORT_R3_R4_INFOSET_TREE_SHADOW_ONLY`;
- six support worlds;
- all four decision layers;
- `terminal_episodes == iterations`;
- root visit total equals the budget;
- fully explored count is not larger than total infoset count.

Q1 has **no strategic PASS threshold** for action agreement, EV dispersion or coverage. Instability is a result to diagnose, not a workflow failure.

## Non-claims

Q1 does not estimate equilibrium EV, exploitability, posterior correctness, full-game ISMCTS convergence, superiority over M5/CFR, or any REAL route certificate. Regardless of Q1 stability, the next strategy-quality authority is 05D CFR/MCCFR on the same reduced game.
