# M5R target-width best-response budget controller contract

Authority: `RIGOROUS_TARGET_WIDTH_BUDGET_CONTROLLER_NOT_ROUTE_CERTIFICATION`.

M5R-E supplies a rigorous best-response interval for a chosen counterfactual-reach pruning threshold. M5R-F reverses that interface: the caller supplies a maximum tolerated unresolved BR width, and a planner selects the most aggressive threshold in the audited family whose **utility-free worst-case remainder cap** stays within that target.

## Planner inputs

- exact frozen opponent policy probabilities;
- responding player identity;
- chance probabilities and legal game topology;
- a validated terminal utility range `Delta_u`;
- target unresolved BR width `B >= 0`.

The planner must not call `terminal_u0`, exact best response, or expected profile value.

## Width accounting

The planner follows the same pruning points as M5R-E and carries only unresolved counterfactual mass.

For a skipped contribution with mass `r`, its action-value width is at most `r * Delta_u`.

At a responding-player round-4 information set, action widths are accumulated over skipped opponent branches and the information-set value width is bounded by the largest action width.

At a responding-player round-3 information set, direct skipped mass and child round-4 width caps are accumulated by own action; the information-set value width is again bounded by the largest action width.

Summing those round-3 information-set width caps yields a deterministic global upper bound on unresolved BR value. No terminal utility is needed to compute it.

## Threshold selection

Candidate thresholds are the distinct positive counterfactual reaches at which the M5R-E prune set can change, plus zero. Among candidates with guaranteed width cap `<= B`, the planner chooses the largest threshold, which minimizes or ties terminal work within this single-threshold family.

This is an architecture result for the threshold family, not a claim of globally optimal pruning. A future best-first controller may dominate it.

## Validation

On tractable reduced games, a separate fresh M5R-E evaluator must verify:

- actual interval width `<=` planner guaranteed width cap `<=` target width;
- exact BR remains inside the interval;
- cold `terminal_u0` invocation count equals planned resolved terminal work.

Exact reference calculations occur on a separate game instance and are not inputs to the planner.

## Fail-closed boundary

M5R-F does not by itself validate a full-game utility envelope, full-game topology scalability, route-local policy/continuation provenance, statistical profile-value uncertainty, or any M5C route. `REAL = 0/50`.