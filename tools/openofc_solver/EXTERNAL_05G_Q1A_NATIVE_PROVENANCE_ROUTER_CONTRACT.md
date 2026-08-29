# OpenOFC external research — 05G-Q1A native provenance/router contract

Status: **precommitted profile-assembly gate / no strategic evaluation**  
Authority: `BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
REAL routes certified: **0/50**

## Purpose

Q0C proved that additional UCT iterations refine on-path probabilities but do not expand Search native support beyond the 20k trajectory basin. Q0D separately determines how far MCCFR native support should be scaled before completion.

Q1A freezes the **provenance architecture** before any completed profile is evaluated. It must make it impossible to call a completion/backfill decision “Search” or “MCCFR” merely because that decision sits inside a profile carrying that learner's name.

Q1A performs no exact profile EV, cross-play, best response, NashConv or exploitability calculation.

## Frozen native learners

For both seeds `20260829` and `20260830`:

### Search native snapshot

- budget: `50,000` UCT iterations;
- exploration: `1.0`;
- only information states actually materialized by Search are `SEARCH_NATIVE`;
- empirical action-visit distributions are preserved exactly;
- missing information states remain absent.

The 50k snapshot is used rather than 20k because Q0C showed identical support but tighter root action concentration. This is a frozen budget choice, not a claim of strategic superiority.

### MCCFR native snapshot

- budget: the Q0D precommitted engineering selection;
- same seed as the paired Search snapshot;
- only information states actually materialized by MCCFR are `MCCFR_NATIVE`;
- current regret-matching distributions are preserved exactly;
- missing information states remain absent.

The Q0D selection rule is external to Q1A and must be recorded verbatim in the Q1A manifest.

## Three provenance maps

Q1A must materialize three source maps over the exhaustive 05G support.

### S-map — Search-native-only

For each information set:

- `SEARCH_NATIVE` if Search materialized it;
- `MISSING` otherwise.

### M-map — MCCFR-native-only

- `MCCFR_NATIVE` if MCCFR materialized it;
- `MISSING` otherwise.

### H-map — Search-priority hybrid native router

- `SEARCH_NATIVE` if Search materialized the information set;
- else `MCCFR_NATIVE` if MCCFR materialized it;
- else `MISSING`.

MCCFR may **never overwrite** a Search-native decision in H-map. This router is intentionally asymmetric because its experimental question is whether broad MCCFR support can backfill Search's off-trajectory holes while preserving Search where Search actually acted.

Q1A does not yet claim that H-map is a good strategy.

## Required provenance accounting

For each seed and each map record:

- exhaustive information-state count;
- source counts and percentages;
- source counts by layer;
- ambiguous non-root source counts;
- missing counts and percentages;
- profile/source-map SHA256;
- exact native distribution SHA256 for Search and MCCFR;
- overlap counts: Search∩MCCFR, Search-only, MCCFR-only, neither;
- Search/MCCFR disagreement metrics only on shared native information sets, clearly labeled diagnostic.

Every information set in the exhaustive support must receive exactly one provenance label in each source map.

## Integrity gates

`PASS_NATIVE_PROVENANCE` requires:

1. physical 36-world support and exhaustive support revalidate unchanged;
2. Q0D selected MCCFR budget is recorded and belongs to the precommitted tested ladder;
3. Search native keys are legal and distributions normalized;
4. MCCFR native keys are legal and distributions normalized;
5. no physical world ID leaks into information-state keys;
6. H-map preserves every Search-native distribution byte-for-byte at Search-native keys;
7. H-map uses MCCFR only on keys missing from Search;
8. all remaining uncovered keys are labeled `MISSING`, never silently uniform or synthetic;
9. source-count arithmetic exactly equals exhaustive support;
10. two seeds are kept separate rather than averaged into a fictitious policy.

## Completion firewall

Q1A is complete when native provenance is frozen. It must **not** fill `MISSING` keys.

Q1B will design and precommit a common completion component. Completion decisions will carry a distinct `COMPLETION_*` source label and will never overwrite native Search/MCCFR decisions.

This separation is required because Q0C showed that a nominal Search-complete profile would otherwise consist overwhelmingly of non-Search decisions.

## Later strategic evaluation

Only after Q1B creates complete source-labeled profiles may 05G-Q1C run exact self-play/cross-play, and only 05G-Q2 exact bilateral best response may rank equilibrium quality inside the reduced fixture.

No result from Q1A can migrate to production.
