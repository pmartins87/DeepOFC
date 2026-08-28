# External OFC component A/B protocol

Purpose: evaluate an external idea without contaminating the frozen strategic baseline or promoting a component on anecdotal evidence.

## 1. Experiment identity

Every experiment must freeze:

- `experiment_id`;
- internal baseline repository/commit;
- research candidate commit;
- external source repository/commit and exact source files that inspired the candidate;
- target rule-contract SHA;
- semantic-invariant artifact SHA;
- component under test;
- declared authority (`PERFORMANCE_ONLY`, `SCREENING_ONLY`, `STRATEGIC_CANDIDATE_NOT_CERTIFIED`, etc.);
- deterministic seed set;
- scenario/corpus manifest SHA;
- hardware/runtime environment;
- time/node/sample budget.

A candidate with a different rule contract is not an A/B strategy comparison. It is a separate-game experiment.

## 2. Required comparison levels

### Level A — semantic parity

Before measuring strength or speed, compare the candidate with the target authority on golden and generated cases. Relevant outputs include:

- legal actions;
- rank/category/tie ordering;
- Joker resolutions;
- royalties;
- foul status;
- Fantasy transition;
- terminal HU score;
- information-state identity;
- hidden-world consistency.

A semantic mismatch blocks promotion unless the mismatch is an intentional target-rule correction supported by independent evidence.

### Level B — exact reduced-game quality

Where an exact/reference solver exists, report:

- candidate action/value;
- exact action/value;
- best-action hit rate;
- value regret / missed deviation;
- rank correlation over candidate actions;
- worst-case error;
- distribution, not only mean;
- failures grouped by state family and game phase.

Use the existing M5R exact-BR/reference machinery when applicable.

### Level C — matched-work strategic comparison

For search/sampling candidates compare at equal expensive work, preferably terminal utility evaluations. Also report wall clock separately.

Examples:

- same number of terminal evaluations;
- same exact-leaf calls;
- same sampled complete worlds;
- same memory cap.

Time-only comparisons can be distorted by language/runtime differences; work-only comparisons can hide useful implementation speedups. Report both.

### Level D — operational performance

After strategic parity/benefit is established, measure:

- p50/p95/p99 decision latency;
- peak memory;
- throughput per core;
- scaling across workers;
- deterministic replay identity;
- timeout/fallback frequency.

Runtime/OpenHoldem metrics remain a separate track when UI/recognition is involved.

## 3. Chance and random-number policy

Use common random numbers when they preserve the same target distribution. Freeze seed IDs and deal-plan identities. Never compare candidates on independently sampled scenario sets and interpret the difference as algorithmic gain.

For imperfect-information search, the determinization sampler itself is part of the candidate and must be validated separately. Candidate A and B may share public roots while sampling hidden worlds from the same frozen sampler authority.

## 4. Statistical reporting

For Monte Carlo/search/RL comparisons report, as applicable:

- number of independent roots;
- number of independent seeds;
- mean difference;
- standard error or confidence interval;
- paired difference when common roots are used;
- maximum/worst observed regression;
- win/tie/loss only as a secondary descriptive metric;
- native point value/regret/exploitability evidence as primary strategic metrics.

A result against only a random opponent is screening evidence, not strategic certification.

## 5. External candidate classes and promotion criteria

### Fast exact/parity kernel

Examples: C++ evaluator, action generator, exact final-street solver.

Promotion requires **zero semantic mismatches** on the approved corpus, deterministic result identity, and a material measured performance gain.

### Heuristic pruning / proposal model

Promotion can only be as a bounded/proposal layer unless exact evidence demonstrates no strategic loss. Must report missed-optimal-action rate and worst regret. The full legal action set remains recoverable through fallback.

### Monte Carlo / MCTS / ISMCTS

May be promoted as search/screening policy after reduced-game exact validation and hidden-information tests. It cannot become a certification authority merely because empirical exploiters fail to beat it.

### RL / self-play policy

Requires the semantic firewall, immutable environment/rule build, diverse held-out opponents, exact/reduced-game tests, and independent exploitation/search evaluation. Training steps are not evidence of correctness.

### Runtime/CV component

Requires recorded-frame corpus, unknown-card handling, state reconstruction and safe-action/shadow tests. Strategic EV gain does not waive runtime safety gates.

## 6. Stop conditions

Stop an experiment early and record a FAIL when:

- target rules differ unexpectedly;
- hidden information leaks;
- the candidate creates impossible cards/worlds;
- deterministic replay breaks where required;
- semantic parity fails;
- a hard timeout or fallback path changes poker semantics;
- a performance gain exists only because the candidate silently prunes legal actions without a declared approximation;
- training reward is not the frozen native objective and no invariance proof exists.

## 7. Minimal result schema

Every result artifact should contain at least:

```json
{
  "schema": "openofc-external-component-ab-v1",
  "experiment_id": "...",
  "baseline_sha": "...",
  "candidate_sha": "...",
  "external_source": {"repo": "...", "sha": "..."},
  "rule_contract_sha256": "...",
  "semantic_firewall_sha256": "...",
  "scenario_manifest_sha256": "...",
  "seed_ids": [],
  "authority": "...",
  "quality": {},
  "work": {},
  "latency": {},
  "failures": [],
  "promotion_recommendation": "KEEP_BASELINE|PROMOTE_SHADOW|PROMOTE_COMPONENT|REJECT|INCONCLUSIVE",
  "real_routes_certified": 0
}
```

`real_routes_certified` may change only through the existing strategic certification authority, never because this A/B schema says `PROMOTE_COMPONENT`.

## 8. First approved experiment order

1. evaluator/Joker differential shadow parity;
2. target observer sampler;
3. phase-specific late exact/bounded search;
4. Fantasy branch-and-bound under exact DeepOFC continuation objective;
5. target ISMCTS baseline;
6. learned rollout/proposal policy;
7. only then consider expensive end-to-end RL/self-play.
