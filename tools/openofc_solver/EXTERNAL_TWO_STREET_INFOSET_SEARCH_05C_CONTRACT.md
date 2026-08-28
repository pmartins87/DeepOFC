# External two-street information-set search contract (05C)

Status: **Q0 ACTIVE AFTER 05B PASS / SHADOW ONLY**.

Authority: `FINITE_SUPPORT_R3_R4_INFOSET_TREE_SHADOW_ONLY`.

05B passed its frozen final-street contract in run `33141424288`: the explicit P1 information-set search selected an exact finite-support optimum and reconstructed the selected-action support value with zero error. This authorizes 05C-Q0 mechanically; it grants no strategic certification authority.

## Why 05C is different from 05A/05B

05A and 05B live entirely on R4. Once P0 chooses an R4 action, P1 answers and the hand terminates. A two-street R3→R4 tree is strategically different: future private packets and public R3 actions alter later information sets, and equilibrium play may require mixed strategies. Therefore determinization-by-determinization minimax is forbidden as an 'exact' reference for 05C.

## Q0 game boundary

The experiment starts at a coherent non-terminal HU state with `round_index=3`, `actor=P0`, legal boards/discard memories through R2, and P0's current R3 packet observed. A finite support of complete physical worlds supplies P1 R3 plus both future R4 packets. Every world is one valid 34-card HU deal with no repeated physical card.

One support world is sampled per episode. Hidden/future cards may drive state transitions, but they cannot enter a decision-node identity before becoming legal information.

Traversal is exactly:

`P0 R3 max -> P1 R3 min -> P0 R4 max -> P1 R4 min -> canonical terminal utility`.

Every node uses `information_state_key(state)` and the canonical legal action set. P0 nodes maximize P0 utility. P1 nodes minimize the same zero-sum quantity. Stable UCB/LCB exploration is a mechanical search baseline only.

## Q0 PASS gates

- support worlds are physically unique legal deals;
- one root information state and one root legal-action set across every hidden world;
- deterministic same-seed replay;
- all four decision layers materialize;
- every episode terminates after exactly four decisions;
- zero heuristic terminal evaluator;
- no exact-response helper inside search;
- action sets remain stable for repeated visits to the same information state;
- artifact remains `real_routes_certified = 0`.

## Q1 and 05D

Q1 may study multi-seed/budget reproducibility, information-set growth, root-action stability and value dispersion. It remains shadow-only.

The first strategic comparator belongs in 05D: CFR/MCCFR on the **same reduced two-street support and action space**. Because the reduced game can require mixed strategies, 05D must not label naive per-world minimax as exact. Any eventual certification authority must still pass the separate M5H/M5L process.

## Explicit non-claims

05C cannot establish full-game ISMCTS convergence, posterior correctness after R0-R2 signalling, exploitability bounds, superiority over M5/CFR, Fantasy continuation correctness, production authority or any REAL route certificate.
