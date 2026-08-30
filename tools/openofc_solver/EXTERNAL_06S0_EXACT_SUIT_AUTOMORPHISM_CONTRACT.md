# OpenOFC 06S0 — exact global-suit automorphism certification

Status: **SHADOW RESEARCH / LOSSLESS-REDUCTION PROOF ONLY**  
Authority: `EXACT_SUIT_AUTOMORPHISM_DIAGNOSTIC_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

## Purpose

06S0 determines whether the current normal-hand HU engine is exactly invariant under a single global permutation of the four regular-card suit labels. It is a proof gate for a possible lossless information-state canonicalizer; it does not alter `strategic_cfr.py` and does not authorize canonicalized training.

The contract is frozen before certification results are inspected.

## Candidate automorphism

For any permutation `pi` of the four regular suits `c,d,h,s`:

- every regular `Card(rank, suit)` becomes `Card(rank, pi[suit])`;
- `JK1` and `JK2` remain unchanged;
- ranks, rows, player identities, dealer position and action timing remain unchanged.

Only one **global** permutation may be applied to a complete state/history. Per-row or per-player suit relabelling is prohibited.

## Required invariants

Across all 24 suit permutations, deterministic representative fixtures and frozen randomized probes must establish:

1. **physical-deck bijection** — transformed 54-card decks contain 54 unique physical cards and invert exactly;
2. **complete-board score invariance** — `score_heads_up` is identical after globally permuting both boards, including foul, royalty and Fantasy-card outputs;
3. **Joker-resolution invariance** — fixtures containing `JK1`, `JK2` and both Jokers preserve `resolve_board` rank/royalty/Fantasy results under suit renaming;
4. **legal-action cardinality/bijection** — every legal action's card/row/discard semantics has one transformed legal counterpart and the inverse mapping recovers the original;
5. **transition commutation** — applying an action then permuting produces the same observable child state as permuting first and applying the corresponding transformed action;
6. **terminal utility invariance** — player-0 and player-1 utilities are unchanged by global suit relabelling;
7. **information-orbit identity** — raw information observations related by a global suit permutation can be canonicalized to the same suit-orbit key without inspecting hidden opponent cards or future cards;
8. **canonical legal-action stability** — suit-isomorphic information states produce exactly the same canonical legal-action-key set;
9. **perfect-recall preservation** — own private discards and full public placement history remain represented;
10. **non-isomorphic firewall probes** — strategically meaningful changes to ranks, rows, public timing, player position or Joker identity are not collapsed merely because suit canonicalization is enabled.

## Canonicalization candidate

For proof purposes only, the reference canonicalizer may enumerate all 24 global suit permutations and choose the lexicographically minimal serialization of the already-certified observable information payload. This intentionally favors auditability over speed.

The selected permutation must also transform the card tokens in legal action keys so that one canonical information key always has one canonical legal-action-key set.

## Joker-identity exclusion

`JK1 <-> JK2` is **not** part of 06S0. Even if later evidence shows the two physical Jokers are strategically interchangeable, that requires its own explicit automorphism gate.

## PASS rule

06S0 passes only if all required deterministic/randomized invariants succeed for all 24 suit permutations with zero mismatches.

PASS means only:

`GLOBAL_SUIT_PERMUTATION_IS_LOSSLESS_AUTOMORPHISM`

It does not mean that the resulting reduction is large enough to solve the full game efficiently.

## Promotion firewall

No strategic policy changes, no CFR winner, no current/average readout winner, no Fantasy continuation claim and no REAL route may be produced by 06S0.

`real_routes_certified = 0`.
