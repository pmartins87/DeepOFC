from __future__ import annotations

"""06S1 lossless suit-canonical tabular-reuse A/B."""

import argparse
from collections import Counter, defaultdict
import gc
import hashlib
import json
import math
from pathlib import Path
import tempfile
from time import perf_counter

from external_06s1_suit_canonical_solver import (
    SUIT_CANONICALIZATION_ID,
    SUIT_CANONICAL_CHECKPOINT_SCHEMA,
    SuitCanonicalOutcomeSamplingMCCFR,
    canonical_solver_finite,
)
from strategic_cfr import OutcomeSamplingMCCFR

EXPERIMENT_ID = "EXT-06S1-SUIT-CANONICAL-TABULAR-REUSE-AB"
AUTHORITY = "EXACT_SUIT_CANONICAL_TABULAR_REUSE_DIAGNOSTIC_ONLY"
SEEDS = (20260830, 20260831)
BUDGETS = (256, 1024, 4096)
OVERALL_REUSE_THRESHOLD = 0.005
LATER_REUSE_THRESHOLD = 0.001
RAW_06B_REFERENCE = {
    20260830: {
        "stored_infosets": 81913,
        "updated_infosets": 40955,
        "repeat_update_mass": 5,
        "repeat_update_fraction": 0.0001220703125,
        "later_repeat_update_fraction": 0.0,
    },
    20260831: {
        "stored_infosets": 81910,
        "updated_infosets": 40958,
        "repeat_update_mass": 2,
        "repeat_update_fraction": 0.000048828125,
        "later_repeat_update_fraction": 0.0,
    },
}


