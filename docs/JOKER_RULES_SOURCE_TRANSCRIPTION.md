# KKPoker OFC Joker — source transcription and locked facts

This document is derived only from the supplied `joker_ofc_frames_and_rules.zip` screenshots. It deliberately separates what the screenshots prove from what still needs confirmation.

## Modes shown by KKPoker

The Advanced Play screen states that four OFC modes are available:

- Regular
- Progressive
- Ultimate
- Joker

### Progressive

After entering Fantasy with the top row consisting of QQ, KK or AA, players receive **14, 15 or 16 cards respectively**, but receive only **14 cards if they re-enter Fantasy**.

### Ultimate

Ultimate uses the same rules as Progressive, except that when players enter re-Fantasy, the number of cards dealt is the same as for Fantasy rather than being fixed at 14.

### Joker

The two Jokers can represent any other playing card to form the strongest hand, provided the resulting board is not fouled.

### 17-card Fantasy

The supplied rule screen states that in **Ultimate mode with Jokers**, players can receive **17 cards for entering Fantasy with trips in the top row**.

> Open item: the screenshots do not, by themselves, state in one unambiguous sentence whether KKPoker's menu item named `Joker` is exactly `Ultimate + two Jokers` for every Fantasy/re-Fantasy rule. We must not silently assume this. It is an R1 validation item.

## Basic card flow

The How To Play screens state:

- Regular OFC uses a 52-card deck without Jokers.
- Cards are shuffled every hand.
- One random player is chosen as Dealer (BTN).
- The player to the left of BTN, UTG, acts first and action moves clockwise.
- There are **five rounds** in each OFC hand.
- First round: **5 cards** are dealt to each player.
- Each subsequent round: **3 cards** are dealt to each player.
- Cards are dealt clockwise; BTN receives cards last each round.
- All five first-round cards must be used.
- On every later round, **two of the three cards must be placed and one discarded**.
- Discarded cards can be found in KKPoker's Card Tracker.
- Once all 13 cards are set, valid boards score by comparing corresponding rows.
- The dealer button moves clockwise after the hand.

For the hero this makes discarded cards known information. Opponent discarded cards are not proven visible in normal play by the supplied frames and therefore must initially be treated as hidden unless later evidence proves otherwise.

## Board structure and foul

Each completed board contains:

- Top: 3 cards
- Middle: 5 cards
- Bottom: 5 cards

The source explicitly says:

- on the top row, only **high card, pair and three of a kind** are valid hand types;
- the strongest possible top row is AAA;
- Bottom must be **stronger than or equal to** Middle;
- Middle must be **stronger than or equal to** Top;
- if this ordering is violated, the hand is fouled;
- a fouled hand forfeits all royalties;
- a fouled hand loses all three rows to any valid hand and is scooped.

The comparison convention for a 3-card top versus a 5-card middle is therefore part of the game engine contract and must be implemented exactly, including the `equal` wording above.

## Fantasyland

The supplied rules state:

- a valid hand with **QQ or better in the top row** enters Fantasy on the next hand;
- in Fantasy the player receives **14 to 17 cards at once**, depending on game mode and top-row hand type;
- the player builds the 13-card 3/5/5 board from those cards and discards the unused card(s);
- to remain in Fantasy, the Fantasy hand must satisfy at least one of:
  1. trips in the top row;
  2. quads or better in the bottom row.

## Scoring

Each row is scored separately.

- Winner of a row: **+1 point**.
- Winning all three rows is a scoop and awards an additional **+3 bonus points**.
- Thus a clean 3-row win is 6 base points before royalty differences.
- Total points are computed from row scores, royalty differences, and scoop bonus.
- KKPoker states: `Player's profit = total points × blind`.

The scoring screen describes pairwise scoring order for a three-player table:

1. UTG scores against MP;
2. UTG scores against BTN;
3. MP scores against BTN.

It also states that the maximum funds a player can win or lose is limited by the amount the player had on the table at the start of the hand, with a win-cap adjustment when a losing player cannot fully pay.

> Open item: exact cap redistribution needs a deterministic worked example before the economy/settlement engine can be frozen.

## Royalties

### Top row

| Hand | Royalty |
|---|---:|
| 66 | 1 |
| 77 | 2 |
| 88 | 3 |
| 99 | 4 |
| TT | 5 |
| JJ | 6 |
| QQ | 7 |
| KK | 8 |
| AA | 9 |
| 222 | 10 |
| 333 | 11 |
| 444 | 12 |
| 555 | 13 |
| 666 | 14 |
| 777 | 15 |
| 888 | 16 |
| 999 | 17 |
| TTT | 18 |
| JJJ | 19 |
| QQQ | 20 |
| KKK | 21 |
| AAA | 22 |

### Middle row

| Hand | Royalty |
|---|---:|
| Trips | 2 |
| Straight | 4 |
| Flush | 8 |
| Full house | 12 |
| Quads | 20 |
| Straight flush | 30 |
| Royal flush | 50 |

### Bottom row

| Hand | Royalty |
|---|---:|
| Straight | 2 |
| Flush | 4 |
| Full house | 6 |
| Quads | 10 |
| Straight flush | 15 |
| Royal flush | 25 |

## Sitting out

The rules state that a player is forced to sit out after taking no action for two rounds. If still sitting out when the hand ends, the player is removed from the table. While sitting out, cards are selected and set automatically.

## Evidence from supplied replay frames

The replay HTML identifies itself as `OFC 10¢` and OpenHoldem 14.0.2.0. Its standard Hold'em state table still shows four generic chairs, while the OFC game screenshots visibly use the 3/5/5 board layout and a `Confirm` placement workflow. This is one reason the normal OpenHoldem chair/card model cannot be treated as the canonical OFC state.

## R1 unresolved list

Before `R1` can pass, we still need source-backed answers for:

1. Is KKPoker `Joker` exactly Ultimate rules plus two Jokers, including 17-card trips Fantasy and Ultimate re-Fantasy card counts?
2. Exact Joker substitution restrictions and tie-breaking if more than one wildcard assignment yields the same hand class.
3. Whether two Jokers may represent the same nominal card/rank/suit when that would otherwise imply duplicate physical cards.
4. Exact supported player counts for the Joker tables and whether scoring order/caps change heads-up.
5. Exact financial win-cap redistribution algorithm.
6. Exact rake trigger, cap, and attribution for the Joker OFC stake we will automate; this belongs in the economy layer, not raw point scoring.
7. Whether opponent discards are ever observable during a live hand via Card Tracker, and if so whether using that UI is operationally legal/available before the hand finishes.
