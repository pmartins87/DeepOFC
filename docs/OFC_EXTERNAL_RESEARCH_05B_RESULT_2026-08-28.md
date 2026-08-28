# OpenOFC external research — 05B result

Date: 2026-08-28
Branch: `research/external-ofc-solver-audit-20260827`
Run: `33141424288`
Head: `0725ad4289716c8b8c061333997a1200a4d2af13`
Status: **PASS / SCREENING ONLY**

## What changed from 05A

05A kept one legal P0 information-set root but used an exact P1 reply helper after each sampled hidden packet. 05B removed that helper. P1 became an explicit information-set node using its own legal private packet plus the public P0 placement, with a zero-sum minimizing confidence rule.

P0's root action is selected before the hidden packet is sampled, so the search cannot condition the root decision on determinization data.

## Frozen result

- iterations: **100,000**
- support worlds: **12** hidden P1 R4 packets
- exact finite-support optimum value: **19.666666666666668**
- selected action: `discard As; 9d -> top; Qh -> middle`
- selected action belongs to the exact optimum set: **yes**
- explicit P1 information sets materialized: **29**
- fully explored P1 information sets: **24**
- selected-action worlds seen: **12/12**
- selected-action worlds with every P1 action explored: **12/12**
- selected root on-policy mean during UCT: **19.693829226324844**
- reconstructed selected-action support backup after P1 coverage: **19.666666666666668**
- absolute error against independent enumerated selected-action value: **0.0**

The difference between the on-policy root mean and the final support backup is expected: early UCT episodes include P1 exploration. Once every P1 action is sampled for every selected-action world, the deterministic terminal values allow the selected-action support backup to reproduce the independent enumerated value exactly.

## Evidence

- workflow artifact: `openofc-external-r4-two-level-05b`
- artifact ID: `9674110132`
- artifact ZIP SHA256: `64a1402520ce7488ef2473a480cec1500bcf7368908c950c36da50385d1f6eaf`
- manifest SHA256: `f6ef73fffac3bfa70a11167fb248116798768b5f5f4b3c3ccadfe1099d434659`
- unit tests: **3 passed**

## Decision

05B is strong enough to authorize the next mechanical shadow experiment, 05C-Q0, where the tree spans R3 and R4. It does not authorize any route certificate or modification of the canonical M5 strategic policy.

REAL strategic route certificates remain **0/50**.
