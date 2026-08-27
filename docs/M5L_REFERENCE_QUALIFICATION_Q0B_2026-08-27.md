# M5L reference-evaluator qualification Q0B — 2026-08-27

Status: `SCALE_DIAGNOSTIC_PASS / APPROX_RESPONSE_STILL_UNDERQUALIFIED / NOT_CERTIFICATION`

## Immutable run identity

- GitHub Actions run: `33086546043`
- workflow: `OpenOFC M5L reference qualification Q0B scale`
- workflow head: `8402a425a7df4c7bfaae28ab5e9c15065a5072d1`
- uploaded artifact id: `9653331976`
- uploaded ZIP SHA-256: `6965eb6aeefd5e37f7fbb2c86d42bb31302ca2961b32a9a3c15f2e9638d495c6`
- artifact payload SHA-256 field: `d4365827e7b881ad65b88535cbc9ce2d16bc226f8eb8f721816ce732b3ca38da`
- authority: `QUALIFICATION_SCALE_DIAGNOSTIC_NOT_CERTIFICATION`
- `reference_manifest_emitted=false`

## Purpose

Q0 had shown that the outcome-sampled response learner materially underestimated exact best response in the exact three-round reduced game at 1,024 episodes. Q0B asked whether this was simply a small-budget problem by extending the same deterministic learners to 4,096, 16,384 and 65,536 episodes.

The exact reference value was independently replayed and remained `10.4187885802469` for both players.

## Results

| Player | Episodes | response value | exact-BR residual | responding infoset coverage |
|---|---:|---:|---:|---:|
| P0 | 1,024 | 7.070505 | 3.348283 | 0.8836% |
| P0 | 4,096 | 6.631848 | 3.786941 | 2.8859% |
| P0 | 16,384 | 6.767843 | 3.650945 | 8.5118% |
| P0 | 65,536 | 7.782793 | **2.635995** | **22.3388%** |
| P1 | 1,024 | 5.390384 | 5.028405 | 0.8860% |
| P1 | 4,096 | 6.233169 | 4.185619 | 2.8332% |
| P1 | 16,384 | 6.879533 | 3.539255 | 8.3674% |
| P1 | 65,536 | 8.056038 | **2.362751** | **22.0499%** |

At the largest budget the learner had seen only about 22% of the exact responding infosets.  Even after 65,536 sampled terminal episodes, the approximate response remained more than 2.36 points below exact BR for both players.

The trajectory is not even monotone at the smaller budgets for P0: the residual worsened from 1,024 to 4,096 before recovering.  Raw sampled-response value therefore cannot be treated as a reliable upper-bound estimator merely by increasing this budget.

## Interpretation

Q0B confirms that the Q0 gap is structural enough that brute-force scaling of the exact-key response learner is not an efficient path to a certification evaluator.  The exact reduced game contains 204,962 responding infosets; the learner covered only 45,786 for P0 and 45,194 for P1 at 65,536 episodes.

This aligns with the independent M5J overlap diagnostic in the full Normal/Normal game: sparse exact-key response learning generalizes poorly to held-out visible-information states.

The result strengthens the reason for M5M's generalized response screen, but it does **not** qualify M5M or any learned response for certification.  Generalization can improve diagnostic power while still remaining a lower-bound response search.

## Authority decision

1. Do not promote the M5I/M5L exact-key outcome-sampled response learner to `CERTIFICATION_ELIGIBLE`.
2. Do not attempt to close the remaining residual merely by pushing the same Q0 learner to much larger budgets without a new justification.
3. Keep M5L Q1 as the pending multi-profile calibration gate.
4. Use M5M only for stronger fail-fast screening in the full Normal/Normal game.
5. A certification reference still requires an exact best response or a separately validated exploitability upper bound before M5H may emit certifying `HELD_OUT` evidence.
