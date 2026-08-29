# OpenOFC — MCCFR current-vs-average strategy literature audit

Date: 2026-08-29  
Scope: external reduced-game research only  
Production authority: **none**

## Why this audit exists

The current OpenOFC shadow comparator `OverlapExternalSamplingMCCFR` accumulates counterfactual regrets and exposes the instantaneous regret-matching policy through `current_profile()`. It does **not** currently accumulate a separate average strategy.

That choice was sufficient for the 05G experiment because exact bilateral best response directly measured the resulting current profile and found it essentially unexploitable on the frozen 36-world reduced game. However, direct success on one finite fixture is distinct from the standard theoretical convergence object of CFR/MCCFR.

## Primary literature

Marc Lanctot, Kevin Waugh, Martin Zinkevich, Michael Bowling, **Monte Carlo Sampling for Regret Minimization in Extensive Games**, NeurIPS 2009:

- official paper: https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- the paper states that the **time-averaged strategy profile** of regret-minimizing algorithms converges toward Nash equilibrium;
- its Eq. 3 defines the average behavioral strategy at an information set using the player's own reach probability as the weighting term;
- external-sampling MCCFR samples opponent/chance actions while enumerating the traverser's actions, and the paper proves regret bounds for this sampling scheme.

Martin Zinkevich, Michael Johanson, Michael Bowling, Carmelo Piccione, **Regret Minimization in Games with Incomplete Information**, NeurIPS 2007:

- https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- CFR's regret argument connects vanishing regret to an approximate Nash equilibrium through the average strategy profile.

## Reference implementation evidence

Google DeepMind OpenSpiel maintains distinct current and cumulative-average policy state for MCCFR:

- Python MCCFR base: https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/algorithms/mccfr.py
- C++ external-sampling MCCFR: https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/algorithms/external_sampling_mccfr.cc
- example evaluating MCCFR exploitability through `average_policy()`: https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/examples/mccfr_example.py

OpenSpiel's external sampler supports two average modes. Its two-player `SIMPLE` mode updates the cumulative policy at the opponent node encountered during the other player's external-sampling traversal. Its `FULL` mode performs a separate full-tree average-policy update weighted by own reach.

## Consequence for DeepOFC research

The existing `current_profile()` is **not declared wrong**. Exact BR remains capable of proving that a particular current profile is good or bad on a finite fixture, independently of asymptotic theory. The 05G Q2 near-zero exploitability therefore remains valid.

But using only the current policy as the MCCFR candidate leaves an avoidable research gap when scaling. We need a shadow implementation of an external-sampling **simple average strategy** and must compare it against the current-policy candidate under identical support, seeds, iteration budgets, completion rules and exact bilateral BR.

## Research guardrail

The average-strategy work is additive. It does not modify the already frozen 05H H1/H2/H3 current-policy path. A parallel gate will be precommitted before 05H exploitability is observed. No solver becomes canonical merely because it matches textbook CFR conventions; exact reduced-game exploitability remains the empirical authority.