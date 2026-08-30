from __future__ import annotations

"""06P3 reduced-game audit of observable irrecoverable-foul action pruning."""

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

from engine import (
    Board,
    ROW_TOP,
    ROW_MIDDLE,
    ROW_BOTTOM,
    _candidate_row_resolutions,
    resolve_board,
)
from external_05g_broad_support import (
    broad_worlds,
    public_pre_r3_state,
    validate_broad_physical_support,
)
from external_05g_uniform_backward_completion import build_uniform_local_backward_completion
from external_hidden_discard_overlap_strategic import (
    OverlapExternalSamplingMCCFR,
    ReachableSupport,
    build_reachable_support,
)
from strategic_cfr import child_state, legal_action_pairs
from run_external_05g_q0b import _support_maps, _validate_profile
from run_external_05g_q1a import _profile_sha256
from run_external_05g_q1b import _assemble_completed, _materialize_completion_profile
from run_external_05g_q2 import _evaluate_profile

EXPERIMENT_ID = "EXT-06P3-IRRECOVERABLE-FOUL-PRUNING-AUDIT"
AUTHORITY = "REDUCED_GAME_PRUNING_SAFETY_AUDIT_ONLY"
SEEDS = (20260829, 20260830)
MCCFR_ITERATIONS = 1_024
TOLERANCE = 1e-9
ZERO_MASS_THRESHOLD = 1e-12
LOW_COST_EXPLOITABILITY_DELTA = 1e-4
EXPECTED_WORLDS = 36
EXPECTED_INFOSETS = 69_828
EXPECTED_NONROOT = 69_825
EXPECTED_AMBIGUOUS_NONROOT = 15_393
EXPECTED_ROOTS = 3


@lru_cache(maxsize=None)
def _row_rank_options(row: tuple) -> tuple:
    return tuple(rank for rank, _resolved in _candidate_row_resolutions(row))


def _complete_pair_compatible(stronger_row: tuple, weaker_row: tuple) -> bool:
    """Whether some row-local Joker resolutions permit stronger >= weaker."""
    stronger = _row_rank_options(stronger_row)
    weaker = _row_rank_options(weaker_row)
    return any(strong >= weak for strong in stronger for weak in weaker)


def irrecoverable_ordering_foul(board: Board) -> bool:
    """True only when already-complete frozen rows make a valid board impossible."""
    top, middle, bottom = board.rows()
    if board.complete():
        return resolve_board(board) is None
    if len(top) == 3 and len(middle) == 5:
        if not _complete_pair_compatible(tuple(middle), tuple(top)):
            return True
    if len(middle) == 5 and len(bottom) == 5:
        if not _complete_pair_compatible(tuple(bottom), tuple(middle)):
            return True
    return False


