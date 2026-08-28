from __future__ import annotations

"""Run one reduced-game M5R prefix-subtree BR interval case."""

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
from m5r_prefix_subtree_br_interval import prefix_subtree_best_response_interval

SCHEMA = "openofc-m5r-prefix-subtree-br-interval-case-v1"
AUTHORITY = "RIGOROUS_PREFIX_SUBTREE_BR_INTERVAL_PILOT_NOT_ROUTE_CERTIFICATION"
DECAY = 0.2
THRESHOLD_MULTIPLIERS = (0.0, 0.01, 0.05, 0.20, 1.0)


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


def _geometric_profile(game, decay: float = DECAY):
    profile = {}
    for info, actions in game.info_actions.items():
        ordered = tuple(sorted(actions, key=lambda action: action.key()))
        raw = [decay**index for index in range(len(ordered))]
        total = sum(raw)
        profile[info] = {
            action: raw[index] / total
            for index, action in enumerate(ordered)
        }
    return profile


def _source_manifest() -> dict[str, object]:
    paths = (
        "tools/openofc_solver/M5R_PREFIX_SUBTREE_BR_INTERVAL_CONTRACT.md",
        "tools/openofc_solver/m5r_prefix_subtree_br_interval.py",
        "tools/openofc_solver/test_m5r_prefix_subtree_br_interval.py",
        "tools/openofc_solver/run_m5r_prefix_subtree_br_interval_case.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=("joker", "hidden-discard"), required=True)
    ap.add_argument("--player", type=int, choices=(0, 1), required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    game = _game(args.family)
    profile = _geometric_profile(game)

    # Validation-only exact authorities.  The prefix-pruned evaluator itself
    # never calls either routine.
    profile_p0_value = float(game.expected_u0(profile))
    exact_br_value = float(exact_best_response(game, profile, args.player).value)
    own_profile_value = profile_p0_value if args.player == 0 else -profile_p0_value
    exact_deviation_gain = exact_br_value - own_profile_value
    utility = exact_terminal_utility_range(game)
    total_terminals = int(game.terminal_count())

    rows = []
    for multiplier in THRESHOLD_MULTIPLIERS:
        threshold = float(game.chance_probability) * multiplier
        result = prefix_subtree_best_response_interval(
            game,
            profile,
            args.player,
            profile_p0_value=profile_p0_value,
            p0_utility_min=utility.minimum,
            p0_utility_max=utility.maximum,
            prune_reach_threshold=threshold,
        )
        row = asdict(result)
        row["threshold_multiplier_of_chance"] = multiplier
        row["contains_exact_br"] = (
            result.lower_br_value <= exact_br_value + 1e-10
            and exact_br_value <= result.upper_br_value + 1e-10
        )
        row["contains_exact_deviation_gain"] = (
            result.lower_deviation_gain <= exact_deviation_gain + 1e-10
            and exact_deviation_gain <= result.upper_deviation_gain + 1e-10
        )
        if result.total_terminal_histories_accounted != total_terminals:
            raise SystemExit(
                f"terminal accounting mismatch: {result.total_terminal_histories_accounted} vs {total_terminals}"
            )
        if not row["contains_exact_br"] or not row["contains_exact_deviation_gain"]:
            raise SystemExit(
                f"prefix interval missed exact authority at multiplier={multiplier}"
            )
        rows.append(row)

    resolved = [int(row["resolved_terminal_histories"]) for row in rows]
    widths = [float(row["interval_width"]) for row in rows]
    if any(resolved[index] < resolved[index + 1] for index in range(len(resolved) - 1)):
        raise SystemExit("resolved terminal work increased as pruning threshold increased")
    if any(widths[index] > widths[index + 1] + 1e-10 for index in range(len(widths) - 1)):
        raise SystemExit("interval width contracted when more prefix subtrees were pruned")
    if abs(widths[0]) > 1e-10:
        raise SystemExit(f"zero-threshold exact collapse failed: width={widths[0]}")
    if resolved[0] != total_terminals:
        raise SystemExit("zero-threshold run did not resolve the complete full-support profile")
    if resolved[-1] != 0:
        raise SystemExit("chance-threshold endpoint did not prune every terminal continuation")
    partial_rows = [
        row for row in rows
        if 0 < int(row["resolved_terminal_histories"]) < total_terminals
    ]
    if not partial_rows:
        raise SystemExit("frozen threshold ladder produced no partial work-saving point")

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family": args.family,
        "player": args.player,
        "profile_rule": {
            "name": "deterministic_geometric_full_support",
            "decay": DECAY,
        },
        "threshold_multipliers_of_chance": list(THRESHOLD_MULTIPLIERS),
        "source_manifest": _source_manifest(),
        "validation_reference": {
            "profile_p0_value": profile_p0_value,
            "exact_br_value": exact_br_value,
            "own_profile_value": own_profile_value,
            "exact_deviation_gain": exact_deviation_gain,
            "p0_utility_minimum": float(utility.minimum),
            "p0_utility_maximum": float(utility.maximum),
            "p0_utility_range": float(utility.utility_range),
            "total_terminal_histories": total_terminals,
            "exact_reference_outside_truncated_evaluator": True,
        },
        "rows": rows,
        "decision": {
            "rigorous_prefix_remainder_bound_validated_on_case": True,
            "exact_collapse_at_zero_threshold_validated": True,
            "full_prune_containment_validated": True,
            "terminal_work_reduction_validated": True,
            "partial_work_saving_points": len(partial_rows),
            "full_game_scalable_evaluator_validated": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
            "next_blocker": "STATE_LOCAL_SUBTREE_UTILITY_ENVELOPE_AND_DEEPER_PREFIX_PRUNING_MISSING",
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
        "exact_deviation_gain": exact_deviation_gain,
        "resolved_terminal_histories": resolved,
        "work_fractions": [row["terminal_work_fraction"] for row in rows],
        "interval_widths": widths,
        "partial_work_saving_points": len(partial_rows),
        "next_blocker": payload["decision"]["next_blocker"],
        "real_routes_certified": 0,
        "sha256": payload["sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
