from __future__ import annotations

"""Validate M5R-F target-driven unresolved-BR width planning."""

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
from m5r_target_width_budget_controller import plan_target_width_budget

SCHEMA = "openofc-m5r-target-width-budget-controller-case-v1"
AUTHORITY = "RIGOROUS_TARGET_WIDTH_BUDGET_CONTROLLER_PILOT_NOT_ROUTE_CERTIFICATION"
DOMINANT_MASS = 0.8
TARGET_RANGE_FRACTIONS = (0.01, 0.05, 0.10, 0.20)


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
        "tools/openofc_solver/M5R_TARGET_WIDTH_BUDGET_CONTROLLER_CONTRACT.md",
        "tools/openofc_solver/m5r_target_width_budget_controller.py",
        "tools/openofc_solver/test_m5r_target_width_budget_controller.py",
        "tools/openofc_solver/run_m5r_target_width_budget_case.py",
        "tools/openofc_solver/m5r_deep_branch_br_interval.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def _instrument(game):
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

    reference = _game(args.family)
    reference_profile = _profile(reference)
    utility = exact_terminal_utility_range(reference)
    profile_p0_value = float(reference.expected_u0(reference_profile))
    exact_br = float(exact_best_response(reference, reference_profile, args.player).value)
    own_profile = profile_p0_value if args.player == 0 else -profile_p0_value
    exact_gain = exact_br - own_profile
    total_terminals = int(reference.terminal_count())

    rows = []
    for fraction in TARGET_RANGE_FRACTIONS:
        target_width = float(utility.utility_range) * fraction
        planner_game = _game(args.family)
        plan = plan_target_width_budget(
            planner_game,
            _profile(planner_game),
            args.player,
            utility_range=utility.utility_range,
            target_width=target_width,
        )
        if plan.guaranteed_unresolved_br_width_cap > target_width + 1e-10:
            raise SystemExit("planner exceeded its requested target width")

        evaluator_game = _game(args.family)
        counter = _instrument(evaluator_game)
        result = deep_branch_best_response_interval(
            evaluator_game,
            _profile(evaluator_game),
            args.player,
            profile_p0_value=profile_p0_value,
            p0_utility_min=utility.minimum_p0_utility,
            p0_utility_max=utility.maximum_p0_utility,
            prune_reach_threshold=plan.selected_prune_reach_threshold,
        )
        if counter["calls"] != plan.planned_resolved_terminal_histories:
            raise SystemExit(
                f"cold work mismatch: calls={counter['calls']} planned={plan.planned_resolved_terminal_histories}"
            )
        if result.resolved_terminal_histories != plan.planned_resolved_terminal_histories:
            raise SystemExit("M5R-F planned/evaluator resolved work mismatch")
        if result.skipped_terminal_histories != plan.planned_skipped_terminal_histories:
            raise SystemExit("M5R-F planned/evaluator skipped work mismatch")
        if result.interval_width > plan.guaranteed_unresolved_br_width_cap + 1e-10:
            raise SystemExit(
                "actual interval exceeded utility-free guaranteed width cap: "
                f"actual={result.interval_width} cap={plan.guaranteed_unresolved_br_width_cap}"
            )
        if not (
            result.lower_br_value <= exact_br + 1e-10
            and exact_br <= result.upper_br_value + 1e-10
        ):
            raise SystemExit("M5R-F evaluator interval missed exact BR")
        if exact_br - result.lower_br_value > plan.guaranteed_unresolved_br_width_cap + 1e-10:
            raise SystemExit("M5R-F guaranteed missed-BR cap was violated")

        rows.append(
            {
                "target_range_fraction": fraction,
                "target_width": target_width,
                "plan": asdict(plan),
                "evaluation": asdict(result),
                "observed_terminal_u0_invocations": counter["calls"],
                "exact_br_value": exact_br,
                "exact_deviation_gain": exact_gain,
                "actual_missed_br_above_lower_bound": exact_br - result.lower_br_value,
                "guaranteed_missed_br_upper_bound": plan.guaranteed_unresolved_br_width_cap,
            }
        )

    if any(
        row["plan"]["planned_resolved_terminal_histories"]
        + row["plan"]["planned_skipped_terminal_histories"]
        != total_terminals
        for row in rows
    ):
        raise SystemExit("M5R-F terminal accounting mismatch")
    partial = [
        row for row in rows
        if 0 < row["plan"]["planned_resolved_terminal_histories"] < total_terminals
    ]
    if not partial:
        raise SystemExit("M5R-F target ladder produced no partial-work plan")

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family": args.family,
        "player": args.player,
        "profile_rule": {
            "name": "deterministic_dominant_bounded_full_support",
            "dominant_mass": DOMINANT_MASS,
        },
        "target_range_fractions": list(TARGET_RANGE_FRACTIONS),
        "source_manifest": _source_manifest(),
        "validation_reference": {
            "exact_br_value": exact_br,
            "profile_p0_value": profile_p0_value,
            "exact_deviation_gain": exact_gain,
            "utility_range": float(utility.utility_range),
            "total_terminal_histories": total_terminals,
            "exact_authority_separate_from_planner_and_evaluator": True,
        },
        "rows": rows,
        "decision": {
            "target_driven_width_planning_validated_on_case": True,
            "planner_uses_no_terminal_utility": True,
            "guaranteed_width_cap_dominates_actual_interval": True,
            "guaranteed_width_cap_dominates_actual_missed_br": True,
            "cold_terminal_work_matches_plan": True,
            "full_game_scalable_evaluator_validated": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
            "next_blocker": "FULL_GAME_STATE_LOCAL_REMAINDER_ENVELOPES_AND_ROUTE_INTEGRATION_MISSING",
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
        "exact_br": exact_br,
        "rows": [
            {
                "target_fraction": row["target_range_fraction"],
                "target_width": row["target_width"],
                "guaranteed_cap": row["guaranteed_missed_br_upper_bound"],
                "actual_width": row["evaluation"]["interval_width"],
                "work_fraction": row["plan"]["planned_terminal_work_fraction"],
                "threshold": row["plan"]["selected_prune_reach_threshold"],
            }
            for row in rows
        ],
        "real_routes_certified": 0,
        "next_blocker": payload["decision"]["next_blocker"],
        "sha256": payload["sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
