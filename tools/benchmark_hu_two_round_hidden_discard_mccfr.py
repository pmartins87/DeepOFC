from __future__ import annotations

from pathlib import Path
import math
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round_br import exact_nash_conv
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR


def main() -> None:
    game = HUTwoRoundHiddenDiscardSubgame()
    uniform = game.uniform_profile()
    uniform_conv, uniform_br0, uniform_br1 = exact_nash_conv(game, uniform)
    uniform_exp = 0.5 * uniform_conv

    solver = TwoRoundExternalSamplingMCCFR(game, seed=20260815)
    started = time.perf_counter()
    solver.run(5_000)
    train_seconds = time.perf_counter() - started

    started = time.perf_counter()
    snap = solver.snapshot(profile_kind="current")
    eval_seconds = time.perf_counter() - started

    if not math.isfinite(snap.exploitability):
        raise SystemExit("hidden-discard external sampling produced non-finite exploitability")
    if snap.exploitability >= uniform_exp:
        raise SystemExit(
            "hidden-discard external sampling failed to improve uniform: "
            f"{snap.exploitability} >= {uniform_exp}"
        )

    print(
        f"uniform br0={uniform_br0.value:.12f} br1={uniform_br1.value:.12f} "
        f"exploitability={uniform_exp:.12f}"
    )
    print(
        f"external_sampling iterations=5000 expected_u0={snap.expected_u0:.12f} "
        f"br0={snap.br0:.12f} br1={snap.br1:.12f} "
        f"nash_conv={snap.nash_conv:.12f} exploitability={snap.exploitability:.12f} "
        f"train_seconds={train_seconds:.6f} exact_eval_seconds={eval_seconds:.6f}"
    )
    print(f"terminal_cache={game.terminal_u0.cache_info()}")
    print("HU TWO-ROUND HIDDEN-DISCARD EXTERNAL-SAMPLING MCCFR: PASS")


if __name__ == "__main__":
    main()
