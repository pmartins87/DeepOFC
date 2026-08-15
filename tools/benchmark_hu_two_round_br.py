from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_br import (
    exact_best_response,
    profile_with_pure_response,
)


def main() -> None:
    game = HUTwoRoundSubgame()
    uniform = game.uniform_profile()

    started0 = time.perf_counter()
    br0 = exact_best_response(game, uniform, 0)
    br0_seconds = time.perf_counter() - started0

    eval0_started = time.perf_counter()
    materialized0 = profile_with_pure_response(game, uniform, br0)
    independent_u0 = game.expected_u0(materialized0)
    eval0_seconds = time.perf_counter() - eval0_started

    started1 = time.perf_counter()
    br1 = exact_best_response(game, uniform, 1)
    br1_seconds = time.perf_counter() - started1

    eval1_started = time.perf_counter()
    materialized1 = profile_with_pure_response(game, uniform, br1)
    independent_u0_against_br1 = game.expected_u0(materialized1)
    eval1_seconds = time.perf_counter() - eval1_started
    independent_u1 = -independent_u0_against_br1

    if br0.value < -1e-12 or br1.value < -1e-12:
        raise SystemExit(f"best response unexpectedly negative: {br0.value}, {br1.value}")
    if abs(br0.value - br1.value) > 1e-10:
        raise SystemExit(
            f"symmetric uniform opponent produced asymmetric BRs: {br0.value} vs {br1.value}"
        )
    if abs(br0.value - independent_u0) > 1e-10:
        raise SystemExit(
            f"BR0 backward value disagrees with full tree: {br0.value} vs {independent_u0}"
        )
    if abs(br1.value - independent_u1) > 1e-10:
        raise SystemExit(
            f"BR1 backward value disagrees with full tree: {br1.value} vs {independent_u1}"
        )

    p0_infos = sum(1 for info in game.info_actions if info.player == 0)
    p1_infos = sum(1 for info in game.info_actions if info.player == 1)
    if len(br0.choices) != p0_infos or len(br1.choices) != p1_infos:
        raise SystemExit("best-response policy did not cover every own infoset")

    nash_conv_uniform = br0.value + br1.value
    print(
        "uniform_exact_br "
        f"br0={br0.value:.12f} br1={br1.value:.12f} "
        f"nash_conv={nash_conv_uniform:.12f} "
        f"exploitability={0.5 * nash_conv_uniform:.12f}"
    )
    print(
        "independent_full_tree_crosscheck "
        f"br0_expected_u0={independent_u0:.12f} "
        f"br1_expected_u1={independent_u1:.12f}"
    )
    print(
        "coverage "
        f"p0_infosets={p0_infos} p1_infosets={p1_infos} "
        f"br0_choices={len(br0.choices)} br1_choices={len(br1.choices)}"
    )
    print(
        "timing "
        f"br0_seconds={br0_seconds:.6f} br0_crosscheck_seconds={eval0_seconds:.6f} "
        f"br1_seconds={br1_seconds:.6f} br1_crosscheck_seconds={eval1_seconds:.6f}"
    )
    print("HU TWO-ROUND EXACT BEST RESPONSE: PASS")


if __name__ == "__main__":
    main()
