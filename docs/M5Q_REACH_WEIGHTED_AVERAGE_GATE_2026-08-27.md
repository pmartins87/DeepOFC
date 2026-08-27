# M5Q — Reach-weighted MCCFR average gate

Date: 2026-08-27

Status: **REDUCED-GAME SEMANTIC GATE PASS / NEXT BLOCKER = PREDICTABLE VARIANCE**

The support-free prerequisite audit identified that the existing External Sampling implementation exposed only a local behavioral time average, which is not the standard CFR own-reach-weighted average required by the regret-to-equilibrium bridge.

A separate candidate average recorder was implemented without changing the sampled-regret update path. It records the pre-update strategy using the same chance and own-sequence reach semantics as the independent full-tree CFR reference.

## Frozen result

Workflow `33124398189` passed.

- mechanics tests: `3 passed`;
- Joker maximum action-probability difference versus full-tree CFR average: `0.0`;
- hidden-discard maximum action-probability difference versus full-tree CFR average: `0.0`;
- tolerance: `1e-15`;
- sampled-regret table difference between instrumented and uninstrumented same-seed solvers after the invariance probe: `0.0`;
- RNG state remained exactly identical;
- the new reach-weighted average differs materially from the old local time average (`max difference = 0.5` in the frozen evolving-strategy probe).

Payload SHA-256: `2c51534c4528d4b53e807a4e76fa8f93872d462c9ca8839ba1073fd23e0e268c`.
Artifact ZIP SHA-256: `1f1768821ac2f389b699cb2b55afd3a422dea1d5f17be48c241f0105176be98f`.

## Interpretation

This closes the average-strategy semantic blocker **on the exact reduced-game validation surface**. The result is stronger than simply adding a method with the right name: it matches the independently implemented full-tree CFR average exactly on both reduced-game families and demonstrably leaves the sampled-regret trajectory untouched.

It does not yet provide a scalable full-game average implementation. The exact recorder deliberately enumerates the reduced-game surface and exists as a semantic reference/certification test object.

## Next blocker

The support-free route now advances to predictable/conditional variance accounting for the sampled regret martingale. A concentration theorem must not be instantiated until its martingale-difference envelope and predictable quadratic variation assumptions are explicitly bound to the implementation.

## Authority firewall

This gate does not prove exploitability, does not authorize a production full-game average implementation, and leaves REAL at `0/50`.
