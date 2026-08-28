from __future__ import annotations

"""Run 05F-Q1: UCT vs MCCFR on deliberate hidden-discard overlap."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from external_hidden_discard_overlap import run_overlap_infoset_uct
from external_hidden_discard_overlap_strategic import (
    AUTHORITY,
    OverlapExternalSamplingMCCFR,
    build_reachable_support,
    complete_profile,
    exact_nash_conv,
    exact_profile_value,
    visit_profile_from_overlap_search,
)
from test_external_hidden_discard_overlap import _overlap_worlds, _public_pre_r3_state

EXPERIMENT_ID = "EXT-05F-Q1-HIDDEN-DISCARD-STRATEGIC-COMPARATOR"
UCT_ITERATIONS = 6_000
UCT_SEED = 2026082891
UCT_EXPLORATION = 1.25
MCCFR_ITERATIONS = 512
MCCFR_SEED = 2026082903
COMPLETION_MIN_ITERATIONS = 64
SEARCH_COMPLETION_SEED = 2026082909
MCCFR_COMPLETION_SEED = 2026082917


def _merge_by_actor(rows, p0_profile, p1_profile):
    merged = {}
    for row in rows:
        source = p0_profile if row.actor == 0 else p1_profile
        merged[row.information_state_key] = dict(source[row.information_state_key])
    return merged


def _profile_sha(profile) -> str:
    raw = json.dumps(profile, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def run() -> dict:
    worlds = _overlap_worlds()
    state = _public_pre_r3_state()
    rows = build_reachable_support(state, worlds)
    max_actions = max(len(row.action_keys) for row in rows)
    ambiguous_rows = [row for row in rows if len(row.concrete_states) > 1]
    ambiguous_nonroot = [row for row in ambiguous_rows if (row.round_index, row.actor) != (3, 0)]

    search = run_overlap_infoset_uct(
        state, worlds, iterations=UCT_ITERATIONS, seed=UCT_SEED, exploration=UCT_EXPLORATION
    )
    search_base = visit_profile_from_overlap_search(search)

    mccfr = OverlapExternalSamplingMCCFR(state, worlds, seed=MCCFR_SEED)
    mccfr.run(MCCFR_ITERATIONS)
    mccfr_base = mccfr.current_profile()
    mccfr_snapshot = mccfr.snapshot()

    completion_iterations = max(COMPLETION_MIN_ITERATIONS, max_actions)
    search_completed = complete_profile(
        search_base,
        rows,
        iterations_per_missing_infoset=completion_iterations,
        seed=SEARCH_COMPLETION_SEED,
        exploration=1.0,
    )
    mccfr_completed = complete_profile(
        mccfr_base,
        rows,
        iterations_per_missing_infoset=completion_iterations,
        seed=MCCFR_COMPLETION_SEED,
        exploration=1.0,
    )

    search_profile = search_completed.profile
    mccfr_profile = mccfr_completed.profile
    search_p0_mccfr_p1 = _merge_by_actor(rows, search_profile, mccfr_profile)
    mccfr_p0_search_p1 = _merge_by_actor(rows, mccfr_profile, search_profile)

    values = {
        "search_self": exact_profile_value(state, worlds, profile=search_profile, support_rows=rows),
        "mccfr_self": exact_profile_value(state, worlds, profile=mccfr_profile, support_rows=rows),
        "search_p0_vs_mccfr_p1": exact_profile_value(state, worlds, profile=search_p0_mccfr_p1, support_rows=rows),
        "mccfr_p0_vs_search_p1": exact_profile_value(state, worlds, profile=mccfr_p0_search_p1, support_rows=rows),
    }
    search_nash = exact_nash_conv(state, worlds, profile=search_profile, support_rows=rows)
    mccfr_nash = exact_nash_conv(state, worlds, profile=mccfr_profile, support_rows=rows)

    source_paths = [
        "tools/openofc_solver/external_hidden_discard_overlap.py",
        "tools/openofc_solver/external_hidden_discard_overlap_strategic.py",
        "tools/openofc_solver/test_external_hidden_discard_overlap.py",
        "tools/openofc_solver/test_external_hidden_discard_overlap_strategic.py",
        "tools/openofc_solver/run_external_05f_q1.py",
        "tools/openofc_solver/EXTERNAL_05F_HIDDEN_DISCARD_OVERLAP_CONTRACT.md",
        "tools/openofc_solver/strategic_cfr.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "hidden-discard-overlap-search-vs-mccfr-exact-br",
        "fixed_game": {
            "support_worlds": len(worlds),
            "reachable_information_states": len(rows),
            "ambiguous_information_states": len(ambiguous_rows),
            "ambiguous_nonroot_information_states": len(ambiguous_nonroot),
            "max_compatible_concrete_states": max(len(row.concrete_states) for row in rows),
            "max_legal_actions": max_actions,
        },
        "search": {
            "iterations": UCT_ITERATIONS,
            "seed": UCT_SEED,
            "base_information_states": len(search_base),
            "base_coverage": len(search_base) / len(rows),
            "completed_information_states": search_completed.reachable_information_states,
            "resolved_information_states": search_completed.resolved_information_states,
            "profile_sha256": _profile_sha(search_profile),
        },
        "mccfr": {
            "iterations": MCCFR_ITERATIONS,
            "seed": MCCFR_SEED,
            "base_information_states": len(mccfr_base),
            "base_coverage": len(mccfr_base) / len(rows),
            "training_terminal_evaluations": mccfr_snapshot.terminal_evaluations,
            "completed_information_states": mccfr_completed.reachable_information_states,
            "resolved_information_states": mccfr_completed.resolved_information_states,
            "profile_sha256": _profile_sha(mccfr_profile),
        },
        "completion": {
            "iterations_per_missing_infoset": completion_iterations,
            "prior": "uniform_over_compatible_concrete_states",
            "newly_resolved_states_do_not_bootstrap_each_other": True,
        },
        "exact_fixed_profile_values": {
            name: {
                "expected_u0": result.expected_u0,
                "terminal_leaves": result.terminal_leaves,
                "information_states_seen": result.information_states_seen,
            }
            for name, result in values.items()
        },
        "exact_best_response": {
            "search": {
                "br0": search_nash.br0.value,
                "br1": search_nash.br1.value,
                "nash_conv": search_nash.nash_conv,
                "exploitability": search_nash.exploitability,
            },
            "mccfr": {
                "br0": mccfr_nash.br0.value,
                "br1": mccfr_nash.br1.value,
                "nash_conv": mccfr_nash.nash_conv,
                "exploitability": mccfr_nash.exploitability,
            },
        },
        "quality": {
            "deliberate_nonroot_ambiguity_present": len(ambiguous_nonroot) > 0,
            "profiles_complete": search_completed.reachable_information_states == len(rows) and mccfr_completed.reachable_information_states == len(rows),
            "values_finite": all(math.isfinite(result.expected_u0) for result in values.values()),
            "nashconv_nonnegative": search_nash.nash_conv >= 0.0 and mccfr_nash.nash_conv >= 0.0,
            "no_production_certification_claim": True,
        },
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "limitations": [
            "four-world deliberately constructed reduced support",
            "finite search/MCCFR snapshots require explicit local completion before exact BR",
            "completion currently uses a uniform compatible-state prior and is itself an approximation",
            "exact BR is exact only for each frozen completed policy on this finite reduced game",
            "no real Bellman route certification",
        ],
        "promotion_recommendation": "IF_Q1_PASSES_RUN_REACH_WEIGHT_AUDIT_ON_AMBIGUOUS_INFOSETS_BEFORE_ALGORITHM_DECISION",
        "real_routes_certified": 0,
    }
    if not all(payload["quality"].values()):
        raise RuntimeError(f"05F-Q1 gate failed: {payload['quality']}")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05f_q1.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "reachable_information_states": payload["fixed_game"]["reachable_information_states"],
        "ambiguous_nonroot_information_states": payload["fixed_game"]["ambiguous_nonroot_information_states"],
        "search_base_coverage": payload["search"]["base_coverage"],
        "mccfr_base_coverage": payload["mccfr"]["base_coverage"],
        "search_exploitability": payload["exact_best_response"]["search"]["exploitability"],
        "mccfr_exploitability": payload["exact_best_response"]["mccfr"]["exploitability"],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
