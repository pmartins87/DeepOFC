# M5Q — Exploration-supported global-support feasibility

Date: 2026-08-27

Status: **FEASIBILITY GATE PASS / GLOBAL-DELTA CERTIFICATION ROUTE REJECTED AS PRACTICAL ARCHITECTURE**

This result is a certification-architecture result. It does not certify any OpenOFC state and it does not modify production training semantics.

## Why this gate existed

M5Q-D showed that the current regret-matching External Sampling kernel loses strictly positive global terminal-history sampling support after the first update. That blocks direct use of the Appendix-C form that depends on a finite `Delta_u / delta` with a global `delta > 0`.

The natural rescue attempt was explicit uniform exploration. For each sampled local action we hypothetically replace the current sampling policy by

`q_epsilon(a|I) = (1-epsilon) q(a|I) + epsilon / |A(I)|`.

The precommitted epsilon ladder was `0.01, 0.05, 0.10, 0.20, 1.00`. No production solver was changed.

## Frozen execution

- workflow run: `33117273274`
- job: `98675023719`
- head: `9396b996f58c2727eb11f7140b5c631b3556e439`
- mechanics: `8 passed`
- artifact payload SHA-256: `317b0fc0a242fb3bfea751c2c611a2c0106a7d13cb8a1497ae23f9f6f31e6bce`
- artifact ZIP SHA-256: `61744ff803b8ca07a0875ec8bf71e0b161cb6c379a960f7f25d6dace3392f276`
- target exploitability used for feasibility accounting: `0.15`
- estimator variance assumption: `0` — deliberately impossible optimistic floor

## Result

Explicit exploration does restore strictly positive structural support for every tested epsilon. The problem is the magnitude of the resulting global support floor.

At `epsilon=1.0`, which gives the **largest guaranteed support floor available anywhere in this frozen mixture family**:

| Reduced family | exact `Delta_u` | guaranteed global `delta` | zero-variance iterations for exploitability 0.15 |
| --- | ---: | ---: | ---: |
| Joker | 4 | 0.0005787037037037037 | 918,799,060,363,021 |
| hidden-discard | 12 | 0.000248015873015873 | 1,382,605,782,910,640,640 |

These are already the most favorable support numbers in the epsilon ladder. Smaller epsilon reduces the support floor further and therefore cannot rescue this theorem route.

## Decision

The project should **stop spending compute on the explicit-exploration + global-minimum-`delta` Appendix-C route as the primary practical exploitability certificate**.

This does not mean exploration is strategically bad. It means that using a worst-terminal-history global sampling floor inside this theorem is computationally unusable even under the deliberately favorable zero-variance assumption and even at 100% uniform exploration.

The next certification research gate is the **support-free martingale prerequisite audit**: before importing any confidence-sequence formula, establish on exact reduced games which sampled regret quantities are unbiased, what their per-iteration increment envelope is, how predictable variance can be computed or upper-bounded, and whether the required reach-weighted average strategy exists with the exact semantics required by the regret-to-exploitability theorem. Only after those prerequisites are machine-checked may a Freedman/empirical-Bernstein/confidence-sequence certificate be instantiated.

## Authority firewall

- no M4Z state is certified by this result;
- no training-policy change is authorized by this result;
- no empirical variance is being treated as a certificate;
- no post-hoc epsilon is selected;
- no support-free concentration theorem is assumed merely because the global-delta route failed;
- REAL route count remains `0/50` until a route passes the complete final certification contract.
