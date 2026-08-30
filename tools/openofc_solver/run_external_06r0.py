from __future__ import annotations

"""06R0 conditioned-suffix reuse-geometry runner."""

import argparse
from collections import Counter, defaultdict
import gc
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

from external_06r0_conditioned_solver import (
    AUTHORITY,
    FROZEN_FIXTURES,
    ConditionedSuitCanonicalOutcomeSamplingMCCFR,
    build_conditioned_fixture,
    checkpoint_semantic_bytes,
    root_probe,
)
from external_06s1_suit_canonical_solver import canonical_solver_finite

EXPERIMENT_ID = "EXT-06R0-CONDITIONED-SUFFIX-REUSE-GEOMETRY"
LEARNER_SEEDS = (20260830, 20260831)
BUDGETS = (512, 2048, 8192)
ARMS = ("FIXED_SUFFIX_CONTROL", "FUTURE_RESAMPLED_CONDITIONED")
STRICT_REPEAT_THRESHOLD = 0.01
STRICT_MAX_VISITS_THRESHOLD = 3
EARLY_FIXTURES = {"R1_P0_A", "R2_P0_A", "R2_P1_A"}
MID_LATE_FIXTURES = {"R3_P0_A", "R3_P1_A", "R4_P0_A"}


def _visit_metrics(rows: list[tuple[int, int]]) -> dict:
    infosets = len(rows)
    total_visits = sum(visits for visits, _actions in rows)
    repeat_mass = sum(max(visits - 1, 0) for visits, _actions in rows)
    action_hist = Counter(actions for _visits, actions in rows)
    return {
        "updated_infosets": infosets,
        "total_update_visits": total_visits,
        "visited_exactly_once": sum(visits == 1 for visits, _actions in rows),
        "revisited_infosets": sum(visits >= 2 for visits, _actions in rows),
        "repeat_update_mass": repeat_mass,
        "repeat_update_fraction": repeat_mass / total_visits if total_visits else 0.0,
        "max_visits": max((visits for visits, _actions in rows), default=0),
        "mean_actions_per_updated_infoset": (
            sum(actions for _visits, actions in rows) / infosets if infosets else 0.0
        ),
        "max_actions": max((actions for _visits, actions in rows), default=0),
        "action_count_histogram": {
            str(actions): count for actions, count in sorted(action_hist.items())
        },
    }


def _snapshot(
    solver: ConditionedSuitCanonicalOutcomeSamplingMCCFR,
    runtime_seconds: float,
) -> dict:
    updated_rows: list[tuple[int, int]] = []
    strict_rows: list[tuple[int, int]] = []
    by_depth: dict[int, list[tuple[int, int]]] = defaultdict(list)
    stored_by_depth: Counter[int] = Counter()
    zero_visit_nodes = 0

    for key, node in solver.nodes.items():
        payload = json.loads(key)
        depth = len(payload["public_history"]) - solver.root_history_length
        if depth < 0:
            raise AssertionError("conditioned solver materialized a node before its root")
        stored_by_depth[depth] += 1
        if node.visits <= 0:
            zero_visit_nodes += 1
            continue
        row = (int(node.visits), len(node.action_keys))
        updated_rows.append(row)
        by_depth[depth].append(row)
        if depth >= 1:
            strict_rows.append(row)

    overall = _visit_metrics(updated_rows)
    strict = _visit_metrics(strict_rows)
    depth_payload = {}
    for depth in sorted(stored_by_depth):
        depth_payload[str(depth)] = {
            "stored_infosets": stored_by_depth[depth],
            **_visit_metrics(by_depth.get(depth, [])),
        }

    expected_total = solver.iterations * solver.expected_updates_per_iteration
    expected_strict = solver.iterations * max(solver.expected_updates_per_iteration - 1, 0)
    root_metrics = _visit_metrics(by_depth.get(0, []))
    return {
        "iterations": solver.iterations,
        "episodes": solver.episodes,
        "stored_infosets": len(solver.nodes),
        "zero_visit_stored_infosets": zero_visit_nodes,
        "stored_nodes_per_iteration": len(solver.nodes) / solver.iterations,
        "runtime_seconds": runtime_seconds,
        "iterations_per_second": solver.iterations / runtime_seconds if runtime_seconds > 0.0 else None,
        "expected_updates_per_iteration": solver.expected_updates_per_iteration,
        "expected_total_update_visits": expected_total,
        "expected_strict_downstream_update_visits": expected_strict,
        "overall": overall,
        "conditioned_root": root_metrics,
        "strict_downstream": strict,
        "by_public_history_depth": depth_payload,
        "overall_update_visit_accounting_exact": overall["total_update_visits"] == expected_total,
        "strict_downstream_update_visit_accounting_exact": strict["total_update_visits"] == expected_strict,
        "conditioned_root_is_single_updated_infoset": root_metrics["updated_infosets"] == 1,
        "conditioned_root_visits_equal_iterations": root_metrics["total_update_visits"] == solver.iterations,
    }


