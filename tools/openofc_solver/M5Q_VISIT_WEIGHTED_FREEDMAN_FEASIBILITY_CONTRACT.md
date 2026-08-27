# M5Q visit-weighted Freedman feasibility contract

Status: frozen reduced-game feasibility architecture; **not certification**.

## Purpose

The exact predictable-visitation audit showed that the all-coordinate `Delta_u^2` variance envelope overstated aggregate conditional second moment by roughly three orders of magnitude. This gate feeds the exact infoset visit probabilities into the same scalar Freedman + action-coordinate-union architecture to determine how much that structural correction improves the concentration floor.

## Frozen construction

For each frozen profile and traverser infoset `I`:

`V_T(I,a) <= T * P(visit I) * Delta_u^2`.

Every action coordinate at the same infoset receives that predictable quadratic-variation upper bound. The martingale-difference upper envelope remains `2*Delta_u`. A one-sided Freedman radius is union-bounded across all action coordinates, and the regret-to-exploitability bridge adds one radius per infoset after the max-over-actions relaxation.

Frozen parameters:

- familywise failure probability: `0.05`;
- target exploitability: `0.15`;
- probe iterations: `1,000,000`;
- profile rules: `uniform`, `hash-mixed`;
- reduced families: Joker, hidden-discard;
- sampled-positive-regret term: exactly zero for this feasibility floor.

The profile is held fixed when extrapolating the predictable visit surface to larger `T`. This is a feasibility surface, **not** an adaptive-training certificate.

## Required outputs

For every family/profile pair:

- total infosets and regret action coordinates;
- number of positive-visit infosets;
- min/max/mean positive visit probability;
- concentration-only exploitability contribution at `1,000,000` iterations;
- minimum `T` whose concentration-only contribution is `<=0.15` under the frozen visit surface.

The workflow must also compare these results with the earlier coarse all-coordinate Freedman floor without altering either result.

## Interpretation rule

A reduction in required iterations validates that predictable visitation is material. It does not by itself make the scalar-union architecture practical. If the remaining floor is still too large for project compute, the next gate must attack another identifiable source of looseness, such as structure-aware grouping, tighter conditional second moments, or a confidence-sequence construction.

## Authority firewall

This gate does not prove a martingale theorem for the implementation, does not evaluate an adaptive training trajectory, does not certify exploitability, does not authorize a full-game implementation, and cannot increase REAL above `0/50`.
