# EXT-06R1F — R4 top-action sample-efficiency result

Date: 2026-08-30
Branch: `research/external-ofc-solver-audit-20260827`
Authority: frozen 06R1F global promotion gate
REAL routes certified: **0**

## Preconditions

06R1F was frozen in `EXT-06R1E-R4-DEPLOYMENT-SEMANTICS-AUDIT.md` before the twelve fixture oracle outputs were observed.

Authoritative fixture seeds:

`65101..65112`

Terminal-evaluation budgets:

`32, 64, 128, 256, 512, 1024`

Learner seeds:

`20260830, 20260831`

Primary operational metric: exact local top-action regret. Mixed-policy regret has no promotion authority.

The first 06R1F attempt was non-authoritative because fixture 65109 exposed that the old cached R4 oracle incorrectly required a one-to-one mapping between posterior worlds and P1 information sets. The corrected oracle groups posterior worlds by P1 information state before the best response.

The dedicated semantic regression completed successfully before interpretation of the v2 suite:

- workflow run: `33335388261`
- verdict: `PASS_GROUPED_CACHED_ORACLE_SEMANTICS`
- reference-versus-cached maximum root-value difference: `0.0`
- posterior worlds: `173558`
- P1 information sets per root action: `162932`
- regression ZIP SHA-256: `9577028df319a4d4d3a3fe1eecebf92b63437504493f86b735c0a10f002f61aa`

The fact that `162932 < 173558` proves that the regression exercises the many-worlds-per-P1-infoset case that invalidated the old uniqueness assumption.

## Authoritative 06R1F v2 execution

Workflow run: `33335414992`

All twelve frozen fixture jobs completed successfully under:

`P1_INFOSET_GROUPED_BEST_RESPONSE_V2`

The authoritative aggregate was produced by `tools/openofc_solver/aggregate_r4_sample_efficiency.py` with schema `openofc-external-06r1f-aggregate-v2`.

Aggregate JSON file SHA-256: `732c445a7bbadf4f206322e31c4ce48bb13c17f3123aa192713ae4c7acc1c7b4`

Aggregate manifest SHA-256: `afc05e4e6f9b066733d42f0511353bd6305731a4283957a412ee4eb762bfa423`

## Exact structural result

Seven of the twelve fixtures are discriminative under the frozen oracle-spread threshold `> 1e-12`:

`65103, 65104, 65106, 65108, 65109, 65111, 65112`

The remaining five are non-discriminative:

`65101, 65102, 65105, 65107, 65110`

This satisfies the frozen minimum of six discriminative fixtures.

Across the seven discriminative fixtures × two learner seeds there are fourteen authoritative method-pair comparisons.

For **every one of those fourteen pairs**:

- ISUCT stable-hit budget = `32`;
- MCCFR stable-hit budget = `32`;
- strict winner = `TIE`.

Therefore:

- ISUCT strict stable-hit wins: `0`;
- MCCFR strict stable-hit wins: `0`;
- ties: `14`;
- ISUCT strict wins within seed 20260830: `0`;
- MCCFR strict wins within seed 20260830: `0`;
- ISUCT strict wins within seed 20260831: `0`;
- MCCFR strict wins within seed 20260831: `0`.

At terminal budget 1024, both methods selected an oracle-optimal top action in every discriminative fixture/seed cell:

- ISUCT: `14 / 14 = 100%`;
- MCCFR: `14 / 14 = 100%`.

## Secondary mixed-policy diagnostic

At budget 1024, over the fourteen discriminative cells, mean exact local mixed-policy regret was:

- ISUCT: `0.01810611091197813`;
- MCCFR: `0.07943266967806209`.

This difference is preserved for diagnostics only. The promotion contract explicitly forbids mixed-policy regret from breaking a top-action sample-efficiency tie.

## Frozen verdict

`NO_PROMOTION_06R1F`

Neither method satisfies the requirement for at least four strict stable-hit wins because both methods already reach the oracle-optimal R4 top action at the smallest tested budget in every discriminative pair.

The scientifically supported interpretation is therefore **benchmark saturation at this final one-decision R4 gate**, not evidence that ISUCT and MCCFR are globally equivalent.

This result satisfies the pre-frozen activation condition for EXT-06R3: solver selection may now move to the multi-decision imperfect-information `HUThreeRoundSequentialSubgameV2` exact-exploitability tribunal.

## Scope firewall

06R1F does not modify canonical or live policy, does not certify arbitrary R1/R2/R3 production states, does not certify Fantasy, and does not add any REAL route.

**REAL remains 0/50.**
