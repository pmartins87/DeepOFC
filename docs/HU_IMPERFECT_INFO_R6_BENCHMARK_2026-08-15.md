# R6 HU imperfect-information architecture benchmark — 2026-08-15

This document freezes the first DeepOFC solver-architecture benchmark that contains real OFC placement decisions, private cards, a hidden discard and strategic response while still having an independently known reference value and exact best-response evaluation.

It is deliberately a **small final-round HU subgame**, not a claim that the full KKPoker Joker Ultimate game has already been solved.

## 1. Why this benchmark exists

R5 established exact terminal scoring/search anchors. R6 needs a different kind of ground truth: an imperfect-information game on which candidate equilibrium algorithms can be compared by **exact exploitability**, not by training loss or self-play score.

The benchmark therefore has four requirements:

1. actions are actual legal OFC `place two / discard one` actions;
2. information sets merge physically different hidden histories;
3. terminal utility is the canonical DeepOFC raw pairwise scorer;
4. the game has a mathematically known reference value and an exact best-response evaluator.

## 2. Frozen subgame

Implementation: `deepofc/hu_subgame.py`.

Both players begin the last normal round with eleven committed cards. Bottom is already full; Top and Middle each have exactly one free slot. Each player privately receives three cards, places one in Top, one in Middle, and discards the third.

The first actor's two confirmed placements are visible before the second actor decides. The first actor's discarded card is **not** revealed. Thus the second actor knows the public placements but not which of the remaining physical cards was discarded or left undealt.

### Fixed boards

Player 0:

```text
Top:    2c 2h _
Middle: 4c 4h 5c 6c _
Bottom: 8c 9c Tc Jc Qc
```

Player 1 is the exact suit mirror:

```text
Top:    2d 2s _
Middle: 4d 4s 5d 6d _
Bottom: 8d 9d Td Jd Qd
```

Chance pool:

```text
Kc Kd Kh Ks Ac Ad Ah As
```

For every chance outcome:

- P0 receives an unordered three-card hand;
- P1 receives an unordered three-card hand from the five remaining cards;
- two cards remain undealt;
- chance independently chooses whether P0 or P1 acts first.

This produces exactly **1,120 equiprobable chance outcomes**.

Every private three-card hand has exactly **6 legal actions**: choose which card goes to Top, which goes to Middle, and which is discarded.

The complete game has **2,352 information sets** in the current representation. Of the second-player information sets, **2,240 merge more than one physically distinct hidden history**, proving that this is not a perfect-information placement toy.

## 3. Why the fixture avoids unresolved rules

The first version of the benchmark used rows that could create a foul when an Ace was placed on Top and a King on Middle. Some chance branches then produced both-player foul, correctly reaching DeepOFC's fail-closed `NotImplementedError` because the exact KKPoker both-player-foul settlement has not yet been source-frozen.

The benchmark was **changed rather than inventing that rule**.

With the frozen boards above:

- Top is always at least a pair of 2s;
- Middle is always at least a pair of 4s;
- Bottom is always a Q-high straight flush;
- no K/A placement can foul;
- no branch enters Fantasy.

The architecture experiment therefore stays entirely inside already certified scoring semantics.

## 4. Exact reference value = 0

The game has a physical automorphism:

```text
swap P0 <-> P1
mirror suits c <-> d and h <-> s
flip which player acts first
```

The chance support is invariant under that transformation, legal actions map bijectively, information structure maps bijectively, and terminal utility changes sign.

Therefore the two-player zero-sum game has exact reference value:

```text
V* = 0
```

`HUFinalRoundSubgame.assert_terminal_swap_symmetry()` exhaustively checks every terminal branch under this transformation:

```text
1,120 chance outcomes × 6 first actions × 6 second actions
= 40,320 terminal symmetry checks
```

All **40,320 / 40,320** passed in the certified workflow.

## 5. Exact best response and exploitability

Because each player acts exactly once in this reduced subgame, a pure best response to any fixed behavioral profile can be computed exactly by aggregating all indistinguishable physical histories at each information set and maximizing the full counterfactual value there. No Monte Carlo is used in evaluation.

Metrics are frozen as:

```text
BR0 = best-response payoff available to P0
BR1 = best-response payoff available to P1 in P1's own utility
NashConv = BR0 + BR1
Exploitability = NashConv / 2
```

The uniform strategy is symmetric and therefore has expected value zero, but it is highly exploitable:

```text
expected_u0 = 0
BR0 = 0.428571428571
BR1 = 0.428571428571
exploitability = 0.428571428571
```

That gives the algorithms a nontrivial starting point while preserving exact game value zero.

## 6. Full-tree CFR+ and DCFR

Implementation: `deepofc/hu_cfr.py`.

The deterministic full-tree solver traverses every physical chance/action branch each iteration. Regret deltas are aggregated over the entire iteration before CFR+ clipping. Exact counterfactual opponent/chance reach is used. Average strategy is accumulated independently of the exact best-response evaluator.

Certified workflow:

```text
HU imperfect-info CFR architecture
run 31902833212
```

### CFR+

| Iterations | Exact exploitability |
|---:|---:|
| 1 | 0.428571428571 |
| 2 | 0.142857142857 |
| 4 | 0.042857142857 |
| 8 | 0.011904761905 |
| 16 | 0.003151260504 |
| 32 | 0.000811688312 |
| 64 | 0.000206043956 |
| 128 | 0.000051910299 |
| 256 | **0.000013028071** |

Training-only time through 256 iterations on the frozen GitHub Ubuntu runner:

```text
42.636661 s
10,321,920 terminal evaluations
```

The exact evaluation checkpoints themselves consumed a separate **2.413395 s** and are not included in the training-only figure.

