from __future__ import annotations

"""Run 05G-Q3 exact counterfactual posterior audit for profile M.

Q3 is diagnostic only.  It does not update a policy, compute a new best
response, re-rank S/M/H, or authorize any production/REAL route.
"""

import argparse
from collections import defaultdict
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
    SOURCE_LABEL as COMPLETION_SOURCE,
    build_uniform_local_backward_completion,
)
from external_hidden_discard_overlap import with_overlap_world
from external_hidden_discard_overlap_strategic import ReachableSupport, build_reachable_support
from strategic_cfr import HUState, child_state, information_state_key, legal_action_pairs
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

EXPERIMENT_ID = "EXT-05G-Q3-COUNTERFACTUAL-POSTERIOR-AUDIT"
PROFILE_NAME = "M"
EPS = 1e-12
TV_THRESHOLDS = (0.01, 0.05, 0.10, 0.25)
TOP_ROWS = 25
EXPECTED_INFORMATION_STATES = 69_828
EXPECTED_NONROOT_INFORMATION_STATES = 69_825
EXPECTED_AMBIGUOUS_NONROOT = 15_393
EXPECTED_ROOT_INFORMATION_STATES = 3

BehaviorProfile = Mapping[str, Mapping[str, float]]


def _layer(row: ReachableSupport) -> str:
    return f"R{row.round_index}_P{row.actor}"


