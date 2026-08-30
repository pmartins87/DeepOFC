from __future__ import annotations

"""06R1F: precommitted low-budget R4 top-action sample-efficiency suite.

This wrapper intentionally reuses the frozen 06R1 belief-correct learners and exact
R4 oracle. It changes only the fixture suite and evaluation budgets, then adds a
tie-safe operational interpretation based on exact top-action regret.

Promotion authority is global across all 12 frozen fixtures; an individual job has
no promotion authority.

Oracle semantic requirement: P1 best response is grouped by P1 information state.
Multiple posterior worlds may share one P1 infoset; P1 must choose one response for
that infoset and may not best-respond independently to hidden worlds.
"""

import argparse
import hashlib
import json
from pathlib import Path

from external_06r0_conditioned_solver import ConditionedFixtureSpec
import run_external_06r1 as r1

ALLOWED_FIXTURE_SEEDS = tuple(range(65101, 65113))
FROZEN_BUDGETS = (32, 64, 128, 256, 512, 1024)
TOP_REGRET_TOL = 1e-9
DISCRIMINATION_TOL = 1e-12
ORACLE_SEMANTICS = "P1_INFOSET_GROUPED_BEST_RESPONSE_V2"


def _stable_hit_budget(rows: list[dict]) -> int | None:
    ordered = sorted(rows, key=lambda x: int(x["terminal_budget"]))
    for i, row in enumerate(ordered):
        tail = ordered[i:]
        if all(float(x["exact_local_top_action_regret"]) <= TOP_REGRET_TOL for x in tail):
            return int(row["terminal_budget"])
    return None


def run(fixture_seed: int) -> dict:
    seed = int(fixture_seed)
    if seed not in ALLOWED_FIXTURE_SEEDS:
        raise ValueError(f"fixture seed {seed} is outside frozen 06R1F suite")

    spec = ConditionedFixtureSpec(f"R4F_{seed}", seed, 4, 0)
    original_spec = r1._spec
    original_budgets = r1.BUDGETS
    try:
        r1._spec = lambda: spec
        r1.BUDGETS = FROZEN_BUDGETS
        payload = r1.run()
    finally:
        r1._spec = original_spec
        r1.BUDGETS = original_budgets

    values = payload["oracle"]["root_action_values"]
    best_value = max(float(v) for v in values.values())
    worst_value = min(float(v) for v in values.values())
    spread = best_value - worst_value
    optimal_keys = sorted(
        key for key, value in values.items()
        if best_value - float(value) <= TOP_REGRET_TOL
    )

    for cell in payload["cells"]:
        tie_safe = float(cell["exact_local_top_action_regret"]) <= TOP_REGRET_TOL
        cell["tie_aware_oracle_optimal_top_action"] = tie_safe
        cell["tie_aware_oracle_best_action_agreement"] = tie_safe

    stable_hits: list[dict] = []
    learner_seeds = tuple(int(x) for x in payload["frozen"]["learner_seeds"])
    for learner_seed in learner_seeds:
        for method in ("ISUCT", "MCCFR"):
            rows = [
                c for c in payload["cells"]
                if c["method"] == method and int(c["seed"]) == learner_seed
            ]
            stable_hits.append({
                "method": method,
                "learner_seed": learner_seed,
                "stable_hit_budget": _stable_hit_budget(rows),
                "budget_1024_oracle_optimal": next(
                    bool(c["tie_aware_oracle_optimal_top_action"])
                    for c in rows if int(c["terminal_budget"]) == 1024
                ),
            })

    if "recommendation" in payload:
        payload["r1_mixed_policy_recommendation"] = payload.pop("recommendation")
    if "final_budget_winners" in payload:
        payload["r1_mixed_policy_final_budget_winners"] = payload.pop("final_budget_winners")

    payload["schema"] = "openofc-external-06r1f-v2"
    payload["experiment_id"] = "EXT-06R1F-R4-TOP-ACTION-SAMPLE-EFFICIENCY"
    payload["authority"] = "BELIEF_CORRECT_R4_TOP_ACTION_SAMPLE_EFFICIENCY_DIAGNOSTIC"
    payload["oracle_semantics"] = ORACLE_SEMANTICS
    payload["r1f_fixture"] = {
        "name": spec.name,
        "seed": seed,
        "round": 4,
        "actor": 0,
        "oracle_action_value_spread": spread,
        "strategically_discriminative": spread > DISCRIMINATION_TOL,
        "oracle_best_value": best_value,
        "oracle_optimal_action_keys": optimal_keys,
        "oracle_optimal_action_count": len(optimal_keys),
    }
    payload["metric_semantics"] = {
        "primary_operational_metric": "exact_local_top_action_regret",
        "oracle_optimal_tolerance": TOP_REGRET_TOL,
        "stable_hit_definition": (
            "smallest tested terminal budget with top-action regret <= 1e-9 "
            "and <= 1e-9 at every larger tested budget"
        ),
        "secondary_diagnostic_metric": "exact_local_policy_regret",
        "secondary_metric_has_promotion_authority": False,
        "reason": (
            "R4 P0 action is public before P1 responds; greedy selected-action quality "
            "is evaluated separately from residual probability in learner-specific root distributions"
        ),
    }
    payload["stable_hits"] = stable_hits
    payload["global_promotion_contract"] = {
        "fixture_seeds": list(ALLOWED_FIXTURE_SEEDS),
        "terminal_budgets": list(FROZEN_BUDGETS),
        "minimum_discriminative_fixtures": 6,
        "discriminative_if_oracle_spread_gt": DISCRIMINATION_TOL,
        "minimum_strict_stable_hit_wins": 4,
        "strict_win_ratio_required_vs_competitor": 2.0,
        "require_nonreversal_within_each_learner_seed": True,
        "require_no_lower_1024_oracle_optimal_hit_rate": True,
        "mixed_policy_regret_can_break_tie": False,
        "failure_or_tie_result": "NO_PROMOTION",
    }
    payload["verdict"] = "PASS_06R1F_FIXTURE_NO_INDIVIDUAL_PROMOTION_AUTHORITY"
    payload["real_routes_certified"] = 0
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture-seed", required=True, type=int)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    payload = run(args.fixture_seed)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "fixture": payload["r1f_fixture"],
        "oracle_semantics": payload["oracle_semantics"],
        "stable_hits": payload["stable_hits"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
