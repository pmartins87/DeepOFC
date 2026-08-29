# OpenOFC external research — 05G-Q1B uniform-local backward completion contract

Status: **precommitted completion-component experiment**  
Authority: `BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
REAL routes certified: **0/50**

## Why a separate completion component is mandatory

Q0C showed that Search materializes only ~2.85% of non-root 05G information states even after 50k iterations. Q0D scales MCCFR further, but any native learner may still leave part of the exact support missing.

A full policy cannot silently map every missing node to uniform play and then attribute the resulting EV to Search or MCCFR. Q1B therefore builds one explicit, learner-independent completion policy and labels every use of it.

## Completion name

`COMPLETION_UNIFORM_LOCAL_BACKWARD_V1`

This is a **baseline completion algorithm**, not an equilibrium solver and not production authority.

## Frozen inputs

The completion policy may use only:

- the frozen 36-world physical support;
- the exhaustive reachable information-set support;
- canonical legal actions;
- exact current-hand terminal utility;
- the acting player's identity;
- the concrete states compatible with the current information set.

It may **not** inspect:

- Search visits, values or probabilities;
- MCCFR regrets, visits or probabilities;
- Search-vs-MCCFR performance;
- exact best responses to Search/MCCFR;
- any production Bellman/runtime result.

Thus the same completion policy is generated once and reused for every learner profile.

## Backward construction

Build a deterministic pure action at every exhaustive information set, in reverse decision order:

1. P1-R4;
2. P0-R4;
3. P1-R3;
4. P0-R3.

For one information set and one candidate legal action:

1. enumerate every compatible concrete state in the frozen finite support;
2. apply the candidate action;
3. at every later information set, follow the already-frozen completion action for that later layer;
4. reach exact terminal current-hand utility `u0`;
5. average `u0` **uniformly over the compatible concrete states of the current information set**.

P0 chooses the action with maximum mean `u0`. P1 chooses the action with minimum mean `u0`.

Ties are broken by canonical lexicographic action key.

The stored completion distribution is pure: selected action probability `1.0`, all others `0.0`.

## Interpretation of the belief model

The local hidden-state belief is deliberately uniform over concrete states compatible with the current information set. It is not claimed to equal the strategic posterior induced by a learned policy.

This local reset can be dynamically inconsistent under signalling. That limitation is known in advance and is one reason 05G-Q3 exists: Q3 will measure counterfactual posterior distortion before any posterior-aware completion A/B.

Q1B must not call this baseline Bayesian-optimal, globally optimal, Nash, CFR or exact infoset EV.

## Completed profiles

Using Q1A provenance maps, create:

### S-complete

- `SEARCH_NATIVE` at every Search-native key;
- `COMPLETION_UNIFORM_LOCAL_BACKWARD_V1` everywhere else.

### M-complete

- `MCCFR_NATIVE` at every MCCFR-native key;
- completion everywhere else.

### H-complete

- `SEARCH_NATIVE` where Search exists;
- else `MCCFR_NATIVE` where MCCFR exists;
- completion on the remaining support.

Native distributions are immutable. Completion can never overwrite a native source.

## Required outputs

For each seed and each completed profile record:

- exhaustive completeness = 100%;
- source counts overall and by layer;
- source counts on ambiguous non-root infosets;
- canonical profile SHA256;
- canonical source-map SHA256;
- completion policy SHA256;
- native-preservation checks;
- number of completion states actually used;
- construction runtime and terminal evaluations;
- deterministic replay hash.

The same completion policy SHA must be used by S/M/H for a given frozen support; ideally it is seed-independent because the completion construction itself contains no learner seed.

## PASS gate

`PASS_EXPLICIT_COMPLETION` requires:

1. the completion policy covers every exhaustive information set;
2. each completion choice is legal and pure;
3. repeated construction is deterministic;
4. S/M/H are all 100% complete;
5. every native Search distribution is preserved byte-for-byte where used;
6. every native MCCFR distribution is preserved byte-for-byte where used;
7. H uses MCCFR only where Search is absent;
8. the completion source label appears only where no higher-priority native source exists;
9. source-count arithmetic equals exhaustive support;
10. no exact BR or strategic winner is computed in Q1B.

## Next gates

- **Q1C:** exact fixed-profile self-play and cross-play EV for the source-labeled S/M/H profiles. Cross-play remains descriptive, not equilibrium authority.
- **Q2:** exact bilateral BR0/BR1, NashConv and exploitability. Q2 is the ranking authority inside the reduced 05G fixture.
- **Q3:** exact counterfactual-posterior audit, explicitly testing the uniform-local belief assumption used by this completion baseline.

No production migration is permitted from Q1B.
