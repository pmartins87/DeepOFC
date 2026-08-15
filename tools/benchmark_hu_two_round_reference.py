from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import HUTwoRoundSubgame


FROZEN_INFOSETS = 79_804
FROZEN_MERGED_ROUND4 = 7_056
FROZEN_TERMINALS = 373_248


def main() -> None:
    # The structural reference depends on a rank-preserving suit-only
    # player-swap automorphism. The frozen fixture also guarantees every legal
    # terminal is non-foul, so no unresolved double-foul semantics are invoked.
    # Pure memoization is allowed only if every frozen structural/value result
    # remains exactly unchanged.
    build_started = time.perf_counter()
    game = HUTwoRoundSubgame()
    build_seconds = time.perf_counter() - build_started
    if len(game.info_actions) != FROZEN_INFOSETS:
        raise SystemExit(
            f"memoization changed infosets: {len(game.info_actions)} vs {FROZEN_INFOSETS}"
        )

    count_started = time.perf_counter()
    terminal_count = game.terminal_count()
    count_seconds = time.perf_counter() - count_started
    if terminal_count != FROZEN_TERMINALS:
        raise SystemExit(f"unexpected terminal count: {terminal_count}")

    merged_started = time.perf_counter()
    merged_round4 = game.count_merged_round4_infosets()
    merged_seconds = time.perf_counter() - merged_started
    if merged_round4 != FROZEN_MERGED_ROUND4:
        raise SystemExit(
            f"memoization changed hidden-history merging: {merged_round4} vs {FROZEN_MERGED_ROUND4}"
        )

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
    print(f"terminal_cache={game.terminal_u0.cache_info()}")
    print(f"round3_board_cache={game._boards_after_round3.cache_info()}")
    print(f"round4_info_cache={game.round4_info.cache_info()}")
    print("HU TWO-ROUND PERFECT-RECALL REFERENCE: PASS")


if __name__ == "__main__":
    main()
