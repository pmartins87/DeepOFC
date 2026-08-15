from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_cfr import TwoRoundFullTreeCFR


FROZEN_UNIFORM_EXPLOITABILITY = 2.099206349206
FROZEN_PRECACHE_EXPLOITABILITY = {
    1: 2.099206349206,
    2: 0.742551892552,
    4: 0.303445902390,
    8: 0.044624397410,
}


def max_profile_difference(left, right) -> float:
    worst = 0.0
    for info, left_dist in left.items():
        right_dist = right[info]
        for action, probability in left_dist.items():
            worst = max(worst, abs(probability - right_dist[action]))
    return worst


def main() -> None:
    game = HUTwoRoundSubgame()
    solver = TwoRoundFullTreeCFR(game, variant="dcfr")
    uniform = game.uniform_profile()

    checkpoints = (1, 2, 4, 8)
    previous = 0
    cumulative_train = 0.0
    final_exploitability = None

    for checkpoint in checkpoints:
        train_started = time.perf_counter()
        solver.run(checkpoint - previous)
        cumulative_train += time.perf_counter() - train_started
        previous = checkpoint

        if checkpoint == 1:
            deviation = max_profile_difference(solver.average_profile(), uniform)
            print(f"iteration1_average_vs_uniform_max_abs={deviation:.18f}")
            if deviation > 1e-15:
                raise SystemExit(
                    "iteration-1 DCFR average must equal the uniform strategy actually used"
                )

        eval_started = time.perf_counter()
        snapshot = solver.snapshot()
        eval_seconds = time.perf_counter() - eval_started
        final_exploitability = snapshot.exploitability
        frozen = FROZEN_PRECACHE_EXPLOITABILITY[checkpoint]
        if abs(snapshot.exploitability - frozen) > 1e-10:
            raise SystemExit(
                "memoization changed certified DCFR semantics at iteration "
                f"{checkpoint}: {snapshot.exploitability} vs {frozen}"
            )
        print(
            f"iteration={checkpoint} expected_u0={snapshot.expected_u0:.12f} "
            f"br0={snapshot.br0:.12f} br1={snapshot.br1:.12f} "
            f"nash_conv={snapshot.nash_conv:.12f} "
            f"exploitability={snapshot.exploitability:.12f} "
            f"cumulative_train_seconds={cumulative_train:.6f} "
            f"exact_eval_seconds={eval_seconds:.6f}"
        )

    if final_exploitability is None:
        raise SystemExit("no DCFR checkpoint evaluated")
    if not final_exploitability < FROZEN_UNIFORM_EXPLOITABILITY:
        raise SystemExit(
            f"two-round DCFR failed to improve exact exploitability: "
            f"{final_exploitability} >= {FROZEN_UNIFORM_EXPLOITABILITY}"
        )

    terminal_evaluations = checkpoints[-1] * game.terminal_count()
    print(
        f"training_terminal_evaluations={terminal_evaluations} "
        f"final_exploitability={final_exploitability:.12f}"
    )
    print(f"terminal_cache={game.terminal_u0.cache_info()}")
    print(f"round3_board_cache={game._boards_after_round3.cache_info()}")
    print(f"round4_info_cache={game.round4_info.cache_info()}")
    print("HU TWO-ROUND FULL-TREE DCFR: PASS")


if __name__ == "__main__":
    main()
