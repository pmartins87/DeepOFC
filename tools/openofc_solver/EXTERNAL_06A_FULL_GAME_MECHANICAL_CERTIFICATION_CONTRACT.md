# OpenOFC 06A — Full-game mechanical certification contract

Status: **SHADOW RESEARCH / PRE-TRAINING CERTIFICATION**  
Authority: `FULL_GAME_MECHANICS_CERTIFICATION_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

## Purpose

06A is the mandatory mechanical gate before expensive full-game training. It does **not** claim strategic strength, equilibrium quality, Fantasy optimality or production readiness. Its sole purpose is to prove that the current full-action HU normal-hand trainer is mechanically reproducible and that its information model, action model, terminal utility and checkpoint/resume behavior are internally consistent.

The gate is frozen before any 06B algorithm comparison or 06C scaling run.

## Frozen full-game object

The object under test is `tools/openofc_solver/strategic_cfr.py` using the canonical engine and M1b Joker semantics. The normal-hand tree must retain:

- 54 physical cards: 52 standard cards plus two physical Jokers;
- 34 cards dealt per HU normal hand without replacement;
- five-card opening packet for each player;
- four subsequent three-card packets per player;
- all **232** legal opening placements, with no opening abstraction;
- all legal place-2/discard-1 actions on rounds 1–4;
- non-dealer acts first on every round, dealer second;
- exactly 13 placed cards and four private discards per player at terminal;
- exact zero-sum current-hand terminal score from the canonical engine.

Fantasy continuation remains outside 06A. Its absence from this gate must not be interpreted as a strategic approximation being approved.

## Information-state firewall

For every tested state, the acting player's information key must contain only information legally known to that player. In particular:

- own board is visible;
- opponent board is visible;
- own private discards are remembered;
- current own packet is visible;
- public placement history is preserved;
- opponent private discards are absent;
- opponent undealt/future/private packet cards are absent;
- physically different hidden opponent cards that produce the same observable history must not alter the acting player's information key.

The same information-state key must always imply the same canonical legal-action-key set.

## Determinism and checkpoint requirement

Full-game scaling will rely on interruption/resume. Therefore 06A requires **exact deterministic continuation**, not merely statistical validity.

For a fixed seed, epsilon, CFR mode and total iteration count:

1. run an uninterrupted solver for `N1 + N2` iterations;
2. independently run the same solver for `N1` iterations;
3. save and reload a checkpoint;
4. run the restored solver for `N2` iterations;
5. compare canonical solver payloads.

The resumed and uninterrupted solvers must match exactly in:

- iteration and episode counts;
- every information-state key;
- action-key order;
- cumulative regrets;
- cumulative average-policy weights;
- visit counts;
- RNG state;
- resulting canonical payload SHA-256.

Consequently the checkpoint schema used by a passing 06A implementation must serialize and restore Python RNG state. Legacy checkpoints that do not contain RNG state may remain readable only if they are explicitly identified as non-deterministic legacy material; they cannot satisfy the 06A deterministic-resume gate.

## CFR-mode identity

06A must not silently equate different algorithms.

- `cfr_plus=True` means negative cumulative regrets are clipped to zero after each update.
- `cfr_plus=False` means cumulative regrets are not clipped.
- The selected mode must survive checkpoint/resume exactly.

This gate does not decide which mode is strategically superior. That is reserved for 06B.

## Required tests

The gate must execute deterministic tests covering at least:

1. deal uniqueness and physical-card accounting;
2. 232-action opening space;
3. hidden-opponent-card invariance of information keys;
4. private-discard secrecy and own-discard recall;
5. public-history preservation;
6. actor/round transition order through terminal;
7. terminal board/discard counts and zero-sum utility;
8. canonical legal-action-set stability for identical infosets;
9. same-seed full-run reproducibility;
10. exact checkpoint/resume equivalence including RNG state;
11. CFR-mode persistence across checkpoint/resume;
12. finite probability/regret/accounting checks for a deterministic smoke run.

## PASS rule

06A passes only if **all** required tests pass on the canonical CI environment with `PYTHONHASHSEED=0`, and the certification runner reports no hidden-information, action-set, terminal-accounting, non-finite-value or deterministic-resume failures.

A failure blocks 06B/06C until the mechanical cause is repaired and the same frozen contract is rerun.

## Promotion firewall

`PASS_06A_FULL_GAME_MECHANICS` means only that the full-game trainer is mechanically trustworthy enough for controlled algorithm experiments. It does **not** certify near-Nash play, long-horizon Fantasy value, production deployment or any REAL route.

`real_routes_certified = 0`.
