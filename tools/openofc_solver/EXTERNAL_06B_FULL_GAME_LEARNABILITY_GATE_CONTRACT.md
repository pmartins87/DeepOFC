# OpenOFC 06B — Full-game tabular learnability / recurrence gate

Status: **SHADOW RESEARCH / PRE-SCALING**  
Authority: `FULL_GAME_TABULAR_LEARNABILITY_DIAGNOSTIC_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

## Why this gate exists

06A established that the full-action normal-hand trainer is mechanically correct and exactly resumable. That is not sufficient to justify expensive training.

The current solver is tabular. Its information-state keys preserve concrete cards, private own discards and full public placement history. In the complete 54-card game, the same exact information state may therefore recur extremely rarely. If nearly every regret update lands on a newly created information set, increasing the number of raw MCCFR iterations mainly increases table size rather than repeatedly refining the same decisions.

06B measures that failure mode **before** choosing a full-game CFR variant or spending large compute.

This gate is frozen before looking at its recurrence results.

## Scientific basis

- Lanctot et al. (NIPS 2009), *Monte Carlo Sampling for Regret Minimization in Extensive Games*, establishes MCCFR as a sampled no-regret framework; outcome sampling has equilibrium guarantees in the appropriate average-strategy setting, but those guarantees do not make a finite tabular implementation computationally dense.
- OpenSpiel's reference outcome-sampling MCCFR maintains a table keyed by information state, uses a default policy for unseen states and exposes the average policy as the standard solver output.
- Waugh (AAAI 2013), *A Fast and Optimal Hand Isomorphism Algorithm*, shows that exact suit isomorphism can collapse strategically equivalent poker card histories without sacrificing value.
- Deep CFR (Brown et al., 2019) was introduced specifically because very large imperfect-information games can make tabular CFR impractical; function approximation provides generalization across information states, at the cost of approximation error.

These references motivate the diagnostic. They do not predetermine its result and do not authorize an approximation.

## Frozen solver variants

The recurrence diagnostic runs the existing certified 06A full-game solver in both mechanically distinct modes:

- `VANILLA_OS_MCCFR`: `cfr_plus=False`;
- `CLIPPED_OS_MCCFR`: `cfr_plus=True`.

No strategic winner can be declared by 06B. The two modes are included only to ensure that the recurrence conclusion is not an artifact of one regret-update mode.

## Frozen seeds and budget ladder

Seeds:

- `20260830`
- `20260831`

Cumulative iteration checkpoints per seed/mode:

- 256
- 1,024
- 4,096

Each MCCFR iteration contains one sampled episode per update player, exactly as certified in 06A.

## Required measurements

At every checkpoint, report separately for each seed/mode:

1. total stored information sets;
2. total **updated** information sets (`visits > 0`);
3. total regret-update visits;
4. information sets visited exactly once;
5. information sets revisited at least twice;
6. `repeat_update_mass = sum(max(visits - 1, 0))`;
7. `repeat_update_fraction = repeat_update_mass / total_update_visits`;
8. maximum visits to one information set;
9. the same metrics by actor and round;
10. aggregate later-round metrics for rounds 1–4;
11. action-count distribution and maximum action count;
12. elapsed time and approximate growth in stored nodes per iteration.

Nodes created only because the acting opponent traversed them but with `visits == 0` must not be counted as learned/revisited nodes. They are reported separately as stored support.

## Exact opening-space reference

The raw non-dealer opening information state contains its exact five-card packet. Before any symmetry reduction, the physical five-card support is

`C(54, 5) = 3,162,510`.

This reference is descriptive only; the empirical recurrence measurements decide the gate.

## Precommitted routing rule

At the 4,096-iteration checkpoint, define a seed/mode as **reuse-starved** when both are true:

- overall `repeat_update_fraction < 0.005` (less than 0.5% of update mass is a revisit); and
- aggregate rounds 1–4 `repeat_update_fraction < 0.001` (less than 0.1% of later-street update mass is a revisit).

### If all four seed/mode cells are reuse-starved

Verdict:

`BLOCK_DIRECT_TABULAR_SCALING_REUSE_STARVED`

The next gate becomes `06S_EXACT_SYMMETRY_AND_GENERALIZATION_DESIGN`. No large direct-tabular training run and no CFR-variant winner selection are authorized.

06S must first investigate **lossless** reductions, beginning with global suit isomorphism and other exact game symmetries. Approximate abstraction or neural generalization may be researched only as a separately labelled fallback and may never be described as mathematically exact.

### If any seed/mode is not reuse-starved

Verdict:

`CONTINUE_06B2_ALGORITHM_AND_POLICY_READOUT_AB`

The project then freezes a separate 06B2 contract for a larger budget and independent strategic evaluation before choosing vanilla vs clipped or current vs average policy.

The threshold is an engineering compute-efficiency gate, not an exploitability theorem.

## Prohibited interpretations

06B cannot establish that:

- vanilla OS-MCCFR is stronger than clipped OS-MCCFR or vice versa;
- current policy is stronger than average policy;
- the full-game strategy is near Nash equilibrium;
- Fantasy continuation has been solved;
- any production route is ready.

A high recurrence rate is necessary for direct tabular learning to be plausible at our compute scale, not sufficient for strategic strength.

## Promotion firewall

`real_routes_certified = 0` regardless of result.
