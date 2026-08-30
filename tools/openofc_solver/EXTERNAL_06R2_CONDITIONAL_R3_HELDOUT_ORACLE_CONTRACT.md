# EXT-06R2 — Conditional R3 held-out oracle validation

Status: **SUPERSEDED BEFORE ACTIVATION AND BEFORE EXT-06R1 RESULTS**

Authority: `R3_HELDOUT_EMPIRICAL_GAME_RESEARCH_ONLY`

This protocol was frozen before EXT-06R1 results, but was superseded before any strategic 06R2 execution after a boundary-information audit found a material issue that does **not** affect the R4 06R1 oracle:

- at R4 P1, no future chance remains after the current packet is known, so fixing the Hero's private historical discards inside a Hero-root posterior does not change P1's terminal action values;
- at R3, private historical discards change the remaining deck and therefore future R4 chance;
- a continuation game built only from one Hero infoset can consequently make an opponent continuation behave as if it knew information about the remaining deck that its own infoset does not reveal.

Because that can change R3 action rankings, this original protocol is **not executable** and must not be used for a strategic claim. The already-created neutral held-out panel core remains valid only as a mechanical sampler/firewall test.

It is replaced by `EXTERNAL_06R2A_R3_PRACTICAL_INFORMATION_SAFE_AB_CONTRACT.md`, which explicitly prioritizes practical strength under information-safe actor-local search rather than claiming a globally exact R3 subgame oracle.

No result was observed and no strategic 06R2 workflow was launched before this supersession. `REAL = 0` throughout.

---

## Historical frozen text (retained for auditability)

The superseded protocol would have activated only after EXT-06R1 mechanically passed, compared the 06R1 winner against the loser on `R3_P0_A` and `R3_P1_A`, used learner seeds `20260830/20260831`, terminal budgets `4,096/16,384`, deterministic held-out panels of 256 worlds, and attempted to certify an empirical continuation oracle by exact bilateral NashConv `<= 1e-6`.

The methodological error was not in those budgets, seeds, or panel mechanics; it was the assumption that a Hero-root-conditioned empirical continuation could serve as an information-correct opponent oracle at R3 while Hero private discards still affect future chance.
