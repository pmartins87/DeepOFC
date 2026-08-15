# DeepOFC Roadmap

The roadmap is deliberately gated. A stage is not considered complete because code exists; it is complete only when its validation conditions are satisfied.

## Current project status — 2026-08-15

| Gate | Status | What is already real | What still blocks PASS |
|---|---|---|---|
| R0 Bootstrap | ✅ Operational | repositories, pinned OH baseline, evidence manifests, replay fixtures | archival copy of supplied legacy `.tm` in repo |
| R1 Rules/canonical state | 🟡 Advanced | target variant, 54-card physical deck, 2–3 players, 5/3/3/3/3, 3/5/5, royalties, Fantasy entry/stay, explicit one-shot Fantasy state, **Joker substitution/duplication/board-validity semantics frozen** | every re-Fantasy count, capped settlement, exact rake attribution, discard-observability edge |
| R2 Exact scoring | 🟡 Advanced | standard + Joker 3-card/5-card ranking, **board-aware strongest-valid Joker assignment**, foul, royalties, scoop, pairwise scoring tests | double-foul rule, capped multiway settlement, full Fantasy triggers, broader exhaustive/property validation |
| R3 Legal actions | 🟡 Advanced | exact normal actions plus lazy exact 14–17-card Fantasy full-board generator | integrate board-aware Joker legality/evaluation into pruning/search and broader independent/property validation |
| R4 Simulator | ⬜ Not started as certified gate | deterministic state primitives exist | complete deal/observation/settlement simulator and fuzzing |
| R5 Baseline decision engine | ⬜ Not started | — | exact/search/Monte-Carlo baselines |
| R6 Solver study | ⬜ Not started | — | architecture benchmark/selection |
| R7 Training | ⬜ Not started | — | reproducible training pipeline if selected architecture needs learning |
| R8 Exploitation | ⬜ Not started | — | opponent model only after strong base policy |
| R9 OpenHoldem state/scraper | 🟡 Active critical path | isolated OFC state, tablemap gate, raw scraper, C++ reconstructor, Python↔C++ replay equality, full Release|Win32 build green, Fantasy pre-routing fail-close, persistent JK1/JK2 interface, cross-repo contract gate, read-only guard | pixels→tablemap→raw→canonical proof, live Joker calibration, full Fantasy 14–17 recognition/state, first-round loose cards, 3-player geometry |
| R10 Autoplayer | 🟡 Infrastructure active / live blocked by R9 | hard no-click guard plus **arbitrary source-card→target drag primitive compiled, exported and loaded by OH** | OFC action executor, source/target resolution, discard/Confirm semantics, post-drag verification, Fantasy reflow handling |
| R11 Shadow | ⬜ Blocked | — | sustained no-click live validation |
| R12 Controlled live | ⬜ Blocked | — | low-stake live validation with kill switch |
| R13 Production | ⬜ Blocked | — | complete operational/runtime/training bundle |

### Variant identity frozen by the newest evidence

DeepOFC targets one concrete KKPoker product: **OFC Joker Ultimate**. Fantasy is a state of that same variant, not a separate runtime game. The new user-supplied capture shows `Game Mode: Ultimate`, `Joker: Yes`, then transitions into the `FANTASY` UI on the same table. The target physical deck is **52 standard cards + two physical Jokers = 54 cards**. See `docs/FANTASY_CAPTURE_AUDIT_2026-08-15.md`.

## R0 — Bootstrap

- [x] Confirm write access to `pmartins87/DeepOFC`.
- [x] Confirm authoritative OpenHoldem repository.
- [x] Pin bootstrap OpenHoldem commit.
- [x] Create dedicated `deepofc` branch in OpenHoldem source.
- [x] Inventory supplied tablemap and replay frames.
- [x] Commit a machine-readable input/evidence manifest with hashes.
- [x] Preserve representative replay evidence in reproducible canonical test fixtures.
- [ ] Commit the supplied `KKPoker_OFC.tm` itself (the manifest already freezes its SHA256).

**Current R0 status:** operationally sufficient; remaining `.tm` copy is archival rather than a mathematical dependency.

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
- Fantasy state and Fantasy deal count;
- button/order;
- score context when relevant.

### R1 progress frozen so far