def _run_cell(arm: str, fixture_name: str, root, learner_seed: int) -> dict:
    if arm not in ARMS:
        raise ValueError(arm)
    solver = ConditionedSuitCanonicalOutcomeSamplingMCCFR(
        base_root=root,
        resample_future=arm == "FUTURE_RESAMPLED_CONDITIONED",
        epsilon=0.6,
        seed=learner_seed,
        cfr_plus=True,
    )
    snapshots = []
    started = perf_counter()
    previous = 0
    for budget in BUDGETS:
        solver.run(budget - previous)
        elapsed = perf_counter() - started
        snap = _snapshot(solver, elapsed)
        snap["budget"] = budget
        snapshots.append(snap)
        previous = budget

    final = snapshots[-1]
    strict = final["strict_downstream"]
    useful = (
        strict["repeat_update_fraction"] >= STRICT_REPEAT_THRESHOLD
        and strict["max_visits"] >= STRICT_MAX_VISITS_THRESHOLD
    )
    finite = canonical_solver_finite(solver)
    result = {
        "arm": arm,
        "fixture": fixture_name,
        "learner_seed": learner_seed,
        "root_round": root.round_index,
        "root_actor": root.actor,
        "root_public_history_length": len(root.public_history),
        "snapshots": snapshots,
        "useful_local_reuse_at_8192": useful,
        "finite": finite,
        "final_payload_sha256": hashlib.sha256(checkpoint_semantic_bytes(solver)).hexdigest(),
    }
    del solver
    gc.collect()
    return result


def _mechanical_probe(fixtures: dict[str, object]) -> dict:
    probes = {}
    for index, spec in enumerate(FROZEN_FIXTURES):
        root = fixtures[spec.name]
        probes[spec.name] = root_probe(
            root,
            sample_seed=906000 + index,
            samples=16,
        )

    deterministic_root = fixtures["R3_P0_A"]
    solver_a = ConditionedSuitCanonicalOutcomeSamplingMCCFR(
        base_root=deterministic_root,
        resample_future=True,
        seed=95060,
        epsilon=0.6,
        cfr_plus=True,
    )
    solver_b = ConditionedSuitCanonicalOutcomeSamplingMCCFR(
        base_root=deterministic_root,
        resample_future=True,
        seed=95060,
        epsilon=0.6,
        cfr_plus=True,
    )
    solver_a.run(8)
    solver_b.run(8)
    same_seed_exact = checkpoint_semantic_bytes(solver_a) == checkpoint_semantic_bytes(solver_b)
    accounting = _snapshot(solver_a, 1.0)
    return {
        "fixture_root_probes": probes,
        "all_root_information_firewalls_exact": all(
            row["raw_and_canonical_root_information_exact"] for row in probes.values()
        ),
        "all_fixtures_resample_multiple_future_plans": all(
            row["unique_sampled_plan_sha256"] > 1 for row in probes.values()
        ),
        "fixture_root_keys_unique": len({row["root_key_sha256"] for row in probes.values()}) == len(probes),
        "same_seed_future_resampled_solver_exact": same_seed_exact,
        "probe_update_accounting_exact": (
            accounting["overall_update_visit_accounting_exact"]
            and accounting["strict_downstream_update_visit_accounting_exact"]
            and accounting["conditioned_root_is_single_updated_infoset"]
            and accounting["conditioned_root_visits_equal_iterations"]
        ),
        "probe_solver_finite": canonical_solver_finite(solver_a) and canonical_solver_finite(solver_b),
    }


