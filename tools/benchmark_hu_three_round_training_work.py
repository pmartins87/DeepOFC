from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_three_round_cfr import HUThreeRoundFullTreeDCFR
from deepofc.hu_three_round_mccfr import HUThreeRoundExternalSamplingMCCFR
from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame


TARGET_TERMINALS = 1_312_200
EXTERNAL_ITERATIONS = 1_620


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("fulltree", "external"), required=True)
    args = ap.parse_args()

    game = HUThreeRoundSequentialSubgame()
    started = time.perf_counter()
    if args.mode == "fulltree":
        solver = HUThreeRoundFullTreeDCFR(game)
        solver.run(1)
        stats = solver.stats()
        iterations = stats.iterations
        terminals = stats.terminal_evaluations
        infosets = stats.infosets
    else:
        solver = HUThreeRoundExternalSamplingMCCFR(game, seed=20260816)
        solver.run(EXTERNAL_ITERATIONS)
        stats = solver.stats()
        iterations = stats.iterations
        terminals = stats.terminal_evaluations
        infosets = stats.regret_infosets
    seconds = time.perf_counter() - started

    if terminals != TARGET_TERMINALS:
        raise SystemExit(
            f"work-normalization drift for {args.mode}: {terminals} != {TARGET_TERMINALS}"
        )
    print(
        f"mode={args.mode} iterations={iterations} terminal_evaluations={terminals} "
        f"infosets_touched={infosets} train_seconds={seconds:.6f} "
        f"terminals_per_second={terminals/seconds:.3f}"
    )
    print("HU THREE-ROUND WORK-NORMALIZED TRAINING COST: PASS")


if __name__ == "__main__":
    main()
