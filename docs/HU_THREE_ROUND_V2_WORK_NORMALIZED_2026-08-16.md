# HU three-round V2 — work-normalized architecture gate

Date: 2026-08-16

Status: **PASS — external sampling promoted as the primary deep-blueprint solver candidate**

## Purpose

This gate replaces the original reduced-support three-decision benchmark as the architecture-selection benchmark. The original benchmark remains useful as a structural proof, but its reduced chance support allowed a player to infer its own future cards from its current private hand. V2 removes that defect and preserves genuine uncertainty across decisions.

The goal here is deliberately narrow: compare full-tree DCFR and external-sampling MCCFR under the same number of terminal evaluations on a sequential hidden-information OFC benchmark whose future chance is not inferable from the current hand.

## V2 structural reference

The canonical V2 benchmark has:

- 32 independent chance scenarios;
- separate future chance for each player;
- genuine private uncertainty between successive decisions;
- JK1 and JK2 preserved as distinct physical cards;
- 162 legal complete action sequences per player;
- 839,808 terminal leaves in the exact tree;
- exact structural symmetry and structural game value 0.

The exhaustive reference audit visited **839,808 / 839,808** terminals.

Because one external-sampling iteration visits 324 terminal leaves in this benchmark, exactly **2,592 external-sampling iterations = 839,808 terminal visits**. One DCFR full-tree pass also visits exactly 839,808 terminals.

## Exact best-response tribunal

Before comparing solver quality, the V2 evaluator was independently gated for both players.

Workflow run: `31924594639`

| Player | Exact BR | Independent pure-policy replay | Absolute difference |
|---|---:|---:|---:|
| P0 | 6.842906555169804 | 6.842906555169804 | 0.0 |
| P1 | 6.8429065551698055 | 6.8429065551698055 | 0.0 |

The exact BR enumerator uses the canonical fast transition for derived states, while the independent replay executes the chosen pure BR through the fully audited state path. Equality to machine precision therefore validates both the optimized BR traversal and its independently replayed policy.

**Important:** the value ~6.8429 above is a BR/reference value of the benchmark and is **not** the exploitability of either trained strategy.

## Equal-terminal-work comparison

Workflow run: `31924926421`

Both methods trained against exactly **839,808 terminal evaluations**.

| Solver | Training budget | Train terminals | BR0 | BR1 | Exploitability | Train time | Wall time |
|---|---:|---:|---:|---:|---:|---:|---:|
| DCFR current | 1 full-tree pass | 839,808 | 1.843063639191901 | 1.8226029274429423 | **1.8328332833174217** | 275.27 s | 493.15 s |
| External current | 2,592 iterations | 839,808 | 0.3456106696384307 | 0.27572825896894364 | **0.31066946430368714** | 461.83 s | 1,165.10 s |

At identical terminal-evaluation budget:

- external sampling reached only about **16.95%** of DCFR's exploitability;
- equivalently, external sampling reduced exploitability by about **83.05%** versus one-pass DCFR;
- one-pass DCFR remained about **5.90×** more exploitable;
- external sampling was slower in this implementation, about **1.68×** in measured training time and **2.36×** in total wall time, but produced substantially better strategy quality per terminal evaluation.

## Interpretation

This benchmark supports the following architecture decision:

1. **External sampling remains the primary candidate for the deep/global blueprint.** It learned much more useful strategy per terminal evaluation on V2.
2. **DCFR remains valuable for smaller or strongly conditioned subgames**, where full-tree traversals are affordable and repeated passes can exploit exact coverage.
3. Outcome sampling and the sampled-DCFR variant previously tested remain rejected by the existing benchmark evidence.
4. The V1 three-decision benchmark must not be used to reverse this decision; it did not preserve the future private uncertainty now guaranteed by V2.

### Fairness caveat

Equal leaf visits are a valid compute-work normalization for expensive game-tree evaluation, but they are **not identical learning opportunities**. External sampling receives 2,592 sequential regret-update iterations while one-pass DCFR receives one full-tree update pass. Therefore the precise claim is:

> Under the current implementations and settings, external sampling gives much better strategy quality per terminal evaluation on V2.

This gate does not claim that one DCFR pass and 2,592 external iterations are algorithmically identical training processes.

A future non-blocking sensitivity curve — for example DCFR at 1/2/4 passes against external at 2,592/5,184/10,368 iterations — can quantify scaling behavior, but it is not required before proceeding with OpenHoldem integration.

## Project decision

The V2 architecture gate is closed as **PASS**.

The strategic layer is not declared globally finished and R6 is not promoted to production solely from this benchmark. However, the solver-architecture uncertainty is no longer a reason to hold back the OpenHoldem branch.

**OpenHoldem/KKPoker OFC integration may now proceed in parallel while deeper blueprint/off-tree work continues.**
