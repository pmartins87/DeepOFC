# M5Q Support-free martingale prerequisite contract

Status: **PRECOMMITTED PREREQUISITE AUDIT — NOT A CONCENTRATION CERTIFICATE**

Authority: `SUPPORT_FREE_MARTINGALE_PREREQUISITE_AUDIT_NOT_CERTIFICATION`

## Motivation

M5Q-E rejected the practical use of the Appendix-C route that divides by a single global minimum terminal-history sampling probability. Even at 100% uniform exploration, the zero-variance iteration floor was approximately `9.19e14` for the reduced Joker family and `1.38e18` for hidden-discard.

The next candidate architecture is a support-free martingale/concentration route. No Freedman, empirical-Bernstein, confidence-sequence, or other concentration formula may be attached to DeepOFC until the quantities to which it would apply are explicitly audited.

## Frozen prerequisite questions

For each exact two-round reduced family, audit:

1. **bounded sampled regret increments** — the production External Sampling regret update at a traverser information set is `action_value - node_value`; action and node values must remain inside the exact terminal utility envelope, giving a finite per-coordinate increment envelope without dividing by a terminal-history sampling probability;
2. **sampling-weight structure** — the production sampled regret increment path must not contain an inverse terminal-history probability correction in the traverser regret accumulation path;
3. **unbiasedness binding** — bind the existing M5Q-A sampled-regret unbiasedness evidence, while keeping its finite Monte Carlo status explicit;
4. **predictable-variance accounting** — determine whether an exact or independently upper-bounded conditional variance process has been implemented and validated;
5. **average-strategy semantics** — determine whether the MCCFR implementation exposes the reach-weighted average strategy required by the regret-to-equilibrium theorem, rather than only a local behavioral time average.

## Fail-closed rule

A support-free concentration certificate is **blocked** if either predictable-variance accounting or theorem-compatible average-strategy semantics is absent.

This audit may discover that the sampled regret increments themselves have a favorable bounded envelope. That is only a prerequisite. It is not permission to turn sampled regrets, empirical standard errors, or a behavioral time average into an exploitability upper bound.

## Exact reduced families

- two-round Joker perfect-recall benchmark;
- two-round hidden-discard perfect-recall benchmark.

Use the exact terminal utility ranges established by M5Q-D.

## Existing evidence binding

M5Q-A payload SHA-256:
`0188c219f6946055b8dae8c350ebfbca7aef65c93403dbb5f79c793cf30cedf5`

Interpretation remains: finite implementation evidence consistent with unbiased sampled regret updates on the audited projections, not a proof.

## Authority firewall

- no production route certification;
- no REAL-count change;
- no confidence level is emitted;
- no concentration theorem is instantiated in this gate;
- no average-strategy semantics are inferred from method names;
- a missing prerequisite is a successful diagnostic result, not a reason to relax the requirement.
