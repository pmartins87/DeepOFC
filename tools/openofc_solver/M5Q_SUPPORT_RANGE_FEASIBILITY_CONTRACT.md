# M5Q — External Sampling support and exact reduced-game range feasibility

## Authority

`EXTERNAL_SAMPLING_SUPPORT_RANGE_FEASIBILITY_NOT_CERTIFICATION`

This gate follows the Appendix-C `M_i(sigma*)` optimistic floor. It is structural diagnostics only; it cannot certify an M4Z route.

## Questions

The long-form Appendix-C convenience bound for sampled counterfactual-value differences may use `DeltaHatPrime_i = Delta_i / delta`, with `delta` a strictly positive lower bound on the sampling probability of terminal histories.

Before estimating variance, M5Q must answer two cheaper questions on exact reduced games:

1. What is the **exact terminal utility range** of the audited reduced game, rather than the global project envelope `206`?
2. Does the current no-explicit-exploration External Sampling regret matcher provide a strictly positive global terminal-history sampling floor `delta` after updates?

## External Sampling probability audited here

For traverser `i`, External Sampling enumerates the traverser's own actions and samples chance plus the opponent's actions. For a complete terminal history `z`, this gate defines

`q_i(z) = pi_chance(z) * pi_-i(z)`

under the frozen current profile.

The gate exhaustively enumerates all reduced-game terminal histories and records for each traverser:

- total terminal histories;
- count with `q_i(z) = 0`;
- minimum positive `q_i(z)` if any;
- maximum `q_i(z)`;
- global minimum `q_i(z)` including zeros.

A single zero-probability terminal history makes the convenient global `Delta_i / delta` substitution unusable with that profile because its global `delta` is zero. This does **not** invalidate External Sampling MCCFR itself; it invalidates only that particular strictly-positive-floor route to the Appendix-C deterministic constant unless support is changed or a different estimator bound is proved.

## Frozen pilot

### Exact terminal utility range

Exhaustively compute min/max raw P0 utility and `Delta_u = max-min` for:

- two-round Joker reduced game;
- two-round hidden-discard reduced game.

### Actual External Sampling support

Audit the two-round Joker `TwoRoundExternalSamplingMCCFR` current profile at precommitted checkpoints:

- iteration 0 (uniform initial regret matcher);
- iteration 1;
- iteration 4;
- iteration 16.

Seed: `2026090201`.

Both traversers are audited independently at every checkpoint. No epsilon exploration is injected; this is the actual current reduced-game External Sampling regret matcher.

## Interpretation firewall

- exact reduced-game utility ranges may tighten feasibility calculations for those reduced games only;
- they do not automatically transfer to full production routes;
- finding `delta=0` is a support diagnosis, not a strategic-quality result;
- adding exploration later would be a new training/sampling contract and must be separately audited;
- no variance estimate or concentration certificate is emitted here;
- REAL route count remains `0/50`.
