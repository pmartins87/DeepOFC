from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_three_round_br import (
    exact_best_response,
    profile_with_pure_response,
)
from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame


EXPECTED_TERMINALS = 1_312_200


def main() -> None:
    game = HUThreeRoundSequentialSubgame()
    uniform = {}

    started = time.perf_counter()
    br0 = exact_best_response(game, uniform, 0)
    br0_seconds = time.perf_counter() - started
    if br0.terminal_histories != EXPECTED_TERMINALS:
        raise SystemExit(
            f"BR0 terminal coverage mismatch: {br0.terminal_histories} vs {EXPECTED_TERMINALS}"
        )

    started = time.perf_counter()
    cross0 = game.expected_u0(profile_with_pure_response(game, uniform, br0))
    cross0_seconds = time.perf_counter() - started
    if abs(br0.value - cross0) > 1e-10:
        raise SystemExit(f"three-round BR0 pure replay mismatch: {br0.value} vs {cross0}")

    started = time.perf_counter()
    br1 = exact_best_response(game, uniform, 1)
    br1_seconds = time.perf_counter() - started
    if br1.terminal_histories != EXPECTED_TERMINALS:
        raise SystemExit(
            f"BR1 terminal coverage mismatch: {br1.terminal_histories} vs {EXPECTED_TERMINALS}"
        )

    started = time.perf_counter()
    cross1 = -game.expected_u0(profile_with_pure_response(game, uniform, br1))
    cross1_seconds = time.perf_counter() - started
    if abs(br1.value - cross1) > 1e-10:
        raise SystemExit(f"three-round BR1 pure replay mismatch: {br1.value} vs {cross1}")

    if abs(br0.value - br1.value) > 1e-10:
        raise SystemExit(
            f"three-round symmetric uniform BR values diverged: {br0.value} vs {br1.value}"
        )

    nash_conv = br0.value + br1.value
    print(
        f"three_round_uniform_br br0={br0.value:.12f} br1={br1.value:.12f} "
        f"nash_conv={nash_conv:.12f} exploitability={0.5*nash_conv:.12f} "
        f"br0_infosets={len(br0.choices)} br1_infosets={len(br1.choices)}"
    )
    print(
        f"independent_crosscheck br0_full_tree={cross0:.12f} br1_full_tree={cross1:.12f}"
    )
    print(
        f"timing br0_seconds={br0_seconds:.6f} cross0_seconds={cross0_seconds:.6f} "
        f"br1_seconds={br1_seconds:.6f} cross1_seconds={cross1_seconds:.6f}"
    )
    print("HU THREE-ROUND EXACT BEST RESPONSE REFERENCE: PASS")


if __name__ == "__main__":
    main()
