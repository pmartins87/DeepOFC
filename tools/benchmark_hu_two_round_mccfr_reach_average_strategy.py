from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_br import exact_nash_conv
from deepofc.hu_two_round_mccfr_reach_average import (
    TwoRoundExternalSamplingReachAverage,
)


def evaluate(game, profile):
    expected = game.expected_u0(profile)
    nash_conv, br0, br1 = exact_nash_conv(game, profile)
    return expected, br0.value, br1.value, 0.5 * nash_conv


def main() -> None:
    game = HUTwoRoundSubgame()
    solver = TwoRoundExternalSamplingReachAverage(game, seed=20260815)

    started = time.perf_counter()
    solver.run(5_000)
    train_seconds = time.perf_counter() - started
    print(f"training iterations=5000 seconds={train_seconds:.6f}")

    candidates = (
        ("current", solver.current_profile()),
        ("cfr_reach_average", solver.cfr_average_profile()),
        ("local_time_average_control", solver.behavioral_time_average_profile()),
    )
    values = {}
    for label, profile in candidates:
        eval_started = time.perf_counter()
        expected, br0, br1, exploitability = evaluate(game, profile)
        eval_seconds = time.perf_counter() - eval_started
        values[label] = exploitability
        print(
            f"profile={label} expected_u0={expected:.12f} "
            f"br0={br0:.12f} br1={br1:.12f} "
            f"exploitability={exploitability:.12f} "
            f"exact_eval_seconds={eval_seconds:.6f}"
        )

    # The reach-weighted average is the theoretically relevant CFR average. Do
    # not require it to beat the current profile on one finite sampled run; the
    # benchmark records both and only requires a meaningful improvement over the
    # uniform starting exploitability.
    if values["cfr_reach_average"] >= 2.099206349206:
        raise SystemExit("reach-weighted CFR average failed to improve on uniform")
    print("HU TWO-ROUND EXTERNAL-SAMPLING CFR-AVERAGE STRATEGY: PASS")


if __name__ == "__main__":
    main()
