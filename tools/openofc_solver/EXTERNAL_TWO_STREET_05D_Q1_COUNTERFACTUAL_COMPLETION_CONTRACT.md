# OpenOFC 05D-Q1 — Counterfactual Information-Set Completion Contract

Status: **SHADOW RESEARCH / NOT CERTIFICATION**

Authority: `COUNTERFACTUAL_INFOSET_COMPLETION_SHADOW_ONLY`

## Why Q1 exists

05D-Q0 showed that the 5,000-iteration two-street UCT snapshot had an explicit policy at only the information sets it visited. Exact cross-profile evaluation can reach additional information sets after an opponent deviation. At those states the Q0 evaluator used a declared uniform fallback. Therefore Q0 mixed two effects: the learned search policy and the arbitrary fallback policy.

Q1 removes that mechanical ambiguity before any strategic conclusion is drawn.

## Frozen reduced game

Q1 keeps the same six-world R3->R4 finite-support fixture used by 05C/05D-Q0, the same canonical OpenOFC transitions, the same terminal utility, and the same canonical information-state keys. A complete physical world remains an internal simulator object only; hidden cards are forbidden from policy keys.

## Reachable-support materialization

Q1 exhaustively traverses every legal action from every frozen physical world and groups concrete simulator states by canonical information-state key. Every group must have one actor, one round, and one legal action set. Concrete hidden states may be retained internally only as compatible support for a resolver.

## Missing-information-set resolver

For each information set absent from a frozen base policy:

1. choose the local root action before sampling a compatible concrete hidden state;
2. sample one concrete state uniformly from the compatible finite-support group;
3. apply the selected local action;
4. roll out downstream decisions using the immutable frozen base profile;
5. if a downstream information set was also absent from the immutable base profile, use an explicit uniform rollout policy there;
6. update only the local root bandit;
7. repeat with deterministic seed derived from the experiment seed and canonical information-state key.

Every legal root action must be visited at least once. P0 maximizes canonical P0 utility; P1 minimizes it.

Newly resolved policies are never used to resolve another missing information set in the same completion pass. This prevents order-dependent recursive bootstrapping.

## Completed-policy requirement

A Q1 completed profile must contain an explicit normalized distribution for every information set reachable in the frozen reduced game. A strict evaluator must fail closed if either player's profile is absent at any reachable acting information set. Successful Q1 comparisons therefore have **zero unseen-information-set fallback**.

## Comparator symmetry

The same completion algorithm may be applied independently to the UCT base profile and to the MCCFR base profile. Each completion is resolved only against its own frozen base profile. Cross-profile evaluation then compares two fully explicit behavior profiles under the same strict evaluator.

## Interpretation boundary

The resolver's uniform weighting over compatible concrete states is a finite-support search prior. It is not claimed to be the posterior induced by earlier-round strategic signalling, a counterfactual-reach-weighted CFR belief, a Nash equilibrium belief, or an exploitability certificate.

Q1 may answer whether the Q0 cross-profile signal survives removal of unseen-state fallback. It cannot certify a real route, prove equilibrium quality, or promote evidence into M5C/M5H/M5L authority.

`real_routes_certified` remains `0`.