def _classify_support(support_rows: tuple[ReachableSupport, ...]) -> tuple[dict[str, frozenset[str]], dict]:
    prunable: dict[str, frozenset[str]] = {}
    by_layer: dict[str, dict[str, int]] = defaultdict(lambda: {
        "information_states": 0,
        "legal_actions": 0,
        "infosets_with_prunable_actions": 0,
        "prunable_actions": 0,
    })
    classification_invariance_checks = 0
    classification_disagreements = 0

    for row in support_rows:
        layer = f"R{row.round_index}_P{row.actor}"
        bucket = by_layer[layer]
        bucket["information_states"] += 1
        bucket["legal_actions"] += len(row.action_keys)

        first_state = row.concrete_states[0]
        first_pairs = dict(legal_action_pairs(first_state))
        if set(first_pairs) != set(row.action_keys):
            raise AssertionError("06P3 support/action mismatch on first concrete state")
        row_prunable: set[str] = set()
        first_labels: dict[str, bool] = {}
        for action_key in row.action_keys:
            child = child_state(first_state, first_pairs[action_key])
            label = irrecoverable_ordering_foul(child.boards[row.actor])
            first_labels[action_key] = label
            if label:
                row_prunable.add(action_key)

        # The label may use only the actor-visible board/incoming/action. Verify
        # this explicitly over every hidden concrete state in the infoset.
        for state in row.concrete_states[1:]:
            pairs = dict(legal_action_pairs(state))
            if set(pairs) != set(row.action_keys):
                raise AssertionError("06P3 support/action mismatch across concrete states")
            for action_key in row.action_keys:
                child = child_state(state, pairs[action_key])
                label = irrecoverable_ordering_foul(child.boards[row.actor])
                classification_invariance_checks += 1
                if label != first_labels[action_key]:
                    classification_disagreements += 1

        if row_prunable:
            bucket["infosets_with_prunable_actions"] += 1
            bucket["prunable_actions"] += len(row_prunable)
            prunable[row.information_state_key] = frozenset(row_prunable)

    total_actions = sum(bucket["legal_actions"] for bucket in by_layer.values())
    total_prunable = sum(bucket["prunable_actions"] for bucket in by_layer.values())
    affected_infosets = sum(bucket["infosets_with_prunable_actions"] for bucket in by_layer.values())
    return prunable, {
        "total_information_states": len(support_rows),
        "total_legal_actions": total_actions,
        "prunable_actions": total_prunable,
        "prunable_action_fraction": total_prunable / total_actions if total_actions else 0.0,
        "infosets_with_prunable_actions": affected_infosets,
        "infoset_affected_fraction": affected_infosets / len(support_rows) if support_rows else 0.0,
        "by_layer": {key: by_layer[key] for key in sorted(by_layer)},
        "classification_invariance_checks": classification_invariance_checks,
        "classification_disagreements": classification_disagreements,
        "classification_invariant": classification_disagreements == 0,
        "row_rank_cache": {
            "hits": _row_rank_options.cache_info().hits,
            "misses": _row_rank_options.cache_info().misses,
            "currsize": _row_rank_options.cache_info().currsize,
        },
    }


def _profile_prunable_mass(profile: dict[str, dict[str, float]], prunable: dict[str, frozenset[str]]) -> dict:
    by_layer = defaultdict(lambda: {
        "rows_with_prunable_actions": 0,
        "rows_with_positive_prunable_mass": 0,
        "prunable_probability_mass_sum": 0.0,
        "max_row_prunable_probability_mass": 0.0,
    })
    row_masses = []
    for info_key, action_keys in prunable.items():
        distribution = profile[info_key]
        mass = sum(float(distribution[action]) for action in action_keys)
        row_masses.append(mass)
        payload = json.loads(info_key)
        layer = f"R{int(payload['round'])}_P{int(payload['player'])}"
        bucket = by_layer[layer]
        bucket["rows_with_prunable_actions"] += 1
        bucket["prunable_probability_mass_sum"] += mass
        bucket["max_row_prunable_probability_mass"] = max(
            bucket["max_row_prunable_probability_mass"], mass
        )
        if mass > 0.0:
            bucket["rows_with_positive_prunable_mass"] += 1
    return {
        "rows_with_prunable_actions": len(row_masses),
        "rows_with_positive_prunable_mass": sum(mass > 0.0 for mass in row_masses),
        "prunable_probability_mass_sum": sum(row_masses),
        "mean_row_prunable_probability_mass": (
            sum(row_masses) / len(row_masses) if row_masses else 0.0
        ),
        "max_row_prunable_probability_mass": max(row_masses, default=0.0),
        "by_layer": {key: by_layer[key] for key in sorted(by_layer)},
    }


def _prune_profile(
    profile: dict[str, dict[str, float]],
    prunable: dict[str, frozenset[str]],
) -> tuple[dict[str, dict[str, float]], dict]:
    out: dict[str, dict[str, float]] = {}
    changed_rows = 0
    fallback_rows = 0
    for info_key, distribution in profile.items():
        banned = prunable.get(info_key, frozenset())
        if not banned:
            out[info_key] = {action: float(prob) for action, prob in distribution.items()}
            continue
        survivor_mass = sum(
            float(prob) for action, prob in distribution.items() if action not in banned
        )
        if survivor_mass <= 0.0:
            fallback_rows += 1
            out[info_key] = {action: float(prob) for action, prob in distribution.items()}
            continue
        candidate = {
            action: 0.0 if action in banned else float(prob) / survivor_mass
            for action, prob in distribution.items()
        }
        if any(abs(candidate[action] - float(distribution[action])) > 0.0 for action in distribution):
            changed_rows += 1
        out[info_key] = candidate
    return out, {
        "changed_distribution_rows": changed_rows,
        "zero_survivor_fallback_rows": fallback_rows,
    }


