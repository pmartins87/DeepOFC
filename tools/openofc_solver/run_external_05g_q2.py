from __future__ import annotations

"""Run 05G-Q2 exact bilateral best response and reduced-fixture ranking."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
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
    build_uniform_local_backward_completion,
    completion_policy_sha256,
)
from external_hidden_discard_overlap_strategic import (
    ReachableSupport,
    build_reachable_support,
    exact_nash_conv,
)
from run_external_05g_q0b import _support_maps, _validate_profile
from run_external_05g_q1a import MCCFR_ITERATIONS, SEARCH_EXPLORATION, SEARCH_ITERATIONS, SEEDS
from run_external_05g_q1b import _materialize_completion_profile
from run_external_05g_q1c import PROFILE_NAMES, _exact_asymmetric_value, _materialize_seed_profiles

EXPERIMENT_ID = "EXT-05G-Q2-EXACT-BILATERAL-BEST-RESPONSE"
RANK_TOLERANCE = 1e-9

BehaviorProfile = Mapping[str, Mapping[str, float]]


def _br_behavior_profile(
    support_rows: Sequence[ReachableSupport],
    *,
    player: int,
    choices: Mapping[str, str],
) -> dict[str, dict[str, float]]:
    expected = {
        row.information_state_key: row
        for row in support_rows
        if row.actor == player
    }
    if set(choices) != set(expected):
        raise AssertionError("BR choice map does not cover every responder infoset")
    profile = {}
    for key, row in expected.items():
        selected = choices[key]
        if selected not in row.action_keys:
            raise AssertionError("BR selected illegal action")
        profile[key] = {
            action_key: 1.0 if action_key == selected else 0.0
            for action_key in row.action_keys
        }
    return profile


def _evaluate_profile(
    *,
    name: str,
    profile: BehaviorProfile,
    base_state,
    worlds,
    support_rows: Sequence[ReachableSupport],
) -> dict:
    t0 = perf_counter()
    nash = exact_nash_conv(
        base_state,
        worlds,
        profile=profile,
        support_rows=support_rows,
    )
    runtime = perf_counter() - t0

    br0_choices = nash.br0.choice_map()
    br1_choices = nash.br1.choice_map()
    br0_profile = _br_behavior_profile(support_rows, player=0, choices=br0_choices)
    br1_profile = _br_behavior_profile(support_rows, player=1, choices=br1_choices)

    br0_replay = _exact_asymmetric_value(
        base_state,
        worlds,
        p0_profile=br0_profile,
        p1_profile=profile,
    )
    br1_replay = _exact_asymmetric_value(
        base_state,
        worlds,
        p0_profile=profile,
        p1_profile=br1_profile,
    )
    br0_error = abs(br0_replay["expected_u0"] - nash.br0.value)
    br1_error = abs((-br1_replay["expected_u0"]) - nash.br1.value)

    responder0_expected = sum(1 for row in support_rows if row.actor == 0)
    responder1_expected = sum(1 for row in support_rows if row.actor == 1)
    coverage_pass = (
        len(br0_choices) == responder0_expected
        and len(br1_choices) == responder1_expected
        and nash.br0.round3_infosets + nash.br0.round4_infosets == responder0_expected
        and nash.br1.round3_infosets + nash.br1.round4_infosets == responder1_expected
    )
    replay_pass = (
        br0_replay["missing_profile_lookups"] == 0
        and br1_replay["missing_profile_lookups"] == 0
        and br0_error <= RANK_TOLERANCE
        and br1_error <= RANK_TOLERANCE
    )
    finite_pass = all(math.isfinite(value) for value in (
        nash.br0.value,
        nash.br1.value,
        nash.nash_conv,
        nash.exploitability,
    ))

    return {
        "profile": name,
        "br0": {
            "value": nash.br0.value,
            "round3_infosets": nash.br0.round3_infosets,
            "round4_infosets": nash.br0.round4_infosets,
            "terminal_leaves": nash.br0.terminal_leaves,
            "choice_sha256": completion_policy_sha256(br0_choices),
            "replay_u0": br0_replay["expected_u0"],
            "replay_absolute_error": br0_error,
        },
        "br1": {
            "value": nash.br1.value,
            "round3_infosets": nash.br1.round3_infosets,
            "round4_infosets": nash.br1.round4_infosets,
            "terminal_leaves": nash.br1.terminal_leaves,
            "choice_sha256": completion_policy_sha256(br1_choices),
            "replay_u0": br1_replay["expected_u0"],
            "replay_player1_value": -br1_replay["expected_u0"],
            "replay_absolute_error": br1_error,
        },
        "nash_conv": nash.nash_conv,
        "exploitability": nash.exploitability,
        "runtime_seconds": runtime,
        "responder_coverage_pass": coverage_pass,
        "exact_replay_pass": replay_pass,
        "finite_pass": finite_pass,
        "nonnegative_nashconv_pass": nash.nash_conv >= -RANK_TOLERANCE,
        "profile_pass": coverage_pass and replay_pass and finite_pass and nash.nash_conv >= -RANK_TOLERANCE,
    }


def _seed_ranking(rows: Sequence[dict]) -> dict:
    if {row["profile"] for row in rows} != set(PROFILE_NAMES):
        raise AssertionError("seed ranking requires S/M/H exactly once")
    values = {row["profile"]: float(row["exploitability"]) for row in rows}
    ordered = sorted(values, key=lambda name: (values[name], name))
    best = ordered[0]
    strict = all(values[best] + RANK_TOLERANCE < values[other] for other in ordered[1:])
    tied_with_best = sorted(
        name for name, value in values.items()
        if abs(value - values[best]) <= RANK_TOLERANCE
    )
    return {
        "ordered_by_exploitability": ordered,
        "exploitability": values,
        "unique_winner": best if strict else None,
        "tied_with_lowest_within_tolerance": tied_with_best,
        "ranking_tolerance": RANK_TOLERANCE,
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
    completion_profile = _materialize_completion_profile(support_rows, completion.choice_map())

    seed_results = []
    world_ids = tuple(world.world_id for world in worlds)
    for seed in SEEDS:
        materialized = _materialize_seed_profiles(
            seed=seed,
            base_state=base_state,
            worlds=worlds,
            support_rows=support_rows,
            completion_profile=completion_profile,
        )
        profiles = materialized["profiles"]
        validations = {
            name: _validate_profile(profiles[name], support_by_key, world_ids)
            for name in PROFILE_NAMES
        }
        complete_and_legal = all(
            set(profiles[name]) == set(support_by_key)
            and all(
                validations[name][field] == 0
                for field in (
                    "illegal_key_count",
                    "action_set_mismatch_count",
                    "invalid_distribution_count",
                    "hidden_world_token_leakage_count",
                )
            )
            for name in PROFILE_NAMES
        )

        evaluations = [
            _evaluate_profile(
                name=name,
                profile=profiles[name],
                base_state=base_state,
                worlds=worlds,
                support_rows=support_rows,
            )
            for name in PROFILE_NAMES
        ]
        ranking = _seed_ranking(evaluations)
        seed_results.append({
            "seed": seed,
            "profile_sha256": {
                name: hashlib.sha256(
                    json.dumps(
                        {
                            key: {action: float(prob) for action, prob in sorted(profiles[name][key].items())}
                            for key in sorted(profiles[name])
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode("utf-8")
                ).hexdigest()
                for name in PROFILE_NAMES
            },
            "profile_validation": validations,
            "evaluations": evaluations,
            "ranking": ranking,
            "seed_pass": complete_and_legal and len(evaluations) == 3 and all(row["profile_pass"] for row in evaluations),
        })

    per_seed_winners = [row["ranking"]["unique_winner"] for row in seed_results]
    unique_cross_seed_winner = (
        per_seed_winners[0]
        if len(per_seed_winners) == 2
        and per_seed_winners[0] is not None
        and per_seed_winners[0] == per_seed_winners[1]
        else None
    )
    cross_seed_verdict = (
        f"UNIQUE_CROSS_SEED_REDUCED_FIXTURE_WINNER_{unique_cross_seed_winner}"
        if unique_cross_seed_winner is not None
        else "NO_UNIQUE_CROSS_SEED_WINNER"
    )

    descriptive_aggregate = {}
    for name in PROFILE_NAMES:
        values = [
            next(item for item in row["evaluations"] if item["profile"] == name)["exploitability"]
            for row in seed_results
        ]
        descriptive_aggregate[name] = {
            "mean_exploitability_descriptive_only": mean(values),
            "median_exploitability_descriptive_only": median(values),
            "not_used_to_override_cross_seed_rule": True,
        }

    quality = {
        "support_36_worlds": len(worlds) == 36,
        "completion_policy_complete": completion.information_states == len(support_rows),
        "both_seeds_pass": len(seed_results) == 2 and all(row["seed_pass"] for row in seed_results),
        "six_bilateral_profile_seed_evaluations": sum(len(row["evaluations"]) for row in seed_results) == 6,
        "all_exact_replays_agree": all(
            item["exact_replay_pass"]
            for row in seed_results
            for item in row["evaluations"]
        ),
        "all_nashconv_nonnegative": all(
            item["nonnegative_nashconv_pass"]
            for row in seed_results
            for item in row["evaluations"]
        ),
        "seeds_ranked_separately": [row["seed"] for row in seed_results] == list(SEEDS),
        "cross_seed_rule_precommitted_no_posthoc_average_winner": True,
    }
    passed = all(quality.values())

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05G_BROAD_HIDDEN_INFORMATION_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q1A_NATIVE_PROVENANCE_ROUTER_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q1B_UNIFORM_BACKWARD_COMPLETION_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q1C_FIXED_PROFILE_EV_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q2_EXACT_BILATERAL_BR_CONTRACT.md",
        "tools/openofc_solver/external_hidden_discard_overlap_strategic.py",
        "tools/openofc_solver/run_external_05g_q1c.py",
        "tools/openofc_solver/run_external_05g_q2.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "exact-bilateral-best-response-ranking-authority-reduced-fixture-only",
        "config": {
            "seeds": list(SEEDS),
            "profiles": list(PROFILE_NAMES),
            "search_iterations": SEARCH_ITERATIONS,
            "search_exploration": SEARCH_EXPLORATION,
            "mccfr_iterations": MCCFR_ITERATIONS,
            "rank_tolerance": RANK_TOLERANCE,
            "chance_worlds": len(worlds),
            "support_sha256": support_sha256(worlds),
            "completion_policy_sha256": completion.policy_sha256,
        },
        "exhaustive_support": {
            "reachable_information_states": len(support_rows),
            "nonroot_information_states": len(nonroot_keys),
            "ambiguous_nonroot_information_states": len(ambiguous_nonroot_keys),
        },
        "completion_build": {
            "runtime_seconds": completion_seconds,
            "terminal_evaluations": completion.terminal_evaluations,
            "policy_sha256": completion.policy_sha256,
        },
        "seed_results": seed_results,
        "cross_seed_ranking": {
            "per_seed_unique_winners": per_seed_winners,
            "unique_cross_seed_winner": unique_cross_seed_winner,
            "verdict": cross_seed_verdict,
            "mean_or_median_cannot_create_winner": True,
        },
        "descriptive_aggregate": descriptive_aggregate,
        "quality": quality,
        "verdict": "PASS_EXACT_BILATERAL_BR" if passed else "BLOCK_EXACT_BILATERAL_BR",
        "promotion_recommendation": (
            "PRESERVE_REDUCED_FIXTURE_WINNER_AND_CONTINUE_Q3_PLUS_BROADER_VALIDATION"
            if passed and unique_cross_seed_winner is not None
            else "CONTINUE_Q3_DIAGNOSTICS_WITHOUT_DECLARING_CROSS_SEED_WINNER"
            if passed
            else "FIX_Q2_EXACTNESS_DEFECT_WITHOUT_CHANGING_FROZEN_PROFILES_OR_RANK_RULE"
        ),
        "limitations": [
            "Q2 ranking authority is limited to the finite 36-world reduced fixture",
            "a reduced-fixture winner does not authorize production migration",
            "broader out-of-fixture validation remains mandatory",
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
        raise RuntimeError(f"05G-Q2 failed: {quality}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05g_q2.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "seed_rankings": [
            {
                "seed": row["seed"],
                "exploitability": row["ranking"]["exploitability"],
                "unique_winner": row["ranking"]["unique_winner"],
            }
            for row in payload["seed_results"]
        ],
        "cross_seed_ranking": payload["cross_seed_ranking"],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
