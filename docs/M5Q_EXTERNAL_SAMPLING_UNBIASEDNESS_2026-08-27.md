# M5Q External Sampling sampled-regret unbiasedness audit — 2026-08-27

Status: `PASS_IMPLEMENTATION_DIAGNOSTIC / NOT_CERTIFICATION`

## Immutable evidence

- workflow run: `33102897371` — PASS
- mechanics tests: PASS
- frozen pilot: PASS
- artifact payload SHA-256: `0188c219f6946055b8dae8c350ebfbca7aef65c93403dbb5f79c793cf30cedf5`
- artifact ZIP digest: `b8536d30c28e540e5ee5ad8af6ec23e6d176e9a6a7524fa5102e390d760e5550`
- durable evidence: `evidence/strategic/m5q_external_sampling_unbiasedness_2026-08-27.json`

## What was tested

The audit did not modify the production MCCFR trainer. A diagnostic subclass called the existing sampled traversal directly and returned the P0+P1 sampled regret-delta table without applying it.

Frozen design:

- exact game: two-round Joker perfect-recall benchmark;
- complete regret surface: `39,456` infoset/action coordinates;
- profiles: `uniform` and deterministic `hash-mixed`;
- sampled probes/profile: `4,096`;
- deterministic dense projections: `8`;
- exact expectation: one standard full-tree CFR step from the identical frozen regret table;
- diagnostic gate: every projection within `6.0` empirical standard errors of exact expectation.

The full-tree CFR and External Sampling solvers exposed exactly the same regret-matching probability surface at both frozen tables (`max probability difference = 0.0`). Probe tests also verified that sampled-delta inspection changes only RNG state, not cumulative regrets, iteration, local strategy sums or averaging clocks.

## Quantitative result

### Uniform profile

- exact-delta SHA-256: `9a2be01620c6fd01e8fc5d3e5852e978c6afc593aa1d2672e2fb2cdcc23fb2ac`
- maximum absolute projection error: `0.000495962078459918`
- maximum standardized error: `1.0755617298608102`
- projections passing: `8/8`

### Hash-mixed profile

- exact-delta SHA-256: `4dd3de1c1083cfe31dea4e1e185519464e09bd3f1e9e127250620d0913c057c5`
- maximum absolute projection error: `0.0010358655604499464`
- maximum standardized error: `1.8775743151804622`
- projections passing: `8/8`

Across all 16 frozen projection checks, the largest discrepancy was under `1.88` empirical SE, comfortably inside the precommitted 6-SE implementation-diagnostic gate.

## Interpretation

This is meaningful because it closes an implementation-level uncertainty before any concentration theorem is attached to the sampled regrets: the actual External Sampling traversal used by DeepOFC behaves consistently with the exact CFR expected regret increment on two materially different frozen profiles.

It is still only an unbiasedness **diagnostic**. Finite Monte Carlo agreement is not a proof of unbiasedness and the empirical SE used by this gate is not a production exploitability confidence interval.

The theoretical basis remains the MCCFR result that sampled updates equal CFR updates in expectation, and the generalized-sampling result that bounded unbiased counterfactual-value estimators can probabilistically minimize regret. M5Q now has empirical implementation evidence consistent with those assumptions on the audited reduced surface.

## Next gate

Before inventing a bespoke martingale inequality, the next step is to quantify the strongest variance-aware bound already available in the CFR literature. Gibson et al. derive an average-regret bound for bounded unbiased counterfactual-value estimators that explicitly depends on estimator variance. We should implement that theorem exactly on reduced games, using exact variance where it can be enumerated, to answer two questions:

1. does variance sensitivity improve the astronomical M5P worst-case counts enough to matter; and
2. if the theorem is still too loose even with exact reduced-game variance, is a new empirical martingale/confidence-sequence certificate actually justified?

This follow-up remains reduced-game theorem feasibility. No empirical variance estimate will be substituted into a theorem requiring true variance without a separate confidence argument.

REAL M4Z route count remains `0/50`.