- [x] Concrete target identified from supplied live frames: **KKPoker OFC Joker Ultimate**.
- [x] New Fantasy capture confirms `Ultimate + Joker + Fantasy` are one target-variant state machine, not separate OH modes.
- [x] Physical deck frozen as **54 cards = 52 standard + JK1 + JK2**.
- [x] 2- and 3-player normal tables frozen as supported engine scope.
- [x] Five-round 5 / 3 / 3 / 3 / 3 Pineapple flow frozen.
- [x] 3/5/5 structure and current-client Bottom >= Middle >= Top foul rule frozen.
- [x] Full royalty table frozen.
- [x] QQ+ Fantasy entry and trips-top / quads+-bottom stay condition frozen.
- [x] Progressive 14/15/16 and Joker Ultimate trips-top 17-card entry transcribed.
- [x] Current official OFC rake headline recorded separately from raw scoring.
- [x] Canonical row-membership model corrected: KKPoker re-sorts cards inside a row, so visual slot identity is not persistent strategy state.
- [x] Pre-arrangement model added: Hero may place cards tentatively before Hero becomes acting player; only Confirm commits.
- [x] Golden normal-play decision fixtures added, including frames 000543 and 000568.
- [x] New Fantasy evidence package audited: 84 BMP + 84 HTML snapshots, 450x830, immutable ZIP hash recorded.
- [x] Python canonical state now represents Hero Fantasy explicitly inside `joker_ultimate`, using a one-shot `round_index=-1`, 14–17 physical incoming cards and strict 13-card tentative-board Confirm shape.
- [x] Joker substitution is **with replacement**: a Joker may duplicate a known nominal card and JK1/JK2 may choose the same nominal card.
- [x] Five-of-a-Kind is explicitly **not** a valid hand category; such nominal substitutions are skipped.
- [x] Complete-board Joker semantics frozen: choose the strongest legal assignment that preserves `Bottom >= Middle >= Top` whenever such an assignment exists; an avoidable Joker-induced foul is forbidden.
- [x] Equivalent nominal assignments with the same HandRank are strategically interchangeable; physical JK1/JK2 identity remains canonical.
- [ ] Freeze every Joker Ultimate re-Fantasy card-count path, especially Bottom-quads-only stay.
- [ ] Freeze exact win-cap settlement from a concrete insufficient-funds example.
- [ ] Freeze exact OFC rake `pot` definition/attribution for settlement.
- [ ] Resolve live observability of opponent discard identities.
- [ ] Canonicalize representative Fantasy transitions and add them to the golden fixture suite.
- [ ] Canonicalize all remaining supplied gameplay transitions and validate them end-to-end.

**Gate:** unit tests reproduce every supplied gameplay transition required for decisions without contradictory state, and no rule affecting action EV remains an unstated assumption.

## R2 — Exact scoring engine

Already implemented and tested:

- [x] 3-card top ranking;
- [x] 5-card middle/bottom ranking;
- [x] Bottom >= Middle >= Top foul comparison with current-client equality rule;
- [x] row win/tie/loss for standard cards;
- [x] scoop;
- [x] full royalty tables;
- [x] standard pairwise point total;
- [x] fail-closed behavior for unresolved both-player-foul case;
- [x] exact Joker substitution over all 52 nominal cards **with replacement**;
- [x] duplicate nominal Joker assignments, including both Jokers selecting the same nominal card;
- [x] Five-of-a-Kind substitutions excluded while continuing to the strongest ordinary poker hand (for example `AAAA + JK -> AAAA K`);
- [x] complete-board Joker selection is board-aware rather than row-greedy: local maxima are reduced when necessary to preserve a valid board;
- [x] no Joker rescue is invented when no legal substitution can satisfy the board ordering.

Still required:

- [ ] Fantasy/re-Fantasy trigger evaluation for every frozen path;
- [ ] both-player-foul settlement;
- [ ] ordered 3-player capped settlement;
- [ ] exhaustive/property testing over legal completed boards where practical.

**Gate:** scoring has no ambiguous Joker/rank/settlement edge cases and passes a frozen golden suite.

## R3 — Legal action generator

Already implemented:

- [x] first-street normal placement assignments;
- [x] later-street choose-one-discard/place-two combinations;
- [x] row-capacity pruning;
- [x] exact coverage of incoming physical cards;
- [x] canonicalization away from purely visual within-row order;
- [x] Fantasy one-shot action generation for 14/15/16/17-card incoming sets;
- [x] each Fantasy action chooses exactly 13 physical cards for canonical 3/5/5 and discards the remaining 1–4;
- [x] exact Fantasy action-space cardinalities frozen by tests;
- [x] Fantasy enumeration is lazy rather than materializing an infeasible action tuple.

Exact raw Fantasy action counts before strategy/search pruning:

