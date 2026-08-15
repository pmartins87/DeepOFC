# DeepOFC tablemap contract — Joker Ultimate v2 (normal + Fantasy)

This supersedes v1 for future runtime work. It is the semantic contract between KKPoker's 450x830 Joker Ultimate client and the read-only OpenHoldem OFC scraper/autoplayer calibration.

## One variant, two observation layouts

There is one runtime gate:

```text
s$ofc_variant        joker_ultimate
s$ofc_players        2        // or 3
s$ofc_hero_chair     1
```

Fantasy is **not** a second `ofc_variant`. It is a state/layout within Joker Ultimate. The same tablemap must support both:

- normal Pineapple observation layout;
- Fantasy observation layout.

The scraper derives `fantasy_state` from current evidence/state transition. It must never select Hold'em semantics when `ofc_variant=joker_ultimate`.

## Physical card model

The target deck has 54 physical cards:

- 52 standard rank/suit cards;
- JK1;
- JK2.

Visual JK1/JK2 faces may be indistinguishable. Frame-local occurrence labels are deterministic/exchangeable unless the client exposes stable identity.

## Canonical board source slots

For canonical chair `p`:

```text
ofc_p{p}_top0 ... ofc_p{p}_top2
ofc_p{p}_middle0 ... ofc_p{p}_middle4
ofc_p{p}_bottom0 ... ofc_p{p}_bottom4
ofc_p{p}_discard0 ... ofc_p{p}_discard3
```

Every source slot uses the v1 fail-closed child contract:

```text
<base>empty
<base>back
<base>joker
<base>rank
<base>suit
```

Visual order within a row is non-canonical because KKPoker re-sorts rows. The canonical state stores row membership only.

## Normal Hero incoming cards

Normal loose source slots remain:

```text
ofc_hero_in0 ... ofc_hero_in4
```

A later normal round needs three physical cards; first street needs five. The tablemap may have multiple mutually exclusive source-layout regions if the UI geometry differs by street, but the raw observation must collapse them to one canonical incoming set.

## Fantasy Hero incoming cards

Fantasy uses a curved, overlapped and rotated fan. It must not be modeled as `ofc_hero_in0..16` merely by copying upright normal transforms without validation.

The runtime contract is nevertheless canonical:

```text
fantasy_incoming_physical_cards: unordered set of 14..17 physical cards
```

The tablemap/scraper implementation may expose orientation/layout-specific source slots, for example:

```text
ofc_fantasy_in14_00 ... ofc_fantasy_in14_13
ofc_fantasy_in15_00 ... ofc_fantasy_in15_14
ofc_fantasy_in16_00 ... ofc_fantasy_in16_15
ofc_fantasy_in17_00 ... ofc_fantasy_in17_16
```

or a more compact shared geometry if real-image tests prove it reliable. These names are **visual source identifiers only**; fan order is never strategic state.

Each fan card must be identified exactly as one of the 54 physical cards. If card overlap/rotation prevents deterministic rank+suit/Joker recognition, the observation is invalid. No card may be guessed from the four suit counters.

### Transform acceptance gate for the fan

Before runtime support is claimed, test the donor T1/T5 card transforms on real Fantasy frames at every fan angle. If any slot orientation is unreliable, use one of:

- orientation-specific rank/suit transforms;
- orientation-specific image/hash/template classifiers;
- another deterministic recognition path with frozen replay tests.

The chosen path must produce exact card identities over representative 14/15/16/17 layouts.

## Fantasy state indicator

Preferred independent signal(s) should be calibrated from the new capture, such as the persistent bottom `FANTASY` arc/banner or equivalent stable visual element:

```text
ofc_fantasy_visible
```

This is a state/layout hint, not sufficient by itself to create a valid Fantasy observation. The card-count/state transition must also be consistent.

## Unknown-suit counters — consistency only

The Fantasy capture shows four left-side counters, one per standard suit. At a clean pre-deal Fantasy frame they show 13 each.

Optional regions:

```text
ofc_unknown_spades
ofc_unknown_hearts
ofc_unknown_clubs
ofc_unknown_diamonds
```

These counters may be used to reject an inconsistent scrape. They do not encode Jokers and may not be used to infer missing exact card identities.

