from __future__ import annotations

"""Frozen 06R1 belief-correct R4 strength × compute runner."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

from external_06r0_conditioned_solver import FROZEN_FIXTURES, build_conditioned_fixture
from external_06r1_belief_correct import (
    AUTHORITY,
    BeliefCorrectISUCT,
    BeliefCorrectMCCFR,
    build_belief_support,
    exact_policy_regret,
    exact_r4_p0_oracle,
    exact_top_action_regret,
    normalize_policy,
    sample_belief_root,
)
from external_06s0_suit_automorphism import canonical_information_state, canonical_legal_action_keys
from strategic_cfr import information_state_key

EXPERIMENT_ID = "EXT-06R1-BELIEF-CORRECT-R4-STRENGTH-COMPUTE"
BUDGETS = (256, 1024, 4096)
SEEDS = (20260830, 20260831)
TOL = 1e-9


def _spec():
    return next(spec for spec in FROZEN_FIXTURES if spec.name == "R4_P0_A")


def _uct_policy(solver: BeliefCorrectISUCT) -> dict[str, float]:
    node = solver.nodes.get(solver.root_key)
    if node is None or node.visits <= 0:
        raise AssertionError("ISUCT root is unvisited")
    return normalize_policy({key: stat.visits for key, stat in node.actions.items()})


def _mccfr_policy(solver: BeliefCorrectMCCFR, root_key: str) -> dict[str, float]:
    node = solver.nodes.get(root_key)
    if node is None:
        raise AssertionError("MCCFR root is absent")
    return normalize_policy(dict(zip(node.action_keys, node.average_policy())))


def _top(policy: dict[str, float]) -> str:
    best = max(policy.values())
    return sorted(key for key, value in policy.items() if abs(value - best) <= 1e-15)[0]


def _tv(a: dict[str, float], b: dict[str, float]) -> float:
    if set(a) != set(b):
        raise ValueError("TV policies have different action sets")
    return 0.5 * sum(abs(a[key] - b[key]) for key in a)


def _cell(method: str, seed: int, budget: int, seconds: float, infosets: int,
          terminal_evaluations: int, policy: dict[str, float], oracle) -> dict:
    top = _top(policy)
    return {
        "method": method,
        "seed": seed,
        "terminal_budget": budget,
        "training_seconds": seconds,
        "information_states": infosets,
        "terminal_evaluations": terminal_evaluations,
        "root_policy": policy,
        "top_action": top,
        "oracle_best_action": oracle.best_action_key,
        "oracle_best_action_agreement": top == oracle.best_action_key,
        "exact_local_policy_regret": exact_policy_regret(policy, oracle),
        "exact_local_top_action_regret": exact_top_action_regret(top, oracle),
    }


def _pareto(cells: list[dict], seed: int) -> list[dict]:
    rows = [c for c in cells if c["seed"] == seed]
    out = []
    for row in rows:
        dominated_by = []
        for other in rows:
            if other is row:
                continue
            no_slower = other["training_seconds"] <= row["training_seconds"] + 1e-12
            no_weaker = other["exact_local_policy_regret"] <= row["exact_local_policy_regret"] + TOL
            strict = (
                other["training_seconds"] < row["training_seconds"] - 1e-12
                or other["exact_local_policy_regret"] + TOL < row["exact_local_policy_regret"]
            )
            if no_slower and no_weaker and strict:
                dominated_by.append({
                    "method": other["method"],
                    "terminal_budget": other["terminal_budget"],
                })
        if not dominated_by:
            out.append({
                "method": row["method"],
                "terminal_budget": row["terminal_budget"],
                "training_seconds": row["training_seconds"],
                "exact_local_policy_regret": row["exact_local_policy_regret"],
            })
    out.sort(key=lambda r: (r["training_seconds"], r["exact_local_policy_regret"], r["method"]))
    return out


def run() -> dict:
    spec = _spec()
    root = build_conditioned_fixture(spec)
    support_started = perf_counter()
    support = build_belief_support(root, spec)
    support_seconds = perf_counter() - support_started

    # Independent mechanical posterior probe before the strategic A/B.
    probe_rng_seed = 606110
    import random
    probe_rng = random.Random(probe_rng_seed)
    sampled_plan_hashes = set()
    root_raw = information_state_key(root)
    root_canonical = canonical_information_state(root)[0]
    root_actions = canonical_legal_action_keys(root)
    for _ in range(32):
        sampled = sample_belief_root(root, spec, support, probe_rng)
        if information_state_key(sampled) != root_raw:
            raise AssertionError("posterior probe changed raw root information")
        if canonical_information_state(sampled)[0] != root_canonical:
            raise AssertionError("posterior probe changed canonical root information")
        if canonical_legal_action_keys(sampled) != root_actions:
            raise AssertionError("posterior probe changed root action set")
        sampled_plan_hashes.add(hashlib.sha256(
            "|".join(map(str, sampled.plan.dealt_cards())).encode("utf-8")
        ).hexdigest())
    if len(sampled_plan_hashes) <= 1:
        raise AssertionError("posterior probe did not materialize multiple worlds")

    oracle_started = perf_counter()
    oracle = exact_r4_p0_oracle(root, spec, support)
    oracle_seconds = perf_counter() - oracle_started
    oracle_values = oracle.value_map()
    if set(oracle_values) != set(root_actions):
        raise AssertionError("oracle action set differs from frozen root")
    if any(not math.isfinite(value) for value in oracle_values.values()):
        raise AssertionError("oracle contains non-finite values")

    cells: list[dict] = []
    for seed in SEEDS:
        uct = BeliefCorrectISUCT(
            base_root=root,
            spec=spec,
            support=support,
            exploration=2.0,
            seed=seed,
        )
        started = perf_counter()
        previous = 0
        for budget in BUDGETS:
            uct.run(budget - previous)
            elapsed = perf_counter() - started
            if not uct.visit_accounting_exact():
                raise AssertionError("ISUCT terminal accounting failed")
            policy = _uct_policy(uct)
            cells.append(_cell(
                "ISUCT", seed, budget, elapsed, len(uct.nodes),
                uct.terminal_evaluations, policy, oracle,
            ))
            previous = budget

        mccfr = BeliefCorrectMCCFR(
            base_root=root,
            spec=spec,
            support=support,
            epsilon=0.6,
            seed=seed,
            cfr_plus=True,
        )
        started = perf_counter()
        previous_iterations = 0
        for budget in BUDGETS:
            target_iterations = budget // 2
            mccfr.run(target_iterations - previous_iterations)
            elapsed = perf_counter() - started
            if mccfr.episodes != budget:
                raise AssertionError("MCCFR terminal accounting failed")
            policy = _mccfr_policy(mccfr, root_canonical)
            cells.append(_cell(
                "MCCFR", seed, budget, elapsed, len(mccfr.nodes),
                mccfr.episodes, policy, oracle,
            ))
            previous_iterations = target_iterations

    cross_seed = []
    for method in ("ISUCT", "MCCFR"):
        for budget in BUDGETS:
            rows = sorted(
                [c for c in cells if c["method"] == method and c["terminal_budget"] == budget],
                key=lambda c: c["seed"],
            )
            if len(rows) != 2:
                raise AssertionError("cross-seed cell count differs from two")
            cross_seed.append({
                "method": method,
                "terminal_budget": budget,
                "tv": _tv(rows[0]["root_policy"], rows[1]["root_policy"]),
                "same_top_action": rows[0]["top_action"] == rows[1]["top_action"],
                "seed_a_top": rows[0]["top_action"],
                "seed_b_top": rows[1]["top_action"],
            })

    final_winners = []
    for seed in SEEDS:
        u = next(c for c in cells if c["method"] == "ISUCT" and c["seed"] == seed and c["terminal_budget"] == BUDGETS[-1])
        m = next(c for c in cells if c["method"] == "MCCFR" and c["seed"] == seed and c["terminal_budget"] == BUDGETS[-1])
        ru = u["exact_local_policy_regret"]
        rm = m["exact_local_policy_regret"]
        if rm + TOL < ru:
            winner = "MCCFR"
        elif ru + TOL < rm:
            winner = "ISUCT"
        else:
            winner = "TIE"
        final_winners.append({"seed": seed, "winner": winner, "isuct_regret": ru, "mccfr_regret": rm})

    winner_names = [row["winner"] for row in final_winners]
    if "ISUCT" not in winner_names and "MCCFR" in winner_names:
        recommendation = "PROMOTE_MCCFR_TO_R2_R3_LOCAL_RESOLVER_VALIDATION"
    elif "MCCFR" not in winner_names and "ISUCT" in winner_names:
        recommendation = "PROMOTE_ISUCT_TO_R2_R3_LOCAL_SEARCH_VALIDATION"
    else:
        recommendation = "NO_CROSS_SEED_R4_WINNER_CONTINUE_DIAGNOSTICS"

    payload = {
        "schema": "openofc-external-06r1-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "frozen": {
            "fixture": spec.name,
            "fixture_seed": spec.seed,
            "terminal_budgets": list(BUDGETS),
            "learner_seeds": list(SEEDS),
            "isuct_exploration": 2.0,
            "mccfr_epsilon": 0.6,
            "mccfr_cfr_plus": True,
            "ranking_tolerance": TOL,
            "posterior": "EXACT_UNDER_FROZEN_PAYOFF_BLIND_PREFIX_POLICY",
        },
        "posterior": {
            "support_build_seconds": support_seconds,
            "hidden_history_count": support.hidden_history_count,
            "hidden_event_rounds": list(support.opponent_hidden_event_rounds),
            "fixed_known_card_count": len(support.fixed_known_cards),
            "probe_samples": 32,
            "probe_unique_world_plans": len(sampled_plan_hashes),
            "root_raw_information_sha256": hashlib.sha256(root_raw.encode("utf-8")).hexdigest(),
            "root_canonical_information_sha256": hashlib.sha256(root_canonical.encode("utf-8")).hexdigest(),
        },
        "oracle": {
            "build_seconds": oracle_seconds,
            "posterior_worlds": oracle.posterior_worlds,
            "root_action_values": dict(oracle.root_action_values),
            "best_action_key": oracle.best_action_key,
            "best_value": oracle.best_value,
            "p1_information_states_by_root_action": dict(oracle.p1_information_states_by_root_action),
        },
        "cells": cells,
        "cross_seed_stability": cross_seed,
        "final_budget_winners": final_winners,
        "pareto": [{"seed": seed, "nondominated": _pareto(cells, seed)} for seed in SEEDS],
        "recommendation": recommendation,
        "quality": {
            "posterior_support_nonempty": support.hidden_history_count > 0,
            "posterior_multiple_worlds_probe": len(sampled_plan_hashes) > 1,
            "exact_root_action_set_preserved": set(oracle_values) == set(root_actions),
            "all_terminal_budgets_exact": all(c["terminal_evaluations"] == c["terminal_budget"] for c in cells),
            "all_regrets_nonnegative": all(c["exact_local_policy_regret"] >= 0.0 and c["exact_local_top_action_regret"] >= 0.0 for c in cells),
            "real_routes_certified_zero": True,
        },
        "verdict": "PASS_06R1_BELIEF_CORRECT_R4_STRENGTH_COMPUTE",
        "real_routes_certified": 0,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    payload = run()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "posterior": payload["posterior"],
        "oracle": {
            "posterior_worlds": payload["oracle"]["posterior_worlds"],
            "best_action_key": payload["oracle"]["best_action_key"],
            "best_value": payload["oracle"]["best_value"],
        },
        "final_budget_winners": payload["final_budget_winners"],
        "recommendation": payload["recommendation"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
