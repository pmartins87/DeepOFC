# M5R — Pre-frozen calibrated three-round BR interval frontier

Status: **reduced-game certification-methodology research only**. This gate certifies no production route and leaves `REAL = 0/50`.

## Objective

The exact M5R BR validation ladder established exact three-round best-response authority on the V1/V2 reduced benchmark families. The conservative interval bridge then established that low-counterfactual-reach **opponent** child subtrees may be replaced by a rigorous state-local utility envelope while preserving containment of the exact BR value and while never pruning a responding-player action.

The initial positive thresholds (`0.01`, `0.05`) were intentionally coarse and proved unusable: they collapsed terminal work to zero and produced very wide intervals. The opponent-reach geometry gate therefore enumerated the exact discrete positive reach values at every legal cut point before this frontier was defined.

This gate measures the complete stepwise compute-versus-bound frontier induced by those observed discrete reach levels. It does **not** select a production threshold after seeing the result.

## Frozen upstream evidence

The threshold panel is bound to evidence that existed before any calibrated frontier cell was run:

- exact BR validation ladder run `33426520598`;
- exact ladder aggregate file SHA-256 `948139daa538ba5af8faa31b5dee3eada4efc01289f66d98dfefae135beddb9d`;
- conservative interval bridge run `33427294227`;
- bridge aggregate file SHA-256 `b44c01e1c17c8ada4e477dc008fc66975b36dca1d7e1405f66ec251a9f37e985`;
- opponent-reach geometry run `33448898087`;
- reach-geometry internal canonical SHA-256 `40f73f3cda42921983d48f5fc688e6ce3af9c709f50c8a385747948846a98c20`;
- reach-geometry workflow artifact digest `sha256:ee8ecc38382fef8408cb98abf26dfc6e9da5e813ad2e909c54b9ae2122accee9`.

The concrete threshold hex values and expected exact-reference values are frozen in `m5r_calibrated_threshold_manifest.py`.

## Threshold rule

For each benchmark family, the positive threshold panel is exactly the sorted set of **all distinct positive opponent-counterfactual-reach levels observed by the geometry gate for that family**. No threshold is inserted, removed, tuned, or shifted based on interval width or runtime.

The threshold comparison remains the bridge's frozen rule:

`child_counterfactual_reach <= prune_reach_threshold`

subject only to the already frozen numerical epsilon in the bridge implementation.

Threshold zero is represented by the exact BR reference row. The calibrated frontier runner does not re-run the zero-threshold interval traversal because the previous bridge gate already proved that threshold zero reproduces the exact BR and full terminal-history count. This avoids duplicating exact work while retaining the same scientific baseline.

## Cell invariants

Every V1/V2 × P0/P1 cell must:

1. reproduce the pre-frozen exact BR value and exact terminal-history count;
2. use exactly the family-specific threshold hex panel in the frozen manifest;
3. retain every responding-player action (`own_action_pruning_count == 0`);
4. contain the exact BR value inside every positive-threshold interval;
5. never increase terminal utility evaluations as the threshold increases;
6. exercise at least one positive-threshold work reduction;
7. remain explicitly in reduced-game methodology authority only;
8. keep `production_certification_eligible = false` and `real_routes_certified = 0`.

## Interpretation firewall

The output is a measured Pareto-like frontier, not a certification threshold decision. Reporting which rows are narrowest or cheapest is descriptive only. A later gate may precommit a full-game transfer rule using this evidence, but it may not retroactively label one calibrated row as a production certificate.

The reduced game also omits the full continuation/Bellman remainder. Therefore even a very tight reduced-game interval cannot authorize M5H/M5C certification. A full-game evaluator must preserve the same counterfactual-reach semantics and must carry a conservative bound over the continuation-coupled value, not merely the terminal raw-point envelope.

## Success verdict

A cell may emit `PASS_M5R_CALIBRATED_INTERVAL_FRONTIER_CELL` only when all invariants above hold. The aggregate may emit `PASS_M5R_CALIBRATED_INTERVAL_FRONTIER` only when all four cells pass.

Neither verdict grants production authority. `REAL` remains `0/50`.