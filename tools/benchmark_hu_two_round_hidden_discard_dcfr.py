from __future__ import annotations

from pathlib import Path
import math
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round_br import exact_nash_conv
from deepofc.hu_two_round_cfr import TwoRoundFullTreeCFR
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame


def main() -> None:
    game = HUTwoRoundHiddenDiscardSubgame()
    uniform = game.uniform_profile()
    uniform_conv, uniform_br0, uniform_br1 = exact_nash_conv(game, uniform)
    uniform_exp = 0.5 * uniform_conv

    solver = TwoRoundFullTreeCFR(game, variant="dcfr")
    started = time.perf_counter()
    solver.run(8)
    train_seconds = time.perf_counter() - started

    started = time.perf_counter()
    snap = solver.snapshot()
    eval_seconds = time.perf_counter() - started

    if not math.isfinite(snap.exploitability):
        raise SystemExit("hidden-discard DCFR produced non-finite exploitability")
    if snap.exploitability >= uniform_exp:
        raise SystemExit(
            f"hidden-discard DCFR failed to improve uniform: {snap.exploitability} >= {uniform_exp}"
        )

    print(
        f"uniform br0={uniform_br0.value:.12f} br1={uniform_br1.value:.12f} "
        f"exploitability={uniform_exp:.12f}"
    )
    print(
        f"dcfr iterations=8 expected_u0={snap.expected_u0:.12f} "
        f"br0={snap.br0:.12f} br1={snap.br1:.12f} "
        f"nash_conv={snap.nash_conv:.12f} exploitability={snap.exploitability:.12f} "
        f"train_seconds={train_seconds:.6f} exact_eval_seconds={eval_seconds:.6f}"
    )
    print(f"terminal_cache={game.terminal_u0.cache_info()}")
    print("HU TWO-ROUND HIDDEN-DISCARD DCFR: PASS")


if __name__ == "__main__":
    main()