- 14 cards: **1,009,008** actions;
- 15 cards: **7,567,560** actions;
- 16 cards: **40,360,320** actions;
- 17 cards: **171,531,360** actions.

This large branching factor is strategically important for R5/R6: production Fantasy decisions cannot be implemented by naively scoring and storing all 171M candidates.

Still required:

- [ ] integrate the now-frozen board-aware Joker evaluator into whole-board legality/pruning/search;
- [ ] broader independent/property validation beyond current combinatorial/count tests;
- [ ] design search/pruning/state-compression strategy for practical Fantasy decision latency.

**Gate:** all legal actions generated, no illegal actions generated, verified against independent/brute-force small states.

## R4 — Environment / simulator

Build a deterministic simulator able to:

- deal complete 54-card Joker Ultimate games from seed;
- step through normal streets and Fantasy hands;
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
- suit/rank symmetry reductions where mathematically valid;
- Fantasy-specific branch reduction/search capable of handling the raw 1M–171M placement space.

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

## R9 — OpenHoldem OFC state support — CURRENT CRITICAL PATH

On `pmartins87/myoh_private:deepofc` the following is already implemented/proven:

- [x] isolated OFC state type instead of reusing Hold'em hole/common cards;
- [x] attach/reset OFC state in `CTableState`;
- [x] explicit physical Joker occurrence representation;
- [x] pending placements represented as row choices rather than persistent visual slots;
- [x] explicit `ofc_variant=joker_ultimate` tablemap gate via `SupportsOFCJokerUltimate()`;
- [x] dedicated raw `ScrapeOFCVisualObservation()` path that never intentionally falls through to Hold'em semantics;
- [x] native C++ stateful canonical reconstructor;
- [x] independent Python canonical reference exporter;
- [x] seven-frame Python -> C++ canonical snapshot equality gate;
- [x] negative replay tests for mid-hand attach, Confirm-before-turn safety and exchangeable JK1/JK2 occurrence labels;
- [x] hard R9 read-only autoplayer guard;
- [x] HU 450x830 normal-play geometry/calibration files;
- [x] deterministic replay-draft tablemap generator and verifier;
- [x] persistent physical Joker interface standardized as `joker1` / `joker2` across tablemap generator, verifier and C++ scraper;
- [x] cross-repository CI gate verifies the real DeepOFC tablemap inputs against the OpenHoldem scraper contract;
- [x] replay-measured `ofc_fantasy_active` detector routes Fantasy **before** normal Hero geometry is trusted;
- [x] C++ runtime fails closed on active Fantasy until the 14–17-card recognition path is certified;
- [x] independent `ofc_fantasy_recognizer_calibrated=0` authority gate prevents mode detection from accidentally enabling fan recognition;
- [x] 15-card Fantasy fan geometry frozen from three real deals;
- [x] first Fantasy15 recognition probe extracted 43/43 ordinary-card glyphs, 43/43 suits, and 42/42 ranks among ranks with an independent second example (the sole `8` had no second training/reference sample);
- [x] native dependency chain compiles on Windows GitHub Actions;
- [x] **full OpenHoldem `Release|Win32` build passes with the canonical reconstructor integrated**;
- [x] canonical heartbeat/reconstructor integration persisted on `myoh_private:deepofc` at commit `ebaa10f3d30cd0e1a2162ecc622a08d3bb73aa83`;
- [x] R9 Windows build gate v3 run `31866747684` completed successfully, including the seven-frame native replay gate and hard no-click guard.

Immediate R9 blockers:

- [ ] feed real replay pixels through `.tm` -> `CScraper` -> raw OFC observation -> C++ reconstructor and compare exactly with Python golden states;
- [ ] calibrate actual visible Joker face recognition rather than the current fail-closed placeholders;
- [ ] capture/validate normal first-round five-loose-card geometry;
- [ ] promote Fantasy15 from measured recognition probe to deterministic golden pixel→cards→canonical-state replay;
- [ ] capture/validate 14-, 16- and 17-card Fantasy fan geometry/recognition;
- [ ] add the same explicit Fantasy state semantics to the C++ raw/canonical state path and cross-language fixtures;
- [ ] derive Fantasy deal count without confusing normal `hero_total_dealt` round inference;
- [ ] add optional four-suit unknown-counter regions as consistency checks;
- [ ] calibrate 3-player Joker Ultimate geometry;
- [ ] add representative Fantasy golden replay frames and detailed replay hooks.

### R9 Fantasy engineering constraint

