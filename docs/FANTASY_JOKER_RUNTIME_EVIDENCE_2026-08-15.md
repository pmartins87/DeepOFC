# KKPoker Joker Ultimate — Fantasy/Joker runtime evidence addendum (2026-08-15)

This addendum is derived directly from the user-supplied `ofc fantasy.zip` replay frames. It replaces several conservative assumptions that were reasonable before visible-Joker/Fantasy evidence existed.

## Evidence chain and hashes

Key frames from `session_1`:

| Frame | SHA256 | What it proves |
|---|---|---|
| `frame000029.bmp` | `7ca75c41c3a34c4d0bc4780ea44c9b44e10d49e3ff6f2e8b2b56da21e842df00` | Hero finishes a normal hand with **KK on Top**, visibly receives the `FANTASY` award. |
| `frame000032.bmp` | `723c94862c6020f838d48938a96403b3f4605e77a36b064c5120135c88884130` | Next Hero Fantasy deal contains **15 visible physical cards** in the curved fan. This directly corroborates KK -> 15-card Fantasy. |
| `frame000052.bmp` | `7ea7ff00bf0c8c0d47b3ce8313e1732c9b2958513f23787eee31b70d3f3a4935` | A 15-card Hero Fantasy fan contains **both physical Jokers simultaneously**, and their faces are visually distinct. |
| `frame000053.bmp` | `bb6232c90019618bb5e172627d03614f97fd6b84a3addea7dcac5c37535f50f5` | Both Jokers are tentatively placed as physical Joker cards; exactly two unused cards remain loose; Confirm is available. |
| `frame000054.bmp` | `a3bd163820c94b409f481727957a4296c4702a10895fc134d349df01bb70b17e` | After Confirm, unused cards are in Hero's discard tracker; confirmed Jokers display as gold nominal cards with persistent color-coded Joker icons; Bottom is a Joker-assisted straight flush; `Fantasy x2` is awarded. |
| `frame000055.bmp` | `e6f7fe547d852e456ca1896334e46605a412140138f2a33be495923968deb2f3` | Clean next-hand Fantasy state; four suit counters show 13/13/13/13 before the new fan appears. |
| `frame000060.bmp` | `05689f26ba0e2d3a3cfa3c25e215f3cae38f1292d8ddede7df2e286d37b9eb99` | The re-Fantasy deal is again **15 cards**. |

## 1. Physical Joker identity is visually persistent — RESOLVED for runtime identity

Before this capture, DeepOFC conservatively treated JK1/JK2 as exchangeable frame-local occurrence labels because no visible Joker face had been supplied.

That assumption is now obsolete for the observed KKPoker client.

`frame000052` shows two visibly different physical Joker faces:

- an **orange/red pineapple Joker**;
- a **gray/black pineapple Joker**.

`frame000053` preserves those distinct faces after both are moved onto Hero's Bottom row.

`frame000054` then re-sorts the confirmed Bottom row and displays the Jokers as nominal substituted cards, but each gold card carries the corresponding small color-coded pineapple icon:

- gray/black Joker displayed as `T♠`;
- orange/red Joker displayed as `8♠`.

Thus the client exposes persistent physical Joker identity across:

`incoming fan -> tentative row placement -> confirmed substituted display`.

DeepOFC runtime identity is therefore frozen as:

```text
JK1 = orange/red physical Joker
JK2 = gray/black physical Joker
```

The numeric names remain implementation labels; their color mapping is now stable and must be recognized by the scraper. Scan-order assignment is no longer acceptable once Joker recognition is calibrated.

### Important scoring distinction

The confirmed gold `T♠`/`8♠` graphics are **displayed wildcard assignments**, not ordinary physical T♠/8♠ cards. Canonical physical state must still store JK2/JK1 respectively. The evaluator may independently derive the legal best wildcard assignment; it must not silently convert the physical Joker into a standard card.

## 2. Fantasy discard UI semantics — RESOLVED

`frame000053` shows a 15-card Fantasy decision after 13 cards have been arranged into 3/5/5. The unused `3♠` and `2♣` remain loose below the board. There is no separate discard-to-trash gesture.

