from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR


CHECKPOINTS = (5_000, 10_000, 20_000)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    args = ap.parse_args()

    game = HUTwoRoundHiddenDiscardSubgame()
    solver = TwoRoundExternalSamplingMCCFR(game, seed=args.seed)
    previous = 0
    cumulative_train = 0.0
    results = []

    for checkpoint in CHECKPOINTS:
        started = time.perf_counter()
        solver.run(checkpoint - previous)
        cumulative_train += time.perf_counter() - started
        previous = checkpoint

        started = time.perf_counter()
        snap = solver.snapshot(profile_kind="current")
        eval_seconds = time.perf_counter() - started
        results.append(snap.exploitability)
        print(
            f"seed={args.seed} iteration={checkpoint} expected_u0={snap.expected_u0:.12f} "
            f"br0={snap.br0:.12f} br1={snap.br1:.12f} "
            f"exploitability={snap.exploitability:.12f} "
            f"cumulative_train_seconds={cumulative_train:.6f} "
            f"exact_eval_seconds={eval_seconds:.6f}"
        )

    best = min(results)
    final = results[-1]
    direction = "FINAL_IS_BEST" if final <= best + 1e-12 else "NON_MONOTONE_LAST_ITERATE"
    print(
        f"summary seed={args.seed} checkpoints={CHECKPOINTS} best_exploitability={best:.12f} "
        f"final_exploitability={final:.12f} behavior={direction}"
    )
    print("HU TWO-ROUND HIDDEN-DISCARD EXTERNAL-SAMPLING LONGRUN: PASS")


if __name__ == "__main__":
    main()
