# DeepOFC

DeepOFC is the Open-Face Chinese Poker project for KKPoker, initially targeting the **Joker** variant.

The end goal is a production player that is mathematically optimal or as close to optimal as practical, with the same engineering philosophy used in DeepKK/SpinCore:

- rules and economics are explicit and versioned;
- strategy is produced by a solver/search engine, not hand-written heuristics;
- uncertainty is measured and audited;
- runtime state must match the mathematical state exactly;
- OpenHoldem is adapted only where necessary to scrape and execute OFC actions;
- all source, patches, validation and roadmap state live in GitHub;
- heavy offline computation may run on the Ryzen 9.

## Authoritative inputs

Initial evidence supplied for bootstrap:

- `KKPoker_OFC.tm` — SHA256 `de8566692d30e4c88092b9521c94a4ed053158669672067bd485ca340b1a69e0`;
- `joker_ofc_frames_and_rules.zip` — SHA256 `7de5a16eee195e3f0aa318e57e6a43c8d75deb5e3d322df6a3a94419658c16c4`;
- OpenHoldem source snapshot text — SHA256 `8a2809bf32b226775a237c9a51f970e8fd55148e777890f9a275b5fd6bd8521e`;
- live OpenHoldem source repository: `pmartins87/myoh_private`, pinned bootstrap commit `3aa8a28944e3759fecc9323fb9f7361d54d4c9af`.

A dedicated branch `deepofc` has been created in `pmartins87/myoh_private` from that commit. DeepOFC-specific OpenHoldem changes must be isolated there until explicitly promoted.

## What the first inspection already proves

The supplied replay set contains 13 consecutive KKPoker OFC frames at 450x830. The table is four-handed. The visible layout is not Hold'em-like: each seat has a 3-card top row plus two 5-card rows, with progressive card placement and explicit fantasy/foul/royalty concepts. Therefore the existing OpenHoldem model of 2 (or 4 Omaha) private cards plus 5 community cards is structurally insufficient.

The current `.tm` still exposes normal Hold'em player-card/common-card regions and several legacy AoF/Blitz regions. It can be reused as a geometric/OCR starting point, but it cannot be treated as an OFC-complete state model.

The OpenHoldem scraper confirms the limitation in code: `CScraper::ScrapePlayerCards()` uses `kNumberOfCardsPerPlayerHoldEm` unless Omaha is enabled, and `ScrapeCommonCards()` is fixed to the standard community-card model. DeepOFC therefore requires an explicit OFC state path instead of trying to encode a 13-card board into the existing Hold'em symbols.

## Architecture direction

DeepOFC will be split into four layers:

1. **Game model** — exact Joker rules, scoring, foul detection, royalties, fantasy rules, turn/deal semantics and economics.
2. **Decision engine** — exact enumeration where tractable, search/Monte Carlo/value approximation where needed, with deterministic reproducibility and error bounds.
3. **Runtime state bridge** — converts a scraped KKPoker OFC table into the canonical mathematical state and converts a chosen placement into a concrete UI action.
4. **OpenHoldem integration** — minimal isolated changes to scraping, state exposure and autoplayer support; poker evaluation/betting abstractions are not reused where they are semantically wrong for OFC.

## Current status

`R0 — BOOTSTRAP` is in progress.

The next hard gate is **R1 — RULES + STATE SPECIFICATION**. We do not train anything and do not modify the autoplayer until the Joker rules, card-flow semantics and canonical state representation are locked by tests against the supplied frames.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) and [`docs/OPENHOLDEM_GAP_ANALYSIS.md`](docs/OPENHOLDEM_GAP_ANALYSIS.md).
