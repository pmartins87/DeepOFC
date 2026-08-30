# OpenOFC 06P — Practical Hybrid Solver Architecture

Date: 2026-08-30
Status: architecture shortlist / research authority only
Production authority: none (`REAL = 0/50`)

## Why this note exists

06B and 06S1 established a concrete full-game limitation: exact-card global tabular outcome-sampling regret minimization receives essentially no repeated downstream updates, and exact global suit canonicalization does not repair that geometry. The project therefore should not treat mathematical exactness as an unconditional deployment requirement.

The governing objective is now `docs/OFC_PRACTICAL_STRENGTH_COMPUTE_POLICY_2026-08-30.md`: obtain the strongest target-rule agent that is practical on the available Ryzen 9 and final runtime environment.

## Architecture conclusion

The leading production hypothesis is **phase-adaptive and hybrid**, not one universal solver.

### Exact semantic shell

Always exact:

- KKPoker target rules;
- 54-card / two-Joker physical deck consistency;
- legal placements and row capacities;
- foul detection;
- target royalties and HU score;
- Ultimate Fantasy 14/15/16/17 transition semantics;
- public/private information firewall;
- lossless suit canonicalization where useful.

This shell prevents the kind of absurd action that comes from illegal-state, foul, scoring or information-leak bugs even when the strategy itself is approximate.

### Early game: generalization/prior first

Opening and early streets have the largest support and the poorest exact tabular recurrence. The preferred role here is a fast generalized policy/value prior rather than per-infoset memorization.

Candidate mechanisms, in rising implementation complexity:

1. Monte Carlo action-value estimates with physically consistent sampled worlds;
2. compact feature/state abstraction with shared statistics;
3. imitation/distillation from stronger offline search labels;
4. small policy/value network trained on self-play/search data;
5. top-K action proposal model followed by a stronger local search.

The prior does not need to be an equilibrium solver. Its job is to rank reasonable actions quickly, avoid strategically nonsensical placements and concentrate subsequent search budget.

### Middle game: sampled imperfect-information search

As public information accumulates, current-state search becomes progressively more attractive. Main candidates:

- suit-canonical conditioned MCCFR / continual resolving;
- target-rule ISMCTS with a physically consistent hidden-world sampler;
- Monte Carlo rollout with strategic rather than purely greedy continuation;
- hybrid proposal + local regret/search refinement.

Hidden states should be sampled jointly without replacement. When an exact Bayesian/reach-weighted posterior is too expensive, a particle/weighted belief approximation is acceptable if its strength-per-compute benefit is measured.

### Late game: bounded or exact search where it fits

The external `Saholy99/ofcp-engine` audit supplied a useful dispatch pattern: exact search when the remaining tree fits, otherwise beam/bounded search, otherwise rollout fallback. DeepOFC should reproduce the architecture under its own target rules rather than import incompatible values.

R3/R4 should therefore prefer progressively stronger search as remaining horizon shrinks. The final action may be exactly enumerable in many states even if the opening is not.

### Fantasy: preserve exact target objective, optimize implementation

Fantasy is structurally different from normal play and already has a target-specific exact V2 kernel. Keep exact semantics/objective there as long as feasible. Performance work may use branch-and-bound, cached frontiers, C++ kernels and multicore execution, provided action/value parity is preserved.

There is no reason to deliberately approximate a tractable Fantasy state merely because normal-play solving is approximate.

## External evidence translated into candidates

The external audit does **not** justify copying a public solver wholesale, but it gives practical components:

