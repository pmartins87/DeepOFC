# EXTERNAL 05H-A1 — MCCFR current vs simple-average exact-BR comparator

Authority: `BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

This comparator is precommitted before any 05H-H3 exploitability is observed. It is a parallel architecture audit and does not rewrite the frozen H1/H2/H3 path.

## Preconditions

- H0 geometry PASS.
- H1 selects one downstream budget mechanically from 1024/2048/4096 before payoff.
- A0 proves that adding the SIMPLE average accumulator leaves current MCCFR regret/current-policy trajectory exactly unchanged.

## Frozen candidates

For each seed independently, run one `OverlapExternalSamplingMCCFRSimpleAverage` solver to exactly the H1-selected budget and extract:

- `CURRENT_NATIVE = solver.current_profile()`;
- `AVERAGE_NATIVE = solver.average_profile()`.

The current profile must reproduce the ordinary solver's trajectory by A0 construction.

Build the same deterministic learner-independent completion once from exhaustive 05H support.

Complete two profiles independently:

- `M_current = CURRENT_NATIVE` wherever present, completion only in its holes;
- `M_average = AVERAGE_NATIVE` wherever present, completion only in its holes.

Neither native source may overwrite the other because the profiles are separate candidates. Completion never overwrites a native key.

## Required provenance

For both candidates and both seeds report:

- native infoset count/fraction and layer counts;
- ambiguous non-root native count/fraction;
- completion count/fraction;
- native SHA-256;
- complete-profile SHA-256;
- source-map SHA-256;
- exact native-preservation checks;
- legal-action/probability/world-leakage firewalls.

## Strategic comparison

For both complete candidates and both seeds compute exact bilateral best response, NashConv and exploitability. Independently replay both BR values through the exact asymmetric evaluator with absolute error <= `1e-9`.

Seeds remain separate. No averaging across seeds may create a winner.

## Frozen interpretation

Numerical comparison tolerance: `1e-9` exploitability.

Per seed:

- `AVERAGE_LOWER` if `exploitability_average + 1e-9 < exploitability_current`;
- `CURRENT_LOWER` if `exploitability_current + 1e-9 < exploitability_average`;
- otherwise `TIED_WITHIN_1E-9`.

Cross-seed:

- `AVERAGE_LOWER_REPLICATED` only if both seeds say `AVERAGE_LOWER`;
- `CURRENT_LOWER_REPLICATED` only if both seeds say `CURRENT_LOWER`;
- `TIED_REPLICATED` only if both seeds tie;
- otherwise `NO_REPLICATED_EXPLOITABILITY_ORDER`.

Separately report whether each architecture satisfies the already-frozen H3 quality bands (`<=1e-6` strict near-Nash; `<=1e-3` low-not-strict). A tiny numerical win between two strict-near-Nash profiles is not itself a production promotion criterion.

## Interpretation discipline

A1 answers two different questions:

1. which finite-budget candidate is less exploitable on this exact reduced fixture;
2. whether the average-strategy architecture, which matches standard CFR/MCCFR convergence practice, changes the scientific conclusion at all.

A1 cannot invalidate a previously exact finite-fixture BR measurement. It can change which MCCFR architecture deserves priority for subsequent larger-scale research.