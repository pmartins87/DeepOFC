# M5N — Normal/Fantasy paired-uncertainty screening contract

Status: `SCREENING_ONLY / NON_CERTIFYING`

## Purpose

M5N hardens the M5K Normal/Fantasy challenger diagnostic without changing its authority class.

M5K already compares one frozen candidate with one independently trained frozen challenger on common held-out physical deal plans.  M5N additionally measures the **paired per-deal response-minus-candidate difference**, its uncertainty, and a conservative across-seed lower signal.

The goal is diagnostic power: if a separately trained visible-information challenger has a statistically stable positive gain, the candidate is demonstrably improvable.  Failure to find such a gain still does not upper-bound exploitability.

## Hard authority boundary

M5N is **not** a best-response oracle and is **not** certification eligible.

Its outputs are `HELD_OUT_SCREENING_ONLY`.  M5C must reject route promotion regardless of how small the measured gain or uncertainty becomes.

A zero conservative M5N signal means only that this challenger, budget and held-out experiment failed to establish a positive lower-bound deviation with the declared confidence multiplier.

## Required invariants

1. Candidate and challenger are immutable `NormalFantasyFixedPolicyOracle` instances.
2. Candidate and challenger model fingerprints match their frozen snapshots.
3. Both snapshots were trained at the exact continuation vector being screened.
4. Candidate and challenger training seed identities are disjoint in the enclosing pilot provenance.
5. At least four unique held-out seed identities are required.
6. Held-out seed identities are disjoint from all declared training identities in the enclosing M5H evidence bundle.
7. Candidate and challenger receive the same physical deal plan for each paired sample.
8. Candidate and challenger receive the same policy-uniform stream seed for each paired sample.
9. The hidden Fantasy packet never enters the visible-information policy API.
10. One explicitly identified terminal evaluator is shared by candidate and challenger rollouts.
11. Per-sample signed Normal-player gain is:
    - Normal=P0: `challenger_p0 - candidate_p0`;
    - Normal=P1: `candidate_p0 - challenger_p0`.
12. Per-seed reports retain the signed mean gain and standard error before any clipping.
13. M5H diagnostic conversion may clip negative signed gain to zero because M5H represents available positive unilateral improvement.
14. Aggregate uncertainty is computed from the independent held-out seed means, not by pretending all deals are one independent seed population.
15. `conservative_lower_signal = max(0, mean_seed_gain - k * seed_standard_error)` for the explicitly frozen positive multiplier `k`.
16. The confidence multiplier is a diagnostic convention only; M5N does not infer or select a production strategic acceptance threshold.
17. M5N never sets `ready_for_real_bellman=true` and never emits certifying `HELD_OUT` evidence.

## Interpretation

A positive conservative signal is strong fail-fast evidence that the candidate can be improved by the tested challenger.

A zero signal is inconclusive.  It may reflect candidate strength, challenger weakness, insufficient training, insufficient held-out precision, or model-generalization error.

M5N therefore strengthens Normal/Fantasy **screening** while preserving the separation between lower-bound challenger evidence and certification-grade exploitability guarantees.