def _validation_pass(validation: dict) -> bool:
    return all(
        validation[field] == 0
        for field in (
            "illegal_key_count",
            "action_set_mismatch_count",
            "invalid_distribution_count",
            "hidden_world_token_leakage_count",
        )
    )


def run() -> dict:
    worlds = broad_worlds()
    base_state = public_pre_r3_state()
    validate_broad_physical_support(base_state, worlds)
    support_rows = build_reachable_support(base_state, worlds)
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)
    geometry_exact = (
        len(worlds) == EXPECTED_WORLDS
        and len(support_rows) == EXPECTED_INFOSETS
        and len(nonroot_keys) == EXPECTED_NONROOT
        and len(ambiguous_nonroot_keys) == EXPECTED_AMBIGUOUS_NONROOT
        and len(root_keys) == EXPECTED_ROOTS
    )

    completion = build_uniform_local_backward_completion(support_rows)
    completion_profile = _materialize_completion_profile(support_rows, completion.choice_map())
    prunable, pruning_geometry = _classify_support(support_rows)

    world_ids = tuple(world.world_id for world in worlds)
    seed_results = []
    for seed in SEEDS:
        solver = OverlapExternalSamplingMCCFR(base_state, worlds, seed=seed)
        solver.run(MCCFR_ITERATIONS)
        native = solver.current_profile()
        original, source_map = _assemble_completed(
            mode="M",
            support_rows=support_rows,
            search={},
            mccfr=native,
            completion=completion_profile,
        )
        pruned, pruning_effect = _prune_profile(original, prunable)

        original_validation = _validate_profile(original, support_by_key, world_ids)
        pruned_validation = _validate_profile(pruned, support_by_key, world_ids)
        original_eval = _evaluate_profile(
            name="M",
            profile=original,
            base_state=base_state,
            worlds=worlds,
            support_rows=support_rows,
        )
        pruned_eval = _evaluate_profile(
            name="M_PRUNED",
            profile=pruned,
            base_state=base_state,
            worlds=worlds,
            support_rows=support_rows,
        )
        mass = _profile_prunable_mass(original, prunable)
        exploitability_delta = pruned_eval["exploitability"] - original_eval["exploitability"]
        seed_pass = (
            set(original) == set(support_by_key)
            and set(pruned) == set(support_by_key)
            and _validation_pass(original_validation)
            and _validation_pass(pruned_validation)
            and original_eval["profile_pass"]
            and pruned_eval["profile_pass"]
            and math.isfinite(exploitability_delta)
        )
        seed_results.append({
            "seed": seed,
            "native_information_states": len(native),
            "source_counts": dict(Counter(source_map.values())),
            "original_profile_sha256": _profile_sha256(original),
            "pruned_profile_sha256": _profile_sha256(pruned),
            "prunable_mass": mass,
            "pruning_effect": pruning_effect,
            "original_evaluation": {
                "exploitability": original_eval["exploitability"],
                "nash_conv": original_eval["nash_conv"],
                "br0_value": original_eval["br0"]["value"],
                "br1_value": original_eval["br1"]["value"],
                "profile_pass": original_eval["profile_pass"],
            },
            "pruned_evaluation": {
                "exploitability": pruned_eval["exploitability"],
                "nash_conv": pruned_eval["nash_conv"],
                "br0_value": pruned_eval["br0"]["value"],
                "br1_value": pruned_eval["br1"]["value"],
                "profile_pass": pruned_eval["profile_pass"],
            },
            "exploitability_delta_pruned_minus_original": exploitability_delta,
            "original_validation": original_validation,
            "pruned_validation": pruned_validation,
            "seed_pass": seed_pass,
        })

    mechanical = (
        geometry_exact
        and pruning_geometry["classification_invariant"]
        and len(seed_results) == 2
        and all(row["seed_pass"] for row in seed_results)
    )
    high_confidence = mechanical and all(
        row["pruning_effect"]["zero_survivor_fallback_rows"] == 0
        and row["prunable_mass"]["prunable_probability_mass_sum"] <= ZERO_MASS_THRESHOLD
        and row["exploitability_delta_pruned_minus_original"] <= TOLERANCE
        for row in seed_results
    )
    low_cost = mechanical and all(
        row["pruning_effect"]["zero_survivor_fallback_rows"] == 0
        and row["exploitability_delta_pruned_minus_original"] <= LOW_COST_EXPLOITABILITY_DELTA
        for row in seed_results
    )
    if not mechanical:
        verdict = "FAIL_06P3_PRUNING_AUDIT_MECHANICS"
        interpretation = "REPAIR_MECHANICS_WITHOUT_CHANGING_FROZEN_PRUNING_RULE"
    elif high_confidence:
        verdict = "PASS_06P3_IRRECOVERABLE_FOUL_PRUNING_AUDIT"
        interpretation = "HIGH_CONFIDENCE_IRRECOVERABLE_FOUL_PRUNING_CANDIDATE"
    elif low_cost:
        verdict = "PASS_06P3_IRRECOVERABLE_FOUL_PRUNING_AUDIT"
        interpretation = "EMPIRICALLY_LOW_COST_FOUL_PRUNING_CANDIDATE_NEEDS_BROADER_AB"
    else:
        verdict = "PASS_06P3_IRRECOVERABLE_FOUL_PRUNING_AUDIT"
        interpretation = "DO_NOT_PROMOTE_FOUL_PRUNING_YET"

    payload = {
        "schema": "openofc-external-06p3-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "frozen": {
            "seeds": list(SEEDS),
            "mccfr_iterations": MCCFR_ITERATIONS,
            "zero_mass_threshold": ZERO_MASS_THRESHOLD,
            "exploitability_tolerance": TOLERANCE,
            "low_cost_exploitability_delta": LOW_COST_EXPLOITABILITY_DELTA,
            "pruning_rule": "COMPLETE_ADJACENT_ROWS_WITH_NO_VALID_ORDERING_RESOLUTION",
        },
        "geometry": {
            "worlds": len(worlds),
            "information_states": len(support_rows),
            "nonroot_information_states": len(nonroot_keys),
            "ambiguous_nonroot_information_states": len(ambiguous_nonroot_keys),
            "root_information_states": len(root_keys),
            "exact": geometry_exact,
        },
        "pruning_geometry": pruning_geometry,
        "seed_results": seed_results,
        "quality": {
            "mechanical_pass": mechanical,
            "geometry_exact": geometry_exact,
            "classification_invariant_across_hidden_states": pruning_geometry["classification_invariant"],
            "both_seed_profiles_and_exact_br_pass": len(seed_results) == 2 and all(row["seed_pass"] for row in seed_results),
            "no_external_heuristic_weights_imported": True,
            "no_retraining_after_pruning": True,
            "real_routes_certified_zero": True,
        },
        "verdict": verdict,
        "interpretation": interpretation,
        "real_routes_certified": 0,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    if not mechanical:
        raise RuntimeError(json.dumps({
            "experiment_id": EXPERIMENT_ID,
            "verdict": verdict,
            "quality": payload["quality"],
        }, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_06p3.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "interpretation": payload["interpretation"],
        "pruning_geometry": payload["pruning_geometry"],
        "seeds": [
            {
                "seed": row["seed"],
                "prunable_mass_sum": row["prunable_mass"]["prunable_probability_mass_sum"],
                "changed_rows": row["pruning_effect"]["changed_distribution_rows"],
                "fallback_rows": row["pruning_effect"]["zero_survivor_fallback_rows"],
                "original_exploitability": row["original_evaluation"]["exploitability"],
                "pruned_exploitability": row["pruned_evaluation"]["exploitability"],
                "delta": row["exploitability_delta_pruned_minus_original"],
            }
            for row in payload["seed_results"]
        ],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
