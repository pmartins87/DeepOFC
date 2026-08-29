from __future__ import annotations

"""Run 05G-Q1B explicit source-labelled completion gate.

Q1B builds the learner-independent COMPLETION_UNIFORM_LOCAL_BACKWARD_V1 policy
once, then uses it only at native holes in S/M/H profiles.  It performs no exact
profile EV, best response, NashConv, exploitability, or strategic ranking.
"""

import argparse
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
from external_05g_uniform_backward_completion import (
    SOURCE_LABEL as COMPLETION_SOURCE,
    build_uniform_local_backward_completion,
)
from external_hidden_discard_overlap import run_overlap_infoset_uct
from external_hidden_discard_overlap_strategic import (
    OverlapExternalSamplingMCCFR,
    ReachableSupport,
    build_reachable_support,
    visit_profile_from_overlap_search,
)
from run_external_05g_q0b import _support_maps, _validate_profile
from run_external_05g_q1a import (
    MCCFR_ITERATIONS,
    MCCFR_NATIVE,
    SEARCH_EXPLORATION,
    SEARCH_ITERATIONS,
    SEARCH_NATIVE,
    SEEDS,
    _profile_sha256,
    _source_map_sha256,
)

EXPERIMENT_ID = "EXT-05G-Q1B-EXPLICIT-UNIFORM-BACKWARD-COMPLETION"

BehaviorProfile = Mapping[str, Mapping[str, float]]


def _materialize_completion_profile(
    support_rows: Sequence[ReachableSupport],
    choices: Mapping[str, str],
) -> dict[str, dict[str, float]]:
    profile: dict[str, dict[str, float]] = {}
    for row in support_rows:
        selected = choices.get(row.information_state_key)
        if selected is None or selected not in row.action_keys:
            raise AssertionError("completion missing legal choice for reachable infoset")
        profile[row.information_state_key] = {
            action_key: 1.0 if action_key == selected else 0.0
            for action_key in row.action_keys
        }
    return profile


def _completed_accounting(
    source_map: Mapping[str, str],
    support_rows: Sequence[ReachableSupport],
) -> dict:
    allowed = (SEARCH_NATIVE, MCCFR_NATIVE, COMPLETION_SOURCE)
    exhaustive = {row.information_state_key for row in support_rows}
    if set(source_map) != exhaustive:
        raise AssertionError("completed source map must cover exhaustive support")
    if any(label not in allowed for label in source_map.values()):
        raise AssertionError("completed source map contains undeclared label")

    counts = {label: 0 for label in allowed}
    by_layer: dict[str, dict[str, int]] = {}
    ambiguous = {label: 0 for label in allowed}
    for row in support_rows:
        label = source_map[row.information_state_key]
        counts[label] += 1
        layer = f"R{row.round_index}_P{row.actor}"
        bucket = by_layer.setdefault(layer, {name: 0 for name in allowed})
        bucket[label] += 1
        if (row.round_index, row.actor) != (3, 0) and len(row.concrete_states) > 1:
            ambiguous[label] += 1
    return {
        "exhaustive_information_states": len(support_rows),
        "counts": counts,
        "percentages": {label: counts[label] / len(support_rows) for label in allowed},
        "counts_by_layer": {layer: by_layer[layer] for layer in sorted(by_layer)},
        "ambiguous_nonroot_counts": ambiguous,
        "completion_states_actually_used": counts[COMPLETION_SOURCE],
        "source_map_sha256": _source_map_sha256(source_map),
    }


def _assemble_completed(
    *,
    mode: str,
    support_rows: Sequence[ReachableSupport],
    search: BehaviorProfile,
    mccfr: BehaviorProfile,
    completion: BehaviorProfile,
) -> tuple[dict[str, dict[str, float]], dict[str, str]]:
    if mode not in {"S", "M", "H"}:
        raise ValueError("completion mode must be S/M/H")
    out: dict[str, dict[str, float]] = {}
    source: dict[str, str] = {}
    for row in support_rows:
        key = row.information_state_key
        if mode in {"S", "H"} and key in search:
            dist = search[key]
            label = SEARCH_NATIVE
        elif mode in {"M", "H"} and key in mccfr:
            dist = mccfr[key]
            label = MCCFR_NATIVE
        else:
            dist = completion[key]
            label = COMPLETION_SOURCE
        out[key] = {action: float(prob) for action, prob in dist.items()}
        source[key] = label
    return out, source


