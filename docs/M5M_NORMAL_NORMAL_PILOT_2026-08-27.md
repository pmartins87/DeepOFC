# M5M — generalized paired Normal/Normal pilot

Status: `PASS_SCREENING / NO_CONSERVATIVE_POSITIVE_SIGNAL / NOT_CERTIFICATION`

## Immutable execution

- GitHub Actions run: `33088654128`
- Workflow result: `success`
- Artifact: `openofc-m5m-normal-normal-pilot`
- Artifact payload SHA-256: `a8e078497aff7e7f0005f5f290b0fd56a3d697de3650b5699eb139005e8e3c7c`
- Schema: `openofc-m5m-normal-normal-pilot-v1`
- Authority: `GENERALIZED_PAIRED_RESPONSE_PILOT_NOT_CERTIFICATION`

## Result

M5M evaluated the two Normal/Normal button states on four paired held-out seeds, 256 samples per seed. Its generalized response avoids the exact-key held-out fallback problem diagnosed by M5J, but remains a learned lower-bound response rather than an exploitability upper-bound evaluator.

| state | player | seed-mean signed gain | seed SE | conservative lower signal |
| --- | --- | ---: | ---: | ---: |
| `B0:P0F0:P1F0` | P0 | -0.1064453125 | 0.11942711243571567 | 0.0 |
| `B0:P0F0:P1F0` | P1 | 0.087890625 | 0.17672993420805172 | 0.0 |
| `B1:P0F0:P1F0` | P0 | -0.310546875 | 0.11594940590541078 | 0.0 |
| `B1:P0F0:P1F0` | P1 | -0.2734375 | 0.22205579671665576 | 0.0 |

Top-level `max_conservative_deviation_signal = 0.0`; `ready_for_real_bellman = 0`; `certification_claimed = false`.

## Critical quality diagnostic

The absence of a conservative positive deviation is **not evidence that the candidate is close to equilibrium**. The distilled response itself remains a weak approximation of the tabular response target:

- validation top-1 action accuracy across the four response materializations is only about 9.9%–12.5%;
- validation mean policy L1 is about 0.676–0.894;
- each response was trained for 1024 iterations and distilled from roughly 230k–236k action examples.

Therefore M5M is useful as a stronger fail-fast screen than M5I, but a zero M5M conservative signal cannot establish candidate adequacy. The correct reading is simply: **this particular generalized response failed to prove a profitable deviation at the frozen confidence rule**.

## Decision

- no route promotion;
- no exploitability upper-bound claim;
- no M4Z REAL evidence;
- retain M5M as screening infrastructure and compare it with exact-BR qualification evidence before deciding whether to improve or replace the generalized response family.

REAL route count remains `0/50`.
