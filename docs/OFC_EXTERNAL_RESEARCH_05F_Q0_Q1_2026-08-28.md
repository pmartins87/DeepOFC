# OpenOFC external research — 05F Q0/Q1/Q2/Q3 hidden-discard overlap

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

## Q3 — reach-weighted Search completion A/B

Authoritative run: `33170050985`

- mechanics: 5/5 PASS;
- artifact `9685398553`;
- artifact ZIP SHA-256 `111525b83d9db175704a07b36a0db5c7c509f7c3130e8df89d70e49dd1bca29e`;
- manifest SHA-256 `45c9b3d67409ee291e30587b494ae416dfbd6a64ddfd368308d9e2f02eea939a`.

Q3 froze every one of the 444 UCT-covered decisions from Q1 and attempted to replace only the 8,658 synthetic completion decisions using the exact acting-player counterfactual posterior induced by the immutable Q1 completed Search profile.

Result:

- Q1 exploitability: **0.09209047925455316**;
- Q3 exploitability: **0.09209047925455316**;
- delta exploitability: **0.0**;
- changed missing-information-set decisions: **0**;
- zero-counterfactual-reach fallbacks: **792**;
- post-Q3 uniform-vs-counterfactual TV remained mean **0.08155869849**, p95/max **0.5**.

Therefore the non-uniform hidden-state posterior identified in Q2 is real, but under this particular four-world payoff surface it does not change the selected synthetic local actions. Reach weighting alone yields no strategic improvement over Q1 on this fixture.

This is informative in both directions: it rejects a tempting Search-specific patch as unnecessary here, while preserving the broader observation that the fixture contains strategic signalling and that a harder support may make posterior weighting decision-relevant.

## Decision after Q3

- keep the Q1 uniform Search implementation as the Search baseline for this exact four-world fixture;
- do not promote Search over MCCFR: exact exploitability still favors MCCFR decisively on 05F;
- do not promote MCCFR to production architecture: four hand-crafted worlds are far too narrow for that conclusion;
- next expand the benchmark so hidden-discard posterior differences affect action values, with more private types/worlds and more varied payoff geometry;
- repeat the same protocol: mechanical ambiguity -> fixed-profile comparison -> exact bilateral BR -> posterior audit -> only then algorithmic decision.

## Interpretation firewall

None of Q0-Q3 justifies replacing the current DeepOFC architecture. The support has only four deliberately designed worlds, the payoff surface appears unusually favorable to a saddle near P0 value 28, and Search still requires large off-trajectory policy materialization for exact exploitability measurement.

No real strategic route is certified: `real_routes_certified = 0`.