def _native_preservation_checks(
    *,
    mode: str,
    profile: BehaviorProfile,
    source_map: Mapping[str, str],
    search: BehaviorProfile,
    mccfr: BehaviorProfile,
) -> dict:
    if mode == "S":
        search_keys = set(search)
        mccfr_expected: set[str] = set()
    elif mode == "M":
        search_keys = set()
        mccfr_expected = set(mccfr)
    elif mode == "H":
        search_keys = set(search)
        mccfr_expected = set(mccfr) - set(search)
    else:
        raise ValueError(mode)

    search_ok = all(
        source_map[key] == SEARCH_NATIVE
        and dict(profile[key]) == {action: float(prob) for action, prob in search[key].items()}
        for key in search_keys
    )
    mccfr_ok = all(
        source_map[key] == MCCFR_NATIVE
        and dict(profile[key]) == {action: float(prob) for action, prob in mccfr[key].items()}
        for key in mccfr_expected
    )
    completion_only_in_holes = all(
        not (
            source_map[key] == COMPLETION_SOURCE
            and (
                (mode in {"S", "H"} and key in search)
                or (mode in {"M", "H"} and key in mccfr and not (mode == "H" and key in search))
            )
        )
        for key in source_map
    )
    h_priority = True
    if mode == "H":
        h_priority = all(source_map[key] == SEARCH_NATIVE for key in set(search) & set(mccfr))

    return {
        "search_native_preserved_exactly": search_ok,
        "mccfr_native_preserved_exactly": mccfr_ok,
        "completion_only_in_native_holes": completion_only_in_holes,
        "search_priority_preserved": h_priority,
    }


def _replay_hash(profile_sha: str, source_sha: str, completion_sha: str) -> str:
    return hashlib.sha256(f"{profile_sha}|{source_sha}|{completion_sha}".encode("ascii")).hexdigest()


