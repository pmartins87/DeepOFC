# External R4 two-level information-set search contract (05B)

Status: **research / screening only**.

Authority: `UNIFORM_FINITE_SUPPORT_R4_TWO_LEVEL_INFOSET_UCT_SCREENING_ONLY`.

## Purpose

05A used a legal P0 information-set root but delegated every P1 response to an exact final-round best-response helper. 05B removes that shortcut so both players are represented by explicit search nodes.

The experiment is intentionally reduced to the final normal OFC street and a frozen finite support of hidden P1 packets. Its job is to test information-set search mechanics against an independently enumerable reference, not to replace M5/CFR or certify strategic routes.

## Required semantics

1. P0's root node is keyed only by `information_state_key(state)` and must be identical across every hidden P1 packet in the frozen support.
2. The hidden P1 packet is sampled **after** P0's root action is selected. P0 can never condition its action on a determinization.
3. After the public P0 placement, P1 acts in `information_state_key(after_root)`. P1 may legally condition on its own current packet, own remembered discards, both public boards and public action history.
4. P0 maximizes canonical P0 terminal utility; P1 minimizes the same quantity.
5. No heuristic terminal evaluator, rollout bonus or Fantasy proxy is allowed.
6. The exact finite-support enumerator is permitted only as an independent validation oracle outside the search loop.

## Search rule

- P0: UCB1 over P0 utility.
- P1: mirrored lower-confidence selection over P0 utility.
- Stable lexicographic tie-breaking.
- One support packet sampled uniformly per iteration.
- Terminal utility from the canonical zero-sum HU scorer.

When every P1 action has been visited for every hidden world reached under the selected P0 action, the experiment may report an empirical support backup. This is evidence about the frozen reduced support only.

## PASS conditions for 05B pilot

- unit tests green;
- deterministic replay under frozen seed;
- selected P0 action belongs to the exact finite-support optimum set;
- every hidden world for the selected P0 action has been reached;
- every P1 action in those selected-action worlds has been visited;
- the resulting selected-action support backup equals the independent enumerated value within numerical tolerance.

## Non-authority firewall

A 05B PASS does **not** imply:

- a strategic posterior after earlier-round signalling;
- convergence of full OFC ISMCTS;
- exploitability certification;
- a REAL Bellman route;
- superiority to the current M5 strategic architecture.

A green 05B only authorizes the next research step: a two-street information-set tree shadow experiment (05C).
