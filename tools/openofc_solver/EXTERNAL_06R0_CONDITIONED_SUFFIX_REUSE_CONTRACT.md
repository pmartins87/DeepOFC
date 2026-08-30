# External OFC 06R0 — Conditioned Suffix Reuse Geometry Contract

Status: FROZEN BEFORE 06R0 PAYOFF/RESULT READOUT

## Authority

`CONDITIONED_SUFFIX_REUSE_GEOMETRY_DIAGNOSTIC_ONLY`

06R0 has no production or strategic-strength authority. It asks whether concentrating computation around an actually observed information state changes the reuse geometry enough to justify a practical local/continual-resolving architecture.

The strategic objective of the project is governed by `docs/OFC_PRACTICAL_STRENGTH_COMPUTE_POLICY_2026-08-30.md`: maximize practical playing strength per available compute rather than require a mathematically exact full-game solution.

## Prior evidence

06S1 proved that the exact global 24-suit orbit is lossless but insufficient for direct global tabular scaling. At 4,096 iterations the canonical arm had zero repeated R1–R4 updated infosets in both seeds.

06R0 must therefore **not** answer that result by merely increasing the same global iteration budget.

## Question

Does a suit-canonical outcome-sampling regret learner, when conditioned on one fixed observed infoset but still sampling unseen future cards, obtain materially useful repeated downstream updates within a small practical budget?

## Frozen representation

- Full-action HU normal-hand game from `strategic_cfr.py`.
- Exact rules, legality, state transitions and terminal current-hand score.
- Exact 24-global-suit canonical information/action representation certified by 06S0.
- No action abstraction.
- CFR+ enabled.
- Exploration epsilon: `0.6`.

## Conditioned-root fixtures

Fixture selection is structural and payoff-blind. A complete deal is generated from a fixed seed. The prefix is advanced to the requested `(round, actor)` by a deterministic SHA-256 selector over the exact legal-action list. No terminal utility, hand score, EV or learned policy is consulted while choosing the prefix.

Frozen fixtures:

| Fixture | Deal/prefix seed | Root |
|---|---:|---|
| `R1_P0_A` | 61001 | round 1, non-dealer to act |
| `R2_P0_A` | 62001 | round 2, non-dealer to act |
| `R2_P1_A` | 62002 | round 2, dealer to act |
| `R3_P0_A` | 63001 | round 3, non-dealer to act |
| `R3_P1_A` | 63002 | round 3, dealer to act |
| `R4_P0_A` | 64001 | round 4, non-dealer to act |

The root observation includes only what the existing certified information-state key exposes to the acting player.

## Two frozen arms

### `FIXED_SUFFIX_CONTROL`

Every episode starts from exactly the same complete underlying deal. This is a positive control only: it is expected to create recurrence and is not a deployable belief model.

### `FUTURE_RESAMPLED_CONDITIONED`

Every episode starts from the same root state but re-samples all *not-yet-fixed future deal packets* uniformly without replacement from the cards not contained in the preserved prefix/current packet set.

Preservation rule:

- opening packets are preserved for R1+ roots;
- all packets from rounds strictly before the root round are preserved;
- at a P0 root, P0's current packet is preserved while P1's not-yet-seen current packet is resampled;
- at a P1 root, both current-round packets are preserved because P0 has already acted publicly and P1 knows its own current packet;
- both players' packets in later rounds are resampled;
- already materialized boards, private own/past state object, discards and public history are unchanged.

This is deliberately a **future-only conditional chance model**. It does not claim a posterior-correct reconstruction of hidden opponent discards from earlier rounds. That posterior problem belongs to a later strategic-strength gate. 06R0 is a geometry test only.

For every generated root world the exact raw root information-state key, suit-canonical root key and legal root action set must equal the base fixture.

## Frozen learner seeds and budgets

Learner seeds:

- `20260830`
- `20260831`

Cumulative iteration budgets:

- `512`
- `2,048`
- `8,192`

One iteration performs one trajectory for each update player, exactly as the existing outcome-sampling shell does.

## Primary reuse metric

For any set of updated infosets:

`repeat_update_fraction = sum(max(visits - 1, 0)) / sum(visits)`

The primary 06R0 quantity is **strict-downstream repeat-update fraction**: the same metric after excluding the conditioned root itself. Strict downstream is defined by public-history length greater than the root public-history length. This prevents the trivially repeated root from making the experiment pass.

Report at every budget:

- stored infosets;
- updated infosets;
- total update visits;
- repeated-update mass and fraction;
- revisited-infoset count;
- maximum visits;
- the same metrics for strict downstream nodes;
- metrics by public-history depth from the root;
- iterations/second and wall-clock runtime;
- exact update-visit accounting.

## Precommitted usefulness threshold

A `FUTURE_RESAMPLED_CONDITIONED` fixture is `USEFUL_LOCAL_REUSE` at 8,192 iterations only if both are true:

1. strict-downstream repeat-update fraction is at least `0.01` (1%);
2. maximum strict-downstream visits is at least `3`.

The 1% threshold is intentionally an order of magnitude above the 0.1% later-round reuse-starvation threshold frozen in 06S1.

## Frozen verdict router

Mechanical failure, information-key drift, invalid deals, non-finite solver state or visit-accounting mismatch:

`FAIL_06R0_MECHANICS_OR_INFORMATION_FIREWALL`

Otherwise, if at least four of the six future-resampled fixtures pass `USEFUL_LOCAL_REUSE`, **and** the passing set contains at least one early fixture (`R1_P0_A`, `R2_P0_A`, `R2_P1_A`) and at least one mid/late fixture (`R3_P0_A`, `R3_P1_A`, `R4_P0_A`):

`PASS_06R0_CONDITIONED_REUSE_GEOMETRY`

If the early fixtures fail but at least two of `R3_P0_A`, `R3_P1_A`, `R4_P0_A` pass:

`PASS_06R0_LATE_ROUND_ONLY_REUSE_GEOMETRY`

Otherwise:

`FAIL_06R0_CONDITIONING_ALONE_STILL_REUSE_STARVED`

## Frozen next-gate routing

`PASS_06R0_CONDITIONED_REUSE_GEOMETRY` -> freeze `06R1` practical local-resolver strength/compute A/B, including a posterior/belief upgrade before strategic promotion.

`PASS_06R0_LATE_ROUND_ONLY_REUSE_GEOMETRY` -> freeze a round-adaptive architecture: global/generalized prior for early play plus local resolving only where geometry supports it.

`FAIL_06R0_CONDITIONING_ALONE_STILL_REUSE_STARVED` -> do not inflate iterations blindly; introduce a stronger generalization/abstraction/value prior before another local-regret experiment.

## Forbidden claims

06R0 cannot claim:

- equilibrium quality;
- exploitability reduction;
- correct opponent hidden-discard posterior;
- current-hand EV superiority;
- Fantasy continuation quality;
- production readiness.

`REAL = 0/50` throughout this gate.