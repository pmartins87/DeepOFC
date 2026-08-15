from __future__ import annotations

from math import sqrt
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deepofc.expectimax import evaluate_penultimate_normal_round_exact_last_chance
from deepofc.monte_carlo import evaluate_penultimate_normal_round_monte_carlo
from deepofc.state import Card, OFCState, PlayerBoard, PlayerState


def C(code: str) -> Card:
    return Card.from_code(code)


def state_and_pool():
    hero = PlayerBoard(
        top=(C("6s"), C("6h")),
        middle=(C("7s"), C("7h"), C("5s")),
        bottom=(C("9s"), C("Ts"), C("Js"), C("Qs")),
    )
    opponent = PlayerBoard(
        top=(C("5c"), C("5d"), C("2c")),
        middle=(C("8c"), C("8d"), C("7c"), C("6c"), C("4c")),
        bottom=(C("Ac"), C("Kc"), C("Qc"), C("Jc"), C("Tc")),
    )
    state = OFCState(
        players=(PlayerState(chair=0, board=opponent), PlayerState(chair=1, board=hero)),
        hero_chair=1,
        dealer_chair=0,
        acting_chair=1,
        round_index=3,
        hero_incoming=(C("Ah"), C("8s"), C("4s")),
        hero_discards=(C("2s"), C("3s")),
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )
    # 8-card chance pool => C(8,3)=56 exact future draws.
    pool = (C("Ks"), C("9h"), C("8h"), C("5h"), C("4h"), C("3h"), C("2h"), C("Ad"))
    return state, pool


def main() -> None:
    state, pool = state_and_pool()
    t0 = time.perf_counter()
    exact = evaluate_penultimate_normal_round_exact_last_chance(
        state, future_draw_pool=pool
    )
    exact_seconds = time.perf_counter() - t0
    exact_by_key = {value.action.key(): value.expected_value for value in exact.values}
    exact_best = {value.action.key() for value in exact.best_actions}

    print(f"chance_pool={len(pool)} branches={exact.chance_branches_per_action}")
    print(f"actions={len(exact.values)}")
    print(f"exact_best_value={exact.best_value:.12f}")
    print(f"exact_seconds={exact_seconds:.6f}")

    for samples in (8, 16, 32, 56):
        t1 = time.perf_counter()
        mc = evaluate_penultimate_normal_round_monte_carlo(
            state,
            samples=samples,
            seed=20260815,
            future_draw_pool=pool,
        )
        seconds = time.perf_counter() - t1
        errors = [
            value.mean_value - exact_by_key[value.action.key()]
            for value in mc.values
        ]
        rmse = sqrt(sum(error * error for error in errors) / len(errors))
        max_abs = max(abs(error) for error in errors)
        mc_best = {value.action.key() for value in mc.best_actions}
        overlap = bool(mc_best & exact_best)
        max_ci = max(value.ci95_half_width for value in mc.values)
        print(
            f"samples={samples} exhaustive={mc.exhaustive} "
            f"best={mc.best_value:.12f} best_overlap={overlap} "
            f"rmse={rmse:.12f} max_abs={max_abs:.12f} "
            f"max_ci95_half={max_ci:.12f} seconds={seconds:.6f}"
        )
        if samples == 56:
            assert mc.exhaustive
            assert rmse == 0.0
            assert max_abs == 0.0
            assert mc.best_indices == exact.best_indices

    print("PENULTIMATE MC CONVERGENCE BENCHMARK: PASS")


if __name__ == "__main__":
    main()
