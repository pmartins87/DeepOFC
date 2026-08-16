from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class Eval:
    expected_u0: float
    br0: float
    br1: float
    nash_conv: float
    exploitability: float


def evaluate(game: HUTwoRoundSubgame, profile) -> Eval:
    expected = game.expected_u0(profile)
    nash_conv, br0, br1 = exact_nash_conv(game, profile)
    return Eval(
        expected_u0=expected,
        br0=br0.value,
        br1=br1.value,
        nash_conv=nash_conv,
        exploitability=0.5 * nash_conv,
    )


def print_eval(label: str, result: Eval, seconds: float) -> None:
    print(
        f"profile={label} expected_u0={result.expected_u0:.12f} "
        f"br0={result.br0:.12f} br1={result.br1:.12f} "
        f"nash_conv={result.nash_conv:.12f} "
        f"exploitability={result.exploitability:.12f} "
        f"exact_eval_seconds={seconds:.6f}"
    )


def main() -> None:
    game = HUTwoRoundSubgame()
    solver = TwoRoundExternalSamplingReachAverage(game, seed=20260815)

    started = time.perf_counter()
    solver.run(5_000)
    train_seconds = time.perf_counter() - started
    print(f"training iterations=5000 seconds={train_seconds:.6f}")

    evaluations = {}
    profiles = (
        ("current", solver.current_profile()),
        ("reach_weighted_cfr_average", solver.cfr_average_profile()),
        ("linear_reach_weighted_cfr_average", solver.linear_cfr_average_profile()),
    )
    for label, profile in profiles:
        started = time.perf_counter()
        result = evaluate(game, profile)
        seconds = time.perf_counter() - started
        evaluations[label] = result
        print_eval(label, result, seconds)

    current = evaluations["current"]
    frozen_current = 0.012517507003
    if abs(current.exploitability - frozen_current) > 1e-10:
        raise SystemExit(
            "reach-average instrumentation changed current training path: "
            f"{current.exploitability} vs {frozen_current}"
        )
    for label in ("reach_weighted_cfr_average", "linear_reach_weighted_cfr_average"):
        if evaluations[label].exploitability >= 2.099206349206:
            raise SystemExit(
                f"{label} failed to improve over uniform baseline: "
                f"{evaluations[label].exploitability}"
            )

    winner = min(evaluations, key=lambda label: evaluations[label].exploitability)
    print(
        f"winner={winner} current={evaluations['current'].exploitability:.12f} "
        f"standard={evaluations['reach_weighted_cfr_average'].exploitability:.12f} "
        f"linear={evaluations['linear_reach_weighted_cfr_average'].exploitability:.12f}"
    )
    print(f"terminal_cache={game.terminal_u0.cache_info()}")
    print("HU TWO-ROUND EXTERNAL-SAMPLING CURRENT/STANDARD/LINEAR EXACT-BR: PASS")


if __name__ == "__main__":
    main()
