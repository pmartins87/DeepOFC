# OpenOFC — evidence-based CFR variant research queue

Date: 2026-08-29  
Scope: future external/shadow solver research only  
Production authority: **none**

## Rule

Do not add solver variants merely because they are newer or famous. Every candidate must be introduced from primary/credible literature, isolated from the canonical solver, and judged on the same frozen reduced fixtures by exact bilateral best response whenever exact evaluation remains tractable.

## Current active question

**External-sampling MCCFR current policy vs accumulated simple-average policy.**

This is active now because classical CFR/MCCFR theory ties equilibrium convergence to an average strategy, while the current OpenOFC comparator historically exposed only the instantaneous regret-matching policy. 05H-A0/A1 address that gap first.

## Candidate queue after A1

### 1. CFR+

Primary work: Oskari Tammelin, *Solving Large Imperfect Information Games Using CFR+* (2014), arXiv:1407.5042.

Reference: https://arxiv.org/abs/1407.5042

Why it matters:

- CFR+ was designed specifically to accelerate approximate equilibrium solving in large imperfect-information games such as poker;
- it uses regret-matching+ and is commonly paired with alternating updates / weighted averaging in practical implementations;
- reported convergence speed materially improved over earlier CFR variants.

Research condition: do **not** implement CFR+ until the current-vs-average A1 result is understood, because otherwise several algorithmic changes would be confounded simultaneously.

### 2. Discounted CFR / sampling-compatible discounted variants

Primary work: Noam Brown, Tuomas Sandholm, *Solving Imperfect-Information Games via Discounted Regret Minimization* (AAAI 2019), arXiv:1809.04040.

References:
- https://arxiv.org/abs/1809.04040
- https://doi.org/10.1609/aaai.v33i01.33011829

Why it matters:

- discounts older regret contributions and reweights output strategies;
- the paper reports variants outperforming CFR+ across all tested games;
- importantly for OpenOFC, the authors identify a strong variant compatible with sampling in the game tree.

Research condition: select the precise sampling-compatible DCFR formulation from the paper before implementation; no parameter choice may be tuned using the target fixture's exploitability without a precommitted calibration protocol.

## Evaluation discipline for future variants

Any CFR+/DCFR experiment should separate at least:

- update rule;
- averaging/output rule;
- sampling rule;
- iteration/terminal-evaluation budget;
- native support coverage;
- completion burden;
- exact exploitability.

A faster wall-clock result at unequal game-tree work is descriptive unless the comparison contract explicitly defines compute normalization. A lower self-play loss is not sufficient. Exact BR/NashConv remains the strategic authority on tractable reduced fixtures.

## Not queued yet

Deep CFR / neural approximations are not the next step. They introduce function-approximation error before the tabular solver architecture is exhausted and would make it harder to distinguish game abstraction error from learning error. They may become relevant only when exact/tabular state storage is the demonstrated bottleneck.