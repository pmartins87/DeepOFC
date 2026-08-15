# OpenHoldem gap analysis for DeepOFC

## Baseline

Authoritative runtime source for the bootstrap is `pmartins87/myoh_private` at commit:

`3aa8a28944e3759fecc9323fb9f7361d54d4c9af`

A branch named `deepofc` was created from exactly that commit. OFC changes belong on that branch until validation is complete.

## Structural mismatch

OpenHoldem assumes a conventional poker state. In the current `CScraper.cpp`:

- `ScrapePlayerCards(int chair)` defaults to `kNumberOfCardsPerPlayerHoldEm` and only switches to the Omaha card count when `SupportsOmaha()` is true;
- player cards are written to `Player(chair)->hole_cards(i)`;
- `ScrapeCommonCards()` clears/populates exactly `kNumberOfCommunityCards` in the common-card array.

This is not just an insufficient constant. OFC has a different ontology:

- up to 13 permanently placed cards per player's board;
- three semantically distinct rows (3 / 5 / 5);
- incoming hero cards that are not yet placed;
- one discarded card on later Pineapple-style streets;
- visible opponent boards but hidden opponent incoming/discarded cards;
- no Hold'em community board;
- no meaningful preflop/flop/turn/river mapping;
- actions are card placements/discards, not fold/call/raise/betsize actions.

Therefore the correct architecture is **not** to increase `kNumberOfCardsPerPlayerHoldEm` to 13 or reuse the five community-card slots. That would contaminate a large number of symbols and evaluators with false semantics.

## Proposed OH additions

### 1. Explicit OFC state model

Add a dedicated state object, conceptually:

```cpp
struct OFCPlayerBoard {
  Card top[3];
  Card middle[5];
  Card bottom[5];
};

struct OFCTableState {
  OFCPlayerBoard board[k_max_number_of_players];
  Card hero_incoming[5];
  int hero_incoming_count;
  int street;
  int acting_chair;
  int dealer_chair;
  bool fantasy[k_max_number_of_players];
  bool hero_action_required;
};
```

The exact class ownership should follow existing OpenHoldem lifetime/state conventions after inspecting `CTableState`, scraper state and symbol-engine dependencies. The key requirement is semantic isolation from `hole_cards` and `CommonCards`.

### 2. Tablemap naming contract

Introduce OFC-specific regions rather than overloading `pXcardface0/1`:

- `ofc_p{chair}_top{0..2}`
- `ofc_p{chair}_mid{0..4}`
- `ofc_p{chair}_bot{0..4}`
- `ofc_hero_in{0..4}`
- `ofc_action_ready`
- `ofc_fantasy_p{chair}` where observable
- optional explicit street/round indicator if the UI supplies one.

Rank/suit/nocard components may reuse the existing card template machinery. Geometry will be calibrated from the supplied 450x830 frames.

### 3. OFC scraper path

Add `CScraper::ScrapeOFCState()` guarded by an OFC tablemap/game-type flag. It should:

1. clear the OFC state;
2. scrape all 13 slots for each occupied chair;
3. scrape hero incoming cards separately;
4. derive street from counts only when the derivation is provably unambiguous; otherwise scrape an explicit UI indicator;
5. validate duplicate-card and impossible-count invariants;
6. fail the OFC state invalid rather than silently substituting `CARD_NOCARD` in strategic decisions.

### 4. Dedicated runtime API

DeepOFC should consume one canonical serialized state from OpenHoldem, not dozens of legacy poker symbols. Candidate interfaces:

- DLL query returning a versioned state snapshot;
- local shared-memory/IPC snapshot;
- or direct plugin extension if the current DLL contract can safely carry the full state.

For initial development, a deterministic JSON log/replay representation is preferred because it makes frame-by-frame validation easy.

### 5. Autoplayer isolation

Existing OpenHoldem action functions are built around poker betting. OFC needs a separate action executor capable of a sequence such as:

`click incoming card -> click target slot -> repeat -> choose discard -> submit`

Safety requirements:

- action plan includes expected pre-state hash;
- before every click, current state must still match the expected state;
- after submission, the scraper must observe the expected placement transition;
- any mismatch aborts the action plan;
- no fallback click based on screen coordinates alone.

## What can be reused

Likely reusable with limited changes:

- auto-connect/window handling;
- bitmap capture;
- tablemap geometry and transformations;
- card rank/suit OCR/template infrastructure;
- player name OCR;
- mouse/keyboard primitives;
- logging/preferences infrastructure;
- DLL/plugin plumbing;
- replay-frame workflow.

## What should not drive the OFC strategy

Do not reuse as strategic truth:

- Hold'em `betround`;
- common-card symbols;
- hole-card count assumptions;
- Hold'em hand-strength symbols over 7-card combinations;
- fold/call/raise/betpot/autoplayer decision model;
- blind/position scenario logic from DeepKK.

## First OpenHoldem coding milestone

Before changing the autoplayer, implement a read-only `OFCState` and a diagnostic dumper on the `deepofc` branch. The first acceptance test is simple and strict:

> Given each supplied KKPoker replay frame, OpenHoldem produces the same canonical card-slot state as the independent DeepOFC fixture parser.

Only after that passes do we attach the decision engine or click executor.
