from __future__ import annotations

from pathlib import Path
import math
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR


SEEDS = (1954132610, 372483540, 20260815, 12345, 917331)
ITERATIONS = 5_000
FROZEN_UNIFORM_EXPLOITABILITY = 2.099206349206


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def main() -> None:
    game = HUTwoRoundSubgame()
    rows = []

    for seed in SEEDS:
        solver = TwoRoundExternalSamplingMCCFR(game, seed=seed)
        train_started = time.perf_counter()
        solver.run(ITERATIONS)
        train_seconds = time.perf_counter() - train_started

        eval_started = time.perf_counter()
        snapshot = solver.snapshot(profile_kind="current")
        eval_seconds = time.perf_counter() - eval_started
        rows.append(
            (
                seed,
                snapshot.exploitability,
                snapshot.expected_u0,
                snapshot.br0,
                snapshot.br1,
                train_seconds,
                eval_seconds,
            )
        )
        print(
            f"seed={seed} exploitability={snapshot.exploitability:.12f} "
            f"expected_u0={snapshot.expected_u0:.12f} "
            f"br0={snapshot.br0:.12f} br1={snapshot.br1:.12f} "
            f"train_seconds={train_seconds:.6f} exact_eval_seconds={eval_seconds:.6f}"
        )

    exploitabilities = [row[1] for row in rows]
    abs_values = [abs(row[2]) for row in rows]
    train_times = [row[5] for row in rows]
    eval_times = [row[6] for row in rows]

    print(
        "summary "
        f"seeds={len(rows)} iterations={ITERATIONS} "
        f"mean_exploitability={statistics.fmean(exploitabilities):.12f} "
        f"median_exploitability={statistics.median(exploitabilities):.12f} "
        f"p95_exploitability={p95(exploitabilities):.12f} "
        f"min_exploitability={min(exploitabilities):.12f} "
        f"max_exploitability={max(exploitabilities):.12f} "
        f"mean_abs_expected_u0={statistics.fmean(abs_values):.12f} "
        f"p95_abs_expected_u0={p95(abs_values):.12f} "
        f"mean_train_seconds={statistics.fmean(train_times):.6f} "
        f"mean_exact_eval_seconds={statistics.fmean(eval_times):.6f}"
    )
    print(f"terminal_cache={game.terminal_u0.cache_info()}")

    if max(exploitabilities) >= FROZEN_UNIFORM_EXPLOITABILITY:
        raise SystemExit("at least one deep sampling seed failed to improve on uniform")
    print("HU TWO-ROUND EXTERNAL-SAMPLING MCCFR MULTISEED: PASS")


if __name__ == "__main__":
    main()
