# External two-street information-set search contract (05C)

Status: **DESIGN FROZEN / DORMANT UNTIL 05B PASS**.

Planned authority: `FINITE_SUPPORT_R3_R4_INFOSET_TREE_SHADOW_ONLY`.

## Why 05C is different from 05A/05B

05A and 05B live entirely on R4. Once P0 chooses an R4 action, P1 answers and the hand terminates. That makes the finite-support reference simple: for each hidden P1 packet, P1's terminal best reply can be enumerated exactly.

A two-street R3→R4 tree is strategically different. Future private packets and public R3 actions alter later information sets. The same R3 information set can lead to many R4 information sets, and optimal play in a zero-sum imperfect-information subgame may require mixed strategies. Therefore a naive determinization-by-determinization minimax is **not** an exact reference for 05C.

## Frozen 05C game boundary

The experiment starts at a coherent non-terminal HU state:

- `round_index = 3`;
- `actor = P0`;
- both boards and private discard memories exactly match a legal history through R2;
- P0's current R3 packet is observed by P0;
- P1's current R3 packet is hidden from P0;
- both R4 packets are future private chance and hidden from both players until their R4 decisions;
- all cards belong to one physical 54-card world with no duplication.

One complete physical world is sampled per iteration. The world may drive state transitions, but hidden/future cards must never enter a decision-node identity before they become legal information.

## Information-set tree

Traversal order:

1. **P0 R3** — maximize P0 utility. Node key: canonical `information_state_key` for P0 R3.
2. **P1 R3** — minimize P0 utility. Node key: canonical P1 R3 information state after observing P0's public placement.
3. **P0 R4** — maximize P0 utility. P0 now observes its R4 packet; node key must include it through canonical state only.
4. **P1 R4** — minimize P0 utility. P1 observes its own R4 packet and all public placements.
5. **Terminal** — canonical exact zero-sum HU score.

Every tree node is keyed by legal information only. No node may be keyed by world ID, opponent private packet, opponent private discard, future packet, RNG state or determinization fingerprint.

## Selection rule for first shadow implementation

For mechanical continuity with 05B:

- P0 nodes use UCB1 on P0 utility;
- P1 nodes use the mirrored lower-confidence rule on P0 utility;
- unvisited actions are expanded in stable canonical order;
- one sampled world is carried through the complete trajectory;
- statistics aggregate across worlds that map to the same legal information state.

This is a search baseline, not an equilibrium theorem.

## Required physical-world firewall

Before an episode starts:

- exactly one world object supplies every still-hidden/current/future packet;
- every physical card is unique across committed boards, private discards, observed packets and hidden/future packets;
- the sampled world is compatible with all public cards and the acting player's remembered private information;
- same seed + same root state + same support produces deterministic replay.

The split-sampling pattern in which P1 R3, P0 R4 and P1 R4 are independently drawn from separate decks is forbidden because it can represent no real deal.

## Validation stages

### 05C-Q0 — mechanical smoke

May start only after 05B is green. Required:

- canonical information-state isolation tests for all four decision layers;
- physical-card conservation tests;
- deterministic replay;
- zero-sum terminal symmetry;
- no exact-response helper inside the search loop;
- node/action-set stability;
- finite runtime on a deliberately tiny frozen world support.

Q0 makes no strategy-quality claim.

### 05C-Q1 — reduced-support reproducibility

Run several seeds and budgets. Measure:

- selected root action stability;
- root value dispersion;
- information-set count growth;
- visit concentration;
- terminal utility distribution;
- fraction of reached infosets with complete action coverage.

Still shadow-only.

### 05D — strategic comparator

The correct next comparator is a CFR/MCCFR solver on the **same reduced two-street support and action space**. Because the game can require mixed strategies, 05D must not call naive per-world minimax an exact oracle.

Preferred comparison outputs:

- value of the search policy against the reduced-game CFR average policy;
- value of the CFR policy against the search policy;
- unilateral learned-response lower bounds for each side;
- policy/action agreement by information state;
- terminal-work-normalized runtime.

A reference becomes certification-eligible only through the separate M5H/M5L authority process. 05C/05D by themselves can never create REAL Bellman routes.

## Promotion rule

05C code may be promoted from dormant design to executable shadow experiment only when 05B has a green artifact satisfying its frozen contract. No 05C result may modify the canonical M5 policy, route registry, certification firewall or live runtime.

## Explicit non-claims

Even a perfect 05C mechanical PASS does not establish:

- full-game ISMCTS convergence;
- strategic posterior correctness after R0-R2 signalling;
- exploitability bounds;
- superiority over MCCFR/DCFR/M5B;
- Fantasy continuation correctness;
- production/live authority;
- any REAL route certificate.
