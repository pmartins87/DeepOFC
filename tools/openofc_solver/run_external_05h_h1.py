from __future__ import annotations

"""05H-H1 MCCFR-native coverage calibration over frozen 144-world support.

No completion, EV, best response, NashConv or exploitability is computed here.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

from external_05h_broad_support import (
    AUTHORITY,
    private_types,
    public_pre_r3_state,
    support_sha256,
    validate_physical_support,
    worlds,
)
from external_hidden_discard_overlap_strategic import (
    OverlapExternalSamplingMCCFR,
    ReachableSupport,
    build_reachable_support,
)
from run_external_05g_q0b import _support_maps, _validate_profile
from run_external_05g_q1a import _profile_sha256

EXPERIMENT_ID = "EXT-05H-H1-MCCFR-NATIVE-COVERAGE-CALIBRATION"
SEEDS = (20260829, 20260830)
BUDGETS = (1024, 2048, 4096)
NONROOT_TARGET = 0.80
AMBIGUOUS_NONROOT_TARGET = 0.95


def _layer_name(row: ReachableSupport) -> str:
    return f"R{row.round_index}_P{row.actor}"


def _coverage(
    profile: Mapping[str, Mapping[str, float]],
    support_rows: Sequence[ReachableSupport],
    nonroot_keys: set[str],
    ambiguous_nonroot_keys: set[str],
) -> dict:
    native = set(profile)
    native_nonroot = native & nonroot_keys
    native_ambiguous = native & ambiguous_nonroot_keys

    by_layer = {}
    for layer in sorted({_layer_name(row) for row in support_rows}):
        layer_rows = [row for row in support_rows if _layer_name(row) == layer]
        layer_keys = {row.information_state_key for row in layer_rows}
        layer_native = native & layer_keys
        layer_ambiguous_keys = {
            row.information_state_key for row in layer_rows if len(row.concrete_states) > 1
        }
        by_layer[layer] = {
            "reachable_information_states": len(layer_keys),
            "native_information_states": len(layer_native),
            "native_fraction": len(layer_native) / len(layer_keys) if layer_keys else 1.0,
            "ambiguous_information_states": len(layer_ambiguous_keys),
            "native_ambiguous_information_states": len(native & layer_ambiguous_keys),
            "native_ambiguous_fraction": (
                len(native & layer_ambiguous_keys) / len(layer_ambiguous_keys)
                if layer_ambiguous_keys else 1.0
            ),
        }

    return {
        "native_information_states": len(native),
        "native_nonroot_information_states": len(native_nonroot),
        "nonroot_native_fraction": len(native_nonroot) / len(nonroot_keys),
        "native_ambiguous_nonroot_information_states": len(native_ambiguous),
        "ambiguous_nonroot_native_fraction": (
            len(native_ambiguous) / len(ambiguous_nonroot_keys)
            if ambiguous_nonroot_keys else 1.0
        ),
        "by_layer": by_layer,
    }


def _sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run() -> dict:
    base_state = public_pre_r3_state()
    support = worlds()
    validate_physical_support(base_state, support)

    t_support = perf_counter()
    support_rows = build_reachable_support(base_state, support)
    support_seconds = perf_counter() - t_support
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)

    if len(support) != 144:
        raise RuntimeError("05H support world count changed")
    if {key: len(value) for key, value in private_types().items()} != {
        "p0_r3": 4, "p1_r3": 4, "p0_r4": 3, "p1_r4": 3,
    }:
        raise RuntimeError("05H private type schedule changed")
    if len(support_rows) <= 69828 or len(ambiguous_nonroot_keys) <= 15393:
        raise RuntimeError("05H H1 refuses a support that did not mechanically broaden 05G")

    world_ids = tuple(world.world_id for world in support)
    seed_results = []
    for seed in SEEDS:
        solver = OverlapExternalSamplingMCCFR(base_state, support, seed=seed)
        snapshots = []
        previous_budget = 0
        cumulative_runtime = 0.0
        for budget in BUDGETS:
            delta = budget - previous_budget
            if delta <= 0:
                raise AssertionError("H1 budgets must be strictly increasing")
            t0 = perf_counter()
            solver.run(delta)
            interval_runtime = perf_counter() - t0
            cumulative_runtime += interval_runtime
            previous_budget = budget

            profile = solver.current_profile()
            validation = _validate_profile(profile, support_by_key, world_ids)
            coverage = _coverage(profile, support_rows, nonroot_keys, ambiguous_nonroot_keys)
            validation_pass = all(
                validation[field] == 0
                for field in (
                    "illegal_key_count",
                    "action_set_mismatch_count",
                    "invalid_distribution_count",
                    "hidden_world_token_leakage_count",
                )
            )
            finite_distribution_pass = all(
                all(math.isfinite(float(prob)) and float(prob) >= 0.0 for prob in dist.values())
                for dist in profile.values()
            )
            snapshots.append({
                "budget": budget,
                "iterations_added": delta,
                "interval_runtime_seconds": interval_runtime,
                "cumulative_runtime_seconds": cumulative_runtime,
                "terminal_evaluations": solver.snapshot().terminal_evaluations,
                "profile_sha256": _profile_sha256(profile),
                "coverage": coverage,
                "profile_validation": validation,
                "snapshot_pass": validation_pass and finite_distribution_pass,
                "meets_downstream_coverage_targets": (
                    coverage["nonroot_native_fraction"] >= NONROOT_TARGET
                    and coverage["ambiguous_nonroot_native_fraction"] >= AMBIGUOUS_NONROOT_TARGET
                ),
            })
        seed_results.append({
            "seed": seed,
            "snapshots": snapshots,
            "seed_pass": len(snapshots) == len(BUDGETS) and all(row["snapshot_pass"] for row in snapshots),
        })

    selected_budget = None
    selection_reason = None
    for budget in BUDGETS:
        rows = [
            next(snapshot for snapshot in seed_row["snapshots"] if snapshot["budget"] == budget)
            for seed_row in seed_results
        ]
        if all(row["meets_downstream_coverage_targets"] for row in rows):
            selected_budget = budget
            selection_reason = "smallest_tested_budget_meeting_80pct_nonroot_and_95pct_ambiguous_on_both_seeds"
            break
    if selected_budget is None:
        selected_budget = BUDGETS[-1]
        selection_reason = "no_tested_budget_met_both_targets_select_4096_and_require_explicit_completion"

    quality = {
        "support_144_worlds": len(support) == 144,
        "both_seeds_separate": [row["seed"] for row in seed_results] == list(SEEDS),
        "all_frozen_budgets_materialized": all(
            [snapshot["budget"] for snapshot in row["snapshots"]] == list(BUDGETS)
            for row in seed_results
        ),
        "all_snapshots_pass_firewalls": all(
            snapshot["snapshot_pass"] for row in seed_results for snapshot in row["snapshots"]
        ),
        "no_completion": True,
        "no_ev": True,
        "no_best_response": True,
        "no_nashconv_or_exploitability": True,
        "no_production_authority": True,
        "real_routes_certified_zero": True,
    }
    passed = all(quality.values())

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05H_144_WORLD_BROADENING_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05H_H1_MCCFR_NATIVE_COVERAGE_CONTRACT.md",
        "tools/openofc_solver/external_05h_broad_support.py",
        "tools/openofc_solver/run_external_05h_h1.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "mccfr-native-coverage-calibration-144-world-fixture",
        "config": {
            "seeds": list(SEEDS),
            "budgets": list(BUDGETS),
            "nonroot_native_target": NONROOT_TARGET,
            "ambiguous_nonroot_native_target": AMBIGUOUS_NONROOT_TARGET,
            "support_sha256": support_sha256(support),
        },
        "exhaustive_support": {
            "chance_worlds": len(support),
            "reachable_information_states": len(support_rows),
            "root_information_states": len(root_keys),
            "nonroot_information_states": len(nonroot_keys),
            "ambiguous_nonroot_information_states": len(ambiguous_nonroot_keys),
            "support_materialization_runtime_seconds": support_seconds,
        },
        "seed_results": seed_results,
        "downstream_budget_selection": {
            "selected_mccfr_iterations": selected_budget,
            "reason": selection_reason,
            "engineering_thresholds_only_not_strategic_convergence_claim": True,
        },
        "quality": quality,
        "verdict": "PASS_05H_H1_COVERAGE_CALIBRATION" if passed else "FAIL_05H_H1_COVERAGE_CALIBRATION",
        "next_gate_recommendation": (
            "05H_H2_EXPLICIT_M_PROVENANCE_AND_COMPLETION"
            if passed else "STOP_AND_DIAGNOSE_H1"
        ),
        "real_routes_certified": 0,
        "files": [{"path": path, "sha256": _sha256_file(path)} for path in source_paths],
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    if not passed:
        raise RuntimeError(json.dumps({
            "experiment_id": EXPERIMENT_ID,
            "verdict": payload["verdict"],
            "quality": quality,
            "manifest_sha256": payload["manifest_sha256"],
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
    compact = {
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "exhaustive_support": payload["exhaustive_support"],
        "downstream_budget_selection": payload["downstream_budget_selection"],
        "seed_coverage": [
            {
                "seed": row["seed"],
                "budgets": [
                    {
                        "budget": snap["budget"],
                        "nonroot": snap["coverage"]["nonroot_native_fraction"],
                        "ambiguous_nonroot": snap["coverage"]["ambiguous_nonroot_native_fraction"],
                    }
                    for snap in row["snapshots"]
                ],
            }
            for row in payload["seed_results"]
        ],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }
    print(json.dumps(compact, sort_keys=True))


if __name__ == "__main__":
    main()
