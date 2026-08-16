from __future__ import annotations

import argparse
from pathlib import Path
import math
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_three_round_br import exact_nash_conv
from deepofc.hu_three_round_cfr import HUThreeRoundFullTreeDCFR
from deepofc.hu_three_round_mccfr import HUThreeRoundExternalSamplingMCCFR
from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame


TARGET_TERMINALS = 1_312_200
EXTERNAL_ITERATIONS = 1_620


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("dcfr", "external"), required=True)
    args = ap.parse_args()

    game = HUThreeRoundSequentialSubgame()

    started = time.perf_counter()
    if args.mode == "dcfr":
        solver = HUThreeRoundFullTreeDCFR(game)
        solver.run(1)
        train_stats = solver.stats()
        profile = solver.current_profile()

        # Iteration one used the uniform policy everywhere. Therefore the DCFR
        # one-iteration average must still be exactly uniform. Freeze this so a
        # future implementation cannot make the unfair comparison silently.
        average = solver.average_profile()
        average_uniform_error = 0.0
        for info, dist in average.items():
            expected = 1.0 / len(dist)
            average_uniform_error = max(
                average_uniform_error,
                max(abs(probability - expected) for probability in dist.values()),
            )
        if average_uniform_error > 1e-12:
            raise SystemExit(
                f"DCFR iteration-one average stopped being uniform: {average_uniform_error}"
            )
        iterations = 1
        terminals = train_stats.terminal_evaluations
        infosets = train_stats.infosets
    else:
        solver = HUThreeRoundExternalSamplingMCCFR(game, seed=20260816)
        solver.run(EXTERNAL_ITERATIONS)
        train_stats = solver.stats()
        profile = solver.current_profile()
        average_uniform_error = float("nan")
        iterations = EXTERNAL_ITERATIONS
        terminals = train_stats.terminal_evaluations
        infosets = train_stats.regret_infosets
    train_seconds = time.perf_counter() - started

    if terminals != TARGET_TERMINALS:
        raise SystemExit(
            f"work-normalization drift for {args.mode}: {terminals} != {TARGET_TERMINALS}"
        )

    started = time.perf_counter()
    nash_conv, br0, br1 = exact_nash_conv(game, profile)
    eval_seconds = time.perf_counter() - started
    exploitability = 0.5 * nash_conv
    if not all(math.isfinite(x) for x in (br0.value, br1.value, exploitability)):
        raise SystemExit("three-round quality benchmark produced non-finite BR diagnostics")
    if exploitability < -1e-10:
        raise SystemExit(f"negative exploitability beyond tolerance: {exploitability}")

    print(
        f"mode={args.mode} iterations={iterations} training_terminals={terminals} "
        f"infosets_touched={infosets} train_seconds={train_seconds:.6f}"
    )
    if args.mode == "dcfr":
        print(f"dcfr_iteration1_average_uniform_max_abs={average_uniform_error:.18e}")
    print(
        f"exact_br br0={br0.value:.12f} br1={br1.value:.12f} "
        f"nash_conv={nash_conv:.12f} exploitability={exploitability:.12f} "
        f"br0_infosets={len(br0.choices)} br1_infosets={len(br1.choices)} "
        f"exact_eval_seconds={eval_seconds:.6f}"
    )
    print("HU THREE-ROUND WORK-NORMALIZED EXACT-BR QUALITY: PASS")


if __name__ == "__main__":
    main()