def run() -> dict:
    started = perf_counter()
    fixtures = {spec.name: build_conditioned_fixture(spec) for spec in FROZEN_FIXTURES}
    mechanical = _mechanical_probe(fixtures)

    cells = []
    for spec in FROZEN_FIXTURES:
        root = fixtures[spec.name]
        for arm in ARMS:
            for learner_seed in LEARNER_SEEDS:
                cells.append(_run_cell(arm, spec.name, root, learner_seed))

    cell_accounting_exact = all(
        snap["overall_update_visit_accounting_exact"]
        and snap["strict_downstream_update_visit_accounting_exact"]
        and snap["conditioned_root_is_single_updated_infoset"]
        and snap["conditioned_root_visits_equal_iterations"]
        for cell in cells
        for snap in cell["snapshots"]
    )
    finite_all = all(cell["finite"] for cell in cells)
    mechanical_pass = (
        mechanical["all_root_information_firewalls_exact"]
        and mechanical["all_fixtures_resample_multiple_future_plans"]
        and mechanical["fixture_root_keys_unique"]
        and mechanical["same_seed_future_resampled_solver_exact"]
        and mechanical["probe_update_accounting_exact"]
        and mechanical["probe_solver_finite"]
        and cell_accounting_exact
        and finite_all
    )

    fixture_readout = []
    passed_fixtures = set()
    for spec in FROZEN_FIXTURES:
        rows = [
            cell for cell in cells
            if cell["fixture"] == spec.name
            and cell["arm"] == "FUTURE_RESAMPLED_CONDITIONED"
        ]
        rows.sort(key=lambda row: row["learner_seed"])
        both_seeds_pass = (
            len(rows) == len(LEARNER_SEEDS)
            and all(row["useful_local_reuse_at_8192"] for row in rows)
        )
        if both_seeds_pass:
            passed_fixtures.add(spec.name)
        fixture_readout.append({
            "fixture": spec.name,
            "round": spec.round_index,
            "actor": spec.actor,
            "both_seeds_useful_local_reuse": both_seeds_pass,
            "seeds": [
                {
                    "learner_seed": row["learner_seed"],
                    "strict_downstream_repeat_update_fraction": row["snapshots"][-1]["strict_downstream"]["repeat_update_fraction"],
                    "strict_downstream_max_visits": row["snapshots"][-1]["strict_downstream"]["max_visits"],
                    "strict_downstream_revisited_infosets": row["snapshots"][-1]["strict_downstream"]["revisited_infosets"],
                    "strict_downstream_updated_infosets": row["snapshots"][-1]["strict_downstream"]["updated_infosets"],
                    "runtime_seconds": row["snapshots"][-1]["runtime_seconds"],
                    "useful": row["useful_local_reuse_at_8192"],
                }
                for row in rows
            ],
        })

    early_pass = bool(passed_fixtures & EARLY_FIXTURES)
    mid_late_pass = bool(passed_fixtures & MID_LATE_FIXTURES)
    late_count = len(passed_fixtures & MID_LATE_FIXTURES)

    if not mechanical_pass:
        verdict = "FAIL_06R0_MECHANICS_OR_INFORMATION_FIREWALL"
        next_gate = "STOP_AND_REPAIR_06R0"
    elif len(passed_fixtures) >= 4 and early_pass and mid_late_pass:
        verdict = "PASS_06R0_CONDITIONED_REUSE_GEOMETRY"
        next_gate = "06R1_PRACTICAL_LOCAL_RESOLVER_STRENGTH_COMPUTE_AB_WITH_BELIEF_UPGRADE"
    elif not early_pass and late_count >= 2:
        verdict = "PASS_06R0_LATE_ROUND_ONLY_REUSE_GEOMETRY"
        next_gate = "06R1_ROUND_ADAPTIVE_GLOBAL_PRIOR_PLUS_LATE_LOCAL_RESOLVING"
    else:
        verdict = "FAIL_06R0_CONDITIONING_ALONE_STILL_REUSE_STARVED"
        next_gate = "06G_GENERALIZATION_ABSTRACTION_OR_VALUE_PRIOR_BEFORE_MORE_LOCAL_REGRET"

    payload = {
        "schema": "openofc-external-06r0-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "frozen": {
            "fixtures": [
                {
                    "name": spec.name,
                    "seed": spec.seed,
                    "round": spec.round_index,
                    "actor": spec.actor,
                }
                for spec in FROZEN_FIXTURES
            ],
            "learner_seeds": list(LEARNER_SEEDS),
            "budgets": list(BUDGETS),
            "arms": list(ARMS),
            "epsilon": 0.6,
            "cfr_plus": True,
            "strict_repeat_threshold": STRICT_REPEAT_THRESHOLD,
            "strict_max_visits_threshold": STRICT_MAX_VISITS_THRESHOLD,
            "fixture_requires_both_learner_seeds": True,
            "future_model": "FUTURE_ONLY_UNIFORM_WITHOUT_REPLACEMENT_PAST_HIDDEN_FIXED",
        },
        "mechanical_probe": mechanical,
        "cells": cells,
        "fixture_readout": fixture_readout,
        "passed_fixture_names": sorted(passed_fixtures),
        "quality": {
            "mechanical_probe_pass": mechanical_pass,
            "all_cell_update_accounting_exact": cell_accounting_exact,
            "all_solver_values_finite": finite_all,
            "no_payoff_based_fixture_selection": True,
            "no_equilibrium_or_strength_claim": True,
            "posterior_correctness_not_claimed": True,
            "real_routes_certified_zero": True,
        },
        "verdict": verdict,
        "next_gate_recommendation": next_gate,
        "runtime_seconds": perf_counter() - started,
        "real_routes_certified": 0,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()

    if not mechanical_pass:
        raise RuntimeError(json.dumps({
            "experiment_id": EXPERIMENT_ID,
            "verdict": verdict,
            "quality": payload["quality"],
            "mechanical_probe": mechanical,
        }, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "passed_fixture_names": payload["passed_fixture_names"],
        "fixture_readout": payload["fixture_readout"],
        "quality": payload["quality"],
        "next_gate_recommendation": payload["next_gate_recommendation"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
