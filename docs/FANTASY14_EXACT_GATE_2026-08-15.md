# Fantasy-14 exact solver gate — 2026-08-15

This document freezes the first independently certified DeepOFC Fantasy decision kernel.

## Scope

The tested problem is a fully observed 14-card Hero Fantasy terminal decision against a complete opponent board. Hero must choose exactly 13 physical cards, partition them as Top=3 / Middle=5 / Bottom=5, discard one, satisfy the frozen board-aware Joker/foul semantics, and maximize exact raw OFC points.

The optimized solver under test is `deepofc/fantasy_solver.py::evaluate_fantasy_exact_subsets`. The independent reference is the older raw canonical iterator `deepofc/actions.py::iter_fantasy_actions`, with every emitted board scored by the canonical `pairwise_points_standard` evaluator.

## Equality gate

GitHub Actions workflow: `Fantasy14 exact equality gate`

Successful run: **31900723944**

Frozen output:

```text
raw_actions=1009008
valid_actions=344428
subset_best=60
brute_best=60
subset_seconds=3.488627
brute_seconds=76.521251
subset_ties=8
subset_stats=FantasySearchStats(
  incoming_cards=14,
  top_subsets=364,
  five_subsets=2002,
  bottom_middle_pairs=252252,
  middle_order_pruned=126110,
  top_partitions_tested=504568,
  top_order_pruned=160140,
  valid_boards_scored=344428
)
FANTASY14 SUBSET == BRUTE FORCE: PASS
```

The optimized solver and brute-force reference therefore agreed on both:

- exact best current-hand value: **60 raw points**;
- canonical lexicographic best action used for deterministic tie-breaking.

The raw iterator independently visited the expected **1,009,008** canonical Fantasy-14 actions. Of those, **344,428** were non-fouled under the frozen board/Joker rules.

## Performance result

On the same GitHub Ubuntu runner:

- subset solver: **3.488627 s**;
- brute-force solver: **76.521251 s**;
- measured speedup: approximately **21.93x**.

This timing is evidence for this fixture/runner only, not a production latency guarantee.

## What this gate proves

For this full 14-card terminal fixture, the subset solver's pruning does not change the mathematical optimum. It is therefore a valid exact reference kernel for this tested scope.

It does **not** yet prove:

- production latency for arbitrary 14-card states containing Jokers;
- practical latency for 15/16/17-card Fantasy;
- optimal live play while an opponent's final board remains hidden/incomplete;
- infinite-horizon value of re-Fantasy;
- KKPoker cash-cap/rake economics.

Those remain separate gates.
