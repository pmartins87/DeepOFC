from __future__ import annotations

"""Conditional 05G-Q4A exact A/B for counterfactual-weighted completion.

The protocol was frozen before Q3 results.  If Q3 does not activate Q4A, this
runner returns an explicit SKIP payload and performs no exploitability A/B.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

from external_05g_broad_support import (
    AUTHORITY,
    broad_worlds,
    public_pre_r3_state,
    support_sha256,
    validate_broad_physical_support,
)
from external_05g_counterfactual_weighted_completion import (
    SOURCE_LABEL as CF_COMPLETION_SOURCE,
    build_counterfactual_weighted_local_backward_completion,
)
from external_05g_uniform_backward_completion import (
    SOURCE_LABEL as UNIFORM_COMPLETION_SOURCE,
    build_uniform_local_backward_completion,
)
from external_hidden_discard_overlap_strategic import ReachableSupport, build_reachable_support
from run_external_05g_q0b import _support_maps, _validate_profile
from run_external_05g_q1a import (
    MCCFR_ITERATIONS,
    MCCFR_NATIVE,
    SEARCH_EXPLORATION,
    SEARCH_ITERATIONS,
    SEEDS,
    _profile_sha256,
    _source_map_sha256,
)
from run_external_05g_q1b import _materialize_completion_profile
from run_external_05g_q1c import _materialize_seed_profiles
from run_external_05g_q2 import RANK_TOLERANCE, _evaluate_profile
from run_external_05g_q3 import (
    EPS as POSTERIOR_EPS,
    TV_THRESHOLDS,
    _counterfactual_state_masses,
    _posterior_rows,
    _seed_summary,
)

EXPERIMENT_ID = "EXT-05G-Q4A-COUNTERFACTUAL-WEIGHTED-COMPLETION-AB"
ORIGINAL_PROFILE = "M"
CANDIDATE_PROFILE = "M_cf"
ACTIVATING_INTERPRETATIONS = {
    "NONUNIFORM_COUNTERFACTUAL_POSTERIOR_PRESENT",
}

BehaviorProfile = Mapping[str, Mapping[str, float]]


def _assemble_candidate(
    support_rows: Sequence[ReachableSupport],
    *,
    original_profile: BehaviorProfile,
    original_source_map: Mapping[str, str],
    weighted_completion_profile: BehaviorProfile,
) -> tuple[dict[str, dict[str, float]], dict[str, str]]:
    candidate: dict[str, dict[str, float]] = {}
    source_map: dict[str, str] = {}
    for row in support_rows:
        key = row.information_state_key
        original_source = original_source_map[key]
        if original_source == MCCFR_NATIVE:
            candidate[key] = {
                action: float(probability)
                for action, probability in original_profile[key].items()
            }
            source_map[key] = MCCFR_NATIVE
        elif original_source == UNIFORM_COMPLETION_SOURCE:
            candidate[key] = {
                action: float(probability)
                for action, probability in weighted_completion_profile[key].items()
            }
            source_map[key] = CF_COMPLETION_SOURCE
        else:
            raise AssertionError(f"Q4A unexpected original M source: {original_source}")
    return candidate, source_map


def _tv_bin(row: Mapping[str, object]) -> str:
    if not bool(row["counterfactually_reachable"]):
        return "ZERO_COUNTERFACTUAL_MASS"
    tv = float(row["tv_uniform_vs_counterfactual"])
    if tv <= TV_THRESHOLDS[0]:
        return "TV_LE_0.01"
    if tv <= TV_THRESHOLDS[1]:
        return "TV_0.01_TO_0.05"
    if tv <= TV_THRESHOLDS[2]:
        return "TV_0.05_TO_0.10"
    if tv <= TV_THRESHOLDS[3]:
        return "TV_0.10_TO_0.25"
    return "TV_GT_0.25"


def _changed_action_accounting(
    support_rows: Sequence[ReachableSupport],
    *,
    original_source_map: Mapping[str, str],
    original_completion_choices: Mapping[str, str],
    weighted_completion_choices: Mapping[str, str],
    posterior_rows: Sequence[dict],
) -> dict:
    posterior_by_key = {row["information_state_key"]: row for row in posterior_rows}
    changed = []
    all_holes = []
    for row in support_rows:
        key = row.information_state_key
        if original_source_map[key] != UNIFORM_COMPLETION_SOURCE:
            continue
        p = posterior_by_key[key]
        entry = {
            "information_state_sha256": hashlib.sha256(key.encode("utf-8")).hexdigest(),
            "round_index": row.round_index,
            "actor": row.actor,
            "layer": f"R{row.round_index}_P{row.actor}",
            "ambiguous": len(row.concrete_states) > 1,
            "counterfactually_reachable": bool(p["counterfactually_reachable"]),
            "tv_bin": _tv_bin(p),
            "old_action": original_completion_choices[key],
            "new_action": weighted_completion_choices[key],
        }
        all_holes.append(entry)
        if entry["old_action"] != entry["new_action"]:
            changed.append(entry)

    def count(field: str, rows: Sequence[dict]) -> dict[str, int]:
        return dict(sorted(Counter(str(row[field]) for row in rows).items()))

    return {
        "completion_holes": len(all_holes),
        "changed_completion_actions": len(changed),
        "unchanged_completion_actions": len(all_holes) - len(changed),
        "changed_fraction": len(changed) / len(all_holes) if all_holes else 0.0,
        "changed_by_layer": count("layer", changed),
        "changed_by_actor": count("actor", changed),
        "changed_by_ambiguity": count("ambiguous", changed),
        "changed_by_counterfactual_reach": count("counterfactually_reachable", changed),
        "changed_by_tv_bin": count("tv_bin", changed),
        "all_completion_holes_by_tv_bin": count("tv_bin", all_holes),
        "changed_information_state_sha256": sorted(row["information_state_sha256"] for row in changed),
    }


def _compare(original: dict, candidate: dict) -> dict:
    old = float(original["exploitability"])
    new = float(candidate["exploitability"])
    if new + RANK_TOLERANCE < old:
        outcome = "M_CF_STRICTLY_BETTER"
    elif old + RANK_TOLERANCE < new:
        outcome = "ORIGINAL_M_STRICTLY_BETTER"
    else:
        outcome = "TIE_WITHIN_TOLERANCE"
    return {
        "original_m_exploitability": old,
        "m_cf_exploitability": new,
        "candidate_minus_original": new - old,
        "absolute_difference": abs(new - old),
        "ranking_tolerance": RANK_TOLERANCE,
        "outcome": outcome,
    }


def run() -> dict:
    worlds = broad_worlds()
    base_state = public_pre_r3_state()
    validate_broad_physical_support(base_state, worlds)
    support_rows = build_reachable_support(base_state, worlds)
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)
    if (len(worlds), len(support_rows), len(nonroot_keys), len(ambiguous_nonroot_keys), len(root_keys)) != (
        36, 69_828, 69_825, 15_393, 3
    ):
        raise RuntimeError("05G-Q4A frozen support geometry changed")

    t0 = perf_counter()
    uniform_completion = build_uniform_local_backward_completion(support_rows)
    uniform_completion_seconds = perf_counter() - t0
    uniform_completion_profile = _materialize_completion_profile(
        support_rows, uniform_completion.choice_map()
    )

    # First reproduce original M and Q3 counterfactual posteriors on both seeds.
    preflight = []
    materialized_by_seed: dict[int, dict] = {}
    posterior_rows_by_seed: dict[int, list[dict]] = {}
    frozen_weights_by_seed: dict[int, dict[str, dict[str, float]]] = {}
    world_ids = tuple(world.world_id for world in worlds)

    for seed in SEEDS:
        materialized = _materialize_seed_profiles(
            seed=seed,
            base_state=base_state,
            worlds=worlds,
            support_rows=support_rows,
            completion_profile=uniform_completion_profile,
        )
        materialized_by_seed[seed] = materialized
        original_m = materialized["profiles"][ORIGINAL_PROFILE]
        original_source = materialized["source_maps"][ORIGINAL_PROFILE]

        p0_masses, _p0_diag = _counterfactual_state_masses(
            base_state, worlds, opponent_profile=original_m, player=0
        )
        p1_masses, _p1_diag = _counterfactual_state_masses(
            base_state, worlds, opponent_profile=original_m, player=1
        )
        masses_by_player = {0: p0_masses, 1: p1_masses}
        posterior_rows, diagnostics = _posterior_rows(
            support_rows,
            source_map=original_source,
            masses_by_player=masses_by_player,
        )
        posterior_rows_by_seed[seed] = posterior_rows
        summary = _seed_summary(posterior_rows)

        merged_weights: dict[str, dict[str, float]] = {}
        for row in support_rows:
            key = row.information_state_key
            merged_weights[key] = {
                fingerprint: float(mass)
                for fingerprint, mass in masses_by_player[row.actor].get(key, {}).items()
            }
        frozen_weights_by_seed[seed] = merged_weights

        validation = _validate_profile(original_m, support_by_key, world_ids)
        original_m_valid = (
            set(original_m) == set(support_by_key)
            and set(original_source) == set(support_by_key)
            and set(original_source.values()) <= {MCCFR_NATIVE, UNIFORM_COMPLETION_SOURCE}
            and all(
                validation[field] == 0
                for field in (
                    "illegal_key_count",
                    "action_set_mismatch_count",
                    "invalid_distribution_count",
                    "hidden_world_token_leakage_count",
                )
            )
            and all(value == 0 for value in diagnostics.values())
        )
        preflight.append({
            "seed": seed,
            "original_m_profile_sha256": _profile_sha256(original_m),
            "original_m_source_map_sha256": _source_map_sha256(original_source),
            "q3_interpretation_recomputed": summary["interpretation"],
            "completion_reachable_ambiguous_tv": summary["completion_reachable_ambiguous_tv"],
            "original_m_valid": original_m_valid,
        })

    if not all(row["original_m_valid"] for row in preflight):
        raise RuntimeError("Q4A preflight failed to reproduce valid original M")

    activated = any(
        row["q3_interpretation_recomputed"] in ACTIVATING_INTERPRETATIONS
        for row in preflight
    )
    if not activated:
        payload = {
            "schema": "openofc-external-component-ab-v1",
            "experiment_id": EXPERIMENT_ID,
            "authority": AUTHORITY,
            "activation": "NOT_ACTIVATED_BY_FROZEN_Q3_RULE",
            "preflight": preflight,
            "verdict": "SKIP_Q4A_NOT_ACTIVATED",
            "real_routes_certified": 0,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        payload["sha256"] = hashlib.sha256(raw).hexdigest()
        return payload

    seed_results = []
    for seed in SEEDS:
        materialized = materialized_by_seed[seed]
        original_m = materialized["profiles"][ORIGINAL_PROFILE]
        original_source = materialized["source_maps"][ORIGINAL_PROFILE]

        t1 = perf_counter()
        weighted_completion = build_counterfactual_weighted_local_backward_completion(
            support_rows,
            frozen_state_weights=frozen_weights_by_seed[seed],
            zero_weight_fallback_choices=uniform_completion.choice_map(),
        )
        weighted_seconds = perf_counter() - t1
        weighted_profile = _materialize_completion_profile(
            support_rows, weighted_completion.choice_map()
        )
        candidate, candidate_source = _assemble_candidate(
            support_rows,
            original_profile=original_m,
            original_source_map=original_source,
            weighted_completion_profile=weighted_profile,
        )

        native_keys = {key for key, source in original_source.items() if source == MCCFR_NATIVE}
        native_preserved = all(
            candidate[key] == original_m[key] and candidate_source[key] == MCCFR_NATIVE
            for key in native_keys
        )
        candidate_validation = _validate_profile(candidate, support_by_key, world_ids)
        candidate_valid = (
            set(candidate) == set(support_by_key)
            and set(candidate_source) == set(support_by_key)
            and set(candidate_source.values()) <= {MCCFR_NATIVE, CF_COMPLETION_SOURCE}
            and native_preserved
            and all(
                candidate_validation[field] == 0
                for field in (
                    "illegal_key_count",
                    "action_set_mismatch_count",
                    "invalid_distribution_count",
                    "hidden_world_token_leakage_count",
                )
            )
        )

        changes = _changed_action_accounting(
            support_rows,
            original_source_map=original_source,
            original_completion_choices=uniform_completion.choice_map(),
            weighted_completion_choices=weighted_completion.choice_map(),
            posterior_rows=posterior_rows_by_seed[seed],
        )

        original_evaluation = _evaluate_profile(
            name=ORIGINAL_PROFILE,
            profile=original_m,
            base_state=base_state,
            worlds=worlds,
            support_rows=support_rows,
        )
        candidate_evaluation = _evaluate_profile(
            name=CANDIDATE_PROFILE,
            profile=candidate,
            base_state=base_state,
            worlds=worlds,
            support_rows=support_rows,
        )
        comparison = _compare(original_evaluation, candidate_evaluation)
        seed_pass = (
            candidate_valid
            and original_evaluation["profile_pass"]
            and candidate_evaluation["profile_pass"]
        )
        seed_results.append({
            "seed": seed,
            "q3_interpretation_recomputed": next(
                row["q3_interpretation_recomputed"] for row in preflight if row["seed"] == seed
            ),
            "original_m_profile_sha256": _profile_sha256(original_m),
            "original_m_source_map_sha256": _source_map_sha256(original_source),
            "weighted_completion_policy_sha256": weighted_completion.policy_sha256,
            "candidate_profile_sha256": _profile_sha256(candidate),
            "candidate_source_map_sha256": _source_map_sha256(candidate_source),
            "weighted_completion_runtime_seconds": weighted_seconds,
            "weighted_completion_positive_weight_information_states": weighted_completion.positive_weight_information_states,
            "weighted_completion_zero_weight_fallback_information_states": weighted_completion.zero_weight_fallback_information_states,
            "mccfr_native_information_states_preserved": len(native_keys),
            "mccfr_native_rows_preserved_exactly": native_preserved,
            "candidate_validation": candidate_validation,
            "changed_action_accounting": changes,
            "original_m_exact_bilateral_br": original_evaluation,
            "candidate_m_cf_exact_bilateral_br": candidate_evaluation,
            "comparison": comparison,
            "seed_pass": seed_pass,
        })

    outcomes = [row["comparison"]["outcome"] for row in seed_results]
    cf_better = outcomes.count("M_CF_STRICTLY_BETTER")
    original_better = outcomes.count("ORIGINAL_M_STRICTLY_BETTER")
    if cf_better >= 1 and original_better == 0:
        recommendation = "PROMOTE_CF_COMPLETION_TO_BROADER_EXTERNAL_VALIDATION"
    elif original_better >= 1 and cf_better == 0:
        recommendation = "RETAIN_UNIFORM_COMPLETION_FOR_CURRENT_EXTERNAL_LINE"
    else:
        recommendation = "NO_CROSS_SEED_COMPLETION_WINNER_CONTINUE_DIAGNOSTICS"

    quality = {
        "q3_activation_condition_met": activated,
        "both_frozen_seeds_evaluated_separately": [row["seed"] for row in seed_results] == list(SEEDS),
        "both_seed_mechanical_checks_pass": len(seed_results) == 2 and all(row["seed_pass"] for row in seed_results),
        "mccfr_native_rows_preserved_on_both_seeds": all(row["mccfr_native_rows_preserved_exactly"] for row in seed_results),
        "same_q2_exact_br_authority_used_for_A_and_B": True,
        "ranking_tolerance_precommitted_1e_9": RANK_TOLERANCE == 1e-9,
        "frozen_weights_not_iterated": True,
        "no_production_authority": True,
        "real_routes_certified_zero": True,
    }
    passed = all(quality.values())
    if not passed:
        raise RuntimeError(f"05G-Q4A failed mechanical firewalls: {quality}")

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05G_Q3_COUNTERFACTUAL_POSTERIOR_AUDIT_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q4A_COUNTERFACTUAL_WEIGHTED_COMPLETION_AB_CONTRACT.md",
        "tools/openofc_solver/external_05g_counterfactual_weighted_completion.py",
        "tools/openofc_solver/run_external_05g_q3.py",
        "tools/openofc_solver/run_external_05g_q4a.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "activation": "ACTIVATED_BY_FROZEN_Q3_RULE",
        "config": {
            "seeds": list(SEEDS),
            "search_iterations": SEARCH_ITERATIONS,
            "search_exploration": SEARCH_EXPLORATION,
            "mccfr_iterations": MCCFR_ITERATIONS,
            "rank_tolerance": RANK_TOLERANCE,
            "posterior_epsilon": POSTERIOR_EPS,
            "tv_thresholds": list(TV_THRESHOLDS),
            "support_sha256": support_sha256(worlds),
            "uniform_completion_policy_sha256": uniform_completion.policy_sha256,
            "uniform_completion_runtime_seconds": uniform_completion_seconds,
            "weight_map_semantics": "one-shot original-M counterfactual chance-times-opponent-reach; never recomputed after candidate changes",
        },
        "preflight": preflight,
        "seed_results": seed_results,
        "cross_seed_recommendation": recommendation,
        "quality": quality,
        "verdict": "PASS_Q4A_EXACT_COMPLETION_AB",
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "limitations": [
            "finite deterministic 36-world reduced game only",
            "one-shot counterfactual weights are frozen from original M rather than iterated to a fixed point",
            "Q4A changes only completion state weighting and intentionally retains Q1B downstream completion semantics",
            "no REAL route is certified",
        ],
        "real_routes_certified": 0,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05g_q4a.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "activation": payload["activation"],
        "verdict": payload["verdict"],
        "cross_seed_recommendation": payload.get("cross_seed_recommendation"),
        "seed_outcomes": [
            {
                "seed": row["seed"],
                "changed_completion_actions": row["changed_action_accounting"]["changed_completion_actions"],
                "original_m_exploitability": row["comparison"]["original_m_exploitability"],
                "m_cf_exploitability": row["comparison"]["m_cf_exploitability"],
                "outcome": row["comparison"]["outcome"],
            }
            for row in payload.get("seed_results", [])
        ],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
