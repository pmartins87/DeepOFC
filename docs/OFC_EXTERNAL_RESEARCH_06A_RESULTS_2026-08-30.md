# OpenOFC external research — 06A full-game mechanical certification

Date: 2026-08-30  
Branch: `research/external-ofc-solver-audit-20260827`  
Workflow run: `33294095108`  
Head SHA: `4a7beccb919998085193dc7b68f82f1bf54db2b0`  
Artifact: `openofc-external-06a` (`9726853843`)  
Artifact ZIP digest: `sha256:b0933e78bf8be48af3ae96ac20c7a391c595610a8f40f5fd4c40028d2d76e1d2`  
Result manifest SHA-256: `75820100bb98db77104d3d62a98d329d36aa94e150354407bd05ac3d27b416b2`

## Verdict

`PASS_06A_FULL_GAME_MECHANICS`

Authority remains `FULL_GAME_MECHANICS_CERTIFICATION_ONLY`. No strategic-strength claim and no REAL route is certified.

## What passed

All frozen 06A quality flags are true:

- 32/32 deterministic deal probes contained exactly 34 unique physical cards;
- all 32 opening probes exposed exactly 232 legal placements;
- the normal-hand actor sequence was exactly P0,P1 for rounds 0 through 4;
- all terminal probes contained 13 placed cards and four private discards per player, with ten public placement events;
- terminal current-hand utility was finite and exactly zero-sum;
- identical-seed training was byte-for-byte reproducible;
- checkpoint schema v2 serialized and restored the Python RNG state exactly;
- a `3 iterations -> checkpoint -> reload -> 4 iterations` run was byte-for-byte identical to an uninterrupted seven-iteration run;
- all inspected solver accounting remained finite;
- CFR+ and vanilla modes were mechanically distinct: CFR+ retained zero negative cumulative-regret entries, while the frozen vanilla probe produced 1,734 negative entries.

## Reproducibility fingerprints

Same-seed independent runs:

`f6206960e5304db87dae93072dbef01c0364722c3937ed84292347881c41b245`

Checkpoint-resumed and uninterrupted seven-iteration runs both produced:

`f07581af29b148c1f2ad50a08efe0db48116c1d6d94d9f5420958cc9b0055b6d`

This closes the previously identified reproducibility defect in checkpoint continuation. Schema v1 checkpoints remain readable but cannot satisfy the deterministic-resume certification because they never stored RNG state.

## Scientific interpretation

06A certifies the mechanics required to perform controlled full-game experiments. It does **not** establish convergence, exploitability, Fantasy continuation quality or production readiness.

A new full-game feasibility concern must be measured before expensive scaling: the current solver is tabular and its information-state keys contain concrete cards and public histories. In the complete 54-card game this can make exact information-state recurrence extremely sparse. If most training updates create new information sets rather than revisit previously learned sets, increasing raw iteration count will be a poor use of compute even though the mechanics are correct.

Therefore 06B begins with a frozen recurrence/learning-density diagnostic before any algorithm winner is selected. This is consistent with MCCFR theory, which supplies sampled regret guarantees but does not remove the practical requirement that a tabular implementation revisit strategically equivalent information sets at useful frequency.

## Promotion

`CONTINUE_TO_06B_FULL_GAME_LEARNABILITY_AND_ALGORITHM_READOUT_GATE`

`real_routes_certified = 0`.
