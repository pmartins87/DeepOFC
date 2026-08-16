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
from deepofc.hu_two_round_mccfr_dcfr import TwoRoundExternalSamplingLazyDCFR


STANDARD_EXTERNAL_EXP = 0.014093715255
FULL_TREE_DCFR8_EXP = 0.044624397410


def main() -> None:
    game = HUTwoRoundHiddenDiscardSubgame()
    solver = TwoRoundExternalSamplingLazyDCFR(game, seed=20260815)

    started = time.perf_counter()
    solver.run(5_000)
    train_seconds = time.perf_counter() - started

    started = time.perf_counter()
    profile = solver.current_profile()
    expected = game.expected_u0(profile)
    conv, br0, br1 = exact_nash_conv(game, profile)
    exploitability = 0.5 * conv
    eval_seconds = time.perf_counter() - started

    if not math.isfinite(exploitability):
        raise SystemExit("lazy sampled-DCFR produced non-finite exploitability")
    if exploitability >= FULL_TREE_DCFR8_EXP:
        raise SystemExit(
            "lazy sampled-DCFR failed crossover-vs-full-tree gate: "
            f"{exploitability} >= {FULL_TREE_DCFR8_EXP}"
        )

    relation = (
        "BETTER_THAN_STANDARD_EXTERNAL"
        if exploitability < STANDARD_EXTERNAL_EXP - 1e-12
        else "WORSE_OR_EQUAL_TO_STANDARD_EXTERNAL"
    )
    print(
        f"sampled_dcfr iterations=5000 expected_u0={expected:.12f} "
        f"br0={br0.value:.12f} br1={br1.value:.12f} "
        f"nash_conv={conv:.12f} exploitability={exploitability:.12f} "
        f"train_seconds={train_seconds:.6f} exact_eval_seconds={eval_seconds:.6f}"
    )
    print(
        f"comparison standard_external={STANDARD_EXTERNAL_EXP:.12f} "
        f"full_tree_dcfr8={FULL_TREE_DCFR8_EXP:.12f} relation={relation}"
    )
    print("HU TWO-ROUND HIDDEN-DISCARD LAZY SAMPLED-DCFR: PASS")


if __name__ == "__main__":
    main()