### DCFR

Default benchmark parameters are `alpha=1.5`, `beta=0`, `gamma=2`.

| Iterations | Exact exploitability |
|---:|---:|
| 1 | 0.428571428571 |
| 2 | 0.085714285714 |
| 4 | 0.014285714286 |
| 8 | 0.002100840336 |
| 16 | 0.000286478228 |
| 32 | 0.000037462537 |
| 64 | 0.000004791720 |
| 128 | 0.000000605957 |
| 256 | **0.000000076188** |

Training-only time through 256 iterations:

```text
42.995676 s
10,321,920 terminal evaluations
```

Exact evaluation checkpoints consumed a separate **2.414413 s**.

On this particular small tree, DCFR therefore dominates CFR+ strongly in convergence at essentially the same full-tree computational cost.

This is **not yet** evidence that DCFR full-tree is the production architecture: its per-iteration cost grows with the entire chance/action tree.

## 7. External-sampling MCCFR

Implementation: `deepofc/hu_mccfr.py`.

One global iteration performs one traversal for each player. Chance and the non-traversing player's action are sampled; all actions at the traverser's reached information set are enumerated.

The solver is deterministic under a fixed seed. Regret updates from both traversers are aggregated before they are applied.

### Average-strategy audit

An early benchmark version had a one-iteration offset in the lazy average-strategy accumulator: the traversal correctly used the pre-update strategy, but the average credited the post-update strategy to that same iteration.

This was corrected in commit `7deed15b55341263c2cc3190c1161b548b9fffc4`. A regression test now requires that after exactly one completed iteration, the average profile remains **exactly the initial uniform profile**, because that is the only strategy that was actually used during iteration 1.

The CI containing that explicit gate passed in run **31902955179**.

### Corrected single-seed benchmark

Seed: `20260815`.

Certified workflow run: **31902939414**.

| Iterations | Exact exploitability |
|---:|---:|
| 100 | 0.363396949405 |
| 500 | 0.256433304578 |
| 2,000 | 0.162460804147 |
| 10,000 | 0.060850523925 |
| 50,000 | **0.013472149428** |

Training-only time through 50,000 iterations:

```text
7.999973 s
~600,000 sampled terminal evaluations
```

Exact checkpoint evaluations consumed a separate **1.814217 s**.

MCCFR is substantially noisier and converges more slowly in exploitability on this tiny game, but it touches only a sampled fraction of the tree per iteration. That scaling distinction is the reason it remains an important candidate for larger DeepOFC subgames.

## 8. Corrected ten-seed MCCFR calibration

Certified workflow:

```text
HU external-sampling MCCFR multi-seed
run 31902939418
```

Ten deterministic seeds were evaluated at 2k / 10k / 20k iterations.

| Iterations | Mean exploitability | Median | P95 / max | Mean training time |
|---:|---:|---:|---:|---:|
| 2,000 | 0.165371618990 | 0.165792607381 | 0.168383110119 | 0.341 s |
| 10,000 | 0.060970259810 | 0.060973486528 | 0.062728391440 | 1.717 s |
| 20,000 | **0.033331994488** | 0.033282879784 | **0.034406383220** | 3.417 s |

At 20k iterations, the mean absolute deviation of the profile's own expected value from the exact zero game value was only **0.000392599337**, while exploitability remained roughly **0.0333**. This is a useful warning: being close to the game value in self-play is not evidence of being hard to exploit. Exact best response is the stronger metric.

## 9. Work-normalized interpretation

On this small benchmark:

- DCFR at 8 full-tree iterations used about **322,560 terminal evaluations**, trained in about **1.33 s**, and reached exploitability **0.002100840336**;
- external-sampling MCCFR at 10k iterations used about **120,000 sampled terminal evaluations**, trained in about **1.62 s** in the corrected single-seed run, and reached exploitability **0.060850523925**;
- at 20k iterations / about **240,000 sampled terminal evaluations**, ten-seed MCCFR mean exploitability was **0.033331994488**.

Thus full-tree DCFR is vastly more sample-efficient on the current tractable tree. The result does **not** establish a global architecture winner, because full traversal becomes impossible long before the complete Joker Ultimate game tree is represented.

The practical implication is a hybrid research direction rather than an immediate winner declaration:

1. use exact/full-tree DCFR wherever the resolved subgame is genuinely tractable;
2. keep sampling methods for larger hidden-information regions where exhaustive traversal is no longer feasible;
3. measure both against exact or independently strong best-response references at every size increase;
4. only introduce learned value/policy approximation when search itself becomes the measured bottleneck.

## 10. What this benchmark proves

It proves that DeepOFC now has:

- a real OFC HU imperfect-information benchmark rather than a poker-themed toy;
- exact structural reference value **0**;
- exhaustive payoff-symmetry validation over **40,320** terminals;
- exact best-response / NashConv / exploitability measurement;
- deterministic full-tree CFR+ and DCFR implementations;
- deterministic external-sampling MCCFR;
- multi-seed sampling calibration;
- a regression gate for a subtle average-strategy timing error found during audit.

## 11. What it does not prove

This benchmark intentionally excludes:

- Jokers;
- Fantasy/re-Fantasy;
- fouls;
- KKPoker rake/cap/economics;
- 3-player play;
- early streets;
- repeated decisions by the same player.

The last limitation is now the most important R6 issue. Because each player acts only once, the exact best-response routine and the MCCFR averaging simplifications are specialized to this benchmark. They must **not** be silently generalized to a deeper game.

The next R6 benchmark must contain at least two decisions by a player, preserve perfect recall/private-discard information, and independently validate exploitability before architecture selection advances.
