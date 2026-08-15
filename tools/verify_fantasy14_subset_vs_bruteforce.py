from __future__ import annotations

import time

from deepofc.actions import fantasy_action_board, iter_fantasy_actions
from deepofc.fantasy_solver import evaluate_fantasy_exact_subsets
from deepofc.scoring import pairwise_points_standard
from deepofc.state import Card, OFCState, PlayerBoard, PlayerState


def C(code: str) -> Card:
    return Card.from_code(code)


def opponent_board() -> PlayerBoard:
    return PlayerBoard(
        top=(C("6c"), C("6d"), C("3c")),
        middle=(C("5c"), C("5d"), C("4c"), C("4d"), C("2c")),
        bottom=(C("9c"), C("Tc"), C("Jc"), C("Qc"), C("Kc")),
    )


def state14() -> OFCState:
    incoming = tuple(
        C(code)
        for code in (
            "As", "Ah", "Ks", "Kh", "Qs", "Qh", "Js", "Jh",
            "Ts", "Th", "9s", "8s", "7s", "2s",
        )
    )
    return OFCState(
        players=(
            PlayerState(chair=0, board=opponent_board()),
            PlayerState(chair=1, fantasy=True),
        ),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=-1,
        hero_incoming=incoming,
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )


def main() -> None:
    state = state14()
    villain = opponent_board()

    t0 = time.perf_counter()
    fast = evaluate_fantasy_exact_subsets(state)
    fast_seconds = time.perf_counter() - t0

    brute_best: int | None = None
    brute_key = None
    brute_actions = 0
    brute_valid = 0

    t1 = time.perf_counter()
    for action in iter_fantasy_actions(state):
        brute_actions += 1
        board = fantasy_action_board(action)
        score = pairwise_points_standard(board, villain)
        if score.hero_foul:
            continue
        brute_valid += 1
        value = score.total_points
        key = action.key()
        if brute_best is None or value > brute_best:
            brute_best = value
            brute_key = key
        elif value == brute_best and (brute_key is None or key < brute_key):
            brute_key = key
    brute_seconds = time.perf_counter() - t1

    if brute_best is None or brute_key is None:
        raise RuntimeError("brute-force reference found no valid Fantasy board")

    print(f"raw_actions={brute_actions}")
    print(f"valid_actions={brute_valid}")
    print(f"subset_best={fast.current_hand_points}")
    print(f"brute_best={brute_best}")
    print(f"subset_seconds={fast_seconds:.6f}")
    print(f"brute_seconds={brute_seconds:.6f}")
    print(f"subset_ties={fast.tied_best_count}")
    print(f"subset_stats={fast.stats}")

    if brute_actions != 1_009_008:
        raise AssertionError(f"expected 1,009,008 raw actions, got {brute_actions}")
    if fast.current_hand_points != brute_best:
        raise AssertionError(
            f"subset/brute EV mismatch: {fast.current_hand_points} != {brute_best}"
        )
    if fast.action.key() != brute_key:
        raise AssertionError("subset/brute canonical best-action mismatch")

    print("FANTASY14 SUBSET == BRUTE FORCE: PASS")


if __name__ == "__main__":
    main()
