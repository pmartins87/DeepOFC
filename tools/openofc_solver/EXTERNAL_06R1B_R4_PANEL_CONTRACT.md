# EXT-06R1B — Multi-root R4 exact strength/compute panel

Status: **FROZEN BEFORE PANEL PAYOFFS**

Authority: `R4_MULTIROOT_EXACT_LOCAL_STRENGTH_RESEARCH_ONLY`

The single frozen `R4_P0_A` root used by EXT-06R1 turned out to be strategically degenerate: its six legal root actions all have the same exact local value. This does not invalidate the 06R1 machinery; it means one payoff-blind random prefix is insufficient as a strength benchmark.

This replacement panel is fixed **before reading any of its payoffs**. No root may be removed because it is inconvenient, easy, hard, fouled, or unfavorable to a candidate method.

`REAL = 0` throughout.

## Frozen roots

Create `ConditionedFixtureSpec` roots at `(round=4, actor=0)` with the same deterministic payoff-blind prefix rule already used by 06R0, for the 16 consecutive seeds:

`64001, 64002, 64003, 64004, 64005, 64006, 64007, 64008, 64009, 64010, 64011, 64012, 64013, 64014, 64015, 64016`.

All 16 roots remain in the artifact.

## Phase A — exact oracle geometry

For every root:

1. build the exact hidden-discard support under the frozen payoff-blind prefix policy;
2. use `EXACT_R4_P0_COMBINATORIAL_V1` to enumerate the exact posterior over opponent hidden histories and current R4 packet;
3. compute the exact P1 best response and exact value of every Hero root action;
4. report action count, posterior world count, oracle build seconds, best value, min/max action value, and action-value spread.

A root is classified as `NONDEGENERATE` iff:

`max(root_action_value) - min(root_action_value) > 1e-9`.

This classification is descriptive; no root is discarded from the panel.

### Phase-A decision

- If at least **6 of 16** roots are nondegenerate, Phase B is activated.
- If fewer than 6 are nondegenerate, do **not** train search methods on this panel. Verdict: `R4_RANDOM_PREFIX_PANEL_TOO_DEGENERATE`. The next gate must replace the prefix generator with one fixed independent plausible-play policy and then freeze a new seed panel before reading payoffs.

The threshold 6/16 is frozen before panel payoffs.

## Phase B — methods

If activated, compare three predeclared policy outputs:

1. `ISUCT_VISIT_POLICY` — conditioned suit-canonical IS-UCT root visit distribution;
2. `MCCFR_CURRENT_POLICY` — conditioned suit-canonical MCCFR current regret-matching policy;
3. `MCCFR_AVERAGE_POLICY` — the same MCCFR run's accumulated average policy.

This deliberately avoids deciding current-vs-average after seeing the panel. Both are first-class candidates.

Frozen learner seeds: `20260830`, `20260831`.

Frozen terminal-evaluation budgets: `256, 1024, 4096`.

MCCFR receives `budget/2` iterations because each iteration runs one update episode per player, so its terminal evaluation count equals the stated budget.

Frozen search settings:

- IS-UCT exploration `2.0`;
- MCCFR epsilon `0.6`;
- MCCFR regret clipping / CFR+ `true`.

## Strength metric

For every root/method/seed/budget compute exact local root-policy regret against that root's exact oracle. Also report top-action regret, oracle-best-action agreement, root-policy TV between learner seeds, runtime, and materialized information states.

Degenerate roots remain present and contribute equal zero regret to every method. Strategic ranking is additionally reported on the pre-defined `NONDEGENERATE` subset so ties from structurally indifferent roots cannot masquerade as evidence.

## Frozen panel ranking

No recommendation is allowed unless Phase A finds at least 6 nondegenerate roots.

At final budget 4096, method A is the panel winner only if all are true:

1. A has the lowest mean exact policy regret on the nondegenerate roots in **both learner seeds** within tolerance `1e-9`;
2. across nondegenerate root × learner-seed cells, A is strictly better than each competitor in at least 60% of cells where their regrets differ by more than `1e-9`;
3. A is not more than `2.0x` slower in median training seconds than the fastest method unless its mean regret is at least 25% lower than that faster method.

Otherwise verdict is `NO_R4_PANEL_WINNER_KEEP_METHODS_OR_TUNE_ON_SEPARATE_DEVELOPMENT_PANEL`.

Possible promotions:

- `PROMOTE_ISUCT_R4_LOCAL_POLICY`
- `PROMOTE_MCCFR_CURRENT_R4_LOCAL_POLICY`
- `PROMOTE_MCCFR_AVERAGE_R4_LOCAL_POLICY`

No result here certifies production, full-game equilibrium, Fantasy value, R3/R2/R1, or REAL routes.