def _run_seed(
    *,
    seed: int,
    base_state,
    worlds,
    support_rows: Sequence[ReachableSupport],
    support_by_key: Mapping[str, ReachableSupport],
    completion_profile: BehaviorProfile,
    completion_sha: str,
) -> dict:
    world_ids = tuple(world.world_id for world in worlds)

    t0 = perf_counter()
    search_result = run_overlap_infoset_uct(
        base_state,
        worlds,
        iterations=SEARCH_ITERATIONS,
        seed=seed,
        exploration=SEARCH_EXPLORATION,
    )
    search = visit_profile_from_overlap_search(search_result)
    search_seconds = perf_counter() - t0

    t1 = perf_counter()
    mccfr_solver = OverlapExternalSamplingMCCFR(base_state, worlds, seed=seed)
    mccfr_solver.run(MCCFR_ITERATIONS)
    mccfr = mccfr_solver.current_profile()
    mccfr_seconds = perf_counter() - t1

    native_validation = {
        "search": _validate_profile(search, support_by_key, world_ids),
        "mccfr": _validate_profile(mccfr, support_by_key, world_ids),
    }

    profiles = {}
    all_modes_pass = True
    for mode, name in (("S", "S_complete"), ("M", "M_complete"), ("H", "H_complete")):
        profile, source_map = _assemble_completed(
            mode=mode,
            support_rows=support_rows,
            search=search,
            mccfr=mccfr,
            completion=completion_profile,
        )
        validation = _validate_profile(profile, support_by_key, world_ids)
        accounting = _completed_accounting(source_map, support_rows)
        preservation = _native_preservation_checks(
            mode=mode,
            profile=profile,
            source_map=source_map,
            search=search,
            mccfr=mccfr,
        )
        profile_sha = _profile_sha256(profile)
        source_sha = accounting["source_map_sha256"]
        complete = len(profile) == len(support_rows) and set(profile) == set(support_by_key)
        validation_pass = all(
            validation[field] == 0
            for field in (
                "illegal_key_count",
                "action_set_mismatch_count",
                "invalid_distribution_count",
                "hidden_world_token_leakage_count",
            )
        )
        arithmetic_pass = sum(accounting["counts"].values()) == len(support_rows)
        mode_pass = all((
            complete,
            validation_pass,
            arithmetic_pass,
            preservation["search_native_preserved_exactly"],
            preservation["mccfr_native_preserved_exactly"],
            preservation["completion_only_in_native_holes"],
            preservation["search_priority_preserved"],
        ))
        all_modes_pass = all_modes_pass and mode_pass
        profiles[name] = {
            "complete_100pct": complete,
            "profile_sha256": profile_sha,
            "source_map_sha256": source_sha,
            "completion_policy_sha256": completion_sha,
            "replay_sha256": _replay_hash(profile_sha, source_sha, completion_sha),
            "accounting": accounting,
            "validation": validation,
            "native_preservation": preservation,
            "mode_pass": mode_pass,
        }

    native_validation_pass = all(
        validation[field] == 0
        for validation in native_validation.values()
        for field in (
            "illegal_key_count",
            "action_set_mismatch_count",
            "invalid_distribution_count",
            "hidden_world_token_leakage_count",
        )
    )

    return {
        "seed": seed,
        "native_budgets": {
            "search_iterations": SEARCH_ITERATIONS,
            "search_exploration": SEARCH_EXPLORATION,
            "mccfr_iterations": MCCFR_ITERATIONS,
        },
        "native_runtime_seconds": {"search": search_seconds, "mccfr": mccfr_seconds},
        "native_profile_sha256": {
            "search": _profile_sha256(search),
            "mccfr": _profile_sha256(mccfr),
        },
        "native_information_states": {"search": len(search), "mccfr": len(mccfr)},
        "native_validation": native_validation,
        "profiles": profiles,
        "seed_pass": native_validation_pass and all_modes_pass,
    }


