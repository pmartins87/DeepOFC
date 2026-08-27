# M5Q reach-weighted MCCFR average gate

Status: candidate validation contract; not a production certificate.

## Purpose

Resolve the first blocker found by the support-free martingale prerequisite audit: the existing External Sampling solver exposed only a local behavioral time average, while standard CFR regret-to-equilibrium statements require an own-reach-weighted average strategy.

## Frozen validation questions

1. Does the candidate average match the independent full-tree CFR reference average semantics on the exact reduced games?
2. Does adding the average recorder leave the sampled-regret trajectory and RNG state unchanged for the same seed?
3. Is the new average observably distinct from the old local behavioral time average once strategies evolve?
4. Does the authority remain fail-closed (`NOT_CERTIFICATION`, `0/50` REAL routes)?

## Candidate semantics

The candidate records the current profile immediately before each sampled MCCFR update. It uses the same chance/own-sequence reach weights as `TwoRoundFullTreeCFR.step()` and explicitly excludes opponent reach from average-strategy weighting.

The implementation enumerates the reduced-game chance/public surface exactly. This makes it an independent semantic reference and validation object, not a claim that the same enumeration is scalable to the full OpenOFC game.

## PASS gate

PASS requires, for both frozen reduced-game families (Joker and hidden-discard):

- maximum action-probability difference between candidate and full-tree CFR one-step average <= `1e-15` from the same frozen non-uniform regret table;
- no non-finite probability or mass;
- candidate authority is exactly `EXACT_REDUCED_GAME_REACH_WEIGHTED_CFR_AVERAGE_REFERENCE_NOT_CERTIFICATION`.

Additionally, on the Joker reduced game:

- same-seed instrumented and uninstrumented External Sampling runs must finish with exactly identical regret tables and RNG state;
- the reach-weighted average must differ from the legacy local behavioral time average after an evolving-strategy probe.

## Authority firewall

A PASS validates reduced-game average-strategy semantics only. It does not instantiate a concentration theorem, does not validate predictable variance accounting, does not prove exploitability, does not authorize a full-game implementation, and cannot increase the REAL route counter above `0/50`.
