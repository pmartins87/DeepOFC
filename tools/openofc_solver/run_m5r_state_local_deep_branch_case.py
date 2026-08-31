from __future__ import annotations

"""Validate state-local M5R deep-BR integration against exact reduced BR."""

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
from m5r_deep_branch_br_interval import deep_branch_best_response_interval
from m5r_full_game_remainder_envelope import GLOBAL_RAW_POINT_ABS_BOUND
from m5r_state_local_deep_branch_br_interval import (
    state_local_deep_branch_best_response_interval,
)

SCHEMA = "openofc-m5r-state-local-deep-branch-case-v1"
AUTHORITY = "RIGOROUS_STATE_LOCAL_DEEP_BRANCH_INTEGRATION_PILOT_NOT_ROUTE_CERTIFICATION"


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


def _dominant_full_support_profile(game, dominant_mass: float = 0.8):
    profile = {}
    for info, actions in game.info_actions.items():
        ordered = tuple(sorted(actions, key=lambda action: action.key()))
        if len(ordered) == 1:
            profile[info] = {ordered[0]: 1.0}
            continue
        tail = (1.0 - dominant_mass) / (len(ordered) - 1)
        profile[info] = {
            action: dominant_mass if index == 0 else tail
            for index, action in enumerate(ordered)
        }
    return profile


def _contains(result, exact_br: float, exact_gain: float, atol: float = 1e-10) -> bool:
    return (
        result.lower_br_value <= exact_br + atol
        and exact_br <= result.upper_br_value + atol
        and result.lower_deviation_gain <= exact_gain + atol
        and exact_gain <= result.upper_deviation_gain + atol
    )


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/scoring.py",
        "deepofc/simulator.py",
        "deepofc/state.py",
        "tools/openofc_solver/m5r_deep_branch_br_interval.py",
        "tools/openofc_solver/m5r_full_game_remainder_envelope.py",
        "tools/openofc_solver/m5r_state_local_deep_branch_br_interval.py",
        "tools/openofc_solver/test_m5r_state_local_deep_branch_br_interval.py",
        "tools/openofc_solver/run_m5r_state_local_deep_branch_case.py",
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
    profile = _dominant_full_support_profile(game)
    p0_value = float(game.expected_u0(profile))
    exact_br = float(exact_best_response(game, profile, args.player).value)
    own_profile = p0_value if args.player == 0 else -p0_value
    exact_gain = exact_br - own_profile

    zero = state_local_deep_branch_best_response_interval(
        game,
        profile,
        args.player,
        profile_p0_value=p0_value,
        prune_reach_threshold=0.0,
    )
    if abs(zero.interval_width) > 1e-10 or abs(zero.lower_br_value - exact_br) > 1e-10:
        raise SystemExit("zero-threshold state-local integration did not collapse to exact BR")

    working_threshold = float(game.chance_probability) * 0.01
    local = state_local_deep_branch_best_response_interval(
        game,
        profile,
        args.player,
        profile_p0_value=p0_value,
        prune_reach_threshold=working_threshold,
    )
    global_scoring = deep_branch_best_response_interval(
        game,
        profile,
        args.player,
        profile_p0_value=p0_value,
        p0_utility_min=-float(GLOBAL_RAW_POINT_ABS_BOUND),
        p0_utility_max=float(GLOBAL_RAW_POINT_ABS_BOUND),
        prune_reach_threshold=working_threshold,
    )
    if not _contains(local, exact_br, exact_gain):
        raise SystemExit("state-local working-threshold BR interval missed exact BR")
    if local.resolved_terminal_histories != global_scoring.resolved_terminal_histories:
        raise SystemExit("state-local integration changed pruning work at equal threshold")
    if local.skipped_terminal_histories != global_scoring.skipped_terminal_histories:
        raise SystemExit("state-local integration changed skipped terminal accounting")
    if local.interval_width > global_scoring.interval_width + 1e-10:
        raise SystemExit("state-local interval became wider than scoring-global interval")
    if local.local_envelope_calls <= 0:
        raise SystemExit("working threshold never exercised a state-local envelope")

    full = state_local_deep_branch_best_response_interval(
        game,
        profile,
        args.player,
        profile_p0_value=p0_value,
        prune_reach_threshold=float(game.chance_probability),
    )
    if not _contains(full, exact_br, exact_gain):
        raise SystemExit("full-prune state-local BR interval missed exact BR")
    if full.resolved_terminal_histories != 0:
        raise SystemExit("full threshold unexpectedly resolved terminal histories")
    if full.skipped_terminal_histories != game.terminal_count():
        raise SystemExit("full threshold failed terminal accounting")

    strict_tightening = local.interval_width < global_scoring.interval_width - 1e-10
    deep_pruning_exercised = (
        local.pruned_round4_opponent_branches + local.pruned_terminal_opponent_actions
    ) > 0

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family": args.family,
        "player": args.player,
        "source_manifest": _source_manifest(),
        "exact_reference": {
            "profile_p0_value": p0_value,
            "own_profile_value": own_profile,
            "exact_br_value": exact_br,
            "exact_deviation_gain": exact_gain,
            "terminal_histories": int(game.terminal_count()),
        },
        "zero_threshold": asdict(zero),
        "working_threshold": {
            "threshold": working_threshold,
            "state_local": asdict(local),
            "scoring_global": asdict(global_scoring),
            "state_local_contains_exact": True,
            "same_terminal_work": True,
            "strict_interval_tightening": strict_tightening,
            "deep_pruning_exercised": deep_pruning_exercised,
            "interval_width_reduction": global_scoring.interval_width - local.interval_width,
            "interval_width_ratio": (
                local.interval_width / global_scoring.interval_width
                if global_scoring.interval_width > 0.0
                else 0.0
            ),
        },
        "full_prune_threshold": asdict(full),
        "decision": {
            "zero_threshold_exact_equivalence": True,
            "exact_br_containment_validated": True,
            "equal_threshold_work_equivalence": True,
            "state_local_never_wider_than_scoring_global_in_tested_cell": True,
            "strict_interval_tightening_observed": strict_tightening,
            "deep_pruning_exercised": deep_pruning_exercised,
            "route_evidence_interface_validated": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
            "next_blocker": "ROUTE_EVIDENCE_INTERFACE_FOR_STATE_LOCAL_BR_UPPER_BOUNDS_MISSING",
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
        "sha256": payload["sha256"],
        "strict_interval_tightening": strict_tightening,
        "deep_pruning_exercised": deep_pruning_exercised,
        "width_ratio": payload["working_threshold"]["interval_width_ratio"],
        "next_blocker": payload["decision"]["next_blocker"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
