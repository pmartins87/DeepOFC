# Real Fantasy-15 frame53 strategy gate — 2026-08-15

This document freezes the first DeepOFC decision benchmark taken directly from a user-supplied KKPoker Joker Ultimate Fantasy state rather than a synthetic strategy fixture.

## Source state

Fixture: `fixtures/replay/fantasy_frame000053.json`

Hero 15-card Fantasy fan:

```text
JK1 JK2 Ac Kd Qc Qd Js 9s 9h 7s 6h 4s 4c 3s 2c
```

Opponent visible completed board:

```text
Top:    Ah Jc 8h
Middle: 6s 5c 4h 3h 2h
Bottom: 9d 8d 6d 4d 2d
```

Observed Hero tentative placement in the real frame:

```text
Top:    Ac Kd 6h
Middle: Qc Qd 9h 4s 4c
Bottom: JK1 JK2 Js 9s 7s
Unused: 3s 2c
```

Under the frozen board-aware Joker evaluator this resolves to:

- Top: A-K-6 high;
- Middle: Queens and Fours, Two Pair;
- Bottom: J-high Straight Flush;
- raw current-hand result versus the visible opponent: **8 points**;
- re-Fantasy qualification: **yes**.

## Exact V1 result

Workflow: `Real Fantasy15 dual-Joker benchmark`

Successful run: **31900847707**

Exact V1 optimum:

```text
Top:    Qc Qd 6h
Middle: Js 9s 7s 4s 3s
Bottom: JK1 JK2 Ac 4c 2c
Unused: Kd 9h
```

Resolved ranks:

- Top: pair of Queens, kicker 6;
- Middle: J-high Flush;
- Bottom: 5-high Straight Flush;
- raw current-hand result: **28 points**;
- re-Fantasy qualification: **yes**.

Measured V1 search time on the GitHub Ubuntu runner: **59.073160 s**.

Search counters:

```text
bottom_middle_pairs=756756
middle_order_pruned=139300
top_partitions_tested=6174560
top_order_pruned=1014430
valid_boards_scored=5160130
```

Thus, for the current-hand raw scoring objective, the exact optimum gains **20 raw points** over the arrangement visible in the supplied frame.

This is not yet a claim of +20 infinite-horizon EV: the exact value/card-count transition of every re-Fantasy path is not fully source-frozen. Both the observed arrangement and the exact optimum do qualify for re-Fantasy.

## Exact V2 result

Workflow: `Fantasy15 exact v2 benchmark`

Successful run based on commit `5e6599c7ff9f26435726cf90bdd1f801eb40ad6a`.

V2 returned the same exact current-hand optimum value: **28 points**. Its representative optimal board was:

```text
Top:    Kd Qc Qd
Middle: Js 9s 7s 4s 3s
Bottom: JK1 JK2 Ac 4c 2c
Unused: 9h 6h
```

This differs from the V1 representative only inside an exact-EV tie. V2 intentionally prefers the strongest achievable Top for each fixed Bottom/Middle pair, whereas V1 eventually applies lexical `action.key()` tie-breaking. The canonical scorer independently reproduces **28 points** for the V2 board.

Measured V2 time: **18.882915 s**.

V2 counters:

```text
bottom_middle_pairs=756756
middle_order_pruned=139300
top_frontiers_built=3003
top_rank_queries=617456
top_rank_query_pruned=9585
valid_boards_scored=607871
```

The V2 transformation therefore reduced the repeated terminal evaluations by roughly an order of magnitude while preserving the exact optimum value. Relative to the V1 timing from the same GitHub runner class, the measured speedup is about **3.13x**.

## Interpretation

This gate proves that DeepOFC can already solve a real supplied 15-card, two-Joker, fully observed Fantasy terminal state exactly under the frozen current-hand rules.

It does not yet prove production readiness. The remaining mathematical issues include:

- exact infinite-horizon re-Fantasy continuation values/card-count paths;
- incomplete/hidden opponent boards while Hero may pre-arrange Fantasy;
- 16/17-card runtime latency;
- broader independent equality/property validation with Jokers;
- eventual KKPoker cap/rake economics.
