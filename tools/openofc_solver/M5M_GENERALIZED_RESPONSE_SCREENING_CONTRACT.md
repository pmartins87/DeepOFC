# M5M — Generalized paired-response screening contract

## Purpose

M5M replaces exact-tabular held-out response lookup as the preferred Normal/Normal screening experiment after M5J exposed a response-coverage problem.

M5M remains a **fail-fast screening layer only**. Its authority is:

`GENERALIZED_PAIRED_RESPONSE_SCREENING_ONLY`

It cannot certify exploitability, set a production threshold, or promote an M4Z route.

## Why M5M exists

M5I trains a tabular unilateral response and uses a uniform fallback when a held-out visible infoset was not seen during response training. M5J showed that increasing response training from 256 to 1,024 episodes changed the response table size by roughly 4x while leaving every held-out metric unchanged. Because the OpenOFC visible-information space is very large, M5M must not depend on exact held-out key overlap.

M5M therefore adds two controls:

1. **visible-information response generalization** — the trained tabular response is distilled into the existing sparse action-conditioned visible-state model; held-out response decisions are always produced by that frozen model rather than by a uniform unseen-key fallback;
2. **paired response evaluation** — candidate and unilateral-response rollouts reuse the same physical deal and the same deterministic policy random numbers, and uncertainty is computed for the response-minus-candidate difference itself.

## Candidate firewall

The candidate must be a frozen `NormalNormalFixedPolicyOracle` whose:

- model fingerprint matches its snapshot;
- snapshot was trained at the exact continuation-vector SHA being screened;
- policy API receives only canonical visible information plus public legal actions.

M5M never retrains or mutates the candidate during held-out evaluation.

## Response training and distillation

For persistent P0 and P1 independently:

1. train the existing M5I outcome-sampled unilateral response against the frozen opponent candidate;
2. split visited response infosets deterministically using the existing stable hash holdout;
3. distill non-holdout response nodes into `SparseActionAdvantageModel` through `DeterministicReservoir`;
4. measure distillation quality on response infosets excluded from model fitting;
5. freeze the generalized response model by SHA-256.

The generalized model receives only the canonical visible state key and canonical legal action keys. Opponent hidden cards, future deals and full chance plans are forbidden response-policy inputs.

Distillation validation is diagnostic. Weak distillation quality does not become a certification claim; it is a reason to improve or reject the screen.

## Paired held-out evaluation

At least four distinct held-out chance-seed identities are required for the default M5M experiment.

For each held-out physical deal, M5M evaluates:

- candidate vs candidate;
- generalized P0 response vs frozen P1 candidate;
- frozen P0 candidate vs generalized P1 response.

All three profiles reuse one deterministic policy-randomness stream for that sample. This common-random-number construction reduces avoidable Monte Carlo variance while preserving the policy-specific action mapping.

M5M stores the **signed** paired differences before any clipping:

- P0 difference = `u0(P0 response) - u0(candidate profile)`;
- P1 difference = `u0(candidate profile) - u0(P1 response)`.

For each chance seed it reports the mean paired difference and the standard error of those paired sample differences.

Across seed means it reports:

- mean signed gain;
- standard error across independent seed means;
- a conservative diagnostic lower-confidence signal `max(0, mean - k * SE)` where `k` is frozen in the configuration.

The lower-confidence signal is a screening diagnostic, not a mathematically certified exploitability bound.

## M5H/M5C boundary

M5M may later feed M5H only as `HELD_OUT_SCREENING_ONLY` evidence with a screening-only reference evaluator manifest. M5C must continue to block it with:

`EVIDENCE_SCREENING_LOWER_BOUND_NOT_CERTIFYING`

No M5M number, including a positive conservative lower-confidence signal, is sufficient to certify one of the 50 routes.

## Promotion path

M5M can answer a narrower question than certification: whether a generalized unilateral policy finds a reproducible candidate weakness on independent chance seeds with paired uncertainty accounting.

Before any response approximation can support a low-exploitability claim, it must be qualified independently against exact/reference best-response evidence under the M5L qualification program and receive an explicit future authority decision.
