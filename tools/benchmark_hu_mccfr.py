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
    uniform_exploitability = game.exploitability(uniform)
    print(
        f"uniform_exploitability={uniform_exploitability:.12f} "
        f"exact_reference_value={game.exact_reference_value:.12f}"
    )

    solver = ExternalSamplingMCCFR(game, seed=20260815)
    checkpoints = (100, 500, 2000, 10000, 50000)
    previous = 0
    started = time.perf_counter()
    final = None
    for checkpoint in checkpoints:
        solver.run(checkpoint - previous)
        previous = checkpoint
        snap = solver.snapshot()
        final = snap.exploitability
        print(
            f"iteration={checkpoint} expected_u0={snap.expected_u0:.12f} "
            f"br0={snap.br0:.12f} br1={snap.br1:.12f} "
            f"nash_conv={snap.nash_conv:.12f} "
            f"exploitability={snap.exploitability:.12f}"
        )
    elapsed = time.perf_counter() - started
    print(f"total_seconds={elapsed:.6f}")

    if final is None or not final < uniform_exploitability:
        raise SystemExit(
            f"external-sampling MCCFR did not improve exploitability: "
            f"final={final} uniform={uniform_exploitability}"
        )
    print("HU EXTERNAL-SAMPLING MCCFR BENCHMARK: PASS")


if __name__ == "__main__":
    main()
