from __future__ import annotations

"""06A mechanical certification runner for the full-action HU normal-hand core."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import tempfile
from time import perf_counter

from strategic_cfr import (
    CHECKPOINT_SCHEMA,
    HUState,
    OutcomeSamplingMCCFR,
    child_state,
    legal_action_pairs,
    sample_deal_plan,
    terminal_utility,
)

EXPERIMENT_ID = "EXT-06A-FULL-GAME-MECHANICAL-CERTIFICATION"
AUTHORITY = "FULL_GAME_MECHANICS_CERTIFICATION_ONLY"


def _canonical_bytes(solver: OutcomeSamplingMCCFR) -> bytes:
    return json.dumps(
        solver.checkpoint_payload(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha(solver: OutcomeSamplingMCCFR) -> str:
    return hashlib.sha256(_canonical_bytes(solver)).hexdigest()


def _terminal_probe(seed: int) -> dict:
    state = HUState(plan=sample_deal_plan(random.Random(seed)))
    actor_round_sequence = []
    while not state.terminal():
        actor_round_sequence.append([state.round_index, state.actor])
        state = child_state(state, legal_action_pairs(state)[0][1])
    u0 = terminal_utility(state, 0)
    u1 = terminal_utility(state, 1)
    return {
        "seed": seed,
        "actor_round_sequence": actor_round_sequence,
        "p0_board_cards": state.boards[0].count(),
        "p1_board_cards": state.boards[1].count(),
        "p0_discards": len(state.discards[0]),
        "p1_discards": len(state.discards[1]),
        "public_events": len(state.public_history),
        "u0": u0,
        "u1": u1,
        "zero_sum": math.isfinite(u0) and math.isfinite(u1) and u0 == -u1,
    }


def run() -> dict:
    t0 = perf_counter()

    deal_checks = []
    for seed in range(32):
        plan = sample_deal_plan(random.Random(seed))
        dealt = plan.dealt_cards()
        opening_actions = len(legal_action_pairs(HUState(plan=plan)))
        deal_checks.append({
            "seed": seed,
            "dealt_cards": len(dealt),
            "unique_dealt_cards": len(set(dealt)),
            "opening_actions": opening_actions,
        })

    terminal_probes = [_terminal_probe(seed) for seed in (101, 202, 303, 404)]
    expected_sequence = [[r, p] for r in range(5) for p in (0, 1)]

    full_a = OutcomeSamplingMCCFR(seed=20260830, epsilon=0.6, cfr_plus=True)
    full_b = OutcomeSamplingMCCFR(seed=20260830, epsilon=0.6, cfr_plus=True)
    full_a.run(7)
    full_b.run(7)
    same_seed_exact = _canonical_bytes(full_a) == _canonical_bytes(full_b)

    staged = OutcomeSamplingMCCFR(seed=20260831, epsilon=0.6, cfr_plus=True)
    staged.run(3)
    pre_resume_rng = staged.rng.getstate()
    with tempfile.TemporaryDirectory() as tmp:
        checkpoint = Path(tmp) / "strategic-cfr-v2.json.gz"
        staged.save_checkpoint(checkpoint)
        restored = OutcomeSamplingMCCFR.load_checkpoint(checkpoint)
        rng_restored_exact = restored.rng.getstate() == pre_resume_rng
        restored.run(4)

    uninterrupted = OutcomeSamplingMCCFR(seed=20260831, epsilon=0.6, cfr_plus=True)
    uninterrupted.run(7)
    resume_exact = _canonical_bytes(restored) == _canonical_bytes(uninterrupted)

    vanilla = OutcomeSamplingMCCFR(seed=31, epsilon=0.6, cfr_plus=False)
    plus = OutcomeSamplingMCCFR(seed=31, epsilon=0.6, cfr_plus=True)
    vanilla.run(8)
    plus.run(8)
    vanilla_negative_regrets = sum(
        value < 0.0
        for node in vanilla.nodes.values()
        for value in node.cumulative_regrets
    )
    plus_negative_regrets = sum(
        value < 0.0
        for node in plus.nodes.values()
        for value in node.cumulative_regrets
    )

    finite_smoke = all(
        math.isfinite(value)
        for solver in (full_a, vanilla, plus)
        for node in solver.nodes.values()
        for value in (*node.cumulative_regrets, *node.cumulative_policy)
    )

    quality = {
        "checkpoint_schema_v2": CHECKPOINT_SCHEMA == "openofc-hu-outcome-sampling-mccfr-v2",
        "all_32_deals_have_34_unique_cards": all(
            row["dealt_cards"] == row["unique_dealt_cards"] == 34 for row in deal_checks
        ),
        "all_32_openings_have_232_actions": all(row["opening_actions"] == 232 for row in deal_checks),
        "terminal_order_exact": all(row["actor_round_sequence"] == expected_sequence for row in terminal_probes),
        "terminal_accounting_exact": all(
            row["p0_board_cards"] == row["p1_board_cards"] == 13
            and row["p0_discards"] == row["p1_discards"] == 4
            and row["public_events"] == 10
            for row in terminal_probes
        ),
        "terminal_zero_sum": all(row["zero_sum"] for row in terminal_probes),
        "same_seed_full_run_exact": same_seed_exact,
        "rng_restored_exact": rng_restored_exact,
        "checkpoint_resume_matches_uninterrupted_exact": resume_exact,
        "cfr_plus_clips_negative_regrets": plus_negative_regrets == 0,
        "vanilla_mode_exercises_unclipped_negative_regrets": vanilla_negative_regrets > 0,
        "finite_solver_accounting": finite_smoke,
        "no_strategic_strength_claim": True,
        "real_routes_certified_zero": True,
    }
    passed = all(quality.values())

    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "checkpoint_schema": CHECKPOINT_SCHEMA,
        "deal_checks": deal_checks,
        "terminal_probes": terminal_probes,
        "reproducibility": {
            "same_seed_payload_sha256_a": _sha(full_a),
            "same_seed_payload_sha256_b": _sha(full_b),
            "same_seed_exact": same_seed_exact,
            "resumed_payload_sha256": _sha(restored),
            "uninterrupted_payload_sha256": _sha(uninterrupted),
            "rng_restored_exact": rng_restored_exact,
            "resume_exact": resume_exact,
        },
        "cfr_mode_probe": {
            "vanilla_negative_regret_entries": vanilla_negative_regrets,
            "cfr_plus_negative_regret_entries": plus_negative_regrets,
        },
        "quality": quality,
        "verdict": "PASS_06A_FULL_GAME_MECHANICS" if passed else "FAIL_06A_FULL_GAME_MECHANICS",
        "next_gate_recommendation": (
            "06B_FREEZE_FULL_GAME_ALGORITHM_AND_POLICY_READOUT_AB"
            if passed else "STOP_AND_REPAIR_FULL_GAME_MECHANICS"
        ),
        "runtime_seconds": perf_counter() - t0,
        "real_routes_certified": 0,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    if not passed:
        raise RuntimeError(json.dumps({
            "experiment_id": EXPERIMENT_ID,
            "verdict": payload["verdict"],
            "quality": quality,
        }, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "quality": payload["quality"],
        "next_gate_recommendation": payload["next_gate_recommendation"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
