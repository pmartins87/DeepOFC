# KKPoker OFC Joker Ultimate — source transcription and frozen facts

This document is the R1 rules contract for DeepOFC. It combines:

1. the supplied KKPoker in-client rule/replay evidence (`joker_ofc_frames_and_rules.zip`), and
2. an official KKPoker website cross-check performed on 2026-08-14.

The in-client rules are treated as the most specific source for the exact live variant observed. The public website is used to corroborate base OFC rules and current economics. Ambiguities remain explicit; they are never silently guessed.

## Target variant identity — RESOLVED

The gameplay frames supplied for this project visibly label the table:

`Joker Ultimate GPS/IP`

and

`$20 JOKER Blinds: 10¢`

The Advanced Play screen states that OFC has Regular, Progressive, Ultimate and Joker features; it further states that **Ultimate mode with Jokers** enables 17-card Fantasy for trips on top.

Therefore DeepOFC is now scoped to the concrete product observed in the replay:

**KKPoker OFC Joker Ultimate**

We are no longer treating the target as an unspecified generic `Joker` mode.

## Official KKPoker website cross-check — 2026-08-14

Official pages checked:

- https://kkpoker.net/how-to-play/open-face-chinese-poker-ofc/
- https://br.kkpoker.net/gamerules/
- https://kkpoker.net/how-to-play/rake-information/
- https://br.kkpoker.net/how-to-play/instant-rakeback-explain/

The public OFC guide and game-rules page corroborate the normal Pineapple flow:

- 13-card 3/5/5 board;
- five rounds;
- five cards initially;
- three cards on later rounds, place two and discard one;
- action begins to the left of BTN and proceeds clockwise;
- QQ or better on top enters Fantasy if the board is valid;
- Fantasy deals 14–17 cards and the player sets 13 at once;
- re-Fantasy condition is trips on top or quads-or-better on bottom;
- one point per row and +3 for a scoop.

The public website is generic OFC documentation and still describes a standard 52-card deck. It does **not** publish the advanced Joker/Ultimate details visible in the current client. Therefore the website does not override the in-client Joker Ultimate rules.

The public rake page currently states for OFC:

- stakes/ante units listed from $0.01 to $2;
- rake = 5%;
- cap = 2 BB;
- no rake when the pot is <= 5 BB.

The public Instant Rakeback page states that OFC is eligible and the system starts at 5% and can reach 50%. Rakeback/PVI belong to the economics layer, not to raw point scoring.

## Deck and modes

### Regular / base OFC

The in-client Basic Play screen says Regular OFC uses a 52-card deck without Jokers.

### Progressive

After entering Fantasy with top QQ, KK or AA, the player receives respectively:

- QQ -> 14 cards
- KK -> 15 cards
- AA -> 16 cards

In Progressive, re-Fantasy receives 14 cards.

### Ultimate

Ultimate follows Progressive rules except that re-Fantasy does not automatically drop to 14; the number dealt follows the Fantasy-card-count rule instead.

### Joker

The in-client Advanced Play screen states:

- there are two physical Jokers;
- a Joker can represent another playing card to form the strongest hand;
- the resulting board must remain non-fouled.

### 17-card Fantasy

The same screen explicitly states that **in Ultimate mode with Jokers**, a player can receive **17 cards** for entering Fantasy with trips in the top row.

This applies directly to the DeepOFC target because the actual replay table is labelled `Joker Ultimate`.

## Player counts — RESOLVED for the engine scope

The supplied gameplay is heads-up, proving 2-player Joker Ultimate exists.

The in-client scoring rules explicitly describe a 3-player settlement order using UTG, MP and BTN, proving 3-player OFC exists.

Normal Pineapple flow deals 17 physical cards per non-Fantasy player across the five rounds (5 + 3 + 3 + 3 + 3). A 52-card regular deck supports at most three such players; the Joker Ultimate deck adds two Jokers but still cannot support four players under this flow.

DeepOFC therefore freezes supported normal-table player counts as:

**2 or 3 players**

Any future evidence of a different KKPoker deal mechanism must deliberately revise this contract.

## Basic card flow

- Cards are shuffled every hand.
- One player is BTN/dealer.
- The player immediately left of BTN acts first; action proceeds clockwise.
- There are five normal rounds.
- Round 1: five cards; all five must be placed.
- Rounds 2–5: three cards; exactly two are placed and one is discarded.
- Once a placement turn is confirmed, previously set cards cannot be moved between rows.
- Hero's own discarded-card identities are known information.
- Opponent discarded-card identities are not shown in the supplied live frames; only card backs/count are visible.

### Important UI observation from supplied frames

KKPoker allows Hero to **pre-arrange** current cards while an opponent is still the acting player. The strategic action is not committed until Hero's turn/Confirm.

