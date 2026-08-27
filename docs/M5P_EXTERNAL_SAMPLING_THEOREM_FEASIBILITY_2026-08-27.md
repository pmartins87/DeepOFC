# M5P External Sampling theorem feasibility — 2026-08-27

Status: `PASS_THEOREM_ACCOUNTING / PRACTICALLY_REJECTED_AS_PRIMARY_CERTIFICATE / NOT_CERTIFICATION`

## Evidence

- workflow run: `33102236780` — PASS
- artifact payload SHA-256: `e0b730ff5c021a6810b2712a21ad0936a5dd305f6ea7c5fb61253443b2830930`
- durable evidence: `evidence/strategic/m5p_external_sampling_theoretical_bound_2026-08-27.json`
- joint confidence: `0.95`
- per-player failure allocation: `0.025`
- theorem source: Lanctot et al., NeurIPS 2009, corrected Theorem 4

The mechanics tests and firewall passed. The structural constants were computed directly from the exact perfect-recall two-round game representation.

## Quantitative result

The classical worst-case theorem is mathematically relevant but unusably loose as DeepOFC's primary practical certification mechanism.

### Joker family

Per player:

- infosets: `4,892`
- own-action prefix groups: `19`
- distinct own-action subsequences: `163`
- `M_i`: `301.4270353022821`

At one million External Sampling iterations, with a normalized utility range `Delta_u = 1`, the theorem still gives exploitability upper bound:

`38.26916576876689`

For target exploitability `0.15`, the theorem requires approximately:

- `65,090,179,940` iterations even with `Delta_u = 1`;
- `2,762,166,875,909,999` iterations with the conservative project raw-pairwise range `Delta_u = 206`.

### Hidden-discard family

Per player:

- infosets: `33,252`
- own-action prefix groups: `43`
- distinct own-action subsequences: `475`
- `M_i`: `1188.9767044688751`

At one million iterations and `Delta_u = 1`, the theorem gives exploitability upper bound:

`257.6873748895559`

For target `0.15`, required work is approximately:

- `2,951,234,807,888` iterations at `Delta_u = 1`;
- `125,238,600,307,517,328` iterations at `Delta_u = 206`.

## Decision

The classical Lanctot External Sampling high-probability theorem remains a useful **correctness backstop**, because it proves that External Sampling MCCFR has bounded regret with high probability under its assumptions. Its worst-case constants are far too conservative for the practical certification budget of DeepOFC. This conclusion is already true with unit utility range, so merely tightening the OFC score range cannot rescue it.

Therefore M5P is closed as:

`THEORETICALLY_VALID / PRIMARY_CERTIFICATE_PRACTICALLY_REJECTED`.

We do not increase samples until these astronomical counts are reached.

## Next architecture: M5Q

The next certification candidate must be **data-dependent** rather than worst-case structural. The target is a martingale/confidence-sequence audit of the sampled counterfactual-regret estimator:

1. prove/verify unbiasedness for the exact External Sampling implementation;
2. expose the per-iteration sampled regret increments used by the solver;
3. derive a bounded-increment or variance-sensitive concentration term with an explicit simultaneous confidence allocation;
4. combine observed sampled cumulative regret with the concentration correction into a high-probability upper bound on true cumulative counterfactual regret;
5. validate coverage against exact best-response NashConv on reduced games across precommitted seeds/checkpoints;
6. reject the design if empirical coverage fails or if the correction remains impractically loose.

M5Q must be independently derived and audited. Raw sampled regret totals, bootstrap intervals, ordinary Monte Carlo standard errors or held-out learned-response residuals are not sufficient by themselves.

REAL M4Z route count remains `0/50`.
