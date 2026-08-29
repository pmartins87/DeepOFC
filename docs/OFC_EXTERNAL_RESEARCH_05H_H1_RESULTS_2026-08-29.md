# OpenOFC external research — 05H-H1 results (2026-08-29)

Authority: `BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

## Run

- Workflow: `OpenOFC external 05H H1 MCCFR coverage`
- Run: `33272194270`
- Job: `99152600237`
- Immutable run head: `0d0957d58fa19799bc9e4d728aa4795f9b092d95`
- Conclusion: `success`
- Artifact: `openofc-external-05h-h1`, id `9720516792`
- Artifact ZIP SHA-256: `253349182c440adbb13f0020aaee3461da7c104894e84275ee8691099b99b320`
- Manifest SHA-256: `3d187698be21494da58e5e421f10301b63b1373810df128b8d6fe76c6840495e`

## Frozen support revalidated

- chance worlds: **144**
- reachable information states: **261,076**
- root information states: **4**
- non-root information states: **261,072**
- ambiguous non-root information states: **43,344**
- exhaustive support materialization in this run: **79.37 s**

## Frozen budget ladder

H1 evaluated the precommitted cumulative MCCFR snapshots `1024`, `2048`, `4096` independently for seeds `20260829` and `20260830`. No completion, EV, best response, NashConv or exploitability was evaluated.

### Seed 20260829

| Budget | Native infosets | Non-root coverage | Ambiguous non-root coverage | Terminal evals | Cumulative train time |
|---:|---:|---:|---:|---:|---:|
| 1,024 | 95,312 | 36.5064% | 75.2584% | 221,184 | 43.07 s |
| 2,048 | 147,278 | 56.4113% | 92.2296% | 442,368 | 86.14 s |
| 4,096 | 203,731 | **78.0348%** | **98.7011%** | 884,736 | 172.50 s |

4096 profile SHA-256: `c495c5e07c4d5b081c31d885efc834a6fe5ea8e825d28cac54d70ac573c90f5b`.

At 4096 by layer:

- R3-P0: 4/4 native, 100%;
- R3-P1: 252/252 native, 100%;
- R4-P0: 15,594/15,876 native, **98.2237%**;
- R4-P1: 187,881/244,944 native, **76.7037%**;
- ambiguous R4-P1: 26,935/27,216 native, **98.9675%**.

### Seed 20260830

| Budget | Native infosets | Non-root coverage | Ambiguous non-root coverage | Terminal evals | Cumulative train time |
|---:|---:|---:|---:|---:|---:|
| 1,024 | 94,927 | 36.3589% | 74.8016% | 221,184 | 43.22 s |
| 2,048 | 146,705 | 56.1918% | 91.9966% | 442,368 | 86.21 s |
| 4,096 | 204,215 | **78.2202%** | **98.5073%** | 884,736 | 172.90 s |

4096 profile SHA-256: `0fbc66b7fe5300fbbe73d0b2971606fc175eda229c7f5ebb90680e75a28c402e`.

At 4096 by layer:

- R3-P0: 4/4 native, 100%;
- R3-P1: 252/252 native, 100%;
- R4-P0: 15,590/15,876 native, **98.1985%**;
- R4-P1: 188,369/244,944 native, **76.9029%**;
- ambiguous R4-P1: 26,855/27,216 native, **98.6736%**.

## Precommitted budget selection

Target rule required **both seeds** to achieve simultaneously:

- >=80% non-root native coverage; and
- >=95% ambiguous non-root native coverage.

4096 easily passed the ambiguous-state target but narrowly missed the global non-root target on both seeds. Therefore no tested budget met both conditions.

The precommitted fallback consequently applies exactly as written:

**selected downstream MCCFR budget = 4096 iterations**, with explicit completion required for every remaining native hole.

Selection reason stored by the artifact:
`no_tested_budget_met_both_targets_select_4096_and_require_explicit_completion`.

No larger budget may now be introduced merely because a later exploitability result is inconvenient; any such expansion requires a new precommitted engineering contract.

## Scientific interpretation

The broad fixture confirms the same engineering pattern seen in 05G: MCCFR expands deeply into counterfactual support, especially the ambiguous information states that matter most to hidden-information uncertainty. At 4096, roughly **98.5–98.7%** of ambiguous non-root infosets are native.

The remaining global coverage deficit is concentrated predominantly in the very large R4-P1 layer. Therefore H2 has a clear, predeclared job: retain the 4096 native policy exactly and fill only the remaining holes with the deterministic, explicitly labelled completion. Coverage itself is not treated as strategic quality.

## Verdict

**`PASS_05H_H1_COVERAGE_CALIBRATION`**.

Next frozen gate: **05H-H2 explicit M provenance + completion at exactly 4096 MCCFR iterations**.