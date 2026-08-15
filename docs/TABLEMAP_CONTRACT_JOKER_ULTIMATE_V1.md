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

Every possible visual card slot has a base name and five children:

```text
<base>empty
<base>back
<base>joker
<base>rank
<base>suit
```

Semantics:

- `empty`: mandatory boolean/color region matching the known empty green background for that source slot;
- `back`: mandatory boolean region distinguishing a hidden card back when the slot is not empty;
- `joker`: mandatory boolean/template region distinguishing a Joker face;
- `rank` / `suit`: standard OpenHoldem rank/suit transforms for a normal face-up card.

The negative/background gate is deliberate: a standard white face and a yellow card back do not share one reliable positive `occupied` color. If `empty=false` but the slot cannot be classified as back, Joker or a valid standard rank+suit pair, the scrape is **invalid**. An OCR miss is never silently converted into an empty slot.

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
ofc_p0_top0empty
ofc_p0_top0back
ofc_p0_top0joker
ofc_p0_top0rank
ofc_p0_top0suit
```

Board-source slots may visually contain committed cards, tentative Hero cards, or hidden opponent incoming backs. A back in a board-source slot increments `hidden_incoming_count`; it is never interpreted as a future row destination.

Opponent discard slots are count-only until R1 probe D1 proves face identities can be valid live information.

## Hero current cards and discards

Normal loose-card source slots:

```text
ofc_hero_in0 ... ofc_hero_in4
```

Hero discard source slots:

```text
ofc_hero_discard0 ... ofc_hero_discard3
```

Each uses the same `empty/back/joker/rank/suit` contract. The same current Hero card must never be accepted simultaneously loose and tentatively over a row.

Fantasy needs a separate geometry path for 14–17 incoming cards and is not yet runtime-supported.

## Joker detection and identity

The two Joker faces may be visually indistinguishable. The scraper therefore uses a per-slot Joker classifier and assigns frame-local JK1/JK2 occurrence labels in deterministic scan order. Those labels are exchangeable occurrence labels, not proof that the KKPoker client exposes persistent Joker identity.

Current replay evidence contains no visible Joker face, so the generated replay-draft tablemap intentionally carries an uncalibrated Joker placeholder. If a Joker appears before calibration, standard rank/suit parsing must fail and invalidate the scrape.

## Dynamic status regions

For each chair:

```text
ofc_p{p}_turn
ofc_p{p}_dealer
```

Global:

```text
ofc_confirm_visible
```

Exactly one actor and one dealer must be identified in a stable normal state. Visible Confirm is not sufficient to authorize a strategy action; supplied frames show it while an earlier opponent timer is active. Canonical safety remains:

```text
hero_can_confirm = confirm_visible && acting_chair == hero_chair
```

until probe U1 proves otherwise.

## Normal-round derivation

```text
hero_total_dealt =
    Hero face cards currently over row source slots
  + loose Hero current cards
  + known Hero discard tracker cards
```

Valid totals:

- 5 -> round 0
- 8 -> round 1
- 11 -> round 2
- 14 -> round 3
- 17 -> round 4

This remains invariant during tentative drag placement because each physical card is counted exactly once.

## HU 450x830 evidence and reproducible generator

Geometry:

`tablemaps/joker_ultimate_hu_450x830_geometry_v1.json`

Replay color/slot calibration:

`tablemaps/joker_ultimate_hu_450x830_calibration_v1.json`

Generator:

`tools/build_joker_hu_tablemap.py`

Verifier:

`deepofc/tablemap_verify.py`

The generator takes the supplied legacy `.tm` as the font/transform donor and produces a deterministic 450x830 **replay-draft** with explicit `ofc_*` regions. The verifier requires the correct target size, OFC symbols and every mandatory HU replay region.

The draft is not a certified live tablemap because:

- the P0 dealer pixel is predicted, not yet observed in supplied evidence;
- first-round five-loose-card geometry is incomplete (the supplied first-round frame already has all five cards pre-arranged);
- Joker face calibration is absent;
- Fantasy and 3-player geometry are absent;
- a Windows/OpenHoldem replay build has not yet validated the regions.

## Fail-closed requirements

A read-only OFC scrape is invalid if, among other things:

- `ofc_variant` missing/wrong;
- player count not 2 or 3;
- mandatory `empty/back/joker/rank/suit` slot child missing;
- `empty=false` but no unambiguous back/Joker/standard face exists;
- duplicate known standard physical card;
- more than two visible Jokers;
- invalid normal total outside 5/8/11/14/17;
- multiple/no actor or dealer;
- committed card disappears/moves rows in reconstruction;
- same Hero current card appears loose and in a row;
- face-up opponent discard appears before D1 is resolved.

No failure may fall back to plausible Hold'em state.