A future invariant may compare the counters with the number of standard cards known to Hero, but only after frame-by-frame semantics are validated against the capture.

## Actor / dealer / Confirm

For each chair:

```text
ofc_p{p}_turn
ofc_p{p}_dealer
```

Global:

```text
ofc_confirm_visible
ofc_fantasy_visible
```

Canonical safety remains:

```text
hero_can_confirm = confirm_visible && acting_chair == hero_chair
```

unless explicit evidence proves safe queued-confirm behavior.

Fantasy may hide/rearrange timer/turn controls; that geometry must be calibrated rather than inherited blindly from normal play.

## R10 drag/drop target contract

Source-card recognition regions and destination/drop regions are separate concepts.

For each canonical row, R10 must eventually have a calibrated **drop target** that remains safe regardless of KKPoker's post-drop within-row resorting:

```text
ofc_drop_top
ofc_drop_middle
ofc_drop_bottom
```

A drop target should be chosen in a stable interior area accepted by the client, not on an existing card corner where overlap could change behavior.

### Hard calibration authorization gate

The existence of those three regions is **not** permission to move the mouse. Every tablemap also carries:

```text
s$ofc_drag_targets_calibrated   0
```

Semantics:

- `0` — replay/draft/guessed geometry. R10 must refuse to build or execute a physical placement step even if `ofc_drop_*` rectangles exist.
- `1` — all supported row targets have been deliberately calibrated against the real KKPoker client and have passed the frozen sandbox/runtime acceptance tests.

Generated replay drafts always write `0`. Changing this value to `1` is a deliberate certification event, not an automatic consequence of adding regions. `COFCActionPlanner` fails closed unless the value is exactly `1`.

Fantasy unused-card discard behavior requires its own calibrated target/gesture contract after observing the UI. If cards are discarded implicitly by leaving them out before Confirm, R10 must verify that behavior rather than inventing a drag-to-trash gesture.

The action loop is always transactional:

1. locate exact physical source card;
2. verify the active tablemap has explicitly certified drag targets;
3. mouse-down;
4. drag through safe path;
5. mouse-up in intended row target;
6. rescrape;
7. verify the physical card is now tentatively/committed in the intended canonical row;
8. continue only on exact match.

Confirm is clicked only after the complete intended placement/discard set has been verified.

## Normal round derivation

When `fantasy_state=false`:

```text
hero_total_dealt =
    Hero face cards over row source slots
  + loose Hero current cards
  + known Hero discard tracker cards
```

Valid totals:

- 5 -> round 0
- 8 -> round 1
- 11 -> round 2
- 14 -> round 3
- 17 -> round 4

When `fantasy_state=true`, this invariant must not be used to infer a normal round. Fantasy has a one-shot 14–17-card private set and its own reconstruction path.

## Fail-closed requirements

A Joker Ultimate scrape/action plan is invalid if, among other things:

- variant gate missing/wrong;
- player count unsupported;
- mandatory slot child missing;
- a non-empty source slot cannot be classified unambiguously;
- duplicate known standard physical card;
- more than two visible Joker occurrences;
- same Hero physical card appears in two source locations;
- normal total is impossible while in normal state;
- Fantasy incoming count/layout is inconsistent with the derived Fantasy state;
- Fantasy fan contains an unrecognized/ambiguous card;
- committed card disappears or moves canonical rows;
- actor/dealer state is contradictory where required;
- a physical placement is requested while `s$ofc_drag_targets_calibrated != 1`;
- post-drag rescrape does not exactly match the requested canonical transition.

No failure may fall back to plausible Hold'em state, a guessed OFC card, or an uncertified drag target.

## Acceptance gates

### R9 tablemap/scraper

Representative normal **and Fantasy** replay pixels must pass:

```text
BMP pixels
  -> tablemap transforms
  -> COFCVisualObservation
  -> COFCReconstructor
  -> versioned canonical snapshot
  == independent DeepOFC Python reference
```

### R10 physical UI actions

A sandbox/replay harness must prove normal and Fantasy source-card selection, drag/drop placement, discard semantics and Confirm with exact post-action canonical verification before the hard R9 read-only guard is removed. Only after the row-target calibration tests pass may the certified runtime tablemap set `s$ofc_drag_targets_calibrated = 1`.
