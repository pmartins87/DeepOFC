# Official KKPoker verification — 2026-08-14

This document records what was verified on the current official KKPoker website after reviewing the supplied in-client Joker OFC rule frames.

## Official pages checked

- `https://kkpoker.net/gamerules/`
- `https://kkpoker.net/how-to-play/open-face-chinese-poker-ofc/`
- `https://kkpoker.net/how-to-play/rake-information/`
- Portuguese localized equivalents under `br.kkpoker.net`

The public website is treated as authoritative for the facts it actually states. The supplied in-client Joker rule screens remain stronger evidence for Joker-specific Advanced Play details that are not present on the public pages.

## Confirmed by both client evidence and official public site

The public KKPoker rules confirm:

- standard OFC uses 52 cards;
- each player builds 13 cards as Top 3 / Middle 5 / Bottom 5;
- Top may contain only high card, pair or trips;
- five rounds are played;
- first round deals five cards and all five are placed;
- later rounds deal three cards, two are placed and one is discarded;
- action begins left of BTN and proceeds clockwise to BTN;
- placed cards cannot be changed after the player's turn concludes;
- QQ or better in Top, without foul, enters Fantasy;
- Fantasy deals 14 to 17 cards and the player sets 13 at once;
- Fantasy remains hidden until standard players finish;
- re-Fantasy requires trips in Top or quads-or-better in Bottom;
- each row win is +1 point;
- sweeping all three rows adds a +3 scoop bonus.

## Public-site facts relevant to economics

The current KKPoker rake page lists OFC stakes by ante from $0.01 through $2. The published OFC rake is:

- 5% rake;
- cap: 2 BB;
- no rake when the pot is <= 5 BB.

This belongs in the economy/settlement layer, not the raw point-scoring engine.

## Joker/Ultimate details: public-site gap

Searches of the current official public site did not expose a page containing the detailed Advanced Play text visible in the supplied client frames for:

- Progressive Fantasy 14/15/16 cards for QQ/KK/AA;
- Ultimate re-Fantasy receiving the same card count as the qualifying Fantasy hand;
- two Joker wildcard behavior;
- 17-card Fantasy for trips in Ultimate with Jokers.

Therefore these remain sourced from the supplied current in-client rule screens, not silently re-derived from generic OFC rules.

## Important source conflict: foul equality

The supplied in-client rule screen says:

- Bottom must be stronger than **or equal to** Middle;
- Middle must be stronger than **or equal to** Top.

The current public KKPoker OFC guide/gamerules instead uses wording equivalent to Bottom being higher/stronger than Middle and Middle higher/stronger than Top, which reads as strict ordering.

This is a real source conflict. DeepOFC must not hide it.

Until a Joker-specific source or deterministic client experiment resolves it:

- the canonical rules document must mark equality as unresolved;
- the scoring implementation must require an explicit equality policy;
- no R1 or R2 PASS may be declared.

## Still unresolved after official-site research

1. Whether the menu mode named `Joker` is exactly `Ultimate + two Jokers` for every Fantasy and re-Fantasy rule.
2. Whether a Joker may represent a nominal card already physically present in the same hand/board, and whether two Jokers may map to the same nominal card.
3. Tie-breaking when multiple Joker substitutions produce the same best hand rank.
4. Exact supported player counts in KKPoker Joker tables.
5. Exact win-cap redistribution algorithm when a losing player cannot pay the full point result.
6. Whether opponent discards can be inspected during the live hand through Card Tracker before all decisions are complete.
7. Exact rake attribution/PVI mechanics for bankroll accounting; published headline rake/cap is confirmed, attribution is a separate runtime accounting question.

## Engineering consequence

R1 remains open. Safe work can continue on source-independent components (state representation, standard-card evaluator, royalties, replay fixtures and read-only OH plumbing), but Joker wildcard evaluation and final foul settlement must fail closed until the unresolved items are frozen.
