from __future__ import annotations

"""Run one M5R-E deep opponent-branch BR interval validation case."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round_br import exact_best_response
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_support_range_feasibility import exact_terminal_utility_range
from m5r_deep_branch_br_interval import deep_branch_best_response_interval

SCHEMA = "openofc-m5r-deep-branch-br-interval-case-v1"
AUTHORITY = "RIGOROUS_DEEP_BRANCH_BR_INTERVAL_PILOT_NOT_ROUTE_CERTIFICATION"
DOMINANT_MASS = 0.8
THRESHOLD_MULTIPLIERS = (0.0, 0.001, 0.005, 0.01, 0.05, 0.20, 1.0)


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _game(family: str):
    if family == "joker":
        return HUTwoRoundJokerSubgame()
    if family == "hidden-discard":
        return HUTwoRoundHiddenDiscardSubgame()
    raise ValueError(f"unsupported family: {family}")


def _profile(game):
    result = {}
    for info, actions in game.info_actions.items():
        ordered = tuple(sorted(actions, key=lambda action: action.key()))
        if len(ordered) == 1:
            result[info] = {ordered[0]: 1.0}
            continue
        tail = (1.0 - DOMINANT_MASS) / (len(ordered) - 1)
        result[info] = {
            action: DOMINANT_MASS if index == 0 else tail
            for index, action in enumerate(ordered)
        }
    return result


def _source_manifest() -> dict[str, object]:
    paths = (
        "tools/openofc_solver/M5R_DEEP_BRANCH_BR_INTERVAL_CONTRACT.md",
        "tools/openofc_solver/m5r_deep_branch_br_interval.py",
        "tools/openofc_solver/test_m5r_deep_branch_br_interval.py",
        "tools/openofc_solver/run_m5r_deep_branch_br_interval_case.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def _instrument_terminal_calls(game):
    original = game.terminal_u0
    counter = {"calls": 0}

    def counted(*args, **kwargs):
        counter["calls"] += 1
        return original(*args, **kwargs)

    game.terminal_u0 = counted
    return counter


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=("joker", "hidden-discard"), required=True)
    ap.add_argument("--player", type=int, choices=(0, 1), required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    # Exact authority is computed on a separate instance.  Evaluator instances
    # below start with a cold terminal_u0 cache and an invocation counter.
    reference_game = _game(args.family)
    reference_profile = _profile(reference_game)
    utility = exact_terminal_utility_range(reference_game)
    profile_p0_value = float(reference_game.expected_u0(reference_profile))
    exact_br_value = float(
        exact_best_response(reference_game, reference_profile, args.player).value
    )
    own_profile_value = profile_p0_value if args.player == 0 else -profile_p0_value
    exact_deviation_gain = exact_br_value - own_profile_value
    total_terminals = int(reference_game.terminal_count())

    rows = []
    for multiplier in THRESHOLD_MULTIPLIERS:
        eval_game = _game(args.family)
        eval_profile = _profile(eval_game)
        counter = _instrument_terminal_calls(eval_game)
        threshold = float(eval_game.chance_probability) * multiplier
        result = deep_branch_best_response_interval(
            eval_game,
            eval_profile,
            args.player,
            profile_p0_value=profile_p0_value,
            p0_utility_min=utility.minimum_p0_utility,
            p0_utility_max=utility.maximum_p0_utility,
            prune_reach_threshold=threshold,
        )
        if counter["calls"] != result.resolved_terminal_histories:
            raise SystemExit(
                "terminal_u0 invocation mismatch: "
                f"observed={counter['calls']} reported={result.resolved_terminal_histories}"
            )
        if result.total_terminal_histories_accounted != total_terminals:
            raise SystemExit(
                f"terminal accounting mismatch: {result.total_terminal_histories_accounted} vs {total_terminals}"
            )
        contains_br = (
            result.lower_br_value <= exact_br_value + 1e-10
            and exact_br_value <= result.upper_br_value + 1e-10
        )
        contains_gain = (
            result.lower_deviation_gain <= exact_deviation_gain + 1e-10
            and exact_deviation_gain <= result.upper_deviation_gain + 1e-10
        )
        if not contains_br or not contains_gain:
            raise SystemExit(
                f"deep branch interval missed exact authority at multiplier={multiplier}"
            )
        row = asdict(result)
        row.update(
            {
                "threshold_multiplier_of_chance": multiplier,
                "observed_terminal_u0_invocations": counter["calls"],
                "contains_exact_br": contains_br,
                "contains_exact_deviation_gain": contains_gain,
            }
        )
        rows.append(row)

    work = [int(row["resolved_terminal_histories"]) for row in rows]
    widths = [float(row["interval_width"]) for row in rows]
    if any(work[index] < work[index + 1] for index in range(len(work) - 1)):
        raise SystemExit("terminal work increased as deep pruning threshold increased")
    if any(widths[index] > widths[index + 1] + 1e-10 for index in range(len(widths) - 1)):
        raise SystemExit("deep interval width contracted when more branches were pruned")
    if work[0] != total_terminals or abs(widths[0]) > 1e-10:
        raise SystemExit("zero-threshold deep evaluator did not collapse to exact full work")
    if work[-1] != 0:
        raise SystemExit("maximum-threshold deep evaluator did not skip all terminal work")
    deep_only_rows = [
        row for row in rows
        if row["pruned_round3_prefixes"] == 0
        and (
            row["pruned_round4_opponent_branches"] > 0
            or row["pruned_terminal_opponent_actions"] > 0
        )
    ]
    if not deep_only_rows:
        raise SystemExit("threshold ladder did not expose a deep-only pruning point")

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family": args.family,
        "player": args.player,
        "profile_rule": {
            "name": "deterministic_dominant_bounded_full_support",
            "dominant_mass": DOMINANT_MASS,
            "tail_rule": "equal_mass_over_remaining_legal_actions",
        },
        "threshold_multipliers_of_chance": list(THRESHOLD_MULTIPLIERS),
        "source_manifest": _source_manifest(),
        "validation_reference": {
            "profile_p0_value": profile_p0_value,
            "exact_br_value": exact_br_value,
            "own_profile_value": own_profile_value,
            "exact_deviation_gain": exact_deviation_gain,
            "p0_utility_minimum": float(utility.minimum_p0_utility),
            "p0_utility_maximum": float(utility.maximum_p0_utility),
            "p0_utility_range": float(utility.utility_range),
            "total_terminal_histories": total_terminals,
            "reference_game_is_separate_from_evaluator_games": True,
        },
        "rows": rows,
        "decision": {
            "rigorous_deep_branch_remainder_bound_validated_on_case": True,
            "cold_terminal_call_count_matches_reported_work": True,
            "deep_only_pruning_point_observed": True,
            "exact_collapse_at_zero_threshold_validated": True,
            "full_prune_containment_validated": True,
            "full_game_scalable_evaluator_validated": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
            "next_blocker": "TARGET_DRIVEN_MISSED_DEVIATION_BUDGET_CONTROLLER_AND_FULL_GAME_TRANSFER_MISSING",
        },
    }
    payload["sha256"] = _sha(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "family": args.family,
        "player": args.player,
        "exact_br": exact_br_value,
        "work": work,
        "work_fractions": [row["terminal_work_fraction"] for row in rows],
        "widths": widths,
        "deep_only_points": len(deep_only_rows),
        "real_routes_certified": 0,
        "sha256": payload["sha256"],
        "next_blocker": payload["decision"]["next_blocker"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
