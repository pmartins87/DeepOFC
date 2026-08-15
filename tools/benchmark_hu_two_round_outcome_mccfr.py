from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_outcome_mccfr import TwoRoundOutcomeSamplingMCCFR


FROZEN_UNIFORM_EXPLOITABILITY = 2.099206349206


def main() -> None:
    game = HUTwoRoundSubgame()
    solver = TwoRoundOutcomeSamplingMCCFR(
        game,
        seed=20260815,
        epsilon=0.6,
    )

    checkpoints = (10_000, 50_000, 200_000, 500_000)
    previous = 0
    cumulative_train = 0.0
    best_exploitability = FROZEN_UNIFORM_EXPLOITABILITY

    for checkpoint in checkpoints:
        train_started = time.perf_counter()
        solver.run(checkpoint - previous)
        cumulative_train += time.perf_counter() - train_started
        previous = checkpoint

        eval_started = time.perf_counter()
        snapshot = solver.snapshot()
        eval_seconds = time.perf_counter() - eval_started
        best_exploitability = min(best_exploitability, snapshot.exploitability)

        expected_terminal_evaluations = 2 * checkpoint
        if snapshot.training_terminal_evaluations != expected_terminal_evaluations:
            raise SystemExit(
                "unexpected outcome-sampling terminal-work count: "
                f"{snapshot.training_terminal_evaluations} vs {expected_terminal_evaluations}"
            )
        print(
            f"iteration={checkpoint} epsilon=0.6 "
            f"training_terminal_evaluations={snapshot.training_terminal_evaluations} "
            f"expected_u0={snapshot.expected_u0:.12f} "
            f"br0={snapshot.br0:.12f} br1={snapshot.br1:.12f} "
            f"nash_conv={snapshot.nash_conv:.12f} "
            f"exploitability={snapshot.exploitability:.12f} "
            f"cumulative_train_seconds={cumulative_train:.6f} "
            f"exact_eval_seconds={eval_seconds:.6f}"
        )

    if best_exploitability >= FROZEN_UNIFORM_EXPLOITABILITY:
        raise SystemExit(
            "outcome sampling failed to improve current strategy at every checkpoint"
        )
    print(f"terminal_cache={game.terminal_u0.cache_info()}")
    print("HU TWO-ROUND OUTCOME-SAMPLING MCCFR: PASS")


if __name__ == "__main__":
    main()
