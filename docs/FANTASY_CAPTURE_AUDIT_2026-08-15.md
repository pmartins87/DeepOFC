# KKPoker Joker Ultimate Fantasy capture audit — 2026-08-15

This note records the new user-supplied replay package `ofc fantasy.zip` and freezes only what is directly supported by the capture plus already-frozen in-client rules.

## Source inventory

- package: `ofc fantasy.zip`
- SHA256: `1b91e038bb42acee2520187907d9ef9d6f34fc303d065ac2bc5dd1e92d52027e`
- client geometry: 450 x 830
- `session_0`: 19 BMP frames + matching HTML snapshots
- `session_1`: 65 BMP frames + matching HTML snapshots
- total: 84 BMP frames + 84 HTML snapshots

The original binary package remains external evidence; this repository records its immutable hash and derived conclusions.

## Variant identity — strengthened by direct UI evidence

The capture shows the same table transitioning between ordinary Pineapple play and Fantasy without changing product/table identity.

In `session_1/frame000000`, the KKPoker **Table Info** panel visibly states:

- `Game Mode: Ultimate`
- `Joker: Yes`
- `Max Player: 2`

The table itself is labelled `Joker Ultimate GPS/IP` during normal play and remains that table when the UI enters the large `FANTASY` layout.

Therefore DeepOFC must model this as **one target variant**:

`KKPoker OFC Joker Ultimate`

with Fantasy as a hand/state inside that variant. `Ultimate`, `Joker`, progressive Fantasy card counts and the 17-card Fantasy feature are not independent runtime games for this project.

There must be no separate OpenHoldem `ofc_variant=fantasy` tablemap gate. The gate remains:

`ofc_variant=joker_ultimate`

and the scraper derives `fantasy_state` from the current observation/state transition.

## Physical deck size — frozen at 54 cards

The already-transcribed in-client rules state:

- Regular/base OFC uses 52 standard suited cards;
- Joker play adds **two physical Jokers**.

The new Fantasy capture independently exposes a useful sanity signal. At a clean Fantasy transition (`session_1/frame000055`) the left card tracker displays `13` unknown cards for each of the four suits before the Fantasy fan is dealt/recognized.

That establishes that the four suit counters account for the ordinary 52-card component (`13 x 4`). Jokers are suitless and therefore are not represented by those four counters.

Combined with the already-frozen two-physical-Joker rule, the DeepOFC Joker Ultimate physical deck is therefore:

**52 standard cards + JK1 + JK2 = 54 physical cards.**

The suit counters alone would not prove the Joker count; the 54-card conclusion uses both pieces of evidence.

## Fantasy UI observations relevant to R9/R10

The capture provides geometry that was previously missing:

1. Fantasy transition/splash inside the same 450x830 table.
2. Hero Fantasy incoming cards are displayed as a curved/overlapping fan near the bottom of the client.
3. The fan may contain 14–17 cards depending on the qualification path; the existing rule contract remains authoritative for the exact deal count.
4. Hero still builds the same canonical 3/5/5 board.
5. Opponent board/card-back geometry remains in the upper portion of the same client.
6. The gold Confirm control remains part of the placement flow.
7. Two orange row-action controls appear on the right during Fantasy arrangement; their exact semantics must be classified before automation.
8. The left card tracker exposes four per-suit unknown-card counters. These are valuable as a **sanity/cross-check signal**, not as a substitute for identifying Hero's exact private cards.
9. Rank/Suits controls are visible in the Fantasy layout and may change the presentation/order of the fan. Runtime must not depend on fan ordering as strategic state.

## Tablemap consequence

The HU tablemap contract must now cover both normal and Fantasy observations under one `joker_ultimate` variant.

At minimum, Fantasy support requires:

- detection/derivation of Fantasy state;
- visual access to up to 17 Hero incoming cards;
- exact card identity despite curved/rotated/overlapping fan presentation;
- unchanged canonical board row regions;
- Confirm visibility/readiness;
- calibrated row drop targets for the future R10 drag-and-drop autoplayer;
- discard semantics for the unused Fantasy cards;
- optional suit-counter regions for fail-closed consistency checks.

A key engineering warning follows from the screenshots: the Fantasy fan is not a simple extension of the three upright normal incoming-card rectangles. The cards are overlapped and rotated. We must validate whether standard OpenHoldem T1/T5 rank/suit transforms remain reliable at those fan angles. If they do not, Fantasy needs orientation-specific transforms/templates or another deterministic scraper path. We must not mark Fantasy tablemap support complete merely because approximate fan rectangles exist.

## Canonical-state consequence

Fantasy is not five normal rounds. At the strategy/state layer a Fantasy hand must expose:

- `fantasy_state = true`;
- deal count 14–17 as determined by the frozen qualification rule;
- all Hero Fantasy incoming physical cards as one private set;
- one-shot construction of a 13-card 3/5/5 board;
- all unused physical cards as Hero-known discards;
- board hidden from ordinary opponents until reveal, where applicable;
- re-Fantasy qualification state for the next hand.

The normal-round invariant `hero_total_dealt in {5,8,11,14,17}` must **not** be used to infer a normal round while `fantasy_state=true`.

## New acceptance requirements

R9 cannot PASS until at least one representative Fantasy sequence is replayed through:

`pixels -> tablemap -> raw OFC observation -> canonical C++ state -> DeepOFC reference`

and agrees exactly.

R10 cannot PASS until the sandbox/replay action layer proves the complete Fantasy gesture sequence, including selecting/dragging the intended physical card, dropping it on the intended canonical row, discarding the correct unused cards, Confirm, and post-action state verification.
