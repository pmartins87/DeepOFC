from __future__ import annotations

"""Run 05D-Q1 with explicit counterfactual information-set completion."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from external_two_street_counterfactual_resolve import (
    AUTHORITY,
    build_reachable_infoset_support,
    complete_profile_with_counterfactual_resolve,
    exact_profile_value_strict,
)
from external_two_street_infoset_search import run_two_street_infoset_uct
from external_two_street_mccfr import (
    TwoStreetExternalSamplingMCCFR,
    root_total_variation,
    visit_profile_from_search,
)
from strategic_cfr import information_state_key, legal_action_pairs
from test_external_two_street_infoset_search import _coherent_r3_state, _support_worlds

EXPERIMENT_ID = "EXT-05D-Q1-COUNTERFACTUAL-COMPLETION"
UCT_ITERATIONS = 5_000
UCT_SEED = 2026082831
MCCFR_ITERATIONS = 256
MCCFR_SEED = 2026082853
RESOLVE_MIN_ITERATIONS = 64
SEARCH_RESOLVE_SEED = 2026082871
MCCFR_RESOLVE_SEED = 2026082873
Q0_MANIFEST_SHA256 = "b7d27c18b559fba48e6f2178aa7aa036fef07a93bab18596f1fa5fb176742a98"


def _profile_sha256(profile) -> str:
    raw = json.dumps(profile, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _root_distribution(state, profile):
    key = information_state_key(state)
    action_keys = tuple(action_key for action_key, _action in legal_action_pairs(state))
    supplied = profile[key]
    weights = {action_key: float(supplied.get(action_key, 0.0)) for action_key in action_keys}
    mass = sum(weights.values())
    if mass <= 0.0:
        raise RuntimeError("completed root distribution has zero mass")
    return {action_key: value / mass for action_key, value in weights.items()}


def run() -> dict:
    worlds = _support_worlds()
    state = _coherent_r3_state(worlds[0])

    search = run_two_street_infoset_uct(
        state,
        worlds,
        iterations=UCT_ITERATIONS,
        seed=UCT_SEED,
        exploration=1.0,
    )
    search_base = visit_profile_from_search(search)

    trainer = TwoStreetExternalSamplingMCCFR(state, worlds, seed=MCCFR_SEED)
    trainer.run(MCCFR_ITERATIONS)
    mccfr_base = trainer.current_profile()
    mccfr_snapshot = trainer.snapshot()

    reachable = build_reachable_infoset_support(state, worlds)
    max_actions = max(len(row.action_keys) for row in reachable)
    resolve_iterations = max(RESOLVE_MIN_ITERATIONS, max_actions)

    search_completed = complete_profile_with_counterfactual_resolve(
        search_base,
        reachable,
        iterations_per_infoset=resolve_iterations,
        seed=SEARCH_RESOLVE_SEED,
        exploration=1.0,
    )
    mccfr_completed = complete_profile_with_counterfactual_resolve(
        mccfr_base,
        reachable,
        iterations_per_infoset=resolve_iterations,
        seed=MCCFR_RESOLVE_SEED,
        exploration=1.0,
    )

    evaluations = {
        "search_completed_self": exact_profile_value_strict(
            state,
            worlds,
            support_rows=reachable,
            p0_profile=search_completed.profile,
            p1_profile=search_completed.profile,
        ),
        "mccfr_completed_self": exact_profile_value_strict(
            state,
            worlds,
            support_rows=reachable,
            p0_profile=mccfr_completed.profile,
            p1_profile=mccfr_completed.profile,
        ),
        "search_completed_p0_vs_mccfr_completed_p1": exact_profile_value_strict(
            state,
            worlds,
            support_rows=reachable,
            p0_profile=search_completed.profile,
            p1_profile=mccfr_completed.profile,
        ),
        "mccfr_completed_p0_vs_search_completed_p1": exact_profile_value_strict(
            state,
            worlds,
            support_rows=reachable,
            p0_profile=mccfr_completed.profile,
            p1_profile=search_completed.profile,
        ),
    }

    base_tv = root_total_variation(state, search_base, mccfr_base)
    completed_tv = root_total_variation(state, search_completed.profile, mccfr_completed.profile)
    total_reachable = len(reachable)

    source_paths = [
        "tools/openofc_solver/external_two_street_infoset_search.py",
        "tools/openofc_solver/external_two_street_mccfr.py",
        "tools/openofc_solver/external_two_street_counterfactual_resolve.py",
        "tools/openofc_solver/test_external_two_street_counterfactual_resolve.py",
        "tools/openofc_solver/run_external_two_street_05d_q1.py",
        "tools/openofc_solver/EXTERNAL_TWO_STREET_05D_Q1_COUNTERFACTUAL_COMPLETION_CONTRACT.md",
        "tools/openofc_solver/strategic_cfr.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "strict-completed-two-street-mccfr-vs-uct",
        "fixed_game": {
            "support_worlds": len(worlds),
            "uniform_physical_world_support": True,
            "canonical_terminal_utility": True,
            "canonical_infoset_keys": True,
            "reachable_information_states": total_reachable,
            "p0_information_states": sum(1 for row in reachable if row.actor == 0),
            "p1_information_states": sum(1 for row in reachable if row.actor == 1),
            "max_legal_actions": max_actions,
        },
        "uct_base": {
            "iterations": UCT_ITERATIONS,
            "seed": UCT_SEED,
            "selected_root_action_key": search.selected_root_action_key,
            "information_states": len(search_base),
            "reachable_coverage_fraction": search_completed.base_information_states_on_support / total_reachable,
            "profile_kind": "local_action_visit_frequencies",
        },
        "mccfr_base": {
            "iterations": MCCFR_ITERATIONS,
            "seed": MCCFR_SEED,
            "information_states": mccfr_snapshot.information_states,
            "training_terminal_evaluations": mccfr_snapshot.terminal_evaluations,
            "reachable_coverage_fraction": mccfr_completed.base_information_states_on_support / total_reachable,
            "profile_kind": "current_regret_matching",
        },
        "completion": {
            "method": "independent_local_root_uct_against_frozen_own_base_profile",
            "root_action_before_hidden_state_sample": True,
            "compatible_state_weighting": "uniform_finite_support_search_prior",
            "downstream_missing_base_policy": "uniform_rollout_only",
            "recursive_bootstrap": False,
            "iterations_per_missing_infoset": resolve_iterations,
            "search": {
                "seed": SEARCH_RESOLVE_SEED,
                "base_information_states_on_support": search_completed.base_information_states_on_support,
                "resolved_information_states": search_completed.resolved_information_states,
                "completed_information_states": search_completed.completed_information_states,
                "profile_sha256": _profile_sha256(search_completed.profile),
            },
            "mccfr": {
                "seed": MCCFR_RESOLVE_SEED,
                "base_information_states_on_support": mccfr_completed.base_information_states_on_support,
                "resolved_information_states": mccfr_completed.resolved_information_states,
                "completed_information_states": mccfr_completed.completed_information_states,
                "profile_sha256": _profile_sha256(mccfr_completed.profile),
            },
        },
        "comparison": {
            name: {
                "expected_u0": result.expected_u0,
                "terminal_leaves": result.terminal_leaves,
                "information_states_seen": result.information_states_seen,
                "strict_unseen_infoset_fallback": False,
            }
            for name, result in evaluations.items()
        },
        "root_total_variation": {
            "base_profiles": base_tv,
            "completed_profiles": completed_tv,
        },
        "q0_reference": {
            "manifest_sha256": Q0_MANIFEST_SHA256,
            "search_self": 27.205631075589622,
            "mccfr_self": 27.099211805573447,
            "search_p0_vs_mccfr_p1": 27.20569863235789,
            "mccfr_p0_vs_search_p1": 27.70528074597922,
            "used_uniform_unseen_infoset_fallback": True,
        },
        "quality": {
            "search_profile_complete": search_completed.completed_information_states == total_reachable,
            "mccfr_profile_complete": mccfr_completed.completed_information_states == total_reachable,
            "search_missing_states_actually_resolved": search_completed.resolved_information_states > 0,
            "mccfr_missing_states_actually_resolved": mccfr_completed.resolved_information_states > 0,
            "all_strict_profile_values_finite": all(
                math.isfinite(result.expected_u0) for result in evaluations.values()
            ),
            "root_total_variations_valid": 0.0 <= base_tv <= 1.0 and 0.0 <= completed_tv <= 1.0,
            "same_root_information_state": mccfr_snapshot.root_information_state_key == information_state_key(state),
            "no_unseen_infoset_fallback_in_strict_comparison": True,
            "no_equilibrium_claim": True,
            "no_exploitability_claim": True,
        },
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "limitations": [
            "six-world reduced support",
            "completion beliefs use uniform weighting over compatible finite-support concrete states",
            "missing downstream states inside each local resolver use the immutable base profile's uniform rollout fallback",
            "MCCFR comparison still uses current regret-matching rather than a separately validated reach-weighted average",
            "no best-response or exploitability authority",
            "not posterior-conditioned on R0-R2 strategic signalling",
        ],
        "promotion_recommendation": "IF_Q1_SIGNAL_SURVIVES_START_05D_Q2_POSTERIOR_OR_REACH_WEIGHT_AUDIT_ELSE_DIAGNOSE_FALLBACK_ARTIFACT",
        "real_routes_certified": 0,
    }
    if not all(payload["quality"].values()):
        raise RuntimeError(f"05D-Q1 mechanical completion gate failed: {payload['quality']}")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_two_street_05d_q1.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "reachable_information_states": payload["fixed_game"]["reachable_information_states"],
        "search_base_coverage": payload["uct_base"]["reachable_coverage_fraction"],
        "mccfr_base_coverage": payload["mccfr_base"]["reachable_coverage_fraction"],
        "comparison": {
            name: values["expected_u0"] for name, values in payload["comparison"].items()
        },
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
