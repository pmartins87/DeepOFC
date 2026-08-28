# OpenOFC 05F — Public-chance-root hidden-discard-overlap benchmark

Status: **SHADOW RESEARCH / NOT CERTIFICATION**

Authority: `HIDDEN_DISCARD_OVERLAP_REDUCED_GAME_SHADOW_ONLY`

## Motivation

05D-Q2 proved that the earlier six-world R3->R4 fixture barely contains hidden-state ambiguity: only one information set contains more than one compatible concrete state. That fixture is therefore too weak to judge algorithms whose main purpose is imperfect-information reasoning.

05F deliberately creates a harder reduced game in which distinct physical worlds can produce the same public placement history while differing in a private discarded card.

## Frozen game shape

- heads-up normal OFC;
- canonical DeepOFC engine, Joker semantics, action generator, scoring and information-state keys;
- public state is frozen immediately before the R3 private packets are dealt;
- chance selects one complete physical R3/R4 world;
- P0 observes only P0's current R3 packet when acting;
- P1 observes only P1's current R3 packet plus public P0 placements;
- discards remain private exactly as in `strategic_cfr.py`;
- R4 packets are private to their owners;
- one physical world contains no duplicate physical cards.

## Required overlap witnesses

The support must contain at least two P0 R3 private types that share two placeable cards and differ only in the candidate discarded card. There must exist a legal P0 action in both worlds with identical public placements but different private discard identities. After those actions, P1 must receive the same canonical information-state key when its own private information is held fixed.

Symmetrically, the support must contain at least two P1 R3 private types with an identical-public-placement/different-private-discard witness such that P0's subsequent R4 information state is identical when P0's own private information is held fixed.

These are hard mechanical requirements, not statistical expectations.

## Q0 goals

1. validate physical card uniqueness in every world;
2. validate that own private packets change the acting player's information state when they should;
3. validate that opponent hidden discard identity does **not** leak into the information-state key;
4. prove explicit P0->P1 and P1->P0 hidden-discard collision witnesses;
5. run an information-set UCT smoke in which nodes are keyed only by canonical information state and report multi-world nodes by layer;
6. fail closed if no non-root ambiguous information set is observed.

## Future Q1/Q2

Q1 will add an independent MCCFR comparator on exactly the same support. Q2 will compute exact bilateral best responses/NashConv for frozen completed profiles. Algorithm promotion requires the exact-BR comparison; cross-play EV is insufficient.

## Promotion firewall

05F is a reduced fixture. It cannot certify a real Bellman route, prove production exploitability, or feed M5C/M5H as REAL evidence. Passing 05F only establishes that a candidate algorithm handles a deliberately ambiguous hidden-discard game mechanically and, in later stages, strategically relative to other candidates on that fixture.

`real_routes_certified = 0`.
