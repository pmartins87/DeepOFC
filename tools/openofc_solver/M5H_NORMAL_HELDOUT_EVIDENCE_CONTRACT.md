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

A REAL `HELD_OUT` evidence object requires:

1. at least two distinct held-out seed identities;
2. a non-empty set of training seed identities;
3. zero overlap between training and held-out seeds;
4. one immutable oracle identity;
5. one implementation SHA-256;
6. one independent reference-evaluator SHA-256 and authority string;
7. one exact continuation-vector SHA-256;
8. equal per-seed sample budgets so seed-level means are exchangeable for the
   uncertainty calculation.

Synthetic/unit-test fixtures default to `SYNTHETIC_TEST_ONLY`. Changing the
continuation vector, implementation identity, evaluator identity, seed set or
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

## Reference evaluator rule

M5H intentionally does **not** implement or bless a best-response algorithm.
The evaluator that generates per-seed unilateral-deviation measurements is a
separate strategic object and must be identified by immutable SHA-256 plus an
authority/provenance string.

This prevents an approximate exploiter from silently becoming a certification
oracle merely because it produced a small observed gain. A future production
reference evaluator must have its own validation contract and evidence.

## Threshold rule

No production strategic threshold exists in M5H. The producer does not accept a
`max_deviation`, `max_standard_error` or similar pass/fail budget.

Acceptance remains exclusively in `m5c_route_certification.py`, using an
independently frozen `StrategicThresholdManifest`.

## Promotion rule

M5H returns a general M5C `HeldoutRouteEvidence` object plus a richer audit
report. The evidence may be marked `HELD_OUT` only when the independence
firewall above passes. Even then, M5H itself leaves promotion to M5C.

No M5H report is by itself a claim of optimality, bounded exploitability or
production readiness.

## Next implementation gate

After this producer/contract is mechanically validated, implement and validate
an independent Normal-route unilateral-deviation evaluator. Start with the two
Normal×Normal states, then extend the same evidence protocol to the 16
Normal×Fantasy states.

Authority:

`NORMAL_ROUTE_HELDOUT_EVIDENCE_PRODUCER_NOT_CERTIFIER`
