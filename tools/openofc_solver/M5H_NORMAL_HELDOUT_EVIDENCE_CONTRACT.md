# M5H — Normal-route held-out strategic evidence contract

## Purpose

M5H is the evidence-production boundary for the **Normal×Normal** and
**Normal×Fantasy** routes required by the general M5C strategic certification
firewall.

M5A can evaluate a frozen visible-information policy at an exact continuation
vector and M5B can improve a policy at current V. Neither operation measures the
strategic gain available to an independently searched unilateral deviator.
M5H therefore separates policy construction from held-out strategic evaluation.

M5H does **not** choose certification thresholds and does **not** certify a
route. It produces SHA-bound route evidence that M5C may later compare against a
separately justified threshold manifest.

## Route classes

M5H accepts only:

- Normal×Normal — both players require unilateral-deviation measurements;
- Normal×Fantasy — only the acting Normal player requires a unilateral-deviation
  measurement because Fantasy terminal play is resolved by the separate exact /
  certified Fantasy-side machinery.

Fantasy×Fantasy remains under the M5E/M5F evidence path.

## Independence firewall

A REAL held-out or held-out-screening evidence object requires:

1. at least two distinct held-out seed identities;
2. a non-empty set of training seed identities;
3. zero overlap between training and held-out seeds;
4. one immutable candidate oracle identity;
5. one candidate implementation SHA-256;
6. one immutable reference-evaluator manifest;
7. one exact continuation-vector SHA-256;
8. equal per-seed sample budgets so seed-level means are exchangeable for the
   uncertainty calculation.

Synthetic/unit-test fixtures default to `SYNTHETIC_TEST_ONLY`. Changing the
continuation vector, implementation identity, evaluator manifest, seed set or
measured metrics changes the evidence/report identity.

## Metrics

For each independent held-out seed M5H records:

- held-out sample count;
- profile value from persistent P0 perspective;
- P0 unilateral-deviation gain when P0 is a required deviator;
- P1 unilateral-deviation gain when P1 is a required deviator.

The route report aggregates:

- mean held-out profile P0 value;
- standard error across independent seed-level profile means;
- maximum P0 deviation gain observed where applicable;
- maximum P1 deviation gain observed where applicable;
- maximum required unilateral-deviation gain used by M5C;
- total held-out sample count and exact seed identities.

The maximum across seeds/required players is deliberately conservative. M5H
never substitutes policy-imitation loss, top-1 agreement or training loss for
strategic deviation evidence.

## Reference evaluator authority manifest

A free-form evaluator SHA/description pair is insufficient. Every M5H reference
evaluator must be frozen through `m5h_reference_evaluator_manifest.py` and is
bound to:

- evaluator id;
- evaluator implementation SHA-256;
- validation-evidence SHA-256;
- method class;
- strategic capability;
- validated kernel classes;
- authority string and validation provenance;
- canonical manifest SHA-256.

The method/capability combinations are fail-closed:

- `LEARNED_RESPONSE_LOWER_BOUND` can only be
  `SCREENING_LOWER_BOUND_ONLY`;
- `LOW_EXPLOITABILITY_CERTIFICATION_ELIGIBLE` requires either an
  `EXACT_BEST_RESPONSE` or a separately
  `VALIDATED_EXPLOITABILITY_BOUND` method.

This makes the strategic asymmetry explicit: finding a profitable learned
response is valid evidence that a policy is exploitable, while failing to find
one is **not** evidence that exploitability is small.

## Evidence classes

M5H distinguishes three evidence classes:

- `SYNTHETIC_TEST_ONLY` — mechanics/unit tests only;
- `HELD_OUT_SCREENING_ONLY` — real independent held-out evidence produced by a
  screening/lower-bound evaluator; useful for fail-fast rejection, never for
  promotion;
- `HELD_OUT` — certifying held-out evidence, allowed only when the reference
  manifest is explicitly certification eligible.

M5C recognizes the screening evidence class and blocks it with
`EVIDENCE_SCREENING_LOWER_BOUND_NOT_CERTIFYING`, regardless of how small the
observed deviation happens to be.

## Threshold rule

No production strategic threshold exists in M5H. The producer does not accept a
`max_deviation`, `max_standard_error` or similar pass/fail budget.

Acceptance remains exclusively in `m5c_route_certification.py`, using an
independently frozen `StrategicThresholdManifest`.

## Promotion rule

M5H returns a general M5C `HeldoutRouteEvidence` object plus a richer audit
report. A report may be marked `HELD_OUT` only when both the independence
firewall and the reference-evaluator certification-authority firewall pass.

No M5H report is by itself a claim of optimality, bounded exploitability or
production readiness.

## Next implementation gate

After the authority manifest is mechanically validated, implement an independent
Normal×Normal learned-response evaluator as a **screening-only lower-bound**
tool. Its first role is to reject obviously exploitable candidate policies and
to exercise the complete M5H evidence path on both Normal×Normal continuation
states. It must not be used to certify low exploitability.

A later certification evaluator requires its own validation evidence establishing
an exact or justified upper-bound property before its manifest may use
`LOW_EXPLOITABILITY_CERTIFICATION_ELIGIBLE`.

Authority:

`NORMAL_ROUTE_HELDOUT_EVIDENCE_PRODUCER_NOT_CERTIFIER`
