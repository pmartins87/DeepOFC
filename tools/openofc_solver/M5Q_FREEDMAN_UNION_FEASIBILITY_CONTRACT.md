# M5Q Freedman coordinate-union feasibility contract

Status: frozen feasibility architecture; **not a strategic certificate**.

## Purpose

The support-free prerequisite gate established a finite sampled-regret increment envelope without a global terminal-history sampling floor. The reach-weighted-average gate then validated standard CFR average-strategy semantics on both exact reduced-game families.

The next question is deliberately narrower: **is the simplest scalar martingale construction already practical enough to serve as the certification architecture?**

This gate evaluates only the following conservative construction:

1. one scalar martingale difference process for every information-set/action regret coordinate;
2. one-sided Freedman concentration for each coordinate;
3. familywise union bound across all regret coordinates;
4. predictable quadratic variation bounded only by the exact terminal utility range via the worst-case Popoviciu variance envelope;
5. conversion from coordinate regret uncertainty to external-regret uncertainty using the safe per-infoset additive relaxation
   `max_a (Rhat(I,a) + radius)^+ <= max_a Rhat(I,a)^+ + radius`;
6. zero sampled-positive-regret contribution in the feasibility calculation, so the reported iteration requirement is an optimistic lower floor for this architecture.

The gate therefore asks whether this **specific** support-free construction can possibly be computationally useful before any expensive empirical-variance work is attempted.

## Frozen theorem/accounting choices

- scalar concentration: Freedman martingale inequality in predictable-quadratic-variation form;
- familywise failure probability: `0.05`;
- exploitability target: `0.15`;
- probe iterations: `1,000,000`;
- exact reduced-game families: Joker and hidden-discard;
- sampled regret coordinate envelope: `Delta_u`;
- martingale-difference upper envelope: `2 * Delta_u`;
- predictable variance upper bound per iteration: `Delta_u^2`;
- union surface: all information-set/action regret coordinates;
- sampled-positive-regret term for feasibility: exactly zero.

No threshold may be selected after observing the result.

## Required outputs

For each family the artifact must freeze:

- P0 infoset count;
- P1 infoset count;
- total infoset count;
- action-coordinate count;
- exact terminal utility range;
- martingale-difference envelope;
- worst-case predictable variance increment;
- Freedman coordinate radius at the probe budget;
- concentration-only exploitability contribution at the probe budget;
- minimum integer iteration count at which the concentration-only contribution reaches `<= 0.15`.

## PASS semantics

A workflow PASS means only that the accounting is internally consistent, deterministic, finite and authority-safe. The numerical result may conclude that the architecture is practical or impractical.

If the required iteration floor is impractical, the project rejects **only** this combination of coordinate-wise Freedman + worst-case predictable variance + union bound + per-infoset additive radius. It does not reject:

- data-dependent predictable variance;
- empirical-Bernstein/Freedman-style bounds with independently justified variance processes;
- confidence sequences;
- grouped or vector-valued martingale bounds;
- structure-aware regret aggregation;
- other rigorous support-free constructions.

## Authority firewall

This gate cannot certify an M4Z state, cannot authorize a production solver change, cannot convert empirical sampled regret into a certificate, and cannot increase the REAL route counter above `0/50`.
