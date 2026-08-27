# M5L Q2 — held-out benchmark-family calibration

Status: `PASS_MECHANICS / QUALIFICATION_ATTEMPT_TERMINATED / NOT_CERTIFICATION`

## Immutable execution

- GitHub Actions run: `33098966144`
- workflow result: `success`
- artifact: `openofc-m5l-reference-qualification-q2`
- GitHub artifact digest: `sha256:7d10aecec2995d5737658c6e38276c860fcd40d749af9e9f9b0700d1338b0c78`
- artifact payload SHA-256: `43ff5da07713afadcee85e93fe17562fe95b1147ec68d8ce02029e758cdaf568`
- source-manifest SHA-256: `30eb2f189a64cc6190feedd2267d31b5762ee684e5ff79145d0e6ab2e25073a3`
- schema: `openofc-m5l-two-round-q2-heldout-v1`
- authority: `HELDOUT_BENCHMARK_FAMILY_CALIBRATION_NOT_CERTIFICATION`
- durable exact evidence: `evidence/strategic/m5l_two_round_q2_2026-08-27.json`

The corrected run passed the Q1 activation precondition, the two-round response mechanics recheck, the full Q2 calibration, the authority firewall and artifact persistence.

## Frozen held-out surface

Q2 evaluated the precommitted surface without post-result tuning:

- families: `hidden-discard`, `joker`;
- profiles: `uniform`, `hash-biased-mixed`;
- both persistent players;
- response seeds `2026083101`, `2026083137`;
- 16,384 response episodes per row;
- 16 rows total.

Every row independently recomputed exact best response, exactly replayed the pure exact response, and then measured the learned response's underestimation residual. Exact BR versus exact replay agreed to within approximately `4.49e-14` at worst.

## Quantitative result

Across all 16 rows:

- minimum underestimation residual: `0.14286807715934624`
- maximum residual: `1.4681521898670882`
- mean residual: `0.751699668089499`
- responding-infoset coverage range: `0.25378924575965356` to `0.7757563368765331`
- mean coverage: about `0.4846595459888604`

By held-out family:

| family | min residual | max residual | mean residual | qualitative result |
| --- | ---: | ---: | ---: | --- |
| `hidden-discard` | 1.1956845238094949 | 1.4681521898670882 | 1.2953965580892841 | large residual persists |
| `joker` | 0.14286807715934624 | 0.32060185185185797 | 0.20800277808971382 | materially tighter, but still underestimates BR |

The family shift is substantial: mean residual differs by roughly a factor of six. Coverage also changes materially across families, from roughly 25%–28% in `hidden-discard` to roughly 62%–78% in `joker`.

## Qualification decision

The current M5L learned-response evaluator **fails the qualification program**.

The contract stated before Q2 that an unstable or large held-out residual envelope ends the qualification attempt for this evaluator design unless the evaluator itself is materially redesigned. Q2 produced exactly that outcome: residual behavior transfers poorly across held-out game families and remains over one raw point in every `hidden-discard` row.

Therefore:

1. Q3 conservative-residual threshold construction is **not activated** for this evaluator;
2. Q4 cannot grant `VALIDATED_EXPLOITABILITY_BOUND` or `LOW_EXPLOITABILITY_CERTIFICATION_ELIGIBLE` authority;
3. no residual observed in Q2 may now be used to tune this same evaluator and then reused as held-out validation;
4. no permissive threshold may be manufactured from the Q1/Q2 residuals;
5. M5L learned responses remain screening/diagnostic lower bounds only.

## Architectural consequence

The certification path must now pivot from learned best-response approximation toward a structurally stronger upper-bound mechanism. The leading candidate is a separately audited **regret-derived exploitability certificate**: first prove the accounting against exact reduced games, then investigate whether an appropriately weighted/stochastic extension is defensible for the scalable MCCFR path.

That follow-on work must start with `NOT_PRODUCTION_CERTIFICATION` authority and must not assume that raw MCCFR regret tables already constitute a valid bound.

REAL route count remains `0/50`.
