# M5K — Normal/Fantasy held-out challenger screening contract

Status: `SCREENING_ONLY / NON_CERTIFYING`

## Purpose

M5K supplies the Normal/Fantasy analogue of the M5I diagnostic boundary.

Under the delayed-response Normal/Fantasy hand model, only the Normal player acts before terminal Fantasy resolution.  A unilateral deviation is therefore an alternate visible-information Normal policy evaluated against the same chance/Fantasy terminal process.

M5K compares one frozen M5A/M5B candidate with one independently trained frozen challenger on common held-out deal plans.  A positive improvement by the challenger is a concrete lower bound on available unilateral improvement.

## Hard authority boundary

M5K is **not** a best-response oracle and is **not** certification eligible.

Its output must be consumed by M5H as `HELD_OUT_SCREENING_ONLY`.  M5C must continue to reject promotion regardless of how small the observed challenger gain is.

A zero observed M5K gain means only that this particular challenger failed to find a profitable deviation under the tested budget and seeds.

## Required invariants

1. Candidate and challenger are frozen `NormalFantasyFixedPolicyOracle` instances.
2. Candidate and challenger model fingerprints match their snapshots.
3. Both snapshots are trained at the exact continuation vector being screened.
4. Candidate training, challenger training and held-out chance seeds are disjoint by explicit identity in the enclosing evidence provenance.
5. The same held-out physical deal plan is used for candidate and challenger on each sample.
6. Common action-uniform streams are used for paired variance reduction; the two policy rollouts remain separate and may diverge in state trajectory.
7. The hidden Fantasy packet never enters the policy API.
8. Terminal utility is computed by one explicitly identified terminal evaluator shared by both profiles.
9. Deviation gain is measured for the persistent Normal player:
   - if P0 is Normal: `max(0, challenger_p0 - candidate_p0)`;
   - if P1 is Normal: `max(0, candidate_p0 - challenger_p0)`.
10. At least two unique held-out seed identities are required for real screening evidence.
11. No threshold is selected or inferred by M5K.
12. M5K never sets `ready_for_real_bellman=true` and never emits certifying `HELD_OUT` evidence.

## Route coverage target

Normal/Fantasy contains 16 state-local routes:

- button 0/1;
- Fantasy player P0 or P1;
- Fantasy packet size 14/15/16/17.

M5K may screen these routes incrementally, but the strategic project must not treat partial screening as route certification.
