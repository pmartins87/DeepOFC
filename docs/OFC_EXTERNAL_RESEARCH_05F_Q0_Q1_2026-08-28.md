# OpenOFC external research — 05F Q0/Q1/Q2 hidden-discard overlap

Date: 2026-08-28

Status: **REDUCED-GAME SHADOW RESEARCH / NOT PRODUCTION CERTIFICATION**

## Why 05F exists

The earlier six-world 05C/05D fixture had 16,381 reachable information sets but only one information set with more than one compatible concrete hidden state. It was therefore too weak to judge imperfect-information algorithms.

05F deliberately cross-products two P0 R3 private types and two P1 R3 private types. The types share public-placeable cards but differ in the identity of the private discard. This creates exact same-public-history/different-hidden-world collisions.

## Q0 — overlap mechanics

Authoritative run: `33168863411`

- 4/4 tests PASS;
- artifact `9684734186`;
- ZIP SHA-256 `58a645521db140cb14ff2b97d4741997095c50f5331ff761cdb47f286cbfb3da`;
- manifest SHA-256 `ef7099a10b8cde608b24f76f382f46e6809a3c1c70e797c26aebc444b80d738f`;
- two explicit hidden-discard collision witnesses, one in each direction;
- 270 non-root ambiguous information states actually observed by the 6,000-iteration information-set search;
- maximum 2 physical worlds merged into one observed information set.

Q0 therefore proves that the benchmark exercises hidden-discard ambiguity mechanically instead of merely claiming to do so.

## Strategic core smoke

Run `33169051150`: 3/3 PASS. This validated exact full-support enumeration, deterministic external-sampling MCCFR and exact pure bilateral best response/NashConv on the four-world game.

## Q1 — exact Search versus MCCFR comparator

Authoritative run: `33169170540`

- artifact `9684977390`;
- ZIP SHA-256 `0d969492867e2ab286013d96b1ab8cab8312beb0ae2f948d6cc2e815d6156183`;
- manifest SHA-256 `32583a75f095528c75b229abae4015fe3644ae68508ec858fea88c1c540a9703`;
- reachable information states: **9,102**;
- ambiguous information states: **1,822**;
- ambiguous non-root information states: **1,820**;
- max compatible concrete states per information set: 2;
- max legal actions: 21.

### Snapshot coverage before completion

| Candidate | Base infosets | Coverage | Missing infosets locally completed |
|---|---:|---:|---:|
| Search/UCT | 444 | 4.8780% | 8,658 |
| MCCFR | 9,093 | 99.9011% | 9 |

The Search snapshot therefore still depends heavily on the local completion mechanism. This is a first-class limitation, not a footnote.

### Exact fixed-profile values after completion

| Match | EV P0 |
|---|---:|
| Search × Search | 27.8158190415 |
| MCCFR × MCCFR | 28.0000000000 |
| Search P0 × MCCFR P1 | 27.8158190415 |
| MCCFR P0 × Search P1 | 28.0000000000 |

### Exact bilateral best response

| Completed profile | BR0 | BR1 | NashConv | exploitability |
|---|---:|---:|---:|---:|
| Search | 28.0000000000 | -27.8158190415 | 0.1841809585 | **0.09209047925** |
| MCCFR | 28.0000000000 | -28.0000000000 | ~1.42e-14 | **~7.11e-15** |

Within this deliberately constructed reduced fixture, the completed MCCFR profile is numerically at the exact saddle point to floating-point precision, while Search remains slightly exploitable on P0's side.

## Q2 — exact conditional-reach audit

Authoritative run: `33169478995`

- artifact `9685052900`;
- ZIP SHA-256 `3989ca5f2fc27b321f3a47a0b530d741ae66655a801979c613096adc4bac2f7a`;
- manifest SHA-256 `550988b2256c2988bf94980104a7c7ffbd59611ad5406787c707e66242cb6c77`.

Q2 asks whether the Q1 local resolver's uniform sampling over compatible hidden states matches the exact acting-player counterfactual posterior induced by the completed fixed profile.

### Search/UCT completed profile

- counterfactual posterior defined on 1,766 ambiguous infosets;
- mean uniform-vs-counterfactual TV: **0.08155869849**;
- median TV: **0.00216666667**;
- p95 TV: **0.5**;
- maximum TV: **0.5**.

A TV of 0.5 with two compatible states means the uniform 50/50 prior is being used where the exact counterfactual posterior has collapsed to one of the two hidden states. Therefore strategic signalling is materially informative in this fixture and the Q1 uniform-determinization Search variant deliberately ignores it.

### MCCFR completed profile

- counterfactual posterior defined on 550 ambiguous infosets;
- mean/median/p95/max uniform-vs-counterfactual TV: **0.0**.

For this frozen MCCFR profile, every defined ambiguous counterfactual posterior is exactly uniform on the constructed support. Q2 therefore gives no reason to alter MCCFR's nine locally completed states in this experiment.

## Decision after Q2

Q1's uniform Search remains a legitimate algorithmic baseline; Q2 does not retroactively invalidate it. It demonstrates that the baseline discards strategic signalling information. Q3 was therefore activated as a clean A/B variant: preserve all 444 original UCT-covered decisions, replace only the 8,658 synthetic Q1 completion decisions using exact counterfactual-reach hidden-state priors derived from the immutable Q1 completed Search profile, and rerun exact bilateral best response.

Q3 remains one-pass and fail-closed. If the updated policy materially changes its own induced posteriors, further fixed-point work is required rather than claiming self-consistency.

## Interpretation firewall

None of Q0-Q2 justifies replacing the current DeepOFC architecture. The support has only four deliberately designed worlds, the payoff surface appears unusually favorable to a saddle near P0 value 28, and Search still requires large off-trajectory policy materialization for exact exploitability measurement.

No real strategic route is certified: `real_routes_certified = 0`.
