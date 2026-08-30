# EXT-06R1D — R4 multi-fixture discrimination

Status: **FROZEN BEFORE 06R1D RESULTS**

Authority: `BELIEF_CORRECT_R4_MULTIFIXTURE_DIAGNOSTIC_ONLY`

06R1 mechanically passed but its single payoff-blind fixture was strategically degenerate: all six exact root-action values were 0.0. Therefore the IS-UCT/MCCFR tie cannot rank algorithms.

06R1D changes only the fixture breadth. It does not alter either learner, the exact posterior construction, scoring, legal actions, canonicalization, terminal budgets, learner seeds, or ranking tolerance.

## Frozen fixture suite

Use four payoff-blind R4 P0 roots generated exactly by `build_conditioned_fixture` with:

- `R4D_64011`: fixture seed 64011
- `R4D_64012`: fixture seed 64012
- `R4D_64013`: fixture seed 64013
- `R4D_64014`: fixture seed 64014

All are `round_index=4, actor=0`.

The suite is fixed by seed before any 06R1D payoff is observed. **No fixture may be removed, replaced, repeated, or selected because its oracle is more interesting.** Degenerate fixtures remain in the report.

## Belief and oracle

For every fixture, use the exact legal-information posterior under the same frozen payoff-blind prefix policy used by 06R1.

For every root action, enumerate the complete R4 posterior and compute the exact P1 best response by P1 information state. Report the complete root-action value vector and its spread:

`oracle_action_value_spread = max(value) - min(value)`.

A fixture is strategically discriminative iff spread `> 1e-12`. This label is descriptive only and may not be used to discard the fixture.

## Learners and budgets

Unchanged from 06R1:

- IS-UCT: exploration 2.0
- MCCFR: epsilon 0.6, CFR+ enabled, average root policy
- learner seeds: 20260830 and 20260831
- terminal budgets: 256, 1024, 4096
- exact regret tolerance: 1e-9

## Ranking

Per fixture/seed/final-budget cell:

- MCCFR wins iff `regret_MCCFR + 1e-9 < regret_ISUCT`;
- IS-UCT wins iff symmetric;
- otherwise tie.

Cross-fixture promotion is permitted only if at least **two of the four frozen fixtures are discriminative**.

Among discriminative fixtures only, one method may be promoted toward R3 if:

1. it is never strictly worse in any discriminative fixture/seed final cell; and
2. it is strictly better in at least two final cells spanning at least two different discriminative fixtures.

Otherwise verdict is `NO_R4_MULTIFIXTURE_WINNER_CONTINUE_PRACTICAL_HYBRID`.

The degenerate fixtures remain part of the artifact and count against claims of fixture representativeness, but cannot create a strategic win because all policies have equal oracle value there.

## Cost discipline

Exact oracle construction dominates runtime. Run the four fixtures as independent parallel CI jobs. Do not increase the fixture count or oracle budget after results.

## Authority firewall

No production migration, no REAL route, no Fantasy valuation claim, and no full-game equilibrium claim. `REAL = 0`.