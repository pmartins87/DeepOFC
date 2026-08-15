# DeepOFC Roadmap

The roadmap is deliberately gated. A stage is not considered complete because code exists; it is complete only when its validation conditions are satisfied.

## R0 — Bootstrap

- [x] Confirm write access to `pmartins87/DeepOFC`.
- [x] Confirm authoritative OpenHoldem repository.
- [x] Pin bootstrap OpenHoldem commit.
- [x] Create dedicated `deepofc` branch in OpenHoldem source.
- [x] Inventory supplied tablemap and replay frames.
- [x] Commit a machine-readable input/evidence manifest with hashes.
- [x] Preserve representative replay evidence in reproducible canonical test fixtures.
- [ ] Commit the supplied `KKPoker_OFC.tm` itself (the manifest already freezes its SHA256).

**Current R0 status:** operationally sufficient to proceed with R1; the remaining physical tablemap copy is archival rather than a mathematical dependency.

**Gate:** repository can reproduce the initial evidence inventory and points to an immutable OH baseline.

## R1 — Joker Ultimate rules and canonical state

Define, test and freeze:

- deck composition, including Joker semantics;
- number of players supported by KKPoker Joker Ultimate;
- first street and subsequent street deal/discard counts;
- exact Joker wildcard behavior;
- exact 3/5/5 row ordering and foul comparison;
- royalties for top/middle/bottom;
- scoop scoring;
- Fantasy entry, progressive/Ultimate Fantasy and stay-in-Fantasy rules;
- dealer/button/acting-order semantics;
- hidden information: own discarded cards, opponent discards and inaccessible card information;
- KKPoker rake/economics separately from raw point scoring.

Canonical state must include at least:

- per-player committed 3/5/5 rows;
- known visible cards;
- hero cards currently in hand this street;
- tentative hero pre-Confirm placements;
- hero discarded cards known to hero;
- opponent hidden-discard count where observable without revealing identity;
- action/placement history where required;
- street/round and actor;
- separate `hero_can_prepare` and `hero_can_confirm` semantics;
- Fantasy state;
- button/order;
- score context when relevant.

### R1 progress frozen so far

- [x] Concrete target identified from supplied live frames: **KKPoker OFC Joker Ultimate**.
- [x] 2- and 3-player normal tables frozen as supported engine scope.
- [x] Five-round 5 / 3 / 3 / 3 / 3 Pineapple flow frozen.
- [x] 3/5/5 structure and current-client Bottom >= Middle >= Top foul rule frozen.
- [x] Full royalty table frozen.
- [x] QQ+ Fantasy entry and trips-top / quads+-bottom stay condition frozen.
- [x] Progressive 14/15/16 and Joker Ultimate trips-top 17-card entry transcribed.
- [x] Current official OFC rake headline recorded separately from raw scoring.
- [x] Canonical row-membership model corrected: KKPoker re-sorts cards inside a row, so visual slot identity is not persistent strategy state.
- [x] Pre-arrangement model added: Hero may place cards tentatively before Hero becomes acting player; only Confirm commits.
- [x] Golden decision fixtures added for frames 000543 and 000568.
- [ ] Freeze Joker wildcard uniqueness/tie semantics.
- [ ] Freeze every Joker Ultimate re-Fantasy card-count path.
- [ ] Freeze exact win-cap settlement from a concrete insufficient-funds example.
- [ ] Freeze exact OFC rake `pot` definition/attribution for settlement.
- [ ] Resolve live observability of opponent discard identities.
- [ ] Canonicalize all remaining supplied gameplay transitions and validate them end-to-end.

**Gate:** unit tests reproduce every supplied gameplay frame transition without contradictory state, and no rule affecting action EV remains an unstated assumption.

## R2 — Exact scoring engine

Implement independent evaluators for:

- 3-card top hand;
- 5-card middle/bottom hand;
- Joker-aware ranking;
- foul detection;
- row win/tie/loss;
- scoop;
- royalties;
- Fantasy triggers;
- pairwise and multiway point settlement.

Use exhaustive property tests over legal completed boards where practical.

**Gate:** scoring has no ambiguous Joker/rank edge cases and passes a frozen golden suite.

## R3 — Legal action generator

Given a state and current cards, enumerate every legal action exactly:

