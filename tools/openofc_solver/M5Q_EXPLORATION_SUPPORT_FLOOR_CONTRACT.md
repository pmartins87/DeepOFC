# M5Q — exploration-supported Appendix-C floor

## Authority

`EXPLORATION_SUPPORTED_APPENDIX_C_FLOOR_NOT_CERTIFICATION`

This gate asks whether the simplest repair for the zero-support problem is numerically viable: mix every current regret-matching distribution with a uniform exploration policy so every legal opponent action retains positive probability.

It does **not** change the production trainer. It evaluates frozen mixed profiles on the exact reduced Joker game only.

## Frozen base profile

- game: exact two-round Joker benchmark;
- External Sampling seed: `2026090201`;
- current regret-matching profile after 16 iterations;
- exact reduced-game terminal utility range: `Delta_u = 4`.

## Exploration family

For every information set with legal action set `A`, define

`pi_epsilon(a|I) = (1-epsilon) * pi_current(a|I) + epsilon / |A|`.

Precommitted epsilon values:

- `0.01`
- `0.05`
- `0.10`
- `0.20`
- `1.00`

`epsilon=1` is the full-uniform support ceiling for this simple family and is intentionally included as the most support-friendly endpoint.

## Quantities

For every epsilon:

1. exhaustively compute External Sampling terminal-history support for both traversers;
2. set `delta` to the smaller exact global terminal sampling probability across both traversers;
3. compute the exact best-response `M_i(sigma_i*)` Appendix-C zero-variance floor using `DeltaHatPrime = Delta_u / delta`;
4. report bound at 1,000,000 iterations and required iterations for target exploitability `0.15`;
5. report exact exploitability of the mixed frozen profile, but do not use it to tune epsilon.

## Decision rule

If even `epsilon=1` requires an impractical iteration count under the impossible-best-case `Var=0` theorem surface, the simple uniform-mixture exploration repair is rejected as the primary certification route. Smaller epsilon values cannot then rescue the theorem through support alone.

This does not reject exploration as a training technique. It rejects only the use of the Appendix-C `Delta_u/delta` global terminal-support bound as the primary practical certificate under this simple exploration family.

## Firewall

- no epsilon is selected from the results for production training;
- no variance term is estimated;
- no M4Z route is certified;
- no production trainer semantics change;
- REAL remains `0/50`.
