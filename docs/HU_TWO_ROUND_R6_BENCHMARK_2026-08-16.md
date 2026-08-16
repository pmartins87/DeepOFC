# R6 — HU two-round imperfect-information benchmark — 2026-08-16

Status: **active architecture evidence, not final production architecture**.

This document freezes the second/deeper R6 benchmark program and the stronger
hidden-discard audit that followed it. The purpose is to choose algorithms from
measured exploitability against exact best response, not from poker analogy,
training loss or self-play value alone.

## 1. What this benchmark is trying to prove

The first R6 benchmark had one decision per player on the final normal OFC
street. It was useful for certifying the extensive-form representation, exact
best response and CFR-family kernels, but it was too shallow to expose the cost
of repeated private decisions.

The deeper benchmark therefore requires:

- two decisions by each player;
- perfect recall of the player's own private round-3 action/discard;
- public observation of confirmed opponent placements;
- new private round-4 cards;
- hidden opponent information merged inside information sets;
- exact terminal scoring through the canonical OFC evaluator;
- a structural exact value of zero from a rank-preserving player/suit
  automorphism;
- an exact best-response evaluator independently replayed through the full game
  tree.

The benchmark remains reduced: it is a laboratory for architecture, not a claim
that the full KKPoker Joker OFC game has been solved.

## 2. Benchmark B — first two-decision fixture

`deepofc/hu_two_round.py` freezes the first repeated-decision game.

Exact structural facts:

- chance outcomes: **32**;
- information sets: **79,804**;
- round-4 information sets merging distinct hidden histories: **7,056**;
- terminal histories: **373,248**;
- terminal swap/suit symmetry checks: **373,248 / 373,248**;
- exact structural game value: **0**;
- uniform-strategy expected value: **0**;
- uniform BR0 = BR1 = **2.099206349206**;
- uniform exploitability = **2.099206349206**.

The deep exact BR was cross-checked by materializing the pure response it found
and evaluating that response through the complete game tree. It was also
validated on a deterministic strongly asymmetric behavioral profile, not only
on the symmetric uniform profile.

### Important audit finding

This fixture correctly hides the discard field from the opponent's information
set, but its two round-3 private-hand variants use disjoint suit patterns. Under
that reduced support, a public two-card placement can reveal which three-card
private hand was dealt and therefore make the discarded card inferable.

That does **not** invalidate this fixture as a repeated-decision/perfect-recall
benchmark: round-4 private cards remain hidden and many histories still merge.
It does mean the fixture must not be cited as proof of strategic ambiguity of
round-3 hidden discards.

That finding caused Benchmark C below to be added rather than weakening the
audit criterion.

## 3. Benchmark C — overlapping-support hidden-discard fixture

`deepofc/hu_two_round_hidden_discard.py` changes only the reduced private-card
support needed to make the same public state physically compatible with
different discards.

Player 0 round-3 support:

- `6c 7c 8c`
- `6c 7c 8d`

Player 1 is the rank-preserving suit mirror:

- `6h 7h 8h`
- `6h 7h 8s`

Thus, for example, the public placement `6c/7c` can coexist with either hidden
discard `8c` or `8d`. The automorphism remains suit-only (`c<->h`, `d<->s`), so
poker rank order is never changed.

Exact certification:

- chance outcomes: **32**;
- information sets: **66,504**;
- merged round-4 information sets: **17,976**;
- terminal histories: **373,248**;
- terminal symmetry checks: **373,248 / 373,248**;
- uniform expected value: **0**;
- public states under uniform support: **2,450**;
- hidden histories represented in those public states: **14,112**;
- public states compatible with multiple distinct discard pairs: **882**;
- maximum distinct discard pairs behind one public state: **4**;
- uniform BR0 = BR1 = **2.099206349206**;
- uniform exploitability = **2.099206349206**.

The exact BR was again audited off symmetry. On a deterministic non-uniform
profile:

- profile EV0 = **-0.016602563000**;
- BR0 = **2.396192856732**;
- BR1 = **2.449981450557**;
- exploitability = **2.423087153644**;
- both BR values were reproduced exactly by full-tree evaluation of the
  materialized pure responses.

This is the current strongest exact HU R6 tribunal.

## 4. Full-tree DCFR versus external-sampling MCCFR

### Full-tree DCFR on Benchmark C

Parameters remain the previously certified DCFR defaults:

- alpha = 1.5;
- beta = 0;
- gamma = 2.

At 8 iterations:

- exploitability = **0.044624397410**;
- BR0 = BR1 = **0.044624397410**;
- isolated training time = about **85.93 s** on the recorded GitHub runner;
- exact evaluation time = about **20.97 s**.

Full-tree DCFR still converges rapidly per iteration, but each iteration pays
for the whole tree.

### External sampling on Benchmark C

At 5,000 iterations, seed `20260815`:

- expected EV0 = **+0.000004506287**;
- BR0 = **0.012613882284**;
- BR1 = **0.015573548227**;
- exploitability = **0.014093715255**;
- isolated training time = about **69.93 s**;
- exact evaluation time = about **21.52 s**.

This beats full-tree DCFR@8 in both measured exploitability and isolated
training time on the stronger hidden-discard fixture.

Five-seed 5k calibration:

| Seed | Exploitability |
|---:|---:|
| 1954132610 | 0.036887933309 |
| 372483540 | 0.036955546629 |
| 20260815 | 0.014093715255 |
| 12345 | 0.025634016464 |
| 917331 | 0.029197436756 |

Summary:

- mean = **0.028553729683**;
- median = **0.029197436756**;
- min = **0.014093715255**;
- max / conservative p95 over these five seeds = **0.036955546629**.

All five seeds remain below full-tree DCFR@8 exploitability
**0.044624397410**. Seed 20260815 is nevertheless materially better than the
five-seed mean, so it must not be treated as representative by itself.

Current interpretation: **external sampling is the strongest measured deep-HU
blueprint candidate at this tree size**, while full-tree DCFR remains valuable
for smaller/late subgames.

## 5. Outcome sampling — mathematically correct, empirically rejected here

The outcome-sampling implementation was not benchmarked before its estimator
was audited.

Exact expectation gate at the uniform state:

- sampled terminal histories integrated: **746,496**;
- regret action entries compared: **413,148**;
- maximum absolute difference versus the corresponding full-tree first-step
  regret update: **2.89e-15**.

Thus the implementation reproduces the intended regret update in expectation to
floating-point precision on this exact game.

Performance at 500,000 iterations = exactly 1,000,000 training terminal
histories:

- current-profile exploitability = **0.324920058955**;
- training time = about **647.04 s**.

Outcome sampling is therefore retained as a certified negative result for this
regime, not as a production candidate.

## 6. Strategy export: current versus CFR averages

Repeated own decisions make a simple local time average theoretically wrong for
standard CFR averaging. A separately implemented own-reach-weighted average was
therefore certified against a brute reference.

Five-iteration exact cross-check:

- information sets: **79,804**;
- action probabilities compared: **413,148**;
- standard reach-weighted average max error: **1.11e-16**;
- linear-in-iteration reach-weighted average max error: **2.22e-16**.

At 5,000 external-sampling iterations on Benchmark B, exact BR gives:

| Exported profile | Exploitability |
|---|---:|
| current regret-matching profile | **0.012517507003** |
| linear reach-weighted CFR average | **0.048175301430** |
| standard reach-weighted CFR average | **0.168649957747** |

The linear average removes much of the early-policy contamination but remains
far weaker than the current profile at this finite budget. The current profile
is therefore the strongest **empirical** export at 5k on this benchmark.

This is not a claim of last-iterate convergence. A longer 5k/10k/20k multi-seed
campaign is running specifically to test whether current-profile exploitability
continues to improve or oscillates.

## 7. Lazy sampled-DCFR — exact mechanism, negative strategic result

A separate candidate combined external sampling with DCFR-style regret
discounting. To preserve sampling scalability, skipped discounts are collapsed
lazily by per-infoset timestamp instead of scanning every information set every
iteration.

Mechanism certification:

- collapsed discount over iterations 3..37 matches sequential multiplication to
  about **1.33e-15**;
- pure skipped discount changes regret-matching strategy by exactly **0**;
- first-iteration traversal/update identity with ordinary external sampling is
  regression-gated because the first DCFR discount acts only on zero regrets.

Benchmark C at 5,000 iterations, seed 20260815:

- exploitability = **0.042376158240**;
- training time = about **144.52 s**;
- exact evaluation time = about **65.64 s** on that isolated run.

Comparison:

- standard external sampling: **0.014093715255**;
- lazy sampled-DCFR: **0.042376158240**;
- full-tree DCFR@8: **0.044624397410**.

The sampled-DCFR candidate is therefore **rejected for this regime**. The
full-tree discount schedule that is very effective on exact full-tree regrets
does not transfer well enough to the noisier sampled regret stream here.

