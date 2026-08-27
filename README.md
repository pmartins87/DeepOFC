# DeepOFC

DeepOFC is the KKPoker **Open-Face Chinese Poker Joker Ultimate** project.

The end goal is a production player that is mathematically optimal, or as close to optimal as can be demonstrated, with the same engineering philosophy used in the wider DeepKK/SpinCore work:

- rules and economics are explicit, source-backed and versioned;
- strategic policy comes from exact evaluation/search/solver work rather than hand-written poker heuristics;
- uncertainty and approximation error are measured;
- runtime visual state must equal the mathematical state;
- OpenHoldem is modified where its Hold'em abstractions are semantically wrong for OFC;
- every source patch, validation gate and roadmap state is persisted in GitHub;
- expensive offline search/training can be delegated when the chosen solver architecture justifies it;
- no live click path is enabled merely because code exists: runtime authority is gated separately from implementation.

## Start here

The canonical current project state is [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md).

For continuation/versioning, read in this order:

1. [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md)
2. [`docs/VERSION_MANIFEST.md`](docs/VERSION_MANIFEST.md)
3. [`docs/HANDOFF.md`](docs/HANDOFF.md)
4. [`docs/ROADMAP.md`](docs/ROADMAP.md)

Historical status files remain evidence, but they must not silently override a newer frozen current-state checkpoint.

## Authoritative repositories

- DeepOFC game model / solver / reference / project documentation: `pmartins87/DeepOFC`, branch `main`.
- OpenHoldem runtime fork: `pmartins87/myoh_private`, branch `deepofc` plus explicitly named runtime experiment branches.
- OpenHoldem bootstrap commit: `3aa8a28944e3759fecc9323fb9f7361d54d4c9af`.

A temporary consolidation exception is documented in `VERSION_MANIFEST.md`: the latest M4/M5 strategic solver staging currently lives in `pmartins87/myoh_private`, branch `openofc-m4v-continuation-transport`, frozen at `c21c3c4f1017c83df07eb22230318a8131bf40d1`, and is being migrated back here through provenance/equivalence gates.

## Authoritative supplied evidence

- `KKPoker_OFC.tm` — SHA256 `de8566692d30e4c88092b9521c94a4ed053158669672067bd485ca340b1a69e0`;
- `joker_ofc_frames_and_rules.zip` — SHA256 `7de5a16eee195e3f0aa318e57e6a43c8d75deb5e3d322df6a3a94419658c16c4`;
- `ofc fantasy.zip` — SHA256 `1b91e038bb42acee2520187907d9ef9d6f34fc303d065ac2bc5dd1e92d52027e`;
- OpenHoldem source snapshot text — SHA256 `8a2809bf32b226775a237c9a51f970e8fd55148e777890f9a275b5fd6bd8521e`.

The machine-readable evidence inventory is `evidence/manifest.json`.

## Frozen target game

DeepOFC targets one concrete KKPoker product/state machine:

**KKPoker OFC Joker Ultimate**

Fantasy is a state/layout of Joker Ultimate, not a separate DeepOFC variant.

The physical deck is:

**52 standard cards + persistent physical JK1 + persistent physical JK2 = 54 cards.**

Current engine scope supports 2–3 players. Normal Pineapple play uses five rounds: `5 / 3 / 3 / 3 / 3`; all five initial cards are placed, and on each later round two of three are placed and one is discarded.

A completed board is `Top[3] + Middle[5] + Bottom[5]`, with current-client foul ordering:

`Bottom >= Middle >= Top`.

The complete rule contract, including royalties and Fantasy, lives in `docs/JOKER_RULES_SOURCE_TRANSCRIPTION.md`.

## Joker semantics

JK1 and JK2 are persistent physical cards. Wildcard assignment exists only in evaluation; it never rewrites canonical physical-card identity.

For evaluation:

- each Joker may represent any standard nominal card;
- duplication is allowed, including duplicating a physical card already present or both Jokers choosing the same nominal;
- only ordinary OFC poker-hand categories are valid, so Five-of-a-Kind is not a hand and such nominal assignments are skipped;
- on a complete board the Jokers are assigned jointly to the **strongest assignment that preserves a valid board whenever one exists**;
- a board is foul only if no valid Joker assignment can satisfy the row-order rule.

## Fantasy

Hero Fantasy is represented as a one-shot `round_index=-1` state inside `joker_ultimate`:

- 14–17 physical Hero incoming cards;
- select 13 to build one 3/5/5 board;
- leave the remaining 1–4 unplaced before Confirm; replay evidence shows KKPoker moves those cards to Hero's discard tracker after commit;
- all current Hero row cards are tentative until Confirm;
- the curved fan can reflow after every drag, so source-card geometry is ephemeral and must be re-scraped.

Real user-supplied frames 52→53 are frozen as golden Fantasy-15 semantic fixtures.

## Architecture

DeepOFC has four main layers:

1. **Game model** — exact Joker Ultimate rules, scoring, foul detection, royalties, Fantasy, turn/deal semantics and economics.
2. **Decision engine** — exact enumeration where tractable, search/Monte Carlo/value approximation where needed, deterministic reproducibility and validation against exact subgames.
3. **Runtime state bridge** — converts KKPoker pixels into canonical state and a chosen canonical placement into physical UI actions.
4. **OpenHoldem integration** — isolated OFC scrape/state/autoplayer support without pretending OFC is Hold'em.

## Current status

As of the 2026-08-27 consolidation/migration checkpoint:

- the continuation/Bellman strategic **architecture is implemented through M5G** in the frozen staging tree;
- M5G is a 50-state registry factory/certification firewall, not a claim that the strategy is solved;
- a REAL dynamic M4Z Bellman surface still requires **50/50 real-certified exact-V routes**: 2 Normal×Normal, 16 Normal×Fantasy and 32 Fantasy×Fantasy;
- the next strategic blocker is independent held-out route evidence, defensible threshold provenance and state-local certification;
- G1 repository inventory passed: 152 staging files were inventoried, 119 classified for migration, 33 preserved historical, with 38 related M4/M5 workflows recorded;
- recent strategic source is being consolidated into DeepOFC without discarding Git/blob/hash provenance;
- the R0–R13 roadmap remains the production-readiness framework;
- R9 recognition/reconstruction remains a runtime live-safety blocker;
- R10 transaction/drag/Confirm infrastructure remains separately gated;
- R11 shadow, R12 controlled live and R13 production remain downstream gates.

OpenHoldem `Release|Win32` has already built with isolated OFC integration in earlier gates. Runtime readiness still requires the stronger deterministic proof:

`real KKPoker pixels -> tablemap/recognizer -> raw OFC observation -> canonical C++ state == independent DeepOFC state`.

A runtime field label is canonical only when source commit, policy, tablemap/recognizer, build and artifact provenance are bound together.

Production readiness is reached only at R13 after strategy, runtime, training and operations are reproducible and certified.
