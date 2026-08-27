# M5Q certification-architecture decision — 2026-08-27

Status: **ARCHITECTURE DECISION, NOT STRATEGIC CERTIFICATION**

REAL route count after this decision: **0/50**.

## Scope

M5Q investigated whether the current External Sampling training process could itself provide a practical theorem-backed certificate strong enough to promote Normal-route strategic evidence. Two concrete routes were audited:

1. restore a strictly positive global sampling floor by adding explicit uniform exploration and then use the Appendix-C global-floor theorem;
2. keep the current no-exploration training semantics and use support-free martingale concentration, first with scalar coordinate union bounds and then with exact visit/predictable-variation accounting.

This record closes only those two concrete certificate architectures. It does **not** prove that all possible support-free concentration methods are impossible.

## Evidence ledger

| Gate | Workflow | Frozen result |
|---|---:|---|
| M5Q-A sampled-regret diagnostic | `33102897371` | projection diagnostics PASS; finite Monte Carlo diagnostic only; payload `0188c219f6946055b8dae8c350ebfbca7aef65c93403dbb5f79c793cf30cedf5` |
| Variance-theorem optimistic floor | `33103460750` | even impossible zero-variance normalized floor remains too large for the intended production role |
| Appendix-C M-star floor | `33113411659` | strategy-dependent M-star improves constants but does not make the raw theorem practical |
| Exact support/range feasibility | `33114239605` | exact reduced ranges Joker `4`, hidden-discard `12`; current regret matcher loses positive global support after first update |
| Exploration support feasibility | `33117273274` | explicit exploration restores support, but best-support endpoint remains computationally prohibitive |
| Support-free prerequisites | `33118314904` | bounded sampled-regret increments available; theorem-compatible average/variance work identified |
| Reach-weighted average gate | `33124398189` | reduced-game CFR-style average semantics validated; payload `2c51534c4528d4b53e807a4e76fa8f93872d462c9ca8839ba1073fd23e0e268c` |
| Coarse Freedman union | `33124925558` | scalar worst-case union bound far too loose; payload `2a38e5415cd68ae8fa5bbf213b3944273c7291e635a622612ab642e17eb7c01e` |
| Predictable visit variance | `33125162221` | exact reduced-game visit accounting PASS; payload `bd0312c66eb13151a7159f1e42eafbba72544b7ab1ad272bf867cba27ce13f51` |
| Visit-weighted Freedman | `33125564827` | 665x–7509x better than coarse union bound, still impractical; payload `5aa1877d067bb871becaa71bdf770bd24b0697ecf589e641803a49ad234482d7` |
| Adaptive predictable-Freedman trajectory | `33125700677` | actual online predictable variation accumulated without changing training; bound still orders of magnitude above exact exploitability; payload `ebb5fb5fa8da4804955445025256649d3526c5902dba97f60072cd26997246ff` |

## Route A — explicit exploration + global minimum support

The exploration-support gate used the frozen epsilon ladder `0.01, 0.05, 0.10, 0.20, 1.00`. Every row restored strictly positive structural support. The `epsilon=1` endpoint deliberately maximizes the guaranteed minimum support in this family, so it is the most favorable endpoint for the theorem-facing global floor.

At `epsilon=1`:

- Joker global sampling-probability floor: `0.0005787037037037037`;
- hidden-discard floor: `0.000248015873015873`;
- required Joker iterations for target exploitability `0.15`: **918,799,060,363,021**;
- required hidden-discard iterations: **1,382,605,782,910,640,640**.

Artifact payload SHA-256: `317b0fc0a242fb3bfea751c2c611a2c0106a7d13cb8a1497ae23f9f6f31e6bce`.

This is already the best guaranteed-support endpoint of the frozen exploration family, and the calculation still uses an intentionally favorable zero-variance theorem surface. Therefore **explicit exploration + global-minimum-probability Appendix-C is deprioritized as the primary production certification architecture**. Adopting exploration would also change training semantics and would require an independent convergence/quality validation before any strategic use.

## Route B — support-free scalar coordinate-union Freedman

M5Q then preserved the current no-exploration training semantics and removed the global-support requirement.

The first coordinate-union Freedman calculation was extremely loose. Exact visit weighting improved the required-iteration estimate by roughly 665x to 7509x, demonstrating that sparse reach structure matters materially:

- Joker uniform: `695,087,830` iterations;
- Joker hash-mixed: `269,017,448`;
- hidden-discard uniform: `107,988,885,079`;
- hidden-discard hash-mixed: `29,676,047,898`.

Those figures still assumed the sampled positive-regret term was zero and therefore remained feasibility lower floors, not usable certificates.

The decisive follow-up instrumented the actual adaptive Joker External Sampling trajectory while preserving exact RNG/training semantics. At checkpoint `T=64`:

- sampled-positive-regret contribution: `1.0007071512319758`;
- concentration additive term: `5592.373477969387`;
- support-free upper bound: `5593.374185120619`;
- exact reduced-game exploitability: `0.6407294367903822`.

The concentration term alone is about **8728x** the exact exploitability at that checkpoint. This is a direct apples-to-apples demonstration that the current scalar coordinate-union martingale architecture remains far too loose even after using actual online predictable variation.

Therefore **scalar coordinate-union Freedman, including the current visit-weighted/predictable-variation form, is deprioritized as the primary production certification architecture**.

## Decision

M5Q does not justify spending further primary effort tightening either of the two audited training-convergence certificates. The next strategic frontier should return to the quantity the M5C/M5H route actually needs: independent deviation/best-response evidence against a **frozen materialized candidate policy**.

The preferred next architecture is:

1. freeze the exact candidate policy and continuation identity;
2. evaluate unilateral deviation with an evaluator whose certification authority is itself independently validated;
3. use exact best response on tractable reduced games as the authority baseline;
4. treat approximate exploiters only as rejection/screening tools unless a separate protocol supplies a valid upper bound on missed exploitability;
5. promote a real route only after the held-out evidence, evaluator authority, uncertainty gate, continuation binding and M5C state-local thresholds all pass.

This pivot avoids requiring a generic MCCFR training-convergence theorem to be tight enough to certify the final frozen policy. It does not weaken the strategic standard: low observed gain from an approximate challenger remains inconclusive.

## Explicit non-claims

- No Normal×Normal, Normal×Fantasy or Fantasy×Fantasy state is certified by M5Q.
- No M5Q theorem gate changes `REAL = 0/50`.
- M5Q does not prove that every support-free theorem or confidence-sequence architecture is impractical.
- M5Q does not authorize changing production External Sampling to an exploration-mixed policy.
- Migration/equivalence and CI success remain separate from strategic optimality.

## Next milestone

**M5R — Frozen-policy best-response certification architecture**: establish an exact reduced-game reference evaluator and a fail-closed manifest/interface for any scalable certification-eligible deviation evaluator before attempting real Normal-route promotion.
