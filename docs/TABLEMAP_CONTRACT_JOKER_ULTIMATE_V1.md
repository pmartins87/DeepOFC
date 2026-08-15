# DeepOFC tablemap contract — Joker Ultimate v1

This is the semantic contract between the KKPoker tablemap and the read-only OpenHoldem OFC scraper. It is not a complete `.tm` file.

The contract intentionally reuses OpenHoldem's mature **per-slot rank/suit transforms** instead of depending on a new multi-card AutoOCR detector. That makes the first runtime tablemap closer to the supplied `.tm`, which already contains working T1/T5 card-rank/suit font transforms.

## Mandatory tablemap symbols

```text
s$ofc_variant        joker_ultimate
s$ofc_players        2        // or 3
s$ofc_hero_chair     1        // canonical chair mapped to the local/bottom seat
```

OpenHoldem branch `deepofc` exposes `CTablemap::SupportsOFCJokerUltimate()`, which returns true **only** when `ofc_variant=joker_ultimate`. A title containing `OFC` is not enough to activate OFC semantics.

## Mandatory visual slot contract

Every possible visual card slot has a base name and four children:

```text
<base>occupied
<base>back
<base>joker
<base>rank
<base>suit
```

Semantics:

- `occupied`: mandatory boolean/color region proving that a physical card object is present;
- `back`: mandatory boolean region distinguishing a hidden card back;
- `joker`: mandatory boolean/template region distinguishing a Joker face;
- `rank` / `suit`: standard OpenHoldem rank/suit transforms for a normal face-up card.

This explicit occupancy gate is critical. If `occupied=true` but the slot cannot be classified as back, Joker or a valid standard rank+suit pair, the scrape is **invalid**. An OCR miss is never silently converted into an empty slot.

### Board slots per canonical chair

For chair `p`:

```text
ofc_p{p}_top0 ... ofc_p{p}_top2
ofc_p{p}_middle0 ... ofc_p{p}_middle4
ofc_p{p}_bottom0 ... ofc_p{p}_bottom4
ofc_p{p}_discard0 ... ofc_p{p}_discard3
```

Example for the first Top source slot:

```text
ofc_p0_top0occupied
ofc_p0_top0back
ofc_p0_top0joker
ofc_p0_top0rank
ofc_p0_top0suit
```

Board-source slots may visually contain:

- committed face-up cards;
- for Hero, tentative current cards dragged over that row;
- for an opponent currently acting, hidden current card backs overlapping row space.

The raw scraper therefore interprets:

- standard/Joker face -> raw visual row card;
- back in a board-source slot -> increment that opponent's `hidden_incoming_count`, **not** a row destination;
- back in opponent discard slot -> increment `hidden_discard_count`;
- no occupied card -> empty visual source slot.

Opponent discard slots are currently **count-only**. If a face-up opponent discard is detected before R1 probe D1 establishes that such identity is valid live information, the scraper fails closed.

## Hero current cards

Normal Pineapple loose-card source slots:

```text
ofc_hero_in0 ... ofc_hero_in4
```

Each uses the same `occupied/back/joker/rank/suit` children.

The supplied later-round 450x830 evidence gives geometry for three loose positions. Slots 3 and 4 are therefore optional in the first scraper build until a first-round frame with five still-loose Hero cards is captured. Their absence is safe because normal physical-card accounting will reject a frame that actually needs unseen cards there.

The same current-street physical card may be either:

- detected in a loose `ofc_hero_in*` slot, or
- detected as a face card over a Hero row because it was pre-arranged.

It must never be accepted in both locations in the same raw observation.

Fantasy requires a separate geometry path because 14–17 incoming cards are displayed differently. No Fantasy geometry is considered supported until representative KKPoker frames are captured.

## Hero discard tracker

```text
ofc_hero_discard0 ... ofc_hero_discard3
```

Hero discarded cards are face-up/known to Hero in supplied evidence and should be returned as physical card identities.

## Joker detection and identity

The target game contains two Jokers, but we do **not** assume that their face artwork makes physical Joker #1 distinguishable from physical Joker #2.

Therefore each visual slot only needs a boolean/template `joker` classifier. The raw OpenHoldem scraper assigns deterministic frame-local labels JK1/JK2 in scan order when one/two Jokers are visible.

Important consequence: JK1/JK2 labels are **interchangeable canonical occurrence labels**, not evidence that the client exposes a persistent physical identity. Canonical state comparison must eventually be invariant to swapping JK1 and JK2 when both are otherwise indistinguishable.

The unresolved R1 wildcard semantics concern what a Joker may **represent**, not the detection of the physical Joker object itself.

## Dynamic boolean/status regions

For each chair:

```text
ofc_p{p}_turn
ofc_p{p}_dealer
ofc_p{p}_fantasy        // only after stable evidence exists
```

Global:

```text
ofc_confirm_visible
```

Exactly one `ofc_p{p}_turn` and one dealer region must be true in a stable normal-play observation.

A true `ofc_confirm_visible` is **not** equivalent to canonical `hero_can_confirm`: supplied replay evidence shows the gold Confirm control while an earlier opponent timer is still active. Safe canonical confirmation requires both:

```text
confirm_visible == true
acting_chair == hero_chair
```

until empirical probe U1 proves a stronger supported pre-action behavior.

## Round derivation for normal play

The raw observation derives/cross-checks the normal round from Hero-visible physical-card accounting:

```text
hero_total_dealt =
    face-up Hero cards currently over row source slots
  + loose current Hero cards
  + known Hero discard tracker cards
```

Valid normal-play totals are exactly:

- 5  -> round 0
- 8  -> round 1
- 11 -> round 2
- 14 -> round 3
- 17 -> round 4

This remains invariant when a current card is dragged from the loose area to a row because it is counted exactly once. It is only a normal-Pineapple invariant; Fantasy uses a separate path.

## HU 450x830 evidence geometry

The current full-card visual rectangle inventory is frozen in:

`tablemaps/joker_ultimate_hu_450x830_geometry_v1.json`

The supplied source `.tm` targets a legacy 500x700 layout but contains useful existing rank/suit transform assets. The first runtime `.tm` should reuse those transforms while relocating per-slot regions to the 450x830 evidence geometry.

It is not yet a certified runtime `.tm` because:

- `occupied/back/joker` child regions still need pixel/template calibration on the actual 450x830 client;
- first-round five-loose-card geometry is incomplete;
- Joker face evidence/template is not yet captured;
- Fantasy and 3-player geometry are not yet available.

## Fail-closed requirements

A read-only OFC scrape is invalid if any of the following occurs:

- `ofc_variant` missing/wrong;
- player count not 2 or 3;
- any mandatory occupied/back/joker/rank/suit slot contract missing;
- an occupied slot cannot be classified unambiguously;
- duplicate known standard physical card;
- more than two visible Jokers;
- row face count exceeds 3/5/5 capacity after canonical reconstruction;
- normal visible-card total is not one of 5/8/11/14/17;
- multiple/no acting-chair region in a stable normal-play state;
- multiple/no dealer region;
- previously committed card disappears/moves rows in stateful reconstruction;
- same Hero current card appears simultaneously loose and in a row;
- unsupported face-up opponent discard appears before D1 is resolved.

No failure may fall back to a plausible Hold'em card or betting state.
