# M5O exact regret-bound pilot — 2026-08-27

Status: `PASS_REDUCED_GAME_BOUND / USEFUL_BUT_LOOSE / NOT_PRODUCTION_CERTIFICATION`

## Immutable evidence

- workflow run: `33100241347` — PASS
- artifact payload SHA-256: `d0a9803553a5c74e1a0019d906e52b7df9c78da89f949c0fe0d8d580bc5d4e68`
- durable evidence: `evidence/strategic/m5o_regret_certificate_pilot_2026-08-27.json`
- solver mode: standard undiscounted full-tree CFR only
- families: `joker`, `hidden-discard`
- exact best response is used independently only to audit the proposed bound on these reduced games

## Result

Every audited cumulative-regret bound dominated exact NashConv. The theorem/accounting implementation therefore survived both the mechanics gate and an independently checked reduced-game pilot.

### Joker checkpoint ladder

| CFR iterations | exact exploitability | exploitability upper bound | NashConv bound / exact NashConv |
| ---: | ---: | ---: | ---: |
| 1 | 1.125000 | 4.233025 | 3.762689x |
| 2 | 0.658900 | 2.215173 | 3.361925x |
| 4 | 0.362577 | 1.140713 | 3.146127x |
| 8 | 0.186041 | 0.575109 | 3.091305x |

The bound contracts monotonically on this ladder and remains conservative by roughly 3.1x at eight iterations. That is loose, but materially different from M5L: this quantity has the correct upper-bound direction in the exact standard-CFR setting instead of merely searching for a profitable deviation.

### Held-out family transfer

At `hidden-discard`, one standard-CFR iteration produced:

- exact exploitability: `2.099206349206348`
- exploitability upper bound: `14.713624338622777`
- NashConv bound / exact NashConv: `7.009136735979096x`

The bound remained valid but became much looser on the larger family (`33,252` infosets/player versus `4,892` for Joker). This is an important scalability warning rather than a failure of correctness.

## Decision

M5O passes as **reduced-game theorem/accounting feasibility** and justifies continuing the regret-certificate architecture.

It does **not** establish a production certificate because the current DeepOFC global/deep training architecture relies on sampled CFR methods, especially External Sampling MCCFR. The deterministic full-tree CFR decomposition cannot simply be applied to sampled regret tables. The next gate must derive and audit a stochastic/high-probability counterpart with explicit sampling probabilities, importance weighting, confidence level, bounded-range assumptions and independently exact reduced-game coverage tests.

Raw MCCFR regret totals remain non-certifying.

REAL M4Z route count remains `0/50`.
