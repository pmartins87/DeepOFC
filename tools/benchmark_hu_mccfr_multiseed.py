from __future__ import annotations

from pathlib import Path
import math
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_mccfr import ExternalSamplingMCCFR
from deepofc.hu_subgame import HUFinalRoundSubgame


SEEDS = (
    1954132610,
    372483540,
    20260815,
    12345,
    917331,
    440021,
    771923,
    880113,
    314159,
    271828,
)
CHECKPOINTS = (2000, 10000, 20000)


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def main() -> None:
    game = HUFinalRoundSubgame()
    uniform_exploitability = game.exploitability(game.uniform_profile())
    by_checkpoint: dict[int, list[tuple[float, float, float]]] = {
        checkpoint: [] for checkpoint in CHECKPOINTS
    }

    wall_started = time.perf_counter()
    for seed in SEEDS:
        solver = ExternalSamplingMCCFR(game, seed=seed)
        previous = 0
        cumulative_train = 0.0
        for checkpoint in CHECKPOINTS:
            train_started = time.perf_counter()
            solver.run(checkpoint - previous)
            cumulative_train += time.perf_counter() - train_started
            previous = checkpoint
            snap = solver.snapshot()
            by_checkpoint[checkpoint].append(
                (snap.exploitability, abs(snap.expected_u0), cumulative_train)
            )
            print(
                f"seed={seed} iteration={checkpoint} "
                f"exploitability={snap.exploitability:.12f} "
                f"abs_expected_u0={abs(snap.expected_u0):.12f} "
                f"train_seconds={cumulative_train:.6f}"
            )

    for checkpoint in CHECKPOINTS:
        rows = by_checkpoint[checkpoint]
        exploitabilities = [row[0] for row in rows]
        abs_values = [row[1] for row in rows]
        train_seconds = [row[2] for row in rows]
        print(
            f"summary iteration={checkpoint} seeds={len(rows)} "
            f"mean_exploitability={statistics.fmean(exploitabilities):.12f} "
            f"median_exploitability={statistics.median(exploitabilities):.12f} "
            f"p95_exploitability={p95(exploitabilities):.12f} "
            f"min_exploitability={min(exploitabilities):.12f} "
            f"max_exploitability={max(exploitabilities):.12f} "
            f"mean_abs_expected_u0={statistics.fmean(abs_values):.12f} "
            f"p95_abs_expected_u0={p95(abs_values):.12f} "
            f"mean_train_seconds={statistics.fmean(train_seconds):.6f}"
        )

    final_values = [row[0] for row in by_checkpoint[CHECKPOINTS[-1]]]
    if statistics.fmean(final_values) >= uniform_exploitability:
        raise SystemExit("multi-seed MCCFR failed to improve mean exploitability")
    if p95(final_values) >= uniform_exploitability:
        raise SystemExit("multi-seed MCCFR failed to improve p95 exploitability")

    print(f"wall_seconds={time.perf_counter() - wall_started:.6f}")
    print("HU EXTERNAL-SAMPLING MCCFR MULTISEED: PASS")


if __name__ == "__main__":
    main()
