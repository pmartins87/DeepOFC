from __future__ import annotations

"""Frozen EXT-06R2 V2 exact-exploitability cell runner."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

from deepofc.hu_three_round_br import exact_nash_conv
from deepofc.hu_three_round_mccfr import HUThreeRoundExternalSamplingMCCFR
from deepofc.hu_three_round_sequential_v2 import HUThreeRoundSequentialSubgameV2
from v2_information_set_uct import V2InformationSetUCT

EXPERIMENT_ID = "EXT-06R2-V2-EXACT-EXPLOITABILITY-SOLVER-SELECTION"
ALLOWED_METHODS = ("MCCFR", "ISUCT")
ALLOWED_SEEDS = (20260830, 20260831)
TARGET_TERMINALS = 839_808
MCCFR_ITERATIONS = 2_592
ISUCT_ITERATIONS = TARGET_TERMINALS
ISUCT_EXPLORATION = 2.0


def run(method: str, seed: int) -> dict:
    method = str(method).upper()
    seed = int(seed)
    if method not in ALLOWED_METHODS:
        raise ValueError(f"method must be one of {ALLOWED_METHODS}")
    if seed not in ALLOWED_SEEDS:
        raise ValueError(f"seed must be one of {ALLOWED_SEEDS}")

    game = HUThreeRoundSequentialSubgameV2()

    started = perf_counter()
    if method == "MCCFR":
        solver = HUThreeRoundExternalSamplingMCCFR(game, seed=seed)
        solver.run(MCCFR_ITERATIONS)
        stats = solver.stats()
        iterations = int(stats.iterations)
        terminal_evaluations = int(stats.terminal_evaluations)
        information_states = int(stats.regret_infosets)
        profile = solver.current_profile()
        profile_semantics = "MCCFR_CURRENT_REGRET_MATCHING_PROFILE"
        if iterations != MCCFR_ITERATIONS:
            raise AssertionError("MCCFR iteration accounting drift")
    else:
        solver = V2InformationSetUCT(
            game,
            exploration=ISUCT_EXPLORATION,
            seed=seed,
        )
        solver.run(ISUCT_ITERATIONS)
        if not solver.accounting_exact():
            raise AssertionError("ISUCT visit/terminal accounting drift")
        iterations = int(solver.iterations)
        terminal_evaluations = int(solver.terminal_evaluations)
        information_states = len(solver.nodes)
        profile = solver.visit_profile()
        profile_semantics = "ISUCT_NORMALIZED_INFOSET_ACTION_VISITS"
        if iterations != ISUCT_ITERATIONS:
            raise AssertionError("ISUCT iteration accounting drift")

    training_seconds = perf_counter() - started
    if terminal_evaluations != TARGET_TERMINALS:
        raise AssertionError(
            f"equal-work terminal accounting failed: {terminal_evaluations} != {TARGET_TERMINALS}"
        )

    # Probability normalization is checked before the exact tribunal. Missing
    # infosets are deliberately allowed because the V2 game defines an explicit
    # uniform fallback for sparse profiles.
    max_probability_error = 0.0
    for _info, distribution in profile.items():
        mass = sum(float(p) for p in distribution.values())
        max_probability_error = max(max_probability_error, abs(mass - 1.0))
        if any((not math.isfinite(float(p))) or float(p) < 0.0 for p in distribution.values()):
            raise AssertionError("profile contains invalid probability")
    if max_probability_error > 1e-12:
        raise AssertionError(f"profile probability mass drift: {max_probability_error}")

    started = perf_counter()
    nash_conv, br0, br1 = exact_nash_conv(game, profile)
    exact_evaluation_seconds = perf_counter() - started
    exploitability = 0.5 * float(nash_conv)

    if not all(math.isfinite(x) for x in (br0.value, br1.value, nash_conv, exploitability)):
        raise AssertionError("06R2 exact tribunal produced a non-finite result")
    if exploitability < -1e-10:
        raise AssertionError("06R2 exploitability is negative beyond tolerance")

    payload = {
        "schema": "openofc-external-06r2-v2-cell-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": "CONDITIONAL_V2_EXACT_EXPLOITABILITY_SOLVER_SELECTION_ONLY",
        "method": method,
        "learner_seed": seed,
        "frozen": {
            "game": "HUThreeRoundSequentialSubgameV2",
            "chance_scenarios": len(game.outcomes),
            "target_terminal_evaluations": TARGET_TERMINALS,
            "mccfr_iterations": MCCFR_ITERATIONS,
            "isuct_iterations": ISUCT_ITERATIONS,
            "isuct_exploration": ISUCT_EXPLORATION,
            "profile_semantics": profile_semantics,
            "unvisited_infoset_semantics": "GAME_DEFINED_UNIFORM_FALLBACK",
            "exact_evaluator": "deepofc.hu_three_round_br.exact_nash_conv",
        },
        "training": {
            "iterations": iterations,
            "terminal_evaluations": terminal_evaluations,
            "information_states_touched": information_states,
            "profile_information_states": len(profile),
            "training_seconds": training_seconds,
            "profile_max_probability_mass_error": max_probability_error,
        },
        "exact_tribunal": {
            "br0_value": float(br0.value),
            "br1_value": float(br1.value),
            "br0_information_states": len(br0.choices),
            "br1_information_states": len(br1.choices),
            "nash_conv": float(nash_conv),
            "exploitability": exploitability,
            "exact_evaluation_seconds": exact_evaluation_seconds,
        },
        "verdict": "PASS_06R2_CELL_NO_INDIVIDUAL_PROMOTION_AUTHORITY",
        "real_routes_certified": 0,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True, choices=ALLOWED_METHODS)
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    payload = run(args.method, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "method": payload["method"],
        "learner_seed": payload["learner_seed"],
        "training": payload["training"],
        "exact_tribunal": payload["exact_tribunal"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
