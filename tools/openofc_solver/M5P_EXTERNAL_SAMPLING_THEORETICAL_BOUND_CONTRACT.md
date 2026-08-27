# M5P external-sampling high-probability bound contract

Status: `THEOREM_FEASIBILITY_ONLY / NOT_PRODUCTION_CERTIFICATION`

## Purpose

M5O established that exact cumulative counterfactual regret can produce a correct exploitability upper bound for deterministic full-tree standard CFR on reduced games. DeepOFC's scalable blueprint, however, uses External Sampling MCCFR. M5P asks whether the classical **high-probability External Sampling MCCFR regret theorem** is numerically useful enough to become a certification primitive before we build any more elaborate stochastic certificate.

Primary source: Marc Lanctot, Kevin Waugh, Martin Zinkevich, Michael Bowling, *Monte Carlo Sampling for Regret Minimization in Extensive Games*, NeurIPS 2009, Theorem 4. The corrected paper states that for external-sampling MCCFR, for any `p in (0,1]`, player `i`'s average overall regret is bounded with probability at least `1-p` by

`(1 + sqrt(2)/sqrt(p)) * Delta_u_i * M_i * sqrt(|Abar_i|) / sqrt(T)`.

Primary paper: `https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html`

## Joint two-player conversion

DeepOFC uses two-player zero-sum HU subgames. M5P allocates an overall failure probability `alpha` equally across the two players (`p = alpha/2`) and uses a union bound. With probability at least `1-alpha`, both player-regret bounds hold simultaneously. The average profile's exploitability upper bound is then half the sum of the two average-regret bounds.

This is a theorem-level worst-case bound. M5P does not replace its constants with observed sampled regrets, empirical standard errors or tuned residuals.

## Structural constants

For the exact two-round perfect-recall benchmark, M5P computes the paper's structural terms directly from the game representation:

- an own-action sequence prefix is empty at round 3;
- at round 4 it is exactly the player's remembered physical round-3 action key;
- `M_i = sum_sequence sqrt(number of player-i infosets sharing that own-action prefix)`;
- `|Abar_i|` is the number of distinct player-i own-action subsequences represented by infoset prefixes and legal outgoing actions.

The implementation fails closed if an infoset is outside this audited two-round structure.

## Utility range

The theorem scales linearly with `Delta_u`. M5P reports a **per-unit-utility-range coefficient** so structural feasibility can be judged independently of score units.

It also reports a project-safe raw pairwise OFC range derived from the frozen scoring tables:

- maximum Top royalty: 22;
- maximum Middle royalty: 50;
- maximum Bottom royalty: 25;
- maximum row+scoop swing before royalties: 6;
- therefore a one-sided raw pairwise magnitude is at most 103 and `Delta_u <= 206`.

Using 206 is conservative. A future route may use a smaller rigorously proven route-local utility range, but cannot substitute an empirical observed range.

## Feasibility decision

M5P computes required iteration counts for frozen target exploitability values under both:

1. `Delta_u = 1`, exposing pure structural scaling;
2. `Delta_u = 206`, the conservative project raw-pairwise range.

A PASS means only that the theorem implementation and structural accounting are coherent. Practical feasibility is a separate quantitative outcome. If even the unit-range requirement is prohibitive, the classical worst-case theorem is retained as a correctness backstop but rejected as the primary production certificate; the next architecture must be a tighter data-dependent martingale/confidence-sequence bound with explicit unbiasedness and bounded-increment proofs.

## Authority firewall

M5P cannot:

- certify an M4Z route;
- convert raw sampled regrets directly into a certificate;
- claim a deterministic guarantee from one sampled run;
- use Q1/Q2 learned-response residuals as thresholds;
- change the REAL route count from `0/50`.
