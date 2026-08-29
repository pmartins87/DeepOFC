from __future__ import annotations

"""Run 05G-Q0D MCCFR-only native coverage scaling diagnostic."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from external_05g_broad_support import AUTHORITY, broad_worlds, public_pre_r3_state, support_sha256, validate_broad_physical_support
from external_hidden_discard_overlap_strategic import OverlapExternalSamplingMCCFR, build_reachable_support
from run_external_05g_q0b import _coverage, _support_maps, _validate_profile
from run_external_05g_q0c import _layer_coverage

EXPERIMENT_ID = "EXT-05G-Q0D-MCCFR-NATIVE-COVERAGE-SCALING"
SEEDS = (20260829, 20260830)
BUDGETS = (1024, 2048)
Q1_NONROOT_TARGET = 0.80
Q1_AMBIGUOUS_TARGET = 0.95


def _trial(*, base_state, worlds, support_rows, support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys, iterations, seed) -> dict:
    world_ids = tuple(world.world_id for world in worlds)
    all_keys = set(support_by_key)

    t0 = perf_counter()
    solver = OverlapExternalSamplingMCCFR(base_state, worlds, seed=seed)
    solver.run(iterations)
    runtime = perf_counter() - t0
    profile = solver.current_profile()
    snapshot = solver.snapshot()

    validation = _validate_profile(profile, support_by_key, world_ids)
    coverage = _coverage(profile, all_keys, nonroot_keys, ambiguous_nonroot_keys)
    roots_present = all(key in profile for key in root_keys)
    p1_r3_rows = [row for row in support_rows if (row.round_index, row.actor) == (3, 1)]
    p1_r3_complete = all(row.information_state_key in profile for row in p1_r3_rows)

    firewalls = all((
        validation["illegal_key_count"] == 0,
        validation["action_set_mismatch_count"] == 0,
        validation["invalid_distribution_count"] == 0,
        validation["hidden_world_token_leakage_count"] == 0,
        roots_present,
        p1_r3_complete,
        coverage["nonroot_hit"] > 0,
    ))

    return {
        "seed": seed,
        "iterations": iterations,
        "technical_firewalls_pass": firewalls,
        "runtime_seconds": runtime,
        "terminal_evaluations": snapshot.terminal_evaluations,
        "reported_information_states": snapshot.information_states,
        "coverage": coverage,
        "layer_coverage": _layer_coverage(profile, support_rows),
        "validation": validation,
        "all_roots_present": roots_present,
        "p1_r3_complete": p1_r3_complete,
        "q1_engineering_target_met": (
            coverage["nonroot_ratio"] >= Q1_NONROOT_TARGET
            and coverage["ambiguous_nonroot_ratio"] >= Q1_AMBIGUOUS_TARGET
        ),
        "uncovered_total": len(all_keys - set(profile)),
        "uncovered_nonroot": len(nonroot_keys - set(profile)),
        "uncovered_ambiguous_nonroot": len(ambiguous_nonroot_keys - set(profile)),
    }


def _monotonic(trials: list[dict], metric: str) -> bool:
    for seed in SEEDS:
        rows = sorted((row for row in trials if row["seed"] == seed), key=lambda row: row["iterations"])
        if len(rows) != 2:
            return False
        if rows[1]["coverage"][metric] < rows[0]["coverage"][metric]:
            return False
    return True


def _selected_budget(trials: list[dict]) -> dict:
    # Q0C already proved the 512 snapshot is below both engineering thresholds
    # for both seeds, so the first eligible candidate here is 1024.
    for budget in BUDGETS:
        rows = [row for row in trials if row["iterations"] == budget]
        if len(rows) == len(SEEDS) and all(row["q1_engineering_target_met"] for row in rows):
            return {
                "budget": budget,
                "reason": "smallest_tested_budget_meeting_80pct_nonroot_and_95pct_ambiguous_on_both_seeds",
                "completion_still_required": any(row["uncovered_total"] > 0 for row in rows),
            }
    return {
        "budget": max(BUDGETS),
        "reason": "no_tested_budget_met_both_engineering_targets_use_highest_tested_fail_explicitly_to_completion",
        "completion_still_required": True,
    }


def run() -> dict:
    worlds = broad_worlds()
    base_state = public_pre_r3_state()
    validate_broad_physical_support(base_state, worlds)
    support_rows = build_reachable_support(base_state, worlds)
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)
    if len(root_keys) != 3:
        raise RuntimeError("05G-Q0D requires exactly three P0-R3 root infosets")

    trials = []
    for budget in BUDGETS:
        for seed in SEEDS:
            trials.append(_trial(
                base_state=base_state,
                worlds=worlds,
                support_rows=support_rows,
                support_by_key=support_by_key,
                nonroot_keys=nonroot_keys,
                ambiguous_nonroot_keys=ambiguous_nonroot_keys,
                root_keys=root_keys,
                iterations=budget,
                seed=seed,
            ))

    selection = _selected_budget(trials)
    quality = {
        "all_four_runs_executed": len(trials) == 4,
        "all_technical_firewalls_pass": all(row["technical_firewalls_pass"] for row in trials),
        "nonroot_coverage_monotonic": _monotonic(trials, "nonroot_hit"),
        "ambiguous_coverage_monotonic": _monotonic(trials, "ambiguous_nonroot_hit"),
        "no_policy_completion_used": True,
        "no_exact_profile_evaluation_used": True,
        "no_exact_best_response_used": True,
        "no_strength_winner_claim": True,
        "ci_runtime_guarded_by_workflow_timeout": True,
    }
    passed = all(quality.values())

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05G_BROAD_HIDDEN_INFORMATION_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q0D_MCCFR_COVERAGE_SCALING_CONTRACT.md",
        "tools/openofc_solver/external_05g_broad_support.py",
        "tools/openofc_solver/external_hidden_discard_overlap_strategic.py",
        "tools/openofc_solver/run_external_05g_q0b.py",
        "tools/openofc_solver/run_external_05g_q0c.py",
        "tools/openofc_solver/run_external_05g_q0d.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "mccfr-native-coverage-scaling-diagnostic",
        "config": {
            "seeds": list(SEEDS),
            "budgets": list(BUDGETS),
            "q1_nonroot_target": Q1_NONROOT_TARGET,
            "q1_ambiguous_target": Q1_AMBIGUOUS_TARGET,
            "q0c_512_known_below_targets": True,
            "support_worlds": len(worlds),
            "support_sha256": support_sha256(worlds),
        },
        "exhaustive_support": {
            "reachable_information_states": len(support_rows),
            "nonroot_information_states": len(nonroot_keys),
            "ambiguous_nonroot_information_states": len(ambiguous_nonroot_keys),
            "root_information_states": len(root_keys),
        },
        "trials": trials,
        "q1_native_mccfr_snapshot_selection": selection,
        "quality": quality,
        "verdict": "PASS_MCCFR_SCALING_DIAGNOSTIC" if passed else "BLOCK_TECHNICAL",
        "promotion_recommendation": "FREEZE_SELECTED_NATIVE_MCCFR_BUDGET_FOR_05G_Q1_ENGINEERING" if passed else "FIX_Q0D_TECHNICAL_DEFECT_WITHOUT_MOVING_GATES",
        "limitations": [
            "coverage is not strategic quality",
            "the Q1 budget threshold is an engineering completion-burden criterion only",
            "no missing policy is completed or evaluated",
            "finite reduced 36-world game only",
            "no REAL route is certified",
        ],
        "files": [{"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()} for path in source_paths],
        "real_routes_certified": 0,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    if not passed:
        raise RuntimeError(f"05G-Q0D failed: {quality}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05g_q0d.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "coverage": [
            {
                "seed": row["seed"],
                "iterations": row["iterations"],
                "nonroot": row["coverage"]["nonroot_ratio"],
                "ambiguous_nonroot": row["coverage"]["ambiguous_nonroot_ratio"],
                "uncovered_nonroot": row["uncovered_nonroot"],
            }
            for row in payload["trials"]
        ],
        "q1_selection": payload["q1_native_mccfr_snapshot_selection"],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
