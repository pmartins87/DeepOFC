from __future__ import annotations

"""Run 05G-Q0C native coverage scaling diagnostic.

No missing policy is completed or evaluated here. Coverage is measured on
materialized native learner states only.
"""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

from external_05g_broad_support import AUTHORITY, broad_worlds, public_pre_r3_state, support_sha256, validate_broad_physical_support
from external_hidden_discard_overlap import run_overlap_infoset_uct
from external_hidden_discard_overlap_strategic import OverlapExternalSamplingMCCFR, ReachableSupport, build_reachable_support, visit_profile_from_overlap_search
from run_external_05g_q0b import _coverage, _root_diagnostics, _support_maps, _validate_profile

EXPERIMENT_ID = "EXT-05G-Q0C-NATIVE-COVERAGE-SCALING"
SEEDS = (20260829, 20260830)
BUDGET_PAIRS = ((20000, 256), (50000, 512))


def _layer_coverage(profile: Mapping[str, Mapping[str, float]], rows: Sequence[ReachableSupport]) -> list[dict]:
    keys = set(profile)
    layers = sorted({(row.round_index, row.actor) for row in rows})
    out = []
    for round_index, actor in layers:
        possible = {row.information_state_key for row in rows if (row.round_index, row.actor) == (round_index, actor)}
        hit = len(keys & possible)
        out.append({
            "round_index": round_index,
            "actor": actor,
            "hit": hit,
            "possible": len(possible),
            "ratio": hit / len(possible) if possible else 0.0,
        })
    return out


def _set_overlap(search_keys: set[str], mccfr_keys: set[str]) -> dict:
    inter = len(search_keys & mccfr_keys)
    union = len(search_keys | mccfr_keys)
    return {
        "intersection": inter,
        "union": union,
        "jaccard": inter / union if union else 1.0,
        "search_keys_in_mccfr_ratio": inter / len(search_keys) if search_keys else 0.0,
        "mccfr_keys_in_search_ratio": inter / len(mccfr_keys) if mccfr_keys else 0.0,
    }


def _trial(*, base_state, worlds, support_rows, support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys, search_iterations, mccfr_iterations, seed) -> dict:
    all_keys = set(support_by_key)
    world_ids = tuple(world.world_id for world in worlds)

    t0 = perf_counter()
    search_result = run_overlap_infoset_uct(base_state, worlds, iterations=search_iterations, seed=seed, exploration=1.0)
    search_seconds = perf_counter() - t0
    search_profile = visit_profile_from_overlap_search(search_result)

    t1 = perf_counter()
    mccfr = OverlapExternalSamplingMCCFR(base_state, worlds, seed=seed)
    mccfr.run(mccfr_iterations)
    mccfr_seconds = perf_counter() - t1
    mccfr_profile = mccfr.current_profile()
    mccfr_snapshot = mccfr.snapshot()

    search_validation = _validate_profile(search_profile, support_by_key, world_ids)
    mccfr_validation = _validate_profile(mccfr_profile, support_by_key, world_ids)
    search_coverage = _coverage(search_profile, all_keys, nonroot_keys, ambiguous_nonroot_keys)
    mccfr_coverage = _coverage(mccfr_profile, all_keys, nonroot_keys, ambiguous_nonroot_keys)
    roots, search_roots_complete, mccfr_roots_complete = _root_diagnostics(search_profile, mccfr_profile, root_keys)

    firewalls = all((
        search_validation["illegal_key_count"] == 0,
        search_validation["action_set_mismatch_count"] == 0,
        search_validation["invalid_distribution_count"] == 0,
        search_validation["hidden_world_token_leakage_count"] == 0,
        mccfr_validation["illegal_key_count"] == 0,
        mccfr_validation["action_set_mismatch_count"] == 0,
        mccfr_validation["invalid_distribution_count"] == 0,
        mccfr_validation["hidden_world_token_leakage_count"] == 0,
        search_roots_complete,
        mccfr_roots_complete,
        search_coverage["nonroot_hit"] > 0,
        mccfr_coverage["nonroot_hit"] > 0,
    ))

    return {
        "seed": seed,
        "search_iterations": search_iterations,
        "mccfr_iterations": mccfr_iterations,
        "technical_firewalls_pass": firewalls,
        "search": {
            "runtime_seconds": search_seconds,
            "coverage": search_coverage,
            "layer_coverage": _layer_coverage(search_profile, support_rows),
            "validation": search_validation,
            "reported_information_states": search_result.information_states,
        },
        "mccfr": {
            "runtime_seconds": mccfr_seconds,
            "coverage": mccfr_coverage,
            "layer_coverage": _layer_coverage(mccfr_profile, support_rows),
            "validation": mccfr_validation,
            "reported_information_states": mccfr_snapshot.information_states,
            "terminal_evaluations": mccfr_snapshot.terminal_evaluations,
        },
        "native_key_overlap": _set_overlap(set(search_profile), set(mccfr_profile)),
        "root_diagnostics": roots,
    }


