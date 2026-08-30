# EXT-06R2 — Conditional R3 held-out oracle validation

Status: **CONDITIONAL PROTOCOL FROZEN BEFORE EXT-06R1 RESULTS**

Authority: `R3_HELDOUT_EMPIRICAL_GAME_RESEARCH_ONLY`

This gate must not alter the canonical solver, runtime, table mapping, strategy authority, or any REAL route. `REAL = 0` throughout.

## Activation

06R2 is activated only after EXT-06R1 mechanically passes.

- If 06R1 returns `PROMOTE_MCCFR_TO_R2_R3_LOCAL_RESOLVER_VALIDATION`, the frozen 06R2 candidate is belief-correct suit-canonical MCCFR.
- If 06R1 returns `PROMOTE_ISUCT_TO_R2_R3_LOCAL_SEARCH_VALIDATION`, the frozen 06R2 candidate is belief-correct suit-canonical IS-UCT.
- If 06R1 returns `NO_CROSS_SEED_R4_WINNER_CONTINUE_DIAGNOSTICS`, **do not run 06R2**. Continue diagnostics instead.

The loser from 06R1 remains the control arm. No algorithm, hyperparameter, fixture, seed, budget, or ranking rule may be selected after seeing the 06R1 result.

## Why R3 before R2

06R0 measured useful strict-downstream reuse on both seeds at R3 but much weaker reuse at R2. R3 is therefore the next falsifiable boundary. R2 is intentionally deferred until R3 demonstrates a repeatable strength/compute advantage.

## Frozen fixtures

Use both payoff-blind 06R0 roots:

- `R3_P0_A`
- `R3_P1_A`

Both fixtures are required. A method may not be promoted from a single favorable root.

## Belief model

Training and evaluation must reconstruct only worlds compatible with the acting player's legal root information under the frozen payoff-blind prefix policy.

Forbidden:

- preserving the original concrete opponent hidden discard merely because it is available in the generated state;
- conditioning on future packets;
- using opponent private discards or packets absent from the root information state;
- sharing training RNG streams with held-out evaluation worlds.

The raw and suit-canonical root infosets and legal canonical root action sets must remain exact across all sampled worlds.

## Train/evaluation separation

Training and evaluation are disjoint by construction.

Frozen learner seeds:

- `20260830`
- `20260831`

Frozen terminal-evaluation budgets per method and seed:

- 4,096
- 16,384

The same terminal-budget definition must be used for both methods. Runtime is measured separately; equal wall-clock is reported as a secondary frontier, not substituted for the frozen terminal-budget comparison.

Held-out world panels use independent deterministic seeds:

- fixture `R3_P0_A`: `306201`, `306202`
- fixture `R3_P1_A`: `306211`, `306212`

Each panel contains 256 posterior-compatible worlds sampled before any candidate policy is evaluated. Duplicate complete deal plans are rejected and resampled. The panel hashes are part of the artifact.

No held-out world may be used for learning, hyperparameter selection, early stopping, completion construction, or oracle training.

## Empirical finite-game oracle

The held-out panel defines a finite imperfect-information continuation game.

For each fixture and each legal canonical root action, build an action-conditioned empirical continuation game over the frozen held-out worlds. The reference continuation solver may use the already audited suit-canonical MCCFR machinery, but **its strategic authority comes only from exact bilateral best-response validation**.

Reference continuation solving is accepted only when exact bilateral NashConv on the empirical game is `<= 1e-6` for every root-action continuation used in ranking. If any required continuation misses that threshold, the affected fixture is `ORACLE_NOT_CERTIFIED` and cannot rank the candidate methods.

The reference solver budget may scale deterministically until either:

1. all required root-action continuations certify `NashConv <= 1e-6`; or
2. the frozen maximum of 262,144 reference terminal evaluations per continuation is reached.

This scaling is an oracle-certification procedure, not candidate tuning. Candidate policies are never changed in response to it.

## Candidate metric

For each method/seed/budget/fixture, extract only the root policy learned from the training stream.

Use the certified held-out empirical oracle to assign a value to every canonical root action. Compute:

- held-out exact empirical root-policy regret;
- held-out top-action regret;
- oracle-best-action agreement;
- root-policy cross-seed TV;
- training seconds;
- information states materialized.

This deliberately avoids ranking a method by its own downstream training coverage.

## Frozen ranking

Tolerance: `1e-9` regret units.

At the final 16,384 terminal budget, method A beats method B in one fixture/seed cell only if:

`regret_A + 1e-9 < regret_B`.

Otherwise the cell is a tie unless B strictly beats A by the same rule.

Cross-fixture recommendation requires all four final cells (2 fixtures × 2 seeds) to have certified oracles.

- `PROMOTE_06R1_WINNER_TOWARD_R2_VALIDATION` only if the 06R1 winner is never strictly worse in any certified final cell and strictly better in at least two final cells spanning **both R3 fixtures**.
- `REVERSE_06R1_LOCAL_PROMOTION` only if the 06R1 loser satisfies the symmetric rule.
- Otherwise: `NO_R3_CROSS_FIXTURE_WINNER_CONTINUE_DIAGNOSTICS`.

No averaging may erase a losing fixture or seed.

## Fail-closed rules

Mechanical/posterior/oracle failure cannot be interpreted as strategic evidence.

No production migration, REAL certification, Fantasy valuation claim, or full-game equilibrium claim is permitted from 06R2.

## Next boundary

Only a successful cross-fixture R3 recommendation may activate an R2 validation protocol. R1 remains a separate boundary because 06R0 did not demonstrate useful local regret-table reuse there.
