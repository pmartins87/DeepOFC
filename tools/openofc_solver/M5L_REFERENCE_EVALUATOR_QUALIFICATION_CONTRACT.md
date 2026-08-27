# M5L — Reference-evaluator qualification contract

Status: `QUALIFICATION_FRAMEWORK / NOT_YET_CERTIFICATION_ELIGIBLE`

## Purpose

M5H already distinguishes a screening-only lower-bound response from a reference evaluator that is allowed to support low-exploitability certification. M5L defines the evidence path required before any approximate response method may claim the existing `VALIDATED_EXPLOITABILITY_BOUND` method class.

The first qualification target is Normal/Normal because DeepOFC already contains independently audited exact best-response benchmarks for tractable two- and three-round HU subgames.

## Gold-standard calibration principle

A candidate approximate evaluator must be tested against exact full-tree best response on reduced games where exact BR0/BR1 is feasible and independently replayable.

For every calibration case M5L records:

- candidate-profile identity;
- responding persistent player;
- exact best-response value;
- approximate learned-response value;
- underestimation residual `exact_br - approximate_response`;
- response-training work;
- responding-infoset coverage;
- exact pure-response replay work;
- implementation and validation source hashes.

The exact reference and approximate evaluator must use independent code paths for policy selection/replay wherever practical.

## Qualification stages

### Q0 — pipeline smoke

Use the audited three-round canonical benchmark with a uniform opponent profile.

- compute exact BR0 and BR1;
- train outcome-sampled unilateral response learners at increasing budgets;
- convert each learned response into a deterministic pure response with deterministic fallback on unseen responding infosets;
- replay that pure response exactly over the full chance/opponent tree;
- verify approximate response never exceeds exact BR beyond numerical tolerance.

Q0 proves mechanics only.

### Q1 — multi-profile calibration

Repeat on materially different fixed opponent profiles, including weak, mixed and solver-generated profiles. Include both responding players and multiple deterministic seeds.

### Q2 — held-out benchmark families

Freeze evaluator implementation/hyperparameters, then test against exact best response on benchmark variants that were not used to tune the evaluator.

### Q3 — conservative residual protocol

Only after Q1/Q2 may the project define a conservative exploitability allowance from exact-vs-approximate residuals. The allowance must include statistical/replication margin and must be frozen independently from the policy being certified.

### Q4 — authority decision

A `ReferenceEvaluatorManifest` may use:

- method class `VALIDATED_EXPLOITABILITY_BOUND`;
- capability `LOW_EXPLOITABILITY_CERTIFICATION_ELIGIBLE`

only after Q0-Q3 evidence is complete and reviewed. Until then every learned/approximate response remains screening-only.

## Important limitation

Calibration on reduced games is empirical validation, not a mathematical proof that the same residual bound transfers without error to the full Joker Ultimate game. Any final production threshold must explicitly account for this model-transfer risk. If the residual envelope is unstable across held-out reduced games, the evaluator must remain screening-only.

## Immediate Q0 acceptance criteria

1. exact three-round BR independent replay passes for P0 and P1;
2. at least three increasing response-training budgets are evaluated;
3. learned pure response value is finite and never above exact BR by more than `1e-9`;
4. underestimation residual is non-negative within tolerance;
5. responding-infoset coverage is reported;
6. higher-budget behavior is preserved as data, not forced to be monotonic;
7. the resulting artifact authority states `QUALIFICATION_DIAGNOSTIC_NOT_CERTIFICATION`;
8. no M5H certification-eligible manifest is emitted by Q0.
