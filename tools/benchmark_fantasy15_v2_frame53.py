from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deepofc.fantasy_solver_v2 import evaluate_fantasy_exact_subsets_v2
from deepofc.scoring import pairwise_points_standard
from deepofc.serde import state_from_dict


def fmt_cards(cards) -> str:
    return " ".join(card.code for card in cards)


def fmt_board(board) -> str:
    return (
        f"top=[{fmt_cards(board.top)}] "
        f"middle=[{fmt_cards(board.middle)}] "
        f"bottom=[{fmt_cards(board.bottom)}]"
    )


def main() -> None:
    payload = json.loads(
        (ROOT / "fixtures/replay/fantasy_frame000053.json").read_text(encoding="utf-8")
    )
    state = state_from_dict(payload["state"])
    opponent = state.player(0).board

    t0 = time.perf_counter()
    result = evaluate_fantasy_exact_subsets_v2(state)
    elapsed = time.perf_counter() - t0
    decision = result.decision

    canonical = pairwise_points_standard(decision.board, opponent)
    print(f"optimal_board={fmt_board(decision.board)}")
    print(f"optimal_discards={fmt_cards(decision.action.discards)}")
    print(f"optimal_ranks={decision.resolved_ranks}")
    print(f"optimal_points={decision.current_hand_points}")
    print(f"optimal_refantasy={decision.refantasy_qualifies}")
    print(f"elapsed_seconds={elapsed:.6f}")
    print(f"stats_v2={result.stats_v2}")

    # 28 is frozen by the exact V1 real-frame run 31900847707. The independent
    # canonical scorer below must also reproduce the same value for V2's board.
    assert decision.current_hand_points == 28
    assert canonical.total_points == decision.current_hand_points
    assert not canonical.hero_foul
    print("REAL FANTASY15 DUAL-JOKER V2: PASS")


if __name__ == "__main__":
    main()
