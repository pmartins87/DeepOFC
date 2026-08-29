from __future__ import annotations

"""05H-H3 exact bilateral best-response evaluation of frozen complete M."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

from external_05g_uniform_backward_completion import build_uniform_local_backward_completion
from external_05h_broad_support import (
    AUTHORITY,
    public_pre_r3_state,
    support_sha256,
    validate_physical_support,
    worlds,
)
from external_hidden_discard_overlap_strategic import (
    OverlapExternalSamplingMCCFR,
    build_reachable_support,
    exact_nash_conv,
)
from run_external_05g_q0b import _support_maps, _validate_profile
from run_external_05g_q1a import _profile_sha256
from run_external_05g_q1b import _materialize_completion_profile
from run_external_05g_q1c import _exact_asymmetric_value
from run_external_05g_q2 import _br_behavior_profile
from run_external_05h_h1 import BUDGETS, SEEDS
from run_external_05h_h2 import _assemble_m

EXPERIMENT_ID = "EXT-05H-H3-EXACT-BILATERAL-BEST-RESPONSE"
REPLAY_TOLERANCE = 1e-9
STRICT_NEAR_NASH = 1e-6
LOW_NOT_STRICT_MAX = 1e-3


def _band(exploitability: float) -> str:
    if exploitability <= STRICT_NEAR_NASH:
        return "NEAR_NASH_STRICT"
    if exploitability <= LOW_NOT_STRICT_MAX:
        return "LOW_BUT_NOT_STRICT"
    return "MATERIAL_EXPLOITABILITY"


def _sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(*, mccfr_iterations: int) -> dict:
    if mccfr_iterations not in BUDGETS:
        raise ValueError(f"H3 MCCFR budget must be frozen H1 candidate: {BUDGETS}")

    base_state = public_pre_r3_state()
    support = worlds()
    validate_physical_support(base_state, support)

    t0 = perf_counter()
    support_rows = build_reachable_support(base_state, support)
    support_seconds = perf_counter() - t0
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)
    if len(support) != 144 or len(support_rows) != 261076:
        raise RuntimeError("H3 refuses geometry that differs from passed H0")

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
        complete = set(m_profile) == set(support_by_key)
        profile_firewall = complete and all(
            validation[field] == 0
            for field in (
                "illegal_key_count",
                "action_set_mismatch_count",
                "invalid_distribution_count",
                "hidden_world_token_leakage_count",
            )
        )
        if not profile_firewall:
            raise RuntimeError("H3 complete M profile failed pre-BR firewall")

        t3 = perf_counter()
        nash = exact_nash_conv(
            base_state,
            support,
            profile=m_profile,
            support_rows=support_rows,
        )
        br_seconds = perf_counter() - t3

        br0_choices = nash.br0.choice_map()
        br1_choices = nash.br1.choice_map()
        br0_profile = _br_behavior_profile(support_rows, player=0, choices=br0_choices)
        br1_profile = _br_behavior_profile(support_rows, player=1, choices=br1_choices)

        t4 = perf_counter()
        br0_replay = _exact_asymmetric_value(
            base_state,
            support,
            p0_profile=br0_profile,
            p1_profile=m_profile,
        )
        br1_replay = _exact_asymmetric_value(
            base_state,
            support,
            p0_profile=m_profile,
            p1_profile=br1_profile,
        )
        replay_seconds = perf_counter() - t4

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
            and br0_error <= REPLAY_TOLERANCE
            and br1_error <= REPLAY_TOLERANCE
        )
        finite_pass = all(math.isfinite(value) for value in (
            nash.br0.value,
            nash.br1.value,
            nash.nash_conv,
            nash.exploitability,
        ))
        nonnegative_pass = nash.nash_conv >= -REPLAY_TOLERANCE
        seed_pass = coverage_pass and replay_pass and finite_pass and nonnegative_pass
        seed_results.append({
            "seed": seed,
            "mccfr_iterations": mccfr_iterations,
            "native_runtime_seconds": mccfr_seconds,
            "native_information_states": len(mccfr),
            "m_profile_sha256": _profile_sha256(m_profile),
            "m_source_counts": {
                "MCCFR_NATIVE": sum(1 for label in source_map.values() if label == "MCCFR_NATIVE"),
                "COMPLETION_UNIFORM_LOCAL_BACKWARD_V1": sum(
                    1 for label in source_map.values() if label == "COMPLETION_UNIFORM_LOCAL_BACKWARD_V1"
                ),
            },
            "best_response": {
                "runtime_seconds": br_seconds,
                "br0_value": nash.br0.value,
                "br1_value": nash.br1.value,
                "br0_round3_infosets": nash.br0.round3_infosets,
                "br0_round4_infosets": nash.br0.round4_infosets,
                "br1_round3_infosets": nash.br1.round3_infosets,
                "br1_round4_infosets": nash.br1.round4_infosets,
                "br0_terminal_leaves": nash.br0.terminal_leaves,
                "br1_terminal_leaves": nash.br1.terminal_leaves,
                "br0_choice_sha256": hashlib.sha256(
                    json.dumps(br0_choices, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
                "br1_choice_sha256": hashlib.sha256(
                    json.dumps(br1_choices, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
                "nash_conv": nash.nash_conv,
                "exploitability": nash.exploitability,
                "interpretation_band": _band(nash.exploitability),
            },
            "exact_replay": {
                "runtime_seconds": replay_seconds,
                "br0_replay_u0": br0_replay["expected_u0"],
                "br1_replay_u0": br1_replay["expected_u0"],
                "br1_replay_player1_value": -br1_replay["expected_u0"],
                "br0_absolute_error": br0_error,
                "br1_absolute_error": br1_error,
                "tolerance": REPLAY_TOLERANCE,
            },
            "coverage_pass": coverage_pass,
            "replay_pass": replay_pass,
            "finite_pass": finite_pass,
            "nonnegative_nashconv_pass": nonnegative_pass,
            "seed_pass": seed_pass,
        })

    bands = [row["best_response"]["interpretation_band"] for row in seed_results]
    if len(bands) == 2 and all(band == "NEAR_NASH_STRICT" for band in bands):
        cross_seed = "05H_NEAR_NASH_REPLICATED"
        next_gate = "05H_H4_COUNTERFACTUAL_POSTERIOR_AUDIT"
    elif len(bands) == 2 and all(band in {"NEAR_NASH_STRICT", "LOW_BUT_NOT_STRICT"} for band in bands):
        cross_seed = "05H_LOW_NOT_STRICT_REPLICATED"
        next_gate = "FREEZE_NEW_MCCFR_BUDGET_EXPANSION_CONTRACT_BEFORE_RETRAINING"
    else:
        cross_seed = "05H_NOT_REPLICATED_AT_LOW_EXPLOITABILITY"
        next_gate = "STOP_AND_DIAGNOSE_EXACT_BR_COMPLETION_OR_TRAINING_FAILURE_MODE"

    quality = {
        "support_matches_h0": len(support) == 144 and len(support_rows) == 261076,
        "completion_complete": completion.information_states == len(support_rows),
        "both_seeds_evaluated_separately": len(seed_results) == 2 and [row["seed"] for row in seed_results] == list(SEEDS),
        "both_seeds_mechanical_pass": len(seed_results) == 2 and all(row["seed_pass"] for row in seed_results),
        "exact_replay_tolerance_frozen": REPLAY_TOLERANCE == 1e-9,
        "strategic_bands_precommitted": STRICT_NEAR_NASH == 1e-6 and LOW_NOT_STRICT_MAX == 1e-3,
        "no_cross_seed_average_for_verdict": True,
        "no_production_authority": True,
        "real_routes_certified_zero": True,
    }
    passed = all(quality.values())

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05H_144_WORLD_BROADENING_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05H_H1_MCCFR_NATIVE_COVERAGE_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05H_H2_M_PROVENANCE_COMPLETION_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05H_H3_EXACT_BILATERAL_BR_CONTRACT.md",
        "tools/openofc_solver/run_external_05h_h3.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "exact-bilateral-best-response-of-complete-M-on-144-world-fixture",
        "config": {
            "seeds": list(SEEDS),
            "mccfr_iterations": mccfr_iterations,
            "support_sha256": support_sha256(support),
            "replay_tolerance": REPLAY_TOLERANCE,
            "strict_near_nash_max_exploitability": STRICT_NEAR_NASH,
            "low_not_strict_max_exploitability": LOW_NOT_STRICT_MAX,
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
        "cross_seed_strategic_interpretation": cross_seed,
        "quality": quality,
        "verdict": "PASS_05H_H3_EXACT_BR_MECHANICS" if passed else "FAIL_05H_H3_EXACT_BR_MECHANICS",
        "next_gate_recommendation": next_gate if passed else "STOP_AND_DIAGNOSE_H3_MECHANICS",
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
        "cross_seed_strategic_interpretation": payload["cross_seed_strategic_interpretation"],
        "seed_summaries": [
            {
                "seed": row["seed"],
                "exploitability": row["best_response"]["exploitability"],
                "nash_conv": row["best_response"]["nash_conv"],
                "band": row["best_response"]["interpretation_band"],
                "br0_replay_error": row["exact_replay"]["br0_absolute_error"],
                "br1_replay_error": row["exact_replay"]["br1_absolute_error"],
            }
            for row in payload["seed_results"]
        ],
        "next_gate_recommendation": payload["next_gate_recommendation"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