- first street placement permutations;
- later street choose/discard/place combinations;
- row-capacity constraints;
- no card duplication;
- no moving previously committed cards;
- canonicalize away purely visual within-row permutations.

**Gate:** all legal actions generated, no illegal actions generated, verified against brute-force small states.

## R4 — Environment / simulator

Build a deterministic simulator able to:

- deal complete Joker Ultimate games from seed;
- step through streets;
- expose observations separately from hidden state;
- settle scores;
- support 2–3 players;
- replay logged/scraped games.

**Gate:** deterministic seed replay and state invariants pass large fuzz runs.

## R5 — Baseline decision engine

Before ML, establish strong reference baselines:

- exact terminal enumeration;
- expectimax / chance-tree search for shallow states;
- Monte Carlo continuation search;
- rollout policies;
- transposition/state hashing;
- suit/rank symmetry reductions where mathematically valid.

Measure decision uncertainty and convergence.

**Gate:** reproducible EV estimates with independent-seed stability tests.

## R6 — Solver architecture study

Benchmark candidates rather than choosing by analogy with Hold'em:

- exhaustive dynamic programming where state compression permits;
- information-set search;
- CFR-family methods if strategically appropriate;
- MCTS variants;
- self-play RL/value-policy networks;
- hybrid exact-search + learned value function.

The selected architecture must explicitly model simultaneous strategic interaction and imperfect information; a single-agent greedy board optimizer is not sufficient for a multi-player competitive solution.

**Gate:** documented benchmark showing why the selected approach dominates alternatives on representative subgames.

## R7 — Training pipeline

If learning is required:

- Ryzen 9 worker package;
- deterministic seeds/manifests;
- checkpointing and resume;
- train/validation state separation;
- exploitability or best-response proxies;
- regression suite against exact small subgames;
- reproducible artifact hashes.

**Gate:** training can be restarted from scratch and independently validated.

## R8 — Opponent modelling / exploitation

Only after a strong base policy exists:

- identify stable opponent placement tendencies;
- model deviations conditional on street/state features;
- derive best responses with shrinkage/uncertainty gates;
- safe fallback to base policy.

**Gate:** exploitation never degrades against the base model beyond a frozen safety tolerance.

## R9 — OpenHoldem OFC state support

On `pmartins87/myoh_private:deepofc`:

- [x] add an isolated OFC state type instead of reusing Hold'em hole/common cards;
- [x] attach/reset it in `CTableState`;
- [x] reserve explicit physical Joker identities in OFC-local card representation;
- [x] represent pending placements as row choices rather than persistent visual slots;
- [ ] detect OFC/Joker Ultimate tablemap mode;
- [ ] scrape all 13 visible row positions per occupied seat and normalize within-row ordering;
- [ ] scrape hero incoming cards independently from committed board rows;
- [ ] scrape/derive round, Fantasy, button, actor and prepare/Confirm readiness;
- [ ] validate duplicate/impossible physical-card states;
- [ ] emit a versioned diagnostic canonical snapshot compatible with DeepOFC fixtures;
- [ ] add detailed replay hooks.

The first committed OH scaffold is deliberately read-only/inert. It is not yet evidence that scraping works.

**Gate:** scraper reconstructs supplied frames exactly into canonical DeepOFC states.

## R10 — OFC autoplayer

Implement concrete KKPoker placement actions:

- select card;
- select target row/visual drop region;
- discard required card;
- confirm/submit if UI requires;
- detect successful canonical state transition;
- fail closed on mismatch.

**Gate:** replay/sandbox UI tests execute 100% correct placements with mismatch protection.

## R11 — End-to-end shadow mode

Run live with no clicks:

- scrape state;
- produce action;
- log expected UI action;
- compare with actual manual play/state transition;
- measure scrape/action latency and mismatches.

**Gate:** sustained zero unsafe state/action mismatches over a substantial sample.

## R12 — Controlled live mode

Enable clicks at the lowest practical stake with hard safety guards, logging and kill switch.

**Gate:** stable runtime, correct scoring/state reconstruction, no duplicate/missed actions, bankroll/rake accounting reconciled.

## R13 — Production DeepOFC

Only here is the project considered "ready for tables".

Requirements include:

- versioned base strategy;
- versioned OH binary/source commit;
- exact tablemap/runtime bundle;
- reproducible solver/training artifacts;
- operational manual;
- rollback procedure;
- ongoing data/training update protocol.
