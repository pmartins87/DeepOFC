# DeepOFC Practical Strength per Compute Policy

Date: 2026-08-30

## Objective

DeepOFC is not required to solve the complete OFC game to mathematical perfection before becoming useful. The engineering objective is:

> **maximize practical playing strength subject to the compute, memory and latency budgets actually available to the project.**

The target offline environment is consumer hardware centered on a Ryzen 9, where strategically worthwhile jobs may run for days, weeks or, when justified by measured gain, months. Online/current-hand computation must remain compatible with the operational latency budget of the final OpenHoldem/KKPoker integration.

Mathematical precision is therefore a resource to allocate, not an unconditional requirement.

## Non-negotiable exact layer

The following remain exact unless a separate correctness proof explicitly replaces them with an equivalent representation:

- game rules and turn order;
- card identity and deck consistency;
- legal-action generation;
- row capacities and placement legality;
- foul detection;
- hand resolution, royalties and HU scoring;
- public/private information boundaries;
- deterministic state transitions;
- any symmetry reduction claimed to be lossless.

Approximation is allowed in **strategy computation**, not in the basic definition of the game.

## Exact methods as oracles, not as a deployment requirement

Exact or near-exact solving remains important on tractable reduced games because it gives calibration targets, best-response measurements and regression tests. A practical solver may be approximate in the full game while still being held against exact reduced-game oracles.

A method is not rejected merely because it lacks a full-game equilibrium proof. Conversely, a mathematically elegant method is not preferred if its compute geometry prevents it from learning a strong policy within the available budget.

## Optimization frontier

Candidate architectures are evaluated on a Pareto frontier containing at least:

- measured strategic strength;
- exploitability or exact best-response loss where tractable;
- cross-play / duplicate-world EV on broader fixtures;
- gross-blunder and foul rates;
- robustness across seeds and strategically different states;
- offline wall-clock cost;
- peak memory and persistent model size;
- online decision latency;
- marginal gain obtained from additional compute.

The preferred candidate is the strongest practically feasible point on this frontier, not necessarily the most exact candidate.

## Precision budget rule

Increase precision while additional computation produces material measured strategic gain. Reduce or stop precision when its marginal gain becomes poor relative to wall-clock, memory or runtime latency.

Examples of acceptable approximations include, when validated empirically:

- chance sampling and Monte Carlo evaluation;
- imperfect-information sampling with correct information boundaries;
- current-hand / continual resolving;
- depth or action pruning with a safe fallback;
- state abstraction or learned generalization;
- value-function approximation at search leaves;
- coarse-to-fine search budgets;
- selective deep search for high-impact or uncertain decisions;
- transposition/canonical-state caching;
- compact global priors refined by local search;
- approximate regret minimization rather than exhaustive tree traversal.

No approximation is accepted solely because it is fast. It must survive strength and correctness tests appropriate to the stage.

## Preferred architecture direction after 06S1

06S1 proved that exact 24-suit canonicalization is lossless but does not create meaningful downstream revisit density for direct global tabular outcome-sampling MCCFR. Therefore direct brute-force scaling of that representation is not the preferred use of compute.

The leading architecture direction is hybrid:

1. an exact rules/scoring/legality core;
2. a compact approximate global policy/value prior learned offline where useful;
3. conditioned current-hand or continual resolving around the actually observed state;
4. selective allocation of more search to strategically sensitive states;
5. cached/canonicalized reuse whenever exact or safely generalized;
6. a robust fallback policy for timeout or low-confidence cases.

This is a working architecture hypothesis, not production authority.

## Experimental discipline

Scientific discipline remains mandatory even though full mathematical perfection is not:

- choose evaluation criteria before looking at candidate payoff when practical;
- separate mechanical/correctness gates from strategic-strength gates;
- preserve exact baselines and reduced-game oracles;
- report compute cost together with strength;
- distinguish source-derived strategies from project adaptations;
- do not promote a component because of sophistication, popularity or theoretical appeal alone;
- retain negative results that close expensive dead ends.

## Stop conditions for an approach

An approach should be deprioritized when one or more of the following persist after a reasonable diagnostic budget:

- negligible learning recurrence or effective sample reuse;
- poor strength-per-wall-clock scaling;
- memory growth incompatible with the target machine;
- online latency incompatible with deployment;
- additional precision fails to improve measured strength materially;
- a cheaper method reaches indistinguishable or better strength across the frozen evaluation suite.

## Production authority

This policy changes the optimization objective, not the certification state.

`REAL = 0/50`

Any production migration remains a separate evidence-based decision.