from __future__ import annotations

from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR


SEEDS = (1954132610, 372483540, 20260815, 12345, 917331)
DCFR8_EXPLOITABILITY = 0.044624397410


def main() -> None:
    game = HUTwoRoundHiddenDiscardSubgame()
    results = []
    for seed in SEEDS:
        solver = TwoRoundExternalSamplingMCCFR(game, seed=seed)
        started = time.perf_counter()
        solver.run(5_000)
        train_seconds = time.perf_counter() - started
        started = time.perf_counter()
        snap = solver.snapshot(profile_kind="current")
        eval_seconds = time.perf_counter() - started
        results.append(snap.exploitability)
        print(
            f"seed={seed} exploitability={snap.exploitability:.12f} "
            f"expected_u0={snap.expected_u0:.12f} br0={snap.br0:.12f} br1={snap.br1:.12f} "
            f"train_seconds={train_seconds:.6f} exact_eval_seconds={eval_seconds:.6f}"
        )

    ordered = sorted(results)
    mean = statistics.fmean(results)
    median = statistics.median(results)
    p95 = ordered[-1]
    worst = max(results)
    best = min(results)
    if worst >= DCFR8_EXPLOITABILITY:
        raise SystemExit(
            "hidden-discard external sampling failed robust crossover gate: "
            f"worst_seed={worst} dcfr8={DCFR8_EXPLOITABILITY}"
        )
    print(
        f"summary seeds={len(SEEDS)} iterations=5000 mean_exploitability={mean:.12f} "
        f"median_exploitability={median:.12f} p95_exploitability={p95:.12f} "
        f"min_exploitability={best:.12f} max_exploitability={worst:.12f}"
    )
    print("HU TWO-ROUND HIDDEN-DISCARD EXTERNAL-SAMPLING MULTISEED: PASS")


if __name__ == "__main__":
    main()
