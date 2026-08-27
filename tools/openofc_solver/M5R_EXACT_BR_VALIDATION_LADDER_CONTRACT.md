# M5R-B — Exact best-response validation ladder

Status: **reference-evaluator validation only; not route certification**.

M5R-A binds the exact two-round best-response evaluator to frozen-policy identity and a fail-closed evaluator manifest. M5R-B broadens the exact-reference validation surface before any scalable approximate evaluator is allowed to seek certification authority.

## Families

The ladder reuses two independently defined three-decision perfect-recall reduced games already present in DeepOFC:

1. `HUThreeRoundSequentialSubgame` (`three-round-v1`);
2. `HUThreeRoundSequentialSubgameV2` (`three-round-v2`).

For each family and each responding player, the gate must:

- evaluate the exact pure best response to the frozen uniform behavioral profile;
- enumerate every responding-player legal alternative, including alternatives assigned zero mass by the supplied profile;
- cover every responding-player infoset;
- bind exact terminal-history work against the family’s frozen expected count;
- independently replay the chosen pure response through `state.apply`, a separate transition path from the BR tree expansion;
- require exact-BR value and independent replay value to agree within `1e-10`;
- record all outputs in a machine artifact.

## Frozen work counts

- three-round-v1 exact BR terminal histories per player: `1,312,200`;
- three-round-v1 pure replay terminal histories per player: `3,240`;
- three-round-v2 exact BR terminal histories per player: `839,808`;
- three-round-v2 pure replay terminal histories per player: `5,184`.

These counts are structural coverage checks, not performance targets.

## What this validates

A PASS shows that the same backward perfect-recall BR construction and independent pure-response replay agree across:

- two different three-decision chance/information structures;
- both responding-player identities;
- millions of enumerated terminal histories.

This strengthens the exact reference evaluator as an authority baseline for tractable games.

## What this does not validate

- It does not make exact enumeration scalable to the full OpenOFC game.
- It does not validate an approximate challenger.
- It does not establish a full-game missed-deviation upper bound.
- It does not certify any M5B policy or M4Z route.

The next blocker remains a scalable evaluator whose missed unilateral gain is independently upper-bounded against the exact-reference ladder.

All artifacts must state `production_certification_eligible=false` and `real_routes_certified=0`.