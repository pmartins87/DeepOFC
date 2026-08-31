# M5R state-local deep-BR integration contract

Status: research/certification infrastructure only. This gate cannot certify a production route and cannot create a REAL M4Z entry.

## Purpose

The full-game remainder-envelope gate established a rigorous raw-point interval for a canonical pair of partial `PlayerBoard` states. This gate integrates that interval into the already validated M5R-E deep best-response pruning algorithm.

The responding player's own legal actions remain explicit. Only chance/opponent counterfactual mass may be pruned. At every pruning cut, the old one-size-fits-all scoring range is replaced by the rigorous state-local P0 interval at that exact canonical board state. For a P1 best response, `[lo0, hi0]` is transformed to `[-hi0, -lo0]` before reach weighting.

## Frozen cut semantics

Three pruning cuts are supported and must use these states:

1. **round-3 prefix cut:** boards immediately after both round-3 placements;
2. **round-4 opponent-first branch cut:** boards after applying the observed opponent first round-4 placement, before the responder's second placement;
3. **terminal-opponent-action cut:** boards after applying the responder's first round-4 placement, before the frozen opponent's second placement.

The interval function must never receive a terminal board produced by the unresolved action below the cut. That would be lookahead leakage.

## Mandatory reduced-family validation

Validation covers both exact two-round families already used by the M5R ladder (`joker` and `hidden-discard`) and both responding players.

For every cell:

- threshold zero must collapse to the exact BR value and resolve all terminal histories;
- a nonzero working threshold must contain the exact BR value and exact deviation gain;
- at equal threshold, state-local and legacy scoring-global evaluators must resolve and skip exactly the same terminal histories;
- the state-local interval must never be wider than the scoring-global `[-103,+103]` interval in the tested cell;
- a full-prune threshold must account for every terminal history and still contain the exact BR.

Across the four cells, at least one must show strict interval-width reduction and at least one must exercise pruning below the round-3 prefix level. These are usefulness/mechanics requirements, not a claim that every future route must tighten.

## Authority boundary

PASS proves that canonical state-local remainder bounds can safely replace a global scoring envelope inside the validated deep-BR pruning mechanics. It still does not prove the route-evidence schema, frozen candidate identity, held-out independence, or M5C threshold decision.

After PASS, the next blocker is:

`ROUTE_EVIDENCE_INTERFACE_FOR_STATE_LOCAL_BR_UPPER_BOUNDS_MISSING`

REAL routes certified by this gate: **0**.
