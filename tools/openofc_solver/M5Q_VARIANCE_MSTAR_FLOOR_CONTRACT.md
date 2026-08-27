# M5Q — Appendix-C `M_i(sigma*)` variance-bound floor

## Authority

`APPENDIX_C_MSTAR_VARIANCE_FLOOR_FEASIBILITY_NOT_CERTIFICATION`

This gate is a theorem-feasibility audit. It cannot certify an M4Z route and cannot change the REAL route count.

## Source theorem

The authoritative mathematical source for this gate is Richard Gibson's long-form treatment of *Generalized Sampling and Variance in Counterfactual Regret Minimization*, Appendix C, Theorem C.1 (the long version of the Gibson–Lanctot–Burch–Szafron–Bowling 2012 work).

For a perfect-recall game, under the assumptions of Lemma 5.1 and Theorem 5.4, and when the difference between two estimates at information set `I` can be bounded in the structured form

`vhat_i(I, sigma(I->a)) - vhat_i(I, sigma(I->b)) <= pi^sigma_-i(I) * DeltaHatPrime_i`,

Theorem C.1 gives, with probability at least `1-p`,

`R_i^T / T <= DeltaHatPrime_i * M_i(sigma_i*) * sqrt(|A_i|) / sqrt(T) + |I_i| * sqrt(Var[r_i-rhat_i]) / sqrt(p*T)`.

The long-form proof also states that ordinary sampled counterfactual values can satisfy the structured difference bound with `DeltaHatPrime_i = Delta_i / delta` for an appropriate positive sampling-probability floor `delta`.

## Why this gate exists

The first M5Q variance-floor gate used the published AAAI Theorem 2 surface containing `|I_i|` in the deterministic term. The long-form Appendix C theorem can replace that deterministic factor by the smaller, strategy-dependent `M_i(sigma_i*)` when its extra structure holds. The variance term, importantly, still retains `|I_i|`.

Before estimating variance, this gate asks the cheapest useful question: how small can the Appendix-C bound look on exact reduced games if we give it the two most optimistic assumptions possible?

1. `Var[r_i-rhat_i] = 0`.
2. sampling probability floor `delta = 1`, so `DeltaHatPrime_i = Delta_i`.

Any real External Sampling run can only worsen either assumption unless exact additional structure proves otherwise.

## Exact reduced-game `M_i(sigma_i*)`

For every audited profile, the reduced game has an independently exact pure best response. The gate computes the best-response reach-weighted

`M_i(sigma_i*) = sum_{B in B_i} pi_i^{sigma_i*}(B) * sqrt(|B|)`,

where `B_i` partitions player-`i` information sets by the player's own action sequence leading to the information set.

For the two-round benchmark:

- all round-3 information sets share the empty own-action prefix;
- round-4 information sets are grouped by the exact remembered own round-3 action, including hidden discard;
- a round-4 group has pure-response own reach one iff the exact best response selected that remembered round-3 action at at least one compatible predecessor information set; otherwise its own reach is zero.

The computed `M_i(sigma_i*)` must never exceed the static `M_i = sum_B sqrt(|B|)` already audited by M5P.

## Frozen pilot profiles

The first pilot uses exact reduced profiles only:

- Joker family: uniform profile and standard full-tree CFR average after 8 iterations;
- hidden-discard family: uniform profile and standard full-tree CFR average after 1 iteration.

For each profile the pilot reports:

- exact best-response values / exact NashConv;
- static `M_i` and exact best-response `M_i(sigma_i*)` for both players;
- zero-variance Appendix-C exploitability coefficient;
- bound at 1,000,000 iterations;
- required iterations for target exploitability `0.15`;
- unit utility-range surface (`Delta_i = 1`);
- conservative project raw HU OFC utility-range surface (`Delta_i = 206`);
- the explicit optimistic assumption `delta = 1`.

## Fail-closed interpretation

A small result is only evidence that the theorem remains numerically worth investigating. It is not a production bound because this gate sets estimator variance to zero and sampling floor to one.

A large result under the raw-range surface is strong evidence against using this theorem as the primary practical certificate, but route-local utility ranges may only replace `206` after they are derived exactly and SHA-bound; they must not be assumed after observing results.

The next variance-aware gate is allowed only if this structural floor remains promising enough to justify the extra work. That next gate must separately address the actual External Sampling estimator variance, the required simultaneous confidence statement, and the sampling-probability condition.

## Firewall

- no threshold is tuned from pilot results;
- no M4Z route becomes REAL;
- no sampled regret table becomes a certificate;
- `REAL = 0/50` remains unchanged.
