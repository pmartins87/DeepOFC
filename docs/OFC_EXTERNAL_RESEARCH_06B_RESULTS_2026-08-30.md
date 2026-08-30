# OpenOFC external research — 06B full-game tabular learnability gate

Date: 2026-08-30  
Branch: `research/external-ofc-solver-audit-20260827`  
Workflow run: `33294273696`  
Head SHA: `64039cdfd79efd051b0b1f793bfa6594be91ef56`  
Artifact: `openofc-external-06b` (`9726972865`)  
Artifact ZIP digest: `sha256:b84e08d3ddbeb6f439ecdf497889aba0a722d0f8143d586764399143fb40ca73`  
Result manifest SHA-256: `a3bd8914fb004973f88f2425f161655b3f23ff5b2c3c5370f7c74c417bf7d695`

## Verdict

`BLOCK_DIRECT_TABULAR_SCALING_REUSE_STARVED`

Next gate: `06S_EXACT_SYMMETRY_AND_GENERALIZATION_DESIGN`.

Authority remains `FULL_GAME_TABULAR_LEARNABILITY_DIAGNOSTIC_ONLY`. No algorithm winner and no production route were selected.

## Frozen routing rule

A seed/mode was predeclared reuse-starved at 4,096 iterations if both held:

- overall repeat-update fraction < 0.5%;
- rounds 1–4 repeat-update fraction < 0.1%.

All four seed/mode cells satisfied both conditions by orders of magnitude.

## 4,096-iteration results

Each cell contained exactly 40,960 regret-update visits.

| Mode | Seed | Updated infosets | Revisited infosets | Overall repeat fraction | R1–R4 repeat fraction |
|---|---:|---:|---:|---:|---:|
| Vanilla OS-MCCFR | 20260830 | 40,955 | 5 | 0.0001220703125 | 0.0 |
| Vanilla OS-MCCFR | 20260831 | 40,958 | 2 | 0.000048828125 | 0.0 |
| Clipped OS-MCCFR | 20260830 | 40,955 | 5 | 0.0001220703125 | 0.0 |
| Clipped OS-MCCFR | 20260831 | 40,958 | 2 | 0.000048828125 | 0.0 |

The maximum visit count of any information set was two. Every information set from R1 through R4 had maximum visit count one.

The only observed recurrence occurred at `R0_P0`:

- seed 20260830: five revisited opening infosets among 4,096 updates (`0.001220703125` repeat fraction);
- seed 20260831: two revisited opening infosets among 4,096 updates (`0.00048828125` repeat fraction).

`R0_P1`, `R1_P0`, `R1_P1`, `R2_P0`, `R2_P1`, `R3_P0`, `R3_P1`, `R4_P0`, and `R4_P1` had **zero recurrence** in both seeds and both regret modes.

The result is independent of regret clipping at this budget: vanilla and clipped modes produced the same recurrence geometry for each seed.

## Stored-state growth

The final tables contained:

- 81,913 stored infosets for seed 20260830;
- 81,910 stored infosets for seed 20260831.

That is approximately twenty stored decision nodes per MCCFR iteration, while essentially every regret update still lands on a previously unupdated exact information state.

The raw non-dealer five-card opening support alone is `C(54,5) = 3,162,510`; later information states additionally encode both public boards, private own discards and full public placement history, making exact recurrence dramatically rarer.

## Scientific interpretation

The full-game trainer passed 06A mechanically, but direct tabular scaling is not a sensible next compute step at the current representation. At 4,096 iterations, 99.9878%–99.9951% of update mass is a first visit, and **100% of R1–R4 update mass is a first visit**.

Therefore a much larger direct run would predominantly materialize new concrete-card/history keys rather than repeatedly reduce regret at previously learned decisions. Choosing vanilla vs clipped MCCFR, or current vs average policy, before addressing this representation bottleneck would confuse algorithm comparison with near-total absence of table reuse.

This is a representation/learnability bottleneck, not evidence against MCCFR itself.

## Next research route

The frozen contract routes to exact reductions first. The leading candidate is global suit isomorphism: the four regular suit labels can potentially be canonicalized under their exact game symmetry while preserving ranks, flush/blocker relations, public signalling and private-memory semantics.

Only after lossless reductions are proved and measured should the project decide whether direct tabular CFR becomes viable. If exact symmetry remains insufficient, approximate generalization or subgame architectures may be investigated under separate labels and validation gates.

`real_routes_certified = 0`.
