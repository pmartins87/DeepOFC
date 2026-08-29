from __future__ import annotations

"""Conditional 05H-H4 exact counterfactual posterior audit of complete M."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from external_05g_uniform_backward_completion import (
    SOURCE_LABEL as COMPLETION_SOURCE,
    build_uniform_local_backward_completion,
)
from external_05h_broad_support import (
    AUTHORITY,
    public_pre_r3_state,
    support_sha256,
    validate_physical_support,
    worlds,
)
from external_hidden_discard_overlap_strategic import OverlapExternalSamplingMCCFR, build_reachable_support
from run_external_05g_q0b import _support_maps, _validate_profile
from run_external_05g_q1a import _profile_sha256, _source_map_sha256
from run_external_05g_q1b import _materialize_completion_profile
from run_external_05g_q3 import (
    EPS,
    TV_THRESHOLDS,
    _counterfactual_state_masses,
    _posterior_rows,
    _seed_summary,
)
from run_external_05h_h1 import BUDGETS, SEEDS
from run_external_05h_h2 import _assemble_m

EXPERIMENT_ID = "EXT-05H-H4-COUNTERFACTUAL-POSTERIOR-AUDIT"


def _sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(*, mccfr_iterations: int) -> dict:
    if mccfr_iterations not in BUDGETS:
        raise ValueError(f"H4 budget must be frozen H1 candidate: {BUDGETS}")

    base_state = public_pre_r3_state()
    support = worlds()
    validate_physical_support(base_state, support)

    t0 = perf_counter()
    support_rows = build_reachable_support(base_state, support)
    support_seconds = perf_counter() - t0
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)
    if len(support) != 144 or len(support_rows) != 261076:
        raise RuntimeError("H4 refuses geometry differing from passed H0")

    t1 = perf_counter()
    completion = build_uniform_local_backward_completion(support_rows)
    completion_seconds = perf_counter() - t1
    completion_profile = _materialize_completion_profile(support_rows, completion.choice_map())

    world_ids = tuple(world.world_id for world in support)
    seed_results = []
    for seed in SEEDS:
        t2 = perf_counter()
        solver = OverlapExternalSamplingMCCFR(base_state, support, seed=seed)
        solver.run(mccfr_iterations)
        mccfr = solver.current_profile()
        mccfr_seconds = perf_counter() - t2
        m_profile, source_map = _assemble_m(
            support_rows=support_rows,
            mccfr=mccfr,
            completion=completion_profile,
        )
        validation = _validate_profile(m_profile, support_by_key, world_ids)
        complete = set(m_profile) == set(support_by_key) and set(source_map) == set(support_by_key)
        firewalls = complete and all(
            validation[field] == 0
            for field in (
                "illegal_key_count",
                "action_set_mismatch_count",
                "invalid_distribution_count",
                "hidden_world_token_leakage_count",
            )
        )
        if not firewalls:
            raise RuntimeError("H4 complete M profile failed firewall")

        t3 = perf_counter()
        masses0, traversal0 = _counterfactual_state_masses(
            base_state,
            support,
            opponent_profile=m_profile,
            player=0,
        )
        masses1, traversal1 = _counterfactual_state_masses(
            base_state,
            support,
            opponent_profile=m_profile,
            player=1,
        )
        posterior_rows, diagnostics = _posterior_rows(
            support_rows,
            source_map=source_map,
            masses_by_player={0: masses0, 1: masses1},
        )
        posterior_seconds = perf_counter() - t3
        summary = _seed_summary(posterior_rows)

        completion_metric = summary["completion_reachable_ambiguous_tv"]
        relevant_count = summary["completion_counterfactually_reachable_ambiguous_information_states"]
        if relevant_count == 0:
            interpretation = "COMPLETION_COUNTERFACTUALLY_IRRELEVANT_05H"
        elif completion_metric["max_tv"] is not None and float(completion_metric["max_tv"]) <= EPS:
            interpretation = "UNIFORM_COMPLETION_MATCHES_COUNTERFACTUAL_POSTERIOR_05H"
        else:
            interpretation = "NONUNIFORM_COUNTERFACTUAL_POSTERIOR_DETECTED_05H"

        diagnostics_pass = all(value == 0 for value in diagnostics.values())
        seed_results.append({
            "seed": seed,
            "mccfr_iterations": mccfr_iterations,
            "native_runtime_seconds": mccfr_seconds,
            "native_information_states": len(mccfr),
            "native_profile_sha256": _profile_sha256(mccfr),
            "m_profile_sha256": _profile_sha256(m_profile),
            "m_source_map_sha256": _source_map_sha256(source_map),
            "profile_validation": validation,
            "counterfactual_traversal": {"player0": traversal0, "player1": traversal1},
            "posterior_runtime_seconds": posterior_seconds,
            "posterior_diagnostics": diagnostics,
            "summary": summary,
            "interpretation": interpretation,
            "seed_pass": firewalls and diagnostics_pass,
        })

    interpretations = [row["interpretation"] for row in seed_results]
    if len(interpretations) == 2 and all(
        value in {
            "UNIFORM_COMPLETION_MATCHES_COUNTERFACTUAL_POSTERIOR_05H",
            "COMPLETION_COUNTERFACTUALLY_IRRELEVANT_05H",
        }
        for value in interpretations
    ):
        cross_seed = "UNIFORM_COMPLETION_MATCHES_COUNTERFACTUAL_POSTERIOR_05H"
        next_gate = "BROADEN_GAME_GEOMETRY_OR_MOVE_TOWARD_LESS_REDUCED_GAME"
    else:
        cross_seed = "NONUNIFORM_COUNTERFACTUAL_POSTERIOR_DETECTED_05H"
        next_gate = "ADAPT_PRECOMMITTED_COUNTERFACTUAL_WEIGHTED_COMPLETION_AB_TO_05H"

    quality = {
        "support_matches_h0": len(support) == 144 and len(support_rows) == 261076,
        "completion_complete": completion.information_states == len(support_rows),
        "both_seeds_audited_separately": len(seed_results) == 2 and [row["seed"] for row in seed_results] == list(SEEDS),
        "both_seeds_pass_mechanical_firewalls": len(seed_results) == 2 and all(row["seed_pass"] for row in seed_results),
        "no_policy_update": True,
        "no_best_response_choice_update": True,
        "no_ev_ranking": True,
        "no_nashconv_recomputation": True,
        "no_production_authority": True,
        "real_routes_certified_zero": True,
    }
    passed = all(quality.values())

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05H_H4_COUNTERFACTUAL_POSTERIOR_AUDIT_CONTRACT.md",
        "tools/openofc_solver/run_external_05h_h4.py",
        "tools/openofc_solver/run_external_05g_q3.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "exact-counterfactual-posterior-audit-of-05H-M-completion-holes",
        "config": {
            "seeds": list(SEEDS),
            "mccfr_iterations": mccfr_iterations,
            "chance_worlds": len(support),
            "support_sha256": support_sha256(support),
            "completion_policy_sha256": completion.policy_sha256,
            "completion_source_label": COMPLETION_SOURCE,
            "posterior_tv_epsilon": EPS,
            "diagnostic_tv_thresholds": list(TV_THRESHOLDS),
            "counterfactual_reach": "uniform_chance_prior_times_opponent_behavior_reach_with_own_actions_enumerated",
            "posterior_baseline": "uniform_over_ReachableSupport.concrete_states_exactly_matching_completion_builder",
        },
        "exhaustive_support": {
            "chance_worlds": len(support),
            "reachable_information_states": len(support_rows),
            "root_information_states": len(root_keys),
            "nonroot_information_states": len(nonroot_keys),
            "ambiguous_nonroot_information_states": len(ambiguous_nonroot_keys),
            "support_materialization_runtime_seconds": support_seconds,
        },
        "completion_build": {
            "runtime_seconds": completion_seconds,
            "information_states": completion.information_states,
            "terminal_evaluations": completion.terminal_evaluations,
            "policy_sha256": completion.policy_sha256,
        },
        "seed_results": seed_results,
        "cross_seed_interpretation": cross_seed,
        "quality": quality,
        "verdict": "PASS_05H_H4_COUNTERFACTUAL_POSTERIOR_AUDIT" if passed else "FAIL_05H_H4_COUNTERFACTUAL_POSTERIOR_AUDIT",
        "next_gate_recommendation": next_gate if passed else "STOP_AND_DIAGNOSE_H4_MECHANICS",
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
    parser.add_argument("--mccfr-iterations", required=True, type=int)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = run(mccfr_iterations=args.mccfr_iterations)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "cross_seed_interpretation": payload["cross_seed_interpretation"],
        "seed_summaries": [
            {
                "seed": row["seed"],
                "completion_counterfactually_reachable_ambiguous_information_states": row["summary"]["completion_counterfactually_reachable_ambiguous_information_states"],
                "completion_reachable_ambiguous_tv": row["summary"]["completion_reachable_ambiguous_tv"],
                "interpretation": row["interpretation"],
            }
            for row in payload["seed_results"]
        ],
        "next_gate_recommendation": payload["next_gate_recommendation"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
