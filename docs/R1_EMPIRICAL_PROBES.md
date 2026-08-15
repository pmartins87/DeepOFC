# R1 empirical probes for rules not published by KKPoker

The current KKPoker public website does not expose enough detail to close every Joker Ultimate rule. These probes define the smallest reproducible evidence needed to close the remaining R1 items without guessing.

## Probe J1 — Joker duplicate-standard-card semantics

Goal: determine whether a physical Joker may represent a nominal card already physically present in the same evaluated row.

Preferred evidence, in order:

1. KKPoker client rule/example that explicitly shows the substitution;
2. completed Joker Ultimate hand where the displayed hand classification is only explainable if duplication is allowed or forbidden;
3. controlled Fantasy test with a row such as four-of-a-kind plus Joker, where duplicate-rank interpretation would create an otherwise unsupported five-of-a-kind.

Record:

- before/after screenshots;
- exact physical cards;
- row classification shown by KKPoker;
- royalties awarded;
- hand ID/table timestamp.

Do not infer from generic wild-card poker rules.

## Probe J2 — Two-Joker collision semantics

Goal: determine whether JK1 and JK2 may represent the same nominal rank/suit or same rank with distinct suits.

Seek a state where the best hand differs under these interpretations. Record classification and royalty exactly as displayed.

## Probe J3 — Joker assignment tie policy

Goal: determine whether the client has a deterministic tie-break when multiple wildcard assignments yield the same final poker rank.

This matters for foul comparison only if the chosen assignment can affect another row. The DeepOFC evaluator should eventually search all legal assignments and optimize the **whole board under KKPoker rules**, not greedily optimize each row independently, unless evidence proves row-local substitution.

## Probe F1 — Bottom-quads-only Joker Ultimate re-Fantasy

Goal: determine card count on the next re-Fantasy when the stay condition is satisfied by Bottom quads-or-better but Top does not independently qualify for QQ/KK/AA/trips.

Capture the next deal and count cards. A single clean example is sufficient to freeze this path.

## Probe S1 — Both players foul in the same pairwise comparison

The public KKPoker rules say that when **a** player fouls, opposing players automatically scoop, but the public pages found in the official-site audit do not state the settlement when both players in the same pair foul.

Goal: freeze whether a double-foul pair scores:

- 0 points / no royalties for both;
- mutual scoop cancellation;
- an order-dependent result;
- or another KKPoker-specific rule.

Capture a real hand where both completed boards are visibly marked fouled and record the exact raw points/balance deltas before applying any inferred rake. Until this is proven, `pairwise_points_standard()` deliberately fails closed on double foul.

## Probe C1 — Three-player win-cap settlement

Goal: freeze the exact ordered transfer/clamping algorithm.

Use the lowest practical point value. Arrange/capture a three-player hand where one player cannot pay the full raw point liability to the first pairwise winner.

Record for all players:

- start-of-hand table balance;
- raw pairwise points before cap if displayed/calculable;
- pairwise scoring order;
- final balance delta;
- any rake deduction shown.

One numeric example should allow competing cap algorithms to be eliminated; a second independent example is required before certification.

## Probe E1 — OFC rake applicability and rounding

The public rake page states:

- OFC designated rake 5%;
- cap 2 BB;
- no rake if pot <= 5 BB;
- generic cash-game text separately says half of designated rake at <=3-player tables.

Because normal OFC has 2–3 players, this ambiguity is economically material.

Collect at least 30 hands across:

- HU and 3-player if available;
- raw result sizes below/equal/above 5 BB;
- result sizes large enough to approach the cap.

For each hand log start balances, raw points, point value, final balances and rake/rakeback credit if visible. Fit candidate rules (5%, 2.5%, cap behavior, rounding unit, player attribution) and accept only a rule that reconciles every hand exactly.

## Probe D1 — Opponent discard identity visibility

During an opponent's live turn and before hand settlement, inspect only normal supported KKPoker UI paths (including Card Tracker if available without exposing prohibited/private information).

Record whether old opponent discards remain card backs or whether rank/suit identities can ever be revealed to Hero before the decision is over.

DeepOFC continues to model only the **count** of opponent discards until this probe proves identity visibility.

## Probe U1 — Confirm-before-turn behavior

Supplied frames show the gold Confirm control while Oxy87's timer is active. The public OFC rules still define ordered action from left of BTN through BTN.

We must determine what clicking Confirm early actually does:

- disabled/no effect despite visible button;
- queues a pre-action that is committed only when Hero's turn arrives;
- immediately commits Hero before seeing the earlier player's final placement.

Until proven otherwise, the runtime must use the conservative policy already encoded in the canonical reconstructor: **visible Confirm is not sufficient; only act when Hero is the canonical acting player.**

## Evidence handling

Every probe result must be committed as:

- original screenshot/replay/log hash;
- canonical JSON interpretation;
- a regression test that fails under the rejected interpretation;
- a short rule-contract update in `docs/JOKER_RULES_SOURCE_TRANSCRIPTION.md`.
