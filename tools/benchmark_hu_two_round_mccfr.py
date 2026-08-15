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
FROZEN_PRECACHE_CURRENT = {
    "expected_u0": 0.0,
    "br0": 0.011904761905,
    "br1": 0.013130252101,
    "exploitability": 0.012517507003,
}
FROZEN_PRECACHE_LOCAL_AVERAGE = {
    "expected_u0": 0.001601589197,
    "br0": 0.173029043717,
    "br1": 0.176124911342,
    "exploitability": 0.174576977529,
}


def _assert_frozen(label, snapshot, frozen):
    for field, expected in frozen.items():
        observed = getattr(snapshot, field)
        if abs(observed - expected) > 1e-10:
            raise SystemExit(
                f"memoization changed {label} {field}: {observed} vs {expected}"
            )


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
    _assert_frozen("current", current, FROZEN_PRECACHE_CURRENT)
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
    _assert_frozen(
        "behavioral_time_average", average, FROZEN_PRECACHE_LOCAL_AVERAGE
    )
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
    print(f"terminal_cache={game.terminal_u0.cache_info()}")
    print(f"round3_board_cache={game._boards_after_round3.cache_info()}")
    print(f"round4_info_cache={game.round4_info.cache_info()}")
    print("HU TWO-ROUND EXTERNAL-SAMPLING MCCFR: PASS")


if __name__ == "__main__":
    main()