The new screenshots show a curved, overlapping, rotated Fantasy card fan. This is materially harder than the normal three upright incoming cards. The current probe shows that deterministic deskew/glyph recognition is promising, but approximate geometry or a successful small replay probe is not sufficient to enable runtime authority. `ofc_fantasy_recognizer_calibrated` remains `0` until representative 14–17-card replay sequences agree exactly through the full state path.

**Gate:** normal and Fantasy supplied replay pixels reconstruct exactly into canonical DeepOFC states, fail closed on ambiguous/invalid observations, and full OH Release|Win32 builds with the integration present.

## R10 — OFC drag-and-drop autoplayer

The KKPoker OFC runtime must manipulate **physical cards**, not emulate Hold'em action buttons.

### R10 infrastructure already proven

- [x] existing OpenHoldem `MouseClickDrag` audited and rejected as insufficient for card-to-row placement because it only drags across one rectangle;
- [x] new arbitrary primitive `MouseDragBetweenRects(hwnd, source_rect, target_rect, duration_ms)` implemented in `mouse.dll`;
- [x] drag start/end use interior points rather than rectangle borders;
- [x] once LEFTDOWN succeeds, held-button movement is atomic and always attempts LEFTUP even after a final-move failure;
- [x] `MouseDragBetweenRects` exported from `mouse.dll` and legacy `MouseClickDrag` preserved;
- [x] OpenHoldem loader requires the new symbol through `GetProcAddress`;
- [x] full mouse DLL + OpenHoldem `Release|Win32` build gate passes;
- [x] R10 arbitrary-drag workflow run `31867422276` completed successfully;
- [x] validated loader persisted to `myoh_private:deepofc` by commit `2b820365`;
- [x] hard R9 no-click guard remained present throughout; CI did **not** generate real mouse input.

Required OFC action transaction:

1. identify the intended physical source card from canonical state;
2. resolve that card to its **current** safe source rectangle;
3. resolve canonical destination row to a calibrated drop region;
4. press mouse on that card;
5. drag/move to the target row;
6. release;
7. wait for a stable frame and rescrape;
8. verify that exact physical card moved to the intended canonical row;
9. only then continue with another placement;
10. perform discard semantics exactly as observed;
11. click Confirm only when `hero_can_confirm` and the complete placement shape are valid;
12. verify the resulting committed canonical state;
13. fail closed immediately on any mismatch, timeout, unexpected resort or lost source card.

Still required:

- [ ] OFC-only action executor behind the hard guard;
- [ ] physical-card -> current source-rectangle resolver;
- [ ] calibrated `ofc_drop_top`, `ofc_drop_middle`, `ofc_drop_bottom` target regions;
- [ ] normal first round: drag all 5 cards;
- [ ] normal later rounds: place 2 + prove exact discard behavior;
- [ ] pre-arrangement support without prematurely confirming;
- [ ] Fantasy 14/15/16/17-card hand: build all 13 row cards and discard unused cards;
- [ ] Fantasy fan source re-resolution after every successful drag because the fan may reflow;
- [ ] Joker physical-card source handling;
- [ ] sandbox/replay mouse-gesture harness;
- [ ] post-gesture canonical-state verification;
- [ ] hard kill switch / no second action after mismatch.

The existing R9 hard no-click guard remains enabled until R9 PASS. R10 code may continue to be developed and build-tested behind the guard, but it may not click a live Joker Ultimate table before the gate is deliberately advanced.

**Gate:** replay/sandbox UI tests execute 100% correct placements/discards/Confirm, including Fantasy, with mismatch protection.

## R11 — End-to-end shadow mode

Run live with no clicks:

- scrape state;
- produce action;
- log expected physical UI gesture sequence;
- compare with actual manual play/state transition;
- measure scrape/action latency and mismatches;
- include normal and Fantasy hands.

**Gate:** sustained zero unsafe state/action mismatches over a substantial sample.

## R12 — Controlled live mode

Enable clicks at the lowest practical stake with hard safety guards, logging and kill switch.

**Gate:** stable runtime, correct scoring/state reconstruction, no duplicate/missed actions, correct drag/drop behavior, bankroll/rake accounting reconciled.

## R13 — Production DeepOFC

Only here is the project considered **ready for tables**.

Requirements include:

- versioned base strategy;
- versioned OH binary/source commit;
- exact normal+Fantasy tablemap/runtime bundle;
- reproducible solver/training artifacts;
- operational manual;
- rollback procedure;
- ongoing data/training update protocol.