def _canonical_bytes(solver) -> bytes:
    return json.dumps(
        solver.checkpoint_payload(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _visit_metrics(rows: list[tuple[int, int]]) -> dict:
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


def _snapshot(solver, runtime_seconds: float) -> dict:
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
        layer: {"stored_infosets": stored_by_layer[layer], **_visit_metrics(rows)}
        for layer, rows in sorted(by_layer.items())
    }
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


def _run_cell(arm: str, seed: int) -> dict:
    if arm == "RAW_06A_KEY":
        solver = OutcomeSamplingMCCFR(seed=seed, epsilon=0.6, cfr_plus=True)
    elif arm == "SUIT_ORBIT_24_EXACT":
        solver = SuitCanonicalOutcomeSamplingMCCFR(seed=seed, epsilon=0.6, cfr_plus=True)
    else:
        raise ValueError(arm)

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
    reuse_starved = (
        final["overall"]["repeat_update_fraction"] < OVERALL_REUSE_THRESHOLD
        and final["rounds_1_to_4"]["repeat_update_fraction"] < LATER_REUSE_THRESHOLD
    )
    finite = (
        canonical_solver_finite(solver)
        if isinstance(solver, SuitCanonicalOutcomeSamplingMCCFR)
        else all(
            math.isfinite(v)
            for node in solver.nodes.values()
            for v in (*node.cumulative_regrets, *node.cumulative_policy)
        )
    )
    result = {
        "arm": arm,
        "seed": seed,
        "snapshots": snapshots,
        "final_reuse_starved": reuse_starved,
        "finite": finite,
        "final_payload_sha256": hashlib.sha256(_canonical_bytes(solver)).hexdigest(),
    }
    del solver
    gc.collect()
    return result


def _mechanical_probe() -> dict:
    same_a = SuitCanonicalOutcomeSamplingMCCFR(seed=9511, epsilon=0.6, cfr_plus=True)
    same_b = SuitCanonicalOutcomeSamplingMCCFR(seed=9511, epsilon=0.6, cfr_plus=True)
    same_a.run(6)
    same_b.run(6)
    same_seed_exact = _canonical_bytes(same_a) == _canonical_bytes(same_b)

    staged = SuitCanonicalOutcomeSamplingMCCFR(seed=9512, epsilon=0.6, cfr_plus=True)
    staged.run(3)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "suit-canonical.json.gz"
        staged.save_checkpoint(path)
        restored = SuitCanonicalOutcomeSamplingMCCFR.load_checkpoint(path)
        rng_restored_exact = restored.rng.getstate() == staged.rng.getstate()
        schema_exact = (
            restored.checkpoint_payload()["schema"] == SUIT_CANONICAL_CHECKPOINT_SCHEMA
            and restored.checkpoint_payload()["canonicalization"] == SUIT_CANONICALIZATION_ID
        )
        restored.run(4)

    uninterrupted = SuitCanonicalOutcomeSamplingMCCFR(seed=9512, epsilon=0.6, cfr_plus=True)
    uninterrupted.run(7)
    resume_exact = _canonical_bytes(restored) == _canonical_bytes(uninterrupted)

    return {
        "same_seed_exact": same_seed_exact,
        "rng_restored_exact": rng_restored_exact,
        "checkpoint_schema_and_mode_exact": schema_exact,
        "checkpoint_resume_exact": resume_exact,
        "finite_same_seed_solver": canonical_solver_finite(same_a),
        "finite_resumed_solver": canonical_solver_finite(restored),
    }


def _raw_reference_match(cell: dict) -> bool:
    ref = RAW_06B_REFERENCE[cell["seed"]]
    final = cell["snapshots"][-1]
    return (
        final["stored_infosets"] == ref["stored_infosets"]
        and final["overall"]["updated_infosets"] == ref["updated_infosets"]
        and final["overall"]["repeat_update_mass"] == ref["repeat_update_mass"]
        and final["overall"]["repeat_update_fraction"] == ref["repeat_update_fraction"]
        and final["rounds_1_to_4"]["repeat_update_fraction"] == ref["later_repeat_update_fraction"]
    )


def run() -> dict:
    started = perf_counter()
    mechanical = _mechanical_probe()
    cells = []
    for arm in ("RAW_06A_KEY", "SUIT_ORBIT_24_EXACT"):
        for seed in SEEDS:
            cells.append(_run_cell(arm, seed))

    raw_cells = {cell["seed"]: cell for cell in cells if cell["arm"] == "RAW_06A_KEY"}
    canonical_cells = {cell["seed"]: cell for cell in cells if cell["arm"] == "SUIT_ORBIT_24_EXACT"}
    raw_reference_reproduced = all(_raw_reference_match(cell) for cell in raw_cells.values())
    accounting_exact = all(
        snap["update_visit_accounting_exact"]
        for cell in cells
        for snap in cell["snapshots"]
    )
    finite_all = all(cell["finite"] for cell in cells)
    mechanical_pass = all(mechanical.values())

    comparisons = []
    for seed in SEEDS:
        raw = raw_cells[seed]["snapshots"][-1]
        canonical = canonical_cells[seed]["snapshots"][-1]
        raw_overall = raw["overall"]["repeat_update_fraction"]
        can_overall = canonical["overall"]["repeat_update_fraction"]
        raw_later = raw["rounds_1_to_4"]["repeat_update_fraction"]
        can_later = canonical["rounds_1_to_4"]["repeat_update_fraction"]
        comparisons.append({
            "seed": seed,
            "raw_stored_infosets": raw["stored_infosets"],
            "canonical_stored_infosets": canonical["stored_infosets"],
            "canonical_to_raw_stored_ratio": canonical["stored_infosets"] / raw["stored_infosets"],
            "raw_updated_infosets": raw["overall"]["updated_infosets"],
            "canonical_updated_infosets": canonical["overall"]["updated_infosets"],
            "canonical_to_raw_updated_ratio": canonical["overall"]["updated_infosets"] / raw["overall"]["updated_infosets"],
            "raw_overall_repeat_fraction": raw_overall,
            "canonical_overall_repeat_fraction": can_overall,
            "overall_repeat_fraction_delta": can_overall - raw_overall,
            "overall_repeat_fraction_ratio": can_overall / raw_overall if raw_overall > 0.0 else None,
            "raw_later_repeat_fraction": raw_later,
            "canonical_later_repeat_fraction": can_later,
            "later_repeat_fraction_delta": can_later - raw_later,
            "later_repeat_fraction_ratio": can_later / raw_later if raw_later > 0.0 else None,
            "canonical_reuse_starved": canonical_cells[seed]["final_reuse_starved"],
        })

    canonical_starved = [canonical_cells[seed]["final_reuse_starved"] for seed in SEEDS]
    gate_mechanics = mechanical_pass and accounting_exact and finite_all and raw_reference_reproduced
    if not gate_mechanics:
        verdict = "FAIL_06S1_MECHANICAL_OR_BASELINE_REPRODUCTION"
        next_gate = "STOP_AND_REPAIR_06S1"
    elif canonical_starved == [False, False]:
        verdict = "SUIT_CANONICALIZATION_BREAKS_REUSE_STARVATION"
        next_gate = "06S2_CANONICAL_ALGORITHM_AND_POLICY_READOUT_AB"
    elif canonical_starved == [True, True]:
        verdict = "SUIT_CANONICALIZATION_EXACT_BUT_INSUFFICIENT_FOR_DIRECT_TABULAR_SCALING"
        next_gate = "06R_CONDITIONED_RESOLVING_AND_GENERALIZATION_ARCHITECTURE"
    else:
        verdict = "SUIT_CANONICALIZATION_REUSE_INCONCLUSIVE"
        next_gate = "06S1B_CANONICAL_ONLY_16384_RESOLUTION_RUN"

    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "frozen": {
            "seeds": list(SEEDS),
            "budgets": list(BUDGETS),
            "epsilon": 0.6,
            "cfr_plus": True,
            "arms": ["RAW_06A_KEY", "SUIT_ORBIT_24_EXACT"],
            "canonicalization": SUIT_CANONICALIZATION_ID,
            "overall_reuse_threshold": OVERALL_REUSE_THRESHOLD,
            "later_reuse_threshold": LATER_REUSE_THRESHOLD,
        },
        "mechanical_probe": mechanical,
        "cells": cells,
        "comparisons_at_4096": comparisons,
        "quality": {
            "mechanical_probe_pass": mechanical_pass,
            "all_update_visit_accounting_exact": accounting_exact,
            "all_solver_values_finite": finite_all,
            "raw_06b_reference_reproduced_both_seeds": raw_reference_reproduced,
            "no_strength_winner_selected": True,
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
    if not gate_mechanics:
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
        "quality": payload["quality"],
        "comparisons_at_4096": payload["comparisons_at_4096"],
        "next_gate_recommendation": payload["next_gate_recommendation"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
