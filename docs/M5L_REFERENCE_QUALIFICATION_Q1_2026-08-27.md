# M5L Q1 — multi-profile exact-BR calibration

Status: `PASS_MECHANICS / EVALUATOR_NOT_QUALIFIED / NOT_CERTIFICATION`

## Immutable execution

- GitHub Actions run: `33086051886`
- Workflow result: `success`
- Artifact: `openofc-m5l-reference-qualification-q1`
- Artifact payload SHA-256: `60339a21eae6e67f90a2a3703ccf9bc34af1b0cec84ce4d8b39c14c9571a5f95`
- Artifact schema: `openofc-m5l-three-round-q1-v1`
- Artifact authority: `MULTI_PROFILE_CALIBRATION_NOT_CERTIFICATION`
- Source-manifest SHA-256: `091582b035158cf0e021bf38a16d2cb374f05bfeea923c00d0faeeea6b16f2d3`

## Frozen calibration surface

Q1 evaluated four materially different fixed opponent profiles (`uniform`, `lexicographic-pure`, `hash-biased-mixed`, `mccfr-1024`), both responding players, and two deterministic response seeds per profile/player: 16 rows total. Every approximate response was replayed exactly and checked against independently computed exact best response.

The Q1 workflow passed because the calibration mechanics and authority firewall behaved correctly. It did **not** qualify the learned response evaluator.

## Quantitative result

Across all 16 rows:

- minimum exact-BR underestimation residual: `0.25`
- maximum residual: `6.305597249699919`
- mean residual: `3.6246697486749984`
- responding-infoset coverage range: `0.0026443926191196416` to `0.00901630546150018`
- mean responding-infoset coverage: `0.006736309657399908`

By profile:

| profile | min residual | max residual | mean residual | mean infoset coverage |
| --- | ---: | ---: | ---: | ---: |
| `lexicographic-pure` | 0.25 | 1.75 | 0.8125 | 0.0026919624125447644 |
| `mccfr-1024` | 2.03551577311573 | 2.563725854727596 | 2.2850062793801635 | 0.006912256906158215 |
| `uniform` | 4.972222222222226 | 5.376736111111114 | 5.237871334876546 | 0.008944340902216021 |
| `hash-biased-mixed` | 5.854159369198488 | 6.305597249699919 | 6.163301380443283 | 0.008396678408680634 |

The response learner therefore remains a loose lower-bound detector. Its error is strongly profile-dependent and, for several profiles, several raw points below the exact best response.

## Decision

Q1 is recorded as successful calibration evidence and as a **negative qualification result** for the current exact-key learned-response method. No `VALIDATED_EXPLOITABILITY_BOUND` manifest may be emitted from Q1, and Q1 cannot promote any M4Z route.

The precommitted Q2 held-out benchmark-family experiment may now be activated because its activation precondition was `Q1_COMPLETE_AND_RECORDED`. Q2 remains calibration-only. If Q2 also shows large or unstable residuals, the project must pivot to a structurally stronger reference evaluator rather than manufacture a permissive certification threshold from these residuals.

REAL route count remains `0/50`.
