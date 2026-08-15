from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deepofc.fantasy_solver_v2 import evaluate_fantasy_exact_subsets_v2
from deepofc.scoring import pairwise_points_standard
from deepofc.state import Card, OFCState, PlayerBoard, PlayerState


def C(code: str) -> Card:
    return Card.from_code(code)


def main() -> None:
    # Extend the real frame53 15-card dual-Joker fan with two additional unique
    # standard cards. Geometry is synthetic; physical/card-game semantics are not.
    incoming = tuple(
        C(code)
        for code in (
            "JK1", "JK2", "Ac", "Kd", "Qc", "Qd", "Js", "9s", "9h",
            "7s", "6h", "4s", "4c", "3s", "2c", "Ts", "Th",
        )
    )
    opponent = PlayerBoard(
        top=(C("Ah"), C("Jc"), C("8h")),
        middle=(C("6s"), C("5c"), C("4h"), C("3h"), C("2h")),
        bottom=(C("9d"), C("8d"), C("6d"), C("4d"), C("2d")),
    )
    state = OFCState(
        players=(
            PlayerState(chair=0, board=opponent),
            PlayerState(chair=1, fantasy=True),
        ),
        hero_chair=1,
        dealer_chair=0,
        acting_chair=1,
        round_index=-1,
        hero_incoming=incoming,
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )

    t0 = time.perf_counter()
    result = evaluate_fantasy_exact_subsets_v2(state)
    elapsed = time.perf_counter() - t0
    decision = result.decision
    canonical = pairwise_points_standard(decision.board, opponent)

    print(f"incoming_cards={len(incoming)}")
    print(f"optimal_points={decision.current_hand_points}")
    print(f"elapsed_seconds={elapsed:.6f}")
    print(f"optimal_board_top={' '.join(c.code for c in decision.board.top)}")
    print(f"optimal_board_middle={' '.join(c.code for c in decision.board.middle)}")
    print(f"optimal_board_bottom={' '.join(c.code for c in decision.board.bottom)}")
    print(f"discards={' '.join(c.code for c in decision.action.discards)}")
    print(f"refantasy={decision.refantasy_qualifies}")
    print(f"stats_v2={result.stats_v2}")

    assert canonical.total_points == decision.current_hand_points
    assert not canonical.hero_foul
    assert len(decision.action.discards) == 4
    print("SYNTHETIC FANTASY17 DUAL-JOKER V2: PASS")


if __name__ == "__main__":
    main()
