# External solver research policy

## Purpose

Before implementing an important OFC component from scratch, search for relevant public implementations, papers, engines, solvers, benchmarks and postmortems. The goal is to avoid needless reinvention and to learn from both successful designs and already-observed failures.

External sophistication is evidence to investigate, not authority to replace the current system.

## Mandatory workflow

For every material external candidate:

1. **Freeze the current baseline.** Record repository, branch, commit SHA, relevant run IDs, artifacts and current strategic certification count.
2. **Pin the external source.** Record repository, exact commit SHA, files used and date of audit. Do not audit a moving branch as if it were immutable evidence.
3. **Audit rules before algorithms.** Establish compatibility separately for player count, deck/Jokers, Joker semantics, opening, Pineapple streets, discard visibility, action order, scoring, scoop, royalties, foul, Fantasy entry/count/progression/stay, heads-up behavior, hidden information and unknown cards.
4. **Audit information sets.** Verify exactly what an agent is allowed to observe. Hidden opponent cards/discards may not leak through state features, action masks, rollout samplers or training labels.
5. **Classify each component.** Use exactly one current status where possible: `EQUIVALENT`, `BETTER_CANDIDATE`, `WORSE_FOR_TARGET`, `COMPLEMENTARY`, `RULE_INCOMPATIBLE`, or `INCONCLUSIVE`.
6. **Separate objective from implementation.** An exhaustive or fast algorithm can still optimize the wrong payoff. Record the exact objective/reward being optimized.
7. **Isolate proposed changes.** New algorithms enter on separate research/experiment branches or feature gates. They do not silently mutate the strategic baseline.
8. **A/B test against the frozen baseline.** Use common scenarios/seeds when valid, report uncertainty, failure cases, runtime and memory. Use exact/reduced-game authorities whenever available.
9. **Preserve certification firewalls.** Approximate Monte Carlo, MCTS, RL or learned exploiters can reject weak policies. They cannot certify low exploitability unless a valid upper-bound/certification authority exists.
10. **Promote only with objective evidence.** Promotion requires demonstrated correctness repair or material performance/strategic gain without rule drift, hidden-information leakage or weakened authority.

## Rule-compatibility checklist

Every audit must explicitly record:

- number of players;
- deck size, existence/count of Jokers;
- Joker substitution/tie-breaking semantics;
- opening deal and placement semantics;
- later-street cards dealt, cards placed and discards;
- discard visibility and dead-card handling;
- order of action and button behavior;
- showdown scoring and zero-sum convention;
- scoop rule;
- Top/Middle/Bottom royalty tables;
- foul definition and foul payoff;
- Fantasy qualification;
- Fantasy cards dealt;
- Progressive/Ultimate Fantasy mapping;
- Fantasy concealment and simultaneous/delayed response timing;
- stay/re-entry rules;
- heads-up-specific behavior;
- behavior when a nominally 3-max engine has only two players;
- information exposed to the agent;
- opponent policy/model assumptions;
- treatment/sampling of unknown cards.

If any target rule is unknown, mark it `INCONCLUSIVE`; do not silently fill it from another OFC ruleset.

## Evidence hierarchy

Prefer, in order:

1. executable source + tests at a pinned commit;
2. explicit source-of-truth rules/contract at the same commit;
3. reproducible benchmark artifacts;
4. project documentation/postmortems;
5. README claims;
6. external descriptions or secondary summaries.

A passing upstream test suite is a project claim until independently reproduced. A benchmark against a heuristic is not proof of optimality. A large training budget is not proof that the environment was correct.

## Heavy-training semantic gate

Before any expensive RL/self-play/model-training campaign, the exact engine/rules build must pass a SHA-bound semantic invariant suite. At minimum it must cover:

- rank ordering: Ace, all pair/trips orderings and kickers;
- all hand-category ordering and straight boundaries including wheel/Broadway;
- cross-row foul ordering;
- exact royalty tables;
- Joker target semantics including edge cases and two-Joker cases when applicable;
- Fantasy entry, exact 14/15/16/17 mapping where applicable, stay/re-entry and concealment;
- terminal scoring antisymmetry / zero-sum invariants;
- opening and Pineapple action cardinality/meaning;
- discard visibility and unknown-card accounting;
- information-set non-leakage;
- deterministic seed/replay invariants.

Training must fail closed if the approved semantic-suite identity does not match the engine/rules identity.

## Runtime separation

Strategic adoption and OpenHoldem/runtime adoption are distinct decisions. Recognition, table-map, UI timing, drag/confirm behavior and unknown-card recovery may use external ideas only through their own runtime tests. A strategic improvement does not imply live-runtime readiness, and a runtime improvement does not certify strategy.