After Confirm (`frame000054`), those two cards appear in Hero's visible discard tracker.

Therefore the observed Fantasy UI contract is:

1. arrange exactly 13 cards into Top/Middle/Bottom;
2. leave the remaining 1–4 cards unplaced;
3. click Confirm;
4. KKPoker automatically converts the unplaced cards into Hero discards.

R10 must **not invent a Fantasy discard drag target** for this client. Its physical gesture plan is 13 placements + Confirm, with unused cards left loose and verified as discards after commit.

This is consistent with the already-modeled normal Pineapple semantics where the one unplaced later-street card is the discard.

## 3. Real 15-card Fantasy entry — independently confirmed

`frame000029` has Hero Top `A♣ K♠ K♥`: the qualifying hand is **KK on Top**.

The subsequent Fantasy fan in `frame000032` contains exactly 15 cards:

```text
A♥ A♣ K♥ J♠ J♦ T♣ 9♠ 9♣ 7♠ 6♠ 6♥ 5♥ 3♠ 3♣ 2♠
```

This directly corroborates the rule transcription:

```text
QQ -> 14
KK -> 15
AA -> 16
trips on Top in Joker Ultimate -> 17
```

Only the KK -> 15 path is newly proven by this specific gameplay sequence; 14/16/17 still require equivalent real-pixel runtime fixtures even though the client rules already state them.

## 4. Bottom-only re-Fantasy path — materially resolved by gameplay

`frame000054` is especially important.

Hero's Top is only:

```text
A♣ K♦ 6♥
```

so Top does **not** independently satisfy QQ/KK/AA/trips Fantasy qualification.

Hero's Bottom is:

```text
J♠  [gray Joker -> T♠]  9♠  [orange Joker -> 8♠]  7♠
```

which KKPoker displays as a straight flush and awards `Fantasy x2`.

The next Fantasy fan (`frame000060`) contains exactly **15 cards**.

Therefore the supplied live client proves at least this exact transition:

```text
current Fantasy deal count = 15
Top does not qualify
Bottom straight flush satisfies quads-or-better stay condition
=> next hand remains Fantasy with 15 cards
```

This closes the empirical uncertainty that a Bottom-only stay might forcibly reset to 14 in Joker Ultimate. It does **not** by itself prove the next count after equivalent Bottom-only stays originating from 14-, 16- or 17-card Fantasy. The engine should preserve this exact proven 15->15 path and remain explicit about the still-unseen counts.

## 5. Two-Joker assignment evidence — partial, not a full wildcard-rule resolution

The same hand proves that both physical Jokers may be used simultaneously in one row and may take **different nominal cards** to form the best hand: T♠ and 8♠ complete J-T-9-8-7 straight flush.

This does **not** resolve:

- whether a Joker may duplicate a nominal standard card already physically present;
- whether both Jokers may ever map to the same nominal card;
- all tie-breaking rules when multiple assignments yield equivalent hand strength.

Those R1 Joker semantic probes remain open.

## 6. R9 scraper consequence

The old single `joker`/scan-order detector contract must evolve. Calibrated runtime slots need to distinguish the two persistent physical identities, including both visual forms:

1. full orange/red or gray/black Joker face while incoming/tentative;
2. small color-coded Joker marker on a confirmed gold substituted card.

Recommended physical slot semantics:

```text
<base>joker1   // orange/red physical Joker
<base>joker2   // gray/black physical Joker
```

If either Joker detector matches, canonical card identity is JK1/JK2 even when rank/suit glyphs are also visible on the confirmed gold card.

## 7. R10 consequence

Fantasy physical execution can now be specified more concretely:

```text
fresh 14..17-card fan scrape
  -> choose exact 13 physical cards
  -> drag each chosen card to canonical row
  -> after every drag, rescrape and re-resolve remaining fan sources
  -> leave unused 1..4 cards loose
  -> verify complete tentative 3/5/5 + correct loose-discard set
  -> Confirm
  -> fresh scrape
  -> verify 13 committed cards + unused cards in Hero discard tracker
```

The real 15-card fan and its two-Joker example are now suitable source material for the first Fantasy pixel/tablemap/runtime golden fixtures.
