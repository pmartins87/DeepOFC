# M5R-C — Rigorous truncated best-response interval pilot

Status: **reduced-game feasibility only; not route certification**.

M5R-A/B establish exact best response as the authority baseline on tractable reduced games. The remaining production blocker is scalability: a certification-facing evaluator must upper-bound profitable unilateral deviation even when it cannot enumerate the whole game.

M5R-C tests the core bounding algebra needed for a future branch-and-bound evaluator.

## Interval construction

For a frozen opponent policy, exact best response accumulates counterfactual terminal contributions into responding-player information-set/action buckets. M5R-C deterministically partitions terminal contributions into:

- **resolved** leaves, whose exact utility contribution is accumulated;
- **unresolved** leaves, whose contribution is replaced by the exact responder-perspective utility interval `[u_min, u_max]` multiplied by its non-negative chance/opponent counterfactual reach.

At each responding information set:

- lower BR value = `max_a lower(Q_a)`;
- upper BR value = `max_a upper(Q_a)`.

Those intervals are then propagated through the responder's perfect-recall predecessor chain exactly as in the exact BR solver. Summing root-information-set intervals yields a guaranteed interval containing the exact best-response value.

For a frozen profile value `v`, the certification-facing unilateral-deviation upper bound is then:

- P0: `BR_upper - v`;
- P1: `BR_upper + v`.

This direction is conservative even if the lower-bound response is weak.

## Deterministic nested resolution ladder

The pilot uses SHA-256 of the complete terminal history and nested modulo filters:

- `modulus=16`: resolve histories with `hash % 16 == 0`;
- `modulus=4`: resolve histories with `hash % 4 == 0`;
- `modulus=1`: resolve every history.

The sets are nested by construction. Therefore interval width must not increase as the resolved set grows, and `modulus=1` must collapse to the independently exact BR value to numerical precision.

The modulo filter is only a deterministic proof fixture. It does **not** save traversal work because the pilot still enumerates the reduced tree to account for unresolved reach mass. Production scalability requires prefix/subtree reach-mass pruning so unresolved subtrees can be bounded without visiting every leaf.

## Required gates

For Joker and hidden-discard, both players, uniform frozen profile:

1. use the previously exact reduced-game terminal utility range;
2. exact BR must lie inside every `[lower, upper]` interval;
3. lower <= upper and deviation upper >= exact deviation gain;
4. widths must be non-increasing across 16 -> 4 -> 1;
5. modulus 1 lower/upper must equal exact BR within `1e-12`;
6. all authority remains reduced-game only;
7. `production_certification_eligible=false`, `real_routes_certified=0`.

## Promotion meaning

A PASS validates the **upper-bound algebra** needed for a scalable best-response certifier. It does not validate a scalable pruning schedule, does not provide a full-game error bound, and does not promote any M5B candidate.

The next step after PASS is a prefix/subtree version that avoids exact leaf enumeration and reports bound width as a function of actual terminal work saved.