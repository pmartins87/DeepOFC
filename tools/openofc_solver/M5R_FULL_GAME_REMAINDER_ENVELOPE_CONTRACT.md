# M5R full-game state-local remainder-envelope contract

Status: research/certification infrastructure only. This contract does **not** certify a production route and cannot create a REAL M4Z entry.

## Purpose

M5R-E/F already proved that unresolved best-response mass can be converted into a rigorous interval when every skipped branch receives a valid terminal-utility envelope. The reduced pilots used one family-global utility range. The next scalable step is a state-local envelope defined directly on canonical full-game `PlayerBoard` states, so skipped continuation mass can be bounded without evaluating every terminal.

## Frozen scoring scope

The envelope is in the same raw OFC point units produced by `deepofc.simulator.settle_raw_points` for heads-up play. It is derived from the existing `deepofc.scoring` contract:

- row comparison contributes -1/0/+1 per row;
- scoop contributes -3/0/+3;
- maximum Top royalty is 22;
- maximum Middle royalty is 50;
- maximum Bottom royalty is 25;
- therefore one non-fouled board has royalty in [0, 97];
- every scoring-defined heads-up terminal is consequently contained in [-103, +103] raw points.

The current scorer intentionally leaves simultaneous two-player foul settlement unresolved. The envelope MUST NOT invent semantics for that case. A complete both-foul input fails closed. For partial boards, the envelope covers every completion whose terminal settlement is defined by the current scorer.

## State-local tightening

`m5r_full_game_remainder_envelope.py` may tighten the global [-103,+103] bound only by facts already immutable in the supplied canonical boards:

1. a complete board has an exact foul/non-foul status;
2. a complete non-fouled board has exact board-aware Joker royalties;
3. a complete non-Joker row on a partial board has an immutable rank and royalty conditional on the final board being non-fouled;
4. when both corresponding rows are complete and contain no Joker, their row comparison is immutable conditional on both boards being non-fouled;
5. all other unresolved row/royalty possibilities remain conservatively over-approximated.

No deck sampling, policy probabilities, hidden-discard identities, learned values, rollout values, or opponent-model assumptions may enter this envelope.

## Mandatory validation

For every exact terminal descended from each tested reduced canonical state, both of these must hold:

- P0 terminal utility is inside the P0 state-local envelope;
- after swapping board perspective, P1 utility `-u0` is inside the swapped envelope.

Validation must cover at least the exact Joker and hidden-discard two-round families already used by the M5R-E/F ladder. At least one nonterminal state after the first round-4 action must be strictly tighter than the global width 206; otherwise the state-local layer has not demonstrated useful tightening.

A terminal pair with defined scoring must collapse to `[u,u]`. A complete both-foul pair must fail closed.

## Authority boundary

PASS of this gate establishes only that a scoring-derived state-local remainder envelope exists and contains exact reduced-family continuations. It does not establish a scalable full-game best-response evaluator, held-out evidence, or M5C route certification.

After PASS, the next blocker is:

`ROUTE_LEVEL_BR_INTEGRATION_OF_STATE_LOCAL_ENVELOPES_MISSING`

REAL routes certified by this gate: **0**.
