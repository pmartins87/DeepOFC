# OpenOFC external research — 05G-Q1C exact fixed-profile EV contract

Status: **precommitted descriptive evaluation / not equilibrium ranking**  
Authority: `BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
REAL routes certified: **0/50**

## Purpose

Q1A freezes native Search/MCCFR provenance and Q1B freezes the common explicit completion component. Q1C evaluates those already-defined complete profiles exactly on the finite 36-world 05G support.

Q1C is descriptive. It may show that two fixed profiles obtain different EVs against one another, but **cross-play and self-play EV do not rank equilibrium quality**. Only Q2 exact bilateral best response/NashConv/exploitability has ranking authority inside 05G.

## Frozen profiles

For each seed `20260829` and `20260830`, reproduce exactly the Q1A/Q1B definitions:

- Search native: 50,000 UCT iterations, exploration `1.0`;
- MCCFR native: 1,024 iterations, the Q0D-selected engineering budget;
- `S-complete`: Search native where present, otherwise `COMPLETION_UNIFORM_LOCAL_BACKWARD_V1`;
- `M-complete`: MCCFR native where present, otherwise the same completion policy;
- `H-complete`: Search native first, MCCFR native only where Search is absent, completion only where both are absent.

The completion policy is learner-independent and seed-independent. No missing-key fallback is permitted during evaluation.

## Exact evaluation matrix

For each seed, compute the full directed `3 x 3` matrix over `S`, `M`, and `H`:

- matrix row = profile used by P0/nondealer;
- matrix column = profile used by P1/dealer;
- cell = exact expected current-hand utility `u0` under uniform chance over all 36 frozen physical worlds.

This produces three self-play diagonal cells and six directed cross-play cells per seed. Position is not swapped, so no antisymmetry assumption is imposed on `EV(A as P0, B as P1)` versus `EV(B as P0, A as P1)`.

## Exactness requirements

For every matrix cell:

1. enumerate all 36 physical worlds with probability `1/36`;
2. at every nonterminal state use only the acting player's complete frozen profile;
3. enumerate every legal action with positive probability exactly;
4. use canonical `child_state` transitions and exact `terminal_utility`;
5. use no Monte Carlo sampling, rollout approximation, uniform missing fallback, best response or policy update;
6. memoization is permitted only as a semantics-preserving optimization;
7. record terminal-state evaluations, nonterminal cache size, runtime, and finite-value checks.

## Integrity gates

`PASS_EXACT_FIXED_PROFILE_EV` requires:

- frozen 36-world support unchanged;
- all S/M/H profiles are 100% complete and legal;
- reproduced profile SHA256 values are recorded;
- the same completion-policy SHA is used everywhere;
- every one of the 18 seed-specific matrix cells is finite;
- each cell evaluates exactly 36 chance roots;
- no missing profile lookup occurs;
- no best response, regret update, policy modification or strategic winner is computed;
- seeds remain separate.

## Allowed diagnostics

Q1C may report:

- self-play EV;
- directed cross-play EV;
- pairwise EV differences;
- between-seed reproducibility/stability of the same named cell;
- computational work.

These are explicitly **not** promotion criteria.

## Next gate

Q2 will run exact bilateral BR0 and BR1 against each frozen S/M/H completed profile and report NashConv/exploitability. Q2 is the first 05G gate allowed to rank equilibrium quality.

No production migration is permitted from Q1C.
