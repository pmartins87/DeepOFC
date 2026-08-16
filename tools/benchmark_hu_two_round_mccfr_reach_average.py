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
    linear_numerator = {
        info: {action: 0.0 for action in actions}
        for info, actions in game.info_actions.items()
    }
    linear_mass = {info: 0.0 for info in game.info_actions}

    started = time.perf_counter()
    for t in range(1, 6):
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
            linear_mass[info] += t * own_reach
            if own_reach != 0.0:
                for action in actions:
                    contribution = own_reach * profile[info][action]
                    numerator[info][action] += contribution
                    linear_numerator[info][action] += t * contribution
        solver.step()

    standard = solver.cfr_average_profile()
    linear = solver.linear_cfr_average_profile()
    worst_standard = 0.0
    worst_linear = 0.0
    worst_standard_label = None
    worst_linear_label = None
    compared = 0
    for info, actions in game.info_actions.items():
        if mass[info] <= 0.0:
            brute = {action: 1.0 / len(actions) for action in actions}
        else:
            brute = {
                action: numerator[info][action] / mass[info]
                for action in actions
            }
        if linear_mass[info] <= 0.0:
            brute_linear = {action: 1.0 / len(actions) for action in actions}
        else:
            brute_linear = {
                action: linear_numerator[info][action] / linear_mass[info]
                for action in actions
            }
        for action in actions:
            standard_error = abs(brute[action] - standard[info][action])
            linear_error = abs(brute_linear[action] - linear[info][action])
            compared += 1
            if standard_error > worst_standard:
                worst_standard = standard_error
                worst_standard_label = (
                    info, action, brute[action], standard[info][action]
                )
            if linear_error > worst_linear:
                worst_linear = linear_error
                worst_linear_label = (
                    info, action, brute_linear[action], linear[info][action]
                )

    elapsed = time.perf_counter() - started
    print(
        "reach_average_crosscheck "
        f"iterations=5 infosets={len(game.info_actions)} "
        f"actions_compared={compared} "
        f"standard_max_abs_probability_error={worst_standard:.18e} "
        f"linear_max_abs_probability_error={worst_linear:.18e} "
        f"seconds={elapsed:.6f}"
    )
    if worst_standard > 1e-12:
        raise SystemExit(
            "event-lazy standard CFR average disagrees with brute reference: "
            f"{worst_standard_label}"
        )
    if worst_linear > 1e-12:
        raise SystemExit(
            "event-lazy linear CFR average disagrees with brute reference: "
            f"{worst_linear_label}"
        )
    print("HU TWO-ROUND REACH-WEIGHTED STANDARD+LINEAR CFR AVERAGE: PASS")


if __name__ == "__main__":
    main()
