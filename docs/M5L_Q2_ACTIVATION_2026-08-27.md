# M5L Q2 activation record

Status: `ACTIVE / HELDOUT_CALIBRATION_ONLY / NOT_CERTIFICATION`

Q1 completed and was durably recorded before Q2 activation, satisfying the precommitted activation rule in `M5L_Q2_HELDOUT_BENCHMARK_PLAN_2026-08-27.md`.

- Q1 run: `33086051886` — PASS mechanics, negative evaluator-qualification result
- Q1 artifact SHA-256: `60339a21eae6e67f90a2a3703ccf9bc34af1b0cec84ce4d8b39c14c9571a5f95`
- Q1 durable evidence: `evidence/strategic/m5l_three_round_q1_2026-08-27.json`
- Q2 driver SHA at activation: `013af07602d3782dbc7dca11d79acdac275aebd3`
- Q2 workflow: `.github/workflows/openofc-m5l-reference-qualification-q2.yml`

The first Q2 workflow invocation (`33098874703`) failed in the preflight before any Q2 computation because the validator searched the human precommit document for literal driver seed IDs that were frozen in the driver rather than written in the document. No Q2 result was observed. The validator was corrected to bind human-plan declarations to the plan and seed/family/profile constants to the already-precommitted driver.

Corrected Q2 invocation: `33098966144`. It is the authoritative Q2 activation run unless superseded by a documented mechanical rerun.

The experiment remains frozen at two held-out families (`hidden-discard`, `joker`), two profile rules (`uniform`, `hash-biased-mixed`), both players, two response seeds, and 16,384 response episodes per row. Q2 cannot emit a certification-eligible reference manifest or promote a route.
