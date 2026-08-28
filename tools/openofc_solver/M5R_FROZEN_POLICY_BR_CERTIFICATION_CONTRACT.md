# M5R — Frozen-policy best-response certification contract

Status: **reference architecture / reduced-game authority only**. This milestone certifies no M4Z route and leaves `REAL = 0/50`.

## Objective

M5Q showed that the audited generic MCCFR training-convergence certificates are far too loose for the production certification role. M5R therefore moves the authority boundary to the object that M5C/M5H actually need to judge: a **frozen materialized candidate policy**.

The core question is no longer “did the training algorithm converge according to a generic worst-case theorem?” It is:

> For this exact frozen policy, how much can either player gain by unilateral deviation, with a certification-eligible evaluator whose own error is independently bounded?

## Frozen-policy identity

Every evaluation must bind a deterministic SHA-256 over the **complete normalized policy**:

- every information set in the evaluated game;
- every legal action at that information set;
- normalized action probabilities, including explicit zeroes;
- deterministic canonical ordering.

Retraining an ostensibly equivalent policy is not a valid substitute for evaluating the frozen candidate.

## Exact reduced-game reference

The two-round perfect-recall reduced games provide the authority baseline because `deepofc.hu_two_round_br.exact_best_response`:

- enumerates every responding-player legal action even when the supplied profile assigns it zero probability;
- uses chance and opponent reach but excludes the responding player’s own reach from counterfactual weighting;
- optimizes round 4 before propagating values to the remembered round-3 predecessor;
- covers every responding-player information set;
- produces a pure exact best response.

M5R must independently cross-check each exact-BR value by materializing the pure response and evaluating that profile through the separate expected-value traversal.

For a frozen profile with expected P0 utility `v`:

- P0 unilateral deviation gain = `BR0 - v`;
- P1 unilateral deviation gain = `BR1 + v`;
- NashConv = `gain0 + gain1`;
- exploitability = `0.5 * NashConv`.

The exact reduced-game reference has missed-deviation upper bound `0.0` by construction, but that authority is scoped only to the enumerated reduced game.

## Reference evaluator manifest

Any evaluator used by later M5H/M5C held-out evidence must be bound by a manifest containing at least:

- evaluator ID;
- implementation SHA-256;
- independent validation-evidence SHA-256;
- validation scope;
- authority string;
- `guaranteed_missed_deviation_upper_bound`;
- `certification_eligible`;
- provenance;
- canonical manifest SHA-256.

A manifest may set `certification_eligible=true` only when:

1. validation status is PASS;
2. a finite non-negative **guaranteed** missed-deviation upper bound exists;
3. the validation scope is explicit and nonempty.

An approximate challenger that merely found a small gain has no such guarantee and must remain `certification_eligible=false`.

## Scalable evaluator promotion rule

A future scalable evaluator cannot inherit authority because it resembles the exact solver. It must be validated against exact-BR authority on a held-out suite of tractable games/candidates. The validation protocol must bound how much unilateral gain the scalable evaluator can miss. Only that guaranteed missed-gain bound may be added to observed deviation to obtain a certification-facing upper bound.

No post-hoc threshold may be chosen after seeing the candidate being certified.

## M5R first gate

The first gate must demonstrate on the Joker and hidden-discard two-round games that:

1. frozen-policy SHA identity is deterministic and probability-sensitive;
2. exact BR values cross-check through independent profile evaluation;
3. exact deviation gains reproduce exact NashConv/exploitability;
4. the exact reference manifest is certification-eligible **only inside the reduced-game validation scope** and carries missed-deviation upper bound `0.0`;
5. an otherwise identical approximate/incomplete manifest with no guaranteed missed-gain bound fails closed;
6. production certification remains false and `real_routes_certified=0`.

## Authority firewall

Passing M5R’s reduced-game gate means the **reference-evaluator architecture** is validated. It does not certify a real OpenOFC continuation state, does not validate a full-game scalable evaluator, and does not promote the M5B candidate.