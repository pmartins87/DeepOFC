# OpenOFC external research — 05H-A0 results (2026-08-29)

Authority: `BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

## Literature trigger

The NeurIPS CFR/MCCFR literature identifies an accumulated average strategy as the standard equilibrium-convergence object, whereas the existing OpenOFC shadow MCCFR exposed only the instantaneous regret-matching current policy. The detailed source audit is recorded in `docs/OFC_MCCFR_CURRENT_VS_AVERAGE_STRATEGY_LITERATURE_AUDIT_2026-08-29.md`.

This distinction does not invalidate 05G-Q2: exact bilateral BR directly established the exploitability of the current finite-fixture profile. A0 exists to make the average-strategy alternative experimentally available without perturbing the existing learner.

## Implementation

Added shadow solver `OverlapExternalSamplingMCCFRSimpleAverage` using two-player external-sampling SIMPLE averaging. The added accumulator records the opponent's current behavior distribution at opponent infosets visited during the other player's traversal, before the opponent action is sampled.

No additional RNG call is introduced and the base regret update logic is preserved.

## Fidelity workflow

- Workflow: `OpenOFC external 05H A0 MCCFR average fidelity`
- Run: `33272635225`
- Immutable head: `e6a703b8856c1690eb4f3c040961f222c62dd3c9`
- Conclusion: **success**

Mechanical assertions passed:

- identical cumulative regret tables between base and average-enabled solver for fixed fixture/seed/budget;
- identical action sets;
- identical iteration/terminal-evaluation snapshot;
- exactly identical `current_profile()`;
- deterministic `average_profile()` for fixed seed;
- every materialized average distribution legal, finite, non-negative and normalized.

The separately prepared A1 comparator core also compiled and passed the same fidelity suite in workflow run `33272699442` at immutable head `ef6c8f7c34f9d3cb047e0340a2336bd375e21724`.

## Verdict

**PASS MCCFR simple-average implementation fidelity.**

A1 is mechanically authorized as a parallel shadow comparator at the **same 4096 iteration budget selected by 05H-H1**. No production authority follows from A0.