# OpenHoldem gap analysis for DeepOFC

## Baseline

Authoritative runtime source for the bootstrap is `pmartins87/myoh_private` at commit:

`3aa8a28944e3759fecc9323fb9f7361d54d4c9af`

A branch named `deepofc` was created from exactly that commit. OFC changes belong on that branch until validation is complete.

Target live product has now been frozen from supplied gameplay evidence as:

**KKPoker OFC Joker Ultimate**

The normal-table engine scope is 2–3 players.

## Structural mismatch

OpenHoldem assumes a conventional poker state. In the bootstrap `CScraper.cpp`:

- `ScrapePlayerCards(int chair)` defaults to `kNumberOfCardsPerPlayerHoldEm` and only switches to the Omaha card count when `SupportsOmaha()` is true;
- player cards are written to `Player(chair)->hole_cards(i)`;
- `ScrapeCommonCards()` clears/populates exactly `kNumberOfCommunityCards` in the common-card array.

`CPlayer` stores legacy `_hole_cards[kMaxNumberOfCardsPerPlayer]`, while `CTableState` stores players plus exactly the legacy community-card array. This is not just an insufficient constant. OFC has a different ontology:

- up to 13 permanently committed cards per player's board;
- three semantically distinct rows (3 / 5 / 5);
- incoming hero cards that are not yet committed;
- Hero can tentatively pre-arrange cards before Hero becomes the acting player;
- one discarded card on later Pineapple streets;
- visible opponent boards but hidden opponent incoming/discard identities;
- two physical Jokers in the target variant;
- no Hold'em community board;
- no meaningful preflop/flop/turn/river mapping;
- actions are card placements/discards/Confirm, not fold/call/raise/betsize actions.

Therefore the correct architecture is **not** to increase `kNumberOfCardsPerPlayerHoldEm` to 13 or reuse the five community-card slots. That would contaminate a large number of symbols and evaluators with false semantics.

## Important replay-derived UI semantics

### Pending placement is not committed state

Supplied KKPoker replay frames show Hero receiving/arranging cards while an opponent's timer is still active. Hero can drag current cards to provisional row locations, but strategy commitment occurs only when Hero is the actor and Confirm is available/used.

The canonical bridge must therefore distinguish:

- committed board rows;
- `hero_incoming`;
- pending `card -> row` placements;
- `hero_can_prepare`;
- `hero_can_confirm` / action-required state.

A screen image containing a card physically over a row is not by itself proof that the card is already committed.

### Visual row slots are not persistent strategic identity

Supplied frames also show KKPoker reordering cards inside a row after Confirm. For example, a top or middle row may display the same card set in a different left-to-right order on the next frame.

Thus the strategic state is **row membership**, not the exact persistent visual slot chosen by the user. The scraper may read fixed screen rectangles, but the bridge must canonicalize their contents before hashing/comparing strategy states.

This matters for both correctness and state-space reduction: actions differing only by eventual auto-sorted within-row permutation are strategically equivalent.

## First OpenHoldem code milestone — STARTED

The `deepofc` branch now contains an inert/read-only scaffold:

- `OpenHoldem/COFCState.h`
  - schema version 1;
  - 2–3 player capacity (storage max 3);
  - explicit 3/5/5 boards;
  - up to 17 incoming Hero cards for Fantasy;
  - physical Joker identities 52/53 in the OFC-local representation;
  - hidden-discard counts;
  - pending placement as `incoming_index -> row`;
  - actor/dealer/round and prepare/Confirm flags.
- `OpenHoldem/CTableState.h`
  - owns a separate `COFCState _ofc_state`;
  - exposes `OFCState()` without altering Hold'em card arrays.
- `OpenHoldem/CTableState.cpp`
  - resets the OFC state with the table state;
  - exposes the accessor.

This scaffold is intentionally **not proof of R9**. It does not yet detect an OFC table, scrape a single OFC card, emit canonical JSON or click anything. It only establishes the correct semantic ownership boundary before scraper work.

## Tablemap naming contract — revised

Because row visual order is non-strategic but the screen still has fixed OCR rectangles, introduce OFC-specific source regions rather than overloading `pXcardface0/1`.

Candidate contract:

