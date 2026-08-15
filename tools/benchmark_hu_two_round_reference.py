from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import HUTwoRoundSubgame


def main() -> None:
    build_started = time.perf_counter()
    game = HUTwoRoundSubgame()
    build_seconds = time.perf_counter() - build_started

    count_started = time.perf_counter()
    terminal_count = game.terminal_count()
    count_seconds = time.perf_counter() - count_started
    if terminal_count != 373_248:
        raise SystemExit(f"unexpected terminal count: {terminal_count}")

    merged_started = time.perf_counter()
    merged_round4 = game.count_merged_round4_infosets()
    merged_seconds = time.perf_counter() - merged_started
    if merged_round4 <= 0:
        raise SystemExit("round-4 infosets unexpectedly reveal every physical history")

    symmetry_started = time.perf_counter()
    symmetry_checks = game.assert_terminal_swap_symmetry()
    symmetry_seconds = time.perf_counter() - symmetry_started
    if symmetry_checks != terminal_count:
        raise SystemExit(
            f"symmetry checked {symmetry_checks} branches, expected {terminal_count}"
        )

    uniform = game.uniform_profile()
    value_started = time.perf_counter()
    uniform_value = game.expected_u0(uniform)
    value_seconds = time.perf_counter() - value_started
    if abs(uniform_value) > 1e-12:
        raise SystemExit(
            f"symmetric uniform profile should have value 0, got {uniform_value}"
        )

    print(
        "two_round_reference "
        f"chance_outcomes={len(game.outcomes)} "
        f"infosets={len(game.info_actions)} "
        f"merged_round4_infosets={merged_round4} "
        f"terminals={terminal_count} "
        f"symmetry_checks={symmetry_checks} "
        f"uniform_expected_u0={uniform_value:.12f}"
    )
    print(
        "timing "
        f"build_seconds={build_seconds:.6f} "
        f"terminal_count_seconds={count_seconds:.6f} "
        f"merged_seconds={merged_seconds:.6f} "
        f"symmetry_seconds={symmetry_seconds:.6f} "
        f"uniform_value_seconds={value_seconds:.6f}"
    )
    print("HU TWO-ROUND PERFECT-RECALL REFERENCE: PASS")


if __name__ == "__main__":
    main()
