from __future__ import annotations

"""Exhaustively validate state-local raw-point envelopes on exact R6 families."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from deepofc.simulator import apply_normal_action
from m5r_full_game_remainder_envelope import (
    GLOBAL_RAW_POINT_ABS_BOUND,
    p0_raw_point_interval,
    raw_point_remainder_envelope,
)

SCHEMA = "openofc-m5r-full-game-remainder-envelope-case-v1"
AUTHORITY = "RIGOROUS_STATE_LOCAL_REMAINDER_CONTAINMENT_PILOT_NOT_ROUTE_CERTIFICATION"


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


def _after_first_round4(game, outcome, first: int, board0, board1, first_r4):
    current = board0 if first == 0 else board1
    updated, _ = apply_normal_action(
        current,
        first_r4,
        round_index=4,
        incoming=outcome.hand(first, 4),
    )
    return (updated, board1) if first == 0 else (board0, updated)


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/scoring.py",
        "deepofc/simulator.py",
        "deepofc/state.py",
        "tools/openofc_solver/m5r_full_game_remainder_envelope.py",
        "tools/openofc_solver/test_m5r_full_game_remainder_envelope.py",
        "tools/openofc_solver/run_m5r_full_game_remainder_envelope_case.py",
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
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    game = _game(args.family)
    terminal_histories = 0
    post_r3_states = 0
    after_first_r4_states = 0
    p0_containment_checks = 0
    p1_containment_checks = 0
    tightened_post_r3_states = 0
    tightened_after_first_r4_states = 0
    min_post_r3_width = 2 * GLOBAL_RAW_POINT_ABS_BOUND
    max_post_r3_width = 0
    min_after_first_width = 2 * GLOBAL_RAW_POINT_ABS_BOUND
    max_after_first_width = 0
    largest_p0_lower_slack = 0.0
    largest_p0_upper_slack = 0.0

    for outcome in game.outcomes:
        first = outcome.first_player
        second = outcome.second_player
        first_r3_info = game.round3_first_info(outcome)
        for first_r3 in game.actions(first_r3_info):
            second_r3_info = game.round3_second_info(outcome, first_r3)
            for second_r3 in game.actions(second_r3_info):
                board0, board1, action0_r3, action1_r3 = game._boards_after_round3(
                    outcome, first_r3, second_r3
                )
                post_env = raw_point_remainder_envelope(board0, board1)
                post_r3_states += 1
                min_post_r3_width = min(min_post_r3_width, post_env.width)
                max_post_r3_width = max(max_post_r3_width, post_env.width)
                if post_env.width < 2 * GLOBAL_RAW_POINT_ABS_BOUND:
                    tightened_post_r3_states += 1

                first_own_r3 = action0_r3 if first == 0 else action1_r3
                first_opp_r3 = action1_r3 if first == 0 else action0_r3
                second_own_r3 = action0_r3 if second == 0 else action1_r3
                second_opp_r3 = action1_r3 if second == 0 else action0_r3
                first_r4_info = game.round4_info(
                    outcome,
                    player=first,
                    own_round3_action=first_own_r3,
                    opponent_round3_action=first_opp_r3,
                    current_first_action=None,
                )
                for first_r4 in game.actions(first_r4_info):
                    after0, after1 = _after_first_round4(
                        game, outcome, first, board0, board1, first_r4
                    )
                    after_env = raw_point_remainder_envelope(after0, after1)
                    after_first_r4_states += 1
                    min_after_first_width = min(min_after_first_width, after_env.width)
                    max_after_first_width = max(max_after_first_width, after_env.width)
                    if after_env.width < 2 * GLOBAL_RAW_POINT_ABS_BOUND:
                        tightened_after_first_r4_states += 1

                    second_r4_info = game.round4_info(
                        outcome,
                        player=second,
                        own_round3_action=second_own_r3,
                        opponent_round3_action=second_opp_r3,
                        current_first_action=first_r4,
                    )
                    for second_r4 in game.actions(second_r4_info):
                        u0 = float(
                            game.terminal_u0(
                                outcome,
                                first_r3,
                                second_r3,
                                first_r4,
                                second_r4,
                            )
                        )
                        terminal_histories += 1
                        for envelope in (post_env, after_env):
                            if not envelope.contains(u0):
                                raise SystemExit(
                                    "state-local P0 remainder envelope missed exact terminal: "
                                    f"family={args.family} value={u0} envelope={asdict(envelope)}"
                                )
                            p0_containment_checks += 1
                            largest_p0_lower_slack = max(
                                largest_p0_lower_slack,
                                u0 - envelope.lower_raw_points,
                            )
                            largest_p0_upper_slack = max(
                                largest_p0_upper_slack,
                                envelope.upper_raw_points - u0,
                            )

                        # Zero-sum/perspective regression: swapping the boards
                        # must conservatively contain the opponent utility -u0.
                        post_p1 = raw_point_remainder_envelope(board1, board0)
                        after_p1 = raw_point_remainder_envelope(after1, after0)
                        if not post_p1.contains(-u0) or not after_p1.contains(-u0):
                            raise SystemExit("state-local P1 swapped envelope missed exact terminal")
                        p1_containment_checks += 2

    expected_terminals = int(game.terminal_count())
    if terminal_histories != expected_terminals:
        raise SystemExit(
            f"terminal accounting mismatch: observed={terminal_histories} expected={expected_terminals}"
        )
    if tightened_after_first_r4_states <= 0:
        raise SystemExit("state-local envelope never tightened after first round-4 action")

    # Adapter must preserve the primary envelope semantics on a deterministic
    # canonical state, without depending on hidden-discard identity or policy.
    sample_game = _game(args.family)
    sample_outcome = sample_game.outcomes[0]
    first = sample_outcome.first_player
    first_r3 = sample_game.actions(sample_game.round3_first_info(sample_outcome))[0]
    second_r3 = sample_game.actions(sample_game.round3_second_info(sample_outcome, first_r3))[0]
    sample0, sample1, *_ = sample_game._boards_after_round3(sample_outcome, first_r3, second_r3)
    callback_interval = p0_raw_point_interval(sample0, sample1)
    primary = raw_point_remainder_envelope(sample0, sample1)
    if callback_interval != (float(primary.lower_raw_points), float(primary.upper_raw_points)):
        raise SystemExit("P0 remainder callback disagrees with primary state-local envelope")

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family": args.family,
        "source_manifest": _source_manifest(),
        "scoring_bound": {
            "global_raw_point_abs_bound": GLOBAL_RAW_POINT_ABS_BOUND,
            "global_width": 2 * GLOBAL_RAW_POINT_ABS_BOUND,
            "both_foul_settlement_policy": "FAIL_CLOSED_UNDEFINED",
        },
        "coverage": {
            "terminal_histories": terminal_histories,
            "post_r3_states": post_r3_states,
            "after_first_r4_states": after_first_r4_states,
            "p0_containment_checks": p0_containment_checks,
            "p1_containment_checks": p1_containment_checks,
        },
        "tightening": {
            "tightened_post_r3_states": tightened_post_r3_states,
            "tightened_after_first_r4_states": tightened_after_first_r4_states,
            "min_post_r3_width": min_post_r3_width,
            "max_post_r3_width": max_post_r3_width,
            "min_after_first_r4_width": min_after_first_width,
            "max_after_first_r4_width": max_after_first_width,
            "largest_p0_lower_slack": largest_p0_lower_slack,
            "largest_p0_upper_slack": largest_p0_upper_slack,
        },
        "decision": {
            "scoring_derived_global_bound_validated": True,
            "state_local_terminal_containment_validated": True,
            "zero_sum_swapped_perspective_containment_validated": True,
            "strict_state_local_tightening_observed": tightened_after_first_r4_states > 0,
            "uses_canonical_full_game_player_board": True,
            "depends_on_policy_or_hidden_discard_identity": False,
            "route_level_br_integration_validated": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
            "next_blocker": "ROUTE_LEVEL_BR_INTEGRATION_OF_STATE_LOCAL_ENVELOPES_MISSING",
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
        "sha256": payload["sha256"],
        "terminal_histories": terminal_histories,
        "tightened_after_first_r4_states": tightened_after_first_r4_states,
        "next_blocker": payload["decision"]["next_blocker"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