## 8. Public-state continual re-solving

`deepofc/hu_two_round_resolve.py` conditions the exact round-4 continuation on
what is genuinely public after round 3:

- first actor identity/order;
- both players' confirmed public round-3 placements.

The public key deliberately excludes:

- both private round-3 hands;
- both round-3 discards;
- both future/private round-4 hands.

Hidden histories receive exact posterior weights from chance and the blueprint's
round-3 behavioral probabilities.

### Reachable-state re-solving on Benchmark C

For the external-sampling 5k current blueprint:

- only **39** public states have positive blueprint reach;
- **38 / 39** already have exact local continuation exploitability zero;
- one state remains locally exploitable.

That state:

- public reach about **0.001588688880**;
- hidden histories = **4**;
- continuation information sets = **26**;
- local exploitability before = **0.001418240758**;
- local exploitability after DCFR-256 = **0.000000118514**;
- resolve time about **0.99 s** in Python on the recorded runner.

Stitching the solved continuation back into the complete blueprint and then
running the **full-game exact best response** changes global exploitability:

- before = **0.014093715255**;
- after = **0.013739169880**;
- delta = **-0.000354545375**.

Resolving all 39 reachable public states produces the same result because only
that one state needed replacement. Total continuation-resolve time in that run
was about **1.15 s**.

Interpretation: late continual re-solving is useful, but the remaining
exploitability is not primarily a final-street problem. Most remaining error is
upstream in round-3 strategy/beliefs.

## 9. Off-tree belief problem

A current regret-matching policy can contain exact zero-probability actions. On
Benchmark C:

- uniform support yields **2,450** compatible public states;
- the 5k current blueprint reaches only **39**.

An opponent can deviate into a public history to which the blueprint assigns
zero probability. Ordinary Bayes conditioning on the current blueprint then has
no posterior to use for runtime re-solving.

An explicit experiment is running with a **belief-only 1% uniform tremble**:

`belief = 0.99 * current + 0.01 * uniform`.

The actual round-3 play policy remains the original current blueprint. The
purpose of the tremble is only to define full-support posterior beliefs for
round-4 re-solving. Every resulting continuation is stitched back into the
original blueprint and judged by exact full-game best response. No promotion is
allowed merely because local subgame values improve.

Result: **pending at time of this document revision**.

## 10. Current R6 architecture interpretation

Evidence now supports a hybrid direction, not one monolithic solver:

1. keep canonical rule/scoring/action/Fantasy kernels exact and authoritative;
2. use **external-sampling MCCFR** as the leading measured candidate for deeper
   HU blueprint computation once full-tree traversal becomes expensive;
3. use **full-tree DCFR** where the conditioned subgame is small enough that
   exact traversal is cheap;
4. use public-state continual re-solving as a **complement** to the blueprint,
   not as a substitute for getting early-round strategy right;
5. reject outcome sampling and the tested lazy sampled-DCFR schedule for the
   measured regime;
6. do not export a CFR average merely because of asymptotic theory when exact BR
   shows that the finite-budget current profile is materially stronger;
7. treat off-tree beliefs as an explicit safety problem rather than silently
   normalizing zero-reach histories;
8. keep 3-player OFC separate: multiplayer zero-sum does not inherit the
   two-player CFR guarantees automatically.

This is still **not** a final production architecture decision.

## 11. Remaining gates before R6 can be promoted further

- finish 5-seed 5k/10k/20k last-iterate convergence curves;
- finish the trembled-belief off-tree re-solving exact-BR gate;
- build a still deeper/earlier-round benchmark or complete sequential HU engine
  so architecture is not selected solely from the last two normal streets;
- introduce Joker-containing stochastic states after exact Joker semantics are
  retained by the benchmark;
- measure memory and CPU scaling, not only exploitability;
- define a production-safe belief mechanism for zero-blueprint-reach public
  histories;
- only then test depth-limited / learned value continuation if exact/search
  continuation becomes the bottleneck;
- treat 3-player training/evaluation as its own R6 track.

## 12. Reproducibility principle

Every R6 candidate is evaluated by an external reference whenever tractable:

- exact structural symmetry/value;
- exact full-game best response;
- independent replay of best-response pure policies;
- exact estimator/averaging cross-checks where applicable;
- isolated algorithm workflows so warm caches do not masquerade as algorithmic
  speedups.

A solver is not promoted because its internal loss decreases or because it wins
against itself.