def _percentile_nearest_rank(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    if not 0.0 <= q <= 1.0:
        raise ValueError(q)
    ordered = sorted(float(value) for value in values)
    rank = max(1, math.ceil(q * len(ordered)))
    return ordered[rank - 1]


def _metric_summary(rows: Sequence[dict]) -> dict:
    values = [float(row["tv_uniform_vs_counterfactual"]) for row in rows]
    masses = [float(row["counterfactual_mass"]) for row in rows]
    total_mass = sum(masses)
    return {
        "count": len(rows),
        "mean_tv": mean(values) if values else None,
        "median_tv": median(values) if values else None,
        "p95_tv_nearest_rank": _percentile_nearest_rank(values, 0.95),
        "max_tv": max(values) if values else None,
        "counterfactual_mass_weighted_mean_tv_descriptive_only": (
            sum(value * mass for value, mass in zip(values, masses)) / total_mass
            if total_mass > 0.0
            else None
        ),
        "count_above_frozen_thresholds": {
            format(threshold, ".2f"): sum(value > threshold for value in values)
            for threshold in TV_THRESHOLDS
        },
    }


def _counterfactual_state_masses(
    base_state: HUState,
    worlds,
    *,
    opponent_profile: BehaviorProfile,
    player: int,
) -> tuple[dict[str, dict[str, float]], dict]:
    """Exact chance * opponent-reach mass for every responder concrete state.

    Own actions are enumerated without multiplying by own strategy, exactly as
    required by unilateral counterfactual reach.  Opponent actions follow the
    supplied complete behavior profile.
    """

    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    chance = 1.0 / len(worlds)
    masses: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    visited_nonterminal = 0
    responder_state_visits = 0
    opponent_distribution_checks = 0
    terminal_visits = 0

    def walk(state: HUState, opponent_reach: float) -> None:
        nonlocal visited_nonterminal, responder_state_visits, opponent_distribution_checks, terminal_visits
        if state.terminal():
            terminal_visits += 1
            return
        visited_nonterminal += 1
        info_key = information_state_key(state)
        pairs = tuple(legal_action_pairs(state))
        action_keys = tuple(action_key for action_key, _action in pairs)
        by_key = dict(pairs)

        if state.actor == player:
            responder_state_visits += 1
            masses[info_key][repr(state)] += chance * opponent_reach
            for action_key in action_keys:
                walk(child_state(state, by_key[action_key]), opponent_reach)
            return

        supplied = opponent_profile.get(info_key)
        if supplied is None:
            raise ValueError("Q3 strict counterfactual traversal refuses missing opponent infoset")
        if set(supplied) != set(action_keys):
            raise ValueError("Q3 opponent profile action set mismatch")
        probs = [float(supplied[key]) for key in action_keys]
        if any((not math.isfinite(prob)) or prob < 0.0 for prob in probs):
            raise ValueError("Q3 opponent profile contains invalid probability")
        if not math.isclose(sum(probs), 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("Q3 opponent profile probability mass is not one")
        opponent_distribution_checks += 1
        for action_key, probability in zip(action_keys, probs):
            if probability <= 0.0:
                continue
            walk(child_state(state, by_key[action_key]), opponent_reach * probability)

    for world in worlds:
        walk(with_overlap_world(base_state, world), 1.0)

    normalized = {
        key: {fingerprint: float(mass) for fingerprint, mass in bucket.items()}
        for key, bucket in masses.items()
    }
    return normalized, {
        "player": player,
        "chance_worlds": len(worlds),
        "visited_nonterminal_states_with_multiplicity": visited_nonterminal,
        "responder_state_visits_with_multiplicity": responder_state_visits,
        "opponent_distribution_checks_with_multiplicity": opponent_distribution_checks,
        "terminal_visits_with_multiplicity": terminal_visits,
        "responder_information_states_with_positive_counterfactual_mass": len(normalized),
    }


def _posterior_rows(
    support_rows: Sequence[ReachableSupport],
    *,
    source_map: Mapping[str, str],
    masses_by_player: Mapping[int, Mapping[str, Mapping[str, float]]],
) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    extra_state_fingerprints = 0
    posterior_mass_failures = 0
    invalid_tv_count = 0
    invalid_mass_count = 0

    for support_row in support_rows:
        key = support_row.information_state_key
        expected_fingerprints = tuple(sorted(repr(state) for state in support_row.concrete_states))
        expected_set = set(expected_fingerprints)
        observed = dict(masses_by_player[support_row.actor].get(key, {}))
        extra = set(observed) - expected_set
        if extra:
            extra_state_fingerprints += len(extra)
        total = sum(float(observed.get(fingerprint, 0.0)) for fingerprint in expected_fingerprints)
        if not math.isfinite(total) or total < 0.0:
            invalid_mass_count += 1
            total = float("nan")

        reachable = math.isfinite(total) and total > 0.0
        k = len(expected_fingerprints)
        if k <= 0:
            raise AssertionError("support row has no concrete states")
        uniform = 1.0 / k
        tv = None
        posterior_sum = None
        positive_states = 0
        max_probability = None
        if reachable:
            posterior = [float(observed.get(fingerprint, 0.0)) / total for fingerprint in expected_fingerprints]
            if any((not math.isfinite(prob)) or prob < 0.0 for prob in posterior):
                posterior_mass_failures += 1
            posterior_sum = sum(posterior)
            if not math.isclose(posterior_sum, 1.0, rel_tol=0.0, abs_tol=EPS):
                posterior_mass_failures += 1
            tv = 0.5 * sum(abs(prob - uniform) for prob in posterior)
            if (not math.isfinite(tv)) or tv < -EPS or tv > 1.0 + EPS:
                invalid_tv_count += 1
            positive_states = sum(prob > 0.0 for prob in posterior)
            max_probability = max(posterior)

        rows.append({
            "information_state_key": key,
            "information_state_sha256": hashlib.sha256(key.encode("utf-8")).hexdigest(),
            "round_index": support_row.round_index,
            "actor": support_row.actor,
            "layer": _layer(support_row),
            "source": source_map[key],
            "concrete_states": k,
            "ambiguous": k > 1,
            "counterfactually_reachable": reachable,
            "counterfactual_mass": total if math.isfinite(total) else None,
            "posterior_probability_sum": posterior_sum,
            "positive_posterior_states": positive_states,
            "max_posterior_probability": max_probability,
            "uniform_probability_per_concrete_state": uniform,
            "tv_uniform_vs_counterfactual": tv,
        })

    diagnostics = {
        "extra_counterfactual_state_fingerprints_not_in_exhaustive_row": extra_state_fingerprints,
        "posterior_mass_failures": posterior_mass_failures,
        "invalid_tv_count": invalid_tv_count,
        "invalid_counterfactual_mass_count": invalid_mass_count,
    }
    return rows, diagnostics


def _posterior_metric_sha256(rows: Sequence[dict]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item["information_state_key"]):
        digest.update(hashlib.sha256(row["information_state_key"].encode("utf-8")).digest())
        digest.update(b"|")
        digest.update(row["source"].encode("ascii"))
        digest.update(b"|")
        digest.update(str(int(row["counterfactually_reachable"])).encode("ascii"))
        digest.update(b"|")
        mass = row["counterfactual_mass"]
        tv = row["tv_uniform_vs_counterfactual"]
        digest.update(("NA" if mass is None else format(float(mass), ".17g")).encode("ascii"))
        digest.update(b"|")
        digest.update(("NA" if tv is None else format(float(tv), ".17g")).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _seed_summary(rows: Sequence[dict]) -> dict:
    reachable = [row for row in rows if row["counterfactually_reachable"]]
    ambiguous_reachable = [row for row in reachable if row["ambiguous"]]
    completion = [row for row in rows if row["source"] == COMPLETION_SOURCE]
    completion_reachable = [row for row in completion if row["counterfactually_reachable"]]
    completion_ambiguous_reachable = [
        row for row in completion_reachable if row["ambiguous"]
    ]

    by_layer: dict[str, dict] = {}
    for layer in sorted({row["layer"] for row in rows}):
        layer_rows = [row for row in rows if row["layer"] == layer]
        layer_reachable_ambiguous = [
            row for row in layer_rows
            if row["counterfactually_reachable"] and row["ambiguous"]
        ]
        layer_completion = [row for row in layer_rows if row["source"] == COMPLETION_SOURCE]
        layer_completion_reachable_ambiguous = [
            row for row in layer_completion
            if row["counterfactually_reachable"] and row["ambiguous"]
        ]
        by_layer[layer] = {
            "information_states": len(layer_rows),
            "counterfactually_reachable": sum(row["counterfactually_reachable"] for row in layer_rows),
            "ambiguous": sum(row["ambiguous"] for row in layer_rows),
            "completion_source": len(layer_completion),
            "completion_counterfactually_reachable": sum(
                row["counterfactually_reachable"] for row in layer_completion
            ),
            "reachable_ambiguous_tv": _metric_summary(layer_reachable_ambiguous),
            "completion_reachable_ambiguous_tv": _metric_summary(layer_completion_reachable_ambiguous),
        }

    by_source: dict[str, dict] = {}
    for source in sorted({row["source"] for row in rows}):
        source_rows = [row for row in rows if row["source"] == source]
        source_reachable_ambiguous = [
            row for row in source_rows
            if row["counterfactually_reachable"] and row["ambiguous"]
        ]
        by_source[source] = {
            "information_states": len(source_rows),
            "counterfactually_reachable": sum(row["counterfactually_reachable"] for row in source_rows),
            "ambiguous": sum(row["ambiguous"] for row in source_rows),
            "reachable_ambiguous_tv": _metric_summary(source_reachable_ambiguous),
        }

    top = sorted(
        completion_ambiguous_reachable,
        key=lambda row: (
            -float(row["tv_uniform_vs_counterfactual"]),
            -float(row["counterfactual_mass"]),
            row["information_state_sha256"],
        ),
    )[:TOP_ROWS]
    top_compact = [
        {
            "information_state_sha256": row["information_state_sha256"],
            "round_index": row["round_index"],
            "actor": row["actor"],
            "layer": row["layer"],
            "source": row["source"],
            "concrete_states": row["concrete_states"],
            "counterfactual_mass": row["counterfactual_mass"],
            "positive_posterior_states": row["positive_posterior_states"],
            "max_posterior_probability": row["max_posterior_probability"],
            "tv_uniform_vs_counterfactual": row["tv_uniform_vs_counterfactual"],
        }
        for row in top
    ]

    completion_metric = _metric_summary(completion_ambiguous_reachable)
    if not completion_ambiguous_reachable:
        interpretation = "COMPLETION_COUNTERFACTUALLY_IRRELEVANT_UNDER_M"
    elif float(completion_metric["max_tv"]) <= EPS:
        interpretation = "UNIFORM_COMPLETION_MATCHES_COUNTERFACTUAL_POSTERIOR"
    else:
        interpretation = "NONUNIFORM_COUNTERFACTUAL_POSTERIOR_PRESENT"

    return {
        "information_states": len(rows),
        "counterfactually_reachable_information_states": len(reachable),
        "zero_counterfactual_mass_information_states": len(rows) - len(reachable),
        "ambiguous_information_states": sum(row["ambiguous"] for row in rows),
        "counterfactually_reachable_ambiguous_information_states": len(ambiguous_reachable),
        "completion_information_states": len(completion),
        "completion_counterfactually_reachable_information_states": len(completion_reachable),
        "completion_zero_counterfactual_mass_information_states": len(completion) - len(completion_reachable),
        "completion_ambiguous_information_states": sum(row["ambiguous"] for row in completion),
        "completion_counterfactually_reachable_ambiguous_information_states": len(completion_ambiguous_reachable),
        "reachable_ambiguous_tv": _metric_summary(ambiguous_reachable),
        "completion_reachable_ambiguous_tv": completion_metric,
        "by_layer": by_layer,
        "by_source": by_source,
        "top_completion_posterior_distortions": top_compact,
        "interpretation": interpretation,
        "posterior_metric_sha256": _posterior_metric_sha256(rows),
    }


def run() -> dict:
    worlds = broad_worlds()
    base_state = public_pre_r3_state()
    validate_broad_physical_support(base_state, worlds)
    support_rows = build_reachable_support(base_state, worlds)
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)

    geometry = {
        "chance_worlds": len(worlds),
        "reachable_information_states": len(support_rows),
        "nonroot_information_states": len(nonroot_keys),
        "ambiguous_nonroot_information_states": len(ambiguous_nonroot_keys),
        "root_information_states": len(root_keys),
    }
    geometry_pass = geometry == {
        "chance_worlds": 36,
        "reachable_information_states": EXPECTED_INFORMATION_STATES,
        "nonroot_information_states": EXPECTED_NONROOT_INFORMATION_STATES,
        "ambiguous_nonroot_information_states": EXPECTED_AMBIGUOUS_NONROOT,
        "root_information_states": EXPECTED_ROOT_INFORMATION_STATES,
    }
    if not geometry_pass:
        raise RuntimeError(f"05G frozen support geometry changed: {geometry}")

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
        profile = materialized["profiles"][PROFILE_NAME]
        source_map = materialized["source_maps"][PROFILE_NAME]
        validation = _validate_profile(profile, support_by_key, world_ids)
        profile_complete = set(profile) == set(support_by_key)
        source_complete = set(source_map) == set(support_by_key)
        source_labels_valid = set(source_map.values()) <= {MCCFR_NATIVE, COMPLETION_SOURCE}

        t1 = perf_counter()
        p0_masses, p0_traversal = _counterfactual_state_masses(
            base_state, worlds, opponent_profile=profile, player=0
        )
        p1_masses, p1_traversal = _counterfactual_state_masses(
            base_state, worlds, opponent_profile=profile, player=1
        )
        posterior_seconds = perf_counter() - t1

        posterior_rows, posterior_diagnostics = _posterior_rows(
            support_rows,
            source_map=source_map,
            masses_by_player={0: p0_masses, 1: p1_masses},
        )
        summary = _seed_summary(posterior_rows)

        validation_fields = (
            "illegal_key_count",
            "action_set_mismatch_count",
            "invalid_distribution_count",
            "hidden_world_token_leakage_count",
        )
        validation_pass = all(validation[field] == 0 for field in validation_fields)
        posterior_pass = all(value == 0 for value in posterior_diagnostics.values())
        seed_pass = (
            validation_pass
            and profile_complete
            and source_complete
            and source_labels_valid
            and posterior_pass
            and len(posterior_rows) == len(support_rows)
        )
        seed_results.append({
            "seed": seed,
            "m_profile_sha256": _profile_sha256(profile),
            "m_source_map_sha256": _source_map_sha256(source_map),
            "native_profile_sha256": materialized["native_sha256"],
            "native_information_states": materialized["native_counts"],
            "profile_validation": validation,
            "profile_complete": profile_complete,
            "source_map_complete": source_complete,
            "source_labels_valid": source_labels_valid,
            "counterfactual_traversal": {"player0": p0_traversal, "player1": p1_traversal},
            "posterior_runtime_seconds": posterior_seconds,
            "posterior_diagnostics": posterior_diagnostics,
            "summary": summary,
            "seed_pass": seed_pass,
        })

    interpretations = [row["summary"]["interpretation"] for row in seed_results]
    cross_seed_interpretation = (
        interpretations[0]
        if len(interpretations) == 2 and interpretations[0] == interpretations[1]
        else "SEED_DEPENDENT_COUNTERFACTUAL_POSTERIOR_RESULT"
    )

    quality = {
        "frozen_geometry_pass": geometry_pass,
        "completion_policy_complete": completion.information_states == len(support_rows),
        "both_seeds_audited_separately": [row["seed"] for row in seed_results] == list(SEEDS),
        "both_seeds_pass_mechanical_firewalls": len(seed_results) == 2 and all(row["seed_pass"] for row in seed_results),
        "no_policy_update": True,
        "no_ev_ranking": True,
        "no_best_response_choice_update": True,
        "no_nashconv_recomputation": True,
        "no_production_authority": True,
        "real_routes_certified_zero": True,
    }
    passed = all(quality.values())

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05G_BROAD_HIDDEN_INFORMATION_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q1A_NATIVE_PROVENANCE_ROUTER_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q1B_UNIFORM_BACKWARD_COMPLETION_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q2_EXACT_BILATERAL_BR_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q3_COUNTERFACTUAL_POSTERIOR_AUDIT_CONTRACT.md",
        "tools/openofc_solver/external_05g_uniform_backward_completion.py",
        "tools/openofc_solver/external_hidden_discard_overlap_strategic.py",
        "tools/openofc_solver/run_external_05g_q1c.py",
        "tools/openofc_solver/run_external_05g_q3.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "exact-counterfactual-posterior-audit-of-M-completion-holes",
        "config": {
            "seeds": list(SEEDS),
            "profile": PROFILE_NAME,
            "search_iterations": SEARCH_ITERATIONS,
            "search_exploration": SEARCH_EXPLORATION,
            "mccfr_iterations": MCCFR_ITERATIONS,
            "chance_worlds": len(worlds),
            "support_sha256": support_sha256(worlds),
            "completion_policy_sha256": completion.policy_sha256,
            "completion_source_label": COMPLETION_SOURCE,
            "posterior_tv_epsilon": EPS,
            "diagnostic_tv_thresholds": list(TV_THRESHOLDS),
            "posterior_baseline": "uniform_over_ReachableSupport.concrete_states_exactly_matching_Q1B_builder",
            "counterfactual_reach": "uniform_chance_prior_times_opponent_behavior_reach_with_own_actions_enumerated",
        },
        "exhaustive_support": geometry,
        "completion_build": {
            "runtime_seconds": completion_seconds,
            "terminal_evaluations": completion.terminal_evaluations,
            "policy_sha256": completion.policy_sha256,
        },
        "seed_results": seed_results,
        "cross_seed_interpretation": cross_seed_interpretation,
        "quality": quality,
        "verdict": "PASS_COUNTERFACTUAL_POSTERIOR_AUDIT" if passed else "BLOCK_COUNTERFACTUAL_POSTERIOR_AUDIT",
        "next_gate_recommendation": (
            "FREEZE_Q4_COUNTERFACTUAL_POSTERIOR_AWARE_COMPLETION_AB_WITHOUT_TOUCHING_NATIVE_ROWS"
            if passed and cross_seed_interpretation in {
                "NONUNIFORM_COUNTERFACTUAL_POSTERIOR_PRESENT",
                "SEED_DEPENDENT_COUNTERFACTUAL_POSTERIOR_RESULT",
            }
            else "BROADEN_EXTERNAL_FIXTURE_WITH_CURRENT_M_PROVENANCE_AND_KEEP_EXACT_BR_AUTHORITY"
            if passed
            else "FIX_Q3_MECHANICS_WITHOUT_CHANGING_Q1_OR_Q2_FROZEN_PROFILES"
        ),
        "interpretation_guardrail": (
            "Q3 diagnoses whether the completion heuristic is belief-principled. "
            "It does not erase Q2 exact NashConv: a correctly computed near-zero exact NashConv "
            "is a property of the complete finite-game profile regardless of how hole rows were generated."
        ),
        "limitations": [
            "finite deterministic 36-world reduced game only",
            "posterior audit is specific to frozen profile M and each frozen seed",
            "counterfactual posterior is diagnostic and does not by itself rank strategy strength",
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
        raise RuntimeError(f"05G-Q3 failed mechanical firewalls: {quality}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05g_q3.json")
    args = parser.parse_args()
    payload = run()
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
                "m_profile_sha256": row["m_profile_sha256"],
                "completion_information_states": row["summary"]["completion_information_states"],
                "completion_counterfactually_reachable_ambiguous_information_states": row["summary"]["completion_counterfactually_reachable_ambiguous_information_states"],
                "completion_reachable_ambiguous_tv": row["summary"]["completion_reachable_ambiguous_tv"],
                "interpretation": row["summary"]["interpretation"],
            }
            for row in payload["seed_results"]
        ],
        "next_gate_recommendation": payload["next_gate_recommendation"],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
