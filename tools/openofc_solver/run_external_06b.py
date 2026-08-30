from __future__ import annotations

"""Frozen 06B tabular recurrence / learnability diagnostic."""

import argparse
from collections import Counter, defaultdict
import gc
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

from strategic_cfr import OutcomeSamplingMCCFR

EXPERIMENT_ID = "EXT-06B-FULL-GAME-TABULAR-LEARNABILITY"
AUTHORITY = "FULL_GAME_TABULAR_LEARNABILITY_DIAGNOSTIC_ONLY"
SEEDS = (20260830, 20260831)
BUDGETS = (256, 1024, 4096)
MODES = (
    ("VANILLA_OS_MCCFR", False),
    ("CLIPPED_OS_MCCFR", True),
)
OVERALL_REUSE_THRESHOLD = 0.005
LATER_REUSE_THRESHOLD = 0.001


def _visit_metrics(rows: list[tuple[int, int]]) -> dict:
    """rows are (visits, action_count) for updated information sets."""
    infosets = len(rows)
    total_visits = sum(visits for visits, _actions in rows)
    once = sum(visits == 1 for visits, _actions in rows)
    revisited = sum(visits >= 2 for visits, _actions in rows)
    repeat_mass = sum(max(visits - 1, 0) for visits, _actions in rows)
    action_hist = Counter(actions for _visits, actions in rows)
    return {
        "updated_infosets": infosets,
        "total_update_visits": total_visits,
        "visited_exactly_once": once,
        "revisited_infosets": revisited,
        "repeat_update_mass": repeat_mass,
        "repeat_update_fraction": (repeat_mass / total_visits) if total_visits else 0.0,
        "max_visits": max((visits for visits, _actions in rows), default=0),
        "mean_actions_per_updated_infoset": (
            sum(actions for _visits, actions in rows) / infosets if infosets else 0.0
        ),
        "max_actions": max((actions for _visits, actions in rows), default=0),
        "action_count_histogram": {
            str(actions): count for actions, count in sorted(action_hist.items())
        },
    }


def _snapshot(solver: OutcomeSamplingMCCFR, runtime_seconds: float) -> dict:
    updated_rows: list[tuple[int, int]] = []
    later_rows: list[tuple[int, int]] = []
    by_layer: dict[str, list[tuple[int, int]]] = defaultdict(list)
    stored_by_layer: Counter[str] = Counter()
    zero_visit_nodes = 0

    for key, node in solver.nodes.items():
        payload = json.loads(key)
        round_index = int(payload["round"])
        player = int(payload["player"])
        layer = f"R{round_index}_P{player}"
        stored_by_layer[layer] += 1
        if node.visits <= 0:
            zero_visit_nodes += 1
            continue
        row = (int(node.visits), len(node.action_keys))
        updated_rows.append(row)
        by_layer[layer].append(row)
        if round_index >= 1:
            later_rows.append(row)

    overall = _visit_metrics(updated_rows)
    later = _visit_metrics(later_rows)
    by_layer_payload = {
        layer: {
            "stored_infosets": stored_by_layer[layer],
            **_visit_metrics(rows),
        }
        for layer, rows in sorted(by_layer.items())
    }
    # Include layers that were stored but never updated, if any.
    for layer in sorted(stored_by_layer):
        if layer not in by_layer_payload:
            by_layer_payload[layer] = {
                "stored_infosets": stored_by_layer[layer],
                **_visit_metrics([]),
            }

    expected_update_visits = solver.iterations * 10
    return {
        "iterations": solver.iterations,
        "episodes": solver.episodes,
        "stored_infosets": len(solver.nodes),
        "zero_visit_stored_infosets": zero_visit_nodes,
        "stored_nodes_per_iteration": len(solver.nodes) / solver.iterations,
        "runtime_seconds": runtime_seconds,
        "iterations_per_second": solver.iterations / runtime_seconds if runtime_seconds > 0.0 else None,
        "expected_update_visits": expected_update_visits,
        "update_visit_accounting_exact": overall["total_update_visits"] == expected_update_visits,
        "overall": overall,
        "rounds_1_to_4": later,
        "by_layer": by_layer_payload,
    }


def _run_cell(seed: int, mode_name: str, cfr_plus: bool) -> dict:
    solver = OutcomeSamplingMCCFR(seed=seed, epsilon=0.6, cfr_plus=cfr_plus)
    snapshots = []
    start = perf_counter()
    previous = 0
    for budget in BUDGETS:
        solver.run(budget - previous)
        elapsed = perf_counter() - start
        snapshot = _snapshot(solver, elapsed)
        snapshot["budget"] = budget
        snapshots.append(snapshot)
        previous = budget

    final = snapshots[-1]
    overall_reuse = final["overall"]["repeat_update_fraction"]
    later_reuse = final["rounds_1_to_4"]["repeat_update_fraction"]
    reuse_starved = (
        overall_reuse < OVERALL_REUSE_THRESHOLD
        and later_reuse < LATER_REUSE_THRESHOLD
    )
    result = {
        "seed": seed,
        "mode": mode_name,
        "cfr_plus": cfr_plus,
        "epsilon": solver.epsilon,
        "snapshots": snapshots,
        "final_reuse_starved": reuse_starved,
        "final_overall_repeat_update_fraction": overall_reuse,
        "final_later_repeat_update_fraction": later_reuse,
    }
    del solver
    gc.collect()
    return result


def run() -> dict:
    started = perf_counter()
    cells = []
    for mode_name, cfr_plus in MODES:
        for seed in SEEDS:
            cells.append(_run_cell(seed, mode_name, cfr_plus))

    accounting_exact = all(
        snapshot["update_visit_accounting_exact"]
        for cell in cells
        for snapshot in cell["snapshots"]
    )
    all_starved = all(cell["final_reuse_starved"] for cell in cells)
    if not accounting_exact:
        verdict = "FAIL_06B_UPDATE_VISIT_ACCOUNTING"
        next_gate = "STOP_AND_REPAIR_06B_DIAGNOSTIC"
    elif all_starved:
        verdict = "BLOCK_DIRECT_TABULAR_SCALING_REUSE_STARVED"
        next_gate = "06S_EXACT_SYMMETRY_AND_GENERALIZATION_DESIGN"
    else:
        verdict = "CONTINUE_06B2_ALGORITHM_AND_POLICY_READOUT_AB"
        next_gate = "06B2_FREEZE_ALGORITHM_AND_POLICY_READOUT_AB"

    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "frozen": {
            "seeds": list(SEEDS),
            "budgets": list(BUDGETS),
            "epsilon": 0.6,
            "modes": [name for name, _cfr_plus in MODES],
            "overall_reuse_threshold": OVERALL_REUSE_THRESHOLD,
            "later_reuse_threshold": LATER_REUSE_THRESHOLD,
            "raw_nondealer_opening_five_card_support": math.comb(54, 5),
        },
        "cells": cells,
        "quality": {
            "all_update_visit_accounting_exact": accounting_exact,
            "all_four_cells_reuse_starved": all_starved,
            "no_algorithm_strength_winner_selected": True,
            "no_current_vs_average_winner_selected": True,
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
    if not accounting_exact:
        raise RuntimeError(json.dumps({
            "experiment_id": EXPERIMENT_ID,
            "verdict": verdict,
            "quality": payload["quality"],
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
        "quality": payload["quality"],
        "next_gate_recommendation": payload["next_gate_recommendation"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
