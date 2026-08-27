# M5Q adaptive predictable-Freedman trajectory pilot

Status: reduced-game trajectory feasibility; **not certification**.

## Purpose

The predictable-visitation gate established an exact conditional second-moment envelope on frozen reduced-game profiles. This pilot now accumulates that predictable envelope along an **adaptive External Sampling MCCFR trajectory**, before each sampled update, and combines it with the actually observed sampled cumulative regret table.

## Frozen pilot

First family: exact two-round Joker reduced game.

- MCCFR seed: `2026090601`;
- checkpoints: `1, 4, 16, 64` iterations;
- familywise failure probability: `0.05`;
- exact utility range: `Delta_u = 4`;
- action-coordinate union surface: all `39,456` regret coordinates;
- martingale-difference upper envelope: `2*Delta_u = 8`;
- predictable coordinate variation upper bound through iteration `T`:
  `Delta_u^2 * sum_t P_t(visit I | F_(t-1))`;
- one-sided scalar Freedman radius per coordinate;
- regret bridge: one radius per infoset after max over actions;
- exploitability accounting: half the sum of both players' average external-regret upper bounds.

## Required validation

1. The instrumented solver must produce exactly the same sampled regret table and RNG state as the uninstrumented solver for the same seed and iteration count.
2. Predictable visit accounting must remain iteration-aligned.
3. Every checkpoint bound must be finite and at least as large as the sampled-positive-regret-only contribution.
4. The artifact must separate sampled-positive-regret contribution from concentration add-on.
5. No result may be labeled a route certificate.

## Interpretation

This is the first gate that follows an actual adaptive sampled-regret trajectory. A numerically small bound would still not certify a route because the implementation/theorem unbiasedness bridge is currently supported by strong finite diagnostics rather than a frozen formal proof, and the scalable full-game reach-weighted average implementation is not yet validated.

A large bound is still useful: it identifies whether the remaining looseness comes mainly from sampled regret itself or from simultaneous concentration.

## Authority firewall

No M4Z route can become REAL from this pilot. REAL remains `0/50`.
