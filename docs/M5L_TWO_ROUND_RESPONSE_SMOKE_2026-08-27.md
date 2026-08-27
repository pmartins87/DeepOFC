# M5L — two-round exact-BR response smoke

Status: `PASS_MECHANICS / EXCLUDED_FROM_Q2 / NOT_CERTIFICATION`

## Execution history

The first workflow run, `33090398271`, failed before strategic computation because the workflow omitted the repository root from `PYTHONPATH` and raised `ModuleNotFoundError: No module named 'deepofc'`. The workflow was corrected to `PYTHONPATH=.:tools/openofc_solver` without changing the experiment semantics.

Corrected immutable execution:

- run: `33090565771`
- result: `success`
- artifact: `openofc-m5l-two-round-response-smoke`
- artifact SHA-256: `15d0c3e09cc466e618b5b5c0eacea4bedc291a87650a52c8d350024aa7513269`
- authority: `TWO_ROUND_RESPONSE_MECHANICS_SMOKE_NOT_Q2_NOT_CERTIFICATION`
- benchmark: `BASE_TWO_ROUND_MECHANICS_ONLY_EXCLUDED_FROM_Q2_HELDOUT`

## Quantitative result

At the intentionally tiny 256-episode response budget:

| player | exact BR | learned-response value | residual | learned / total infosets | coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| P0 | 2.0992063492063466 | -0.12847222222222168 | 2.2276785714285685 | 318 / 39,902 | 0.007969525337075836 |
| P1 | 2.0992063492063466 | -0.12499999999999958 | 2.224206349206346 | 313 / 39,902 | 0.007844218334920555 |

The independently replayed exact response agrees with exact BR to numerical precision. The learned response remains far below exact BR, as expected at this mechanics-only budget.

## Decision

This run proves the two-round response learner, pure-response fallback, exact replay path, and authority firewall execute end-to-end. It is explicitly excluded from Q2 and cannot support calibration transfer, a certification threshold, a reference-evaluator manifest, or route promotion.

REAL route count remains `0/50`.
