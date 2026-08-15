# DeepOFC decision-engine architecture v1

## Objective

The final player must choose every placement/discard in KKPoker OFC Joker Ultimate, including one-shot 14–17-card Fantasy, using a mathematically grounded strategy rather than hand-strength heuristics.

The problem must be separated into layers because OFC combines:

- exact combinatorial poker scoring;
- irreversible row-placement decisions;
- chance draws from a 54-card physical deck;
- public opponent rows;
- private incoming cards and hidden discards;
- action order;
- future Fantasy continuation value;
- 2-player zero-sum and 3-player multi-player interaction.

A locally strongest Hero board is not generally the strategically optimal action because points depend on row-by-row comparison, scoop, royalties, foul risk, future Fantasy and what opponents can still complete.

## Layer 0 — exact rules/scoring/action space

Already present or substantially present:

- physical 54-card model;
- board-aware Joker evaluator;
- ordinary-hand validity (no Five-of-a-Kind);
- 3/5/5 foul semantics;
- royalties and scoop;
- normal UI-legal action enumeration;
- exact lazy Fantasy action enumeration;
- deterministic deck/action/settlement primitives.

No learned model is allowed to override these rules.

## Layer 1 — exact terminal kernels

The first exact strategic kernels solve states with no future chance after Hero's action.

### Normal round 5

Given:

- Hero's 11 committed cards;
- Hero's final 3 incoming cards;
- complete opponent board(s);

there are at most 27 raw later-round actions and usually fewer because row capacities prune them. Every action can be scored exactly.

The current R5 kernel additionally exposes Fantasy continuation as an explicit external value. This is important: a placement that earns 14/15/16/17-card Fantasy has value beyond the current hand, and that value must not be hidden inside a heuristic bonus.

### Fantasy

Fantasy is also terminal with respect to current-hand placement once the 14–17 private cards and relevant opponent boards/distributions are known, but its raw action space is large:

- 14 cards: 1,009,008 canonical boards;
- 15 cards: 7,567,560;
- 16 cards: 40,360,320;
- 17 cards: 171,531,360.

Production Fantasy solving therefore needs exact branch-and-bound / subset dynamic programming rather than blind materialization.

## Layer 2 — exact Fantasy optimizer

Target formulation for a fixed opponent completed board:

maximize

`row points + scoop + Hero royalties - opponent royalties + re-Fantasy continuation`

subject to:

- choose 13 of N physical cards;
- Top=3, Middle=5, Bottom=5;
- Bottom >= Middle >= Top after global Joker optimization;
- unused N-13 cards become discards.

Planned exact acceleration:

1. precompute every 3-card subset Top rank/royalty/row result;
2. precompute every 5-card subset Middle/Bottom rank/royalty/row result;
3. represent subsets as N-bit masks;
4. join only disjoint Bottom/Middle/Top masks;
5. prune impossible row-order combinations before constructing full boards;
6. maintain admissible upper bounds for remaining row points + royalties + scoop + continuation;
7. regression-test optimized search against the raw exact iterator on 14-card and reduced-card subspaces.

For an opponent whose Fantasy board is still hidden, utility is expectation over that opponent's strategy/distribution, not comparison against a fictitious known board.

## Layer 3 — normal-play stochastic search

Rounds 1–4 have future random draws. A candidate placement must therefore be valued by future continuation, not only by current hand strength.

A minimal non-equilibrium baseline can perform seeded Monte Carlo rollouts:

`candidate action -> future 54-card chance draws -> future placement policy -> terminal exact score`

This is useful for engineering and convergence tests but is not the final mathematically optimal policy, because opponent future choices are strategic.

## Layer 4 — extensive-form game solution

### Heads-up

Before rake/cash-cap, HU pairwise OFC is zero-sum. The target representation is an extensive-form imperfect-information game with perfect recall:

- chance = physical card deals;
- private information = each player's incoming cards and known own discards;
- public information = committed rows, actor/order, visible Fantasy state and public history;
- action = canonical row placement/discard partition, never visual slot order;
- terminal utility = exact raw points + correctly solved continuation value.

Candidates to benchmark:

- external-sampling MCCFR;
- outcome-sampling MCCFR;
- CFR+/DCFR on tractable subgames;
- continual re-solving from the live public state;
- hybrid search with a learned value/policy function for deep continuation states.

We will not select one by analogy with Hold'em. R6 must benchmark them on exact small subgames where exploitability/best response can be measured.

### Three-player

Three-player OFC is not a two-player zero-sum game. Pairwise raw points still sum to zero globally, but strategic interaction is multiplayer/general-sum at the individual pairwise-decision level and standard two-player CFR convergence guarantees do not transfer automatically.

R6 must therefore treat 3-player separately and benchmark multiplayer self-play / equilibrium-approximation methods rather than silently reusing the HU solver.

## Layer 5 — infinite-horizon Fantasy continuation

Current-hand decisions can change the probability/type of the next Fantasy hand. Therefore the truly correct objective is not simply one-hand points.

We will expose continuation values explicitly by qualification state, initially something like:

- V14 = expected value of entering 14-card Fantasy next hand;
- V15;
- V16;
- V17;
- re-Fantasy continuation states as their exact rules are frozen.

These values can be solved by self-consistent value iteration / policy evaluation around the per-hand solver rather than approximated with arbitrary royalty bonuses.

## Layer 6 — KKPoker economics

Only after raw strategic scoring is correct do we layer:

- cash point conversion;
- win cap;
- rake attribution;
- rakeback/PVI if relevant to actual decision EV.

A rule/economic uncertainty must remain explicit and may not contaminate the raw game solver.

## Runtime policy hierarchy

The production decision path should ultimately be:

1. exact canonical state validation;
2. exact terminal/subgame lookup where available;
3. equilibrium/base policy for the current information set;
4. optional opponent-specific best response only behind evidence/confidence gates;
5. deterministic action plan for physical drag/drop;
6. post-action rescrape verification.

No GUI/tablemap heuristic is permitted to substitute for a missing strategy value.

## Immediate work order

1. complete deterministic simulator invariants (R4);
2. certify exact normal round-5 decision kernel (R5);
3. build exact Fantasy subset optimizer and compare against raw enumeration;
4. add Monte Carlo continuation baseline for rounds 1–4;
5. construct small HU extensive-form subgames with exact exploitability measurement;
6. benchmark CFR-family / search methods;
7. only then commit Ryzen 9 time to large training/self-play.
