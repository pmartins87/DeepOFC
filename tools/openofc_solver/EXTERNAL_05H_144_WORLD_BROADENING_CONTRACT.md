# EXTERNAL 05H — 144-world geometry-first broadening contract

Authority: `BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

## Purpose

05G produced a complete finite reduced-game profile M with near-zero exact exploitability and Q3 found no counterfactual-posterior distortion in its completion holes. The next step is therefore to increase hidden-information breadth before making any further strategic claim.

05H broadens **all four private/future axes** while preserving the same public pre-R3 state and the same exact R3→R4 rules. Fixture selection is based only on card/information geometry. No terminal utility, Search result, MCCFR result, EV, best response, NashConv or exploitability may participate in selecting the support.

## Frozen support

Cartesian schedule: **4 × 4 × 3 × 3 = 144 physical worlds**.

P0 R3 private packets:
1. `7c 8c 8h`
2. `7c 8c 9d`
3. `7c 8c Td`
4. `7c 8c 8s`

P1 R3 private packets:
1. `Ah Kh Qh`
2. `Ah Kh Ks`
3. `Ah Kh As`
4. `Ah Kh Js`

P0 R4 future packets:
1. `9h Th Ts`
2. `9s 8d 7d`
3. `4d 5d 6d`

P1 R4 future packets:
1. `Ad Kc Qs`
2. `Ac Kd Qs`
3. `4s 5s 6s`

The added cards were chosen solely from cards unused by the frozen public prefix and the 05G categories. The fourth R3 type on each side preserves the deliberate shared-two-card / varying-third-card construction that can create hidden-discard overlap. The third R4 type on each side broadens future-card geometry without reusing a card across categories in any physical world.

## H0 — geometry gate

H0 may compute only physical/support geometry. It must not train Search/MCCFR and must not evaluate payoff.

Required mechanical facts:

- exactly 144 unique physical worlds;
- exactly 4 P0-R3 private packet types;
- exactly 4 P1-R3 private packet types;
- exactly 3 P0-R4 private packet types;
- exactly 3 P1-R4 private packet types;
- every world forms the same legal 34-card HU deal geometry;
- hidden-discard collisions exist in both directions;
- all four decision layers R3-P0, R3-P1, R4-P0, R4-P1 are reachable;
- reachable infosets > the frozen 05G value 69,828;
- ambiguous non-root infosets > the frozen 05G value 15,393;
- non-root infosets with at least 3 compatible concrete states > the frozen 05G value 10,101;
- maximum compatible concrete states > the frozen 05G value 12.

H0 must report exact counts, per-layer counts/ambiguity/max-compatible-state multiplicity, support SHA-256 and runtime.

If H0 fails due computation size/runtime rather than a correctness defect, no smaller support may be selected by looking at strategic payoff. A mechanical scaling redesign must be documented first.

## Planned routing after H0

If H0 passes, 05H proceeds in stages:

1. **H1 native coverage calibration:** MCCFR only, with budgets selected before any strategic payoff is evaluated. Search is not required because 05G already established that its native support saturates and is not a viable counterfactual-completeness mechanism.
2. **H2 explicit M completion/provenance:** `MCCFR_NATIVE` wherever materialized and `COMPLETION_UNIFORM_LOCAL_BACKWARD_V1` only in holes. Source counts/hashes must remain explicit.
3. **H3 exact bilateral best response:** exact NashConv/exploitability is the strategic authority on the 144-world fixture. Cross-play and self-play EV, if reported, remain descriptive only.
4. **H4 posterior audit:** if M still relies on ambiguous completion holes with positive counterfactual mass, rerun the exact Q3-style posterior audit on 05H. The already-prepared counterfactual-weighted completion machinery may be activated only if non-uniformity is actually detected.

## Strategic guardrails

A PASS on 05H is still a reduced-game research result. It does not authorize replacement of the canonical DeepOFC solver, production strategy, table interaction, or any REAL route. The canonical baseline remains untouched unless a later explicit promotion contract is created and passed.