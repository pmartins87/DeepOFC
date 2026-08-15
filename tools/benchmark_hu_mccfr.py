from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_mccfr import ExternalSamplingMCCFR
from deepofc.hu_subgame import HUFinalRoundSubgame


def main() -> None:
    game = HUFinalRoundSubgame()
    uniform = game.uniform_profile()
    eval_started = time.perf_counter()
    uniform_exploitability = game.exploitability(uniform)
    uniform_eval_seconds = time.perf_counter() - eval_started
    print(
        f"uniform_exploitability={uniform_exploitability:.12f} "
        f"exact_reference_value={game.exact_reference_value:.12f} "
        f"exact_eval_seconds={uniform_eval_seconds:.6f}"
    )

    solver = ExternalSamplingMCCFR(game, seed=20260815)
    checkpoints = (100, 500, 2000, 10000, 50000)
    previous = 0
    cumulative_train = 0.0
    cumulative_eval = 0.0
    final = None
    for checkpoint in checkpoints:
        train_started = time.perf_counter()
        solver.run(checkpoint - previous)
        cumulative_train += time.perf_counter() - train_started
        previous = checkpoint

        snapshot_started = time.perf_counter()
        snap = solver.snapshot()
        cumulative_eval += time.perf_counter() - snapshot_started
        final = snap.exploitability
        print(
            f"iteration={checkpoint} expected_u0={snap.expected_u0:.12f} "
            f"br0={snap.br0:.12f} br1={snap.br1:.12f} "
            f"nash_conv={snap.nash_conv:.12f} "
            f"exploitability={snap.exploitability:.12f} "
            f"cumulative_train_seconds={cumulative_train:.6f} "
            f"cumulative_exact_eval_seconds={cumulative_eval:.6f}"
        )
    sampled_terminal_evals = checkpoints[-1] * 12
    print(
        f"training_seconds={cumulative_train:.6f} "
        f"exact_evaluation_seconds={cumulative_eval:.6f} "
        f"approx_training_terminal_evaluations={sampled_terminal_evals}"
    )

    if final is None or not final < uniform_exploitability:
        raise SystemExit(
            f"external-sampling MCCFR did not improve exploitability: "
            f"final={final} uniform={uniform_exploitability}"
        )
    print("HU EXTERNAL-SAMPLING MCCFR BENCHMARK: PASS")


if __name__ == "__main__":
    main()
