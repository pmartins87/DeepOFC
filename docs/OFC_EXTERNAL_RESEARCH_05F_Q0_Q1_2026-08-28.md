# OpenOFC external research — 05F Q0/Q1 hidden-discard overlap

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

## Interpretation firewall

This result does **not** justify replacing the current DeepOFC architecture with MCCFR. Three reasons are material:

1. the support has only four deliberately designed worlds;
2. the payoff surface appears unusually favorable to a saddle at P0 value 28 and may be strategically easy despite its information ambiguity;
3. Search required synthetic local completion at 95.1% of reachable information states, and Q1 completion sampled compatible hidden states uniformly rather than from the conditional counterfactual distribution induced by the frozen policy.

Q2 is therefore mandatory before using Q1 to rank architectures. It measures whether the uniform compatible-state prior is wrong at ambiguous information sets. If Q2 reports nonzero uniform-vs-counterfactual TV, 05F-Q3 must replace the completion prior with exact counterfactual-reach weights and Q1's exact-BR comparison must be rerun.

No real strategic route is certified: `real_routes_certified = 0`.