- `Saholy99/ofcp-engine`: strongest architectural evidence for phase dispatch, hidden-state sampling, bounded late search, telemetry and fallback;
- `xeond8/OFC-Poker-Agents`: high-value target-rule experiment direction for ISMCTS/determinization under fixed move budgets;
- `yuanzd123/OFC-Pineapple-Solver`: simple current-action Monte Carlo baseline worth retaining as a low-cost comparator;
- `StiopaPopa/ananas_final`: evidence for a phase-specific learned-policy + late-search architecture;
- `ainaosyusi/ofc-pineapple-ai`: fast C++ evaluator/Fantasy/search engineering, but strategic/rule semantics must remain DeepOFC's;
- `neery1218/OFCSolver`: throughput ideas only; its independently sampled hero/opponent future cards are not a valid joint chance model.

## Practical candidate ladder

The next strategic comparison should not ask which method is theoretically most elegant. It should ask which method supplies the strongest decisions at matched cost.

Candidate ladder:

**P0 — Fast rollout baseline**

Enumerate current legal actions or a safe candidate subset, sample legal hidden/future worlds jointly, continue with a fixed competent rollout policy and estimate target HU utility. This establishes the minimum viable strength/latency curve.

**P1 — Target-rule ISMCTS**

Information-set MCTS with re-determinization/hidden-world sampling that never exposes hidden opponent state to the acting policy. Compare directly with P0 at matched terminal evaluations and matched wall-clock.

**P2 — Conditioned MCCFR / continual resolving**

Use the 06R0 geometry result to decide which rounds can benefit. Evaluate current/average output and potentially DCFR/CFR+ only after the architecture itself demonstrates reuse.

**P3 — Hybrid prior + search**

Use a compact global policy/value model to propose/rank actions; spend search only on top candidates and high-uncertainty states. This is the leading long-term architecture if pure online search is too slow early.

**P4 — Learned generalization / Deep-CFR-like family**

06B/06S1 have now satisfied the condition that the older CFR-variant queue had reserved for considering function approximation: exact tabular storage/reuse is a demonstrated bottleneck. Neural/generalized regret or policy/value approximation is therefore no longer excluded on principle. It remains behind cheaper P0-P3 methods because implementation/training complexity is higher, not because mathematical approximation is undesirable.

## Equal-budget evaluation

Every candidate should expose a strength curve rather than one cherry-picked operating point. Preferred budgets are wall-clock or terminal-evaluation counts that map to deployment reality.

For each method measure:

- target utility / cross-play performance;
- exact BR/NashConv on reduced games where tractable;
- decision agreement/value regret against exact late-game/Fantasy teachers;
- foul/illegal-action rate (must be zero after semantic shell);
- gross-blunder rate on curated tactical states;
- runtime latency distribution, especially p50/p95/p99;
- offline compute used to create priors/models;
- RAM/model size;
- marginal strength gain from the next compute tier.

A candidate can win while being mathematically less precise if its measured playing strength is better at the available cost.

## Reduced certification burden

Do not create a long chain of proof gates for every minor algorithmic detail. The default development sequence becomes:

1. **mechanical firewall** — rules, information boundary, physical chance sampling, deterministic replay and legality;
2. **small calibration** — compare against exact/reduced authorities and obvious tactical cases;
3. **matched-budget strength A/B** — the primary decision gate;
4. **broader holdout/robustness validation** before production promotion.

Additional diagnostic gates are added only when an actual observed failure mode demands them.

## Stop / scale rule

For any method, build a compute ladder and stop increasing precision when the next compute tier produces little or no measured strategic improvement. The released operating point is the strongest practical point below the latency/offline-compute budget, not necessarily the highest-budget point ever tested.

Long Ryzen 9 runs are justified only after smaller matched-budget ladders demonstrate favorable scaling.

## Current routing

06R0 is the active geometry experiment. Its frozen router determines only how broadly conditioned regret search is worth testing:

- broad reuse -> include conditioned MCCFR in the main matched-budget competition;
- late-only reuse -> use it as a late-round component;
- insufficient reuse -> move directly to stronger generalization / ISMCTS / rollout architecture rather than spend more iterations on the same table.

Regardless of the 06R0 result, the project no longer depends on obtaining a full-game exact equilibrium before building an extremely strong practical player.
