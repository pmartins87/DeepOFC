# OpenOFC external research — 05E exact reduced-game exploitability

Date: 2026-08-28

Authority: `EXACT_FINITE_SUPPORT_TWO_STREET_BR_REDUCED_GAME_ONLY`

This result belongs to the isolated external-solver research branch. It does not certify any real Bellman route and does not alter the production solver authority.

## Authoritative run

- workflow run: `33144245830`
- artifact: `9675337526`
- artifact ZIP SHA-256: `dbb407cee553b57239a0fef00fb9d46f076ef2f7a19e89c512a15a467381f7da`
- payload manifest SHA-256: `3047efb35b25b2f0e80116ee23186e3a2da74d898f21dfc6fbfee7181677c63a`
- exact-BR smoke: `33144108934`, 3/3 tests PASS

## Exact six-world result

| Profile | self-play u0 | BR0 | BR1 | NashConv | exploitability |
|---|---:|---:|---:|---:|---:|
| Search completed | 27.2134607631 | 28.0000000000 | -27.2044796875 | 0.7955203125 | **0.39776015625** |
| MCCFR completed | 27.0992118056 | 28.0000000000 | -23.3333333333 | 4.6666666667 | **2.33333333333** |

Within this frozen reduced fixture, the completed Search profile is substantially less exploitable than the completed current-regret-matching MCCFR profile: exploitability differs by about `1.93557` points, or roughly a factor of `5.87`.

This reverses the tempting interpretation of the earlier cross-play result where MCCFR P0 gained about +0.50 against Search P1. Cross-play EV alone was not a reliable equilibrium-quality ranking. Exact bilateral best response is the stronger reduced-game diagnostic.

## Important limitation discovered by 05D-Q2

The six-world fixture has 16,381 reachable information sets, but only one information set has more than one compatible concrete hidden state. Consequently it barely exercises hidden-state ambiguity after the root. The corrected Q2 run `33144391169` therefore observed zero TV between uniform and conditional counterfactual reach on the only multi-state information set.

The next benchmark must deliberately create hidden-discard overlap: distinct physical worlds whose private discarded cards differ while their public placements are identical, causing later opponent information sets to contain multiple concrete states. This is required before treating the Search-vs-MCCFR ranking as representative of the real imperfect-information problem.

## Decision

- keep Search/ISMCTS-style information-set search as a live candidate;
- keep MCCFR as an independent comparator and potential training backbone;
- do not promote either from this fixture;
- construct the 05F public-chance-root hidden-discard-overlap benchmark;
- require exact-BR comparison again on that harder fixture before any architecture decision.

`real_routes_certified = 0`.
