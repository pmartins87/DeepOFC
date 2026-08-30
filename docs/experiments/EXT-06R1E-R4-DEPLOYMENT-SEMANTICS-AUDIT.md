# EXT-06R1E — R4 deployment-semantics audit

Date: 2026-08-30
Branch: `research/external-ofc-solver-audit-20260827`
Authority: diagnostic / interpretation only
REAL routes certified: **0**

## Why this gate exists

06R1D precommitted four R4 one-decision fixtures and required investigation rather than promotion if the mixed-policy winner disagreed across discriminative fixtures. That branch fired.

The investigation found that the apparent disagreement is not evidence that one learner chooses a worse final R4 move. In this benchmark P0 chooses one public Pineapple action, P1 observes that realized action, and the exact oracle then minimizes P0 utility over P1's legal response. Therefore, for this final public decision, the operational action-selection quantity is the exact value of the action actually selected. Residual probability mass in a training/search distribution is a different diagnostic quantity.

06R1D's two policy objects are also not semantically identical:

- ISUCT `root_policy` is normalized root visit frequency;
- MCCFR `root_policy` is the normalized accumulated average strategy;
- both solvers additionally have an argmax/final-action notion.

Directly using expected oracle value under those two different training distributions as the sole promotion metric is therefore not a sound tie-breaker for a greedy one-decision R4 deployment.

## Frozen 06R1D evidence re-read

Artifact ZIP SHA-256 values:

- fixture 64011: `25cc06df0551fc43c9645446bd629cfb87a12138cad053e79569ffc9ec786f86`
- fixture 64012: `1b23adfe3d7c299e98a6a7b5d3bf251eb7743d329c21599f4edb8fd8cf10d43d`
- fixture 64013: `978b47aa4527a24f555006f757cca46a4aab26be9a95540d5abb12636fb5403d`
- fixture 64014: `13f85c5d0d52e5aab1e7834565a9098472f1c881f394dc6f694bdf4899facc87`

Structural discrimination:

| fixture | exact oracle spread | discriminative |
|---|---:|---|
| 64011 | 6.0 | yes |
| 64012 | 0.0 | no |
| 64013 | 8.440607447472436 | yes |
| 64014 | 0.0 | no |

On **both discriminative fixtures**, for **both learner seeds**, at every frozen budget **256 / 1024 / 4096**, both ISUCT and MCCFR have:

`exact_local_top_action_regret = 0.0`

Thus every tested final top action is oracle-optimal. The mixed-policy metric still differs because each method leaves a different amount of probability mass on inferior actions, but 06R1E does not treat that residue as evidence of an inferior greedy R4 decision.

Fixture 64011 also exposes a diagnostic bug in `oracle_best_action_agreement`: the oracle has two tied best actions, while the boolean compares the learner top action against only one canonical `best_action_key`. A tied-best action can therefore be marked `false` despite exact top-action regret being zero. The value-based regret itself is tie-safe and remains authoritative for action quality.

## 06R1E verdict

**NO_METHOD_PROMOTION_FROM_06R1D**

Reason:

1. only 2/4 fixtures are strategically discriminative;
2. on those two fixtures both methods select an exact oracle-optimal top action in every tested cell;
3. the apparent cross-fixture winner conflict comes from mixed-distribution residue, not from final-action error;
4. 06R1D starts too late (budget 256) to measure which method reaches an oracle-optimal action sooner.

The old mixed-policy result is preserved as a secondary diagnostic and is not deleted or rewritten.

## Frozen next gate: 06R1F

06R1F is a precommitted sample-efficiency benchmark with **12 fixture seeds fixed before seeing any oracle result**:

`65101..65112`

Budgets:

`32, 64, 128, 256, 512, 1024 terminal evaluations`

Learner seeds remain exactly those frozen by 06R1: `20260830, 20260831`.

Primary metric: `exact_local_top_action_regret`, with oracle-optimal success when regret `<= 1e-9`.

For each discriminative fixture × learner seed × method, define **stable-hit budget** as the smallest tested budget at which top-action regret is `<= 1e-9` and remains `<= 1e-9` at every larger tested budget.

A method may be promoted only if all conditions hold:

1. at least **6 of 12** fixtures have exact oracle spread `> 1e-12`;
2. the method has at least **4 strict stable-hit wins** across discriminative fixture × learner-seed pairs;
3. its strict-win count is at least **2×** the competitor's strict-win count;
4. the win direction does not reverse by learner seed: within each learner seed, its strict wins are at least the competitor's;
5. its oracle-optimal top-action hit rate at budget 1024 is not lower than the competitor's.

Otherwise the result is **NO_PROMOTION**. Mixed-policy regret is secondary diagnostic only and cannot break an operational top-action tie.

This rule is frozen before any 06R1F oracle output is observed.

## Post-freeze oracle implementation discovery

The first 06R1F execution exposed a separate implementation issue before any aggregate result could be interpreted. Fixture `65109` stopped at the exact-oracle firewall with:

`AssertionError: R4 P1 infoset spans multiple posterior worlds`

This failure was valuable: the reference belief-correct oracle in `external_06r1_belief_correct.py` already has the correct semantics — it groups posterior worlds by P1 information state and lets P1 choose one response per infoset. The memoized/direct accelerator in `r4_exact_oracle_cached.py` had added a stronger assumption that every P1 infoset uniquely identified one posterior world. That assumption is false in general.

Why it matters: if multiple worlds share the same P1 infoset, minimizing separately inside each world would grant P1 knowledge of hidden information it does not possess. The safe assertion prevented such leakage, but it also proved that the accelerator was not universally semantics-preserving.

The cached oracle has therefore been corrected to reproduce the original grouped best-response calculation while retaining board-resolution memoization and direct world materialization. A dedicated regression compares the corrected accelerator against the original reference oracle on fixture `65109`, specifically because that fixture contains many-worlds-per-P1-infoset structure.

Consequences for provenance:

- **06R1F run 1 is non-authoritative and cannot be aggregated**; it used the old cached-oracle implementation and was interrupted by its own safety assertion.
- **06R1F v2** is explicitly bound to `P1_INFOSET_GROUPED_BEST_RESPONSE_V2`.
- The 06R1D fixtures that completed under the old accelerator satisfied its one-world-per-P1-infoset assertion. On those particular fixtures, grouping and per-world minimization are mathematically identical, so this discovery does not retroactively change their exact action values; it does show that those fixtures were a special subset and cannot justify the uniqueness assumption globally.
- No method promotion is allowed until the grouped-oracle regression passes and the complete 12-fixture 06R1F v2 suite is available.

## Scope firewall

06R1E/06R1F are external solver-selection experiments. They do not modify the canonical strategy, do not certify a full-game equilibrium, do not certify Fantasy, and do not add any REAL route.

**REAL remains 0/50.**
