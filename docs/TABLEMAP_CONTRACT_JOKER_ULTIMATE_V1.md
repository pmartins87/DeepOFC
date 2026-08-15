# DeepOFC tablemap contract — Joker Ultimate v1

This is the semantic contract between the KKPoker tablemap and the read-only OpenHoldem OFC scraper. It is not a complete `.tm` file.

## Mandatory tablemap symbols

```text
s$ofc_variant        joker_ultimate
s$ofc_players        2        // or 3
s$ofc_hero_chair     1        // canonical chair mapped to the local/bottom seat
```

OpenHoldem branch `deepofc` now exposes `CTablemap::SupportsOFCJokerUltimate()`, which returns true **only** when `ofc_variant=joker_ultimate`. A title containing `OFC` is not enough to activate OFC semantics.

## Card-area naming

Each area is intended for AutoOCR/template detection and may return multiple card labels. Standard card labels use the existing OpenHoldem card representation; Joker templates must return distinct physical labels `JK1` and `JK2` (or another frozen pair translated losslessly to physical Joker IDs 52/53).

For each canonical chair `p`:

```text
area_ofc_p{p}_top
area_ofc_p{p}_middle
area_ofc_p{p}_bottom
area_ofc_p{p}_discards
```

The first three areas may contain:

- committed face-up cards;
- for Hero, tentative current cards dragged over that row;
- for an opponent currently acting, hidden card backs visually overlapping row space.

The scraper therefore must classify detections by type:

- standard/Joker face -> raw visual row card;
- card back in row area -> `hidden_incoming_count`, never a row destination;
- card back in discard area -> `hidden_discard_count`;
- no card -> ignored.

## Hero current cards

Normal Pineapple loose cards:

```text
area_ofc_hero_incoming
```

The same current-street physical card may be either:

- detected in `area_ofc_hero_incoming`, or
- detected as a face card over a Hero row because it was pre-arranged.

It must never be accepted in both locations in the same raw observation.

Fantasy requires a separate geometry path because 14–17 incoming cards are displayed differently. No Fantasy geometry is considered supported until representative KKPoker frames are captured.

## Hero discard tracker

```text
area_ofc_hero_discards
```

Hero discarded cards are face-up/known to Hero in supplied evidence and should be returned as physical card identities.

Opponent discard identities remain hidden unless later probe D1 proves otherwise.

## Dynamic boolean/status regions

For each chair:

```text
ofc_p{p}_turn
ofc_p{p}_dealer
ofc_p{p}_fantasy        // when stable visual evidence exists
```

Global:

```text
ofc_confirm_visible
```

Exactly one `ofc_p{p}_turn` should be true in a stable normal-play observation. Exactly one dealer marker should be true.

A true `ofc_confirm_visible` is **not** equivalent to canonical `hero_can_confirm`: supplied replay evidence shows the gold Confirm control while an earlier opponent timer is still active. Safe canonical confirmation requires both:

```text
confirm_visible == true
acting_chair == hero_chair
```

until empirical probe U1 proves a stronger supported pre-action behavior.

## Round derivation for normal play

The raw observation can cross-check the normal round from Hero-visible physical-card accounting:

```text
hero_total_dealt =
    visual Hero row faces
  + loose current Hero faces
  + known Hero discard tracker faces

round_index = (hero_total_dealt - 5) / 3
```

Valid normal-play totals are exactly:

- 5  -> round 0
- 8  -> round 1
- 11 -> round 2
- 14 -> round 3
- 17 -> round 4

This works even when current cards are tentatively moved from the loose-card area into a row, because they remain counted exactly once. It is only a normal-Pineapple invariant; Fantasy uses a separate path.

## HU 450x830 evidence geometry

The current visual rectangle inventory is frozen in:

`tablemaps/joker_ultimate_hu_450x830_geometry_v1.json`

It is evidence-only and not yet a runtime `.tm` because:

- the supplied `.tm` targets a legacy 500x700 layout;
- it contains inherited Hold'em/AoF regions;
- current 450x830 OFC geometry differs;
- Joker face templates are not yet captured;
- Fantasy and 3-player geometry are not yet available.

## Fail-closed requirements

A read-only OFC scrape is invalid if any of the following occurs:

- `ofc_variant` missing/wrong;
- player count not 2 or 3;
- required row areas missing;
- duplicate known physical card;
- more than two physical Jokers;
- row face count exceeds 3/5/5 capacity after canonical reconstruction;
- normal visible-card total is not one of 5/8/11/14/17;
- multiple acting-chair regions are true;
- no acting chair is identifiable in a state that is supposed to be actionable;
- previously committed card disappears/moves rows in stateful reconstruction;
- same Hero current card appears simultaneously loose and in a row;
- any Joker detector output is ambiguous between JK1/JK2.

No failure may fall back to a plausible Hold'em card or betting state.
