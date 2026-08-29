# OpenOFC external research — 05G-Q0C native coverage scaling contract

Status: **precommitted diagnostic / no strategic ranking**  
Authority: `BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
REAL routes certified: **0/50**

## Trigger

05G-Q0B passed technically and showed a large downstream native-coverage gap at bounded smoke budgets while Search and MCCFR were already close at the three root decisions.

Q0C asks whether that coverage gap persists as both learners receive larger, still bounded budgets. It does **not** complete missing policy, compute exact EV, compute best responses, or rank strategic quality.

## Frozen support and semantics

Reuse Q0A/Q0B byte-for-byte:

- 36 physical worlds;
- 69,828 exhaustive reachable information states at the Q0B snapshot;
- 3 P0-R3 root information states;
- canonical acting-player information-state key;
- private own discards;
- no opponent hidden discard/future packet/world ID leakage;
- same legal action generator and terminal evaluator.

## Frozen seeds and budgets

Seeds:

- `20260829`
- `20260830`

Budget pairs:

1. Search `20,000`; MCCFR `256`.
2. Search `50,000`; MCCFR `512`.

For a fixed learner and seed, the larger run restarts from the same seed. Its initial trajectory is therefore expected to reproduce the smaller run prefix; native materialized coverage must not decrease.

## Measurements

For every paired run record:

- total native infoset coverage;
- non-root native coverage;
- ambiguous non-root native coverage;
- coverage by layer: P0-R3, P1-R3, P0-R4, P1-R4;
- Search/MCCFR key-set intersection, union, Jaccard similarity;
- fraction of Search keys also materialized by MCCFR;
- fraction of MCCFR keys also materialized by Search;
- root-policy TV diagnostics;
- runtime;
- MCCFR terminal evaluations;
- the same legal-key/action-set/normalization/hidden-token firewalls as Q0B.

## PASS gate

`PASS_SCALING_DIAGNOSTIC` requires:

1. all four paired trials execute;
2. all Q0B semantic/profile-validation firewalls remain green;
3. all three root infosets exist for both learners in every run;
4. both learners have non-zero non-root coverage;
5. for each seed, Search 50k coverage is at least Search 20k coverage;
6. for each seed, MCCFR 512 coverage is at least MCCFR 256 coverage;
7. the same monotonic rule holds for ambiguous non-root coverage;
8. CI finishes inside the workflow timeout.

No minimum coverage ratio is a PASS threshold. Q0C measures the scaling curve before Q1 completion is designed.

## Forbidden interpretations

Q0C cannot claim that broader coverage means a strategically better policy. Coverage is an engineering property, not equilibrium quality. Root agreement also cannot substitute for downstream exact-BR analysis.

## Decision use

Q0C data will choose the **architecture of the next experiment**, not its winner. In particular it will show whether Q1 should:

- invest more in native Search coverage;
- use MCCFR as a broad proposal/rollout source;
- test a declared hybrid/router;
- or isolate completion as a separate algorithmic component.

No production migration is permitted from Q0C alone.
