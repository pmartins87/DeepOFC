# OpenOFC external research — 05G-Q0D MCCFR native-coverage scaling contract

Status: **precommitted engineering diagnostic / no strategic ranking**  
Authority: `BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
REAL routes certified: **0/50**

## Trigger

05G-Q0C showed that Search native support is already saturated by 20k iterations, while MCCFR coverage still grows strongly from 256 to 512 iterations. Q0D therefore scales **only MCCFR** before introducing any policy-completion mechanism.

Q0D asks one engineering question: how much of the 69,828-state finite support can MCCFR materialize natively at modest additional cost?

It does not compute policy EV, cross-play, exact best response, NashConv, exploitability, or a strategic winner.

## Frozen support and semantics

Reuse Q0A–Q0C unchanged:

- 36 physical worlds;
- canonical public pre-R3 state;
- exhaustive acting-player information-set support;
- exact legal action generator;
- own private discards retained;
- opponent hidden discards/future packets/world IDs excluded from acting-player keys;
- one physical world per MCCFR iteration sample;
- current regret-matching profile only for native materialized nodes.

## Frozen seeds and budgets

Seeds:

- `20260829`
- `20260830`

Budgets:

1. `1,024` MCCFR iterations;
2. `2,048` MCCFR iterations.

Each larger run restarts from the same seed. Native coverage must therefore be monotonic for the same seed.

## Measurements

For every run record:

- total/non-root/ambiguous non-root coverage;
- coverage by layer P0-R3, P1-R3, P0-R4, P1-R4;
- runtime;
- terminal evaluations;
- normalized-profile/legal-key/action-set/hidden-token firewalls;
- marginal non-root and ambiguous coverage gain from 1,024 to 2,048;
- uncovered support remaining.

## Precommitted Q1 snapshot-selection rule

Q0D may choose a **native MCCFR budget for Q1 engineering purposes only**. This is not a strategic-selection rule.

Evaluate budgets in ascending order over the cumulative tested ladder `512 -> 1,024 -> 2,048`.

Choose the smallest budget for which **both frozen seeds** satisfy simultaneously:

- non-root native coverage `>= 80%`;
- ambiguous non-root native coverage `>= 95%`.

If no tested budget satisfies both thresholds, choose `2,048` as the Q1 native MCCFR snapshot and explicitly retain a completion requirement for the uncovered remainder.

The thresholds only limit how much Q1 policy is delegated to an artificial completion component. They do not identify the strategically best policy.

## PASS gate

`PASS_MCCFR_SCALING_DIAGNOSTIC` requires:

1. all four runs execute;
2. semantic/profile firewalls remain green;
3. all three root information sets are materialized;
4. all P1-R3 information sets remain materialized;
5. for each seed, 2,048 non-root coverage is at least 1,024 coverage;
6. for each seed, 2,048 ambiguous coverage is at least 1,024 coverage;
7. CI completes inside the workflow timeout.

No coverage target is required for the experiment itself to pass; the 80%/95% thresholds govern only the later snapshot-selection rule.

## Decision use

After Q0D, freeze the selected MCCFR native snapshot budget and design Q1 with explicit source provenance. Search native nodes, MCCFR native nodes and any completion decisions must remain distinguishable and auditable.

No production migration is permitted from Q0D alone.
