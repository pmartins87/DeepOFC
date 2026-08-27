# M5L reference-evaluator qualification — Q0 result

Date: 2026-08-27

Status: `Q0_PIPELINE_SMOKE_PASS / NOT_CERTIFICATION_ELIGIBLE`

GitHub Actions run: `33084052158`

Artifact: `openofc-m5l-reference-qualification-q0`

Artifact digest: `sha256:f09ddbe65a4799ac47ed7a9075c9cb3eaa4b35c0bbcae1934fea5ef1036e6656`

Artifact payload SHA-256: `d721bffa7f49b1483385222c4a25c0240b02896a42cd6a664050b009ad58b5c0`

## What Q0 established

Q0 satisfied the mechanics-only acceptance criteria in `M5L_REFERENCE_EVALUATOR_QUALIFICATION_CONTRACT.md`:

- exact three-round BR was computed independently for persistent P0 and P1;
- exact pure-response replay reproduced the BR value within floating-point tolerance;
- response budgets 64, 256 and 1024 were evaluated;
- every learned-response replay remained at or below exact BR;
- every underestimation residual remained non-negative;
- responding-infoset coverage was recorded;
- artifact authority remained `QUALIFICATION_DIAGNOSTIC_NOT_CERTIFICATION`;
- no certification-eligible `ReferenceEvaluatorManifest` was emitted.

The exact BR value against the uniform candidate was `10.418788580246916` for each persistent responding player. Independent replay produced `10.418788580246913`.

## Calibration signal

The current outcome-sampled response learner materially underestimates exact BR at the tested budgets.

| player | budget | approximate pure-response value | residual exact - approximate | responding-infoset coverage |
|---|---:|---:|---:|---:|
| P0 | 64 | 2.376350308642 | 8.042438271605 | 0.0761% |
| P0 | 256 | 4.657600308642 | 5.761188271605 | 0.2649% |
| P0 | 1024 | 7.070505401235 | 3.348283179012 | 0.8836% |
| P1 | 64 | 1.589699074074 | 8.829089506173 | 0.0727% |
| P1 | 256 | 4.355806327160 | 6.062982253086 | 0.2649% |
| P1 | 1024 | 5.390383873457 | 5.028404706790 | 0.8860% |

The increasing budgets improve the observed lower bound in this smoke case, but even the 1024-budget learner sees fewer than 1% of the responding infosets reached by exact BR. This is strong evidence that the present learner/budget cannot be treated as a low-exploitability upper-bound mechanism.

## Authority boundary

Q0 proves the calibration pipeline and exposes the scale of approximation error. It does **not** validate a transferable residual bound, strategic certification threshold, exploitability upper bound, or any of the 50 M4Z continuation routes.

Q1 is therefore useful as a diagnostic next step: measure whether the underestimation residual is stable or highly profile/player/seed dependent across materially different opponent policies. Q1 remains non-certifying regardless of outcome.
