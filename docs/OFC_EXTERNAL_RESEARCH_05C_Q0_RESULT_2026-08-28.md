# OpenOFC external research — 05C-Q0 result

Date: 2026-08-28
Branch: `research/external-ofc-solver-audit-20260827`
Corrected run: `33141837728`
Head: `8c0a53517d07fcb9c5f39667337a8cbc2fe3b3e6`
Status: **PASS / MECHANICAL SHADOW ONLY**

## Failure and correction

The first Q0 run (`33141720158`) had all three source tests green but failed the workflow gate because a good condition was encoded with negative polarity: `exact_response_helper_inside_search: false` was fed into `all(...)`. The search itself had not failed. The workflow was corrected to the positive assertion `no_exact_response_helper_inside_search: true`; no search semantics changed.

## Frozen Q0 result

- iterations: **5,000**
- physical support worlds: **6**
- selected P0 R3 action: `discard 8h; 7c -> bottom; 8c -> bottom`
- total information sets materialized: **949**
- fully action-covered information sets: **763** (80.40%)
- terminal P0 utility mean: **27.1854**
- terminal P0 utility min/max: **0 / 28**

Information-set growth by layer:

| Layer | Infosets | Total visits |
|---|---:|---:|
| P0 R3 | 1 | 5,000 |
| P1 R3 | 26 | 5,000 |
| P0 R4 | 146 | 5,000 |
| P1 R4 | 776 | 5,000 |

All four decision layers were reached. Every episode used one physical world, the root remained hidden-world blind, node identities were canonical information-state keys, terminal episode count equaled the requested iterations, and no exact-response helper was used inside search.

## Evidence

- workflow: `OpenOFC external two-street infoset Q0`
- run: `33141837728`
- job: `98754161949`
- unit tests: **3 passed**
- artifact: `openofc-external-two-street-05c-q0`
- artifact ID: `9674230824`
- artifact ZIP SHA256: `76076ab8f4c89123a24fdd2a2d58f474aedd5a513cfa157477d0f533d6d744e8`
- manifest SHA256: `293a09972103505cc6b17555a4a57c9273c9750e9688c83db6d631d1bbca93be`

## Interpretation

Q0 proves the mechanics needed for a two-street information-set tree can execute coherently on a small frozen support. The mean terminal utility is an on-search trajectory statistic, not an equilibrium value. At this stage it must not be compared directly with M5/CFR exploitability or used as a strategy-quality certificate.

The next authorized step is Q1 reproducibility across multiple search budgets and seeds. The first strategic comparator remains 05D: CFR/MCCFR on the same reduced two-street game.

REAL strategic route certificates remain **0/50**.