The replay also proves that KKPoker **auto-sorts cards within a row after confirmation**. Therefore visual slot order inside a row is not persistent strategic state. DeepOFC canonicalizes row membership; the OpenHoldem scraper may read fixed screen slots but must normalize them to row card sets.

## Board structure and foul — RESOLVED

Each completed board contains:

- Top: 3 cards
- Middle: 5 cards
- Bottom: 5 cards

The in-client Basic Play screen is explicit:

- top supports only high card, pair and trips;
- strongest possible top is AAA;
- **Bottom must be stronger than or equal to Middle**;
- **Middle must be stronger than or equal to Top**;
- otherwise the board is fouled;
- a fouled board forfeits all royalties;
- a fouled board loses all three rows to any valid opponent and is scooped.

The public website uses looser wording such as `outrank`/`higher`, but the current client explicitly includes equality. DeepOFC therefore follows the in-client rule: **equality is legal for foul ordering**.

The exact cross-size comparison contract (3-card Top vs 5-card Middle) will be implemented in R2 and frozen by golden tests.

## Fantasyland

Base entry:

- valid Top QQ or better enters Fantasy on the next hand.

Fantasy behavior:

- player receives 14–17 cards depending on the applicable mode/qualifier;
- chooses 13 cards for the 3/5/5 board at once;
- unused cards are discarded;
- Fantasy board remains hidden until standard OFC players finish.

Stay in Fantasy if the Fantasy board has at least one of:

1. trips on Top;
2. quads or better on Bottom.

### Remaining Fantasy ambiguity

The source is sufficient for 14/15/16 initial Progressive entry and 17-card trips entry in Joker Ultimate. It is **not yet fully explicit for every re-Fantasy path**, especially a re-Fantasy triggered only by Bottom quads-or-better when Top itself does not independently map to QQ/KK/AA/trips.

This remains an R1 validation item. The engine must not invent a card count for that path.

## Scoring

Each player pair is scored independently.

- row win: +1 point;
- row loss: -1 point;
- row tie: 0;
- win all three rows: +3 scoop bonus;
- lose all three rows: -3 scoop bonus;
- royalties are compared as a difference between players;
- player's profit = total points x blind/point value.

The in-client formula is:

`total points = score of each row + royalties difference + scoop bonus (if any)`

## Royalties — FROZEN

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

The same royalty table is also published as an image on the official KKPoker OFC webpage.

## Three-player settlement and win cap

The in-client Scoring screen freezes the pairwise scoring order for a 3-player table:

1. UTG vs MP;
2. UTG vs BTN;
3. MP vs BTN.

It also states:

- maximum funds a player can win or lose are capped at that player's funds at the **start of the hand**;
- if a player cannot pay in full, the winner and the next player in the scoring order may bear the gap as the win cap is applied.

This proves that settlement is order-dependent when caps bind.

### Remaining settlement ambiguity

The screen does not provide a numeric worked example. Before R2 settlement can be certified, we still need to validate the exact transfer/clamping algorithm against a real capped hand or another source-backed example.

## Economics

Raw strategy/scoring and site economics are separate layers.

Current official public OFC rake information (checked 2026-08-14):

- rake: 5%;
- cap: 2 BB;
- no rake if pot <= 5 BB;
- published OFC stake units: $0.01, $0.02, $0.05, $0.10, $0.20, $0.50, $1, $2.

The supplied live table is labelled `$20 JOKER Blinds: 10¢`; its point/blind value is therefore captured separately from the player's stack cap.

Exact rake attribution and how `pot` is defined for OFC settlement must be validated before the bankroll/EV layer is certified.

## Sitting out

The client states:

- no action for two rounds forces sit-out;
- if still sitting out when the hand ends, the player is removed;
- while sitting out, cards are selected/set automatically.

## R1 unresolved list after website cross-check

Resolved in this pass:

- target product identity is `Joker Ultimate`;
- supported player counts for DeepOFC are 2–3;
- equality is legal in Bottom >= Middle >= Top foul ordering;
- base OFC rake headline is 5%, cap 2 BB, no rake at pot <= 5 BB;
- row visual slot identity is not strategic state;
- Hero can pre-arrange before Hero is the acting player.

Still unresolved before R1 can PASS:

1. Exact Joker wildcard uniqueness rules: may two Jokers map to the same nominal card, and may a Joker duplicate a physical standard card already present?
2. Exact tie-breaking/wildcard assignment rule if multiple Joker substitutions produce equivalent best hand ranks.
3. Exact Joker Ultimate re-Fantasy card count for every stay condition, especially Bottom-quads-only re-Fantasy.
4. Exact financial win-cap transfer/clamping algorithm under a concrete insufficient-funds example.
5. Exact OFC rake `pot` definition and attribution for the KKPoker Joker Ultimate cash game.
6. Whether opponent discard identities can ever become legally observable during a live hand before settlement; current replay evidence shows only hidden backs/count.