def run() -> dict:
    worlds = broad_worlds()
    base_state = public_pre_r3_state()
    validate_broad_physical_support(base_state, worlds)
    support_rows = build_reachable_support(base_state, worlds)
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)
    if len(worlds) != 36 or len(root_keys) != 3:
        raise RuntimeError("05G frozen support geometry changed")

    t0 = perf_counter()
    completion = build_uniform_local_backward_completion(support_rows)
    completion_seconds = perf_counter() - t0
    choices = completion.choice_map()
    completion_profile = _materialize_completion_profile(support_rows, choices)
    completion_validation = _validate_profile(
        completion_profile,
        support_by_key,
        tuple(world.world_id for world in worlds),
    )
    completion_pure = all(
        sum(1 for probability in dist.values() if probability == 1.0) == 1
        and all(probability in (0.0, 1.0) for probability in dist.values())
        for dist in completion_profile.values()
    )
    completion_complete = set(completion_profile) == set(support_by_key)
    completion_validation_pass = all(
        completion_validation[field] == 0
        for field in (
            "illegal_key_count",
            "action_set_mismatch_count",
            "invalid_distribution_count",
            "hidden_world_token_leakage_count",
        )
    )

    seed_results = [
        _run_seed(
            seed=seed,
            base_state=base_state,
            worlds=worlds,
            support_rows=support_rows,
            support_by_key=support_by_key,
            completion_profile=completion_profile,
            completion_sha=completion.policy_sha256,
        )
        for seed in SEEDS
    ]

    completion_shas_used = {
        profile["completion_policy_sha256"]
        for row in seed_results
        for profile in row["profiles"].values()
    }
    quality = {
        "support_36_worlds": len(worlds) == 36,
        "completion_covers_exhaustive_support": completion_complete,
        "completion_choices_legal_normalized_pure": completion_validation_pass and completion_pure,
        "completion_single_seed_independent_sha": completion_shas_used == {completion.policy_sha256},
        "both_seeds_all_profiles_pass": len(seed_results) == 2 and all(row["seed_pass"] for row in seed_results),
        "all_s_m_h_profiles_100pct_complete": all(
            profile["complete_100pct"]
            for row in seed_results
            for profile in row["profiles"].values()
        ),
        "no_exact_profile_ev_used": True,
        "no_best_response_used": True,
        "no_strength_winner_claim": True,
    }
    passed = all(quality.values())

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05G_BROAD_HIDDEN_INFORMATION_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q1A_NATIVE_PROVENANCE_ROUTER_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q1B_UNIFORM_BACKWARD_COMPLETION_CONTRACT.md",
        "tools/openofc_solver/external_05g_broad_support.py",
        "tools/openofc_solver/external_05g_uniform_backward_completion.py",
        "tools/openofc_solver/external_hidden_discard_overlap.py",
        "tools/openofc_solver/external_hidden_discard_overlap_strategic.py",
        "tools/openofc_solver/run_external_05g_q1a.py",
        "tools/openofc_solver/run_external_05g_q1b.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "explicit-source-labelled-uniform-backward-completion",
        "config": {
            "seeds": list(SEEDS),
            "search_iterations": SEARCH_ITERATIONS,
            "search_exploration": SEARCH_EXPLORATION,
            "mccfr_iterations": MCCFR_ITERATIONS,
            "completion_source": COMPLETION_SOURCE,
            "support_worlds": len(worlds),
            "support_sha256": support_sha256(worlds),
        },
        "exhaustive_support": {
            "reachable_information_states": len(support_rows),
            "nonroot_information_states": len(nonroot_keys),
            "ambiguous_nonroot_information_states": len(ambiguous_nonroot_keys),
            "root_information_states": len(root_keys),
        },
        "completion_build": {
            "source_label": completion.source_label,
            "information_states": completion.information_states,
            "terminal_evaluations": completion.terminal_evaluations,
            "rollout_cache_entries": completion.rollout_cache_entries,
            "layer_counts": list(completion.layer_counts),
            "policy_sha256": completion.policy_sha256,
            "runtime_seconds": completion_seconds,
            "validation": completion_validation,
        },
        "seed_results": seed_results,
        "quality": quality,
        "verdict": "PASS_EXPLICIT_COMPLETION" if passed else "BLOCK_EXPLICIT_COMPLETION",
        "promotion_recommendation": "CONTINUE_TO_Q1C_FIXED_PROFILE_EV" if passed else "FIX_Q1B_TECHNICAL_DEFECT_WITHOUT_CHANGING_COMPLETION_SEMANTICS",
        "limitations": [
            "uniform compatible-state completion is a declared baseline belief model, not a strategic posterior",
            "Q1B computes no exact profile EV and no equilibrium-quality ranking",
            "finite reduced 36-world game only",
            "no REAL route is certified",
        ],
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "real_routes_certified": 0,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    if not passed:
        raise RuntimeError(f"05G-Q1B failed: {quality}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05g_q1b.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "completion_policy_sha256": payload["completion_build"]["policy_sha256"],
        "completion_terminal_evaluations": payload["completion_build"]["terminal_evaluations"],
        "seed_summaries": [
            {
                "seed": row["seed"],
                "S_completion_used": row["profiles"]["S_complete"]["accounting"]["completion_states_actually_used"],
                "M_completion_used": row["profiles"]["M_complete"]["accounting"]["completion_states_actually_used"],
                "H_completion_used": row["profiles"]["H_complete"]["accounting"]["completion_states_actually_used"],
                "S_profile_sha256": row["profiles"]["S_complete"]["profile_sha256"],
                "M_profile_sha256": row["profiles"]["M_complete"]["profile_sha256"],
                "H_profile_sha256": row["profiles"]["H_complete"]["profile_sha256"],
            }
            for row in payload["seed_results"]
        ],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
