# M5Q — Support-free martingale prerequisites

Date: 2026-08-27

Status: **BOUNDED-INCREMENT PREREQUISITE PASS / AVERAGE-STRATEGY BLOCKER IDENTIFIED**

Workflow `33118314904` passed the frozen prerequisite audit. This is certification-architecture evidence only; it does not certify an OpenOFC route.

## What passed

For the exact reduced games, the sampled External Sampling regret coordinate increment has a finite direct envelope without dividing by a terminal-history sampling floor:

- Joker: exact terminal range `[-2,+2]`, so `|delta regret coordinate| <= 4`;
- hidden-discard: exact terminal range `[-6,+6]`, so `|delta regret coordinate| <= 12`.

The concrete sampled-regret traversal path contains no explicit division operator in the audited regret accumulation stages. Combined with M5Q-A's finite Monte Carlo unbiasedness diagnostic, this is enough to keep a support-free martingale route alive as a research direction.

## What blocked the first instantiation

The production reduced-game External Sampling class exposed only `behavioral_time_average_profile()`. Its own source explicitly states that this is a local behavioral time average and is **not** a standard CFR average when players act repeatedly.

Therefore the gate correctly refused to instantiate a support-free exploitability bound. A standard regret-to-equilibrium bridge needs an own-reach-weighted average-strategy object with independently validated semantics.

The second missing prerequisite is predictable/conditional variance accounting for sampled regret increments.

## Frozen identity

- workflow run: `33118314904`
- job: `98678571813`
- head: `1b488b5135fce4010a5a23e43278697fe55fcbab`
- payload SHA-256: `c434bfcc5267ddb0d5b57964c0e6319effd1383fbbb33d029c0ea19a18e96e54`
- artifact ZIP SHA-256: `af5efc0fa9463642957cef3f6aea610dc5159939cf123e9f3ac131ec480dfa37`
- mechanics tests: `5 passed`

## Decision

The next gate is not another exploitability calculation. It is an exact semantic-equivalence test for a reach-weighted MCCFR average against the independent full-tree CFR reference. Only after that passes should predictable variance accounting be implemented and a named martingale theorem instantiated.

## Authority firewall

This result does not create a route certificate, does not change production training semantics, and leaves the REAL counter at `0/50`.
