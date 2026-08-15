# OpenHoldem DeepOFC GUI plan

## Finding

The OpenHoldem GUI source is available in `pmartins87/myoh_private`, including `OpenHoldem/OpenHoldemView.cpp` and `.h`.

The stock renderer is structurally Hold'em/Omaha-specific:

- five `CommonCards` are drawn in the center;
- player cards are read from `Player(chair)->hole_cards(i)`;
- the number of cards is driven by `NumberOfCardsPerPlayer()`;
- seated/active state, player name, dealer indicator, balance and bet already have independent GUI rendering.

Therefore DeepOFC must not try to force its 3/5/5 rows into the existing hole/community-card renderer. The GUI should branch on `p_tablemap->SupportsOFCJokerUltimate()` and draw directly from `CTableState::OFCState()`.

## Desired OFC debug/runtime view

For each 2- or 3-player chair display:

- seated/occupied/active state;
- dealer/button;
- acting player;
- Fantasy state;
- Top row (3 cards);
- Middle row (5 cards);
- Bottom row (5 cards);
- known card faces;
- cardbacks/unknown-count markers where identity is hidden;
- persistent JK1 / JK2 identity;
- Hero current incoming cards (3/5 normal, 14..17 Fantasy);
- Hero known discards;
- opponent hidden discard count;
- pending Hero placements before Confirm;
- `hero_can_prepare` / `hero_can_confirm` / `action_required` safety state;
- later: selected DeepOFC action and action EV diagnostics.

The renderer is diagnostic only. It must never be a source of strategic state. Data flow remains:

`KKPoker pixels -> tablemap/scraper -> COFCVisualObservation -> COFCState -> solver/action executor -> GUI`

not the reverse.

## Card rendering

Standard cards may reuse the existing `DrawCard` artwork after conversion from OFC's 0..51 standard-card convention.

JK1/JK2 require explicit OFC rendering because legacy Hold'em card values do not represent the two physical Jokers. Until dedicated bitmaps exist, a clear debug glyph such as `JK1` / `JK2` is preferable to silently mapping either Joker to a normal card.

Unknown/cardback state should remain visually distinct from empty slots.

## Layout

The existing percentage-based poker-seat layout can be retained for player identity/status, but row geometry needs an OFC-specific layout. It does **not** need to mimic the KKPoker pixels; the OpenHoldem window is a diagnostic representation of canonical state.

For HU, a useful initial layout is:

- opponent 3/5/5 board in upper half;
- Hero 3/5/5 board in lower half;
- Hero incoming/discards beneath or beside Hero board;
- central status panel with round/Fantasy/actor/action/EV.

Three-player should use compact row blocks around the existing three seat anchors.

## Gate

GUI work is not on the mathematical critical path. It can be implemented after the canonical state and decision engine stabilize, but it must be complete before R11 shadow mode so visual debugging does not require reading raw logs.

Acceptance:

1. replay fixture canonical states render all board cards exactly;
2. cardbacks/unknowns are visibly different from empty;
3. JK1/JK2 remain distinguishable;
4. active/dealer/actor/Fantasy state matches canonical state;
5. GUI has no code path that mutates `COFCState` or authorizes clicking.
