# DeepOFC Roadmap

The roadmap is deliberately gated. A stage is not considered complete because code exists; it is complete only when its validation conditions are satisfied.

## R0 — Bootstrap

- [x] Confirm write access to `pmartins87/DeepOFC`.
- [x] Confirm authoritative OpenHoldem repository.
- [x] Pin bootstrap OpenHoldem commit.
- [x] Create dedicated `deepofc` branch in OpenHoldem source.
- [x] Inventory supplied tablemap and replay frames.
- [ ] Commit the supplied tablemap and machine-readable input manifest.
- [ ] Preserve representative replay evidence in a reproducible test-fixture format.

**Gate:** repository can reproduce the initial evidence inventory and points to an immutable OH baseline.

## R1 — Joker rules and canonical state

Define, test and freeze:

- deck composition, including Joker semantics;
- number of players supported by KKPoker Joker;
- first street and subsequent street deal/discard counts;
- whether Joker is wild, restricted wild, or transformed by special rules;
- exact 3/5/5 row ordering and foul comparison;
- royalties for top/middle/bottom;
- scoop scoring;
- fantasy entry, progressive fantasy, stay-in-fantasy rules;
- dealer/button/acting-order semantics;
- hidden information: own discarded cards, opponent discards and any inaccessible card information;
- KKPoker rake/economics separately from raw point scoring.

Canonical state must include at least:

- per-player 13 board slots with explicit row/slot identity;
- known visible cards;
- hero cards currently in hand this street;
- hero discarded cards known to hero;
- public dead cards;
- action/placement history where required;
- street/round and actor;
- fantasy state;
- button/order;
- score context when relevant.

**Gate:** unit tests reproduce every supplied frame transition without contradictory state.

## R2 — Exact scoring engine

Implement independent evaluators for:

- 3-card top hand;
- 5-card middle/bottom hand;
- Joker-aware ranking;
- foul detection;
- row win/tie/loss;
- scoop;
- royalties;
- fantasy triggers;
- pairwise and multiway point settlement.

Use exhaustive property tests over legal completed boards where practical.

**Gate:** scoring has no ambiguous Joker/rank edge cases and passes a frozen golden suite.

## R3 — Legal action generator

Given a state and current cards, enumerate every legal action exactly:

- first street placement permutations;
- later street choose/discard/place combinations;
- slot constraints;
- no card duplication;
- no moving previously placed cards.

Canonicalize equivalent actions to reduce branching without changing EV.

**Gate:** all legal actions generated, no illegal actions generated, verified against brute-force small states.

## R4 — Environment / simulator

Build a deterministic simulator able to:

- deal complete Joker games from seed;
- step through streets;
- expose observations separately from hidden state;
- settle scores;
- support 2–4 players if KKPoker rules allow;
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

- add an explicit OFC game/state type;
- scrape all 13 visible slots per seat;
- scrape hero incoming cards independently from board slots;
- expose street/fantasy/button/action readiness;
- avoid shoehorning OFC cards into Hold'em hole/community arrays;
- add detailed state logs and replay hooks.

**Gate:** scraper reconstructs supplied frames exactly into canonical DeepOFC states.

## R10 — OFC autoplayer

Implement concrete KKPoker placement actions:

- select card;
- select target slot/row;
- discard required card;
- confirm/submit if UI requires;
- detect successful state transition;
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
