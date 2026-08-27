# M5I — Normal×Normal learned-response screening contract

## Purpose

M5I is a **fail-fast screening layer** for the two Normal×Normal HU continuation
states. It trains an independent unilateral response for persistent P0 and P1
against one frozen M5A candidate policy and evaluates those learned responses on
chance seeds that are disjoint from response training.

M5I is intentionally weaker than a best-response/exploitability certificate.
Its strategic authority is:

`LEARNED_RESPONSE_LOWER_BOUND_SCREENING_ONLY`

A learned response explores only the strategy quality reached by its finite
training procedure. Therefore an observed response gain can expose a weak
candidate, while a small observed gain cannot establish that no stronger
response exists.

Finite held-out Monte Carlo adds a second limitation: the reported gains are
sample estimates. They become convincing rejection evidence only together with
adequate held-out uncertainty / replication. M5I never turns a small or zero
sample gain into a low-exploitability claim.

## Candidate firewall

The candidate must be a frozen `NormalNormalFixedPolicyOracle`:

- its policy API is the canonical visible-information key plus public legal
  actions only;
- model SHA-256 must match its policy snapshot;
- all action probabilities come from that frozen model;
- the policy snapshot's `training_continuation_sha256` must equal the exact
  continuation-vector SHA being screened;
- the exact 50-state continuation vector is also SHA-bound to the screening
  report.

A candidate trained at a stale or different continuation vector is rejected
before response training. Merely recording the current vector in the report is
not sufficient exact-V evidence.

M5I does not retrain or mutate the candidate during screening.

## Unilateral response training

For each Normal×Normal state M5I trains two independent response policies:

1. persistent P0 may deviate while P1 remains the frozen candidate;
2. persistent P1 may deviate while P0 remains the frozen candidate.

The response learner uses the full canonical Normal-hand action surface and
outcome-sampling regret matching+. It sees only the deviating player's legal
visible information state. Opponent hidden cards/discards are never arguments to
the response policy.

Training RNG identity is derived from:

- M5I base seed;
- exact continuation-state key;
- persistent deviating player.

Thus P0 and P1 response training are deterministic and independently identified.

## Held-out evaluation

At least two distinct held-out chance seed identities are required. For every
held-out seed M5I evaluates:

- candidate vs candidate profile value from persistent P0 perspective;
- learned P0 response vs frozen P1 candidate;
- frozen P0 candidate vs learned P1 response.

The same sampled deal plan is reused across the three profile comparisons for a
sample. Policy-action randomness is deterministic and independent of response
training. M5I reports non-negative observed gains:

- P0 gain = `max(0, E_hat[P0-response] - E_hat[candidate profile])`;
- P1 gain = `max(0, E_hat[candidate profile] - E_hat[P1-response profile])`.

These are screening estimates, not certified exploitability bounds.

## M5H/M5C routing

M5I output is designed to feed M5H with an evaluator manifest whose method class
is `LEARNED_RESPONSE_LOWER_BOUND` and capability is
`SCREENING_LOWER_BOUND_ONLY`.

The resulting M5H evidence kind must be:

`HELD_OUT_SCREENING_ONLY`

M5C always blocks that evidence class from REAL Bellman promotion with:

`EVIDENCE_SCREENING_LOWER_BOUND_NOT_CERTIFYING`

This remains true even when every numeric value lies below a threshold manifest.
No M5I result can therefore certify one of the 50 M4Z routes.

## Promotion boundary

M5I can answer: **"did an independently trained response find an exploitable
weakness worth rejecting or investigating?"**

M5I cannot answer: **"is this route below the production exploitability
budget?"**

That second statement requires an exact best response or a separately validated
upper-bound method with its own SHA-bound validation evidence and M5H reference
authority manifest.
