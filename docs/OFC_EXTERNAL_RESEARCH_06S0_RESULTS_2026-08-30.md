# OpenOFC external research — 06S0 exact global-suit automorphism

Date: 2026-08-30  
Branch: `research/external-ofc-solver-audit-20260827`  
Workflow run: `33294655789`  
Head SHA: `6cfed196ee82b7348cc961b65d44f6909b219780`  
Artifact: `openofc-external-06s0` (`9727027272`)  
Artifact ZIP digest: `sha256:fc196d78291a55720ac41963ca9c8f5587d12300e1fbdd2469db7739f86c1f40`  
Result manifest SHA-256: `ae9f07bb6e2f263cdb743aac276325988e3a0bbd260764d1666348e5a5586a98`

## Verdict

`GLOBAL_SUIT_PERMUTATION_IS_LOSSLESS_AUTOMORPHISM`

Next gate:

`SUIT_CANONICALIZATION_ELIGIBLE_FOR_SEPARATE_INTEGRATION_AB`

06S0 is a symmetry proof only. The strategic trainer remained unchanged and `real_routes_certified = 0`.

## Exact proof surface

The reference implementation enumerated all 24 global permutations of the four regular-card suit labels while leaving `JK1` and `JK2` unchanged.

All frozen checks passed with zero mismatches:

- deck bijection mismatches: `0`;
- inverse-permutation mismatches: `0`;
- complete-board score checks: `768`, mismatches `0`;
- explicit Joker-resolution checks: `96`, mismatches `0`;
- information-orbit mismatches: `0`;
- canonical legal-action-set mismatches: `0`;
- raw legal-action-bijection mismatches: `0`;
- one-step transition commutation checks: `37,296`, mismatches `0`;
- terminal-utility mismatches: `0`.

The randomized scoring sample contained Jokers in 24 of 32 two-board fixtures. Four additional explicit Joker boards exercised `JK1`, `JK2` and dual-Joker configurations.

## Information and recall firewalls

The canonicalizer starts only from the already-certified observable `information_state_key` payload. It never consults opponent private discards, opponent future packets or undealt cards.

The following also passed:

- hidden-information firewall preserved;
- own private-discard recall preserved;
- public placement history preserved;
- player/dealer position preserved;
- round preserved;
- rank changes not collapsed;
- public row-history changes not collapsed;
- `JK1` and `JK2` identity not collapsed.

## Scientific interpretation

A single global relabelling of clubs/diamonds/hearts/spades is an exact automorphism of the current HU normal-hand game implementation. Therefore all suit-isomorphic observable information states may, in principle, share one regret-table entry with transformed action keys without changing game value.

This is qualitatively different from hand-strength bucketing or neural generalization: no strategic information is intentionally discarded.

06S0 does **not** establish that a factor of at most `4! = 24` is enough to make direct tabular full-game MCCFR computationally viable. 06S1 must integrate the symmetry only in a research solver and rerun the recurrence gate against the raw 06B baseline.

`real_routes_certified = 0`.
