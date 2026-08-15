from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_mccfr_reach_average import (
    TwoRoundExternalSamplingReachAverage,
)


def main() -> None:
    game = HUTwoRoundSubgame()
    solver = TwoRoundExternalSamplingReachAverage(game, seed=20260815)

    numerator = {
        info: {action: 0.0 for action in actions}
        for info, actions in game.info_actions.items()
    }
    mass = {info: 0.0 for info in game.info_actions}

    started = time.perf_counter()
    for _ in range(5):
        # Brute reference: scan every infoset before the sampled update, using
        # exactly the behavioral profile that will be used this iteration.
        profile = solver.current_profile()
        for info, actions in game.info_actions.items():
            if info.round_index == 3:
                own_reach = 1.0
            else:
                parent, parent_action = solver.round4_parent[info]
                own_reach = profile[parent][parent_action]
            mass[info] += own_reach
            if own_reach != 0.0:
                for action in actions:
                    numerator[info][action] += (
                        own_reach * profile[info][action]
                    )
        solver.step()

    lazy = solver.cfr_average_profile()
    worst = 0.0
    worst_label = None
    compared = 0
    for info, actions in game.info_actions.items():
        if mass[info] <= 0.0:
            brute = {action: 1.0 / len(actions) for action in actions}
        else:
            brute = {
                action: numerator[info][action] / mass[info]
                for action in actions
            }
        for action in actions:
            error = abs(brute[action] - lazy[info][action])
            compared += 1
            if error > worst:
                worst = error
                worst_label = (info, action, brute[action], lazy[info][action])

    elapsed = time.perf_counter() - started
    print(
        "reach_average_crosscheck "
        f"iterations=5 infosets={len(game.info_actions)} "
        f"actions_compared={compared} max_abs_probability_error={worst:.18e} "
        f"seconds={elapsed:.6f}"
    )
    if worst > 1e-12:
        raise SystemExit(
            "lazy reach-weighted CFR average disagrees with brute reference: "
            f"{worst_label}"
        )
    print("HU TWO-ROUND REACH-WEIGHTED CFR AVERAGE: PASS")


if __name__ == "__main__":
    main()
