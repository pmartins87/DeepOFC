from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deepofc.actions import FantasyPlacementAction, fantasy_action_board
from deepofc.fantasy_solver import evaluate_fantasy_exact_subsets
from deepofc.scoring import completed_board_ranks, is_foul, pairwise_points_standard
from deepofc.serde import state_from_dict
from deepofc.simulator import refantasy_qualifies
from deepofc.state import PendingPlacement, Row


def action_from_pending(state) -> FantasyPlacementAction:
    pending = tuple(state.hero_pending)
    placed = {p.card for p in pending}
    discards = tuple(card for card in state.hero_incoming if card not in placed)
    return FantasyPlacementAction(placements=pending, discards=discards)


def fmt_cards(cards) -> str:
    return " ".join(card.code for card in cards)


def fmt_board(board) -> str:
    return (
        f"top=[{fmt_cards(board.top)}] "
        f"middle=[{fmt_cards(board.middle)}] "
        f"bottom=[{fmt_cards(board.bottom)}]"
    )


def main() -> None:
    fixture_path = ROOT / "fixtures" / "replay" / "fantasy_frame000053.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    state = state_from_dict(payload["state"])
    opponent = state.player(0).board

    if len(state.hero_incoming) != 15:
        raise AssertionError("frame53 must remain a 15-card Fantasy fixture")
    if {card.code for card in state.hero_incoming if card.is_joker} != {"JK1", "JK2"}:
        raise AssertionError("frame53 must contain both physical Jokers")
    if not opponent.is_complete():
        raise AssertionError("frame53 opponent board must be complete")

    actual_action = action_from_pending(state)
    actual_board = fantasy_action_board(actual_action)
    actual_score = pairwise_points_standard(actual_board, opponent)
    if actual_score.hero_foul:
        raise AssertionError("observed frame53 Hero arrangement unexpectedly fouls")

    t0 = time.perf_counter()
    optimum = evaluate_fantasy_exact_subsets(state)
    elapsed = time.perf_counter() - t0

    print("fixture=fixtures/replay/fantasy_frame000053.json")
    print(f"incoming={fmt_cards(state.hero_incoming)}")
    print(f"opponent={fmt_board(opponent)}")
    print(f"observed_board={fmt_board(actual_board)}")
    print(f"observed_discards={fmt_cards(actual_action.discards)}")
    print(f"observed_ranks={completed_board_ranks(actual_board)}")
    print(f"observed_points={actual_score.total_points}")
    print(f"observed_refantasy={refantasy_qualifies(actual_board)}")
    print(f"optimal_board={fmt_board(optimum.board)}")
    print(f"optimal_discards={fmt_cards(optimum.action.discards)}")
    print(f"optimal_ranks={optimum.resolved_ranks}")
    print(f"optimal_points={optimum.current_hand_points}")
    print(f"optimal_refantasy={optimum.refantasy_qualifies}")
    print(f"point_gain_vs_observed={optimum.current_hand_points - actual_score.total_points}")
    print(f"elapsed_seconds={elapsed:.6f}")
    print(f"tied_best_count={optimum.tied_best_count}")
    print(f"stats={optimum.stats}")

    assert not is_foul(optimum.board, equality_allowed=True)
    assert optimum.current_hand_points >= actual_score.total_points
    assert optimum.board.is_complete()
    assert set(optimum.action.placed_cards) | set(optimum.action.discards) == set(state.hero_incoming)
    print("REAL FANTASY15 DUAL-JOKER EXACT SOLVE: PASS")


if __name__ == "__main__":
    main()