- `ofc_p{seat}_top{0..2}`
- `ofc_p{seat}_middle{0..4}`
- `ofc_p{seat}_bottom{0..4}`
- `ofc_hero_in{0..16}` — enough for 17-card Fantasy
- `ofc_action_confirm`
- `ofc_action_timer_p{seat}` or another actor indicator supported by stable pixels/text
- `ofc_fantasy_p{seat}` where observable
- optional discard-back/count regions where useful.

The source index in these names identifies a **screen rectangle only**. After scrape, cards are normalized into canonical row membership.

The supplied `KKPoker_OFC.tm` is still largely inherited from conventional poker/AoF and contains legacy `pXcardface0/1`, `c0cardface0..4` and unrelated old regions. Its geometry/template assets are useful, but it is not yet a complete OFC tablemap.

## OFC scraper path

Add `CScraper::ScrapeOFCState()` guarded by an explicit OFC/Joker Ultimate tablemap flag. It should:

1. clear only the OFC snapshot being rebuilt;
2. identify occupied OFC seats and map screen seats to canonical chairs;
3. scrape all 13 visual board rectangles per occupied seat;
4. normalize each row into canonical row membership;
5. scrape Hero incoming cards independently from committed board rows;
6. identify pending Hero placements without treating them as committed;
7. scrape or derive actor/Confirm readiness with a source-backed rule;
8. derive round from committed counts/incoming counts only when unambiguous; otherwise use explicit UI evidence;
9. represent opponent hidden discards by count only unless card identities are demonstrably visible to Hero at decision time;
10. validate duplicate-card, Joker-count, impossible-row-count and impossible-transition invariants;
11. fail the OFC snapshot invalid rather than silently substituting strategic cards;
12. emit a versioned deterministic diagnostic representation compatible with DeepOFC replay fixtures.

## Physical Joker representation

Legacy `Card`/StdDeck logic is 52-card poker. The OFC scaffold therefore uses an isolated integer representation:

- 0..51: standard physical cards using the existing OH/StdDeck convention where possible;
- 52: physical Joker 1;
- 53: physical Joker 2;
- negative values: OFC-local unknown/no-card/back sentinels.

These Joker/local values must **never** be fed to legacy Hold'em hand evaluators. Joker substitution belongs in the independent DeepOFC scoring engine and, later, in an explicitly Joker-aware runtime component.

## Dedicated runtime API

DeepOFC should consume one canonical serialized state from OpenHoldem, not dozens of legacy poker symbols. Candidate interfaces remain:

- DLL query returning a versioned state snapshot;
- local shared-memory/IPC snapshot;
- direct plugin extension if the existing DLL contract can safely carry the full state.

For initial development, deterministic JSON/log output is preferred because it permits exact frame-by-frame comparison against `fixtures/replay/*.json`.

## Autoplayer isolation

Existing OpenHoldem action functions are built around poker betting. OFC needs a separate action executor capable of a sequence such as:

`choose incoming card -> choose target row/drop region -> repeat -> leave/select discard -> Confirm`

The solver action should be row-based. The UI executor is responsible for translating that row action to a safe screen drop target that the KKPoker client will accept.

Safety requirements:

- action plan includes expected canonical pre-state hash;
- before every click, current canonical state must still match the expected plan state;
- clicks made only because Hero can prepare must never trigger Confirm before `hero_can_confirm`;
- immediately before Confirm, state/action shape is revalidated;
- after Confirm, scraper must observe the expected committed row transition;
- any mismatch aborts the plan;
- no fallback click based on coordinates alone.

## What can be reused

Likely reusable with limited changes:

- auto-connect/window handling;
- bitmap capture;
- tablemap geometry and transformations;
- standard-card rank/suit OCR/template infrastructure;
- player name OCR;
- mouse/keyboard primitives;
- logging/preferences infrastructure;
- DLL/plugin plumbing;
- replay-frame workflow.

## What should not drive OFC strategy

Do not reuse as strategic truth:

- Hold'em `betround`;
- common-card symbols;
- hole-card count assumptions;
- Hold'em hand-strength symbols over 7-card combinations;
- fold/call/raise/betpot/autoplayer decision model;
- blind/position scenario logic from DeepKK;
- raw visual row-slot order.

## Current first acceptance target

Before changing the autoplayer, finish the read-only scraper and diagnostic dumper on `myoh_private:deepofc`.

The acceptance test remains strict:

> Given every supplied KKPoker gameplay frame/transition, OpenHoldem must produce the same canonical card-row/incoming/pending/actor state as the independent DeepOFC fixture representation.

Only after that passes do we attach the decision engine or click executor.
