# OpenOFC external research — 05C design note

Date: 2026-08-28
Branch: `research/external-ofc-solver-audit-20260827`
Status: design frozen; implementation intentionally dormant until 05B finishes green.

## Main design decision

The next experiment will extend the information-set search from one street (R4) to two streets (R3→R4), but it will **not** use determinization-by-determinization minimax as a claimed exact reference.

That distinction matters because 05B's final-street reduced game has a simple exact finite-support benchmark: P0 chooses one R4 action without seeing P1's packet, then P1 sees its own packet and answers at terminal. In R3→R4, public actions create new later information sets and equilibrium play may require mixing. Solving each hidden world independently would leak information and solve a different game.

## Frozen architecture

One complete physical hidden world will be sampled per episode. The same world supplies P1 R3 plus both future R4 packets. The tree will then traverse four legal decision nodes:

`P0 R3 (max) -> P1 R3 (min) -> P0 R4 (max) -> P1 R4 (min) -> exact terminal score`.

Every decision node will use the repository's canonical `information_state_key`. Hidden/future cards may exist in the transient world object but cannot alter a node key until they are actually part of that player's legal information.

## Scientific reference strategy

05C-Q0 will be a mechanical smoke test only. The stronger quality comparison is deferred to 05D, where the same reduced two-street support/action space will be solved independently with CFR/MCCFR. This prevents us from manufacturing an 'exact' label for a game where pure determinized minimax is not the correct authority.

The external ISMCTS work therefore remains a shadow research line. It can improve search engineering or expose weaknesses in the current strategic architecture, but it remains behind the M5H/M5L certification firewall and cannot create REAL routes by itself.
