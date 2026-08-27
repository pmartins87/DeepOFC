# M5Q predictable visit-variance reference contract

Status: exact reduced-game variance-accounting reference; **not certification**.

## Purpose

The coarse Freedman gate bounds every sampled regret coordinate as if it could be active on every iteration. External Sampling is substantially sparser: a traverser's regret coordinate can change only when its information set is reached by sampled chance/opponent decisions.

For a frozen pre-update profile, that visitation event is predictable. On the exact two-round reduced games this gate computes its probability exactly and uses

`E[X_t(I,a)^2 | F_(t-1)] <= P_t(visit I | F_(t-1)) * Delta_u^2`.

This is a rigorous conditional second-moment upper bound for the sampled coordinate increment, assuming the previously frozen `|X_t(I,a)| <= Delta_u` envelope. It does not estimate variance from observed samples.

## Frozen semantic checks

For each traverser and each frozen profile:

1. every visit probability is finite and in `[0,1]`;
2. total round-3 traverser visit mass is exactly `1`, because one traverser round-3 infoset is visited on every sampled traversal;
3. total round-4 visit mass equals the independently computed expected number of enumerated own round-3 branches;
4. the reference works for both the uniform profile and the deterministic hash-mixed regret-matching stress profile;
5. all authority remains non-certifying.

## Scope

The exact calculation is a reduced-game reference. It is allowed to enumerate the 32-outcome benchmark chance surface and opponent action distributions. It is not yet a claim that the same computation is scalable to the complete OpenOFC tree.

A PASS authorizes the next feasibility experiment to replace the crude `Delta_u^2` per-coordinate/per-iteration predictable-variance envelope with accumulated exact visit-probability envelopes on the reduced games.

## Authority firewall

A PASS does not prove External Sampling unbiasedness as a theorem, does not instantiate a final confidence sequence, does not provide a full-game variance implementation, does not certify exploitability, and leaves REAL at `0/50`.