def _monotonic(trials: Sequence[dict], learner: str, metric: str) -> bool:
    for seed in SEEDS:
        rows = sorted((row for row in trials if row["seed"] == seed), key=lambda row: row[f"{learner}_iterations"])
        if len(rows) != 2:
            return False
        small = rows[0][learner]["coverage"][metric]
        large = rows[1][learner]["coverage"][metric]
        if large < small:
            return False
    return True


def run() -> dict:
    worlds = broad_worlds()
    base_state = public_pre_r3_state()
    validate_broad_physical_support(base_state, worlds)
    support_rows = build_reachable_support(base_state, worlds)
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)
    if len(root_keys) != 3:
        raise RuntimeError("05G-Q0C requires exactly three P0-R3 root infosets")

    trials = []
    for search_iterations, mccfr_iterations in BUDGET_PAIRS:
        for seed in SEEDS:
            trials.append(_trial(
                base_state=base_state,
                worlds=worlds,
                support_rows=support_rows,
                support_by_key=support_by_key,
                nonroot_keys=nonroot_keys,
                ambiguous_nonroot_keys=ambiguous_nonroot_keys,
                root_keys=root_keys,
                search_iterations=search_iterations,
                mccfr_iterations=mccfr_iterations,
                seed=seed,
            ))

    quality = {
        "all_four_paired_trials_executed": len(trials) == 4,
        "all_technical_firewalls_pass": all(row["technical_firewalls_pass"] for row in trials),
        "search_nonroot_coverage_monotonic": _monotonic(trials, "search", "nonroot_hit"),
        "search_ambiguous_coverage_monotonic": _monotonic(trials, "search", "ambiguous_nonroot_hit"),
        "mccfr_nonroot_coverage_monotonic": _monotonic(trials, "mccfr", "nonroot_hit"),
        "mccfr_ambiguous_coverage_monotonic": _monotonic(trials, "mccfr", "ambiguous_nonroot_hit"),
        "no_policy_completion_used": True,
        "no_exact_profile_evaluation_used": True,
        "no_exact_best_response_used": True,
        "no_strength_winner_claim": True,
        "ci_runtime_guarded_by_workflow_timeout": True,
    }
    passed = all(quality.values())

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05G_BROAD_HIDDEN_INFORMATION_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q0B_SEARCH_MCCFR_SMOKE_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q0C_NATIVE_COVERAGE_SCALING_CONTRACT.md",
        "tools/openofc_solver/external_05g_broad_support.py",
        "tools/openofc_solver/external_hidden_discard_overlap.py",
        "tools/openofc_solver/external_hidden_discard_overlap_strategic.py",
        "tools/openofc_solver/run_external_05g_q0b.py",
        "tools/openofc_solver/run_external_05g_q0c.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "native-coverage-scaling-diagnostic",
        "config": {
            "seeds": list(SEEDS),
            "budget_pairs": [{"search_iterations": s, "mccfr_iterations": m} for s, m in BUDGET_PAIRS],
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
        "quality": quality,
        "verdict": "PASS_SCALING_DIAGNOSTIC" if passed else "BLOCK_TECHNICAL",
        "promotion_recommendation": "DESIGN_05G_Q1_COMPLETION_AS_SEPARATE_COMPONENT" if passed else "FIX_Q0C_TECHNICAL_DEFECT_WITHOUT_MOVING_GATES",
        "limitations": [
            "native coverage is not strategic quality",
            "no missing policy is completed or evaluated",
            "root TV is diagnostic only",
            "finite reduced 36-world game only",
            "no REAL route is certified",
        ],
        "files": [{"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()} for path in source_paths],
        "real_routes_certified": 0,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    if not passed:
        raise RuntimeError(f"05G-Q0C failed: {quality}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05g_q0c.json")
    args = parser.parse_args()
    payload = run()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "coverage": [
            {
                "seed": row["seed"],
                "search_iterations": row["search_iterations"],
                "mccfr_iterations": row["mccfr_iterations"],
                "search_nonroot": row["search"]["coverage"]["nonroot_ratio"],
                "mccfr_nonroot": row["mccfr"]["coverage"]["nonroot_ratio"],
                "jaccard": row["native_key_overlap"]["jaccard"],
            }
            for row in payload["trials"]
        ],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
