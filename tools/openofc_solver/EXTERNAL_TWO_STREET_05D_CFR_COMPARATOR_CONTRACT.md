# External two-street search vs CFR comparator — 05D contract

Status: **DESIGN FROZEN / DORMANT UNTIL 05C-Q1 RESULT IS PRESERVED**.

Authority: `REDUCED_GAME_STRATEGIC_COMPARATOR_NOT_CERTIFICATION`.

## Purpose

05C establishes that a legal information-set tree can be searched across R3→R4. 05D will answer the first strategy-quality question on that reduced game: how does the search policy compare with a regret-minimization policy trained on exactly the same finite physical-world support and exact terminal utility?

05D is deliberately a comparator, not an exploitability certificate. The six-world fixture is too small and is not a strategically conditioned posterior for the real game.

## Frozen game identity

The comparator must use the exact same game object as 05C:

- same coherent R3 root;
- same six complete physical worlds and uniform chance weights;
- same canonical `information_state_key` identities;
- same legal action generator and `child_state` transitions;
- same physical 54-card semantics / 34 dealt cards in each HU world;
- same canonical zero-sum terminal utility;
- no heuristic leaf evaluation, rollout bonus or determinized perfect-information shortcut.

A world may determine private cards and chance, but no policy may condition on a world identifier or opponent/future private cards outside the canonical information state.

## Independent CFR-family comparator

The first implementation should use external-sampling MCCFR because the existing DeepOFC research history already supports this architecture on imperfect-information HU subgames and because full-tree enumeration can become unnecessarily expensive.

Required mechanics:

1. one global iteration uses the same pre-update regret tables for the P0 and P1 traversals;
2. at a traverser's information set, enumerate every legal action;
3. at the opponent's information set, sample from the current regret-matching policy;
4. chance samples only from the frozen six-world support;
5. update regrets in the traverser's own utility sign;
6. stable canonical action ordering and frozen RNG seeds;
7. no policy table may be indexed by hidden world identity.

The comparator must clearly distinguish:

- current regret-matching profile;
- any behavioral time average;
- any own-reach-weighted CFR average estimator.

A plain local time average must **not** be mislabeled a theorem-backed CFR average when repeated own decisions are present. If a reach-weighted average is implemented, its estimator and validation must be explicit.

## Search policy extraction

05D must not compare CFR against only one root action while silently changing deeper behavior. A complete search profile is required for every reached information set. The frozen first candidate is:

- action probabilities proportional to visit counts at each information set;
- if an information set has zero recorded visits, use a declared fail-closed fallback (uniform canonical policy for research comparison only);
- profile snapshot is SHA-bound to search budget, seed, support and source files.

A deterministic greedy-by-visits profile may also be measured as a secondary ablation, but must be labeled separately.

## Evaluation matrix

At minimum preserve:

- value of search profile vs CFR profile on the frozen six-world game;
- value of CFR profile vs search profile;
- self-play value of each profile;
- policy agreement by information set, weighted and unweighted;
- root-policy total variation distance;
- terminal-work-normalized training/search runtime;
- information-set/action coverage;
- unilateral learned-response lower bounds against each profile for both players.

Where exact evaluation of a fixed pair of behavioral profiles is tractable on the reduced support, use exact enumeration. Learned response remains a lower bound on exploitability, not a certificate.

## Budgets and seeds

05D budgets must be selected only after reading the 05C-Q1 stability artifact. The contract therefore freezes no numerical training budget yet. Budget choice must be documented before the first 05D run; it may not be tuned after seeing held-out comparator results without creating a new experiment ID.

## Promotion / authority firewall

05D can establish that one reduced-game algorithm beats another under a frozen finite support. It cannot establish real-game optimality or low exploitability.

No 05D artifact may:

- populate M5C as `HELD_OUT` certification evidence;
- emit a certification-eligible M5H reference manifest;
- create a REAL Bellman route;
- modify live/runtime strategy;
- claim the six-world support is the real posterior after earlier-round signalling.

Any future attempt to turn a CFR-family evaluator into certification authority must pass the independent M5L reference-evaluator qualification process.

REAL route certificates therefore remain `0/50` throughout 05D.
