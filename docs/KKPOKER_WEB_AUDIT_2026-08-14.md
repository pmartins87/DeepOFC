# KKPoker official-site audit — 2026-08-14

Purpose: resolve R1 ambiguities using only current official KKPoker public pages, as requested by the project owner. This audit supplements the more specific in-client rule screenshots supplied with the replay package.

## Official pages checked

- `https://kkpoker.net/how-to-play/open-face-chinese-poker-ofc/`
- `https://br.kkpoker.net/how-to-play/open-face-chinese-poker-ofc/`
- `https://kkpoker.net/gamerules/`
- `https://br.kkpoker.net/gamerules/`
- `https://kkpoker.net/how-to-play/rake-information/`
- `https://br.kkpoker.net/how-to-play/rake-information/`
- `https://br.kkpoker.net/how-to-play/instant-rakeback-explain/`

Searches were also performed on the official domain for the terms/ideas `Joker`, `Ultimate`, `17 cards`, `two Jokers`, `win cap`, `maximum funds`, opponent `discard`, Card Tracker, and OFC rake attribution.

## What the public site confirms

The public OFC guide/rules confirms the generic Pineapple contract:

- 52-card base OFC deck;
- 13-card 3/5/5 board;
- five rounds;
- five cards initially;
- three cards in each later round;
- place two / discard one on later rounds;
- action from the player left of BTN clockwise to BTN;
- QQ or better on Top, without foul, enters Fantasy;
- Fantasy deals 14–17 cards and 13 are set at once;
- re-Fantasy/stay condition: trips on Top or quads-or-better on Bottom;
- one point per row and +3 scoop bonus.

The public OFC rake table currently lists:

- 5% designated OFC rake;
- 2 BB cap;
- no rake if pot <= 5 BB;
- OFC ante/stake units $0.01, $0.02, $0.05, $0.10, $0.20, $0.50, $1 and $2.

The generic cash-game rake section on the same official page also states that **half of the designated rake is charged when a table has <= 3 players**. Because OFC normal tables are 2–3 players, this wording could materially affect the effective OFC rake, but the OFC-specific subsection does not repeat the half-rake sentence. DeepOFC therefore does **not** silently convert the 5% headline into 2.5%; exact live OFC applicability remains an empirical/economics validation item.

The public Instant Rakeback page explicitly includes OFC and states a minimum 5% system rakeback with levels up to 50%.

## What the public site does NOT resolve

The current public KKPoker rules pages do not expose the advanced `Joker Ultimate` rule text visible in the supplied client screenshots. In particular, official-domain searches did not produce source text resolving:

1. whether a Joker may duplicate a standard physical card already present in the hand;
2. whether both physical Jokers may represent the same nominal card;
3. wildcard assignment/tie rules when multiple substitutions make the same best rank;
4. every Joker Ultimate re-Fantasy card-count path, especially Bottom-quads-only stay-in-Fantasy;
5. the numeric win-cap redistribution/clamping algorithm for insufficient funds;
6. exact OFC `pot` definition and rake attribution/rounding under capped pairwise settlement;
7. whether an opponent's discard **identity** can be viewed during a live hand via a supported UI before settlement.

The public `gamerules` page contains no `Joker` or `win cap` text in its OFC section. Therefore these items remain open rather than being inferred from non-KKPoker OFC rules.

## Source precedence for DeepOFC

For the exact target table, the supplied current-client evidence is more specific than the generic public webpage:

- replay table label: `Joker Ultimate GPS/IP`;
- in-client Advanced Play screen: two Jokers are wild; Ultimate-with-Jokers trips-on-Top can receive 17 Fantasy cards;
- in-client Basic Play screen: Bottom >= Middle >= Top, explicitly allowing equality for foul ordering;
- in-client Scoring screen: start-of-hand funds cap and ordered three-player settlement behavior.

DeepOFC freezes those client-proven facts and uses the public site as corroboration/current-economics evidence. Any unresolved EV-relevant rule remains fail-closed.
