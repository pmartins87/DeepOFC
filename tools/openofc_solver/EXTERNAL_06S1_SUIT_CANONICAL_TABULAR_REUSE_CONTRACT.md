# OpenOFC 06S1 — lossless suit-canonical tabular-reuse A/B contract

Status: **SHADOW RESEARCH / EXACT-REDUCTION A/B**  
Authority: `EXACT_SUIT_CANONICAL_TABULAR_REUSE_DIAGNOSTIC_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

## Purpose

06B proved that direct full-game tabular MCCFR with concrete suit-labelled information keys is reuse-starved: at 4,096 iterations all R1-R4 regret updates were first visits. 06S0 then proved that one global permutation of the four regular suit labels is an exact automorphism of the current game implementation.

06S1 asks one narrow question:

> Does replacing raw information/action keys by their exact global-suit orbit representative create enough recurrence to make direct tabular full-game training plausible at our compute scale?

This is an engineering/representation gate. It cannot rank strategic strength.

The contract is frozen before any 06S1 recurrence result is inspected.

## Frozen A/B

Both arms use the 06A-certified outcome-sampling trainer with:

- epsilon `0.6`;
- `cfr_plus=True`;
- one sampled episode per update player per iteration;
- identical deal/trajectory RNG semantics;
- exact current-hand terminal utility;
- Fantasy continuation still excluded.

Arms:

- `RAW_06A_KEY`: the certified `information_state_key` and raw canonical action keys;
- `SUIT_ORBIT_24_EXACT`: information states canonicalized to the lexicographically minimal observable payload across all 24 global regular-suit permutations, with every legal action key transformed under the same selected permutation.

`JK1` and `JK2` are left unchanged. No rank, row, player, timing, public-history or hidden-card abstraction is allowed.

The suit-canonical arm must live in an isolated research solver until this gate passes.

## Frozen seeds and budget ladder

Seeds:

- `20260830`
- `20260831`

Cumulative checkpoints:

- 256 iterations;
- 1,024 iterations;
- 4,096 iterations.

Each arm/seed starts from an empty table. No warm start is allowed.

## Mandatory mechanical firewalls

Before recurrence metrics are accepted, the suit-canonical research solver must demonstrate:

1. deterministic same-seed reproducibility;
2. checkpoint -> reload -> continuation exactly equals uninterrupted training;
3. checkpoint records explicit suit-canonical schema/mode;
4. one canonical information key always yields one identical canonical legal-action-key set;
5. no non-finite regrets, policy weights or probabilities;
6. all 06S0 exact-symmetry proof tests remain passing on the same head SHA.

A mechanical failure blocks all routing regardless of recurrence.

## Recurrence metrics

At every checkpoint and for each arm/seed report:

- stored information states;
- updated information states (`visits > 0`);
- total regret-update visits;
- information states visited exactly once;
- information states revisited at least twice;
- repeat-update mass;
- repeat-update fraction;
- maximum visits;
- metrics by `R0_P0`, `R0_P1`, ..., `R4_P1`;
- aggregate R1-R4 metrics;
- stored nodes per iteration;
- runtime and iterations/second.

Also report canonical-vs-raw ratios at 4,096 iterations for stored states, updated states, overall repeat fraction and R1-R4 repeat fraction.

## Frozen reuse-starvation rule

Reuse-starved retains the exact 06B definition at the 4,096 checkpoint:

- overall `repeat_update_fraction < 0.005`; **and**
- aggregate R1-R4 `repeat_update_fraction < 0.001`.

The thresholds are engineering compute-efficiency gates, not equilibrium theorems.

## Precommitted routing

### A. Both suit-canonical seeds are not reuse-starved

Verdict:

`SUIT_CANONICALIZATION_BREAKS_REUSE_STARVATION`

Next gate:

`06S2_CANONICAL_ALGORITHM_AND_POLICY_READOUT_AB`

Only then may vanilla/clipped and current/average strategy questions be reopened under the canonical representation.

### B. Both suit-canonical seeds remain reuse-starved

Verdict:

`SUIT_CANONICALIZATION_EXACT_BUT_INSUFFICIENT_FOR_DIRECT_TABULAR_SCALING`

Next gate:

`06R_CONDITIONED_RESOLVING_AND_GENERALIZATION_ARCHITECTURE`

No larger direct global-tabular run is authorized. The project must evaluate architectures that concentrate computation on strategically relevant conditioned subgames/infosets, while preserving exact reductions where possible. Approximate function approximation, if later needed, must remain explicitly labelled approximate.

### C. Mixed seeds

Verdict:

`SUIT_CANONICALIZATION_REUSE_INCONCLUSIVE`

Next gate freezes a canonical-only 16,384-iteration resolution run before any architecture choice.

## Prohibited claims

06S1 cannot establish exploitability, Nash equilibrium, solver strength, Fantasy value or production readiness. A recurrence improvement only establishes that regret learning can revisit exact symmetry classes more often.

`real_routes_certified = 0`.
