# OpenOFC 06S preparatory research — exact symmetry before approximation

Date: 2026-08-30  
Status: **preparatory only; not activated unless a full-game recurrence gate justifies it**

## Purpose

This note records the lossless state-space reductions that should be investigated before any approximate abstraction or neural generalization is allowed into the full-game solver.

The note does not change `strategic_cfr.py`, does not select a strategy and does not certify a production route.

## External research checked first

1. Lanctot, Waugh, Zinkevich & Bowling (NIPS 2009), *Monte Carlo Sampling for Regret Minimization in Extensive Games* — MCCFR provides sampled regret updates and convergence guarantees, but large concrete information-state spaces remain a practical representation problem.
   - https://papers.nips.cc/paper_files/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
2. Waugh (AAAI 2013), *A Fast and Optimal Hand Isomorphism Algorithm* — global suit permutations can be canonicalized exactly in poker; strategically isomorphic hands map to one representative without sacrificing value.
   - https://www.cs.cmu.edu/~waugh/publications/isomorphism13.pdf
3. Brown et al. (2019), *Deep Counterfactual Regret Minimization* — very large imperfect-information games can make tabular CFR impractical; function approximation is one way to generalize across information states, but it introduces approximation and therefore cannot be labelled mathematically exact.
   - https://arxiv.org/abs/1811.00164
4. Brown & Sandholm (2019), *Solving Imperfect-Information Games via Discounted Regret Minimization* — modern regret weighting can materially accelerate convergence, but algorithmic acceleration is distinct from solving a representation that almost never revisits the same table key.
   - https://arxiv.org/abs/1809.04040

## Source audit of DeepOFC

`tools/openofc_solver/engine.py` represents each regular card as `(rank, suit)` with four suits `c,d,h,s`; both Jokers are suitless physical cards `JK1` and `JK2`. Hand evaluation depends on rank relations and equality of suits, not on the names assigned to the four suits. The legal-action generator depends on row capacities and incoming-card indices, not suit labels.

Therefore a **single global permutation of the four regular-card suit labels** is a candidate exact automorphism of the current normal-hand game. There are at most `4! = 24` such permutations. Jokers must remain unchanged unless a separate exact Joker-identity symmetry is independently proved.

## Candidate exact canonicalizer

The safest initial implementation is deliberately simple rather than clever:

1. enumerate all 24 global suit permutations;
2. apply each permutation to every regular card legally observable at the information state:
   - own board;
   - opponent public board;
   - own private discards;
   - current incoming packet;
   - every public-history placement;
3. leave `JK1` and `JK2` unchanged;
4. serialize each transformed information state using the existing canonical sorting rules;
5. select the lexicographically smallest serialization as the canonical information-state key;
6. transform legal action keys under the **same selected permutation** before entering the regret table.

This avoids heuristic suit features and preserves flush/blocker relations exactly.

## Mandatory proof obligations before integration

A suit-canonical path may not replace the raw path until deterministic exhaustive/randomized tests establish all of the following:

- **score invariance**: applying any of the 24 global suit permutations to two complete boards leaves `score_heads_up` identical;
- **Joker-resolution invariance**: row-local Joker resolution and royalties are unchanged by suit renaming;
- **legal-action bijection**: every legal raw action maps to exactly one legal transformed action and vice versa;
- **transition commutation**: suit-transforming after `child_state` equals applying the transformed action in the transformed state;
- **information-state orbit identity**: globally suit-isomorphic observations share one canonical key;
- **hidden-information firewall**: canonicalization never inspects opponent private discards, opponent future packets or undealt cards;
- **perfect recall**: public action history and own private discard memory remain present after canonicalization;
- **action-key stability**: a canonical information state always produces the same canonical legal-action-key set;
- **checkpoint reproducibility**: canonicalized training preserves the 06A byte-exact resume property.

## Important non-reductions

The following must **not** be collapsed merely to save memory:

- public placement timing/history: it can carry strategic signalling and perfect-recall information;
- dealer and non-dealer positions: acting order makes them strategically distinct;
- arbitrary rank relabelling: straights, royalty thresholds and remaining-deck structure make rank labels strategically meaningful;
- different hidden opponent cards that are not related by an actual game automorphism;
- approximate strength/equity buckets under an `EXACT` label.

## Joker identity

The engine treats the two physical Jokers as `JK1` and `JK2`, while scoring substitutes Jokers row-locally by the same rule. A `JK1 <-> JK2` swap may therefore be another exact automorphism and could add up to a factor of two. It is **not assumed here**. It requires a dedicated proof across deal uniqueness, legal actions, information keys, transitions, complete-board resolution, scoring and runtime card mapping before use.

## If exact symmetry is insufficient

If a lossless symmetry layer still leaves the full game reuse-starved, the project should compare larger architectural options rather than simply raising iteration count:

- public-state/subgame decomposition with exact or bounded local solving;
- more suitable sampled-CFR variants for large action spaces;
- regret/value function approximation such as Deep CFR, explicitly labelled approximate;
- hybrid blueprint plus real-time re-solving;
- carefully bounded abstractions with independent exploitability/lower-bound diagnostics.

No approximate route is authorized by this note.

`real_routes_certified = 0`.
