# OpenOFC 05E — Exact Best Response on the Frozen Two-Street Reduced Game

Status: **REDUCED-GAME EXACT / SHADOW RESEARCH / NOT REAL-GAME CERTIFICATION**

Authority: `EXACT_FINITE_SUPPORT_TWO_STREET_BR_REDUCED_GAME_ONLY`

## Purpose

05D head-to-head comparisons can show that two policies differ, but they do not measure how exploitable either policy is. 05E adds an exact pure best-response evaluator for the frozen R3->R4 finite-support game so UCT-derived and MCCFR-derived profiles can be compared by exact reduced-game NashConv rather than only by cross-play EV.

## Frozen game

05E uses exactly the same finite physical-world support, canonical information-state keys, legal actions, transitions, and exact current-hand terminal utility as 05C/05D. It does not add earlier rounds, Fantasy continuation, or any hidden information to policy keys.

## Best-response semantics

For a responding player `i`:

- chance and every opponent action probability contribute to counterfactual reach;
- the responding player's own strategy probabilities never contribute to counterfactual reach;
- every legal responding-player action is enumerated, including actions assigned zero probability by the supplied profile;
- the opponent profile is fixed and must be explicit at every reachable opponent information state;
- round-4 responding-player information sets are optimized first;
- each round-4 information set must map to exactly one own round-3 predecessor information set and own round-3 action, enforcing the perfect-recall relationship;
- optimized round-4 counterfactual values are propagated to round-3 action values;
- each round-3 information set then chooses its maximizing pure action;
- P0 utility is maximized directly; P1 maximizes `-u0`.

Ties are broken deterministically by canonical action key.

## Independent replay check

The pure best response must be materializable as a complete behavioral profile and replayed through the independent exact fixed-profile evaluator. The replayed utility must equal the direct best-response value within numerical tolerance for both players.

## Reduced-game NashConv

For a complete profile `sigma`:

`NashConv(sigma) = BR0_value(sigma_1) + BR1_value(sigma_0)`

and reduced-game exploitability is reported as `0.5 * NashConv`.

These quantities are exact only for the frozen finite-support R3->R4 game.

## Firewall

05E does **not** certify the full normal hand, Fantasy transitions, the 50 Bellman routes, or live/runtime strategy. A low reduced-game exploitability is architecture evidence only and cannot be promoted into M5C/M5H/M5L certification authority.

`real_routes_certified` remains `0`.
