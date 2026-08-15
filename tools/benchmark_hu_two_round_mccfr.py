from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR


FROZEN_UNIFORM_EXPLOITABILITY = 2.099206349206


def main() -> None:
    game = HUTwoRoundSubgame()
    solver = TwoRoundExternalSamplingMCCFR(game, seed=20260815)

    train_started = time.perf_counter()
    solver.run(5_000)
    train_seconds = time.perf_counter() - train_started
    print(f"training iterations=5000 seconds={train_seconds:.6f}")

    current_started = time.perf_counter()
    current = solver.snapshot(profile_kind="current")
    current_eval_seconds = time.perf_counter() - current_started
    print(
        "profile=current "
        f"expected_u0={current.expected_u0:.12f} "
        f"br0={current.br0:.12f} br1={current.br1:.12f} "
        f"nash_conv={current.nash_conv:.12f} "
        f"exploitability={current.exploitability:.12f} "
        f"exact_eval_seconds={current_eval_seconds:.6f}"
    )

    average_started = time.perf_counter()
    average = solver.snapshot(profile_kind="behavioral_time_average")
    average_eval_seconds = time.perf_counter() - average_started
    print(
        "profile=behavioral_time_average "
        f"expected_u0={average.expected_u0:.12f} "
        f"br0={average.br0:.12f} br1={average.br1:.12f} "
        f"nash_conv={average.nash_conv:.12f} "
        f"exploitability={average.exploitability:.12f} "
        f"exact_eval_seconds={average_eval_seconds:.6f}"
    )

    best = min(current.exploitability, average.exploitability)
    if best >= FROZEN_UNIFORM_EXPLOITABILITY:
        raise SystemExit(
            "deep external sampling failed to improve either evaluated policy: "
            f"best={best} uniform={FROZEN_UNIFORM_EXPLOITABILITY}"
        )
    print("HU TWO-ROUND EXTERNAL-SAMPLING MCCFR: PASS")


if __name__ == "__main__":
    main()
